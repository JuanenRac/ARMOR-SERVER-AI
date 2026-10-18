"""The service's side of the conversation with ARMOR-SERVER: the HTTP client (against a stand-in server on the loopback of this machine), the settings from the environment and the run loop."""
import contextlib
import io
import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from armor_server_ai import service
from armor_server_ai.motion import FRAME_BYTES
from armor_server_ai.service import HttpServer, ServerError, check_server_url, main, min_interval_s

TOKEN = "t" * 32


class StandIn(BaseHTTPRequestHandler):
    """What the real server would answer, recorded: the tests set `routes` before each request."""

    routes: dict[tuple[str, str], tuple[int, bytes]] = {}
    seen: list[dict] = []

    def log_message(self, *args):
        pass

    def respond(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        StandIn.seen.append({"method": self.command, "path": self.path, "auth": self.headers.get("Authorization"), "body": body, "type": self.headers.get("Content-Type")})
        status, payload = StandIn.routes.get((self.command, self.path), (404, b'{"error":"not_found"}'))
        self.send_response(status)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    do_GET = respond
    do_POST = respond


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), StandIn)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        StandIn.routes = {}
        StandIn.seen = []
        self.client = HttpServer(self.url, TOKEN, timeout_s=3)

    def test_the_context_is_asked_with_the_token_and_decoded(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (200, json.dumps({"mode": "armed", "cameras": []}).encode())
        self.assertEqual(self.client.context(), {"mode": "armed", "cameras": []})
        self.assertEqual(StandIn.seen[0]["auth"], f"Bearer {TOKEN}")

    def test_a_trailing_slash_in_the_address_does_not_double_the_slash(self):
        client = HttpServer(self.url + "/", TOKEN)
        StandIn.routes[("GET", "/api/v1/ai/context")] = (200, b"{}")
        self.assertEqual(client.context(), {})

    def test_a_frame_is_asked_by_an_encoded_camera_id(self):
        StandIn.routes[("GET", "/api/v1/ai/cameras/gate%2Fnorth%20side/frame")] = (200, b"\x01" * FRAME_BYTES)
        self.assertEqual(self.client.frame("gate/north side"), b"\x01" * FRAME_BYTES)

    def test_an_oversized_frame_is_cut_not_read_to_the_end(self):
        StandIn.routes[("GET", "/api/v1/ai/cameras/cam/frame")] = (200, b"\x02" * (FRAME_BYTES * 3))
        # one byte more than expected is read, so the caller can see it is not the size expected, but not all of it
        self.assertEqual(len(self.client.frame("cam")), FRAME_BYTES + 1)

    def test_an_observation_is_sent_as_json(self):
        StandIn.routes[("POST", "/api/v1/ai/observations")] = (200, b'{"accepted":true}')
        self.assertEqual(self.client.observe({"camera_id": "cam", "severity": "review"}), {"accepted": True})
        sent = StandIn.seen[0]
        self.assertEqual(json.loads(sent["body"]), {"camera_id": "cam", "severity": "review"})
        self.assertEqual(sent["type"], "application/json")

    def test_the_error_the_server_gives_is_kept(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (401, b'{"error":"unauthorized"}')
        with self.assertRaises(ServerError) as caught:
            self.client.context()
        self.assertEqual((caught.exception.status, caught.exception.code), (401, "unauthorized"))

    def test_an_error_without_a_body_or_with_garbage_is_still_an_error_with_a_name(self):
        for body in (b"", b"<html>nope</html>", b"[1,2]", b'"text"'):
            StandIn.routes[("GET", "/api/v1/ai/context")] = (503, body)
            with self.assertRaises(ServerError) as caught:
                self.client.context()
            self.assertEqual((caught.exception.status, caught.exception.code), (503, "http_error"), body)

    def test_a_server_that_is_not_there_is_unreachable(self):
        dead = HttpServer("http://127.0.0.1:9", TOKEN, timeout_s=1)
        with self.assertRaises(ServerError) as caught:
            dead.context()
        self.assertEqual((caught.exception.status, caught.exception.code), (0, "unreachable"))

    def test_a_reply_that_is_not_json_is_not_swallowed_silently(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (200, b"not json")
        with self.assertRaises(ValueError):
            self.client.context()


class SettingsTests(unittest.TestCase):
    def test_the_address_rules(self):
        for good in ("https://armor.example/", "http://127.0.0.1:18080", "http://localhost:8080", "http://[::1]:8080", "https://10.0.0.5"):
            self.assertEqual(check_server_url(good), good)
        for bad in ("http://192.168.0.5:18080", "http://armor.example", "http://127.0.0.1.evil.example", "ftp://127.0.0.1", "file:///etc/passwd", "https://", "http://", "", "127.0.0.1:18080"):
            with self.assertRaises(SystemExit, msg=bad):
                check_server_url(bad)

    def test_the_pass_is_spaced_by_the_limit_of_the_server(self):
        self.assertEqual(min_interval_s(0), 0.0)
        self.assertAlmostEqual(min_interval_s(10), 3.0)
        self.assertAlmostEqual(min_interval_s(200), 60.0)

    def test_numbers_from_the_environment(self):
        with mock.patch.dict(os.environ, {"X_SETTING": ""}):
            self.assertEqual(service._number("X_SETTING", 3.0, 1.0, 60.0), 3.0)
        for value, expected in (("5", 5.0), (" 2.5 ", 2.5), ("60", 60.0), ("1", 1.0)):
            with mock.patch.dict(os.environ, {"X_SETTING": value}):
                self.assertEqual(service._number("X_SETTING", 3.0, 1.0, 60.0), expected)
        for value in ("abc", "0.5", "61", "-1", "nan"):
            with mock.patch.dict(os.environ, {"X_SETTING": value}):
                with self.assertRaises(SystemExit, msg=value):
                    service._number("X_SETTING", 3.0, 1.0, 60.0)

    def test_the_service_will_not_start_with_a_short_token_or_bad_settings(self):
        with mock.patch.dict(os.environ, {"ARMOR_AI_TOKEN": "short"}):
            with self.assertRaises(SystemExit) as caught:
                main(["--once"])
            self.assertIn("ARMOR_AI_TOKEN", str(caught.exception))
        base = {"ARMOR_AI_TOKEN": TOKEN}
        for name, value in (("ARMOR_AI_SERVER_URL", "http://example.org"), ("ARMOR_AI_INTERVAL_S", "0"), ("ARMOR_AI_CONFIRM_FRAMES", "0"), ("ARMOR_AI_COOLDOWN_S", "-5")):
            with mock.patch.dict(os.environ, {**base, name: value}):
                with self.assertRaises(SystemExit, msg=name):
                    main(["--once"])

    def test_a_watcher_needs_at_least_one_confirming_frame(self):
        with self.assertRaises(ValueError):
            service.Watcher(mock.Mock(), confirm_frames=0)


class OncePassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), StandIn)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        StandIn.routes = {}
        StandIn.seen = []

    def run_once(self):
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"ARMOR_AI_TOKEN": TOKEN, "ARMOR_AI_SERVER_URL": self.url}), contextlib.redirect_stdout(out):
            main(["--once"])
        return out.getvalue()

    def test_a_disarmed_house_is_looked_at_by_nobody(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (200, json.dumps({"mode": "disarmed", "cameras": [{"id": "cam"}]}).encode())
        self.assertEqual(json.loads(self.run_once()), [])
        self.assertEqual([item["path"] for item in StandIn.seen], ["/api/v1/ai/context"])   # not one picture was asked for

    def test_an_armed_house_has_its_cameras_asked_once_each(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (200, json.dumps({"mode": "armed", "nodes": [], "cameras": [{"id": "a"}, {"id": "b"}]}).encode())
        StandIn.routes[("GET", "/api/v1/ai/cameras/a/frame")] = (200, b"\x40" * FRAME_BYTES)
        StandIn.routes[("GET", "/api/v1/ai/cameras/b/frame")] = (200, b"\x40" * FRAME_BYTES)
        self.assertEqual(json.loads(self.run_once()), [])   # the first frame has nothing to be compared with
        self.assertEqual(sorted(item["path"] for item in StandIn.seen), ["/api/v1/ai/cameras/a/frame", "/api/v1/ai/cameras/b/frame", "/api/v1/ai/context"])

    def test_a_server_that_refuses_the_token_is_a_clean_exit_not_a_traceback(self):
        StandIn.routes[("GET", "/api/v1/ai/context")] = (401, b'{"error":"unauthorized"}')
        with mock.patch.dict(os.environ, {"ARMOR_AI_TOKEN": TOKEN, "ARMOR_AI_SERVER_URL": self.url}):
            with self.assertRaises(SystemExit) as caught:
                main(["--once"])
        self.assertIn("unauthorized", str(caught.exception))

    def test_a_context_that_is_not_an_object_is_refused(self):
        class Odd:
            def context(self):
                return ["not", "an", "object"]
        with self.assertRaises(ServerError) as caught:
            service.Watcher(Odd()).run_once()
        self.assertEqual(caught.exception.code, "bad_context")

    def test_odd_lists_in_the_context_are_ignored_not_fatal(self):
        class Odd:
            def context(self):
                return {"mode": "armed", "nodes": "nope", "cameras": [1, {"id": 5}, {"id": "ok"}, "x"]}

            def frame(self, camera_id):
                return b"\x10" * FRAME_BYTES
        watcher = service.Watcher(Odd())
        self.assertEqual(watcher.run_once(), [])
        self.assertEqual(watcher.camera_count, 1)

    def test_a_picture_of_the_wrong_size_is_said_once_and_not_judged(self):
        class Small:
            def context(self):
                return {"mode": "armed", "cameras": [{"id": "cam"}]}

            def frame(self, camera_id):
                return b"\x10" * 10
        watcher = service.Watcher(Small())
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            watcher.run_once()
            watcher.run_once()
        self.assertEqual(err.getvalue().count("not the size expected"), 1)


class RunLoopTests(unittest.TestCase):
    """The loop that runs for ever, stopped by a signal handler the test calls itself."""

    def test_a_server_that_fails_is_said_once_and_when_it_answers_again(self):
        answers = [ServerError(0, "unreachable"), ServerError(0, "unreachable"), [], ServerError(500, "http_error")]
        handlers = {}

        class Fake:
            camera_count = 0

            def __init__(self, *args, **kwargs):
                pass

            def run_once(self):
                answer = answers.pop(0)
                if not answers:
                    handlers["stop"]()
                if isinstance(answer, Exception):
                    raise answer
                return answer

        err = io.StringIO()
        env = {"ARMOR_AI_TOKEN": TOKEN, "ARMOR_AI_INTERVAL_S": "1"}
        with mock.patch.dict(os.environ, env), mock.patch.object(service, "Watcher", Fake), mock.patch.object(service.time, "sleep"), \
                mock.patch.object(service.signal, "signal", side_effect=lambda number, handler: handlers.setdefault("stop", handler)), contextlib.redirect_stderr(err):
            main([])
        lines = err.getvalue().splitlines()
        self.assertEqual(sum("could not be asked (unreachable)" in line for line in lines), 1)     # twice the same problem, said once
        self.assertEqual(sum("the server answers again" in line for line in lines), 1)
        self.assertEqual(sum("could not be asked (http_error)" in line for line in lines), 1)


if __name__ == "__main__":
    unittest.main()
