"""Extract actual conversations from chatSessions JSONL."""
import json
from pathlib import Path

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"
session_file = ws / "6670fe4bd8b8307349284159bb488c2d" / "chatSessions" / "796b36ee-fecd-4087-ac90-95b45b47fa2b.jsonl"

entries = []
with open(session_file, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass

# Show metadata
meta = [e for e in entries if e.get("kind") == 0]
if meta:
    m = meta[0]["v"]
    print(f"Session: {m.get('sessionId', '?')}")
    print(f"Created: {m.get('creationDate', '?')}")
    print(f"Title: {m.get('responderUsername', '?')}")

# Show first few request/response pairs
prompts = [e for e in entries if e.get("kind") == 1]
responses = [e for e in entries if e.get("kind") == 2]

print(f"\nTotal prompts (kind=1): {len(prompts)}")
print(f"Total responses (kind=2): {len(responses)}")

# Show first 3 exchanges
for i in range(min(3, len(prompts))):
    print(f"\n{'='*60}")
    print(f"EXCHANGE {i+1}")
    print(f"{'='*60}")
    
    # User prompt
    user_text = prompts[i]["v"]
    if isinstance(user_text, str):
        print(f"USER: {user_text[:200]}")
    elif isinstance(user_text, dict):
        print(f"USER (dict): {json.dumps(user_text)[:200]}")
    
    # Response
    if i < len(responses):
        resp = responses[i]["v"]
        if isinstance(resp, list):
            print(f"RESPONSE: {len(resp)} parts")
            for j, part in enumerate(resp[:3]):
                if isinstance(part, dict):
                    print(f"  Part {j} keys: {list(part.keys())[:10]}")
                    # Try to find text
                    for key in ["value", "text", "content", "message"]:
                        if key in part:
                            val = part[key]
                            if isinstance(val, str):
                                print(f"  Part {j}.{key}: {val[:150]}")
                            break
                elif isinstance(part, str):
                    print(f"  Part {j}: {part[:150]}")
        elif isinstance(resp, str):
            print(f"RESPONSE: {resp[:200]}")
