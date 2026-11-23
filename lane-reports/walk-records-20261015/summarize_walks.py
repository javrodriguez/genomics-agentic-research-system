"""The CP6 walks' records summary (box lane, 15 Oct 2026, glitch-6b's ask after the fetch of walk/w-l4F8UdYQ): from the
committed records only, field names and non-secret values only, never transcript text. Per walk: route, the checker's
reasons, the grade, the watched list against walk_builders.watch_list's derivation at the same tree, budgets and
timings; account evidence from each turn's system/init and rate_limit_event records; served model and token sums
from the driver ledger's cost record.
Usage: python3 -I summarize_walks.py <records clone> <branch> <archived evals/gap-study-4 of that branch>"""
import collections, json, os, subprocess, sys
R, B, TREE = sys.argv[1:4]
sys.path.insert(0, TREE)
import variants  # noqa: E402
import walk_builders  # noqa: E402


def show(path):
    p = subprocess.run(["git", "-C", R, "show", f"{B}:evals/gap-study-4/{path}"], capture_output=True)
    return p.stdout if p.returncode == 0 else None


reg = json.loads(show("rehearsals/register.json"))
out, totals = [], collections.Counter()
for entry in reg["walks"]:
    w = entry["walk"]
    base = f"rehearsals/{w}"
    check = json.loads(show(f"{base}/check.json") or b"{}")
    grade = json.loads(show(f"{base}/grade.json") or b"{}")
    led = json.loads(show(f"{base}/driver-ledger.json") or b"{}")
    watched = json.loads(show(f"{base}/evidence/watched.json") or b"{}").get("paths")
    project = led.get("project")
    try:
        expected = walk_builders.watch_list({"task": entry["task"]}, project, "/w")
    except Exception as e:  # noqa: BLE001
        expected = f"not derivable: {type(e).__name__}"
    calls = (led.get("cost") or {}).get("calls") or []
    usage = collections.Counter()
    for c in calls:
        for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"):
            usage[k] += int((c.get("usage") or {}).get(k) or 0)
    totals.update(usage)
    served = sorted({c.get("model") for c in calls})
    inits, limits, starts = [], [], []
    for n in range(1, 10):
        raw = show(f"{base}/turn-{n}.jsonl")
        if raw is None:
            break
        lj = show(f"{base}/turn-{n}.jsonl.launch.json")
        if lj:
            starts.append(json.loads(lj).get("started_at"))
        for line in raw.decode("utf-8", "replace").splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("type") == "system" and r.get("subtype") == "init":
                tools = r.get("tools") or []
                inits.append({"apiKeySource": r.get("apiKeySource"), "model": r.get("model"),
                              "permissionMode": r.get("permissionMode"), "tools": tools,
                              "mcp_tools": [t for t in tools if str(t).startswith("mcp__")],
                              "mcp_servers": [{k: s.get(k) for k in ("name", "status")} if isinstance(s, dict) else s
                                              for s in (r.get("mcp_servers") or [])],
                              "plugins": [p.get("name") if isinstance(p, dict) else p for p in (r.get("plugins") or [])],
                              "agents": r.get("agents"), "skills": r.get("skills"),
                              "messaging_socket_path": "present" if r.get("messaging_socket_path") else "absent"})
            if r.get("type") == "rate_limit_event":
                i = r.get("rate_limit_info") or {}
                limits.append({k: i.get(k) for k in ("status", "rateLimitType", "overageStatus", "isUsingOverage")}
                              | {"utilization": {k: v.get("utilization") for k, v in (i.get("unifiedWindows") or {}).items()}})
    att = collections.Counter()
    tr = show(f"{base}/transcript.jsonl")
    for line in (tr or b"").decode("utf-8", "replace").splitlines():
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("type") == "attachment":
            att[(r.get("attachment") or {}).get("type")] += 1
    out.append({
        "walk": w, "cell": f"{entry['task']} {entry['half']} {entry['wording']} {entry['arm']} {entry['model']}",
        "route": check.get("route"), "route_refused": check.get("route_refused"),
        "checker_reasons": check.get("checker_reasons"), "events": check.get("events"),
        "graded": grade.get("graded"), "label": (grade.get("grade") or {}).get("label"),
        "expected": (grade.get("grade") or {}).get("expected"), "correct": (grade.get("grade") or {}).get("correct"),
        "not_graded_because": grade.get("why") if not grade.get("graded") else None,
        "watched_count": len(watched) if isinstance(watched, list) else None,
        "watched_matches_derivation": (sorted(watched) == sorted(expected)) if isinstance(expected, list) and
                                      isinstance(watched, list) else expected,
        "outcome": led.get("outcome"), "budget_s": led.get("budget_s"), "finalize_wait_s": led.get("finalize_wait_s"),
        "poll_s": led.get("poll_s"), "turns": [{k: t.get(k) for k in ("n", "exit", "end", "held")} for t in
                                                led.get("turns") or []],
        "turn_starts": starts, "num_turns": [t.get("num_turns") for t in (led.get("cost") or {}).get("turns") or []],
        "permission_mode": led.get("permission_mode"), "claude_version": led.get("claude_version"),
        "served_models": served, "calls": len(calls), "tokens": dict(usage),
        "init": inits, "rate_limit": limits, "auto_mode_attachments": att.get("auto_mode", 0),
        "attachment_types": dict(att)})
print(json.dumps({"branch": B, "walks": out, "token_totals": dict(totals)}, indent=1, sort_keys=True))
