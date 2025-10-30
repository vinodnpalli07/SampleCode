"""Pydantic schemas describing test runs, failures, and analytics."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from pydantic import BaseModel, Field


class FailureContext(BaseModel):
    test_case_id: str = Field(..., description="Unique identifier of the test case")
    test_case_name: str = Field(..., description="Human readable name of the test")
    message: str = Field(..., description="Failure message extracted from logs")
    stack_trace: str | None = Field(default=None, description="Associated stack trace excerpt")
    log_excerpt: str | None = Field(default=None, description="Relevant log lines")
    attachments: list[str] = Field(
        default_factory=list,
        description="Paths or URLs to artifacts/screenshots for this failure",
    )


class ErrorSignature(BaseModel):
    signature_hash: str = Field(..., description="Stable hash of the error message/stack trace")
    summary: str = Field(..., description="Short description of the error")
    category: str | None = Field(default=None, description="Optional category label")
    probable_cause: str | None = Field(
        default=None, description="Classifier output describing the probable root cause"
    )


class ErrorOccurrence(BaseModel):
    signature: ErrorSignature
    occurrences: int = Field(..., description="Number of tests affected in this run")
    failures: list[FailureContext] = Field(default_factory=list)


class TestRunIngestRequest(BaseModel):
    run_id: str
    plan: str
    suite: str | None = None
    build: str | None = None
    environment: str | None = None
    triggered_by: str | None = Field(default=None, description="User or system who triggered the run")
    status: str = Field(..., description="Final status reported by Bamboo")
    start_time: datetime
    end_time: datetime | None = None
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int = 0
    not_executed_tests: int = 0
    duration_seconds: float | None = None
    bamboo_result_key: str | None = Field(
        default=None,
        description="Bamboo result key (e.g. PLAN-KEY-123) used for log lookups",
    )
    bamboo_result_url: str | None = None
    bamboo_log_url: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    failure_summaries: list[FailureContext] = Field(
        default_factory=list,
        description="Known failure contexts captured client side (optional)",
    )


class TestRunDocument(BaseModel):
    run_id: str
    plan: str
    suite: str | None
    build: str | None
    environment: str | None
    triggered_by: str | None
    status: str
    start_time: datetime
    end_time: datetime | None
    duration_seconds: float | None
    total_tests: int
    passed_tests: int
    failed_tests: int
    blocked_tests: int
    not_executed_tests: int
    bamboo_result_key: str | None = None
    bamboo_result_url: str | None
    bamboo_log_url: str | None
    meta: dict[str, Any]
    analysis_completed: bool = False
    error_occurrences: list[ErrorOccurrence] = Field(default_factory=list)
    aggregated_metrics: dict[str, Any] = Field(default_factory=dict)
    ingested_at: datetime

    @classmethod
    def from_ingest(
        cls,
        payload: TestRunIngestRequest,
        error_occurrences: Iterable[ErrorOccurrence] | None = None,
        aggregated_metrics: dict[str, Any] | None = None,
    ) -> "TestRunDocument":
        duration = payload.duration_seconds
        if duration is None and payload.end_time is not None:
            duration = (payload.end_time - payload.start_time).total_seconds()

        return cls(
            run_id=payload.run_id,
            plan=payload.plan,
            suite=payload.suite,
            build=payload.build,
            environment=payload.environment,
            triggered_by=payload.triggered_by,
            status=payload.status,
            start_time=payload.start_time,
            end_time=payload.end_time,
            duration_seconds=duration,
            total_tests=payload.total_tests,
            passed_tests=payload.passed_tests,
            failed_tests=payload.failed_tests,
            blocked_tests=payload.blocked_tests,
            not_executed_tests=payload.not_executed_tests,
            bamboo_result_key=payload.bamboo_result_key,
            bamboo_result_url=payload.bamboo_result_url,
            bamboo_log_url=payload.bamboo_log_url,
            meta=payload.meta,
            analysis_completed=error_occurrences is not None,
            error_occurrences=list(error_occurrences or []),
            aggregated_metrics=aggregated_metrics or {},
            ingested_at=datetime.utcnow(),
        )

