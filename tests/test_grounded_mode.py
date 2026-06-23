import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app
import llm.client as llm_client
from llm.client import (
    LLMGenerationResult,
    _provider_extra_body,
    build_grounded_fact_table,
)
from llm.prompts import build_fact_extraction_messages, build_messages
from schema import OutlineRequest


def _raw_sparse_outline() -> str:
    return json.dumps(
        {
            "title": "严格材料测试",
            "slides": [
                {
                    "page_number": 1,
                    "title": "课程说明",
                    "content_points": ["课程安排", "报名规则"],
                    "slide_type": "title",
                    "fact_ids": [1],
                },
                {
                    "page_number": 2,
                    "title": "时间",
                    "content_points": ["每周三15:40—16:40"],
                    "slide_type": "content",
                    "fact_ids": [1],
                },
                {
                    "page_number": 3,
                    "title": "录取",
                    "content_points": ["超过名额后抽签"],
                    "slide_type": "content",
                    "fact_ids": [2],
                },
                {
                    "page_number": 4,
                    "title": "总结",
                    "content_points": ["课程免费", "不按报名先后"],
                    "slide_type": "conclusion",
                    "fact_ids": [1, 2],
                },
            ],
        },
        ensure_ascii=False,
    )


class TestGroundedSchema(unittest.TestCase):
    def test_grounded_outline_requires_material(self):
        with self.assertRaises(ValueError):
            OutlineRequest.model_validate(
                {
                    "topic": "只有主题",
                    "generation_mode": "grounded",
                }
            )

    def test_confirmed_fact_table_must_not_be_empty(self):
        with self.assertRaises(ValueError):
            OutlineRequest.model_validate(
                {
                    "reference_text": "课程免费。",
                    "generation_mode": "grounded",
                    "fact_table": [],
                }
            )

    def test_confirmed_fact_ids_must_be_unique(self):
        with self.assertRaises(ValueError):
            OutlineRequest.model_validate(
                {
                    "reference_text": "课程免费。",
                    "generation_mode": "grounded",
                    "fact_table": [
                        {"id": 1, "text": "课程免费。"},
                        {"id": 1, "text": "课程地点为科学教室。"},
                    ],
                }
            )


class TestGroundedFactTable(unittest.TestCase):
    def test_sensitive_model_paraphrase_is_replaced_by_exact_source_clause(self):
        material = (
            "课程共有24个名额。"
            "学生不得擅自拆卸电器或进入配电区域。"
            "课程地点为科学教室。"
        )
        model_facts = [
            {"id": 1, "text": "课程名额为24人。"},
            {"id": 2, "text": "学生不需要拆卸电器。"},
            {"id": 3, "text": "课程地点为科学教室。"},
        ]
        with patch("llm.client.extract_facts", return_value=model_facts):
            facts = build_grounded_fact_table(material)
        texts = [fact["text"] for fact in facts]
        self.assertIn("课程共有24个名额。", texts)
        self.assertIn("学生不得擅自拆卸电器或进入配电区域。", texts)
        self.assertNotIn("学生不需要拆卸电器。", texts)
        self.assertIn("课程地点为科学教室。", texts)

    def test_source_clauses_are_fallback_when_model_extraction_fails(self):
        with patch("llm.client.extract_facts", return_value=[]):
            facts = build_grounded_fact_table("第一周观察土壤。第二周播种。")
        self.assertEqual(
            [fact["text"] for fact in facts],
            ["第一周观察土壤。", "第二周播种。"],
        )

    def test_english_sentences_remain_separate_fallback_facts(self):
        material = "The course is free. Students must bring a laptop."
        with patch("llm.client.extract_facts", return_value=[]):
            facts = build_grounded_fact_table(material)
        self.assertEqual(
            [fact["text"] for fact in facts],
            ["The course is free.", "Students must bring a laptop."],
        )


class TestGroundedPrompt(unittest.TestCase):
    def test_strict_prompt_allows_sparse_content_and_forbids_diagrams(self):
        messages = build_messages(
            topic="课程",
            num_slides=4,
            scenario="teaching",
            output_language="zh",
            reference_text="课程免费。",
            mode="grounded",
            fact_table=[{"id": 1, "text": "课程免费。"}],
        )
        system = messages[0]["content"]
        self.assertIn("内容页：1-5个要点", system)
        self.assertIn("不要生成diagram字段", system)
        self.assertIn("所有编号事实都必须至少表达一次", system)

    def test_confirmed_fact_table_replaces_raw_reference_in_grounded_prompt(self):
        messages = build_messages(
            topic="课程",
            num_slides=4,
            scenario="teaching",
            output_language="zh",
            reference_text="这条原始材料已被用户取消，不应进入提示词。",
            mode="grounded",
            fact_table=[{"id": 1, "text": "用户确认保留：课程免费。"}],
        )
        user_prompt = messages[1]["content"]
        self.assertIn("用户确认保留：课程免费。", user_prompt)
        self.assertNotIn("这条原始材料已被用户取消", user_prompt)

    def test_fact_extraction_preserves_source_language(self):
        messages = build_fact_extraction_messages(
            "La clase usa PowerPoint，并保留 speaker notes。"
        )
        system = messages[0]["content"]
        self.assertIn("保留原材料使用的语言", system)
        self.assertIn("不要翻译", system)

    def test_bilingual_output_is_mandatory_not_optional(self):
        messages = build_messages(
            topic="人工智能素养",
            num_slides=4,
            scenario="teaching",
            output_language="bilingual",
            mode="creative",
        )
        self.assertIn("都必须同时包含简体中文与自然英文", messages[1]["content"])

    def test_creative_material_mode_allows_teaching_expansion_with_boundaries(self):
        messages = build_messages(
            topic="课程",
            num_slides=4,
            scenario="teaching",
            output_language="zh",
            reference_text="课程面向初学者。",
            mode="creative",
        )
        user_prompt = messages[1]["content"]
        self.assertIn("可以补充一般性的教学背景、例子、提问和过渡", user_prompt)
        self.assertIn("不得捏造具体数字", user_prompt)

    def test_dashscope_requests_disable_thinking(self):
        with patch.object(
            llm_client.config,
            "LLM_BASE_URL",
            "https://x.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        ):
            self.assertEqual(_provider_extra_body(), {"enable_thinking": False})


class TestGroundedEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_grounded_end_to_end_prepare_confirm_generate_repair_audit_notes(self):
        """Smoke the whole pilot path without spending cloud tokens.

        Each response is fed into the next endpoint so this catches integration
        drift that isolated endpoint tests cannot see.
        """
        facts = [
            {"id": 1, "text": "课程每周三15:40—16:40。"},
            {"id": 2, "text": "超过名额后采用抽签方式录取。"},
        ]
        initial_payload = json.loads(_raw_sparse_outline())
        initial_payload["slides"].insert(
            -1,
            {
                "page_number": 4,
                "title": "录取补充",
                "content_points": ["抽签决定录取"],
                "slide_type": "content",
                "fact_ids": [2],
            },
        )
        for index, slide in enumerate(initial_payload["slides"], start=1):
            slide["page_number"] = index

        initial_result = LLMGenerationResult(
            raw_text=json.dumps(initial_payload, ensure_ascii=False),
            elapsed_seconds=0.2,
            llm_model="smoke-model",
        )
        repaired_result = LLMGenerationResult(
            raw_text=_raw_sparse_outline(),
            elapsed_seconds=0.1,
            llm_model="smoke-model",
        )
        notes_result = LLMGenerationResult(
            raw_text=json.dumps(
                {"notes": ["开场提示", "时间说明", "录取说明", "总结提示"]},
                ensure_ascii=False,
            ),
            elapsed_seconds=0.1,
            llm_model="smoke-model",
        )

        with (
            patch.object(
                app,
                "build_grounded_fact_table",
                return_value=facts,
            ) as prepare_facts,
            patch.object(
                app,
                "generate_outline_text",
                return_value=initial_result,
            ) as generate_outline,
            patch.object(
                app,
                "repair_grounded_outline_text",
                return_value=repaired_result,
            ) as repair_outline,
            patch.object(
                app,
                "generate_speaker_notes",
                return_value=notes_result,
            ) as generate_notes,
        ):
            prepare_response = self.client.post(
                "/api/prepare-grounded-facts",
                json={
                    "reference_text": (
                        "课程每周三15:40—16:40。"
                        "超过名额后采用抽签方式录取。"
                    ),
                },
            )
            self.assertEqual(prepare_response.status_code, 200)
            prepared = prepare_response.get_json()
            confirmed_facts = prepared["fact_table"]

            outline_response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "科学课程",
                    "reference_text": "教师确认后的原始课程材料",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": confirmed_facts,
                },
            )
            self.assertEqual(outline_response.status_code, 200)
            generated = outline_response.get_json()
            audit = generated["generation_audit"]
            self.assertTrue(audit["retry_attempted"])
            self.assertTrue(audit["retry_succeeded"])
            self.assertEqual(audit["initial_slides"], 5)
            self.assertEqual(audit["retry_slides"], 4)
            self.assertEqual(audit["final_fact_coverage"], 1.0)
            self.assertEqual(audit["missing_fact_ids"], [])
            self.assertEqual(audit["invalid_fact_ids"], [])
            self.assertEqual(audit["ungrounded_content_pages"], [])

            notes_response = self.client.post(
                "/api/generate-notes",
                json={
                    "outline": generated["outline"],
                    "output_language": "zh",
                    "duration": 10,
                    "style": "classroom",
                    "generation_mode": "grounded",
                    "fact_table": generated["fact_table"],
                },
            )
            self.assertEqual(notes_response.status_code, 200)
            notes = notes_response.get_json()
            self.assertEqual(len(notes["notes"]), 4)
            self.assertEqual(notes["generation_mode"], "grounded")

        prepare_facts.assert_called_once()
        self.assertEqual(generate_outline.call_args.kwargs["fact_table"], facts)
        self.assertEqual(repair_outline.call_args.kwargs["fact_table"], facts)
        self.assertEqual(generate_notes.call_args.kwargs["fact_table"], facts)

    def test_prepare_facts_endpoint_returns_reviewable_table(self):
        facts = [
            {"id": 1, "text": "课程免费。"},
            {"id": 2, "text": "课程地点为科学教室。"},
        ]
        with patch.object(app, "build_grounded_fact_table", return_value=facts) as build:
            response = self.client.post(
                "/api/prepare-grounded-facts",
                json={
                    "reference_text": "课程免费。课程地点为科学教室。",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["fact_table"], facts)
        self.assertEqual(data["fact_count"], 2)
        self.assertEqual(data["fact_table_source"], "extracted")
        build.assert_called_once_with("课程免费。课程地点为科学教室。")

    def test_outline_endpoint_uses_grounded_pipeline_and_returns_facts(self):
        fake_result = LLMGenerationResult(
            raw_text=_raw_sparse_outline(),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "每周三15:40—16:40。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with patch.object(
            app,
            "generate_outline_text",
            return_value=fake_result,
        ) as generate:
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "课程",
                    "reference_text": "课程材料",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["generation_mode"], "grounded")
        self.assertEqual(data["fact_table"], facts)
        self.assertEqual(len(data["outline"]["slides"][1]["content_points"]), 1)
        self.assertEqual(data["generation_audit"]["final_fact_coverage"], 1.0)
        self.assertFalse(data["generation_audit"]["retry_attempted"])
        kwargs = generate.call_args.kwargs
        self.assertEqual(kwargs["mode"], "grounded")
        self.assertEqual(kwargs["temperature"], 0.2)
        self.assertEqual(kwargs["fact_table"], facts)

    def test_outline_endpoint_uses_confirmed_facts_without_reextracting(self):
        fake_result = LLMGenerationResult(
            raw_text=_raw_sparse_outline(),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        confirmed_facts = [
            {"id": 1, "text": "教师确认：课程免费。"},
            {"id": 2, "text": "教师确认：超过名额后抽签。"},
        ]
        with (
            patch.object(
                app,
                "build_grounded_fact_table",
                side_effect=AssertionError("confirmed facts must not be re-extracted"),
            ),
            patch.object(app, "generate_outline_text", return_value=fake_result) as generate,
        ):
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "课程",
                    "reference_text": "原始课程材料",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": confirmed_facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["fact_table"], confirmed_facts)
        self.assertEqual(data["fact_table_source"], "confirmed")
        self.assertEqual(generate.call_args.kwargs["fact_table"], confirmed_facts)

    def test_grounded_missing_fact_is_returned_in_generation_audit(self):
        payload = json.loads(_raw_sparse_outline())
        for slide in payload["slides"]:
            slide["fact_ids"] = [1]
        fake_result = LLMGenerationResult(
            raw_text=json.dumps(payload, ensure_ascii=False),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "课程免费。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with patch.object(app, "generate_outline_text", return_value=fake_result):
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "reference_text": "课程材料",
                    "num_slides": 4,
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["generation_audit"]["missing_fact_ids"], [2])
        self.assertNotIn("warnings", data)

    def test_outline_endpoint_rejects_explicit_empty_confirmed_facts(self):
        response = self.client.post(
            "/api/generate-outline",
            json={
                "reference_text": "课程材料",
                "generation_mode": "grounded",
                "fact_table": [],
            },
        )
        self.assertEqual(response.status_code, 422)

    def test_notes_endpoint_inherits_grounded_facts(self):
        fake_result = LLMGenerationResult(
            raw_text='{"notes":["a","b","c","d"]}',
            elapsed_seconds=0.1,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "课程免费。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with patch.object(
            app,
            "generate_speaker_notes",
            return_value=fake_result,
        ) as generate:
            response = self.client.post(
                "/api/generate-notes",
                json={
                    "outline": json.loads(_raw_sparse_outline()),
                    "output_language": "zh",
                    "duration": 10,
                    "style": "classroom",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        kwargs = generate.call_args.kwargs
        self.assertEqual(kwargs["mode"], "grounded")
        self.assertEqual(kwargs["temperature"], 0.2)
        self.assertEqual(kwargs["fact_table"], facts)

    def test_grounded_count_mismatch_retries_once_and_still_never_trims(self):
        payload = json.loads(_raw_sparse_outline())
        payload["slides"].insert(
            -1,
            {
                "page_number": 4,
                "title": "额外事实",
                "content_points": ["不能静默删除"],
                "slide_type": "content",
                "fact_ids": [1],
            },
        )
        for index, slide in enumerate(payload["slides"], start=1):
            slide["page_number"] = index
        fake_result = LLMGenerationResult(
            raw_text=json.dumps(payload, ensure_ascii=False),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "不能静默删除。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with (
            patch.object(app, "generate_outline_text", return_value=fake_result),
            patch.object(
                app,
                "repair_grounded_outline_text",
                return_value=fake_result,
            ) as repair,
        ):
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "课程",
                    "reference_text": "课程材料",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 502)
        self.assertIn("未自动裁页", response.get_json()["error"])
        self.assertEqual(repair.call_count, 1)
        audit = response.get_json()["generation_audit"]
        self.assertTrue(audit["retry_attempted"])
        self.assertFalse(audit["retry_succeeded"])
        self.assertEqual(audit["initial_slides"], 5)
        self.assertEqual(audit["retry_slides"], 5)

    def test_grounded_count_mismatch_is_repaired_once_with_previous_outline(self):
        payload = json.loads(_raw_sparse_outline())
        payload["slides"].insert(
            -1,
            {
                "page_number": 4,
                "title": "额外事实",
                "content_points": ["等待合并"],
                "slide_type": "content",
                "fact_ids": [2],
            },
        )
        for index, slide in enumerate(payload["slides"], start=1):
            slide["page_number"] = index
        initial = LLMGenerationResult(
            raw_text=json.dumps(payload, ensure_ascii=False),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        repaired = LLMGenerationResult(
            raw_text=_raw_sparse_outline(),
            elapsed_seconds=0.1,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "每周三上课。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with (
            patch.object(app, "generate_outline_text", return_value=initial),
            patch.object(
                app,
                "repair_grounded_outline_text",
                return_value=repaired,
            ) as repair,
        ):
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "课程",
                    "reference_text": "课程材料",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data["outline"]["slides"]), 4)
        self.assertTrue(data["generation_audit"]["retry_attempted"])
        self.assertTrue(data["generation_audit"]["retry_succeeded"])
        self.assertEqual(data["generation_audit"]["initial_slides"], 5)
        self.assertEqual(data["generation_audit"]["retry_slides"], 4)
        self.assertEqual(data["elapsed_seconds"], 0.3)
        repair_kwargs = repair.call_args.kwargs
        self.assertEqual(
            len(repair_kwargs["previous_outline"]["slides"]),
            5,
        )
        self.assertEqual(repair_kwargs["target_slides"], 4)

    def test_grounded_shortfall_below_schema_minimum_can_still_be_repaired(self):
        payload = json.loads(_raw_sparse_outline())
        del payload["slides"][2]
        for index, slide in enumerate(payload["slides"], start=1):
            slide["page_number"] = index
        initial = LLMGenerationResult(
            raw_text=json.dumps(payload, ensure_ascii=False),
            elapsed_seconds=0.2,
            llm_model="test-model",
        )
        repaired = LLMGenerationResult(
            raw_text=_raw_sparse_outline(),
            elapsed_seconds=0.1,
            llm_model="test-model",
        )
        facts = [
            {"id": 1, "text": "每周三上课。"},
            {"id": 2, "text": "超过名额后抽签。"},
        ]
        with (
            patch.object(app, "generate_outline_text", return_value=initial),
            patch.object(
                app,
                "repair_grounded_outline_text",
                return_value=repaired,
            ) as repair,
        ):
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "reference_text": "课程材料",
                    "num_slides": 4,
                    "output_language": "zh",
                    "generation_mode": "grounded",
                    "fact_table": facts,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["generation_audit"]["initial_slides"], 3)
        self.assertTrue(response.get_json()["generation_audit"]["retry_succeeded"])
        self.assertEqual(
            len(repair.call_args.kwargs["previous_outline"]["slides"]),
            3,
        )


if __name__ == "__main__":
    unittest.main()
