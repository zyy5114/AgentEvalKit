"""Tests for TaskSpec JSON Schema behavior-rules contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator

ROOT_DIR = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT_DIR / "schemas" / "task_spec.schema.json"
EXAMPLES_DIR = ROOT_DIR / "examples"


def _load_json(path: Path) -> dict[str, Any]:
    """Load and parse a JSON file into a Python mapping."""
    return json.loads(path.read_text(encoding="utf-8"))


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load and parse a YAML file into a Python mapping."""
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def test_task_spec_schema_is_valid_draft_2020_12() -> None:
    """Task spec schema should declare and satisfy JSON Schema Draft 2020-12."""
    schema = _load_json(SCHEMA_PATH)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("filename", ["task_echo.yaml", "task_math.yaml"])
def test_task_spec_examples_pass_schema_validation(filename: str) -> None:
    """Shipped YAML task examples should satisfy the task spec schema."""
    schema = _load_json(SCHEMA_PATH)
    payload = _load_yaml(EXAMPLES_DIR / filename)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    assert errors == []


@pytest.mark.parametrize(
    ("behavior_rules", "expected_path"),
    [
        ({"forbid_tools": "web.search"}, ("behavior_rules", "forbid_tools")),
        ({"forbid_tools": [1]}, ("behavior_rules", "forbid_tools", 0)),
        (
            {"require_tools_any_of": ["web.search"]},
            ("behavior_rules", "require_tools_any_of", 0),
        ),
        (
            {"require_tools_any_of": [["tool_a", 2]]},
            ("behavior_rules", "require_tools_any_of", 0, 1),
        ),
        ({"max_steps": 0}, ("behavior_rules", "max_steps")),
        ({"max_tool_calls": 0}, ("behavior_rules", "max_tool_calls")),
        ({"trace_required": "true"}, ("behavior_rules", "trace_required")),
        ({"timeout_sec": 0}, ("behavior_rules", "timeout_sec")),
        ({"unknown_rule": True}, ("behavior_rules",)),
    ],
)
def test_task_spec_schema_rejects_invalid_behavior_rules(
    behavior_rules: dict[str, Any],
    expected_path: tuple[str | int, ...],
) -> None:
    """Schema should reject behavior rule type/constraint violations."""
    schema = _load_json(SCHEMA_PATH)
    validator = Draft202012Validator(schema)
    payload = _minimal_task_spec_payload()
    payload["behavior_rules"] = behavior_rules

    errors = sorted(validator.iter_errors(payload), key=lambda error: list(error.path))
    assert errors
    assert tuple(errors[0].absolute_path) == expected_path


def _minimal_task_spec_payload() -> dict[str, Any]:
    """Return a minimal valid task spec payload."""
    return {
        "task_id": "contract_minimal",
        "description": "Minimal payload for schema contract tests.",
        "input": {},
        "adapter": {"type": "python_callable"},
        "output_schema": {"type": "object"},
        "behavior_rules": {},
        "scorers": [{"type": "exact_match"}],
    }
