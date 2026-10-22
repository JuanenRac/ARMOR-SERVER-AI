"""The JSONL policy worker: one answer per line, a bad line never stops it, and what it says is a recommendation, never a command."""
import _paths  # noqa: F401
import contextlib
import io
import json
import unittest
from unittest import mock

from armor_server_ai import cli
from armor_server_ai.profile import ProfileSelector


def run(lines, radar_tracks=0):
    return list(cli.process(lines, radar_tracks, ProfileSelector()))


class ProcessTests(unittest.TestCase):
    def test_a_person_in_the_dark_with_a_radar_track_is_high_and_authorizes_nothing(self):
        (result,) = run([json.dumps({"label": "person", "confidence": 0.95, "lux": 2, "camera_id": "cam-01"})], radar_tracks=1)
        self.assertEqual(result["line"], 1)
        self.assertEqual(result["severity"], "high")
        self.assertFalse(result["authorizes_action"])
        self.assertTrue(result["reasons"])

    def test_the_track_count_of_the_line_wins_over_the_default(self):
        line = json.dumps({"label": "person", "confidence": 0.95, "lux": 100, "radar_tracks": 0})
        self.assertNotEqual(run([line], radar_tracks=3)[0]["severity"], "high")

    def test_blank_lines_are_skipped_but_still_counted_in_the_line_numbers(self):
        good = json.dumps({"label": "person", "confidence": 0.9, "lux": 50})
        results = run([good, "", "   \n", good])
        self.assertEqual([item["line"] for item in results], [1, 4])

    def test_every_kind_of_bad_line_is_reported_with_its_number_and_the_worker_goes_on(self):
        good = json.dumps({"label": "person", "confidence": 0.9, "lux": 50})
        bad_lines = {
            "{not json": "line 1",
            "[1, 2]": "JSON object",
            json.dumps({"label": "x", "confidence": 0.5}): "missing field 'lux'",
            json.dumps({"label": "x", "confidence": "high", "lux": 5}): "could not convert",
            json.dumps({"label": "x", "confidence": 0.5, "lux": 5, "radar_tracks": 1.5}): "whole number",
            json.dumps({"label": "x", "confidence": 0.5, "lux": 5, "radar_tracks": True}): "whole number",
            json.dumps({"label": "x", "confidence": 7, "lux": 5}): "unrecognised visual label",
            "x" * 5000: "longer than 4096 bytes",
        }
        for bad, fragment in bad_lines.items():
            results = run([bad, good])
            self.assertEqual(results[-1]["line"], 2, bad[:30])
            self.assertIn("severity", results[-1], bad[:30])            # the line after the bad one is still answered
            if "error" in results[0]:
                self.assertEqual(results[0]["line"], 1)
                self.assertIn(fragment, results[0]["error"], bad[:30])

    def test_the_size_limit_counts_bytes_not_characters(self):
        text = json.dumps({"label": "é" * 2100, "confidence": 0.5, "lux": 5})
        self.assertIn("longer than", run([text])[0]["error"])

    def test_the_profile_follows_the_light_across_lines_but_not_every_flicker(self):
        def line(lux):
            return json.dumps({"label": "person", "confidence": 0.9, "lux": lux})
        results = run([line(500), line(5), line(500)])          # a second apart: night is entered at once, but day is not returned to before the dwell time
        self.assertEqual([item["profile"] for item in results], ["daylight", "low-light", "low-light"])
        self.assertTrue(all(item["authorizes_action"] is False for item in results))


class MainTests(unittest.TestCase):
    def run_main(self, argv, text):
        out = io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(text)), contextlib.redirect_stdout(out):
            cli.main(argv)
        return [json.loads(line) for line in out.getvalue().splitlines()]

    def test_lines_in_lines_out(self):
        lines = self.run_main([], json.dumps({"label": "person", "confidence": 0.9, "lux": 80}) + "\nnot json\n")
        self.assertEqual([item["line"] for item in lines], [1, 2])
        self.assertIn("error", lines[1])

    def test_the_default_number_of_radar_tracks_comes_from_the_option(self):
        text = json.dumps({"label": "person", "confidence": 0.95, "lux": 2}) + "\n"
        self.assertNotEqual(self.run_main([], text)[0]["severity"], "high")
        self.assertEqual(self.run_main(["--radar-tracks", "2"], text)[0]["severity"], "high")

    def test_a_negative_number_of_tracks_is_refused_by_the_parser(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(SystemExit) as caught:
                self.run_main(["--radar-tracks", "-1"], "")
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("non-negative", err.getvalue())

    def test_output_is_compact_json_one_object_per_line(self):
        out = io.StringIO()
        cli.run(io.StringIO(json.dumps({"label": "person", "confidence": 0.9, "lux": 80}) + "\n"), out, 0)
        text = out.getvalue()
        self.assertTrue(text.endswith("\n"))
        self.assertEqual(text.count("\n"), 1)
        self.assertNotIn(", ", text)


if __name__ == "__main__":
    unittest.main()
