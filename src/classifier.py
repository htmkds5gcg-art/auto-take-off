from __future__ import annotations

import re
from pathlib import Path

from .models import ClassifiedFeature, GeometryFeature, PlanSheet, TextBlock, TextQuantityCandidate

DEFAULT_PATTERNS = [
    (r'\b\d+\s*"\s*RCP\b|\bSTORM\b|\bTYPE\s+[A-Z]\s+INLET\b', "Storm drainage", "Storm pipe/structure", "length"),
    (r'\b\d+\s*"\s*PVC\b|\bSANITARY\b|\bMANHOLE\b', "Sanitary sewer", "Sanitary sewer", "length"),
    (r"\bWATER\s*MAIN\b|\bDIP\b|\bFIRE\s+HYDRANT\b|\bVALVE\b", "Water main", "Water utility", "length"),
    (r"\bCURB(?:\s+AND\s+GUTTER)?\b", "Curb", "Curb and gutter", "length"),
    (r"\bSILT\s+FENCE\b|\bEROSION\b|\bSTABILIZED\s+CONSTRUCTION\s+ENTRANCE\b", "Erosion control", "Erosion control", "length"),
    (r"\bASPHALT\b|\bPAVEMENT\b|\bMILLING\b", "Asphalt paving", "Asphalt pavement", "area"),
    (r"\bSIDEWALK\b|\bCONCRETE\b", "Concrete", "Concrete flatwork", "area"),
    (r"\bSOD\b|\bLANDSCAP(?:E|ING)\b", "Landscaping/sod", "Landscape area", "area"),
    (r"\bSIGN\b|\bTREE\b|\bCLEANOUT\b|\bHYDRANT\b|\bINLET\b|\bMANHOLE\b", "Structures", "Count item", "count"),
]


class CivilClassifier:
    def __init__(self, patterns: list[tuple[str, str, str, str]] | None = None) -> None:
        self.patterns = [(re.compile(p, re.I), c, n, m) for p, c, n, m in (patterns or DEFAULT_PATTERNS)]

    @classmethod
    def from_config(cls, config_dir: Path) -> CivilClassifier:
        # Config files are shipped for customization; defaults keep the prototype dependency-light.
        return cls()

    def classify_geometry(self, geom: GeometryFeature, text_blocks: list[TextBlock]) -> ClassifiedFeature:
        nearby_text = " ".join(block.text for block in text_blocks[:500])
        for pattern, category, name, measurement in self.patterns:
            if pattern.search(nearby_text):
                return ClassifiedFeature(
                    category,
                    name,
                    measurement,  # type: ignore[arg-type]
                    min(0.82, geom.confidence + 0.15),
                    f"Classified from sheet text matching {pattern.pattern}",
                )
        if geom.geometry_type in {"polygon", "contour"}:
            return ClassifiedFeature("Miscellaneous", "Unclassified area", "area", 0.45, "No label matched; area candidate requires review")
        return ClassifiedFeature("Miscellaneous", "Unclassified linework", "length", 0.40, "No label matched; linework requires review")

    def extract_text_items(self, sheet: PlanSheet) -> list[TextQuantityCandidate]:
        text = sheet.text or ""
        candidates: list[TextQuantityCandidate] = []
        quantity_re = re.compile(r"(?P<qty>\d+(?:\.\d+)?)\s*(?P<unit>LF|SF|SY|CY|EA|EACH)\s+(?P<label>[A-Z0-9\"' .-/]+)", re.I)
        for match in quantity_re.finditer(text):
            label = match.group("label")[:80]
            category, name, measurement = self._classify_text(label)
            candidates.append(
                TextQuantityCandidate(category, name, measurement, float(match.group("qty")), match.group("unit").upper(), 0.78, match.group(0))
            )

        for pattern, category, name, measurement in self.patterns:
            for match in pattern.finditer(text):
                candidates.append(TextQuantityCandidate(category, name, measurement, None, None, 0.55, match.group(0)))
        return candidates

    def _classify_text(self, label: str) -> tuple[str, str, str]:
        for pattern, category, name, measurement in self.patterns:
            if pattern.search(label):
                return category, name, measurement
        return "Miscellaneous", label.title(), "unknown"
