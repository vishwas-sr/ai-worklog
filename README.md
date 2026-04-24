# worklog

[![CI](https://github.com/vishwas-sr/ai-worklog/actions/workflows/ci.yml/badge.svg)](https://github.com/vishwas-sr/ai-worklog/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

A local-first CLI that tracks and summarizes your work across AI/agentic sessions (GitHub Copilot, Claude Code, OpenAI Codex, Agency, VS Code Agentic CLI, git) for reviews, work journals, and self-assessment.

All data stays on your machine. No cloud services, no API keys, no telemetry.

---

## How It Works

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                  │
│                                                                      │
│  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐          │
│  │  VS Code     │  │  Claude   │  │  OpenAI  │  │  Git    │          │
│  │  Copilot &   │  │  Code     │  │  Codex   │  │  Repos  │          │
│  │  Agentic CLI │  │  CLI      │  │  CLI     │  │         │          │
│  └──────┬───────┘  └────┬─────┘  └────┬─────┘  └────┬────┘          │
│         │               │             │              │               │
│         └──────┬────────┘             │              │               │
│                │                      │              │               │
│         ┌──────┴───────┐              │              │               │
│         │   Agency     │              │              │               │
│         │ (MS internal)│              │              │               │
│         └──────┬───────┘              │              │               │
│                │                      │              │               │
│                ▼                      ▼              ▼               │
│                     CAPTURE LAYER                                    │
│                                                                      │
│  worklog onboard ──────────────────── Initial bulk import            │
│  worklog scan ─────────────────────── Periodic git scan              │
│  worklog log ──────────────────────── Manual entry                   │
│  worklog disable / enable ─────────── Pause / resume logging         │
│  auto-logger instructions ─────────── AI tools log during sessions   │
│                                                                      │
│                          ▼                                           │
│              ~/.local/share/worklog/sessions.jsonl                   │
│                 (append-only, git-versioned)                         │
│                          ▼                                           │
│                    OUTPUT LAYER                                      │
│                                                                      │
│  worklog summary ──── Markdown │ HTML │ CSV │ JSON │ Review │ Report │
│  worklog stats ────── Quick terminal overview                        │
│  worklog list ─────── Recent entries                                 │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### One-click setup with AI agent

The fastest way to set up worklog is to let an AI agent do it for you. Add this agent URL to your VS Code Copilot chat and ask it to "set up worklog":

```
https://raw.githubusercontent.com/vishwas-sr/ai-worklog/main/.github/agents/worklog-setup.agent.md
```

The agent will walk you through the entire setup — install the tool, ask which AI tools you use, configure auto-logging, import your existing sessions, and generate your first report. No manual steps needed.

To use it: open VS Code Copilot Chat → select the agent picker (`@`) → add the URL above as a custom agent → type "set up worklog".

### Prerequisites

- **Python 3.10+** — [download from python.org](https://www.python.org/downloads/) if not already installed. Verify with `python --version`.
- **pip** — included with Python. Verify with `pip --version`.

### Manual install

```bash
pip install git+https://github.com/vishwas-sr/ai-worklog.git

# or from source:
git clone https://github.com/vishwas-sr/ai-worklog.git
cd ai-worklog
pip install -e .
```

### Initialize

```bash
worklog init
# → Worklog initialized at /home/you/.local/share/worklog
```

### Log your work

```bash
# Manual entries — be specific for performance reviews
worklog log "Implemented circuit breaker pattern in PaymentService using Polly v8 to handle downstream API failures gracefully" -c feature -r payment-service -t "polly,resilience,circuit-breaker"
worklog log "Investigated and resolved OOM crashes in file-sync worker — root cause was undisposed BlobDownloadStreamingResult streams" -c bugfix -r file-sync -t "memory-leak,azure-sdk,blob-storage"
worklog log "Built KQL dashboard tracking p50/p95 API latency by endpoint with alerting thresholds" -c research -r analytics -t "kql,observability,latency"

# Import git history
worklog config --add-repo /path/to/your/repo
worklog config --author you@example.com
worklog scan --since 2w

# One-time bulk import of all AI sessions
worklog onboard
```

### View and export

```bash
# Quick overview
worklog stats --since 7d

# Recent entries
worklog list --since 7d

# Full summary
worklog summary --since 30d
worklog summary --since 3m -f html -o review.html
worklog summary --since 1m -f csv -o export.csv
```

---

## Supported Data Sources

| Source | Scanner | What it captures |
|--------|---------|-----------------|
| **VS Code Copilot Chat** | ✅ Automatic | Full conversations — prompts, responses, tool calls |
| **VS Code Agentic CLI** (`code chat`) | ✅ Automatic | Same as above — shares VS Code session storage |
| **VS Code Insiders** | ✅ Automatic | Same format, separate install detected |
| **Claude Code CLI** (`claude`) | ✅ Automatic | Session history with prompts and responses |
| **Claude Desktop** | ✅ Automatic | Shares storage with Claude Code CLI |
| **OpenAI Codex CLI** (`codex`) | ✅ Automatic | Session history with prompts and responses |
| **Agency** (Microsoft internal) | ✅ Automatic | Built on Copilot CLI + Claude Code — sessions captured via their scanners |
| **Git commits** | ✅ Via `worklog scan` | Commit messages, files changed, auto-categorized |
| **Copilot Memory** | ✅ Automatic | Persisted memory notes |
| **Auto-logger instructions** | ✅ Via instruction files | Copilot, Claude Code, and Codex auto-log during sessions |
| **Manual entries** | ✅ `worklog log` | Whatever you type |

---

## Platform Support

| Platform | Data Directory | VS Code Scanner | Claude Code Scanner | Codex CLI Scanner |
|----------|---------------|-----------------|---------------------|-------------------|
| **Linux** | `~/.local/share/worklog` | ✅ `~/.config/Code` | ✅ `~/.claude/` | ✅ `~/.codex/` |
| **macOS** | `~/Library/Application Support/worklog` | ✅ `~/Library/Application Support/Code` | ✅ `~/.claude/` | ✅ `~/.codex/` |
| **Windows** | `%LOCALAPPDATA%\worklog` (or OneDrive if detected) | ✅ `%APPDATA%\Code` | ✅ `%USERPROFILE%\.claude\` | ✅ `%USERPROFILE%\.codex\` |

Override the data directory with the `WORKLOG_DIR` environment variable:

```bash
export WORKLOG_DIR=~/my-custom-worklog
worklog init
```

VS Code Insiders is also supported automatically.

---

## Commands

### `worklog init`

Create the data directory and initialize local git versioning.

### `worklog log "<action>" [OPTIONS]`

Manually record a work entry.

| Option | Default | Description |
|--------|---------|-------------|
| `-c, --category` | `other` | `feature` `bugfix` `research` `review` `docs` `config` `refactor` `test` `meeting` `other` |
| `-s, --source` | `manual` | `vscode-copilot` `gh-cli` `git` `manual` |
| `-r, --repo` | — | Repository name |
| `-t, --tags` | — | Comma-separated tags |
| `-d, --details` | — | Longer description |

### `worklog list [OPTIONS]`

View recent entries in the terminal.

| Option | Default | Description |
|--------|---------|-------------|
| `--since` | `7d` | Lookback period |
| `-n, --limit` | `20` | Max entries |
| `--repo` | — | Filter by repo |
| `--category` | — | Filter by category |

### `worklog scan [OPTIONS]`

Import git commits from configured repos.

| Option | Default | Description |
|--------|---------|-------------|
| `--since` | `30d` | Start date (`YYYY-MM-DD` or relative: `7d`, `2w`, `3m`) |
| `--until` | now | End date |

Commits are auto-categorized using [conventional commit](https://www.conventionalcommits.org/) prefixes (`fix:` → bugfix, `feat:` → feature, `ci:` → config, etc.) with fallback to keyword matching.

### `worklog onboard [OPTIONS]`

One-time import of all existing session history. Scans VS Code Copilot chat sessions, Claude Code sessions, Codex CLI sessions, Copilot memory files, and git history.

| Option | Default | Description |
|--------|---------|-------------|
| `--since` | all | Only import after this date |
| `--dry-run` | off | Preview without writing |
| `--vscode/--no-vscode` | on | Include VS Code Copilot sessions |
| `--claude/--no-claude` | on | Include Claude Code sessions |
| `--codex/--no-codex` | on | Include Codex CLI sessions |
| `--memory/--no-memory` | on | Include Copilot memory |
| `--git/--no-git` | on | Include git commits |

### `worklog summary [OPTIONS]`

Generate a formatted work summary.

| Option | Default | Description |
|--------|---------|-------------|
| `--since` | `30d` | Start date |
| `--until` | now | End date |
| `-f, --format` | `markdown` | `markdown` `html` `csv` `json` `review` `report` |
| `-o, --output` | stdout | File path |
| `--source` | all | Filter by source |
| `--category` | all | Filter by category |
| `--repo` | all | Filter by repo (substring) |

### `worklog stats [--since 7d]`

Quick terminal stats for recent activity.

### `worklog config [OPTIONS]`

| Option | Description |
|--------|-------------|
| `--show` | Display current config |
| `--add-repo <path>` | Add git repo to scan |
| `--remove-repo <path>` | Remove git repo |
| `--author <email>` | Set git author filter |
| `--auto-commit/--no-auto-commit` | Toggle local git versioning |

### `worklog disable` / `worklog enable`

Pause and resume all logging. When disabled, write commands are blocked. Read-only commands (`summary`, `stats`, `list`, `config --show`) still work.

### `worklog status`

Show enabled/disabled state and security permissions.

### `worklog lock`

Restrict the data folder to owner-only access (NTFS ACLs on Windows, `chmod 700` on Unix). Applied automatically on first `init`.

### `worklog delete`

Delete a worklog entry interactively or by ID. Shows a numbered list of recent entries for easy selection.

```bash
worklog delete                # Interactive — pick from numbered list
worklog delete --id <uuid>    # Delete directly by entry ID
worklog delete --yes          # Skip confirmation prompt
```

Previous versions are always recoverable from local git history.

### `worklog exclude {add|remove|list}`

Manage excluded sessions — excluded sessions won't be re-imported by `worklog onboard`.

```bash
worklog exclude list                  # Show all excluded session IDs
worklog exclude add --from-list       # Pick a session interactively
worklog exclude add -s <session-id>   # Exclude by session ID
worklog exclude remove -s <session-id>  # Un-exclude a session
```

### `worklog completions <shell>`

Generate shell completion scripts. Supports `bash`, `zsh`, `fish`.

```bash
# Add to your .bashrc / .zshrc
eval "$(worklog completions bash)"
```

---

## Date Formats

All `--since` and `--until` options accept:

| Format | Example | Meaning |
|--------|---------|---------|
| Relative days | `7d` | Last 7 days |
| Relative weeks | `2w` | Last 2 weeks |
| Relative months | `3m` | Last ~90 days |
| Absolute | `2025-01-01` | Specific date |

---

## Data Model

Each entry in `sessions.jsonl` is a JSON line:

```json
{
  "id": "a1b2c3d4-...",
  "timestamp": "2026-04-16T14:30:00Z",
  "source": "vscode-copilot",
  "repo": "my-project",
  "action": "Implemented retry logic for blob uploads",
  "category": "feature",
  "complexity": "medium",
  "impact": "Reduced upload failures from 12% to 0.3% under peak load",
  "files": ["src/client.py", "tests/test_client.py"],
  "tags": ["python", "retry", "resilience"],
  "collaboration": ["reviewer: Jane Smith"],
  "details": "[Context] Uploads failing under load. [Thinking] Considered increasing timeout vs retry. [Steps] Implemented Polly retry with backoff. [Outcome] Failure rate dropped to 0.3%.",
  "duration_minutes": 45
}
```

| Field | Type | Description |
|-------|------|-------------|
| `source` | enum | `vscode-copilot`, `claude-code`, `codex-cli`, `gh-cli`, `git`, `manual` |
| `category` | enum | `feature`, `bugfix`, `research`, `review`, `docs`, `config`, `refactor`, `test`, `meeting`, `other` |
| `complexity` | enum | `trivial`, `low`, `medium`, `high`, `critical` |
| `impact` | string | One-sentence business/user impact — the "so what?" |
| `collaboration` | string[] | People or teams involved |
| `details` | string | Structured narrative with `[Context]`, `[Thinking]`, `[Steps]`, `[Outcome]`, `[Follow-up]` tags |
| `duration_minutes` | float | Estimated time spent |

---

## Storage

All data is stored locally in a single directory:

```
<data-dir>/
├── sessions.jsonl      ← Append-only work log (one JSON entry per line)
├── config.json         ← Configuration (repos, author, enabled state)
├── .git/               ← Local version history for undo/recovery
└── .gitignore
```

**Design principles:**

- **JSONL format** — one entry per line, atomic appends, crash-safe, easy to inspect and debug
- **Local git versioning** — every write is auto-committed so you can `git log` or `git diff` to see changes, or recover accidentally deleted entries. It never pushes anywhere.
- **No network calls** — the tool never makes HTTP requests. No telemetry, no analytics, no cloud sync.
- **Portable** — the entire data directory can be backed up, moved, or synced via any cloud drive (OneDrive, Dropbox, iCloud) without any tool-specific setup.

---

## Security

All data stays on your machine. Multiple layers protect your worklog:

- **Owner-only file permissions** — NTFS ACLs (Windows) or `chmod 700` (Unix) are applied automatically on `worklog init`. Re-apply anytime with `worklog lock`.
- **Pause logging** — `worklog disable` blocks all writes instantly. Resume with `worklog enable`.
- **No secrets stored** — no API keys, tokens, or credentials are ever written to the worklog.
- **No telemetry** — zero network calls, no analytics, no crash reporting, no phone-home.
- **Append-only log** — entries are never modified or deleted by the tool.
- **Audit trail** — local git history tracks every change to `sessions.jsonl`.

---

## Auto-Logging

Auto-logging works by placing an **instruction file** into each AI tool's config directory. When the AI tool starts a session, it reads these instructions and follows them — appending a JSON entry to `sessions.jsonl` after each significant action.

### How it works

Each AI coding tool supports persistent instructions that shape its behavior:

- **GitHub Copilot** reads `~/.github/copilot-instructions.md`
- **Claude Code** reads `~/.claude/CLAUDE.md`
- **OpenAI Codex** reads `~/.codex/AGENTS.md`

The instruction tells the AI to append one line of JSON to `sessions.jsonl` after completing work. The AI decides when to log based on a **hybrid strategy**:

- **Short sessions** (1-10 exchanges): log once at the end
- **Long sessions** (10+ exchanges): log a checkpoint every ~10 exchanges, plus a final summary
- **Always log immediately** after: code changes, builds/tests, research results, PR reviews, or documentation

### What gets logged

Each auto-logged entry is a single JSON line:

```json
{
  "source": "vscode-copilot",
  "action": "Implemented adaptive retry with exponential backoff for database connections",
  "category": "feature",
  "complexity": "medium",
  "impact": "Reduced connection failures from 8% to 0.1% during peak traffic",
  "files": ["src/db/connection_pool.py", "tests/test_connection_pool.py"],
  "tags": ["python", "database", "resilience", "retry"],
  "details": "[Context] Connection pool exhaustion during peak hours. [Thinking] Evaluated fixed delay vs exponential backoff vs circuit breaker. [Steps] Implemented backoff with jitter, added connection health checks. [Outcome] Failure rate dropped from 8% to 0.1% in load testing.",
  "duration_minutes": 45
}
```

The `details` field uses structured `[Section]` tags so worklog can parse and reformat them for different outputs (review docs, status reports, etc.):

| Tag | What it captures |
|-----|-----------------|
| `[Context]` | What triggered the work — problem, request, or goal |
| `[Thinking]` | User's reasoning, hypotheses, trade-offs considered |
| `[Steps]` | Chronological problem-solving journey, including dead ends |
| `[Outcome]` | Results with metrics, before/after numbers |
| `[Follow-up]` | Open questions and future work identified |

### Setup

`worklog init` installs the Copilot instruction by default. Claude Code and Codex are opt-in:

```bash
worklog init                    # Copilot only (default)
worklog init --claude           # Copilot + Claude Code
worklog init --codex            # Copilot + Codex
worklog init --claude --codex   # All three
```

| Tool | Flag | Instruction installed to |
|------|------|------------------------|
| **GitHub Copilot** (VS Code) | *always* | `~/.github/copilot-instructions.md` |
| **Claude Code** (CLI/Desktop) | `--claude` or auto-detected | `~/.claude/CLAUDE.md` |
| **OpenAI Codex** (CLI) | `--codex` or auto-detected | `~/.codex/AGENTS.md` |

Claude Code and Codex are also auto-detected — if `~/.claude/` or `~/.codex/` already exists on your machine, `worklog init` will install their instruction files automatically without needing the flag.

If you already have instruction files for these tools, worklog appends its logging instructions rather than overwriting. If the logging instructions are already present, it skips the file.

If you install a new tool later, just run `worklog init --codex` — it will set up auto-logging for it.

---

## Onboarding Walkthrough

Here's what a typical first-time setup looks like from start to finish:

**Step 1 — Install and initialize:**

```
$ pip install git+https://github.com/vishwas-sr/ai-worklog.git
$ worklog init
Worklog initialized at /home/you/.local/share/worklog
Data is stored locally with automatic git versioning.
Permissions: owner-only access enforced, sharing disabled.
```

**Step 2 — Import all existing AI sessions:**

```
$ worklog onboard --dry-run
Scanning VS Code Copilot chat sessions...
  Found 28 chat session(s)
Scanning Claude Code sessions...
  Found 3 Claude Code session(s)
Scanning Codex CLI sessions...
  Found 0 Codex CLI session(s)
Scanning Copilot memory files...
  Found 0 memory note(s)

============================================================
Total entries to import: 31
Date range: 2026-02-04 to 2026-04-17
By source: vscode-copilot=28, claude-code=3
By category: feature=8, research=6, bugfix=5, config=4, other=4, review=2, docs=2

Dry run — no entries written.

$ worklog onboard
Imported 31 entries into /home/you/.local/share/worklog/sessions.jsonl
```

**Step 3 — Add git repos and log manual work:**

```
$ worklog config --add-repo ~/projects/backend-api
Added repo: /home/you/projects/backend-api

$ worklog scan --since 2w
Scanning 1 git repo(s)...
  Found 14 commits.
Added 14 new entries.

$ worklog log "Implemented circuit breaker for payment gateway using Polly v8" \
    -c feature -r backend-api -t "polly,resilience,circuit-breaker"
Logged: Implemented circuit breaker for payment gateway using Polly v8
```

**Step 4 — View your work:**

```
$ worklog stats --since 30d
Entries: 22  (since 2026-03-23)
Sources: vscode-copilot=11, git=7, manual=4
Categories: feature=7, bugfix=4, review=2, test=2, refactor=2, research=1

$ worklog list --since 7d -n 5
  2026-04-22 18:42  [manual] [feature] (backend-api)  Implemented circuit breaker for payment gateway
  2026-04-22 13:40  [vscode-copilot] [feature] (worklog)  Added HTML and CSV export formatters
  2026-04-21 11:06  [vscode-copilot] [bugfix] (worklog)  Fixed off-by-one in deduplication logic
  2026-04-20 10:49  [git] [feature] (worklog)  Initial commit: CLI with scan, log, summary
  2026-04-20 09:32  [vscode-copilot] [feature] (worklog)  Created worklog CLI tool
```

**Step 5 — Generate reports:**

```
$ worklog summary --since 14d -f review
# Performance Review — Work Summary
**Period:** 2026-04-08 — 2026-04-22
**Total items:** 20
**Estimated time invested:** 8 hours

## backend-api
- **Implemented circuit breaker for payment gateway** [medium]
- **Implemented health check endpoints for all components** [medium]
- **Built functional test suite using Testcontainers** [medium] (120 min)
- **Researched Redis Cluster vs Sentinel for HA needs** [medium] (60 min)
...

$ worklog summary --since 30d -f html -o report.html
Summary written to report.html
```

---

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check worklog/
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for full guidelines.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `WORKLOG_DIR` | Override data directory path | Platform-specific (see above) |

---

## License

[MIT](LICENSE)
