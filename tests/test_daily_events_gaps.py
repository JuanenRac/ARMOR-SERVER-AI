"""The refusals of the daily-event reader that the usual files never reach: too large, too many events, a line that is not an event, a simulator message with a bad topic or a bad date, a
power channel without watts, and a file that cannot be read."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _paths  # noqa: E402, F401

from armor_server_ai import daily_events  # noqa: E402
from armor_server_ai.daily_events import EventError, load_events, load_events_file, parse_text  # noqa: E402


def message(topic, payload):
    return json.dumps({"topic": topic, "payload": payload})


class Reading(unittest.TestCase):
    def test_a_text_larger_than_the_limit_is_refused(self):
        with self.assertRaises(EventError) as raised:
            parse_text(" " * (daily_events.MAX_BYTES + 1))
        self.assertIn("larger than", str(raised.exception))

    def test_more_events_than_the_limit_are_refused_in_a_list_and_in_lines(self):
        old = daily_events.MAX_EVENTS
        daily_events.MAX_EVENTS = 2
        try:
            with self.assertRaises(EventError):
                parse_text("[{}, {}, {}]")
            with self.assertRaises(EventError):
                parse_text("{}\n{}\n{}\n")
        finally:
            daily_events.MAX_EVENTS = old

    def test_a_line_that_is_not_json_names_its_number(self):
        with self.assertRaises(EventError) as raised:
            parse_text('{"a": 1}\n\nnot json\n')
        self.assertIn("line 3", str(raised.exception))

    def test_a_list_that_is_not_json_is_refused(self):
        with self.assertRaises(EventError) as raised:
            parse_text("[1, 2")
        self.assertIn("not valid JSON", str(raised.exception))


class Simulator(unittest.TestCase):
    def test_a_message_with_a_topic_that_is_not_text_or_a_payload_that_is_not_an_object_is_refused(self):
        for text in (json.dumps({"topic": 5, "payload": {"timestamp_ms": 1}}), json.dumps({"topic": "armor/node/a/telemetry", "payload": [1]})):
            with self.assertRaises(EventError) as raised:
                load_events(text)
            self.assertIn("'topic' must be text", str(raised.exception))

    def test_a_message_outside_the_day_or_without_a_date_is_refused(self):
        for stamp in (-1, 86_400_000, "noon", True, None):
            with self.assertRaises(EventError) as raised:
                load_events(message("armor/node/a/telemetry", {"timestamp_ms": stamp}))
            self.assertIn("timestamp_ms", str(raised.exception))

    def test_a_node_that_goes_quiet_and_comes_back_is_a_lost_link_and_one_that_says_offline_too(self):
        text = "\n".join([message("armor/node/radar-1/telemetry", {"timestamp_ms": 1000}), message("armor/node/radar-1/telemetry", {"timestamp_ms": 100_000}),
                          message("armor/node/radar-1/health", {"timestamp_ms": 200_000, "online": False})])
        events = load_events(text)
        self.assertEqual([event.type for event in events], ["node_link_lost", "node_link_lost"])
        self.assertEqual(events[0].duration_s, 99.0)

    def test_the_power_of_the_house_channel_is_read_and_a_missing_or_negative_one_is_refused(self):
        good = message("armor/electrical/meter-1/state", {"timestamp_ms": 5000, "channels": [{"id": "pv", "power_w": 1}, {"id": "house", "power_w": 350}]})
        self.assertEqual([(event.type, event.watts) for event in load_events(good)], [("power", 350.0)])
        for channels in ([], [{"id": "house"}], [{"id": "house", "power_w": -4}], [{"id": "house", "power_w": True}], "none"):
            with self.assertRaises(EventError) as raised:
                load_events(message("armor/electrical/meter-1/state", {"timestamp_ms": 5000, "channels": channels}))
            self.assertIn("power_w", str(raised.exception))

    def test_other_topics_are_left_out(self):
        self.assertEqual(load_events(message("armor/other/x/y", {"timestamp_ms": 5})), [])

    def test_a_mix_of_events_and_messages_is_refused(self):
        with self.assertRaises(EventError):
            load_events(message("armor/node/a/telemetry", {"timestamp_ms": 5}) + "\n" + '{"t_s": 5, "type": "power"}')


class Files(unittest.TestCase):
    def test_a_file_that_is_missing_too_large_or_not_utf8_is_refused_with_its_name(self):
        with tempfile.TemporaryDirectory() as folder:
            missing = Path(folder) / "missing.jsonl"
            with self.assertRaises(EventError) as raised:
                load_events_file(missing)
            self.assertIn("cannot read missing.jsonl", str(raised.exception))
            binary = Path(folder) / "binary.jsonl"
            binary.write_bytes(b"\xff\xfe\x00bad")
            with self.assertRaises(EventError) as raised:
                load_events_file(binary)
            self.assertIn("not UTF-8", str(raised.exception))
            big = Path(folder) / "big.jsonl"
            big.write_text("x" * 100, encoding="utf-8")
            old = daily_events.MAX_BYTES
            daily_events.MAX_BYTES = 10
            try:
                with self.assertRaises(EventError) as raised:
                    load_events_file(big)
            finally:
                daily_events.MAX_BYTES = old
            self.assertIn("big.jsonl is larger", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
