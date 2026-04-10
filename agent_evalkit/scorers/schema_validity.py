"""JSON Schema validity scorer for final task outputs."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TypedDict

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


class SchemaValidityError(TypedDict):
    """Normalized machine-readable validation error."""

    path: str
    message: str
    keyword: str


class SchemaValidityResult(TypedDict):
    """Result payload returned by the schema validity scorer."""

    passed: bool
    score: float
    errors: list[SchemaValidityError]


def _format_error_path(path_parts: Iterable[Any]) -> str:
    """Convert jsonschema path parts into a stable dotted path."""
    path = "$"
    for part in path_parts:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}"
    return path


def score_schema_validity(
    final_output: Any,
    output_schema: dict[str, Any],
) -> SchemaValidityResult:
    """Validate final output against a JSON Schema Draft 2020-12 schema.

    Args:
        final_output: Candidate final output payload to validate.
        output_schema: JSON Schema used for output validation.

    Returns:
        A machine-readable result with pass/fail status, score, and normalized errors.
    """

    try:
        Draft202012Validator.check_schema(output_schema)
    except SchemaError as exc:
        return {
            "passed": False,
            "score": 0.0,
            "errors": [
                {
                    "path": _format_error_path(exc.absolute_path),
                    "message": f"Invalid output schema: {exc.message}",
                    "keyword": "schema",
                }
            ],
        }

    validator = Draft202012Validator(output_schema)
    raw_errors = sorted(
        validator.iter_errors(final_output),
        key=lambda err: (_format_error_path(err.absolute_path), err.message),
    )

    normalized_errors: list[SchemaValidityError] = [
        {
            "path": _format_error_path(error.absolute_path),
            "message": error.message,
            "keyword": str(error.validator),
        }
        for error in raw_errors
    ]

    return {
        "passed": not normalized_errors,
        "score": 1.0 if not normalized_errors else 0.0,
        "errors": normalized_errors,
    }
