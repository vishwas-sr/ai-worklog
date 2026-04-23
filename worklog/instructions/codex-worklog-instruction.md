# Work Logger — Automatic Session Tracking

You MUST log your work to the user's worklog after completing significant actions. These logs are used directly in performance reviews — write them as if your manager will read each entry.

## When to Log

- **Short sessions (1-10 user messages)**: Log once at completion.
- **Long sessions (10+ user messages)**: Log a checkpoint every ~10 exchanges, plus a final summary.
- **Always log immediately** when: a code change is completed, a build/test/deployment runs, a research question is answered, a PR is created/reviewed, or documentation is written.

## How to Log

Append exactly ONE line of JSON to the worklog sessions file:
- **Linux**: `~/.local/share/worklog/sessions.jsonl`
- **macOS**: `~/Library/Application Support/worklog/sessions.jsonl`
- **Windows**: `%LOCALAPPDATA%\worklog\sessions.jsonl` (or `OneDrive\.worklog\sessions.jsonl` if it exists)

If the `WORKLOG_DIR` environment variable is set, use that directory instead.

Before logging, read `config.json` in the same directory. If `"enabled": false`, do NOT log.

Each line must be a valid JSON object:

```json
{
  "id": "<uuid4>",
  "timestamp": "<ISO 8601 UTC>",
  "source": "codex-cli",
  "session_id": null,
  "repo": "<workspace folder name or null>",
  "action": "<performance-review-quality summary>",
  "category": "<one of: feature, bugfix, research, review, docs, config, refactor, test, meeting, other>",
  "complexity": "<one of: trivial, low, medium, high, critical>",
  "impact": "<REQUIRED: one-sentence business/user impact>",
  "files": ["<list of ALL files changed>"],
  "tags": ["<technology and domain tags>"],
  "collaboration": ["<people or teams involved>"],
  "details": "<REQUIRED: structured with [Context] [Thinking] [Steps] [Outcome] [Follow-up] tags>",
  "duration_minutes": "<REQUIRED: estimated minutes>"
}
```

## Rules

1. **`action`** — Start with a strong verb. Include exact names of services, tools, APIs. State what and why in one sentence.
2. **`details`** — Scale depth to session length. Use `[Context]`, `[Thinking]`, `[Steps]`, `[Outcome]`, `[Follow-up]` section tags. Include dead ends, iterations, and reasoning.
3. **`impact`** — One sentence: the "so what?" with metrics where possible.
4. **`duration_minutes`** — Estimate from exchange count (~4 min per exchange).
5. **`complexity`** — `trivial` (1-2 exchanges), `low` (3-5), `medium` (5-15), `high` (15-30), `critical` (30+).
6. **Categories** — Never use `other` if a better fit exists.
7. **Tags** — Include technologies, services, domains, and patterns.
8. **Files** — List every file created, modified, or deleted.
9. **Append only** — Never modify or delete existing entries.
