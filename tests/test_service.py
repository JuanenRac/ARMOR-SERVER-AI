import unittest

from armor_server_ai.motion import FRAME_BYTES, brightness, changed_ratio, estimate_lux, motion_confidence
from armor_server_ai.policy import VisualObservation, decide
from armor_server_ai.service import GLOBAL_CHANGE_RATIO, CameraState, ServerError, Watcher, look


def frame(value: int, moved: int = 0, to: int = 255) -> bytes:
    """A flat grey frame in which `moved` pixels (from the start) are `to`."""
    data = bytearray([value]) * FRAME_BYTES
    for index in range(moved):
        data[index] = to
    return bytes(data)


class MotionTests(unittest.TestCase):
    def test_nothing_moved_between_equal_frames_and_noise_is_not_movement(self):
        self.assertEqual(changed_ratio(frame(100), frame(100)), 0.0)
        self.assertEqual(changed_ratio(frame(100), frame(110)), 0.0)   # the noise of the sensor, under the threshold
        self.assertEqual(changed_ratio(frame(100), frame(100, moved=230)), 230 / FRAME_BYTES)

    def test_confidence_is_the_changed_share_against_what_moving_fully_means(self):
        self.assertEqual(motion_confidence(0.0), 0.0)
        self.assertAlmostEqual(motion_confidence(0.05), 0.5)
        self.assertEqual(motion_confidence(0.5), 1.0)
        with self.assertRaises(ValueError):
            motion_confidence(-1)
        with self.assertRaises(ValueError):
            changed_ratio(b"short", frame(0))

    def test_a_dark_picture_is_low_light_and_a_bright_one_is_daylight(self):
        self.assertLess(estimate_lux(frame(30)), 30)
        self.assertGreater(estimate_lux(frame(120)), 60)
        self.assertEqual(brightness(frame(50)), 50.0)


class PolicyTests(unittest.TestCase):
    def test_strong_movement_with_a_radar_track_is_high_and_alone_it_is_only_a_review(self):
        strong = VisualObservation(label="motion", confidence=0.9, lux=100.0)
        self.assertEqual(decide(strong, 1).severity, "high")
        self.assertEqual(decide(strong, 0).severity, "review")
        self.assertEqual(decide(VisualObservation(label="motion", confidence=0.2, lux=100.0), 0).severity, "ignore")
        # a little movement is not made a review by a radar track somewhere else in the house; a clear one is
        self.assertEqual(decide(VisualObservation(label="motion", confidence=0.2, lux=100.0), 2).severity, "ignore")
        self.assertEqual(decide(VisualObservation(label="motion", confidence=0.35, lux=100.0), 2).severity, "review")


class Server:
    """A stand-in for ARMOR-SERVER: the context, the frames of the cameras, and what is told."""

    def __init__(self, mode="armed", tracks=0, lux=None, cameras=("cam-gate",)):
        self.mode, self.tracks, self.lux, self.cameras = mode, tracks, lux, list(cameras)
        self.frames: dict[str, list[bytes]] = {name: [] for name in cameras}
        self.told: list[dict] = []
        self.failing: set[str] = set()

    def context(self):
        return {"mode": self.mode, "nodes": [{"id": "radar", "online": True, "targets": self.tracks, "lux": self.lux}], "cameras": [{"id": name, "name": name} for name in self.cameras]}

    def frame(self, camera_id):
        if camera_id in self.failing:
            raise ServerError(502, "camera_not_answering")
        return self.frames[camera_id].pop(0)

    def observe(self, report):
        self.told.append(report)
        return {"raised": True}


class WatcherTests(unittest.TestCase):
    def test_movement_in_two_frames_in_a_row_with_a_radar_track_is_told_once(self):
        server = Server(tracks=1, lux=200.0)
        server.frames["cam-gate"] = [frame(100), frame(100, moved=400), frame(100, moved=400), frame(100), frame(100, moved=400)]
        clock = iter(range(0, 1000, 5))
        watcher = Watcher(server, confirm_frames=2, cooldown_s=60.0, clock=lambda: next(clock))
        outcomes = [watcher.run_once() for _ in range(5)]
        self.assertEqual([len(item) for item in outcomes], [0, 0, 0, 0, 1], "one frame is not enough, and two in a row are")
        report = server.told[0]
        self.assertEqual((report["camera_id"], report["severity"], report["radar_tracks"], report["profile"]), ("cam-gate", "high", 1, "daylight"))
        self.assertIn("radar track(s) agree", " ".join(report["reasons"]))

    def test_the_cooldown_stops_it_from_telling_the_same_thing_every_few_seconds(self):
        server = Server(tracks=1, lux=200.0)
        server.frames["cam-gate"] = [frame(100)] + [frame(100, moved=400) if index % 2 else frame(100) for index in range(1, 14)]
        now = [0.0]
        watcher = Watcher(server, confirm_frames=1, cooldown_s=60.0, clock=lambda: now[0])
        for _ in range(14):
            watcher.run_once()
            now[0] += 3
        self.assertEqual(len(server.told), 1)

    def test_nothing_is_looked_at_while_the_system_is_disarmed_and_a_light_switching_on_is_not_movement(self):
        disarmed = Server(mode="disarmed")
        self.assertEqual(Watcher(disarmed).run_once(), [])
        self.assertEqual(disarmed.frames["cam-gate"], [])   # no frame was even asked for
        lit = Server(tracks=2)
        lit.frames["cam-gate"] = [frame(20), frame(200), frame(20), frame(200)]
        watcher = Watcher(lit, confirm_frames=1, cooldown_s=0.0)
        for _ in range(4):
            watcher.run_once()
        self.assertEqual(lit.told, [])
        self.assertEqual(changed_ratio(frame(20), frame(200)), 0.0, "the whole picture changing by the same amount is a light, not movement")
        # a change of the light with a real movement in it: only the movement counts
        self.assertEqual(changed_ratio(frame(100), frame(160, moved=230, to=255)), 230 / FRAME_BYTES)

    def test_the_radar_and_the_light_that_count_are_those_of_the_nodes_that_cover_the_camera(self):
        server = Server(tracks=0, lux=200.0, cameras=("cam-a",))
        base = server.context
        server.context = lambda: {**base(), "nodes": [{"id": "north", "online": True, "targets": 0, "lux": 200.0}, {"id": "south", "online": True, "targets": 3, "lux": 5.0}],
                                  "cameras": [{"id": "cam-a", "nodes": ["north"]}]}
        server.frames["cam-a"] = [frame(100), frame(100, moved=230)]
        watcher = Watcher(server, confirm_frames=1, cooldown_s=0.0)
        watcher.run_once()
        watcher.run_once()
        self.assertEqual([(item["radar_tracks"], item["profile"]) for item in server.told], [(0, "daylight")], "the 3 targets of the other side of the house are not this camera's")

    def test_a_camera_that_does_not_answer_is_skipped_and_the_others_go_on(self):
        server = Server(tracks=1, lux=200.0, cameras=("cam-a", "cam-b"))
        server.failing = {"cam-a"}
        server.frames["cam-b"] = [frame(100), frame(100, moved=400)]
        watcher = Watcher(server, confirm_frames=1, cooldown_s=0.0)
        watcher.run_once()
        watcher.run_once()
        self.assertEqual([item["camera_id"] for item in server.told], ["cam-b"])

    def test_an_observation_the_server_never_got_does_not_silence_the_camera(self):
        server = Server(tracks=1, lux=200.0)
        server.frames["cam-gate"] = [frame(100), frame(100, moved=400), frame(100), frame(100, moved=400)]
        refuse = [True]
        original = server.observe

        def observe(report):
            if refuse[0]:
                refuse[0] = False
                raise ServerError(0, "unreachable")
            return original(report)
        server.observe = observe
        clock = iter(range(0, 1000, 5))
        watcher = Watcher(server, confirm_frames=1, cooldown_s=60.0, clock=lambda: next(clock))
        for _ in range(4):
            watcher.run_once()
        self.assertEqual(len(server.told), 1, "the second movement is told at once: the first never arrived, so there is no cooldown to wait for")

    def test_a_camera_that_fails_keeps_its_cooldown_and_odd_data_does_not_end_the_pass(self):
        server = Server(tracks=1, lux=200.0, cameras=("cam-a", "cam-b"))
        server.frames["cam-a"] = [frame(100), frame(100, moved=400)]
        server.frames["cam-b"] = [frame(100), frame(100, moved=400)]
        base = server.context
        server.context = lambda: {**base(), "nodes": [{"id": "radar", "online": True, "targets": [{}, {}]}, "not a node", {"id": "x", "online": True, "targets": "many"}]}
        watcher = Watcher(server, confirm_frames=1, cooldown_s=0.0)
        watcher.run_once()
        watcher.run_once()
        self.assertEqual(sorted(item["camera_id"] for item in server.told), ["cam-a", "cam-b"])
        self.assertEqual(server.told[0]["radar_tracks"], 2, "a list of targets counts its members")
        self.assertEqual(watcher.camera_count, 2)

    def test_the_server_address_is_checked_and_the_pass_is_spaced_for_many_cameras(self):
        from armor_server_ai.service import check_server_url, min_interval_s
        self.assertEqual(check_server_url("http://127.0.0.1:18080"), "http://127.0.0.1:18080")
        self.assertEqual(check_server_url("https://armor.example:18080"), "https://armor.example:18080")
        for bad in ("http://192.168.0.180:18080", "file:///etc/passwd", "ftp://127.0.0.1"):
            with self.assertRaises(SystemExit):
                check_server_url(bad)
        self.assertGreater(min_interval_s(60), 3.0)
        self.assertLess(min_interval_s(5), 3.0)

    def test_the_first_frame_after_being_armed_has_nothing_old_to_be_compared_with(self):
        server = Server(tracks=1, lux=200.0)
        server.frames["cam-gate"] = [frame(100, moved=400)]
        self.assertIsNone(look(CameraState(), "cam-gate", server.frames["cam-gate"][0], 0.0, 1, 200.0, 1, 0.0))
        with self.assertRaises(ValueError):
            Watcher(server, confirm_frames=0)


if __name__ == "__main__":
    unittest.main()
