"""Python callable adapter execution for black-box function-based tasks."""

from __future__ import annotations

import importlib
import time
from collections.abc import Callable, Mapping
from typing import Any, Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, Field


class PythonCallable(Protocol):
    """Callable signature expected by the Python adapter."""

    def __call__(self, input_payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Execute with a task input payload and return output plus trace metadata."""


class PythonTraceEvent(BaseModel):
    """Normalized trace event emitted by a Python callable."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    step_index: int | None = Field(default=None, ge=0)
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PythonAgentResponse(BaseModel):
    """Canonical response payload expected from Python callables."""

    model_config = ConfigDict(extra="forbid")

    final_output: dict[str, Any]
    trace_events: list[PythonTraceEvent] = Field(default_factory=list)


class PythonAdapterResult(BaseModel):
    """Execution result payload returned by the Python adapter."""

    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1)
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    status: Literal["succeeded", "failed"]
    final_output: dict[str, Any]
    trace_events: list[PythonTraceEvent]
    elapsed_sec: float = Field(ge=0.0)


def run_python_callable(
    *,
    target: str | PythonCallable,
    input_payload: Mapping[str, Any],
) -> PythonAdapterResult:
    """Run a Python callable and return a normalized adapter result.

    Args:
        target: Callable object or import string in ``module.path:callable_name`` format.
        input_payload: Task input payload passed to the callable.

    Returns:
        A normalized execution result suitable for downstream scoring and tracing.
    """

    target_label = _target_label(target)
    start = time.perf_counter()

    try:
        resolved_callable, target_label = _resolve_target(target)
        raw_response = resolved_callable(dict(input_payload))
        response = PythonAgentResponse.model_validate(raw_response)
        elapsed = time.perf_counter() - start
        return PythonAdapterResult(
            target=target_label,
            returncode=0,
            stdout="",
            stderr="",
            timed_out=False,
            status="succeeded",
            final_output=response.final_output,
            trace_events=response.trace_events,
            elapsed_sec=elapsed,
        )
    except Exception as exc:
        elapsed = time.perf_counter() - start
        error_message = f"{type(exc).__name__}: {exc}"
        return PythonAdapterResult(
            target=target_label,
            returncode=1,
            stdout="",
            stderr=error_message,
            timed_out=False,
            status="failed",
            final_output={},
            trace_events=[
                PythonTraceEvent(
                    event_type="error",
                    step_index=0,
                    message=error_message,
                    metadata={"target": target_label},
                )
            ],
            elapsed_sec=elapsed,
        )


def _resolve_target(target: str | PythonCallable) -> tuple[PythonCallable, str]:
    """Resolve callable object from a direct callable or ``module:attribute`` target."""
    if callable(target):
        return cast(PythonCallable, target), _target_label(target)

    if not isinstance(target, str) or ":" not in target:
        raise ValueError(
            "target must be a callable or a string in 'module.path:callable_name' format."
        )

    module_name, attribute_path = target.split(":", maxsplit=1)
    if not module_name or not attribute_path:
        raise ValueError(
            "target must be a callable or a string in 'module.path:callable_name' format."
        )

    module = importlib.import_module(module_name)
    resolved: Any = module
    for attribute in attribute_path.split("."):
        if not hasattr(resolved, attribute):
            raise ValueError(f"Target attribute not found: {target}")
        resolved = getattr(resolved, attribute)

    if not callable(resolved):
        raise ValueError(f"Resolved target is not callable: {target}")

    return cast(PythonCallable, resolved), target


def _target_label(target: str | Callable[..., Any]) -> str:
    """Return a stable target label for reporting."""
    if isinstance(target, str):
        return target
    module_name = getattr(target, "__module__", "callable")
    callable_name = getattr(target, "__qualname__", getattr(target, "__name__", "callable"))
    return f"{module_name}:{callable_name}"
