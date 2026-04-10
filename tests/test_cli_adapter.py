"""Tests for CLI adapter subprocess execution behavior."""

from __future__ import annotations

import sys

from agent_evalkit.adapters.cli_adapter import run_cli_command


def test_run_cli_command_successful_execution() -> None:
    """Adapter should capture stdout/stderr and mark successful completion."""
    command = [
        sys.executable,
        "-c",
        "import sys; print('ok'); sys.stderr.write('warn\\n')",
    ]

    result = run_cli_command(command=command, timeout_sec=2.0)

    assert result.command == command
    assert result.returncode == 0
    assert result.stdout == "ok\n"
    assert result.stderr == "warn\n"
    assert result.timed_out is False
    assert result.status == "succeeded"
    assert result.trace_events == []


def test_run_cli_command_nonzero_exit() -> None:
    """Adapter should distinguish command failures from timeout outcomes."""
    command = [
        sys.executable,
        "-c",
        "import sys; sys.stderr.write('boom\\n'); raise SystemExit(7)",
    ]

    result = run_cli_command(command=command, timeout_sec=2.0)

    assert result.command == command
    assert result.returncode == 7
    assert result.stdout == ""
    assert result.stderr == "boom\n"
    assert result.timed_out is False
    assert result.status == "failed"
    assert result.trace_events == []


def test_run_cli_command_timeout_records_trace_event() -> None:
    """Timeouts should be classified separately and emit trace metadata."""
    command = [
        sys.executable,
        "-c",
        "import time; time.sleep(1.0)",
    ]

    result = run_cli_command(command=command, timeout_sec=0.05)

    assert result.command == command
    assert result.returncode is None
    assert result.timed_out is True
    assert result.status == "timeout"
    assert result.trace_events

    timeout_event = result.trace_events[0]
    assert timeout_event.event_type == "timeout"
    assert timeout_event.command == command
    assert timeout_event.timeout_sec == 0.05
