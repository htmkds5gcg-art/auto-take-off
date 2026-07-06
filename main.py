from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from src.takeoff_runner import run_takeoff
from src.utils import parse_bool, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Civil/sitework Auto Takeoff Agent")
    parser.add_argument("--input", default=None, help="PDF, image, or folder to process")
    parser.add_argument("--output", default="./output", help="Output directory")
    parser.add_argument("--project", default="Untitled Project", help="Project name")
    parser.add_argument("--manual-scale", default=None, help='Manual fallback scale, e.g. "1in=20ft"')
    parser.add_argument("--sheet-filter", default=None, help="Comma-separated sheet numbers to include")
    parser.add_argument("--confidence-threshold", type=float, default=0.70)
    parser.add_argument("--export-markups", type=parse_bool, default=True)
    parser.add_argument("--debug", type=parse_bool, default=False)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("Auto Takeoff Agent is installed and ready.")
        print()
        parser.print_help()
        return 0

    args = parser.parse_args(argv)
    if not args.input:
        parser.error("the following arguments are required for takeoff runs: --input")
    setup_logging(args.debug)

    input_path = Path(args.input)
    output_dir = Path(args.output)
    sheet_filter = {sheet.strip().upper() for sheet in args.sheet_filter.split(",")} if args.sheet_filter else None
    result = run_takeoff(
        input_path=input_path,
        output_dir=output_dir,
        project=args.project,
        manual_scale=args.manual_scale,
        sheet_filter=sheet_filter,
        confidence_threshold=args.confidence_threshold,
        export_markups=args.export_markups,
    )
    print(json.dumps(result.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
