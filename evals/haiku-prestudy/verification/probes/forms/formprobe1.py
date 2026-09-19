import json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
S = Path(__file__).parent / "formprobe"
OUT = Path(__file__).parent / "formprobe-each"
OUT.mkdir(exist_ok=True)
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
allow = sys.argv[1:]
def one(i):
    prompt = f"Run this exact shell command as a single Bash tool call, verbatim, then report its output:\n{forms[i]}"
    argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "auto",
            "--permission-prompts", "none", "--model", "claude-haiku-4-5-20251001",
            "--setting-sources", "project,local", "--strict-mcp-config"] + (["--allowedTools", *allow] if allow else [])
    p = subprocess.run(argv, cwd=S, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    (OUT / f"form{i+1}.{'-'.join(re.sub('[^a-z0-9]','',a.lower()) for a in allow) or 'none'}.jsonl").write_text(p.stdout)
    ran_exact, denied, other = 0, 0, []
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
                    cmd = pending.get(c["tool_use_id"])
                    if "Permission for this tool use was denied" in s:
                        denied += 1
                        m = re.search(r"requires approval: (.*)", s)
                        other.append((m.group(1)[:60] if m else "?"))
                    elif cmd == forms[i]: ran_exact += 1
    return i, ran_exact, denied, other, [c for c in pending.values() if c != forms[i]]
with ThreadPoolExecutor(3) as ex:
    for i, ran, den, why, alt in sorted(ex.map(one, range(len(forms)))):
        print(f"form {i+1}: {'DENIED' if den else ('ran' if ran else 'NOT RUN VERBATIM')}  {forms[i][:70]}"
              + (f"\n      needs approval: {why[0]}" if why else "") + (f"\n      ran instead: {alt[:2]}" if alt and not ran else ""))
