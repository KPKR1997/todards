# Todards Evaluation + Observatory

The original files in this directory—`metrics.py`, `reporter.py`, and every file under `reports/`—are part of the main Todards pipeline. They have not been changed by the observatory.

The new read-only observability application is isolated in:

- `backend/` — FastAPI CSV reader, normalized metric service, schemas, and tests.
- `frontend/` — Next.js TypeScript dashboard.
- `docs/observatory-architecture.md` — architecture, verified telemetry semantics, and metric rules.

## Run locally

In one terminal, create an isolated environment and start the API:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app:app --reload --port 8000
```

In another terminal, start the UI:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`. The API documentation is at `http://127.0.0.1:8000/docs`.

The dashboard reads `reports/performance_history.csv` only. It does not create, rewrite, or transform pipeline reports.

## Verify the isolated backend logic

```powershell
python -m unittest discover -s backend\tests -v
```
