"""
LLM Client — OpenAI-compatible interface for LM Studio / Ollama / cloud APIs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, BadRequestError, OpenAI

import config  # import the module, not its names, so hot-reload works
from .prompts import build_messages, build_article_messages, build_notes_messages

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


def generate_outline_text(
    topic: str,
    num_slides: int,
    scenario: str,
    language: str,
    reference_text: str | None = None,
) -> LLMGenerationResult:
    """Generate raw outline text from the configured model."""
    messages = build_messages(
        topic=topic,
        num_slides=num_slides,
        scenario=scenario,
        language=language,
        reference_text=reference_text,
    )
    return _run_chat(messages, use_json_mode=True)


def generate_article_text(
    topic: str,
    scenario: str,
    language: str,
    reference_text: str | None = None,
    prior_article: str | None = None,
    correction: str | None = None,
) -> LLMGenerationResult:
    """Generate a freeform draft article (plain text) for the pre-outline step."""
    messages = build_article_messages(
        topic=topic,
        scenario=scenario,
        language=language,
        reference_text=reference_text,
        prior_article=prior_article,
        correction=correction,
    )
    return _run_chat(messages, use_json_mode=False)


def generate_speaker_notes(
    outline: dict,
    language: str,
    duration_minutes: int,
    style: str,
    article: str | None = None,
) -> LLMGenerationResult:
    """Generate per-slide speaker notes as JSON ({"notes": [...]})."""
    messages = build_notes_messages(
        outline=outline,
        language=language,
        duration_minutes=duration_minutes,
        style=style,
        article=article,
    )
    return _run_chat(messages, use_json_mode=True, json_keys=('"notes"',))


def _run_chat(
    messages: list[dict[str, str]],
    *,
    use_json_mode: bool = True,
    json_keys: tuple[str, ...] = ('"slides"', '"title"'),
) -> LLMGenerationResult:
    """Run a chat completion with retries, JSON-mode fallback, and reasoning salvage."""
    client = _build_client()
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        started_at = time.perf_counter()
        try:
            request_kwargs = {
                "model": config.LLM_MODEL,
                "messages": messages,
                "temperature": config.LLM_TEMPERATURE,
                "max_tokens": config.LLM_MAX_TOKENS,
            }
            if use_json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}

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


def translate_to_english(text: str) -> str:
    """Translate a given query/text to English using the configured LLM.
    If the text is already in English, or translation fails/timeouts, returns the original text.
    """
    if not text:
        return text

    # Quick check: if all characters are ASCII, it's likely already in English/ASCII.
    try:
        text.encode('ascii')
        return text
    except UnicodeEncodeError:
        pass

    try:
        client = _build_client()
        prompt = (
            "You are a translation assistant. Translate the following Chinese/non-English query to a concise, search-friendly English keyword or short phrase (suitable for searching pictures on Pixabay, e.g. 'church', 'artificial intelligence', 'happy family').\n"
            "Return ONLY the translated English text. Do not include quotes, explanation, or punctuation.\n"
            f"Query: {text}\n"
            "English translation:"
        )

        response = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=20,
            timeout=5, # Fast timeout for UI responsiveness
        )

        choice = response.choices[0] if response.choices else None
        message = getattr(choice, "message", None)
        translated = (getattr(message, "content", None) or "").strip()
        # Clean quotes
        translated = translated.replace('"', '').replace("'", "")

        if translated:
            logger.info("Translated search query from '%s' to '%s'", text, translated)
            return translated
    except Exception as e:
        logger.warning("Failed to translate query '%s' to English: %s", text, e)

    return text

