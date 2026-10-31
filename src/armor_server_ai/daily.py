"""The daily summary of the events of a day: `armor-vision-policy --daily-summary FILE --summary-config CONFIG`. Off until the settings say `"enabled": true`.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

It reads the events (see `daily_events.py`), builds a structured summary and the patterns, writes the text in the language of the settings (or `--lang`), and, only when
`ai.enabled` is true, adds the note of the AI provider. Every text that leaves is redacted. Anything malformed ends with a message and exit code 2, and prints nothing else.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .daily_ai import ProviderRefused, SummaryProvider, make_note
from .daily_config import ConfigError, load_config
from .daily_events import EventError, load_events_file
from .daily_summary import build_summary, detect_patterns
from .daily_text import TEXTS, render_text
from .redact import redact_text, redact_value


class Disabled(Exception):
    """The daily summary is switched off in the settings."""


def daily_report(events_path: Path | str, config_path: Path | str | None, language: str | None = None, providers: dict[str, SummaryProvider] | None = None) -> dict[str, Any]:
    """{"summary", "findings", "text", "ai_note"?} for the events of a file. Raises Disabled, ConfigError, EventError or ProviderRefused; nothing is partly done."""
    config = load_config(config_path)
    if not config["enabled"]:
        raise Disabled("the daily summary is off: set \"enabled\": true in the settings file to use it")
    if language is not None and language not in TEXTS:
        raise ConfigError(f"unknown language '{language}'")
    events = load_events_file(events_path, config["summary"]["link_gap_s"])
    summary = build_summary(events, config)
    findings = detect_patterns(events, config)
    names = config["ai"]["redact_names"]
    note = make_note(summary, findings, config, providers)
    text = redact_text(render_text(summary, findings, language or config["language"]), names)
    report: dict[str, Any] = {"summary": redact_value(summary, names), "findings": redact_value(findings, names), "text": text}
    if note is not None:
        report["ai_note"] = note
        report["text"] += f"\n{TEXTS[language or config['language']]['ai_note']}: {note}"
    return report


def run(events_path: Path, config_path: Path | None, language: str | None, as_json: bool) -> tuple[int, str, str]:
    """(exit code, stdout, stderr): 0 with the report, 2 with the reason and nothing on stdout."""
    try:
        report = daily_report(events_path, config_path, language)
    except (Disabled, ConfigError, EventError, ProviderRefused) as error:
        return 2, "", f"armor-vision-policy: daily summary: {error}\n"
    return 0, (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) if as_json else report["text"]) + "\n", ""
