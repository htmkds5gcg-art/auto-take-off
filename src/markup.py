from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .models import PlanSheet, TakeoffItem


class MarkupRenderer:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def render(self, sheets: list[PlanSheet], items: list[TakeoffItem]) -> None:
        by_sheet: dict[str | None, list[TakeoffItem]] = {}
        for item in items:
            by_sheet.setdefault(item.sheet_number, []).append(item)

        for sheet in sheets:
            if not sheet.image_path or not Path(sheet.image_path).exists():
                continue
            image = Image.open(sheet.image_path).convert("RGB")
            draw = ImageDraw.Draw(image)
            for item in by_sheet.get(sheet.sheet_number, []):
                color = "green" if item.include_in_final else "orange"
                if item.bbox:
                    draw.rectangle(item.bbox, outline=color, width=3)
                    label = f"{item.item_name} {item.quantity or ''} {item.unit}".strip()
                    draw.text((item.bbox[0], max(0, item.bbox[1] - 14)), label, fill=color)
                elif len(item.coordinates) >= 2:
                    draw.line(item.coordinates, fill=color, width=3)
            image.save(self.output_dir / f"{sheet.sheet_id}_markup.png")
