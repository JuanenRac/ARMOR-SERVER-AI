"""Learning which parts of a picture are always busy, so that a tree or a road can be proposed as an area to ignore.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Off unless the person turns it on (`ARMOR_AI_LEARN=1`), and only while the system is disarmed: it looks at the pictures of the cameras that the system already takes, compares each with
the one before, and adds one to a counter for every cell of the 16 x 9 grid that moved. What is kept is those counters and the number of comparisons: never a picture, never a copy
of one. After enough comparisons over enough hours, the cells that moved in a large share of them are joined into rectangles and PROPOSED as areas to ignore. Nothing is applied: the
proposal is shown to the person (in the status of the service) and becomes an ignore zone of the camera only when they accept it in the site design.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from .motion_core import GRID_COLUMNS, GRID_ROWS, region_extents, regions

#: Comparisons needed before a proposal is made (at one every 3 s, 24 hours is 28 800; this asks for a fifth of that so that a service that was off at night still learns).
DEFAULT_MIN_COMPARISONS = 5_000
#: Hours between the first and the last comparison before a proposal is made.
DEFAULT_MIN_HOURS = 12.0
#: A cell is proposed when it moved in at least this share of the comparisons.
DEFAULT_BUSY_SHARE = 0.25
MAX_CAMERAS = 64
SCHEMA = 1


class ZoneLearner:
    def __init__(self, path: Path | None = None, min_comparisons: int = DEFAULT_MIN_COMPARISONS, min_hours: float = DEFAULT_MIN_HOURS, busy_share: float = DEFAULT_BUSY_SHARE,
                 clock: Callable[[], float] | None = None) -> None:
        if min_comparisons < 1 or min_hours < 0 or not 0 < busy_share <= 1:
            raise ValueError("min_comparisons must be at least 1, min_hours not negative and busy_share above 0 and at most 1")
        import time
        self._clock = clock or time.time
        self._path, self.min_comparisons, self.min_hours, self.busy_share = path, min_comparisons, min_hours, busy_share
        self._cameras: dict[str, dict] = {}
        if path is not None:
            self._load(path)

    # ---- counting ---------------------------------------------------------------------------------------------------------------------------
    def feed(self, camera_id: str, cells: frozenset | set) -> None:
        """One comparison of two pictures of a camera: the (column, row) cells that moved."""
        entry = self._cameras.get(camera_id)
        if entry is None:
            if len(self._cameras) >= MAX_CAMERAS:
                return
            entry = {"comparisons": 0, "first_s": self._clock(), "last_s": self._clock(), "counts": [[0] * GRID_COLUMNS for _ in range(GRID_ROWS)]}
            self._cameras[camera_id] = entry
        entry["comparisons"] += 1
        entry["last_s"] = self._clock()
        for column, row in cells:
            if 0 <= column < GRID_COLUMNS and 0 <= row < GRID_ROWS:
                entry["counts"][row][column] += 1

    def forget(self, camera_id: str) -> None:
        self._cameras.pop(camera_id, None)

    # ---- proposing --------------------------------------------------------------------------------------------------------------------------
    def ready(self, camera_id: str) -> bool:
        entry = self._cameras.get(camera_id)
        if entry is None:
            return False
        return entry["comparisons"] >= self.min_comparisons and (entry["last_s"] - entry["first_s"]) / 3600.0 >= self.min_hours

    def proposal(self, camera_id: str) -> list[dict] | None:
        """The areas to propose for a camera as rectangles `{x, y, w, h}` (fractions of the picture), or None while there is not enough to say. An empty list means: nothing is always busy."""
        if not self.ready(camera_id):
            return None
        entry = self._cameras[camera_id]
        busy = {(column, row) for row in range(GRID_ROWS) for column in range(GRID_COLUMNS) if entry["counts"][row][column] / entry["comparisons"] >= self.busy_share}
        return regions(region_extents(busy))

    def report(self) -> dict:
        """For the status of the service: how far each camera is and what is proposed. Counters only."""
        return {camera_id: {"comparisons": entry["comparisons"], "ready": self.ready(camera_id), "proposal": self.proposal(camera_id)} for camera_id, entry in sorted(self._cameras.items())}

    # ---- keeping the counters ---------------------------------------------------------------------------------------------------------------
    def save(self) -> bool:
        """Write the counters whole to a neighbour and rename it over the file (a reader never sees half of it); False when there is no file or it cannot be written."""
        if self._path is None:
            return False
        body = json.dumps({"schema": SCHEMA, "cameras": self._cameras}, separators=(",", ":"))
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            handle, name = tempfile.mkstemp(dir=self._path.parent, prefix=self._path.name, suffix=".tmp")
            with os.fdopen(handle, "w", encoding="utf-8") as stream:
                stream.write(body)
            os.replace(name, self._path)
        except OSError:
            return False
        return True

    def _load(self, path: Path) -> None:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(document, dict) or document.get("schema") != SCHEMA or not isinstance(document.get("cameras"), dict):
            return
        for camera_id, entry in list(document["cameras"].items())[:MAX_CAMERAS]:
            counts = entry.get("counts") if isinstance(entry, dict) else None
            ok = (isinstance(camera_id, str) and isinstance(counts, list) and len(counts) == GRID_ROWS
                  and all(isinstance(row, list) and len(row) == GRID_COLUMNS and all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in row) for row in counts)
                  and all(isinstance(entry.get(k), (int, float)) and not isinstance(entry.get(k), bool) and math.isfinite(entry[k]) for k in ("comparisons", "first_s", "last_s")))
            if ok and entry["comparisons"] >= 0 and entry["last_s"] >= entry["first_s"]:
                self._cameras[camera_id] = {"comparisons": int(entry["comparisons"]), "first_s": float(entry["first_s"]), "last_s": float(entry["last_s"]), "counts": counts}
