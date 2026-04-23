"""Tests for worklog.scanners."""
from worklog.scanners import _categorize_commit


class TestCategorizeCommit:
    def test_fix_detected(self):
        assert _categorize_commit("fix: handle null pointer").value == "bugfix"

    def test_feature_detected(self):
        assert _categorize_commit("feat: add user authentication").value == "feature"

    def test_refactor_detected(self):
        assert _categorize_commit("refactor: extract shared module").value == "refactor"

    def test_test_detected(self):
        assert _categorize_commit("test: add coverage for auth module").value == "test"

    def test_docs_detected(self):
        assert _categorize_commit("docs: update README").value == "docs"

    def test_config_detected(self):
        assert _categorize_commit("ci: add GitHub Actions pipeline").value == "config"

    def test_unknown_defaults_to_other(self):
        assert _categorize_commit("updated stuff").value == "other"

    def test_case_insensitive(self):
        assert _categorize_commit("FIX: crash on startup").value == "bugfix"
