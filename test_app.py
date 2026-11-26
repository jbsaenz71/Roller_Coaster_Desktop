import tkinter as tk
import unittest

from app import RollerCoasterApp


class RollerCoasterAppTests(unittest.TestCase):
    def test_app_builds_and_starts_on_starter_preset(self):
        root = tk.Tk()
        root.withdraw()
        app = RollerCoasterApp(root)
        self.assertEqual(app.preset.get(), "Starter")
        self.assertEqual(len(app.points), 3)
        self.assertEqual(app.profile["outcome"], "complete")
        root.update()
        root.destroy()


if __name__ == "__main__":
    unittest.main()
