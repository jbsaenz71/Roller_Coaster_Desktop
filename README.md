# Roller Coaster Designer

Roller Coaster Designer is a desktop app for shaping a 2D coaster track and exploring how the car's speed and rider load change during a ride.

## Start the app

1. Install Python 3 with Tkinter available.
2. Open a terminal in the project folder.
3. Run:

   ```powershell
   py app.py
   ```

   If `py` is not available, run `python app.py` instead.

## Shape a track

- Choose a track from the **Track preset** list. The app opens with **Starter** selected. Choosing a preset replaces the current track and resets the ride.
- The presets demonstrate different outcomes: **Starter** is the basic ride, **Rollback hill** demonstrates a rollback, **High-g valley** demonstrates the upper g-force limit, and **Low-g crest** demonstrates the lower limit.
- Drag a control point in the track editor to change its position. The horizontal axis is distance from 0 to 200 m; the vertical axis is height from 0 to 60 m. Points stay in left-to-right order with at least 1 m between them, and the starting point stays higher than the next point.
- Select **Add fourth point** to add another editable point to the curve. Tracks support up to four points.
- Editing the track changes the selection to **Custom** and resets the ride. Choose a preset to return to a built-in track.

## Run a ride

- Select **Ride** to release the car from rest at the first point.
- Select **Reset** to return the car to the start and clear a failure marker.
- Read the live **Speed** in mph and **Rider load** in g beside the controls. The speed and load plots show how those values change with distance along the track; the moving indicator marks the car's current position.
- A ride stops if the rider load goes above 4 g or below -1 g, or if the car stalls at a crest. The app marks the failure and shows its reason and ride readings. If the car runs out of speed while climbing before the next crest, it rolls back to the start.
- A ride that reaches the end without a failure is marked complete.

## Save and reopen tracks

Use the **File** menu:

- **New** resets to the Starter track.
- **Open...** loads a saved `.json` track.
- **Save** saves to the current file. If the track has not been saved before, Save opens the Save As dialog.
- **Save As...** saves to a chosen file.
- **Exit** closes the app.

Keyboard shortcuts are **Ctrl+N** for New, **Ctrl+O** for Open, **Ctrl+S** for Save, and **Ctrl+Shift+S** for Save As. If you have unsaved edits, the app asks whether to save them before replacing a track or exiting. Choose **Save**, **Don't Save**, or **Cancel** as appropriate.

## What the simulation represents

The app models a two-dimensional track and ignores friction and air resistance. Its speed and rider-load readings are intended for learning and exploration; they are not a real-world ride-safety assessment.
