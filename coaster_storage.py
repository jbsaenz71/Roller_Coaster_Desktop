import json
import math
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from coaster_physics import PRESETS, Point


SCHEMA_VERSION = 1


class TrackFileError(ValueError):
    """Raised when a saved track does not match the supported file format."""


def _validate_document(document) -> Tuple[str, List[Point]]:
    if not isinstance(document, dict):
        raise TrackFileError("The track file must contain a JSON object.")

    version = document.get("schema_version")
    if type(version) is not int or version != SCHEMA_VERSION:
        raise TrackFileError(
            f"Unsupported track file version: {version!r}."
        )

    preset = document.get("preset")
    if preset not in (*PRESETS.keys(), "Custom"):
        raise TrackFileError("The track file names an unknown preset.")

    raw_points = document.get("points")
    if not isinstance(raw_points, list) or not 3 <= len(raw_points) <= 4:
        raise TrackFileError("A track must contain three or four control points.")

    points = []
    for index, raw_point in enumerate(raw_points):
        if not isinstance(raw_point, list) or len(raw_point) != 2:
            raise TrackFileError(
                f"Control point {index + 1} must contain x and height values."
            )
        x, height = raw_point
        if (
            isinstance(x, bool)
            or isinstance(height, bool)
            or not isinstance(x, (int, float))
            or not isinstance(height, (int, float))
            or (isinstance(x, float) and not math.isfinite(x))
            or (isinstance(height, float) and not math.isfinite(height))
        ):
            raise TrackFileError(
                f"Control point {index + 1} must contain finite numbers."
            )
        if not 0 <= x <= 200 or not 0 <= height <= 60:
            raise TrackFileError(
                f"Control point {index + 1} is outside the track bounds."
            )
        if points and x - points[-1][0] < 1:
            raise TrackFileError(
                "Control points must be ordered with at least 1 m spacing."
            )
        points.append((float(x), float(height)))

    if points[0][1] <= points[1][1]:
        raise TrackFileError("The first point must be higher than the second point.")

    if preset != "Custom":
        expected = PRESETS[preset]
        if points != [(float(x), float(height)) for x, height in expected]:
            raise TrackFileError(
                "The saved points do not match the selected track preset."
            )

    return preset, points


def save_track(path, points: Sequence[Point], preset: str) -> None:
    document = {
        "schema_version": SCHEMA_VERSION,
        "preset": preset,
        "points": [[float(x), float(height)] for x, height in points],
    }
    _validate_document(document)

    target = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=target.name + ".",
            suffix=".tmp",
            dir=str(target.parent),
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(document, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass


def load_track(path) -> Tuple[str, List[Point]]:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except json.JSONDecodeError as error:
        raise TrackFileError("The selected file is not valid JSON.") from error
    return _validate_document(document)
