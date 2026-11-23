"""The pinned Claude Code binary's route-name read, v3 beside claude_binary_sweep.py (box lane, 15 Oct 2026). Same
extraction (docker create --network none + docker cp from the take image, never run; container removed; the caller
deletes the work folder). drive.py's harness patterns name only CLAUDE_CODE_USE_(BEDROCK|VERTEX|FOUNDRY), so a newer
provider switch would sit outside them: this records every env-shaped name matching
CLAUDE_CODE_USE_*, *_BASE_URL, *_PROVIDER*, CLAUDE_CODE_SKIP_*, and the names given on the command line, each with
up to 4 contexts and how many of its occurrences read like an environment access (`.NAME` after an identifier, or
`env.NAME` / `env["NAME"]`)."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
EXTRA = set(sys.argv[3:])
BIN = "/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": os.environ.get("HOME", "/nonexistent")}
def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=600)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout.strip()[:200], "stderr": p.stderr.strip()[:300]}
steps = []
create = run(["docker", "create", "--pull=never", "--network", "none", IMAGE, "true"]); steps.append(create)
cid = create["stdout"]; out = os.path.join(WORK, "claude.bin")
if create["rc"] == 0 and re.fullmatch(r"[0-9a-f]{64}", cid):
    try:
        steps.append(run(["docker", "cp", "-L", f"{cid}:{BIN}", out]))
    finally:
        steps.append(run(["docker", "rm", cid]))
data = open(out, "rb").read() if os.path.isfile(out) else b""
def text(i, j):
    return "".join(ch if 32 <= ord(ch) < 127 else "." for ch in data[max(0, i):j].decode("latin-1"))
NAME = re.compile(rb"(?<![A-Za-z0-9_$])[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+(?![A-Za-z0-9_$])")
WANT = re.compile(r"^CLAUDE_CODE_USE_|_BASE_URL$|PROVIDER|^CLAUDE_CODE_SKIP_")
ACCESS = re.compile(rb'([A-Za-z0-9_$]\.|env\.|env\[")$')
names = {}
for m in NAME.finditer(data):
    n = m.group().decode()
    if not (WANT.search(n) or n in EXTRA):
        continue
    e = names.setdefault(n, {"count": 0, "env_access_like": 0, "contexts": []})
    e["count"] += 1
    if ACCESS.search(data[max(0, m.start() - 6):m.start()]):
        e["env_access_like"] += 1
    if len(e["contexts"]) < 4:
        e["contexts"].append(text(m.start() - 80, m.end() + 80))
print(json.dumps({"probe": "claude-route-names", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "binary_bytes": len(data),
                  "extraction": steps, "want": WANT.pattern, "extra": sorted(EXTRA),
                  "absent_extra": sorted(EXTRA - set(names)), "names": names}, indent=1, sort_keys=True))
