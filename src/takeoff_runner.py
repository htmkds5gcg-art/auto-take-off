from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .classifier import CivilClassifier
from .intake import PlanIntake
from .manual_review import ManualReviewQueue
from .markup import MarkupRenderer
from .measurement import MeasurementEngine
from .quantity_report import QuantityReporter
from .raster_geometry import RasterGeometryExtractor
from .scale_detection import ScaleDetector
from .vector_extraction import VectorExtractor


@dataclass(frozen=True)
class TakeoffRunResult:
    project: str
    items: int
    review_items: int
    output: str

    def to_dict(self) -> dict[str, str | int]:
        return {
            "project": self.project,
            "items": self.items,
            "review_items": self.review_items,
            "output": self.output,
        }


def run_takeoff(
    input_path: Path,
    output_dir: Path,
    project: str = "Untitled Project",
    manual_scale: str | None = None,
    sheet_filter: set[str] | None = None,
    confidence_threshold: float = 0.70,
    export_markups: bool = True,
) -> TakeoffRunResult:
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.info("Starting takeoff for %s", project)
    sheets = PlanIntake(output_dir / "sheets").process(input_path)
    if sheet_filter:
        sheets = [sheet for sheet in sheets if (sheet.sheet_number or "").upper() in sheet_filter]

    scale_detector = ScaleDetector(manual_scale=manual_scale)
    vector_extractor = VectorExtractor()
    raster_extractor = RasterGeometryExtractor()
    classifier = CivilClassifier.from_config(Path(__file__).resolve().parent.parent / "config")
    measurer = MeasurementEngine(confidence_threshold=confidence_threshold)
    review = ManualReviewQueue(threshold=confidence_threshold)

    all_items = []
    assumptions = []
    for sheet in sheets:
        scale = scale_detector.detect(sheet)
        assumptions.extend(scale.assumptions)
        if scale.review_required:
            review.add_sheet(sheet, scale.reason)

        geometries = []
        geometries.extend(vector_extractor.extract(sheet))
        geometries.extend(raster_extractor.extract(sheet))
        for geometry in geometries:
            classified = classifier.classify_geometry(geometry, sheet.text_blocks)
            item = measurer.measure(sheet, geometry, classified, scale)
            all_items.append(item)
            review.consider_item(item)

        for text_item in classifier.extract_text_items(sheet):
            item = measurer.from_text_item(sheet, text_item, scale)
            all_items.append(item)
            review.consider_item(item)

    reporter = QuantityReporter(output_dir)
    reporter.write_json(all_items, output_dir / "takeoff_items.json")
    reporter.write_excel(all_items, review.items, assumptions, output_dir / "takeoff_summary.xlsx")
    reporter.write_pdf(project, all_items, review.items, assumptions, output_dir / "takeoff_report.pdf")

    if export_markups:
        MarkupRenderer(output_dir / "marked_up_sheets").render(sheets, all_items)

    logging.info("Finished. Items=%s Review=%s", len(all_items), len(review.items))
    return TakeoffRunResult(project, len(all_items), len(review.items), str(output_dir))
