"""
Lightweight language detection — Unicode range based, no external dependencies.

Only needs to distinguish which script a line belongs to so the renderer
can pick the right font and the parser can pair bilingual lines.
"""

import re

# Unicode ranges for script classification
SCRIPT_RANGES: dict[str, list[tuple[int, int]]] = {
    "zh": [
        (0x4E00, 0x9FFF),   # CJK Unified Ideographs
        (0x3400, 0x4DBF),   # CJK Extension A
        (0xF900, 0xFAFF),   # CJK Compatibility Ideographs
        (0x20000, 0x2A6DF), # CJK Extension B
    ],
    "ko": [
        (0xAC00, 0xD7AF),   # Hangul Syllables
        (0x1100, 0x11FF),   # Hangul Jamo
        (0x3130, 0x318F),   # Hangul Compatibility Jamo
    ],
    "ja": [
        (0x3040, 0x309F),   # Hiragana
        (0x30A0, 0x30FF),   # Katakana
    ],
    "latin": [
        (0x0041, 0x024F),   # Basic Latin + Latin Extended
    ],
}

# Punctuation / whitespace to ignore when classifying
_STRIP_RE = re.compile(r'[\s\u3000-\u303F\uFF00-\uFFEF\u2000-\u206F.,;:!?\'\"()\[\]{}\-—–…·、。，；：！？""''「」『』【】《》〈〉]')


def _char_script(cp: int) -> str | None:
    """Return the script key for a single code point, or None."""
    # Check ja before zh — hiragana/katakana are uniquely Japanese
    for script in ("ja", "ko", "zh", "latin"):
        for low, high in SCRIPT_RANGES[script]:
            if low <= cp <= high:
                return script
    return None


def classify_line(text: str) -> str:
    """
    Classify a line of text by its dominant script.

    Returns one of: "zh", "ko", "ja", "latin", "mixed", "unknown".
    """
    cleaned = _STRIP_RE.sub('', text)
    if not cleaned:
        return "unknown"

    counts: dict[str, int] = {}
    total = 0
    for ch in cleaned:
        script = _char_script(ord(ch))
        if script:
            counts[script] = counts.get(script, 0) + 1
            total += 1

    if total == 0:
        return "unknown"

    # Find dominant script (> 50% of classified characters)
    for script, count in sorted(counts.items(), key=lambda x: -x[1]):
        if count / total > 0.5:
            return script

    return "mixed"


def detect_bilingual_structure(lines: list[str]) -> dict:
    """
    Detect whether lyrics have a bilingual structure.

    Returns a dict with:
      - is_bilingual: bool
      - format: "alternating" | "separated" | "none"
      - primary_script: str
      - secondary_script: str
      - is_confident: bool — False if detection is ambiguous
      - line_assignments: list of {"line": int, "role": "primary"|"secondary"}
    """
    result = {
        "is_bilingual": False,
        "format": "none",
        "primary_script": "unknown",
        "secondary_script": "unknown",
        "is_confident": False,
        "line_assignments": [],
    }

    if not lines:
        return result

    # Classify every non-empty line
    classifications = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped:
            classifications.append((i, classify_line(stripped)))

    if len(classifications) < 2:
        if classifications:
            result["primary_script"] = classifications[0][1]
        return result

    scripts = [c[1] for c in classifications]
    unique_scripts = {s for s in scripts if s not in ("mixed", "unknown")}

    # All same script — not bilingual
    if len(unique_scripts) <= 1:
        result["primary_script"] = unique_scripts.pop() if unique_scripts else "unknown"
        result["is_confident"] = True
        return result

    if len(unique_scripts) != 2:
        # More than 2 scripts detected — ambiguous
        result["primary_script"] = scripts[0]
        return result

    script_a, script_b = sorted(unique_scripts)

    # Count which script appears more — that's the primary
    count_a = scripts.count(script_a)
    count_b = scripts.count(script_b)
    if count_a >= count_b:
        primary, secondary = script_a, script_b
    else:
        primary, secondary = script_b, script_a

    result["primary_script"] = primary
    result["secondary_script"] = secondary

    # Check alternating pattern (odd/even lines alternate scripts)
    is_alternating = True
    if len(classifications) >= 4:
        for i in range(0, len(classifications) - 1, 2):
            s1 = classifications[i][1]
            s2 = classifications[i + 1][1]
            if s1 == s2:
                is_alternating = False
                break
    else:
        is_alternating = False

    if is_alternating:
        result["is_bilingual"] = True
        result["format"] = "alternating"
        result["is_confident"] = True

        # Determine which script is on even lines
        even_script = classifications[0][1]
        odd_script = classifications[1][1]
        if even_script != primary:
            primary, secondary = secondary, primary
            result["primary_script"] = primary
            result["secondary_script"] = secondary

        for idx, (line_idx, s) in enumerate(classifications):
            role = "primary" if idx % 2 == 0 else "secondary"
            result["line_assignments"].append({"line": line_idx, "role": role})
        return result

    # Check separated pattern (first half one script, second half another)
    mid = len(classifications) // 2
    first_half_scripts = {classifications[i][1] for i in range(mid) if classifications[i][1] not in ("mixed", "unknown")}
    second_half_scripts = {classifications[i][1] for i in range(mid, len(classifications)) if classifications[i][1] not in ("mixed", "unknown")}

    if len(first_half_scripts) == 1 and len(second_half_scripts) == 1 and first_half_scripts != second_half_scripts:
        result["is_bilingual"] = True
        result["format"] = "separated"
        result["is_confident"] = True

        first_script = first_half_scripts.pop()
        result["primary_script"] = first_script
        result["secondary_script"] = second_half_scripts.pop()

        for idx, (line_idx, s) in enumerate(classifications):
            role = "primary" if idx < mid else "secondary"
            result["line_assignments"].append({"line": line_idx, "role": role})
        return result

    # Could not confidently determine structure
    result["is_bilingual"] = True  # there ARE two scripts
    result["format"] = "none"
    result["is_confident"] = False
    for idx, (line_idx, s) in enumerate(classifications):
        role = "primary" if s == primary else "secondary"
        result["line_assignments"].append({"line": line_idx, "role": role})

    return result


def pair_bilingual_lines(
    lines: list[str],
    structure: dict,
) -> list[tuple[str, str]]:
    """
    Pair primary and secondary lines for bilingual rendering.

    Returns a list of (primary_text, secondary_text) tuples.
    If line counts don't match, missing lines are filled with "".
    """
    if not structure.get("is_bilingual"):
        return [(line, "") for line in lines]

    fmt = structure.get("format", "none")
    assignments = structure.get("line_assignments", [])

    if fmt == "alternating" and assignments:
        pairs = []
        i = 0
        while i < len(assignments) - 1:
            a = assignments[i]
            b = assignments[i + 1]
            primary_line = lines[a["line"]] if a["line"] < len(lines) else ""
            secondary_line = lines[b["line"]] if b["line"] < len(lines) else ""
            if a["role"] == "primary":
                pairs.append((primary_line, secondary_line))
            else:
                pairs.append((secondary_line, primary_line))
            i += 2
        # Odd trailing line
        if i < len(assignments):
            a = assignments[i]
            text = lines[a["line"]] if a["line"] < len(lines) else ""
            if a["role"] == "primary":
                pairs.append((text, ""))
            else:
                pairs.append(("", text))
        return pairs

    if fmt == "separated" and assignments:
        primary_lines = [lines[a["line"]] for a in assignments if a["role"] == "primary" and a["line"] < len(lines)]
        secondary_lines = [lines[a["line"]] for a in assignments if a["role"] == "secondary" and a["line"] < len(lines)]
        max_len = max(len(primary_lines), len(secondary_lines))
        pairs = []
        for i in range(max_len):
            p = primary_lines[i] if i < len(primary_lines) else ""
            s = secondary_lines[i] if i < len(secondary_lines) else ""
            pairs.append((p, s))
        return pairs

    # Fallback: best-effort pairing by role
    primary_lines = [lines[a["line"]] for a in assignments if a["role"] == "primary" and a["line"] < len(lines)]
    secondary_lines = [lines[a["line"]] for a in assignments if a["role"] == "secondary" and a["line"] < len(lines)]
    max_len = max(len(primary_lines), len(secondary_lines), 1)
    pairs = []
    for i in range(max_len):
        p = primary_lines[i] if i < len(primary_lines) else ""
        s = secondary_lines[i] if i < len(secondary_lines) else ""
        pairs.append((p, s))
    return pairs
