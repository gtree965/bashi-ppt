# Bashi PPT

[中文说明 / Chinese README](./README_CN.md)

**Version:** 0.1.0

**License:** [MIT License](./LICENSE)

**Changelog:** [CHANGELOG.md](./CHANGELOG.md)

Bashi PPT, formerly called SlideForge, is a local-first AI presentation builder for educators, churches, and family communication. It can generate editable presentation outlines from a topic or reference article, render `.pptx` files locally, and also create worship lyric slides in single-language or bilingual mode.

## Highlights

- Local AI outline generation through an OpenAI-compatible endpoint such as LM Studio
- Editable presentation workflow for teaching, church, parent, and general scenarios
- Automatic theme mapping for presentation mode
- Pure Python PPTX rendering with Chinese font handling and text fitting
- Hymn lyrics workflow with single-language and bilingual projection slides
- Optional Traditional/Simplified Chinese conversion for single-language Chinese lyrics
- Optional extended single-language pagination up to 6 lines per slide
- Optional title and amen slides for lyric decks
- Windows portable launcher with embedded Python
- Frontend and backend served together through Flask for a simple local setup

## Current Release Scope

This first release focuses on two core workflows:

1. `Presentation PPT`
   Generate an outline from a topic, review and edit it, then export a PowerPoint file.
2. `Hymn Lyrics PPT`
   Paste hymn lyrics, preview pagination, and export dark-background lyric slides without using an LLM.

## Requirements

- Python 3.10 or newer
- Node.js 18 or newer
- `npm`
- LM Studio or another OpenAI-compatible local/server endpoint for presentation outline generation

Notes:

- The hymn lyrics workflow does not require an LLM.
- The presentation workflow does require a working model endpoint.

## Quick Start

### Windows Portable Edition

```bat
run_portable.bat
```

Then open:

```text
http://localhost:5100
```

The portable launcher:

- uses the bundled embedded Python on Windows
- installs backend dependencies automatically
- ensures OpenCC is available for Traditional/Simplified Chinese conversion
- serves the prebuilt frontend from `frontend/dist`
- starts the app on port `5100`

Notes:

- `Presentation PPT` still requires LM Studio or another OpenAI-compatible endpoint.
- `Hymn Lyrics PPT` can run without any LLM.

## Manual Setup

Manual setup is recommended for development, for macOS / Linux, or if you do not want to use the Windows portable bundle.

### 1. Configure the backend

Copy `.env.example` to `.env` and adjust it if needed.

Default local settings use LM Studio:

```env
LLM_BASE_URL=http://localhost:1234/v1
LLM_API_KEY=lm-studio
LLM_MODEL=qwen3.5-4b
LLM_MAX_TOKENS=16384
LLM_TIMEOUT=360
FLASK_PORT=5100
```

### 2. Install backend dependencies

```bash
python -m venv venv
```

Windows:

```bat
venv\Scripts\activate
pip install -r backend/requirements.txt
```

macOS / Linux:

```bash
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Install frontend dependencies

```bash
cd frontend
npm install
npm run build
```

### 4. Start the app

```bash
cd backend
python app.py
```

Then open:

```text
http://localhost:5100
```

## Development

For frontend development with Vite:

```bash
cd frontend
npm install
npm run dev
```

For backend development:

```bash
cd backend
python app.py
```

The Vite config proxies `/api` requests to the Flask backend on port `5100`.

## Main Features

### Presentation workflow

- Topic input with scenario selection
- Optional reference article input
- AI-generated structured outline
- Outline editing before export
- PowerPoint export using local rendering

### Hymn workflow

- Paste raw hymn lyrics
- Single-language or bilingual mode
- Language dropdowns instead of fixed language presets
- Optional Traditional/Simplified Chinese conversion in single-language Chinese mode
- Optional extended single-language pagination up to 6 lines per slide
- Smart section parsing and slide splitting
- Projection-oriented dark themes
- Preview before export

## How to Use

### Presentation PPT

1. Open the `Presentation PPT` tab.
2. Enter a topic and choose a scenario.
3. Optionally paste a reference article.
4. Wait for the local model to generate an outline.
5. Review and edit the outline.
6. Export the deck as a PowerPoint file.

### Hymn Lyrics PPT

1. Open the `Hymn Lyrics PPT` tab.
2. Enter the song title and paste the lyrics.
3. Choose single-language or bilingual mode.
4. If needed, enable Chinese script conversion or extended single-language line count.
5. Adjust lines per slide and theme.
6. Optionally enable a title slide or amen slide.
7. Preview pagination.
8. Export the lyric deck as a PowerPoint file.

## Project Structure

```text
slideforge/
├─ backend/
│  ├─ app.py
│  ├─ llm/
│  ├─ lyrics/
│  ├─ renderer/
│  └─ templates/
├─ frontend/
│  ├─ src/
│  └─ dist/
├─ scripts/
├─ .env.example
├─ README.md
└─ README_CN.md
```

## Tech Stack

- Frontend: React, Vite, Tailwind CSS
- Backend: Flask, Pydantic
- PPTX generation: `python-pptx`, Pillow
- LLM integration: OpenAI-compatible API client

## Troubleshooting

### Presentation mode cannot generate outlines

Check these first:

- LM Studio is running
- A model is loaded
- The model id in `.env` matches the active model
- The local server is enabled on the expected port

### Frontend is not visible

Build the frontend first:

```bash
cd frontend
npm install
npm run build
```

### PowerPoint text overflows

The renderer already applies text fitting, but extremely long titles or dense content may still need manual editing before export.

## FAQ

### Does the hymn workflow need LM Studio?

No. Hymn lyric generation is a local parsing and rendering workflow and can run without any LLM.

### Does Chinese script conversion need internet access?

No. Traditional/Simplified Chinese conversion is handled locally through OpenCC after the dependency is installed.

### Why is outline generation slow?

Presentation mode depends on a local model. On smaller or reasoning-heavy models, generation can take several minutes.

### Can I use my own OpenAI-compatible endpoint?

Yes. Update `.env` with your own `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.

## Credits

- Flask for the backend web framework
- React and Vite for the frontend
- `python-pptx` and Pillow for PowerPoint generation
- LM Studio for local OpenAI-compatible model serving
- The open-source community

## Author

**Alex Li**  
Email: ncorecpu@gmail.com

## License

This project is released under the **[MIT License](./LICENSE)**.
