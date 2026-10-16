"""String-context probe (box lane, 15 Oct 2026; glitch-6b's isolation ruling on RemoteTrigger, SendMessage and
ListAgents). Records the printable context around occurrences of each named string in the pinned Claude Code binary,
so tool names, the crossSessionInbound setting's values and the --disallowedTools parsing are read from the binary's
own text. Same extraction as the THRIFTY probes: `docker create --network none` + `docker cp`, never run.
Run on athena as javier:  python3 -I - <take image id> <work folder> <max per needle> <half window> <needle>..."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK, MAXN, HALF, NEEDLES = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5:]
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
res = {}
for nd in NEEDLES:
    occ = [m.start() for m in re.finditer(re.escape(nd.encode()), data)]
    res[nd] = {"count": len(occ), "sites": [{"offset": i, "text": text(i - HALF, i + len(nd) + HALF),
                                              "sha256": hashlib.sha256(data[max(0, i - HALF):i + len(nd) + HALF]).hexdigest()}
                                             for i in occ[:MAXN]]}
print(json.dumps({"probe": "claude-string-context", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "extraction": steps,
                  "half_window": HALF, "needles": res}, indent=1, sort_keys=True))
