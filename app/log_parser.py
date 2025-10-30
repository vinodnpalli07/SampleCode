"""Utilities to extract failure signatures from Bamboo logs."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from .models.schemas import ErrorOccurrence, ErrorSignature, FailureContext


TRACEBACK_START = re.compile(r"Traceback \(most recent call last\):")
ERROR_LINE = re.compile(r"^(?P<level>ERROR|FATAL|FAIL|TRACEBACK)[:\s](?P<body>.*)$", re.IGNORECASE)
JAVA_EXCEPTION = re.compile(r"^(?P<class>[\w.]+Exception):\s*(?P<message>.*)")
TEST_NAME_HINT = re.compile(r"(?:Test(?:Case)?|Scenario)[:\s]+(?P<name>[\w .:/-]+)")


@dataclass(slots=True)
class LogFailureCandidate:
    header: str
    body_lines: list[str]

    def to_failure_context(self) -> FailureContext:
        stack_trace = "\n".join(self.body_lines).strip() or None
        test_name = _extract_test_name(self.body_lines) or "Unknown Test"
        message = _derive_message(self.header, self.body_lines)
        return FailureContext(
            test_case_id=test_name.lower().replace(" ", "-"),
            test_case_name=test_name,
            message=message,
            stack_trace=stack_trace,
            log_excerpt=f"{self.header}\n{stack_trace}" if stack_trace else self.header,
        )


def _extract_test_name(lines: Iterable[str]) -> str | None:
    for line in lines:
        match = TEST_NAME_HINT.search(line)
        if match:
            return match.group("name").strip()
    return None


def _derive_message(header: str, body: list[str]) -> str:
    if body:
        first_body_line = body[0].strip()
        if first_body_line:
            return first_body_line
    return header.split(":", 1)[-1].strip() or header


def _hash_signature(summary: str, stack_trace: str | None) -> str:
    raw = summary if stack_trace is None else f"{summary}\n{stack_trace.splitlines()[0]}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def extract_error_occurrences(log_text: str) -> list[ErrorOccurrence]:
    """Analyze raw log text and return aggregated error occurrences."""

    candidates: list[LogFailureCandidate] = []
    lines = log_text.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        match = ERROR_LINE.match(line)
        if match:
            body: list[str] = []
            idx += 1
            while idx < len(lines) and not ERROR_LINE.match(lines[idx]):
                body.append(lines[idx])
                idx += 1
            candidates.append(LogFailureCandidate(header=line, body_lines=body))
            continue

        if TRACEBACK_START.search(line):
            body = [line]
            idx += 1
            while idx < len(lines) and lines[idx].strip():
                body.append(lines[idx])
                idx += 1
            header = body[-1] if body else line
            candidates.append(LogFailureCandidate(header=header, body_lines=body))
            continue

        java_match = JAVA_EXCEPTION.match(line)
        if java_match:
            body = [line]
            idx += 1
            while idx < len(lines) and lines[idx].startswith("\tat "):
                body.append(lines[idx])
                idx += 1
            candidates.append(LogFailureCandidate(header=line, body_lines=body))
            continue

        idx += 1

    grouped: dict[str, list[FailureContext]] = defaultdict(list)
    summaries: dict[str, str] = {}
    for candidate in candidates:
        failure = candidate.to_failure_context()
        summary = failure.message
        signature_hash = _hash_signature(summary, failure.stack_trace)
        grouped[signature_hash].append(failure)
        summaries.setdefault(signature_hash, summary)

    occurrences: list[ErrorOccurrence] = []
    for signature_hash, failures in grouped.items():
        signature = ErrorSignature(
            signature_hash=signature_hash,
            summary=summaries[signature_hash],
            category=_infer_category(summaries[signature_hash]),
        )
        occurrences.append(
            ErrorOccurrence(
                signature=signature,
                occurrences=len(failures),
                failures=failures,
            )
        )

    return occurrences


def _infer_category(summary: str) -> str | None:
    summary_lower = summary.lower()
    if "timeout" in summary_lower:
        return "Timeout"
    if "connection" in summary_lower and "refused" in summary_lower:
        return "Network"
    if "assert" in summary_lower:
        return "Assertion"
    if "nullpointer" in summary_lower or "none" in summary_lower:
        return "Null Reference"
    if "outofmemory" in summary_lower:
        return "Resource"
    return None

