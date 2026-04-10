"""Tests for run record metadata and JSON persistence."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from agent_evalkit.runners import (
    RUN_RECORD_FILENAME,
    RunRecord,
    build_run_record,
    load_run_record,
    persist_run_record,
)


def test_build_run_record_sets_runs_layout_fields(tmp_path: Path) -> None:
    """Builder should set required fields and runs/<run_id>/ artifact path."""
    runs_root = tmp_path / "runs"
    started = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    finished = datetime(2026, 1, 1, 0, 1, tzinfo=UTC)

    record = build_run_record(
        run_id="run_001",
        task_hash="task_hash_abc",
        fingerprint_stub={"model_id": "fake-model", "seed": 42},
        runs_root=runs_root,
        started_at=started,
        finished_at=finished,
        status="succeeded",
    )

    assert isinstance(record, RunRecord)
    assert record.run_id == "run_001"
    assert record.task_hash == "task_hash_abc"
    assert record.fingerprint_stub["model_id"] == "fake-model"
    assert Path(record.artifacts_path) == runs_root / "run_001"
    assert record.started_at == started
    assert record.finished_at == finished
    assert record.status == "succeeded"


def test_persist_run_record_writes_json_under_run_directory(tmp_path: Path) -> None:
    """Persistence should write run_record.json under runs/<run_id>/."""
    record = build_run_record(
        run_id="run_002",
        task_hash="task_hash_xyz",
        fingerprint_stub={"python_version": "3.11.0"},
        runs_root=tmp_path / "runs",
        started_at=datetime(2026, 1, 1, 1, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 1, 2, tzinfo=UTC),
        status="failed",
    )

    record_path = persist_run_record(record)
    payload = json.loads(record_path.read_text(encoding="utf-8"))

    assert record_path.name == RUN_RECORD_FILENAME
    assert record_path.parent == Path(record.artifacts_path)
    assert payload["run_id"] == "run_002"
    assert payload["task_hash"] == "task_hash_xyz"
    assert payload["fingerprint_stub"]["python_version"] == "3.11.0"
    assert payload["status"] == "failed"


def test_load_run_record_round_trips_from_run_directory(tmp_path: Path) -> None:
    """Loader should support loading from a run directory path."""
    runs_root = tmp_path / "runs"
    record = build_run_record(
        run_id="run_003",
        task_hash="task_hash_003",
        fingerprint_stub={"network_enabled": False},
        runs_root=runs_root,
        started_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        finished_at=datetime(2026, 1, 1, 2, 0, tzinfo=UTC),
        status="completed",
    )
    persist_run_record(record)

    loaded = load_run_record(runs_root / "run_003")

    assert loaded.model_dump() == record.model_dump()


def test_load_run_record_fails_for_invalid_payload(tmp_path: Path) -> None:
    """Loader should raise a clear error when required fields are missing."""
    record_path = tmp_path / RUN_RECORD_FILENAME
    record_path.write_text('{"run_id": "missing_fields"}', encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid run record"):
        load_run_record(record_path)


def test_load_run_record_fails_when_file_missing(tmp_path: Path) -> None:
    """Loader should raise a clear error for missing run record files."""
    missing_path = tmp_path / "missing_run_record.json"

    with pytest.raises(ValueError, match="Run record file not found"):
        load_run_record(missing_path)


def test_run_record_rejects_finished_before_started() -> None:
    """Model validation should reject inverted timestamp ranges."""
    with pytest.raises(ValueError, match="finished_at must be greater than or equal"):
        build_run_record(
            run_id="run_004",
            task_hash="task_hash_004",
            fingerprint_stub={},
            started_at=datetime(2026, 1, 1, 5, 0, tzinfo=UTC),
            finished_at=datetime(2026, 1, 1, 4, 59, tzinfo=UTC),
            status="failed",
        )
