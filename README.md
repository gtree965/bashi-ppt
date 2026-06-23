<div align="center">
  <img src="frontend/dist/Bashi_PPT_logo.png" alt="Bashi PPT" width="560">

  # Bashi PPT

  **A teacher-centered lesson-prep, speaker-notes, and editable PowerPoint assistant**

  [简体中文](README_CN.md) · [User Guide](docs/USER_GUIDE.md) · [Privacy](docs/PRIVACY.md) · [Releases](https://github.com/gtree965/bashi-ppt/releases)
</div>

> Bashi PPT is not trying to win the “one-click AI slideshow” race. It helps teachers turn a topic or source material into a reviewable lesson structure, editable slides, and per-slide speaking notes while retaining human control.

## Why Bashi PPT?

Most AI presentation tools optimize for speed from prompt to finished deck. Bashi PPT optimizes for a different workflow:

1. understand and review the material;
2. confirm the content boundary;
3. edit the outline before rendering;
4. keep every slide editable;
5. place the teaching script in PowerPoint speaker notes.

The first audience is educators working primarily in Chinese, including Chinese-English mixed teaching materials.

## Core workflows

### Teaching creation

Use a topic, optional source material, or a generated prep article to create:

- a recommended slide count;
- an editable outline;
- a preparation article that can be exported as Markdown, DOCX, or ODT;
- per-slide speaker notes with selectable duration and teaching style;
- an editable `.pptx` file rather than a stack of slide images.

### Strictly grounded material

For policies, course notices, source articles, or other material whose boundaries matter:

- extract a fact table from the source;
- let the user review, edit, remove, and confirm those facts;
- associate confirmed facts with individual slides;
- audit missing, invalid, and unassigned fact references;
- refuse to silently trim slides or invent facts to satisfy a page count.

The audit verifies structural fact references. It does **not** claim that an AI has proven every sentence semantically true.

### Hymn projection

The included hymn tool works without an LLM and supports:

- single-language and bilingual lyrics;
- projection-oriented dark themes;
- preview and pagination controls;
- Simplified/Traditional Chinese conversion;
- optional title and amen slides.

## Highlights

- Local-first architecture with LM Studio and Ollama support
- Optional OpenAI-compatible cloud endpoints
- Creative and strictly grounded generation modes
- Human-confirmed fact table and live structural grounding audit
- Editable outline, speaker notes, diagrams, images, and PPTX elements
- Slide-count recommendation based on topic or source-material scope
- Simplified Chinese, English, and Chinese-English output
- Chinese, English, and mixed Chinese-English source input
- PowerPoint speaker-notes export
- Preparation-article export to Markdown, DOCX, and ODT
- Optional Pixabay image search
- Prebuilt React frontend served locally by Flask
- Independent hymn-lyrics presentation workflow

## Download

Download the latest Windows portable package from:

**https://github.com/gtree965/bashi-ppt/releases**

The Windows package includes Python and the required Python libraries. Node.js is not required.

## Windows portable quick start

1. Download `Bashi-PPT-v0.1.0-Windows-Portable.zip`.
2. Extract the entire archive to a normal writable folder.
3. Double-click `run_portable.bat`.
4. Open `http://localhost:5100`.
5. Open the gear icon and configure a local or cloud model.

Do not run the application directly inside the ZIP archive.

## AI model options

### Local

- **LM Studio**: default endpoint `http://localhost:1234/v1`
- **Ollama**: default endpoint `http://localhost:11434/v1`

Local models keep lesson content on the computer, but their speed and output quality depend heavily on available RAM, GPU memory, model size, and quantization.

### Cloud

OpenRouter is available in the settings interface. Other OpenAI-compatible services can be configured in `.env` using:

```env
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=your-api-key
LLM_MODEL=provider-model-id
```

When a cloud endpoint is used, prompts, source material, outlines, and speaker-note requests are sent to that provider. Review the provider’s terms, retention policy, geographic availability, and fees before using sensitive material.

See [Privacy and Data Flow](docs/PRIVACY.md).

## Manual installation

Manual installation is intended for macOS, Linux, development, or users who prefer system Python.

Requirements:

- Python 3.10 or newer
- Internet access for the initial dependency installation
- An OpenAI-compatible model endpoint for AI workflows

```bash
git clone https://github.com/gtree965/bashi-ppt.git
cd bashi-ppt
python -m venv venv
```

Windows:

```bat
venv\Scripts\activate
python -m pip install -r backend\requirements.txt
copy .env.example .env
python backend\app.py
```

macOS / Linux:

```bash
source venv/bin/activate
python -m pip install -r backend/requirements.txt
cp .env.example .env
python backend/app.py
```

The repository already contains the production frontend build. Node.js is only needed when changing frontend source code.

## Development

Backend:

```bash
python -m unittest discover -s tests
python backend/app.py
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run test:grounding-audit
npm run dev
```

Production build:

```bash
cd frontend
npm run build
```

## Current support scope

- Primary target: Windows with PowerPoint or WPS Office
- Code path: Windows, macOS, and Linux
- macOS/Linux packaging: manual Python installation in v0.1.0
- Official source/output languages: Chinese, English, and Chinese-English mixed content
- Other languages: experimental
- Keynote and LibreOffice may render some PPTX details differently

## Documentation

- [English User Guide](docs/USER_GUIDE.md)
- [中文使用指南](docs/USER_GUIDE_CN.md)
- [Privacy and Data Flow](docs/PRIVACY.md)
- [隐私与数据去向](docs/PRIVACY_CN.md)
- [Release Notes v0.1.0](docs/RELEASE_NOTES_v0.1.0.md)
- [Contributing](CONTRIBUTING.md)
- [Security Policy](SECURITY.md)

## License

Bashi PPT is released under the [MIT License](LICENSE).

## Author

Alex Li · ncorecpu@gmail.com
