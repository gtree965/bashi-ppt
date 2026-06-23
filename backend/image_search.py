"""Helpers for producing relevant, presentation-friendly Pixabay results."""

from __future__ import annotations

import math
import re
from typing import Any


_GENERIC_TERMS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "growth",
    "image",
    "of",
    "photo",
    "the",
    "with",
}

_AI_QUERY_TERMS = {
    "ai",
    "artificial",
    "automation",
    "brain",
    "computer",
    "data",
    "digital",
    "intelligence",
    "machine",
    "neural",
    "robot",
    "technology",
}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if token not in _GENERIC_TERMS
    }


def _terms_overlap(query_terms: set[str], tag_terms: set[str]) -> int:
    exact = len(query_terms & tag_terms)
    related = 0
    for query_term in query_terms - tag_terms:
        if len(query_term) < 4:
            continue
        if any(
            len(tag_term) >= 4
            and (query_term.startswith(tag_term) or tag_term.startswith(query_term))
            for tag_term in tag_terms
        ):
            related += 1
    return exact * 3 + related


def rank_pixabay_hits(hits: list[dict[str, Any]], query: str, limit: int = 12) -> list[dict[str, Any]]:
    """Drop obviously unrelated results and rank the rest by tags and popularity."""
    query_terms = _tokens(query)
    if {"artificial", "intelligence"} <= query_terms or "ai" in query_terms:
        query_terms |= _AI_QUERY_TERMS

    ranked: list[tuple[float, int, dict[str, Any]]] = []
    for index, hit in enumerate(hits):
        searchable = " ".join(
            str(hit.get(field) or "")
            for field in ("tags", "pageURL")
        )
        tag_terms = _tokens(searchable)
        semantic_score = _terms_overlap(query_terms, tag_terms)
        if query_terms and semantic_score == 0:
            continue

        popularity = (
            math.log1p(max(int(hit.get("likes") or 0), 0))
            + math.log1p(max(int(hit.get("downloads") or 0), 0)) * 0.15
        )
        ranked.append((semantic_score * 100 + popularity, -index, hit))

    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [hit for _, _, hit in ranked[:limit]]
