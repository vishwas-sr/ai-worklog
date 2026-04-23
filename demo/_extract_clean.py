"""Extract clean conversation pairs from chatSessions JSONL."""
import json
from pathlib import Path
from datetime import datetime, timezone

ws = Path.home() / "AppData" / "Roaming" / "Code" / "User" / "workspaceStorage"

# Try a smaller session from QEPE
target_ws = "a672d09af7a4d6e29dc59f00c18935d3"  # QEPE
sessions_dir = ws / target_ws / "chatSessions"

for sf in sorted(sessions_dir.iterdir())[:1]:
    print(f"=== {sf.name} ({sf.stat().st_size:,} bytes) ===\n")
    
    entries = []
    with open(sf, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    
    # Extract metadata
    meta = next((e["v"] for e in entries if e.get("kind") == 0), {})
    created_ms = meta.get("creationDate", 0)
    created = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc) if created_ms else None
    session_id = meta.get("sessionId", "?")
    
    # Build conversation
    prompts = []
    responses = []
    for e in entries:
        kind = e.get("kind")
        v = e.get("v")
        if kind == 1:
            if isinstance(v, str):
                prompts.append(v)
            elif isinstance(v, dict) and "value" in v:
                prompts.append(f"[user action: {v['value']}]")
        elif kind == 2:
            if isinstance(v, list):
                # Extract text content from response parts
                texts = []
                tool_calls = []
                for part in v:
                    if isinstance(part, dict):
                        if "value" in part and isinstance(part["value"], str):
                            texts.append(part["value"])
                        elif "invocationMessage" in part:
                            msg = part.get("pastTenseMessage") or part.get("invocationMessage") or ""
                            if isinstance(msg, str):
                                tool_calls.append(msg[:80])
                resp_text = " ".join(texts) if texts else None
                responses.append({
                    "text": resp_text,
                    "tool_calls": tool_calls,
                    "timestamp": next((p.get("timestamp") for p in v if isinstance(p, dict) and "timestamp" in p), None),
                })
    
    print(f"Session ID: {session_id}")
    print(f"Created: {created}")
    print(f"Exchanges: {len(prompts)} prompts, {len(responses)} responses")
    print()
    
    # Show all exchanges
    for i in range(min(len(prompts), 8)):
        print(f"--- Exchange {i+1} ---")
        print(f"  USER: {prompts[i][:120]}")
        if i < len(responses):
            r = responses[i]
            if r["tool_calls"]:
                print(f"  TOOLS: {len(r['tool_calls'])} calls")
                for tc in r["tool_calls"][:2]:
                    print(f"    - {tc}")
            if r["text"]:
                print(f"  RESPONSE: {r['text'][:150]}")
            else:
                print(f"  RESPONSE: [no text, {len(r.get('tool_calls',[]))} tool calls only]")
        print()
