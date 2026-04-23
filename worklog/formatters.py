"""Output formatters: markdown, HTML, CSV, JSON."""
from __future__ import annotations

import csv
import html as html_mod
import io
import json
from datetime import datetime

from .models import WorkSummary


def to_markdown(summary: WorkSummary) -> str:
    lines: list[str] = []
    lines.append(f"# Work Summary")
    lines.append(f"**Period:** {_fmt(summary.start)} — {_fmt(summary.end)}")
    lines.append(f"**Total items:** {summary.total_entries}")
    lines.append("")

    if summary.by_category:
        lines.append("## By Category")
        for cat, count in summary.by_category.items():
            lines.append(f"- **{cat}**: {count}")
        lines.append("")

    if summary.by_source:
        lines.append("## By Source")
        for src, count in summary.by_source.items():
            lines.append(f"- **{src}**: {count}")
        lines.append("")

    if summary.by_repo:
        lines.append("## By Repository")
        for repo, count in summary.by_repo.items():
            lines.append(f"- **{repo}**: {count}")
        lines.append("")

    if summary.top_files:
        lines.append("## Most Touched Files")
        for f in summary.top_files:
            lines.append(f"- `{f}`")
        lines.append("")

    if summary.tags_used:
        lines.append("## Tags")
        lines.append(", ".join(f"`{t}`" for t in summary.tags_used))
        lines.append("")

    # Detailed log grouped by date
    lines.append("## Activity Log")
    entries_by_date: dict[str, list] = {}
    for e in summary.entries:
        day = e.timestamp.strftime("%Y-%m-%d")
        entries_by_date.setdefault(day, []).append(e)

    for day in sorted(entries_by_date, reverse=True):
        lines.append(f"\n### {day}")
        for e in entries_by_date[day]:
            time_str = e.timestamp.strftime("%H:%M")
            src_tag = f"[{e.source.value}]"
            repo_tag = f" ({e.repo})" if e.repo else ""
            lines.append(f"- **{time_str}** {src_tag}{repo_tag} {e.action}")
            if e.details:
                lines.append(f"  > {e.details}")

    return "\n".join(lines) + "\n"


def to_html(summary: WorkSummary) -> str:
    """Render a styled HTML dashboard with stats cards, charts, and timeline."""
    from collections import Counter

    period = f"{_fmt(summary.start)} — {_fmt(summary.end)}"
    total_min = sum(e.duration_minutes or 0 for e in summary.entries)
    hours_str = f"{total_min / 60:.0f}h" if total_min > 0 else "—"
    repos_count = len(summary.by_repo)

    # Complexity breakdown
    complexity_counts = Counter(
        e.complexity.value for e in summary.entries if hasattr(e, "complexity") and e.complexity
    )

    # Build category bar chart data
    max_cat = max(summary.by_category.values()) if summary.by_category else 1

    cat_bars = ""
    cat_colors = {
        "feature": "#4CAF50", "bugfix": "#f44336", "research": "#2196F3",
        "review": "#9C27B0", "docs": "#FF9800", "config": "#607D8B",
        "refactor": "#00BCD4", "test": "#8BC34A", "meeting": "#FFC107", "other": "#9E9E9E",
    }
    for cat, count in summary.by_category.items():
        pct = (count / max_cat) * 100
        color = cat_colors.get(cat, "#9E9E9E")
        cat_bars += f'<div class="bar-row"><span class="bar-label">{cat}</span><div class="bar-track"><div class="bar-fill" style="width:{pct}%;background:{color}"></div></div><span class="bar-value">{count}</span></div>\n'

    # Source breakdown
    source_items = ""
    for src, count in summary.by_source.items():
        source_items += f'<span class="tag">{src}: {count}</span> '

    # Repo breakdown
    repo_items = ""
    for repo, count in summary.by_repo.items():
        repo_items += f'<span class="tag">{repo}: {count}</span> '

    # Complexity pills
    complexity_pills = ""
    cx_colors = {"critical": "#d32f2f", "high": "#f57c00", "medium": "#1976d2", "low": "#388e3c", "trivial": "#9e9e9e"}
    for cx, count in complexity_counts.most_common():
        color = cx_colors.get(cx, "#9e9e9e")
        complexity_pills += f'<span class="pill" style="background:{color}">{cx}: {count}</span> '

    # Activity timeline
    entries_by_date: dict[str, list] = {}
    for e in summary.entries:
        day = e.timestamp.strftime("%Y-%m-%d")
        entries_by_date.setdefault(day, []).append(e)

    timeline_html = ""
    for day in sorted(entries_by_date, reverse=True):
        entries = entries_by_date[day]
        timeline_html += f'<div class="day-group"><h3>{day}</h3>\n'
        for e in entries:
            time_str = e.timestamp.strftime("%H:%M")
            cat = e.category.value
            color = cat_colors.get(cat, "#9E9E9E")
            repo_tag = f' <span class="entry-repo">{e.repo}</span>' if e.repo else ""
            cx = e.complexity.value if hasattr(e, "complexity") and e.complexity else ""
            cx_badge = f' <span class="cx-badge" style="background:{cx_colors.get(cx, "#ccc")}">{cx}</span>' if cx else ""
            dur = f' <span class="dur">{e.duration_minutes:.0f}m</span>' if e.duration_minutes else ""

            impact_line = ""
            if hasattr(e, "impact") and e.impact:
                impact_html = html_mod.escape(e.impact)
                impact_line = f'<div class="entry-impact">{impact_html}</div>'

            details_html = ""
            if e.details:
                sections = _parse_details_sections(e.details)
                for key, val in sections.items():
                    if key == "_raw":
                        details_html += f'<p>{html_mod.escape(val)}</p>'
                    else:
                        details_html += f'<p><strong>{html_mod.escape(key)}:</strong> {html_mod.escape(val)}</p>'

            # Show collaboration if present
            collab_html = ""
            if hasattr(e, "collaboration") and e.collaboration:
                collab_html = '<div class="entry-collab">👥 ' + ", ".join(html_mod.escape(c) for c in e.collaboration) + '</div>'

            action_escaped = html_mod.escape(e.action)
            tags_html = " ".join(f'<span class="tag-sm">{html_mod.escape(t)}</span>' for t in e.tags)

            # If no details, make action more prominent with a "no details" note
            no_detail_note = ""
            if not e.details and not (hasattr(e, "impact") and e.impact):
                no_detail_note = '<div class="entry-note">ℹ️ Imported from session history — no detailed description available</div>'

            timeline_html += f'''<div class="entry">
  <div class="entry-header">
    <span class="entry-time">{time_str}</span>
    <span class="entry-cat" style="background:{color}">{cat}</span>{repo_tag}{cx_badge}{dur}
  </div>
  <div class="entry-action">{action_escaped}</div>
  {impact_line}
  {collab_html}
  <div class="entry-details">{details_html}</div>
  <div class="entry-tags">{tags_html}</div>
  {no_detail_note}
</div>\n'''
        timeline_html += "</div>\n"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Work Summary — {period}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
         background: #f5f5f5; color: #1a1a1a; line-height: 1.6; }}
  .container {{ max-width: 960px; margin: 0 auto; padding: 2rem 1rem; }}
  h1 {{ font-size: 1.8rem; font-weight: 700; margin-bottom: 0.25rem; }}
  h2 {{ font-size: 1.2rem; font-weight: 600; margin: 1.5rem 0 0.75rem; color: #333; }}
  h3 {{ font-size: 1rem; font-weight: 600; color: #555; margin: 1rem 0 0.5rem;
        padding-bottom: 0.25rem; border-bottom: 1px solid #e0e0e0; }}
  .subtitle {{ color: #666; font-size: 0.95rem; margin-bottom: 1.5rem; }}

  /* Stats cards */
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: #fff; border-radius: 8px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); text-align: center; }}
  .stat-value {{ font-size: 2rem; font-weight: 700; color: #0078d4; }}
  .stat-label {{ font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }}

  /* Bar chart */
  .chart {{ background: #fff; border-radius: 8px; padding: 1.25rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 1.5rem; }}
  .bar-row {{ display: flex; align-items: center; margin: 0.4rem 0; }}
  .bar-label {{ width: 80px; font-size: 0.85rem; color: #555; text-align: right; padding-right: 0.75rem; }}
  .bar-track {{ flex: 1; height: 22px; background: #f0f0f0; border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .bar-value {{ width: 30px; font-size: 0.85rem; color: #555; padding-left: 0.5rem; font-weight: 600; }}

  /* Tags & pills */
  .tag {{ display: inline-block; background: #e8f0fe; color: #1a73e8; padding: 2px 10px;
          border-radius: 12px; font-size: 0.8rem; margin: 2px; }}
  .pill {{ display: inline-block; color: #fff; padding: 2px 10px; border-radius: 12px;
           font-size: 0.75rem; margin: 2px; font-weight: 600; }}
  .tag-sm {{ display: inline-block; background: #f0f0f0; color: #666; padding: 1px 8px;
             border-radius: 8px; font-size: 0.75rem; margin: 1px; }}

  /* Timeline */
  .day-group {{ margin-bottom: 1.5rem; }}
  .entry {{ background: #fff; border-radius: 8px; padding: 1rem 1.25rem; margin: 0.5rem 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-left: 3px solid #0078d4; }}
  .entry-header {{ display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.4rem; }}
  .entry-time {{ font-size: 0.8rem; color: #888; font-family: monospace; }}
  .entry-cat {{ display: inline-block; color: #fff; padding: 1px 8px; border-radius: 10px;
                font-size: 0.75rem; font-weight: 600; }}
  .entry-repo {{ font-size: 0.8rem; color: #1a73e8; font-weight: 600; }}
  .cx-badge {{ display: inline-block; color: #fff; padding: 1px 8px; border-radius: 10px;
               font-size: 0.7rem; font-weight: 600; }}
  .dur {{ font-size: 0.75rem; color: #888; }}
  .entry-action {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 0.3rem; }}
  .entry-impact {{ font-size: 0.85rem; color: #2e7d32; font-style: italic; margin-bottom: 0.3rem;
                   padding: 0.3rem 0.5rem; background: #e8f5e9; border-radius: 4px; }}
  .entry-details {{ font-size: 0.85rem; color: #555; }}
  .entry-details p {{ margin: 0.3rem 0; }}
  .entry-details strong {{ color: #333; }}
  .entry-tags {{ margin-top: 0.4rem; }}
  .entry-collab {{ font-size: 0.82rem; color: #5e35b1; margin-bottom: 0.3rem; }}
  .entry-note {{ font-size: 0.8rem; color: #999; margin-top: 0.4rem; font-style: italic; }}

  @media (max-width: 600px) {{
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
    .stat-value {{ font-size: 1.5rem; }}
  }}
</style>
</head>
<body>
<div class="container">
  <h1>Work Summary</h1>
  <div class="subtitle">{period}</div>

  <div class="stats">
    <div class="stat-card"><div class="stat-value">{summary.total_entries}</div><div class="stat-label">Entries</div></div>
    <div class="stat-card"><div class="stat-value">{hours_str}</div><div class="stat-label">Time Invested</div></div>
    <div class="stat-card"><div class="stat-value">{repos_count}</div><div class="stat-label">Repositories</div></div>
    <div class="stat-card"><div class="stat-value">{len(summary.by_category)}</div><div class="stat-label">Categories</div></div>
  </div>

  <div class="chart">
    <h2>By Category</h2>
    {cat_bars}
  </div>

  <div style="margin-bottom:1.5rem">
    <h2>Sources</h2>{source_items}
  </div>
  <div style="margin-bottom:1.5rem">
    <h2>Repositories</h2>{repo_items}
  </div>
  {"<div style='margin-bottom:1.5rem'><h2>Complexity</h2>" + complexity_pills + "</div>" if complexity_pills else ""}

  <h2>Activity Timeline</h2>
  {timeline_html}
</div>
</body>
</html>
"""


def to_csv(summary: WorkSummary) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "timestamp", "source", "repo", "category", "complexity",
        "action", "impact", "files", "tags", "collaboration",
        "details", "duration_minutes",
    ])
    for e in summary.entries:
        writer.writerow([
            e.timestamp.isoformat(),
            e.source.value,
            e.repo or "",
            e.category.value,
            e.complexity.value if e.complexity else "",
            e.action,
            e.impact or "",
            "; ".join(e.files),
            "; ".join(e.tags),
            "; ".join(e.collaboration),
            e.details or "",
            e.duration_minutes or "",
        ])
    return buf.getvalue()


def to_json(summary: WorkSummary) -> str:
    return summary.model_dump_json(indent=2)


# ---------------------------------------------------------------------------
# Structured details parser
# ---------------------------------------------------------------------------

_SECTION_TAGS = ["Context", "Thinking", "Steps", "Outcome", "Follow-up"]


def _parse_details_sections(details: str | None) -> dict[str, str]:
    """Parse [Section] tags from a details string into a dict.

    Only recognized tags are treated as section headers.
    Returns e.g. {"Context": "...", "Outcome": "..."}.
    Falls back to {"_raw": details} if no tags found.
    """
    if not details:
        return {}

    import re

    known_tags = {"Context", "Thinking", "Steps", "Outcome", "Follow-up"}
    # Match [Tag] only for known tags
    pattern = r"\[(" + "|".join(re.escape(t) for t in known_tags) + r")\]\s*"

    parts = re.split(pattern, details)
    # parts alternates: [preamble, tag1, content1, tag2, content2, ...]

    sections: dict[str, str] = {}
    if parts[0].strip():
        sections["_preamble"] = parts[0].strip()

    i = 1
    while i < len(parts) - 1:
        tag = parts[i].strip()
        content = parts[i + 1].strip()
        if tag and content:
            sections[tag] = content
        i += 2

    if not sections:
        sections["_raw"] = details
    return sections


# ---------------------------------------------------------------------------
# Review format — performance review bullet points
# ---------------------------------------------------------------------------

def to_review(summary: WorkSummary) -> str:
    """Format entries as performance-review-ready bullet points.

    Groups by repo, shows impact + action, sorted by complexity.
    """
    lines: list[str] = []
    lines.append(f"# Performance Review — Work Summary")
    lines.append(f"**Period:** {_fmt(summary.start)} — {_fmt(summary.end)}")
    lines.append(f"**Total items:** {summary.total_entries}")

    # Total time
    total_min = sum(e.duration_minutes or 0 for e in summary.entries)
    if total_min > 0:
        hours = total_min / 60
        lines.append(f"**Estimated time invested:** {hours:.0f} hours")
    lines.append("")

    # Complexity breakdown
    from collections import Counter
    complexity_counts = Counter(
        e.complexity.value for e in summary.entries if e.complexity
    )
    if complexity_counts:
        lines.append("## Complexity Breakdown")
        for c, n in complexity_counts.most_common():
            lines.append(f"- **{c}**: {n}")
        lines.append("")

    # Group by repo
    entries_by_repo: dict[str, list] = {}
    for e in summary.entries:
        repo = e.repo or "General"
        entries_by_repo.setdefault(repo, []).append(e)

    complexity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "trivial": 4}

    for repo in sorted(entries_by_repo):
        lines.append(f"## {repo}")
        entries = sorted(
            entries_by_repo[repo],
            key=lambda e: complexity_order.get(
                e.complexity.value if e.complexity else "medium", 2
            ),
        )
        for e in entries:
            # Impact line (bold) or fall back to action
            bullet = e.impact or e.action
            complexity_tag = f"[{e.complexity.value}]" if e.complexity else ""
            duration_tag = f" ({e.duration_minutes:.0f} min)" if e.duration_minutes else ""

            lines.append(f"- **{bullet}** {complexity_tag}{duration_tag}")

            # If impact exists, show action as sub-line
            if e.impact and e.action != e.impact:
                lines.append(f"  - {e.action}")

            # Show outcome from structured details
            sections = _parse_details_sections(e.details)
            outcome = sections.get("Outcome")
            if outcome:
                lines.append(f"  - *Outcome:* {outcome}")

            # Collaboration
            if e.collaboration:
                lines.append(f"  - *Collaboration:* {', '.join(e.collaboration)}")

        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Report format — weekly/monthly status report
# ---------------------------------------------------------------------------

def to_report(summary: WorkSummary) -> str:
    """Format entries as a status report grouped by date and category."""
    lines: list[str] = []
    lines.append(f"# Status Report")
    lines.append(f"**Period:** {_fmt(summary.start)} — {_fmt(summary.end)}")
    lines.append("")

    # Key highlights (high/critical complexity items)
    highlights = [
        e for e in summary.entries
        if e.complexity and e.complexity.value in ("high", "critical")
    ]
    if highlights:
        lines.append("## Key Highlights")
        for e in highlights:
            impact = e.impact or e.action
            repo_tag = f" ({e.repo})" if e.repo else ""
            lines.append(f"- {impact}{repo_tag}")
        lines.append("")

    # By category
    category_entries: dict[str, list] = {}
    for e in summary.entries:
        category_entries.setdefault(e.category.value, []).append(e)

    category_labels = {
        "feature": "Features Delivered",
        "bugfix": "Bugs Fixed",
        "research": "Research & Analysis",
        "review": "Reviews",
        "docs": "Documentation",
        "config": "Infrastructure & Config",
        "refactor": "Refactoring",
        "test": "Testing",
        "meeting": "Meetings & Planning",
        "other": "Other",
    }

    for cat, label in category_labels.items():
        entries = category_entries.get(cat, [])
        if not entries:
            continue
        lines.append(f"## {label}")
        for e in entries:
            repo_tag = f" ({e.repo})" if e.repo else ""
            lines.append(f"- {e.action}{repo_tag}")
            sections = _parse_details_sections(e.details)
            context = sections.get("Context")
            outcome = sections.get("Outcome")
            if context:
                lines.append(f"  - *Context:* {context}")
            if outcome:
                lines.append(f"  - *Result:* {outcome}")
        lines.append("")

    # Follow-ups
    followups = []
    for e in summary.entries:
        sections = _parse_details_sections(e.details)
        fu = sections.get("Follow-up")
        if fu:
            repo_tag = f" ({e.repo})" if e.repo else ""
            followups.append(f"- {fu}{repo_tag}")
    if followups:
        lines.append("## Follow-up Items")
        lines.extend(followups)
        lines.append("")

    return "\n".join(lines) + "\n"


FORMATTERS: dict[str, callable] = {
    "markdown": to_markdown,
    "md": to_markdown,
    "html": to_html,
    "csv": to_csv,
    "json": to_json,
    "review": to_review,
    "report": to_report,
}


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")
