# Demo Script

## 1. Start Backend

```powershell
cd D:\OmniAssistant_Workspace\project-root
python scripts/run_backend.py
```

Check:

```text
http://localhost:8000/health
```

## 2. Start Frontend

```powershell
cd D:\OmniAssistant_Workspace\project-root\frontend
npm.cmd run dev
```

Open:

```text
http://localhost:3000
```

## 3. Institutional RAG

Page: `/`

Ask:

```text
khoa hoc du lieu hoc nhung mon gi
```

Show:

- intent `rag`
- sources/citations
- route metadata

## 4. Daily Briefing

Ask:

```text
hom nay toi can lam gi
```

Show:

- intent `daily_briefing`
- Gmail mock summary
- Calendar today events
- priorities

## 5. Add Memory

Ask:

```text
hay nho toi dang lam do an OmniAssistant
```

Then open `/memory` and show the remembered fact.

## 6. Task Question

Create a task on `/memory` or ask:

```text
toi co task nao chua xong
```

Show:

- intent `tasks`
- open task list

## 7. Voice Button

On `/`, click the voice button:

1. Allow microphone.
2. Speak a short request.
3. Stop recording.
4. Show transcript, answer, and audio playback.

If ASR model is unavailable, show the clear backend error and explain optional dependency/model cache.

## 8. Dashboard

Open `/dashboard`.

Show:

- total documents
- total chunks
- chunks by type chart
- retrieval hit rate
- groundedness score
- duplicate chunk status

## 9. Admin CMS

Open `/admin`.

Show:

- processed documents
- document type filter
- search
- source links
- content hashes

## 10. QA Reports

Show files:

```text
qa_ba/reports/data_quality_report.json
qa_ba/reports/retrieval_eval_report.json
qa_ba/reports/rag_eval_report.json
```

Run:

```powershell
python -m pytest qa_ba/api_tests -q
```
