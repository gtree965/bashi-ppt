"""Bashi PPT Flask backend and local frontend server."""

import json
import logging

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from config import (
    APP_VERSION,
    FLASK_PORT,
    FLASK_DEBUG,
    FRONTEND_DIST,
    LOG_FILE,
    TEMPLATES_DIR,
)
from schema import (
    OutlineRequest,
    GroundedFactPreparationRequest,
    SlideRecommendationRequest,
    GenerateNotesRequest,
    ArticleExportRequest,
    LyricsRequest,
    LLMSettingsRequest,
    LYRICS_LANGUAGE_OPTIONS,
    LYRICS_THEMES_META,
    LYRICS_MODE_LIMITS,
    LYRICS_CHINESE_SCRIPT_OPTIONS,
    OLLAMA_RECOMMENDED_MODELS,
    OPENROUTER_RECOMMENDED_MODELS,
    SILICONFLOW_RECOMMENDED_MODELS,
    DASHSCOPE_RECOMMENDED_MODELS,
    PROVIDER_DEFAULTS,
    LOCAL_PROVIDERS,
    CLOUD_API_KEY_PROVIDERS,
    error_response,
    format_validation_errors,
)
from lyrics.chinese_script import ChineseScriptConversionUnavailableError, convert_text
from article_export import build_article_export
from image_search import rank_pixabay_hits
from grounding_audit import audit_grounded_outline
from slide_recommendation import recommend_from_material, recommend_slide_count
from llm.client import (
    LLMReasoningOnlyError,
    LLMTimeoutError,
    LLMUnavailableError,
    OutlineGenerationError,
    check_llm_health,
    build_grounded_fact_table,
    generate_article_text,
    generate_outline_text,
    repair_grounded_outline_text,
    generate_speaker_notes,
)
from llm.outline_parser import (
    OutlineParseError,
    OutlineValidationError,
    parse_outline,
    validate_parsed_outline,
)

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger("slideforge")

# === Flask app ===
app = Flask(__name__, static_folder=str(FRONTEND_DIST), static_url_path="")
CORS(app)


def _split_bilingual_pairs_by_slide(slides: list[dict], all_pairs: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    """
    Distribute bilingual pairs across already-split slides.

    Slides produced by `split_into_slides(..., is_bilingual=True)` carry `pair_count`.
    Fall back to deriving it from raw lines so older slide payloads still work.
    """
    grouped_pairs: list[list[tuple[str, str]]] = []
    pair_idx = 0

    for slide_data in slides:
        pair_count = slide_data.get("pair_count")
        if pair_count is None:
            raw_lines = slide_data.get("lines", [])
            pair_count = (len(raw_lines) + 1) // 2

        pair_count = max(int(pair_count), 0)
        grouped_pairs.append(all_pairs[pair_idx:pair_idx + pair_count])
        pair_idx += pair_count

    if pair_idx < len(all_pairs):
        logger.warning(
            "Bilingual pair distribution mismatch: %s leftover pairs after slide split; appending to final slide.",
            len(all_pairs) - pair_idx,
        )
        if grouped_pairs:
            grouped_pairs[-1].extend(all_pairs[pair_idx:])
        else:
            grouped_pairs.append(all_pairs[pair_idx:])

    return grouped_pairs


def _apply_chinese_script_conversion(payload: LyricsRequest) -> tuple[str, str, str | None]:
    """Apply optional Traditional/Simplified conversion to title and lyrics."""
    mode = payload.chinese_script_mode
    if (
        mode == "original"
        or payload.language_mode != "single"
        or payload.language_config.primary != "zh"
    ):
        return payload.title, payload.lyrics, None

    converted_title = convert_text(payload.title, mode)
    converted_lyrics = convert_text(payload.lyrics, mode)
    if mode == "to_simplified":
        warning = "已按设定将中文原文转换为简体后再进行预览和导出。"
    else:
        warning = "已按设定将中文原文转换为繁體後再进行预览和导出。"
    return converted_title, converted_lyrics, warning


# =====================================================================
# Frontend serving
# =====================================================================

@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")


@app.errorhandler(404)
def fallback(e):
    """SPA fallback: non-API 404s serve index.html."""
    if request.path.startswith("/api/"):
        return error_response("API路径不存在", "API path not found", 404)
    return send_from_directory(app.static_folder, "index.html")


# =====================================================================
# API Routes
# =====================================================================

@app.route("/api/health")
def health():
    """Health check — reports whether the configured LLM endpoint is reachable."""
    llm_connected, llm_model = check_llm_health()
    response = {
        "status": "ok",
        "version": APP_VERSION,
        "llm_connected": llm_connected,
        "llm_model": llm_model,
    }
    return jsonify(response)


@app.route("/api/templates")
def list_templates():
    """Return available template configs."""
    templates = []
    for json_file in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            templates.append(data)
        except Exception as e:
            logger.warning(f"Failed to load template {json_file.name}: {e}")
    return jsonify({"templates": templates})


@app.route("/api/recommend-slides", methods=["POST"])
def recommend_slides():
    """Recommend a page count without making an extra LLM request."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)
    try:
        payload = SlideRecommendationRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    recommendation = recommend_slide_count(
        topic=payload.topic,
        reference_text=payload.reference_text,
        scenario=payload.scenario,
        output_language=payload.output_language,
    )
    return jsonify({"success": True, **recommendation.to_dict()})


@app.route("/api/prepare-grounded-facts", methods=["POST"])
def prepare_grounded_facts():
    """Extract source facts so the user can confirm the content boundary."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)
    try:
        payload = GroundedFactPreparationRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    try:
        fact_table = build_grounded_fact_table(
            payload.reference_text,
        )
        if not fact_table:
            return error_response(
                "未能从参考材料提取可用事实，请检查材料内容或改用教学扩展模式。",
                "No usable facts could be extracted. Check the source material or use creative mode.",
                502,
            )
        return jsonify(
            {
                "success": True,
                "fact_table": fact_table,
                "fact_count": len(fact_table),
                "fact_table_source": "extracted",
            }
        )
    except Exception as exc:  # noqa: BLE001 - map known LLM errors, else 500
        mapped = _llm_error_response(exc)
        if mapped is not None:
            return mapped
        logger.exception("Unexpected error preparing grounded facts: %s", exc)
        return error_response(
            "提取材料事实时出现未知错误。",
            "Unexpected error while extracting source facts.",
            500,
        )


@app.route("/api/generate-outline", methods=["POST"])
def generate_outline():
    """Generate an outline from a topic via the configured LLM."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    try:
        payload = OutlineRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    recommendation = recommend_slide_count(
        topic=payload.topic,
        reference_text=payload.reference_text,
        scenario=payload.scenario,
        output_language=payload.output_language,
    )
    effective_slides = (
        recommendation.recommended_slides
        if payload.slide_count_mode == "auto"
        else payload.num_slides
    )

    logger.info(
        "Generating outline: topic='%s', slides=%s, scenario=%s, output_language=%s, "
        "reference_chars=%s, mode=%s, slide_count_mode=%s",
        payload.topic,
        effective_slides,
        payload.scenario,
        payload.output_language,
        len(payload.reference_text or ""),
        payload.generation_mode,
        payload.slide_count_mode,
    )

    try:
        fact_table: list[dict] = []
        fact_table_source = "none"
        if payload.generation_mode == "grounded":
            fact_table = [fact.model_dump() for fact in payload.fact_table or []]
            fact_table_source = "confirmed"
            if not fact_table:
                return error_response(
                    "未能从参考材料提取可用事实，请检查材料内容或改用教学创作模式。",
                    "No usable facts could be extracted. Check the source material or use creative mode.",
                    502,
                )

        llm_result = generate_outline_text(
            topic=payload.topic,
            num_slides=effective_slides,
            scenario=payload.scenario,
            output_language=payload.output_language,
            reference_text=payload.reference_text,
            temperature=0.2 if payload.generation_mode == "grounded" else None,
            mode=payload.generation_mode,
            fact_table=fact_table or None,
        )
        parsed_result = parse_outline(
            llm_result.raw_text,
            expected_slides=(
                None
                if payload.generation_mode == "grounded"
                else effective_slides
            ),
            validate=payload.generation_mode != "grounded",
        )
        total_elapsed = llm_result.elapsed_seconds
        result_for_response = llm_result
        initial_slides = len(parsed_result.outline["slides"])
        retry_attempted = False
        retry_slides: int | None = None
        retry_succeeded = False
        initial_audit = (
            audit_grounded_outline(parsed_result.outline, fact_table)
            if payload.generation_mode == "grounded"
            else None
        )
        final_audit = initial_audit

        if payload.generation_mode == "grounded" and initial_slides != effective_slides:
            retry_attempted = True
            logger.warning(
                "Grounded outline count mismatch; attempting one directed repair: "
                "model=%s, requested=%s, coverage=%.3f",
                initial_slides,
                effective_slides,
                initial_audit.fact_coverage if initial_audit else 0.0,
            )
            repair_result = repair_grounded_outline_text(
                previous_outline=parsed_result.outline,
                target_slides=effective_slides,
                output_language=payload.output_language,
                fact_table=fact_table,
                missing_fact_ids=(
                    initial_audit.missing_fact_ids if initial_audit else None
                ),
            )
            repaired = parse_outline(
                repair_result.raw_text,
                expected_slides=None,
                validate=False,
            )
            retry_slides = len(repaired.outline["slides"])
            retry_succeeded = retry_slides == effective_slides
            total_elapsed += repair_result.elapsed_seconds
            result_for_response = repair_result
            final_audit = audit_grounded_outline(repaired.outline, fact_table)
            if not retry_succeeded:
                generation_audit = {
                    "recommended_slides": recommendation.recommended_slides,
                    "requested_slides": effective_slides,
                    "initial_slides": initial_slides,
                    "retry_attempted": True,
                    "retry_slides": retry_slides,
                    "retry_succeeded": False,
                    "initial_fact_coverage": initial_audit.fact_coverage,
                    "final_fact_coverage": final_audit.fact_coverage,
                    "fact_count": final_audit.fact_count,
                    "declared_fact_ids": final_audit.declared_fact_ids,
                    "missing_fact_ids": final_audit.missing_fact_ids,
                    "invalid_fact_ids": final_audit.invalid_fact_ids,
                    "ungrounded_content_pages": final_audit.ungrounded_content_pages,
                }
                logger.warning(
                    "Grounded repair failed: requested=%s, initial=%s, retry=%s, "
                    "coverage=%.3f",
                    effective_slides,
                    initial_slides,
                    retry_slides,
                    final_audit.fact_coverage,
                )
                return jsonify(
                    {
                        "success": False,
                        "error": (
                            f"严格材料模式要求 {effective_slides} 页；模型首次返回 "
                            f"{initial_slides} 页，自动修复后仍为 {retry_slides} 页。"
                            "为避免删除事实或编造内容，本次未自动裁页。"
                        ),
                        "error_en": (
                            f"Grounded mode requested {effective_slides} slides; "
                            f"the first result had {initial_slides} and the single repair "
                            f"still had {retry_slides}. No slides were trimmed or invented."
                        ),
                        "generation_audit": generation_audit,
                    }
                ), 502
            parsed_result = repaired

        if payload.generation_mode == "grounded":
            parsed_result = validate_parsed_outline(parsed_result)

        generation_audit = None
        if payload.generation_mode == "grounded" and final_audit is not None:
            generation_audit = {
                "recommended_slides": recommendation.recommended_slides,
                "requested_slides": effective_slides,
                "initial_slides": initial_slides,
                "retry_attempted": retry_attempted,
                "retry_slides": retry_slides,
                "retry_succeeded": retry_succeeded,
                "initial_fact_coverage": initial_audit.fact_coverage,
                "final_fact_coverage": final_audit.fact_coverage,
                "fact_count": final_audit.fact_count,
                "declared_fact_ids": final_audit.declared_fact_ids,
                "missing_fact_ids": final_audit.missing_fact_ids,
                "invalid_fact_ids": final_audit.invalid_fact_ids,
                "ungrounded_content_pages": final_audit.ungrounded_content_pages,
            }

        response = {
            "success": True,
            "outline": parsed_result.outline,
            "elapsed_seconds": round(total_elapsed, 1),
            "llm_model": result_for_response.llm_model,
            "generation_mode": payload.generation_mode,
            "fact_table": fact_table,
            "fact_table_source": fact_table_source,
            "slide_count_mode": payload.slide_count_mode,
            "recommended_slides": recommendation.recommended_slides,
            "effective_num_slides": effective_slides,
            "slide_recommendation_reason": recommendation.reason,
        }
        warnings = list(parsed_result.warnings)
        if generation_audit is not None:
            response["generation_audit"] = generation_audit
        if warnings:
            response["warnings"] = list(dict.fromkeys(warnings))

        logger.info(
            "Outline generation complete: %s slides, %.1fs, retry=%s, "
            "fact_coverage=%s, warnings=%s",
            len(parsed_result.outline["slides"]),
            total_elapsed,
            retry_attempted,
            final_audit.fact_coverage if final_audit else None,
            len(warnings),
        )
        return jsonify(response)
    except LLMUnavailableError as exc:
        logger.warning("LLM unavailable: %s", exc)
        return error_response(
            "LM Studio未连接、未加载模型，或 .env 中的 LLM_MODEL 与当前模型不一致。",
            "LM Studio is unavailable, no model is loaded, or LLM_MODEL does not match the active model.",
            503,
        )
    except LLMTimeoutError as exc:
        logger.warning("LLM timeout: %s", exc)
        return error_response(
            "本地模型响应超时，请检查LM Studio是否正在运行并已加载模型。",
            "The local model timed out. Please check that LM Studio is running and a model is loaded.",
            504,
        )
    except LLMReasoningOnlyError as exc:
        logger.warning("LLM returned reasoning only: %s", exc)
        return error_response(
            "当前模型只返回思考内容，没有输出最终答案。请在LM Studio中关闭思考模式，或改用非推理模型。",
            "The current model returned reasoning only and no final answer. Disable thinking in LM Studio or use a non-reasoning model.",
            502,
        )
    except (OutlineParseError, OutlineValidationError) as exc:
        logger.warning("Invalid model output format: %s", exc)
        return error_response(
            "模型返回的大纲格式无效，请重试或缩短主题描述。",
            "The model returned an invalid outline. Please retry or simplify the topic.",
            502,
        )
    except OutlineGenerationError as exc:
        logger.warning("LLM API Generation Error: %s", exc)
        return error_response(
            f"大纲生成失败 (API 错误): {exc}",
            f"Outline generation failed (API error): {exc}",
            502,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected server error while generating outline: %s", exc)
        return error_response(
            "服务器处理大纲时出现未知错误。",
            "The server encountered an unexpected error while generating the outline.",
            500,
        )


def _llm_error_response(exc: Exception):
    """Map a known LLM exception to a Flask error response, or None if unrecognized."""
    if isinstance(exc, LLMUnavailableError):
        return error_response(
            "LM Studio未连接、未加载模型，或 .env 中的 LLM_MODEL 与当前模型不一致。",
            "LM Studio is unavailable, no model is loaded, or LLM_MODEL does not match the active model.",
            503,
        )
    if isinstance(exc, LLMTimeoutError):
        return error_response(
            "本地模型响应超时，请检查LM Studio是否正在运行并已加载模型。",
            "The local model timed out. Please check that LM Studio is running and a model is loaded.",
            504,
        )
    if isinstance(exc, LLMReasoningOnlyError):
        return error_response(
            "当前模型只返回思考内容，没有输出最终答案。请在LM Studio中关闭思考模式。",
            "The model returned reasoning only. Disable thinking mode in LM Studio.",
            502,
        )
    if isinstance(exc, OutlineGenerationError):
        return error_response(
            f"生成失败 (API 错误): {exc}", f"Generation failed (API error): {exc}", 502
        )
    return None


def _build_draft_response(payload, prior_article: str | None = None, correction: str | None = None):
    """Generate a draft article then an outline derived from it (shared by draft/refine)."""
    try:
        article_result = generate_article_text(
            topic=payload.topic,
            scenario=payload.scenario,
            output_language=payload.output_language,
            reference_text=payload.reference_text,
            prior_article=prior_article,
            correction=correction,
        )
        article = article_result.raw_text.strip()
        if not article:
            return error_response("模型未生成文章内容，请重试。", "The model returned no article. Please retry.", 502)

        if payload.reference_text:
            recommendation = recommend_slide_count(
                topic=payload.topic,
                reference_text=payload.reference_text,
                scenario=payload.scenario,
                output_language=payload.output_language,
            )
        else:
            recommendation = recommend_from_material(
                article,
                output_language=payload.output_language,
                basis="generated_article",
            )
        effective_slides = (
            recommendation.recommended_slides
            if payload.slide_count_mode == "auto"
            else payload.num_slides
        )

        # Outline derived from the article — reuse the existing generator with the
        # article supplied as reference text (topic still steers intent).
        outline_result = generate_outline_text(
            topic=payload.topic,
            num_slides=effective_slides,
            scenario=payload.scenario,
            output_language=payload.output_language,
            reference_text=article,
        )
        parsed = parse_outline(outline_result.raw_text, expected_slides=effective_slides)

        response = {
            "success": True,
            "article": article,
            "outline": parsed.outline,
            "elapsed_seconds": round(article_result.elapsed_seconds + outline_result.elapsed_seconds, 1),
            "llm_model": outline_result.llm_model,
            "generation_mode": "creative",
            "fact_table": [],
            "slide_count_mode": payload.slide_count_mode,
            "recommended_slides": recommendation.recommended_slides,
            "effective_num_slides": effective_slides,
            "slide_recommendation_reason": recommendation.reason,
        }
        if parsed.warnings:
            response["warnings"] = parsed.warnings
        return jsonify(response)
    except (OutlineParseError, OutlineValidationError) as exc:
        logger.warning("Invalid outline from article draft: %s", exc)
        return error_response(
            "模型根据文章生成的大纲格式无效，请重试。",
            "The outline generated from the article was invalid. Please retry.",
            502,
        )
    except Exception as exc:  # noqa: BLE001 - map known LLM errors, else 500
        mapped = _llm_error_response(exc)
        if mapped is not None:
            return mapped
        logger.exception("Unexpected error generating draft: %s", exc)
        return error_response("生成草稿时出现未知错误。", "Unexpected error while generating the draft.", 500)


def _validate_outline_request(data):
    """Return (payload, None) or (None, error_response)."""
    if data is None:
        return None, error_response("请提供JSON数据", "JSON body required", 400)
    try:
        return OutlineRequest.model_validate(data), None
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return None, error_response(message_zh, message_en, 422)


def _is_masked_secret(value: str | None) -> bool:
    """Return True for UI placeholders like sk-...abcd or ********."""
    text = (value or "").strip()
    return bool(text) and ("..." in text or set(text) == {"*"})


def _normalize_provider_base_url(provider: str, base_url: str | None) -> str:
    """Apply provider defaults and local /v1 normalization."""
    normalized = (base_url or PROVIDER_DEFAULTS.get(provider, PROVIDER_DEFAULTS["lmstudio"]) or "").strip()
    if provider in LOCAL_PROVIDERS and normalized:
        clean_url = normalized.rstrip("/")
        if not clean_url.endswith("/v1"):
            normalized = clean_url + "/v1"
    return normalized


def _cloud_test_extra_body(provider: str, base_url: str) -> dict | None:
    """Disable high-cost reasoning by default for providers that support it."""
    lower_url = (base_url or "").lower()
    if provider in {"siliconflow", "dashscope"}:
        return {"enable_thinking": False}
    if "siliconflow" in lower_url or "dashscope.aliyuncs.com" in lower_url or ".maas.aliyuncs.com" in lower_url:
        return {"enable_thinking": False}
    return None


@app.route("/api/generate-draft", methods=["POST"])
def generate_draft():
    """Generate a draft article + an outline derived from it."""
    data = request.get_json(silent=True)
    payload, err = _validate_outline_request(data)
    if err is not None:
        return err
    logger.info("Generating draft: topic='%s', reference_chars=%s", payload.topic, len(payload.reference_text or ""))
    return _build_draft_response(payload)


@app.route("/api/refine-draft", methods=["POST"])
def refine_draft():
    """Regenerate the draft article + outline from a prior article and a correction prompt."""
    data = request.get_json(silent=True)
    outline_data = (
        {key: value for key, value in data.items() if key not in {"prior_article", "correction"}}
        if isinstance(data, dict)
        else data
    )
    payload, err = _validate_outline_request(outline_data)
    if err is not None:
        return err
    prior_article = (data.get("prior_article") or "").strip() or None
    correction = (data.get("correction") or "").strip() or None
    logger.info("Refining draft: topic='%s', has_correction=%s", payload.topic, bool(correction))
    return _build_draft_response(payload, prior_article=prior_article, correction=correction)


@app.route("/api/export-article", methods=["POST"])
def export_article():
    """Download the editable prep article as Markdown, DOCX, or ODT."""
    from io import BytesIO
    from flask import send_file

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)
    try:
        payload = ArticleExportRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    try:
        content, filename, mimetype = build_article_export(
            payload.title,
            payload.article,
            payload.format,
        )
        buffer = BytesIO(content)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype=mimetype,
        )
    except Exception as exc:
        logger.exception("Unexpected error exporting prep article: %s", exc)
        return error_response(
            "导出备课文章时发生错误。",
            "Error exporting prep article.",
            500,
        )


def _parse_notes(raw_text: str) -> list[str] | None:
    """Parse the notes JSON. Returns the raw note list, or None if unparseable."""
    data = None
    try:
        data = json.loads(raw_text)
    except Exception:
        try:
            from json_repair import repair_json
            data = json.loads(repair_json(raw_text))
        except Exception:
            return None

    if isinstance(data, dict):
        notes_list = data.get("notes")
    elif isinstance(data, list):
        notes_list = data
    else:
        notes_list = None
    if not isinstance(notes_list, list):
        return None
    return [str(item).strip() for item in notes_list]


@app.route("/api/generate-notes", methods=["POST"])
def generate_notes():
    """Generate per-slide speaker notes (讲稿) for the current outline."""
    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    try:
        payload = GenerateNotesRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    slides = payload.outline.get("slides")
    if not isinstance(slides, list) or not slides:
        return error_response("请提供完整的大纲数据", "Outline data required", 400)

    if payload.generation_mode == "grounded":
        note_fact_table = [fact.model_dump() for fact in payload.fact_table]
        note_audit = audit_grounded_outline(payload.outline, note_fact_table)
        if (
            note_audit.missing_fact_ids
            or note_audit.invalid_fact_ids
            or note_audit.ungrounded_content_pages
        ):
            return jsonify(
                {
                    "success": False,
                    "error": "请先完成逐页事实对应，再生成严格材料讲稿。",
                    "error_en": (
                        "Complete the per-slide fact mapping before generating "
                        "grounded speaker notes."
                    ),
                    "grounding_audit": note_audit.to_dict(),
                }
            ), 422

    try:
        result = generate_speaker_notes(
            outline=payload.outline,
            output_language=payload.output_language,
            duration_minutes=payload.duration,
            style=payload.style,
            article=payload.article,
            temperature=0.2 if payload.generation_mode == "grounded" else None,
            mode=payload.generation_mode,
            fact_table=[fact.model_dump() for fact in payload.fact_table] or None,
        )
    except Exception as exc:  # noqa: BLE001 - map known LLM errors, else 500
        mapped = _llm_error_response(exc)
        if mapped is not None:
            return mapped
        logger.exception("Unexpected error generating speaker notes: %s", exc)
        return error_response("生成讲稿时出现未知错误。", "Unexpected error while generating speaker notes.", 500)

    parsed = _parse_notes(result.raw_text)
    count = len(slides)
    # A completely unparseable / empty result is a real failure, not success.
    if not parsed or not any(parsed):
        logger.warning("Speaker notes unparseable or empty (%s slides)", count)
        return error_response(
            "未能解析模型返回的讲稿，请重试。",
            "Could not parse speaker notes from the model. Please retry.",
            502,
        )

    warnings: list[str] = []
    if len(parsed) != count:
        warnings.append(f"模型返回 {len(parsed)} 段讲稿，已对齐到 {count} 页。")
        if len(parsed) < count:
            parsed = parsed + [""] * (count - len(parsed))
        else:
            parsed = parsed[:count]

    logger.info("Speaker notes generated: %s slides, %.1fs, warnings=%s", count, result.elapsed_seconds, len(warnings))
    response = {
        "success": True,
        "notes": parsed,
        "elapsed_seconds": round(result.elapsed_seconds, 1),
        "generation_mode": payload.generation_mode,
    }
    if warnings:
        response["warnings"] = warnings
    return jsonify(response)


@app.route("/api/generate-pptx", methods=["POST"])
def generate_pptx():
    """Render PPTX from outline."""
    from renderer.engine import PPTXRenderer
    from io import BytesIO
    from flask import send_file

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)
    
    outline = data.get("outline")
    template_id = data.get("template_id", "teaching")
    bullet_style = data.get("bullet_style", "dot")
    theme_id = data.get("theme_id")
    
    if not outline:
        return error_response("请提供完整的大纲数据", "Outline data required", 400)
        
    try:
        renderer = PPTXRenderer(template_id, theme_id=theme_id)
        pptx_bytes = renderer.render(outline, bullet_style=bullet_style)
        
        buffer = BytesIO(pptx_bytes)
        buffer.seek(0)
        
        filename = f"{outline.get('title', 'Presentation')}.pptx"
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
        )
    except Exception as exc:
        logger.exception("Unexpected error rendering PPTX: %s", exc)
        return error_response(
            "生成PPT时发生错误",
            "Error generating PPTX",
            500,
        )


# =====================================================================
# Lyrics API Routes
# =====================================================================

@app.route("/api/lyrics-config")
def lyrics_config():
    """Return all config the frontend needs for the lyrics UI."""
    return jsonify({
        "languages": LYRICS_LANGUAGE_OPTIONS,
        "themes": LYRICS_THEMES_META,
        "limits": LYRICS_MODE_LIMITS,
        "chinese_script_options": LYRICS_CHINESE_SCRIPT_OPTIONS,
    })


@app.route("/api/preview-lyrics", methods=["POST"])
def preview_lyrics():
    """Preview lyrics slide breakdown without generating PPTX."""
    from lyrics.parser import parse_lyrics, split_into_slides
    from lyrics.lang_detect import detect_bilingual_structure, pair_bilingual_lines

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    try:
        payload = LyricsRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    is_bilingual = payload.language_mode == "bilingual"
    warnings = []

    try:
        title_text, lyrics_text, conversion_warning = _apply_chinese_script_conversion(payload)
    except ChineseScriptConversionUnavailableError:
        return error_response(
            "当前安装缺少繁简转换组件，请重新安装依赖后再使用此功能。",
            "Chinese script conversion is unavailable because this installation is missing the required dependency.",
            503,
        )

    if conversion_warning:
        warnings.append(conversion_warning)

    # Parse lyrics
    doc = parse_lyrics(lyrics_text, title=title_text)

    # Detect bilingual structure
    all_lines = [line.text for section in doc.sections for line in section.lines]
    detected = detect_bilingual_structure(all_lines)

    if is_bilingual and not detected["is_confident"]:
        warnings.append("双语检测信心不足，请检查歌词格式是否为逐行交替或上下分段。")
    if not is_bilingual and detected["is_bilingual"] and detected["is_confident"]:
        warnings.append(f"检测到{detected['format']}格式的双语歌词，建议切换到双语对照模式。")

    # Split into slides
    slides = split_into_slides(doc, payload.lines_per_slide, is_bilingual)

    # For bilingual mode, pair lines so preview matches export
    all_pairs = None
    if is_bilingual:
        all_pairs = pair_bilingual_lines(all_lines, detected)

    # Build preview response
    preview_slides = []
    page = 1
    slide_pair_groups = _split_bilingual_pairs_by_slide(slides, all_pairs) if is_bilingual and all_pairs is not None else []

    if payload.add_title_slide:
        preview_slides.append({"page": page, "type": "title", "lines": [title_text]})
        page += 1

    for slide_index, slide_data in enumerate(slides):
        slide_entry = {
            "page": page,
            "type": "lyrics",
            "is_chorus": slide_data.get("is_chorus", False),
        }

        if is_bilingual and all_pairs is not None:
            # Return paired lines so frontend can render primary/secondary
            slide_pairs = slide_pair_groups[slide_index] if slide_index < len(slide_pair_groups) else []
            slide_entry["pairs"] = [{"primary": p, "secondary": s} for p, s in slide_pairs]
            # Also include flat lines for simple display fallback
            flat = []
            for p, s in slide_pairs:
                flat.append(p)
                if s:
                    flat.append(s)
            slide_entry["lines"] = flat
        else:
            slide_entry["lines"] = slide_data["lines"]

        preview_slides.append(slide_entry)
        page += 1

    if payload.add_amen_slide:
        amen_text = "阿们" if payload.language_config.primary == "zh" else "Amen"
        amen_text = convert_text(amen_text, payload.chinese_script_mode)
        preview_slides.append({"page": page, "type": "amen", "lines": [amen_text]})
        page += 1

    normalized_sections = [
        {"type": s.section_type, "line_count": len(s.lines), "repeat_count": s.repeat_count}
        for s in doc.sections
    ]

    return jsonify({
        "success": True,
        "slides": preview_slides,
        "total_pages": len(preview_slides),
        "detected_structure": detected,
        "warnings": warnings,
        "normalized_sections": normalized_sections,
    })


@app.route("/api/generate-lyrics-pptx", methods=["POST"])
def generate_lyrics_pptx():
    """Generate and download a lyrics PPTX file."""
    from io import BytesIO
    from flask import send_file
    from lyrics.parser import parse_lyrics, split_into_slides
    from lyrics.lang_detect import detect_bilingual_structure, pair_bilingual_lines
    from lyrics.renderer import LyricsPPTXRenderer

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    try:
        payload = LyricsRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    try:
        is_bilingual = payload.language_mode == "bilingual"
        title_text, lyrics_text, _ = _apply_chinese_script_conversion(payload)
        doc = parse_lyrics(lyrics_text, title=title_text)
        slides = split_into_slides(doc, payload.lines_per_slide, is_bilingual)

        bilingual_pairs = None
        if is_bilingual:
            all_lines = [line.text for section in doc.sections for line in section.lines]
            structure = detect_bilingual_structure(all_lines)
            all_pairs = pair_bilingual_lines(all_lines, structure)
            bilingual_pairs = _split_bilingual_pairs_by_slide(slides, all_pairs)

        renderer = LyricsPPTXRenderer()
        lang_cfg = {
            "primary": payload.language_config.primary,
            "secondary": payload.language_config.secondary,
            "script_conversion": payload.chinese_script_mode,
        }
        pptx_bytes = renderer.render(
            slides_data=slides,
            title=title_text,
            theme=payload.theme,
            language_mode=payload.language_mode,
            language_config=lang_cfg,
            add_title_slide=payload.add_title_slide,
            add_amen_slide=payload.add_amen_slide,
            bilingual_pairs=bilingual_pairs,
            font_family=payload.font_family,
            font_size_adjustment=payload.font_size_adjustment,
            line_spacing=payload.line_spacing,
        )

        buffer = BytesIO(pptx_bytes)
        buffer.seek(0)
        filename = f"{title_text}.pptx"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        )
    except ChineseScriptConversionUnavailableError:
        return error_response(
            "当前安装缺少繁简转换组件，请重新安装依赖后再使用此功能。",
            "Chinese script conversion is unavailable because this installation is missing the required dependency.",
            503,
        )
    except Exception as exc:
        logger.exception("Error generating lyrics PPTX: %s", exc)
        return error_response("生成歌词PPT时发生错误", "Error generating lyrics PPTX", 500)


# =====================================================================
# LLM Settings API
# =====================================================================

@app.route("/api/settings/llm", methods=["GET"])
def get_llm_settings():
    """Return current LLM settings (api_key is masked)."""
    import config as cfg
    api_key = cfg.LLM_API_KEY or ""
    masked = (
        api_key[:4] + "..." + api_key[-4:]
        if len(api_key) > 10 else ("*" * len(api_key) if api_key else "")
    )
    pixabay_key = getattr(cfg, "PIXABAY_API_KEY", "") or ""
    pixabay_masked = (
        pixabay_key[:4] + "..." + pixabay_key[-4:]
        if len(pixabay_key) > 8 else ("*" * len(pixabay_key) if pixabay_key else "")
    )
    return jsonify({
        "provider":  cfg.LLM_PROVIDER,
        "base_url":  cfg.LLM_BASE_URL,
        "model":     cfg.LLM_MODEL,
        "api_key_masked": masked,
        "api_key_set": bool(api_key),
        "pixabay_api_key_masked": pixabay_masked,
        "pixabay_api_key_set": bool(pixabay_key),
    })


@app.route("/api/settings/llm", methods=["POST"])
def save_llm_settings():
    """Persist new LLM settings to .env and hot-reload config."""
    import config as cfg
    from config import save_to_env, reload as reload_config

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    try:
        payload = LLMSettingsRequest.model_validate(data)
    except ValidationError as exc:
        message_zh, message_en = format_validation_errors(exc)
        return error_response(message_zh, message_en, 422)

    base_url = _normalize_provider_base_url(payload.provider, payload.base_url)
    api_key = (payload.api_key or "").strip()
    key_is_masked = _is_masked_secret(api_key)
    if payload.provider in CLOUD_API_KEY_PROVIDERS and key_is_masked:
        if payload.provider != cfg.LLM_PROVIDER or not cfg.LLM_API_KEY:
            return error_response(
                "请重新填写当前云端服务的真实 API Key。",
                "Please enter the real API key for the selected cloud provider.",
                422,
            )
    elif payload.provider in CLOUD_API_KEY_PROVIDERS and not api_key:
        return error_response(
            "云端模型需要 API Key。",
            "Cloud providers require an API key.",
            422,
        )
    elif payload.provider == "lmstudio":
        api_key = api_key or "lm-studio"
    elif payload.provider == "ollama":
        api_key = api_key or "ollama"

    model    = payload.model or cfg.LLM_MODEL

    save_data = {
        "LLM_PROVIDER": payload.provider,
        "LLM_BASE_URL": base_url,
        "LLM_MODEL": model,
    }
    if not key_is_masked:
        save_data["LLM_API_KEY"] = api_key
    
    if payload.pixabay_api_key is not None:
        p_key = payload.pixabay_api_key.strip()
        if p_key and not ("*" in p_key or "..." in p_key):
            save_data["PIXABAY_API_KEY"] = p_key
        elif not p_key:
            save_data["PIXABAY_API_KEY"] = ""

    save_to_env(**save_data)
    reload_config()

    logger.info("LLM settings updated: provider=%s model=%s", payload.provider, model)
    return jsonify({"success": True, "provider": payload.provider, "model": model})


@app.route("/api/images/search", methods=["GET"])
def search_images():
    """Search images on Pixabay."""
    import config as cfg
    import urllib.request
    import urllib.parse
    import urllib.error
    import json
    import ssl
    
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"success": False, "error": "请输入搜索关键字", "images": []}), 400
        
    api_key = getattr(cfg, "PIXABAY_API_KEY", "").strip()
    if not api_key:
        return jsonify({
            "success": False,
            "error": "未配置 Pixabay API Key，请先在右上角⚙️设置中配置。",
            "images": []
        }), 400
        
    try:
        # Translate Chinese/non-English query to English for better search results
        from llm.client import translate_to_english
        translated_query = translate_to_english(query)
        lang = "en" if translated_query.isascii() else "zh"

        base_url = "https://pixabay.com/api/?"
        params = {
            "key": api_key,
            "q": translated_query,
            "image_type": "all",
            "orientation": "horizontal",
            "safesearch": "true",
            "order": "popular",
            "per_page": 48,
            "lang": lang,
        }
        url = base_url + urllib.parse.urlencode(params)
        
        # Disable SSL verification for proxies/VPNs if requested
        if not getattr(cfg, "VERIFY_SSL", True):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
        else:
            ctx = None
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(url, headers=headers)
        
        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
        hits = rank_pixabay_hits(res_data.get("hits", []), translated_query, limit=12)
        images = []
        for hit in hits:
            images.append({
                "id": hit.get("id"),
                "preview_url": hit.get("previewURL"),
                "webformat_url": hit.get("webformatURL"),
                "large_image_url": hit.get("largeImageURL"),
                "tags": hit.get("tags")
            })
            
        return jsonify({
            "success": True,
            "images": images,
            "search_query": translated_query,
        })
    except urllib.error.HTTPError as exc:
        try:
            err_msg = exc.read().decode('utf-8', errors='ignore').strip()
        except Exception:
            err_msg = ""
        
        logger.error("Pixabay API HTTPError %d: %s", exc.code, err_msg)
        if "Invalid or missing API key" in err_msg or exc.code == 400:
            friendly_err = "Pixabay API Key 无效或失效，请检查右上角 ⚙️ 设置中配置的 Key 是否正确。"
        else:
            friendly_err = f"图片搜索服务请求失败: {err_msg or exc.reason}"
            
        return jsonify({
            "success": False,
            "error": friendly_err,
            "images": []
        }), 400
    except Exception as exc:
        logger.exception("Error searching images on Pixabay: %s", exc)
        return jsonify({
            "success": False,
            "error": f"图片搜索服务请求失败: {exc}",
            "images": []
        }), 502


@app.route("/api/settings/recommended-models")
def recommended_models():
    """Return recommended model lists for each provider."""
    return jsonify({
        "ollama":     OLLAMA_RECOMMENDED_MODELS,
        "openrouter": OPENROUTER_RECOMMENDED_MODELS,
        "siliconflow": SILICONFLOW_RECOMMENDED_MODELS,
        "dashscope": DASHSCOPE_RECOMMENDED_MODELS,
    })


@app.route("/api/settings/openrouter/free-models")
def openrouter_free_models():
    """Fetch the latest free models from OpenRouter."""
    import config as cfg
    import httpx
    try:
        res = httpx.get("https://openrouter.ai/api/v1/models", verify=getattr(cfg, "VERIFY_SSL", True), timeout=10)
        res.raise_for_status()
        models = res.json().get("data", [])
        
        free_models = []
        for m in models:
            pricing = m.get("pricing", {})
            if pricing.get("prompt") == "0" and pricing.get("completion") == "0":
                model_id = m.get("id", "")
                name = m.get("name", model_id)
                
                # Filter for recognized high-quality families to avoid clutter
                lower_id = model_id.lower()
                if any(brand in lower_id for brand in ["gemma", "llama", "qwen", "mistral", "phi"]):
                    # Create a friendly label
                    brand_name = name.split()[0] if name else "AI"
                    label = f"{name}（免费）"
                    free_models.append({"id": model_id, "label": label})
                    
        if not free_models:
            return jsonify({"success": False, "error": "未找到免费模型"})
            
        return jsonify({"success": True, "models": free_models})
    except Exception as exc:
        logger.warning("Failed to fetch OpenRouter free models: %s", exc)
        return jsonify({"success": False, "error": str(exc)})



@app.route("/api/settings/test-llm", methods=["POST"])
def test_llm_settings():
    """Test LLM connectivity using the submitted credentials — does NOT save anything."""
    import config as cfg
    import httpx
    from openai import OpenAI, APIConnectionError, APITimeoutError

    data = request.get_json(silent=True)
    if data is None:
        return error_response("请提供JSON数据", "JSON body required", 400)

    provider = (data.get("provider") or "lmstudio").lower()
    if provider not in PROVIDER_DEFAULTS:
        return jsonify({"connected": False, "model_id": None, "message": "不支持的 AI 服务商"})

    base_url = _normalize_provider_base_url(provider, data.get("base_url"))
    api_key = (data.get("api_key") or "").strip()
    if provider in CLOUD_API_KEY_PROVIDERS:
        if _is_masked_secret(api_key):
            if provider == cfg.LLM_PROVIDER and cfg.LLM_API_KEY:
                api_key = cfg.LLM_API_KEY
            else:
                return jsonify({
                    "connected": False,
                    "model_id": None,
                    "message": "请重新填写当前云端服务的真实 API Key 后再测试。"
                })
        if not api_key:
            return jsonify({"connected": False, "model_id": None,
                            "message": "云端模型需要 API Key"})
    elif provider == "lmstudio":
        api_key = api_key or "lm-studio"
    elif provider == "ollama":
        api_key = api_key or "ollama"

    model     = data.get("model") or ""

    try:
        client = OpenAI(
            base_url=base_url,
            api_key=api_key or "local",
            timeout=10,
            http_client=httpx.Client(verify=getattr(cfg, "VERIFY_SSL", True))
        )
        try:
            models = client.models.list()
        except Exception:
            if not model:
                raise
            chat_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 8,
                "temperature": 0,
            }
            extra_body = _cloud_test_extra_body(provider, base_url)
            if extra_body:
                chat_kwargs["extra_body"] = extra_body
            client.chat.completions.create(**chat_kwargs)
            return jsonify({
                "connected": True,
                "model_id": model,
                "message": f"已通过一次简短请求连接：{model}"
            })

        model_data = getattr(models, "data", None) or []
        if not model_data:
            if model:
                return jsonify({
                    "connected": True,
                    "model_id": model,
                    "message": f"已成功连接到服务。注意：未检测到可用模型列表，将使用配置的模型: {model}"
                })
            return jsonify({
                "connected": False,
                "message": "已连接到服务，但未检测到已加载的可用模型，且未指定模型名称。请在 LM Studio / Ollama 中加载模型。",
                "model_id": None
            })
        
        detected_model = model
        available_ids = [getattr(m, "id", None) for m in model_data if getattr(m, "id", None)]
        if model and model in available_ids:
            detected_model = model
        elif available_ids:
            detected_model = available_ids[0]
            
        return jsonify({
            "connected": True,
            "model_id": detected_model,
            "message": f"已连接：{detected_model}"
        })
    except APIConnectionError:
        return jsonify({"connected": False, "model_id": None,
                        "message": f"无法连接到 {base_url}，请确认服务正在运行"})
    except APITimeoutError:
        return jsonify({"connected": False, "model_id": None,
                        "message": "连接超时，请检查网络或服务状态"})
    except Exception as exc:
        msg = str(exc)
        if "401" in msg or "authentication" in msg.lower() or "api key" in msg.lower():
            return jsonify({"connected": False, "model_id": None,
                            "message": "API Key 无效或已过期，请重新检查"})
        logger.warning("LLM settings test error: %s", exc)
        return jsonify({"connected": False, "model_id": None, "message": f"连接失败：{msg[:120]}"})



# =====================================================================
# Entry point
# =====================================================================

if __name__ == "__main__":
    logger.info(f"Bashi PPT v{APP_VERSION} starting on http://127.0.0.1:{FLASK_PORT}")
    logger.info(f"Frontend served from: {FRONTEND_DIST}")
    app.run(debug=FLASK_DEBUG, host="127.0.0.1", port=FLASK_PORT)
