"""The service against a server that fails: every status the server may answer (a read-only role among them), a body cut short, a server too slow, a refused connection,
and the odd inputs of the small parsers, with a fixed seed for the random ones."""
import _paths  # noqa: F401
import json
import os
import random
import socket
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from armor_server_ai import service
from armor_server_ai.service import HttpServer, ServerError, check_server_url, min_interval_s

TOKEN = "t" * 32


class Misbehaving(BaseHTTPRequestHandler):
    """Answers as `mode` says: a status with a body, a body shorter than it promised, or nothing for a long time."""

    mode: tuple = ("status", 200, b"{}")

    def log_message(self, *args):
        pass

    def respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        kind = Misbehaving.mode[0]
        if kind == "status":
            _, status, payload = Misbehaving.mode
            self.send_response(status)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        elif kind == "short":
            self.send_response(200)
            self.send_header("Content-Length", "1000")
            self.end_headers()
            self.wfile.write(b'{"a":')
            self.wfile.flush()
            self.close_connection = True
        elif kind == "slow":
            time.sleep(Misbehaving.mode[1])

    do_GET = respond
    do_POST = respond


class FaultTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Misbehaving)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def client(self, timeout_s=3.0):
        return HttpServer(self.url, TOKEN, timeout_s=timeout_s)

    def test_every_error_status_keeps_its_number_and_the_name_the_server_gave(self):
        for status in (400, 401, 403, 404, 409, 413, 429, 500, 502, 503, 504):
            Misbehaving.mode = ("status", status, json.dumps({"error": f"e{status}"}).encode())
            with self.assertRaises(ServerError) as caught:
                self.client().context()
            self.assertEqual((caught.exception.status, caught.exception.code), (status, f"e{status}"))

    def test_a_read_only_role_may_read_but_is_refused_when_it_reports(self):
        # the server lets a read-only token ask for the context and the pictures, and answers 403 to the writes
        Misbehaving.mode = ("status", 403, b'{"error":"read_only"}')
        for call in (lambda c: c.observe({"camera_id": "c1"}), lambda c: c.propose_ignore("c1", [])):
            with self.assertRaises(ServerError) as caught:
                call(self.client())
            self.assertEqual((caught.exception.status, caught.exception.code), (403, "read_only"))

    def test_the_text_of_a_server_error_names_the_status_and_the_code(self):
        self.assertEqual(str(ServerError(403, "read_only")), "403 read_only")

    def test_an_error_name_that_is_not_text_still_gives_an_error(self):
        for body in (b'{"error":null}', b'{"error":42}', b'{"error":["a"]}', b'{"other":1}'):
            Misbehaving.mode = ("status", 500, body)
            with self.assertRaises(ServerError) as caught:
                self.client().context()
            self.assertEqual(caught.exception.status, 500)
            self.assertTrue(caught.exception.code)

    def test_a_body_cut_short_is_an_error_not_a_hang_or_a_half_answer(self):
        Misbehaving.mode = ("short",)
        with self.assertRaises((ServerError, ValueError)):
            self.client().context()

    def test_a_server_too_slow_is_unreachable_after_the_timeout(self):
        Misbehaving.mode = ("slow", 2.0)
        started = time.monotonic()
        with self.assertRaises(ServerError) as caught:
            self.client(timeout_s=0.3).frame("c1")
        self.assertEqual((caught.exception.status, caught.exception.code), (0, "unreachable"))
        self.assertLess(time.monotonic() - started, 1.8)

    def test_a_refused_connection_is_unreachable_for_every_call(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        dead = HttpServer(f"http://127.0.0.1:{port}", TOKEN, timeout_s=1)
        for call in (dead.context, lambda: dead.frame("c1"), lambda: dead.observe({}), lambda: dead.propose_ignore("c1", [])):
            with self.assertRaises(ServerError) as caught:
                call()
            self.assertEqual((caught.exception.status, caught.exception.code), (0, "unreachable"))

    def test_an_address_that_does_not_resolve_is_unreachable(self):
        with self.assertRaises(ServerError) as caught:
            HttpServer("http://no-such-host.invalid", TOKEN, timeout_s=2).context()
        self.assertEqual(caught.exception.status, 0)

    def test_an_empty_answer_to_an_observation_is_not_swallowed(self):
        Misbehaving.mode = ("status", 200, b"")
        with self.assertRaises(ValueError):
            self.client().observe({})

    def test_the_reply_to_an_observation_is_limited(self):
        big = json.dumps({"pad": "x" * (service.MAX_REPLY_BYTES + 10)}).encode()
        Misbehaving.mode = ("status", 200, big)
        with self.assertRaises(ValueError):
            self.client().observe({})   # cut at the limit, so the JSON is incomplete


class ParserEdgeTests(unittest.TestCase):
    def test_count_of_radar_targets(self):
        cases = [(True, 0), (False, 0), (0, 0), (3, 3), (2.9, 2), (-4, 0), ([], 0), ([1, 2, 3], 3), (None, 0), ("5", 0), ({"a": 1}, 0), ((1, 2), 0)]
        for value, expected in cases:
            self.assertEqual(service._count(value), expected, repr(value))

    def test_min_interval_grows_with_the_cameras_and_is_never_negative(self):
        previous = -1.0
        for cameras in range(0, 40):
            value = min_interval_s(cameras)
            self.assertGreaterEqual(value, previous)
            previous = value
        self.assertEqual(min_interval_s(0), 0.0)

    def test_server_url_fuzz_with_a_fixed_seed_only_ever_accepts_or_exits(self):
        rng = random.Random(20260101)
        alphabet = "abc:/.@[]-_0123456789 %#?\\é"
        for _ in range(500):
            url = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 40)))
            try:
                self.assertEqual(check_server_url(url), url)
            except SystemExit:
                pass

    def test_server_url_fuzz_never_accepts_a_plain_http_url_to_another_machine(self):
        rng = random.Random(7)
        for _ in range(300):
            host = ".".join(str(rng.randint(1, 254)) for _ in range(4))
            if host.startswith("127."):
                continue
            with self.assertRaises(SystemExit, msg=host):
                check_server_url(f"http://{host}:{rng.randint(1, 65535)}")

    def test_server_url_with_credentials_in_front_of_a_foreign_host_is_refused(self):
        for url in ("http://127.0.0.1@evil.example", "http://localhost@evil.example/", "http://evil.example#127.0.0.1"):
            with self.assertRaises(SystemExit, msg=url):
                check_server_url(url)

    def test_number_setting_edges(self):
        for value in ("1e1", "  7  ", "+3"):
            os.environ["X_FAULT_SETTING"] = value
            try:
                self.assertIsInstance(service._number("X_FAULT_SETTING", 5.0, 1.0, 60.0), float)
            finally:
                del os.environ["X_FAULT_SETTING"]
        for value in ("inf", "-inf", "nan", "1,5", "0x10", "ten"):
            os.environ["X_FAULT_SETTING"] = value
            try:
                with self.assertRaises(SystemExit, msg=value):
                    service._number("X_FAULT_SETTING", 5.0, 1.0, 60.0)
            finally:
                del os.environ["X_FAULT_SETTING"]


class StatusFileTests(unittest.TestCase):
    class Fake:
        def status(self):
            return {"passes": 2, "sent": 1}

    def test_the_file_is_written_whole_and_no_temporary_is_left(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "status.json"
            service.write_status(path, self.Fake(), "", now=lambda: 0)
            body = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(body["updated"], "1970-01-01T00:00:00Z")
            self.assertIsNone(body["server_problem"])
            self.assertEqual([p.name for p in Path(folder).iterdir()], ["status.json"])

    def test_a_server_problem_is_written_and_replaced_by_the_next_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "status.json"
            service.write_status(path, self.Fake(), "unreachable", now=lambda: 60)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["server_problem"], "unreachable")
            service.write_status(path, self.Fake(), "", now=lambda: 120)
            again = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsNone(again["server_problem"])
            self.assertEqual(again["updated"], "1970-01-01T00:02:00Z")

    def test_a_folder_that_does_not_exist_raises_for_the_caller_to_say(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(OSError):
                service.write_status(Path(folder) / "missing" / "status.json", self.Fake(), "")


if __name__ == "__main__":
    unittest.main()
