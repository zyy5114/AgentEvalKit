"""YAML task specification loading and validation."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, ValidationError


class ScorerSpec(BaseModel):
    """Minimal scorer configuration for v0.1 task specs."""

    model_config = ConfigDict(extra="forbid")

    type: str


class BehaviorRulesSpec(BaseModel):
    """Executable behavior-rule contract for v0.1 task specs."""

    model_config = ConfigDict(extra="forbid")

    forbid_tools: list[str] | None = None
    require_tools_any_of: list[list[str]] | None = None
    max_steps: int | None = None
    trace_required: bool | None = None
    max_tool_calls: int | None = None
    timeout_sec: float | None = None


class TaskSpec(BaseModel):
    """Minimal task specification for v0.1."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    description: str
    input: dict[str, Any]
    adapter: dict[str, Any]
    output_schema: dict[str, Any]
    behavior_rules: BehaviorRulesSpec
    scorers: list[ScorerSpec]


REQUIRED_FIELDS: tuple[str, ...] = (
    "task_id",
    "description",
    "input",
    "adapter",
    "output_schema",
    "behavior_rules",
    "scorers",
)

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "task_spec.schema.json"


@lru_cache(maxsize=1)
def _task_spec_validator() -> Draft202012Validator:
    """Load and cache the JSON Schema validator used for task specs."""
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Task spec schema file not found: {SCHEMA_PATH}") from exc
    except OSError as exc:
        raise RuntimeError(f"Failed to read task spec schema file: {SCHEMA_PATH}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid JSON in task spec schema file: {SCHEMA_PATH}") from exc

    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _format_schema_error_path(path_parts: list[object]) -> str:
    """Return a stable dotted path for schema validation errors."""
    if not path_parts:
        return "$"
    joined_parts = ".".join(str(part) for part in path_parts)
    return f"$.{joined_parts}"


def load_task_spec(path: str | Path) -> TaskSpec:
    """Load and validate a task specification from YAML.

    Args:
        path: Path to a YAML task specification file.

    Returns:
        A validated ``TaskSpec`` instance.

    Raises:
        ValueError: If parsing or validation fails.
    """

    spec_path = Path(path)
    try:
        raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Task spec file not found: {spec_path}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read task spec file: {spec_path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in task spec file: {spec_path}: {exc}") from exc

    if raw is None:
        raise ValueError(f"Task spec file is empty: {spec_path}.")

    if not isinstance(raw, dict):
        actual = type(raw).__name__
        raise ValueError(f"Task spec root must be a mapping/object in {spec_path}, got {actual}.")

    missing = [field for field in REQUIRED_FIELDS if field not in raw]
    if missing:
        missing_joined = ", ".join(missing)
        raise ValueError(f"Missing required task spec fields in {spec_path}: {missing_joined}.")

    validator = _task_spec_validator()
    errors = sorted(validator.iter_errors(raw), key=lambda error: list(error.absolute_path))
    if errors:
        first_error = errors[0]
        error_path = _format_schema_error_path(list(first_error.absolute_path))
        raise ValueError(
            f"Invalid task spec in {spec_path}: schema validation failed at "
            f"{error_path}: {first_error.message}"
        )

    try:
        return TaskSpec.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid task spec in {spec_path}: {exc}") from exc
