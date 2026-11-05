"""Movement between two small grey frames, and how bright a frame is.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

No neural network and no GPU: a frame is 64 x 36 grey bytes (the server takes it from the camera's stream and does not keep it), and movement is the share of pixels that
changed by more than a threshold between two frames. It cannot tell a person from a cat or a branch - the fusion policy (policy.py) only trusts it, together with a radar
track, enough to *review* or, when it is strong and the radar agrees, to call high; telling a person from something else needs the Jetson and a detector.

Pure functions, so they are tested without a camera.
"""

from __future__ import annotations

from . import motion_core as core

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
MIN_COUNTED_PIXELS = core.MIN_COUNTED_PIXELS
#: Most ignore zones of a camera.
MAX_ZONES = 16


def mask_from_zones(zones) -> bytes | None:
    """The mask of a camera's ignore zones: 1 for a pixel that counts, 0 for one inside a zone. Each zone is a rectangle in fractions of the picture, `(x, y, width, height)` or a
    dict with those keys; one that is not a rectangle inside the picture is left out. None when there is nothing to ignore (no zones, or none valid)."""
    return core.rect_mask(list(zones or [])[:MAX_ZONES], FRAME_WIDTH, FRAME_HEIGHT)


def observe(previous: bytes, current: bytes, threshold: int = PIXEL_THRESHOLD, mask: bytes | None = None) -> core.Motion:
    """The movement between two frames by the model every observation service shares (motion_core.py): the share of the pixels that changed once the change of the whole picture
    (the camera's exposure, a cloud, the switch to infrared) is taken away, and the cells where it moved. With a `mask` (see mask_from_zones) the pixels inside an ignore zone are
    left out of everything - the changes, the median and the count - so a tree that waves in a corner of the picture is never movement."""
    check_frame(previous)
    check_frame(current)
    if mask is not None and len(mask) != FRAME_BYTES:
        raise ValueError(f"a mask is {FRAME_BYTES} bytes")
    return core.analyze(previous, current, FRAME_WIDTH, FRAME_HEIGHT, threshold, mask)


def changed_ratio(previous: bytes, current: bytes, threshold: int = PIXEL_THRESHOLD, mask: bytes | None = None) -> float:
    """The share (0 to 1) of the pixels that changed by more than `threshold` between two frames (see `observe`)."""
    return observe(previous, current, threshold, mask).ratio


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
