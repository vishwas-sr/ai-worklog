"""Inspect Copilot CLI session-state events.jsonl format."""
import json
from collections import Counter
from pathlib import Path

session_dir = Path.home() / ".copilot" / "session-state" / "d8e71a07-68ad-46d4-83c2-f347706da5d3"
events_file = session_dir / "events.jsonl"

types = Counter()
user_msgs = []
assistant_msgs = []
all_events = []

with open(events_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            e = json.loads(line)
            all_events.append(e)
            t = e.get("type", "")
            types[t] += 1
        except json.JSONDecodeError:
            pass

print(f"Total events: {len(all_events)}")
print(f"\nEvent types:")
for t, c in types.most_common():
    print(f"  {t}: {c}")

# Show user message events
print(f"\n--- User messages ---")
for e in all_events:
    t = e.get("type", "")
    data = e.get("data", {})
    if t == "message.user":
        text = data.get("text", data.get("content", ""))
        if isinstance(text, str):
            print(f"  [{e['timestamp'][:19]}] {text[:120]}")
    elif "user" in t.lower() and "message" in t.lower():
        print(f"  [{t}] {json.dumps(data)[:120]}")

# Show assistant response events
print(f"\n--- Assistant responses ---")
for e in all_events:
    t = e.get("type", "")
    data = e.get("data", {})
    if t == "message.assistant":
        text = data.get("text", data.get("content", ""))
        if isinstance(text, str):
            print(f"  [{e['timestamp'][:19]}] {text[:150]}")
        elif isinstance(text, list):
            for p in text[:2]:
                if isinstance(p, dict) and "text" in p:
                    print(f"  [{e['timestamp'][:19]}] {p['text'][:150]}")

# Show session info
print(f"\n--- Session metadata ---")
for e in all_events:
    t = e.get("type", "")
    data = e.get("data", {})
    if t == "session.start":
        print(f"  Session ID: {data.get('sessionId')}")
        print(f"  Started: {data.get('startTime')}")
        print(f"  Producer: {data.get('producer')}")
    elif t == "session.resume":
        print(f"  CWD: {data.get('context', {}).get('cwd')}")
    elif t == "session.shutdown":
        print(f"  Lines added: {data.get('codeChanges', {}).get('linesAdded')}")
        print(f"  Lines removed: {data.get('codeChanges', {}).get('linesRemoved')}")
        print(f"  Files modified: {data.get('codeChanges', {}).get('filesModified', [])[:5]}")
        print(f"  Total tokens: {data.get('currentTokens')}")

# Check workspace.yaml
ws = session_dir / "workspace.yaml"
if ws.exists():
    print(f"\n--- workspace.yaml ---")
    print(ws.read_text(encoding="utf-8")[:200])
