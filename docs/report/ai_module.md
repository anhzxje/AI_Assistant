# AI Module

## Components

RAG:

- `data_platform/feature_store/embeddings/embedding_model.py`
- `data_platform/feature_store/embeddings/qdrant_indexer.py`
- `data_platform/feature_store/embeddings/retriever.py`
- `backend/app/services/answer_service.py`

Assistant orchestration:

- `orchestration/assistant_graph.py`
- `orchestration/intent_classifier.py`
- `orchestration/nodes/*`

Personal memory:

- `backend/app/services/memory/session_memory.py`
- `backend/app/services/memory/long_term_memory.py`
- `backend/app/services/memory/semantic_memory.py`
- `backend/app/services/memory/task_memory.py`

Voice:

- `ai_module/asr/faster_whisper_service.py`
- `ai_module/tts/tts_service.py`
- `backend/app/api/voice.py`

## Local-first Strategy

- No OpenAI key is required.
- Ollama is optional.
- If Ollama is unavailable, RAG uses extractive fallback.
- Qdrant server is preferred, local Qdrant path is supported.
- TTS falls back to local generated WAV/text when edge-tts is unavailable.

## Routing Intents

- `rag`: academic and institutional knowledge.
- `daily_briefing`: today plan across calendar, email, and tasks.
- `calendar`: read-only calendar today.
- `gmail`: read-only email summary.
- `tasks`: open task memory.
- `memory`: explicit remember/query memory.
- `fallback`: unsupported/unknown requests.

## Safety Boundaries

- No send email.
- No calendar write actions.
- No hidden long-term memory writes except explicit memory phrases.
- Voice is push-to-talk only, not always-on.
