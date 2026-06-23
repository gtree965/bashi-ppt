"""Script-aware text length rules for editable slide content.

Chinese text is dense enough that a character budget works well. Applying the
same raw-character budget to Latin text truncates words in the middle and makes
English or mixed-language slides unusably terse. These helpers use approximate
visual units instead:

- one CJK character = 1 unit;
- one Latin/number word = 2 units;
- punctuation is inexpensive but still counted.

The limits in ``SLIDE_CONSTRAINTS`` remain the familiar Chinese-character
budgets while Latin and mixed text receive an equivalent word-aware allowance.
"""

from __future__ import annotations

import re


_TOKEN_PATTERN = re.compile(
    r"[\u3400-\u9fff]|"
    r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+)*|"
    r"\s+|.",
    flags=re.UNICODE,
)
_CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")
_WORD_PATTERN = re.compile(
    r"^[A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+)*$",
    flags=re.UNICODE,
)


def _token_half_units(token: str) -> int:
    if token.isspace():
        return 0
    if _CJK_PATTERN.fullmatch(token):
        return 2
    if _WORD_PATTERN.fullmatch(token):
        return 4
    return 1


def text_display_units(text: str) -> float:
    """Return approximate slide-space units for CJK, Latin, or mixed text."""
    half_units = sum(_token_half_units(token) for token in _TOKEN_PATTERN.findall(text or ""))
    return half_units / 2


def fits_display_limit(text: str, limit: int) -> bool:
    return text_display_units(text) <= limit


def truncate_to_display_limit(text: str, limit: int) -> str:
    """Trim at token boundaries without cutting a Latin word in half."""
    clean = (text or "").strip()
    if fits_display_limit(clean, limit):
        return clean

    budget = limit * 2
    used = 0
    kept: list[str] = []
    for token in _TOKEN_PATTERN.findall(clean):
        cost = _token_half_units(token)
        if used + cost > budget:
            break
        kept.append(token)
        used += cost
    return "".join(kept).rstrip(" \t\r\n,，;；:：-—")


def limit_description(limit: int, output_language: str) -> str:
    """Human-readable prompt/UI hint for one display-unit limit."""
    latin_words = max(1, limit // 2)
    if output_language == "en":
        return f"about {latin_words} English words"
    if output_language == "bilingual":
        return f"约{limit}个中文显示单位（英文单词约{latin_words}词，中英合计）"
    return f"约{limit}个中文字符（英文单词约{latin_words}词）"
