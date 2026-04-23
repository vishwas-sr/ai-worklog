"""Tests for worklog.formatters."""
from datetime import datetime, timezone

from worklog.formatters import to_csv, to_html, to_json, to_markdown
from worklog.models import WorkSummary
from worklog.summarizer import summarize


class TestMarkdown:
    def test_basic_output(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        md = to_markdown(s)

        assert "# Work Summary" in md
        assert "**Total items:** 5" in md
        assert "## By Category" in md
        assert "## By Source" in md
        assert "## By Repository" in md
        assert "## Activity Log" in md

    def test_contains_entries(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        md = to_markdown(s)
        assert "Initial commit" in md
        assert "Sprint planning meeting" in md


class TestHTML:
    def test_is_valid_html(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        html = to_html(s)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_escapes_special_chars(self, sample_entries):
        from worklog.models import Source, WorkEntry, Category
        entry = WorkEntry(
            source=Source.MANUAL,
            action='Test <script>alert("xss")</script>',
            category=Category.OTHER,
        )
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize([entry], start, end)
        html = to_html(s)
        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestCSV:
    def test_has_header(self, sample_entries):
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        csv_str = to_csv(s)
        lines = csv_str.strip().splitlines()
        assert lines[0] == "timestamp,source,repo,category,complexity,action,impact,files,tags,collaboration,details,duration_minutes"
        assert len(lines) == 6  # header + 5 entries


class TestJSON:
    def test_valid_json(self, sample_entries):
        import json
        start = datetime(2026, 4, 1, tzinfo=timezone.utc)
        end = datetime(2026, 4, 30, tzinfo=timezone.utc)
        s = summarize(sample_entries, start, end)
        j = to_json(s)
        parsed = json.loads(j)
        assert parsed["total_entries"] == 5
