from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import Iterable


def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s %(name)s: %(message)s")


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def safe_stem(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", path.stem).strip("_") or "sheet"


def polyline_length(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def polygon_area(points: Iterable[tuple[float, float]]) -> float:
    pts = list(points)
    if len(pts) < 3:
        return 0.0
    area = 0.0
    for index, point in enumerate(pts):
        next_point = pts[(index + 1) % len(pts)]
        area += point[0] * next_point[1] - next_point[0] * point[1]
    return abs(area) / 2.0


def bbox_from_points(points: Iterable[tuple[float, float]]) -> tuple[float, float, float, float] | None:
    pts = list(points)
    if not pts:
        return None
    xs = [point[0] for point in pts]
    ys = [point[1] for point in pts]
    return min(xs), min(ys), max(xs), max(ys)
