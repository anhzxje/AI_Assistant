# Data Layer

## Scope

The Data Layer ingests institutional sources and read-only personal sources, stores raw artifacts, normalizes them into processed records, and builds AI-ready features.

## Implemented Sources

Institutional:

- `hus.vnu.edu.vn`
- `tuyensinh.hus.vnu.edu.vn`
- local curriculum PDFs from `Agent_Knowledge_Base/crawl`

Personal read-only:

- Gmail mock/OAuth-ready read-only connector
- Google Calendar mock/OAuth-ready read-only connector
- uploaded voice audio for ASR

## Storage Layers

Raw:

- `data/raw/web/YYYY-MM-DD/.../index.html`
- `data/raw/pdf/YYYY-MM-DD/*.pdf`
- `data/raw/gmail/YYYY-MM-DD/*.json`
- `data/raw/calendar/YYYY-MM-DD/*.json`
- `data/raw/voice/*`

Processed:

- `data/processed/documents/YYYY-MM-DD/processed_documents.jsonl`
- `data/processed/personal/gmail_messages.jsonl`
- `data/processed/personal/calendar_events.jsonl`

Features:

- `data/features/chunks/YYYY-MM-DD/document_chunks.jsonl`
- `data/features/metadata/YYYY-MM-DD/feature_summary.json`
- `data/features/personal/tasks_from_email.jsonl`
- `data/features/personal/daily_briefing.json`
- Qdrant local/vector collections

Metadata:

- `data/metadata/crawl_manifest.jsonl`

## Governance

- URL/domain allowlist.
- Hash-based duplicate tracking.
- Stable document and chunk IDs.
- QA validation for required fields, duplicate chunk IDs, offsets, scores, and document types.
- Personal data, generated audio, OAuth credentials, and model caches are excluded from git.

## Current Metrics

- Documents: 60
- Chunks: 938
- Duplicate chunk IDs: 0
- Chunk issue count: 0
- Top source domains: `hus.vnu.edu.vn`, `tuyensinh.hus.vnu.edu.vn`
