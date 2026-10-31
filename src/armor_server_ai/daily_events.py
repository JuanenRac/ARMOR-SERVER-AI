"""Reads the events of one day: JSON lines or a JSON list, strictly, from the events of the alarm system or from the messages of ARMOR-SIMULATOR.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

An event is `{"t_s": seconds from the start of the day (0 up to 86400), "type"?: "alarm" | "node_link_lost" | "reading" | "power", "code"?, "zone"?, "node"?,
"severity"?, "sensor"?, "value"?, "watts"?, "false_alarm"?, "duration_s"?, "detail"?}` (the same keys that `ARMOR-SIMULATOR --verify-alarms` reads for an alarm). A line `{"topic", "payload"}` as
`python -m armor_simulator --alarm-scenario ... / --energy` prints it is accepted too: the silences of a node become `node_link_lost` and the power of the house becomes `power`.
`detail` is free text that is read to check its shape and then dropped: it never reaches the summary.
Whatever is not understood (a key that is not listed, a wrong type or range, a repeated key, NaN, an identifier with odd characters, a file over 8 MB, more than 100 000 events) refuses
the whole file, with the number of the line.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DAY_S = 86400
MAX_BYTES = 8 * 1024 * 1024
MAX_EVENTS = 100_000
TYPES = ("alarm", "node_link_lost", "reading", "power")
SEVERITIES = ("info", "low", "medium", "high", "critical")
_ID = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,63}$")
_KEYS = {"t_s", "type", "code", "zone", "node", "severity", "sensor", "value", "watts", "false_alarm", "duration_s", "detail"}


class EventError(ValueError):
    """The events cannot be trusted; the message says where."""


@dataclass(frozen=True)
class Event:
    t_s: float
    type: str
    code: str = ""
    zone: str = ""
    node: str = ""
    severity: str = ""
    sensor: str = ""
    value: float | None = None
    watts: float | None = None
    false_alarm: bool = False
    duration_s: float = 0.0

    @property
    def hour(self) -> int:
        return int(self.t_s // 3600)


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    keys = [key for key, _ in pairs]
    if len(set(keys)) != len(keys):
        raise EventError("a key is repeated")
    return dict(pairs)


def _no_constants(name: str) -> Any:
    raise EventError(f"{name} is not a valid number")


def _number(value: Any, where: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise EventError(f"{where} must be a number between {low:g} and {high:g}")
    return float(value)


def _ident(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise EventError(f"{where} must be 1 to 64 letters, digits, '_', '.' or '-'")
    return value


def parse_event(raw: Any, where: str) -> Event:
    """One event from its JSON object; EventError says what is wrong."""
    if not isinstance(raw, dict):
        raise EventError(f"{where}: each event must be a JSON object")
    unknown = sorted(set(raw) - _KEYS)
    if unknown:
        raise EventError(f"{where}: unknown key '{unknown[0]}'")
    if "t_s" not in raw:
        raise EventError(f"{where}: missing 't_s'")
    try:
        t_s = _number(raw["t_s"], "t_s", 0, DAY_S - 1e-9)
        kind = raw.get("type", "alarm")
        if kind not in TYPES:
            raise EventError(f"type must be one of {', '.join(TYPES)}")
        fields: dict[str, Any] = {}
        for key in ("code", "zone", "node", "sensor"):
            if key in raw:
                fields[key] = _ident(raw[key], key)
        if "severity" in raw:
            if raw["severity"] not in SEVERITIES:
                raise EventError(f"severity must be one of {', '.join(SEVERITIES)}")
            fields["severity"] = raw["severity"]
        if "detail" in raw and (not isinstance(raw["detail"], str) or len(raw["detail"]) > 500):
            raise EventError("detail must be a text of at most 500 characters")
        if "false_alarm" in raw:
            if not isinstance(raw["false_alarm"], bool):
                raise EventError("false_alarm must be true or false")
            fields["false_alarm"] = raw["false_alarm"]
        if "value" in raw:
            fields["value"] = _number(raw["value"], "value", -1e12, 1e12)
        if "watts" in raw:
            fields["watts"] = _number(raw["watts"], "watts", 0, 1e9)
        if "duration_s" in raw:
            fields["duration_s"] = _number(raw["duration_s"], "duration_s", 0, DAY_S)
        if kind == "alarm" and not fields.get("code"):
            raise EventError("an alarm needs a 'code'")
        if kind == "node_link_lost" and not fields.get("node"):
            raise EventError("node_link_lost needs a 'node'")
        if kind == "reading" and not (fields.get("node") and fields.get("sensor") and "value" in fields):
            raise EventError("a reading needs 'node', 'sensor' and 'value'")
        if kind == "power" and "watts" not in fields:
            raise EventError("a power sample needs 'watts'")
    except EventError as error:
        raise EventError(f"{where}: {error}") from None
    return Event(t_s=t_s, type=kind, **fields)


def parse_text(text: str) -> list[dict[str, Any]]:
    """The objects of a JSON list or of JSON lines."""
    if len(text.encode("utf-8", "replace")) > MAX_BYTES:
        raise EventError(f"the events are larger than {MAX_BYTES} bytes")
    objects: list[dict[str, Any]] = []
    try:
        if text.lstrip().startswith("["):
            raw = json.loads(text, object_pairs_hook=_no_duplicates, parse_constant=_no_constants)
            if len(raw) > MAX_EVENTS:
                raise EventError(f"more than {MAX_EVENTS} events")
            return raw
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                objects.append(json.loads(line, object_pairs_hook=_no_duplicates, parse_constant=_no_constants))
            except (json.JSONDecodeError, EventError) as error:
                raise EventError(f"line {number}: {error}") from None
            if len(objects) > MAX_EVENTS:
                raise EventError(f"more than {MAX_EVENTS} events")
    except json.JSONDecodeError as error:
        raise EventError(f"not valid JSON: {error}") from None
    return objects


def _from_simulator(messages: list[tuple[int, dict[str, Any]]], link_gap_s: float) -> list[Event]:
    """Events from simulator messages: the silence of a node longer than `link_gap_s` is a lost link; the power of the house is a sample."""
    events: list[Event] = []
    last_seen: dict[str, float] = {}

    def when(item: tuple[int, dict[str, Any]]) -> float:
        stamp = item[1]["payload"].get("timestamp_ms") if isinstance(item[1]["payload"], dict) else None
        return float(stamp) if isinstance(stamp, (int, float)) and not isinstance(stamp, bool) else 0.0

    for number, message in sorted(messages, key=when):
        topic, payload = message["topic"], message["payload"]
        if not isinstance(topic, str) or not isinstance(payload, dict):
            raise EventError(f"line {number}: 'topic' must be text and 'payload' an object")
        stamp = payload.get("timestamp_ms")
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not 0 <= stamp < DAY_S * 1000:
            raise EventError(f"line {number}: the payload needs a 'timestamp_ms' inside the day")
        t_s = stamp / 1000
        parts = topic.split("/")
        if len(parts) == 4 and parts[:2] == ["armor", "node"] and parts[3] in ("telemetry", "health"):
            node = _ident(parts[2], "the node of the topic")
            if parts[3] == "health" and payload.get("online") is False:
                events.append(Event(t_s=t_s, type="node_link_lost", node=node))
            elif parts[3] == "telemetry":
                if node in last_seen and t_s - last_seen[node] > link_gap_s:
                    events.append(Event(t_s=last_seen[node], type="node_link_lost", node=node, duration_s=t_s - last_seen[node]))
                last_seen[node] = t_s
        elif len(parts) == 4 and parts[:2] == ["armor", "electrical"] and parts[3] == "state":
            channels = payload.get("channels")
            house = next((c for c in channels if isinstance(c, dict) and c.get("id") == "house"), None) if isinstance(channels, list) else None
            watts = house.get("power_w") if house else None
            if isinstance(watts, bool) or not isinstance(watts, (int, float)) or watts < 0:
                raise EventError(f"line {number}: the 'house' channel needs a 'power_w' of at least 0")
            events.append(Event(t_s=t_s, type="power", node=_ident(parts[2], "the node of the topic"), watts=float(watts)))
    return events


def load_events(text: str, link_gap_s: float = 30.0) -> list[Event]:
    """The events of a day, sorted by time. A mix of events and simulator messages is refused."""
    objects = parse_text(text)
    simulator = [(n, o) for n, o in enumerate(objects, start=1) if isinstance(o, dict) and set(o) == {"topic", "payload"}]
    if simulator and len(simulator) != len(objects):
        raise EventError("the file mixes events with simulator messages")
    events = _from_simulator(simulator, link_gap_s) if simulator else [parse_event(item, f"event {n}") for n, item in enumerate(objects, start=1)]
    return sorted(events, key=lambda e: (e.t_s, e.type, e.code, e.zone, e.node, e.sensor))


def load_events_file(path: Path | str, link_gap_s: float = 30.0) -> list[Event]:
    path = Path(path)
    try:
        if path.stat().st_size > MAX_BYTES:
            raise EventError(f"{path.name} is larger than {MAX_BYTES} bytes")
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise EventError(f"cannot read {path.name}: {error.strerror or error}") from None
    except UnicodeDecodeError:
        raise EventError(f"{path.name} is not UTF-8") from None
    return load_events(text, link_gap_s)
