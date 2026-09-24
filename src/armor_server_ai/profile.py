"""Day/night vision profile selection, with hysteresis so dusk cannot make it flap.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Pure decision logic: cameras and GPU runtimes are adapters outside this module.
A single threshold makes the profile toggle on every reading near it (a cloud
passing, a light being switched on). The selector therefore enters low-light
below ``low_lux``, returns to daylight only above ``high_lux`` and never
changes twice within ``min_dwell_s`` seconds.
"""

from __future__ import annotations

from dataclasses import dataclass

DAYLIGHT = "daylight"
LOW_LIGHT = "low-light"
MAX_LUX = 200_000.0


def choose_profile(lux: float, threshold_lux: float = 30.0) -> str:
    """A stateless decision at one threshold (kept for callers that have no history)."""
    _check_lux(lux)
    if threshold_lux < 0:
        raise ValueError("lux values must be non-negative")
    return LOW_LIGHT if lux < threshold_lux else DAYLIGHT


def _check_lux(lux: float) -> None:
    if isinstance(lux, bool) or not isinstance(lux, (int, float)) or lux != lux or lux < 0 or lux > MAX_LUX:
        raise ValueError(f"lux must be a number between 0 and {MAX_LUX:g}")


@dataclass
class ProfileSelector:
    low_lux: float = 30.0
    high_lux: float = 60.0
    min_dwell_s: float = 30.0
    profile: str = DAYLIGHT
    _changed_at: float | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.low_lux < self.high_lux:
            raise ValueError("low_lux must be non-negative and below high_lux")
        if self.min_dwell_s < 0:
            raise ValueError("min_dwell_s must not be negative")
        if self.profile not in (DAYLIGHT, LOW_LIGHT):
            raise ValueError("unknown profile")

    def update(self, lux: float, now_s: float) -> str:
        """Feed one lux reading taken at `now_s`; returns the profile to use."""
        _check_lux(lux)
        wanted = self.profile
        if self.profile == DAYLIGHT and lux < self.low_lux:
            wanted = LOW_LIGHT
        elif self.profile == LOW_LIGHT and lux > self.high_lux:
            wanted = DAYLIGHT
        if wanted != self.profile:
            settled = self._changed_at is None or now_s - self._changed_at >= self.min_dwell_s
            if settled:
                self.profile = wanted
                self._changed_at = now_s
        return self.profile
