from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

MeasurementType = Literal["length", "area", "count", "volume", "unknown"]
SourceMethod = Literal["vector", "ocr", "raster", "manual", "text", "unknown"]


@dataclass
class TextBlock:
    text: str
    bbox: tuple[float, float, float, float] | None = None
    confidence: float = 0.75


@dataclass
class PlanSheet:
    sheet_id: str
    source_path: Path
    page_number: int = 1
    pdf_page_path: Path | None = None
    image_path: Path | None = None
    metadata_path: Path | None = None
    width_px: int | None = None
    height_px: int | None = None
    dpi: int = 300
    sheet_size: str | None = None
    sheet_number: str | None = None
    sheet_title: str | None = None
    revision_date: str | None = None
    discipline: str | None = None
    text: str = ""
    text_blocks: list[TextBlock] = field(default_factory=list)


@dataclass
class ScaleResult:
    feet_per_pixel: float | None
    source: str
    confidence: float
    scale_text: str | None = None
    review_required: bool = False
    reason: str | None = None
    assumptions: list[str] = field(default_factory=list)


@dataclass
class GeometryFeature:
    geometry_type: str
    source_method: SourceMethod
    coordinates: list[tuple[float, float]]
    bbox: tuple[float, float, float, float] | None = None
    raw_length_px: float | None = None
    raw_area_px: float | None = None
    confidence: float = 0.65
    label: str | None = None
    notes: str | None = None


@dataclass
class ClassifiedFeature:
    category: str
    item_name: str
    measurement_type: MeasurementType
    confidence: float
    notes: str = ""


@dataclass
class TextQuantityCandidate:
    category: str
    item_name: str
    measurement_type: MeasurementType
    quantity: float | None
    unit: str | None
    confidence: float
    text: str
    bbox: tuple[float, float, float, float] | None = None


@dataclass
class TakeoffItem:
    category: str
    item_name: str
    sheet_number: str | None
    measurement_type: MeasurementType
    quantity: float | None
    unit: str
    source_method: SourceMethod
    confidence: float
    notes: str = ""
    coordinates: list[tuple[float, float]] = field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None
    include_in_final: bool = True
    review_required: bool = False
    assumption_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["coordinates"] = [list(point) for point in self.coordinates]
        return data
