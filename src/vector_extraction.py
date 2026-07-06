from __future__ import annotations

import logging

from .models import GeometryFeature, PlanSheet
from .utils import bbox_from_points, polygon_area, polyline_length

log = logging.getLogger(__name__)


class VectorExtractor:
    def extract(self, sheet: PlanSheet) -> list[GeometryFeature]:
        if not sheet.pdf_page_path:
            return []
        try:
            import fitz
        except ImportError:
            return []

        features: list[GeometryFeature] = []
        try:
            doc = fitz.open(sheet.pdf_page_path)
            page = doc[0]
            scale = (sheet.dpi or 300) / 72.0
            for drawing in page.get_drawings():
                points: list[tuple[float, float]] = []
                for item in drawing.get("items", []):
                    op = item[0]
                    if op == "l":
                        points.extend([(item[1].x * scale, item[1].y * scale), (item[2].x * scale, item[2].y * scale)])
                    elif op == "re":
                        rect = item[1]
                        points.extend(
                            [
                                (rect.x0 * scale, rect.y0 * scale),
                                (rect.x1 * scale, rect.y0 * scale),
                                (rect.x1 * scale, rect.y1 * scale),
                                (rect.x0 * scale, rect.y1 * scale),
                            ]
                        )
                    elif op == "c":
                        points.append((item[-1].x * scale, item[-1].y * scale))

                if len(points) < 2:
                    continue
                closed = len(points) > 3 and points[0] == points[-1]
                raw_area = polygon_area(points) if closed else None
                features.append(
                    GeometryFeature(
                        "polygon" if closed else "polyline",
                        "vector",
                        points,
                        bbox_from_points(points),
                        polyline_length(points),
                        raw_area,
                        0.78,
                        notes="Extracted from PDF vector drawing commands",
                    )
                )
        except Exception as exc:
            log.warning("Vector extraction failed for %s: %s", sheet.sheet_id, exc)
        return features
