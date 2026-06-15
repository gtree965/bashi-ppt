# Hymn Lyrics Feature (Generalized Language Mode)

This plan details the implementation of a new "Hymn Lyrics PPT" mode for Bashi PPT. It transitions the application from a single-purpose presentation generator into a dual-mode tool capable of creating both standard presentations and specialized hymn lyric slides with support for single and bilingual formatting.

## User Review Required

The proposed plan is exceptionally well-structured and maps perfectly to the current Bashi PPT architecture. I have reviewed the codebase and everything aligns well:
- `backend/renderer/utils.py` already exists as an empty file, ready for the utility extraction.
- The dual-mode UI fits neatly into the React frontend.
- Isolating the lyrics backend logic into `backend/lyrics/` is a solid architectural decision to prevent bloating the core PPTX generation engine.

Please review the plan below. If you approve, I will begin execution starting with Phase 5 (Utility Extraction).

## Proposed Changes

---

### Shared Utilities

Extracting shared functions allows both the standard presentation renderer and the new lyrics renderer to use them without circular dependencies.

#### [MODIFY] [backend/renderer/engine.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/engine.py)
- Remove `hex_to_rgb` and `set_chinese_font`.
- Add imports for these functions from `backend.renderer.utils`.

#### [MODIFY] [backend/renderer/utils.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/utils.py)
- Add `hex_to_rgb` function.
- Add `set_chinese_font` function (and potentially alias or rename it to `set_font_with_east_asian` as suggested, to reflect its broader utility for multiple scripts).

---

### Backend: Lyrics Module

Isolated module for handling all lyrics-specific logic including language detection, parsing, and PPTX rendering.

#### [NEW] [backend/lyrics/__init__.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/lyrics/__init__.py)
- Empty initialization file to make the directory a package.

#### [NEW] [backend/lyrics/schemas.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/lyrics/schemas.py)
- Define Pydantic models: `LanguageConfig`, `LyricsRequest`.
- Define dataclasses: `LyricLine`, `LyricSection`, `LyricDocument`.
- Define `LANGUAGE_OPTIONS` list for frontend consumption.

#### [NEW] [backend/lyrics/lang_detect.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/lyrics/lang_detect.py)
- Unicode-based language detection.
- `SCRIPT_RANGES`: Dictionary mapping scripts.
- `classify_line`: Returns dominant script.
- `detect_bilingual_structure`: Detects alternating vs separated format.
- `pair_bilingual_lines`: Pairs primary/secondary lines.

#### [NEW] [backend/lyrics/parser.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/lyrics/parser.py)
- `parse_lyrics`: Splits by blank lines, detects section markers.
- `split_into_slides`: Smart pagination respecting section boundaries.

#### [NEW] [backend/lyrics/renderer.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/lyrics/renderer.py)
- PPTX generation specific to lyrics (no bullets, centered large text).
- `LYRICS_THEMES`, `LANGUAGE_FONT_SIZES`, `LANGUAGE_FONTS` configurations.
- `LyricsPPTXRenderer` class with `render` method and slide-specific rendering helpers.

---

### Backend: API Routes

Connect the new lyrics module to the frontend via Flask routes.

#### [MODIFY] [backend/app.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/app.py)
- Add `POST /api/preview-lyrics`: Returns JSON with slide breakdown for frontend previews.
- Add `POST /api/generate-lyrics-pptx`: Returns the generated PPTX binary.
- Add `GET /api/lyrics-languages`: Returns available language options.

---

### Frontend: Core Components

New components for the Hymn Lyrics workflow.

#### [NEW] [frontend/src/components/LyricsInput.jsx](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/frontend/src/components/LyricsInput.jsx)
- Form with textarea for lyrics.
- Song title input.
- Generalized language selector (Single vs Bilingual, corresponding dropdowns).
- Lines per slide selector (2-4 single, 2-3 bilingual).
- Theme picker, check-boxes for title/amen slides.

#### [NEW] [frontend/src/components/LyricsPreview.jsx](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/frontend/src/components/LyricsPreview.jsx)
- Horizontal scrolling card grid displaying slide thumbnails.
- Shows page count.

---

### Frontend: App Integration

Integrate the new workflow into the main React app.

#### [MODIFY] [frontend/src/api/client.js](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/frontend/src/api/client.js)
- Add `previewLyrics(payload)` API wrapper.
- Add `generateLyricsPptx(payload)` API wrapper.

#### [MODIFY] [frontend/src/App.jsx](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/frontend/src/App.jsx)
- Add top-level mode state: `'presentation' | 'hymn'`.
- Add a mode switcher tab bar below the `<Header />`.
- Conditionally render either the existing presentation flow or the new Hymn Lyrics flow based on mode state.

## Open Questions

- Just to confirm the font behavior, if a user selects bilingual with (zh, en), we should render both fonts appropriately (using `set_chinese_font` properly updated). 
- If you're ready to proceed with the execution order, you can approve the plan and I'll jump right in.

## Verification Plan

### Automated Tests
- Test the new API routes via curl/Postman to ensure the schemas validate properly and the `preview-lyrics` endpoint returns the expected JSON slide breakdown.

### Manual Verification
- Start the Flask backend and Vite dev server.
- Toggle between "Presentation PPT" and "Hymn Lyrics PPT" modes in the UI.
- Paste a sample hymn (single language) and verify the preview cards show accurate pagination.
- Switch to Bilingual mode, select primary/secondary languages, verify lines are paired properly.
- Generate and download the PPTX to ensure the rendering output matches the selected theme and layout rules without errors.
