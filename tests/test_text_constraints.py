import sys
import unittest
import json
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from llm.outline_parser import parse_outline
from schema import OutlineRequest
from text_constraints import (
    fits_display_limit,
    text_display_units,
    truncate_to_display_limit,
)


class TestScriptAwareLength(unittest.TestCase):
    def test_latin_words_receive_word_based_allowance(self):
        text = "Artificial intelligence supports creative classroom lesson planning"
        self.assertEqual(text_display_units(text), 14)
        self.assertTrue(fits_display_limit(text, 20))

    def test_truncation_never_cuts_latin_word(self):
        text = "Artificial intelligence supports creative classroom lesson planning"
        truncated = truncate_to_display_limit(text, 10)
        self.assertEqual(truncated, "Artificial intelligence supports creative classroom")
        self.assertEqual(truncated.split()[-1], "classroom")

    def test_mixed_chinese_english_is_counted_without_rejecting_terms(self):
        text = "使用 PowerPoint Speaker Notes 辅助课堂讲解"
        self.assertTrue(fits_display_limit(text, 20))

    def test_outline_parser_trims_english_at_word_boundary(self):
        raw = {
            "title": "Teaching Artificial Intelligence",
            "slides": [
                {
                    "page_number": 1,
                    "title": "Teaching Artificial Intelligence Responsibly",
                    "content_points": ["Purpose", "Audience"],
                    "slide_type": "title",
                },
                {
                    "page_number": 2,
                    "title": "Classroom Applications",
                    "content_points": [
                        "Artificial intelligence supports creative classroom lesson planning "
                        "with practical examples for every learner today"
                    ],
                    "slide_type": "content",
                },
                {
                    "page_number": 3,
                    "title": "Practical Activities",
                    "content_points": ["Try one guided activity"],
                    "slide_type": "content",
                },
                {
                    "page_number": 4,
                    "title": "Conclusion",
                    "content_points": ["Review", "Reflect"],
                    "slide_type": "conclusion",
                },
            ],
        }
        result = parse_outline(json.dumps(raw))
        point = result.outline["slides"][1]["content_points"][0]
        self.assertFalse(point.endswith("lear"))
        self.assertTrue(point.endswith("every"))


class TestCleanProductModes(unittest.TestCase):
    def test_product_default_is_creative(self):
        payload = OutlineRequest.model_validate({"topic": "人工智能入门"})
        self.assertEqual(payload.generation_mode, "creative")

    def test_product_schema_rejects_legacy(self):
        with self.assertRaises(ValueError):
            OutlineRequest.model_validate(
                {"topic": "人工智能入门", "generation_mode": "legacy"}
            )

    def test_old_language_field_is_rejected(self):
        with self.assertRaises(ValueError):
            OutlineRequest.model_validate(
                {"topic": "English topic", "language": "en"}
            )


if __name__ == "__main__":
    unittest.main()
