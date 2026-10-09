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
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .motion import FRAME_BYTES, changed_ratio, estimate_lux, motion_confidence
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


class Server(Protocol):
    def context(self) -> dict: ...
    def frame(self, camera_id: str) -> bytes: ...
    def observe(self, report: dict) -> dict: ...


class HttpServer:
    """The three things the service may ask of ARMOR-SERVER, with its own token."""

    def __init__(self, base_url: str, token: str, timeout_s: float = 15.0) -> None:
        self._base, self._token, self._timeout = base_url.rstrip("/"), token, timeout_s

    def _call(self, method: str, path: str, body: dict | None = None) -> bytes:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(self._base + path, data=data, method=method, headers={"Authorization": f"Bearer {self._token}", "Accept": "application/json", **({"Content-Type": "application/json"} if data else {})})
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as reply:
                return reply.read()
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
        return json.loads(self._call("GET", "/api/v1/ai/context"))

    def frame(self, camera_id: str) -> bytes:
        return self._call("GET", f"/api/v1/ai/cameras/{urllib.request.quote(camera_id, safe='')}/frame")

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


def look(state: CameraState, camera_id: str, frame: bytes, now_s: float, radar_tracks: int, node_lux: float | None, confirm_frames: int, cooldown_s: float) -> Sighting | None:
    """Weigh one frame of a camera against the one before; a Sighting when a movement is worth telling the server, else None."""
    previous, state.previous = state.previous, frame
    lux = node_lux if node_lux is not None else estimate_lux(frame)
    profile = state.selector.update(lux, now_s)
    if previous is None:
        return None
    ratio = changed_ratio(previous, frame)
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
    state.last_report_s = now_s
    return Sighting(camera_id, decision.severity, decision.reasons, profile, round(confidence, 3), radar_tracks)


class Watcher:
    """One pass at a time, so a test (or `--once`) can drive it."""

    def __init__(self, server: Server, confirm_frames: int = 2, cooldown_s: float = 60.0, clock: Callable[[], float] = time.monotonic) -> None:
        if confirm_frames < 1:
            raise ValueError("confirm_frames must be at least 1")
        self._server, self._confirm, self._cooldown, self._clock = server, confirm_frames, cooldown_s, clock
        self._cameras: dict[str, CameraState] = {}

    def run_once(self) -> list[dict]:
        """One pass over the cameras; what was told to the server, as dicts."""
        context = self._server.context()
        if context.get("mode") != "armed":
            self._cameras.clear()   # when it is armed again the first frame has nothing old to be compared with
            return []
        nodes = [node for node in context.get("nodes", []) if node.get("online")]
        tracks = sum(int(node.get("targets") or 0) for node in nodes)
        lux_values = [float(node["lux"]) for node in nodes if isinstance(node.get("lux"), (int, float))]
        node_lux = min(lux_values) if lux_values else None
        told: list[dict] = []
        wanted = {camera["id"] for camera in context.get("cameras", [])}
        for gone in set(self._cameras) - wanted:
            del self._cameras[gone]
        for camera_id in sorted(wanted):
            try:
                frame = self._server.frame(camera_id)
            except ServerError:
                self._cameras.pop(camera_id, None)   # a camera that did not answer: the next frame starts again
                continue
            if len(frame) != FRAME_BYTES:
                continue
            sighting = look(self._cameras.setdefault(camera_id, CameraState()), camera_id, frame, self._clock(), tracks, node_lux, self._confirm, self._cooldown)
            if sighting is None:
                continue
            report = {"camera_id": sighting.camera_id, "severity": sighting.severity, "reasons": list(sighting.reasons), "profile": sighting.profile, "motion": sighting.motion, "radar_tracks": sighting.radar_tracks}
            try:
                answer = self._server.observe(report)
            except ServerError as error:
                print(f"armor-ai: the observation of {camera_id} could not be told ({error.code})", file=sys.stderr, flush=True)
                continue
            told.append({**report, "answer": answer})
        return told


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
    watcher = Watcher(HttpServer(os.environ.get("ARMOR_AI_SERVER_URL", "http://127.0.0.1:18080"), token),
                      confirm_frames=int(_number("ARMOR_AI_CONFIRM_FRAMES", 2, 1, 20)), cooldown_s=_number("ARMOR_AI_COOLDOWN_S", 60.0, 0.0, 3600.0))
    if args.once:
        print(json.dumps(watcher.run_once(), separators=(",", ":")))
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
        except (ServerError, ValueError) as error:
            problem = str(getattr(error, "code", error))
            if problem != last_problem:
                print(f"armor-ai: the server could not be asked ({problem})", file=sys.stderr, flush=True)
                last_problem = problem
        time.sleep(interval)


if __name__ == "__main__":
    main()
