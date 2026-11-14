"""Where a radar track is in the picture of a camera: the geometry that lets a movement on the camera and a track of the radar be the same thing.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Without it a radar track anywhere in the area a camera is said to cover counts as evidence for any movement on that camera. With it (off by default, `ARMOR_AI_SPATIAL=1`) a track
counts only when it falls, seen from the camera, on the same side of the picture as a region of movement. The geometry is the one of the site design: a pose is a position on the
floor plan in millimetres and the direction the device faces, in degrees clockwise from the +y axis of the plan.

    node entry:    {"pose": {"x_mm": 0, "y_mm": 0, "yaw_deg": 90}, "targets": [{"x_mm": 500, "y_mm": 3000}, ...]}     (x to the right of the radar, y straight ahead of it)
    camera entry:  {"pose": {"x_mm": 2000, "y_mm": 0, "yaw_deg": 0}, "fov_deg": 90, "range_mm": 15000}

It is a flat approximation (a pinhole camera looking along the plan, no lens distortion, no height): good enough to say "on the left of the picture" and "not in the picture at all",
not to point at a pixel. Anything that is missing or does not make sense leaves today's rule alone: the count of tracks of the nodes that cover the camera.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_FOV_DEG = 90.0
DEFAULT_RANGE_MM = 15_000.0
MAX_COORD_MM = 1_000_000.0
MIN_FOV_DEG, MAX_FOV_DEG = 20.0, 180.0
#: How far outside a region of movement a track may fall and still match (a fraction of the picture width): the radar and the picture do not agree to the pixel.
MARGIN = 0.12


@dataclass(frozen=True)
class Pose:
    x_mm: float
    y_mm: float
    yaw_deg: float


def _number(value: object, low: float, high: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        return None
    return float(value)


def parse_pose(raw: object) -> Pose | None:
    """The pose of a device, or None when it is missing or not three sensible numbers."""
    if not isinstance(raw, dict):
        return None
    x, y, yaw = _number(raw.get("x_mm"), -MAX_COORD_MM, MAX_COORD_MM), _number(raw.get("y_mm"), -MAX_COORD_MM, MAX_COORD_MM), _number(raw.get("yaw_deg"), -720.0, 720.0)
    return None if x is None or y is None or yaw is None else Pose(x, y, yaw)


def _axes(pose: Pose) -> tuple[tuple[float, float], tuple[float, float]]:
    """(forward, right) unit vectors of a pose on the plan."""
    angle = math.radians(pose.yaw_deg)
    return (math.sin(angle), math.cos(angle)), (math.cos(angle), -math.sin(angle))


def track_on_plan(node: Pose, x_mm: float, y_mm: float) -> tuple[float, float]:
    """A radar track (x to the right of the radar, y ahead of it) on the floor plan."""
    forward, right = _axes(node)
    return node.x_mm + x_mm * right[0] + y_mm * forward[0], node.y_mm + x_mm * right[1] + y_mm * forward[1]


def column_in_picture(camera: Pose, fov_deg: float, range_mm: float, point: tuple[float, float]) -> float | None:
    """Where a point of the plan falls across the picture of a camera, 0 at its left edge and 1 at its right; None behind the camera, farther than its range or outside its view."""
    forward, right = _axes(camera)
    dx, dy = point[0] - camera.x_mm, point[1] - camera.y_mm
    ahead, side = dx * forward[0] + dy * forward[1], dx * right[0] + dy * right[1]
    if ahead <= 0 or math.hypot(dx, dy) > range_mm:
        return None
    angle = math.atan2(side, ahead)
    half = math.radians(fov_deg) / 2
    if abs(angle) > half:
        return None
    return 0.5 + math.tan(angle) / (2 * math.tan(half))


def _tracks(raw: object) -> list[tuple[float, float]] | None:
    """The tracks of a node as (x_mm, y_mm), or None when the node gives only a count (or something else) and its tracks cannot be placed."""
    if not isinstance(raw, list):
        return None
    found = []
    for item in raw:
        if isinstance(item, dict):
            x, y = _number(item.get("x_mm"), -MAX_COORD_MM, MAX_COORD_MM), _number(item.get("y_mm"), -MAX_COORD_MM, MAX_COORD_MM)
            if x is not None and y is not None:
                found.append((x, y))
    return found if found or not raw else None


def matching_tracks(camera: dict, nodes: Sequence[dict], regions: Sequence[dict], count_of_all: int) -> int:
    """How many radar tracks agree with the movement of a camera.

    A track of a node whose pose is known counts when it falls inside a region of movement (with a margin) seen from the camera; a track that falls outside the picture, or on another
    side of it, does not. The tracks of a node that cannot be placed (no pose, or only a count) keep counting, as before: geometry that is not there never takes evidence away. Without
    the pose of the camera, or without any region of movement, nothing can be judged and the whole count `count_of_all` is returned.
    """
    pose = parse_pose(camera.get("pose"))
    if pose is None or not regions:
        return count_of_all
    fov = _number(camera.get("fov_deg", DEFAULT_FOV_DEG), MIN_FOV_DEG, MAX_FOV_DEG)
    reach = _number(camera.get("range_mm", DEFAULT_RANGE_MM), 1.0, MAX_COORD_MM)
    if fov is None or reach is None:
        return count_of_all
    total = 0
    for node in nodes:
        placed = _tracks(node.get("targets"))
        node_pose = parse_pose(node.get("pose"))
        if node_pose is None or placed is None:
            total += _unplaced(node.get("targets"))
            continue
        for x_mm, y_mm in placed:
            column = column_in_picture(pose, fov, reach, track_on_plan(node_pose, x_mm, y_mm))
            if column is not None and any(float(r["x"]) - MARGIN <= column <= float(r["x"]) + float(r["w"]) + MARGIN for r in regions):
                total += 1
    return total


def _unplaced(raw: object) -> int:
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, (int, float)):
        return max(0, int(raw))
    return len(raw) if isinstance(raw, list) else 0
