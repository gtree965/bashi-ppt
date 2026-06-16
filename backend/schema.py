"""
Bashi PPT (巴适PPT) schema — THE single source of truth.

Imported by: prompts.py, outline_parser.py, frontend OutlineEditor, renderer engine.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# =====================================================================
# Slide constraints (used by LLM prompts, validation, and frontend)
# =====================================================================

SLIDE_CONSTRAINTS = {
    "title": {
        "min_points": 2,
        "max_points": 4,
        "max_point_length": 20,   # characters
        "max_title_length": 25,
    },
    "content": {
        "min_points": 3,
        "max_points": 5,
        "max_point_length": 25,   # characters
        "max_title_length": 20,
    },
    "conclusion": {
        "min_points": 2,
        "max_points": 4,
        "max_point_length": 20,   # characters
        "max_title_length": 15,
    },
}

OUTLINE_CONSTRAINTS = {
    "min_slides": 4,
    "max_slides": 15,
    "required_structure": ["title", "content+", "conclusion"],
    # "content+" means one or more content slides
}

ScenarioType = Literal["teaching", "church", "parents", "general"]
LanguageType = Literal["zh", "en", "bilingual"]

VALID_SCENARIOS = ("teaching", "church", "parents", "general")
VALID_LANGUAGES = ("zh", "en", "bilingual")

# =====================================================================
# Pydantic models
# =====================================================================

class SlideData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    page_number: int = Field(ge=1, le=OUTLINE_CONSTRAINTS["max_slides"])
    title: str = Field(min_length=1, max_length=30)
    content_points: List[str] = Field(min_length=1, max_length=5)
    slide_type: Literal["title", "content", "conclusion"]
    image_url: Optional[str] = Field(default=None, description="Optional image URL for the slide")
    diagram: Optional[str] = Field(default=None, description="Optional Mermaid diagram code (content slides only)")
    diagram_image: Optional[str] = Field(default=None, description="Optional base64 data-URL of the rendered hand-drawn diagram")

    @field_validator("content_points")
    @classmethod
    def normalize_content_points(cls, value: List[str]) -> List[str]:
        normalized = []
        for point in value:
            text = str(point).strip()
            if text:
                normalized.append(text)
        return normalized

    @model_validator(mode="after")
    def validate_slide_constraints(self):
        constraints = SLIDE_CONSTRAINTS[self.slide_type]

        if len(self.title) > constraints["max_title_length"]:
            raise ValueError(
                f"{self.slide_type} slide title exceeds {constraints['max_title_length']} characters"
            )

        point_count = len(self.content_points)
        if point_count < constraints["min_points"] or point_count > constraints["max_points"]:
            raise ValueError(
                f"{self.slide_type} slide must have {constraints['min_points']}-"
                f"{constraints['max_points']} content points"
            )

        for point in self.content_points:
            if len(point) > constraints["max_point_length"]:
                raise ValueError(
                    f"{self.slide_type} slide point exceeds {constraints['max_point_length']} characters"
                )

        return self


class OutlineData(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=50)
    slides: List[SlideData] = Field(min_length=4, max_length=15)

    @model_validator(mode="after")
    def validate_outline_structure(self):
        if not self.slides:
            raise ValueError("outline must include slides")

        if self.slides[0].slide_type != "title":
            raise ValueError("first slide must be title")

        if self.slides[-1].slide_type != "conclusion":
            raise ValueError("last slide must be conclusion")

        middle_slides = self.slides[1:-1]
        if not middle_slides:
            raise ValueError("outline must include at least one content slide")

        if any(slide.slide_type != "content" for slide in middle_slides):
            raise ValueError("middle slides must all be content")

        for index, slide in enumerate(self.slides, start=1):
            if slide.page_number != index:
                raise ValueError("page numbers must be sequential starting at 1")

        return self


class OutlineRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    topic: str = Field(min_length=0, max_length=200, default="")
    reference_text: str | None = Field(default=None, max_length=6000)
    num_slides: int = Field(
        default=8,
        ge=OUTLINE_CONSTRAINTS["min_slides"],
        le=OUTLINE_CONSTRAINTS["max_slides"],
    )
    scenario: ScenarioType = Field(default="general")
    language: LanguageType = Field(default="zh")

    @field_validator("reference_text")
    @classmethod
    def normalize_reference_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    @model_validator(mode="after")
    def validate_content_provided(self):
        if not self.topic.strip() and not self.reference_text:
            raise ValueError("Must provide either a topic or reference text")
        return self


class GeneratePptxRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    outline: OutlineData
    template_id: str = Field(default="teaching", min_length=1)


# =====================================================================
# Lyrics schemas
# =====================================================================

LyricsLanguageMode = Literal["single", "bilingual"]
LyricsThemeType = Literal["classic_dark", "deep_blue", "warm_dark"]
LyricsChineseScriptMode = Literal["original", "to_simplified", "to_traditional"]

LYRICS_LANGUAGE_OPTIONS = [
    {"code": "zh", "label": "中文", "native_label": "中文", "script": "zh", "default_font": "Microsoft YaHei"},
    {"code": "en", "label": "English", "native_label": "English", "script": "latin", "default_font": "Arial"},
    {"code": "fr", "label": "Français", "native_label": "Français", "script": "latin", "default_font": "Arial"},
    {"code": "es", "label": "Español", "native_label": "Español", "script": "latin", "default_font": "Arial"},
    {"code": "ko", "label": "한국어", "native_label": "한국어", "script": "ko", "default_font": "Malgun Gothic"},
    {"code": "ja", "label": "日本語", "native_label": "日本語", "script": "ja", "default_font": "Yu Gothic"},
    {"code": "id", "label": "Bahasa Indonesia", "native_label": "Bahasa Indonesia", "script": "latin", "default_font": "Arial"},
    {"code": "pt", "label": "Português", "native_label": "Português", "script": "latin", "default_font": "Arial"},
    {"code": "de", "label": "Deutsch", "native_label": "Deutsch", "script": "latin", "default_font": "Arial"},
]

LYRICS_THEMES_META = [
    {"id": "classic_dark", "name": "经典黑底白字", "background": "#000000", "text_color": "#FFFFFF", "chorus_color": "#FFD700"},
    {"id": "deep_blue", "name": "深蓝渐变", "background": "#0C1445", "text_color": "#FFFFFF", "chorus_color": "#81D4FA"},
    {"id": "warm_dark", "name": "暖色深底", "background": "#1A0A00", "text_color": "#FFF8E1", "chorus_color": "#FFB74D"},
]

LYRICS_MODE_LIMITS = {
    "single": {"min_lines": 2, "max_lines": 4, "default_lines": 4},
    "single_extended": {"min_lines": 2, "max_lines": 6, "default_lines": 4},
    "bilingual": {"min_lines": 2, "max_lines": 3, "default_lines": 2},
}

LYRICS_CHINESE_SCRIPT_OPTIONS = [
    {"id": "original", "name": "原文", "name_en": "Original"},
    {"id": "to_simplified", "name": "转为简体", "name_en": "To Simplified"},
    {"id": "to_traditional", "name": "转为繁體", "name_en": "To Traditional"},
]

VALID_LANGUAGE_CODES = {opt["code"] for opt in LYRICS_LANGUAGE_OPTIONS}


class LanguageConfig(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    primary: str = Field(min_length=1)
    secondary: Optional[str] = None
    primary_label: str = ""
    secondary_label: str = ""

    @field_validator("primary")
    @classmethod
    def validate_primary(cls, v: str) -> str:
        if v not in VALID_LANGUAGE_CODES:
            raise ValueError(f"unsupported language code: {v}")
        return v

    @field_validator("secondary")
    @classmethod
    def validate_secondary(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_LANGUAGE_CODES:
            raise ValueError(f"unsupported language code: {v}")
        return v


class LyricsRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    lyrics: str = Field(min_length=1, max_length=20000)
    title: str = Field(min_length=1, max_length=100)
    lines_per_slide: int = Field(default=4, ge=2, le=6)
    theme: LyricsThemeType = "classic_dark"
    language_mode: LyricsLanguageMode = "single"
    chinese_script_mode: LyricsChineseScriptMode = "original"
    extended_single_lines: bool = False
    language_config: LanguageConfig
    add_title_slide: bool = True
    add_amen_slide: bool = False
    font_family: Optional[str] = None
    font_size_adjustment: int = Field(default=0, ge=-10, le=10)
    line_spacing: float = Field(default=1.5, ge=1.0, le=2.5)

    @model_validator(mode="after")
    def validate_language_consistency(self):
        if self.language_mode == "bilingual":
            if not self.language_config.secondary:
                raise ValueError("bilingual mode requires a secondary language")
            if self.language_config.secondary == self.language_config.primary:
                raise ValueError("primary and secondary languages must be different in bilingual mode")
            if self.chinese_script_mode != "original":
                raise ValueError("chinese script conversion is only available in single-language Chinese mode")
            if self.extended_single_lines:
                raise ValueError("extended single-line mode is only available in single-language mode")
            limits = LYRICS_MODE_LIMITS["bilingual"]
            if self.lines_per_slide < limits["min_lines"] or self.lines_per_slide > limits["max_lines"]:
                raise ValueError(
                    f"bilingual mode requires lines_per_slide between "
                    f"{limits['min_lines']} and {limits['max_lines']}"
                )
        if self.language_mode == "single":
            self.language_config.secondary = None
            if self.language_config.primary != "zh" and self.chinese_script_mode != "original":
                raise ValueError("chinese script conversion is only available when the language is zh")
            limits_key = "single_extended" if self.extended_single_lines else "single"
            limits = LYRICS_MODE_LIMITS[limits_key]
            if self.lines_per_slide < limits["min_lines"] or self.lines_per_slide > limits["max_lines"]:
                raise ValueError(
                    f"single mode requires lines_per_slide between "
                    f"{limits['min_lines']} and {limits['max_lines']}"
                )
        return self


# =====================================================================
# Helpers
# =====================================================================

def error_response(message_zh: str, message_en: str, status_code: int = 400):
    """Standardized bilingual error response."""
    from flask import jsonify
    return jsonify({
        "success": False,
        "error": message_zh,
        "error_en": message_en,
    }), status_code


def format_validation_errors(exc: ValidationError) -> tuple[str, str]:
    """Convert Pydantic validation errors into compact bilingual messages."""
    zh_messages: List[str] = []
    en_messages: List[str] = []

    for error in exc.errors():
        loc = [str(part) for part in error.get("loc", ()) if part != "__root__"]
        field = loc[-1] if loc else "request"
        error_type = error.get("type", "")
        ctx = error.get("ctx", {})

        field_zh = {
            "topic": "主题",
            "reference_text": "参考文章",
            "num_slides": "页数",
            "scenario": "场景",
            "language": "语言",
            "lyrics": "歌词",
            "outline": "大纲",
            "template_id": "模板",
            "title": "标题",
            "slides": "幻灯片",
            "page_number": "页码",
            "content_points": "要点",
            "slide_type": "页面类型",
            "lines_per_slide": "每页行数",
            "theme": "主题样式",
            "language_mode": "语言模式",
            "chinese_script_mode": "中文转换",
            "extended_single_lines": "单语扩展行数",
            "language_config": "语言配置",
            "primary": "主语言",
            "secondary": "副语言",
        }.get(field, field)

        field_en = {
            "topic": "topic",
            "reference_text": "reference article",
            "num_slides": "slide count",
            "scenario": "scenario",
            "language": "language",
            "lyrics": "lyrics",
            "outline": "outline",
            "template_id": "template",
            "title": "title",
            "slides": "slides",
            "page_number": "page number",
            "content_points": "content points",
            "slide_type": "slide type",
            "lines_per_slide": "lines per slide",
            "theme": "theme",
            "language_mode": "language mode",
            "chinese_script_mode": "Chinese script conversion",
            "extended_single_lines": "extended single-line mode",
            "language_config": "language config",
            "primary": "primary language",
            "secondary": "secondary language",
        }.get(field, field)

        if error_type == "missing":
            zh_messages.append(f"{field_zh}为必填项")
            en_messages.append(f"{field_en} is required")
        elif error_type in {"literal_error", "enum"}:
            expected = ctx.get("expected", "")
            if field == "scenario":
                zh_messages.append("场景必须是 teaching、church、parents 或 general")
                en_messages.append("scenario must be one of teaching, church, parents, or general")
            elif field == "language":
                zh_messages.append("语言必须是 zh、en 或 bilingual")
                en_messages.append("language must be one of zh, en, or bilingual")
            else:
                zh_messages.append(f"{field_zh}包含无效值")
                en_messages.append(f"{field_en} contains an invalid value")
        elif error_type in {"string_too_short", "too_short"}:
            minimum = ctx.get("min_length", ctx.get("min_items", 1))
            zh_messages.append(f"{field_zh}长度不能少于{minimum}")
            en_messages.append(f"{field_en} must be at least {minimum} characters/items")
        elif error_type in {"string_too_long", "too_long"}:
            maximum = ctx.get("max_length", ctx.get("max_items", 1))
            zh_messages.append(f"{field_zh}长度不能超过{maximum}")
            en_messages.append(f"{field_en} must not exceed {maximum} characters/items")
        elif error_type in {"greater_than_equal", "less_than_equal", "int_parsing", "int_type"}:
            if field == "num_slides":
                zh_messages.append("页数必须是4到15之间的整数")
                en_messages.append("slide count must be an integer between 4 and 15")
            elif field == "lines_per_slide":
                zh_messages.append("每页行数格式无效")
                en_messages.append("lines per slide has an invalid format")
            else:
                zh_messages.append(f"{field_zh}格式无效")
                en_messages.append(f"{field_en} has an invalid format")
        else:
            message = error.get("msg", "Invalid value")
            zh_messages.append(f"{field_zh}无效: {message}")
            en_messages.append(f"{field_en} is invalid: {message}")

    zh_text = "；".join(dict.fromkeys(zh_messages)) or "请求数据无效"
    en_text = "; ".join(dict.fromkeys(en_messages)) or "Request payload is invalid"
    return zh_text, en_text


def validate_outline_request(data: dict) -> List[str]:
    """Backward-compatible helper used by early Sprint 1 code paths."""
    try:
        OutlineRequest.model_validate(data)
    except ValidationError as exc:
        zh_text, _ = format_validation_errors(exc)
        return zh_text.split("；")
    return []


# =====================================================================
# LLM Settings (used by POST /api/settings/llm)
# =====================================================================

OLLAMA_RECOMMENDED_MODELS = [
    {"id": "gemma4:e2b", "label": "Gemma 4 E2B（快速，约 3.2GB）"},
    {"id": "gemma4:e4b", "label": "Gemma 4 E4B（高质量，约 6.4GB）"},
    {"id": "mistral",    "label": "Mistral 7B（通用）"},
    {"id": "llama3.2",   "label": "Llama 3.2 3B（轻量）"},
]

OPENROUTER_RECOMMENDED_MODELS = [
    {"id": "google/gemma-4-31b-it:free",      "label": "Gemma 4 31B（免费，高质量）"},
    {"id": "meta-llama/llama-3.3-70b-instruct:free", "label": "Llama 3.3 70B（免费，高质量）"},
    {"id": "qwen/qwen3-coder:free",           "label": "Qwen 3 Coder（免费，速度快）"},
    {"id": "meta-llama/llama-3.2-3b-instruct:free", "label": "Llama 3.2 3B（免费，轻量）"},
]


class LLMSettingsRequest(BaseModel):
    """Request body for POST /api/settings/llm."""

    provider: Literal["lmstudio", "ollama", "openrouter"] = "lmstudio"
    model: str = Field(default="", description="Model identifier for the chosen provider")
    api_key: Optional[str] = Field(default=None, description="API key (OpenRouter only)")
    base_url: Optional[str] = Field(default=None, description="Override base URL (advanced)")
    pixabay_api_key: Optional[str] = Field(default=None, description="Pixabay API Key")

    @model_validator(mode="after")
    def validate_openrouter_key(self) -> "LLMSettingsRequest":
        if self.provider == "openrouter" and not (self.api_key or "").strip():
            raise ValueError("OpenRouter 需要 API Key / OpenRouter requires an API key")
        return self
