from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Source(str, Enum):
    VSCODE_COPILOT = "vscode-copilot"
    CLAUDE_CODE = "claude-code"
    CODEX_CLI = "codex-cli"
    GH_CLI = "gh-cli"
    GIT = "git"
    MANUAL = "manual"


class Category(str, Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    RESEARCH = "research"
    REVIEW = "review"
    DOCS = "docs"
    CONFIG = "config"
    REFACTOR = "refactor"
    TEST = "test"
    MEETING = "meeting"
    OTHER = "other"


class Complexity(str, Enum):
    TRIVIAL = "trivial"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: Source
    session_id: Optional[str] = None
    repo: Optional[str] = None
    action: str
    category: Category = Category.OTHER
    complexity: Complexity = Complexity.MEDIUM
    impact: Optional[str] = None
    files: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    details: Optional[str] = None
    collaboration: list[str] = Field(default_factory=list)
    duration_minutes: Optional[float] = None


class WorkSummary(BaseModel):
    """Aggregated summary over a time period."""
    start: datetime
    end: datetime
    total_entries: int = 0
    by_category: dict[str, int] = Field(default_factory=dict)
    by_source: dict[str, int] = Field(default_factory=dict)
    by_repo: dict[str, int] = Field(default_factory=dict)
    top_actions: list[str] = Field(default_factory=list)
    top_files: list[str] = Field(default_factory=list)
    tags_used: list[str] = Field(default_factory=list)
    entries: list[WorkEntry] = Field(default_factory=list)
