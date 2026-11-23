"""The pinned Claude Code binary's origin-kind read, v2 of claude_binary_sweep.py's (b) (box lane, 15 Oct 2026).
Same extraction (docker create --network none + docker cp from the take image, never run; container removed; the
caller deletes the work folder). Records, from the binary's bundled source:
  writers   every exact `origin:{kind:"<x>"` construction and every `{kind:"task-notification"` object, counted;
  readers   every `origin?.kind==="<x>"` / `origin.kind==="<x>"` comparison, counted;
  classifier 1600 bytes around each `frame:"non-user"` (the function that sorts a user record's origin into frames)."""
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
def count(rx):
    c = {}
    for m in re.finditer(rx, data):
        k = m.group(1).decode(); c[k] = c.get(k, 0) + 1
    return dict(sorted(c.items()))
writers = count(rb'origin:\{kind:"([A-Za-z0-9_-]{1,60})"')
objects = count(rb'\{kind:"(task-notification)"')
readers = count(rb'origin\??\.kind===?"([A-Za-z0-9_-]{1,60})"')
cls = [text(m.start() - 1000, m.end() + 600) for m in re.finditer(rb'frame:"non-user"', data)][:4]
print(json.dumps({"probe": "claude-origin-kinds", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "binary_bytes": len(data),
                  "extraction": steps, "writers": writers, "task_notification_objects": objects,
                  "readers": readers, "classifier_contexts": cls}, indent=1, sort_keys=True))
