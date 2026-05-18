# Streaming Ingestion MVP

Production streaming can be implemented with Kafka or RabbitMQ when the deployment needs continuous event ingestion.

For this local MVP, OmniAssistant uses Redis-backed caches plus JSONL job queues under `data/jobs/` and `data/feedback/`:

- feedback events are appended immediately;
- admin actions enqueue recrawl, rebuild, reindex, and QA jobs;
- `scripts/run_jobs.py` drains the queue deterministically;
- job state is auditable in `data/jobs/jobs.jsonl` and exposed through `/api/admin/jobs`.

This is intentionally simpler than Kafka/RabbitMQ but preserves the required event-driven loop:

`feedback -> queue -> processing job -> reindex/eval -> dashboard update`.
