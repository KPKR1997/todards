"""FastAPI entry point for the read-only Todards Observatory API."""

from __future__ import annotations

import os
from datetime import date
from typing import Annotated
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .schemas import DashboardResponse, DefinitionsResponse, HealthResponse, RunsResponse
from .services.analytics import build_dashboard
from .services.metric_definitions import definitions_as_list
from .services.telemetry import default_telemetry_path, filter_records, load_telemetry


app = FastAPI(
    title="Todards Model & Pipeline Observatory API",
    version="1.0.0",
    description="Read-only metrics API over Todards performance_history.csv.",
)

allowed_origins = [item.strip() for item in os.getenv("TODARDS_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if item.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _read() -> tuple[list, dict]:
    try:
        return load_telemetry()
    except (FileNotFoundError, ValueError, OSError) as exc:
        raise HTTPException(status_code=503, detail=f"Telemetry source is unavailable: {exc}") from exc


@app.get("/api/v1/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    records, meta = _read()
    return HealthResponse(status="ok", telemetry_path=meta["path"], row_count=len(records))


@app.get("/api/v1/dashboard", response_model=DashboardResponse, tags=["observability"])
def dashboard(
    date_from: Annotated[date | None, Query(description="Inclusive ISO date (YYYY-MM-DD).")] = None,
    date_to: Annotated[date | None, Query(description="Inclusive ISO date (YYYY-MM-DD).")] = None,
) -> DashboardResponse:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be later than date_to.")
    records, meta = _read()
    return DashboardResponse(**build_dashboard(filter_records(records, date_from, date_to), meta, date_from, date_to))


@app.get("/api/v1/runs", response_model=RunsResponse, tags=["observability"])
def runs(date_from: date | None = None, date_to: date | None = None) -> RunsResponse:
    """Return only the run ledger for lightweight integrations."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be later than date_to.")
    records, meta = _read()
    payload = build_dashboard(filter_records(records, date_from, date_to), meta, date_from, date_to)
    return RunsResponse(meta=payload["meta"], runs=payload["runs"])


@app.get("/api/v1/metric-definitions", response_model=DefinitionsResponse, tags=["documentation"])
def metric_definitions() -> DefinitionsResponse:
    return DefinitionsResponse(definitions=definitions_as_list())
