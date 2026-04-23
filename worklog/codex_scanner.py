"""Scanner for OpenAI Codex CLI session history.

Codex CLI stores session data in ~/.codex/ (overridable via CODEX_HOME).
Sessions are persisted as JSONL/JSON files containing conversation history.

Storage location: ~/.codex/ (all platforms), or CODEX_HOME env var.
Key files: history.jsonl, sessions/, and project-specific session files.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import Category, Complexity, Source, WorkEntry

log = logging.getLogger(__name__)


def _codex_dirs() -> list[Path]:
    """Return candidate Codex CLI data directories."""
    home = Path.home()
    candidates = [home / ".codex"]
    env_dir = os.environ.get("CODEX_HOME")
    if env_dir:
        candidates.insert(0, Path(env_dir).expanduser().resolve())
    return [d for d in candidates if d.exists()]


_CATEGORY_HINTS: list[tuple[list[str], Category]] = [
    (["bug", "fix", "error", "troubleshoot", "debug", "issue", "crash"], Category.BUGFIX),
    (["test", "spec", "coverage", "unittest"], Category.TEST),
    (["refactor", "clean", "rename", "restructure", "migrate"], Category.REFACTOR),
    (["doc", "readme", "wiki", "comment", "writing", "adr"], Category.DOCS),
    (["config", "ci", "build", "deploy", "pipeline", "yaml", "setup"], Category.CONFIG),
    (["review", "pr", "feedback", "code review"], Category.REVIEW),
    (["research", "understand", "explore", "investigate", "analyze"], Category.RESEARCH),
    (["feat", "implement", "add", "create", "new", "generate"], Category.FEATURE),
]


def _categorize(text: str) -> Category:
    lower = text.lower()
    for keywords, cat in _CATEGORY_HINTS:
        if any(kw in lower for kw in keywords):
            return cat
    return Category.OTHER


def _extract_tags(text: str) -> list[str]:
    tags: list[str] = []
    lower = text.lower()
    kw_map = {
        "python": "python", "typescript": "typescript", "javascript": "javascript",
        "rust": "rust", "go ": "golang", ".net": "dotnet", "c#": "csharp",
        "sql": "sql", "docker": "docker", "kubernetes": "kubernetes",
        "openai": "openai", "codex": "codex", "gpt": "gpt",
        "api": "api", "terraform": "terraform", "azure": "azure", "aws": "aws",
    }
    for kw, tag in kw_map.items():
        if kw in lower:
            tags.append(tag)
    return tags


def _parse_codex_session(session_file: Path) -> dict | None:
    """Parse a Codex CLI session file (JSONL or JSON)."""
    try:
        content = session_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        log.debug("Could not read Codex session %s: %s", session_file, exc)
        return None

    if not content:
        return None

    # Parse JSONL or JSON
    entries = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    if not entries:
        try:
            data = json.loads(content)
            entries = [data] if isinstance(data, dict) else (data if isinstance(data, list) else [])
        except json.JSONDecodeError:
            return None

    if not entries:
        return None

    session_id = session_file.stem
    created = None
    prompts: list[str] = []
    responses: list[dict] = []
    project_path: str | None = None

    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Session metadata
        for id_key in ["sessionId", "id", "session_id"]:
            if id_key in entry and entry[id_key]:
                session_id = str(entry[id_key])
                break

        # Timestamps
        for ts_key in ["createdAt", "created", "timestamp", "creationDate"]:
            if ts_key in entry and not created:
                ts_val = entry[ts_key]
                if isinstance(ts_val, (int, float)):
                    if ts_val > 1e12:
                        ts_val = ts_val / 1000
                    created = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                elif isinstance(ts_val, str):
                    try:
                        created = datetime.fromisoformat(ts_val.replace("Z", "+00:00"))
                    except ValueError:
                        pass

        # Project context
        for dir_key in ["cwd", "workingDirectory", "projectPath"]:
            if dir_key in entry and not project_path:
                project_path = entry[dir_key]

        # JSONL kind-based format
        kind = entry.get("kind")
        v = entry.get("v")
        if kind == 1 and v:
            if isinstance(v, str) and v.strip():
                prompts.append(v.strip())
            elif isinstance(v, dict) and isinstance(v.get("value"), str):
                prompts.append(v["value"].strip())
        elif kind == 2 and isinstance(v, list):
            texts = []
            tool_calls = []
            for part in v:
                if isinstance(part, dict):
                    if "value" in part and isinstance(part["value"], str):
                        texts.append(part["value"])
                    if "invocationMessage" in part or "toolId" in part:
                        msg = part.get("pastTenseMessage") or part.get("invocationMessage") or ""
                        if isinstance(msg, str) and msg:
                            tool_calls.append(msg)
            responses.append({"text": " ".join(texts).strip() if texts else None, "tool_calls": tool_calls})

        # Direct message format
        role = entry.get("role", entry.get("type", ""))
        if role in ("user", "human"):
            msg = entry.get("content", entry.get("message", entry.get("text", "")))
            if isinstance(msg, str) and msg.strip():
                prompts.append(msg.strip())
            elif isinstance(msg, list):
                for p in msg:
                    if isinstance(p, dict) and p.get("type") == "text":
                        prompts.append(p["text"].strip())
        elif role in ("assistant", "ai"):
            msg = entry.get("content", entry.get("message", entry.get("text", "")))
            texts, tool_calls = [], []
            if isinstance(msg, str) and msg.strip():
                texts.append(msg.strip())
            elif isinstance(msg, list):
                for p in msg:
                    if isinstance(p, dict):
                        if p.get("type") == "text":
                            texts.append(p["text"])
                        elif p.get("type") in ("tool_use", "function_call"):
                            tool_calls.append(p.get("name", "tool_call"))
            responses.append({"text": " ".join(texts).strip() if texts else None, "tool_calls": tool_calls})

    if not prompts:
        return None

    repo_name = Path(project_path).name if project_path else None

    if not created:
        try:
            created = datetime.fromtimestamp(session_file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            created = datetime.now(timezone.utc)

    return {
        "session_id": session_id,
        "created": created,
        "title": prompts[0][:120],
        "repo": repo_name,
        "prompts": prompts,
        "responses": responses,
        "exchange_count": len(prompts),
        "tool_call_count": sum(len(r.get("tool_calls", [])) for r in responses),
    }


def _estimate_complexity(exchange_count: int, tool_calls: int) -> Complexity:
    if exchange_count >= 25 or tool_calls >= 40:
        return Complexity.HIGH
    if exchange_count >= 10 or tool_calls >= 15:
        return Complexity.MEDIUM
    if exchange_count >= 3:
        return Complexity.LOW
    return Complexity.TRIVIAL


def _build_details(session: dict) -> str:
    prompts = session["prompts"]
    parts = [f"[Context] User initiated Codex CLI session: {prompts[0][:200]}"]
    steps = [f"({i+1}) {p[:100]}" for i, p in enumerate(prompts[:15]) if len(p) > 5]
    if steps:
        parts.append("[Steps] " + ". ".join(steps))
    for r in reversed(session["responses"]):
        if r.get("text"):
            parts.append(f"[Outcome] {r['text'][:300]}")
            break
    parts.append(f"Session had {session['exchange_count']} exchanges with {session['tool_call_count']} tool calls.")
    return " ".join(parts)


def scan_codex_sessions(since: datetime | None = None) -> list[WorkEntry]:
    """Scan Codex CLI session files from ~/.codex/.

    Gracefully returns empty list if Codex CLI is not installed.
    """
    entries: list[WorkEntry] = []
    seen: set[str] = set()

    dirs = _codex_dirs()
    if not dirs:
        log.debug("Codex CLI not found — skipping")
        return entries

    skip_filenames = {
        "config.toml", "settings.json", "settings.local.json",
        "managed-settings.json", ".codex.json",
    }

    for codex_dir in dirs:
        search_dirs = [
            codex_dir / "sessions",
            codex_dir / "history",
            codex_dir,
        ]
        for sdir in search_dirs:
            if not sdir.exists():
                continue
            for pattern in ["*.jsonl", "*.json"]:
                for sf in sdir.rglob(pattern):
                    if sf.name in skip_filenames:
                        continue
                    session = _parse_codex_session(sf)
                    if not session:
                        continue
                    sid = session["session_id"]
                    if sid in seen:
                        continue
                    seen.add(sid)
                    if since and session["created"] < since:
                        continue

                    ec = session["exchange_count"]
                    tc = session["tool_call_count"]
                    entries.append(WorkEntry(
                        timestamp=session["created"],
                        source=Source.CODEX_CLI,
                        session_id=sid,
                        repo=session.get("repo"),
                        action=session["title"],
                        category=_categorize(session["title"]),
                        complexity=_estimate_complexity(ec, tc),
                        files=[],
                        tags=_extract_tags(session["title"]),
                        details=_build_details(session),
                        duration_minutes=max(5.0, ec * 4.0),
                    ))
    return entries
