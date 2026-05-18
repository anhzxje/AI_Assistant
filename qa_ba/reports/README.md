# QA/BA Reports

This folder stores generated QA/QC reports for the Data Mining rubric.

## Reports

- `data_quality_report.json`: validates processed documents and feature chunks.
- `retrieval_eval_report.json`: evaluates top-k retrieval against Vietnamese seed cases.
- `rag_eval_report.json`: evaluates groundedness heuristics for RAG answers.

## Rubric Coverage

- BA requirements: personas, use cases, and KPIs under `qa_ba/requirements`.
- Data QA: schema, duplicate, source, language, date, and score validation.
- Model/Retrieval QA: document-type hit rate, keyword hit rate, retrieval score, latency.
- RAG QA: citation marker checks, non-empty answers, and lexical groundedness against retrieved context.
- API QA: FastAPI endpoint tests under `qa_ba/api_tests`.
