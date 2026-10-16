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
site = data.find(b'{type:"edited_text_file",filename:', 219270000)
# the enclosing function: the nearest `async function NAME(` or `function NAME(` before the site
heads = [m for m in re.finditer(rb'(?:async )?function ([A-Za-z0-9_$]+)\(', data[site - 20000:site])]
fn = heads[-1].group(1).decode() if heads else None
fn_at = site - 20000 + heads[-1].start() if heads else None
calls = [m.start() for m in re.finditer(re.escape((fn + "(").encode()), data)] if fn else []
envs = sorted(set(m.group(0).decode() for m in re.finditer(rb'process\.env\.[A-Z0-9_]+', data[site - 20000:site + 6000])))
keys = sorted(set(m.group(1).decode() for m in re.finditer(rb'"(CLAUDE_CODE_[A-Z0-9_]*(?:FILE|CHANGE|WATCH|EDIT|DIFF|ATTACH)[A-Z0-9_]*)"', data)))
envs_all = sorted(set(m.group(0).decode() for m in re.finditer(rb'CLAUDE_CODE_[A-Z0-9_]*(?:FILE_CHANGE|CHANGED_FILE|FILE_WATCH|EDITED_FILE|FILE_ATTACH|CHANGE_ATTACH)[A-Z0-9_]*', data)))
res = {"probe": "edited-text-file-trigger", "image": IMAGE, "binary_sha256": hashlib.sha256(data).hexdigest(),
       "extraction": steps, "site": site, "function": fn, "function_at": fn_at,
       "function_window": win(fn_at, site + 1500) if fn_at else None,
       "call_sites": [win(c - 700, c + 300) for c in calls[:6]], "n_calls": len(calls),
       "env_reads_near": envs, "env_names_file_change": envs_all, "quoted_env_like": keys}
print(json.dumps(res, indent=1))
