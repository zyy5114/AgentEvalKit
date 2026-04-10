"""Tests for run fingerprint generation and environment snapshot helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from agent_evalkit import __version__
from agent_evalkit.fingerprint.env_snapshot import (
    collect_environment_snapshot,
    compute_dependencies_hash,
)
from agent_evalkit.fingerprint.fingerprint import (
    generate_run_fingerprint,
    hash_json_payload,
    normalize_run_fingerprint,
)
from agent_evalkit.specs.loader import ScorerSpec


def test_generate_run_fingerprint_populates_required_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Generator should produce a stable payload with all required fields."""
    monkeypatch.setattr(
        "agent_evalkit.fingerprint.fingerprint.collect_environment_snapshot",
        lambda **_: {
            "python_version": "3.11.9",
            "os": "linux-6.8.0",
            "dependencies_hash": "sha256:deps",
        },
    )

    task_spec = {"description": "example", "task_id": "task_1"}
    scorer_config = [{"type": "schema_validity"}]
    fingerprint = generate_run_fingerprint(
        adapter_type="cli",
        adapter_version="1.2.3",
        runner_version="0.1.0",
        seed=123,
        network_enabled=False,
        task_spec=task_spec,
        scorer_config=scorer_config,
        model_id="model-x",
    )

    assert set(fingerprint.keys()) == {
        "schema_version",
        "python_version",
        "os",
        "adapter_type",
        "adapter_version",
        "runner_version",
        "dependencies_hash",
        "seed",
        "network_enabled",
        "task_spec_hash",
        "scorer_config_hash",
        "model_id",
    }
    assert fingerprint["schema_version"] == "1.0"
    assert fingerprint["python_version"] == "3.11.9"
    assert fingerprint["os"] == "linux-6.8.0"
    assert fingerprint["adapter_type"] == "cli"
    assert fingerprint["adapter_version"] == "1.2.3"
    assert fingerprint["runner_version"] == "0.1.0"
    assert fingerprint["dependencies_hash"] == "sha256:deps"
    assert fingerprint["seed"] == 123
    assert fingerprint["network_enabled"] is False
    assert fingerprint["task_spec_hash"] == hash_json_payload(task_spec)
    assert fingerprint["scorer_config_hash"] == hash_json_payload(scorer_config)
    assert fingerprint["model_id"] == "model-x"


def test_generate_run_fingerprint_explicit_missing_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing optional values should remain explicit in normalized output."""
    monkeypatch.setattr(
        "agent_evalkit.fingerprint.fingerprint.collect_environment_snapshot",
        lambda **_: {
            "python_version": None,
            "os": None,
            "dependencies_hash": None,
        },
    )

    fingerprint = generate_run_fingerprint()

    assert fingerprint["runner_version"] == __version__
    assert fingerprint["python_version"] is None
    assert fingerprint["os"] is None
    assert fingerprint["adapter_type"] is None
    assert fingerprint["adapter_version"] is None
    assert fingerprint["dependencies_hash"] is None
    assert fingerprint["seed"] is None
    assert fingerprint["network_enabled"] is None
    assert fingerprint["task_spec_hash"] is None
    assert fingerprint["scorer_config_hash"] is None
    assert fingerprint["model_id"] is None


def test_normalize_run_fingerprint_fills_missing_fields() -> None:
    """Normalization should keep stable shape and explicit null defaults."""
    normalized = normalize_run_fingerprint({"schema_version": "1.0", "adapter_type": "python"})

    assert normalized["schema_version"] == "1.0"
    assert normalized["adapter_type"] == "python"
    assert normalized["python_version"] is None
    assert normalized["os"] is None
    assert normalized["adapter_version"] is None
    assert normalized["runner_version"] is None
    assert normalized["dependencies_hash"] is None
    assert normalized["seed"] is None
    assert normalized["network_enabled"] is None
    assert normalized["task_spec_hash"] is None
    assert normalized["scorer_config_hash"] is None
    assert normalized["model_id"] is None


def test_hash_json_payload_is_stable_across_key_order() -> None:
    """JSON payload hashing should be deterministic for equivalent mappings."""
    left = {"b": 2, "a": 1}
    right = {"a": 1, "b": 2}

    assert hash_json_payload(left) == hash_json_payload(right)


def test_compute_dependencies_hash_uses_local_dependency_metadata(tmp_path: Path) -> None:
    """Dependency hash should include recognized metadata files and contents."""
    pyproject = tmp_path / "pyproject.toml"
    requirements = tmp_path / "requirements.txt"
    pyproject.write_text("[project]\nname = 'agent-evalkit'\n", encoding="utf-8")
    requirements.write_text("typer==0.12.0\n", encoding="utf-8")

    digest = compute_dependencies_hash(project_root=tmp_path)

    expected_hasher = hashlib.sha256()
    for path in sorted([pyproject, requirements], key=lambda item: item.as_posix()):
        expected_hasher.update(path.relative_to(tmp_path).as_posix().encode("utf-8"))
        expected_hasher.update(b"\0")
        expected_hasher.update(path.read_bytes())
        expected_hasher.update(b"\0")
    expected = f"sha256:{expected_hasher.hexdigest()}"

    assert digest == expected


def test_compute_dependencies_hash_returns_none_without_metadata(tmp_path: Path) -> None:
    """Dependency hash should be explicit missing when no metadata files exist."""
    assert compute_dependencies_hash(project_root=tmp_path) is None


def test_collect_environment_snapshot_accepts_explicit_overrides(tmp_path: Path) -> None:
    """Snapshot overrides should take precedence and stay normalized."""
    snapshot = collect_environment_snapshot(
        project_root=tmp_path,
        python_version="3.11.11",
        os_name="linux-6.8.0",
        dependencies_hash="sha256:manual",
    )

    assert snapshot == {
        "python_version": "3.11.11",
        "os": "linux-6.8.0",
        "dependencies_hash": "sha256:manual",
    }


def test_hash_json_payload_returns_none_for_unserializable_values() -> None:
    """Hasher should return explicit missing value when payload is not JSON serializable."""

    class NotJsonSerializable:
        pass

    assert hash_json_payload({"payload": NotJsonSerializable()}) is None


def test_hash_json_payload_handles_pydantic_objects_in_sequences() -> None:
    """Hasher should support scorer configs represented as pydantic model lists."""
    scorer_models = [ScorerSpec(type="schema_validity"), ScorerSpec(type="behavior_compliance")]

    model_hash = hash_json_payload(scorer_models)
    dict_hash = hash_json_payload([{"type": "schema_validity"}, {"type": "behavior_compliance"}])

    assert model_hash is not None
    assert model_hash == dict_hash
