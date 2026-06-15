import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from renderer.utils import hex_to_rgb
from pptx.dml.color import RGBColor

class TestRendererUtils(unittest.TestCase):
    def test_hex_to_rgb(self):
        self.assertEqual(hex_to_rgb("#FFFFFF"), RGBColor(255, 255, 255))
        self.assertEqual(hex_to_rgb("FF0000"), RGBColor(255, 0, 0))
        self.assertEqual(hex_to_rgb("#00FF00"), RGBColor(0, 255, 0))
        self.assertEqual(hex_to_rgb("0000FF"), RGBColor(0, 0, 255))
        self.assertEqual(hex_to_rgb("#0a0b0c"), RGBColor(10, 11, 12))

if __name__ == "__main__":
    unittest.main()
