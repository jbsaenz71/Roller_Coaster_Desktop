import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple


G = 9.81
MPH_PER_MPS = 2.23694
Point = Tuple[float, float]


@dataclass
class Reading:
    offset: float
    distance: float
    time: float
    height: float
    slope: float
    speed_mps: float
    speed_mph: float
    load: float
    segment: int = -1


PRESETS = {
    "Starter": [(0, 10), (20, 0), (30, 2.5)],
    "Rollback hill": [(0, 10), (20, 0), (45, 15.625)],
    "High-g valley": [(0, 10), (10, 0), (15, 2.5)],
    "Low-g crest": [(0, 10), (20, 2), (25, 3), (32, 1)],
}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def track_slopes(points: Sequence[Point]) -> List[float]:
    slopes = []
    count = len(points)
    for i, (x, height) in enumerate(points):
        first = clamp(i - 1, 0, count - 3)
        p0 = points[first]
        p1 = points[first + 1]
        p2 = points[first + 2]
        s1 = (p1[1] - p0[1]) / (p1[0] - p0[0])
        s2 = (p2[1] - p1[1]) / (p2[0] - p1[0])
        slope = s1 + (s2 - s1) / (p2[0] - p0[0]) * (2 * x - p0[0] - p1[0])
        slopes.append(slope)
    return slopes


def track_segments(points: Sequence[Point]):
    slopes = track_slopes(points)
    segments = []
    for i, (x0, h0) in enumerate(points[:-1]):
        x1, h1 = points[i + 1]
        width = x1 - x0
        rise = h1 - h0
        slope = slopes[i]
        end_slope = slopes[i + 1]
        b = (3 * rise - width * (2 * slope + end_slope)) / width ** 2
        c = (-2 * rise + width * (slope + end_slope)) / width ** 3
        segments.append({
            "index": i,
            "x0": x0,
            "width": width,
            "h0": h0,
            "slope": slope,
            "end_slope": end_slope,
            "b": b,
            "c": c,
        })
    return segments


def segment_height(segment, u: float) -> float:
    return segment["h0"] + u * (
        segment["slope"] + u * (segment["b"] + u * segment["c"])
    )


def segment_slope(segment, u: float) -> float:
    return segment["slope"] + u * (
        2 * segment["b"] + 3 * segment["c"] * u
    )


def reading_at(points: Sequence[Point], segment, u: float, distance: float = 0,
               elapsed: float = 0) -> Reading:
    start_height = points[0][1]
    h = segment_height(segment, u)
    slope = segment_slope(segment, u)
    speed_squared = 2 * G * max(0.0, start_height - h)
    speed_mps = math.sqrt(speed_squared)
    grade = math.hypot(1.0, slope)
    curvature = (2 * segment["b"] + 6 * segment["c"] * u) / grade ** 3
    load = 1.0 / grade + speed_squared * curvature / G
    return Reading(
        offset=segment["x0"] + u,
        distance=distance,
        time=elapsed,
        height=h,
        slope=slope,
        speed_mps=speed_mps,
        speed_mph=speed_mps * MPH_PER_MPS,
        load=load,
        segment=segment["index"],
    )


def stationary_points(segment) -> List[float]:
    b = segment["b"]
    c = segment["c"]
    slope = segment["slope"]
    width = segment["width"]
    discriminant = b * b - 3 * c * slope
    if abs(c) < 1e-14:
        roots = [-slope / (2 * b)] if abs(b) > 1e-14 else []
    elif discriminant >= 0:
        roots = [
            (-b - math.sqrt(discriminant)) / (3 * c),
            (-b + math.sqrt(discriminant)) / (3 * c),
        ]
    else:
        roots = []
    return sorted(set(u for u in roots if 0 < u < width))


def bisect(low: float, high: float, predicate):
    for _ in range(40):
        middle = (low + high) / 2
        if predicate(middle):
            high = middle
        else:
            low = middle
    return (low + high) / 2


def calculate_profile(points: Sequence[Point]):
    if len(points) < 2:
        return [], "stall", None
    segments = track_segments(points)
    start_height = points[0][1]
    samples: List[Reading] = []
    valley: Optional[Reading] = None
    outcome = "complete"

    for segment_index, segment in enumerate(segments):
        extrema = stationary_points(segment)
        extent = segment["width"]

        if segment_index == 0 and segment["slope"] >= 0:
            extent = 0
            outcome = "stall"
        else:
            previous = 0.0
            for u in [*extrema, segment["width"]]:
                h = segment_height(segment, u)
                if h - start_height >= -1e-9:
                    if h - start_height > 1e-9:
                        extent = bisect(
                            previous,
                            u,
                            lambda value: segment_height(segment, value) > start_height,
                        )
                    else:
                        extent = u
                    if u != segment["width"] or extent < segment["width"] or (
                        segment_index < len(segments) - 1
                        and abs(segment_slope(segment, extent)) < 1e-8
                    ):
                        outcome = (
                            "stall"
                            if abs(segment_slope(segment, extent)) < 1e-8
                            else "rollback"
                        )
                    break
                previous = u

        stops = [0.0]
        if extent > 0:
            stops.extend(extent * i / 240 for i in range(1, 241))
            stops.extend(u for u in extrema if u < extent)
            stops = sorted(set(stops))

        previous_u = 0.0
        for u in stops:
            reading = reading_at(points, segment, u)
            if outcome != "complete" and u == stops[-1] and extent > 0:
                reading.speed_mps = 0.0
                reading.speed_mph = 0.0

            last = samples[-1] if samples else None
            grade_u = math.hypot(1, segment_slope(segment, u))
            grade_mid = math.hypot(1, segment_slope(segment, (previous_u + u) / 2))
            grade_prev = math.hypot(1, segment_slope(segment, previous_u))
            distance_step = (u - previous_u) / 6 * (
                grade_prev + 4 * grade_mid + grade_u
            )
            distance = (last.distance if last else 0.0) + distance_step
            speed_time = (
                2 * distance_step / (reading.speed_mps + last.speed_mps)
                if last and distance_step > 0
                else 0.0
            )
            elapsed = (last.time if last else 0.0) + speed_time
            reading.distance = distance
            reading.time = elapsed
            samples.append(reading)

            if (
                valley is None
                and u > 0
                and abs(reading.slope) < 1e-6
                and 2 * segment["b"] + 6 * segment["c"] * u > 0
            ):
                valley = reading
            previous_u = u

        if outcome != "complete":
            break

    if not samples:
        samples = [reading_at(points, segments[0], 0.0)]
    return samples, outcome, valley


def first_load_failure(
    points: Sequence[Point],
    samples: Sequence[Reading],
) -> Optional[Tuple[Reading, float]]:
    segments = track_segments(points)
    for i, reading in enumerate(samples):
        if -1.0 <= reading.load <= 4.0:
            continue
        limit = 4.0 if reading.load > 4.0 else -1.0
        previous = samples[i - 1] if i > 0 else None
        if previous is None:
            return reading, limit
        if previous.segment != reading.segment:
            return reading, limit
        segment = segments[reading.segment]
        offset = bisect(
            previous.offset,
            reading.offset,
            lambda x: (
                reading_at(
                    points,
                    segment,
                    x - segment["x0"],
                ).load
                > limit
                if limit == 4.0
                else reading_at(
                    points,
                    segment,
                    x - segment["x0"],
                ).load
                < limit
            ),
        )
        u = offset - segment["x0"]
        crossing = reading_at(points, segment, u)
        fraction = (
            (crossing.offset - previous.offset)
            / (reading.offset - previous.offset)
            if reading.offset != previous.offset
            else 0.0
        )
        crossing.distance = previous.distance + (
            reading.distance - previous.distance
        ) * fraction
        crossing.time = previous.time + 2 * (
            crossing.distance - previous.distance
        ) / (previous.speed_mps + crossing.speed_mps)
        return crossing, limit
    return None
