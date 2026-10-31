"""The daily summary: off by default, strict about its input, deterministic, explainable, redacted, and with an AI note that cannot send anything away without a switch."""
import _paths  # noqa: F401
import contextlib
import copy
import io
import json
import random
import re
import string
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from armor_server_ai import cli
from armor_server_ai.daily import Disabled, daily_report, run as run_daily
from armor_server_ai.daily_ai import ProviderRefused, SimulatedProvider, choose_provider, make_note
from armor_server_ai.daily_config import DEFAULTS, LANGUAGES, ConfigError, check_config, load_config
from armor_server_ai.daily_events import EventError, load_events, parse_event
from armor_server_ai.daily_summary import build_summary, detect_patterns
from armor_server_ai.daily_text import TEXTS, render_text
from armor_server_ai.redact import MARK, redact_text, redact_value

ON = check_config({"enabled": True})
SIMULATOR = Path(__file__).resolve().parents[2] / "ARMOR-SIMULATOR"


def lines(*events):
    return "\n".join(json.dumps(e) for e in events)


def random_events(seed, count=300):
    rng = random.Random(seed)
    events = []
    for _ in range(count):
        kind = rng.choice(["alarm", "alarm", "node_link_lost", "reading", "power"])
        event = {"t_s": rng.uniform(0, 86399), "type": kind}
        if kind == "alarm":
            event |= {"code": rng.choice(["intrusion", "pet", "sensor_fault", "door"]), "severity": rng.choice(["info", "high", "critical"]), "false_alarm": rng.random() < 0.2}
            if rng.random() < 0.8:
                event["zone"] = rng.choice(["garden", "hall", "garage"])
        elif kind == "node_link_lost":
            event["node"] = rng.choice(["radar-1", "radar-2"])
        elif kind == "reading":
            event |= {"node": "radar-1", "sensor": "lux", "value": rng.gauss(50, 3) if rng.random() < 0.97 else 5000}
        else:
            event["watts"] = rng.uniform(200, 900) if rng.random() < 0.95 else 5000
        events.append(event)
    return events


class ConfigTests(unittest.TestCase):
    def test_the_defaults_are_off_and_conservative(self):
        config = load_config(None)
        self.assertFalse(config["enabled"])
        self.assertFalse(config["ai"]["enabled"])
        self.assertFalse(config["ai"]["allow_external"])

    def test_the_example_file_is_the_defaults(self):
        self.assertEqual(load_config(Path(__file__).resolve().parents[1] / "docs" / "daily_summary.example.json"), DEFAULTS)

    def test_what_is_not_understood_refuses_the_file(self):
        for bad in ({"nope": 1}, {"summary": {"nope": 1}}, {"enabled": "yes"}, {"language": "xx"}, {"summary": {"peak_count": 0}}, {"summary": {"peak_count": 2.5}},
                    {"summary": {"peak_count": True}}, {"patterns": {"consumption_sigma": 1e999}}, {"ai": {"redact_names": [1]}}, {"summary": []}, [], {"summary": {"serious_codes": "a"}}):
            with self.assertRaises(ConfigError, msg=bad):
                check_config(bad)

    def test_a_repeated_key_nan_and_a_missing_file_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            for text in ('{"enabled": true, "enabled": false}', '{"summary": {"link_gap_s": NaN}}', "not json"):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ConfigError, msg=text):
                    load_config(path)
            with self.assertRaises(ConfigError):
                load_config(Path(tmp) / "missing.json")


class EventTests(unittest.TestCase):
    def test_a_good_alarm_and_the_defaults(self):
        event = parse_event({"t_s": 5, "code": "intrusion", "zone": "garden", "severity": "high", "detail": "free text is read and dropped"}, "x")
        self.assertEqual((event.type, event.code, event.zone, event.hour), ("alarm", "intrusion", "garden", 0))

    def test_every_malformed_event_is_refused_with_its_place(self):
        bad = [{"code": "x"}, {"t_s": -1, "code": "x"}, {"t_s": 86400, "code": "x"}, {"t_s": "1", "code": "x"}, {"t_s": True, "code": "x"}, {"t_s": 1, "code": "x", "extra": 1},
               {"t_s": 1}, {"t_s": 1, "code": "a b"}, {"t_s": 1, "code": "../x"}, {"t_s": 1, "code": "x", "severity": "dire"}, {"t_s": 1, "type": "wat"},
               {"t_s": 1, "type": "reading", "node": "n"}, {"t_s": 1, "type": "power"}, {"t_s": 1, "type": "power", "watts": -2}, {"t_s": 1, "type": "node_link_lost"},
               {"t_s": 1, "code": "x", "detail": "d" * 501}, {"t_s": 1, "code": "x", "false_alarm": "no"}, [1], "text", None]
        for item in bad:
            with self.assertRaises(EventError, msg=item):
                parse_event(item, "event 1")

    def test_a_file_with_one_bad_line_is_refused_whole_and_says_the_line(self):
        text = lines({"t_s": 1, "code": "a"}) + "\n{broken\n"
        with self.assertRaisesRegex(EventError, "line 2"):
            load_events(text)
        for text in ('[{"t_s": 1, "code": "a", "code": "b"}]', '{"t_s": NaN, "code": "a"}', '[{"t_s": 1, "code": "a"}, 3]', lines({"t_s": 1, "code": "a"}, {"topic": "armor/node/n/health", "payload": {}})):
            with self.assertRaises(EventError, msg=text):
                load_events(text)

    def test_a_json_list_and_json_lines_give_the_same_events_sorted_by_time(self):
        items = [{"t_s": 30, "code": "b"}, {"t_s": 10, "code": "a"}]
        self.assertEqual(load_events(json.dumps(items)), load_events(lines(*items)))
        self.assertEqual([e.code for e in load_events(json.dumps(items))], ["a", "b"])

    def test_simulator_messages_become_link_losses_and_power(self):
        messages = [{"topic": "armor/node/radar-1/telemetry", "payload": {"node_id": "radar-1", "timestamp_ms": s * 1000}} for s in (0, 1, 2, 100, 101)]
        messages.append({"topic": "armor/electrical/home/state", "payload": {"timestamp_ms": 5000, "channels": [{"id": "grid", "power_w": 9}, {"id": "house", "power_w": 321.5}]}})
        events = load_events(lines(*reversed(messages)))
        self.assertEqual([(e.type, e.node, e.duration_s) for e in events if e.type == "node_link_lost"], [("node_link_lost", "radar-1", 98.0)])
        self.assertEqual([e.watts for e in events if e.type == "power"], [321.5])
        with self.assertRaises(EventError):
            load_events(lines({"topic": "armor/electrical/home/state", "payload": {"timestamp_ms": 5000, "channels": [{"id": "house", "power_w": "x"}]}}))
        with self.assertRaises(EventError):
            load_events(lines({"topic": "armor/node/n/telemetry", "payload": {"timestamp_ms": 10 ** 12}}))


class SummaryPropertyTests(unittest.TestCase):
    def test_the_counts_always_add_up_for_many_random_days(self):
        for seed in range(25):
            events = load_events(lines(*random_events(seed, 50 + seed * 10)))
            summary = build_summary(events, ON)
            total = summary["totals"]["events"]
            self.assertEqual(total, len(events))
            self.assertEqual(sum(summary["by_type"].values()), total)
            self.assertEqual(sum(summary["by_zone"].values()), total)
            self.assertEqual(sum(summary["by_hour"]), total)
            self.assertEqual(len(summary["by_hour"]), 24)
            self.assertEqual(summary["by_type"].get("alarm", 0), summary["totals"]["alarms"])
            self.assertLessEqual(summary["totals"]["serious_alarms"], summary["totals"]["alarms"])
            self.assertEqual(len(summary["serious_alarms"]), summary["totals"]["serious_alarms"])
            self.assertEqual(summary["busiest_hour"], max(range(24), key=lambda h: (summary["by_hour"][h], -h)))

    def test_the_same_events_in_any_order_give_the_same_summary_and_findings_byte_for_byte(self):
        raw = random_events(7, 400)
        shuffled = copy.deepcopy(raw)
        random.Random(99).shuffle(shuffled)
        a, b = load_events(lines(*raw)), load_events(lines(*shuffled))
        self.assertEqual(json.dumps(build_summary(a, ON), sort_keys=True), json.dumps(build_summary(b, ON), sort_keys=True))
        self.assertEqual(json.dumps(detect_patterns(a, ON), sort_keys=True), json.dumps(detect_patterns(b, ON), sort_keys=True))
        self.assertEqual(json.dumps(build_summary(a, ON), sort_keys=True), json.dumps(build_summary(a, ON), sort_keys=True))

    def test_an_empty_day_is_a_valid_summary(self):
        summary = build_summary([], ON)
        self.assertEqual(summary["totals"]["events"], 0)
        self.assertIsNone(summary["busiest_hour"])
        self.assertEqual(detect_patterns([], ON), [])
        self.assertIn(TEXTS["en"]["empty"], render_text(summary, [], "en"))

    def test_serious_alarms_link_losses_outliers_and_peaks(self):
        events = [{"t_s": 100, "code": "intrusion", "zone": "garden"}, {"t_s": 200, "code": "door", "severity": "critical"}, {"t_s": 300, "code": "door", "severity": "info"},
                  {"t_s": 400, "code": "intrusion", "false_alarm": True},
                  {"t_s": 500, "type": "node_link_lost", "node": "n1", "duration_s": 40}, {"t_s": 600, "type": "node_link_lost", "node": "n1", "duration_s": 20}]
        events += [{"t_s": 1000 + i, "type": "reading", "node": "n1", "sensor": "lux", "value": 50 + (i % 3)} for i in range(10)] + [{"t_s": 2000, "type": "reading", "node": "n1", "sensor": "lux", "value": 900}]
        events += [{"t_s": 3000 + i, "type": "power", "node": "h", "watts": w} for i, w in enumerate((100, 4000, 300, 2500))]
        summary = build_summary(load_events(lines(*events)), ON)
        self.assertEqual([a["code"] for a in summary["serious_alarms"]], ["intrusion", "door"])
        self.assertEqual(summary["nodes_link_lost"], [{"node": "n1", "count": 2, "total_s": 60.0}])
        self.assertEqual([(o["t_s"], o["value"]) for o in summary["outlier_readings"]], [(2000.0, 900.0)])
        self.assertEqual([p["watts"] for p in summary["consumption"]["peaks"]], [4000.0, 2500.0, 300.0])
        self.assertEqual(summary["consumption"]["max_w"], 4000.0)


class PatternTests(unittest.TestCase):
    def patterns(self, events, **changes):
        config = check_config({"enabled": True, "patterns": changes} if changes else {"enabled": True})
        return detect_patterns(load_events(lines(*events)), config)

    def test_the_same_alarm_at_the_same_time_of_the_hour(self):
        events = [{"t_s": h * 3600 + 15 * 60 + d, "code": "door", "zone": "hall"} for h, d in ((1, 0), (2, 40), (5, 100))] + [{"t_s": 7 * 3600 + 50 * 60, "code": "door", "zone": "hall"}]
        (finding,) = self.patterns(events)
        self.assertEqual((finding["kind"], finding["subject"], finding["count"]), ("hourly_repeat", {"code": "door", "zone": "hall"}, 3))
        self.assertEqual(finding["detail"]["hours"], [1, 2, 5])
        self.assertEqual(len(finding["evidence"]), 3)
        self.assertEqual(self.patterns(events, hourly_repeat_min_hours=4), [])

    def test_a_sensor_that_fails_on_and_off(self):
        events = [{"t_s": t, "code": "sensor_fault", "node": "n1", "zone": "z1"} for t in (100, 400, 900)]
        (finding,) = self.patterns(events)
        self.assertEqual((finding["kind"], finding["count"], finding["detail"]["max_gap_s"]), ("intermittent_sensor", 3, 500.0))
        self.assertEqual(self.patterns(events, intermittent_max_gap_s=300.0), [])
        self.assertEqual(self.patterns(events[:2]), [])

    def test_a_node_that_keeps_losing_its_link(self):
        events = [{"t_s": t, "type": "node_link_lost", "node": "n1", "duration_s": 5} for t in (10, 20000, 50000)]
        (finding,) = self.patterns(events)
        self.assertEqual((finding["kind"], finding["subject"], finding["count"]), ("intermittent_link", {"node": "n1"}, 3))
        self.assertEqual(self.patterns(events, link_loss_min=4), [])

    def test_a_zone_with_recurring_false_alarms(self):
        events = [{"t_s": t, "code": "pet", "zone": "hall"} for t in (10, 20000)] + [{"t_s": 50000, "code": "door", "zone": "hall", "false_alarm": True}, {"t_s": 60000, "code": "pet", "zone": "garage"}]
        (finding,) = self.patterns(events)
        self.assertEqual((finding["kind"], finding["subject"], finding["count"]), ("recurrent_false_alarm", {"zone": "hall"}, 3))

    def test_consumption_far_above_the_moving_average_carries_its_numbers(self):
        events = [{"t_s": i * 900, "type": "power", "watts": 500 + (i % 2) * 10} for i in range(20)]
        events[15]["watts"] = 4000
        (finding,) = self.patterns(events)
        self.assertEqual(finding["kind"], "anomalous_consumption")
        (proof,) = finding["evidence"]
        self.assertEqual((proof["t_s"], proof["watts"]), (15 * 900.0, 4000.0))
        self.assertLess(proof["limit_w"], 4000.0)
        self.assertGreater(proof["mean_w"], 490)
        self.assertEqual(self.patterns(events, consumption_min_ratio=20.0), [])

    def test_a_calm_day_has_no_patterns(self):
        self.assertEqual(self.patterns([{"t_s": i * 900, "type": "power", "watts": 500} for i in range(30)] + [{"t_s": 5, "code": "door"}]), [])

    def test_every_finding_of_random_days_has_evidence_that_belongs_to_the_day(self):
        for seed in range(15):
            events = load_events(lines(*random_events(seed, 400)))
            for finding in detect_patterns(events, ON):
                self.assertTrue(finding["evidence"])
                self.assertLessEqual(len(finding["evidence"]), 20)
                times = {round(e.t_s, 3) for e in events}
                for proof in finding["evidence"]:
                    self.assertIn(proof["t_s"], times)


class TextTests(unittest.TestCase):
    def test_the_eight_languages_have_exactly_the_same_keys_and_placeholders(self):
        self.assertEqual(set(TEXTS), set(LANGUAGES))
        for language, texts in TEXTS.items():
            self.assertEqual(set(texts), set(TEXTS["en"]), language)
            for key, text in texts.items():
                self.assertEqual(sorted(re.findall(r"\{(\w+)\}", text)), sorted(re.findall(r"\{(\w+)\}", TEXTS["en"][key])), f"{language}.{key}")
                self.assertTrue(text.strip())

    def test_every_language_renders_a_full_day_and_differs_from_english(self):
        raw = random_events(3, 400) + [{"t_s": h * 3600 + 900, "code": "door", "zone": "hall"} for h in (1, 2, 3)] + [{"t_s": t, "code": "sensor_fault", "node": "n1", "zone": "z1"} for t in (1, 2, 3)]
        events = load_events(lines(*raw))
        summary, findings = build_summary(events, ON), detect_patterns(events, ON)
        self.assertGreaterEqual({f["kind"] for f in findings}, {"hourly_repeat", "intermittent_sensor"})
        english = render_text(summary, findings, "en")
        for language in LANGUAGES:
            text = render_text(summary, findings, language)
            self.assertNotIn("{", text)
            self.assertEqual(text.count("\n"), english.count("\n"), language)
            if language != "en":
                self.assertNotEqual(text, english)

    def test_portuguese_is_the_one_of_portugal(self):
        joined = " ".join(TEXTS["pt"].values()).lower()
        for brazilian in ("rastreio de", "tela", "celular", "arquivo", "ligações perdidas", "você"):
            self.assertNotIn(brazilian, joined)
        self.assertIn("ligação", joined)


class RedactionTests(unittest.TestCase):
    def test_addresses_credentials_and_names_are_removed(self):
        text = ("Juan Perez at 192.168.0.12 and 2001:db8::1 mac aa:bb:cc:dd:ee:ff mail juan@example.org password=hunter2 Authorization: Bearer abcdef123456 "
                "see https://user:pw@host.example/path?token=1 key " + "a1" * 20)
        out = redact_text(text, ["Juan Perez"])
        for secret in ("Juan", "Perez", "192.168", "2001:db8", "aa:bb", "juan@", "hunter2", "abcdef123456", "user:pw", "a1a1a1a1"):
            self.assertNotIn(secret, out)
        self.assertEqual(redact_text("see 192.168.0.12."), f"see {MARK}.")

    def test_clock_times_versions_and_plain_ids_are_left_alone(self):
        text = "alarm at 12:30:45 on radar-front, version 0.2.8, ratio 1.5, hour 10:00"
        self.assertEqual(redact_text(text), text)

    def test_names_match_whole_words_without_regard_to_case(self):
        self.assertEqual(redact_text("ana and banana", ["ANA"]), f"{MARK} and banana")

    def test_fields_that_sound_personal_are_replaced_entirely_and_data_keys_stay(self):
        value = {"owner_name": "Ana", "wifi_password": "x", "ip": "10.0.0.1", "nodes": ["radar-1"], "code": "door", "nested": [{"user": "bob", "zone": "hall"}]}
        out = redact_value(value)
        self.assertEqual(out["owner_name"], MARK)
        self.assertEqual(out["wifi_password"], MARK)
        self.assertEqual(out["ip"], MARK)
        self.assertEqual((out["nodes"], out["code"]), (["radar-1"], "door"))
        self.assertEqual(out["nested"], [{"user": MARK, "zone": "hall"}])
        self.assertEqual(redact_value({"by_zone": {"192.168.1.5": 2}}), {"by_zone": {MARK: 2}})

    def test_random_text_never_keeps_a_listed_name_or_an_address(self):
        rng = random.Random(5)
        for _ in range(200):
            noise = "".join(rng.choice(string.ascii_letters + " .:-_") for _ in range(rng.randint(0, 60)))
            ip = ".".join(str(rng.randint(0, 255)) for _ in range(4))
            out = redact_text(f"{noise} Zorro {ip} {noise}", ["Zorro"])
            self.assertNotIn("Zorro", out)
            self.assertNotIn(ip, out)


class StubProvider:
    name = "remote-stub"
    external = True

    def __init__(self):
        self.seen = None

    def enrich(self, payload):
        self.seen = payload
        return "Call Juan Perez at 10.1.2.3, token=abc123"


class AiTests(unittest.TestCase):
    def config(self, **ai):
        return check_config({"enabled": True, "ai": ai})

    def test_off_by_default_and_the_report_has_no_note(self):
        self.assertIsNone(choose_provider(ON))
        self.assertIsNone(make_note({}, [], ON))

    def test_the_simulated_provider_is_deterministic_and_offline(self):
        events = load_events(lines(*random_events(1, 100)))
        summary, findings = build_summary(events, ON), detect_patterns(events, ON)
        config = self.config(enabled=True)
        first = make_note(summary, findings, config)
        self.assertEqual(first, make_note(summary, findings, config))
        self.assertIsNotNone(first)
        self.assertTrue(first and first.startswith("[simulated]"))
        self.assertFalse(SimulatedProvider.external)

    def test_an_unknown_or_external_provider_is_refused_without_the_switch(self):
        with self.assertRaises(ProviderRefused):
            choose_provider(self.config(enabled=True, provider="gpt-something"))
        stub = StubProvider()
        with self.assertRaises(ProviderRefused):
            make_note({"totals": {}}, [], self.config(enabled=True, provider="remote-stub"), {"remote-stub": stub})
        self.assertIsNone(stub.seen)   # it was never called

    def test_with_the_switch_the_payload_and_the_answer_are_redacted(self):
        stub = StubProvider()
        events = load_events(lines({"t_s": 1, "code": "door", "zone": "192.168.9.9"}, {"t_s": 2, "code": "door", "zone": "Zorro"}))
        summary, findings = build_summary(events, ON), detect_patterns(events, ON)
        note = make_note(summary, findings, self.config(enabled=True, provider="remote-stub", allow_external=True, redact_names=["Zorro", "Juan Perez"]), {"remote-stub": stub})
        sent = json.dumps(stub.seen)
        for secret in ("192.168.9.9", "Zorro"):
            self.assertNotIn(secret, sent)
        for secret in ("Juan", "10.1.2.3", "abc123"):
            self.assertNotIn(secret, note or "")

    def test_a_provider_that_answers_something_else_than_text_is_refused(self):
        class Bad(StubProvider):
            external = False

            def enrich(self, payload):
                return {"x": 1}
        with self.assertRaises(ProviderRefused):
            make_note({"totals": {}}, [], self.config(enabled=True, provider="remote-stub"), {"remote-stub": Bad()})

    def test_the_answer_is_cut_to_a_fixed_length(self):
        class Long(StubProvider):
            external = False

            def enrich(self, payload):
                return "x" * 50_000
        self.assertEqual(len(make_note({"totals": {}}, [], self.config(enabled=True, provider="remote-stub"), {"remote-stub": Long()}) or ""), 2000)


class ReportAndCliTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.events = self.dir / "day.jsonl"
        self.events.write_text(lines({"t_s": 3600, "code": "intrusion", "zone": "garden", "severity": "high"}, {"t_s": 3700, "code": "pet", "zone": "hall"}), encoding="utf-8")

    def config(self, **changes):
        path = self.dir / "config.json"
        path.write_text(json.dumps({"enabled": True, **changes}), encoding="utf-8")
        return path

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                cli.main(list(argv))
                code = 0
            except SystemExit as exit_:
                code = exit_.code
        return code, out.getvalue(), err.getvalue()

    def test_without_the_switch_it_refuses_and_says_how_to_turn_it_on(self):
        code, out, err = self.cli("--daily-summary", str(self.events))
        self.assertEqual((code, out), (2, ""))
        self.assertIn('"enabled": true', err)
        off = self.dir / "off.json"
        off.write_text('{"enabled": false}', encoding="utf-8")
        self.assertEqual(self.cli("--daily-summary", str(self.events), "--summary-config", str(off))[0], 2)
        with self.assertRaises(Disabled):
            daily_report(self.events, None)

    def test_text_in_the_chosen_language_and_json_with_the_same_numbers(self):
        config = self.config(language="pt")
        code, out, _ = self.cli("--daily-summary", str(self.events), "--summary-config", str(config))
        self.assertEqual(code, 0)
        self.assertIn("Resumo diário", out)
        code, out, _ = self.cli("--daily-summary", str(self.events), "--summary-config", str(config), "--lang", "de")
        self.assertIn("Tagesübersicht", out)
        code, out, _ = self.cli("--daily-summary", str(self.events), "--summary-config", str(config), "--json")
        report = json.loads(out)
        self.assertEqual(report["summary"]["totals"]["events"], 2)
        self.assertNotIn("ai_note", report)
        self.assertEqual(self.cli("--daily-summary", str(self.events), "--summary-config", str(config), "--lang", "xx")[0], 2)

    def test_malformed_input_prints_nothing_on_stdout_and_exits_2(self):
        bad = self.dir / "bad.jsonl"
        bad.write_text('{"t_s": 1, "code": "a"}\n{"t_s": 2}\n', encoding="utf-8")
        code, out, err = self.cli("--daily-summary", str(bad), "--summary-config", str(self.config()))
        self.assertEqual((code, out), (2, ""))
        self.assertIn("event 2", err)
        self.assertEqual(self.cli("--daily-summary", str(self.dir / "missing.jsonl"), "--summary-config", str(self.config()))[0], 2)
        self.assertEqual(self.cli("--daily-summary", str(self.events), "--summary-config", str(self.dir / "missing.json"))[0], 2)

    def test_the_ai_note_is_added_only_when_asked_and_the_text_is_redacted_to_the_end(self):
        self.events.write_text(lines({"t_s": 1, "code": "intrusion", "zone": "Zorro", "severity": "high"}), encoding="utf-8")
        plain = daily_report(self.events, self.config(ai={"redact_names": ["Zorro"]}))
        self.assertNotIn("ai_note", plain)
        self.assertNotIn("Zorro", json.dumps(plain))
        noted = daily_report(self.events, self.config(ai={"enabled": True}))
        self.assertTrue(noted["ai_note"].startswith("[simulated]"))
        self.assertIn(noted["ai_note"], noted["text"])
        code, out, err = run_daily(self.events, self.config(ai={"enabled": True, "provider": "elsewhere"}), None, False)
        self.assertEqual((code, out), (2, ""))
        self.assertIn("unknown AI provider", err)

    def test_flags_of_the_summary_without_it_are_a_usage_error_and_the_worker_is_untouched(self):
        for flag in (["--summary-config", "x"], ["--lang", "en"], ["--json"]):
            self.assertEqual(self.cli(*flag)[0], 2)

    def test_the_summary_makes_no_network_call(self):
        with mock.patch("socket.socket", side_effect=AssertionError("network")), mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            report = daily_report(self.events, self.config(ai={"enabled": True}))
        self.assertTrue(report["text"])


@unittest.skipUnless((SIMULATOR / "src" / "armor_simulator").is_dir(), "ARMOR-SIMULATOR is not next to this repository")
class SimulatorDataTests(unittest.TestCase):
    def play(self, *argv):
        env = {"PYTHONPATH": str(SIMULATOR / "src"), "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
        done = subprocess.run([sys.executable, "-m", "armor_simulator", *argv, "--start-ms", "0"], capture_output=True, text=True, env=env, cwd=SIMULATOR, check=True)
        return done.stdout

    def test_a_scenario_with_a_silent_node_and_a_day_of_energy_summarise_deterministically(self):
        silent = self.play("--alarm-scenario", "examples/alarm/node-comm-loss.json")
        energy = "\n".join(line for line in self.play("--energy", "--energy-config", "examples/energy/summer-house.json", "--seed", "1").splitlines() if "/electrical/" in line)
        links = build_summary(load_events(silent), ON)["nodes_link_lost"]
        self.assertTrue(links and links[0]["total_s"] > 30)
        first = build_summary(load_events(energy), ON)
        self.assertEqual(first, build_summary(load_events(energy), ON))
        self.assertGreater(first["consumption"]["samples"], 50)
        self.assertEqual(sum(first["by_hour"]), first["totals"]["events"])


if __name__ == "__main__":
    unittest.main()
