from __future__ import annotations

from .models import ClassifiedFeature, GeometryFeature, PlanSheet, ScaleResult, TakeoffItem, TextQuantityCandidate


class MeasurementEngine:
    def __init__(self, confidence_threshold: float = 0.70) -> None:
        self.confidence_threshold = confidence_threshold

    def measure(self, sheet: PlanSheet, geom: GeometryFeature, classified: ClassifiedFeature, scale: ScaleResult) -> TakeoffItem:
        quantity = None
        unit = "UNSCALED"
        notes = classified.notes
        confidence = min(geom.confidence, classified.confidence, scale.confidence)

        if scale.feet_per_pixel is None:
            notes = self._append(notes, scale.reason or "No scale available")
            confidence = min(confidence, 0.35)
        elif classified.measurement_type == "length":
            quantity = round((geom.raw_length_px or 0.0) * scale.feet_per_pixel, 2)
            unit = "LF"
        elif classified.measurement_type == "area":
            area_px = geom.raw_area_px
            if area_px is None and geom.geometry_type == "polygon":
                from .utils import polygon_area

                area_px = polygon_area(geom.coordinates)
            quantity = round((area_px or 0.0) * scale.feet_per_pixel * scale.feet_per_pixel, 2)
            unit = "SF"
        elif classified.measurement_type == "count":
            quantity = 1.0
            unit = "EA"
            confidence = min(confidence, 0.60)
        else:
            confidence = min(confidence, 0.40)

        review_required = confidence < self.confidence_threshold or scale.review_required or quantity is None
        include_in_final = confidence >= 0.40 and quantity is not None and not scale.review_required
        return TakeoffItem(
            classified.category,
            classified.item_name,
            sheet.sheet_number,
            classified.measurement_type,
            quantity,
            unit,
            geom.source_method,
            round(confidence, 2),
            notes,
            geom.coordinates,
            geom.bbox,
            include_in_final,
            review_required,
            list(scale.assumptions),
        )

    def from_text_item(self, sheet: PlanSheet, candidate: TextQuantityCandidate, scale: ScaleResult) -> TakeoffItem:
        unit = candidate.unit or self._default_unit(candidate.measurement_type)
        quantity = candidate.quantity
        confidence = candidate.confidence if quantity is not None else min(candidate.confidence, 0.45)
        review_required = confidence < self.confidence_threshold or quantity is None
        include_in_final = confidence >= 0.40 and quantity is not None
        notes = "Quantity parsed from text" if quantity is not None else "Text cue found without explicit quantity"
        return TakeoffItem(
            candidate.category,
            candidate.item_name,
            sheet.sheet_number,
            candidate.measurement_type,
            quantity,
            unit,
            "text",
            round(confidence, 2),
            notes,
            [],
            candidate.bbox,
            include_in_final,
            review_required,
            list(scale.assumptions),
        )

    def _default_unit(self, measurement_type: str) -> str:
        return {"length": "LF", "area": "SF", "count": "EA", "volume": "CY"}.get(measurement_type, "UNK")

    def _append(self, base: str, extra: str) -> str:
        return f"{base}; {extra}" if base else extra
