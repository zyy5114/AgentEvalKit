"""Shared pytest fixtures for local deterministic test isolation."""

from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def tmp_path() -> Path:
    """Provide an isolated temporary directory under the test workspace.

    This fixture intentionally stays local to the repository so tests remain
    deterministic in restricted environments.
    """
    root = Path(__file__).resolve().parent / "_tmp_path_runtime"
    root.mkdir(parents=True, exist_ok=True)

    case_dir = root / uuid4().hex
    case_dir.mkdir(parents=True, exist_ok=False)

    try:
        yield case_dir
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)
        if root.exists() and not any(root.iterdir()):
            root.rmdir()
