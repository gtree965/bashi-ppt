"""
SlideForge configuration — loaded from .env file.

Compatible with:
- LM Studio (default): localhost:1234
- OpenRouter: openrouter.ai/api/v1
- Mistral: api.mistral.ai/v1
- Any OpenAI-compatible endpoint
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Project root is one level up from backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# --- LLM ---
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "lm-studio")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5-4b")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "16384"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "1200"))

# --- Flask ---
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"

# --- Paths ---
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
LOG_FILE = PROJECT_ROOT / "slideforge.log"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
