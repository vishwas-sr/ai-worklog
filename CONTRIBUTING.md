# Contributing to worklog

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/vishwas-sr/ai-worklog.git
cd worklog
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
pytest --cov=worklog --cov-report=term-missing
```

## Code Style

This project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check worklog/
ruff format worklog/
```

## Making Changes

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Make your changes
4. Add or update tests as needed
5. Run `pytest` and `ruff check` to verify
6. Commit with a descriptive message
7. Push and open a Pull Request

## Commit Messages

Use clear, descriptive commit messages:

- `fix: handle corrupted config.json gracefully`
- `feat: add worklog export command`
- `docs: update README with Linux setup`
- `test: add CLI integration tests`

## Reporting Issues

- Use [GitHub Issues](https://github.com/vishwas-sr/ai-worklog/issues)
- Include your OS, Python version, and steps to reproduce
- Attach relevant error output

## Architecture

```
worklog/
├── cli.py           ← Click CLI commands (entry point)
├── models.py        ← Pydantic data models
├── storage.py       ← JSONL I/O, config, permissions
├── scanners.py      ← Git log scanner
├── vscode_scanner.py← VS Code SQLite session scanner
├── summarizer.py    ← Aggregation logic
└── formatters.py    ← Output formatters (Markdown, HTML, CSV, JSON)
```

Key design decisions:
- **JSONL over SQLite** — append-only, no corruption risk, easy to debug
- **platformdirs** — cross-platform data directory resolution
- **No network calls** — the tool never phones home
- **Optional git versioning** — local `.git` in data dir for undo/recovery
