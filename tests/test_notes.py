import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from llm.prompts import build_notes_messages
from llm.client import _extract_text_from_reasoning


def _outline():
    return {
        "title": "T",
        "slides": [
            {"page_number": 1, "title": "标题", "content_points": ["a", "b"], "slide_type": "title"},
            {"page_number": 2, "title": "内容", "content_points": ["x", "y", "z"], "slide_type": "content"},
            {"page_number": 3, "title": "结语", "content_points": ["m", "n"], "slide_type": "conclusion"},
        ],
    }


class TestNotesPrompt(unittest.TestCase):
    def test_includes_duration_style_language(self):
        messages = build_notes_messages(_outline(), language="zh", duration_minutes=10, style="classroom")
        system, user = messages[0]["content"], messages[1]["content"]
        self.assertIn("课堂讲解", system)   # style hint
        self.assertIn("10 分钟", user)       # duration budget
        self.assertIn("第2页", user)         # per-slide listing

    def test_article_included_when_present(self):
        messages = build_notes_messages(
            _outline(), language="zh", duration_minutes=5, style="formal", article="文章内容XYZ"
        )
        self.assertIn("文章内容XYZ", messages[1]["content"])

    def test_reasoning_salvage_for_notes(self):
        text = 'think... {"notes":["n1","n2"]} end'
        self.assertEqual(_extract_text_from_reasoning(text, ('"notes"',)), '{"notes":["n1","n2"]}')
        # The default outline-key salvage must NOT grab the notes object.
        self.assertIsNone(_extract_text_from_reasoning(text))


class TestNotesParse(unittest.TestCase):
    def test_parse_variants(self):
        from app import _parse_notes
        self.assertEqual(_parse_notes('{"notes":["a","b"]}'), ["a", "b"])
        self.assertEqual(_parse_notes('["a","b"]'), ["a", "b"])
        self.assertFalse(_parse_notes("not json at all"))  # None or [] → both falsy


class TestNotesRendering(unittest.TestCase):
    def test_notes_embedded_per_slide(self):
        from pptx import Presentation
        from renderer.engine import PPTXRenderer

        outline = {
            "title": "T",
            "slides": [
                {"page_number": 1, "title": "标题", "content_points": ["a", "b"], "slide_type": "title", "notes": "开场白"},
                {"page_number": 2, "title": "内容", "content_points": ["x", "y", "z"], "slide_type": "content", "notes": "讲这页"},
                {"page_number": 3, "title": "结语", "content_points": ["m", "n"], "slide_type": "conclusion"},
            ],
        }
        prs = Presentation(io.BytesIO(PPTXRenderer("teaching").render(outline)))
        self.assertEqual(prs.slides[0].notes_slide.notes_text_frame.text, "开场白")
        self.assertEqual(prs.slides[1].notes_slide.notes_text_frame.text, "讲这页")
        # A slide without notes should not get a notes slide created.
        self.assertFalse(prs.slides[2].has_notes_slide)


if __name__ == "__main__":
    unittest.main()
