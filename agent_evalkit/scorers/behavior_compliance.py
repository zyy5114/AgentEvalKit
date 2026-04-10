"""Behavior compliance scorer against normalized execution traces."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, TypedDict


class BehaviorViolation(TypedDict):
    """Stable machine-readable behavior violation payload."""

    type: str
    message: str
    path: str


class BehaviorComplianceResult(TypedDict):
    """Result payload returned by the behavior compliance scorer."""

    passed: bool
    score: float
    violations: list[BehaviorViolation]


_TOOL_EVENT_TYPES: frozenset[str] = frozenset({"tool_call", "tool_use", "tool"})
_TOOL_NAME_KEYS: tuple[str, ...] = ("tool_name", "tool", "name")


def score_behavior_compliance(
    *,
    behavior_rules: Mapping[str, Any] | Any,
    trace_events: Sequence[Any] | None,
) -> BehaviorComplianceResult:
    """Score behavior-rule compliance for a normalized execution trace.

    Args:
        behavior_rules: Behavior rule mapping (or model with matching attributes).
        trace_events: Normalized trace event list.

    Returns:
        Pass/fail, numeric score, and stable machine-readable violations.
    """

    normalized_events = _normalize_trace_events(trace_events)
    violations: list[BehaviorViolation] = []

    trace_required = bool(_rule_value(behavior_rules, "trace_required"))
    if trace_required and not normalized_events:
        violations.append(
            {
                "type": "missing_trace",
                "message": "Trace is required but no trace events were provided.",
                "path": "$.trace_events",
            }
        )
        return {"passed": False, "score": 0.0, "violations": violations}

    forbid_tools_raw = _rule_value(behavior_rules, "forbid_tools")
    forbid_tools = set(forbid_tools_raw) if isinstance(forbid_tools_raw, list) else set()

    tool_calls = _tool_calls(normalized_events)
    for event_index, tool_name in tool_calls:
        if tool_name in forbid_tools:
            violations.append(
                {
                    "type": "forbidden_tool_used",
                    "message": f"Forbidden tool '{tool_name}' was used.",
                    "path": f"$.trace_events[{event_index}].tool_name",
                }
            )

    required_groups_raw = _rule_value(behavior_rules, "require_tools_any_of")
    required_groups: list[list[str]] = (
        required_groups_raw if isinstance(required_groups_raw, list) else []
    )
    used_tools = {tool_name for _, tool_name in tool_calls}
    for group_index, tool_group in enumerate(required_groups):
        if not any(tool in used_tools for tool in tool_group):
            group_display = ", ".join(tool_group)
            violations.append(
                {
                    "type": "missing_required_tool_group",
                    "message": f"None of required tools were used: [{group_display}].",
                    "path": f"$.behavior_rules.require_tools_any_of[{group_index}]",
                }
            )

    max_steps = _rule_value(behavior_rules, "max_steps")
    if isinstance(max_steps, int):
        step_count = _step_count(normalized_events)
        if step_count > max_steps:
            violations.append(
                {
                    "type": "step_limit_exceeded",
                    "message": f"Step count {step_count} exceeded max_steps {max_steps}.",
                    "path": "$.behavior_rules.max_steps",
                }
            )

    max_tool_calls = _rule_value(behavior_rules, "max_tool_calls")
    if isinstance(max_tool_calls, int):
        tool_call_count = len(tool_calls)
        if tool_call_count > max_tool_calls:
            violations.append(
                {
                    "type": "tool_call_limit_exceeded",
                    "message": (
                        f"Tool call count {tool_call_count} exceeded max_tool_calls "
                        f"{max_tool_calls}."
                    ),
                    "path": "$.behavior_rules.max_tool_calls",
                }
            )

    return {
        "passed": not violations,
        "score": 1.0 if not violations else 0.0,
        "violations": violations,
    }


def _rule_value(behavior_rules: Mapping[str, Any] | Any, key: str) -> Any:
    """Read a behavior rule from mapping-like or attribute-like values."""
    if isinstance(behavior_rules, Mapping):
        return behavior_rules.get(key)
    return getattr(behavior_rules, key, None)


def _normalize_trace_events(trace_events: Sequence[Any] | None) -> list[dict[str, Any]]:
    """Normalize trace events into plain dictionaries."""
    if not trace_events:
        return []

    normalized: list[dict[str, Any]] = []
    for event in trace_events:
        if isinstance(event, Mapping):
            normalized.append(dict(event))
            continue

        model_dump = getattr(event, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump()
            normalized.append(dict(dumped) if isinstance(dumped, Mapping) else {})
            continue

        normalized.append({})

    return normalized


def _tool_calls(events: list[dict[str, Any]]) -> list[tuple[int, str]]:
    """Extract tool call entries as ``(event_index, tool_name)`` tuples."""
    extracted: list[tuple[int, str]] = []
    for event_index, event in enumerate(events):
        event_type = event.get("event_type")
        tool_name = _tool_name(event)
        if isinstance(event_type, str) and event_type in _TOOL_EVENT_TYPES and tool_name:
            extracted.append((event_index, tool_name))
            continue
        if tool_name:
            extracted.append((event_index, tool_name))
    return extracted


def _tool_name(event: Mapping[str, Any]) -> str | None:
    """Extract tool name from top-level or nested metadata fields."""
    for key in _TOOL_NAME_KEYS:
        value = event.get(key)
        if isinstance(value, str) and value:
            return value

    metadata = event.get("metadata")
    if not isinstance(metadata, Mapping):
        return None

    for key in _TOOL_NAME_KEYS:
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _step_count(events: list[dict[str, Any]]) -> int:
    """Compute step count from normalized trace events."""
    step_events = [
        event
        for event in events
        if isinstance(event.get("event_type"), str) and event["event_type"] == "step"
    ]
    if step_events:
        return len(step_events)

    step_indexes = [
        event.get("step_index")
        for event in events
        if isinstance(event.get("step_index"), int) and event.get("step_index") is not None
    ]
    if step_indexes:
        return max(step_indexes) + 1

    return 0
