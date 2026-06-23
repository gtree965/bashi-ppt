"""Run one real-cloud grounded workflow smoke test.

This script deliberately uses the application's current .env configuration and
the Flask endpoints that the frontend calls. It prints only operational
metadata and structural audit results; API keys and generated teaching content
are never printed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import app  # noqa: E402
import config  # noqa: E402


REFERENCE_TEXT = (
    "本课程主题为校园植物观察，共持续四周。"
    "学生每周三下午在学校生物园开展一次观察活动。"
    "每组四人，必须记录植物高度、叶片数量和天气情况。"
    "观察期间不得采摘植物，也不得离开教师划定的区域。"
    "第四周每组提交一页观察结论，并在课堂上进行三分钟汇报。"
)


def _require_success(response, stage: str) -> dict:
    payload = response.get_json(silent=True) or {}
    if response.status_code != 200 or not payload.get("success"):
        safe_error = payload.get("error_en") or payload.get("error") or "unknown error"
        raise RuntimeError(
            f"{stage} failed with HTTP {response.status_code}: {safe_error}"
        )
    return payload


def main() -> int:
    provider_host = urlparse(config.LLM_BASE_URL).netloc
    if not config.LLM_API_KEY:
        raise RuntimeError("LLM_API_KEY is not configured")
    if not provider_host:
        raise RuntimeError("LLM_BASE_URL does not identify a cloud provider")

    client = app.app.test_client()

    prepared = _require_success(
        client.post(
            "/api/prepare-grounded-facts",
            json={"reference_text": REFERENCE_TEXT},
        ),
        "prepare",
    )
    fact_table = prepared["fact_table"]

    generated = _require_success(
        client.post(
            "/api/generate-outline",
            json={
                "topic": "校园植物观察",
                "reference_text": REFERENCE_TEXT,
                "num_slides": 4,
                "scenario": "teaching",
                "output_language": "zh",
                "generation_mode": "grounded",
                "slide_count_mode": "manual",
                "fact_table": fact_table,
            },
        ),
        "generate",
    )
    audit = generated.get("generation_audit") or {}
    incomplete = {
        "missing_fact_ids": audit.get("missing_fact_ids") or [],
        "invalid_fact_ids": audit.get("invalid_fact_ids") or [],
        "ungrounded_content_pages": audit.get("ungrounded_content_pages") or [],
    }
    if any(incomplete.values()):
        raise RuntimeError(
            "generate returned an incomplete structural fact mapping: "
            + json.dumps(incomplete, ensure_ascii=False)
        )

    notes = _require_success(
        client.post(
            "/api/generate-notes",
            json={
                "outline": generated["outline"],
                "output_language": "zh",
                "duration": 10,
                "style": "classroom",
                "generation_mode": "grounded",
                "fact_table": generated["fact_table"],
            },
        ),
        "notes",
    )

    print(
        json.dumps(
            {
                "success": True,
                "provider_host": provider_host,
                "model": config.LLM_MODEL,
                "fact_count": prepared["fact_count"],
                "slide_count": len(generated["outline"]["slides"]),
                "note_count": len(notes["notes"]),
                "outline_elapsed_seconds": generated["elapsed_seconds"],
                "notes_elapsed_seconds": notes["elapsed_seconds"],
                "retry_attempted": audit.get("retry_attempted"),
                "retry_succeeded": audit.get("retry_succeeded"),
                "fact_coverage": audit.get("final_fact_coverage"),
                "missing_fact_ids": incomplete["missing_fact_ids"],
                "invalid_fact_ids": incomplete["invalid_fact_ids"],
                "ungrounded_content_pages": incomplete["ungrounded_content_pages"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
