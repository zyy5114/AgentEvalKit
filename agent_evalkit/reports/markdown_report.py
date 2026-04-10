"""Markdown regression report rendering for baseline/candidate diffs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def render_regression_markdown(diff_payload: Mapping[str, Any]) -> str:
    """Render a concise engineering-oriented Markdown regression report."""
    baseline_source = str(diff_payload.get("baseline_source", ""))
    candidate_source = str(diff_payload.get("candidate_source", ""))
    baseline_count = int(diff_payload.get("baseline_task_count", 0))
    candidate_count = int(diff_payload.get("candidate_task_count", 0))
    shared_count = int(diff_payload.get("shared_task_count", 0))

    success = _metric(diff_payload, "success_rate")
    score = _metric(diff_payload, "score")
    latency = _metric(diff_payload, "latency_sec")

    changed = diff_payload.get("changed_failure_cases")
    changed_mapping = changed if isinstance(changed, Mapping) else {}
    pass_to_fail = _string_list(changed_mapping.get("pass_to_fail"))
    fail_to_pass = _string_list(changed_mapping.get("fail_to_pass"))
    violation_changes = changed_mapping.get("violation_type_changes")
    violation_change_rows = list(violation_changes) if isinstance(violation_changes, list) else []

    violations_distribution = diff_payload.get("violations_distribution")
    violations_mapping = (
        violations_distribution if isinstance(violations_distribution, Mapping) else {}
    )
    baseline_violations = _int_map(violations_mapping.get("baseline"))
    candidate_violations = _int_map(violations_mapping.get("candidate"))
    delta_violations = _int_map(violations_mapping.get("delta"))
    violation_types = sorted(
        set(baseline_violations) | set(candidate_violations) | set(delta_violations)
    )

    drift_hints = _string_list(diff_payload.get("drift_hints"))

    lines: list[str] = []
    lines.append("# AgentEvalKit Regression Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Baseline source: `{baseline_source}`")
    lines.append(f"- Candidate source: `{candidate_source}`")
    lines.append(
        f"- Tasks: baseline={baseline_count}, candidate={candidate_count}, shared={shared_count}"
    )
    lines.append("")
    lines.append("## Metric Deltas")
    lines.append("| Metric | Baseline | Candidate | Delta |")
    lines.append("| --- | ---: | ---: | ---: |")
    lines.append(
        "| Success rate | "
        f"{_format_ratio(success['baseline'])} | "
        f"{_format_ratio(success['candidate'])} | "
        f"{_format_ratio_delta(success['delta'])} |"
    )
    lines.append(
        "| Score | "
        f"{_format_decimal(score['baseline'])} | "
        f"{_format_decimal(score['candidate'])} | "
        f"{_format_delta(score['delta'])} |"
    )
    lines.append(
        "| Latency (sec) | "
        f"{_format_decimal(latency['baseline'])} | "
        f"{_format_decimal(latency['candidate'])} | "
        f"{_format_delta(latency['delta'])} |"
    )
    lines.append("")
    lines.append("## Changed Failure Cases")
    lines.append(f"- `pass -> fail`: {_inline_list(pass_to_fail)}")
    lines.append(f"- `fail -> pass`: {_inline_list(fail_to_pass)}")
    if violation_change_rows:
        lines.append("- `violation type changes`:")
        for row in violation_change_rows:
            if not isinstance(row, Mapping):
                continue
            task_id = str(row.get("task_id", ""))
            baseline_types = _string_list(row.get("baseline"))
            candidate_types = _string_list(row.get("candidate"))
            lines.append(
                f"  - `{task_id}`: "
                f"{_inline_list(baseline_types)} -> {_inline_list(candidate_types)}"
            )
    else:
        lines.append("- `violation type changes`: none")
    lines.append("")
    lines.append("## Violation Distribution")
    if violation_types:
        lines.append("| Violation type | Baseline | Candidate | Delta |")
        lines.append("| --- | ---: | ---: | ---: |")
        for violation_type in violation_types:
            lines.append(
                f"| `{violation_type}` | "
                f"{baseline_violations.get(violation_type, 0)} | "
                f"{candidate_violations.get(violation_type, 0)} | "
                f"{delta_violations.get(violation_type, 0):+d} |"
            )
    else:
        lines.append("- none")
    lines.append("")
    lines.append("## Drift Hints")
    if drift_hints:
        for hint in drift_hints:
            lines.append(f"- {hint}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def _metric(payload: Mapping[str, Any], key: str) -> dict[str, float | None]:
    """Read a metric object and normalize baseline/candidate/delta values."""
    value = payload.get(key)
    mapping = value if isinstance(value, Mapping) else {}
    return {
        "baseline": _as_float(mapping.get("baseline")),
        "candidate": _as_float(mapping.get("candidate")),
        "delta": _as_float(mapping.get("delta")),
    }


def _int_map(value: Any) -> dict[str, int]:
    """Normalize mapping values to integer counts."""
    if not isinstance(value, Mapping):
        return {}
    normalized: dict[str, int] = {}
    for raw_key, raw_count in value.items():
        key = str(raw_key)
        if isinstance(raw_count, bool):
            continue
        if isinstance(raw_count, int | float):
            normalized[key] = int(raw_count)
    return normalized


def _string_list(value: Any) -> list[str]:
    """Normalize string sequence values for stable report rendering."""
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str):
            normalized.append(item)
        else:
            normalized.append(str(item))
    return normalized


def _as_float(value: Any) -> float | None:
    """Normalize numeric values for report formatting."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _format_decimal(value: float | None) -> str:
    """Format decimal metrics with a concise fixed precision."""
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def _format_delta(value: float | None) -> str:
    """Format signed decimal deltas."""
    if value is None:
        return "n/a"
    return f"{value:+.3f}"


def _format_ratio(value: float | None) -> str:
    """Format ratio values as percentages."""
    if value is None:
        return "n/a"
    return f"{value * 100.0:.1f}%"


def _format_ratio_delta(value: float | None) -> str:
    """Format ratio deltas in percentage points."""
    if value is None:
        return "n/a"
    return f"{value * 100.0:+.1f} pp"


def _inline_list(values: list[str]) -> str:
    """Render short inline lists for concise report bullets."""
    if not values:
        return "none"
    return ", ".join(f"`{value}`" for value in values)
