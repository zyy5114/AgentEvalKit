"""CLI adapter execution for black-box command-based tasks."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CliTraceEvent(BaseModel):
    """Normalized trace event emitted by the CLI adapter."""

    model_config = ConfigDict(extra="forbid")

    event_type: str = Field(min_length=1)
    command: list[str]
    timeout_sec: float | None = None
    message: str | None = None


class CliAdapterResult(BaseModel):
    """Execution result payload returned by the CLI adapter."""

    model_config = ConfigDict(extra="forbid")

    command: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    status: Literal["succeeded", "failed", "timeout"]
    trace_events: list[CliTraceEvent]
    elapsed_sec: float = Field(ge=0.0)


def run_cli_command(
    *,
    command: Sequence[str],
    timeout_sec: float | None = None,
    cwd: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> CliAdapterResult:
    """Run a command using subprocess and return a normalized adapter result.

    Args:
        command: Command and arguments to execute.
        timeout_sec: Maximum runtime in seconds. ``None`` disables timeout.
        cwd: Optional working directory for subprocess execution.
        env: Optional environment variables for subprocess execution.

    Returns:
        A normalized command execution result suitable for scoring and tracing.
    """

    normalized_command = [str(part) for part in command]
    trace_events: list[CliTraceEvent] = []
    start = time.perf_counter()

    try:
        completed = subprocess.run(
            normalized_command,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            cwd=str(cwd) if cwd is not None else None,
            env=dict(env) if env is not None else None,
        )
        elapsed = time.perf_counter() - start

        status: Literal["succeeded", "failed", "timeout"]
        if completed.returncode == 0:
            status = "succeeded"
        else:
            status = "failed"

        return CliAdapterResult(
            command=normalized_command,
            returncode=completed.returncode,
            stdout=_coerce_text(completed.stdout),
            stderr=_coerce_text(completed.stderr),
            timed_out=False,
            status=status,
            trace_events=trace_events,
            elapsed_sec=elapsed,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.perf_counter() - start
        trace_events.append(
            CliTraceEvent(
                event_type="timeout",
                command=normalized_command,
                timeout_sec=float(timeout_sec) if timeout_sec is not None else None,
                message=f"Command exceeded timeout of {timeout_sec} seconds.",
            )
        )
        return CliAdapterResult(
            command=normalized_command,
            returncode=None,
            stdout=_coerce_text(exc.stdout),
            stderr=_coerce_text(exc.stderr),
            timed_out=True,
            status="timeout",
            trace_events=trace_events,
            elapsed_sec=elapsed,
        )


def _coerce_text(value: str | bytes | None) -> str:
    """Normalize subprocess output values into text for stable persistence."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value
