# Bashi PPT — Local AI PPT Generator
## Implementation Plan for AI Agents

> **Project codename:** Bashi PPT (幻灯锻造)
> **Architecture:** Flask API + React Frontend + python-pptx renderer
> **AI Integration:** LM Studio (OpenAI-compatible API on localhost:1234)
> **Target users:** Teachers, parents, church/community members (non-technical)
> **Language:** Bilingual Chinese/English, Chinese-first UI

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Diagram](#2-architecture-diagram)
3. [Directory Structure](#3-directory-structure)
4. [Phase 1: Core Backend — LLM Outline Generation](#phase-1-core-backend--llm-outline-generation)
5. [Phase 2: Core Backend — PPTX Rendering Engine](#phase-2-core-backend--pptx-rendering-engine)
6. [Phase 3: Template System](#phase-3-template-system)
7. [Phase 4: React Frontend](#phase-4-react-frontend)
8. [Phase 5: Integration & API Routes](#phase-5-integration--api-routes)
9. [Phase 6: Packaging & Distribution](#phase-6-packaging--distribution)
10. [JSON Schema Reference](#json-schema-reference)
11. [Prompt Engineering Reference](#prompt-engineering-reference)
12. [Testing Checklist](#testing-checklist)
13. [Known Constraints & Design Decisions](#known-constraints--design-decisions)

---

## 1. Project Overview

### Problem Statement
LandPPT requires 6 sequential LLM calls per slide, consuming ~12K tokens of context
per slide. This exceeds the context window of local 4B models (12,288 tokens) and
takes 25+ minutes per slide. We need a system that uses exactly 1 LLM call total
(~900 input tokens, ~2000 output tokens) and renders everything else in pure code.

### Core Workflow (3 steps, user perspective)
```
User types topic → AI generates outline → Click "Generate" → Download .pptx
```

### Core Workflow (technical)
```
[React Frontend]
    │
    ├─ POST /api/generate-outline
    │   → Flask calls LM Studio (1 LLM call, ~900 input tokens)
    │   → Returns JSON outline
    │   → User can edit outline in browser
    │
    ├─ POST /api/generate-pptx
    │   → Flask takes JSON outline + selected template
    │   → python-pptx renders .pptx (zero LLM calls)
    │   → Returns .pptx file for download
    │
    └─ GET /api/templates
        → Returns available template list
```

### Hardware Target
- CPU: AMD Ryzen 7 5700X
- RAM: 32GB DDR4
- GPU: AMD RX 590 (8GB VRAM, Vulkan backend)
- Model: Qwen3.5-4B-Q4_K_M via LM Studio (localhost:1234)
- OS: Windows 10/11 (potential future Linux migration)

---

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    React Frontend                        │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Topic    │  │ Outline      │  │ Template          │  │
│  │ Input    │→ │ Editor       │→ │ Selector          │  │
│  │ Form     │  │ (editable)   │  │ + Generate Button │  │
│  └──────────┘  └──────────────┘  └───────────────────┘  │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP API
┌───────────────────────┴─────────────────────────────────┐
│                    Flask Backend                         │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ /api/        │  │ /api/         │  │ /api/        │  │
│  │ generate-    │  │ generate-     │  │ templates    │  │
│  │ outline      │  │ pptx          │  │              │  │
│  └──────┬───────┘  └───────┬───────┘  └──────────────┘  │
│         │                  │                             │
│  ┌──────┴───────┐  ┌──────┴───────┐                     │
│  │ LLM Client   │  │ PPTX         │                     │
│  │ (OpenAI SDK) │  │ Renderer     │                     │
│  └──────┬───────┘  │ (python-pptx)│                     │
│         │          └──────────────┘                      │
└─────────┼───────────────────────────────────────────────┘
          │ OpenAI-compatible API
┌─────────┴───────────────────────────────────────────────┐
│  LM Studio (localhost:1234)                              │
│  Model: Qwen3.5-4B / Qwen2.5-7B / any GGUF model       │
│  Also compatible with: OpenRouter, Mistral, DeepSeek     │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Directory Structure

```
Bashi PPT/
├── backend/
│   ├── app.py                    # Flask entry point
│   ├── config.py                 # Configuration (LLM endpoint, ports)
│   ├── requirements.txt          # Python dependencies
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py             # OpenAI-compatible LLM client
│   │   ├── prompts.py            # System & user prompt templates
│   │   └── outline_parser.py     # JSON response validation/repair
│   │
│   ├── renderer/
│   │   ├── __init__.py
│   │   ├── engine.py             # Main PPTX rendering engine
│   │   ├── slide_layouts.py      # Slide layout strategies
│   │   ├── theme.py              # Color schemes, fonts, styling
│   │   └── utils.py              # Helper functions (unit conversion etc.)
│   │
│   ├── templates/                # PPTX template definitions (JSON)
│   │   ├── default.json          # Default clean template
│   │   ├── teaching.json         # Education/classroom template
│   │   ├── church.json           # Church/ministry template
│   │   └── professional.json     # Business/parent meeting template
│   │
│   └── output/                   # Generated PPTX files (gitignored)
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx               # Main app component
│   │   ├── index.jsx             # Entry point
│   │   ├── components/
│   │   │   ├── TopicInput.jsx    # Step 1: Topic input form
│   │   │   ├── OutlineEditor.jsx # Step 2: Editable outline
│   │   │   ├── TemplateSelector.jsx # Step 3: Template picker
│   │   │   ├── GenerateButton.jsx   # Generate + download
│   │   │   ├── ProgressBar.jsx      # Generation progress
│   │   │   └── Header.jsx           # App header
│   │   ├── api/
│   │   │   └── client.js         # API client functions
│   │   └── styles/
│   │       └── globals.css       # Tailwind config
│   │
│   └── public/
│       └── index.html
│
├── scripts/
│   ├── start.bat                 # Windows one-click launcher
│   ├── start.sh                  # Linux/Mac launcher
│   └── setup.bat                 # First-time setup script
│
├── .env                          # User configuration
├── .env.example                  # Template for .env
└── README.md                     # User-facing documentation (bilingual)
```

---

## Phase 1: Core Backend — LLM Outline Generation

### Goal
Single LLM call that takes a topic string and returns a structured JSON outline.

### File: `backend/llm/client.py`

```python
"""
LLM Client — OpenAI-compatible interface.
Connects to LM Studio (default), OpenRouter, or any OpenAI-compatible endpoint.

Key design decisions:
- Uses openai Python SDK for maximum compatibility
- Timeout set to 300s (local models can be slow)
- Retries: 2 attempts with exponential backoff
- Response format: request JSON mode when supported
"""

# Dependencies: openai>=1.0.0
# Config from: backend/config.py → LLM_BASE_URL, LLM_API_KEY, LLM_MODEL

# Implementation requirements:
# 1. Function: generate_outline(topic: str, num_slides: int, scenario: str, language: str) -> dict
# 2. Construct system prompt from prompts.py
# 3. Construct user prompt with topic, num_slides, scenario
# 4. Call LLM with temperature=0.7, max_tokens=4096
# 5. Parse JSON from response (handle markdown code fences)
# 6. Validate with outline_parser.py
# 7. Return validated outline dict or raise OutlineGenerationError
```

### File: `backend/llm/prompts.py`

```python
"""
Prompt templates for outline generation.

CRITICAL DESIGN PRINCIPLE:
The prompt must be under 500 tokens to leave room for output.
Total budget: ~900 tokens input, ~2000-3000 tokens output.
NO chart_config, NO image_config, NO design instructions.
The model ONLY generates content structure.
"""

SYSTEM_PROMPT = """你是PPT大纲生成助手。根据用户主题，生成结构化JSON大纲。

严格规则：
1. 只输出JSON，不要其他文字
2. 每页3-4个要点，每个要点不超过30个字
3. 第一页是标题页(slide_type: "title")
4. 最后一页是总结页(slide_type: "conclusion")
5. 中间页是内容页(slide_type: "content")
6. 不要生成chart_config或任何图表数据
7. 内容要适合目标受众的理解水平"""

# User prompt template — kept minimal to save tokens
USER_PROMPT_TEMPLATE = """主题：{topic}
页数：{num_slides}
场景：{scenario}
语言：{language}

请生成JSON大纲，格式如下：
{{"title": "演示文稿标题", "slides": [{{"page_number": 1, "title": "页面标题", "content_points": ["要点1", "要点2", "要点3"], "slide_type": "title"}}]}}"""

# Scenario descriptions for prompt context (keep short)
SCENARIOS = {
    "teaching": "小学编程教学课堂",
    "church": "教会讲座或主日学",
    "parents": "面向家长的课程说明",
    "general": "通用演示文稿"
}
```

### File: `backend/llm/outline_parser.py`

```python
"""
JSON outline validation and repair.

Local models sometimes output:
- JSON wrapped in markdown code fences (```json ... ```)
- Trailing commas in arrays/objects
- Missing closing brackets
- Extra text before/after JSON

This module handles all these cases gracefully.
"""

# Implementation requirements:
# 1. Function: parse_outline(raw_text: str) -> dict
#    - Strip markdown code fences
#    - Attempt json.loads()
#    - If fails: try regex to extract JSON object
#    - If still fails: try json_repair library
#    - Validate against expected schema
#
# 2. Function: validate_outline(outline: dict) -> tuple[bool, list[str]]
#    - Check required fields: title, slides
#    - Check each slide has: page_number, title, content_points, slide_type
#    - Check slide_type is one of: title, content, conclusion
#    - Check content_points is a list of 1-6 strings
#    - Return (is_valid, list_of_errors)
#
# 3. Function: repair_outline(outline: dict) -> dict
#    - Add missing page_numbers
#    - Default missing slide_type to "content"
#    - Trim content_points longer than 50 chars
#    - Remove any chart_config or image_config fields
```

---

## Phase 2: Core Backend — PPTX Rendering Engine

### Goal
Take a validated JSON outline + template config and produce a .pptx file.
Zero LLM calls. Pure deterministic rendering.

### File: `backend/renderer/engine.py`

```python
"""
PPTX Rendering Engine — the heart of Bashi PPT.

Takes a JSON outline and a template config, produces a .pptx file.

Key design decisions:
- Uses python-pptx library
- Widescreen 16:9 format (13.333" x 7.5")
- Chinese font stack: 微软雅黑 → Noto Sans SC → Arial
- Each slide_type maps to a layout strategy
- Template config controls colors, fonts, decorations
"""

# Dependencies: python-pptx>=0.6.23, Pillow>=10.0

# Implementation requirements:
#
# 1. Class: PPTXRenderer
#    - __init__(self, template_config: dict)
#    - render(self, outline: dict) -> bytes  # Returns PPTX as bytes
#    - _render_title_slide(self, slide, slide_data: dict)
#    - _render_content_slide(self, slide, slide_data: dict)
#    - _render_conclusion_slide(self, slide, slide_data: dict)
#    - _add_slide_number(self, slide, current: int, total: int)
#    - _apply_background(self, slide, bg_config: dict)
#
# 2. Title slide layout:
#    - Main title: centered, large font (44pt), bold
#    - Subtitle/points: centered below title, smaller font (20pt)
#    - Optional decorative line between title and subtitle
#
# 3. Content slide layout:
#    - Page title: top-left, 32pt, bold, colored
#    - Content points: bullet list, 20pt, with spacing
#    - Page number: bottom-right, 10pt, gray
#    - Left accent bar (optional, from template)
#
# 4. Conclusion slide layout:
#    - Similar to title but with "Thank you" styling
#    - Summary points listed below
#
# 5. Font handling for Chinese:
#    - Primary: "Microsoft YaHei" (微软雅黑) — available on Windows
#    - Fallback in code: set both font.name and font.eastAsian
#    - Use python-pptx's font assignment:
#      run.font.name = "Microsoft YaHei"
#      run._element.rPr.attrib[qn('a:ea')] = "Microsoft YaHei"  # East Asian font
```

### File: `backend/renderer/slide_layouts.py`

```python
"""
Slide layout strategies.

Each layout defines WHERE elements go on the slide.
Templates define HOW they look (colors, fonts, sizes).

Available layouts:
- TitleCenterLayout: Big centered title + subtitle below
- ContentBulletLayout: Title at top + bullet points below
- ContentTwoColumnLayout: Title + two columns of points
- ContentIconListLayout: Title + icon-style numbered list
- ConclusionLayout: Centered "thank you" + summary points
"""

# Implementation requirements:
#
# All measurements in Inches (from pptx.util import Inches, Pt, Emu)
# Slide dimensions: 13.333" x 7.5" (widescreen 16:9)
#
# TitleCenterLayout:
#   title_box:    x=1.0, y=2.0, w=11.333, h=1.5
#   subtitle_box: x=2.0, y=4.0, w=9.333,  h=2.0
#   accent_line:  x=5.0, y=3.7, w=3.333,  h=0.02  (optional)
#
# ContentBulletLayout:
#   title_box:    x=0.8, y=0.4, w=11.733, h=0.9
#   content_box:  x=1.0, y=1.6, w=11.333, h=5.2
#   page_number:  x=12.0, y=7.0, w=1.0,   h=0.3
#   accent_bar:   x=0.0, y=0.4, w=0.15,   h=0.9   (optional, left edge)
#
# ContentTwoColumnLayout:
#   title_box:    x=0.8, y=0.4, w=11.733, h=0.9
#   left_col:     x=0.8, y=1.6, w=5.4,    h=5.2
#   right_col:    x=6.8, y=1.6, w=5.4,    h=5.2
#
# ConclusionLayout:
#   title_box:    x=1.0, y=1.5, w=11.333, h=1.5
#   points_box:   x=2.0, y=3.5, w=9.333,  h=3.0
```

### File: `backend/renderer/theme.py`

```python
"""
Theme definitions — colors, fonts, and visual styling.

Each theme is a dict with standardized keys.
Templates reference themes to control appearance.
"""

# Theme structure:
THEME_SCHEMA = {
    "name": "str — display name",
    "colors": {
        "primary": "str — hex color for titles and accents",
        "secondary": "str — hex color for subtitles",
        "background": "str — hex color for slide background",
        "text": "str — hex color for body text",
        "accent": "str — hex color for decorative elements",
        "page_number": "str — hex color for page numbers"
    },
    "fonts": {
        "title": "str — font name for titles",
        "body": "str — font name for body text",
        "title_size": "int — title font size in pt",
        "body_size": "int — body font size in pt",
        "page_number_size": "int — page number size in pt"
    },
    "decorations": {
        "accent_bar": "bool — show left accent bar on content slides",
        "title_underline": "bool — show line under slide titles",
        "slide_number_format": "str — '{current} / {total}' or '{current}'"
    }
}

# Built-in themes:
THEMES = {
    "clean_blue": {
        "name": "简约蓝 (Clean Blue)",
        "colors": {
            "primary": "1A5276",
            "secondary": "5DADE2",
            "background": "FFFFFF",
            "text": "2C3E50",
            "accent": "2E86C1",
            "page_number": "95A5A6"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 32,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": True,
            "slide_number_format": "{current} / {total}"
        }
    },
    "warm_earth": {
        "name": "暖色大地 (Warm Earth)",
        "colors": {
            "primary": "6E2C00",
            "secondary": "D35400",
            "background": "FEF9E7",
            "text": "2C3E50",
            "accent": "E67E22",
            "page_number": "B7950B"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 32,
            "body_size": 20,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": False,
            "slide_number_format": "{current} / {total}"
        }
    },
    "dark_arcade": {
        "name": "暗色游戏 (Dark Arcade)",
        "colors": {
            "primary": "FF6B00",
            "secondary": "4ECDC4",
            "background": "1A1C29",
            "text": "ECEFF1",
            "accent": "2F80ED",
            "page_number": "78909C"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 36,
            "body_size": 22,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": True,
            "title_underline": False,
            "slide_number_format": "{current} / {total}"
        }
    },
    "church_grace": {
        "name": "恩典之光 (Grace)",
        "colors": {
            "primary": "1B4F72",
            "secondary": "7FB3D8",
            "background": "F8F9F9",
            "text": "2C3E50",
            "accent": "2980B9",
            "page_number": "AEB6BF"
        },
        "fonts": {
            "title": "Microsoft YaHei",
            "body": "Microsoft YaHei",
            "title_size": 34,
            "body_size": 22,
            "page_number_size": 10
        },
        "decorations": {
            "accent_bar": False,
            "title_underline": True,
            "slide_number_format": "{current}"
        }
    }
}
```

---

## Phase 3: Template System

### File: `backend/templates/teaching.json`

```json
{
  "id": "teaching",
  "name": "课堂教学 (Classroom)",
  "description": "适合编程教学、课堂演示",
  "theme": "clean_blue",
  "default_slides": 8,
  "default_scenario": "teaching",
  "layout_mapping": {
    "title": "TitleCenterLayout",
    "content": "ContentBulletLayout",
    "conclusion": "ConclusionLayout"
  }
}
```

### File: `backend/templates/church.json`

```json
{
  "id": "church",
  "name": "教会讲座 (Church)",
  "description": "适合主日学、查经班、讲座",
  "theme": "church_grace",
  "default_slides": 10,
  "default_scenario": "church",
  "layout_mapping": {
    "title": "TitleCenterLayout",
    "content": "ContentBulletLayout",
    "conclusion": "ConclusionLayout"
  }
}
```

---

## Phase 4: React Frontend

### Design Principles
- **Three-step wizard** — Topic → Outline → Generate
- **Large touch targets** — buttons minimum 48px height
- **Chinese-first labels** with English subtitle
- **No jargon** — "生成PPT" not "渲染幻灯片"
- **Instant feedback** — loading spinners, progress indication
- **Single page app** — no routing needed, just step transitions

### File: `frontend/src/App.jsx`

```jsx
/**
 * Main App — Three-step wizard layout
 *
 * State machine:
 *   IDLE → GENERATING_OUTLINE → EDITING_OUTLINE → GENERATING_PPTX → DONE
 *
 * Components:
 *   Step 1 (IDLE): TopicInput — text input + scenario selector + slide count
 *   Step 2 (EDITING_OUTLINE): OutlineEditor — editable slide titles/points
 *   Step 3 (GENERATING_PPTX → DONE): GenerateButton + download link
 *
 * Styling: Tailwind CSS via CDN (no build step needed for prototype)
 *
 * Key UX requirements:
 * - "生成大纲" button triggers outline generation
 * - Outline is shown as editable cards (one per slide)
 * - User can add/remove/reorder slides
 * - User can edit titles and content points inline
 * - "生成PPT" button triggers PPTX rendering
 * - Download starts automatically when ready
 * - "重新开始" button resets to Step 1
 */
```

### File: `frontend/src/components/TopicInput.jsx`

```jsx
/**
 * Step 1: Topic Input Form
 *
 * Fields:
 * - 主题 (Topic): text input, placeholder "例如：MakeCode Arcade游戏编程入门"
 * - 场景 (Scenario): radio buttons — 课堂教学 / 教会讲座 / 家长说明 / 通用
 * - 页数 (Slides): number input, range 4-15, default 8
 * - 语言 (Language): radio buttons — 中文 / English / 双语
 *
 * Submit button: "✨ 生成大纲" (large, primary color, centered)
 *
 * Layout:
 * - Card-style container, max-width 600px, centered
 * - Each field is a labeled row
 * - Generous spacing (py-3 between fields)
 * - Mobile-friendly (single column)
 */
```

### File: `frontend/src/components/OutlineEditor.jsx`

```jsx
/**
 * Step 2: Outline Editor
 *
 * Displays the AI-generated outline as editable slide cards.
 *
 * Each slide card shows:
 * - Slide number badge (colored circle)
 * - Slide type label (标题页 / 内容页 / 总结页)
 * - Title: editable text input
 * - Content points: editable list (add/remove/reorder)
 *
 * Actions:
 * - "添加幻灯片" button at bottom to add new slide
 * - "×" button on each slide to delete it
 * - Drag handle (optional, Phase 2) for reordering
 * - Template selector dropdown at the top
 *
 * Bottom action bar:
 * - "← 返回修改主题" (secondary button)
 * - "生成 PPT →" (primary button, large)
 *
 * Design notes:
 * - Each card has subtle border-left color matching slide type
 * - Title page cards have blue accent
 * - Content page cards have gray accent
 * - Conclusion cards have green accent
 */
```

### File: `frontend/src/components/TemplateSelector.jsx`

```jsx
/**
 * Template Selector — shown in Step 2
 *
 * Displays available templates as small preview cards:
 * - Template name (Chinese)
 * - Color swatch showing primary/secondary/accent
 * - Selected state: highlighted border
 *
 * Fetches template list from GET /api/templates
 *
 * Layout: horizontal scroll row or 2x2 grid
 * Default selection: based on scenario (teaching→teaching, church→church)
 */
```

---

## Phase 5: Integration & API Routes

### File: `backend/app.py`

```python
"""
Flask application entry point.

Routes:
  GET  /                           → Serve React frontend
  GET  /api/templates              → List available templates
  GET  /api/health                 → Health check (also checks LLM connectivity)
  POST /api/generate-outline       → Generate outline from topic (1 LLM call)
  POST /api/generate-pptx          → Render PPTX from outline (0 LLM calls)
  GET  /api/download/<filename>    → Download generated PPTX file

CORS: Enabled for localhost development
Static files: Serve React build from frontend/build/

LLM connectivity check on startup:
  - Try GET http://localhost:1234/v1/models
  - If fails: warn but don't crash (user might start LM Studio later)
  - Display LLM status on frontend health indicator
"""

# Route specifications:

# POST /api/generate-outline
# Request body:
# {
#   "topic": "MakeCode Arcade游戏编程入门",
#   "num_slides": 8,
#   "scenario": "teaching",   // teaching|church|parents|general
#   "language": "zh"          // zh|en|bilingual
# }
# Response: { "success": true, "outline": { ... } }
# Error: { "success": false, "error": "LM Studio未连接" }
# Timeout: 300 seconds

# POST /api/generate-pptx
# Request body:
# {
#   "outline": { ... },      // validated outline JSON
#   "template_id": "teaching" // template to use
# }
# Response: file download (application/vnd.openxmlformats-officedocument.presentationml.presentation)
# Filename: {outline.title}_{date}.pptx

# GET /api/templates
# Response: { "templates": [ { "id": "teaching", "name": "课堂教学", ... } ] }

# GET /api/health
# Response: {
#   "status": "ok",
#   "llm_connected": true/false,
#   "llm_model": "qwen3.5-4b-...",
#   "version": "0.1.0"
# }
```

### File: `backend/config.py`

```python
"""
Configuration — loaded from .env file or environment variables.

All LLM settings are compatible with:
- LM Studio (default): localhost:1234
- OpenRouter: openrouter.ai/api/v1
- Mistral: api.mistral.ai/v1
- Any OpenAI-compatible endpoint
"""

# CONFIG SCHEMA:
# LLM_BASE_URL     = "http://localhost:1234/v1"  # LM Studio default
# LLM_API_KEY      = "lm-studio"                 # LM Studio ignores this
# LLM_MODEL        = "qwen3.5-4b"                # Model identifier
# LLM_TEMPERATURE  = 0.7
# LLM_MAX_TOKENS   = 4096
# LLM_TIMEOUT      = 300                          # seconds
#
# SERVER_HOST      = "127.0.0.1"
# SERVER_PORT      = 5000
# OUTPUT_DIR       = "./output"
#
# To use OpenRouter instead:
# LLM_BASE_URL     = "https://openrouter.ai/api/v1"
# LLM_API_KEY      = "sk-or-v1-your-key-here"
# LLM_MODEL        = "meta-llama/llama-3.3-70b-instruct"
```

---

## Phase 6: Packaging & Distribution

### File: `scripts/start.bat` (Windows one-click launcher)

```batch
@echo off
chcp 65001 >nul
echo.
echo  ╔══════════════════════════════════════╗
echo  ║    Bashi PPT 幻灯锻造 v0.1.0       ║
echo  ║    本地AI PPT生成器                  ║
echo  ╚══════════════════════════════════════╝
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

REM Check/create venv
if not exist "venv" (
    echo [安装] 首次运行，正在创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r backend\requirements.txt
) else (
    call venv\Scripts\activate
)

REM Check LM Studio
echo [检查] 正在检测LM Studio...
curl -s http://localhost:1234/v1/models >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] LM Studio未检测到，请先启动LM Studio并加载模型
    echo [提示] 启动后可继续使用，按任意键继续...
    pause >nul
)

REM Start Flask server
echo [启动] 正在启动Bashi PPT服务...
echo [访问] 请打开浏览器访问: http://localhost:5000
echo.
python backend/app.py
```

### File: `requirements.txt`

```
flask>=3.0.0
flask-cors>=4.0.0
openai>=1.0.0
python-pptx>=0.6.23
python-dotenv>=1.0.0
Pillow>=10.0.0
json-repair>=0.30.0
```

---

## JSON Schema Reference

### Outline JSON (LLM Output)

```json
{
  "title": "演示文稿标题",
  "slides": [
    {
      "page_number": 1,
      "title": "欢迎来到游戏编程世界！",
      "content_points": [
        "适合8-9岁小创客",
        "用代码创造乐趣",
        "开启第一节课"
      ],
      "slide_type": "title"
    },
    {
      "page_number": 2,
      "title": "课程结构概览",
      "content_points": [
        "为什么学习编程？",
        "基础概念解析",
        "实践案例展示",
        "互动活动设计"
      ],
      "slide_type": "content"
    }
  ]
}
```

### Template Config JSON

```json
{
  "id": "teaching",
  "name": "课堂教学 (Classroom)",
  "description": "适合编程教学、课堂演示",
  "theme": "clean_blue",
  "default_slides": 8,
  "default_scenario": "teaching",
  "layout_mapping": {
    "title": "TitleCenterLayout",
    "content": "ContentBulletLayout",
    "conclusion": "ConclusionLayout"
  }
}
```

---

## Prompt Engineering Reference

### Why the prompt is designed this way

The system prompt is intentionally minimal (~200 tokens) because:
1. Local 4B model has 12K context window
2. User prompt adds ~100 tokens (topic + settings)
3. Output needs ~2000-3000 tokens for 8-slide outline
4. Total budget: ~200 (system) + ~100 (user) + ~3000 (output) = ~3300 tokens
5. This leaves ~9000 tokens of headroom — no context pressure

### Critical instructions in the prompt

The line "不要生成chart_config或任何图表数据" is essential.
Without it, Qwen3.5-4B will hallucinate chart configurations on every slide
(confirmed by testing — see devlogs from 2026-03-25).

The line "每个要点不超过30个字" prevents the model from generating
paragraph-length bullet points that overflow the PPTX text boxes.

### Testing prompts for different scenarios

**Teaching test:**
主题：MakeCode Arcade游戏编程入门 — 给8-9岁小学生的第一节课

**Church test:**
主题：认识圣经：旧约概览 — 适合慕道友的入门介绍

**Parent communication test:**
主题：为什么孩子应该学编程 — 面向家长的课程说明会

---

## Testing Checklist

### Phase 1 Tests (LLM Outline)
- [ ] Generate outline with LM Studio + Qwen3.5-4B → valid JSON returned
- [ ] Generate outline with LM Studio + Qwen2.5-7B → valid JSON returned
- [ ] Generate outline with OpenRouter + Llama 3.3 70B → valid JSON returned
- [ ] Handle LM Studio not running → graceful error message
- [ ] Handle malformed JSON response → parser repairs it
- [ ] Handle timeout (>300s) → error message, not crash
- [ ] Outline with 4 slides → correct structure
- [ ] Outline with 15 slides → correct structure
- [ ] Chinese topic → Chinese content
- [ ] English topic → English content
- [ ] Church topic (旧约概览) → no censorship issues with local model

### Phase 2 Tests (PPTX Rendering)
- [ ] Render 8-slide outline → valid .pptx file
- [ ] Open in PowerPoint → renders correctly
- [ ] Open in WPS Office → renders correctly
- [ ] Open in LibreOffice Impress → renders correctly
- [ ] Chinese characters display correctly (微软雅黑)
- [ ] All 4 themes render without errors
- [ ] Page numbers show correctly (1/8, 2/8, etc.)
- [ ] Title slide has centered layout
- [ ] Content slides have bullet points
- [ ] Conclusion slide has appropriate layout
- [ ] File size is reasonable (<2MB for 8 slides, no images)

### Phase 3 Tests (Frontend)
- [ ] Topic input form submits correctly
- [ ] Outline editor displays all slides
- [ ] Can edit slide titles inline
- [ ] Can edit content points inline
- [ ] Can add a new slide
- [ ] Can delete a slide
- [ ] Template selector shows all templates
- [ ] Changing template updates preview color swatches
- [ ] "生成PPT" triggers download
- [ ] Downloaded file opens correctly
- [ ] "重新开始" resets the form
- [ ] Works in Chrome, Edge, Firefox

### Phase 4 Tests (End-to-End)
- [ ] Full flow: topic → outline → edit → generate → download → open in PPT
- [ ] Total time from topic to download: under 2 minutes with local 4B model
- [ ] start.bat launches successfully on Windows
- [ ] Health check endpoint reports correct LLM status

---

## Known Constraints & Design Decisions

### Why python-pptx instead of HTML slides?
LandPPT generates HTML slides, which look great in a browser but:
- Can't be edited in PowerPoint/WPS (which all target users have)
- PPTX export requires paid Apryse SDK license
- HTML slides need internet for fonts/CSS CDNs
python-pptx produces native .pptx that works offline, everywhere.

### Why no images in v0.1?
Image handling adds significant complexity:
- Need image search API (Pixabay/Unsplash)
- Need image placement logic (sizing, positioning, cropping)
- Need to handle network failures gracefully
- Increases file size dramatically
Plan: Add image support in v0.2 after core flow is stable.

### Why Flask and not FastAPI?
User is already familiar with Flask from Edge TTS Studio and
Local Voice Studio projects. Consistency > novelty.

### Why Tailwind CDN instead of a build step?
Target users may need to tweak the frontend. A build step
(npm run build) adds complexity. Tailwind CDN works without Node.js
for the initial prototype. Can migrate to a build step later.

### Why 16:9 widescreen?
Standard for modern projectors and screens. LandPPT also uses 16:9.
python-pptx default is 4:3, so we explicitly set 13.333" x 7.5".

### Font strategy for cross-platform compatibility
- Windows: "Microsoft YaHei" (微软雅黑) — pre-installed
- Linux: "Noto Sans SC" — installable via apt
- macOS: "PingFang SC" — pre-installed
- The renderer sets eastAsian font properties to ensure Chinese
  characters render correctly even if the primary font doesn't
  have CJK glyphs.

### Context window budget breakdown
```
System prompt:        ~200 tokens
User prompt:          ~100 tokens
Model output:        ~2500 tokens (8-slide outline)
─────────────────────────────────
Total:               ~2800 tokens
Available:           12,288 tokens (Qwen3.5-4B with n_ctx=12288)
Headroom:            ~9,400 tokens (77% free)
```
Compare with LandPPT's pipeline: 11,951 tokens input for a single
slide's HTML generation, leaving only 337 tokens for output (truncated).

---

## Development Order for AI Agents

Recommended build sequence:

```
Sprint 1 (Day 1-2): Skeleton
  → backend/config.py
  → backend/app.py (Flask shell with routes returning mock data)
  → frontend/ (React shell with hardcoded UI)
  → Verify: Flask serves React, API routes respond

Sprint 2 (Day 3-4): LLM Integration
  → backend/llm/prompts.py
  → backend/llm/client.py
  → backend/llm/outline_parser.py
  → Verify: POST /api/generate-outline returns valid JSON from LM Studio

Sprint 3 (Day 5-7): PPTX Renderer
  → backend/renderer/theme.py
  → backend/renderer/slide_layouts.py
  → backend/renderer/engine.py
  → Verify: POST /api/generate-pptx returns downloadable .pptx

Sprint 4 (Day 8-10): Frontend Polish
  → frontend/src/components/TopicInput.jsx
  → frontend/src/components/OutlineEditor.jsx
  → frontend/src/components/TemplateSelector.jsx
  → frontend/src/components/GenerateButton.jsx
  → Verify: Full end-to-end flow works

Sprint 5 (Day 11-12): Packaging
  → scripts/start.bat
  → scripts/setup.bat
  → .env.example
  → README.md (bilingual)
  → Verify: Double-click start.bat, full flow works
```
