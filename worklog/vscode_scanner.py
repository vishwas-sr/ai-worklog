"""Scanner for existing VS Code Copilot chat sessions and memory files.

Reads the chatSessions/*.jsonl files that VS Code persists for each workspace.
These contain full conversation content (prompts, responses, and tool calls),
enabling rich worklog entries with details, duration estimates, and tags.

Storage locations per platform:
  Windows: %APPDATA%/Code/User/workspaceStorage/<hash>/chatSessions/
  macOS:   ~/Library/Application Support/Code/User/workspaceStorage/<hash>/chatSessions/
  Linux:   ~/.config/Code/User/workspaceStorage/<hash>/chatSessions/

Supports VS Code stable and Insiders builds.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse

from .models import Category, Complexity, Source, WorkEntry

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Cross-platform VS Code storage paths
# ---------------------------------------------------------------------------

def _vscode_data_dirs() -> list[Path]:
    """Return candidate VS Code user-data directories for the current platform."""
    home = Path.home()
    variants = ["Code", "Code - Insiders"]
    dirs: list[Path] = []

    if sys.platform == "win32":
        appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        for v in variants:
            dirs.append(appdata / v / "User")
    elif sys.platform == "darwin":
        for v in variants:
            dirs.append(home / "Library" / "Application Support" / v / "User")
    else:  # Linux / BSD
        config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        for v in variants:
            dirs.append(config / v / "User")

    return [d for d in dirs if d.exists()]


def _get_vscode_storage_paths() -> tuple[list[Path], list[Path]]:
    """Return (global_session_dirs, workspace_storage_dirs) across all VS Code installs."""
    global_dirs: list[Path] = []
    ws_dirs: list[Path] = []

    for user_dir in _vscode_data_dirs():
        # Global sessions (no workspace open)
        gs = user_dir / "globalStorage" / "emptyWindowChatSessions"
        if gs.exists():
            global_dirs.append(gs)
        # Workspace-scoped sessions
        ws = user_dir / "workspaceStorage"
        if ws.exists():
            ws_dirs.append(ws)

    return global_dirs, ws_dirs

# Category inference from session titles
_TITLE_CATEGORY_HINTS: list[tuple[list[str], Category]] = [
    (["bug", "fix", "error", "troubleshoot", "debug", "issue"], Category.BUGFIX),
    (["feat", "implement", "add", "create", "build", "new", "generate"], Category.FEATURE),
    (["refactor", "clean", "rename", "restructure", "migrate"], Category.REFACTOR),
    (["test", "spec", "coverage", "unittest", "functional test"], Category.TEST),
    (["doc", "readme", "wiki", "comment", "writing"], Category.DOCS),
    (["config", "ci", "pipeline", "yaml", "deploy", "setup", "install"], Category.CONFIG),
    (["review", "pr", "feedback", "code review"], Category.REVIEW),
    (["research", "understand", "explore", "investigate", "learn", "query", "fetch", "list"], Category.RESEARCH),
]


def _categorize_title(title: str) -> Category:
    lower = title.lower()
    for keywords, cat in _TITLE_CATEGORY_HINTS:
        if any(kw in lower for kw in keywords):
            return cat
    return Category.OTHER


def _folder_uri_to_name(folder_uri: str | None) -> str | None:
    """Extract a human-friendly repo/folder name from a VS Code folder URI."""
    if not folder_uri:
        return None
    try:
        parsed = urlparse(folder_uri)
        path = unquote(parsed.path)
        # Strip leading slash on Windows paths like /c:/Users/...
        if len(path) > 2 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return Path(path).name or None
    except Exception:
        return folder_uri


def _read_workspace_folder(ws_dir: Path) -> str | None:
    """Read workspace.json to determine what folder/repo this workspace maps to."""
    ws_json = ws_dir / "workspace.json"
    if not ws_json.exists():
        return None
    try:
        data = json.loads(ws_json.read_text(encoding="utf-8"))
        return _folder_uri_to_name(data.get("folder") or data.get("workspace"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# chatSessions JSONL parser
# ---------------------------------------------------------------------------

def _parse_chat_session(session_file: Path) -> dict | None:
    """Parse a chatSessions/*.jsonl file into structured conversation data.

    JSONL format (one JSON object per line):
      kind=0: session metadata (sessionId, creationDate, title)
      kind=1: user prompt (string or dict with 'value')
      kind=2: response (list of parts — tool calls and text)

    Returns dict with: session_id, created, title, exchanges, exchange_count,
                       tool_call_count, response_summary.
    """
    entries = []
    try:
        with open(session_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError as exc:
        log.debug("Could not read session file %s: %s", session_file, exc)
        return None

    if not entries:
        return None

    # Extract metadata (kind=0)
    meta = {}
    for e in entries:
        if e.get("kind") == 0:
            meta = e.get("v", {})
            break

    session_id = meta.get("sessionId", session_file.stem)
    created_ms = meta.get("creationDate", 0)
    created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc) if created_ms else None

    # Build conversation exchanges
    prompts: list[str] = []
    responses: list[dict] = []
    last_timestamp = None

    for e in entries:
        kind = e.get("kind")
        v = e.get("v")

        if kind == 1:
            if isinstance(v, str) and v.strip():
                prompts.append(v.strip())
            elif isinstance(v, dict):
                val = v.get("value")
                if isinstance(val, str) and val.strip():
                    prompts.append(val.strip())

        elif kind == 2 and isinstance(v, list):
            texts = []
            tool_calls = []
            for part in v:
                if not isinstance(part, dict):
                    continue
                # Text response
                if "value" in part and isinstance(part["value"], str):
                    texts.append(part["value"])
                # Tool call
                if "invocationMessage" in part or "toolId" in part:
                    msg = part.get("pastTenseMessage") or part.get("invocationMessage") or ""
                    if isinstance(msg, str) and msg:
                        tool_calls.append(msg)
                # Timestamp
                if "timestamp" in part:
                    last_timestamp = part["timestamp"]

            responses.append({
                "text": " ".join(texts).strip() if texts else None,
                "tool_calls": tool_calls,
            })

    # Skip empty sessions
    if not prompts:
        return None

    # Determine title from first prompt (kind=1)
    title = prompts[0][:120] if prompts else session_file.stem

    # Build response summary (concatenate all response texts for detail extraction)
    all_response_text = " ".join(
        r["text"] for r in responses if r.get("text")
    )
    total_tool_calls = sum(len(r.get("tool_calls", [])) for r in responses)

    return {
        "session_id": session_id,
        "created": created,
        "title": title,
        "prompts": prompts,
        "responses": responses,
        "exchange_count": len(prompts),
        "tool_call_count": total_tool_calls,
        "response_summary": all_response_text[:2000] if all_response_text else None,
        "last_timestamp": last_timestamp,
    }


def _estimate_complexity(exchange_count: int, tool_calls: int) -> Complexity:
    """Estimate task complexity from session metrics."""
    if exchange_count >= 25 or tool_calls >= 40:
        return Complexity.HIGH
    if exchange_count >= 10 or tool_calls >= 15:
        return Complexity.MEDIUM
    if exchange_count >= 3:
        return Complexity.LOW
    return Complexity.TRIVIAL


def _estimate_duration(exchange_count: int) -> float:
    """Estimate session duration in minutes from exchange count."""
    # ~3-5 min per exchange (thinking + typing + reading response)
    return max(5.0, exchange_count * 4.0)


def _build_details(session: dict) -> str:
    """Build structured [Section] details from parsed session data."""
    prompts = session["prompts"]
    responses = session["responses"]
    exchange_count = session["exchange_count"]
    tool_calls = session["tool_call_count"]

    parts = []

    # [Context] — first user prompt
    parts.append(f"[Context] User initiated session: {prompts[0][:200]}")

    # [Steps] — summarize the conversation flow
    steps = []
    for i, prompt in enumerate(prompts[:15]):
        if len(prompt) > 5:  # skip trivial inputs like "1" or "yes"
            steps.append(f"({i+1}) {prompt[:100]}")
    if steps:
        parts.append("[Steps] " + ". ".join(steps))

    # [Outcome] — from the last response text
    last_resp = None
    for r in reversed(responses):
        if r.get("text"):
            last_resp = r["text"]
            break
    if last_resp:
        parts.append(f"[Outcome] {last_resp[:300]}")

    # Session metrics
    parts.append(
        f"Session had {exchange_count} exchanges with {tool_calls} tool calls."
    )

    return " ".join(parts)


def scan_vscode_sessions(
    since: datetime | None = None,
) -> list[WorkEntry]:
    """Scan all VS Code chatSessions directories for conversation history.

    Reads the JSONL files that store full conversation content, producing
    rich WorkEntry objects with structured details, duration, and complexity.
    """
    entries: list[WorkEntry] = []
    seen_sessions: set[str] = set()

    global_dirs, ws_roots = _get_vscode_storage_paths()

    # Collect all (session_dir, repo_name) pairs
    sources: list[tuple[Path, str | None]] = []

    for gdir in global_dirs:
        sources.append((gdir, None))

    for ws_root in ws_roots:
        for ws_dir in ws_root.iterdir():
            if not ws_dir.is_dir():
                continue
            chat_dir = ws_dir / "chatSessions"
            if chat_dir.exists():
                repo_name = _read_workspace_folder(ws_dir)
                sources.append((chat_dir, repo_name))

    for chat_dir, repo_name in sources:
        for session_file in chat_dir.glob("*.jsonl"):
            session = _parse_chat_session(session_file)
            if not session:
                continue

            sid = session["session_id"]
            if sid in seen_sessions:
                continue
            seen_sessions.add(sid)

            created = session["created"]
            if not created:
                continue
            if since and created < since:
                continue

            exchange_count = session["exchange_count"]
            tool_calls = session["tool_call_count"]
            title = session["title"]

            entry = WorkEntry(
                timestamp=created,
                source=Source.VSCODE_COPILOT,
                session_id=sid,
                repo=repo_name,
                action=title,
                category=_categorize_title(title),
                complexity=_estimate_complexity(exchange_count, tool_calls),
                impact=None,
                files=[],
                tags=_extract_tags(title),
                collaboration=[],
                details=_build_details(session),
                duration_minutes=_estimate_duration(exchange_count),
            )
            entries.append(entry)

    return entries


def _extract_tags(title: str) -> list[str]:
    """Extract technology/topic tags from a session title."""
    tags: list[str] = []
    lower = title.lower()
    tech_keywords = {
        "python": "python",
        "typescript": "typescript",
        "javascript": "javascript",
        ".net": "dotnet",
        "c#": "csharp",
        "sql": "sql",
        "kusto": "kusto",
        "kql": "kql",
        "docker": "docker",
        "kubernetes": "kubernetes",
        "azure": "azure",
        "cosmos": "cosmosdb",
        "mcp": "mcp",
        "api": "api",
        "excel": "excel",
        "csv": "csv",
        "icm": "icm",
        "pipeline": "pipeline",
    }
    for kw, tag in tech_keywords.items():
        if kw in lower:
            tags.append(tag)
    return tags


def scan_copilot_memory() -> list[WorkEntry]:
    """Scan Copilot memory files for any persisted notes/context.

    Memory files are typically in ~/.copilot/ or VS Code global storage.
    These contain notes the user has asked Copilot to remember, which
    can serve as evidence of work done.
    """
    entries: list[WorkEntry] = []
    memory_dirs = [
        Path.home() / ".copilot" / "memories",
    ]
    # Also scan VS Code global storage for each detected install
    for user_dir in _vscode_data_dirs():
        gs_mem = user_dir / "globalStorage" / "github.copilot-chat" / "memories"
        if gs_mem not in memory_dirs:
            memory_dirs.append(gs_mem)

    for mem_dir in memory_dirs:
        if not mem_dir.exists():
            continue
        for f in mem_dir.rglob("*.md"):
            try:
                content = f.read_text(encoding="utf-8")
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                entries.append(
                    WorkEntry(
                        timestamp=mtime,
                        source=Source.VSCODE_COPILOT,
                        action=f"Memory note: {f.stem}",
                        category=Category.DOCS,
                        files=[str(f)],
                        tags=["memory"],
                        details=content[:500] if content else None,
                    )
                )
            except Exception:
                continue

    return entries


# ---------------------------------------------------------------------------
# Copilot CLI / Agency session-state scanner
# ---------------------------------------------------------------------------

def _copilot_cli_session_dirs() -> list[Path]:
    """Return Copilot CLI session-state directories."""
    home = Path.home()
    candidates = [home / ".copilot" / "session-state"]
    env_dir = os.environ.get("COPILOT_HOME")
    if env_dir:
        candidates.insert(0, Path(env_dir).expanduser().resolve() / "session-state")
    return [d for d in candidates if d.exists()]


def _parse_copilot_cli_session(session_dir: Path) -> dict | None:
    """Parse a Copilot CLI session from ~/.copilot/session-state/<id>/."""
    events_file = session_dir / "events.jsonl"
    if not events_file.exists():
        return None

    events = []
    try:
        with open(events_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return None

    if not events:
        return None

    session_id = session_dir.name
    created = None
    cwd = None
    summary = None
    prompts: list[str] = []
    responses: list[dict] = []
    tool_call_count = 0
    lines_added = 0
    lines_removed = 0
    files_modified: list[str] = []

    for e in events:
        t = e.get("type", "")
        data = e.get("data", {})

        if t == "session.start":
            session_id = data.get("sessionId", session_id)
            ts = data.get("startTime")
            if ts:
                try:
                    created = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    pass

        elif t == "session.resume":
            ctx = data.get("context", {})
            cwd = ctx.get("cwd")

        elif t == "session.shutdown":
            changes = data.get("codeChanges", {})
            lines_added = changes.get("linesAdded", 0)
            lines_removed = changes.get("linesRemoved", 0)
            files_modified = changes.get("filesModified", [])

        elif t == "user.message":
            content = data.get("content", "")
            if isinstance(content, str) and content.strip():
                prompts.append(content.strip())

        elif t == "assistant.message":
            content = data.get("content", "")
            texts = []
            if isinstance(content, str) and content.strip():
                texts.append(content.strip())
            elif isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        texts.append(part["text"])
            responses.append({"text": " ".join(texts).strip() if texts else None})

        elif t in ("tool.execution_start", "tool.execution_complete"):
            tool_call_count += 1

    if not prompts:
        return None

    # Try workspace.yaml for summary
    ws_yaml = session_dir / "workspace.yaml"
    if ws_yaml.exists():
        try:
            ws_text = ws_yaml.read_text(encoding="utf-8")
            for line in ws_text.splitlines():
                if line.startswith("summary:"):
                    summary = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass

    if not created:
        try:
            created = datetime.fromtimestamp(events_file.stat().st_mtime, tz=timezone.utc)
        except OSError:
            created = datetime.now(timezone.utc)

    repo_name = Path(cwd).name if cwd else None
    title = summary or prompts[0][:120]

    return {
        "session_id": session_id,
        "created": created,
        "title": title,
        "repo": repo_name,
        "prompts": prompts,
        "responses": responses,
        "exchange_count": len(prompts),
        "tool_call_count": tool_call_count // 2,  # start + complete = 1 call
        "lines_added": lines_added,
        "lines_removed": lines_removed,
        "files_modified": files_modified,
    }


def scan_copilot_cli_sessions(since: datetime | None = None) -> list[WorkEntry]:
    """Scan Copilot CLI / Agency sessions from ~/.copilot/session-state/."""
    entries: list[WorkEntry] = []
    seen: set[str] = set()

    dirs = _copilot_cli_session_dirs()
    if not dirs:
        return entries

    for state_dir in dirs:
        for session_dir in state_dir.iterdir():
            if not session_dir.is_dir():
                continue

            session = _parse_copilot_cli_session(session_dir)
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
            title = session["title"]

            details_parts = [f"[Context] User initiated Copilot CLI session: {session['prompts'][0][:200]}"]
            steps = [f"({i+1}) {p[:100]}" for i, p in enumerate(session["prompts"][:15]) if len(p) > 5]
            if steps:
                details_parts.append("[Steps] " + ". ".join(steps))
            for r in reversed(session["responses"]):
                if r.get("text"):
                    details_parts.append(f"[Outcome] {r['text'][:300]}")
                    break
            if session["lines_added"] or session["lines_removed"]:
                details_parts.append(
                    f"Code changes: +{session['lines_added']}/-{session['lines_removed']} lines, "
                    f"{len(session['files_modified'])} files."
                )
            details_parts.append(f"Session had {ec} exchanges with {tc} tool calls.")

            entries.append(WorkEntry(
                timestamp=session["created"],
                source=Source.VSCODE_COPILOT,
                session_id=sid,
                repo=session.get("repo"),
                action=title,
                category=_categorize_title(title),
                complexity=_estimate_complexity(ec, tc),
                impact=None,
                files=session.get("files_modified", [])[:15],
                tags=_extract_tags(title),
                collaboration=[],
                details=" ".join(details_parts),
                duration_minutes=_estimate_duration(ec),
            ))

    return entries


def scan_all_existing(since: datetime | None = None) -> list[WorkEntry]:
    """Run all historical scanners and return combined results."""
    from .claude_scanner import scan_claude_code_sessions
    from .codex_scanner import scan_codex_sessions

    entries: list[WorkEntry] = []
    entries.extend(scan_vscode_sessions(since=since))
    entries.extend(scan_copilot_cli_sessions(since=since))
    entries.extend(scan_claude_code_sessions(since=since))
    entries.extend(scan_codex_sessions(since=since))
    entries.extend(scan_copilot_memory())
    entries.sort(key=lambda e: e.timestamp)
    return entries
