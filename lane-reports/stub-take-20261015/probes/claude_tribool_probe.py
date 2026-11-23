"""Third THRIFTY_SONIC probe (box lane, 15 Oct 2026). The second probe showed the env module declares
`rE=H.triBool()` and exports `CLAUDE_CODE_THRIFTY_SONIC:()=>rE`; this one records every place `triBool` is defined
(occurrences not of the form `<x>.triBool()` in the declaration list) so the accepted false spellings are read from
the parser's own source. Same extraction: `docker create --network none` + `docker cp`, never run.
Run on athena as javier, fed over ssh stdin:  python3 -I - <take image id> <work folder>"""
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
hits = []
for m in re.finditer(rb"triBool", data):
    s = m.start()
    if re.match(rb"\.triBool\(\)[,;]", data[s - 1:s + 10]):
        continue  # a declaration that uses it
    hits.append({"offset": s, "text": text(s - 300, s + 900), "sha256_1200": hashlib.sha256(data[s - 300:s + 900]).hexdigest()})
    if len(hits) >= 12: break
print(json.dumps({"probe": "claude-tribool", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "extraction": steps,
                  "definition_sites": hits}, indent=1, sort_keys=True))
