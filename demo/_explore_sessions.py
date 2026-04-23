"""Explore VS Code chat session content structure."""
import sqlite3, json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"
for d in sorted(ws.iterdir())[-10:]:
    db = d / "state.vscdb"
    if not db.exists():
        continue
    conn = sqlite3.connect(str(db))
    cur = conn.cursor()
    cur.execute("SELECT value FROM ItemTable WHERE key = ?", ("memento/interactive-session",))
    row = cur.fetchone()
    if not row:
        conn.close()
        continue
    data = json.loads(row[0])
    copilot = data.get("history", {}).get("copilot", [])
    print(f"Sessions: {len(copilot)}")
    for i, session in enumerate(copilot[:3]):
        print(f"\n--- Session {i} ---")
        print(f"Keys: {list(session.keys())[:15]}")
        title = session.get("title", session.get("name", "?"))
        print(f"Title: {title}")
        reqs = session.get("requests", [])
        print(f"Requests (exchanges): {len(reqs)}")
        for j, req in enumerate(reqs[:3]):
            msg = req.get("message", {})
            text = msg.get("text", "")
            print(f"  [{j}] User: {text[:120]}")
            resp = req.get("response", req.get("result", {}))
            if isinstance(resp, dict):
                resp_text = resp.get("value", resp.get("text", ""))
                if isinstance(resp_text, str):
                    print(f"  [{j}] Response: {resp_text[:120]}")
                elif isinstance(resp_text, list) and resp_text:
                    first = resp_text[0] if isinstance(resp_text[0], str) else str(resp_text[0])[:120]
                    print(f"  [{j}] Response: {first}")
    conn.close()
    break
