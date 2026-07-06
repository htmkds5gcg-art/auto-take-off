from __future__ import annotations

import logging

from .models import GeometryFeature, PlanSheet
from .utils import bbox_from_points, polygon_area, polyline_length

log = logging.getLogger(__name__)


class RasterGeometryExtractor:
    def extract(self, sheet: PlanSheet) -> list[GeometryFeature]:
        if not sheet.image_path:
            return []
        try:
            import cv2
            import numpy as np
        except ImportError:
            log.warning("OpenCV unavailable; raster extraction skipped")
            return []

        try:
            image = cv2.imread(str(sheet.image_path), cv2.IMREAD_GRAYSCALE)
            if image is None:
                return []
            edges = cv2.Canny(image, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=120, minLineLength=80, maxLineGap=12)
            features: list[GeometryFeature] = []
            if lines is not None:
                for line in lines[:1000]:
                    x1, y1, x2, y2 = [float(value) for value in line[0]]
                    points = [(x1, y1), (x2, y2)]
                    features.append(
                        GeometryFeature(
                            "line",
                            "raster",
                            points,
                            bbox_from_points(points),
                            polyline_length(points),
                            None,
                            0.55,
                            notes="Detected with raster Hough line transform",
                        )
                    )

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for contour in contours[:300]:
                area = float(cv2.contourArea(contour))
                if area < 2500:
                    continue
                approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
                points = [(float(point[0][0]), float(point[0][1])) for point in approx]
                if len(points) >= 3:
                    features.append(
                        GeometryFeature(
                            "polygon",
                            "raster",
                            points,
                            bbox_from_points(points),
                            polyline_length(points + [points[0]]),
                            polygon_area(points),
                            0.50,
                            notes="Detected as raster closed contour candidate",
                        )
                    )
            return features
        except Exception as exc:
            log.warning("Raster extraction failed for %s: %s", sheet.sheet_id, exc)
            return []
