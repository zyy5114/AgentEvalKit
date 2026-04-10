"""Tests for baseline vs candidate comparison and drift-hint logic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_evalkit.diff.compare import build_drift_hints, compare_run_results


def test_compare_run_results_from_json_files() -> None:
    """Comparator should compute deltas and failure changes from normalized files."""
    baseline = {
        "tasks": [
            {"task_id": "task_a", "passed": True, "score": 1.0, "latency_sec": 1.0},
            {
                "task_id": "task_b",
                "passed": False,
                "score": 0.0,
                "latency_sec": 2.0,
                "violations": [{"type": "missing_trace"}],
            },
            {"task_id": "task_c", "passed": True, "score": 1.0, "latency_sec": 3.0},
        ],
        "fingerprint": {
            "model_id": "model-a",
            "network_enabled": False,
            "seed": 99,
            "dependencies_hash": "sha256:base",
        },
    }
    candidate = {
        "tasks": [
            {"task_id": "task_a", "passed": True, "score": 1.0, "latency_sec": 1.2},
            {"task_id": "task_b", "passed": True, "score": 1.0, "latency_sec": 2.1},
            {
                "task_id": "task_c",
                "passed": False,
                "score": 0.0,
                "latency_sec": 2.7,
                "violations": [{"type": "forbidden_tool_used"}],
            },
            {"task_id": "task_d", "passed": False, "score": 0.0, "latency_sec": 1.0},
        ],
        "fingerprint": {
            "model_id": "model-b",
            "network_enabled": True,
            "seed": None,
            "dependencies_hash": "sha256:candidate",
        },
    }

    diff = compare_run_results(baseline, candidate)

    assert diff["baseline_task_count"] == 3
    assert diff["candidate_task_count"] == 4
    assert diff["shared_task_count"] == 3
    assert diff["baseline_only_tasks"] == []
    assert diff["candidate_only_tasks"] == ["task_d"]

    assert diff["success_rate"]["baseline"] == pytest.approx(2.0 / 3.0)
    assert diff["success_rate"]["candidate"] == pytest.approx(2.0 / 4.0)
    assert diff["success_rate"]["delta"] == pytest.approx((2.0 / 4.0) - (2.0 / 3.0))

    assert diff["score"]["baseline"] == pytest.approx((1.0 + 0.0 + 1.0) / 3.0)
    assert diff["score"]["candidate"] == pytest.approx((1.0 + 1.0 + 0.0 + 0.0) / 4.0)
    assert diff["score"]["delta"] == pytest.approx(((1.0 + 1.0 + 0.0 + 0.0) / 4.0) - 2.0 / 3.0)

    assert diff["latency_sec"]["baseline"] == pytest.approx((1.0 + 2.0 + 3.0) / 3.0)
    assert diff["latency_sec"]["candidate"] == pytest.approx((1.2 + 2.1 + 2.7 + 1.0) / 4.0)
    assert diff["latency_sec"]["delta"] == pytest.approx(
        ((1.2 + 2.1 + 2.7 + 1.0) / 4.0) - ((1.0 + 2.0 + 3.0) / 3.0)
    )

    changed = diff["changed_failure_cases"]
    assert changed["pass_to_fail"] == ["task_c"]
    assert changed["fail_to_pass"] == ["task_b"]
    assert changed["violation_type_changes"] == [
        {"task_id": "task_b", "baseline": ["missing_trace"], "candidate": []},
        {"task_id": "task_c", "baseline": [], "candidate": ["forbidden_tool_used"]},
    ]

    violations = diff["violations_distribution"]
    assert violations["baseline"] == {"missing_trace": 1}
    assert violations["candidate"] == {"forbidden_tool_used": 1}
    assert violations["delta"] == {"forbidden_tool_used": 1, "missing_trace": -1}

    assert "model_id changed (model-a -> model-b)" in diff["drift_hints"]
    assert "network_enabled changed (False -> True)" in diff["drift_hints"]
    assert "seed unset in candidate" in diff["drift_hints"]
    assert "dependencies hash changed" in diff["drift_hints"]


def test_compare_run_results_supports_run_directories(tmp_path: Path) -> None:
    """Comparator should load summary and fingerprint from run result directories."""
    baseline_dir = tmp_path / "baseline"
    candidate_dir = tmp_path / "candidate"
    baseline_dir.mkdir()
    candidate_dir.mkdir()

    (baseline_dir / "summary.json").write_text(
        json.dumps(
            {
                "tasks": {"task_x": {"passed": True, "score": 1.0, "latency_sec": 1.0}},
            }
        ),
        encoding="utf-8",
    )
    (baseline_dir / "fingerprint.json").write_text(
        json.dumps(
            {
                "model_id": "fixed-model",
                "network_enabled": False,
                "seed": 7,
                "dependencies_hash": "sha256:same",
            }
        ),
        encoding="utf-8",
    )

    (candidate_dir / "results.json").write_text(
        json.dumps(
            {
                "tasks": {"task_x": {"passed": False, "score": 0.0, "latency_sec": 1.5}},
            }
        ),
        encoding="utf-8",
    )
    (candidate_dir / "fingerprint.json").write_text(
        json.dumps(
            {
                "model_id": "fixed-model",
                "network_enabled": False,
                "seed": 7,
                "dependencies_hash": "sha256:same",
            }
        ),
        encoding="utf-8",
    )

    diff = compare_run_results(baseline_dir, candidate_dir)

    assert diff["baseline_source"] == str(baseline_dir)
    assert diff["candidate_source"] == str(candidate_dir)
    assert diff["changed_failure_cases"]["pass_to_fail"] == ["task_x"]
    assert diff["drift_hints"] == []


def test_build_drift_hints_handles_unset_seed_in_both() -> None:
    """Drift hints should surface explicit seed-unset signal when both are missing."""
    hints = build_drift_hints(
        baseline_fingerprint={"seed": None},
        candidate_fingerprint={"seed": None},
    )

    assert hints == ["seed unset in both baseline and candidate"]


def test_compare_run_results_supports_task_results_mapping_shape() -> None:
    """Comparator should normalize mapping-based task containers and nested violations."""
    baseline = {
        "task_results": {
            "task_x": {
                "status": "completed",
                "score": 1.0,
                "latency_sec": 0.2,
            }
        }
    }
    candidate = {
        "results": {
            "task_x": {
                "status": "failed",
                "scorer_results": {
                    "behavior_compliance": {
                        "violations": {"missing_trace": 2},
                    }
                },
                "metrics": {"duration_sec": 0.3},
            }
        }
    }

    diff = compare_run_results(baseline, candidate)

    assert diff["changed_failure_cases"]["pass_to_fail"] == ["task_x"]
    assert diff["violations_distribution"]["candidate"] == {"missing_trace": 2}
    assert diff["latency_sec"]["baseline"] == pytest.approx(0.2)
    assert diff["latency_sec"]["candidate"] == pytest.approx(0.3)


def test_compare_run_results_rejects_missing_source_path(tmp_path: Path) -> None:
    """Comparator should fail clearly when a file/directory source does not exist."""
    missing_path = tmp_path / "missing-result.json"

    with pytest.raises(ValueError, match="Run result source not found"):
        compare_run_results(missing_path, missing_path)
