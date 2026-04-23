<#
.SYNOPSIS
    Polished demo script for the worklog CLI tool.
    Designed to be recorded with terminalizer for team presentation.
#>

function Write-Banner {
    param([string]$Text)
    $line = "-" * 58
    Write-Host ""
    Write-Host "  +$line+" -ForegroundColor DarkCyan
    Write-Host "  |  $Text" -ForegroundColor Cyan
    Write-Host "  +$line+" -ForegroundColor DarkCyan
    Write-Host ""
}

function Write-Cmd {
    param([string]$Cmd)
    Write-Host "  > " -ForegroundColor Green -NoNewline
    Write-Host $Cmd -ForegroundColor White
    Write-Host ""
}

function Pause-Demo {
    param([int]$Ms = 1500)
    Start-Sleep -Milliseconds $Ms
}

# ============================================================
Clear-Host
Write-Host ""
Write-Host "  +=========================================================+" -ForegroundColor Magenta
Write-Host "  |                                                         |" -ForegroundColor Magenta
Write-Host "  |   worklog  --  Track and Summarize Your Work Sessions   |" -ForegroundColor Magenta
Write-Host "  |   Local-first CLI * Git * Copilot * Summaries           |" -ForegroundColor Magenta
Write-Host "  |                                                         |" -ForegroundColor Magenta
Write-Host "  +=========================================================+" -ForegroundColor Magenta
Write-Host ""
Write-Host "  A CLI tool that tracks work across AI/agentic sessions" -ForegroundColor DarkGray
Write-Host "  for performance reviews, work journals, and self-assessment." -ForegroundColor DarkGray
Write-Host ""
Pause-Demo 2500

# ---- Step 1: Help ----
Write-Banner "1. Available Commands"
Write-Cmd "worklog --help"
worklog --help
Pause-Demo 2000

# ---- Step 2: Init ----
Write-Banner "2. Initialize Worklog (data stored on OneDrive)"
Write-Cmd "worklog init"
worklog init
Pause-Demo 2000

# ---- Step 3: Manual log ----
Write-Banner "3. Manually Log a Work Entry"
Write-Cmd 'worklog log "Deployed Scheduler hotfix to UAT" -c bugfix -r Juno.Scheduler -t deploy,hotfix'
worklog log "Deployed Scheduler hotfix to UAT" -c bugfix -r Juno.Scheduler -t deploy,hotfix
Pause-Demo 1500

Write-Cmd 'worklog log "Sprint retro -- discussed on-call improvements" -c meeting -t sprint'
worklog log "Sprint retro -- discussed on-call improvements" -c meeting -t sprint
Pause-Demo 2000

# ---- Step 4: Stats ----
Write-Banner "4. Quick Stats Overview"
Write-Cmd "worklog stats --since 30d"
worklog stats --since 30d
Pause-Demo 2500

# ---- Step 5: Summary (Markdown) ----
Write-Banner "5. Generate Work Summary (Markdown)"
Write-Cmd "worklog summary --since 14d"
worklog summary --since 14d
Pause-Demo 3000

# ---- Step 6: Config ----
Write-Banner "6. Configure Git Repos to Scan"
Write-Cmd "worklog config --show"
worklog config --show
Pause-Demo 2000

# ---- Closing ----
Write-Host ""
Write-Host "  +=========================================================+" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  |   [ok] All data stays local (OneDrive for backup)       |" -ForegroundColor Green
Write-Host "  |   [ok] No cloud services or API keys needed             |" -ForegroundColor Green
Write-Host "  |   [ok] Exports to Markdown, HTML, CSV, JSON             |" -ForegroundColor Green
Write-Host "  |   [ok] Auto-scans git history + VS Code Copilot chats   |" -ForegroundColor Green
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  |   pip install -e .  ->  worklog init  ->  done!         |" -ForegroundColor Yellow
Write-Host "  |                                                         |" -ForegroundColor Green
Write-Host "  +=========================================================+" -ForegroundColor Green
Write-Host ""
