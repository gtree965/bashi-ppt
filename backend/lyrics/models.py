"""
Lyrics domain models — parser-internal data structures.

These are NOT Pydantic request/response schemas (those live in schema.py).
These represent the parsed structure of a hymn's lyrics.
"""

from dataclasses import dataclass, field


@dataclass
class LyricLine:
    """A single line of lyrics."""
    text: str
    is_chorus: bool = False
    script: str = "zh"  # classified script: "zh", "ko", "ja", "latin", "mixed", "unknown"


@dataclass
class LyricSection:
    """A verse, chorus, or bridge — a group of contiguous lyric lines."""
    section_type: str  # "verse" | "chorus" | "bridge"
    lines: list[LyricLine] = field(default_factory=list)
    repeat_count: int = 1


@dataclass
class LyricDocument:
    """The fully parsed representation of a hymn."""
    title: str
    sections: list[LyricSection] = field(default_factory=list)

    @property
    def total_lines(self) -> int:
        return sum(len(s.lines) for s in self.sections)
