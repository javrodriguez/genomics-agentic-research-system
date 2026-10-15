"""Function-source probe (box lane, 15 Oct 2026): the third THRIFTY_SONIC probe showed
`triBool:()=>s` with `s=i((n)=>{if(Ne(n))return!0;if(vs(n))return!1;return})` in the env-schema module ending at
offset ~207489237. This records the source of named functions inside a byte window before an anchor, so the false
spellings `vs` accepts (and the `i` wrapper's handling of the raw value) are read from the binary's own text.
Same extraction: `docker create --network none` + `docker cp`, never run.
Run on athena as javier:  python3 -I - <take image id> <work folder> <anchor text> <window bytes> <name>..."""
import hashlib, json, os, re, subprocess, sys
IMAGE, WORK, ANCHOR, WINDOW, NAMES = sys.argv[1], sys.argv[2], sys.argv[3].encode(), int(sys.argv[4]), sys.argv[5:]
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
anchor = data.find(ANCHOR)
lo = max(0, anchor - WINDOW)
res = {}
for key in NAMES:
    res[key] = []
    if key.startswith("ctx:"):  # the raw text of the N bytes before the anchor (the module's imports)
        n = int(key[4:]); res[key].append({"offset": anchor - n, "text": text(anchor - n, anchor),
                                           "sha256_600": hashlib.sha256(data[anchor - n:anchor]).hexdigest()})
        continue
    nm, base, region = (key[4:], 0, data) if key.startswith("any:") else (key, lo, data[lo:anchor])
    pats = [rb"function " + re.escape(nm.encode()) + rb"\(",
            rb"(?<![A-Za-z0-9_$.])" + re.escape(nm.encode()) + rb"=(?:\([^)]{0,40}\)|[A-Za-z_$]{1,3})=>"]
    for p in pats:
        for f in re.finditer(p, region):
            s = base + f.start()
            res[key].append({"offset": s, "text": text(s, s + 600), "sha256_600": hashlib.sha256(data[s:s + 600]).hexdigest()})
            if len(res[key]) >= 8: break
print(json.dumps({"probe": "claude-fn-source", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "extraction": steps,
                  "anchor": ANCHOR.decode(), "anchor_offset": anchor, "window": WINDOW, "sources": res},
                 indent=1, sort_keys=True))
