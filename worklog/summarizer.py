"""Build aggregated WorkSummary from a list of WorkEntry objects."""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from .models import WorkEntry, WorkSummary


def summarize(
    entries: list[WorkEntry],
    start: datetime,
    end: datetime,
    top_n: int = 15,
) -> WorkSummary:
    by_category: Counter[str] = Counter()
    by_source: Counter[str] = Counter()
    by_repo: Counter[str] = Counter()
    all_files: Counter[str] = Counter()
    all_tags: set[str] = set()

    for e in entries:
        by_category[e.category.value] += 1
        by_source[e.source.value] += 1
        if e.repo:
            by_repo[e.repo] += 1
        for f in e.files:
            all_files[f] += 1
        all_tags.update(e.tags)

    return WorkSummary(
        start=start,
        end=end,
        total_entries=len(entries),
        by_category=dict(by_category.most_common()),
        by_source=dict(by_source.most_common()),
        by_repo=dict(by_repo.most_common(top_n)),
        top_actions=[e.action for e in entries[:top_n]],
        top_files=[f for f, _ in all_files.most_common(top_n)],
        tags_used=sorted(all_tags),
        entries=entries,
    )
