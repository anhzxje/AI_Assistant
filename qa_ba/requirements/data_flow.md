# Data Flow

1. Ingestion lands immutable raw snapshots in `data/raw`.
2. Parsers and cleaners create normalized records in `data/processed`.
3. Feature builders create chunks, scores, metadata, context packs, and embeddings in `data/features`.
4. Qdrant serves vector retrieval for RAG.
5. Assistant responses generate feedback opportunities.
6. Feedback is reviewed by admins, promoted to eval, and can queue recrawl/reindex/QA jobs.
7. QA and drift reports update dashboard decision panels.
