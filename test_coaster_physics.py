import unittest

from coaster_physics import (
    PRESETS,
    calculate_profile,
    first_load_failure,
    segment_height,
    track_segments,
    track_slopes,
)


class CoasterPhysicsTests(unittest.TestCase):
    def test_starter_control_points_reproduce_specified_parabola(self):
        points = PRESETS["Starter"]
        segments = track_segments(points)

        slopes = track_slopes(points)
        self.assertAlmostEqual(slopes[1], 0.0, delta=1e-9)

        for segment in segments:
            for fraction in (0.0, 0.25, 0.5, 0.75, 1.0):
                u = segment["width"] * fraction
                x = segment["x0"] + u
                height = segment_height(segment, u)
                self.assertAlmostEqual(height, (x - 20.0) ** 2 / 40.0, delta=1e-9)

    def test_starter_valley_matches_hand_calculation(self):
        samples, outcome, valley = calculate_profile(PRESETS["Starter"])
        self.assertEqual(outcome, "complete")
        self.assertIsNotNone(valley)
        self.assertAlmostEqual(valley.speed_mph, 31.3261, delta=0.2)
        self.assertAlmostEqual(valley.load, 2.0, delta=0.01)

    def test_rollback_stops_at_start_height(self):
        samples, outcome, valley = calculate_profile(PRESETS["Rollback hill"])
        self.assertEqual(outcome, "rollback")
        turning_point = samples[-1]
        self.assertAlmostEqual(turning_point.offset, 40.0, delta=0.1)
        self.assertEqual(turning_point.speed_mph, 0.0)

    def test_high_g_stops_before_valley(self):
        samples, outcome, valley = calculate_profile(PRESETS["High-g valley"])
        failure = first_load_failure(PRESETS["High-g valley"], samples)
        self.assertIsNotNone(failure)
        reading, limit = failure
        self.assertEqual(limit, 4.0)
        self.assertLess(reading.offset, 10.0)
        self.assertAlmostEqual(reading.load, 4.0, delta=0.01)

    def test_low_g_crest_crosses_at_negative_one_g(self):
        samples, outcome, valley = calculate_profile(PRESETS["Low-g crest"])
        failure = first_load_failure(PRESETS["Low-g crest"], samples)
        self.assertIsNotNone(failure)
        reading, limit = failure
        self.assertEqual(limit, -1.0)
        self.assertGreater(reading.offset, 20.0)
        self.assertAlmostEqual(reading.load, -1.0, delta=0.05)

    def test_reachable_segment_is_empty_for_uphill_start(self):
        samples, outcome, valley = calculate_profile([(0, 1), (20, 10), (30, 12)])
        self.assertEqual(outcome, "stall")

    def test_preset_transition_values_match_specification(self):
        rollback_samples, rollback_outcome, _ = calculate_profile(
            PRESETS["Rollback hill"]
        )
        rollback_turn = rollback_samples[-1]
        self.assertEqual(rollback_outcome, "rollback")
        self.assertAlmostEqual(rollback_turn.offset, 40.0, delta=0.1)
        self.assertAlmostEqual(rollback_turn.height, 10.0, delta=0.01)
        self.assertEqual(rollback_turn.speed_mph, 0.0)

        low_samples, _, _ = calculate_profile(PRESETS["Low-g crest"])
        low_failure, low_limit = first_load_failure(
            PRESETS["Low-g crest"],
            low_samples,
        )
        self.assertIsNotNone(low_failure)
        self.assertEqual(low_limit, -1.0)
        self.assertAlmostEqual(low_failure.offset, 24.17, delta=0.05)
        self.assertAlmostEqual(low_failure.distance, 26.42, delta=0.05)
        self.assertAlmostEqual(low_failure.speed_mph, 26.33, delta=0.2)
        self.assertAlmostEqual(low_failure.load, -1.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
