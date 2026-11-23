"""Second THRIFTY_SONIC probe (box lane, 15 Oct 2026). The first probe showed HXt() returns
`a.CLAUDE_CODE_THRIFTY_SONIC` and the env module exports it as `CLAUDE_CODE_THRIFTY_SONIC:()=>rE`; this one reads
the definition of that getter target and the source of the function it calls (the tri-state parser).
Run on athena as javier, fed over ssh stdin:  python3 -I - <take image id> <work folder>
Same extraction as the first probe: `docker create --network none` + `docker cp`, never run; container removed."""
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
exp = data.find(b"CLAUDE_CODE_THRIFTY_SONIC:()=>")
m = re.match(rb"CLAUDE_CODE_THRIFTY_SONIC:\(\)=>([A-Za-z_$][A-Za-z0-9_$]*)", data[exp:exp + 80]) if exp >= 0 else None
target = m.group(1) if m else None
lo, hi = max(0, exp - 4_000_000), exp + 4_000_000
defs = []
if target:
    for d in re.finditer(rb"(?<![A-Za-z0-9_$.])" + re.escape(target) + rb"=(?!=)", data[lo:hi]):
        defs.append({"offset": lo + d.start(), "sha256_600": hashlib.sha256(data[lo + d.start(): lo + d.start() + 600]).hexdigest(),
                     "text": text(lo + d.start() - 80, lo + d.start() + 600)})
        if len(defs) >= 4: break
# the function each definition calls on process.env, and its source
called = set()
for d in defs:
    for c in re.finditer(r"=([A-Za-z_$][A-Za-z0-9_$]{0,5})\((?:process\.env|[A-Za-z_$]{1,3})\.CLAUDE_CODE_THRIFTY_SONIC|=([A-Za-z_$][A-Za-z0-9_$]{0,5})\(\"CLAUDE_CODE_THRIFTY_SONIC\"", d["text"]):
        called.add((c.group(1) or c.group(2)))
srcs = {}
for fn in sorted(called):
    srcs[fn] = []
    for f in re.finditer(rb"function " + re.escape(fn.encode()) + rb"\(", data[lo:hi]):
        s = lo + f.start(); srcs[fn].append({"offset": s, "text": text(s, s + 700),
                                             "sha256_700": hashlib.sha256(data[s:s + 700]).hexdigest()})
        if len(srcs[fn]) >= 3: break
    for f in re.finditer(rb"(?<![A-Za-z0-9_$.])" + re.escape(fn.encode()) + rb"=(?:\([^)]{0,40}\)|[A-Za-z_$]{1,3})=>", data[lo:hi]):
        s = lo + f.start(); srcs[fn].append({"offset": s, "text": text(s, s + 700),
                                             "sha256_700": hashlib.sha256(data[s:s + 700]).hexdigest()})
        if len(srcs[fn]) >= 6: break
print(json.dumps({"probe": "claude-thrifty-sonic-parser", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "extraction": steps,
                  "export_offset": exp, "getter_target": target.decode() if target else None,
                  "definitions": defs, "called": sorted(called), "parser_sources": srcs}, indent=1, sort_keys=True))
