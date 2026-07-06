# Auto Takeoff Agent

A Python prototype for civil/sitework quantity takeoff from PDF sheets, raster images, vector geometry, and text-derived plan data. It is engine-first and conservative: every measured item carries source method, confidence, assumptions, and review flags.

## Setup

```bash
cd auto_takeoff_agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

For OCR, install Tesseract separately and ensure `tesseract` is on PATH.

## Example

```bash
python main.py --input ./input/plans.pdf --output ./output --project "Project Name" --manual-scale "1in=20ft" --export-markups true
```

Optional arguments:

```bash
--sheet-filter "C-100,C-200,C-300"
--confidence-threshold 0.70
--debug true
```

## Railway / Web API

The repo includes a FastAPI wrapper for hosted use on Railway.

Railway can use the included `railway.json` start command:

```bash
uvicorn api:app --host 0.0.0.0 --port $PORT
```

Local API run:

```bash
uvicorn api:app --reload
```

Useful endpoints:

- `GET /health`: health check
- `GET /docs`: interactive OpenAPI docs
- `POST /takeoff`: upload a plan file and start a takeoff job
- `GET /takeoff/{job_id}`: check job status
- `GET /takeoff/{job_id}/download`: download all outputs as a zip

Example upload:

```bash
curl -X POST http://localhost:8000/takeoff \
  -F "file=@./input/plans.pdf" \
  -F "project=Project Name" \
  -F "manual_scale=1in=20ft"
```

The hosted API stores uploaded files and outputs under `runs/` by default. Set `TAKEOFF_RUN_ROOT` to change that location.

## How Scale Is Detected

The scale engine uses a conservative chain:

1. Native PDF text and OCR are searched for scale patterns such as `1" = 20'`, `SCALE: 1"=40'`, `GRAPHIC SCALE`, and `NOT TO SCALE`.
2. If a valid text scale is found, it converts drawing inches to real feet and computes feet per pixel from image DPI.
3. If the sheet is marked `NOT TO SCALE`, the sheet is flagged and automatic measured quantities are held for review.
4. If text scale is missing or low confidence, a manual scale such as `1in=20ft` can be supplied.
5. The system never silently guesses scale. Unscaled geometry is output as review-needed, not final quantity.

Graphic scale-bar detection is scaffolded for production extension; the first version flags `GRAPHIC SCALE` text but does not treat it as authoritative unless measured/calibrated.

## How Quantities Are Measured

PDF vector paths are extracted when available with PyMuPDF. Raster linework is detected with OpenCV using edges and Hough line detection. Closed contours provide rough area candidates. Measurements are converted to feet, square feet, or count units when enough scale and geometry context exists. Text labels and configured regex patterns classify nearby items into civil categories.

## Outputs

Running the CLI creates:

- `takeoff_summary.xlsx`: category, sheet, detail, review, and assumptions tabs
- `takeoff_items.json`: machine-readable output
- `marked_up_sheets/`: sheet images with labels and bounding boxes when enabled
- `takeoff_report.pdf`: summary report, or a `.txt` fallback if ReportLab is unavailable
- `sheets/`: per-sheet images and metadata from intake

## Known Limitations

- OCR quality depends on the installed OCR engine and sheet resolution.
- Raster geometry detection is intentionally conservative and may detect linework that requires human classification.
- Graphic scale-bar measurement is a placeholder in this first version.
- Duplicate detection across matchlines is heuristic and must be reviewed.
- Profiles, details, enlarged plans, and typical sections are flagged by text but not fully semantically modeled.
- Cut/fill requires surfaces/elevations that are not implemented in this prototype.

## Production Upgrades

- Interactive manual calibration UI with point picking.
- Robust graphic scale-bar detector.
- CAD layer-aware DXF classification.
- Sheet registration, matchline clipping, and duplicate suppression.
- ML symbol detector for structures, hydrants, valves, signs, trees, and fixtures.
- Human-in-the-loop review dashboard with approval workflow.
