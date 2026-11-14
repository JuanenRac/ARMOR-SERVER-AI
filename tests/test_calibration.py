"""Learning the busy parts of a picture: only counters are kept, a proposal needs enough time and enough comparisons, and nothing is applied."""
import _paths  # noqa: F401
import json
import tempfile
import unittest
from pathlib import Path

from armor_server_ai.calibration import ZoneLearner


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


TREE = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})   # a corner that waves in every comparison


class Learning(unittest.TestCase):
    def learner(self, clock: Clock, **kwargs) -> ZoneLearner:
        return ZoneLearner(clock=clock, min_comparisons=kwargs.pop("min_comparisons", 10), min_hours=kwargs.pop("min_hours", 1.0), **kwargs)

    def test_nothing_is_proposed_before_enough_comparisons_and_enough_hours(self):
        clock = Clock()
        learner = self.learner(clock)
        for _ in range(9):
            learner.feed("cam", TREE)
        clock.now += 7200
        self.assertIsNone(learner.proposal("cam"), "nine comparisons are fewer than ten")
        learner.feed("cam", TREE)
        self.assertEqual(len(learner.proposal("cam")), 1)
        fast = self.learner(Clock())
        for _ in range(20):
            fast.feed("cam", TREE)
        self.assertIsNone(fast.proposal("cam"), "twenty comparisons in no time are not a day of learning")

    def test_a_cell_that_is_always_busy_is_proposed_and_one_that_moved_once_is_not(self):
        clock = Clock()
        learner = self.learner(clock)
        for index in range(10):
            learner.feed("cam", TREE | ({(10, 5)} if index == 0 else set()))
        clock.now += 7200
        learner.feed("cam", TREE)
        proposal = learner.proposal("cam")
        self.assertEqual(len(proposal), 1)
        self.assertEqual(proposal[0]["x"], 0.0)
        self.assertEqual(proposal[0]["y"], 0.0)
        self.assertAlmostEqual(proposal[0]["w"], 2 / 16, places=3)
        self.assertAlmostEqual(proposal[0]["h"], 2 / 9, places=3)

    def test_a_quiet_picture_proposes_nothing_but_says_it_is_ready(self):
        clock = Clock()
        learner = self.learner(clock)
        for _ in range(11):
            learner.feed("cam", frozenset())
        clock.now += 7200
        learner.feed("cam", frozenset())
        self.assertEqual(learner.proposal("cam"), [])
        self.assertTrue(learner.report()["cam"]["ready"])

    def test_cells_outside_the_grid_and_too_many_cameras_are_ignored(self):
        learner = self.learner(Clock())
        learner.feed("cam", {(99, 99), (-1, 0), (3, 3)})
        self.assertEqual(learner.report()["cam"]["comparisons"], 1)
        for index in range(100):
            learner.feed(f"cam-{index}", frozenset())
        self.assertLessEqual(len(learner.report()), 64)

    def test_a_camera_can_be_forgotten(self):
        learner = self.learner(Clock())
        learner.feed("cam", TREE)
        learner.forget("cam")
        self.assertEqual(learner.report(), {})

    def test_bad_settings_are_refused(self):
        for kwargs in ({"min_comparisons": 0}, {"min_hours": -1}, {"busy_share": 0}, {"busy_share": 1.5}):
            with self.assertRaises(ValueError):
                ZoneLearner(**kwargs)


class Keeping(unittest.TestCase):
    def test_the_counters_survive_a_restart_and_hold_nothing_but_counters(self):
        with tempfile.TemporaryDirectory() as holder:
            path = Path(holder) / "learn.json"
            clock = Clock()
            first = ZoneLearner(path, clock=clock, min_comparisons=2, min_hours=0)
            first.feed("cam", TREE)
            first.feed("cam", TREE)
            self.assertTrue(first.save())
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(document), {"schema", "cameras"})
            self.assertEqual(set(document["cameras"]["cam"]), {"comparisons", "first_s", "last_s", "counts"})
            second = ZoneLearner(path, clock=clock, min_comparisons=2, min_hours=0)
            self.assertEqual(second.report()["cam"]["comparisons"], 2)
            self.assertEqual(len(second.proposal("cam")), 1)

    def test_a_damaged_or_foreign_file_is_ignored_not_trusted(self):
        with tempfile.TemporaryDirectory() as holder:
            path = Path(holder) / "learn.json"
            for text in ("{not json", "[]", json.dumps({"schema": 2, "cameras": {}}), json.dumps({"schema": 1, "cameras": {"cam": {"comparisons": 1, "first_s": 1, "last_s": 1, "counts": [[0]]}}}),
                         json.dumps({"schema": 1, "cameras": {"cam": {"comparisons": 1, "first_s": 5, "last_s": 1, "counts": [[0] * 16] * 9}}}),
                         json.dumps({"schema": 1, "cameras": {"cam": {"comparisons": 1, "first_s": 1, "last_s": 1, "counts": [[-1] * 16] * 9}}})):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(ZoneLearner(path).report(), {}, text)
            self.assertEqual(ZoneLearner(Path(holder) / "missing.json").report(), {})

    def test_without_a_file_nothing_is_written(self):
        learner = ZoneLearner()
        learner.feed("cam", TREE)
        self.assertFalse(learner.save())

    def test_a_folder_that_cannot_be_written_is_said_with_false_not_a_crash(self):
        with tempfile.TemporaryDirectory() as holder:
            blocker = Path(holder) / "file"
            blocker.write_text("x", encoding="utf-8")
            learner = ZoneLearner(blocker / "learn.json")
            learner.feed("cam", TREE)
            self.assertFalse(learner.save())


class InTheService(unittest.TestCase):
    class Server:
        def __init__(self, mode):
            self.mode, self.frames, self.asked = mode, [], 0

        def context(self):
            return {"mode": self.mode, "nodes": [], "cameras": [{"id": "cam"}]}

        def frame(self, camera_id):
            self.asked += 1
            return self.frames.pop(0)

        def observe(self, report):
            raise AssertionError("learning never tells the server anything")

    @staticmethod
    def picture(moved: bool) -> bytes:
        from armor_server_ai.motion import FRAME_BYTES
        data = bytearray([100]) * FRAME_BYTES
        if moved:
            for y in range(9, 27):
                for x in range(0, 16):
                    data[y * 64 + x] = 255
        return bytes(data)

    def test_while_disarmed_the_cells_that_moved_are_counted_and_the_server_hears_nothing(self):
        from armor_server_ai.service import Watcher
        server = self.Server("disarmed")
        server.frames = [self.picture(False), self.picture(True), self.picture(False)]
        learner = ZoneLearner(min_comparisons=2, min_hours=0)
        watcher = Watcher(server, learner=learner)
        for _ in range(3):
            self.assertEqual(watcher.run_once(), [])
        self.assertEqual(learner.report()["cam"]["comparisons"], 2)
        self.assertTrue(learner.report()["cam"]["ready"])
        self.assertEqual(len(learner.proposal("cam")), 1)
        self.assertEqual(watcher.status()["learning"]["cam"]["comparisons"], 2)

    def test_without_the_learner_a_disarmed_system_asks_for_no_picture(self):
        from armor_server_ai.service import Watcher
        server = self.Server("disarmed")
        watcher = Watcher(server)
        watcher.run_once()
        self.assertEqual(server.asked, 0)
        self.assertNotIn("learning", watcher.status())

    def test_a_camera_that_does_not_answer_is_skipped_and_its_previous_picture_forgotten(self):
        from armor_server_ai.service import ServerError, Watcher
        server = self.Server("disarmed")
        learner = ZoneLearner()
        watcher = Watcher(server, learner=learner)
        server.frames = [self.picture(False)]
        watcher.run_once()
        server.frame = lambda camera_id: (_ for _ in ()).throw(ServerError(502, "camera_not_answering"))
        watcher.run_once()
        self.assertEqual(learner.report(), {})
        self.assertEqual(watcher._learn_previous, {})

    def test_it_is_off_unless_the_environment_asks(self):
        import os
        from unittest import mock
        from armor_server_ai.service import _learner_from_environment
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ARMOR_AI_LEARN", None)
            self.assertIsNone(_learner_from_environment())
        with mock.patch.dict(os.environ, {"ARMOR_AI_LEARN": "1"}):
            os.environ.pop("ARMOR_AI_LEARN_FILE", None)
            self.assertIsNotNone(_learner_from_environment())


if __name__ == "__main__":
    unittest.main()
