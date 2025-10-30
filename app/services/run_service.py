"""Service responsible for ingesting runs and storing them in MongoDB."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase
from dateutil import parser

from ..bamboo_client import fetch_bamboo_run
from ..config import get_settings
from ..database import Database
from ..log_parser import extract_error_occurrences
from ..models.schemas import (
    ErrorOccurrence,
    ErrorSignature,
    FailureContext,
    TestRunDocument,
    TestRunIngestRequest,
)


class RunService:
    def __init__(self, db: AsyncIOMotorDatabase | None = None) -> None:
        self._db = db or Database.get_database()
        self._runs: AsyncIOMotorCollection = self._db["test_runs"]
        self._error_signatures: AsyncIOMotorCollection = self._db["error_signatures"]

    async def ensure_indexes(self) -> None:
        await self._runs.create_index("run_id", unique=True)
        await self._runs.create_index([("plan", 1), ("suite", 1), ("start_time", -1)])
        await self._runs.create_index([("environment", 1), ("start_time", -1)])
        await self._error_signatures.create_index("signature_hash", unique=True)
        await self._error_signatures.create_index("last_seen")

    async def ingest_run(self, payload: TestRunIngestRequest, *, auto_analyze: bool = True) -> TestRunDocument:
        error_occurrences: list[ErrorOccurrence] = []
        analysis_completed = False
        log_text: str | None = None

        if auto_analyze and payload.bamboo_result_key:
            metadata, log_text = await fetch_bamboo_run(payload.bamboo_result_key)
            self._merge_bamboo_metadata(payload, metadata)
            payload.bamboo_log_url = (
                f"{get_settings().bamboo.base_url.rstrip('/')}/download/result/{payload.bamboo_result_key}/log"
            )

        if log_text:
            error_occurrences = extract_error_occurrences(log_text)
            analysis_completed = True
        elif payload.failure_summaries:
            error_occurrences = self._from_failure_summaries(payload.failure_summaries)
            analysis_completed = True

        aggregated_metrics = self._compute_run_metrics(payload, error_occurrences)
        document = TestRunDocument.from_ingest(
            payload,
            error_occurrences if analysis_completed else None,
            aggregated_metrics,
        )

        await self._runs.update_one(
            {"run_id": document.run_id},
            {"$set": document.model_dump()},
            upsert=True,
        )

        if error_occurrences:
            await self._update_error_signatures(document.run_id, error_occurrences)

        return document

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        doc = await self._runs.find_one({"run_id": run_id})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def list_runs(self, limit: int = 50, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = self._build_query(filters)
        cursor = self._runs.find(query).sort("start_time", -1).limit(limit)
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    def _build_query(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}
        query: dict[str, Any] = {}
        for key in ("plan", "suite", "environment", "triggered_by", "build", "status"):
            if value := filters.get(key):
                query[key] = value
        if "from" in filters or "to" in filters:
            date_filter: dict[str, Any] = {}
            if filters.get("from"):
                date_filter["$gte"] = filters["from"]
            if filters.get("to"):
                date_filter["$lte"] = filters["to"]
            query["start_time"] = date_filter
        return query

    async def _update_error_signatures(
        self, run_id: str, occurrences: list[ErrorOccurrence]
    ) -> None:
        for occurrence in occurrences:
            signature_data = occurrence.signature.model_dump()
            summary = signature_data["summary"]
            update_doc = {
                "$setOnInsert": {"first_seen": datetime.utcnow()},
                "$set": {
                    "summary": summary,
                    "category": signature_data.get("category"),
                    "probable_cause": signature_data.get("probable_cause"),
                    "last_seen": datetime.utcnow(),
                    "sample_stack_trace": occurrence.failures[0].stack_trace if occurrence.failures else None,
                },
                "$addToSet": {
                    "runs": run_id,
                    "affected_tests": {"$each": [f.test_case_id for f in occurrence.failures]},
                },
                "$inc": {"occurrences": occurrence.occurrences},
            }
            await self._error_signatures.update_one(
                {"signature_hash": signature_data["signature_hash"]},
                update_doc,
                upsert=True,
            )

    def _compute_run_metrics(
        self, payload: TestRunIngestRequest, occurrences: list[ErrorOccurrence]
    ) -> dict[str, Any]:
        total = payload.total_tests or max(1, payload.passed_tests + payload.failed_tests + payload.blocked_tests)
        pass_rate = payload.passed_tests / total if total else 0
        fail_rate = payload.failed_tests / total if total else 0

        errors_by_category = Counter(o.signature.category or "Uncategorized" for o in occurrences)
        return {
            "pass_rate": round(pass_rate, 4),
            "fail_rate": round(fail_rate, 4),
            "error_categories": dict(errors_by_category),
        }

    def _from_failure_summaries(self, failures: list[FailureContext]) -> list[ErrorOccurrence]:
        groups: dict[str, list[FailureContext]] = defaultdict(list)
        for failure in failures:
            groups[failure.message].append(failure)

        occurrences: list[ErrorOccurrence] = []
        for message, failure_group in groups.items():
            stack_sample = failure_group[0].stack_trace if failure_group else None
            signature_hash = self._hash_for_message(message, stack_sample)
            signature = ErrorSignature(
                signature_hash=signature_hash,
                summary=message,
                category=None,
            )
            occurrences.append(
                ErrorOccurrence(
                    signature=signature,
                    occurrences=len(failure_group),
                    failures=failure_group,
                )
            )
        return occurrences

    def _hash_for_message(self, message: str, stack_trace: str | None) -> str:
        from hashlib import sha256

        raw = message if not stack_trace else f"{message}\n{stack_trace.splitlines()[0]}"
        return sha256(raw.encode("utf-8", errors="ignore")).hexdigest()

    def _merge_bamboo_metadata(self, payload: TestRunIngestRequest, metadata: dict[str, Any]) -> None:
        payload.meta["bamboo_metadata"] = metadata
        if "buildState" in metadata:
            payload.status = metadata["buildState"].capitalize()
        if "buildDurationInSeconds" in metadata and metadata["buildDurationInSeconds"]:
            payload.duration_seconds = metadata["buildDurationInSeconds"]
        if "buildStartedTime" in metadata:
            try:
                payload.start_time = parser.isoparse(metadata["buildStartedTime"])
            except (ValueError, TypeError):
                pass
        if "buildCompletedDate" in metadata:
            try:
                payload.end_time = parser.isoparse(metadata["buildCompletedDate"])
            except (ValueError, TypeError):
                pass
        if "link" in metadata and isinstance(metadata["link"], dict):
            payload.bamboo_result_url = metadata["link"].get("href", payload.bamboo_result_url)

        test_results = metadata.get("testResults") or {}
        if isinstance(test_results, dict):
            failed = test_results.get("failed")
            if failed is not None:
                payload.failed_tests = int(failed)
            passed = test_results.get("successful")
            if passed is not None:
                payload.passed_tests = int(passed)
            skipped = test_results.get("skipped")
            if skipped is not None:
                payload.blocked_tests = int(skipped)
            total = test_results.get("total")
            if total is None:
                total = (
                    (payload.failed_tests or 0)
                    + (payload.passed_tests or 0)
                    + (payload.blocked_tests or 0)
                )
            if total is not None:
                payload.total_tests = int(total)


