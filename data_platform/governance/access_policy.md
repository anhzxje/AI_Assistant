# Data Access Policy

- Raw data is append-only. Jobs may add snapshots but should not edit or delete existing raw artifacts.
- Processed and feature layers can be regenerated from raw data and must keep lineage to the source snapshot.
- Admin APIs require the `admin` role for data inspection, quality reports, model registry, and maintenance jobs.
- User data, conversations, memory, task records, Gmail mock data, and calendar mock data are scoped by authenticated user id.
- External crawling and API ingestion are restricted to configured allowlisted domains.
- Secrets must stay in `.env` or local secret stores and must not be committed into data artifacts.
