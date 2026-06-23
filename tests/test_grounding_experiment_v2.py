import importlib.util
import json
import sys
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "backend"
    / "experiments"
    / "grounding_experiment_v2.py"
)
SPEC = importlib.util.spec_from_file_location("grounding_experiment_v2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestGroundingExperimentV2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases, cls.gold = MODULE.selected_cases()

    def test_gold_cases_match_original_cases(self):
        self.assertEqual(
            set(self.cases),
            {
                "reference_only_facts",
                "long_material_compression",
                "church_good_samaritan",
            },
        )
        self.assertEqual(set(self.cases), set(self.gold))

    def test_dashscope_thinking_variants_share_model_and_endpoint(self):
        disabled = MODULE.MODELS["dashscope-qwen37-off"]
        enabled = MODULE.MODELS["dashscope-qwen37-on"]
        self.assertEqual(disabled["model"], "qwen3.7-plus")
        self.assertEqual(disabled["model"], enabled["model"])
        self.assertEqual(disabled["base_url"], enabled["base_url"])
        self.assertFalse(disabled["extra_body"]["enable_thinking"])
        self.assertTrue(enabled["extra_body"]["enable_thinking"])

    def test_provider_payload_includes_requested_thinking_mode(self):
        spec = MODULE.MODELS["dashscope-qwen37-on"]
        payload = MODULE.build_request_payload(
            spec=spec,
            messages=[{"role": "user", "content": "只输出JSON"}],
            temperature=0.2,
        )
        self.assertEqual(payload["model"], "qwen3.7-plus")
        self.assertEqual(payload["temperature"], 0.2)
        self.assertTrue(payload["enable_thinking"])
        self.assertEqual(payload["response_format"], {"type": "json_object"})

    def test_response_metrics_records_reasoning_usage(self):
        metrics = MODULE.response_metrics(
            {
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"ok":true}',
                            "reasoning_content": "先检查格式",
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                    "completion_tokens_details": {"reasoning_tokens": 12},
                },
            }
        )
        self.assertEqual(metrics["reasoning_tokens"], 12)
        self.assertEqual(metrics["reasoning_chars"], 5)
        self.assertEqual(metrics["total_tokens"], 30)

    def test_focused_flag_is_available(self):
        original = sys.argv
        try:
            sys.argv = ["grounding_experiment_v2.py", "--focused"]
            args = MODULE.parse_args()
        finally:
            sys.argv = original
        self.assertTrue(args.focused)

    def test_reference_gold_detects_complete_material(self):
        case = self.cases["reference_only_facts"]
        gold = self.gold["reference_only_facts"]
        observed = [
            fact["id"]
            for fact in gold["facts"]
            if MODULE.fact_matches(case["reference_text"], fact)
        ]
        self.assertEqual(len(observed), len(gold["facts"]))

    def test_seat_count_fact_accepts_number_before_or_after_noun(self):
        gold = self.gold["reference_only_facts"]
        fact = next(item for item in gold["facts"] if item["id"] == 5)
        self.assertTrue(MODULE.fact_matches("课程共有24个名额。", fact))
        self.assertTrue(MODULE.fact_matches("课程名额共24个。", fact))

    def test_long_material_gold_detects_complete_material(self):
        case = self.cases["long_material_compression"]
        gold = self.gold["long_material_compression"]
        observed = [
            fact["id"]
            for fact in gold["facts"]
            if MODULE.fact_matches(case["reference_text"], fact)
        ]
        self.assertEqual(len(observed), len(gold["facts"]))

    def test_evaluation_fact_accepts_natural_ratio_wording(self):
        gold = self.gold["long_material_compression"]
        fact = next(item for item in gold["facts"] if item["id"] == 6)
        text = (
            "调查证据占评价比例的30%。方案可行性占评价比例的30%。"
            "团队合作占评价比例的20%。表达与反思占评价比例的20%。"
        )
        self.assertTrue(MODULE.fact_matches(text, fact))

    def test_forbidden_church_expansion_fails(self):
        case = self.cases["church_good_samaritan"]
        gold = self.gold["church_good_samaritan"]
        raw = json.dumps(
            {
                "title": "测试",
                "slides": [
                    {
                        "page_number": 1,
                        "title": "故事",
                        "content_points": ["耶稣在路加福音第十章讲述"],
                        "slide_type": "title",
                        "fact_ids": [1],
                    },
                    {
                        "page_number": 2,
                        "title": "经过",
                        "content_points": ["祭司和利未人没有停下"],
                        "slide_type": "content",
                        "fact_ids": [2],
                    },
                    {
                        "page_number": 3,
                        "title": "帮助",
                        "content_points": ["撒玛利亚人动了慈心"],
                        "slide_type": "content",
                        "fact_ids": [3],
                    },
                    {
                        "page_number": 4,
                        "title": "行动",
                        "content_points": ["包裹伤口并带到旅店照顾"],
                        "slide_type": "content",
                        "fact_ids": [4, 5],
                    },
                    {
                        "page_number": 5,
                        "title": "总结",
                        "content_points": ["怜悯要落实为行动"],
                        "slide_type": "conclusion",
                        "fact_ids": [8],
                    },
                ],
            },
            ensure_ascii=False,
        )
        score = MODULE.score_output(
            raw,
            workflow="outline",
            expected_count=5,
            material=case["reference_text"],
            gold=gold,
            grounded=True,
        )
        self.assertFalse(score.quality_pass)
        self.assertIn("材料外经文出处", score.forbidden_hits)
        self.assertIn("材料外教义应用", score.forbidden_hits)

    def test_declared_fact_without_support_fails(self):
        case = self.cases["reference_only_facts"]
        gold = self.gold["reference_only_facts"]
        raw = json.dumps(
            {
                "title": "测试",
                "slides": [
                    {
                        "page_number": 1,
                        "title": "课程",
                        "content_points": ["课程介绍"],
                        "slide_type": "title",
                        "fact_ids": [1],
                    },
                    {
                        "page_number": 2,
                        "title": "安排",
                        "content_points": ["内容待定"],
                        "slide_type": "content",
                        "fact_ids": [2],
                    },
                    {
                        "page_number": 3,
                        "title": "总结",
                        "content_points": ["欢迎报名"],
                        "slide_type": "conclusion",
                        "fact_ids": [17],
                    },
                ],
            },
            ensure_ascii=False,
        )
        score = MODULE.score_output(
            raw,
            workflow="outline",
            expected_count=3,
            material=case["reference_text"],
            gold=gold,
            grounded=True,
        )
        self.assertFalse(score.quality_pass)
        self.assertTrue(score.unsupported_declared_ids)
        self.assertTrue(score.unmatched_grounded_points)


if __name__ == "__main__":
    unittest.main()
