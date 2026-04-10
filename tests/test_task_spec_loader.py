"""Tests for YAML task specification loading."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from textwrap import indent
from uuid import uuid4

import pytest

from agent_evalkit.specs.loader import BehaviorRulesSpec, TaskSpec, load_task_spec

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
RUNTIME_DIR = Path(__file__).resolve().parent / "_runtime_specs"


@contextmanager
def _runtime_spec_file(content: str) -> Path:
    """Create and clean up a temporary spec file under the test workspace."""
    RUNTIME_DIR.mkdir(exist_ok=True)
    path = RUNTIME_DIR / f"{uuid4().hex}.yaml"
    path.write_text(content, encoding="utf-8")
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
        if RUNTIME_DIR.exists() and not any(RUNTIME_DIR.iterdir()):
            RUNTIME_DIR.rmdir()


@pytest.mark.parametrize(
    "filename",
    ["task_echo.yaml", "task_math.yaml"],
)
def test_load_task_spec_valid_examples(filename: str) -> None:
    """Loader should parse and validate shipped example task specs."""
    spec = load_task_spec(EXAMPLES_DIR / filename)
    assert isinstance(spec, TaskSpec)
    assert spec.task_id
    assert spec.description
    assert isinstance(spec.input, dict)
    assert isinstance(spec.adapter, dict)
    assert isinstance(spec.output_schema, dict)
    assert isinstance(spec.behavior_rules, BehaviorRulesSpec)
    assert isinstance(spec.scorers, list)
    assert spec.scorers
    assert all(scorer.type for scorer in spec.scorers)


def test_load_task_spec_missing_required_fields() -> None:
    """Loader should fail fast when required fields are missing."""
    with _runtime_spec_file(
        """
description: Missing task id and other required fields.
input: {}
adapter: {}
output_schema: {}
behavior_rules: {}
scorers: []
""".strip(),
    ) as spec_file:
        with pytest.raises(ValueError, match="Missing required task spec fields"):
            load_task_spec(spec_file)


def test_load_task_spec_invalid_field_type() -> None:
    """Loader should return an explicit error for invalid field types."""
    with _runtime_spec_file(
        """
task_id: invalid_scorers
description: scorers should be a list
input: {}
adapter: {}
output_schema: {}
behavior_rules: {}
scorers: wrong_type
""".strip(),
    ) as spec_file:
        with pytest.raises(ValueError, match="Invalid task spec"):
            load_task_spec(spec_file)


def test_load_task_spec_invalid_root_type() -> None:
    """Loader should require a mapping/object at document root."""
    with _runtime_spec_file(
        """
- task_id: list_root
""".strip(),
    ) as spec_file:
        with pytest.raises(ValueError, match="Task spec root must be a mapping/object"):
            load_task_spec(spec_file)


def test_load_task_spec_rejects_unsafe_yaml_tags() -> None:
    """Loader should use safe YAML parsing and reject unsafe tags."""
    with _runtime_spec_file(
        """
!!python/object/new:os.system ["echo unsafe"]
""".strip(),
    ) as spec_file:
        with pytest.raises(ValueError, match="Invalid YAML in task spec file"):
            load_task_spec(spec_file)


def test_load_task_spec_empty_yaml_fails_clearly() -> None:
    """Loader should fail clearly for empty YAML documents."""
    with _runtime_spec_file("") as spec_file:
        with pytest.raises(ValueError, match="Task spec file is empty"):
            load_task_spec(spec_file)


def test_load_task_spec_behavior_rules_valid_definition() -> None:
    """Loader should accept all supported behavior rule fields."""
    behavior_rules = """
forbid_tools:
  - web.search
  - shell.exec
require_tools_any_of:
  - [memory.read]
  - [trace.log, trace.capture]
max_steps: 4
trace_required: true
max_tool_calls: 2
timeout_sec: 1.5
""".strip()
    with _runtime_spec_file(_build_spec_with_behavior_rules(behavior_rules)) as spec_file:
        spec = load_task_spec(spec_file)

    assert spec.behavior_rules.forbid_tools == ["web.search", "shell.exec"]
    assert spec.behavior_rules.require_tools_any_of == [
        ["memory.read"],
        ["trace.log", "trace.capture"],
    ]
    assert spec.behavior_rules.max_steps == 4
    assert spec.behavior_rules.trace_required is True
    assert spec.behavior_rules.max_tool_calls == 2
    assert spec.behavior_rules.timeout_sec == 1.5


@pytest.mark.parametrize(
    ("behavior_rules", "expected_fragment"),
    [
        ("forbid_tools: web.search", "$.behavior_rules.forbid_tools"),
        ("forbid_tools:\n  - 1", "$.behavior_rules.forbid_tools.0"),
        ("require_tools_any_of:\n  - web.search", "$.behavior_rules.require_tools_any_of.0"),
        (
            "require_tools_any_of:\n  - [tool_a, 2]",
            "$.behavior_rules.require_tools_any_of.0.1",
        ),
        ("max_steps: 0", "$.behavior_rules.max_steps"),
        ("max_steps: bad", "$.behavior_rules.max_steps"),
        ("trace_required: 'yes'", "$.behavior_rules.trace_required"),
        ("max_tool_calls: 0", "$.behavior_rules.max_tool_calls"),
        ("timeout_sec: 0", "$.behavior_rules.timeout_sec"),
        ("timeout_sec: bad", "$.behavior_rules.timeout_sec"),
        ("unknown_rule: true", "$.behavior_rules"),
    ],
)
def test_load_task_spec_behavior_rules_invalid_definitions(
    behavior_rules: str,
    expected_fragment: str,
) -> None:
    """Loader should reject invalid behavior rule contracts."""
    with _runtime_spec_file(_build_spec_with_behavior_rules(behavior_rules)) as spec_file:
        with pytest.raises(ValueError, match="schema validation failed") as exc_info:
            load_task_spec(spec_file)

    assert expected_fragment in str(exc_info.value)


def _build_spec_with_behavior_rules(behavior_rules: str) -> str:
    """Build a minimal task spec fixture with a caller-provided behavior_rules block."""
    return """
task_id: behavior_rules_contract
description: Validate behavior rules contract.
input: {{}}
adapter: {{}}
output_schema: {{}}
behavior_rules:
{behavior_rules}
scorers:
  - type: exact_match
""".strip().format(behavior_rules=indent(behavior_rules, "  "))
