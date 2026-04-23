# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.3.0] - 2026-04-22

### Added
- Claude Code session scanner — reads `~/.claude/` session files automatically
- `claude-code` source type for entries from Claude Code CLI and Desktop
- `--claude/--no-claude` flag for `worklog onboard`
- `complexity` field (`trivial`, `low`, `medium`, `high`, `critical`) for entries
- `impact` field for one-sentence business impact statements
- `collaboration` field for tracking people/teams involved
- Structured `[Context]/[Thinking]/[Steps]/[Outcome]/[Follow-up]` details format
- `review` output format — performance review bullet points grouped by repo
- `report` output format — status report grouped by category with highlights
- HTML dashboard with stats cards, CSS bar charts, and styled activity timeline
- Session duration estimation from exchange count
- Complexity estimation from exchange count + tool calls
- VS Code chatSessions JSONL parser — reads full conversation content instead of SQLite titles
- Hybrid checkpoint logging strategy in auto-logger instruction

### Changed
- Scanner now reads `chatSessions/*.jsonl` files directly (was SQLite `state.vscdb` title-only index)
- HTML output is a proper styled dashboard (was raw pre-formatted text)
- CSV export includes complexity, impact, collaboration, duration columns
- Onboard scans Claude Code sessions alongside VS Code and git

### Removed
- SQLite dependency for VS Code session scanning (now pure JSON file parsing)

## [0.2.0] - 2026-04-20

### Added
- Cross-platform support (Windows, macOS, Linux) via `platformdirs`
- `WORKLOG_DIR` environment variable for custom data directory
- `worklog list` command to view recent entries
- `worklog completions` command for bash/zsh/fish shell completions
- `worklog disable` / `worklog enable` to pause/resume logging
- `worklog status` shows enabled state + permission status
- `worklog lock` for owner-only file permissions
- VS Code Insiders edition support in scanner
- Config validation with automatic defaults merging
- Comprehensive test suite
- GitHub Actions CI pipeline
- MIT license, CONTRIBUTING.md, CHANGELOG.md

### Changed
- Data directory auto-detected per platform (was hardcoded to OneDrive)
- VS Code scanner uses cross-platform paths (was Windows-only)
- SQLite opened in immutable/read-only mode to avoid locking
- HTML formatter uses `html.escape()` (was manual string replacement)
- Date parsing provides user-friendly error messages
- Config loading is resilient to corrupted JSON
- Git scanner warns on missing repos instead of silently skipping
- Removed `jinja2` dependency (unused)

### Fixed
- HTML output XSS vulnerability from manual escaping
- Silent data loss on malformed JSONL entries (now logged)
- Crash on invalid date input (now shows helpful message)
- Git init failure blocking worklog initialization

## [0.1.0] - 2026-04-14

### Added
- Initial release
- `worklog init`, `log`, `scan`, `onboard`, `summary`, `stats`, `config` commands
- VS Code Copilot chat session scanner
- Git commit scanner
- Markdown, HTML, CSV, JSON output formatters
- Local git versioning of worklog data
- Copilot auto-logging instruction file
