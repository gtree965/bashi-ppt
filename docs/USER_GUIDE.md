# Bashi PPT v0.1.0 User Guide

[简体中文](USER_GUIDE_CN.md) · [Back to README](../README.md)

## 1. Configure an AI endpoint

Open the gear icon in the upper-right corner.

- LM Studio and Ollama keep generation requests on the local machine.
- OpenRouter can be configured in the interface.
- Other OpenAI-compatible services can be configured in `.env`.

Use “Test connection” before starting a lesson-prep workflow.

## 2. Provide a topic or source material

You may provide a topic, source material, or both. When both are supplied, the source material defines the main content boundary and the topic describes the intended task.

Bashi PPT recommends a slide count from the topic scope or source length. You can always override the recommendation.

## 3. Choose a generation mode

### Teaching creation

The model may add general teaching background, examples, questions, and transitions.

### Strictly grounded material

1. Bashi PPT extracts source facts.
2. You edit, remove, and confirm them.
3. The outline declares fact references per slide.
4. You review and adjust those references.
5. Grounded speaker notes are enabled only after the structural mapping is complete.

Fact-reference auditing is structural and does not replace human semantic review.

## 4. Choose a preparation path

Full path:

`topic/material → preparation article → outline → notes → PPTX`

Fast path:

`topic/material → outline → notes → PPTX`

Preparation articles can be edited and exported as Markdown, DOCX, or ODT.

## 5. Review and export

You can edit slide titles, points, order, diagrams, images, themes, and fact references. Speaker notes are generated per slide and exported into the PowerPoint Notes pane.

Always open the final PPTX on the classroom computer before teaching. Font substitution and office-software differences can affect wrapping, diagrams, and notes.

## 6. Hymn lyrics

The hymn workflow does not use an LLM. It supports single-language and bilingual projection, pagination preview, Chinese script conversion, themes, title slides, and amen slides.

## Troubleshooting

- Connection failures: verify endpoint, model ID, API key, firewall, proxy, provider balance, and rate limits.
- Slow local generation: use a smaller model or a faster cloud endpoint.
- Image search: add a Pixabay API key in settings.
- Layout changes: test the exported deck in the actual office application and font environment.
