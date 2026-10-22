import _paths  # noqa: F401
import unittest

from armor_server_ai.motion import FRAME_BYTES, FRAME_WIDTH, MAX_ZONES, changed_ratio, mask_from_zones


def frame(value: int = 100, patches=()) -> bytes:
    data = bytearray([value]) * FRAME_BYTES
    for x0, y0, x1, y1, grey in patches:
        for y in range(y0, y1):
            for x in range(x0, x1):
                data[y * FRAME_WIDTH + x] = grey
    return bytes(data)


class IgnoreZonesTests(unittest.TestCase):
    def test_no_zones_is_no_mask(self):
        self.assertIsNone(mask_from_zones(None))
        self.assertIsNone(mask_from_zones([]))
        self.assertIsNone(mask_from_zones([{"x": 2, "y": 0, "w": 0.5, "h": 0.5}, "nope", {"x": 0}]))   # none of them is a rectangle inside the picture

    def test_a_zone_takes_its_pixels_out(self):
        mask = mask_from_zones([{"x": 0.0, "y": 0.0, "w": 0.5, "h": 1.0}])
        self.assertEqual(len(mask), FRAME_BYTES)
        self.assertEqual(sum(mask), FRAME_BYTES // 2)
        self.assertEqual(mask[0], 0)
        self.assertEqual(mask[FRAME_WIDTH - 1], 1)
        self.assertEqual(mask_from_zones([(0.0, 0.0, 0.5, 1.0)]), mask)   # a tuple says the same

    def test_movement_inside_a_zone_is_not_movement(self):
        before = frame()
        waving = frame(patches=[(0, 0, 20, 36, 230)])   # a tree on the left of the picture
        self.assertGreater(changed_ratio(before, waving), 0.2)
        mask = mask_from_zones([{"x": 0.0, "y": 0.0, "w": 0.4, "h": 1.0}])
        self.assertEqual(changed_ratio(before, waving, mask=mask), 0.0)

    def test_movement_outside_a_zone_still_counts_and_is_a_share_of_what_is_left(self):
        before = frame()
        person = frame(patches=[(50, 10, 60, 30, 230)])   # on the right
        mask = mask_from_zones([{"x": 0.0, "y": 0.0, "w": 0.4, "h": 1.0}])
        self.assertAlmostEqual(changed_ratio(before, person), 200 / FRAME_BYTES, places=3)
        self.assertGreater(changed_ratio(before, person, mask=mask), changed_ratio(before, person))   # the same movement is a bigger share of a smaller picture
        self.assertAlmostEqual(changed_ratio(before, person, mask=mask), 200 / sum(mask), places=3)

    def test_a_picture_that_is_almost_all_ignored_is_not_judged(self):
        mask = mask_from_zones([{"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.98}])
        self.assertEqual(changed_ratio(frame(), frame(200), mask=mask), 0.0)

    def test_the_most_zones_and_a_wrong_mask(self):
        zones = [{"x": 0.0, "y": i / 20, "w": 0.05, "h": 0.04} for i in range(MAX_ZONES + 4)]
        self.assertIsNotNone(mask_from_zones(zones))
        with self.assertRaises(ValueError):
            changed_ratio(frame(), frame(), mask=b"short")


if __name__ == "__main__":
    unittest.main()
