"""Run fingerprint generation and normalization helpers."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from agent_evalkit import __version__
from agent_evalkit.fingerprint.env_snapshot import collect_environment_snapshot

FINGERPRINT_SCHEMA_VERSION = "1.0"


class RunFingerprint(BaseModel):
    """Stable, JSON-serializable run fingerprint payload."""

    model_config = ConfigDict(extra="forbid")

    schema_version: str = FINGERPRINT_SCHEMA_VERSION
    python_version: str | None = None
    os: str | None = None
    adapter_type: str | None = None
    adapter_version: str | None = None
    runner_version: str | None = None
    dependencies_hash: str | None = None
    seed: int | str | None = None
    network_enabled: bool | None = None
    task_spec_hash: str | None = None
    scorer_config_hash: str | None = None
    model_id: str | None = None


def generate_run_fingerprint(
    *,
    adapter_type: str | None = None,
    adapter_version: str | None = None,
    runner_version: str | None = None,
    dependencies_hash: str | None = None,
    seed: int | str | None = None,
    network_enabled: bool | None = None,
    task_spec: Any = None,
    scorer_config: Any = None,
    task_spec_hash: str | None = None,
    scorer_config_hash: str | None = None,
    model_id: str | None = None,
    project_root: str | Path | None = None,
    python_version: str | None = None,
    os_name: str | None = None,
) -> dict[str, Any]:
    """Generate a normalized run fingerprint with explicit missing fields."""
    env_snapshot = collect_environment_snapshot(
        project_root=project_root,
        python_version=python_version,
        os_name=os_name,
        dependencies_hash=dependencies_hash,
    )

    resolved_task_spec_hash = _normalize_optional_string(task_spec_hash)
    if resolved_task_spec_hash is None:
        resolved_task_spec_hash = hash_json_payload(task_spec)

    resolved_scorer_config_hash = _normalize_optional_string(scorer_config_hash)
    if resolved_scorer_config_hash is None:
        resolved_scorer_config_hash = hash_json_payload(scorer_config)

    fingerprint = RunFingerprint(
        python_version=env_snapshot["python_version"],
        os=env_snapshot["os"],
        adapter_type=_normalize_optional_string(adapter_type),
        adapter_version=_normalize_optional_string(adapter_version),
        runner_version=_normalize_optional_string(runner_version) or __version__,
        dependencies_hash=env_snapshot["dependencies_hash"],
        seed=seed,
        network_enabled=network_enabled,
        task_spec_hash=resolved_task_spec_hash,
        scorer_config_hash=resolved_scorer_config_hash,
        model_id=_normalize_optional_string(model_id),
    )
    return fingerprint.model_dump(mode="json")


def normalize_run_fingerprint(raw_fingerprint: Any) -> dict[str, Any]:
    """Validate and normalize a fingerprint payload into the stable structure."""
    return RunFingerprint.model_validate(raw_fingerprint).model_dump(mode="json")


def hash_json_payload(payload: Any) -> str | None:
    """Build a stable content hash from JSON-serializable payloads."""
    if payload is None:
        return None

    normalized_payload = _coerce_json_payload(payload)
    try:
        canonical_json = json.dumps(
            normalized_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError):
        return None

    digest = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _coerce_json_payload(payload: Any) -> Any:
    """Convert pydantic models and other objects to JSON-ready values."""
    model_dump = getattr(payload, "model_dump", None)
    if callable(model_dump):
        return _coerce_json_payload(model_dump(mode="json"))
    if isinstance(payload, Mapping):
        return {str(key): _coerce_json_payload(value) for key, value in payload.items()}
    if isinstance(payload, Sequence) and not isinstance(payload, str | bytes | bytearray):
        return [_coerce_json_payload(item) for item in payload]
    return payload


def _normalize_optional_string(value: object) -> str | None:
    """Normalize optional string-like values and blanks."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized
