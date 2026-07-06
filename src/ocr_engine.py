from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)


class OcrEngine:
    def extract(self, image_path: Path) -> tuple[str, list[tuple[str, tuple[float, float, float, float] | None, float]]]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError:
            log.warning("pytesseract/Pillow unavailable; OCR skipped for %s", image_path)
            return "", []

        try:
            image = Image.open(image_path)
            text = pytesseract.image_to_string(image)
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            blocks = []
            for index, word in enumerate(data.get("text", [])):
                word = word.strip()
                if not word:
                    continue
                try:
                    confidence = max(0.0, min(1.0, float(data.get("conf", ["0"])[index]) / 100.0))
                except ValueError:
                    confidence = 0.5
                x = data["left"][index]
                y = data["top"][index]
                width = data["width"][index]
                height = data["height"][index]
                blocks.append((word, (float(x), float(y), float(x + width), float(y + height)), confidence))
            return text, blocks
        except Exception as exc:
            log.warning("OCR failed for %s: %s", image_path, exc)
            return "", []
