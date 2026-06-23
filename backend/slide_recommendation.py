"""Explainable slide-count recommendations for Bashi PPT.

Recommendations are deliberately deterministic: pasting or editing source
material must not trigger an extra cloud-model request. Reference material
always takes precedence over the topic because it defines the available content
boundary. Topic-only recommendations estimate likely scope; the draft-first
workflow recalculates from the generated article before creating its outline.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass


MIN_SLIDES = 4
MAX_SLIDES = 15

_INTRO_WORDS = (
    "入门",
    "简介",
    "概览",
    "初识",
    "介绍",
    "说明",
    "intro",
    "introduction",
    "overview",
    "basics",
)
_BROAD_WORDS = (
    "完整",
    "全面",
    "系统",
    "综合",
    "深入",
    "全景",
    "历史",
    "原因",
    "影响",
    "比较",
    "分析",
    "实践",
    "课程",
    "complete",
    "comprehensive",
    "systematic",
    "history",
    "causes",
    "impact",
    "comparison",
    "analysis",
)


@dataclass(frozen=True)
class SlideRecommendation:
    recommended_slides: int
    basis: str
    reason: str
    content_units: int

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(value: int) -> int:
    return max(MIN_SLIDES, min(MAX_SLIDES, value))


def _visible_length(text: str) -> int:
    cjk = len(re.findall(r"[\u3400-\u9fff]", text))
    latin_word = r"[A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+(?:[-'’][A-Za-zÀ-ÖØ-öø-ÿĀ-ž0-9]+)*"
    latin_words = len(re.findall(latin_word, text))
    # One English word occupies roughly the information space of 2-3 Chinese
    # characters in concise slide bullets.
    return cjk + latin_words * 3


def recommend_from_material(
    material: str,
    *,
    output_language: str = "zh",
    basis: str = "reference_material",
) -> SlideRecommendation:
    text = (material or "").strip()
    if not text:
        raise ValueError("material is required")

    visible_length = _visible_length(text)
    paragraphs = len([part for part in re.split(r"\n\s*\n+", text) if part.strip()])
    nonempty_lines = [line.strip() for line in text.splitlines() if line.strip()]
    list_items = len(
        [
            line
            for line in nonempty_lines
            if re.match(r"^(?:[-*•]|\d+[.)、]|[一二三四五六七八九十]+[、.])", line)
        ]
    )
    sentences = len(
        [
            part
            for part in re.split(r"(?<=[。！？；])|(?<=[.!?;])\s+|\n+", text)
            if part.strip()
        ]
    )

    length_slides = math.ceil(visible_length / 420)
    sentence_slides = math.ceil(sentences / 4)
    structure_slides = math.ceil(max(paragraphs, list_items) / 2)
    content_slides = max(2, length_slides, sentence_slides, structure_slides)
    recommended = _clamp(content_slides + 2)  # title + conclusion
    if output_language == "bilingual":
        recommended = _clamp(recommended + 1)

    basis_label = "生成的备课文章" if basis == "generated_article" else "参考材料"
    reason = (
        f"按{basis_label}的长度、段落和信息点密度估算；"
        f"建议{recommended}页（含标题页和总结页）。"
    )
    return SlideRecommendation(
        recommended_slides=recommended,
        basis=basis,
        reason=reason,
        content_units=max(visible_length, sentences * 80, list_items * 120),
    )


def recommend_from_topic(
    topic: str,
    *,
    scenario: str = "general",
    output_language: str = "zh",
) -> SlideRecommendation:
    clean = re.sub(r"\s+", " ", (topic or "").strip())
    scenario_labels = {
        "teaching": "课堂教学",
        "church": "教会讲座",
        "parents": "家长说明",
        "general": "通用演示",
    }
    baseline = {
        "teaching": 8,
        "church": 7,
        "parents": 7,
        "general": 7,
    }.get(scenario, 7)
    lowered = clean.lower()
    if any(word in lowered for word in _INTRO_WORDS):
        baseline -= 1
    if any(word in lowered for word in _BROAD_WORDS):
        baseline += 1
    if len(clean) >= 28 or re.search(r"[、,，/]|与|和|及", clean):
        baseline += 1
    if output_language == "bilingual":
        baseline += 1
    recommended = _clamp(baseline)
    return SlideRecommendation(
        recommended_slides=recommended,
        basis="topic_scope",
        reason=(
            f"只有主题时，按主题范围和{scenario_labels.get(scenario, '通用演示')}场景"
            f"预估为{recommended}页；"
            "生成备课文章后会按实际内容量重新校准。"
        ),
        content_units=len(clean),
    )


def recommend_slide_count(
    *,
    topic: str = "",
    reference_text: str | None = None,
    scenario: str = "general",
    output_language: str = "zh",
) -> SlideRecommendation:
    if reference_text and reference_text.strip():
        return recommend_from_material(
            reference_text,
            output_language=output_language,
        )
    return recommend_from_topic(
        topic,
        scenario=scenario,
        output_language=output_language,
    )
