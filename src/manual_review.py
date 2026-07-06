from __future__ import annotations

from .models import PlanSheet, TakeoffItem


class ManualReviewQueue:
    def __init__(self, threshold: float = 0.70) -> None:
        self.threshold = threshold
        self.items: list[TakeoffItem | dict[str, str | None]] = []

    def add_sheet(self, sheet: PlanSheet, reason: str | None) -> None:
        self.items.append(
            {
                "type": "sheet",
                "sheet_number": sheet.sheet_number,
                "sheet_id": sheet.sheet_id,
                "reason": reason or "Manual review required",
            }
        )

    def consider_item(self, item: TakeoffItem) -> None:
        if item.review_required or item.confidence < self.threshold:
            self.items.append(item)
