"""Tests for worklog.summarizer."""
from datetime import datetime, timezone

from worklog.summarizer import summarize


class TestSummarize:
    def test_basic_counts(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)

        assert s.total_entries == 5
        assert s.by_category["feature"] == 1
        assert s.by_category["bugfix"] == 1
        assert s.by_source["git"] == 2
        assert s.by_source["vscode-copilot"] == 2
        assert s.by_source["manual"] == 1

    def test_repo_counts(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        assert s.by_repo["my-api"] == 4

    def test_top_files(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        assert "src/main.py" in s.top_files

    def test_tags_collected(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        assert "auth" in s.tags_used
        assert "sprint" in s.tags_used

    def test_empty_input(self):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize([], start, end)
        assert s.total_entries == 0
        assert s.entries == []
