"""Run metadata and disk persistence helpers."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

RUN_RECORD_FILENAME = "run_record.json"


class RunRecord(BaseModel):
    """Machine-readable metadata for a single run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1)
    task_hash: str = Field(min_length=1)
    fingerprint_stub: dict[str, Any]
    artifacts_path: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime
    status: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_time_range(self) -> RunRecord:
        """Ensure time range is internally consistent."""
        if self.finished_at < self.started_at:
            raise ValueError("finished_at must be greater than or equal to started_at.")
        return self


def run_dir_for_id(runs_root: str | Path, run_id: str) -> Path:
    """Return the standard run directory path: ``runs/<run_id>/``."""
    return Path(runs_root) / run_id


def build_run_record(
    *,
    run_id: str,
    task_hash: str,
    fingerprint_stub: dict[str, Any],
    runs_root: str | Path = "runs",
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    status: str = "completed",
) -> RunRecord:
    """Build a run record using the v0.1 ``runs/<run_id>/`` layout."""
    started = started_at or datetime.now(tz=UTC)
    finished = finished_at or started
    artifacts_dir = run_dir_for_id(runs_root=runs_root, run_id=run_id)

    return RunRecord(
        run_id=run_id,
        task_hash=task_hash,
        fingerprint_stub=fingerprint_stub,
        artifacts_path=str(artifacts_dir),
        started_at=started,
        finished_at=finished,
        status=status,
    )


def persist_run_record(record: RunRecord) -> Path:
    """Persist a run record as JSON under ``runs/<run_id>/run_record.json``."""
    artifacts_dir = Path(record.artifacts_path)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    record_path = artifacts_dir / RUN_RECORD_FILENAME

    payload = record.model_dump(mode="json")
    record_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return record_path


def load_run_record(path: str | Path) -> RunRecord:
    """Load a persisted run record from a file or run directory path."""
    source = Path(path)
    record_path = source / RUN_RECORD_FILENAME if source.is_dir() else source

    try:
        raw_payload = json.loads(record_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"Run record file not found: {record_path}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read run record file: {record_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in run record file: {record_path}: {exc}") from exc

    if not isinstance(raw_payload, dict):
        actual = type(raw_payload).__name__
        raise ValueError(
            f"Run record root must be a mapping/object in {record_path}, got {actual}."
        )

    try:
        return RunRecord.model_validate(raw_payload)
    except ValidationError as exc:
        raise ValueError(f"Invalid run record in {record_path}: {exc}") from exc
