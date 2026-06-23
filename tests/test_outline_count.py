import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from llm.outline_parser import parse_outline


def _outline(n: int) -> str:
    """Build a structurally valid outline JSON string with n slides."""
    slides = []
    for i in range(1, n + 1):
        if i == 1:
            slide_type = "title"
        elif i == n:
            slide_type = "conclusion"
        else:
            slide_type = "content"
        slides.append(
            {
                "page_number": i,
                "title": f"第{i}页",
                "content_points": ["要点一", "要点二", "要点三"],
                "slide_type": slide_type,
            }
        )
    return json.dumps({"title": "测试大纲", "slides": slides}, ensure_ascii=False)


class TestSlideCountReconcile(unittest.TestCase):
    def test_surplus_is_trimmed_to_requested(self):
        result = parse_outline(_outline(9), expected_slides=7)
        slides = result.outline["slides"]
        self.assertEqual(len(slides), 7)
        self.assertEqual([s["page_number"] for s in slides], list(range(1, 8)))
        self.assertEqual(slides[0]["slide_type"], "title")
        self.assertEqual(slides[-1]["slide_type"], "conclusion")
        self.assertTrue(any("Trimmed" in w for w in result.warnings))

    def test_exact_count_is_untouched(self):
        result = parse_outline(_outline(7), expected_slides=7)
        self.assertEqual(len(result.outline["slides"]), 7)
        self.assertFalse(any("Trimmed" in w for w in result.warnings))

    def test_shortfall_is_flagged_not_fabricated(self):
        result = parse_outline(_outline(5), expected_slides=7)
        # We never fabricate slides; the deck stays valid and a warning is raised.
        self.assertEqual(len(result.outline["slides"]), 5)
        self.assertTrue(any("7 were requested" in w for w in result.warnings))

    def test_no_expected_count_keeps_model_output(self):
        result = parse_outline(_outline(6))
        self.assertEqual(len(result.outline["slides"]), 6)

    def test_at_least_one_content_slide_survives_aggressive_trim(self):
        # Requesting fewer than structurally possible must still keep title +
        # one content + conclusion (min 3), never drop the only content slide.
        result = parse_outline(_outline(8), expected_slides=4)
        slides = result.outline["slides"]
        self.assertGreaterEqual(len(slides), 4)
        self.assertEqual(slides[0]["slide_type"], "title")
        self.assertEqual(slides[-1]["slide_type"], "conclusion")
        self.assertTrue(any(s["slide_type"] == "content" for s in slides))


if __name__ == "__main__":
    unittest.main()
