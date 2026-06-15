import sys
import unittest
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from lyrics.lang_detect import classify_line, detect_bilingual_structure, pair_bilingual_lines
from lyrics.parser import parse_lyrics, split_into_slides

class TestLyricsLangDetect(unittest.TestCase):
    def test_classify_line(self):
        self.assertEqual(classify_line("奇异恩典 何等甘甜"), "zh")
        self.assertEqual(classify_line("Amazing grace! how sweet the sound"), "latin")
        self.assertEqual(classify_line("주기도문 (하늘에 계신)"), "ko")
        self.assertEqual(classify_line("きょうは よい 天气 です"), "ja")
        self.assertEqual(classify_line("  "), "unknown")

    def test_detect_bilingual_structure_single(self):
        lines = [
            "奇异恩典 何等甘甜",
            "我罪已得赦免",
            "前我失丧 今被寻回",
            "瞎眼今得看见"
        ]
        res = detect_bilingual_structure(lines)
        self.assertFalse(res["is_bilingual"])
        self.assertEqual(res["primary_script"], "zh")

    def test_detect_bilingual_structure_alternating(self):
        lines = [
            "Amazing grace! how sweet the sound",
            "奇异恩典 何等甘甜",
            "That saved a wretch like me!",
            "我罪已得赦免"
        ]
        res = detect_bilingual_structure(lines)
        self.assertTrue(res["is_bilingual"])
        self.assertEqual(res["format"], "alternating")
        # In alternating mode, the first script encountered is treated as primary
        self.assertEqual(res["primary_script"], "latin")
        self.assertEqual(res["secondary_script"], "zh")

    def test_detect_bilingual_structure_separated(self):
        lines = [
            "奇异恩典 何等甘甜",
            "我罪已得赦免",
            "Amazing grace! how sweet the sound",
            "That saved a wretch like me!"
        ]
        res = detect_bilingual_structure(lines)
        self.assertTrue(res["is_bilingual"])
        self.assertEqual(res["format"], "separated")
        self.assertEqual(res["primary_script"], "zh")
        self.assertEqual(res["secondary_script"], "latin")

    def test_pair_bilingual_lines(self):
        lines = [
            "Amazing grace! how sweet the sound",
            "奇异恩典 何等甘甜",
            "That saved a wretch like me!",
            "我罪已得赦免"
        ]
        struct = detect_bilingual_structure(lines)
        pairs = pair_bilingual_lines(lines, struct)
        self.assertEqual(len(pairs), 2)
        # Latin is primary, Chinese is secondary
        self.assertEqual(pairs[0], ("Amazing grace! how sweet the sound", "奇异恩典 何等甘甜"))
        self.assertEqual(pairs[1], ("That saved a wretch like me!", "我罪已得赦免"))


class TestLyricsParser(unittest.TestCase):
    def test_parse_lyrics_basic(self):
        lyrics = (
            "[Verse 1]\n"
            "奇异恩典 何等甘甜\n"
            "我罪已得赦免\n"
            "\n"
            "副歌\n"
            "Amazing grace (x2)\n"
            "How sweet"
        )
        doc = parse_lyrics(lyrics, title="Amazing Grace")
        self.assertEqual(doc.title, "Amazing Grace")
        self.assertEqual(len(doc.sections), 2)
        
        # [Verse 1] is treated as a line since it's not a standard chorus/bridge marker.
        # Punctuation (brackets) is stripped.
        self.assertEqual(doc.sections[0].section_type, "verse")
        self.assertEqual(len(doc.sections[0].lines), 3)
        self.assertEqual(doc.sections[0].lines[0].text, "Verse 1")
        self.assertEqual(doc.sections[0].lines[1].text, "奇异恩典 何等甘甜")
        self.assertEqual(doc.sections[0].repeat_count, 1)

        # "副歌" is a valid standalone chorus marker.
        self.assertEqual(doc.sections[1].section_type, "chorus")
        self.assertEqual(len(doc.sections[1].lines), 2)
        # "Amazing grace (x2)" extracts repeat count = 2
        self.assertEqual(doc.sections[1].lines[0].text, "Amazing grace")
        self.assertEqual(doc.sections[1].repeat_count, 2)

    def test_split_into_slides_single(self):
        lyrics = (
            "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        )
        doc = parse_lyrics(lyrics, title="Test")
        # Split single language, lines_per_slide = 2
        slides = split_into_slides(doc, lines_per_slide=2, is_bilingual=False)
        # 5 lines total split by 2 per slide:
        # First slide: 2 lines
        # Second slide: 2 lines
        # Third slide: 1 line -> gets merged into Second slide because of the trailing 1-line check
        # So total slides is 2.
        self.assertEqual(len(slides), 2)
        self.assertEqual(slides[0]["lines"], ["Line 1", "Line 2"])
        self.assertEqual(slides[1]["lines"], ["Line 3", "Line 4", "Line 5"])

if __name__ == "__main__":
    unittest.main()
