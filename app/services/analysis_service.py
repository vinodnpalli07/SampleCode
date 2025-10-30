"""Service responsible for computing dashboard analytics and visualisations."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorDatabase

from ..database import Database


class AnalysisService:
    def __init__(self, db: AsyncIOMotorDatabase | None = None) -> None:
        self._db = db or Database.get_database()
        self._runs: AsyncIOMotorCollection = self._db["test_runs"]
        self._error_signatures: AsyncIOMotorCollection = self._db["error_signatures"]

    async def dashboard_summary(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        match_stage = self._build_match(filters)
        pipeline = [match_stage] if match_stage else []
        pipeline.extend(
            [
                {
                    "$group": {
                        "_id": None,
                        "runs": {"$sum": 1},
                        "total_tests": {"$sum": "$total_tests"},
                        "passed_tests": {"$sum": "$passed_tests"},
                        "failed_tests": {"$sum": "$failed_tests"},
                        "blocked_tests": {"$sum": "$blocked_tests"},
                        "avg_duration": {"$avg": "$duration_seconds"},
                    }
                }
            ]
        )
        result = await self._runs.aggregate(pipeline).to_list(length=1)
        aggregate = result[0] if result else {}

        total_tests = aggregate.get("total_tests", 0) or 0
        passed_tests = aggregate.get("passed_tests", 0) or 0
        failed_tests = aggregate.get("failed_tests", 0) or 0
        blocked_tests = aggregate.get("blocked_tests", 0) or 0

        avg_duration = aggregate.get("avg_duration")
        if avg_duration is not None:
            avg_duration = float(avg_duration)

        return {
            "runs": aggregate.get("runs", 0),
            "total_tests": total_tests,
            "pass_rate": round(passed_tests / total_tests, 4) if total_tests else 0,
            "fail_rate": round(failed_tests / total_tests, 4) if total_tests else 0,
            "blocked_rate": round(blocked_tests / total_tests, 4) if total_tests else 0,
            "avg_duration_seconds": avg_duration,
        }

    async def recent_runs(self, limit: int = 20, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = self._build_query(filters)
        cursor = self._runs.find(query).sort("start_time", -1).limit(limit)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    async def common_errors(self, limit: int = 15, days: int | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if days is not None:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query["last_seen"] = {"$gte": cutoff}

        cursor = (
            self._error_signatures.find(query)
            .sort("occurrences", -1)
            .limit(limit)
        )
        results: list[dict[str, Any]] = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    async def error_trends(self, limit: int = 30) -> list[dict[str, Any]]:
        pipeline = [
            {
                "$unwind": {
                    "path": "$error_occurrences",
                    "preserveNullAndEmptyArrays": False,
                }
            },
            {
                "$group": {
                    "_id": {
                        "signature_hash": "$error_occurrences.signature.signature_hash",
                        "run_id": "$run_id",
                    },
                    "occurrences": {"$sum": "$error_occurrences.occurrences"},
                    "run_start": {"$first": "$start_time"},
                    "summary": {"$first": "$error_occurrences.signature.summary"},
                }
            },
            {"$sort": {"run_start": -1}},
            {"$limit": limit},
        ]
        cursor = self._runs.aggregate(pipeline)
        return [doc async for doc in cursor]

    def _build_match(self, filters: dict[str, Any] | None) -> dict[str, Any] | None:
        if not filters:
            return None
        conditions = self._build_query(filters)
        if not conditions:
            return None
        return {"$match": conditions}

    def _build_query(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}
        query: dict[str, Any] = {}
        if plan := filters.get("plan"):
            query["plan"] = plan
        if suite := filters.get("suite"):
            query["suite"] = suite
        if environment := filters.get("environment"):
            query["environment"] = environment
        if owner := filters.get("triggered_by"):
            query["triggered_by"] = owner
        if build := filters.get("build"):
            query["build"] = build
        if status := filters.get("status"):
            query["status"] = status
        if date_from := filters.get("from"):
            query.setdefault("start_time", {})["$gte"] = date_from
        if date_to := filters.get("to"):
            query.setdefault("start_time", {})["$lte"] = date_to
        return query

