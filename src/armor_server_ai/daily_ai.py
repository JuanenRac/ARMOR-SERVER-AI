"""The optional note of an AI provider on the daily summary: off by default, nothing leaves the machine without an explicit switch, and everything that leaves is redacted first.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

A provider is anything with `name`, `external` (does it send the data off this machine?) and `enrich(payload) -> str`. Only a deterministic SIMULATED provider ships: it calls nothing.
A provider that is `external` is refused unless the settings say `ai.allow_external: true` (off by default). The payload given to any provider is the structured summary and findings after
`redact_value` (names, addresses and credentials removed; no free text from the events is ever in it), and the text that comes back is redacted again and cut to a fixed length.
"""

from __future__ import annotations

from typing import Any, Protocol

from .redact import redact_text, redact_value

MAX_NOTE_CHARS = 2000


class ProviderRefused(Exception):
    """The note was not asked for: a switch is off, the provider is unknown or it would send the data away without permission."""


class SummaryProvider(Protocol):
    name: str
    external: bool

    def enrich(self, payload: dict[str, Any]) -> str: ...


class SimulatedProvider:
    """A deterministic stand-in: it answers from the payload alone, with no network and no randomness, so tests and demonstrations repeat exactly."""

    name = "simulated"
    external = False

    def enrich(self, payload: dict[str, Any]) -> str:
        totals = payload["summary"]["totals"]
        kinds = sorted({finding["kind"] for finding in payload["findings"]})
        return (f"[simulated] {totals['events']} events, {totals['serious_alarms']} serious; patterns: {', '.join(kinds) if kinds else 'none'}. "
                f"Check the evidence of each pattern before acting; this note authorizes nothing.")


BUILT_IN: dict[str, SummaryProvider] = {"simulated": SimulatedProvider()}


def choose_provider(config: dict[str, Any], extra: dict[str, SummaryProvider] | None = None) -> SummaryProvider | None:
    """The provider the settings ask for, or None when the AI note is off. Raises ProviderRefused for an unknown one or an external one without permission."""
    ai = config["ai"]
    if not ai["enabled"]:
        return None
    provider = {**BUILT_IN, **(extra or {})}.get(ai["provider"])
    if provider is None:
        raise ProviderRefused(f"unknown AI provider '{ai['provider']}'")
    if provider.external and not ai["allow_external"]:
        raise ProviderRefused(f"the provider '{provider.name}' would send data away: set ai.allow_external to true to allow it")
    return provider


def make_note(summary: dict[str, Any], findings: list[dict[str, Any]], config: dict[str, Any], extra: dict[str, SummaryProvider] | None = None) -> str | None:
    """The redacted note of the provider, or None when the AI note is off."""
    provider = choose_provider(config, extra)
    if provider is None:
        return None
    names = config["ai"]["redact_names"]
    payload = redact_value({"summary": summary, "findings": findings}, names)
    note = provider.enrich(payload)
    if not isinstance(note, str):
        raise ProviderRefused("the provider did not answer with text")
    return redact_text(note, names)[:MAX_NOTE_CHARS]
