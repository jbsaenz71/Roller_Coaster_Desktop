import tkinter as tk
import unittest

from app import RollerCoasterApp


class RollerCoasterAppTests(unittest.TestCase):
    def test_stage1_desktop_shell_starts_on_starter_preset(self):
        root = tk.Tk()
        root.geometry("1100x780")
        app = RollerCoasterApp(root)
        root.update()

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

        root.geometry("760x620")
        root.update()
        app.render()
        root.update()
        self.assertGreater(app.track_canvas.winfo_width(), 0)
        self.assertGreater(app.track_canvas.winfo_height(), 0)
        self.assertGreater(app.speed_canvas.winfo_width(), 0)
        self.assertGreater(app.load_canvas.winfo_width(), 0)
        root.destroy()


if __name__ == "__main__":
    unittest.main()
