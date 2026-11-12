"""The movement model is the one of ARMOR-COMMON, and what the service reports about it follows the contract."""
import _paths  # noqa: F401
import os
import sys
import unittest
from pathlib import Path

from armor_server_ai import motion_core
from armor_server_ai.motion import FRAME_BYTES, observe
from armor_server_ai.service import Watcher
from test_service import Server, frame

ROOT = Path(__file__).resolve().parents[1]
COMMON = Path(os.environ.get("ARMOR_COMMON_DIR") or ROOT.parent / "ARMOR-COMMON")


class SharedMotionTests(unittest.TestCase):
    def test_the_copy_is_the_original_of_the_shared_repository(self):
        original = COMMON / "src" / "armor_common" / "motion_core.py"
        if not original.is_file():
            self.skipTest("ARMOR-COMMON is not next to this repository")
        wanted = original.read_bytes().decode("utf-8").replace("\r\n", "\n")
        mine = (ROOT / "src" / "armor_server_ai" / "motion_core.py").read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(mine, wanted, "copy src/armor_common/motion_core.py of ARMOR-COMMON here (python tools/sync_motion_core.py sync there)")

    def test_the_service_decides_with_the_shared_model(self):
        motion = observe(frame(100), frame(100, moved=400))
        self.assertEqual(motion.ratio, 400 / FRAME_BYTES)
        self.assertTrue(motion.extents)
        self.assertIsInstance(motion, motion_core.Motion)

    def told(self):
        server = Server(tracks=1, lux=200.0)
        server.frames["cam-gate"] = [frame(100), frame(100, moved=400)]
        watcher = Watcher(server, confirm_frames=1, cooldown_s=0.0)
        watcher.run_once()
        watcher.run_once()
        return server.told[0]

    def test_the_observation_tells_where_it_moved_as_rectangles(self):
        report = self.told()
        self.assertTrue(report["regions"])
        self.assertLessEqual(len(report["regions"]), 16)
        for rect in report["regions"]:
            self.assertEqual(sorted(rect), ["h", "w", "x", "y"])
            self.assertTrue(0 <= rect["x"] <= 1 and 0 <= rect["y"] <= 1 and 0 < rect["w"] <= 1 and 0 < rect["h"] <= 1)

    def test_the_report_passes_the_contract_when_the_shared_repository_is_there(self):
        if not (COMMON / "src" / "armor_common" / "contracts.py").is_file():
            self.skipTest("ARMOR-COMMON is not next to this repository")
        sys.path.insert(0, str(COMMON / "src"))
        try:
            from armor_common.contracts import validate_payload
        finally:
            sys.path.pop(0)
        validate_payload("ai_observation", self.told())


class LightAndNoiseTests(unittest.TestCase):
    """A light that comes on changes the whole picture and a person only some neighbouring cells; scattered noise is no region (the check by cells of the area detector)."""

    def test_a_light_switching_on_alone_is_no_cell_and_no_region(self):
        motion = observe(frame(40), frame(220))
        self.assertEqual((motion.ratio, motion.cells, motion.extents), (0.0, frozenset(), ()))

    def test_a_person_inside_a_light_change_is_the_only_region(self):
        from armor_server_ai.motion import FRAME_WIDTH
        lit = bytearray(frame(190))
        for y in range(10, 22):
            for x in range(20, 28):
                lit[y * FRAME_WIDTH + x] = 255
        motion = observe(frame(40), bytes(lit))
        self.assertTrue(motion.cells)
        self.assertEqual(len(motion.extents), 1)
        first_column, first_row, last_column, last_row = motion.extents[0]
        self.assertLessEqual(last_column - first_column, 3)
        self.assertLessEqual(last_row - first_row, 3)

    def test_scattered_noise_over_the_threshold_makes_no_cell(self):
        noisy = bytearray(frame(100))
        for index in range(0, FRAME_BYTES, 40):
            noisy[index] = 200
        motion = observe(frame(100), bytes(noisy))
        self.assertEqual((motion.cells, motion.extents), (frozenset(), ()))
        self.assertLess(motion.ratio, 0.05)

    def test_two_separate_people_are_two_regions_and_touching_cells_are_one(self):
        self.assertEqual(len(motion_core.region_extents({(1, 1), (2, 1), (2, 2)})), 1)
        self.assertEqual(len(motion_core.region_extents({(1, 1), (10, 6)})), 2)
        self.assertEqual(len(motion_core.region_extents({(1, 1), (2, 2)})), 2)   # a diagonal does not join


if __name__ == "__main__":
    unittest.main()
