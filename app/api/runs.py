"""Routes for ingesting and retrieving test runs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.schemas import TestRunDocument, TestRunIngestRequest
from ..services.run_service import RunService
from ..utils import serialize_document


router = APIRouter(prefix="/api/runs", tags=["runs"])


def get_run_service() -> RunService:
    return RunService()


@router.post("", response_model=TestRunDocument)
async def ingest_run(
    payload: TestRunIngestRequest,
    auto_analyze: bool = Query(default=True, description="Fetch logs from Bamboo and analyze automatically"),
    service: RunService = Depends(get_run_service),
) -> TestRunDocument:
    document = await service.ingest_run(payload, auto_analyze=auto_analyze)
    return document


@router.get("/{run_id}")
async def get_run(run_id: str, service: RunService = Depends(get_run_service)) -> dict:
    doc = await service.get_run(run_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Run not found")
    return serialize_document(doc)


@router.get("")
async def list_runs(
    limit: int = Query(default=50, ge=1, le=200),
    plan: str | None = None,
    suite: str | None = None,
    environment: str | None = None,
    status: str | None = None,
    service: RunService = Depends(get_run_service),
) -> list[dict]:
    filters = {
        "plan": plan,
        "suite": suite,
        "environment": environment,
        "status": status,
    }
    records = await service.list_runs(limit=limit, filters={k: v for k, v in filters.items() if v})
    return [serialize_document(record) for record in records]

