from pathlib import Path

from src.models import PlanSheet
from src.scale_detection import ScaleDetector


def test_text_scale_detection():
    sheet = PlanSheet("s1", Path("plans.pdf"), text="SCALE: 1\" = 20'")
    result = ScaleDetector().detect(sheet)
    assert result.feet_per_pixel == 20 / 300
    assert result.confidence >= 0.9
    assert not result.review_required


def test_not_to_scale_flags_review():
    sheet = PlanSheet("s1", Path("plans.pdf"), text="DETAIL - NOT TO SCALE")
    result = ScaleDetector().detect(sheet)
    assert result.feet_per_pixel is None
    assert result.review_required


def test_manual_scale_fallback():
    sheet = PlanSheet("s1", Path("plans.pdf"), text="NO SCALE FOUND")
    result = ScaleDetector(manual_scale="1in=40ft").detect(sheet)
    assert round(result.feet_per_pixel or 0, 6) == round(40 / 300, 6)
    assert result.source == "manual"
