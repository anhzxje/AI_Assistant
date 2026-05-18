"""Run data quality checks for processed docs and chunks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_platform.config import get_settings
from data_platform.feature_store.feature_builder import latest_processed_documents_path
from qa_ba.data_quality.validate_chunks import validate_chunks
from qa_ba.data_quality.validate_file_ingestion import validate_file_ingestion
from qa_ba.data_quality.validate_processed_docs import validate_processed_documents


def main() -> None:
    settings = get_settings()
    docs_path = latest_processed_documents_path(settings.resolved_data_root)
    chunk_path = sorted((settings.resolved_data_root / "features" / "chunks").glob("*/document_chunks.jsonl"))[-1]
    report_path = PROJECT_ROOT / "qa_ba" / "reports" / "data_quality_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "processed_documents": validate_processed_documents(docs_path),
        "chunks": validate_chunks(chunk_path),
        "file_ingestion": validate_file_ingestion(settings.resolved_data_root),
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"data_quality_report={report_path}")
    print(f"documents={report['processed_documents']['total_documents']} doc_issues={report['processed_documents']['issue_count']}")
    print(f"chunks={report['chunks']['total_chunks']} chunk_issues={report['chunks']['issue_count']}")
    print(f"duplicate_doc_hashes={report['processed_documents']['duplicate_content_hash_count']}")
    print(f"file_ingestion_issues={report['file_ingestion']['issue_count']}")


if __name__ == "__main__":
    main()
