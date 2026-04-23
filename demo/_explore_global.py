"""Check global state DB for chat/session content."""
import sqlite3, json
from pathlib import Path

base = Path.home() / "AppData" / "Roaming" / "Code" / "User"
gdb = base / "globalStorage" / "state.vscdb"
conn = sqlite3.connect(str(gdb))
cur = conn.cursor()

# Find relevant keys
cur.execute(
    "SELECT key, length(value) FROM ItemTable "
    "WHERE key LIKE '%chat%' OR key LIKE '%session%' OR key LIKE '%copilot%' "
    "ORDER BY length(value) DESC LIMIT 20"
)
print("=== Global state.vscdb ===")
for k, sz in cur.fetchall():
    print(f"  {k}: {sz:,} bytes")

# Check the chat session index for full data
cur.execute("SELECT value FROM ItemTable WHERE key = 'chat.ChatSessionStore.index'")
row = cur.fetchone()
if row:
    data = json.loads(row[0])
    entries = data.get("entries", {})
    print(f"\nChat sessions in global DB: {len(entries)}")
    for sid, info in list(entries.items())[:3]:
        print(f"  {sid}: title={info.get('title', '?')[:60]}")
        print(f"    keys: {list(info.keys())[:10]}")
        # Check if there's actual content
        if "requests" in info:
            print(f"    requests: {len(info['requests'])}")

# Check for separate session content storage
cur.execute("SELECT key, length(value) FROM ItemTable ORDER BY length(value) DESC LIMIT 5")
print("\n=== Largest keys ===")
for k, sz in cur.fetchall():
    print(f"  {k}: {sz:,} bytes")

conn.close()

# Check for session files on disk
for pattern in ["sessions", "chat-sessions", "copilot"]:
    for p in base.rglob(f"*{pattern}*"):
        if p.is_file() and p.stat().st_size > 1000:
            print(f"\nFile: {p.relative_to(base)} ({p.stat().st_size:,} bytes)")
