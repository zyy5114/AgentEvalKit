"""Tests for JSON Schema examples used in output validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "extract_output.schema.json"
EXAMPLES_DIR = ROOT_DIR / "examples"


def _load_json(path: Path) -> dict[str, object]:
    """Load and parse a JSON file into a Python dictionary."""
    return json.loads(path.read_text(encoding="utf-8"))


def test_extract_output_schema_is_valid_draft_2020_12() -> None:
    """Schema should declare and satisfy JSON Schema Draft 2020-12."""
    schema = _load_json(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


def test_extract_output_valid_example_passes() -> None:
    """Valid extraction payload should pass schema validation."""
    schema = _load_json(SCHEMA_PATH)
    payload = _load_json(EXAMPLES_DIR / "extract_output.valid.json")
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: error.path)
    assert errors == []


@pytest.mark.parametrize(
    ("filename", "expected_validator", "message_fragment"),
    [
        (
            "extract_output.invalid.missing_answer.json",
            "required",
            "answer",
        ),
        (
            "extract_output.invalid.wrong_citations_type.json",
            "type",
            "array",
        ),
    ],
)
def test_extract_output_invalid_examples_fail(
    filename: str,
    expected_validator: str,
    message_fragment: str,
) -> None:
    """Invalid extraction payloads should fail with realistic schema errors."""
    schema = _load_json(SCHEMA_PATH)
    payload = _load_json(EXAMPLES_DIR / filename)
    validator = Draft202012Validator(schema)

    errors = list(validator.iter_errors(payload))
    assert errors
    assert errors[0].validator == expected_validator
    assert message_fragment in errors[0].message
