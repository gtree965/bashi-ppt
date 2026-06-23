# Security Policy

## Supported version

Security fixes currently target the latest release on the `main` branch.

## Reporting a vulnerability

Please do not open a public issue for vulnerabilities involving:

- API-key exposure;
- arbitrary file access;
- unsafe archive or path handling;
- remote code execution;
- accidental transmission of private lesson material.

Send a private report to **ncorecpu@gmail.com** with:

- affected version;
- operating system;
- reproduction steps;
- expected and actual behavior;
- whether any credentials or private content may have been exposed.

Remove real API keys and sensitive teaching content from logs and screenshots.

## Local secrets

Bashi PPT stores configured API keys in the local `.env` file as plain text. Keep the application folder private, do not commit `.env`, and revoke any key that is accidentally shared.
