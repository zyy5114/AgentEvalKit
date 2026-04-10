"""Tests for Python callable adapter execution behavior."""

from __future__ import annotations

from typing import Any

from agent_evalkit.adapters.python_adapter import run_python_callable
from examples.fake_agent import fake_local_agent, offline_demo_inputs


def test_run_python_callable_with_direct_callable() -> None:
    """Adapter should invoke callables and capture normalized output/trace."""
    payload = {"task_id": "unit_task_01", "input_text": "hello"}
    expected = fake_local_agent(payload)

    result = run_python_callable(target=fake_local_agent, input_payload=payload)

    assert result.status == "succeeded"
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.timed_out is False
    assert result.final_output == expected["final_output"]
    assert [event.model_dump() for event in result.trace_events] == expected["trace_events"]
    assert result.elapsed_sec >= 0.0


def test_run_python_callable_with_import_target() -> None:
    """Adapter should resolve ``module:function`` targets and run them."""
    payload = {"task_id": "unit_task_02", "prompt": "2 + 3"}
    expected = fake_local_agent(payload)

    result = run_python_callable(
        target="examples.fake_agent:fake_local_agent",
        input_payload=payload,
    )

    assert result.target == "examples.fake_agent:fake_local_agent"
    assert result.status == "succeeded"
    assert result.returncode == 0
    assert result.final_output == expected["final_output"]
    assert [event.model_dump() for event in result.trace_events] == expected["trace_events"]


def test_run_python_callable_captures_failures_without_raising() -> None:
    """Adapter should return a failed result when invocation cannot complete."""
    result = run_python_callable(
        target="examples.fake_agent:missing_callable",
        input_payload={"task_id": "unit_task_03", "input_text": "ignored"},
    )

    assert result.status == "failed"
    assert result.returncode == 1
    assert result.final_output == {}
    assert result.trace_events
    assert result.trace_events[0].event_type == "error"
    assert "Target attribute not found" in result.stderr


def test_run_python_callable_rejects_invalid_target_format() -> None:
    """Adapter should fail with a clear message for malformed import targets."""
    result = run_python_callable(
        target="examples.fake_agent.fake_local_agent",
        input_payload={"task_id": "unit_task_04"},
    )

    assert result.status == "failed"
    assert result.returncode == 1
    assert result.trace_events[0].event_type == "error"
    assert "target must be a callable or a string" in result.stderr


def test_run_python_callable_rejects_non_callable_target_attribute() -> None:
    """Adapter should fail when a resolved import target is not callable."""
    result = run_python_callable(
        target="examples.fake_agent:__doc__",
        input_payload={"task_id": "unit_task_05"},
    )

    assert result.status == "failed"
    assert result.returncode == 1
    assert result.trace_events[0].event_type == "error"
    assert "Resolved target is not callable" in result.stderr


def test_run_python_callable_captures_runtime_errors_from_callable() -> None:
    """Adapter should convert callable exceptions into normalized failed results."""

    def _boom(_: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("boom")

    result = run_python_callable(
        target=_boom,
        input_payload={"task_id": "unit_task_06"},
    )

    assert result.status == "failed"
    assert result.returncode == 1
    assert result.final_output == {}
    assert result.trace_events[0].event_type == "error"
    assert result.trace_events[0].metadata["target"] == result.target
    assert "RuntimeError: boom" in result.stderr


def test_fake_agent_is_deterministic_across_demo_inputs() -> None:
    """Same payload should always produce identical output and trace."""
    for payload in offline_demo_inputs():
        first = run_python_callable(target=fake_local_agent, input_payload=payload)
        second = run_python_callable(target=fake_local_agent, input_payload=payload)

        assert first.status == "succeeded"
        assert second.status == "succeeded"
        assert first.final_output == second.final_output
        assert _trace_dump(first.trace_events) == _trace_dump(second.trace_events)


def _trace_dump(trace_events: list[Any]) -> list[dict[str, Any]]:
    """Convert trace events to dictionaries for stable comparison in tests."""
    return [event.model_dump() for event in trace_events]
