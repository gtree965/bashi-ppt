# Changelog

All notable user-visible changes to Bashi PPT are documented here.

## v0.1.0 — 2026-06-23

First public co-creation release.

### Lesson preparation

- Added creative and strictly grounded material workflows.
- Added source-fact extraction, user confirmation, per-slide fact mapping, and live structural grounding audit.
- Added one bounded page-count repair that merges or splits content without silently trimming facts.
- Added slide-count recommendations based on topic and source-material scope.
- Added editable preparation articles and Markdown, DOCX, and ODT export.
- Added per-slide speaker notes with duration and teaching-style controls.
- Added PowerPoint Notes-pane export.

### Presentation output

- Added editable PPTX generation with local rendering.
- Added diagrams, optional Pixabay image search, themes, and script-aware text fitting.
- Added Chinese, English, and Chinese-English mixed input handling.
- Added Simplified Chinese, English, and bilingual output.

### Additional workflow

- Added single-language and bilingual hymn-lyrics presentation generation.
- Added Chinese script conversion, pagination preview, title slides, and amen slides.

### Distribution

- Added Bashi Creation Suite branding and favicon assets.
- Added a prebuilt frontend and Windows portable launcher.
- Added English and Chinese user, privacy, security, and contribution documentation.

### Known boundaries

- Windows with PowerPoint or WPS Office is the primary tested target.
- macOS and Linux use manual Python installation in this release.
- Grounding audit validates declared fact references, not semantic truth.
- Cloud model privacy, availability, and fees depend on the selected provider.
