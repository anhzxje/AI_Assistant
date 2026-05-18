# OmniAssistant Data Platform

This package owns institutional and personal data ingestion for the OmniAssistant
project. It is intentionally separate from the chat UI and model serving code.

## Current Scope

Step 1 scaffolds the package and runtime configuration for:

- immutable raw storage under `data/raw`
- normalized artifacts under `data/processed`
- AI-ready features under `data/features`
- lineage and manifests under `data/metadata`
- seed crawling from `Agent_Knowledge_Base/crawl/seed_sources.txt`

## Package Boundaries

- `ingestion/connectors`: source-specific API/file connectors
- `ingestion/crawlers`: allowlisted web crawlers
- `ingestion/parsers`: raw HTML/PDF/DOC parsers
- `processing/cleaners`: boilerplate removal and text normalization
- `processing/chunkers`: retrieval chunk generation
- `processing/extractors`: dates, document type, and entity extraction
- `governance`: manifests, validation, audit, and lineage
- `feature_store`: embeddings, vector DB, graph, and metadata adapters

## Configuration

Copy `.env.example` to `.env` for local overrides. All project-specific settings
use the `OMNI_` prefix.

## Seed Crawl

The seed crawler reads authoritative HUS URLs from:

```text
../Agent_Knowledge_Base/crawl/seed_sources.txt
```

It enforces the configured domain allowlist, removes URL fragments, avoids duplicate
URLs, checks `robots.txt`, downloads PDFs, stores raw HTML/PDF artifacts, and appends
lineage records to:

```text
data/metadata/crawl_manifest.jsonl
```

Smoke-test command:

```bash
python scripts/run_seed_crawl.py --depth 1 --max-pages 20
```

Raw output paths:

```text
data/raw/web/YYYY-MM-DD/<domain>/<safe_path>/index.html
data/raw/pdf/YYYY-MM-DD/<safe_filename>.pdf
```

## Raw Parsing

Raw HTML/PDF artifacts listed in the crawl manifest can be converted into
normalized processed document records:

```bash
python scripts/run_parse_raw.py --limit 50
```

Output:

```text
data/processed/documents/YYYY-MM-DD/processed_documents.jsonl
```

The parser extracts titles, readable text, headings, tables, links, language,
document type, publication date when detectable, content hashes, and citation
metadata. PDF parsing uses PyMuPDF when installed; HTML parsing works with
BeautifulSoup and falls back to the standard `html.parser` when `lxml` is not
available.

## Chunk Features

Processed documents can be converted into citation-preserving retrieval chunks
without building embeddings yet:

```bash
python scripts/run_build_features.py --latest --chunk-size 800 --chunk-overlap 120
```

Outputs:

```text
data/features/chunks/YYYY-MM-DD/document_chunks.jsonl
data/features/metadata/YYYY-MM-DD/feature_summary.json
```

Each chunk includes source provenance, stable IDs, character offsets, keyword
hints, freshness score, authority score, and rule-based entity mentions.

## Qdrant Indexing

Chunk records can be embedded locally and indexed into Qdrant:

```bash
docker compose up -d qdrant
python scripts/run_index_qdrant.py --latest --collection omni_hus_chunks --batch-size 32
```

Retrieval smoke test:

```bash
python scripts/run_retrieve_test.py "khoa học dữ liệu học những môn gì" --top-k 5
```

The default embedding model is `intfloat/multilingual-e5-small`, with
`sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` as fallback. The
model can be changed with `OMNI_EMBEDDING_MODEL_NAME` in `.env`.

## RAG API Backend

The current retriever can be exposed through FastAPI:

```bash
python scripts/run_backend.py
```

Equivalent uvicorn command:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

Endpoints:

```text
GET  /health
POST /api/rag/query
GET  /api/admin/documents
GET  /api/admin/feature-summary
GET  /api/admin/qa-reports
POST /api/memory/remember
POST /api/memory/query
GET  /api/memory/summary
DELETE /api/memory/{memory_id}
GET  /api/tasks
POST /api/tasks
PATCH /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
GET  /api/google/status
POST /api/google/gmail/sync
GET  /api/google/gmail/summary
POST /api/google/calendar/sync
GET  /api/google/calendar/today
GET  /api/assistant/daily-briefing
POST /api/assistant/chat
POST /api/voice/transcribe
POST /api/voice/speak
POST /api/voice/chat
GET  /api/voice/audio/{date_dir}/{filename}
```

The answer endpoint tries Ollama first using `OLLAMA_BASE_URL` and
`OLLAMA_MODEL`. If Ollama is unavailable, it returns a grounded extractive
fallback using only retrieved chunks.

## Personal Memory

Step 9 adds a personal memory subsystem to the backend without Gmail, Calendar,
voice, or LangGraph:

- short-term session memory: Redis list with in-process fallback
- long-term user memory: PostgreSQL table with JSONL fallback
- task memory: PostgreSQL table with JSONL fallback
- semantic memory: Qdrant collection `omni_user_memory`

Privacy rule:

```text
data/personal_memory/** is gitignored and must never be committed.
```

Start local storage services when Docker is available:

```bash
docker compose up -d db redis qdrant
```

Explicit memory example:

```bash
curl -X POST http://localhost:8000/api/memory/remember ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"demo\",\"session_id\":\"s1\",\"text\":\"Hãy nhớ tôi thích câu trả lời ngắn gọn\"}"
```

Task example:

```bash
curl -X POST http://localhost:8000/api/tasks ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"demo\",\"title\":\"Nộp báo cáo Data Mining\",\"priority\":\"high\"}"
```

Demo script:

```bash
python scripts/run_backend.py
```

Then, in another terminal:

```bash
curl http://localhost:8000/api/memory/summary?user_id=default
curl -X POST http://localhost:8000/api/memory/remember -H "Content-Type: application/json" -d "{\"text\":\"Remember that I prefer concise answers\",\"user_id\":\"default\"}"
curl -X POST http://localhost:8000/api/tasks -H "Content-Type: application/json" -d "{\"title\":\"Review Data Mining demo\",\"user_id\":\"default\",\"priority\":\"high\"}"
curl http://localhost:8000/api/memory/summary?user_id=default
```

RAG queries now accept optional memory fields:

```json
{
  "query": "chương trình khoa học dữ liệu học gì",
  "top_k": 5,
  "use_llm": false,
  "user_id": "demo",
  "session_id": "s1",
  "include_memory": true
}
```

## Google Personal Connectors

Step 10 adds read-only Gmail and Google Calendar connectors. The demo path uses
mock fixtures by default when OAuth credentials are unavailable.

Security rules:

- Gmail uses only `https://www.googleapis.com/auth/gmail.readonly`.
- Calendar uses only `https://www.googleapis.com/auth/calendar.readonly`.
- No endpoint sends email.
- No endpoint creates, updates, or deletes calendar events.
- OAuth credential files such as `client_secret*.json`, `credentials*.json`,
  and `token*.json` are gitignored and must never be committed.

Optional OAuth setup:

```text
GOOGLE_CLIENT_SECRET_PATH=C:\path\outside\repo\client_secret.json
```

Install optional Google libraries only when testing real OAuth:

```bash
python -m pip install ".[google]"
```

Mock fixture paths:

```text
backend/app/services/connectors/fixtures/gmail_mock.json
backend/app/services/connectors/fixtures/calendar_mock.json
```

Data layer outputs:

```text
data/raw/gmail/YYYY-MM-DD/*.json
data/raw/calendar/YYYY-MM-DD/*.json
data/processed/personal/gmail_messages.jsonl
data/processed/personal/calendar_events.jsonl
data/features/personal/tasks_from_email.jsonl
data/features/personal/daily_briefing.json
```

Demo script:

```bash
python scripts/run_backend.py
curl http://localhost:8000/api/google/status
curl -X POST http://localhost:8000/api/google/gmail/sync -H "Content-Type: application/json" -d "{\"user_id\":\"default\",\"max_results\":20,\"use_mock\":true}"
curl -X POST http://localhost:8000/api/google/calendar/sync -H "Content-Type: application/json" -d "{\"user_id\":\"default\",\"days_ahead\":7,\"use_mock\":true}"
curl http://localhost:8000/api/assistant/daily-briefing?user_id=default
```

## Assistant Orchestration

Step 11 adds a LangGraph-style orchestration layer under `orchestration/`.
The current implementation is a deterministic local graph runner with the same
state-in/state-out shape expected by LangGraph nodes. It routes requests to:

- institutional RAG
- personal memory
- open tasks
- Gmail summary
- Calendar today
- daily briefing
- fallback suggestions

Chat endpoint:

```bash
curl -X POST http://localhost:8000/api/assistant/chat -H "Content-Type: application/json" -d "{\"user_id\":\"default\",\"session_id\":\"browser-session-id\",\"message\":\"hom nay toi can lam gi\",\"include_memory\":true,\"use_mock_google\":true}"
```

Routing examples:

```text
khoa hoc du lieu hoc nhung mon gi -> rag
hom nay toi can lam gi -> daily_briefing
lich hom nay cua toi -> calendar
tom tat email -> gmail
toi co task nao chua xong -> tasks
hay nho toi dang lam do an OmniAssistant -> memory
```

## Voice Layer

Step 12 adds push-to-talk voice interaction. This is not full duplex realtime
voice; it is request/response audio:

```text
browser microphone -> /api/voice/chat -> ASR -> assistant graph -> TTS -> audio URL
```

ASR:

- Preferred engine: `faster-whisper`
- Config:
  - `WHISPER_MODEL_SIZE=small`
  - `WHISPER_DEVICE=auto`
  - `WHISPER_COMPUTE_TYPE=int8`
- If faster-whisper or the model runtime is unavailable, the API returns a
  clear `503` error instead of crashing.

TTS:

- Preferred engine: `edge-tts` with Vietnamese voice `vi-VN-HoaiMyNeural`.
- If `edge-tts` is not installed, the backend writes a local text artifact and
  a short placeholder WAV so the UI and API remain demo-safe.

Generated audio:

```text
data/generated/audio/YYYY-MM-DD/
```

Install optional voice dependencies:

```bash
python -m pip install ".[voice]"
```

Voice endpoints:

```bash
curl -X POST http://localhost:8000/api/voice/speak -H "Content-Type: application/json" -d "{\"text\":\"Xin chao\",\"language\":\"vi\"}"
```

## Presentation Layer

The Next.js frontend lives under `frontend/` and provides the rubric-facing UI:

```bash
cd frontend
npm install
npm run dev
```

Default URLs:

```text
Backend:  http://localhost:8000
Frontend: http://localhost:3000
```

Pages:

- `/` orchestrated chat UI for `POST /api/assistant/chat`
- push-to-talk microphone support on `/`
- `/briefing` read-only Gmail/Calendar daily briefing
- `/memory` personal memory and task management
- `/dashboard` BI dashboard backed by feature summaries and QA reports
- `/admin` read-only knowledge CMS over processed documents
