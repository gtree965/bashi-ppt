# Bashi PPT - Sprint 3 Walkthrough

**Objective:** Implement the pure-Python PPTX rendering engine, resolving the context window limitations by offloading the rendering from the LLM to code.

## Changes Made
1. **Visual Themes ([backend/renderer/theme.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/theme.py))**
   - Configured `clean_blue` (default) and `church_grace` palettes.
   - Set accurate Chinese/English font pairings (Microsoft YaHei).

2. **Slide Layouts ([backend/renderer/slide_layouts.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/slide_layouts.py))**
   - Hardcoded inch-based positional coordinates for title box, content box, and decorations for `TitleCenterLayout`, `ContentBulletLayout`, and `ConclusionLayout`.

3. **Core Rendering Engine ([backend/renderer/engine.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/engine.py))**
   - Initialized widescreen presentation (13.333" x 7.5").
   - Implemented [set_chinese_font](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/engine.py#21-37) to safely inject 'zh-CN' and East Asian (`<a:ea>`) tags using `lxml`, preventing Chinese characters rendering as boxes.
   - Implemented [_fit_text_in_box](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/engine.py#50-75) logic to detect structural text overflow and safely compress the text by scaling down font sizes before truncating strings as a last resort.

4. **API Integration ([backend/app.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/app.py))**
   - Replaced the mockup 501 `Not Implemented` error in the `POST /api/generate-pptx` endpoint.
   - Connected [PPTXRenderer](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/backend/renderer/engine.py#76-284). Handled the byte streams to return the native `.pptx` file over HTTP so that it isn't stored locally.

5. **Test Setup ([scripts/test_generate_pptx.py](file:///c:/Users/alex1/OneDrive/Documents/CS%20Teaching/edge-tts-app-v2.11-windows/Bashi PPT/scripts/test_generate_pptx.py))**
   - Created a CLI test script that bypasses the React frontend, submitting a direct dummy JSON payload to the Flask endpoint to verify the generated PPTX blob.

## Manual Verification Required
1. Launch the `Bashi PPT` app by running your `scripts/start.bat` file to establish the Flask backend.
2. In a separate terminal, run `python scripts/test_generate_pptx.py` to trigger an end-to-end slide generation test.
3. Open `test_output.pptx` in PowerPoint or WPS Office. Check that the Chinese fonts (`Microsoft YaHei`) appear properly and that longer strings did not overflow off the slide.
4. Open the web interface at `http://127.0.0.1:5000` and generate an actual response through the 3-step wizard UI.
