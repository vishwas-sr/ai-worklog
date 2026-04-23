"""Tests for worklog.storage."""
import json

from worklog.models import Category, Source, WorkEntry
from worklog.storage import (
    append_entries,
    append_entry,
    deduplicate_entries,
    load_config,
    read_entries,
    save_config,
)


class TestConfig:
    def test_load_default_config(self, tmp_worklog):
        cfg = load_config()
        assert cfg["git_repos"] == []
        assert cfg["enabled"] is True
        assert cfg["auto_commit"] is True

    def test_save_and_load(self, tmp_worklog):
        cfg = load_config()
        cfg["author_email"] = "user@example.com"
        cfg["git_repos"] = ["/path/to/repo"]
        save_config(cfg)

        loaded = load_config()
        assert loaded["author_email"] == "user@example.com"
        assert loaded["git_repos"] == ["/path/to/repo"]

    def test_corrupted_config_returns_defaults(self, tmp_worklog):
        from worklog.storage import CONFIG_FILE
        CONFIG_FILE.write_text("not valid json!!!", encoding="utf-8")
        cfg = load_config()
        assert cfg["git_repos"] == []
        assert cfg["enabled"] is True

    def test_missing_keys_filled_from_defaults(self, tmp_worklog):
        from worklog.storage import CONFIG_FILE
        CONFIG_FILE.write_text('{"git_repos": ["/a"]}', encoding="utf-8")
        cfg = load_config()
        assert cfg["git_repos"] == ["/a"]
        assert cfg["enabled"] is True  # filled from default


class TestAppendAndRead:
    def test_append_and_read_single(self, tmp_worklog, sample_entry):
        append_entry(sample_entry, auto_commit=False)
        entries = read_entries()
        assert len(entries) == 1
        assert entries[0].action == "Test action"

    def test_append_multiple(self, tmp_worklog, sample_entries):
        append_entries(sample_entries)
        entries = read_entries()
        assert len(entries) == 5

    def test_read_filters_by_source(self, tmp_worklog, sample_entries):
        append_entries(sample_entries)
        git_entries = read_entries(source="git")
        assert all(e.source == Source.GIT for e in git_entries)
        assert len(git_entries) == 2

    def test_read_filters_by_category(self, tmp_worklog, sample_entries):
        append_entries(sample_entries)
        bugs = read_entries(category="bugfix")
        assert len(bugs) == 1
        assert bugs[0].category == Category.BUGFIX

    def test_read_filters_by_repo(self, tmp_worklog, sample_entries):
        append_entries(sample_entries)
        api_entries = read_entries(repo="my-api")
        assert len(api_entries) == 4  # 4 with repo='my-api', 1 with repo=None is excluded
        no_repo = [e for e in api_entries if e.repo is None]
        assert len(no_repo) == 0

    def test_read_filters_by_date(self, tmp_worklog, sample_entries):
        from datetime import datetime, timezone
        append_entries(sample_entries)
        start = datetime(2026, 4, 12, tzinfo=timezone.utc)
        entries = read_entries(start=start)
        assert len(entries) == 3

    def test_disabled_blocks_writes(self, tmp_worklog, sample_entry):
        cfg = load_config()
        cfg["enabled"] = False
        save_config(cfg)
        append_entry(sample_entry, auto_commit=False)
        entries = read_entries()
        assert len(entries) == 0

    def test_malformed_lines_skipped(self, tmp_worklog):
        from worklog.storage import SESSIONS_FILE
        entry = WorkEntry(source=Source.MANUAL, action="good")
        SESSIONS_FILE.write_text(
            "this is not json\n"
            + entry.model_dump_json() + "\n"
            + "{bad json\n",
            encoding="utf-8",
        )
        entries = read_entries()
        assert len(entries) == 1
        assert entries[0].action == "good"


class TestDedup:
    def test_dedup_by_id(self, sample_entry):
        duped = [sample_entry, sample_entry]
        unique = deduplicate_entries(duped)
        assert len(unique) == 1

    def test_dedup_preserves_order(self, sample_entries):
        unique = deduplicate_entries(sample_entries + [sample_entries[0]])
        assert len(unique) == 5
        assert unique[0].action == sample_entries[0].action
