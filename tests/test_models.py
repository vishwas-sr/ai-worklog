"""Tests for worklog.models."""
from datetime import datetime, timezone
from uuid import UUID

from worklog.models import Category, Source, WorkEntry, WorkSummary


class TestWorkEntry:
    def test_defaults(self):
        entry = WorkEntry(source=Source.MANUAL, action="test")
        assert isinstance(entry.id, UUID)
        assert entry.category == Category.OTHER
        assert entry.files == []
        assert entry.tags == []
        assert entry.repo is None
        assert entry.details is None
        assert entry.duration_minutes is None

    def test_all_fields(self):
        entry = WorkEntry(
            source=Source.GIT,
            action="Added feature",
            category=Category.FEATURE,
            repo="my-repo",
            files=["a.py"],
            tags=["python"],
            details="Details here",
            duration_minutes=30.0,
        )
        assert entry.source == Source.GIT
        assert entry.action == "Added feature"
        assert entry.repo == "my-repo"
        assert entry.duration_minutes == 30.0

    def test_json_roundtrip(self):
        entry = WorkEntry(
            source=Source.VSCODE_COPILOT,
            action="Roundtrip test",
            category=Category.BUGFIX,
        )
        json_str = entry.model_dump_json()
        restored = WorkEntry.model_validate_json(json_str)
        assert restored.id == entry.id
        assert restored.action == entry.action
        assert restored.source == entry.source

    def test_timestamp_is_utc(self):
        entry = WorkEntry(source=Source.MANUAL, action="tz test")
        assert entry.timestamp.tzinfo is not None


class TestEnums:
    def test_source_values(self):
        assert Source.VSCODE_COPILOT.value == "vscode-copilot"
        assert Source.GIT.value == "git"
        assert Source.MANUAL.value == "manual"

    def test_category_values(self):
        assert Category.FEATURE.value == "feature"
        assert Category.BUGFIX.value == "bugfix"
        assert Category.OTHER.value == "other"

    def test_all_categories_exist(self):
        expected = {"feature", "bugfix", "research", "review", "docs",
                    "config", "refactor", "test", "meeting", "other"}
        assert {c.value for c in Category} == expected


class TestWorkSummary:
    def test_defaults(self):
        s = WorkSummary(
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 4, 1, tzinfo=timezone.utc),
        )
        assert s.total_entries == 0
        assert s.by_category == {}
        assert s.entries == []
