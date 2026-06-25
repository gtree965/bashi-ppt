"""Local, file-based project store for Bashi PPT.

Projects are saved as one human-readable JSON file each under ``projects/`` in
the app root (portable, travels with the extracted release). Everything stays
on the user's machine — nothing here is transmitted.

A project file looks like::

    {
      "id": "<hex>",
      "title": "...",
      "created_at": "2026-06-24T13:00:00Z",
      "updated_at": "2026-06-24T13:05:00Z",
      "summary": {topic, scenario, generation_mode, slide_count, output_language},
      "state": { ...full frontend snapshot... }
    }
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
# Reject obviously oversized payloads (serialized state) to avoid filling disk.
MAX_STATE_BYTES = 2 * 1024 * 1024


class ProjectStoreError(RuntimeError):
    """Raised for invalid ids or missing projects."""


def projects_dir() -> Path:
    """Return the projects directory, creating it on first use."""
    path = Path(config.PROJECT_ROOT) / "projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _valid_id(project_id: str) -> bool:
    return bool(project_id) and bool(_ID_RE.match(project_id))


def _project_path(project_id: str) -> Path:
    if not _valid_id(project_id):
        raise ProjectStoreError(f"Invalid project id: {project_id!r}")
    return projects_dir() / f"{project_id}.json"


def _derive_summary(state: dict[str, Any]) -> dict[str, Any]:
    """Build a small list-view summary from the frontend state snapshot.

    Defensive: the snapshot shape is owned by the frontend, so every lookup
    falls back safely rather than raising.
    """
    state = state if isinstance(state, dict) else {}
    params = state.get("inputParams") if isinstance(state.get("inputParams"), dict) else {}
    context = state.get("generationContext") if isinstance(state.get("generationContext"), dict) else {}
    outline = state.get("outline") if isinstance(state.get("outline"), dict) else {}
    slides = outline.get("slides") if isinstance(outline.get("slides"), list) else []
    return {
        "topic": str(params.get("topic") or "").strip(),
        "scenario": state.get("scenario") or params.get("scenario") or "",
        "generation_mode": context.get("mode") or params.get("generationMode") or "creative",
        "slide_count": len(slides),
        "output_language": state.get("outputLanguage") or params.get("outputLanguage") or "",
    }


def _summary_record(record: dict[str, Any]) -> dict[str, Any]:
    """The fields returned for list views (no heavy ``state``)."""
    return {
        "id": record.get("id"),
        "title": record.get("title"),
        "created_at": record.get("created_at"),
        "updated_at": record.get("updated_at"),
        "summary": record.get("summary", {}),
    }


def save_project(payload: dict[str, Any]) -> dict[str, Any]:
    """Create or update (upsert by id) a project. Returns the summary record."""
    state = payload.get("state")
    if not isinstance(state, dict):
        raise ProjectStoreError("Project state must be an object.")

    requested_id = str(payload.get("id") or "").strip()
    project_id = requested_id if _valid_id(requested_id) else uuid.uuid4().hex

    if len(json.dumps(state, ensure_ascii=False).encode("utf-8")) > MAX_STATE_BYTES:
        raise ProjectStoreError("Project is too large to save.")

    now = _now_iso()
    created_at = now
    path = _project_path(project_id)
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            created_at = existing.get("created_at") or now
        except Exception:
            created_at = now

    title = str(payload.get("title") or "").strip()[:200] or "未命名项目"
    record = {
        "id": project_id,
        "title": title,
        "created_at": created_at,
        "updated_at": now,
        "summary": _derive_summary(state),
        "state": state,
    }
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return _summary_record(record)


def list_projects(limit: int | None = 5) -> list[dict[str, Any]]:
    """Return project summaries, newest first. ``limit=None``/0 returns all."""
    records: list[dict[str, Any]] = []
    for path in projects_dir().glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue  # skip unreadable / non-project json
        if not isinstance(record, dict) or not record.get("id"):
            continue
        records.append(_summary_record(record))

    records.sort(key=lambda r: r.get("updated_at") or "", reverse=True)
    if limit:
        return records[:limit]
    return records


def load_project(project_id: str) -> dict[str, Any]:
    """Return the full project record (including ``state``)."""
    path = _project_path(project_id)
    if not path.exists():
        raise ProjectStoreError(f"Project not found: {project_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def delete_project(project_id: str) -> bool:
    """Delete a project; returns True if a file was removed."""
    path = _project_path(project_id)
    if path.exists():
        path.unlink()
        return True
    return False
