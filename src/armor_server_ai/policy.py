"""Conservative, explainable correlation of visual detections with radar tracks.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

The policy only ever *recommends*. A `Decision` carries the severity, the
reasons behind it and the fact that it authorises nothing: switching a light,
sounding a siren or moving a camera is the central server's decision, made after
it has authenticated and authorised the event. There is deliberately no field
here that could be read as an instruction to actuate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: "motion" is what the movement detector (motion.py) sees: something moved, not what it is.
LABELS = frozenset({"person", "vehicle", "animal", "unknown", "motion"})
SEVERITIES = ("ignore", "review", "high")
MAX_AGE_S = 10.0

# In low light a camera is less certain, so a slightly lower confidence still
# deserves a human look; the bar for "high" (person plus radar) does not move.
REVIEW_CONFIDENCE = {"daylight": 0.55, "low-light": 0.45}
HIGH_CONFIDENCE = 0.80


@dataclass(frozen=True)
class VisualObservation:
    label: str
    confidence: float
    lux: float
    profile: str = "daylight"
    camera_id: str = ""
    #: Seconds since the frame was taken; an old detection must not raise an alert.
    age_s: float = 0.0


@dataclass(frozen=True)
class Decision:
    severity: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    #: Always False: the policy recommends, the central server decides and acts.
    authorizes_action: bool = False


def _validate(observation: VisualObservation, radar_tracks: int) -> None:
    if observation.label not in LABELS:
        raise ValueError("unrecognised visual label")
    confidence, lux, age = observation.confidence, observation.lux, observation.age_s
    for name, value in (("confidence", confidence), ("lux", lux), ("age_s", age)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != value:
            raise ValueError(f"{name} must be a number")
    if not 0 <= confidence <= 1 or lux < 0 or age < 0:
        raise ValueError("invalid observation range")
    if isinstance(radar_tracks, bool) or not isinstance(radar_tracks, int) or radar_tracks < 0:
        raise ValueError("invalid observation range")
    if observation.profile not in REVIEW_CONFIDENCE:
        raise ValueError("unknown vision profile")


def decide(observation: VisualObservation, radar_tracks: int) -> Decision:
    """Correlate one detection with the radar tracks currently active for the same node."""
    _validate(observation, radar_tracks)
    if observation.age_s > MAX_AGE_S:
        return Decision("ignore", (f"detection is {observation.age_s:.0f} s old; only fresh detections count",))
    review_bar = REVIEW_CONFIDENCE[observation.profile]
    if observation.label == "person" and observation.confidence >= HIGH_CONFIDENCE and radar_tracks:
        return Decision("high", (
            f"person seen with {observation.confidence:.0%} confidence",
            f"{radar_tracks} radar track(s) agree",
        ))
    if observation.label == "motion" and observation.confidence >= HIGH_CONFIDENCE and radar_tracks:
        return Decision("high", (
            f"strong movement on the camera ({observation.confidence:.0%})",
            f"{radar_tracks} radar track(s) agree",
        ))
    reasons: list[str] = []
    if observation.confidence >= review_bar:
        reasons.append(f"{observation.label} seen with {observation.confidence:.0%} confidence (review bar {review_bar:.0%} in {observation.profile})")
    if radar_tracks:
        reasons.append(f"{radar_tracks} radar track(s) without a confident visual match")
    if reasons:
        return Decision("review", tuple(reasons))
    return Decision("ignore", ("no confident detection and no radar track",))


def event_severity(observation: VisualObservation, radar_tracks: int) -> str:
    """The severity alone, for callers that do not need the reasons."""
    return decide(observation, radar_tracks).severity
