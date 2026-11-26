import json
import tempfile
import unittest
from pathlib import Path

from coaster_physics import PRESETS
from coaster_storage import SCHEMA_VERSION, TrackFileError, load_track, save_track


class CoasterStorageTests(unittest.TestCase):
    def test_preset_track_round_trips_with_versioned_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "starter.json"
            save_track(path, PRESETS["Starter"], "Starter")

            preset, points = load_track(path)
            document = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(document["schema_version"], SCHEMA_VERSION)
        self.assertEqual(preset, "Starter")
        self.assertEqual(points, [(0.0, 10.0), (20.0, 0.0), (30.0, 2.5)])

    def test_custom_four_point_track_round_trips(self):
        custom = [(0, 10), (10, 4), (20, 1), (30, 2)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.json"
            save_track(path, custom, "Custom")

            preset, points = load_track(path)

        self.assertEqual(preset, "Custom")
        self.assertEqual(points, [(0.0, 10.0), (10.0, 4.0), (20.0, 1.0), (30.0, 2.0)])

    def test_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "malformed.json"
            path.write_text("{", encoding="utf-8")

            with self.assertRaisesRegex(TrackFileError, "not valid JSON"):
                load_track(path)

    def test_unsupported_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "future.json"
            path.write_text(
                json.dumps({
                    "schema_version": SCHEMA_VERSION + 1,
                    "preset": "Starter",
                    "points": PRESETS["Starter"],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TrackFileError, "Unsupported track file version"):
                load_track(path)

    def test_out_of_bounds_points_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "out-of-bounds.json"
            path.write_text(
                json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "preset": "Custom",
                    "points": [[0, 10], [20, 0], [201, 2]],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TrackFileError, "outside the track bounds"):
                load_track(path)

    def test_points_must_match_named_preset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mismatched.json"
            path.write_text(
                json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "preset": "Starter",
                    "points": [[0, 10], [20, 0], [31, 2.5]],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TrackFileError, "do not match"):
                load_track(path)

    def test_duplicate_or_unsorted_points_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unordered.json"
            path.write_text(
                json.dumps({
                    "schema_version": SCHEMA_VERSION,
                    "preset": "Custom",
                    "points": [[0, 10], [20, 0], [19.5, 2]],
                }),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TrackFileError, "at least 1 m spacing"):
                load_track(path)


if __name__ == "__main__":
    unittest.main()
