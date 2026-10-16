"""Movement between two small grey frames, and how bright a frame is.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

No neural network and no GPU: a frame is 64 x 36 grey bytes (the server takes it from the camera's stream and does not keep it), and movement is the share of pixels that
changed by more than a threshold between two frames. It cannot tell a person from a cat or a branch - the fusion policy (policy.py) only trusts it, together with a radar
track, enough to *review* or, when it is strong and the radar agrees, to call high; telling a person from something else needs the Jetson and a detector.

Pure functions, so they are tested without a camera.
"""

from __future__ import annotations

FRAME_WIDTH = 64
FRAME_HEIGHT = 36
FRAME_BYTES = FRAME_WIDTH * FRAME_HEIGHT

#: How much a pixel has to change (of 255) to count as moved; below this is the noise of the sensor and of the compression.
PIXEL_THRESHOLD = 18
#: The share of the picture that moving fully means (10 %): a person across a gate is a few per cent of a 64 x 36 frame.
FULL_MOTION_RATIO = 0.10


def check_frame(frame: bytes) -> None:
    if not isinstance(frame, (bytes, bytearray)) or len(frame) != FRAME_BYTES:
        raise ValueError(f"a frame is {FRAME_BYTES} grey bytes")


#: Fewest pixels that must be left to look at once the ignore zones are taken out (about 3 % of the frame): with less, a handful of pixels would decide.
MIN_COUNTED_PIXELS = 64
#: Most ignore zones of a camera.
MAX_ZONES = 16


def mask_from_zones(zones) -> bytes | None:
    """The mask of a camera's ignore zones: 1 for a pixel that counts, 0 for one inside a zone. Each zone is a rectangle in fractions of the picture, `(x, y, width, height)` or a
    dict with those keys; one that is not a rectangle inside the picture is left out. None when there is nothing to ignore (no zones, or none valid)."""
    mask = bytearray(b"\x01" * FRAME_BYTES)
    ignored = False
    for zone in list(zones or [])[:MAX_ZONES]:
        try:
            x, y, w, h = (zone["x"], zone["y"], zone["w"], zone["h"]) if isinstance(zone, dict) else zone
            x, y, w, h = float(x), float(y), float(w), float(h)
        except (KeyError, TypeError, ValueError):
            continue
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 < w <= 1.0 and 0.0 < h <= 1.0):
            continue
        left, right = int(x * FRAME_WIDTH), min(FRAME_WIDTH, int((x + w) * FRAME_WIDTH + 0.999))
        top, bottom = int(y * FRAME_HEIGHT), min(FRAME_HEIGHT, int((y + h) * FRAME_HEIGHT + 0.999))
        for row in range(top, bottom):
            for column in range(left, right):
                mask[row * FRAME_WIDTH + column] = 0
                ignored = True
    return bytes(mask) if ignored else None


def changed_ratio(previous: bytes, current: bytes, threshold: int = PIXEL_THRESHOLD, mask: bytes | None = None) -> float:
    """The share (0 to 1) of the pixels that changed by more than `threshold` between two frames. With a `mask` (see mask_from_zones) the pixels inside an ignore zone are left out of
    everything - the changes, the median that is taken away and the count the share is of - so a tree that waves in a corner of the picture is never movement."""
    check_frame(previous)
    check_frame(current)
    if mask is not None:
        if len(mask) != FRAME_BYTES:
            raise ValueError(f"a mask is {FRAME_BYTES} bytes")
        kept = [index for index in range(FRAME_BYTES) if mask[index]]
        if len(kept) < MIN_COUNTED_PIXELS:
            return 0.0
        differences = [current[index] - previous[index] for index in kept]
        shift = sorted(differences)[len(differences) // 2]
        return sum(1 for difference in differences if abs(difference - shift) > threshold) / len(kept)
    # The whole picture getting brighter or darker (the camera's automatic exposure, a cloud, the switch to infrared) is not something moving: the typical change of all the pixels
    # (their median, which a moving person barely shifts) is taken away first, so only what changed MORE than the rest counts.
    differences = [after - before for before, after in zip(previous, current)]
    shift = sorted(differences)[len(differences) // 2]
    moved = sum(1 for difference in differences if abs(difference - shift) > threshold)
    return moved / FRAME_BYTES


def motion_confidence(ratio: float) -> float:
    """How sure it is that something moved, 0 to 1: the changed share against what moving fully means."""
    if ratio != ratio or ratio < 0:
        raise ValueError("ratio must be a number from 0")
    return min(1.0, ratio / FULL_MOTION_RATIO)


def brightness(frame: bytes) -> float:
    """The mean grey of a frame, 0 (black) to 255."""
    check_frame(frame)
    return sum(frame) / FRAME_BYTES


def estimate_lux(frame: bytes) -> float:
    """A rough lux for the day/night profile when no light sensor says: a camera's picture is dark below about 40 of 255. It is an estimate, not a measurement."""
    return (brightness(frame) / 255.0) ** 2.2 * 800.0
