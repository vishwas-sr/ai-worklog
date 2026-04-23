"""Shared test fixtures."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from worklog.models import Category, Source, WorkEntry
from worklog.storage import DEFAULT_CONFIG


@pytest.fixture()
def tmp_worklog(tmp_path, monkeypatch):
    """Point WORKLOG_DIR at a temporary directory and initialize files."""
    import worklog.storage as storage

    worklog_dir = tmp_path / ".worklog"
    worklog_dir.mkdir()

    sessions = worklog_dir / "sessions.jsonl"
    sessions.touch()

    config = worklog_dir / "config.json"
    config.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")

    monkeypatch.setattr(storage, "WORKLOG_DIR", worklog_dir)
    monkeypatch.setattr(storage, "SESSIONS_FILE", sessions)
    monkeypatch.setattr(storage, "CONFIG_FILE", config)
    monkeypatch.setattr(storage, "_PERMISSIONS_MARKER", worklog_dir / ".permissions_set")

    return worklog_dir


@pytest.fixture()
def sample_entry() -> WorkEntry:
    return WorkEntry(
        source=Source.MANUAL,
        action="Test action",
        category=Category.FEATURE,
        repo="test-repo",
        tags=["python", "test"],
        details="Some details",
    )


@pytest.fixture()
def sample_entries() -> list[WorkEntry]:
    """Return a list of diverse entries for testing."""
    base = datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
    return [
        WorkEntry(
            timestamp=base,
            source=Source.GIT,
            action="Initial commit",
            category=Category.FEATURE,
            repo="my-api",
            files=["src/main.py"],
        ),
        WorkEntry(
            timestamp=base.replace(day=11),
            source=Source.VSCODE_COPILOT,
            action="Fixed auth middleware bug",
            category=Category.BUGFIX,
            repo="my-api",
            tags=["auth"],
        ),
        WorkEntry(
            timestamp=base.replace(day=12),
            source=Source.MANUAL,
            action="Sprint planning meeting",
            category=Category.MEETING,
            tags=["sprint"],
        ),
        WorkEntry(
            timestamp=base.replace(day=13),
            source=Source.GIT,
            action="Refactored database layer",
            category=Category.REFACTOR,
            repo="my-api",
            files=["src/db.py", "tests/test_db.py"],
        ),
        WorkEntry(
            timestamp=base.replace(day=14),
            source=Source.VSCODE_COPILOT,
            action="Added unit tests for auth module",
            category=Category.TEST,
            repo="my-api",
            tags=["test", "auth"],
        ),
    ]
