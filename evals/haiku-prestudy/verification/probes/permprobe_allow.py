"""Probe: which permission mode does each model's headless session run under, and is a Bash call denied?"""
import json, os, re, subprocess, sys
from pathlib import Path

S = Path(__file__).parent / "permprobe"
S.mkdir(exist_ok=True)
env = {k: os.environ[k] for k in ("HOME", "USER", "PATH") if k in os.environ}
env.update(TERM="dumb", ENABLE_CLAUDEAI_MCP_SERVERS="false", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
modes = sys.argv[2:] or ["auto"]
for m in sys.argv[1].split(","):
    for mode in modes:
        argv = ["claude", "-p", "Run this shell command and tell me its output: python3 -c 'print(6*7)'",
                "--output-format", "stream-json", "--verbose", "--permission-mode", mode,
                "--permission-prompts", "none", "--model", m,
                "--setting-sources", "project,local", "--strict-mcp-config", "--allowedTools", "Bash(python3:*)"]
        p = subprocess.run(argv, cwd=S, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=240)
        out = p.stdout
        (S / f"{m}.{mode}.allow.jsonl").write_text(out)
        seen = sorted(set(re.findall(r'"permissionMode":"([a-zA-Z]+)"', out)))
        denied = out.count("Permission for this tool use was denied")
        result = ""
        for line in out.splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("type") == "result":
                result = (r.get("result") or "")[:200].replace("\n", " ")
        print(f"{m} requested={mode} exit={p.returncode} modes_seen={seen} denied={denied}")
        print(f"   result: {result}")
        if p.stderr.strip():
            print(f"   stderr: {p.stderr.strip()[:400]}")
