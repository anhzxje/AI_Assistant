# Lumi Frontend

Next.js presentation layer for the VNU-HUS assistant.

## Pages

- `/` Orchestrated assistant chat for `POST /api/assistant/chat`, with push-to-talk voice via `/api/voice/chat`.
- `/briefing` Read-only Gmail/Calendar daily briefing with mock sync controls.
- `/memory` Personal memory and task management.
- `/dashboard` BI dashboard for feature summary and QA reports.
- `/admin` Read-only knowledge admin/CMS view over processed documents.

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Default backend:

```text
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

Run the backend from the project root first:

```bash
python scripts/run_backend.py
```

## Notes

This UI intentionally avoids auth, email sending, calendar event writes, full
duplex realtime voice, and write-action agents. It is the Presentation Layer
for the current Data Layer, RAG API, memory, read-only personal connectors,
push-to-talk voice, and QA/BI artifacts.

Personal memory is local demo data. Backend fallback files live under
`data/personal_memory/**`, which is gitignored and must not be committed.
