"""Seed realistic demo data for the worklog tool demo recording."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


def _resolve_worklog_dir() -> Path:
    """Resolve worklog dir the same way storage.py does."""
    import os
    env = os.environ.get("WORKLOG_DIR")
    if env:
        return Path(env).expanduser().resolve()
    if sys.platform == "win32":
        for candidate in [
            Path.home() / "OneDrive - Microsoft" / ".worklog",
            Path.home() / "OneDrive" / ".worklog",
        ]:
            if candidate.parent.exists():
                return candidate
    try:
        from platformdirs import user_data_dir
        return Path(user_data_dir("worklog", appauthor=False))
    except ImportError:
        return Path.home() / ".local" / "share" / "worklog"


WORKLOG_DIR = _resolve_worklog_dir()
SESSIONS_FILE = WORKLOG_DIR / "sessions.jsonl"

# Demo entries spanning the last 14 days - generic OSS project work
DEMO_ENTRIES = [
    # --- 14 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Investigated intermittent 429 throttling in API gateway",
        "category": "bugfix",
        "repo": "backend-api",
        "tags": ["throttling", "api"],
        "details": "Root cause: database connection pool exhaustion during peak traffic",
        "duration_minutes": 45,
    },
    {
        "source": "git",
        "action": "Added adaptive retry policy with exponential backoff",
        "category": "bugfix",
        "repo": "backend-api",
        "tags": ["resilience", "retry"],
        "files": ["src/retry_policy.py", "src/db_client.py"],
    },
    # --- 12 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Designed new file processing reconciliation pipeline",
        "category": "feature",
        "repo": "file-processor",
        "tags": ["design", "pipeline"],
        "details": "New pipeline to detect and reconcile stuck files older than 24h",
    },
    {
        "source": "git",
        "action": "Implemented ReconciliationWorker with fan-out pattern",
        "category": "feature",
        "repo": "file-processor",
        "tags": ["worker", "async"],
        "files": ["src/workers/reconciliation.py", "src/tasks/reconcile.py"],
    },
    # --- 10 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Code review for PR #452: Content pipeline retry improvements",
        "category": "review",
        "repo": "content-service",
        "tags": ["code-review"],
    },
    {
        "source": "manual",
        "action": "Sprint planning meeting - Q3 reliability OKRs",
        "category": "meeting",
        "tags": ["sprint", "okrs"],
    },
    # --- 8 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Built functional test suite using Testcontainers",
        "category": "test",
        "repo": "backend-api",
        "tags": ["testcontainers", "functional-tests"],
        "details": "PostgreSQL + Redis emulators with Docker Compose",
        "duration_minutes": 120,
    },
    {
        "source": "git",
        "action": "Added 12 functional tests covering retry, timeout, and dead-letter scenarios",
        "category": "test",
        "repo": "backend-api",
        "files": ["tests/functional/test_retry.py", "tests/functional/test_deadletter.py"],
    },
    # --- 6 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Researched Redis Cluster vs Sentinel for HA needs",
        "category": "research",
        "repo": "backend-api",
        "tags": ["redis", "capacity-planning"],
        "duration_minutes": 60,
    },
    {
        "source": "git",
        "action": "Updated Terraform modules for Redis cluster configuration",
        "category": "config",
        "repo": "backend-api",
        "tags": ["terraform", "infrastructure"],
        "files": ["deploy/redis.tf", "deploy/variables.tf"],
    },
    # --- 5 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Refactored DI registration to support test-mode toggle",
        "category": "refactor",
        "repo": "worker-service",
        "tags": ["dependency-injection", "testability"],
        "files": ["src/startup.py", "src/container.py"],
    },
    {
        "source": "git",
        "action": "Extracted FileProcessor interface for mock injection in tests",
        "category": "refactor",
        "repo": "worker-service",
        "files": ["src/interfaces/file_processor.py", "src/processors/xliff.py"],
    },
    # --- 4 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Debugged memory leak in blob download - fixed stream disposal",
        "category": "bugfix",
        "repo": "storage-service",
        "tags": ["memory-leak", "blob-storage"],
        "details": "StreamReader was not closing underlying download stream",
        "duration_minutes": 90,
    },
    {
        "source": "manual",
        "action": "Architecture review: proposed circuit breaker for cross-service calls",
        "category": "review",
        "tags": ["architecture", "resilience"],
    },
    # --- 3 days ago ---
    {
        "source": "git",
        "action": "Wrote ADR-017: Adopt resilience library for unified retry strategy",
        "category": "docs",
        "repo": "backend-api",
        "tags": ["adr", "resilience"],
        "files": ["docs/adr/017-resilience-strategy.md"],
    },
    {
        "source": "vscode-copilot",
        "action": "Implemented health check endpoints for all service components",
        "category": "feature",
        "repo": "backend-api",
        "tags": ["health-checks", "observability"],
        "files": ["src/health/db_check.py", "src/health/cache_check.py"],
    },
    # --- 2 days ago ---
    {
        "source": "vscode-copilot",
        "action": "Created worklog CLI tool for tracking development sessions",
        "category": "feature",
        "repo": "worklog",
        "tags": ["tooling", "productivity", "cli"],
        "details": "Local-first CLI: scans git, VS Code Copilot sessions, generates summaries",
        "duration_minutes": 180,
    },
    {
        "source": "git",
        "action": "Initial commit: worklog CLI with scan, log, summary, stats commands",
        "category": "feature",
        "repo": "worklog",
        "files": ["worklog/cli.py", "worklog/models.py", "worklog/storage.py", "worklog/formatters.py"],
    },
    # --- 1 day ago ---
    {
        "source": "vscode-copilot",
        "action": "Fixed off-by-one in onboard deduplication logic",
        "category": "bugfix",
        "repo": "worklog",
        "tags": ["bugfix"],
        "files": ["worklog/cli.py"],
    },
    {
        "source": "manual",
        "action": "1:1 with manager - discussed Q3 goals and career growth",
        "category": "meeting",
        "tags": ["1-1", "career"],
    },
    # --- Today ---
    {
        "source": "vscode-copilot",
        "action": "Added HTML and CSV export formatters for worklog summaries",
        "category": "feature",
        "repo": "worklog",
        "tags": ["formatters", "export"],
        "files": ["worklog/formatters.py"],
        "duration_minutes": 30,
    },
]


def seed():
    """Write demo entries to sessions.jsonl."""
    WORKLOG_DIR.mkdir(parents=True, exist_ok=True)

    # Back up existing file if present
    if SESSIONS_FILE.exists() and SESSIONS_FILE.stat().st_size > 0:
        backup = SESSIONS_FILE.with_suffix(".jsonl.bak")
        backup.write_bytes(SESSIONS_FILE.read_bytes())
        print(f"Backed up existing data to {backup}")

    now = datetime.now(timezone.utc)
    day_offsets = [14, 14, 12, 12, 10, 10, 8, 8, 6, 6, 5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 0]

    with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
        for i, entry_data in enumerate(DEMO_ENTRIES):
            offset_days = day_offsets[i] if i < len(day_offsets) else 0
            hour = 9 + (i % 8)
            ts = (now - timedelta(days=offset_days)).replace(
                hour=hour, minute=(i * 17) % 60, second=0, microsecond=0
            )
            record = {
                "id": str(uuid4()),
                "timestamp": ts.isoformat(),
                **entry_data,
            }
            record.setdefault("session_id", None)
            record.setdefault("repo", None)
            record.setdefault("files", [])
            record.setdefault("tags", [])
            record.setdefault("details", None)
            record.setdefault("duration_minutes", None)
            f.write(json.dumps(record) + "\n")

    print(f"Seeded {len(DEMO_ENTRIES)} demo entries into {SESSIONS_FILE}")


if __name__ == "__main__":
    seed()
