import json, os, re, subprocess, sys
from pathlib import Path
S = Path(__file__).parent / "allowprobe"
env = {k: os.environ[k] for k in ("HOME", "USER", "PATH") if k in os.environ}
env.update(TERM="dumb", ENABLE_CLAUDEAI_MCP_SERVERS="false", CLAUDE_CODE_DISABLE_AUTO_MEMORY="1")
prompt = ("Run exactly these three shell commands, each as its own Bash call, verbatim, and report each output: "
          f"(1) cd {S}/gars && python3 _system/reg.py assays  "
          f"(2) python3 {S}/gars/_system/reg.py create  "
          "(3) python3 -c \"print(6*7)\"")
argv = ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--permission-mode", "auto",
        "--permission-prompts", "none", "--model", "claude-haiku-4-5-20251001",
        "--setting-sources", "project,local", "--strict-mcp-config", "--allowedTools", sys.argv[1]]
p = subprocess.run(argv, cwd=S, env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
(S.parent / f"allowprobe.{re.sub('[^a-z0-9]','_',sys.argv[1].lower())}.jsonl").write_text(p.stdout)
for line in p.stdout.splitlines():
    r = json.loads(line)
    if r.get("type") == "assistant":
        for c in r["message"]["content"]:
            if c.get("type") == "tool_use": print("CALL:", c["input"].get("command"))
    if r.get("type") == "user" and isinstance(r["message"]["content"], list):
        for c in r["message"]["content"]:
            if c.get("type") == "tool_result":
                s = c["content"] if isinstance(c["content"], str) else json.dumps(c["content"])
                print("  ->", s[:140].replace("\n", " | "))
print("denied:", p.stdout.count("Permission for this tool use was denied"),
      "modes:", sorted(set(re.findall(r'"permissionMode":"([a-zA-Z]+)"', p.stdout))))
