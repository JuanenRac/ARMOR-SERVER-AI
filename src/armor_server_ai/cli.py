"""JSONL policy worker: reads visual observations, writes explainable recommendations.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

One JSON object per input line:
    {"label": "person", "confidence": 0.91, "lux": 4, "age_s": 0.4, "camera_id": "cam-01"}
One JSON object per output line, in the same order:
    {"line": 1, "severity": "high", "reasons": [...], "authorizes_action": false}
A bad line produces {"line": N, "error": "..."} and never stops the worker. The
output is a recommendation for the central server, never a command.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from typing import TextIO

from .policy import VisualObservation, decide
from .profile import ProfileSelector

MAX_LINE_BYTES = 4096


def process(lines: Iterable[str], radar_tracks: int, selector: ProfileSelector, clock: float = 0.0) -> Iterable[dict]:
    """Yield one result per non-empty input line. `clock` advances by one second per line for the profile selector."""
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if len(line.encode("utf-8", "replace")) > MAX_LINE_BYTES:
            yield {"line": number, "error": f"line is longer than {MAX_LINE_BYTES} bytes"}
            continue
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("each line must be a JSON object")
            lux = float(item["lux"])
            profile = selector.update(lux, clock + number)
            observation = VisualObservation(
                label=str(item["label"]), confidence=float(item["confidence"]), lux=lux, profile=profile,
                camera_id=str(item.get("camera_id", "")), age_s=float(item.get("age_s", 0.0)),
            )
            decision = decide(observation, int(item.get("radar_tracks", radar_tracks)))
            yield {"line": number, "severity": decision.severity, "reasons": list(decision.reasons), "profile": profile, "authorizes_action": decision.authorizes_action}
        except (KeyError, TypeError, ValueError) as error:  # json.JSONDecodeError is a ValueError
            message = f"missing field {error}" if isinstance(error, KeyError) else str(error)
            yield {"line": number, "error": message}


def run(stdin: TextIO, stdout: TextIO, radar_tracks: int) -> None:
    for result in process(stdin, radar_tracks, ProfileSelector()):
        stdout.write(json.dumps(result, separators=(",", ":")) + "\n")
        stdout.flush()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Classify validated visual observations from JSONL")
    parser.add_argument("--radar-tracks", type=int, default=0, help="active radar tracks for the node when a line does not say")
    args = parser.parse_args(argv)
    if args.radar_tracks < 0:
        parser.error("--radar-tracks must be non-negative")
    run(sys.stdin, sys.stdout, args.radar_tracks)


if __name__ == "__main__":
    main()
