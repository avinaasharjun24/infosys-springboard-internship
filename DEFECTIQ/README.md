# DEFECTIQ — AI-powered software defect intelligence

A local-first prototype for investigating software defects using the Eclipse JDT historical issue corpus, semantic retrieval, and a five-stage LangGraph workflow.

## Current implementation

- React + Vite customer-facing workspace UI.
- FastAPI backend with persistent SQLAlchemy records.
- PostgreSQL as the primary application database; SQLite is an explicitly selected lightweight development option.
- Qdrant local persistent vector store.
- Sentence Transformers `all-MiniLM-L6-v2` (384 dimensions).
- Chunked, resumable CSV ingestion with semantic text chunks for the Eclipse JDT export.
- Semantic retrieval with source metadata and issue links.
- Five real workflow stages: triage baseline, log inspection, historical retrieval, evidence-based root-cause hypothesis, and remediation guidance.
- TXT, LOG, CSV, PDF and DOCX text extraction.
- Investigation history and result reports.

## Important product integrity notes

1. The severity estimate in this initial build is a transparent keyword baseline, **not a trained classifier**. Do not present it as a validated ML prediction.
2. The root-cause agent produces hypotheses, not confirmed causes. Similarity scores are evidence, not proof.
3. Gemini enhances ambiguous triage and contextual log interpretation when configured; deterministic agent logic remains available without a key. Use `POST /api/gemini/verify` for one explicit credential/model capability check.
4. The dashboard severity chart is live application telemetry, not a source-dataset snapshot.
5. Do not bundle the 5.49 GB/5.94 GB source CSV in the repository. Keep it locally and ingest by path.
6. The user-provided JDT CSV schema uses `Op sys`, `History/Activity Log`, `Dupe of`, etc.; ingestion maps those exact column names.

## Requirements

- Windows 10/11
- Python 3.11 recommended
- Node.js LTS + npm
- 8 GB RAM minimum recommended; 16 GB+ preferred for embedding ingestion
- Several GB of free disk space for the embedding model and Qdrant index

Create the PostgreSQL database before startup and set `DATABASE_URL` in `backend/.env`. For a quick local smoke test without PostgreSQL, explicitly set `DATABASE_URL=sqlite:///./defectiq.db`. The checked-in configuration template does not contain credentials.

## Start the backend (Windows PowerShell)

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python run.py
```

Backend: http://localhost:8000 (or http://127.0.0.1:8000)  
Swagger API: http://localhost:8000/docs

The first knowledge-base operation downloads the embedding model from Hugging Face. Allow internet access for this first run.

## Start the frontend (second PowerShell terminal)

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173 (or http://127.0.0.1:5173)

## Ingest the Eclipse JDT dataset

1. Ensure the backend is running.
2. Open http://127.0.0.1:8000/docs.
3. Find `POST /api/knowledge/ingest`.
4. Run a bounded test first (100 records) from the Knowledge Base dashboard, then inspect its job counters and RAG retrieval.
5. Start full ingestion explicitly only after that succeeds. The configured absolute path is:
   `C:\Users\avina\Downloads\JDT\JDT_dataset_issues (1).csv`

The ingestion is chunked (default 500 rows per batch) and writes bounded semantic chunks from Summary, Description, Comments, and History/Activity Log into Qdrant. Every vector carries the original JDT ID and source field. UUIDv5 point IDs include defect ID and chunk index, so re-running updates rather than duplicates. Jobs persist an absolute CSV row resume offset; a bounded resumed run processes the requested number of additional rows. Deterministic point IDs make replay idempotent. Local Qdrant and upload paths are anchored to the backend directory, independent of the shell working directory.

CLI equivalents:

```powershell
cd backend
python -m app.ingest_cli --test-limit 100 --batch-size 500
python -m app.ingest_cli --test-limit 100 --batch-size 500 --offset 100
python -m app.ingest_cli --full --batch-size 500
```

## PostgreSQL configuration

Create a database named `defectiq`, then edit `backend/.env`:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/defectiq
```

Restart the backend. SQLAlchemy creates the tables automatically.

## API overview

- `GET /api/health`
- `POST /api/gemini/verify`
- `GET /api/overview`
- `POST /api/knowledge/ingest?path=...`
- `POST /api/knowledge/search`
- `POST /api/bugs`
- `POST /api/uploads`
- `POST /api/analyses/{id}/run`
- `GET /api/analyses`
- `GET /api/analyses/{id}`

## Security and deployment caveats

This is a local development prototype, not yet a hardened public multi-tenant deployment. Before exposing it to customers, add authentication/authorization, request rate limits, audit logging, malware scanning and upload size limits, background job processing, database migrations, backups, observability, secrets management, tenant isolation, and a production deployment architecture. Keep `.env`, database files, uploaded logs, and the raw dataset out of Git.
