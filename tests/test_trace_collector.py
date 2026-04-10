"""Tests for trace contract schema and trace self-validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from agent_evalkit.traces import collector as collector_module
from agent_evalkit.traces.collector import collect_and_validate_trace, validate_trace

ROOT_DIR = Path(__file__).resolve().parents[1]
TRACE_SCHEMA_PATH = ROOT_DIR / "schemas" / "trace.schema.json"


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse a JSON file into a Python mapping."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_trace_schema_is_valid_draft_2020_12() -> None:
    """Trace schema should declare and satisfy JSON Schema Draft 2020-12."""
    schema = _load_json(TRACE_SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_collect_and_validate_trace_happy_path() -> None:
    """Collector should return a valid trace document for normalized events."""
    result = collect_and_validate_trace(
        [
            {"event_type": "step", "step_index": 0, "message": "parse"},
            {"event_type": "tool_call", "step_index": 1, "metadata": {"tool_name": "search"}},
            {"event_type": "final", "step_index": 2, "message": "done"},
        ]
    )

    assert result["valid"] is True
    assert result["errors"] == []
    assert result["trace"]["schema_version"] == "1.0"
    assert len(result["trace"]["events"]) == 3


def test_collect_and_validate_trace_moves_extra_fields_into_metadata() -> None:
    """Collector should normalize adapter-specific extra fields into metadata."""
    result = collect_and_validate_trace(
        [
            {
                "event_type": "timeout",
                "message": "Command exceeded timeout.",
                "command": ["python", "-c", "import time; time.sleep(1)"],
                "timeout_sec": 0.1,
            }
        ]
    )

    assert result["valid"] is True
    normalized_event = result["trace"]["events"][0]
    assert "command" not in normalized_event
    assert "timeout_sec" not in normalized_event
    assert normalized_event["metadata"]["command"] == [
        "python",
        "-c",
        "import time; time.sleep(1)",
    ]
    assert normalized_event["metadata"]["timeout_sec"] == 0.1


def test_collect_and_validate_trace_normalizes_model_dump_events() -> None:
    """Collector should accept model_dump events and preserve extra metadata fields."""

    class Event:
        def model_dump(self) -> dict[str, Any]:
            return {
                "event_type": "tool_call",
                "step_index": 1,
                "tool_name": "search",
            }

    result = collect_and_validate_trace([Event()])

    assert result["valid"] is True
    event = result["trace"]["events"][0]
    assert event["event_type"] == "tool_call"
    assert event["step_index"] == 1
    assert event["metadata"]["tool_name"] == "search"


def test_validate_trace_rejects_missing_required_event_type() -> None:
    """Validator should fail when a trace event omits event_type."""
    result = validate_trace(
        {
            "schema_version": "1.0",
            "events": [{"step_index": 0, "message": "no type", "metadata": {}}],
        }
    )

    assert result["valid"] is False
    assert result["errors"]
    assert result["errors"][0]["path"] == "$.events[0]"
    assert "event_type" in result["errors"][0]["message"]
    _assert_error_shape(result["errors"][0])


def test_validate_trace_rejects_invalid_step_index() -> None:
    """Validator should fail when step_index has invalid value/type."""
    result = validate_trace(
        {
            "schema_version": "1.0",
            "events": [{"event_type": "step", "step_index": -1, "metadata": {}}],
        }
    )

    assert result["valid"] is False
    assert result["errors"]
    assert result["errors"][0]["path"] == "$.events[0].step_index"
    _assert_error_shape(result["errors"][0])


def test_validate_trace_rejects_invalid_schema_version() -> None:
    """Validator should fail when schema_version does not match supported version."""
    result = validate_trace({"schema_version": "2.0", "events": []})

    assert result["valid"] is False
    assert result["errors"]
    assert result["errors"][0]["path"] == "$.schema_version"
    _assert_error_shape(result["errors"][0])


def test_validate_trace_handles_missing_schema_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validator should return a machine-readable error when schema loading fails."""
    collector_module._trace_validator.cache_clear()
    missing_schema = Path(__file__).resolve().parent / "_no_such_trace_schema.json"
    monkeypatch.setattr(collector_module, "TRACE_SCHEMA_PATH", missing_schema)

    result = collector_module.validate_trace({"schema_version": "1.0", "events": []})

    collector_module._trace_validator.cache_clear()
    assert result["valid"] is False
    assert result["errors"][0]["path"] == "$"
    assert "Trace schema file not found" in result["errors"][0]["message"]


def _assert_error_shape(error: dict[str, Any]) -> None:
    """Validate stable machine-readable trace validation error fields."""
    assert set(error.keys()) >= {"path", "message"}
