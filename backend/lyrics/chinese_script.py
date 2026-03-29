"""
Chinese script conversion helpers for hymn lyrics.

Uses OpenCC for offline Traditional/Simplified conversion.
"""

from functools import lru_cache


_MODE_TO_CONFIG = {
    "to_simplified": "t2s",
    "to_traditional": "s2t",
}


class ChineseScriptConversionUnavailableError(RuntimeError):
    """Raised when Chinese script conversion is requested but OpenCC is unavailable."""


@lru_cache(maxsize=2)
def _get_converter(config_name: str):
    try:
        from opencc import OpenCC
    except ImportError as exc:  # pragma: no cover - depends on local install
        raise ChineseScriptConversionUnavailableError(
            "OpenCC is not installed for this SlideForge environment."
        ) from exc
    return OpenCC(config_name)


def convert_text(text: str, mode: str) -> str:
    """Convert Chinese text according to the requested script mode."""
    if mode == "original" or not text:
        return text
    config_name = _MODE_TO_CONFIG.get(mode)
    if not config_name:
        return text
    converter = _get_converter(config_name)
    return converter.convert(text)
