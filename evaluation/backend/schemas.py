"""Pydantic response envelopes used by the public FastAPI endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ApiMeta(BaseModel):
    source: dict[str, Any]
    selected_row_count: int
    warnings: list[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    meta: ApiMeta
    period: dict[str, str | None]
    overview: dict[str, Any]
    duration_trend: list[dict[str, Any]]
    stages: dict[str, Any]
    content: dict[str, Any]
    llm: dict[str, Any]
    safety: dict[str, Any]
    runs: list[dict[str, Any]]


class DefinitionsResponse(BaseModel):
    definitions: list[dict[str, str]]


class RunsResponse(BaseModel):
    meta: ApiMeta
    runs: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    telemetry_path: str
    row_count: int
