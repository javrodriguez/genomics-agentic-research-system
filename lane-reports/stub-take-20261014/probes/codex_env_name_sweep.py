"""The environment-name sweep of the pinned Codex binary (glitch-06, 14 Oct 2026), run on athena as javier. The
binary is copied out of the pinned take-o image (box/codex/image.lock image_id) with `docker create` + `docker cp`,
never run; the container is removed. No `strings` on athena, so the printable-run extraction is done here, the same
rule as `strings -a -n 4` (runs of 4+ printable ASCII bytes, tab included). Every match of
(CODEX|OPENAI|AWS|AZURE|ANTHROPIC|GOOGLE)_[A-Z0-9_]+ is recorded with the byte after it (to see a run-together
boundary) and up to two short contexts. Prints one JSON record; the binary is deleted with its folder by the caller.
Usage: python3 -I codex_env_name_sweep.py <image id> <work folder>"""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
BIN = "/usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex"
ENV = dict(os.environ, DOCKER_HOST="unix:///run/user/1000/docker.sock")
def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=300)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout.strip()[:200], "stderr": p.stderr.strip()[:300]}
steps = []
create = run(["docker", "create", "--pull=never", "--network", "none", IMAGE, "true"])
steps.append(create)
cid = create["stdout"]
out = os.path.join(WORK, "codex.bin")
if create["rc"] == 0 and re.fullmatch(r"[0-9a-f]{64}", cid):
    try:
        steps.append(run(["docker", "cp", f"{cid}:{BIN}", out]))
    finally:
        steps.append(run(["docker", "rm", cid]))
data = open(out, "rb").read() if os.path.isfile(out) else b""
PREFIX = re.compile(rb"(CODEX|OPENAI|AWS|AZURE|ANTHROPIC|GOOGLE)_[A-Z0-9_]+")
RUNS = re.compile(rb"[\x20-\x7e\t]{4,}")
names = {}
for r in RUNS.finditer(data):
    s = r.group()
    for m in PREFIX.finditer(s):
        raw = m.group().decode()
        after = s[m.end():m.end() + 1].decode()
        e = names.setdefault(raw, {"count": 0, "next_bytes": {}, "contexts": []})
        e["count"] += 1
        e["next_bytes"][after or "<end>"] = e["next_bytes"].get(after or "<end>", 0) + 1
        if len(e["contexts"]) < 2:
            e["contexts"].append(s[max(0, m.start() - 40):m.end() + 40].decode("ascii", "replace"))
print(json.dumps({"probe": "codex-env-name-sweep", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "binary_bytes": len(data),
                  "extraction": steps, "printable_runs_rule": "strings -a -n 4 (in Python: no strings on athena)",
                  "regex": PREFIX.pattern.decode(), "raw_matches": len(names), "names": names},
                 indent=1, sort_keys=True))
