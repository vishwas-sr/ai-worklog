"""Explore VS Code SQLite DB to find chat content storage."""
import sqlite3
import json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"
for d in sorted(ws.iterdir())[-10:]:
    db = d / "state.vscdb"
    if not db.exists():
        continue
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute(
        "SELECT key FROM ItemTable WHERE key LIKE '%chat%' OR key LIKE '%agent%' OR key LIKE '%copilot%' ORDER BY key"
    )
    keys = [r[0] for r in cur.fetchall()]
    if keys:
        print(f"\n=== {d.name} ===")
        for k in keys[:25]:
            cur.execute("SELECT length(value) FROM ItemTable WHERE key=?", (k,))
            sz = cur.fetchone()[0]
            print(f"  {k} ({sz:,} bytes)")
        conn.close()
        break
    conn.close()
