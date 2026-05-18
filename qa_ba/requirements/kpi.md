# KPI

## Data KPIs

- Processed document validity rate >= 95%.
- Chunk validity rate >= 98%.
- Duplicate content hash rate tracked per ingestion run.
- Unknown/stale date count tracked for announcements and regulations.

## Retrieval KPIs

- Expected document type hit@5 >= 70% for seed eval set.
- Keyword hit rate >= 60% for seed eval set.
- Average retrieval latency < 10 seconds on laptop after model warm-up.

## RAG KPIs

- 100% answers include citation markers when context exists.
- 0 empty answers.
- Groundedness heuristic score >= 0.65 average.
- If retrieval context is weak, answer must explicitly say data is insufficient.
