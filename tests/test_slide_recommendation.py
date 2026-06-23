import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app
from llm.client import LLMGenerationResult
from slide_recommendation import recommend_from_material, recommend_slide_count


def _outline_json(count: int) -> str:
    slides = []
    for index in range(1, count + 1):
        slide_type = "content"
        if index == 1:
            slide_type = "title"
        elif index == count:
            slide_type = "conclusion"
        slides.append(
            {
                "page_number": index,
                "title": f"第{index}页",
                "content_points": ["要点一", "要点二", "要点三"],
                "slide_type": slide_type,
            }
        )
    return json.dumps({"title": "推荐页数测试", "slides": slides}, ensure_ascii=False)


class TestSlideRecommendation(unittest.TestCase):
    def test_longer_material_recommends_more_slides(self):
        short = recommend_from_material("课程免费。每周三上课。")
        long = recommend_from_material(
            "\n\n".join(
                f"第{index}部分：介绍任务、方法、限制和评价要求。"
                for index in range(1, 31)
            )
        )
        self.assertGreater(long.recommended_slides, short.recommended_slides)
        self.assertGreaterEqual(short.recommended_slides, 4)
        self.assertLessEqual(long.recommended_slides, 15)

    def test_reference_material_wins_when_topic_is_also_present(self):
        material = "第一部分。第二部分。第三部分。第四部分。"
        reference_only = recommend_slide_count(reference_text=material)
        both = recommend_slide_count(
            topic="一个非常全面、系统、深入、复杂的历史比较分析课程",
            reference_text=material,
            scenario="teaching",
        )
        self.assertEqual(reference_only.recommended_slides, both.recommended_slides)
        self.assertEqual(both.basis, "reference_material")

    def test_topic_scope_is_explainable(self):
        intro = recommend_slide_count(topic="人工智能入门", scenario="teaching")
        broad = recommend_slide_count(
            topic="人工智能的历史、影响与系统实践分析",
            scenario="teaching",
        )
        self.assertGreater(broad.recommended_slides, intro.recommended_slides)
        self.assertEqual(intro.basis, "topic_scope")

    def test_bilingual_material_gets_extra_space(self):
        material = "课程介绍。学习目标。课堂活动。评价方法。"
        zh = recommend_from_material(material, output_language="zh")
        bilingual = recommend_from_material(material, output_language="bilingual")
        self.assertGreaterEqual(
            bilingual.recommended_slides,
            zh.recommended_slides,
        )

    def test_latin_sentences_and_accented_words_are_counted(self):
        short = "Introducción breve."
        long = (
            "Introducción breve. La información se presenta con claridad. "
            "Los estudiantes analizan ejemplos prácticos. Después comparan resultados. "
            "Finalmente explican sus conclusiones."
        )
        self.assertGreater(
            recommend_from_material(long, output_language="en").content_units,
            recommend_from_material(short, output_language="en").content_units,
        )


class TestSlideRecommendationEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_recommend_endpoint_uses_reference_when_both_present(self):
        response = self.client.post(
            "/api/recommend-slides",
            json={
                "topic": "复杂主题",
                "reference_text": "课程免费。每周三上课。",
                "scenario": "teaching",
                "output_language": "zh",
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["basis"], "reference_material")
        self.assertIn("参考材料", data["reason"])

    def test_outline_auto_mode_uses_backend_recommendation(self):
        recommendation = recommend_slide_count(
            topic="人工智能入门",
            scenario="teaching",
            output_language="zh",
        )

        def fake_generate(**kwargs):
            return LLMGenerationResult(
                raw_text=_outline_json(kwargs["num_slides"]),
                elapsed_seconds=0.1,
                llm_model="test",
            )

        with patch.object(
            app,
            "generate_outline_text",
            side_effect=fake_generate,
        ) as generate:
            response = self.client.post(
                "/api/generate-outline",
                json={
                    "topic": "人工智能入门",
                    "num_slides": 15,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "generation_mode": "creative",
                    "slide_count_mode": "auto",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(
            data["effective_num_slides"],
            recommendation.recommended_slides,
        )
        self.assertEqual(
            generate.call_args.kwargs["num_slides"],
            recommendation.recommended_slides,
        )

    def test_draft_auto_mode_recalibrates_from_generated_article(self):
        article = "\n\n".join(
            f"第{index}部分介绍一个独立的教学重点和课堂活动。"
            for index in range(1, 13)
        )
        expected = recommend_from_material(
            article,
            basis="generated_article",
        ).recommended_slides

        def fake_outline(**kwargs):
            return LLMGenerationResult(
                raw_text=_outline_json(kwargs["num_slides"]),
                elapsed_seconds=0.1,
                llm_model="test",
            )

        with (
            patch.object(
                app,
                "generate_article_text",
                return_value=LLMGenerationResult(
                    raw_text=article,
                    elapsed_seconds=0.1,
                    llm_model="test",
                ),
            ),
            patch.object(
                app,
                "generate_outline_text",
                side_effect=fake_outline,
            ) as generate,
        ):
            response = self.client.post(
                "/api/generate-draft",
                json={
                    "topic": "综合教学主题",
                    "num_slides": 4,
                    "scenario": "teaching",
                    "output_language": "zh",
                    "slide_count_mode": "auto",
                },
            )
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["effective_num_slides"], expected)
        self.assertEqual(data["recommended_slides"], expected)
        self.assertEqual(generate.call_args.kwargs["num_slides"], expected)
        self.assertIn("生成的备课文章", data["slide_recommendation_reason"])


if __name__ == "__main__":
    unittest.main()
