# Purpose

A 2D roller coaster simulator for students. Shape a track, release a car from rest at the top of the first hill, and see how speed and rider g-force change during the ride.

# Platform

# Inputs

- Drag the control points on a side-view grid to shape the track. Point coordinates are horizontal distance (x) from 0 to 200 m and height (h) from 0 to 60 m. Keep the points in left-to-right order with at least 1 m between them. The first point starts the ride and must be higher than the second point.
- Start with three points at ((0,10)), ((20,0)), and ((30,2.5)), in meters.
- **Add fourth point** inserts an editable point halfway across the widest gap, provided the new point can stay at least 1 m from its neighbors. Its initial height comes from the existing curve, clamped to the same height limits as a dragged point.
- Add a **Track preset** dropdown next to the ride controls. **Starter** is selected on open. **Rollback hill** loads (0, 10), (20, 0), and (45, 15.625). **High-g valley** loads (0, 10), (10, 0), and (15, 2.5). All coordinates are (horizontal distance, height) in meters. Choosing a preset replaces the current track, parks the car at the start, and clears the previous failure marker.
- **Low-g crest** loads (0, 10), (20, 2), (25, 3), and (32, 1). The fourth point lets the curve form a crest below the starting height.
- **Ride** starts the car from rest. **Reset** returns the car to the start and clears any failure marker. Editing the track resets the ride.

# Calculations

- Connect the points with a piecewise cubic Hermite curve. At each control point, use the slope of the quadratic through that point and its two nearest neighbors in track order. At the ends, use the first or last three points. Position and slope are continuous. At a join, check the g-force on both sides for a threshold crossing because curvature can jump.
- Ignore friction and air resistance. Compute speed from conservation of energy using (v=sqrt{2g(h_0-h)}), where (v) is speed in m/s, (g=9.81 mathrm{m/s^2}), (h_0) is the starting height in m, and (h) is the current height in m. Multiply (v) by 2.23694 for mph. Advance the car along the curve according to its speed and elapsed time.
- Compute signed rider g-force perpendicular to the track using (n=cos	heta+v^2kappa/g). Here (n) is the load in multiples of gravity, (	heta) is the track tangent angle from horizontal, and (kappa=h''(x)/(1+h'(x)^2)^{3/2}) is signed curvature in (mathrm{m^{-1}}). The primes are derivatives with respect to (x). Curvature is positive at a valley and negative at a crest. At the flat bottom of a valley, this gives (n=1+v^2/(gR)), where (R=1/kappa) is the radius in m.
- If the car reaches zero speed on a climb before the next crest, mark the turning point and animate the car rolling back along the track. If it reaches a crest at zero speed, mark it as stalled. Stop the animation and mark the first point where the load exceeds (4,g) or drops below (-1,g). A ride that reaches the end without a failure is complete.

# Outputs

- Side view of the track with its control points, an animated car, and a labeled marker at the first failure point.
- Next to the marker, show the failure reason, distance measured along the track from the start (m), speed (mph), and signed rider load (g) at the failure point. Keep those values fixed if the car rolls back. Use plain-language reasons such as “Car ran out of speed before the crest” and “Rider load crossed the 4 g limit.” If the failure is reported at a continuous threshold crossing, show the load at that location rather than inventing a higher reading.
- Live speed in mph and signed rider g-force in g.
- Two plots sharing a distance-along-track axis in meters. Show speed in mph and g-force in g, with a moving position indicator and the g-force limits marked.

# Look and feel

Open with the starter track visible and the car at the first point. Put the track editor above the plots, with the ride controls and live readouts beside the track on wide screens. On phones, stack the sections and make the control points large enough to drag by touch.

# Validation

Use the default points ((0,10)), ((20,0)), and ((30,2.5)) in meters. They lie on (h=(x-20)^2/40) when coordinates are expressed in meters, so the interpolation reproduces that parabola. At (x=20 mathrm{m}), the tangent is horizontal and the curvature is (1/20 mathrm{m^{-1}}), giving a valley radius of (20 mathrm{m}).

- **Speed at the first valley.** The car drops (10-0=10 mathrm{m}). By hand, (v=sqrt{2(9.81)(10)}=sqrt{196.2}approx14.01 mathrm{m/s}), or **31.33 mph**.
- **Rider g-force at the valley.** By hand, (n=1+196.2/(9.81	imes20)=2.00), so the expected readout is **2.00 g**.
- Once the app is built, ride the default track and compare its plotted values at the valley with these hand calculations, rounded to two decimal places.
- **Rollback hill.** The curve returns to the starting height of 10 m at a horizontal position of 40 m. Check that the marker reports 0.00 mph there and that the marker and its readings stay in place as the car rolls back.
- **High-g valley.** The drop is 10 m and the valley radius is 5 m, so the predicted load at the valley is 1 + 20/5 = 5.00 g. Check that the car stops at the first 4 g crossing before the valley and that the marker gives the reason, distance, speed, and rider load. Switch back to **Starter** and check that the marker clears.
- **Low-g crest.** The car should stop on the climb to the crest at approximately 24.17 m horizontally from the start (26.42 m along the track). Expect 26.33 mph and −1.00 g at the crossing. Check that Reset clears the marker.

# Platform

The roller coaster simulator is a Tkinter desktop application rather than a browser application.

## Implementation plan

1. Review the existing simulator specification and browser implementation to preserve track editing, presets, physics, readouts, plots, and failure behavior.
2. Initialize or confirm Git repository state and retain the repository requirement that each plan or change is committed.
3. Implement the Tkinter application in staged changes, keeping each logical stage as a separate commit.
4. Convert the track editor to desktop controls, including drag editing and the four-point/preset behavior described in this specification.
5. Reproduce the gravity-driven ride, live readouts, plots, rollback behavior, g-force failures, and Reset behavior in the Tkinter interface.
6. Add focused automated checks for geometry, physics, controls, presets, and ride outcomes.
7. Run the test suite and app-level validation, compare required preset values with the specification, verify the Git history, and confirm a clean working tree.

## Save feature

- Place a menu tab labeled **File** in the top-left corner of the desktop window.
- The **File** tab provides access to the save feature.
- The save feature saves the current roller coaster track configuration, including control-point coordinates and the selected preset/custom state.
- Saving must preserve the editable track for reopening or later use.
- Saving must park the car at the start and clear any active failure marker when the saved configuration is restored.
- The save interaction and file format will be defined in a later implementation plan before coding begins.

# Out of scope

Friction, air resistance, powered lifts, braking, loops, 3D views, and structural or ride safety certification.
