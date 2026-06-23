import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from grounding_audit import audit_grounded_outline
from llm.outline_parser import parse_outline
from llm.prompts import build_grounded_repair_messages


class TestGroundingAudit(unittest.TestCase):
    def test_shared_frontend_backend_contract_cases(self):
        fixture_path = (
            Path(__file__).resolve().parent
            / "fixtures"
            / "grounding_audit_contract.json"
        )
        cases = json.loads(fixture_path.read_text(encoding="utf-8"))

        for case in cases:
            with self.subTest(case=case["name"]):
                actual = audit_grounded_outline(
                    case.get("outline"),
                    case.get("fact_table"),
                ).to_dict()
                self.assertEqual(actual, case["expected"])

    def test_reports_coverage_invalid_ids_and_ungrounded_pages(self):
        outline = {
            "slides": [
                {"page_number": 1, "slide_type": "title", "fact_ids": [1]},
                {"page_number": 2, "slide_type": "content", "fact_ids": [1, 99]},
                {"page_number": 3, "slide_type": "content", "fact_ids": []},
                {"page_number": 4, "slide_type": "conclusion", "fact_ids": [2]},
            ]
        }
        audit = audit_grounded_outline(
            outline,
            [
                {"id": 1, "text": "事实一"},
                {"id": 2, "text": "事实二"},
                {"id": 3, "text": "事实三"},
            ],
        )
        self.assertEqual(audit.declared_fact_ids, [1, 2])
        self.assertEqual(audit.missing_fact_ids, [3])
        self.assertEqual(audit.invalid_fact_ids, [99])
        self.assertEqual(audit.ungrounded_content_pages, [3])
        self.assertEqual(audit.fact_coverage, 0.667)
        self.assertFalse(audit.structurally_valid)
        self.assertFalse(audit.complete)

    def test_parser_preserves_and_normalizes_fact_ids(self):
        raw = {
            "title": "事实编号",
            "slides": [
                {
                    "page_number": 1,
                    "title": "首页",
                    "content_points": ["事实", "范围"],
                    "slide_type": "title",
                    "fact_ids": [1, 1, "2"],
                },
                {
                    "page_number": 2,
                    "title": "内容",
                    "content_points": ["事实一"],
                    "slide_type": "content",
                    "fact_ids": [1],
                },
                {
                    "page_number": 3,
                    "title": "内容二",
                    "content_points": ["事实二"],
                    "slide_type": "content",
                    "fact_ids": [2],
                },
                {
                    "page_number": 4,
                    "title": "总结",
                    "content_points": ["回顾", "完成"],
                    "slide_type": "conclusion",
                    "fact_ids": [1, 2],
                },
            ],
        }
        result = parse_outline(json.dumps(raw, ensure_ascii=False))
        self.assertEqual(result.outline["slides"][0]["fact_ids"], [1])
        self.assertTrue(any("invalid fact ID" in item for item in result.warnings))

    def test_repair_prompt_is_directional_and_reuses_previous_outline(self):
        previous = {
            "title": "课程",
            "slides": [
                {"page_number": index, "title": f"第{index}页", "fact_ids": [1]}
                for index in range(1, 7)
            ],
        }
        messages = build_grounded_repair_messages(
            previous_outline=previous,
            target_slides=4,
            output_language="zh",
            fact_table=[{"id": 1, "text": "课程免费。"}],
            missing_fact_ids=[1],
        )
        prompt = messages[1]["content"]
        self.assertIn("当前多出 2 页", prompt)
        self.assertIn("合并主题相近的内容页", prompt)
        self.assertIn("上一版大纲", prompt)
        self.assertIn('"slides"', prompt)
        self.assertIn("尚未声明覆盖这些事实编号：1", prompt)


if __name__ == "__main__":
    unittest.main()
