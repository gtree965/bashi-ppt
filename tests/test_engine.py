import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from renderer.engine import _fit_text_in_box

class TestEngine(unittest.TestCase):
    def test_fit_text_in_box_basic(self):
        # Normal fitting with no overflow
        font_size, line_spacing, points, layout_warning = _fit_text_in_box(
            max_height_inches=5.0,
            box_width_inches=6.0,
            content_points=["第一点", "第二点"],
            base_font_size=20,
            min_font_size=14
        )
        self.assertEqual(font_size, 20)
        self.assertFalse(layout_warning)
        self.assertEqual(points, ["第一点", "第二点"])

    def test_fit_text_in_box_truncation(self):
        # Truncation logic when size is extremely small (forcing truncation)
        font_size, line_spacing, points, layout_warning = _fit_text_in_box(
            max_height_inches=0.2, # Very tiny height
            box_width_inches=1.0,
            content_points=["这是一个非常非常长而且无法在小盒子中容纳的点"],
            base_font_size=20,
            min_font_size=14
        )
        self.assertEqual(font_size, 12)
        self.assertTrue(layout_warning)
        # Verify it truncated the string or popped it, ensuring no crash/loop
        self.assertTrue(len(points) == 0 or points[0].endswith("..."))

    def test_fit_text_in_box_infinite_loop_guard(self):
        # Large input designed to trigger loop, validating that it stops
        font_size, line_spacing, points, layout_warning = _fit_text_in_box(
            max_height_inches=0.1,
            box_width_inches=0.5,
            content_points=["A" * 100],
            base_font_size=20,
            min_font_size=14
        )
        self.assertTrue(layout_warning)
        self.assertTrue(len(points) == 0 or len(points[0]) < 100)

if __name__ == "__main__":
    unittest.main()
