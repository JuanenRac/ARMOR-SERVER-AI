"""Where a radar track falls in the picture of a camera: the geometry, the match with the regions of movement, and the switch that is off by default."""
import _paths  # noqa: F401
import math
import unittest

from armor_server_ai.motion import FRAME_BYTES
from armor_server_ai.service import Watcher
from armor_server_ai.spatial import Pose, column_in_picture, matching_tracks, parse_pose, track_on_plan

WIDTH = 64   # the frames are 64 x 36 grey pixels


def band(value: int, x0: int, x1: int, y0: int = 9, y1: int = 27, to: int = 255) -> bytes:
    """A flat frame with a block of pixels at `to` (columns x0..x1-1, rows y0..y1-1)."""
    data = bytearray([value]) * FRAME_BYTES
    for y in range(y0, y1):
        for x in range(x0, x1):
            data[y * WIDTH + x] = to
    return bytes(data)


CAMERA = {"pose": {"x_mm": 0, "y_mm": 0, "yaw_deg": 0}, "fov_deg": 90, "range_mm": 15000}
HERE = {"pose": {"x_mm": 0, "y_mm": 0, "yaw_deg": 0}}   # a radar standing at the camera, facing the same way
LEFT = {"x": 0.0, "y": 0.2, "w": 0.25, "h": 0.5}
RIGHT = {"x": 0.75, "y": 0.2, "w": 0.25, "h": 0.5}


class Geometry(unittest.TestCase):
    def test_a_point_straight_ahead_is_the_middle_of_the_picture_and_the_sides_follow_the_view(self):
        camera = Pose(0, 0, 0)
        self.assertAlmostEqual(column_in_picture(camera, 90, 15000, (0, 4000)), 0.5)
        left = column_in_picture(camera, 90, 15000, (-2000, 4000))
        right = column_in_picture(camera, 90, 15000, (2000, 4000))
        self.assertAlmostEqual(left, 0.25)
        self.assertAlmostEqual(right, 0.75)
        self.assertAlmostEqual(column_in_picture(camera, 90, 15000, (-4000, 4000)), 0.0)   # on the edge of the view

    def test_behind_beyond_the_range_or_outside_the_view_is_not_in_the_picture(self):
        camera = Pose(0, 0, 0)
        self.assertIsNone(column_in_picture(camera, 90, 15000, (0, -1000)))
        self.assertIsNone(column_in_picture(camera, 90, 15000, (0, 16000)))
        self.assertIsNone(column_in_picture(camera, 90, 15000, (-5000, 4000)))

    def test_a_radar_turned_to_the_east_places_its_tracks_to_the_east(self):
        east = Pose(0, 0, 90)
        x, y = track_on_plan(east, 0, 3000)
        self.assertAlmostEqual(x, 3000)
        self.assertAlmostEqual(y, 0, places=6)
        x, y = track_on_plan(east, 1000, 0)   # to the right of a radar that faces east is south
        self.assertAlmostEqual(x, 0, places=6)
        self.assertAlmostEqual(y, -1000)

    def test_a_pose_must_be_three_sensible_numbers(self):
        self.assertEqual(parse_pose({"x_mm": 1, "y_mm": 2, "yaw_deg": 3}), Pose(1, 2, 3))
        for bad in (None, {}, {"x_mm": 1, "y_mm": 2}, {"x_mm": True, "y_mm": 2, "yaw_deg": 0}, {"x_mm": math.nan, "y_mm": 2, "yaw_deg": 0}, {"x_mm": 1e12, "y_mm": 2, "yaw_deg": 0}, "x"):
            self.assertIsNone(parse_pose(bad), bad)


class Matching(unittest.TestCase):
    def test_a_track_on_the_side_of_the_movement_counts_and_one_on_the_other_side_does_not(self):
        left_track = {**HERE, "targets": [{"x_mm": -2000, "y_mm": 4000}]}
        right_track = {**HERE, "targets": [{"x_mm": 2000, "y_mm": 4000}]}
        self.assertEqual(matching_tracks(CAMERA, [left_track], [LEFT], 1), 1)
        self.assertEqual(matching_tracks(CAMERA, [right_track], [LEFT], 1), 0)
        self.assertEqual(matching_tracks(CAMERA, [left_track, right_track], [RIGHT], 2), 1)

    def test_the_placed_tracks_the_server_sends_as_track_points_are_judged_and_the_count_is_kept(self):
        left_track = {**HERE, "targets": 1, "track_points": [{"x_mm": -2000, "y_mm": 4000}]}
        right_track = {**HERE, "targets": 1, "track_points": [{"x_mm": 2000, "y_mm": 4000}]}
        self.assertEqual(matching_tracks(CAMERA, [left_track], [LEFT], 1), 1)
        self.assertEqual(matching_tracks(CAMERA, [right_track], [LEFT], 1), 0)
        counted_only = {**HERE, "targets": 2}   # a node that sends no points: its tracks keep counting
        self.assertEqual(matching_tracks(CAMERA, [counted_only, right_track], [LEFT], 3), 2)

    def test_a_track_outside_the_picture_does_not_count(self):
        behind = {**HERE, "targets": [{"x_mm": 0, "y_mm": -3000}]}
        self.assertEqual(matching_tracks(CAMERA, [behind], [LEFT, RIGHT], 1), 0)

    def test_what_cannot_be_placed_keeps_counting_as_before(self):
        self.assertEqual(matching_tracks({}, [{"targets": 2}], [LEFT], 2), 2, "no pose for the camera")
        self.assertEqual(matching_tracks(CAMERA, [{"targets": 3}], [LEFT], 3), 3, "a node that gives only a count")
        self.assertEqual(matching_tracks(CAMERA, [{**HERE, "targets": 2}], [LEFT], 2), 2, "a node with a pose that gives only a count")
        self.assertEqual(matching_tracks(CAMERA, [{"targets": [{"x_mm": 0, "y_mm": 3000}]}], [LEFT], 1), 1, "tracks of a node without a pose")
        self.assertEqual(matching_tracks(CAMERA, [{**HERE, "targets": [{"x_mm": -2000, "y_mm": 4000}]}], [], 1), 1, "no region of movement to compare with")
        self.assertEqual(matching_tracks({**CAMERA, "fov_deg": 5}, [{**HERE, "targets": [{"x_mm": 0, "y_mm": 3000}]}], [LEFT], 1), 1, "a view that makes no sense")

    def test_odd_tracks_are_ignored_not_trusted(self):
        node = {**HERE, "targets": [{"x_mm": "a", "y_mm": 1}, {"x_mm": -2000, "y_mm": 4000}, 5, None]}
        self.assertEqual(matching_tracks(CAMERA, [node], [LEFT], 4), 1)


class Server:
    def __init__(self, targets):
        self.targets, self.frames, self.told = targets, [], []

    def context(self):
        return {"mode": "armed", "nodes": [{"id": "radar", "online": True, "targets": self.targets, "lux": 200.0, **HERE}],
                "cameras": [{"id": "cam", "nodes": ["radar"], **CAMERA}]}

    def frame(self, camera_id):
        return self.frames.pop(0)

    def observe(self, report):
        self.told.append(report)
        return {"raised": True}


class WatcherSwitch(unittest.TestCase):
    def run_watcher(self, spatial: bool, track_x: int) -> list[dict]:
        server = Server([{"x_mm": track_x, "y_mm": 4000}])
        server.frames = [band(100, 0, 0), band(100, 0, 16)]   # the movement is in the left quarter of the picture
        watcher = Watcher(server, confirm_frames=1, cooldown_s=0.0, spatial=spatial)
        watcher.run_once()
        watcher.run_once()
        return server.told

    def test_off_by_default_any_track_of_the_covering_nodes_counts(self):
        told = self.run_watcher(False, 2000)    # the track is on the right, the movement on the left
        self.assertEqual([item["radar_tracks"] for item in told], [1])

    def test_on_a_track_on_the_other_side_of_the_picture_is_not_evidence(self):
        self.assertEqual([item["radar_tracks"] for item in self.run_watcher(True, 2000)], [0])
        told = self.run_watcher(True, -2000)
        self.assertEqual([(item["radar_tracks"], item["severity"]) for item in told], [(1, "high")])

    def test_the_default_of_the_class_is_off(self):
        self.assertFalse(Watcher(Server([]))._spatial)


if __name__ == "__main__":
    unittest.main()
