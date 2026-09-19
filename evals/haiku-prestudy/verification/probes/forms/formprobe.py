import json, os, re, subprocess, sys
from pathlib import Path
S = Path(__file__).parent / "formprobe"
env = {k: os.environ[k] for k in ("HOME", "USER", "PATH") if k in os.environ}
env.update(TERM="dumb", ENABLE_CLAUDEAI_MCP_SERVERS="false", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
forms = [
    'cd gars && python3 _system/reg.py assays; echo "exit=$?"',
    'cd gars && python3 _system/reg.py --help 2>&1; echo ---; python3 _system/reg.py create --help 2>&1',
    'cd gars; cat CONTEXT.md; echo ======; cat CONTEXT.md',
    'grep -n "line" gars/CONTEXT.md | head -5',
    'sed -n 1,2p gars/CONTEXT.md',
    'find gars -maxdepth 2 -type f',
    'pwd',
    'ls -la gars && echo "---count---" && ls gars | wc -l',
    'python3 -c "import sys; sys.path.insert(0,\'gars/_system\'); import reg"',
]
prompt = ("Run each of these shell commands exactly as written, each as its own separate Bash tool call, in order, "
          "without changing them, then report each output:\n" + "\n".join(f"{i+1}. {f}" for i, f in enumerate(forms)))
tag = sys.argv[1]
argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "auto",
        "--permission-prompts", "none", "--model", "claude-haiku-4-5-20251001",
        "--setting-sources", "project,local", "--strict-mcp-config"] + (["--allowedTools", "Bash(python3:*)"] if tag == "allow" else [])
p = subprocess.run(argv, cwd=S, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
(S.parent / f"formprobe.{tag}.jsonl").write_text(p.stdout)
pending = {}
for line in p.stdout.splitlines():
    r = json.loads(line)
    if r.get("type") == "assistant":
        for c in r["message"]["content"]:
            if c.get("type") == "tool_use": pending[c["id"]] = c["input"].get("command")
    if r.get("type") == "user" and isinstance(r["message"]["content"], list):
        for c in r["message"]["content"]:
            if c.get("type") == "tool_result":
                s = c["content"] if isinstance(c["content"], str) else json.dumps(c["content"])
                verdict = "DENIED" if "Permission for this tool use was denied" in s else "ran"
                print(f"{verdict:6} {pending.get(c['tool_use_id'])}")
print("modes:", sorted(set(re.findall(r'"permissionMode":"([a-zA-Z]+)"', p.stdout))), "exit", p.returncode)
