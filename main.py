from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from src.classifier import CivilClassifier
from src.intake import PlanIntake
from src.manual_review import ManualReviewQueue
from src.markup import MarkupRenderer
from src.measurement import MeasurementEngine
from src.quantity_report import QuantityReporter
from src.raster_geometry import RasterGeometryExtractor
from src.scale_detection import ScaleDetector
from src.utils import parse_bool, setup_logging
from src.vector_extraction import VectorExtractor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Civil/sitework Auto Takeoff Agent")
    parser.add_argument("--input", required=True, help="PDF, image, or folder to process")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--project", default="Untitled Project", help="Project name")
    parser.add_argument("--manual-scale", default=None, help='Manual fallback scale, e.g. "1in=20ft"')
    parser.add_argument("--sheet-filter", default=None, help="Comma-separated sheet numbers to include")
    parser.add_argument("--confidence-threshold", type=float, default=0.70)
    parser.add_argument("--export-markups", type=parse_bool, default=True)
    parser.add_argument("--debug", type=parse_bool, default=False)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging(args.debug)

    input_path = Path(args.input)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    sheet_filter = {sheet.strip().upper() for sheet in args.sheet_filter.split(",")} if args.sheet_filter else None

    logging.info("Starting takeoff for %s", args.project)
    sheets = PlanIntake(output_dir / "sheets").process(input_path)
    if sheet_filter:
        sheets = [sheet for sheet in sheets if (sheet.sheet_number or "").upper() in sheet_filter]

    scale_detector = ScaleDetector(manual_scale=args.manual_scale)
    vector_extractor = VectorExtractor()
    raster_extractor = RasterGeometryExtractor()
    classifier = CivilClassifier.from_config(Path(__file__).parent / "config")
    measurer = MeasurementEngine(confidence_threshold=args.confidence_threshold)
    review = ManualReviewQueue(threshold=args.confidence_threshold)

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
    reporter.write_pdf(args.project, all_items, review.items, assumptions, output_dir / "takeoff_report.pdf")

    if args.export_markups:
        MarkupRenderer(output_dir / "marked_up_sheets").render(sheets, all_items)

    logging.info("Finished. Items=%s Review=%s", len(all_items), len(review.items))
    print(json.dumps({"project": args.project, "items": len(all_items), "review_items": len(review.items), "output": str(output_dir)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
