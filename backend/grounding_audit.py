"""Product-level audit for strict-material outline fact references.

This audit is deliberately structural and inexpensive. It checks the model's
declared ``fact_ids`` against the user-confirmed fact table without sending the
content to another model. Semantic verification can be added later, but these
signals are already useful for retry guidance and transparent user warnings.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class GroundingAudit:
    fact_count: int
    declared_fact_ids: list[int]
    missing_fact_ids: list[int]
    invalid_fact_ids: list[int]
    ungrounded_content_pages: list[int]
    fact_coverage: float

    @property
    def structurally_valid(self) -> bool:
        return not self.invalid_fact_ids and not self.ungrounded_content_pages

    @property
    def complete(self) -> bool:
        return (
            self.fact_count > 0
            and not self.missing_fact_ids
            and self.structurally_valid
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "structurally_valid": self.structurally_valid,
            "complete": self.complete,
        }


def _is_integer_id(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def audit_grounded_outline(
    outline: dict[str, Any],
    fact_table: list[dict[str, Any]],
) -> GroundingAudit:
    facts = fact_table if isinstance(fact_table, list) else []
    valid_ids = {
        int(fact["id"])
        for fact in facts
        if isinstance(fact, dict) and _is_integer_id(fact.get("id"))
    }
    declared: set[int] = set()
    invalid: set[int] = set()
    ungrounded_pages: list[int] = []

    slide_value = outline.get("slides", []) if isinstance(outline, dict) else []
    slides = slide_value if isinstance(slide_value, list) else []
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        values = slide.get("fact_ids", [])
        values = values if isinstance(values, list) else []
        integer_ids = [value for value in values if _is_integer_id(value)]
        valid_on_page = [value for value in integer_ids if value in valid_ids]
        declared.update(valid_on_page)
        invalid.update(value for value in integer_ids if value not in valid_ids)
        if slide.get("slide_type") == "content" and not valid_on_page:
            page_number = slide.get("page_number", index)
            ungrounded_pages.append(
                page_number if _is_integer_id(page_number) else index
            )

    missing = sorted(valid_ids - declared)
    coverage = round(len(declared) / max(len(valid_ids), 1), 3)
    return GroundingAudit(
        fact_count=len(valid_ids),
        declared_fact_ids=sorted(declared),
        missing_fact_ids=missing,
        invalid_fact_ids=sorted(invalid),
        ungrounded_content_pages=sorted(set(ungrounded_pages)),
        fact_coverage=coverage,
    )
