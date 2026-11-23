import json, os
H = "/home/javier/gap4-held-walks/w-E91dWW6d/w041"
lines = open(H + "/transcript.jsonl").read().splitlines()
fn = json.loads(lines[57])["attachment"]["filename"]
print("FILE:", fn)
base = os.path.basename(fn)
for i, l in enumerate(lines, 1):
    r = json.loads(l)
    if r.get("type") == "assistant":
        for c in (r.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                inp = c.get("input") or {}
                if c["name"] == "Read":
                    print(i, "Read", inp.get("file_path"), "offset" in inp or "limit" in inp)
                elif c["name"] == "Bash":
                    cmd = inp.get("command", "")
                    print(i, "Bash", "names-file" if (base in cmd) else "-", "background" if inp.get("run_in_background") else "",
                          "runs:", " ".join(w for w in cmd.split() if w.endswith(".py") or w in ("finalize", "link", "init", "validate"))[:120])
s1 = json.load(open(H + "/evidence/snapshots/pre-1.json")); s2 = json.load(open(H + "/evidence/snapshots/post-1.json"))
def ent(s):
    out = {}
    for e in s["entries"]:
        p = e.get("path") if isinstance(e, dict) else None
        if p and p.endswith(base): out[p] = {k: e.get(k) for k in ("mtime", "mtime_ns", "size", "sha256") if k in e}
    return out
print("pre-1", s1.get("taken_at"), ent(s1)); print("post-1", s2.get("taken_at"), ent(s2))
print("entry keys:", sorted(s1["entries"][0]) if s1["entries"] and isinstance(s1["entries"][0], dict) else None)
