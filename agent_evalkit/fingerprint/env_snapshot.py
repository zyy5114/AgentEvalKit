"""Environment snapshot helpers for run fingerprinting."""

from __future__ import annotations

import hashlib
import platform
import sys
from pathlib import Path
from typing import TypedDict

DEPENDENCY_METADATA_FILENAMES: tuple[str, ...] = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
    "Pipfile.lock",
)


class EnvironmentSnapshot(TypedDict):
    """Normalized environment fields used by run fingerprinting."""

    python_version: str | None
    os: str | None
    dependencies_hash: str | None


def collect_environment_snapshot(
    *,
    project_root: str | Path | None = None,
    python_version: str | None = None,
    os_name: str | None = None,
    dependencies_hash: str | None = None,
) -> EnvironmentSnapshot:
    """Collect normalized environment fields with explicit missing values."""
    resolved_root = Path(project_root) if project_root is not None else Path.cwd()
    resolved_python_version = _normalize_optional_string(python_version)
    resolved_os_name = _normalize_optional_string(os_name)
    resolved_dependencies_hash = _normalize_optional_string(dependencies_hash)

    if resolved_python_version is None:
        resolved_python_version = _current_python_version()
    if resolved_os_name is None:
        resolved_os_name = _current_os_name()
    if resolved_dependencies_hash is None:
        resolved_dependencies_hash = compute_dependencies_hash(project_root=resolved_root)

    return {
        "python_version": resolved_python_version,
        "os": resolved_os_name,
        "dependencies_hash": resolved_dependencies_hash,
    }


def compute_dependencies_hash(*, project_root: str | Path | None = None) -> str | None:
    """Return a stable digest from local dependency metadata files when available."""
    root = Path(project_root) if project_root is not None else Path.cwd()
    existing_files = sorted(
        (
            root / filename
            for filename in DEPENDENCY_METADATA_FILENAMES
            if (root / filename).is_file()
        ),
        key=lambda path: path.as_posix(),
    )
    if not existing_files:
        return None

    hasher = hashlib.sha256()
    for file_path in existing_files:
        try:
            file_bytes = file_path.read_bytes()
        except OSError:
            return None

        relative_path = file_path.relative_to(root).as_posix()
        hasher.update(relative_path.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(file_bytes)
        hasher.update(b"\0")

    return f"sha256:{hasher.hexdigest()}"


def _current_python_version() -> str | None:
    """Return current interpreter version in ``major.minor.patch`` format."""
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return _normalize_optional_string(version)


def _current_os_name() -> str | None:
    """Return normalized OS identifier suitable for stable run metadata."""
    system = _normalize_optional_string(platform.system())
    release = _normalize_optional_string(platform.release())
    if system and release:
        return f"{system}-{release}"
    if system:
        return system
    return _normalize_optional_string(platform.platform(terse=True))


def _normalize_optional_string(value: object) -> str | None:
    """Normalize optional string-like inputs and convert blanks to ``None``."""
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized
