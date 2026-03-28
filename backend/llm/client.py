"""
LLM Client — OpenAI-compatible interface for LM Studio / cloud APIs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, BadRequestError, OpenAI

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MAX_TOKENS,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_TIMEOUT,
)
from .prompts import build_messages

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
    return OpenAI(
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        timeout=LLM_TIMEOUT,
    )


def _json_mode_not_supported(exc: BadRequestError) -> bool:
    message = str(exc).lower()
    return "response_format" in message or "json_object" in message or "unsupported" in message


def _extract_text_from_reasoning(reasoning_text: str) -> str | None:
    """Try to pull a JSON object out of reasoning_content.

    Qwen3.5 with thinking enabled sometimes puts the final JSON answer
    inside the reasoning block (after its chain-of-thought).  We look
    for the *last* top-level ``{...}`` that contains ``"slides"`` — that
    is almost certainly the outline, not part of the reasoning.
    """
    import re

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

    # Return the last candidate that looks like an outline
    for candidate in reversed(candidates):
        if '"slides"' in candidate and '"title"' in candidate:
            return candidate

    return None


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
        return True, model_id or LLM_MODEL
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
    client = _build_client()
    messages = build_messages(
        topic=topic,
        num_slides=num_slides,
        scenario=scenario,
        language=language,
        reference_text=reference_text,
    )

    use_json_mode = True
    last_error: Exception | None = None

    for attempt in range(MAX_RETRIES + 1):
        started_at = time.perf_counter()
        try:
            request_kwargs = {
                "model": LLM_MODEL,
                "messages": messages,
                "temperature": LLM_TEMPERATURE,
                "max_tokens": LLM_MAX_TOKENS,
            }
            if use_json_mode:
                request_kwargs["response_format"] = {"type": "json_object"}

            logger.info(
                "Calling LLM endpoint: model=%s, slides=%s, scenario=%s, language=%s, attempt=%s",
                LLM_MODEL,
                num_slides,
                scenario,
                language,
                attempt + 1,
            )
            response = client.chat.completions.create(**request_kwargs)
            elapsed = time.perf_counter() - started_at

            choice = response.choices[0] if response.choices else None
            message = getattr(choice, "message", None)
            raw_text = (getattr(message, "content", None) or "").strip()
            reasoning_text = (getattr(message, "reasoning_content", None) or "").strip()
            finish_reason = getattr(choice, "finish_reason", None)
            resolved_model = getattr(response, "model", None) or LLM_MODEL

            if not raw_text:
                if reasoning_text:
                    # Qwen3.5 with thinking mode on: the JSON outline often
                    # ends up inside reasoning_content.  Try to salvage it.
                    raw_text = _extract_text_from_reasoning(reasoning_text)
                    if raw_text:
                        logger.warning(
                            "content was empty; extracted %s chars from reasoning_content",
                            len(raw_text),
                        )
                    else:
                        raise LLMReasoningOnlyError(
                            "The model returned reasoning_content but no usable JSON."
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
