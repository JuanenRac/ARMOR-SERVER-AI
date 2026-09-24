import io
import json
import sys
import unittest

sys.path.insert(0, "src")

from armor_server_ai import DAYLIGHT, LOW_LIGHT, Decision, ProfileSelector, VisualObservation, choose_profile, decide, event_severity
from armor_server_ai.cli import process, run


class StatelessProfileTests(unittest.TestCase):
    def test_boundary_is_daylight(self):
        self.assertEqual(choose_profile(30), "daylight")

    def test_darkness_is_low_light(self):
        self.assertEqual(choose_profile(0), "low-light")

    def test_bad_readings_are_refused(self):
        for bad in (-1, float("nan"), True, "5", None, 200_001):
            with self.assertRaises(ValueError, msg=repr(bad)):
                choose_profile(bad)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            choose_profile(5, threshold_lux=-1)


class HysteresisTests(unittest.TestCase):
    def test_it_does_not_flap_around_the_threshold(self):
        selector = ProfileSelector(low_lux=30, high_lux=60, min_dwell_s=0)
        seen = [selector.update(lux, t) for t, lux in enumerate([100, 40, 31, 29, 35, 45, 59, 61])]
        self.assertEqual(seen, [DAYLIGHT, DAYLIGHT, DAYLIGHT, LOW_LIGHT, LOW_LIGHT, LOW_LIGHT, LOW_LIGHT, DAYLIGHT])

    def test_a_change_needs_the_minimum_dwell_time(self):
        selector = ProfileSelector(min_dwell_s=30)
        self.assertEqual(selector.update(5, 0), LOW_LIGHT)
        self.assertEqual(selector.update(500, 10), LOW_LIGHT)      # too soon to change back
        self.assertEqual(selector.update(500, 31), DAYLIGHT)

    def test_the_first_change_is_immediate(self):
        self.assertEqual(ProfileSelector(min_dwell_s=600).update(0, 0), LOW_LIGHT)

    def test_invalid_settings_are_refused(self):
        for kwargs in ({"low_lux": 60, "high_lux": 30}, {"low_lux": -1}, {"min_dwell_s": -1}, {"profile": "dusk"}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                ProfileSelector(**kwargs)

    def test_a_bad_reading_does_not_change_the_profile(self):
        selector = ProfileSelector()
        with self.assertRaises(ValueError):
            selector.update(float("nan"), 0)
        self.assertEqual(selector.profile, DAYLIGHT)


class PolicyTests(unittest.TestCase):
    def test_correlated_person_is_high(self):
        self.assertEqual(event_severity(VisualObservation("person", .9, 4), 1), "high")

    def test_a_person_without_radar_is_only_a_review(self):
        self.assertEqual(event_severity(VisualObservation("person", .9, 4), 0), "review")

    def test_radar_alone_is_a_review_and_nothing_at_all_is_ignored(self):
        self.assertEqual(event_severity(VisualObservation("unknown", .1, 4), 2), "review")
        self.assertEqual(event_severity(VisualObservation("unknown", .1, 4), 0), "ignore")

    def test_low_light_lowers_only_the_review_bar(self):
        self.assertEqual(event_severity(VisualObservation("vehicle", .50, 2, profile="daylight"), 0), "ignore")
        self.assertEqual(event_severity(VisualObservation("vehicle", .50, 2, profile="low-light"), 0), "review")
        self.assertEqual(event_severity(VisualObservation("person", .70, 2, profile="low-light"), 1), "review")  # never "high" below 80 %

    def test_an_old_detection_never_raises_an_alert(self):
        decision = decide(VisualObservation("person", .99, 4, age_s=30), 3)
        self.assertEqual(decision.severity, "ignore")
        self.assertIn("old", decision.reasons[0])

    def test_every_decision_explains_itself_and_authorizes_nothing(self):
        for observation, tracks in [(VisualObservation("person", .9, 4), 1), (VisualObservation("animal", .6, 4), 0), (VisualObservation("animal", .1, 4), 0)]:
            decision = decide(observation, tracks)
            self.assertIsInstance(decision, Decision)
            self.assertTrue(decision.reasons)
            self.assertFalse(decision.authorizes_action)

    def test_invalid_observations_are_refused(self):
        bad = [VisualObservation("cat", .5, 1), VisualObservation("person", 1.5, 1), VisualObservation("person", -.1, 1),
               VisualObservation("person", .5, -1), VisualObservation("person", .5, 1, age_s=-1), VisualObservation("person", float("nan"), 1),
               VisualObservation("person", True, 1), VisualObservation("person", .5, 1, profile="dusk")]
        for observation in bad:
            with self.assertRaises(ValueError, msg=repr(observation)):
                decide(observation, 0)
        for tracks in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                decide(VisualObservation("person", .5, 1), tracks)  # type: ignore[arg-type]


class WorkerTests(unittest.TestCase):
    def results(self, *lines, tracks=0):
        return list(process(lines, tracks, ProfileSelector(min_dwell_s=0)))

    def test_each_line_gets_a_numbered_explained_recommendation(self):
        [result] = self.results('{"label":"person","confidence":0.9,"lux":4,"radar_tracks":2}')
        self.assertEqual((result["line"], result["severity"], result["profile"], result["authorizes_action"]), (1, "high", "low-light", False))
        self.assertTrue(result["reasons"])

    def test_the_profile_follows_the_light_across_lines(self):
        profiles = [r["profile"] for r in self.results(*(json.dumps({"label": "unknown", "confidence": 0.1, "lux": lux}) for lux in (500, 5, 5, 500)))]
        self.assertEqual(profiles, ["daylight", "low-light", "low-light", "daylight"])

    def test_a_bad_line_reports_its_number_and_the_worker_carries_on(self):
        results = self.results("not json", '{"label":"person"}', "[1]", '{"label":"cat","confidence":0.5,"lux":1}', '{"label":"person","confidence":0.9,"lux":4}', tracks=1)
        self.assertEqual([("error" in r) for r in results], [True, True, True, True, False])
        self.assertEqual([r["line"] for r in results], [1, 2, 3, 4, 5])
        self.assertIn("missing field", results[1]["error"])

    def test_blank_lines_are_skipped_and_huge_lines_refused(self):
        self.assertEqual(self.results("", "  \n"), [])
        [result] = self.results('{"label":"' + "x" * 5000 + '"}')
        self.assertIn("longer than", result["error"])

    def test_run_writes_json_lines(self):
        out = io.StringIO()
        run(io.StringIO('{"label":"animal","confidence":0.6,"lux":100}\n'), out, 0)
        self.assertEqual(json.loads(out.getvalue())["severity"], "review")


if __name__ == "__main__":
    unittest.main()
