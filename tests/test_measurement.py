from pathlib import Path

from src.measurement import MeasurementEngine
from src.models import ClassifiedFeature, GeometryFeature, PlanSheet, ScaleResult


def test_length_measurement_scaled():
    sheet = PlanSheet("s1", Path("plans.pdf"), sheet_number="C-100")
    geom = GeometryFeature("line", "raster", [(0, 0), (300, 0)], raw_length_px=300, confidence=0.8)
    classified = ClassifiedFeature("Curb", "Curb and gutter", "length", 0.8)
    scale = ScaleResult(20 / 300, "text", 0.9)
    item = MeasurementEngine().measure(sheet, geom, classified, scale)
    assert item.quantity == 20.0
    assert item.unit == "LF"
    assert item.include_in_final


def test_unscaled_requires_review():
    sheet = PlanSheet("s1", Path("plans.pdf"), sheet_number="C-100")
    geom = GeometryFeature("line", "raster", [(0, 0), (300, 0)], raw_length_px=300, confidence=0.8)
    classified = ClassifiedFeature("Curb", "Curb and gutter", "length", 0.8)
    scale = ScaleResult(None, "unknown", 0.2, review_required=True, reason="No scale")
    item = MeasurementEngine().measure(sheet, geom, classified, scale)
    assert item.quantity is None
    assert item.review_required
    assert not item.include_in_final
