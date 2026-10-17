"""The observation service: it looks at the cameras the server has, notices movement, weighs it with the radar tracks and the light, and tells the server.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Every few seconds, while the system is armed (disarmed, it only waits and looks at nothing), it asks the server for the context - the mode, the radar nodes with their tracks
and light, the cameras - takes one tiny grey frame of each camera, and compares it with the previous one (motion.py). A movement counts only when it is seen in a few frames
in a row, it is not the whole picture changing (a light switched on) and the policy (policy.py) finds it worth a *review* - or *high* when it is strong and a radar track agrees.
Then it reports it (`POST /api/v1/ai/observations`) and the server raises the alarm - at most once until it is closed - so that the notifications, Telegram and Home Assistant
all work from what is already there. The service holds no camera address or password: the server takes the frames. It recommends; it cannot arm, disarm or change anything.

    python -m armor_server_ai.service            # runs for ever (what the unit does)
    python -m armor_server_ai.service --once     # one pass, printing what it saw, for a check by hand

Settings, from the environment: ARMOR_AI_TOKEN (required), ARMOR_AI_SERVER_URL (default http://127.0.0.1:18080), ARMOR_AI_INTERVAL_S (3),
ARMOR_AI_CONFIRM_FRAMES (2), ARMOR_AI_COOLDOWN_S (60).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
from concurrent.futures import ThreadPoolExecutor
import os
import signal
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .motion import FRAME_BYTES, changed_ratio, estimate_lux, mask_from_zones, motion_confidence
from .policy import VisualObservation, decide
from .profile import ProfileSelector

#: A change of more than this share of the picture is the light changing (a lamp, the sun, the camera's exposure), not something moving in it.
GLOBAL_CHANGE_RATIO = 0.60
#: Less than this share of the picture moving is not movement (the radar alone is not what this service reports: the radar nodes have their own alarms).
MIN_MOTION_RATIO = 0.01


class ServerError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(f"{status} {code}")
        self.status, self.code = status, code


#: What the server may send back, at most: the context (a house's nodes and cameras) and a reply to an observation; a frame is exactly FRAME_BYTES.
MAX_CONTEXT_BYTES = 1_000_000
MAX_REPLY_BYTES = 65_536
#: The server lets this service ask for this many pictures a minute altogether.
FRAMES_PER_MINUTE = 200


def check_server_url(url: str) -> str:
    """The token travels in clear over plain http, so that is accepted only to this same machine; anything else must be https (and no file:// or ftp://)."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    local = host == "localhost"
    if not local:
        try:
            local = ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
    if parsed.scheme == "https" and host or (parsed.scheme == "http" and local):
        return url
    raise SystemExit("ARMOR_AI_SERVER_URL must be https://..., or http:// to this same machine (127.0.0.1 or localhost): the token must not cross a network in clear")


def min_interval_s(cameras: int) -> float:
    """A pass asks for one picture per camera: with more cameras than the server's limit allows every few seconds, the pass is spaced out so none is refused."""
    return cameras * 60.0 / FRAMES_PER_MINUTE


class Server(Protocol):
    def context(self) -> dict: ...
    def frame(self, camera_id: str) -> bytes: ...
    def observe(self, report: dict) -> dict: ...


class HttpServer:
    """The three things the service may ask of ARMOR-SERVER, with its own token."""

    def __init__(self, base_url: str, token: str, timeout_s: float = 15.0) -> None:
        self._base, self._token, self._timeout = base_url.rstrip("/"), token, timeout_s

    def _call(self, method: str, path: str, body: dict | None = None, limit: int = MAX_REPLY_BYTES) -> bytes:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self._base + path, data=data, method=method, headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json", **({"Content-Type": "application/json"} if data else {})})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as reply:   # noqa: S310 - the scheme is checked by check_server_url
                return reply.read(limit + 1)[:limit + 1]
        except urllib.error.HTTPError as error:
            detail = ""
            try:
                detail = str(json.loads(error.read()).get("error", ""))
            except (ValueError, AttributeError):
                pass
            raise ServerError(error.code, detail or "http_error") from None
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ServerError(0, "unreachable") from error

    def context(self) -> dict:
        return json.loads(self._call("GET", "/api/v1/ai/context", limit=MAX_CONTEXT_BYTES))

    def frame(self, camera_id: str) -> bytes:
        return self._call("GET", f"/api/v1/ai/cameras/{urllib.request.quote(camera_id, safe='')}/frame", limit=FRAME_BYTES)

    def observe(self, report: dict) -> dict:
        return json.loads(self._call("POST", "/api/v1/ai/observations", report))


@dataclass
class CameraState:
    """What is remembered about one camera between passes."""

    selector: ProfileSelector = field(default_factory=ProfileSelector)
    previous: bytes | None = None
    streak: int = 0
    last_report_s: float | None = None


@dataclass(frozen=True)
class Sighting:
    camera_id: str
    severity: str
    reasons: tuple[str, ...]
    profile: str
    motion: float
    radar_tracks: int
    #: When the camera was last told about, before this sighting: given back if the server never got it, so a hiccup does not silence the camera for a whole cooldown.
    previous_report_s: float | None = None


def _count(value: object) -> int:
    """Radar targets of a node: a number, or the list of them; anything else is none."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, (int, float)):
        return max(0, int(value))
    return len(value) if isinstance(value, list) else 0


def look(state: CameraState, camera_id: str, frame: bytes, now_s: float, radar_tracks: int, node_lux: float | None, confirm_frames: int, cooldown_s: float, ignore: bytes | None = None) -> Sighting | None:
    """Weigh one frame of a camera against the one before; a Sighting when a movement is worth telling the server, else None."""
    previous, state.previous = state.previous, frame
    lux = node_lux if node_lux is not None else estimate_lux(frame)
    profile = state.selector.update(lux, now_s)
    if previous is None:
        return None
    ratio = changed_ratio(previous, frame, mask=ignore)
    if ratio > GLOBAL_CHANGE_RATIO:   # the light changed, not what is in front of the camera
        state.streak = 0
        return None
    if ratio < MIN_MOTION_RATIO:
        state.streak = 0
        return None
    confidence = motion_confidence(ratio)
    decision = decide(VisualObservation(label="motion", confidence=confidence, lux=lux, profile=profile, camera_id=camera_id), radar_tracks)
    if decision.severity == "ignore":
        state.streak = 0
        return None
    state.streak += 1
    if state.streak < confirm_frames:
        return None
    if state.last_report_s is not None and now_s - state.last_report_s < cooldown_s:
        return None
    before, state.last_report_s = state.last_report_s, now_s
    return Sighting(camera_id, decision.severity, decision.reasons, profile, round(confidence, 3), radar_tracks, before)


class Watcher:
    """One pass at a time, so a test (or `--once`) can drive it."""

    def __init__(self, server: Server, confirm_frames: int = 2, cooldown_s: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        if confirm_frames < 1:
            raise ValueError("confirm_frames must be at least 1")
        self._server, self._confirm, self._cooldown, self._clock = server, confirm_frames, cooldown_s, clock
        self._cameras: dict[str, CameraState] = {}
        self._problems: dict[str, str] = {}   # what was last said about each camera, so it is said again only when it changes
        self.camera_count = 0

    def _say_camera(self, camera_id: str, problem: str) -> None:
        if self._problems.get(camera_id, "") == problem:
            return
        self._problems[camera_id] = problem
        print(f"armor-ai: camera {camera_id}: {problem}" if problem else f"armor-ai: camera {camera_id} answers again", file=sys.stderr, flush=True)

    def run_once(self) -> list[dict]:
        """One pass over the cameras; what was told to the server, as dicts."""
        context = self._server.context()
        if not isinstance(context, dict):
            raise ServerError(0, "bad_context")
        if context.get("mode") != "armed":
            self._cameras.clear()   # when it is armed again the first frame has nothing old to be compared with
            self.camera_count = 0
            return []
        raw_nodes = context.get("nodes")
        online = [node for node in (raw_nodes if isinstance(raw_nodes, list) else []) if isinstance(node, dict) and node.get("online")]
        told: list[dict] = []
        raw_cameras = context.get("cameras")
        cameras = {camera["id"]: camera for camera in (raw_cameras if isinstance(raw_cameras, list) else []) if isinstance(camera, dict) and isinstance(camera.get("id"), str)}
        self.camera_count = len(cameras)
        wanted = set(cameras)
        for gone in set(self._cameras) - wanted:
            del self._cameras[gone]
        # The pictures are asked for at the same time: a camera that does not answer made every other one wait its whole timeout, pass after pass.
        def fetch(camera_id: str):
            try:
                return self._server.frame(camera_id)
            except ServerError as error:
                return error
        order = sorted(wanted)
        with ThreadPoolExecutor(max_workers=min(4, max(1, len(order)))) as pool:
            frames = dict(zip(order, pool.map(fetch, order)))
        for camera_id in order:
            frame = frames[camera_id]
            if isinstance(frame, ServerError):
                # a camera that did not answer: the next frame starts again, but what is remembered of it (the cooldown, the day/night choice) is kept
                state = self._cameras.get(camera_id)
                if state is not None:
                    state.previous, state.streak = None, 0
                self._say_camera(camera_id, f"no picture ({frame.code})")
                continue
            if len(frame) != FRAME_BYTES:
                self._say_camera(camera_id, "the picture is not the size expected")
                continue
            self._say_camera(camera_id, "")
            try:
                told += self._watch_camera(camera_id, cameras[camera_id], frame, online)
            except (ValueError, TypeError, KeyError, AttributeError, ServerError) as error:   # one odd camera must not blind the others
                self._say_camera(camera_id, f"could not be judged ({error})")
        return told

    def _watch_camera(self, camera_id: str, camera: dict, frame: bytes, online: list[dict]) -> list[dict]:
        # The radar nodes and the light that count for this camera are the ones the server says cover it (`nodes` in its entry); when it does not say, all of them do (as before).
        covering = camera.get("nodes")
        nodes = [node for node in online if (node.get("id") or node.get("node_id")) in covering] if isinstance(covering, list) and covering else online
        tracks = sum(_count(node.get("targets")) for node in nodes)
        lux_values = [float(node["lux"]) for node in nodes if isinstance(node.get("lux"), (int, float))]
        node_lux = min(lux_values) if lux_values else None
        # the zones of the picture that the person said to ignore (a tree, a road, a screen): the server sends them with the camera
        ignore = mask_from_zones(camera.get("ignore"))
        state = self._cameras.setdefault(camera_id, CameraState())
        sighting = look(state, camera_id, frame, self._clock(), tracks, node_lux, self._confirm, self._cooldown, ignore)
        if sighting is None:
            return []
        report = {"camera_id": sighting.camera_id, "severity": sighting.severity, "reasons": list(sighting.reasons), "profile": sighting.profile, "motion": sighting.motion, "radar_tracks": sighting.radar_tracks}
        try:
            answer = self._server.observe(report)
        except ServerError as error:
            state.last_report_s = sighting.previous_report_s   # it never arrived: the next movement is told, not held back by a cooldown it did not earn
            print(f"armor-ai: the observation of {camera_id} could not be told ({error.code})", file=sys.stderr, flush=True)
            return []
        return [{**report, "answer": answer}]


def _number(name: str, default: float, minimum: float, maximum: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        raise SystemExit(f"{name} must be a number") from None
    if not minimum <= value <= maximum:
        raise SystemExit(f"{name} must be between {minimum:g} and {maximum:g}")
    return value


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="A.R.M.O.R. observation service: movement on the cameras, weighed with the radars")
    parser.add_argument("--once", action="store_true", help="one pass, printing what it saw")
    args = parser.parse_args(argv)
    token = os.environ.get("ARMOR_AI_TOKEN", "").strip()
    if len(token) < 24:
        raise SystemExit("ARMOR_AI_TOKEN (at least 24 characters) is needed")
    interval = _number("ARMOR_AI_INTERVAL_S", 3.0, 1.0, 60.0)
    watcher = Watcher(HttpServer(check_server_url(os.environ.get("ARMOR_AI_SERVER_URL", "http://127.0.0.1:18080")), token),
                      confirm_frames=int(_number("ARMOR_AI_CONFIRM_FRAMES", 2, 1, 20)), cooldown_s=_number("ARMOR_AI_COOLDOWN_S", 60.0, 0.0, 3600.0))
    if args.once:
        try:
            print(json.dumps(watcher.run_once(), separators=(",", ":")))
        except ServerError as error:
            raise SystemExit(f"armor-ai: the server could not be asked ({error.code})") from None
        return
    stopping = False

    def stop(*_: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print(f"armor-ai: watching, every {interval:g} s", file=sys.stderr, flush=True)
    last_problem = ""   # what was said last, so it is said again only when it changes, and when it is over
    while not stopping:
        try:
            watcher.run_once()
            if last_problem:
                print("armor-ai: the server answers again", file=sys.stderr, flush=True)
                last_problem = ""
        except Exception as error:   # noqa: BLE001 - whatever the server sends, the service says it once and goes on; a restart would lose what it remembers
            problem = str(getattr(error, "code", None) or f"{type(error).__name__}: {error}")[:120]
            if problem != last_problem:
                print(f"armor-ai: the server could not be asked ({problem})", file=sys.stderr, flush=True)
                last_problem = problem
        time.sleep(max(interval, min_interval_s(watcher.camera_count)))


if __name__ == "__main__":
    main()
