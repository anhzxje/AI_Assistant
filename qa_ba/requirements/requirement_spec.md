# Requirement Specification

## Functional

- Users can chat with a general assistant.
- Institutional HUS questions use RAG with visible citations.
- Users can manage personal memory and tasks.
- Gmail and Calendar integrations are read-only or mock-safe.
- Admins can inspect data sources, QA reports, feedback, and jobs.
- Admins can promote feedback into eval cases and queue maintenance jobs.

## Non-Functional

- Local-first runtime with Ollama, Qdrant, Redis, and PostgreSQL.
- No paid API dependency.
- Role-aware metadata visibility.
- Deterministic fast paths must validate official sources.
- Data quality, model evaluation, and drift reports must be reproducible.
