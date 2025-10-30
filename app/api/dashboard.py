"""Routes powering the analytics dashboard metrics."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query

from ..services.analysis_service import AnalysisService
from ..utils import serialize_document


router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def get_analysis_service() -> AnalysisService:
    return AnalysisService()


def _build_filters(
    plan: str | None,
    suite: str | None,
    environment: str | None,
    owner: str | None,
    build: str | None,
    status: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict[str, Any]:
    filters = {
        "plan": plan,
        "suite": suite,
        "environment": environment,
        "triggered_by": owner,
        "build": build,
        "status": status,
        "from": date_from,
        "to": date_to,
    }
    return {k: v for k, v in filters.items() if v is not None}


@router.get("/summary")
async def dashboard_summary(
    plan: str | None = None,
    suite: str | None = None,
    environment: str | None = None,
    owner: str | None = None,
    build: str | None = None,
    status: str | None = None,
    date_from: datetime | None = Query(default=None, description="Filter runs starting from this datetime"),
    date_to: datetime | None = Query(default=None, description="Filter runs up to this datetime"),
    service: AnalysisService = Depends(get_analysis_service),
) -> dict[str, Any]:
    filters = _build_filters(plan, suite, environment, owner, build, status, date_from, date_to)
    return await service.dashboard_summary(filters)


@router.get("/recent-runs")
async def dashboard_runs(
    limit: int = Query(default=20, ge=1, le=100),
    plan: str | None = None,
    suite: str | None = None,
    environment: str | None = None,
    owner: str | None = None,
    status: str | None = None,
    service: AnalysisService = Depends(get_analysis_service),
) -> list[dict[str, Any]]:
    filters = _build_filters(plan, suite, environment, owner, None, status, None, None)
    runs = await service.recent_runs(limit=limit, filters=filters)
    return [serialize_document(run) for run in runs]


@router.get("/common-errors")
async def dashboard_common_errors(
    limit: int = Query(default=15, ge=1, le=100),
    days: int | None = Query(default=30, ge=1),
    service: AnalysisService = Depends(get_analysis_service),
) -> list[dict[str, Any]]:
    errors = await service.common_errors(limit=limit, days=days)
    return [serialize_document(err) for err in errors]


@router.get("/error-trends")
async def dashboard_error_trends(
    limit: int = Query(default=30, ge=1, le=200),
    service: AnalysisService = Depends(get_analysis_service),
) -> list[dict[str, Any]]:
    return [serialize_document(doc) for doc in await service.error_trends(limit=limit)]

