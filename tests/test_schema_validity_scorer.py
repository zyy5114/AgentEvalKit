"""Tests for schema validity scoring."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agent_evalkit.scorers.schema_validity import score_schema_validity

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "extract_output.schema.json"
EXAMPLES_DIR = ROOT_DIR / "examples"


def _load_json(path: Path) -> Any:
    """Load JSON from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_score_schema_validity_passes_for_valid_example() -> None:
    """Valid payload should receive a passing schema score."""
    schema = _load_json(SCHEMA_PATH)
    payload = _load_json(EXAMPLES_DIR / "extract_output.valid.json")

    result = score_schema_validity(final_output=payload, output_schema=schema)

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["errors"] == []


def test_score_schema_validity_fails_for_missing_required_field() -> None:
    """Missing required field should produce a structured validation error."""
    schema = _load_json(SCHEMA_PATH)
    payload = _load_json(EXAMPLES_DIR / "extract_output.invalid.missing_answer.json")

    result = score_schema_validity(final_output=payload, output_schema=schema)

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["errors"]

    error = result["errors"][0]
    assert set(error) >= {"path", "message", "keyword"}
    assert error["path"] == "$"
    assert "required property" in error["message"]
    assert "answer" in error["message"]
    assert error["keyword"] == "required"


def test_score_schema_validity_collects_multiple_errors() -> None:
    """Scorer should return multiple schema errors when they are available."""
    schema = _load_json(SCHEMA_PATH)
    payload = {
        "answer": 123,
        "citations": "doc_010",
        "unexpected_field": True,
    }

    result = score_schema_validity(final_output=payload, output_schema=schema)

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert len(result["errors"]) >= 2

    paths = {error["path"] for error in result["errors"]}
    messages = " | ".join(error["message"] for error in result["errors"])
    assert "$.answer" in paths
    assert "$.citations" in paths
    assert "unexpected_field" in messages


def test_score_schema_validity_handles_invalid_output_schema() -> None:
    """Scorer should return a structured schema error for invalid JSON Schemas."""
    invalid_schema = {"type": 123}

    result = score_schema_validity(final_output={"answer": "ok"}, output_schema=invalid_schema)

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["errors"]
    assert result["errors"][0]["keyword"] == "schema"
    assert "Invalid output schema" in result["errors"][0]["message"]
