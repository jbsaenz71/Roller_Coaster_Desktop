import tkinter as tk
from tkinter import ttk
from typing import Optional
import time

from coaster_physics import (
    G,
    PRESETS,
    Point,
    calculate_profile,
    clamp,
    first_load_failure,
    reading_at,
    track_segments,
)


class RollerCoasterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Roller Coaster Designer")
        self.root.geometry("1100x780")
        self.root.minsize(760, 620)
        self.root.configure(bg="#101827")

        self.points = [list(point) for point in PRESETS["Starter"]]
        self.drag_index: Optional[int] = None
        self.profile = None
        self.position = None
        self.failure = None
        self.animation_id = None

        self.configure_styles()
        self.build_ui()
        self.update_track()

    def configure_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background="#182439", foreground="#f3f6fc", font=("Segoe UI", 10))
        style.configure("TFrame", background="#182439")
        style.configure("TLabel", background="#182439", foreground="#bfcde2")
        style.configure("Title.TLabel", font=("Segoe UI", 11, "bold"), foreground="#f3f6fc")
        style.configure("Readout.TLabel", font=("Segoe UI", 16, "bold"), foreground="#f3f6fc")
        style.configure("TButton", padding=8)
        style.map("TButton", background=[("active", "#34455f")])
        style.configure("TCombobox", fieldbackground="#263750", background="#263750",
                        foreground="#f3f6fc", padding=5)

    def build_ui(self):
        outer = ttk.Frame(self.root, padding=20)
        outer.pack(fill="both", expand=True)

        title = tk.Label(outer, text="Roller Coaster Designer", bg="#101827",
                         fg="#f3f6fc", font=("Segoe UI", 24, "bold"))
        title.pack(anchor="w")
        subtitle = tk.Label(outer, text="Drag the control points to shape the track.",
                            bg="#101827", fg="#bfcde2", font=("Segoe UI", 10))
        subtitle.pack(anchor="w", pady=(0, 12))

        layout = ttk.Frame(outer)
        layout.pack(fill="both", expand=True)
        layout.columnconfigure(0, weight=3)
        layout.columnconfigure(1, weight=1)
        layout.rowconfigure(0, weight=3)
        layout.rowconfigure(1, weight=2)

        editor = ttk.Frame(layout, padding=12)
        editor.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=(0, 8))
        ttk.Label(editor, text="Track editor", style="Title.TLabel").pack(anchor="w")
        self.track_canvas = tk.Canvas(
            editor, height=350, bg="#111c2e", highlightthickness=1,
            highlightbackground="#34455f", cursor="hand2"
        )
        self.track_canvas.pack(fill="both", expand=True, pady=(8, 8))
        self.track_canvas.bind("<Configure>", lambda event: self.render())
        self.track_canvas.bind("<Button-1>", self.pointer_down)
        self.track_canvas.bind("<B1-Motion>", self.pointer_move)
        self.track_canvas.bind("<ButtonRelease-1>", self.pointer_up)

        self.add_point_button = ttk.Button(editor, text="Add fourth point",
                                           command=self.add_point)
        self.add_point_button.pack(anchor="w")
        self.failure_label = tk.Label(
            editor, text="", fg="#ffb5b5", bg="#182439", justify="left",
            wraplength=650
        )
        self.failure_label.pack(anchor="w", pady=(8, 0))

        controls = ttk.Frame(layout, padding=12)
        controls.grid(row=0, column=1, sticky="nsew", pady=(0, 8))
        ttk.Label(controls, text="Ride controls", style="Title.TLabel").pack(anchor="w")
        ttk.Label(controls, text="Track preset").pack(anchor="w", pady=(12, 4))
        self.preset = tk.StringVar(value="Starter")
        preset_box = ttk.Combobox(
            controls, textvariable=self.preset, state="readonly",
            values=["Starter", "Rollback hill", "High-g valley", "Low-g crest", "Custom"]
        )
        preset_box.pack(fill="x")
        preset_box.bind("<<ComboboxSelected>>", self.preset_changed)

        button_row = ttk.Frame(controls)
        button_row.pack(fill="x", pady=(12, 8))
        self.ride_button = ttk.Button(button_row, text="Ride", command=self.start_ride)
        self.ride_button.pack(side="left", padx=(0, 6))
        ttk.Button(button_row, text="Reset", command=self.reset_ride).pack(side="left")

        self.status_label = ttk.Label(controls, text="Ready to ride")
        self.status_label.pack(anchor="w", pady=(8, 12))

        ttk.Label(controls, text="Speed").pack(anchor="w")
        self.speed_label = ttk.Label(controls, text="0.00 mph", style="Readout.TLabel")
        self.speed_label.pack(anchor="w", pady=(0, 12))
        ttk.Label(controls, text="Rider load").pack(anchor="w")
        self.load_label = ttk.Label(controls, text="0.00 g", style="Readout.TLabel")
        self.load_label.pack(anchor="w", pady=(0, 12))
        ttk.Label(controls, text="First valley").pack(anchor="w")
        self.valley_label = ttk.Label(controls, text="No reachable valley",
                                      style="Readout.TLabel")
        self.valley_label.pack(anchor="w")

        plots = ttk.Frame(layout, padding=12)
        plots.grid(row=1, column=0, columnspan=2, sticky="nsew")
        ttk.Label(plots, text="Track calculations", style="Title.TLabel").pack(anchor="w")

        self.speed_canvas = tk.Canvas(
            plots, height=145, bg="#111c2e", highlightthickness=1,
            highlightbackground="#34455f"
        )
        self.speed_canvas.pack(fill="both", expand=True, pady=(8, 4))
        self.load_canvas = tk.Canvas(
            plots, height=145, bg="#111c2e", highlightthickness=1,
            highlightbackground="#34455f"
        )
        self.load_canvas.pack(fill="both", expand=True)

    def track_mapping(self, canvas):
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        left, right = 45, width - 20
        top, bottom = 15, height - 35
        return (
            left,
            right,
            top,
            bottom,
            lambda x: left + (right - left) * x / 200,
            lambda h: bottom - (bottom - top) * h / 60,
        )

    def pointer_down(self, event):
        left, right, top, bottom, x_map, y_map = self.track_mapping(self.track_canvas)
        distances = [
            ((event.x - x_map(x)) ** 2 + (event.y - y_map(h)) ** 2) ** 0.5
            for x, h in self.points
        ]
        closest = min(distances)
        if closest <= 22:
            self.drag_index = distances.index(closest)

    def pointer_move(self, event):
        if self.drag_index is None:
            return
        left, right, top, bottom, x_map, y_map = self.track_mapping(self.track_canvas)
        index = self.drag_index
        x = (event.x - left) / (right - left) * 200
        y = (bottom - event.y) / (bottom - top) * 60
        min_x = 0 if index == 0 else self.points[index - 1][0] + 1
        max_x = 200 if index == len(self.points) - 1 else self.points[index + 1][0] - 1
        min_h = self.points[1][1] + 0.01 if index == 0 else 0
        max_h = self.points[0][1] - 0.01 if index == 1 else 60
        self.points[index] = [clamp(x, min_x, max_x), clamp(y, min_h, max_h)]
        self.preset.set("Custom")
        self.update_track()

    def pointer_up(self, event):
        self.drag_index = None

    def preset_changed(self, event=None):
        name = self.preset.get()
        if name == "Custom":
            return
        self.points = [list(point) for point in PRESETS[name]]
        self.update_track()

    def add_point(self):
        if len(self.points) >= 4:
            return
        segments = track_segments([tuple(point) for point in self.points])
        widest_index = 1 if segments[1]["width"] > segments[0]["width"] else 0
        segment = segments[widest_index]
        if segment["width"] < 2:
            return
        u = segment["width"] / 2
        from coaster_physics import segment_height
        height_limit = self.points[0][1] - 0.01 if widest_index == 0 else 60
        height = clamp(segment_height(segment, u), 0, height_limit)
        x = segment["x0"] + u
        self.points.insert(widest_index + 1, [x, height])
        self.preset.set("Custom")
        self.update_track()

    def update_track(self):
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        can_add = len(self.points) < 4 and all(
            self.points[i + 1][0] - self.points[i][0] >= 2
            for i in range(len(self.points) - 1)
        )
        self.add_point_button.configure(state="normal" if can_add else "disabled")
        point_tuples = [tuple(point) for point in self.points]
        samples, outcome, valley = calculate_profile(point_tuples)
        self.profile = {"samples": samples, "outcome": outcome, "valley": valley}
        self.reset_ride()

    def reset_ride(self):
        if self.animation_id is not None:
            self.root.after_cancel(self.animation_id)
            self.animation_id = None
        self.failure = None
        self.failure_label.configure(text="")
        if self.profile:
            self.position = self.profile["samples"][0]
        self.ride_button.configure(state="normal")
        self.status_label.configure(text="Ready to ride")
        self.render()

    def hermite_points(self):
        from coaster_physics import segment_height, segment_slope, track_segments
        segments = track_segments([tuple(point) for point in self.points])
        points = []
        left, right, top, bottom, x_map, y_map = self.track_mapping(self.track_canvas)
        for segment in segments:
            for i in range(21):
                u = segment["width"] * i / 20
                x = segment["x0"] + u
                height = segment_height(segment, u)
                points.extend((x_map(x), y_map(height)))
        return points

    def draw_track(self):
        canvas = self.track_canvas
        canvas.delete("all")
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        left, right, top, bottom, x_map, y_map = self.track_mapping(canvas)

        canvas.create_line(left, bottom, right, bottom, fill="#34455f")
        canvas.create_line(left, top, left, bottom, fill="#34455f")
        canvas.create_line(*self.hermite_points(), fill="#56e4df", width=4, smooth=False)

        for x, h in self.points:
            px, py = x_map(x), y_map(h)
            canvas.create_oval(px - 8, py - 8, px + 8, py + 8,
                               fill="#111c2e", outline="#56e4df", width=3)

        if self.position:
            px = x_map(self.position.offset)
            py = y_map(self.position.height)
            canvas.create_rectangle(px - 10, py - 16, px + 10, py - 5,
                                    fill="#ffbd74", outline="")
            canvas.create_oval(px - 7, py - 7, px - 3, py - 3,
                               fill="#f3f6fc", outline="")
            canvas.create_oval(px + 3, py - 7, px + 7, py - 3,
                               fill="#f3f6fc", outline="")

        if self.failure:
            px = x_map(self.failure.offset)
            py = y_map(self.failure.height)
            canvas.create_oval(px - 9, py - 9, px + 9, py + 9,
                               outline="#ff8f91", width=3)
            canvas.create_text(px + (12 if px < right - 80 else -12), py - 12,
                               text="Failure", anchor="w" if px < right - 80 else "e",
                               fill="#ffb5b5")

    def draw_plot(self, canvas, field, title, y_limits):
        canvas.delete("all")
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        left, right = 45, width - 20
        top, bottom = 15, height - 30
        samples = self.profile["samples"]
        distance_max = max(4.0, ((samples[-1].distance + 3.999) // 4) * 4)
        values = [getattr(sample, field) for sample in samples]
        y_min, y_max = y_limits(values)

        def x_map(distance):
            return left + (right - left) * distance / distance_max

        def y_map(value):
            return bottom - (bottom - top) * (value - y_min) / (y_max - y_min)

        canvas.create_text(left, 3, text=title, anchor="w", fill="#bfcde2")
        for i in range(5):
            value = y_min + (y_max - y_min) * i / 4
            y = y_map(value)
            canvas.create_line(left, y, right, y, fill="#34455f")
            canvas.create_text(left - 7, y, text=f"{value:.1f}", anchor="e",
                               fill="#bfcde2")
            distance = distance_max * i / 4
            x = x_map(distance)
            canvas.create_line(x, top, x, bottom, fill="#34455f")
            canvas.create_text(x, bottom + 12, text=f"{distance:.0f}",
                               anchor="n", fill="#bfcde2")

        coords = []
        for sample in samples:
            coords.extend((x_map(sample.distance), y_map(getattr(sample, field))))
        color = "#56e4df" if field == "speed_mph" else "#ffbd74"
        if len(coords) >= 4:
            canvas.create_line(*coords, fill=color, width=3)
        if self.position:
            px = x_map(self.position.distance)
            py = y_map(getattr(self.position, field))
            canvas.create_oval(px - 4, py - 4, px + 4, py + 4,
                               fill=color, outline="")

        if field == "load":
            for limit in (-1, 4):
                y = y_map(limit)
                canvas.create_line(left, y, right, y, fill="#ff8f91",
                                   dash=(5, 4))

    def render(self):
        self.draw_track()
        if not self.profile:
            return
        samples = self.profile["samples"]
        max_speed = max(1.0, max(sample.speed_mph for sample in samples))
        speed_max = ((max_speed + 4.999) // 5) * 5
        self.draw_plot(
            self.speed_canvas,
            "speed_mph",
            "Speed (mph)",
            lambda values: (0, max(5.0, speed_max)),
        )
        load_values = [sample.load for sample in samples]
        load_min = min(-1.0, min(load_values))
        load_max = max(4.0, max(load_values))
        padding = (load_max - load_min) / 20
        self.draw_plot(
            self.load_canvas,
            "load",
            "Rider load (g)",
            lambda values: (load_min - padding, load_max + padding),
        )
        if self.position:
            self.speed_label.configure(text=f"{self.position.speed_mph:.2f} mph")
            self.load_label.configure(text=f"{self.position.load:.2f} g")
        valley = self.profile["valley"]
        self.valley_label.configure(
            text=(
                f"{valley.speed_mph:.2f} mph · {valley.load:.2f} g"
                if valley
                else "No reachable valley"
            )
        )

    def mark_failure(self, reading, reason):
        self.failure = reading
        self.failure_label.configure(
            text=(
                f"{reason} · {reading.distance:.2f} m along track · "
                f"{reading.speed_mph:.2f} mph · {reading.load:.2f} g"
            )
        )

    def sample_at_time(self, elapsed):
        samples = self.profile["samples"]
        if elapsed <= 0:
            return samples[0]
        for i in range(1, len(samples)):
            before = samples[i - 1]
            after = samples[i]
            if after.time >= elapsed:
                span = after.time - before.time
                fraction = (elapsed - before.time) / span if span > 0 else 0
                segment = track_segments([tuple(point) for point in self.points])[after.segment]
                u = before.offset + (after.offset - before.offset) * fraction
                result = reading_at(
                    [tuple(point) for point in self.points],
                    segment,
                    u - segment["x0"],
                )
                result.distance = before.distance + (
                    after.distance - before.distance
                ) * fraction
                result.time = elapsed
                return result
        return samples[-1]

    def start_ride(self):
        self.reset_ride()
        samples = self.profile["samples"]
        outcome = self.profile["outcome"]
        if len(samples) == 1:
            self.mark_failure(samples[0], "Car stalled at the start")
            self.status_label.configure(text="Ride stopped")
            self.render()
            return

        point_tuples = [tuple(point) for point in self.points]
        load_failure = first_load_failure(point_tuples, samples)
        finish = samples[-1]
        rolls_back = outcome == "rollback" and load_failure is None
        stop_time = (
            load_failure[0].time
            if load_failure
            else (2 * finish.time if rolls_back else finish.time)
        )
        started = {"time": None}

        def advance():
            if started["time"] is None:
                started["time"] = time.monotonic()
            elapsed = time.monotonic() - started["time"]
            returning = rolls_back and elapsed >= finish.time
            if returning and self.failure is None:
                self.mark_failure(finish, "Car ran out of speed before the crest")
                self.status_label.configure(text="Rolling back")

            if elapsed >= stop_time:
                if load_failure:
                    self.position = load_failure[0]
                    reading, limit = load_failure
                    reason = f"Rider load crossed the {limit:g} g limit"
                    self.mark_failure(reading, reason)
                    self.status_label.configure(text="Ride stopped")
                elif rolls_back:
                    self.position = samples[0]
                    self.status_label.configure(text="Rolled back to the start")
                else:
                    self.position = finish
                    if outcome == "stall":
                        self.mark_failure(finish, "Car stalled at the crest")
                        self.status_label.configure(text="Ride stopped")
                    else:
                        self.status_label.configure(text="Ride complete")
                self.ride_button.configure(state="normal")
                self.animation_id = None
            else:
                travel_time = 2 * finish.time - elapsed if returning else elapsed
                self.position = self.sample_at_time(travel_time)
                self.animation_id = self.root.after(16, advance)
            self.render()

        self.ride_button.configure(state="disabled")
        self.status_label.configure(text="Riding")
        self.animation_id = self.root.after(16, advance)


def main():
    root = tk.Tk()
    app = RollerCoasterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
