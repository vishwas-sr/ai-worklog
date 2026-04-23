"""Deep scan all VS Code state.vscdb files for chat conversation content."""
import sqlite3
import json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"

for d in sorted(ws.iterdir()):
    db = d / "state.vscdb"
    if not db.exists():
        continue
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro&immutable=1", uri=True)
        cur = conn.cursor()
        # Find all large keys that might contain chat content
        cur.execute(
            "SELECT key, length(value) FROM ItemTable "
            "WHERE length(value) > 5000 "
            "ORDER BY length(value) DESC LIMIT 5"
        )
        rows = cur.fetchall()
        if rows:
            # Read workspace.json for repo name
            ws_json = d / "workspace.json"
            repo = "?"
            if ws_json.exists():
                try:
                    wdata = json.loads(ws_json.read_text(encoding="utf-8"))
                    folder = wdata.get("folder", wdata.get("workspace", ""))
                    repo = folder.split("/")[-1] if folder else "?"
                except Exception:
                    pass
            
            print(f"\n=== {d.name} ({repo}) ===")
            for key, sz in rows:
                print(f"  {key}: {sz:,} bytes")
                # Check if any key contains chat requests/responses
                if any(kw in key.lower() for kw in ["chat", "session", "interactive", "copilot", "agent"]):
                    cur.execute("SELECT value FROM ItemTable WHERE key = ?", (key,))
                    val = cur.fetchone()[0]
                    try:
                        data = json.loads(val)
                        # Look for conversation structure
                        if isinstance(data, dict):
                            for k, v in data.items():
                                if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                                    sample = v[0]
                                    if any(x in sample for x in ["message", "text", "response", "requests", "prompt"]):
                                        print(f"    >>> FOUND conversation data in '{k}': {len(v)} items")
                                        print(f"    >>> Sample keys: {list(sample.keys())[:10]}")
                                        if "requests" in sample:
                                            reqs = sample["requests"]
                                            print(f"    >>> {len(reqs)} requests in first session")
                                            if reqs:
                                                r = reqs[0]
                                                print(f"    >>> Request keys: {list(r.keys())[:10]}")
                                                msg = r.get("message", {})
                                                if isinstance(msg, dict):
                                                    txt = msg.get("text", "")
                                                    print(f"    >>> First user msg: {txt[:100]}")
                                                resp = r.get("response", [])
                                                if isinstance(resp, list) and resp:
                                                    print(f"    >>> Response parts: {len(resp)}")
                                                    for rp in resp[:2]:
                                                        if isinstance(rp, dict):
                                                            print(f"    >>>   Part keys: {list(rp.keys())[:8]}")
                                                            val_text = rp.get("value", "")
                                                            if isinstance(val_text, str) and val_text:
                                                                print(f"    >>>   Text: {val_text[:100]}")
                                elif isinstance(v, dict):
                                    for k2, v2 in v.items():
                                        if isinstance(v2, list) and len(v2) > 0 and isinstance(v2[0], dict):
                                            sample = v2[0]
                                            if any(x in sample for x in ["requests", "message", "prompt"]):
                                                print(f"    >>> FOUND in '{k}.{k2}': {len(v2)} items")
                                                print(f"    >>> Keys: {list(sample.keys())[:15]}")
                                                if "requests" in sample:
                                                    print(f"    >>> {len(sample['requests'])} requests")
                    except (json.JSONDecodeError, TypeError):
                        pass
        conn.close()
    except Exception as e:
        print(f"Error with {d.name}: {e}")
