"""Trace collection and self-validation helpers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

TRACE_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "trace.schema.json"
TRACE_SCHEMA_VERSION = "1.0"
_CORE_EVENT_FIELDS = frozenset({"event_type", "step_index", "message", "metadata"})


class TraceValidationError(TypedDict):
    """Machine-readable validation error payload."""

    path: str
    message: str


class TraceValidationResult(TypedDict):
    """Validation result for a trace document."""

    valid: bool
    errors: list[TraceValidationError]


class TraceCollectionResult(TypedDict):
    """Result for end-of-run trace collection and self-validation."""

    trace: dict[str, Any]
    valid: bool
    errors: list[TraceValidationError]


def collect_trace(
    trace_events: Sequence[Any] | None,
    *,
    schema_version: str = TRACE_SCHEMA_VERSION,
) -> dict[str, Any]:
    """Build a normalized trace document from event inputs."""
    normalized_events = [_normalize_event(event) for event in list(trace_events or [])]
    return {
        "schema_version": schema_version,
        "events": normalized_events,
    }


def validate_trace(trace: Any) -> TraceValidationResult:
    """Validate a trace document and return machine-readable errors."""
    try:
        validator = _trace_validator()
    except (RuntimeError, SchemaError) as exc:
        return {
            "valid": False,
            "errors": [{"path": "$", "message": str(exc)}],
        }

    raw_errors = sorted(
        validator.iter_errors(trace),
        key=lambda err: (_format_path(err.absolute_path), err.message),
    )
    normalized_errors: list[TraceValidationError] = [
        {"path": _format_path(error.absolute_path), "message": error.message}
        for error in raw_errors
    ]
    return {
        "valid": not normalized_errors,
        "errors": normalized_errors,
    }


def collect_and_validate_trace(
    trace_events: Sequence[Any] | None,
    *,
    schema_version: str = TRACE_SCHEMA_VERSION,
) -> TraceCollectionResult:
    """Collect trace events and run trace self-validation at run completion."""
    trace = collect_trace(trace_events, schema_version=schema_version)
    validation = validate_trace(trace)
    return {
        "trace": trace,
        "valid": validation["valid"],
        "errors": validation["errors"],
    }


@lru_cache(maxsize=1)
def _trace_validator() -> Draft202012Validator:
    """Load and cache the trace schema validator."""
    try:
        schema = json.loads(TRACE_SCHEMA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Trace schema file not found: {TRACE_SCHEMA_PATH}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to read trace schema file: {TRACE_SCHEMA_PATH}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in trace schema file: {TRACE_SCHEMA_PATH}") from exc

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _normalize_event(event: Any) -> dict[str, Any]:
    """Normalize a single trace event into the trace schema shape."""
    raw_event = _event_mapping(event)

    normalized_metadata: dict[str, Any] = {}
    raw_metadata = raw_event.get("metadata")
    if isinstance(raw_metadata, Mapping):
        normalized_metadata.update(dict(raw_metadata))

    for key, value in raw_event.items():
        if key not in _CORE_EVENT_FIELDS:
            normalized_metadata[key] = value

    normalized_event: dict[str, Any] = {"metadata": normalized_metadata}
    if "event_type" in raw_event:
        normalized_event["event_type"] = raw_event.get("event_type")
    if "step_index" in raw_event:
        normalized_event["step_index"] = raw_event.get("step_index")
    if "message" in raw_event:
        normalized_event["message"] = raw_event.get("message")
    return normalized_event


def _event_mapping(event: Any) -> Mapping[str, Any]:
    """Convert event inputs into a mapping for normalization."""
    if isinstance(event, Mapping):
        return event

    model_dump = getattr(event, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, Mapping):
            return dumped

    return {}


def _format_path(path_parts: Iterable[Any]) -> str:
    """Convert validator paths into a stable machine-readable format."""
    path = "$"
    for part in path_parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path
