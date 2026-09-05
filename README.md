# ResearchOS

ResearchOS is an autonomous ML experimentation engine. Point it at a tabular dataset and a research objective, and it runs the research loop end to end: **Understand → Baseline → Hypothesize → Experiment → Measure → Interpret → Iterate**.

The system establishes a reproducible baseline, proposes experiments, executes them, evaluates the results, and iterates toward a better model — with actual training, evaluation, and comparison performed deterministically and programmatically. An LLM is used only for reasoning and experiment selection, and can be swapped out for a built-in deterministic planner.

## What it does

1. Create a research project.
2. Upload a tabular CSV dataset and select a target column.
3. Define a research objective in plain language.
4. ResearchOS analyzes the dataset and trains a baseline model.
5. It proposes and runs follow-up experiments, tracking metrics for each.
6. Results, interpretations, and progress are surfaced through a web UI.

## Stack

- **Backend:** FastAPI, SQLAlchemy, pandas, scikit-learn, XGBoost, LightGBM
- **Frontend:** React, TypeScript, Vite, React Router, Recharts
- **Storage:** SQLite (default) for metadata, local filesystem for datasets/artifacts

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env
uvicorn researchos.main:app --reload
```

The API serves on `http://127.0.0.1:8000` (see `/health`).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app serves on `http://localhost:5173`.

### Configuration

Backend settings live in `backend/.env` (see `backend/.env.example`):

- `LLM_PROVIDER` — `mock` (default, no API key needed) or `anthropic` for LLM-assisted planning/critique/interpretation.
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` — required only when `LLM_PROVIDER=anthropic`.
- `DATABASE_URL` — defaults to a local SQLite file.
- `CORS_ORIGINS` — comma-separated list of allowed frontend origins.

Frontend settings live in `frontend/.env.local` (see `frontend/.env.example`):

- `VITE_API_URL` — base URL of the backend API.

## Deployment (Railway + Vercel)

**Backend (Railway):**

1. Create a new Railway service from this repo, with the service's root directory set to `backend/`.
2. Railway auto-detects Python via `requirements.txt` and uses `backend/Procfile` to run `uvicorn researchos.main:app --host 0.0.0.0 --port $PORT`.
3. Attach a persistent volume (e.g. mounted at `/data`) so SQLite and uploaded datasets/artifacts survive redeploys.
4. Set environment variables:
   - `DATABASE_URL=sqlite:////data/researchos.db` (or point at a Railway Postgres addon instead)
   - `DATASET_STORAGE_DIR=/data/storage/datasets`
   - `ARTIFACT_STORAGE_DIR=/data/storage/artifacts`
   - `CORS_ORIGINS=https://<your-vercel-domain>.vercel.app`
   - `LLM_PROVIDER`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` as needed
5. Note your Railway service's public URL (e.g. `https://researchos-backend.up.railway.app`).

**Frontend (Vercel):**

1. Import this repo into Vercel with the project root set to `frontend/`.
2. Build command `npm run build`, output directory `dist` (Vercel's Vite preset sets these automatically).
3. Set the environment variable `VITE_API_URL` to your Railway backend URL from above.
4. Deploy — Vercel gives you the public frontend domain to plug back into `CORS_ORIGINS` on Railway.

## Project layout

```
backend/
  researchos/
    api/          # FastAPI routers (projects, datasets, research, experiments, events)
    core/         # config, logging, database setup
    datasets/     # dataset ingestion & analysis
    experiments/  # experiment execution & tracking
    research/     # planning/critique/interpretation (LLM or mock provider)
    reports/      # result reporting
frontend/
  src/
    api/          # API client
    components/   # UI components
    pages/        # route-level views
```

## Status

Early-stage / Phase 1: the core research loop (baseline → propose → run → evaluate → iterate) with a working web UI. Not yet feature-complete.
