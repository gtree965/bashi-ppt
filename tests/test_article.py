import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from llm.prompts import build_article_user_prompt, build_article_messages
from llm.client import _strip_think_tags


class TestArticlePrompt(unittest.TestCase):
    def test_topic_only(self):
        prompt = build_article_user_prompt(topic="搜索引擎如何工作")
        self.assertIn("主题：搜索引擎如何工作", prompt)
        self.assertNotIn("只整理材料中已有的信息", prompt)

    def test_reference_only_extracts_not_invents(self):
        prompt = build_article_user_prompt(topic="", reference_text="一些参考材料内容")
        self.assertIn("只整理材料中已有的信息", prompt)
        self.assertIn("一些参考材料内容", prompt)

    def test_topic_plus_reference_topic_controls(self):
        prompt = build_article_user_prompt(topic="主题X", reference_text="材料Y")
        self.assertIn("主导方向", prompt)
        self.assertIn("材料Y", prompt)

    def test_correction_includes_prior_and_instruction(self):
        prompt = build_article_user_prompt(
            topic="主题X",
            prior_article="上一版文章内容",
            correction="改成面向小学生",
        )
        self.assertIn("上一版文章内容", prompt)
        self.assertIn("改成面向小学生", prompt)

    def test_messages_shape(self):
        messages = build_article_messages(topic="X", scenario="teaching", language="zh")
        self.assertEqual([m["role"] for m in messages], ["system", "user"])

    def test_strip_think_tags_recovers_prose(self):
        # Freeform reasoning salvage: answer follows the closing tag.
        self.assertEqual(_strip_think_tags("<think>思考...</think>\n文章正文"), "文章正文")
        # No tags → returned as-is (trimmed).
        self.assertEqual(_strip_think_tags("  纯文本  "), "纯文本")


if __name__ == "__main__":
    unittest.main()
