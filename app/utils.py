"""Utility helpers for serialization and formatting."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from bson import ObjectId


def serialize_document(document: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in document.items():
        serialized[key] = _serialize_value(value)
    return serialized


def _serialize_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in value.items()}
    return value

