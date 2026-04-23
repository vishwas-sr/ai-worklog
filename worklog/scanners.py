"""Scanners that pull work data from external sources into WorkEntry format."""

from __future__ import annotations

import logging
import subprocess
from datetime import datetime
from pathlib import Path

from .models import Category, Source, WorkEntry

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Git log scanner
# ---------------------------------------------------------------------------

_COMMIT_CATEGORY_HINTS: list[tuple[list[str], Category]] = [
    (["fix", "bug", "patch", "hotfix"], Category.BUGFIX),
    (["test", "spec", "coverage"], Category.TEST),
    (["refactor", "clean", "rename", "restructure"], Category.REFACTOR),
    (["doc", "readme", "comment", "wiki"], Category.DOCS),
    (["config", "ci", "build", "deploy", "pipeline", "yaml"], Category.CONFIG),
    (["review", "pr", "feedback"], Category.REVIEW),
    (["feat", "add", "implement", "new", "create"], Category.FEATURE),
]

# Conventional commit prefixes (checked before substring hints)
_PREFIX_MAP: dict[str, Category] = {
    "fix": Category.BUGFIX,
    "feat": Category.FEATURE,
    "test": Category.TEST,
    "refactor": Category.REFACTOR,
    "docs": Category.DOCS,
    "doc": Category.DOCS,
    "ci": Category.CONFIG,
    "build": Category.CONFIG,
    "chore": Category.CONFIG,
    "perf": Category.REFACTOR,
    "style": Category.REFACTOR,
    "review": Category.REVIEW,
}


def _categorize_commit(message: str) -> Category:
    msg = message.lower().strip()
    # Check conventional commit prefix first (e.g. "fix: ..." or "feat(scope): ...")
    prefix = msg.split(":")[0].split("(")[0].strip() if ":" in msg else ""
    if prefix in _PREFIX_MAP:
        return _PREFIX_MAP[prefix]
    # Fall back to substring matching
    for keywords, cat in _COMMIT_CATEGORY_HINTS:
        if any(kw in msg for kw in keywords):
            return cat
    return Category.OTHER


def scan_git_repos(
    repo_paths: list[str],
    since: str | None = None,
    until: str | None = None,
    author: str | None = None,
) -> list[WorkEntry]:
    """Scan one or more git repos and return WorkEntry per commit."""
    entries: list[WorkEntry] = []

    for repo_path in repo_paths:
        repo = Path(repo_path).resolve()
        if not (repo / ".git").exists():
            log.warning("Skipping %s — not a git repo", repo)
            continue

        cmd = ["git", "log", "--format=%H|%aI|%s|%an", "--name-only"]
        if since:
            cmd.append(f"--since={since}")
        if until:
            cmd.append(f"--until={until}")
        if author:
            cmd.append(f"--author={author}")

        try:
            result = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
        except FileNotFoundError:
            log.warning("git not found — cannot scan repos")
            return entries
        if result.returncode != 0:
            log.warning("git log failed for %s: %s", repo, result.stderr.strip())
            continue

        current: WorkEntry | None = None
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                if current:
                    entries.append(current)
                    current = None
                continue

            if "|" in line and line.count("|") >= 3:
                parts = line.split("|", 3)
                hash_val, ts, subject, author_name = parts
                current = WorkEntry(
                    timestamp=datetime.fromisoformat(ts),
                    source=Source.GIT,
                    repo=repo.name,
                    action=subject,
                    category=_categorize_commit(subject),
                    files=[],
                    tags=[],
                    details=f"commit {hash_val[:8]} by {author_name}",
                )
            elif current:
                current.files.append(line)

        if current:
            entries.append(current)

    return entries
