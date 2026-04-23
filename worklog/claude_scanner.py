"""Scanner for Claude Code (Anthropic) session history.

Claude Code stores session data in ~/.claude/ as JSON files. Each session
contains the full conversation with prompts, responses, and tool calls.

Cross-platform locations:
  Windows: %USERPROFILE%\\.claude\\
  macOS:   ~/.claude/
  Linux:   ~/.claude/
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from .models import Category, Complexity, Source, WorkEntry

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Claude Code session directory discovery
# ---------------------------------------------------------------------------

def _claude_code_dirs() -> list[Path]:
    """Return candidate Claude Code data directories."""
    home = Path.home()
    candidates = [
        home / ".claude",
    ]
    # Also check CLAUDE_CONFIG_DIR env var if set
    env_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if env_dir:
        candidates.insert(0, Path(env_dir).expanduser().resolve())

    return [d for d in candidates if d.exists()]


# ---------------------------------------------------------------------------
# Category inference
# ---------------------------------------------------------------------------

_TITLE_CATEGORY_HINTS: list[tuple[list[str], Category]] = [
    (["bug", "fix", "error", "troubleshoot", "debug", "issue", "crash"], Category.BUGFIX),
    (["test", "spec", "coverage", "unittest"], Category.TEST),
    (["refactor", "clean", "rename", "restructure", "migrate"], Category.REFACTOR),
    (["doc", "readme", "wiki", "comment", "writing", "adr"], Category.DOCS),
    (["config", "ci", "build", "deploy", "pipeline", "yaml", "setup", "install"], Category.CONFIG),
    (["review", "pr", "feedback", "code review"], Category.REVIEW),
    (["research", "understand", "explore", "investigate", "learn", "query", "analyze"], Category.RESEARCH),
    (["feat", "implement", "add", "create", "new", "generate"], Category.FEATURE),
]


def _categorize(text: str) -> Category:
    lower = text.lower()
    for keywords, cat in _TITLE_CATEGORY_HINTS:
        if any(kw in lower for kw in keywords):
            return cat
    return Category.OTHER


def _extract_tags(text: str) -> list[str]:
    tags: list[str] = []
    lower = text.lower()
    tech_keywords = {
        "python": "python", "typescript": "typescript", "javascript": "javascript",
        "rust": "rust", "go ": "golang", ".net": "dotnet", "c#": "csharp",
        "sql": "sql", "docker": "docker", "kubernetes": "kubernetes",
        "azure": "azure", "aws": "aws", "terraform": "terraform",
        "api": "api", "mcp": "mcp", "claude": "claude",
    }
    for kw, tag in tech_keywords.items():
        if kw in lower:
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# Session file parser
# ---------------------------------------------------------------------------

def _parse_claude_session(session_file: Path) -> dict | None:
    """Parse a Claude Code session file.

    Claude Code sessions can be stored as:
    - JSONL files (one JSON object per line, similar to VS Code chatSessions)
    - Single JSON files with a conversation array

    Returns parsed session data or None if unparsable.
    """
    try:
        content = session_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        log.debug("Could not read Claude Code session %s: %s", session_file, exc)
        return None

    if not content:
        return None

    # Try JSONL format first (one JSON object per line)
    lines = content.splitlines()
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not entries:
        # Try single JSON object
        try:
            data = json.loads(content)
            if isinstance(data, dict):
                entries = [data]
            elif isinstance(data, list):
                entries = data
        except json.JSONDecodeError:
            log.debug("Could not parse Claude Code session %s", session_file)
            return None

    if not entries:
        return None

    # Extract session metadata and conversation
    session_id = session_file.stem
    created = None
    prompts: list[str] = []
    responses: list[dict] = []
    project_path: str | None = None

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Session metadata formats
        if "sessionId" in entry:
            session_id = entry["sessionId"]
        if "id" in entry and not session_id:
            session_id = entry["id"]

        # Timestamps
        for ts_key in ["createdAt", "created", "timestamp", "creationDate"]:
            if ts_key in entry and not created:
                ts_val = entry[ts_key]
                if isinstance(ts_val, (int, float)):
                    # Milliseconds
                    if ts_val > 1e12:
                        ts_val = ts_val / 1000
                    created = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                elif isinstance(ts_val, str):
                    try:
                        created = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                    except ValueError:
                        pass

        # Project/directory context
        for dir_key in ["cwd", "workingDirectory", "projectPath", "directory"]:
            if dir_key in entry and not project_path:
                project_path = entry[dir_key]

        # JSONL format with kind field (similar to VS Code)
        kind = entry.get("kind")
        v = entry.get("v")
        if kind == 1 and v:
            if isinstance(v, str) and v.strip():
                prompts.append(v.strip())
            elif isinstance(v, dict) and "value" in v:
                val = v["value"]
                if isinstance(val, str) and val.strip():
                    prompts.append(val.strip())
        elif kind == 2 and isinstance(v, list):
            texts = []
            tool_calls = []
            for part in v:
                if not isinstance(part, dict):
                    continue
                if "value" in part and isinstance(part["value"], str):
                    texts.append(part["value"])
                if "invocationMessage" in part or "toolId" in part:
                    msg = part.get("pastTenseMessage") or part.get("invocationMessage") or ""
                    if isinstance(msg, str) and msg:
                        tool_calls.append(msg)
            responses.append({"text": " ".join(texts).strip() if texts else None, "tool_calls": tool_calls})

        # Alternative format: direct message objects
        role = entry.get("role", entry.get("type", ""))
        if role in ("user", "human"):
            msg_content = entry.get("content", entry.get("message", entry.get("text", "")))
            if isinstance(msg_content, str) and msg_content.strip():
                prompts.append(msg_content.strip())
            elif isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        prompts.append(part["text"].strip())
        elif role in ("assistant", "ai"):
            msg_content = entry.get("content", entry.get("message", entry.get("text", "")))
            texts = []
            tool_calls = []
            if isinstance(msg_content, str) and msg_content.strip():
                texts.append(msg_content.strip())
            elif isinstance(msg_content, list):
                for part in msg_content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            texts.append(part["text"])
                        elif part.get("type") == "tool_use":
                            tool_calls.append(part.get("name", "tool_call"))
            responses.append({"text": " ".join(texts).strip() if texts else None, "tool_calls": tool_calls})

    if not prompts:
        return None

    # Derive repo name from project path
    repo_name = None
    if project_path:
        repo_name = Path(project_path).name

    # Use file modification time as fallback for created timestamp
    if not created:
        try:
            created = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            created = datetime.now(timezone.utc)

    total_tool_calls = sum(len(r.get("tool_calls", [])) for r in responses)
    title = prompts[0][:120] if prompts else session_file.stem

    return {
        "session_id": session_id,
        "created": created,
        "title": title,
        "repo": repo_name,
        "prompts": prompts,
        "responses": responses,
        "exchange_count": len(prompts),
        "tool_call_count": total_tool_calls,
    }


def _estimate_complexity(exchange_count: int, tool_calls: int) -> Complexity:
    if exchange_count >= 25 or tool_calls >= 40:
        return Complexity.HIGH
    if exchange_count >= 10 or tool_calls >= 15:
        return Complexity.MEDIUM
    if exchange_count >= 3:
        return Complexity.LOW
    return Complexity.TRIVIAL


def _estimate_duration(exchange_count: int) -> float:
    return max(5.0, exchange_count * 4.0)


def _build_details(session: dict) -> str:
    prompts = session["prompts"]
    responses = session["responses"]
    exchange_count = session["exchange_count"]
    tool_calls = session["tool_call_count"]

    parts = []
    parts.append(f"[Context] User initiated Claude Code session: {prompts[0][:200]}")

    steps = []
    for i, prompt in enumerate(prompts[:15]):
        if len(prompt) > 5:
            steps.append(f"({i+1}) {prompt[:100]}")
    if steps:
        parts.append("[Steps] " + ". ".join(steps))

    last_resp = None
    for r in reversed(responses):
        if r.get("text"):
            last_resp = r["text"]
            break
    if last_resp:
        parts.append(f"[Outcome] {last_resp[:300]}")

    parts.append(f"Session had {exchange_count} exchanges with {tool_calls} tool calls.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_claude_code_sessions(
    since: datetime | None = None,
) -> list[WorkEntry]:
    """Scan Claude Code session files for conversation history.

    Reads session files from ~/.claude/ and produces rich WorkEntry objects.
    Gracefully returns empty list if Claude Code is not installed.
    """
    entries: list[WorkEntry] = []
    seen_sessions: set[str] = set()

    dirs = _claude_code_dirs()
    if not dirs:
        log.debug("Claude Code not found — skipping")
        return entries

    for claude_dir in dirs:
        # Claude Code may store sessions in various subdirectories
        session_dirs = [
            claude_dir / "sessions",
            claude_dir / "history",
            claude_dir / "projects",
            claude_dir,  # root may contain session files too
        ]

        for sdir in session_dirs:
            if not sdir.exists():
                continue

            # Scan for JSON and JSONL files
            for pattern in ["*.jsonl", "*.json"]:
                for session_file in sdir.rglob(pattern):
                    # Skip config/settings files
                    if session_file.name in (
                        "settings.json", "settings.local.json",
                        ".claude.json", "managed-settings.json",
                        "config.json", "mcp.json",
                    ):
                        continue

                    session = _parse_claude_session(session_file)
                    if not session:
                        continue

                    sid = session["session_id"]
                    if sid in seen_sessions:
                        continue
                    seen_sessions.add(sid)

                    created = session["created"]
                    if since and created < since:
                        continue

                    exchange_count = session["exchange_count"]
                    tool_calls = session["tool_call_count"]
                    title = session["title"]

                    entry = WorkEntry(
                        timestamp=created,
                        source=Source.CLAUDE_CODE,
                        session_id=sid,
                        repo=session.get("repo"),
                        action=title,
                        category=_categorize(title),
                        complexity=_estimate_complexity(exchange_count, tool_calls),
                        files=[],
                        tags=_extract_tags(title),
                        details=_build_details(session),
                        duration_minutes=_estimate_duration(exchange_count),
                    )
                    entries.append(entry)

    return entries
