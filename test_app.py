import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import RollerCoasterApp
from coaster_physics import PRESETS, first_load_failure


class RollerCoasterAppTests(unittest.TestCase):
    def create_app(self):
        root = tk.Tk()
        root.geometry("1100x780")
        app = RollerCoasterApp(root)
        root.update()
        self.addCleanup(root.destroy)
        return root, app

    def test_stage1_desktop_shell_starts_on_starter_preset(self):
        root, app = self.create_app()

        self.assertEqual(root.title(), "Roller Coaster Designer")
        self.assertEqual(app.status_label.cget("text"), "Ready to ride")
        self.assertEqual(app.preset.get(), "Starter")
        self.assertEqual(len(app.points), 3)
        self.assertEqual(app.points, [[0, 10], [20, 0], [30, 2.5]])
        self.assertEqual(app.profile["outcome"], "complete")
        self.assertIsNotNone(app.profile["valley"])
        self.assertGreater(len(app.track_canvas.find_all()), 0)
        self.assertGreater(len(app.speed_canvas.find_all()), 0)
        self.assertGreater(len(app.load_canvas.find_all()), 0)
        self.assertGreater(len(app.track_canvas.find_withtag("grid")), 0)
        self.assertGreater(len(app.track_canvas.find_withtag("axis-label")), 0)

        root.geometry("760x620")
        root.update()
        app.render()
        root.update()
        self.assertGreater(app.track_canvas.winfo_width(), 0)
        self.assertGreater(app.track_canvas.winfo_height(), 0)
        self.assertGreater(app.speed_canvas.winfo_width(), 0)
        self.assertGreater(app.load_canvas.winfo_width(), 0)

    def test_dragging_control_point_obeys_track_constraints(self):
        root, app = self.create_app()
        left, right, top, bottom, x_map, y_map = app.track_mapping(app.track_canvas)
        app.pointer_down(SimpleNamespace(x=x_map(20), y=y_map(0)))
        self.assertEqual(app.drag_index, 1)

        app.pointer_move(SimpleNamespace(x=x_map(200), y=y_map(60)))

        self.assertEqual(app.preset.get(), "Custom")
        self.assertAlmostEqual(app.points[1][0], app.points[2][0] - 1)
        self.assertAlmostEqual(app.points[1][1], app.points[0][1] - 0.01)
        self.assertEqual(app.status_label.cget("text"), "Ready to ride")
        self.assertIsNone(app.failure)
        app.pointer_up(SimpleNamespace())
        self.assertIsNone(app.drag_index)

    def test_adding_fourth_point_uses_widest_gap_and_existing_curve(self):
        root, app = self.create_app()

        app.add_point()

        self.assertEqual(len(app.points), 4)
        self.assertAlmostEqual(app.points[1][0], 10.0)
        self.assertAlmostEqual(app.points[1][1], 2.5)
        self.assertEqual(app.preset.get(), "Custom")
        self.assertEqual(str(app.add_point_button.cget("state")), "disabled")

    def test_preset_replaces_track_and_resets_ride(self):
        root, app = self.create_app()
        app.points[1] = [19.0, 1.0]
        app.preset.set("Custom")
        app.update_track()
        app.failure = app.profile["samples"][0]

        app.preset.set("Rollback hill")
        app.preset_changed()

        self.assertEqual(app.points, [list(point) for point in PRESETS["Rollback hill"]])
        self.assertEqual(app.status_label.cget("text"), "Ready to ride")
        self.assertIsNone(app.failure)
        self.assertEqual(app.position.offset, 0)

    def test_all_presets_have_matching_point_counts(self):
        root, app = self.create_app()
        for name, points in PRESETS.items():
            with self.subTest(preset=name):
                app.preset.set(name)
                app.preset_changed()
                self.assertEqual(app.points, [list(point) for point in points])
                self.assertEqual(len(app.points), len(points))

    def run_ride_to_completion(self, preset_name):
        root, app = self.create_app()
        app.preset.set(preset_name)
        app.preset_changed()

        callbacks = []
        app.root.after = lambda delay, callback: callbacks.append(callback) or len(callbacks)
        clock = [100.0]
        samples = app.profile["samples"]
        load_failure = first_load_failure(
            [tuple(point) for point in app.points],
            samples,
        )
        finish = samples[-1]
        stop_time = (
            load_failure[0].time
            if load_failure
            else (2 * finish.time if app.profile["outcome"] == "rollback" else finish.time)
        )

        with patch("app.time.monotonic", side_effect=lambda: clock[0]):
            app.start_ride()
            self.assertEqual(app.status_label.cget("text"), "Riding")
            self.assertEqual(str(app.ride_button.cget("state")), "disabled")

            callbacks.pop(0)()
            clock[0] += 0.25
            callbacks.pop(0)()
            self.assertGreater(app.position.offset, 0)
            self.assertGreater(app.position.speed_mph, 0)

            clock[0] = 100.0 + stop_time + 0.1
            callbacks.pop(0)()

        self.assertEqual(str(app.ride_button.cget("state")), "normal")
        self.assertIsNone(app.animation_id)
        return app

    def test_starter_ride_animates_and_completes(self):
        app = self.run_ride_to_completion("Starter")

        self.assertEqual(app.status_label.cget("text"), "Ride complete")
        self.assertIsNone(app.failure)
        self.assertAlmostEqual(app.position.offset, 30.0)

    def test_rollback_ride_keeps_turning_point_failure_marker(self):
        app = self.run_ride_to_completion("Rollback hill")

        self.assertEqual(app.status_label.cget("text"), "Rolled back to the start")
        self.assertIsNotNone(app.failure)
        self.assertAlmostEqual(app.failure.offset, 40.0, delta=0.1)
        self.assertAlmostEqual(app.failure.speed_mph, 0.0)
        self.assertAlmostEqual(app.position.offset, 0.0)
        self.assertIn("Car ran out of speed before the crest", app.failure_label.cget("text"))

    def test_high_g_ride_stops_at_four_g_crossing(self):
        app = self.run_ride_to_completion("High-g valley")

        self.assertEqual(app.status_label.cget("text"), "Ride stopped")
        self.assertIsNotNone(app.failure)
        self.assertAlmostEqual(app.failure.load, 4.0, delta=0.01)
        self.assertIn("Rider load crossed the 4 g limit", app.failure_label.cget("text"))

    def test_low_g_ride_stops_at_negative_one_g_crossing(self):
        app = self.run_ride_to_completion("Low-g crest")

        self.assertEqual(app.status_label.cget("text"), "Ride stopped")
        self.assertIsNotNone(app.failure)
        self.assertAlmostEqual(app.failure.offset, 24.17, delta=0.05)
        self.assertAlmostEqual(app.failure.load, -1.0, delta=0.01)
        self.assertIn("Rider load crossed the -1 g limit", app.failure_label.cget("text"))

    def test_reset_after_ride_clears_failure_and_returns_to_start(self):
        app = self.run_ride_to_completion("High-g valley")

        app.reset_ride()

        self.assertIsNone(app.failure)
        self.assertEqual(app.status_label.cget("text"), "Ready to ride")
        self.assertEqual(app.position.offset, 0.0)
        self.assertEqual(app.failure_label.cget("text"), "")


if __name__ == "__main__":
    unittest.main()
