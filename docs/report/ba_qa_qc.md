# BA and QA/QC

## Business Analysis

Stakeholders:

- Undergraduate students
- Graduate students
- Lecturers/researchers
- Department/admin staff

Core workflows:

- Ask academic program questions.
- Search lecturer/department information.
- Review announcements and regulations.
- Get daily briefing.
- Manage local memory and tasks.
- Inspect data and QA status through dashboard/CMS.

## QA/QC Coverage

Data QA:

- `qa_ba/data_quality/validate_processed_docs.py`
- `qa_ba/data_quality/validate_chunks.py`
- Output: `qa_ba/reports/data_quality_report.json`

Retrieval QA:

- `qa_ba/model_eval/evaluate_retrieval.py`
- Vietnamese eval set: `qa_ba/test_cases/rag_eval_questions.jsonl`
- Output: `qa_ba/reports/retrieval_eval_report.json`

RAG groundedness QA:

- `qa_ba/model_eval/evaluate_rag_groundedness.py`
- Output: `qa_ba/reports/rag_eval_report.json`

API QA:

- `qa_ba/api_tests/test_rag_api.py`
- `qa_ba/api_tests/test_memory_api.py`
- `qa_ba/api_tests/test_google_connectors_api.py`
- `qa_ba/api_tests/test_assistant_orchestration_api.py`
- `qa_ba/api_tests/test_voice_api.py`

## Current QA Results

- API tests: 24 passed
- Data quality processed document issue count: 0
- Chunk issue count: 0
- Duplicate chunk IDs: 0
- Retrieval document-type hit rate: 0.60
- Average keyword hit rate: 0.7556
- Average groundedness score: 0.90
- Citation marker pass rate: 1.00
