"""
SlideForge v0.1.0 — Flask backend entry point.

Routes:
  GET  /                      → Serve React frontend
  GET  /api/health             → Health check
  GET  /api/templates          → List available templates
  POST /api/generate-outline   → Generate outline (Sprint 1: mock data)
  POST /api/generate-pptx      → Render PPTX (Sprint 1: not implemented)
"""

import json
import logging

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from pydantic import ValidationError

from config import FLASK_PORT, FLASK_DEBUG, FRONTEND_DIST, LOG_FILE, TEMPLATES_DIR
from schema import (
    OutlineRequest,
    LyricsRequest,
    LYRICS_LANGUAGE_OPTIONS,
    LYRICS_THEMES_META,
    LYRICS_MODE_LIMITS,
    LYRICS_CHINESE_SCRIPT_OPTIONS,
    error_response,
    format_validation_errors,
)
from lyrics.chinese_script import ChineseScriptConversionUnavailableError, convert_text
from llm.client import (
    LLMReasoningOnlyError,
    LLMTimeoutError,
    LLMUnavailableError,
    OutlineGenerationError,
    check_llm_health,
    generate_outline_text,
)
from llm.outline_parser import OutlineParseError, OutlineValidationError, parse_outline

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
        "version": "0.1.0",
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

    logger.info(
        "Generating outline: topic='%s', slides=%s, scenario=%s, language=%s, reference_chars=%s",
        payload.topic,
        payload.num_slides,
        payload.scenario,
        payload.language,
        len(payload.reference_text or ""),
    )

    try:
        llm_result = generate_outline_text(
            topic=payload.topic,
            num_slides=payload.num_slides,
            scenario=payload.scenario,
            language=payload.language,
            reference_text=payload.reference_text,
        )
        parsed_result = parse_outline(llm_result.raw_text)

        response = {
            "success": True,
            "outline": parsed_result.outline,
            "elapsed_seconds": round(llm_result.elapsed_seconds, 1),
            "llm_model": llm_result.llm_model,
        }
        if parsed_result.warnings:
            response["warnings"] = parsed_result.warnings

        logger.info(
            "Outline generation complete: %s slides, %.1fs, warnings=%s",
            len(parsed_result.outline["slides"]),
            llm_result.elapsed_seconds,
            len(parsed_result.warnings),
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
    except (OutlineParseError, OutlineValidationError, OutlineGenerationError) as exc:
        logger.warning("Invalid model output: %s", exc)
        return error_response(
            "模型返回的大纲格式无效，请重试或缩短主题描述。",
            "The model returned an invalid outline. Please retry or simplify the topic.",
            502,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Unexpected server error while generating outline: %s", exc)
        return error_response(
            "服务器处理大纲时出现未知错误。",
            "The server encountered an unexpected error while generating the outline.",
            500,
        )


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
    
    if not outline:
        return error_response("请提供完整的大纲数据", "Outline data required", 400)
        
    try:
        renderer = PPTXRenderer(template_id)
        pptx_bytes = renderer.render(outline)
        
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
# Entry point
# =====================================================================

if __name__ == "__main__":
    logger.info(f"SlideForge v0.1.0 starting on http://127.0.0.1:{FLASK_PORT}")
    logger.info(f"Frontend served from: {FRONTEND_DIST}")
    app.run(debug=FLASK_DEBUG, host="127.0.0.1", port=FLASK_PORT)
