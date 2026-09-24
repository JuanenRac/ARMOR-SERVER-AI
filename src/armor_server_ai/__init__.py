"""A.R.M.O.R. visual-service domain code."""
from .engine_registry import EngineRegistryError, EngineSet, discover_engines
from .policy import Decision, VisualObservation, decide, event_severity
from .profile import DAYLIGHT, LOW_LIGHT, ProfileSelector, choose_profile

__all__ = [
    "DAYLIGHT", "Decision", "EngineRegistryError", "EngineSet", "LOW_LIGHT", "ProfileSelector", "VisualObservation",
    "choose_profile", "decide", "discover_engines", "event_severity",
]
__version__ = "0.2.0"
