"""What the policy worker and the service did before the daily summary existed, fixed so that nothing in them changes."""
import _paths  # noqa: F401
import contextlib
import io
import json
import unittest
from unittest import mock

import armor_server_ai
from armor_server_ai import cli, service

LINE = json.dumps({"label": "person", "confidence": 0.95, "lux": 2, "camera_id": "cam-01"})


def run_main(argv, stdin_text=""):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(stdin_text)), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            cli.main(argv)
            code = 0
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


class WorkerStaysTests(unittest.TestCase):
    def test_without_flags_the_worker_reads_stdin_and_writes_one_compact_json_line_per_input(self):
        code, out, _ = run_main(["--radar-tracks", "1"], LINE + "\n")
        self.assertEqual(code, 0)
        (result,) = [json.loads(line) for line in out.splitlines()]
        self.assertEqual((result["line"], result["severity"], result["authorizes_action"]), (1, "high", False))
        self.assertTrue(out.startswith('{"line":1,"severity":"high"'))   # compact separators

    def test_a_negative_radar_track_default_is_refused_with_a_usage_error(self):
        code, _, err = run_main(["--radar-tracks", "-1"])
        self.assertEqual(code, 2)
        self.assertIn("--radar-tracks must be non-negative", err)

    def test_an_unknown_flag_is_a_usage_error(self):
        self.assertEqual(run_main(["--nonexistent"])[0], 2)

    def test_empty_input_gives_empty_output(self):
        self.assertEqual(run_main([], ""), (0, "", ""))


class ServiceStaysTests(unittest.TestCase):
    def test_the_service_listens_on_no_port(self):
        with open(service.__file__, encoding="utf-8") as stream:
            source = stream.read()
        for word in ("http.server", "socketserver", ".listen(", "HTTPServer"):
            self.assertNotIn(word, source)

    def test_the_server_url_rules(self):
        self.assertEqual(service.check_server_url("http://127.0.0.1:18080"), "http://127.0.0.1:18080")
        self.assertEqual(service.check_server_url("https://example.org"), "https://example.org")
        for bad in ("http://example.org", "ftp://127.0.0.1", "file:///etc/passwd"):
            with self.assertRaises(SystemExit):
                service.check_server_url(bad)

    def test_the_pass_is_spaced_out_for_the_server_limit(self):
        self.assertEqual(service.min_interval_s(0), 0.0)
        self.assertGreater(service.min_interval_s(300), service.min_interval_s(100))

    def test_the_service_still_needs_its_token(self):
        with mock.patch.dict("os.environ", {"ARMOR_AI_TOKEN": "short"}), self.assertRaises(SystemExit):
            service.main(["--once"])

    def test_the_public_names_of_the_package(self):
        self.assertEqual(sorted(name for name in ("decide", "discover_engines", "ProfileSelector", "VisualObservation") if hasattr(armor_server_ai, name)),
                         ["ProfileSelector", "VisualObservation", "decide", "discover_engines"])


if __name__ == "__main__":
    unittest.main()
