"""The daily summary and the patterns found in the events of a day, without any AI: counts, serious alarms, lost links, outlying readings, consumption peaks, and five explainable patterns.

Copyright (C) 2026 JuanenRac (Electro Hobby 3D). GPL-3.0-or-later.

Everything here is deterministic: the same events and settings give the same result, byte for byte. Every number that decides something comes from the settings (`daily_config.py`).
A finding always carries its evidence (the events that make it) and the numbers that were compared, so it can be checked by hand.
"""

from __future__ import annotations

import statistics
from collections import Counter
from typing import Any

from .daily_events import Event

SCHEMA = "armor-daily-summary/1"
NO_ZONE = "-"
MAX_EVIDENCE = 20


def _r(value: float) -> float:
    return round(value, 3)


def _brief(event: Event) -> dict[str, Any]:
    out: dict[str, Any] = {"t_s": _r(event.t_s)}
    for key in ("code", "zone", "node", "sensor"):
        if getattr(event, key):
            out[key] = getattr(event, key)
    if event.watts is not None:
        out["watts"] = _r(event.watts)
    if event.value is not None:
        out["value"] = _r(event.value)
    return out


def _is_serious(event: Event, settings: dict[str, Any]) -> bool:
    return event.type == "alarm" and not event.false_alarm and (event.severity in settings["serious_severities"] or event.code in settings["serious_codes"])


def outlier_readings(events: list[Event], settings: dict[str, Any]) -> list[dict[str, Any]]:
    """Readings far from the median of their own sensor (modified z-score with the median absolute deviation, with a floor on the scale so a flat series does not flag noise)."""
    series: dict[tuple[str, str], list[Event]] = {}
    for event in events:
        if event.type == "reading" and event.value is not None:
            series.setdefault((event.node, event.sensor), []).append(event)
    found = []
    for (node, sensor), items in sorted(series.items()):
        if len(items) < settings["outlier_min_samples"]:
            continue
        values = [e.value for e in items if e.value is not None]
        median = statistics.median(values)
        scale = max(1.4826 * statistics.median(abs(v - median) for v in values), settings["outlier_min_scale"])
        for event in items:
            assert event.value is not None
            score = abs(event.value - median) / scale
            if score > settings["outlier_mad_k"]:
                found.append({"t_s": _r(event.t_s), "node": node, "sensor": sensor, "value": _r(event.value), "median": _r(median), "score": _r(score)})
    return found


def build_summary(events: list[Event], config: dict[str, Any]) -> dict[str, Any]:
    """The structured summary of a day. The counts by type, by zone (`-` for no zone) and by hour each add up to `totals.events`."""
    settings = config["summary"]
    by_type = Counter(e.type for e in events)
    by_zone = Counter((e.zone or NO_ZONE) for e in events)
    by_hour = [0] * 24
    for event in events:
        by_hour[event.hour] += 1
    alarms = [e for e in events if e.type == "alarm"]
    serious = [e for e in alarms if _is_serious(e, settings)]
    links: dict[str, list[Event]] = {}
    for event in events:
        if event.type == "node_link_lost":
            links.setdefault(event.node, []).append(event)
    power = sorted((e for e in events if e.type == "power" and e.watts is not None), key=lambda e: (-(e.watts or 0.0), e.t_s))
    watts = [e.watts for e in power if e.watts is not None]
    return {
        "schema": SCHEMA,
        "totals": {"events": len(events), "alarms": len(alarms), "serious_alarms": len(serious), "false_alarms": sum(1 for e in alarms if e.false_alarm)},
        "by_type": dict(sorted(by_type.items())),
        "by_zone": dict(sorted(by_zone.items())),
        "by_hour": by_hour,
        "busiest_hour": max(range(24), key=lambda h: (by_hour[h], -h)) if events else None,
        "serious_alarms": [_brief(e) | ({"severity": e.severity} if e.severity else {}) for e in serious],
        "nodes_link_lost": [{"node": node, "count": len(items), "total_s": _r(sum(e.duration_s for e in items))} for node, items in sorted(links.items())],
        "outlier_readings": outlier_readings(events, settings),
        "consumption": {"samples": len(watts), "mean_w": _r(statistics.fmean(watts)) if watts else None, "max_w": _r(max(watts)) if watts else None,
                        "peaks": [_brief(e) for e in power[: settings["peak_count"]]]},
    }


# ------------------------------------------------------------------ patterns

def _hourly_repeat(events: list[Event], p: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[Event]] = {}
    for event in events:
        if event.type == "alarm":
            groups.setdefault((event.code, event.zone or NO_ZONE), []).append(event)
    found = []
    span = 2 * p["hourly_repeat_tolerance_min"]
    for (code, zone), items in sorted(groups.items()):
        marks = sorted(((e.t_s % 3600 / 60, e.hour, e) for e in items), key=lambda m: (m[0], m[1]))
        best: list[Event] = []
        for i, (start, _, _) in enumerate(marks):
            window: dict[int, Event] = {}
            for minute, hour, event in marks[i:]:
                if minute - start > span:
                    break
                window.setdefault(hour, event)
            if len(window) > len(best):
                best = [window[h] for h in sorted(window)]
        if len(best) >= p["hourly_repeat_min_hours"]:
            found.append({"kind": "hourly_repeat", "subject": {"code": code, "zone": zone}, "count": len(best), "detail": {"hours": [e.hour for e in best], "tolerance_min": p["hourly_repeat_tolerance_min"]},
                          "evidence": [_brief(e) for e in best][:MAX_EVIDENCE]})
    return found


def _intermittent_sensor(events: list[Event], p: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[Event]] = {}
    for event in events:
        if event.type == "alarm" and event.code in p["sensor_fault_codes"]:
            groups.setdefault((event.node or NO_ZONE, event.zone or NO_ZONE), []).append(event)
    found = []
    for (node, zone), items in sorted(groups.items()):
        times = sorted({e.t_s for e in items})
        gaps = [b - a for a, b in zip(times, times[1:], strict=False)]
        if len(times) >= p["intermittent_min_faults"] and all(g <= p["intermittent_max_gap_s"] for g in gaps):
            found.append({"kind": "intermittent_sensor", "subject": {"node": node, "zone": zone}, "count": len(times), "detail": {"max_gap_s": _r(max(gaps)), "limit_s": p["intermittent_max_gap_s"]},
                          "evidence": [_brief(e) for e in items][:MAX_EVIDENCE]})
    return found


def _intermittent_link(events: list[Event], p: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[Event]] = {}
    for event in events:
        if event.type == "node_link_lost":
            groups.setdefault(event.node, []).append(event)
    return [{"kind": "intermittent_link", "subject": {"node": node}, "count": len(items), "detail": {"minimum": p["link_loss_min"]}, "evidence": [_brief(e) | {"duration_s": _r(e.duration_s)} for e in items][:MAX_EVIDENCE]}
            for node, items in sorted(groups.items()) if len(items) >= p["link_loss_min"]]


def _false_alarms(events: list[Event], p: dict[str, Any]) -> list[dict[str, Any]]:
    groups: dict[str, list[Event]] = {}
    for event in events:
        if event.type == "alarm" and (event.false_alarm or event.code in p["false_alarm_codes"]):
            groups.setdefault(event.zone or NO_ZONE, []).append(event)
    return [{"kind": "recurrent_false_alarm", "subject": {"zone": zone}, "count": len(items), "detail": {"minimum": p["false_alarm_min"]}, "evidence": [_brief(e) for e in items][:MAX_EVIDENCE]}
            for zone, items in sorted(groups.items()) if len(items) >= p["false_alarm_min"]]


def _consumption(events: list[Event], p: dict[str, Any]) -> list[dict[str, Any]]:
    samples = sorted((e for e in events if e.type == "power" and e.watts is not None), key=lambda e: e.t_s)
    window = p["consumption_window"]
    evidence = []
    for i in range(window, len(samples)):
        before = [s.watts for s in samples[i - window:i] if s.watts is not None]
        mean, spread = statistics.fmean(before), statistics.pstdev(before)
        watts = samples[i].watts
        assert watts is not None
        if watts > mean + p["consumption_sigma"] * spread and watts >= mean * p["consumption_min_ratio"]:
            evidence.append(_brief(samples[i]) | {"mean_w": _r(mean), "limit_w": _r(max(mean + p["consumption_sigma"] * spread, mean * p["consumption_min_ratio"]))})
    if not evidence:
        return []
    return [{"kind": "anomalous_consumption", "subject": {}, "count": len(evidence), "detail": {"window": window, "sigma": p["consumption_sigma"], "min_ratio": p["consumption_min_ratio"]}, "evidence": evidence[:MAX_EVIDENCE]}]


def detect_patterns(events: list[Event], config: dict[str, Any]) -> list[dict[str, Any]]:
    """The patterns of the day: the same alarm at the same time of the hour, a sensor that fails on and off, a node that keeps losing its link, a zone with recurring false alarms,
    and consumption far above its moving average. Each finding has `kind`, `subject`, `count`, `detail` (the numbers compared) and `evidence` (the events)."""
    p = config["patterns"]
    return [*_hourly_repeat(events, p), *_intermittent_sensor(events, p), *_intermittent_link(events, p), *_false_alarms(events, p), *_consumption(events, p)]
