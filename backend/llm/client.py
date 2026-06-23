"""
LLM Client — OpenAI-compatible interface for LM Studio / Ollama / cloud APIs.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, BadRequestError, OpenAI

import config  # import the module, not its names, so hot-reload works
from .prompts import (
    build_messages,
    build_article_messages,
    build_notes_messages,
    build_fact_extraction_messages,
    build_grounded_repair_messages,
)

logger = logging.getLogger("slideforge")

MAX_RETRIES = 2
BACKOFF_SECONDS = (1.0, 2.0)


class LLMUnavailableError(RuntimeError):
    """Raised when the LLM endpoint cannot be reached."""


class LLMTimeoutError(RuntimeError):
    """Raised when the LLM request exceeds the configured timeout."""


class OutlineGenerationError(RuntimeError):
    """Raised when the model returns an unusable response."""


class LLMReasoningOnlyError(OutlineGenerationError):
    """Raised when the model returns reasoning but no final answer."""


@dataclass
class LLMGenerationResult:
    raw_text: str
    elapsed_seconds: float
    llm_model: str
    finish_reason: str | None = None


def _build_client() -> OpenAI:
    """Build an OpenAI client using the *current* config values.

    Reading from the config module object (not cached names) means that
    after a POST /api/settings/llm + config.reload(), the very next call
    to _build_client() will use the new provider/key/URL without a restart.
    """
    base_url = config.LLM_BASE_URL
    if config.LLM_PROVIDER in ("lmstudio", "ollama") and base_url:
        clean_url = base_url.strip().rstrip("/")
        if not clean_url.endswith("/v1"):
            base_url = clean_url + "/v1"

    return OpenAI(
        base_url=base_url,
        api_key=config.LLM_API_KEY or "local",
        timeout=config.LLM_TIMEOUT,
        http_client=httpx.Client(verify=config.VERIFY_SSL),
    )


def _provider_extra_body() -> dict:
    """Provider-specific request extras for the OpenAI-compatible call.

    SiliconFlow's Qwen3 hybrid models think by default and put the real answer
    in ``reasoning_content`` (often leaving ``content`` empty and the request
    slow).  Disable thinking so we get fast, complete content.
    """
    base = (config.LLM_BASE_URL or "").lower()
    if "siliconflow" in base:
        return {"enable_thinking": False}
    if "dashscope.aliyuncs.com" in base or ".maas.aliyuncs.com" in base:
        return {"enable_thinking": False}
    return {}



def _json_mode_not_supported(exc: BadRequestError) -> bool:
    message = str(exc).lower()
    return "response_format" in message or "json_object" in message or "unsupported" in message


def _extract_text_from_reasoning(
    reasoning_text: str, required_keys: tuple[str, ...] = ('"slides"', '"title"')
) -> str | None:
    """Try to pull a JSON object out of reasoning_content.

    Qwen3.5 with thinking enabled sometimes puts the final JSON answer
    inside the reasoning block (after its chain-of-thought).  We return the
    *last* top-level ``{...}`` that contains all ``required_keys`` — e.g.
    ``"slides"``/``"title"`` for an outline, or ``"notes"`` for speaker notes.
    """
    # Find all top-level JSON-like blocks (starting with { on a line)
    candidates: list[str] = []
    depth = 0
    start = -1
    in_string = False
    escaped = False

    for i, ch in enumerate(reasoning_text):
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start >= 0:
                candidates.append(reasoning_text[start : i + 1])
                start = -1

    # Return the last candidate that contains all required keys
    for candidate in reversed(candidates):
        if all(key in candidate for key in required_keys):
            return candidate

    return None


def _strip_think_tags(text: str) -> str:
    """Recover freeform prose from reasoning_content for non-JSON requests.

    Thinking models may emit a <think>…</think> block; the real answer (if any)
    follows the last closing tag. Prefer that tail, else just drop the tags.
    """
    close = text.rfind("</think>")
    if close != -1:
        text = text[close + len("</think>") :]
    return text.replace("<think>", "").replace("</think>", "").strip()


def _model_not_ready(exc: BadRequestError) -> bool:
    message = str(exc).lower()
    return (
        "no models loaded" in message
        or "model not found" in message
        or "unknown model" in message
        or "please load a model" in message
    )


def check_llm_health() -> tuple[bool, str | None]:
    """Check whether the configured OpenAI-compatible endpoint is reachable."""
    try:
        client = _build_client()
        models = client.models.list()
        model_data = getattr(models, "data", None) or []
        if not model_data:
            return False, None
        model_id = getattr(model_data[0], "id", None)
        return True, model_id or config.LLM_MODEL
    except Exception as exc:
        logger.warning("LLM health check failed: %s", exc)
        return False, None


def extract_facts(
    material: str,
    temperature: float | None = 0.0,
) -> list[dict]:
    """Pre-pass for grounded generation: extract a numbered fact table.

    Returns a list of ``{"id": int, "text": str}``; empty list on any failure
    (callers fall back to passing the raw material instead).
    """
    import json

    if not material or not material.strip():
        return []

    def _loads(text: str):
        """Lenient parse: plain JSON, then json-repair (handles text-mode models
        like LM Studio that reject response_format=json_object and return prose)."""
        try:
            return json.loads(text)
        except Exception:
            try:
                from json_repair import repair_json
                return json.loads(repair_json(text))
            except Exception:
                return None

    try:
        messages = build_fact_extraction_messages(material)
        result = _run_chat(messages, use_json_mode=True, json_keys=('"facts"',), temperature=temperature)
        data = _loads(result.raw_text)
        facts = data.get("facts", []) if isinstance(data, dict) else []
        cleaned: list[dict] = []
        for i, fact in enumerate(facts, start=1):
            if isinstance(fact, dict):
                text = str(fact.get("text", "")).strip()
                fid = fact.get("id", i)
            else:
                text, fid = str(fact).strip(), i
            if text:
                cleaned.append({"id": int(fid) if str(fid).isdigit() else i, "text": text})
        return cleaned
    except Exception as exc:
        logger.warning("Fact extraction failed (%s); proceeding without fact table", exc)
        return []


_GROUNDING_SENSITIVE_PATTERN = re.compile(
    r"("
    r"\d|%|％|"
    r"不得|禁止|严禁|必须|务必|不按|不允许|不能|不可|无需|不需要|不要求|"
    r"只限|仅限|至少|至多|应当|需要|负责|提供|承担|"
    r"\b(?:must|shall|required|may\s+not|must\s+not|do\s+not|only|"
    r"at\s+least|at\s+most|responsible|provide)\b"
    r")",
    flags=re.IGNORECASE,
)


def _source_fact_clauses(material: str) -> list[str]:
    """Split source material into short clauses while preserving exact wording."""
    text = (material or "").strip()
    if not text:
        return []
    chunks = re.split(
        r"(?:\r?\n)+|(?<=[。！？；])|(?<=[.!?;])\s+",
        text,
    )
    clauses: list[str] = []
    for chunk in chunks:
        cleaned = re.sub(r"\s+", " ", chunk).strip(" \t\r\n•*-")
        if not cleaned:
            continue
        if len(cleaned) <= 1000:
            clauses.append(cleaned)
            continue
        # Avoid dropping a long paragraph if the source did not contain sentence
        # punctuation. Comma-level chunks remain verbatim and are easier to audit.
        parts = re.split(r"(?<=[，,：:])", cleaned)
        clauses.extend(part.strip() for part in parts if part.strip())
    return clauses


def _normalized_fact_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def build_grounded_fact_table(
    material: str,
    *,
    max_facts: int = 80,
) -> list[dict]:
    """Build a safer fact table from model extraction plus exact source clauses.

    The LLM provides semantic coverage. Exact source clauses containing numbers,
    negation, duties, limits, or responsibility are then appended verbatim so a
    paraphrase cannot silently weaken "不得" into "不要求", alter a time, or
    change who must act. If model extraction fails, source clauses become the
    complete fallback fact table.
    """
    source_clauses = _source_fact_clauses(material)
    model_facts = extract_facts(material, temperature=0.0)
    if model_facts:
        # Let exact source wording replace model paraphrases for high-risk facts.
        # This avoids asking the generator to cover duplicate versions of the
        # same rule while retaining semantic extraction for ordinary facts.
        candidates = [
            str(fact.get("text", "")).strip()
            for fact in model_facts
            if isinstance(fact, dict)
            and str(fact.get("text", "")).strip()
            and not _GROUNDING_SENSITIVE_PATTERN.search(str(fact.get("text", "")))
        ]
        candidates.extend(
            clause
            for clause in source_clauses
            if _GROUNDING_SENSITIVE_PATTERN.search(clause)
        )
    else:
        candidates = list(source_clauses)

    result: list[dict] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = _normalized_fact_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append({"id": len(result) + 1, "text": candidate[:1000]})
        if len(result) >= max_facts:
            break

    logger.info(
        "Grounded fact table built: model_facts=%s, source_clauses=%s, final_facts=%s",
        len(model_facts),
        len(source_clauses),
        len(result),
    )
    return result


def generate_outline_text(
    topic: str,
    num_slides: int,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
    temperature: float | None = None,
    mode: str = "creative",
    fact_table: list[dict] | None = None,
) -> LLMGenerationResult:
    """Generate raw outline text from the configured model."""
    messages = build_messages(
        topic=topic,
        num_slides=num_slides,
        scenario=scenario,
        output_language=output_language,
        reference_text=reference_text,
        mode=mode,
        fact_table=fact_table,
    )
    return _run_chat(messages, use_json_mode=True, temperature=temperature)


def repair_grounded_outline_text(
    *,
    previous_outline: dict,
    target_slides: int,
    output_language: str,
    fact_table: list[dict],
    missing_fact_ids: list[int] | None = None,
) -> LLMGenerationResult:
    """Perform one directed count repair while retaining all confirmed facts."""
    messages = build_grounded_repair_messages(
        previous_outline=previous_outline,
        target_slides=target_slides,
        output_language=output_language,
        fact_table=fact_table,
        missing_fact_ids=missing_fact_ids,
    )
    return _run_chat(messages, use_json_mode=True, temperature=0.1)


def generate_article_text(
    topic: str,
    scenario: str,
    output_language: str,
    reference_text: str | None = None,
    prior_article: str | None = None,
    correction: str | None = None,
    temperature: float | None = None,
) -> LLMGenerationResult:
    """Generate a freeform draft article (plain text) for the pre-outline step."""
    messages = build_article_messages(
        topic=topic,
        scenario=scenario,
        output_language=output_language,
        reference_text=reference_text,
        prior_article=prior_article,
        correction=correction,
    )
    return _run_chat(messages, use_json_mode=False, temperature=temperature)


def generate_speaker_notes(
    outline: dict,
    output_language: str,
    duration_minutes: int,
    style: str,
    article: str | None = None,
    temperature: float | None = None,
    mode: str = "creative",
    fact_table: list[dict] | None = None,
) -> LLMGenerationResult:
    """Generate per-slide speaker notes as JSON ({"notes": [...]})."""
    messages = build_notes_messages(
        outline=outline,
        output_language=output_language,
        duration_minutes=duration_minutes,
        style=style,
        article=article,
        mode=mode,
        fact_table=fact_table,
    )
    return _run_chat(messages, use_json_mode=True, json_keys=('"notes"',), temperature=temperature)


def _run_chat(
    messages: list[dict[str, str]],
    *,
    use_json_mode: bool = True,
    json_keys: tuple[str, ...] = ('"slides"', '"title"'),
    temperature: float | None = None,
) -> LLMGenerationResult:
    """Run a chat completion with retries, JSON-mode fallback, and reasoning salvage."""
    client = _build_client()
    last_error: Exception | None = None
    effective_temperature = config.LLM_TEMPERATURE if temperature is None else temperature

    for attempt in range(MAX_RETRIES + 1):
        started_at = time.perf_counter()
        try:
            request_kwargs = {
                "model": config.LLM_MODEL,
                "messages": messages,
                "temperature": effective_temperature,
                "max_tokens": config.LLM_MAX_TOKENS,
            }
            if use_json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}
            extra_body = _provider_extra_body()
            if extra_body:
                request_kwargs["extra_body"] = extra_body

            logger.info(
                "Calling LLM endpoint: model=%s, json_mode=%s, attempt=%s",
                config.LLM_MODEL,
                use_json_mode,
                attempt + 1,
            )
            response = client.chat.completions.create(**request_kwargs)
            elapsed = time.perf_counter() - started_at

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            raw_text = (getattr(message, "content", None) or "").strip()
            reasoning_text = (getattr(message, "reasoning_content", None) or "").strip()
            finish_reason = getattr(choice, "finish_reason", None)
            resolved_model = getattr(response, "model", None) or config.LLM_MODEL

            if not raw_text:
                if reasoning_text:
                    if use_json_mode:
                        # Qwen3.5 with thinking mode on: the JSON answer often
                        # ends up inside reasoning_content.  Salvage by required keys.
                        raw_text = _extract_text_from_reasoning(reasoning_text, json_keys)
                    else:
                        # Freeform (e.g. article) output has no JSON to extract — fall
                        # back to the reasoning text itself, stripping any <think> wrapper.
                        raw_text = _strip_think_tags(reasoning_text)
                    if raw_text:
                        logger.warning(
                            "content was empty; recovered %s chars from reasoning_content",
                            len(raw_text),
                        )
                    else:
                        raise LLMReasoningOnlyError(
                            "The model returned reasoning_content but no usable answer."
                        )
                else:
                    raise OutlineGenerationError("The model returned an empty response.")

            logger.info(
                "LLM response received: %s chars in %.1fs (finish_reason=%s, model=%s)",
                len(raw_text),
                elapsed,
                finish_reason,
                resolved_model,
            )
            return LLMGenerationResult(
                raw_text=raw_text,
                elapsed_seconds=elapsed,
                llm_model=resolved_model,
                finish_reason=finish_reason,
            )
        except BadRequestError as exc:
            if use_json_mode and _json_mode_not_supported(exc):
                logger.warning("LLM JSON mode unsupported, retrying without response_format: %s", exc)
                use_json_mode = False
                last_error = exc
                continue
            if _model_not_ready(exc):
                raise LLMUnavailableError("The LLM endpoint is reachable, but no model is loaded.") from exc
            raise OutlineGenerationError(f"LLM request was rejected: {exc}") from exc
        except APITimeoutError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                backoff = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                logger.warning("LLM timed out, retrying in %.1fs", backoff)
                time.sleep(backoff)
                continue
            raise LLMTimeoutError("LLM request timed out.") from exc
        except APIConnectionError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                backoff = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                logger.warning("LLM connection failed, retrying in %.1fs", backoff)
                time.sleep(backoff)
                continue
            raise LLMUnavailableError("Unable to connect to the configured LLM endpoint.") from exc
        except APIError as exc:
            last_error = exc
            if attempt < MAX_RETRIES:
                backoff = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                logger.warning("Transient LLM API error, retrying in %.1fs: %s", backoff, exc)
                time.sleep(backoff)
                continue
            raise OutlineGenerationError(f"LLM API error: {exc}") from exc
        except OutlineGenerationError:
            raise
        except Exception as exc:
            last_error = exc
            raise OutlineGenerationError(f"Unexpected LLM error: {exc}") from exc

    raise OutlineGenerationError(f"LLM request failed after retries: {last_error}")


def _clean_image_search_phrase(line: str, *, min_words: int = 1) -> str | None:
    """Validate one candidate line as an English image-search phrase."""
    line = re.sub(
        r"^(?:final_query|english(?: translation| keywords?| query)?|"
        r"search(?: keywords?| query)?|answer)\s*:\s*",
        "",
        line.strip(),
        flags=re.IGNORECASE,
    )
    line = line.strip("`*_#\"' .,:;!?()[]{}<>")
    line = re.sub(r"[-_/]+", " ", line)
    line = re.sub(r"[^A-Za-z0-9+& ]+", " ", line)
    line = re.sub(r"\s+", " ", line).strip().lower()
    words = line.split()
    if not (min_words <= len(words) <= 5) or len(line) > 72:
        return None

    # Common fragments from a model explaining the task instead of answering it.
    rejected_phrases = (
        "literal translation",
        "task convert",
        "convert to",
        "english stock",
        "stock photo keywords",
        "words here",
    )
    if any(line.startswith(phrase) for phrase in rejected_phrases):
        return None
    return line


def _sanitize_image_search_phrase(
    raw_text: str,
    *,
    require_final_marker: bool = False,
) -> str | None:
    """Extract a complete query without mistaking reasoning fragments for answers.

    Normal ``message.content`` may be a plain one-line phrase.  Reasoning output
    is untrusted unless the model emitted an explicit ``FINAL_QUERY:`` line.
    """
    if not raw_text:
        return None

    cleaned = _strip_think_tags(raw_text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    marked_lines = [
        line
        for line in lines
        if re.match(r"^\s*(?:[-*]\s*)?final_query\s*:", line, flags=re.IGNORECASE)
    ]
    for line in reversed(marked_lines):
        candidate = re.sub(r"^\s*[-*]\s*", "", line)
        result = _clean_image_search_phrase(candidate, min_words=2)
        if result:
            return result

    if require_final_marker or len(lines) != 1:
        return None
    return _clean_image_search_phrase(lines[0])


def _translate_image_query_with_lmstudio(text: str) -> str | None:
    """Use LM Studio's native API so thinking can be disabled per request."""
    if config.LLM_PROVIDER != "lmstudio":
        return None

    native_base_url = re.sub(r"/v1/?$", "", config.LLM_BASE_URL.strip().rstrip("/"))
    url = f"{native_base_url}/api/v1/chat"
    prompt = (
        "Translate this slide title into one natural English stock-photo search phrase "
        "of 2 to 5 words. Output the phrase only, without labels or explanation.\n"
        f"Title: {text}"
    )
    headers = {
        "Authorization": f"Bearer {config.LLM_API_KEY or 'lm-studio'}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": prompt,
        "temperature": 0,
        "max_output_tokens": 24,
        "reasoning": "off",
        "store": False,
    }

    try:
        with httpx.Client(verify=config.VERIFY_SSL, timeout=8) as client:
            models_response = client.get(
                f"{native_base_url}/api/v1/models",
                headers=headers,
            )
            models_response.raise_for_status()
            loaded_models = []
            for model in models_response.json().get("models", []):
                if model.get("type") != "llm":
                    continue
                for instance in model.get("loaded_instances", []):
                    loaded_models.append(
                        {
                            "key": str(model.get("key") or ""),
                            "id": str(instance.get("id") or ""),
                        }
                    )

            configured_model = config.LLM_MODEL
            matching_model = next(
                (
                    model["id"] or model["key"]
                    for model in loaded_models
                    if configured_model in (model["id"], model["key"])
                ),
                None,
            )
            if matching_model:
                native_model = matching_model
            elif len(loaded_models) == 1:
                native_model = loaded_models[0]["id"] or loaded_models[0]["key"]
            else:
                native_model = configured_model

            payload["model"] = native_model
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        for item in data.get("output", []):
            if item.get("type") != "message":
                continue
            translated = _sanitize_image_search_phrase(str(item.get("content") or ""))
            if translated:
                reasoning_tokens = data.get("stats", {}).get("reasoning_output_tokens")
                logger.info(
                    "Translated image query with LM Studio thinking disabled: '%s' to '%s' "
                    "(reasoning_tokens=%s)",
                    text,
                    translated,
                    reasoning_tokens,
                )
                return translated
    except Exception as exc:
        # Older LM Studio versions do not have /api/v1/chat. Fall back to the
        # OpenAI-compatible endpoint so image search remains available.
        logger.warning(
            "LM Studio native no-thinking image translation failed for '%s': %s",
            text,
            exc,
        )
    return None


def translate_to_english(text: str) -> str:
    """Convert a slide title into a concise, visually meaningful English query.

    If conversion fails, return the original text so Pixabay can still use its
    own language support.
    """
    if not text:
        return text

    # Quick check: if all characters are ASCII, it's likely already in English/ASCII.
    try:
        text.encode('ascii')
        return _sanitize_image_search_phrase(text) or text
    except UnicodeEncodeError:
        pass

    translated = _translate_image_query_with_lmstudio(text)
    if translated:
        return translated

    try:
        client = _build_client()
        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Translate the slide title into one natural English stock-photo search "
                        "phrase of 2 to 5 words. Return exactly one line in this format: "
                        "FINAL_QUERY: words here."
                    ),
                },
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=32,
            timeout=8,
            extra_body=_provider_extra_body() or None,
        )

        choice = response.choices[0] if response.choices else None
        message = getattr(choice, "message", None)
        content = (getattr(message, "content", None) or "").strip()
        reasoning = (getattr(message, "reasoning_content", None) or "").strip()
        translated = _sanitize_image_search_phrase(content)
        if not translated:
            translated = _sanitize_image_search_phrase(
                reasoning,
                require_final_marker=True,
            )

        if translated:
            logger.info("Translated search query from '%s' to '%s'", text, translated)
            return translated
        logger.warning(
            "Rejected incomplete image-search translation for '%s'; using original query",
            text,
        )
    except Exception as e:
        logger.warning("Failed to translate query '%s' to English: %s", text, e)

    return text

