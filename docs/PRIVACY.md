# Bashi PPT: Privacy and Data Flow

[简体中文](PRIVACY_CN.md) · [Back to README](../README.md)

## Application behavior

Bashi PPT has no account system, advertising, content analytics, or built-in usage telemetry. The web interface is normally served from `127.0.0.1`.

## Local models

With LM Studio or Ollama, generation requests are sent to the configured local endpoint. Bashi PPT does not intentionally relay those prompts to another AI provider.

Local model software, proxies, remote image URLs, and update services may have their own network behavior.

## Cloud models

When a cloud OpenAI-compatible endpoint is selected, the provider may receive:

- topics and source material;
- fact-extraction and confirmed-fact requests;
- preparation articles, outlines, and revisions;
- per-slide speaker-note requests;
- text used to translate image-search queries.

Retention, logging, model training, jurisdiction, availability, and fees are controlled by that provider.

Do not submit personal student records, health data, private pastoral records, exam banks, trade secrets, or material restricted by policy or contract unless you have confirmed that such processing is permitted.

## Pixabay

When image search is enabled, search terms are sent to Pixabay and selected images are downloaded from remote URLs. Users are responsible for reviewing image suitability, licensing, and provider terms.

## Local storage

- API keys are stored as plain text in the local `.env` file.
- Logs may contain errors, model identifiers, timing, and technical metadata.
- Generated PPTX and article files are saved where the user chooses.

Remove credentials, private paths, and sensitive content before sharing logs.

## User responsibility

Selecting a cloud provider is a user decision to transmit content to that provider. Users must assess school policy, local law, cross-border processing, and the sensitivity of their material.

Use a local model and de-identified content when the processing basis is uncertain.
