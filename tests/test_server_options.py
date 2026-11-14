"""The options of the server (both off by default) decide where the radar tracks are placed and whether the pictures are studied; the areas found are proposed to the server, which applies nothing."""
import _paths  # noqa: F401
import unittest

from armor_server_ai.calibration import ZoneLearner
from armor_server_ai.motion import FRAME_BYTES
from armor_server_ai.service import ServerError, Watcher


def picture(moved: bool) -> bytes:
    data = bytearray([100]) * FRAME_BYTES
    if moved:
        for y in range(9, 27):
            for x in range(0, 16):
                data[y * 64 + x] = 255
    return bytes(data)


class Server:
    def __init__(self, options=None, answers=None):
        self.options, self.answers, self.proposed, self.frames = options, list(answers or []), [], []

    def context(self):
        body = {"mode": "disarmed", "nodes": [], "cameras": [{"id": "cam"}]}
        if self.options is not None:
            body["options"] = self.options
        return body

    def frame(self, camera_id):
        return self.frames.pop(0)

    def observe(self, report):
        raise AssertionError("studying the pictures never tells an observation")

    def propose_ignore(self, camera_id, zones):
        self.proposed.append((camera_id, zones))
        answer = self.answers.pop(0) if self.answers else {"stored": True}
        if isinstance(answer, Exception):
            raise answer
        return answer


def watcher(server):
    return Watcher(server, learner_factory=lambda: ZoneLearner(min_comparisons=2, min_hours=0))


class FollowingTheOptions(unittest.TestCase):
    def test_the_study_starts_only_when_the_server_says_learn_and_stops_when_it_says_no(self):
        server = Server({"spatial": False, "learn": False})
        service = watcher(server)
        service.run_once()
        self.assertIsNone(service._learner)
        server.options = {"spatial": True, "learn": True}
        server.frames = [picture(False)]
        service.run_once()
        self.assertIsNotNone(service._learner)
        self.assertTrue(service._spatial)
        server.options = {"spatial": False, "learn": False}
        service.run_once()
        self.assertIsNone(service._learner)
        self.assertFalse(service._spatial)

    def test_a_server_that_tells_no_options_leaves_the_environment_in_charge(self):
        service = Watcher(Server(None), spatial=True, learner_factory=lambda: ZoneLearner())
        service.run_once()
        self.assertTrue(service._spatial)
        self.assertIsNone(service._learner)

    def test_what_is_found_is_proposed_once_and_again_only_when_it_changes(self):
        server = Server({"spatial": False, "learn": True})
        server.frames = [picture(False), picture(True), picture(False), picture(False), picture(False)]
        service = watcher(server)
        for _ in range(3):
            service.run_once()
        self.assertEqual(len(server.proposed), 1)
        self.assertEqual(server.proposed[0][0], "cam")
        self.assertTrue(all(set(zone) == {"x", "y", "w", "h"} for zone in server.proposed[0][1]))
        service.run_once()
        self.assertEqual(len(server.proposed), 1, "the same proposal is not told twice")

    def test_a_server_without_the_route_or_a_refusal_does_not_stop_the_service(self):
        server = Server({"spatial": False, "learn": True}, answers=[ServerError(404, "not_found")])
        server.frames = [picture(False), picture(True), picture(False), picture(True)]
        service = watcher(server)
        for _ in range(4):
            service.run_once()
        self.assertGreaterEqual(len(server.proposed), 2, "a refused proposal is tried again")

    def test_a_server_that_remembers_a_rejection_is_not_asked_again(self):
        server = Server({"spatial": False, "learn": True}, answers=[{"stored": False, "reason": "rejected_before"}])
        server.frames = [picture(False), picture(True), picture(False), picture(False)]
        service = watcher(server)
        for _ in range(4):
            service.run_once()
        self.assertEqual(len(server.proposed), 1)


if __name__ == "__main__":
    unittest.main()
