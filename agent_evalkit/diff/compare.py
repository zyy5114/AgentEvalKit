"""Baseline versus candidate comparison for v0.1 regression diffs."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

SUMMARY_CANDIDATE_FILENAMES: tuple[str, ...] = (
    "summary.json",
    "results.json",
    "run_results.json",
    "normalized_results.json",
)
FINGERPRINT_FILENAME = "fingerprint.json"


class NormalizedTaskResult(TypedDict):
    """Normalized per-task result shape used for diff computation."""

    task_id: str
    passed: bool
    score: float | None
    latency_sec: float | None
    violation_types: list[str]


class NormalizedRunResult(TypedDict):
    """Normalized run result shape used for baseline/candidate comparison."""

    source: str
    tasks: dict[str, NormalizedTaskResult]
    fingerprint: dict[str, Any]


class MetricDelta(TypedDict):
    """Simple numeric delta payload."""

    baseline: float | None
    candidate: float | None
    delta: float | None


class ChangedViolationTypes(TypedDict):
    """Violation-type change payload for one task."""

    task_id: str
    baseline: list[str]
    candidate: list[str]


class ChangedFailureCases(TypedDict):
    """Changed failure-case categories for shared tasks."""

    pass_to_fail: list[str]
    fail_to_pass: list[str]
    violation_type_changes: list[ChangedViolationTypes]


class ViolationDistributionDelta(TypedDict):
    """Violation-type distribution and delta payload."""

    baseline: dict[str, int]
    candidate: dict[str, int]
    delta: dict[str, int]


class RunComparison(TypedDict):
    """Normalized diff output for v0.1 baseline/candidate comparisons."""

    baseline_source: str
    candidate_source: str
    baseline_task_count: int
    candidate_task_count: int
    shared_task_count: int
    baseline_only_tasks: list[str]
    candidate_only_tasks: list[str]
    success_rate: MetricDelta
    score: MetricDelta
    latency_sec: MetricDelta
    changed_failure_cases: ChangedFailureCases
    violations_distribution: ViolationDistributionDelta
    drift_hints: list[str]


def compare_run_results(
    baseline: str | Path | Mapping[str, Any],
    candidate: str | Path | Mapping[str, Any],
) -> RunComparison:
    """Compare baseline and candidate run results from files, directories, or mappings."""
    baseline_result = load_run_result(baseline)
    candidate_result = load_run_result(candidate)
    return compare_normalized_results(
        baseline_result=baseline_result,
        candidate_result=candidate_result,
    )


def load_run_result(source: str | Path | Mapping[str, Any]) -> NormalizedRunResult:
    """Load and normalize run results from a mapping, JSON file, or run directory."""
    if isinstance(source, Mapping):
        return _normalize_run_payload(payload=dict(source), source_label="<in-memory>")

    source_path = Path(source)
    if source_path.is_file():
        payload = _load_json_file(source_path)
        return _normalize_run_payload(payload=payload, source_label=str(source_path))

    if source_path.is_dir():
        summary_path = _discover_summary_file(source_path)
        payload = _load_json_file(summary_path)
        normalized = _normalize_run_payload(payload=payload, source_label=str(source_path))

        if not normalized["fingerprint"]:
            fingerprint_path = source_path / FINGERPRINT_FILENAME
            if fingerprint_path.is_file():
                raw_fingerprint = _load_json_file(fingerprint_path)
                if isinstance(raw_fingerprint, Mapping):
                    normalized["fingerprint"] = dict(raw_fingerprint)
        return normalized

    raise ValueError(f"Run result source not found: {source_path}")


def compare_normalized_results(
    *,
    baseline_result: NormalizedRunResult,
    candidate_result: NormalizedRunResult,
) -> RunComparison:
    """Compare two normalized run results and return machine-readable regression diff."""
    baseline_tasks = baseline_result["tasks"]
    candidate_tasks = candidate_result["tasks"]

    baseline_task_ids = set(baseline_tasks.keys())
    candidate_task_ids = set(candidate_tasks.keys())
    shared_task_ids = sorted(baseline_task_ids & candidate_task_ids)
    baseline_only_tasks = sorted(baseline_task_ids - candidate_task_ids)
    candidate_only_tasks = sorted(candidate_task_ids - baseline_task_ids)

    success_rate = {
        "baseline": _fraction_true([task["passed"] for task in baseline_tasks.values()]),
        "candidate": _fraction_true([task["passed"] for task in candidate_tasks.values()]),
        "delta": None,
    }
    if success_rate["baseline"] is not None and success_rate["candidate"] is not None:
        success_rate["delta"] = success_rate["candidate"] - success_rate["baseline"]

    score = {
        "baseline": _mean([task["score"] for task in baseline_tasks.values()]),
        "candidate": _mean([task["score"] for task in candidate_tasks.values()]),
        "delta": None,
    }
    if score["baseline"] is not None and score["candidate"] is not None:
        score["delta"] = score["candidate"] - score["baseline"]

    latency = {
        "baseline": _mean([task["latency_sec"] for task in baseline_tasks.values()]),
        "candidate": _mean([task["latency_sec"] for task in candidate_tasks.values()]),
        "delta": None,
    }
    if latency["baseline"] is not None and latency["candidate"] is not None:
        latency["delta"] = latency["candidate"] - latency["baseline"]

    pass_to_fail: list[str] = []
    fail_to_pass: list[str] = []
    violation_type_changes: list[ChangedViolationTypes] = []

    for task_id in shared_task_ids:
        baseline_task = baseline_tasks[task_id]
        candidate_task = candidate_tasks[task_id]

        if baseline_task["passed"] and not candidate_task["passed"]:
            pass_to_fail.append(task_id)
        if not baseline_task["passed"] and candidate_task["passed"]:
            fail_to_pass.append(task_id)

        baseline_violations = sorted(set(baseline_task["violation_types"]))
        candidate_violations = sorted(set(candidate_task["violation_types"]))
        if baseline_violations != candidate_violations and (
            baseline_violations or candidate_violations
        ):
            violation_type_changes.append(
                {
                    "task_id": task_id,
                    "baseline": baseline_violations,
                    "candidate": candidate_violations,
                }
            )

    baseline_violation_counts = _violation_type_counts(baseline_tasks)
    candidate_violation_counts = _violation_type_counts(candidate_tasks)
    all_violation_types = sorted(set(baseline_violation_counts) | set(candidate_violation_counts))
    violation_delta = {
        violation_type: candidate_violation_counts.get(violation_type, 0)
        - baseline_violation_counts.get(violation_type, 0)
        for violation_type in all_violation_types
    }

    drift_hints = build_drift_hints(
        baseline_fingerprint=baseline_result["fingerprint"],
        candidate_fingerprint=candidate_result["fingerprint"],
    )

    return {
        "baseline_source": baseline_result["source"],
        "candidate_source": candidate_result["source"],
        "baseline_task_count": len(baseline_tasks),
        "candidate_task_count": len(candidate_tasks),
        "shared_task_count": len(shared_task_ids),
        "baseline_only_tasks": baseline_only_tasks,
        "candidate_only_tasks": candidate_only_tasks,
        "success_rate": success_rate,
        "score": score,
        "latency_sec": latency,
        "changed_failure_cases": {
            "pass_to_fail": pass_to_fail,
            "fail_to_pass": fail_to_pass,
            "violation_type_changes": violation_type_changes,
        },
        "violations_distribution": {
            "baseline": dict(baseline_violation_counts),
            "candidate": dict(candidate_violation_counts),
            "delta": violation_delta,
        },
        "drift_hints": drift_hints,
    }


def build_drift_hints(
    *,
    baseline_fingerprint: Mapping[str, Any] | None,
    candidate_fingerprint: Mapping[str, Any] | None,
) -> list[str]:
    """Generate concise drift hints from fingerprint field differences."""
    baseline = dict(baseline_fingerprint or {})
    candidate = dict(candidate_fingerprint or {})
    hints: list[str] = []

    baseline_model = _normalized_string(baseline.get("model_id"))
    candidate_model = _normalized_string(candidate.get("model_id"))
    if baseline_model != candidate_model and baseline_model and candidate_model:
        hints.append(f"model_id changed ({baseline_model} -> {candidate_model})")

    baseline_network = _optional_bool(baseline.get("network_enabled"))
    candidate_network = _optional_bool(candidate.get("network_enabled"))
    if baseline_network != candidate_network:
        hints.append(f"network_enabled changed ({baseline_network!s} -> {candidate_network!s})")

    baseline_seed = baseline.get("seed")
    candidate_seed = candidate.get("seed")
    if baseline_seed is None and candidate_seed is None:
        hints.append("seed unset in both baseline and candidate")
    elif baseline_seed is not None and candidate_seed is None:
        hints.append("seed unset in candidate")
    elif baseline_seed is None and candidate_seed is not None:
        hints.append("seed set in candidate (baseline unset)")

    baseline_deps = _normalized_string(baseline.get("dependencies_hash"))
    candidate_deps = _normalized_string(candidate.get("dependencies_hash"))
    if baseline_deps != candidate_deps and baseline_deps and candidate_deps:
        hints.append("dependencies hash changed")

    return hints


def _normalize_run_payload(*, payload: Any, source_label: str) -> NormalizedRunResult:
    """Normalize a raw run payload to the internal comparison shape."""
    if not isinstance(payload, Mapping):
        actual = type(payload).__name__
        raise ValueError(
            f"Run result payload must be a JSON object in {source_label}, got {actual}."
        )

    raw_tasks = _extract_raw_tasks(payload=payload, source_label=source_label)
    tasks: dict[str, NormalizedTaskResult] = {}
    for task_index, raw_task in enumerate(raw_tasks):
        task_id = _extract_task_id(raw_task=raw_task, index=task_index)
        tasks[task_id] = _normalize_task(task_id=task_id, raw_task=raw_task)

    raw_fingerprint = payload.get("fingerprint")
    normalized_fingerprint = dict(raw_fingerprint) if isinstance(raw_fingerprint, Mapping) else {}

    return {
        "source": source_label,
        "tasks": dict(sorted(tasks.items(), key=lambda item: item[0])),
        "fingerprint": normalized_fingerprint,
    }


def _extract_raw_tasks(*, payload: Mapping[str, Any], source_label: str) -> list[Any]:
    """Extract task result entries from known v0.1 container keys."""
    for key in ("tasks", "task_results", "results"):
        if key not in payload:
            continue
        value = payload[key]
        if isinstance(value, Mapping):
            return [dict(task_data, task_id=task_id) for task_id, task_data in value.items()]
        if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
            return list(value)
        raise ValueError(f"Run result field '{key}' must be a list or mapping in {source_label}.")

    raise ValueError(
        f"Run result in {source_label} must include one of: tasks, task_results, results."
    )


def _extract_task_id(*, raw_task: Any, index: int) -> str:
    """Resolve a stable task_id from a task result entry."""
    if isinstance(raw_task, Mapping):
        task_id = _normalized_string(raw_task.get("task_id"))
        if task_id:
            return task_id
    return f"task_{index}"


def _normalize_task(*, task_id: str, raw_task: Any) -> NormalizedTaskResult:
    """Normalize one task result for downstream diff logic."""
    task_mapping = dict(raw_task) if isinstance(raw_task, Mapping) else {}
    violations = _extract_violation_types(task_mapping)
    return {
        "task_id": task_id,
        "passed": _extract_passed(task_mapping, violations=violations),
        "score": _extract_score(task_mapping),
        "latency_sec": _extract_latency_sec(task_mapping),
        "violation_types": violations,
    }


def _extract_passed(task: Mapping[str, Any], *, violations: list[str]) -> bool:
    """Extract boolean pass/fail with conservative deterministic fallbacks."""
    for key in ("passed", "success", "succeeded"):
        value = task.get(key)
        if isinstance(value, bool):
            return value

    status = _normalized_string(task.get("status"))
    if status is not None:
        if status in {"passed", "pass", "succeeded", "success", "ok", "completed"}:
            return True
        if status in {"failed", "fail", "error", "timeout"}:
            return False

    for key in ("schema_validity", "behavior_compliance", "result"):
        nested = task.get(key)
        if isinstance(nested, Mapping):
            nested_passed = nested.get("passed")
            if isinstance(nested_passed, bool):
                return nested_passed

    if violations:
        return False

    score = _extract_score(task)
    if score is not None:
        return score >= 1.0

    return False


def _extract_score(task: Mapping[str, Any]) -> float | None:
    """Extract a comparable score for one task."""
    direct_score = _optional_float(task.get("score"))
    if direct_score is not None:
        return direct_score

    scores: list[float] = []
    for key in ("schema_validity", "behavior_compliance", "result"):
        nested = task.get(key)
        if isinstance(nested, Mapping):
            nested_score = _optional_float(nested.get("score"))
            if nested_score is not None:
                scores.append(nested_score)

    for key in ("scorer_results", "scores", "scorers"):
        nested = task.get(key)
        if isinstance(nested, Mapping):
            for value in nested.values():
                if isinstance(value, Mapping):
                    nested_score = _optional_float(value.get("score"))
                    if nested_score is not None:
                        scores.append(nested_score)
        elif isinstance(nested, Sequence) and not isinstance(nested, str | bytes | bytearray):
            for item in nested:
                if isinstance(item, Mapping):
                    nested_score = _optional_float(item.get("score"))
                    if nested_score is not None:
                        scores.append(nested_score)

    return _mean(scores)


def _extract_latency_sec(task: Mapping[str, Any]) -> float | None:
    """Extract task latency in seconds when available."""
    for key in ("latency_sec", "elapsed_sec", "duration_sec"):
        value = _optional_float(task.get(key))
        if value is not None:
            return value

    metrics = task.get("metrics")
    if isinstance(metrics, Mapping):
        for key in ("latency_sec", "elapsed_sec", "duration_sec"):
            value = _optional_float(metrics.get(key))
            if value is not None:
                return value

    return None


def _extract_violation_types(task: Mapping[str, Any]) -> list[str]:
    """Extract normalized violation types for one task."""
    collected: list[str] = []
    for key in ("violations", "behavior_violations"):
        collected.extend(_violation_types_from_value(task.get(key)))

    for key in ("behavior", "behavior_compliance", "behavior_result"):
        nested = task.get(key)
        if isinstance(nested, Mapping):
            collected.extend(_violation_types_from_value(nested.get("violations")))

    scorer_results = task.get("scorer_results")
    if isinstance(scorer_results, Mapping):
        for scorer_payload in scorer_results.values():
            if isinstance(scorer_payload, Mapping):
                collected.extend(_violation_types_from_value(scorer_payload.get("violations")))
    elif isinstance(scorer_results, Sequence) and not isinstance(
        scorer_results, str | bytes | bytearray
    ):
        for scorer_payload in scorer_results:
            if isinstance(scorer_payload, Mapping):
                collected.extend(_violation_types_from_value(scorer_payload.get("violations")))

    return sorted(collected)


def _violation_types_from_value(value: Any) -> list[str]:
    """Normalize violation-type entries from common list/map representations."""
    if value is None:
        return []
    if isinstance(value, Mapping):
        types: list[str] = []
        for raw_type, count in value.items():
            violation_type = _normalized_string(raw_type)
            if not violation_type:
                continue
            repetitions = 1
            if isinstance(count, int) and count > 0:
                repetitions = count
            types.extend([violation_type] * repetitions)
        return types
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        normalized: list[str] = []
        for item in value:
            if isinstance(item, str):
                item_type = _normalized_string(item)
            elif isinstance(item, Mapping):
                item_type = _normalized_string(item.get("type"))
            else:
                item_type = None
            if item_type:
                normalized.append(item_type)
        return normalized
    return []


def _violation_type_counts(tasks: Mapping[str, NormalizedTaskResult]) -> Counter[str]:
    """Count violation type occurrences across tasks."""
    counts: Counter[str] = Counter()
    for task in tasks.values():
        counts.update(task["violation_types"])
    return counts


def _discover_summary_file(run_dir: Path) -> Path:
    """Find the normalized result file in a run directory using known filenames."""
    for filename in SUMMARY_CANDIDATE_FILENAMES:
        candidate = run_dir / filename
        if candidate.is_file():
            return candidate
    supported = ", ".join(SUMMARY_CANDIDATE_FILENAMES)
    raise ValueError(
        f"Could not find normalized result file under {run_dir}. Checked: {supported}."
    )


def _load_json_file(path: Path) -> Any:
    """Load a JSON file with clear errors for parse/read failures."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"JSON file not found: {path}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read JSON file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _fraction_true(values: Sequence[bool]) -> float | None:
    """Return share of true values in a sequence."""
    if not values:
        return None
    return sum(1.0 for value in values if value) / float(len(values))


def _mean(values: Sequence[float | None]) -> float | None:
    """Return mean across non-null values."""
    numeric_values = [value for value in values if value is not None]
    if not numeric_values:
        return None
    return sum(numeric_values) / float(len(numeric_values))


def _optional_float(value: Any) -> float | None:
    """Coerce numeric values into float for stable metric comparisons."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_bool(value: Any) -> bool | None:
    """Normalize optional bool-like values."""
    if isinstance(value, bool):
        return value
    return None


def _normalized_string(value: Any) -> str | None:
    """Normalize optional string values and collapse blanks to ``None``."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized
