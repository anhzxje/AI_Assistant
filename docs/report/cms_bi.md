# CMS and BI

## Frontend

The frontend is a Next.js/TypeScript/Tailwind application under `frontend/`.

Pages:

- `/`: orchestrated chat with voice button.
- `/briefing`: read-only Gmail/Calendar daily briefing.
- `/memory`: personal memory and task management.
- `/dashboard`: BI dashboard.
- `/admin`: read-only knowledge CMS.

## Admin CMS

The CMS page reads processed documents through:

- `GET /api/admin/documents`

Displayed fields:

- title
- document type
- source URL
- source path
- text length
- content hash
- language

## BI Dashboard

The dashboard reads:

- `GET /api/admin/feature-summary`
- `GET /api/admin/qa-reports`

Displayed metrics:

- total documents
- total chunks
- chunks by document type
- retrieval hit rate
- groundedness score
- duplicate chunk status
- QA report table

Filters:

- document type filter
- report/metric selection through dashboard panels

## Demo Value

The CMS/BI subsystem proves the system has operational visibility over the data and model layers, not just an end-user chat screen.
