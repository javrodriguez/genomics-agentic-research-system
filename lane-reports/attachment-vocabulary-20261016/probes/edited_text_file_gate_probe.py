"""edited_text_file trigger probe (harness lane, 15 Oct 2026, glitch-6b's ruling 1a): static read of the pinned
binary. docker create --network none + docker cp -L + docker rm, never run. Prints windows (printable text) and
their sha256 around the edited_text_file creation site, its enclosing function and its call sites, and every
process.env read and settings key within the window."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK = sys.argv[1], sys.argv[2]
BIN = "/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": os.environ.get("HOME", "/nonexistent")}
def run(argv):
    p = subprocess.run(argv, env=ENV, capture_output=True, text=True, timeout=600)
    return {"argv": argv, "rc": p.returncode, "stdout": p.stdout.strip()[:200], "stderr": p.stderr.strip()[:300]}
steps = []; create = run(["docker", "create", "--pull=never", "--network", "none", IMAGE, "true"]); steps.append(create)
cid = create["stdout"]; out = os.path.join(WORK, "claude.bin")
if create["rc"] == 0 and re.fullmatch(r"[0-9a-f]{64}", cid):
    try: steps.append(run(["docker", "cp", "-L", f"{cid}:{BIN}", out]))
    finally: steps.append(run(["docker", "rm", cid]))
data = open(out, "rb").read()
def txt(i, j): return "".join(c if 32 <= ord(c) < 127 else "." for c in data[max(0, i):j].decode("latin-1"))
def win(i, j): return {"start": max(0, i), "end": j, "sha256": hashlib.sha256(data[max(0, i):j]).hexdigest(), "text": txt(i, j)}

import re as _re
calls = [m.start() + 1 for m in _re.finditer(rb'[^A-Za-z0-9_$.]ear\(', data)]
dis = [m.start() for m in _re.finditer(rb'CLAUDE_CODE_DISABLE_ATTACHMENTS', data)]
res = {"binary_sha256": hashlib.sha256(data).hexdigest(), "extraction": steps,
       "ear_calls": [win(c - 900, c + 400) for c in calls], "disable_attachments": [win(c - 500, c + 700) for c in dis]}
print(json.dumps(res, indent=1))
