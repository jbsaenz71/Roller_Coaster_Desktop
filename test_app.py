import tkinter as tk
import unittest
import tempfile
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path

from app import RollerCoasterApp
from coaster_physics import PRESETS, first_load_failure
from coaster_storage import load_track


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
        expected_height = min(620, max(480, root.winfo_screenheight() - 160))
        self.assertEqual(root.minsize(), (760, expected_height))
        self.assertEqual(root.winfo_height(), expected_height)
        window_bottom = root.winfo_rooty() + root.winfo_height()
        self.assertLessEqual(
            window_bottom,
            root.winfo_screenheight() - 20,
        )
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
        for canvas in (app.speed_canvas, app.load_canvas):
            self.assertLessEqual(
                canvas.winfo_rooty() + canvas.winfo_height(),
                window_bottom,
            )
        axis_title = app.track_canvas.find_withtag("axis-title")[0]
        self.assertEqual(app.track_canvas.itemcget(axis_title, "angle"), "90.0")
        title_bounds = app.track_canvas.bbox(axis_title)
        top_tick = next(
            item
            for item in app.track_canvas.find_withtag("axis-label")
            if app.track_canvas.itemcget(item, "text") == "60"
        )
        tick_bounds = app.track_canvas.bbox(top_tick)
        self.assertGreater(title_bounds[1], tick_bounds[3])

        root.geometry(f"760x{expected_height}")
        root.update()
        app.render()
        root.update()
        self.assertGreater(app.track_canvas.winfo_width(), 0)
        self.assertGreater(app.track_canvas.winfo_height(), 0)
        self.assertGreater(app.speed_canvas.winfo_width(), 0)
        self.assertGreater(app.load_canvas.winfo_width(), 0)

    def test_plot_titles_are_outside_equal_height_canvases(self):
        root, app = self.create_app()
        editor_plot_ratio = (
            app.track_canvas.winfo_height() / app.speed_canvas.winfo_height()
        )
        self.assertGreaterEqual(editor_plot_ratio, 1.8)
        self.assertLessEqual(editor_plot_ratio, 2.5)

        root.geometry(f"760x{app.window_height}")
        root.update()
        app.render()
        root.update()

        self.assertEqual(app.speed_plot_title.cget("text"), "Speed (mph)")
        self.assertEqual(app.load_plot_title.cget("text"), "Rider load (g)")
        self.assertEqual(app.plot_layout, "side-by-side")
        self.assertGreaterEqual(app.speed_canvas.winfo_height(), 90)
        self.assertGreaterEqual(app.load_canvas.winfo_height(), 90)
        self.assertLessEqual(
            abs(app.speed_canvas.winfo_height() - app.load_canvas.winfo_height()),
            1,
        )
        window_bottom = root.winfo_rooty() + root.winfo_height()
        self.assertLessEqual(
            app.load_canvas.winfo_rooty() + app.load_canvas.winfo_height(),
            window_bottom,
        )
        self.assertLessEqual(
            app.valley_label.winfo_rooty() + app.valley_label.winfo_height(),
            window_bottom,
        )
        for canvas in (app.speed_canvas, app.load_canvas):
            canvas_text = [
                canvas.itemcget(item, "text")
                for item in canvas.find_all()
                if canvas.type(item) == "text"
            ]
            self.assertNotIn("Speed (mph)", canvas_text)
            self.assertNotIn("Rider load (g)", canvas_text)
            for item in canvas.find_all():
                if canvas.type(item) != "text":
                    continue
                bounds = canvas.bbox(item)
                self.assertGreaterEqual(bounds[0], 0)
                self.assertGreaterEqual(bounds[1], 0)
                self.assertLessEqual(bounds[2], canvas.winfo_width())
                self.assertLessEqual(bounds[3], canvas.winfo_height())

        app.update_plot_layout(SimpleNamespace(width=600))
        self.assertEqual(app.plot_layout, "stacked")
        self.assertEqual(int(app.speed_plot_frame.grid_info()["row"]), 1)
        self.assertEqual(int(app.load_plot_frame.grid_info()["row"]), 2)

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

    def test_plot_y_tick_labels_adapt_to_short_canvas(self):
        root, app = self.create_app()

        with patch.object(app.speed_canvas, "winfo_height", return_value=60):
            app.draw_plot(
                app.speed_canvas,
                "speed_mph",
                lambda values: (0, 40),
            )

        tick_labels = app.speed_canvas.find_withtag("y-tick-label")
        self.assertEqual(len(tick_labels), 2)
        bounds = sorted(app.speed_canvas.bbox(item) for item in tick_labels)
        self.assertGreaterEqual(bounds[1][1], bounds[0][3])

    def test_orbit_rider_is_drawn_and_moves_with_car(self):
        root, app = self.create_app()
        start_head = app.track_canvas.bbox("rider-head")
        start_car = app.track_canvas.bbox("car")
        self.assertIsNotNone(start_head)
        self.assertIsNotNone(start_car)
        self.assertGreater(len(app.track_canvas.find_withtag("rider")), 0)

        app.position = app.profile["samples"][120]
        app.render()
        moved_head = app.track_canvas.bbox("rider-head")
        car = app.track_canvas.bbox("car")

        self.assertIsNotNone(moved_head)
        self.assertIsNotNone(car)
        self.assertGreater(moved_head[0], start_head[0])
        self.assertAlmostEqual(
            (moved_head[0] + moved_head[2]) / 2,
            (car[0] + car[2]) / 2,
        )
        self.assertAlmostEqual(
            (moved_head[1] + moved_head[3] - start_head[1] - start_head[3]) / 2,
            (car[1] + car[3] - start_car[1] - start_car[3]) / 2,
        )
        self.assertGreater(len(app.track_canvas.find_withtag("rider-antenna")), 0)
        self.assertGreater(len(app.track_canvas.find_withtag("rider-visor")), 0)

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
            self.assertGreater(len(app.track_canvas.find_withtag("rider")), 0)

            callbacks.pop(0)()
            clock[0] += 0.25
            callbacks.pop(0)()
            self.assertGreater(app.position.offset, 0)
            self.assertGreater(app.position.speed_mph, 0)
            self.assertGreater(len(app.track_canvas.find_withtag("rider")), 0)

            clock[0] = 100.0 + stop_time + 0.1
            callbacks.pop(0)()

        self.assertEqual(str(app.ride_button.cget("state")), "normal")
        self.assertIsNone(app.animation_id)
        self.assertGreater(len(app.track_canvas.find_withtag("rider")), 0)
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

    def test_file_menu_has_file_actions_and_keyboard_shortcuts(self):
        root, app = self.create_app()

        labels = [
            app.file_menu.entrycget(index, "label")
            for index in range(app.file_menu.index("end") + 1)
            if app.file_menu.type(index) != "separator"
        ]
        self.assertEqual(labels, ["New", "Open...", "Save", "Save As...", "Exit"])
        for sequence in (
            "<Control-n>",
            "<Control-o>",
            "<Control-s>",
            "<Control-Shift-s>",
        ):
            with self.subTest(shortcut=sequence):
                self.assertTrue(root.tk.call("bind", "all", sequence))

    def test_save_as_and_open_restore_custom_track_and_reset_ride(self):
        root, app = self.create_app()
        app.add_point()
        expected_points = [list(point) for point in app.points]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "custom.json"
            with patch("app.filedialog.asksaveasfilename", return_value=str(path)):
                self.assertTrue(app.save_as())

            self.assertTrue(path.exists())
            self.assertFalse(app.dirty)
            self.assertIn("custom.json", root.title())

            app.preset.set("Rollback hill")
            app.preset_changed()
            app.failure = app.profile["samples"][-1]
            with patch("app.messagebox.askyesnocancel", return_value=False), patch(
                "app.filedialog.askopenfilename", return_value=str(path)
            ):
                app.open_track()

        self.assertEqual(app.preset.get(), "Custom")
        self.assertEqual(app.points, expected_points)
        self.assertIsNone(app.failure)
        self.assertEqual(app.position.offset, 0.0)
        self.assertFalse(app.dirty)
        self.assertIn("Opened custom.json", app.status_label.cget("text"))

    def test_save_updates_current_file_after_track_edit(self):
        root, app = self.create_app()
        app.add_point()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "track.json"
            with patch("app.filedialog.asksaveasfilename", return_value=str(path)):
                self.assertTrue(app.save_as())

            app.points[1][1] += 0.5
            expected_points = [tuple(point) for point in app.points]
            app.mark_dirty()
            self.assertTrue(app.save_current())

            preset, saved_points = load_track(path)

        self.assertEqual(preset, "Custom")
        self.assertEqual(saved_points, expected_points)
        self.assertFalse(app.dirty)
        self.assertIn("track.json", root.title())

    def test_new_resets_to_starter_and_clears_active_file(self):
        root, app = self.create_app()
        app.add_point()
        app.current_file = "previous.json"
        app.update_window_title()

        with patch("app.messagebox.askyesnocancel", return_value=False):
            app.new_track()

        self.assertEqual(app.points, [list(point) for point in PRESETS["Starter"]])
        self.assertEqual(app.preset.get(), "Starter")
        self.assertIsNone(app.current_file)
        self.assertFalse(app.dirty)
        self.assertEqual(root.title(), "Roller Coaster Designer")

    def test_cancelled_open_leaves_track_unchanged(self):
        root, app = self.create_app()
        app.add_point()
        expected_points = [list(point) for point in app.points]

        with patch("app.messagebox.askyesnocancel", return_value=False), patch(
            "app.filedialog.askopenfilename", return_value=""
        ):
            app.open_track()

        self.assertEqual(app.points, expected_points)
        self.assertTrue(app.dirty)

    def test_save_error_is_reported_and_leaves_track_dirty(self):
        root, app = self.create_app()
        app.add_point()
        app.current_file = "track.json"

        with patch("app.save_track", side_effect=OSError("disk unavailable")), patch(
            "app.messagebox.showerror"
        ) as show_error:
            self.assertFalse(app.save_current())

        self.assertTrue(app.dirty)
        show_error.assert_called_once()

    def test_cancelled_save_as_leaves_track_unsaved_and_unchanged(self):
        root, app = self.create_app()
        app.add_point()
        expected_points = [list(point) for point in app.points]

        with patch("app.filedialog.asksaveasfilename", return_value=""):
            self.assertFalse(app.save_as())

        self.assertEqual(app.points, expected_points)
        self.assertTrue(app.dirty)
        self.assertIsNone(app.current_file)

    def test_malformed_open_reports_error_without_changing_track(self):
        root, app = self.create_app()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            expected_points = [list(point) for point in app.points]

            with patch("app.filedialog.askopenfilename", return_value=str(path)), patch(
                "app.messagebox.showerror"
            ) as show_error:
                app.open_track()

        self.assertEqual(app.points, expected_points)
        self.assertIsNone(app.current_file)
        self.assertFalse(app.dirty)
        show_error.assert_called_once()

    def test_cancel_unsaved_changes_keeps_track_when_creating_new(self):
        root, app = self.create_app()
        app.add_point()
        expected_points = [list(point) for point in app.points]

        with patch("app.messagebox.askyesnocancel", return_value=None):
            app.new_track()

        self.assertEqual(app.points, expected_points)
        self.assertTrue(app.dirty)
        self.assertEqual(app.preset.get(), "Custom")


if __name__ == "__main__":
    unittest.main()
