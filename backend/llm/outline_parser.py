"""
JSON outline validation and repair.

Handles:
- JSON wrapped in markdown fences
- Extra prose before/after the JSON payload
- Trailing commas or malformed JSON via json-repair fallback
- Safe normalization for page numbers, slide types, and forbidden fields
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from schema import OutlineData, SLIDE_CONSTRAINTS, format_validation_errors

try:
    from json_repair import repair_json
except ImportError:  # pragma: no cover - dependency should exist in runtime env
    repair_json = None

FORBIDDEN_FIELDS = {"chart_config", "image_config", "description", "type"}


class OutlineParseError(RuntimeError):
    """Raised when raw model output cannot be parsed into JSON."""


class OutlineValidationError(RuntimeError):
    """Raised when parsed JSON cannot be normalized into a valid outline."""


@dataclass
class ParsedOutlineResult:
    outline: dict[str, Any]
    warnings: list[str]


def strip_code_fences(raw_text: str) -> str:
    """Remove optional ```json fences around model output."""
    text = raw_text.strip()
    text = re.sub(r"^\s*```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def extract_json_object(raw_text: str) -> str | None:
    """Extract the first balanced JSON object from surrounding prose."""
    start = raw_text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False

    for index in range(start, len(raw_text)):
        char = raw_text[index]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return raw_text[start : index + 1]

    return None


def _remove_forbidden_fields(value: Any, warnings: list[str]) -> Any:
    """Remove forbidden metadata keys recursively."""
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in FORBIDDEN_FIELDS:
                warnings.append(f"Removed forbidden field: {key}")
                continue
            cleaned[key] = _remove_forbidden_fields(item, warnings)
        return cleaned
    if isinstance(value, list):
        return [_remove_forbidden_fields(item, warnings) for item in value]
    return value


def _normalize_slide_type(index: int, total: int, raw_type: Any) -> tuple[str, str | None]:
    expected = "content"
    if index == 0:
        expected = "title"
    elif index == total - 1:
        expected = "conclusion"

    if raw_type != expected:
        return expected, f"Adjusted slide_type on slide {index + 1} to {expected}"
    return expected, None


def _normalize_outline(outline: dict[str, Any]) -> ParsedOutlineResult:
    warnings: list[str] = []
    cleaned = _remove_forbidden_fields(outline, warnings)

    if not isinstance(cleaned, dict):
        raise OutlineValidationError("Model output must be a JSON object.")

    title = str(cleaned.get("title", "")).strip()
    if title:
        if len(title) > 50:
            title = title[:50].rstrip()
            warnings.append("Trimmed presentation title to 50 characters")
    else:
        raise OutlineValidationError("Outline title is missing.")

    raw_slides = cleaned.get("slides")
    if not isinstance(raw_slides, list):
        raise OutlineValidationError("Outline slides must be a list.")

    normalized_slides: list[dict[str, Any]] = []
    total_slides = len(raw_slides)

    for index, slide in enumerate(raw_slides):
        if not isinstance(slide, dict):
            raise OutlineValidationError(f"Slide {index + 1} must be an object.")

        slide_type, slide_type_warning = _normalize_slide_type(
            index=index,
            total=total_slides,
            raw_type=slide.get("slide_type"),
        )
        if slide_type_warning:
            warnings.append(slide_type_warning)

        constraints = SLIDE_CONSTRAINTS[slide_type]
        slide_title = str(slide.get("title", "")).strip()
        if len(slide_title) > constraints["max_title_length"]:
            slide_title = slide_title[: constraints["max_title_length"]].rstrip()
            warnings.append(f"Trimmed title on slide {index + 1}")

        raw_points = slide.get("content_points", [])
        if isinstance(raw_points, str):
            raw_points = [raw_points]
            warnings.append(f"Wrapped string content_points into a list on slide {index + 1}")
        if not isinstance(raw_points, list):
            raw_points = []

        normalized_points: list[str] = []
        for point in raw_points:
            text = str(point).strip()
            if not text:
                continue
            if len(text) > constraints["max_point_length"]:
                text = text[: constraints["max_point_length"]].rstrip()
                warnings.append(f"Trimmed an overlong point on slide {index + 1}")
            normalized_points.append(text)

        max_points = constraints["max_points"]
        if len(normalized_points) > max_points:
            normalized_points = normalized_points[:max_points]
            warnings.append(f"Trimmed extra content points on slide {index + 1}")

        normalized_slides.append(
            {
                "page_number": index + 1,
                "title": slide_title,
                "content_points": normalized_points,
                "slide_type": slide_type,
            }
        )

    normalized_outline = {
        "title": title,
        "slides": normalized_slides,
    }

    return ParsedOutlineResult(outline=normalized_outline, warnings=list(dict.fromkeys(warnings)))


def parse_outline(raw_text: str) -> ParsedOutlineResult:
    """Parse, repair, normalize, and validate outline JSON."""
    if not raw_text or not raw_text.strip():
        raise OutlineParseError("Model returned empty text.")

    candidates: list[tuple[str, str]] = []
    stripped = strip_code_fences(raw_text)
    candidates.append(("raw", stripped))

    extracted = extract_json_object(stripped)
    if extracted and extracted != stripped:
        candidates.append(("extracted", extracted))

    parsed_data = None
    parse_errors: list[str] = []

    for label, candidate in candidates:
        try:
            parsed_data = json.loads(candidate)
            break
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{label}: {exc}")

    if parsed_data is None and repair_json is not None:
        repair_source = extracted or stripped
        try:
            repaired = repair_json(repair_source)
            parsed_data = json.loads(repaired)
        except Exception as exc:  # pragma: no cover - depends on malformed model output
            parse_errors.append(f"repair: {exc}")

    if parsed_data is None:
        raise OutlineParseError("Unable to parse JSON outline. " + " | ".join(parse_errors))

    normalized = _normalize_outline(parsed_data)

    try:
        validated = OutlineData.model_validate(normalized.outline)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        raise OutlineValidationError(f"{message_en} / {message_zh}") from exc

    return ParsedOutlineResult(
        outline=validated.model_dump(),
        warnings=normalized.warnings,
    )
