---
description: "Automatically log work activity to ~/.worklog/sessions.jsonl for performance tracking"
applyTo: "**"
---

# Work Logger — Automatic Session Tracking

You MUST log your work to the user's worklog. These logs are used directly in performance reviews and self-assessments — write them as if your manager will read each entry.

## When to Log — Hybrid Strategy

Use a **hybrid event-driven + periodic checkpoint** approach based on session length:

### Short sessions (1-10 user messages)
Log **once at completion** — a single comprehensive entry covering the full task.

### Long sessions (10+ user messages)
Log **periodic checkpoints every ~10 user exchanges**, plus a **final summary entry** at the end:

- **Checkpoint entries** (category: same as the work, add tag `checkpoint`):
  - Lighter weight — 2-3 sentences in `details`
  - Capture progress so far, current direction, intermediate findings
  - Use `action` like: "Checkpoint: identified root cause of 429 errors in Cosmos partition design"
  - Set `complexity` to `low` (these are progress markers, not standalone deliverables)

- **Final summary entry** (at session end):
  - Full comprehensive entry with all structured `[Section]` tags
  - Rolls up the entire session journey including dead ends, pivots, and decisions
  - References the checkpoints implicitly through the narrative
  - Set `complexity` to the actual task complexity

### Always log immediately when:
- A significant code change is completed (file edit, refactor, bug fix, new feature)
- A build, test, or deployment is run
- A research question is answered or data analysis is completed
- A PR is created or reviewed
- Documentation or ADRs are written
- The user explicitly asks you to do something

### Counting user messages
Track the number of user messages in the current session. At around every 10th user message, if significant work has happened since the last log, write a checkpoint. At session end (or when the topic shifts significantly), write the final summary.

## How to Log

Append exactly ONE line of JSON to the worklog sessions file. The file location depends on the platform:
- **Linux**: `~/.local/share/worklog/sessions.jsonl`
- **macOS**: `~/Library/Application Support/worklog/sessions.jsonl`
- **Windows**: `%LOCALAPPDATA%\worklog\sessions.jsonl` (or `OneDrive\.worklog\sessions.jsonl` if it exists)

If the `WORKLOG_DIR` environment variable is set, use that directory instead.

Use the file editing tools available to you.

Each line must be a valid JSON object with this schema:

```json
{
  "id": "<uuid4>",
  "timestamp": "<ISO 8601 UTC>",
  "source": "vscode-copilot",
  "session_id": null,
  "repo": "<workspace folder name or null>",
  "action": "<performance-review-quality summary — see rules below>",
  "category": "<one of: feature, bugfix, research, review, docs, config, refactor, test, meeting, other>",
  "complexity": "<one of: trivial, low, medium, high, critical>",
  "impact": "<REQUIRED: one-sentence business/user impact statement — the 'so what?'>",
  "files": ["<list of ALL files changed>"],
  "tags": ["<technology, service, and domain tags>"],
  "collaboration": ["<people or teams involved, e.g. 'partner: Cosmos DB team', 'reviewer: Jane Smith'>"],
  "details": "<REQUIRED: structured narrative with [Section] tags — see rules below>",
  "duration_minutes": "<REQUIRED: estimated time spent — see rules below>"
}
```

## Rules for Writing Entries

### 1. Check if logging is enabled
Before logging, read `config.json` in the same directory. If `"enabled": false`, do NOT log.

### 2. Write the `action` as a performance review bullet point
- Start with a strong action verb (Implemented, Fixed, Investigated, Designed, Migrated, Optimized, Automated, Refactored)
- Include the **exact names** of services, tools, repos, APIs, tables, pipelines, and features — never abbreviate or genericize them
- State the **what** and **why** in one sentence

**Good examples:**
- `"Implemented adaptive retry policy with exponential backoff in PaymentService CosmosClientFactory to resolve 429 throttling during peak checkout"`
- `"Migrated content-pipeline evaluation step from GPT-4o to GPT-5, updating prompt templates and temperature settings"`
- `"Built SQL query in analytics-dashboard to compute average response-time trends from requests table over last 30 days"`
- `"Fixed memory leak in file-sync BlobDownloadHandler — StreamReader was not disposing underlying BlobDownloadStreamingResult"`

**Bad examples (too vague):**
- `"GPT 5 migration"` — which service? what was migrated? why?
- `"Connecting to prod db for data count"` — what was the outcome? what data?
- `"Made some changes"` — meaningless for performance review

### 3. The `details` field is REQUIRED — scale depth to session length
The detail level MUST be proportional to the length and complexity of the session. A longer session means the user invested more time thinking, debugging, iterating, and problem-solving — capture all of that.

**Scaling guide:**

| Session length | Detail level | Sentences | What to cover |
|---------------|-------------|-----------|---------------|
| Quick (1-5 exchanges) | Brief | 2-3 | Context, what was done, outcome |
| Medium (5-15 exchanges) | Moderate | 4-6 | + user's reasoning, alternatives considered, key decisions |
| Long (15-30 exchanges) | Detailed | 6-10 | + full debugging journey, dead ends tried, pivots made, multiple approaches evaluated |
| Deep (30+ exchanges) | Comprehensive | 10-15 | + every hypothesis tested, every tool/query used, timeline of discoveries, lessons learned, follow-up items identified |

For every entry, structure the `details` field using **[Section] tags**. These tags allow the tool to parse and reformat details for different outputs (review docs, status reports, etc.). Use these sections:

- **[Context]** What problem or goal prompted this work? What triggered it (incident, request, observation)?
- **[Thinking]** What was the user's hypothesis or reasoning? What options did they consider? What trade-offs did they weigh? Why did they choose this path over alternatives? What did they try that didn't work?
- **[Steps]** Walk through the key steps the user followed in chronological order — debugging steps, queries run, docs consulted, approaches tried and abandoned, intermediate findings, pivots, and breakthroughs. For long sessions, this should read like a problem-solving narrative.
- **[Outcome]** What was the result? What did it unblock? Include metrics, before/after numbers, or scope of impact.
- **[Follow-up]** (if any) What remaining work, open questions, or future improvements were identified?

For short sessions, you may combine sections. For long sessions, every section should be substantial.

**Short session example (3 exchanges):**
```
"details": "[Context] Needed to update Redis connection string for new premium-tier cluster. [Steps] Updated appsettings.INT.json and Key Vault reference in deploy/keyvault.bicep. [Outcome] Verified connectivity via health check endpoint after deployment."
```

**Long session example (25+ exchanges):**
```
"details": "The Scheduler Function App was hitting Cosmos DB 429 (TooManyRequests) errors during the 2am-4am scheduling window when ~50k jobs are queued. User started by checking App Insights dependency telemetry — confirmed 429s correlated with the /scheduleJob endpoint, peaking at 340 failures/min. Initial hypothesis was under-provisioned RUs (currently 4000 RU/s). User queried Cosmos DB metrics and found RU consumption was hitting 100% but only on the 'jobs-active' container, suggesting a hot partition rather than global RU shortage. Investigated partition key design — found all jobs for a given tenant land on the same partition, and tenant 'contoso-global' alone generates 40% of traffic. User considered three approaches: (1) increase RU to 10000 (+$580/mo), (2) redesign partition key to include job-type suffix, (3) implement client-side adaptive retry. Ruled out option 2 due to migration complexity and data volume (~8M docs). Chose option 3 as immediate fix with option 1 as fallback if retries aren't sufficient. Implemented retry policy using Polly v8 with exponential backoff (initial 200ms, max 30s, jitter factor 0.5). Also added per-partition-key RU tracking via a custom TelemetryInitializer to detect hot partitions proactively — this surfaces as a custom metric 'cosmos_ru_by_partition' in App Insights. Ran load test in INT simulating 50k jobs — 429 rate dropped from 12% to 0.3%. User noted that if 429s return above 2%, the team should revisit partition key redesign. Filed follow-up work item #4892 for partition key analysis."
```

### 4. Categorize precisely — never use "other" if a better category fits
- `feature` — new functionality, new endpoints, new UI
- `bugfix` — fixing broken behavior, crash fixes, data corruption fixes
- `research` — investigations, POCs, architecture spikes, data analysis, KQL queries
- `review` — code reviews, PR reviews, design reviews
- `docs` — documentation, ADRs, wiki updates, runbooks
- `config` — CI/CD, infrastructure, ARM/Bicep/Terraform, pipeline config
- `refactor` — restructuring code without changing behavior
- `test` — writing or updating tests
- `meeting` — planning, retro, 1:1s, architecture reviews
- `other` — ONLY if nothing else fits

### 5. Use rich, specific tags
Include tags for:
- **Technologies**: `cosmos-db`, `service-bus`, `redis`, `polly`, `durable-functions`, `kql`, `gpt-5`, `bicep`, `terraform`
- **Services/Projects**: use the actual repo or service names from the workspace
- **Domains**: `payments`, `analytics`, `infrastructure`, `auth`, `observability`, `data-pipeline`
- **Patterns**: `retry-policy`, `circuit-breaker`, `fan-out`, `testcontainers`

### 6. Include ALL files changed
List every file path that was created, modified, or deleted. Use relative paths from the repo root.

### 7. Log EARLY
If a task has multiple steps, log after each significant step. Don't wait until the end. If a session is interrupted, partial work should still be captured.

### 8. Append only
Never modify or delete existing entries. Create the file if it doesn't exist.

### 9. Estimate `duration_minutes` for every entry
Estimate how long the user spent on this task based on the session length and complexity:
- Count the number of user messages in the session — each exchange typically represents 2-5 minutes of thinking, reading, and typing
- Factor in complexity: debugging and research sessions have more thinking time between exchanges than config changes
- Quick sessions (1-5 exchanges) = 10-20 min
- Medium sessions (5-15 exchanges) = 30-60 min  
- Long sessions (15-30 exchanges) = 60-120 min
- Deep sessions (30+ exchanges) = 120-240 min
- Never leave it as `null` — an estimate is always better than nothing

## Example Entries

### Feature work (medium session ~12 exchanges)
```json
{"id": "a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d", "timestamp": "2026-04-16T14:30:00Z", "source": "vscode-copilot", "session_id": null, "repo": "payment-service", "action": "Implemented automatic retry pipeline for failed payment transactions using Durable Functions fan-out pattern", "category": "feature", "files": ["src/Orchestrators/RetryOrchestrator.cs", "src/Activities/RetryPaymentActivity.cs", "src/Models/RetryRequest.cs", "tests/RetryOrchestratorTests.cs"], "tags": ["payment-service", "durable-functions", "retry", "fan-out"], "details": "[Context] Support team reported ~8% of payment transactions failing silently during peak hours, requiring manual re-processing. [Thinking] User proposed automating with a retry pipeline. Evaluated two approaches: (1) timer-triggered function polling for failures, or (2) Durable Functions orchestrator triggered by the failure event. Chose option 2 for event-driven responsiveness. [Steps] Implemented RetryOrchestrator subscribing to the payment-failures Service Bus topic. Fans out to RetryPaymentActivity for each failed tx (batch up to 500). Added 3-retry dead-letter for persistent failures. Considered whether to notify the user after retry — deferred to follow-up. [Outcome] Integration tested with 50 synthetic failures — all retried within 30s. [Follow-up] Add user notification on successful retry.", "duration_minutes": 55}
```

### Research / Data Analysis (long session ~22 exchanges)
```json
{"id": "b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e", "timestamp": "2026-04-08T22:42:00Z", "source": "vscode-copilot", "session_id": null, "repo": "analytics-dashboard", "action": "Built SQL query to compute average response-time trends from requests table over last 30 days, broken down by endpoint", "category": "research", "files": ["queries/response-time-trends.sql"], "tags": ["sql", "analytics", "performance", "data-analysis"], "details": "[Context] Product team requested latency trend data to evaluate whether the March caching update improved response times. [Thinking] Started by exploring the requests table schema. First AVG(response_ms) returned unexpectedly high numbers — suspected outliers from health-check timeouts skewing results. [Steps] Added filter for response_ms < 30000 and computed p50/p95 percentiles. Joined with endpoints table for readable names. Built weekly breakdown. [Outcome] Results showed /api/checkout improved from 340ms to 180ms p50 post-cache-update, but /api/search remained flat at 450ms — flagged for investigation. [Follow-up] Share query with team and investigate /api/search latency.", "duration_minutes": 90}
```

### Bug Fix (deep session ~30 exchanges)
```json
{"id": "c3d4e5f6-a7b8-4c9d-0e1f-2a3b4c5d6e7f", "timestamp": "2026-04-12T13:24:00Z", "source": "vscode-copilot", "session_id": null, "repo": "file-sync-service", "action": "Fixed memory leak in BlobDownloadHandler caused by undisposed BlobDownloadStreamingResult streams", "category": "bugfix", "files": ["src/Handlers/BlobDownloadHandler.cs", "src/Extensions/StreamExtensions.cs", "tests/BlobDownloadHandlerTests.cs"], "tags": ["file-sync", "memory-leak", "blob-storage", "azure-sdk", "disposable"], "details": "[Context] Monitoring alert showed worker memory growing from 200MB to 2.4GB over 6 hours before OOM crash. [Thinking] First hypothesis: leak in message processing loop. Memory dumps showed large byte arrays in Azure.Storage.Blobs namespace, narrowing scope to BlobDownloadHandler. Considered simple 'using' block but stream was passed to async pipeline — needed 'await using'. [Steps] Traced allocations to DownloadAsync(). Read Azure SDK source — BlobDownloadStreamingResult.Content is a network stream requiring explicit dispose. Created StreamExtensions.ReadAndDisposeAsync() helper. Audited UploadHandler — confirmed it auto-disposes. Ran 24h soak test. [Outcome] Memory stays flat at ~220MB processing 12k files. Added regression test. [Follow-up] Filed work item for cross-service audit of this pattern.", "duration_minutes": 150}
```
