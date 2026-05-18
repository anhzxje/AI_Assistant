# OmniAssistant Final Report

## Project Summary

OmniAssistant is a local-first AI assistant platform specialized for VNU University of Science. It is not a chatbot demo: it includes a data lake, ingestion pipelines, feature engineering, vector search, RAG API, personal memory, read-only personal connectors, assistant orchestration, push-to-talk voice, QA evaluation, CMS/admin views, and BI dashboard.

Current dataset snapshot:

- Processed institutional documents: 60
- Retrieval chunks: 938
- Data quality chunk issues: 0
- Duplicate chunk IDs: 0
- Retrieval document-type hit rate: 0.60
- Retrieval keyword hit rate: 0.7556
- RAG groundedness score: 0.90
- RAG citation marker pass rate: 1.00

## 1. Data Layer

Implemented data lake layout:

```text
data/
  raw/
    web/
    pdf/
    gmail/
    calendar/
    voice/
  processed/
    documents/
    personal/
  features/
    chunks/
    metadata/
    personal/
    qdrant_local/
    qdrant_memory_local/
  metadata/
  generated/
```

Implemented pipelines:

- Seed crawler: `scripts/run_seed_crawl.py`
- Raw parser: `scripts/run_parse_raw.py`
- Feature builder: `scripts/run_build_features.py`
- Qdrant indexer: `scripts/run_index_qdrant.py`
- Gmail/Calendar read-only ingestion: `backend/app/services/connectors/personal_ingestion.py`

Governance:

- Raw artifacts are immutable-style dated files.
- Crawl manifest records URL, parent URL, status, content type, saved path, title, hash, and time.
- Content hashes and stable IDs are generated for processed documents and chunks.
- Personal data and generated audio are gitignored.
- Google credentials are gitignored and must never be committed.

## 2. AI Module

Implemented capabilities:

- Institutional RAG using Qdrant and sentence-transformer embeddings.
- Extractive fallback answer generation when Ollama is unavailable.
- Assistant orchestration router for RAG, memory, tasks, Gmail, Calendar, daily briefing, and fallback.
- Personal memory: session, long-term, semantic, and task memory.
- Voice layer:
  - ASR: faster-whisper, lazy-loaded.
  - TTS: edge-tts if installed, fallback WAV/text artifact otherwise.

Main backend APIs:

- `POST /api/rag/query`
- `POST /api/assistant/chat`
- `POST /api/memory/remember`
- `POST /api/tasks`
- `POST /api/google/gmail/sync`
- `POST /api/google/calendar/sync`
- `POST /api/voice/chat`

## 3. BA & QA/QC

BA artifacts:

- Personas: `qa_ba/requirements/personas.md`
- Use cases: `qa_ba/requirements/use_cases.md`
- KPIs: `qa_ba/requirements/kpi.md`

QA implemented:

- Data QA for processed documents and chunks.
- Retrieval QA over Vietnamese eval questions.
- RAG groundedness heuristic.
- API tests for RAG, memory, Google connectors, orchestration, and voice.

Reports:

- `qa_ba/reports/data_quality_report.json`
- `qa_ba/reports/retrieval_eval_report.json`
- `qa_ba/reports/rag_eval_report.json`

## 4. CMS & BI

Frontend app:

- `/`: orchestrated assistant chat with push-to-talk voice.
- `/briefing`: read-only Gmail/Calendar daily briefing.
- `/memory`: memory and task manager.
- `/dashboard`: BI dashboard with metrics, filters, charts, and QA status.
- `/admin`: read-only knowledge CMS over processed documents.

Backend admin endpoints:

- `GET /api/admin/documents`
- `GET /api/admin/feature-summary`
- `GET /api/admin/qa-reports`

## Known Limitations

- No email sending.
- No calendar create/update/delete.
- No full duplex realtime voice.
- No production authentication yet.
- RAG quality is limited by the current cold-start dataset size.
- Real Google OAuth is documented but mock mode is used by default.
- Semantic memory and RAG require embedding cache/model availability for full live retrieval.
