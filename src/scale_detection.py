from __future__ import annotations

import re

from .models import PlanSheet, ScaleResult

_SCALE_RE = re.compile(
    r"(?P<draw>\d+(?:\.\d+)?)\s*(?:\"|IN|INCH|INCHES)\s*=\s*(?P<real>\d+(?:\.\d+)?)\s*(?:'|FT|FEET|FOOT)",
    re.I,
)
_MANUAL_RE = re.compile(
    r"(?P<draw>\d+(?:\.\d+)?)\s*(?:in|inch|\")\s*=\s*(?P<real>\d+(?:\.\d+)?)\s*(?:ft|feet|foot|')",
    re.I,
)


class ScaleDetector:
    def __init__(self, manual_scale: str | None = None) -> None:
        self.manual_scale = manual_scale

    def detect(self, sheet: PlanSheet) -> ScaleResult:
        text = sheet.text or ""
        if re.search(r"NOT\s+TO\s+SCALE|N\.?T\.?S\.?", text, re.I):
            return ScaleResult(
                None,
                "text",
                0.95,
                review_required=True,
                reason="Sheet is marked NOT TO SCALE",
                assumptions=[f"{sheet.sheet_id}: NOT TO SCALE detected"],
            )

        match = _SCALE_RE.search(text)
        if match:
            return self._from_match(sheet, match, "text", 0.90)

        if self.manual_scale:
            manual = _MANUAL_RE.search(self.manual_scale)
            if manual:
                result = self._from_match(sheet, manual, "manual", 0.85)
                result.assumptions.append(f"{sheet.sheet_id}: manual scale used: {self.manual_scale}")
                return result

        if re.search(r"GRAPHIC\s+SCALE", text, re.I):
            return ScaleResult(
                None,
                "graphic-scale-text",
                0.45,
                review_required=True,
                reason="Graphic scale label found but bar was not calibrated",
                assumptions=[f"{sheet.sheet_id}: graphic scale requires manual calibration"],
            )

        return ScaleResult(
            None,
            "unknown",
            0.20,
            review_required=True,
            reason="No reliable scale detected",
            assumptions=[f"{sheet.sheet_id}: no scale detected; manual calibration required"],
        )

    def _from_match(self, sheet: PlanSheet, match: re.Match[str], source: str, confidence: float) -> ScaleResult:
        draw_in = float(match.group("draw"))
        real_ft = float(match.group("real"))
        if draw_in <= 0 or real_ft <= 0:
            return ScaleResult(None, source, 0.0, review_required=True, reason="Invalid scale values")
        dpi = sheet.dpi or 300
        feet_per_pixel = real_ft / (draw_in * dpi)
        scale_text = match.group(0)
        return ScaleResult(
            feet_per_pixel,
            source,
            confidence,
            scale_text=scale_text,
            assumptions=[
                f"{sheet.sheet_id}: scale {scale_text} interpreted as {feet_per_pixel:.6f} ft/pixel at {dpi} DPI"
            ],
        )
