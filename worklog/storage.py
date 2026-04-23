"""Append-only JSONL storage with local git versioning.

Data directory is resolved in this order:
1. ``WORKLOG_DIR`` environment variable (explicit override)
2. Platform-specific default via ``platformdirs``
   - Linux:   ``~/.local/share/worklog``
   - macOS:   ``~/Library/Application Support/worklog``
   - Windows: ``%LOCALAPPDATA%/worklog`` (or OneDrive if detected)
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_data_dir

from .models import WorkEntry

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data directory resolution
# ---------------------------------------------------------------------------

def _resolve_worklog_dir() -> Path:
    """Return the worklog data directory, respecting env-var overrides."""
    env = os.environ.get("WORKLOG_DIR")
    if env:
        return Path(env).expanduser().resolve()

    # On Windows, prefer OneDrive location if it exists
    if sys.platform == "win32":
        for candidate in [
            Path.home() / "OneDrive - Microsoft" / ".worklog",
            Path.home() / "OneDrive" / ".worklog",
        ]:
            if candidate.parent.exists():
                return candidate

    return Path(user_data_dir("worklog", appauthor=False))


WORKLOG_DIR = _resolve_worklog_dir()
SESSIONS_FILE = WORKLOG_DIR / "sessions.jsonl"
CONFIG_FILE = WORKLOG_DIR / "config.json"

DEFAULT_CONFIG = {
    "git_repos": [],          # paths to scan for git activity
    "author_email": None,     # git author filter
    "auto_commit": True,      # auto git-commit locally after writes (for version history)
    "enabled": True,          # set to False to pause all logging
}

_REQUIRED_CONFIG_KEYS = {"git_repos", "enabled"}


def ensure_worklog_dir() -> None:
    """Create the worklog data directory and initialize a local git repo."""
    first_run = not WORKLOG_DIR.exists()
    WORKLOG_DIR.mkdir(parents=True, exist_ok=True)
    if not (WORKLOG_DIR / ".git").exists():
        try:
            subprocess.run(
                ["git", "init"],
                cwd=WORKLOG_DIR,
                check=True,
                capture_output=True,
            )
        except FileNotFoundError:
            log.debug("git not found — skipping local version history")
        except subprocess.CalledProcessError as exc:
            log.debug("git init failed: %s", exc)
        # Create .gitignore for temp files
        gitignore = WORKLOG_DIR / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.tmp\n*.lock\n", encoding="utf-8")
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.touch()
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8"
        )
    if first_run:
        _lock_down_permissions()


# ---------------------------------------------------------------------------
# Security: Owner-only NTFS ACL + OneDrive sharing disabled
# ---------------------------------------------------------------------------

_PERMISSIONS_MARKER = WORKLOG_DIR / ".permissions_set"


def _lock_down_permissions() -> None:
    """Restrict the worklog directory to the current user only.

    - Removes inherited permissions.
    - Grants full control only to the current user.
    - Blocks OneDrive sharing by setting a restrictive attribute.
    """
    if _PERMISSIONS_MARKER.exists():
        return  # already done

    if os.name != "nt":
        # On non-Windows, use POSIX permissions: owner rwx, no one else
        try:
            os.chmod(WORKLOG_DIR, 0o700)
        except OSError:
            pass
        _PERMISSIONS_MARKER.touch()
        return

    username = os.environ.get("USERNAME") or os.getlogin()

    try:
        # 1. Disable permission inheritance, remove all inherited ACEs
        subprocess.run(
            ["icacls", str(WORKLOG_DIR), "/inheritance:r"],
            check=True,
            capture_output=True,
        )
        # 2. Grant current user full control (recurse into contents)
        subprocess.run(
            [
                "icacls", str(WORKLOG_DIR),
                "/grant:r", f"{username}:(OI)(CI)F",
                "/T",
            ],
            check=True,
            capture_output=True,
        )
        # 3. Block OneDrive sharing by marking with SYSTEM attribute
        #    and creating a .nosync / desktop.ini hint
        _disable_onedrive_sharing()

    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        pass  # best-effort; don't break init if icacls is unavailable

    _PERMISSIONS_MARKER.touch()


def _disable_onedrive_sharing() -> None:
    """Prevent OneDrive from offering sharing options for this folder.

    Sets the folder to 'keep on this device only' mode and writes
    desktop.ini with a no-sharing hint.
    """
    try:
        # Set hidden + system attributes so casual browsing won't expose it
        subprocess.run(
            ["attrib", "+H", "+S", str(WORKLOG_DIR)],
            capture_output=True,
        )
        # Write desktop.ini to discourage sharing UI
        ini_path = WORKLOG_DIR / "desktop.ini"
        if not ini_path.exists():
            ini_path.write_text(
                "[.ShellClassInfo]\r\n"
                "InfoTip=Private worklog data - sharing disabled\r\n"
                "IconResource=%SystemRoot%\\system32\\shell32.dll,48\r\n"
                "[OneDrive]\r\n"
                "ShareEnabled=0\r\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["attrib", "+H", "+S", str(ini_path)],
                capture_output=True,
            )
    except (OSError, subprocess.CalledProcessError):
        pass


def verify_permissions() -> dict[str, bool]:
    """Check that the worklog directory has owner-only permissions.

    Returns a dict with diagnostic results.
    """
    result = {
        "directory_exists": WORKLOG_DIR.exists(),
        "permissions_applied": _PERMISSIONS_MARKER.exists(),
        "owner_only_acl": False,
    }
    if os.name == "nt" and WORKLOG_DIR.exists():
        try:
            proc = subprocess.run(
                ["icacls", str(WORKLOG_DIR)],
                capture_output=True,
                text=True,
            )
            lines = proc.stdout.strip().splitlines()
            # Should have exactly one user ACE (the owner)
            ace_lines = [ln for ln in lines if ":" in ln and WORKLOG_DIR.name not in ln]
            result["owner_only_acl"] = len(ace_lines) <= 1
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
    return result


def load_config() -> dict:
    """Load config, merging with defaults for any missing keys."""
    ensure_worklog_dir()
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Config file corrupted or unreadable (%s), using defaults", exc)
        cfg = {}
    # Merge with defaults so new keys are always present
    merged = {**DEFAULT_CONFIG, **cfg}
    return merged


def save_config(config: dict) -> None:
    ensure_worklog_dir()
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")


def is_enabled() -> bool:
    """Return True if worklog logging is enabled."""
    return load_config().get("enabled", True)


def append_entry(entry: WorkEntry, auto_commit: bool | None = None) -> None:
    """Append a single work entry to the JSONL log. Atomic per-line."""
    if not is_enabled():
        return
    ensure_worklog_dir()
    with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")
        f.flush()

    if auto_commit is None:
        auto_commit = load_config().get("auto_commit", True)
    if auto_commit:
        _git_commit_quiet()


def append_entries(entries: list[WorkEntry]) -> None:
    """Append multiple entries then commit once."""
    if not is_enabled():
        return
    ensure_worklog_dir()
    with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry.model_dump_json() + "\n")
        f.flush()
    if load_config().get("auto_commit", True):
        _git_commit_quiet()


def read_entries(
    start: datetime | None = None,
    end: datetime | None = None,
    source: str | None = None,
    category: str | None = None,
    repo: str | None = None,
) -> list[WorkEntry]:
    """Read entries with optional filters."""
    if not SESSIONS_FILE.exists():
        return []

    entries: list[WorkEntry] = []
    with open(SESSIONS_FILE, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = WorkEntry.model_validate_json(line)
            except Exception as exc:
                log.warning("Skipping malformed entry on line %d: %s", lineno, exc)
                continue

            if start and entry.timestamp < start:
                continue
            if end and entry.timestamp > end:
                continue
            if source and entry.source.value != source:
                continue
            if category and entry.category.value != category:
                continue
            if repo and (not entry.repo or repo.lower() not in entry.repo.lower()):
                continue
            entries.append(entry)
    return entries


def deduplicate_entries(entries: list[WorkEntry]) -> list[WorkEntry]:
    """Remove duplicate entries by id."""
    seen: set[str] = set()
    unique: list[WorkEntry] = []
    for e in entries:
        key = str(e.id)
        if key not in seen:
            seen.add(key)
            unique.append(e)
    return unique


EXCLUDES_FILE = WORKLOG_DIR / "excluded_sessions.json"


def delete_entry(entry_id: str) -> bool:
    """Delete a single entry by ID. Rewrites the JSONL file without it."""
    if not SESSIONS_FILE.exists():
        return False

    lines = SESSIONS_FILE.read_text(encoding="utf-8").strip().splitlines()
    kept = []
    found = False
    for line in lines:
        if not line.strip():
            continue
        try:
            entry = WorkEntry.model_validate_json(line)
            if str(entry.id) == entry_id:
                found = True
                continue
            kept.append(line)
        except Exception:
            kept.append(line)

    if found:
        SESSIONS_FILE.write_text("\n".join(kept) + "\n" if kept else "", encoding="utf-8")
        if load_config().get("auto_commit", True):
            _git_commit_quiet()

    return found


def load_excludes() -> set[str]:
    """Load the set of excluded session IDs."""
    if not EXCLUDES_FILE.exists():
        return set()
    try:
        data = json.loads(EXCLUDES_FILE.read_text(encoding="utf-8"))
        return set(data) if isinstance(data, list) else set()
    except (json.JSONDecodeError, OSError):
        return set()


def add_exclude(session_id: str) -> None:
    """Add a session ID to the exclusion list."""
    excludes = load_excludes()
    excludes.add(session_id)
    EXCLUDES_FILE.write_text(json.dumps(sorted(excludes), indent=2), encoding="utf-8")


def remove_exclude(session_id: str) -> bool:
    """Remove a session ID from the exclusion list."""
    excludes = load_excludes()
    if session_id in excludes:
        excludes.discard(session_id)
        EXCLUDES_FILE.write_text(json.dumps(sorted(excludes), indent=2), encoding="utf-8")
        return True
    return False


def _git_commit_quiet() -> None:
    """Stage and commit all changes in the local worklog git repo.

    This is purely for local version history (undo, diff, recover).
    OneDrive handles the actual cloud backup.
    """
    try:
        subprocess.run(
            ["git", "add", "."],
            cwd=WORKLOG_DIR,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"worklog {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            ],
            cwd=WORKLOG_DIR,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
