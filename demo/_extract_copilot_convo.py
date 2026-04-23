"""Extract conversation from Copilot CLI session-state events.jsonl."""
import json
from pathlib import Path

session_dir = Path.home() / ".copilot" / "session-state" / "d8e71a07-68ad-46d4-83c2-f347706da5d3"

events = []
with open(session_dir / "events.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass

# Extract conversation pairs
for e in events:
    t = e.get("type", "")
    data = e.get("data", {})
    ts = e.get("timestamp", "")[:19]

    if t == "user.message":
        content = data.get("content", "")
        print(f"\nUSER [{ts}]: {content[:200]}")

    elif t == "assistant.message":
        content = data.get("content", "")
        if isinstance(content, str):
            print(f"\nASSISTANT [{ts}]: {content[:200]}")
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        print(f"\nASSISTANT [{ts}]: {part['text'][:200]}")
                    elif part.get("type") == "tool_use":
                        print(f"\nTOOL [{ts}]: {part.get('name', '?')}({json.dumps(part.get('input', {}))[:100]})")

    elif t == "tool.execution_complete":
        result = data.get("result", "")
        if isinstance(result, str) and len(result) > 10:
            print(f"  TOOL RESULT: {result[:120]}...")
