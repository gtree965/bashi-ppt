"""
Lyrics parser — converts raw lyrics text into structured LyricDocument,
then splits into slides respecting section boundaries.

No LLM calls, no external dependencies. Pure text processing.
"""

import re

from .models import LyricDocument, LyricLine, LyricSection
from .lang_detect import classify_line

# Section markers that indicate chorus
_CHORUS_MARKERS = re.compile(
    r'^(?:副歌|chorus|refrain|※)\s*[:：]?\s*$',
    re.IGNORECASE,
)

# Section markers that indicate bridge
_BRIDGE_MARKERS = re.compile(
    r'^(?:桥段|bridge|间奏)\s*[:：]?\s*$',
    re.IGNORECASE,
)

# Repeat markers like (x2), (重复), (repeat)
_REPEAT_MARKER = re.compile(
    r'\((?:x(\d+)|重复(\d*)(?:次)?|repeat\s*(\d*))\)',
    re.IGNORECASE,
)


def _semantic_line_count(raw_line_count: int, is_bilingual: bool) -> int:
    """Return display-line count, treating an incomplete bilingual pair as one line."""
    if not is_bilingual:
        return raw_line_count
    return (raw_line_count + 1) // 2


def _extract_repeat_count(text: str) -> tuple[str, int]:
    """Strip repeat markers from text and return (cleaned_text, repeat_count)."""
    match = _REPEAT_MARKER.search(text)
    if not match:
        return text, 1
    count_str = match.group(1) or match.group(2) or match.group(3) or "2"
    count = int(count_str) if count_str else 2
    cleaned = _REPEAT_MARKER.sub('', text).strip()
    return cleaned, count


def parse_lyrics(raw_text: str, title: str = "") -> LyricDocument:
    """
    Parse raw lyrics text into a LyricDocument.

    Steps:
      1. Split by blank lines into raw sections
      2. Detect section markers (chorus/bridge)
      3. Classify each line's script
      4. Build LyricDocument
    """
    lines = raw_text.splitlines()
    sections: list[LyricSection] = []
    current_lines: list[str] = []
    pending_type: str = "verse"
    pending_repeat: int = 1

    def flush_section():
        nonlocal current_lines, pending_type, pending_repeat
        if not current_lines:
            return
        lyric_lines = []
        for raw_line in current_lines:
            text = raw_line.strip()
            if text:
                script = classify_line(text)
                is_chorus = pending_type == "chorus"
                lyric_lines.append(LyricLine(text=text, is_chorus=is_chorus, script=script))
        if lyric_lines:
            sections.append(LyricSection(
                section_type=pending_type,
                lines=lyric_lines,
                repeat_count=pending_repeat,
            ))
        current_lines = []
        pending_type = "verse"
        pending_repeat = 1

    for raw_line in lines:
        stripped = raw_line.strip()

        # Blank line — flush current section
        if not stripped:
            flush_section()
            continue

        # Check for section marker lines
        if _CHORUS_MARKERS.match(stripped):
            flush_section()
            pending_type = "chorus"
            continue

        if _BRIDGE_MARKERS.match(stripped):
            flush_section()
            pending_type = "bridge"
            continue

        # Check for repeat markers within the line
        cleaned, repeat = _extract_repeat_count(stripped)
        if repeat > 1:
            pending_repeat = max(pending_repeat, repeat)
            if cleaned:
                current_lines.append(cleaned)
        else:
            current_lines.append(stripped)

    # Flush remaining
    flush_section()

    return LyricDocument(title=title, sections=sections)


def split_into_slides(
    doc: LyricDocument,
    lines_per_slide: int = 4,
    is_bilingual: bool = False,
) -> list[dict]:
    """
    Split a LyricDocument into slide-sized chunks.

    Returns a list of dicts:
      {"lines": [str, ...], "is_chorus": bool, "type": "lyrics"}

    In bilingual mode, the raw text has interleaved primary/secondary lines
    (e.g. zh/en/zh/en). ``lines_per_slide`` refers to *semantic* lines
    (pairs), so we group raw lines by 2 before counting.

    Rules:
      - Prefer not splitting within a section
      - If a section exceeds lines_per_slide, split at line boundaries
      - Chorus sections repeat (each repeat is a separate slide)
      - Short trailing sections (<=2 lines) merge with the previous slide
      - If the last slide has only 1 line, merge with the previous
    """
    slides: list[dict] = []

    for section in doc.sections:
        for _ in range(section.repeat_count):
            section_lines = [line.text for line in section.lines]
            is_chorus = section.section_type == "chorus"

            if is_bilingual:
                # Group raw lines into pairs so that lines_per_slide counts
                # semantic pairs, not raw interleaved lines.
                # E.g. 8 raw lines with lines_per_slide=2 → 2 chunks of 4 raw lines.
                raw_per_slide = lines_per_slide * 2
            else:
                raw_per_slide = lines_per_slide

            if len(section_lines) <= raw_per_slide:
                # Whole section fits on one slide
                # Try merging short sections with previous slide
                semantic_len = _semantic_line_count(len(section_lines), is_bilingual)
                prev_semantic = _semantic_line_count(len(slides[-1]["lines"]), is_bilingual) if slides else 0
                if (
                    semantic_len <= 2
                    and slides
                    and slides[-1]["type"] == "lyrics"
                    and prev_semantic + semantic_len <= lines_per_slide
                    and not is_chorus
                    and not slides[-1]["is_chorus"]
                ):
                    slides[-1]["lines"].extend(section_lines)
                    if is_bilingual:
                        slides[-1]["pair_count"] = _semantic_line_count(len(slides[-1]["lines"]), True)
                    if is_chorus:
                        slides[-1]["is_chorus"] = True
                else:
                    slide = {
                        "lines": section_lines,
                        "is_chorus": is_chorus,
                        "type": "lyrics",
                    }
                    if is_bilingual:
                        slide["pair_count"] = semantic_len
                    slides.append(slide)
            else:
                # Section too long — split into chunks
                for i in range(0, len(section_lines), raw_per_slide):
                    chunk = section_lines[i:i + raw_per_slide]
                    slide = {
                        "lines": chunk,
                        "is_chorus": is_chorus,
                        "type": "lyrics",
                    }
                    if is_bilingual:
                        slide["pair_count"] = _semantic_line_count(len(chunk), True)
                    slides.append(slide)

    # Merge last slide if it has only 1 semantic line
    if len(slides) >= 2:
        last_semantic = _semantic_line_count(len(slides[-1]["lines"]), is_bilingual)
        if last_semantic == 1:
            last = slides.pop()
            prev_semantic = _semantic_line_count(len(slides[-1]["lines"]), is_bilingual)
            if prev_semantic + last_semantic <= lines_per_slide + 1:
                slides[-1]["lines"].extend(last["lines"])
                if is_bilingual:
                    slides[-1]["pair_count"] = _semantic_line_count(len(slides[-1]["lines"]), True)
            else:
                slides.append(last)

    return slides
