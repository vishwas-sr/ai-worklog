"""Inspect the memento/interactive-session data for actual conversation content."""
import sqlite3
import json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"

# Check the QEPE workspace (largest interactive-session at 64KB)
target = "a672d09af7a4d6e29dc59f00c18935d3"
db = ws / target / "state.vscdb"

conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()
cur.execute("SELECT value FROM ItemTable WHERE key = ?", ("memento/interactive-session",))
row = cur.fetchone()
data = json.loads(row[0])

# Explore structure
def explore(obj, prefix="", depth=0):
    if depth > 4:
        return
    if isinstance(obj, dict):
        for k, v in list(obj.items())[:10]:
            if isinstance(v, (dict, list)):
                size = len(json.dumps(v))
                print(f"{'  '*depth}{prefix}{k}: {type(v).__name__} ({size:,} chars)")
                explore(v, f"{k}.", depth+1)
            else:
                val_str = str(v)[:80]
                print(f"{'  '*depth}{prefix}{k}: {type(v).__name__} = {val_str}")
    elif isinstance(obj, list):
        print(f"{'  '*depth}{prefix}[list of {len(obj)}]")
        if len(obj) > 0:
            if isinstance(obj[0], dict):
                print(f"{'  '*depth}  First item keys: {list(obj[0].keys())[:15]}")
                explore(obj[0], "[0].", depth+1)
            elif isinstance(obj[0], str):
                print(f"{'  '*depth}  First: {obj[0][:100]}")

explore(data)
conn.close()
