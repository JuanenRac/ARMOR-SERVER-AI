"""The settings of the daily summary: every tuned value lives in a JSON file, and the whole feature is off until the file says `"enabled": true`.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Nothing is read loosely: a key that is not here, a value of the wrong type or outside its range, a repeated key or a file larger than 64 KiB refuses the whole file.
`docs/daily_summary.example.json` holds every key with its default.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

MAX_CONFIG_BYTES = 64 * 1024
LANGUAGES = ("en", "es", "de", "fr", "it", "ja", "zh", "pt")

DEFAULTS: dict[str, Any] = {
    "enabled": False,
    "language": "en",
    "summary": {
        "serious_severities": ["high", "critical"],
        "serious_codes": ["intrusion", "tamper", "fire", "panic"],
        "peak_count": 3,
        "link_gap_s": 30.0,
        "outlier_mad_k": 6.0,
        "outlier_min_scale": 0.5,
        "outlier_min_samples": 8,
    },
    "patterns": {
        "hourly_repeat_min_hours": 3,
        "hourly_repeat_tolerance_min": 5,
        "intermittent_min_faults": 3,
        "intermittent_max_gap_s": 1800.0,
        "sensor_fault_codes": ["sensor_fault", "sensor_stuck", "sensor_dead", "sensor_noise"],
        "link_loss_min": 3,
        "false_alarm_min": 3,
        "false_alarm_codes": ["false_alarm", "pet", "wind"],
        "consumption_window": 8,
        "consumption_sigma": 3.0,
        "consumption_min_ratio": 1.5,
    },
    "ai": {"enabled": False, "provider": "simulated", "allow_external": False, "redact_names": []},
}

# (low, high) for numbers; for lists of text the maximum length of the list.
_RANGES: dict[tuple[str, str], tuple[float, float]] = {
    ("summary", "peak_count"): (1, 20), ("summary", "link_gap_s"): (1, 86400), ("summary", "outlier_mad_k"): (1, 100), ("summary", "outlier_min_scale"): (1e-6, 1e6),
    ("summary", "outlier_min_samples"): (3, 10000),
    ("patterns", "hourly_repeat_min_hours"): (2, 24), ("patterns", "hourly_repeat_tolerance_min"): (0, 30), ("patterns", "intermittent_min_faults"): (2, 1000),
    ("patterns", "intermittent_max_gap_s"): (1, 86400), ("patterns", "link_loss_min"): (2, 1000), ("patterns", "false_alarm_min"): (2, 1000),
    ("patterns", "consumption_window"): (3, 1000), ("patterns", "consumption_sigma"): (0.5, 100), ("patterns", "consumption_min_ratio"): (1.0, 100),
}


class ConfigError(ValueError):
    """The settings file cannot be trusted."""


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise ConfigError("a key is repeated")
    return dict(pairs)


def _no_constants(name: str) -> Any:
    raise ConfigError(f"{name} is not a valid number")


def check_config(raw: Any) -> dict[str, Any]:
    """The settings with the defaults filled in; ConfigError for anything unknown or out of range."""
    if not isinstance(raw, dict):
        raise ConfigError("the settings must be a JSON object")
    config = copy.deepcopy(DEFAULTS)
    for key, value in raw.items():
        if key not in DEFAULTS:
            raise ConfigError(f"unknown setting '{key}'")
        if isinstance(DEFAULTS[key], dict):
            if not isinstance(value, dict):
                raise ConfigError(f"'{key}' must be an object")
            for name, inner in value.items():
                if name not in DEFAULTS[key]:
                    raise ConfigError(f"unknown setting '{key}.{name}'")
                config[key][name] = _check_value(key, name, inner, DEFAULTS[key][name])
        else:
            config[key] = _check_value("", key, value, DEFAULTS[key])
    return config


def _check_value(section: str, name: str, value: Any, default: Any) -> Any:
    label = f"{section}.{name}" if section else name
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ConfigError(f"'{label}' must be true or false")
        return value
    if isinstance(default, str):
        if not isinstance(value, str) or not value or len(value) > 64:
            raise ConfigError(f"'{label}' must be a short text")
        if label == "language" and value not in LANGUAGES:
            raise ConfigError(f"'language' must be one of {', '.join(LANGUAGES)}")
        return value
    if isinstance(default, list):
        if not isinstance(value, list) or len(value) > 64 or not all(isinstance(item, str) and 0 < len(item) <= 64 for item in value):
            raise ConfigError(f"'{label}' must be a list of up to 64 short texts")
        return list(value)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"'{label}' must be a number")
    low, high = _RANGES[(section, name)]
    if not low <= value <= high:
        raise ConfigError(f"'{label}' must be between {low:g} and {high:g}")
    if isinstance(default, int):
        if not float(value).is_integer():
            raise ConfigError(f"'{label}' must be a whole number")
        return int(value)
    return float(value)


def load_config(path: Path | str | None) -> dict[str, Any]:
    """The settings of a file; without a file, the defaults (which leave the feature off)."""
    if path is None:
        return copy.deepcopy(DEFAULTS)
    path = Path(path)
    try:
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise ConfigError(f"{path.name} is larger than {MAX_CONFIG_BYTES} bytes")
        raw = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates, parse_constant=_no_constants)
    except OSError as error:
        raise ConfigError(f"cannot read {path.name}: {error.strerror or error}") from None
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConfigError(f"{path.name} is not valid JSON in UTF-8: {error}") from None
    return check_config(raw)
