"""CLI helper to ingest Bamboo run results into MongoDB."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime

from app.models.schemas import TestRunIngestRequest
from app.services.run_service import RunService


async def ingest_run(service: RunService, result_key: str) -> None:
    payload = TestRunIngestRequest(
        run_id=result_key,
        plan=result_key.split("-", 1)[0],
        suite=None,
        build=result_key,
        environment=None,
        status="UNKNOWN",
        start_time=datetime.utcnow(),
        end_time=None,
        total_tests=0,
        passed_tests=0,
        failed_tests=0,
        bamboo_result_key=result_key,
    )
    document = await service.ingest_run(payload, auto_analyze=True)
    print(f"Ingested {document.run_id} with {document.failed_tests} failures")


async def main(result_keys: list[str]) -> None:
    service = RunService()
    for key in result_keys:
        await ingest_run(service, key)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest Bamboo results into MongoDB")
    parser.add_argument("result_keys", nargs="+", help="Bamboo result keys, e.g. PLAN-KEY-123")
    args = parser.parse_args()

    asyncio.run(main(args.result_keys))

