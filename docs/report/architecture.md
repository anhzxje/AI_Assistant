# Architecture

## Overall System Architecture

```mermaid
flowchart LR
  User[Student / Lecturer / Admin] --> Web[Next.js Frontend]
  Web --> API[FastAPI Backend]
  API --> Orchestrator[Assistant Graph Router]
  Orchestrator --> RAG[RAG Service]
  Orchestrator --> Memory[Personal Memory]
  Orchestrator --> Google[Read-only Google Connectors]
  Orchestrator --> Voice[Voice Layer]
  RAG --> Qdrant[(Qdrant / Local Qdrant)]
  RAG --> Chunks[Feature Chunks]
  Memory --> Postgres[(PostgreSQL / JSONL fallback)]
  Memory --> Redis[(Redis / in-process fallback)]
  Memory --> MQdrant[(Semantic Memory Qdrant)]
  Google --> PersonalData[Raw/Processed Personal Data]
  API --> Admin[Admin/BI APIs]
  Admin --> Reports[QA Reports and Feature Summary]
```

## Data Pipeline

```mermaid
flowchart TD
  Seeds[seed_sources.txt + local PDFs] --> Crawl[Seed crawler]
  Crawl --> RawWeb[data/raw/web]
  Crawl --> RawPDF[data/raw/pdf]
  RawWeb --> Parse[HTML/PDF parsers]
  RawPDF --> Parse
  Parse --> Processed[data/processed/documents]
  Processed --> Clean[Clean + classify + extract dates]
  Clean --> Chunk[Chunking]
  Chunk --> Features[data/features/chunks]
  Features --> Embed[Embedding builder]
  Embed --> Qdrant[(Qdrant collection omni_hus_chunks)]
  Crawl --> Manifest[data/metadata/crawl_manifest.jsonl]
```

## RAG Pipeline

```mermaid
flowchart LR
  Query[User query] --> EmbedQ[Embed query]
  EmbedQ --> Search[Qdrant search]
  Search --> Rerank[Score = vector*.75 + authority*.15 + freshness*.10]
  Rerank --> Context[Top-k cited chunks]
  Context --> Answer[Ollama if available, extractive fallback otherwise]
  Answer --> Citations[Citations and previews]
```

## Assistant Orchestration Flow

```mermaid
flowchart TD
  Message[Message] --> Intent[Rule-based intent classifier]
  Intent -->|academic| RagNode[RAG node]
  Intent -->|remember| MemoryNode[Memory node]
  Intent -->|tasks| TaskNode[Task node]
  Intent -->|email| GmailNode[Gmail node]
  Intent -->|calendar| CalendarNode[Calendar node]
  Intent -->|today plan| BriefingNode[Briefing node]
  Intent -->|unknown| FallbackNode[Fallback node]
  RagNode --> Response[Assistant response]
  MemoryNode --> Response
  TaskNode --> Response
  GmailNode --> Response
  CalendarNode --> Response
  BriefingNode --> Response
  FallbackNode --> Response
```

## Voice Pipeline

```mermaid
flowchart LR
  Mic[Browser MediaRecorder] --> Upload[/api/voice/chat]
  Upload --> ASR[faster-whisper ASR]
  ASR --> Graph[Assistant graph]
  Graph --> TTS[edge-tts or fallback WAV]
  TTS --> Audio[data/generated/audio]
  Audio --> Player[Browser audio player]
```

## Memory Architecture

```mermaid
flowchart TD
  Chat[Chat/session events] --> Session[Short-term session memory]
  Explicit[Explicit remember command] --> LongTerm[Long-term memory]
  Summary[Conversation summaries] --> Semantic[Semantic memory]
  Todo[Task phrases/API] --> Tasks[Task memory]
  Session --> Redis[(Redis / fallback)]
  LongTerm --> Postgres[(Postgres / JSONL fallback)]
  Semantic --> Qdrant[(Qdrant memory collection)]
  Tasks --> Postgres
  LongTerm --> Context[Memory context]
  Session --> Context
  Semantic --> Context
  Tasks --> Context
  Context --> Assistant[Assistant prompt/context]
```
