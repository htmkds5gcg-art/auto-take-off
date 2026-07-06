from src.classifier import CivilClassifier
from src.models import GeometryFeature, TextBlock


def test_classifier_matches_storm_text():
    classifier = CivilClassifier()
    geom = GeometryFeature("line", "vector", [(0, 0), (1, 1)], raw_length_px=1)
    result = classifier.classify_geometry(geom, [TextBlock('18" RCP STORM PIPE')])
    assert result.category == "Storm drainage"
    assert result.measurement_type == "length"


def test_classifier_defaults_unclassified_area():
    classifier = CivilClassifier()
    geom = GeometryFeature("polygon", "raster", [(0, 0), (1, 0), (1, 1)], raw_area_px=1)
    result = classifier.classify_geometry(geom, [])
    assert result.item_name == "Unclassified area"
    assert result.confidence < 0.7
