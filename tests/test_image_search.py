import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from image_search import rank_pixabay_hits
from llm.client import (
    _sanitize_image_search_phrase,
    _translate_image_query_with_lmstudio,
    translate_to_english,
)


class TestImageSearchQuery(unittest.TestCase):
    def test_non_english_titles_are_decided_by_llm(self):
        titles_and_queries = [
            ("AI 工具的爆发式增长", "artificial intelligence growth"),
            ("人工智能大模型", "large language models"),
            ("角色转变：从码农到架构师", "software architect career"),
            ("编程本质是思维训练", "programming thinking skills"),
            ("我们的核心疑问", "important question discussion"),
        ]
        with patch(
            "llm.client._translate_image_query_with_lmstudio",
            side_effect=[query for _, query in titles_and_queries],
        ) as native_translate:
            for title, expected in titles_and_queries:
                with self.subTest(title=title):
                    self.assertEqual(translate_to_english(title), expected)

        self.assertEqual(
            [call.args[0] for call in native_translate.call_args_list],
            [title for title, _ in titles_and_queries],
        )

    def test_marked_reasoning_answer_is_recovered(self):
        message = SimpleNamespace(
            content="",
            reasoning_content=(
                "Key concepts:\n- classroom\n"
                "FINAL_QUERY: computer programming classroom"
            ),
        )
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: response)
            )
        )
        with (
            patch("llm.client._translate_image_query_with_lmstudio", return_value=None),
            patch("llm.client._build_client", return_value=client),
        ):
            self.assertEqual(
                translate_to_english("创新课堂展示"),
                "computer programming classroom",
            )

    def test_reasoning_fragment_is_never_treated_as_answer(self):
        message = SimpleNamespace(
            content="",
            reasoning_content=(
                '* Source: "角色转变：从码农到架构师"\n'
                "* Key concepts:\n"
                "* Key"
            ),
        )
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **kwargs: response)
            )
        )
        with (
            patch("llm.client._translate_image_query_with_lmstudio", return_value=None),
            patch("llm.client._build_client", return_value=client),
        ):
            self.assertEqual(translate_to_english("未收录的测试标题"), "未收录的测试标题")

    def test_search_phrase_rejects_explanation_without_marker(self):
        self.assertIsNone(
            _sanitize_image_search_phrase(
                "I should avoid a literal metaphor.\nEnglish keywords: creative student"
            )
        )

    def test_plain_content_and_marked_content_are_accepted(self):
        self.assertEqual(
            _sanitize_image_search_phrase("creative student"),
            "creative student",
        )
        self.assertEqual(
            _sanitize_image_search_phrase("FINAL_QUERY: creative student"),
            "creative student",
        )

    def test_lmstudio_native_translation_disables_thinking(self):
        captured = {}

        class FakeResponse:
            def __init__(self, payload):
                self.payload = payload

            def raise_for_status(self):
                return None

            def json(self):
                return self.payload

        class FakeClient:
            def __init__(self, **kwargs):
                captured["client_kwargs"] = kwargs

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def get(self, url, **kwargs):
                captured["models_url"] = url
                return FakeResponse(
                    {
                        "models": [
                            {
                                "type": "llm",
                                "key": "google/gemma-test",
                                "loaded_instances": [{"id": "google/gemma-test"}],
                            }
                        ]
                    }
                )

            def post(self, url, **kwargs):
                captured["url"] = url
                captured["request_kwargs"] = kwargs
                return FakeResponse(
                    {
                        "output": [
                            {
                                "type": "message",
                                "content": "software engineer architect transition",
                            }
                        ],
                        "stats": {"reasoning_output_tokens": 0},
                    }
                )

        with (
            patch("llm.client.config.LLM_PROVIDER", "lmstudio"),
            patch("llm.client.config.LLM_BASE_URL", "http://localhost:1234/v1"),
            patch("llm.client.httpx.Client", FakeClient),
        ):
            translated = _translate_image_query_with_lmstudio("测试标题")

        self.assertEqual(translated, "software engineer architect transition")
        self.assertEqual(captured["url"], "http://localhost:1234/api/v1/chat")
        self.assertEqual(captured["request_kwargs"]["json"]["reasoning"], "off")
        self.assertEqual(
            captured["request_kwargs"]["json"]["model"],
            "google/gemma-test",
        )
        self.assertFalse(captured["request_kwargs"]["json"]["store"])


class TestImageResultRanking(unittest.TestCase):
    def test_unrelated_face_and_tools_are_removed_from_ai_results(self):
        hits = [
            {"id": 1, "tags": "face, makeup, cosmetics", "likes": 500},
            {"id": 2, "tags": "tools, wrench, workshop", "likes": 400},
            {"id": 3, "tags": "artificial intelligence, neural network, technology", "likes": 20},
            {"id": 4, "tags": "ai, digital brain, computer", "likes": 10},
        ]
        ranked = rank_pixabay_hits(
            hits,
            "artificial intelligence neural network",
        )
        self.assertEqual([hit["id"] for hit in ranked], [3, 4])

    def test_general_query_keeps_tag_matches_only(self):
        hits = [
            {"id": 1, "tags": "family, parents, children"},
            {"id": 2, "tags": "mountain, lake, landscape"},
        ]
        ranked = rank_pixabay_hits(hits, "happy family")
        self.assertEqual([hit["id"] for hit in ranked], [1])

    def test_uploader_name_does_not_create_false_match(self):
        hits = [
            {"id": 1, "tags": "mountain, lake", "user": "family_photos"},
            {"id": 2, "tags": "family, parents", "user": "landscape_user"},
        ]
        ranked = rank_pixabay_hits(hits, "happy family")
        self.assertEqual([hit["id"] for hit in ranked], [2])


if __name__ == "__main__":
    unittest.main()
