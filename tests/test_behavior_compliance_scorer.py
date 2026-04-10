"""Tests for behavior compliance scoring against normalized traces."""

from __future__ import annotations

from typing import Any

from agent_evalkit.scorers.behavior_compliance import score_behavior_compliance


def test_score_behavior_compliance_happy_path() -> None:
    """Compliant traces should pass with full score and no violations."""
    result = score_behavior_compliance(
        behavior_rules={
            "forbid_tools": ["web.search"],
            "require_tools_any_of": [["calculator", "python.eval"]],
            "max_steps": 3,
            "trace_required": True,
            "max_tool_calls": 2,
        },
        trace_events=[
            {"event_type": "step", "step_index": 0},
            {"event_type": "tool_call", "tool_name": "calculator"},
            {"event_type": "step", "step_index": 1},
            {"event_type": "final", "step_index": 2},
        ],
    )

    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["violations"] == []


def test_score_behavior_compliance_forbidden_tool_used() -> None:
    """Using a forbidden tool should create a forbidden_tool_used violation."""
    result = score_behavior_compliance(
        behavior_rules={"forbid_tools": ["web.search"]},
        trace_events=[{"event_type": "tool_call", "tool_name": "web.search"}],
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["violations"][0]["type"] == "forbidden_tool_used"
    assert result["violations"][0]["path"] == "$.trace_events[0].tool_name"
    _assert_violation_shape(result["violations"][0])


def test_score_behavior_compliance_missing_required_tool_group() -> None:
    """Missing one required any-of group should emit missing_required_tool_group."""
    result = score_behavior_compliance(
        behavior_rules={"require_tools_any_of": [["search", "browse"], ["calculator"]]},
        trace_events=[{"event_type": "tool_call", "tool_name": "search"}],
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert len(result["violations"]) == 1
    assert result["violations"][0]["type"] == "missing_required_tool_group"
    assert result["violations"][0]["path"] == "$.behavior_rules.require_tools_any_of[1]"
    _assert_violation_shape(result["violations"][0])


def test_score_behavior_compliance_step_limit_exceeded() -> None:
    """Too many steps should emit a step_limit_exceeded violation."""
    result = score_behavior_compliance(
        behavior_rules={"max_steps": 2},
        trace_events=[
            {"event_type": "step", "step_index": 0},
            {"event_type": "step", "step_index": 1},
            {"event_type": "step", "step_index": 2},
        ],
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["violations"][0]["type"] == "step_limit_exceeded"
    assert result["violations"][0]["path"] == "$.behavior_rules.max_steps"
    _assert_violation_shape(result["violations"][0])


def test_score_behavior_compliance_tool_call_limit_exceeded() -> None:
    """Too many tool calls should emit a tool_call_limit_exceeded violation."""
    result = score_behavior_compliance(
        behavior_rules={"max_tool_calls": 1},
        trace_events=[
            {"event_type": "tool_call", "tool_name": "search"},
            {"event_type": "tool_call", "tool_name": "calculator"},
        ],
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert result["violations"][0]["type"] == "tool_call_limit_exceeded"
    assert result["violations"][0]["path"] == "$.behavior_rules.max_tool_calls"
    _assert_violation_shape(result["violations"][0])


def test_score_behavior_compliance_missing_trace() -> None:
    """Required traces should emit missing_trace when trace data is absent."""
    result = score_behavior_compliance(
        behavior_rules={
            "trace_required": True,
            "max_steps": 1,
            "require_tools_any_of": [["calculator"]],
        },
        trace_events=[],
    )

    assert result["passed"] is False
    assert result["score"] == 0.0
    assert len(result["violations"]) == 1
    assert result["violations"][0]["type"] == "missing_trace"
    assert result["violations"][0]["path"] == "$.trace_events"
    _assert_violation_shape(result["violations"][0])


def _assert_violation_shape(violation: dict[str, Any]) -> None:
    """Verify stable violation fields used for stats and diffing."""
    assert set(violation.keys()) >= {"type", "message", "path"}
