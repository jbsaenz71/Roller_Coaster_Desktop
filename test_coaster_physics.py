import unittest

from coaster_physics import (
    PRESETS,
    calculate_profile,
    first_load_failure,
)


class CoasterPhysicsTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
