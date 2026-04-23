"""CLI entry point for the worklog tool."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from . import formatters as fmt
from .claude_scanner import scan_claude_code_sessions
from .codex_scanner import scan_codex_sessions
from .models import Category, Source, WorkEntry
from .scanners import scan_git_repos
from .storage import (
    WORKLOG_DIR,
    _lock_down_permissions,
    add_exclude,
    append_entries,
    append_entry,
    deduplicate_entries,
    delete_entry,
    ensure_worklog_dir,
    is_enabled,
    load_config,
    load_excludes,
    read_entries,
    remove_exclude,
    save_config,
    verify_permissions,
)
from .summarizer import summarize
from .vscode_scanner import (
    scan_copilot_cli_sessions,
    scan_copilot_memory,
    scan_vscode_sessions,
)

# ---------------------------------------------------------------------------
# Auto-install instruction files for AI tools
# ---------------------------------------------------------------------------

_INSTRUCTION_TARGETS = [
    # (source_filename, target_dir, target_filename, tool_name, require_dir_exists)
    ("copilot-worklog-instruction.md", Path.home() / ".github", "copilot-instructions.md", "GitHub Copilot", False),
    ("claude-worklog-instruction.md", Path.home() / ".claude", "CLAUDE.md", "Claude Code", True),
    ("codex-worklog-instruction.md", Path.home() / ".codex", "AGENTS.md", "OpenAI Codex", True),
]


def _install_instructions(include: set[str] | None = None) -> None:
    """Install auto-logging instruction files for AI tools.

    - GitHub Copilot: always installed
    - Claude Code: if --claude passed or ~/.claude/ already exists
    - OpenAI Codex: if --codex passed or ~/.codex/ already exists

    Appends to existing files if they already exist. Skips if already installed.
    """
    # Look for instruction files bundled inside the package first,
    # then fall back to the repo root (for editable installs)
    pkg_dir = Path(__file__).parent / "instructions"
    if not pkg_dir.exists():
        pkg_dir = Path(__file__).parent.parent / "instructions"
    if not pkg_dir.exists():
        pkg_dir = Path.cwd() / "instructions"
    if not pkg_dir.exists():
        return

    marker = "# Work Logger — Automatic Session Tracking"

    for src_name, target_dir, target_name, tool_name, key in _INSTRUCTION_TARGETS:
        src_file = pkg_dir / src_name
        if not src_file.exists():
            continue

        # Copilot is always installed. Others need explicit opt-in or existing dir.
        if key != "copilot":
            explicitly_requested = include and key in include
            already_installed = target_dir.exists()
            if not explicitly_requested and not already_installed:
                continue

        target_file = target_dir / target_name
        src_content = src_file.read_text(encoding="utf-8")

        if target_file.exists():
            existing = target_file.read_text(encoding="utf-8")
            if marker in existing:
                click.echo(f"  {tool_name}: auto-logging already installed")
                continue
            # Append to existing file
            target_dir.mkdir(parents=True, exist_ok=True)
            with open(target_file, "a", encoding="utf-8") as f:
                f.write("\n\n" + src_content)
            click.echo(f"  {tool_name}: auto-logging appended to {target_file}")
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file.write_text(src_content, encoding="utf-8")
            click.echo(f"  {tool_name}: auto-logging installed at {target_file}")


def _parse_date(val: str) -> datetime:
    """Parse YYYY-MM-DD or relative like '7d', '2w', '1m'.

    Raises click.BadParameter on invalid input.
    """
    try:
        if val.endswith("d"):
            return datetime.now(timezone.utc) - timedelta(days=int(val[:-1]))
        if val.endswith("w"):
            return datetime.now(timezone.utc) - timedelta(weeks=int(val[:-1]))
        if val.endswith("m"):
            return datetime.now(timezone.utc) - timedelta(days=int(val[:-1]) * 30)
        return datetime.fromisoformat(val).replace(tzinfo=timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise click.BadParameter(
            f"Invalid date '{val}'. Use YYYY-MM-DD or relative format (7d, 2w, 3m)."
        ) from exc


@click.group()
def main():
    """worklog — track and summarize AI/agentic work sessions."""
    pass


# ---- init ----

@main.command()
@click.option("--claude", is_flag=True, help="Also install auto-logging for Claude Code.")
@click.option("--codex", is_flag=True, help="Also install auto-logging for OpenAI Codex.")
def init(claude, codex):
    """Initialize the worklog data directory and install auto-logging instructions."""
    ensure_worklog_dir()
    click.echo(f"Worklog initialized at {WORKLOG_DIR}")
    click.echo("Data is stored locally with automatic git versioning.")
    perms = verify_permissions()
    if perms["permissions_applied"]:
        click.echo("Permissions: owner-only access enforced, sharing disabled.")
    else:
        click.echo("Run 'worklog lock' to restrict access to your account only.")

    # Auto-install instruction files
    include = set()
    if claude:
        include.add("claude")
    if codex:
        include.add("codex")
    _install_instructions(include=include if include else None)


# ---- enable / disable ----

@main.command()
def disable():
    """Pause worklog — no sessions will be logged until re-enabled."""
    cfg = load_config()
    cfg["enabled"] = False
    save_config(cfg)
    click.echo("Worklog disabled. No sessions will be logged.")
    click.echo("Run 'worklog enable' to resume.")


@main.command()
def enable():
    """Resume worklog session logging."""
    cfg = load_config()
    cfg["enabled"] = True
    save_config(cfg)
    click.echo("Worklog enabled. Sessions will be logged.")


@main.command()
def status():
    """Show whether worklog is currently enabled or disabled."""
    state = "enabled" if is_enabled() else "disabled"
    click.echo(f"Worklog is {state}.")
    perms = verify_permissions()
    if perms["permissions_applied"]:
        click.echo("Permissions: locked (owner-only access).")
    else:
        click.echo("Permissions: not locked. Run 'worklog lock' to secure.")


# ---- lock (security) ----

@main.command()
def lock():
    """Restrict worklog folder to owner-only access and disable sharing."""
    ensure_worklog_dir()
    _lock_down_permissions()
    perms = verify_permissions()
    if perms["permissions_applied"]:
        click.echo("Worklog directory locked down:")
        click.echo(f"  Folder: {WORKLOG_DIR}")
        click.echo("  - Inherited permissions removed")
        click.echo("  - Only your account has access")
        click.echo("  - OneDrive sharing disabled")
    else:
        click.echo("Could not apply permissions. Check folder access.")


# ---- onboard ----

@main.command()
@click.option(
    "--since", default=None,
    help="Only import after this date (YYYY-MM-DD or relative: 30d, 3m). Default: all.",
)
@click.option("--dry-run", is_flag=True, help="Show what would be imported without writing.")
@click.option("--git/--no-git", "include_git", default=True, help="Include git commit history from configured repos.")
@click.option("--vscode/--no-vscode", "include_vscode", default=True, help="Include VS Code Copilot chat sessions.")
@click.option("--claude/--no-claude", "include_claude", default=True, help="Include Claude Code sessions.")
@click.option("--codex/--no-codex", "include_codex", default=True, help="Include OpenAI Codex CLI sessions.")
@click.option("--memory/--no-memory", "include_memory", default=True, help="Include Copilot memory notes.")
def onboard(since, dry_run, include_git, include_vscode, include_claude, include_codex, include_memory):
    """Import all existing sessions and history for initial worklog setup.

    Scans VS Code Copilot chat sessions, Claude Code sessions, Codex CLI
    sessions, Copilot memory notes, and git commit history.
    """
    ensure_worklog_dir()
    start = _parse_date(since) if since else None
    all_new: list[WorkEntry] = []

    if include_vscode:
        click.echo("Scanning VS Code Copilot chat sessions...")
        vscode_entries = scan_vscode_sessions(since=start)
        click.echo(f"  Found {len(vscode_entries)} chat session(s)")
        all_new.extend(vscode_entries)

        click.echo("Scanning Copilot CLI / Agency sessions...")
        cli_entries = scan_copilot_cli_sessions(since=start)
        click.echo(f"  Found {len(cli_entries)} Copilot CLI session(s)")
        all_new.extend(cli_entries)

    if include_claude:
        click.echo("Scanning Claude Code sessions...")
        claude_entries = scan_claude_code_sessions(since=start)
        click.echo(f"  Found {len(claude_entries)} Claude Code session(s)")
        all_new.extend(claude_entries)

    if include_codex:
        click.echo("Scanning Codex CLI sessions...")
        codex_entries = scan_codex_sessions(since=start)
        click.echo(f"  Found {len(codex_entries)} Codex CLI session(s)")
        all_new.extend(codex_entries)

    if include_memory:
        click.echo("Scanning Copilot memory files...")
        mem_entries = scan_copilot_memory()
        click.echo(f"  Found {len(mem_entries)} memory note(s)")
        all_new.extend(mem_entries)

    if include_git:
        cfg = load_config()
        if cfg["git_repos"]:
            click.echo(f"Scanning {len(cfg['git_repos'])} git repo(s)...")
            since_str = start.isoformat() if start else None
            git_entries = scan_git_repos(
                cfg["git_repos"],
                since=since_str,
                author=cfg.get("author_email"),
            )
            click.echo(f"  Found {len(git_entries)} commit(s)")
            all_new.extend(git_entries)
        else:
            click.echo("  No git repos configured (use: worklog config --add-repo <path>)")

    if not all_new:
        click.echo("\nNo entries found to import.")
        return

    # Sort by timestamp
    all_new.sort(key=lambda e: e.timestamp)

    # Preview
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Total entries to import: {len(all_new)}")
    start_str = all_new[0].timestamp.strftime("%Y-%m-%d")
    end_str = all_new[-1].timestamp.strftime("%Y-%m-%d")
    click.echo(f"Date range: {start_str} to {end_str}")

    from collections import Counter
    by_source = Counter(e.source.value for e in all_new)
    by_cat = Counter(e.category.value for e in all_new)
    click.echo(f"By source: {', '.join(f'{s}={c}' for s, c in by_source.most_common())}")
    click.echo(f"By category: {', '.join(f'{cat}={c}' for cat, c in by_cat.most_common())}")
    click.echo()

    # Show sample entries
    click.echo("Sample entries:")
    for e in all_new[:10]:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M")
        repo = f" ({e.repo})" if e.repo else ""
        click.echo(f"  {ts} [{e.source.value}]{repo} {e.action[:80]}")
    if len(all_new) > 10:
        click.echo(f"  ... and {len(all_new) - 10} more")
    click.echo()

    if dry_run:
        click.echo("Dry run — no entries written.")
        return

    # Deduplicate against existing entries and exclusions
    existing = read_entries()
    existing_actions = {(e.source.value, e.action, e.timestamp.strftime("%Y-%m-%d")) for e in existing}
    excludes = load_excludes()
    truly_new = [
        e for e in all_new
        if (e.source.value, e.action, e.timestamp.strftime("%Y-%m-%d")) not in existing_actions
        and (e.session_id or str(e.id)) not in excludes
    ]

    excluded_count = sum(1 for e in all_new if (e.session_id or str(e.id)) in excludes)
    if excluded_count:
        click.echo(f"Skipping {excluded_count} excluded session(s).")

    if not truly_new:
        click.echo("All entries already exist in worklog. Nothing to import.")
        return

    if len(truly_new) < len(all_new):
        click.echo(f"Skipping {len(all_new) - len(truly_new)} duplicate(s).")

    append_entries(truly_new)
    click.echo(f"Imported {len(truly_new)} entries into {WORKLOG_DIR / 'sessions.jsonl'}")


# ---- config ----

@main.command()
@click.option("--add-repo", multiple=True, help="Add a git repo path to scan.")
@click.option("--remove-repo", multiple=True, help="Remove a git repo path.")
@click.option("--author", default=None, help="Set default git author email filter.")
@click.option(
    "--auto-commit/--no-auto-commit", default=None,
    help="Toggle auto git-commit on writes (for local version history).",
)
@click.option("--show", is_flag=True, help="Show current config.")
def config(add_repo, remove_repo, author, auto_commit, show):
    """View or modify worklog configuration."""
    cfg = load_config()

    if show:
        import json
        click.echo(json.dumps(cfg, indent=2))
        return

    for r in add_repo:
        p = str(Path(r).resolve())
        if p not in cfg["git_repos"]:
            cfg["git_repos"].append(p)
            click.echo(f"Added repo: {p}")

    for r in remove_repo:
        p = str(Path(r).resolve())
        if p in cfg["git_repos"]:
            cfg["git_repos"].remove(p)
            click.echo(f"Removed repo: {p}")

    if author is not None:
        cfg["author_email"] = author
    if auto_commit is not None:
        cfg["auto_commit"] = auto_commit

    save_config(cfg)
    click.echo("Config saved.")


# ---- log (manual entry) ----

@main.command()
@click.argument("action")
@click.option("-c", "--category", type=click.Choice([c.value for c in Category]), default="other")
@click.option("-s", "--source", type=click.Choice([s.value for s in Source]), default="manual")
@click.option("-r", "--repo", default=None)
@click.option("-t", "--tags", default=None, help="Comma-separated tags.")
@click.option("-d", "--details", default=None)
def log(action, category, source, repo, tags, details):
    """Manually log a work entry."""
    if not is_enabled():
        click.echo("Worklog is disabled. Run 'worklog enable' to resume.")
        return
    entry = WorkEntry(
        source=Source(source),
        action=action,
        category=Category(category),
        repo=repo,
        tags=tags.split(",") if tags else [],
        details=details,
    )
    append_entry(entry)
    click.echo(f"Logged: {action}")


# ---- scan (import from git / M365) ----

@main.command()
@click.option("--since", default="30d", help="Start date (YYYY-MM-DD or relative: 7d, 2w, 1m).")
@click.option("--until", default=None, help="End date (YYYY-MM-DD, default=now).")
def scan(since, until):
    """Import work entries from configured git repos."""
    cfg = load_config()
    start = _parse_date(since)
    end = _parse_date(until) if until else datetime.now(timezone.utc)
    all_new: list[WorkEntry] = []

    if cfg["git_repos"]:
        click.echo(f"Scanning {len(cfg['git_repos'])} git repo(s)...")
        git_entries = scan_git_repos(
            cfg["git_repos"],
            since=start.isoformat(),
            until=end.isoformat(),
            author=cfg.get("author_email"),
        )
        all_new.extend(git_entries)
        click.echo(f"  Found {len(git_entries)} commits.")
    else:
        click.echo("No git repos configured. Use: worklog config --add-repo <path>")

    if all_new:
        # Merge with existing to avoid duplicates
        existing = read_entries()
        combined = deduplicate_entries(existing + all_new)
        new_count = len(combined) - len(existing)
        if new_count > 0:
            # Only append the truly new entries
            existing_ids = {str(e.id) for e in existing}
            to_add = [e for e in all_new if str(e.id) not in existing_ids]
            append_entries(to_add)
            click.echo(f"Added {len(to_add)} new entries.")
        else:
            click.echo("No new entries to add.")
    else:
        click.echo("No entries found.")


# ---- summary ----

@main.command()
@click.option("--since", default="30d", help="Start date (YYYY-MM-DD or relative: 7d, 2w, 1m).")
@click.option("--until", default=None, help="End date (YYYY-MM-DD, default=now).")
@click.option(
    "-f", "--format", "fmt_name",
    type=click.Choice(["markdown", "md", "html", "csv", "json", "review", "report"]),
    default="markdown",
)
@click.option("-o", "--output", default=None, help="Write to file instead of stdout.")
@click.option("--source", default=None, help="Filter by source.")
@click.option("--category", default=None, help="Filter by category.")
@click.option("--repo", default=None, help="Filter by repo name (substring match).")
def summary(since, until, fmt_name, output, source, category, repo):
    """Generate a work summary for the given time period."""
    start = _parse_date(since)
    end = _parse_date(until) if until else datetime.now(timezone.utc)

    entries = read_entries(start=start, end=end, source=source, category=category, repo=repo)
    if not entries:
        click.echo("No entries found for the specified period.")
        return

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    s = summarize(entries, start, end)

    formatter = fmt.FORMATTERS[fmt_name]
    result = formatter(s)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        click.echo(f"Summary written to {output}")
    else:
        click.echo(result)


# ---- stats (quick overview) ----

@main.command()
@click.option("--since", default="7d", help="Lookback period.")
def stats(since):
    """Quick stats for recent activity."""
    start = _parse_date(since)
    entries = read_entries(start=start)
    if not entries:
        click.echo("No entries found.")
        return

    from collections import Counter
    cats = Counter(e.category.value for e in entries)
    sources = Counter(e.source.value for e in entries)

    click.echo(f"Entries: {len(entries)}  (since {start.strftime('%Y-%m-%d')})")
    click.echo(f"Sources: {', '.join(f'{s}={c}' for s, c in sources.most_common())}")
    click.echo(f"Categories: {', '.join(f'{cat}={c}' for cat, c in cats.most_common())}")


# ---- list (recent entries) ----

@main.command("list")
@click.option("--since", default="7d", help="Lookback period (default: 7d).")
@click.option("-n", "--limit", default=20, help="Max entries to show.")
@click.option("--repo", default=None, help="Filter by repo (substring).")
@click.option("--category", default=None, help="Filter by category.")
def list_entries(since, limit, repo, category):
    """List recent work entries."""
    start = _parse_date(since)
    entries = read_entries(start=start, repo=repo, category=category)
    if not entries:
        click.echo("No entries found.")
        return

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    shown = entries[:limit]

    for e in shown:
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M")
        src = e.source.value
        repo_tag = f" ({e.repo})" if e.repo else ""
        cat = e.category.value
        click.echo(f"  {ts}  [{src}] [{cat}]{repo_tag}  {e.action[:80]}")

    if len(entries) > limit:
        click.echo(f"\n  ... {len(entries) - limit} more entries (use -n to show more)")


# ---- delete ----

@main.command()
@click.option("--since", default="30d", help="Lookback period to show entries from.")
@click.option("--id", "entry_id", default=None, help="Delete by entry ID directly (skip interactive picker).")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt.")
def delete(since, entry_id, yes):
    """Delete a worklog entry.

    Shows recent entries with numbers for easy selection.
    The entry is permanently removed from sessions.jsonl.
    The previous version is preserved in local git history.
    """
    if entry_id:
        # Direct delete by ID
        if not yes:
            click.confirm(f"Delete entry {entry_id}?", abort=True)
        if delete_entry(entry_id):
            click.echo(f"Deleted entry {entry_id}")
        else:
            click.echo(f"Entry {entry_id} not found.")
        return

    # Interactive: show numbered list and let user pick
    start = _parse_date(since)
    entries = read_entries(start=start)
    if not entries:
        click.echo("No entries found.")
        return

    entries.sort(key=lambda e: e.timestamp, reverse=True)
    shown = entries[:30]

    click.echo("\nRecent entries:\n")
    for i, e in enumerate(shown, 1):
        ts = e.timestamp.strftime("%Y-%m-%d %H:%M")
        src = e.source.value
        repo_tag = f" ({e.repo})" if e.repo else ""
        click.echo(f"  [{i:2d}]  {ts}  [{src}]{repo_tag}  {e.action[:70]}")

    click.echo()
    choice = click.prompt("Enter number to delete (or 'q' to cancel)", default="q")

    if choice.lower() == "q":
        click.echo("Cancelled.")
        return

    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(shown):
            click.echo("Invalid number.")
            return
    except ValueError:
        click.echo("Invalid input.")
        return

    target = shown[idx]
    click.echo(f"\n  {target.timestamp.strftime('%Y-%m-%d %H:%M')}  [{target.source.value}]  {target.action}")
    if target.details:
        click.echo(f"  Details: {target.details[:120]}...")

    if not yes:
        click.confirm("\nDelete this entry?", abort=True)

    if delete_entry(str(target.id)):
        click.echo("Deleted.")
    else:
        click.echo("Entry not found (may have already been deleted).")


# ---- exclude ----

@main.command()
@click.argument("action", type=click.Choice(["add", "remove", "list"]))
@click.option("--session-id", "-s", default=None, help="Session ID to exclude/include.")
@click.option("--from-list", is_flag=True, help="Pick a session interactively from recent entries.")
def exclude(action, session_id, from_list):
    """Manage excluded sessions (won't be re-imported by onboard).

    \b
    worklog exclude list              Show all excluded session IDs
    worklog exclude add -s <id>       Exclude a session by ID
    worklog exclude add --from-list   Pick from recent entries interactively
    worklog exclude remove -s <id>    Un-exclude a session
    """
    if action == "list":
        excludes = load_excludes()
        if not excludes:
            click.echo("No excluded sessions.")
        else:
            click.echo(f"Excluded sessions ({len(excludes)}):")
            for sid in sorted(excludes):
                click.echo(f"  {sid}")
        return

    if action == "add":
        if from_list:
            entries = read_entries()
            if not entries:
                click.echo("No entries found.")
                return
            entries.sort(key=lambda e: e.timestamp, reverse=True)
            shown = entries[:20]

            click.echo("\nRecent entries:\n")
            for i, e in enumerate(shown, 1):
                ts = e.timestamp.strftime("%Y-%m-%d %H:%M")
                sid = e.session_id or str(e.id)
                repo_tag = f" ({e.repo})" if e.repo else ""
                click.echo(f"  [{i:2d}]  {ts}{repo_tag}  {e.action[:60]}")
                click.echo(f"        session: {sid[:40]}")

            click.echo()
            choice = click.prompt("Enter number to exclude (or 'q' to cancel)", default="q")
            if choice.lower() == "q":
                click.echo("Cancelled.")
                return
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(shown):
                    click.echo("Invalid number.")
                    return
            except ValueError:
                click.echo("Invalid input.")
                return

            target = shown[idx]
            session_id = target.session_id or str(target.id)

        if not session_id:
            click.echo("Provide --session-id or use --from-list.")
            return

        add_exclude(session_id)
        click.echo(f"Excluded session: {session_id}")
        click.echo("This session won't be re-imported by 'worklog onboard'.")
        return

    if action == "remove":
        if not session_id:
            click.echo("Provide --session-id to un-exclude.")
            return
        if remove_exclude(session_id):
            click.echo(f"Un-excluded session: {session_id}")
        else:
            click.echo(f"Session {session_id} was not in the exclusion list.")


# ---- completions ----

@main.command("completions")
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]))
def completions(shell):
    """Generate shell completion script.

    Usage: eval "$(worklog completions bash)"
    """
    import os
    env_var = f"_{main.name.upper()}_COMPLETE"
    source_map = {"bash": "bash_source", "zsh": "zsh_source", "fish": "fish_source"}
    os.environ[env_var] = source_map[shell]
    try:
        main(standalone_mode=False)
    finally:
        os.environ.pop(env_var, None)


if __name__ == "__main__":
    main()
