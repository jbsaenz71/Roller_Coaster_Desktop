import tkinter as tk
import unittest
from types import SimpleNamespace

from app import RollerCoasterApp
from coaster_physics import PRESETS


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


if __name__ == "__main__":
    unittest.main()
