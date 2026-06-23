# Contributing to Bashi PPT

Thank you for helping improve a teacher-centered, editable lesson-preparation tool.

## Before opening a pull request

1. Keep the teacher workflow clearer, not merely more feature-rich.
2. Do not weaken editable PPTX or speaker-notes behavior.
3. Preserve the distinction between creative and strictly grounded material modes.
4. Do not add analytics or external data transfer without explicit documentation and opt-in design.
5. Add or update tests for behavior changes.

## Development checks

Backend:

```bash
python -m unittest discover -s tests
```

Frontend:

```bash
cd frontend
npm install
npm run lint
npm run test:grounding-audit
npm run build
```

## Reporting product feedback

Teacher feedback is especially valuable when it includes:

- subject and teaching context;
- operating system and office software;
- local or cloud model used;
- whether creative or grounded mode was chosen;
- where the workflow felt reassuring, confusing, or too heavy.

Do not attach confidential student records, unpublished teaching material, API keys, or other sensitive information to public issues.
