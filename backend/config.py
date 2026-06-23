"""
Bashi PPT (巴适PPT) configuration — loaded from .env file.

LLM_PROVIDER options:
  lmstudio   — LM Studio on localhost:1234 (default)
  ollama     — Ollama on localhost:11434
  openrouter — OpenRouter cloud API (requires LLM_API_KEY)

Settings can be changed at runtime via POST /api/settings/llm.
Call config.reload() after writing the .env to pick up new values.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv, set_key

# Project root is one level up from backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
VERSION_PATH = PROJECT_ROOT / "VERSION"
APP_VERSION = (
    VERSION_PATH.read_text(encoding="utf-8").strip()
    if VERSION_PATH.exists()
    else "0.1.0"
)

# Default base URLs per provider
_PROVIDER_DEFAULTS: dict[str, str] = {
    "lmstudio":   "http://localhost:1234/v1",
    "ollama":     "http://localhost:11434/v1",
    "openrouter": "https://openrouter.ai/api/v1",
}


def _load() -> None:
    """Load (or reload) all settings from the .env file."""
    load_dotenv(ENV_PATH, override=True)

    provider = os.getenv("LLM_PROVIDER", "lmstudio").lower()
    default_url = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["lmstudio"])
    default_key = "lm-studio" if provider != "openrouter" else ""

    global LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
    global LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_TIMEOUT
    global FLASK_PORT, FLASK_DEBUG, FRONTEND_DIST, LOG_FILE, TEMPLATES_DIR
    global PIXABAY_API_KEY, VERIFY_SSL

    LLM_PROVIDER    = provider
    LLM_BASE_URL    = os.getenv("LLM_BASE_URL", default_url)
    LLM_API_KEY     = os.getenv("LLM_API_KEY", default_key)
    LLM_MODEL       = os.getenv("LLM_MODEL", "local-model")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS  = int(os.getenv("LLM_MAX_TOKENS", "16384"))
    LLM_TIMEOUT     = int(os.getenv("LLM_TIMEOUT", "1200"))
    PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
    VERIFY_SSL      = os.getenv("VERIFY_SSL", "true").lower() == "true"

    FLASK_PORT  = int(os.getenv("FLASK_PORT", "5100"))
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

    FRONTEND_DIST  = PROJECT_ROOT / "frontend" / "dist"
    LOG_FILE       = PROJECT_ROOT / "slideforge.log"
    TEMPLATES_DIR  = Path(__file__).resolve().parent / "templates"


def reload() -> None:
    """Hot-reload config from disk and push new values into all modules
    that imported LLM_* names directly (llm.client, app, etc.)."""
    _load()
    # Propagate updated values to already-imported sibling modules
    this = sys.modules[__name__]
    for mod_name, mod in list(sys.modules.items()):
        if mod is None or mod is this:
            continue
        for attr in ("LLM_PROVIDER", "LLM_BASE_URL", "LLM_API_KEY",
                     "LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS",
                     "LLM_TIMEOUT", "PIXABAY_API_KEY", "VERIFY_SSL"):
            if hasattr(mod, attr) and getattr(mod, "__name__", "").startswith(("llm", "app", "renderer")):
                setattr(mod, attr, getattr(this, attr))


def save_to_env(**kwargs: str) -> None:
    """Persist one or more key=value pairs to the .env file."""
    ENV_PATH.touch(exist_ok=True)
    for key, value in kwargs.items():
        set_key(str(ENV_PATH), key, value)


# Initial load on import
_load()
