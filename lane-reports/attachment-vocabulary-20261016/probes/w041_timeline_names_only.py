import json, sys
H = "/home/javier/gap4-held-walks/w-E91dWW6d/w041"
lines = open(H + "/transcript.jsonl").read().splitlines()
rec = json.loads(lines[57])
att = rec.get("attachment", {})
fn = att.get("filename")
print("line 58 keys:", sorted(rec), "attachment keys:", sorted(att), "type:", att.get("type"), "filename:", fn,
      "snippet_len:", len(att.get("snippet") or ""), "timestamp:", rec.get("timestamp"))
events = []
for i, l in enumerate(lines, 1):
    try: r = json.loads(l)
    except Exception: continue
    ts = r.get("timestamp")
    if r.get("type") == "assistant":
        for c in (r.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                inp = c.get("input") or {}
                events.append((i, ts, "tool_use", c.get("name"), "touches_file=%s" % (fn in json.dumps(inp)),
                               "background=%s" % bool(inp.get("run_in_background")), "id=" + c.get("id", "")[-6:]))
    elif r.get("type") == "user":
        m = (r.get("message") or {}).get("content")
        if isinstance(m, list):
            for c in m:
                if c.get("type") == "tool_result":
                    events.append((i, ts, "tool_result", "id=" + str(c.get("tool_use_id", ""))[-6:]))
        elif isinstance(m, str) and "task-notification" in m:
            events.append((i, ts, "task-notification (user record)"))
    elif r.get("type") == "attachment":
        events.append((i, ts, "attachment", (r.get("attachment") or {}).get("type")))
    elif r.get("type") not in (None,):
        if r.get("type") in ("queue-operation", "system"):
            events.append((i, ts, r.get("type"), r.get("subtype") or r.get("operation")))
for e in events: print(*e)
w = json.load(open(H + "/evidence/watched.json"))
print("watched has file:", fn in json.dumps(w))
for snap in ("pre-1", "post-1"):
    s = json.load(open(H + f"/evidence/snapshots/{snap}.json"))
    txt = json.dumps(s)
    print(snap, "names the file:", fn in txt or (fn.split("/")[-1] in txt), "top keys:", sorted(s)[:8] if isinstance(s, dict) else type(s).__name__)
