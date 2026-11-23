"""CLAUDE_CODE_THRIFTY_SONIC in the pinned Claude Code 2.1.296 binary (box lane, 15 Oct 2026; glitch-6b's study-
condition ruling on the auto_mode steer). Run on athena as javier, fed over ssh stdin:
    python3 -I - <take image id> <work folder>
The binary is copied out of the pinned take image with `docker create --network none` + `docker cp`, never run; the
container is removed and the caller deletes the work folder. Records the printable context around every occurrence of
the name, every occurrence of HXt, and the source of each short identifier called on the variable (the tri-state
parser), so the false value is read from the parser's own text."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
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
name = b"CLAUDE_CODE_THRIFTY_SONIC"
occ = [m.start() for m in re.finditer(name, data)]
ctx = [{"offset": i, "text": text(i - 400, i + 400)} for i in occ[:12]]
callers = sorted({m.group(1).decode() for i in occ for m in
                  re.finditer(rb"([A-Za-z_$][A-Za-z0-9_$]{0,5})\((?:process\.env|[A-Za-z_$]{1,3})\." + name, data[max(0, i - 40):i + 40])})
funcs = {}
for fn in callers:
    pat = rb"function " + re.escape(fn.encode()) + rb"\("
    funcs[fn] = [{"offset": m.start(), "text": text(m.start(), m.start() + 500)} for m in re.finditer(pat, data)][:3]
hxt = [{"offset": m.start(), "text": text(m.start() - 100, m.start() + 600)} for m in re.finditer(rb"function HXt\(", data)][:3]
print(json.dumps({"probe": "claude-thrifty-sonic", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "extraction": steps,
                  "occurrences": len(occ), "contexts": ctx, "parser_callers": callers, "parser_sources": funcs,
                  "HXt": hxt}, indent=1, sort_keys=True))
