"""Removes what is personal or secret from anything that leaves the summary: names, addresses, credentials.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

It runs on the data given to an AI provider and on every text the summary prints, so a name or an address that slipped into an identifier never leaves.
The list of names to hide comes from the settings (`ai.redact_names`); the rest is recognised by its shape.
"""

from __future__ import annotations

import ipaddress
import re
from typing import Any

MARK = "[redacted]"

# a field whose name says it holds something personal or secret is never copied, whatever it contains
_SENSITIVE_WORDS = frozenset(("name names owner user username person who pass password passwd pwd secret token key apikey credential credentials auth authorization cookie session "
                              "ip host hostname addr address mac mail email phone url uri").split())
_SAFE_KEYS = {"node", "nodes", "zone", "zones", "sensor", "code", "severity", "type", "kind", "hour", "count", "t_s", "watts", "value", "schema"}
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_URL = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.I)
_MAC = re.compile(r"\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b")
_BEARER = re.compile(r"\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}", re.I)
_ASSIGNMENT = re.compile(r"\b(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|credential|authorization)\b\s*[:=]\s*\S+", re.I)
_LONG_SECRET = re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{32,}\b")
_ADDRESS_CANDIDATE = re.compile(r"[0-9A-Fa-f:.]*[:.][0-9A-Fa-f:.]*")


def _hide_addresses(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        stripped = token.strip(".")      # a full stop that ends a sentence is not part of the address
        for candidate in (stripped, stripped.split("%")[0]):
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                continue
            return MARK + token[len(token.rstrip(".")):]
        return token
    return _ADDRESS_CANDIDATE.sub(replace, text)


def redact_text(text: str, names: list[str] | tuple[str, ...] = ()) -> str:
    """The text with e-mails, URLs, addresses (IPv4, IPv6, MAC), bearer tokens, `password=...` assignments, long token-like strings and the given names replaced by a mark."""
    text = _URL.sub(MARK, text)
    text = _EMAIL.sub(MARK, text)
    text = _BEARER.sub(MARK, text)
    text = _ASSIGNMENT.sub(MARK, text)
    text = _MAC.sub(MARK, text)
    text = _hide_addresses(text)
    text = _LONG_SECRET.sub(MARK, text)
    for name in sorted({n.strip() for n in names if n.strip()}, key=len, reverse=True):
        text = re.sub(r"(?<!\w)" + re.escape(name) + r"(?!\w)", MARK, text, flags=re.I)
    return text


def redact_value(value: Any, names: list[str] | tuple[str, ...] = ()) -> Any:
    """The same for a whole structure: every text is redacted, and a field named like something personal or secret is replaced entirely."""
    if isinstance(value, str):
        return redact_text(value, names)
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            key_text = redact_text(str(key), names)
            if key not in _SAFE_KEYS and any(word in _SENSITIVE_WORDS for word in re.split(r"[^a-z]+", str(key).lower())):
                out[key_text] = MARK
            else:
                out[key_text] = redact_value(item, names)
        return out
    if isinstance(value, (list, tuple)):
        return [redact_value(item, names) for item in value]
    return value
