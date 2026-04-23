"""Tests for worklog CLI commands."""
from __future__ import annotations

import json

from click.testing import CliRunner

from worklog.cli import main
from worklog.storage import DEFAULT_CONFIG


def _setup_worklog(tmp_path, monkeypatch):
    """Set up a temp worklog dir and patch storage module."""
    import worklog.storage as storage

    d = tmp_path / ".worklog"
    d.mkdir()
    (d / "sessions.jsonl").touch()
    (d / "config.json").write_text(json.dumps(DEFAULT_CONFIG, indent=2))

    monkeypatch.setattr(storage, "WORKLOG_DIR", d)
    monkeypatch.setattr(storage, "SESSIONS_FILE", d / "sessions.jsonl")
    monkeypatch.setattr(storage, "CONFIG_FILE", d / "config.json")
    monkeypatch.setattr(storage, "_PERMISSIONS_MARKER", d / ".permissions_set")
    return d


class TestInit:
    def test_init(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Worklog initialized" in result.output


class TestStatus:
    def test_status_enabled(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "enabled" in result.output


class TestDisableEnable:
    def test_disable_then_enable(self, tmp_path, monkeypatch):
        d = _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()

        result = runner.invoke(main, ["disable"])
        assert result.exit_code == 0
        assert "disabled" in result.output.lower()

        cfg = json.loads((d / "config.json").read_text())
        assert cfg["enabled"] is False

        result = runner.invoke(main, ["enable"])
        assert result.exit_code == 0
        assert "enabled" in result.output.lower()

        cfg = json.loads((d / "config.json").read_text())
        assert cfg["enabled"] is True


class TestLog:
    def test_log_entry(self, tmp_path, monkeypatch):
        d = _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["log", "Did something", "-c", "feature"])
        assert result.exit_code == 0
        assert "Logged" in result.output

        lines = (d / "sessions.jsonl").read_text().strip().splitlines()
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["action"] == "Did something"
        assert entry["category"] == "feature"

    def test_log_blocked_when_disabled(self, tmp_path, monkeypatch):
        d = _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        runner.invoke(main, ["disable"])
        result = runner.invoke(main, ["log", "Should not save"])
        assert "disabled" in result.output.lower()

        lines = (d / "sessions.jsonl").read_text().strip()
        assert lines == ""


class TestList:
    def test_list_entries(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        runner.invoke(main, ["log", "First thing", "-c", "feature"])
        runner.invoke(main, ["log", "Second thing", "-c", "bugfix"])

        result = runner.invoke(main, ["list", "--since", "30d"])
        assert result.exit_code == 0
        assert "First thing" in result.output
        assert "Second thing" in result.output

    def test_list_empty(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["list"])
        assert "No entries" in result.output


class TestStats:
    def test_stats_with_data(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        runner.invoke(main, ["log", "Bug fix", "-c", "bugfix"])
        runner.invoke(main, ["log", "Feature", "-c", "feature"])

        result = runner.invoke(main, ["stats", "--since", "30d"])
        assert result.exit_code == 0
        assert "Entries: 2" in result.output

    def test_stats_empty(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["stats"])
        assert "No entries" in result.output


class TestSummary:
    def test_summary_markdown(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        runner.invoke(main, ["log", "Built API", "-c", "feature", "-r", "my-api"])

        result = runner.invoke(main, ["summary", "--since", "30d"])
        assert result.exit_code == 0
        assert "# Work Summary" in result.output
        assert "Built API" in result.output

    def test_summary_json(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        runner.invoke(main, ["log", "Test entry", "-c", "test"])

        result = runner.invoke(main, ["summary", "--since", "30d", "-f", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["total_entries"] == 1


class TestConfig:
    def test_config_show(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--show"])
        assert result.exit_code == 0
        cfg = json.loads(result.output)
        assert "git_repos" in cfg

    def test_config_set_author(self, tmp_path, monkeypatch):
        d = _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--author", "user@example.com"])
        assert result.exit_code == 0

        cfg = json.loads((d / "config.json").read_text())
        assert cfg["author_email"] == "user@example.com"


class TestDateParsing:
    def test_invalid_date(self, tmp_path, monkeypatch):
        _setup_worklog(tmp_path, monkeypatch)
        runner = CliRunner()
        result = runner.invoke(main, ["stats", "--since", "not-a-date"])
        assert result.exit_code != 0
