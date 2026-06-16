# Excalidraw Diagram Integration — Handoff / Status

> Purpose: a self-contained brief so another agent (e.g. Codex in VS Code) can pick up
> remaining work without re-deriving context. Covers the plan, what is **already done**
> (do not redo), and **scoped tasks** to delegate.

App: **Bashi PPT / SlideForge** — a portable Windows, local-first AI PowerPoint generator.
Backend: Flask + python-pptx + Pillow. Frontend: React 19 + Vite 8 + Tailwind, pre-built
to `frontend/dist/` and served statically by Flask. Launched via `run_portable.bat` on an
embedded Python (no system Python/npm at runtime). LLM is OpenAI-compatible (LM Studio etc.).

---

## 1. Goal & Approved Approach

Add optional **hand-drawn (Excalidraw-style) diagrams** to content slides.

- **Architecture: Option B — frontend Excalidraw bridge.** The LLM (or user) supplies
  **Mermaid**; the browser converts it to an Excalidraw PNG and the backend embeds that PNG.
  Chosen because the app is already fully browser-driven (no headless CLI to support) and
  this gives true hand-drawn fidelity without server-side Node/Chromium.
- **Source: both** — the LLM suggests Mermaid; the user can edit it before export.
- **Target model:** user runs `google/gemma-4-12b-qat` (12B), so Mermaid generation is
  reliable enough (the old prompt ban on chart data existed for a 4B model).

Data flow:
```
LLM outline → slide.diagram (Mermaid)          [prompts.py asks; outline_parser.py preserves]
Editor      → user views/edits; live preview
On export   → mermaid → Excalidraw PNG → slide.diagram_image (base64 data-URL)
POST /api/generate-pptx (full outline) → engine.py decodes base64 → right column
```

Key gotcha (the reason naive plans fail): `outline_parser._normalize_outline` **rebuilds
each slide dict from scratch**, dropping any field it doesn't explicitly copy (this is why
`image_url`, added client-side, never survives the parser). So an LLM `diagram` field must
be copied through explicitly. `diagram_image` is added client-side only and never touches
the parser; `/api/generate-pptx` renders the raw dict without re-validation.

---

## 2. What Is DONE (implemented, tested — do not redo)

### Backend
- **`backend/schema.py`** — `SlideData` now has optional `diagram: Optional[str]` and
  `diagram_image: Optional[str]`.
- **`backend/llm/outline_parser.py`** — `_normalize_outline` copies a non-empty `diagram`
  through **on content slides only**; `chart_config`/`image_config`/`description`/`type`
  still stripped. `diagram` is intentionally NOT in `FORBIDDEN_FIELDS`.
- **`backend/llm/prompts.py`** — old rule 9 narrowed; new rule 10 asks the model to add an
  optional `diagram` (Mermaid) **only** on content slides where a flow/relationship helps,
  with short node labels; title/conclusion slides must not have it.
- **`backend/renderer/engine.py`**:
  - New `_decode_data_url(data_url)` — decodes a `data:image/png;base64,...` URL to a temp
    PNG. (The existing `_download_image` uses urllib and cannot read data URLs.)
  - `_render_content_slide` graphic selection: `image_url` wins; else `diagram_image` is
    decoded. Reuses the existing aspect-ratio / centering / temp-file cleanup path, so the
    diagram lands in the same right-column box as search images.

### Frontend
- Deps added: `@excalidraw/excalidraw@0.18.1`, `@excalidraw/mermaid-to-excalidraw@2.2.2`.
  (Installed with `--strict-ssl=false` due to the network's SSL interception.)
- **`frontend/src/utils/diagramRenderer.js`** (new) — `mermaidToPngDataUrl(mermaid)`:
  `parseMermaidToExcalidraw` → `convertToExcalidrawElements` → `exportToBlob` → data-URL.
  Runs **headless** (no `<Excalidraw>` component mount), so React 19 incompatibility of the
  component is irrelevant. Returns `null` on invalid Mermaid (recoverable).
- **`frontend/src/components/OutlineEditor.jsx`** — on content slides: a Mermaid `<textarea>`
  (`updateSlideDiagram`), a "预览/Preview" button, inline preview image, loading/error states,
  and a note when a search image will take precedence. Previews live in `diagramPreviews`
  state keyed by `page_number`, each tagged with the `source` Mermaid it was rendered from
  so renumbering/edits self-correct. A **debounced** (600 ms) `useEffect` auto-renders any
  content slide whose `diagram` lacks an up-to-date preview (LLM-supplied, user-edited, or
  stale after renumber) — debounced so typing doesn't render on every keystroke. The manual
  Preview button renders immediately.
- **`frontend/src/App.jsx`** — `ensureDiagramImages(outline)` renders a **fresh** PNG for each
  content slide's `diagram` right before `generatePptx` (avoids stale images) and clears
  `diagram_image` when `image_url` is set. Called in `handleGeneratePptx`.
- **Offline fonts** (critical): Excalidraw fetches fonts at runtime from
  `${window.EXCALIDRAW_ASSET_PATH}fonts/...`; **none are bundled by default**. So:
  - `frontend/index.html` sets `window.EXCALIDRAW_ASSET_PATH = '/'` via an inline `<head>`
    script, so it runs before any module bundle evaluates (not dependent on ESM import order).
  - `frontend/vite.config.js` has an inline `copyExcalidrawFonts` plugin that copies
    `node_modules/@excalidraw/excalidraw/dist/prod/fonts` → `dist/fonts/` on build
    (234 woff2, ~12.5 MB incl. CJK Xiaolai needed for Chinese labels). Verified that
    `dist/fonts/Virgil/Virgil-Regular.woff2` etc. match the runtime requests off base `/`.

### Tests
- **`tests/test_diagrams.py`** (new): parser preserves `diagram` on content + strips it on
  title/conclusion + still removes `chart_config`; engine embeds `diagram_image` as one
  picture; `image_url` precedence (diagram not used when image present).
- Full suite green: `venv\Scripts\python.exe -m unittest discover -s tests` → **15/15 OK**.
- `npm run build` succeeds. Repo-wide `npm run lint` exits **0** (clean). There is one
  remaining **pre-existing warning** (not an error) in `ImageSearchModal.jsx`
  (`react-hooks/exhaustive-deps` on `handleSearch`), intentionally left as-is because the
  obvious fix changes when searches fire. Note: a few pre-existing lint *errors* in
  `LLMSettings.jsx` / `LyricsInput.jsx` / `TopicInput.jsx` were fixed as part of this work
  (unused prop + `set-state-in-effect` → render-phase "adjust state" pattern).

---

## 3. What is NOT yet done (needs the user's machine — cannot be done by a coding agent)

Manual end-to-end verification, requires LM Studio + a browser:
1. Load `google/gemma-4-12b-qat`; generate an outline for a flow-y topic
   (e.g. "搜索引擎如何工作"). Confirm ≥1 content slide arrives with a `diagram`.
2. Confirm the editor shows a hand-drawn preview; edit the Mermaid and re-preview.
3. Export PPTX; confirm the wobbly diagram sits in the right column with correct aspect
   ratio; slides without diagrams unchanged.
4. Regression: Hymn workflow + a no-diagram outline still work.
5. Offline check: with no internet, the preview/export still renders (fonts from `/fonts`).

---

## 4. Scoped tasks that CAN be delegated to Codex

Each is independent and well-bounded. Pick any.

### Task A — DONE (lazy-loaded diagram libraries)

Implemented: `frontend/src/utils/diagramRenderer.js` now dynamically `import()`s
`@excalidraw/excalidraw` and `@excalidraw/mermaid-to-excalidraw` inside
`mermaidToPngDataUrl` (same async signature, so `OutlineEditor.jsx` / `App.jsx` are
unchanged). Result: the main bundle dropped from **~1,468 KB → ~236 KB**; Excalidraw
(~1.78 MB) and mermaid now load as separate async chunks only when a diagram is first
rendered. Offline font copy is unaffected (still set in index.html + copied to dist/fonts).

### Task B — DONE (debounced live preview)

Implemented: the auto-preview `useEffect` is debounced 600 ms, so editing the Mermaid
textarea refreshes the preview after the user pauses rather than on every keystroke; the
manual "预览" button still renders immediately. No further action needed unless you want to
tune the delay or switch back to manual-only.

### Task C — Export progress affordance
`ensureDiagramImages` can take a second or two when several slides have diagrams. Add a small
"正在渲染图示…" state to `handleGeneratePptx` (reuse existing `GENERATING_PPTX` step / spinner)
so the user knows export is working. Pure UX, no backend change.

### Task D — Docs
Update `README.md` / `README_CN.md` with a short "手绘图示 / Diagrams" section: how the LLM
suggests Mermaid, how to edit/preview, and that it embeds as an image in the right column.

---

## 5. Conventions / constraints to respect
- Keep the **portable/offline** model: no new runtime network calls, no server-side Node or
  native binaries; frontend additions are static weight in `dist` (acceptable), not embedded
  Python weight.
- Backend tests are **unittest** (no pytest installed). Run with
  `venv\Scripts\python.exe -m unittest discover -s tests`.
- Backend modules import as top-level (e.g. `from renderer.engine import ...`) because
  `backend/` is added to `sys.path`; tests do `sys.path.insert(0, .../backend)`.
- npm installs in this environment need `--strict-ssl=false` (SSL interception). Mirrors the
  app's own `VERIFY_SSL=false` proxy support.
- Slide constraints (points/title lengths, 4–15 slides, first=title/last=conclusion) are
  enforced in both `backend/schema.py` and `frontend/src/components/OutlineEditor.jsx`.

## 6. Touched files (for review)
```
backend/schema.py
backend/llm/outline_parser.py
backend/llm/prompts.py
backend/renderer/engine.py
frontend/package.json            (+ package-lock.json)
frontend/index.html              (sets window.EXCALIDRAW_ASSET_PATH)
frontend/vite.config.js
frontend/src/main.jsx
frontend/src/utils/diagramRenderer.js   (new)
frontend/src/components/OutlineEditor.jsx
frontend/src/App.jsx
tests/test_diagrams.py           (new)
frontend/dist/**                 (rebuilt; includes dist/fonts/**)

# Pre-existing lint errors fixed alongside this work (unrelated to diagrams):
frontend/src/components/LLMSettings.jsx   (removed unused onClose prop)
frontend/src/components/LyricsInput.jsx   (set-state-in-effect → render-phase pattern)
frontend/src/components/TopicInput.jsx    (set-state-in-effect → render-phase pattern)
```
