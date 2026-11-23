"""The pinned Claude Code binary's provider tables, v4 beside claude_binary_sweep.py (box lane, 15 Oct 2026). Same
extraction (docker create --network none + docker cp from the take image, never run; container removed; the caller
deletes the work folder). Records 900 bytes after each place one of the binary's own provider tables is assigned
(`<NAME>=` or `<NAME> =`): PROVIDER_SELECTOR_ENV_FLAGS, THIRD_PARTY_PROVIDER_ENV_VARS, PROVIDER_CLI_FLAG,
PROVIDER_ARMS, CREDENTIAL_KINDS_FOR_PROVIDER; and 600 bytes around each CLAUDE_CODE_USE_GATEWAY and
CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST env-like access."""
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
tables = {}
for t in ("PROVIDER_SELECTOR_ENV_FLAGS", "THIRD_PARTY_PROVIDER_ENV_VARS", "PROVIDER_CLI_FLAG", "PROVIDER_ARMS",
          "CREDENTIAL_KINDS_FOR_PROVIDER"):
    tables[t] = [text(m.start(), m.end() + 900) for m in re.finditer(rb"(?<![A-Za-z0-9_$])" + t.encode() + rb"\s?=(?!=)", data)][:3]
access = {}
for n in ("CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "ANTHROPIC_UNIX_SOCKET", "ANTHROPIC_IDENTITY_TOKEN"):
    access[n] = [text(m.start() - 300, m.end() + 300) for m in re.finditer(rb"[A-Za-z0-9_$]\." + n.encode() + rb"(?![A-Za-z0-9_])", data)][:3]
print(json.dumps({"probe": "claude-provider-tables", "image": IMAGE, "binary_path": BIN,
                  "binary_sha256": hashlib.sha256(data).hexdigest() if data else None, "binary_bytes": len(data),
                  "extraction": steps, "tables": tables, "env_access_contexts": access}, indent=1, sort_keys=True))
