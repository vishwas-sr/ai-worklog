"""Study the chatSessions JSONL format to understand all entry kinds and structure."""
import json
from pathlib import Path
from collections import Counter

# Read a session file
ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"

# Use the current worklog-tool workspace session
session_file = ws / "6670fe4bd8b8307349284159bb488c2d" / "chatSessions" / "796b36ee-fecd-4087-ac90-95b45b47fa2b.jsonl"

kinds = Counter()
samples = {}

with open(session_file, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            kind = entry.get("kind", "?")
            kinds[kind] += 1
            if kind not in samples:
                samples[kind] = entry
        except json.JSONDecodeError:
            pass

print(f"Total lines: {sum(kinds.values())}")
print(f"\nEntry kinds:")
for k, c in kinds.most_common():
    print(f"  {k}: {c}")

print("\n" + "="*60)
for kind, sample in samples.items():
    print(f"\n--- KIND: {kind} ---")
    v = sample.get("v", {})
    if isinstance(v, dict):
        for key in list(v.keys())[:15]:
            val = v[key]
            if isinstance(val, str):
                print(f"  {key}: {val[:150]}")
            elif isinstance(val, (int, float, bool)):
                print(f"  {key}: {val}")
            elif isinstance(val, list):
                print(f"  {key}: list[{len(val)}]")
                if val and isinstance(val[0], dict):
                    print(f"    [0] keys: {list(val[0].keys())[:10]}")
                    # Look for text content
                    for subk in ["text", "value", "content", "message"]:
                        if subk in val[0]:
                            txt = str(val[0][subk])
                            print(f"    [0].{subk}: {txt[:120]}")
            elif isinstance(val, dict):
                print(f"  {key}: dict keys={list(val.keys())[:8]}")
    elif isinstance(v, str):
        print(f"  v (str): {v[:200]}")
    elif isinstance(v, list):
        print(f"  v (list): {len(v)} items")
