# Use Cases

## UC-01 Ask Institutional Knowledge

User asks a Vietnamese question about HUS programs, admissions, staff, regulations, or announcements. The system retrieves official chunks and returns a grounded answer with citations.

## UC-02 Verify Source

User inspects citations and opens the original HUS URL or local document path.

## UC-03 Data QA Review

Admin runs data quality checks on processed documents and chunks to find missing fields, invalid document types, duplicates, stale/unknown dates, and broken citation metadata.

## UC-04 Retrieval QA

QA lead runs Vietnamese eval queries and measures whether relevant document types and keywords appear in top-k results.

## UC-05 Groundedness QA

QA lead evaluates generated or extractive answers for citation markers, non-empty content, and lexical support from retrieved context.
