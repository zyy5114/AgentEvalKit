"""Tests for Markdown regression report generation."""

from __future__ import annotations

from agent_evalkit.reports.markdown_report import render_regression_markdown


def test_render_regression_markdown_includes_required_sections() -> None:
    """Renderer should include concise sections with required regression signals."""
    diff_payload = {
        "baseline_source": "runs/base",
        "candidate_source": "runs/candidate",
        "baseline_task_count": 3,
        "candidate_task_count": 4,
        "shared_task_count": 3,
        "success_rate": {"baseline": 2.0 / 3.0, "candidate": 0.5, "delta": -1.0 / 6.0},
        "score": {"baseline": 2.0 / 3.0, "candidate": 0.5, "delta": -1.0 / 6.0},
        "latency_sec": {"baseline": 2.0, "candidate": 1.75, "delta": -0.25},
        "changed_failure_cases": {
            "pass_to_fail": ["task_c"],
            "fail_to_pass": ["task_b"],
            "violation_type_changes": [
                {"task_id": "task_c", "baseline": [], "candidate": ["forbidden_tool_used"]}
            ],
        },
        "violations_distribution": {
            "baseline": {"missing_trace": 1},
            "candidate": {"forbidden_tool_used": 1},
            "delta": {"forbidden_tool_used": 1, "missing_trace": -1},
        },
        "drift_hints": [
            "model_id changed (model-a -> model-b)",
            "network_enabled changed (False -> True)",
            "seed unset in candidate",
            "dependencies hash changed",
        ],
    }

    report = render_regression_markdown(diff_payload)

    assert "# AgentEvalKit Regression Report" in report
    assert "## Summary" in report
    assert "## Metric Deltas" in report
    assert "## Changed Failure Cases" in report
    assert "## Violation Distribution" in report
    assert "## Drift Hints" in report

    assert "| Success rate | 66.7% | 50.0% | -16.7 pp |" in report
    assert "| Score | 0.667 | 0.500 | -0.167 |" in report
    assert "| Latency (sec) | 2.000 | 1.750 | -0.250 |" in report

    assert "- `pass -> fail`: `task_c`" in report
    assert "- `fail -> pass`: `task_b`" in report
    assert "`task_c`: none -> `forbidden_tool_used`" in report

    assert "| `missing_trace` | 1 | 0 | -1 |" in report
    assert "| `forbidden_tool_used` | 0 | 1 | +1 |" in report
    assert "- model_id changed (model-a -> model-b)" in report


def test_render_regression_markdown_handles_missing_optional_metrics() -> None:
    """Renderer should show n/a for unavailable metrics and concise empty sections."""
    diff_payload = {
        "baseline_source": "base.json",
        "candidate_source": "candidate.json",
        "baseline_task_count": 1,
        "candidate_task_count": 1,
        "shared_task_count": 1,
        "success_rate": {"baseline": 1.0, "candidate": 1.0, "delta": 0.0},
        "score": {"baseline": None, "candidate": None, "delta": None},
        "latency_sec": {"baseline": None, "candidate": None, "delta": None},
        "changed_failure_cases": {
            "pass_to_fail": [],
            "fail_to_pass": [],
            "violation_type_changes": [],
        },
        "violations_distribution": {"baseline": {}, "candidate": {}, "delta": {}},
        "drift_hints": [],
    }

    report = render_regression_markdown(diff_payload)

    assert "| Score | n/a | n/a | n/a |" in report
    assert "| Latency (sec) | n/a | n/a | n/a |" in report
    assert "- `pass -> fail`: none" in report
    assert "- `fail -> pass`: none" in report
    assert "- `violation type changes`: none" in report
    assert "## Violation Distribution\n- none" in report
    assert "## Drift Hints\n- none" in report
