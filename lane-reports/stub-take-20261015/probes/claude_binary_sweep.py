"""The pinned Claude Code binary's static sweep (box lane, 15 Oct 2026; glitch-6b's item for the checker-constants ruling).
Run on athena as javier, fed over ssh stdin: python3 -I - <take image id> <work folder>. The binary is copied out of
the pinned take image (box/image.lock image_id) with `docker create --network none` + `docker cp`, never run; the
container is removed and the caller deletes the work folder. No model, no login, no network.
(a) every env-shaped name (UPPER_CASE with an underscore, on identifier boundaries) that drive.py's environment_record
    patterns match (HARNESS_NAME_PATTERNS, GENERIC_NAME_PATTERNS, re.search, case-sensitive), with counts and two
    short contexts;
(b) every occurrence of "task-notification", with contexts, and every `kind:"<x>"` within 120 bytes after an
    `origin` token, counted (the user-record origin kinds the binary writes)."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
BIN = "/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": os.environ.get("HOME", "/nonexistent")}
HARNESS = ("^ANTHROPIC_", "^CLAUDE_CODE_USE_(BEDROCK|VERTEX|FOUNDRY)$", "^CLAUDE_CODE_SKIP_.*_AUTH$",
           "^CLAUDE_CODE_OAUTH_TOKEN$", "^CLAUDE_CODE_OAUTH_REFRESH_TOKEN$", "^CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR$",
           "^CLAUDE_CODE_GATEWAY_TOKEN_FILE_DESCRIPTOR$", "^CLAUDE_CODE_SESSION_ACCESS_TOKEN$",
           "^CLAUDE_CODE_API_BASE_URL$", "^CLAUDE_CODE_CUSTOM_OAUTH_URL$", "^AWS_", "^GOOGLE_APPLICATION_CREDENTIALS$",
           "^AZURE_")
GENERIC = ("(API_?KEY|AUTH_?TOKEN|ACCESS_?TOKEN|_TOKEN$|SECRET|CREDENTIAL|PASSWORD)",)
def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=600)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout.strip()[:200], "stderr": p.stderr.strip()[:300]}
steps = []
create = run(["docker", "create", "--pull=never", "--network", "none", IMAGE, "true"])
steps.append(create)
cid = create["stdout"]
out = os.path.join(WORK, "claude.bin")
if create["rc"] == 0 and re.fullmatch(r"[0-9a-f]{64}", cid):
    try:
        steps.append(run(["docker", "cp", "-L", f"{cid}:{BIN}", out]))
    finally:
        steps.append(run(["docker", "rm", cid]))
data = open(out, "rb").read() if os.path.isfile(out) else b""
def ctx(i, j):
    s = data[max(0, i - 60):j + 60].decode("latin-1")
    return "".join(ch if 32 <= ord(ch) < 127 else "." for ch in s)
NAME = re.compile(rb"(?<![A-Za-z0-9_$])[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+(?![A-Za-z0-9_$])")
hp = [re.compile(p) for p in HARNESS]; gp = [re.compile(p) for p in GENERIC]
names = {}
for m in NAME.finditer(data):
    n = m.group().decode()
    by = "harness" if any(p.search(n) for p in hp) else ("generic" if any(p.search(n) for p in gp) else None)
    if by is None:
        continue
    e = names.setdefault(n, {"matched_by": by, "count": 0, "contexts": []})
    e["count"] += 1
    if len(e["contexts"]) < 2:
        e["contexts"].append(ctx(m.start(), m.end()))
tn = [m.start() for m in re.finditer(rb"task-notification", data)]
origin_kinds = {}
for m in re.finditer(rb"origin", data):
    w = data[m.end():m.end() + 120]
    for k in re.finditer(rb'kind:\s*"([A-Za-z0-9_-]{1,60})"', w):
        x = k.group(1).decode(); e = origin_kinds.setdefault(x, {"count": 0, "contexts": []}); e["count"] += 1
        if len(e["contexts"]) < 3:
            e["contexts"].append(ctx(m.start(), m.end() + k.end()))
print(json.dumps({"probe": "claude-binary-sweep", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "binary_bytes": len(data),
                  "extraction": steps, "name_regex": NAME.pattern.decode(), "harness_patterns": HARNESS,
                  "generic_patterns": GENERIC, "names": names,
                  "task_notification": {"count": len(tn), "contexts": [ctx(i, i + 17) for i in tn[:20]]},
                  "origin_kinds": origin_kinds}, indent=1, sort_keys=True))
