"""Search every key in every state.vscdb for conversation content patterns."""
import sqlite3
import json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"

# Check the worklog-tool workspace (current session's workspace)
target = "6670fe4bd8b8307349284159bb488c2d"
db = ws / target / "state.vscdb"

conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
cur = conn.cursor()

# Get ALL keys and scan for anything with conversation-like structure
cur.execute("SELECT key, length(value) FROM ItemTable ORDER BY length(value) DESC")
for key, sz in cur.fetchall():
    if sz < 500:
        continue
    cur2 = conn.cursor()
    cur2.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
    raw = cur2.fetchone()[0]
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Check if it contains conversation-like strings
        if isinstance(raw, str) and any(x in raw.lower() for x in ["response", "user message", "assistant"]):
            print(f"TEXT KEY {key}: {sz:,} bytes — contains conversation keywords")
        continue
    
    raw_str = json.dumps(data)
    # Look for response content patterns
    has_response = '"response"' in raw_str and ('"text"' in raw_str or '"value"' in raw_str)
    has_request = '"request"' in raw_str or '"message"' in raw_str
    has_content = '"content"' in raw_str
    
    if has_response or (has_request and has_content):
        print(f"\n>>> KEY: {key} ({sz:,} bytes)")
        # Dig in
        if isinstance(data, dict):
            for k in data:
                v = data[k]
                v_str = json.dumps(v) if not isinstance(v, str) else v
                if len(v_str) > 200 and ('"response"' in v_str or '"content"' in v_str):
                    print(f"    Sub-key '{k}': {len(v_str):,} chars")
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        print(f"    First item keys: {list(v[0].keys())[:15]}")

# Also check global DB
print("\n\n=== GLOBAL DB ===")
gdb = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "globalStorage" / "state.vscdb"
conn2 = sqlite3.connect(f"file:{gdb}?mode=ro&immutable=1", uri=True)
cur3 = conn2.cursor()
cur3.execute("SELECT key, length(value) FROM ItemTable WHERE length(value) > 1000 ORDER BY length(value) DESC LIMIT 20")
for key, sz in cur3.fetchall():
    cur4 = conn2.cursor()
    cur4.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
    raw = cur4.fetchone()[0]
    try:
        data = json.loads(raw)
        raw_str = json.dumps(data)
        if '"response"' in raw_str or '"requests"' in raw_str:
            print(f">>> {key}: {sz:,} bytes — HAS response/requests data")
    except Exception:
        pass

conn.close()
conn2.close()
