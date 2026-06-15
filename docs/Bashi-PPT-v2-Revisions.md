# Bashi PPT v2 Revisions
## Mandatory Changes from Peer Review

> Feed this THIRD, after the Implementation Plan and Agent Briefing.
> This document OVERRIDES any conflicting instructions in those two files.
> All five reviewers (ChatGPT, Gemini, Grok, Qwen3.5, GLM-5) flagged
> the same core issues. This revision addresses them.

---

## Revision 1: Frontend — Pick One Route

**Problem:** Documents say "Tailwind CDN, no build step" but also reference
`frontend/build/`, React components with JSX, and `package.json`. These
are contradictory. AI agents will produce broken hybrid output.

**Decision: Use React + Vite + Tailwind (with build step).**

Rationale: Node.js is available on the system. The component structure
is already designed around React. The OutlineEditor needs proper state
management. CDN-only React cannot handle JSX without a transpiler.

**Agent instructions:**
```
Frontend setup:
- Use Vite with React template: npm create vite@latest frontend -- --template react
- Install Tailwind CSS via PostCSS (not CDN)
- Use npm run build to produce static files
- Flask serves the built files from frontend/dist/ (Vite default, not build/)
- During development: Vite dev server on port 5173 proxying API to Flask on 5000
```

**Delete from original plan:**
- All references to "Tailwind CDN" and "no build step"
- The phrase "Serve React build from frontend/build/"
- Change to: "Serve Vite output from frontend/dist/"

---

## Revision 2: Performance Targets — Be Honest

**Problem:** Testing showed 3.5 minutes for outline generation on local
Qwen3.5-4B, but the test checklist says "under 2 minutes end-to-end."
This is impossible and will cause every test to fail.

**Revised targets:**
```
Outline generation (local 4B model):   2–5 minutes (depending on slide count)
Outline generation (cloud API):        5–15 seconds
PPTX rendering:                        1–5 seconds
End-to-end (local):                    3–6 minutes
End-to-end (cloud):                    10–30 seconds
```

**UX requirement:** The frontend MUST show real progress during generation.
Do NOT use a fake progress bar. Instead:

```
Option A (v0.1 — simplest):
  - Show "正在生成大纲，请稍候..." with a spinning indicator
  - Set fetch timeout to 360 seconds (6 minutes)
  - Flask returns the complete response when done

Option B (v0.2 — better):
  - POST /api/generate-outline returns a task_id immediately
  - Frontend polls GET /api/outline-status/{task_id} every 3 seconds
  - Backend runs LLM in a background thread
  - Status responses: { "status": "thinking", "elapsed_seconds": 45 }
  - When done: { "status": "complete", "outline": {...} }
```

**For v0.1, use Option A.** It's simpler and the 4B model won't crash
Flask since it's a single-user local app. Add a clear message to the
UI: "本地模型生成中，通常需要3-5分钟，请耐心等待..."

---

## Revision 3: Unified Schema — Single Source of Truth

**Problem:** Prompt says "3-4 points per slide", parser allows "1-6",
reference JSON has 5 points on some slides. This inconsistency will
cause the model output to drift and the editor/renderer to disagree.

**The canonical schema (use this everywhere):**

```python
# File: backend/schema.py — THE single source of truth

SLIDE_CONSTRAINTS = {
    "title": {
        "min_points": 2,
        "max_points": 4,
        "max_point_length": 20,  # characters
        "max_title_length": 25,
    },
    "content": {
        "min_points": 3,
        "max_points": 5,
        "max_point_length": 25,  # characters
        "max_title_length": 20,
    },
    "conclusion": {
        "min_points": 2,
        "max_points": 4,
        "max_point_length": 20,
        "max_title_length": 15,
    },
}

OUTLINE_CONSTRAINTS = {
    "min_slides": 4,
    "max_slides": 15,
    "required_structure": ["title", "content+", "conclusion"],
    # "content+" means one or more content slides
}
```

**This file is imported by:**
- `prompts.py` — to generate the prompt dynamically from constraints
- `outline_parser.py` — to validate against the same rules
- Frontend `OutlineEditor.jsx` — to enforce the same limits in the UI
- `renderer/engine.py` — to know max text lengths for overflow handling

**Update the system prompt to match:**
```
"标题页：2-4个要点，每点不超过20字
内容页：3-5个要点，每点不超过25字
总结页：2-4个要点，每点不超过20字"
```

---

## Revision 4: Download — Stream Bytes, Don't Save Files

**Problem:** The file-based download mechanism (`output/` directory +
`/api/download/<filename>`) creates unnecessary complexity for a
single-user local app: file cleanup, name collisions, Chinese filename
encoding, disk accumulation.

**Revised approach:**

```python
# In app.py — POST /api/generate-pptx

from flask import send_file
from io import BytesIO

@app.route('/api/generate-pptx', methods=['POST'])
def generate_pptx():
    data = request.get_json()
    outline = data['outline']
    template_id = data.get('template_id', 'default')

    renderer = PPTXRenderer(template_id)
    pptx_bytes = renderer.render(outline)  # Returns bytes

    buffer = BytesIO(pptx_bytes)
    buffer.seek(0)

    filename = f"{outline['title']}.pptx"

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation'
    )
```

```javascript
// In frontend API client

async function generatePptx(outline, templateId) {
  const response = await fetch('/api/generate-pptx', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outline, template_id: templateId }),
  });

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${outline.title}.pptx`;
  a.click();
  URL.revokeObjectURL(url);
}
```

**Delete from original plan:**
- The `backend/output/` directory
- The `GET /api/download/<filename>` route
- Any file cleanup logic

---

## Revision 5: Text Overflow Strategy

**Problem:** All reviewers flagged this. Even with character limits in the
prompt, real-world content (bilingual text, long Bible verse references,
parent communication details) WILL overflow textboxes. python-pptx has
no auto-shrink — you must implement it manually.

**Add to `backend/renderer/engine.py`:**

```python
def _fit_text_in_box(self, text_frame, max_height_inches, content_points,
                     base_font_size=20, min_font_size=14):
    """
    Progressive text fitting strategy:

    Step 1: Render at base_font_size
    Step 2: If overflow → reduce font size by 2pt, retry
    Step 3: If still overflow at min_font_size → reduce line spacing
    Step 4: If still overflow → truncate last point and add "..."
    Step 5: Return layout_warning=True so frontend can flag it

    Overflow detection:
    python-pptx doesn't provide rendered text height directly.
    Estimate using: line_count * (font_size_pt * 1.5) / 72 inches
    where 1.5 is approximate line spacing factor.
    """
    pass  # Implementation details for the agent
```

**Estimation formula for text height:**
```python
def estimate_text_height(content_points, font_size_pt, box_width_inches):
    """
    Rough estimate of rendered text height.
    Assumes average Chinese character width ≈ font_size_pt points.
    """
    total_lines = 0
    chars_per_line = int(box_width_inches * 72 / font_size_pt)  # approximate

    for point in content_points:
        lines_needed = max(1, -(-len(point) // chars_per_line))  # ceil division
        total_lines += lines_needed

    # Height = lines × font_size × line_spacing_factor / 72 (convert pt to inches)
    line_spacing = 1.5
    height_inches = total_lines * font_size_pt * line_spacing / 72
    return height_inches
```

---

## Revision 6: Error Handling & Input Validation

**Problem:** Multiple reviewers noted missing input validation, no
structured error responses, and no logging.

**Add to `backend/app.py`:**

```python
# Standardized error response format
def error_response(message_zh, message_en, status_code=400):
    return jsonify({
        "success": False,
        "error": message_zh,
        "error_en": message_en,
    }), status_code

# Input validation for /api/generate-outline
def validate_outline_request(data):
    errors = []

    topic = data.get('topic', '').strip()
    if not topic:
        errors.append("请输入主题")
    if len(topic) > 200:
        errors.append("主题不能超过200个字符")

    num_slides = data.get('num_slides', 8)
    if not isinstance(num_slides, int) or num_slides < 4 or num_slides > 15:
        errors.append("页数必须在4-15之间")

    scenario = data.get('scenario', 'general')
    if scenario not in ('teaching', 'church', 'parents', 'general'):
        errors.append("无效的场景类型")

    return errors
```

**Add logging:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('Bashi PPT.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('Bashi PPT')

# Usage in outline generation:
logger.info(f"Generating outline: topic='{topic}', slides={num_slides}")
logger.info(f"LLM response received: {len(raw_text)} chars in {elapsed:.1f}s")
logger.warning(f"JSON repair needed: {repair_details}")
```

---

## Revision 7: Additional Dependencies

**Updated `requirements.txt`:**
```
flask>=3.0.0
flask-cors>=4.0.0
openai>=1.0.0
python-pptx>=0.6.23
python-dotenv>=1.0.0
Pillow>=10.0.0
json-repair>=0.30.0
pydantic>=2.0.0
```

**Why Pydantic:** Use it for outline validation instead of manual dict
checking. This gives you automatic type coercion, clear error messages,
and a schema that can be exported to JSON Schema for the frontend.

```python
from pydantic import BaseModel, Field, validator
from typing import List, Literal

class SlideData(BaseModel):
    page_number: int = Field(ge=1, le=15)
    title: str = Field(max_length=30)
    content_points: List[str] = Field(min_length=2, max_length=5)
    slide_type: Literal["title", "content", "conclusion"]

class OutlineData(BaseModel):
    title: str = Field(max_length=50)
    slides: List[SlideData] = Field(min_length=4, max_length=15)
```

---

## Revision 8: Themes — Start with 2, Not 4

**Problem:** Multiple reviewers noted that polishing 2 themes is better
than shipping 4 half-baked ones.

**v0.1 ships with:**
- `clean_blue` — default for teaching and general use
- `church_grace` — for church content

**v0.2 adds:**
- `warm_earth` — for parent communication
- `dark_arcade` — for MakeCode/gaming content

**Delete `warm_earth` and `dark_arcade` from the v0.1 theme definitions.**
Keep them in the code as comments marked `# v0.2` so nothing is lost.

---

## Summary: What the Agent Gets

Feed the AI coding agent these three files in order:

```
1. Bashi PPT-Implementation-Plan.md    ← What to build
2. Bashi PPT-Agent-Briefing.md         ← Why and constraints
3. Bashi PPT-v2-Revisions.md           ← THIS FILE: overrides & fixes
```

Tell the agent: "Document 3 overrides Documents 1 and 2 wherever they
conflict. Follow Document 3's decisions on frontend approach, performance
targets, schema, download method, and error handling."

---

## Revised Sprint Plan

```
Sprint 1 (Day 1-2): Skeleton + Schema
  → backend/config.py, backend/schema.py, backend/app.py
  → Vite + React + Tailwind frontend scaffold
  → .env.example with LM Studio defaults
  → Verify: Flask serves React, API routes return mock data

Sprint 2 (Day 3-5): LLM Integration + Robustness
  → backend/llm/prompts.py (using schema.py constraints)
  → backend/llm/client.py (with 360s timeout, retry logic)
  → backend/llm/outline_parser.py (with Pydantic validation)
  → Verify: POST /api/generate-outline returns valid JSON from LM Studio
  → Test with all 3 scenarios: teaching, church, parents

Sprint 3 (Day 6-8): PPTX Renderer
  → backend/renderer/theme.py (2 themes only: clean_blue, church_grace)
  → backend/renderer/slide_layouts.py
  → backend/renderer/engine.py (with text overflow strategy)
  → Verify: POST /api/generate-pptx streams downloadable .pptx
  → Test: open in PowerPoint, WPS, LibreOffice

Sprint 4 (Day 9-11): Frontend Polish
  → TopicInput.jsx with input validation
  → OutlineEditor.jsx with add/delete/edit
  → TemplateSelector.jsx (2 templates)
  → GenerateButton.jsx with loading state + "请耐心等待" message
  → Verify: full end-to-end flow

Sprint 5 (Day 12-13): Packaging + Testing
  → scripts/start.bat with Python version check
  → README.md (bilingual)
  → End-to-end testing with all 3 test prompts
  → Fix any text overflow issues found in testing
```
