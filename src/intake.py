from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from PIL import Image

from .models import PlanSheet, TextBlock
from .ocr_engine import OcrEngine
from .utils import safe_stem

log = logging.getLogger(__name__)


class PlanIntake:
    def __init__(self, output_dir: Path, dpi: int = 300) -> None:
        self.output_dir = output_dir
        self.dpi = dpi
        self.ocr = OcrEngine()

    def process(self, input_path: Path) -> list[PlanSheet]:
        if not input_path.exists():
            raise FileNotFoundError(input_path)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if input_path.is_dir():
            sheets: list[PlanSheet] = []
            for child in sorted(input_path.iterdir()):
                if child.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
                    sheets.extend(self.process(child))
            return sheets
        if input_path.suffix.lower() == ".pdf":
            return self._process_pdf(input_path)
        if input_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
            return [self._process_image(input_path)]
        raise ValueError(f"Unsupported input type: {input_path.suffix}")

    def _process_pdf(self, path: Path) -> list[PlanSheet]:
        try:
            import fitz
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for PDF intake") from exc

        doc = fitz.open(path)
        sheets: list[PlanSheet] = []
        for index, page in enumerate(doc, start=1):
            sheet_id = f"{safe_stem(path)}_p{index:03d}"
            img_path = self.output_dir / f"{sheet_id}.png"
            pdf_page_path = self.output_dir / f"{sheet_id}.pdf"
            meta_path = self.output_dir / f"{sheet_id}.metadata.json"

            pix = page.get_pixmap(matrix=fitz.Matrix(self.dpi / 72, self.dpi / 72), alpha=False)
            pix.save(img_path)

            single_page = fitz.open()
            single_page.insert_pdf(doc, from_page=index - 1, to_page=index - 1)
            single_page.save(pdf_page_path)

            native_text = page.get_text("text") or ""
            ocr_text, raw_blocks = self.ocr.extract(img_path) if len(native_text.strip()) < 40 else (native_text, [])
            text = native_text if len(native_text.strip()) >= len(ocr_text.strip()) else ocr_text
            blocks = [TextBlock(text=t, bbox=b, confidence=c) for t, b, c in raw_blocks]
            if native_text.strip():
                blocks.append(TextBlock(text=native_text, bbox=None, confidence=0.90))

            sheet = PlanSheet(
                sheet_id=sheet_id,
                source_path=path,
                page_number=index,
                pdf_page_path=pdf_page_path,
                image_path=img_path,
                metadata_path=meta_path,
                width_px=pix.width,
                height_px=pix.height,
                dpi=self.dpi,
                text=text,
                text_blocks=blocks,
            )
            self._enrich_metadata(sheet)
            self._write_metadata(sheet)
            sheets.append(sheet)
        return sheets

    def _process_image(self, path: Path) -> PlanSheet:
        image = Image.open(path)
        text, raw_blocks = self.ocr.extract(path)
        sheet = PlanSheet(
            sheet_id=safe_stem(path),
            source_path=path,
            image_path=path,
            metadata_path=self.output_dir / f"{safe_stem(path)}.metadata.json",
            width_px=image.width,
            height_px=image.height,
            dpi=self.dpi,
            text=text,
            text_blocks=[TextBlock(text=t, bbox=b, confidence=c) for t, b, c in raw_blocks],
        )
        self._enrich_metadata(sheet)
        self._write_metadata(sheet)
        return sheet

    def _enrich_metadata(self, sheet: PlanSheet) -> None:
        text = sheet.text or ""
        candidates = re.findall(r"\b(?:C|CG|CE|CS|CU|L|LA|E|A|S)[-. ]?\d{2,4}[A-Z]?\b", text, re.I)
        sheet.sheet_number = candidates[0].upper().replace(" ", "-") if candidates else sheet.sheet_id
        title_lines = [line.strip() for line in text.splitlines() if 4 <= len(line.strip()) <= 80]
        sheet.sheet_title = title_lines[0] if title_lines else None
        date_match = re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text)
        sheet.revision_date = date_match.group(0) if date_match else None
        upper = text.upper()
        if "GRADING" in upper or "EROSION" in upper:
            sheet.discipline = "Civil"
        elif "UTILITY" in upper or "STORM" in upper or "SANITARY" in upper:
            sheet.discipline = "Utility"
        elif "LANDSCAPE" in upper:
            sheet.discipline = "Landscape"

    def _write_metadata(self, sheet: PlanSheet) -> None:
        if not sheet.metadata_path:
            return
        payload = {k: str(v) if isinstance(v, Path) else v for k, v in sheet.__dict__.items() if k != "text_blocks"}
        payload["text_blocks"] = [
            {"text": block.text, "bbox": block.bbox, "confidence": block.confidence}
            for block in sheet.text_blocks[:200]
        ]
        sheet.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
