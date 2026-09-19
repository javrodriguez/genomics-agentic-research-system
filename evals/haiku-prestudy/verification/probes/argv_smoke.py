"""One real turn with the argv drive.one_turn builds, run where nothing of the study is: are both entries honoured?"""
import importlib.util, json, os, re, subprocess, sys, uuid
from pathlib import Path
from unittest import mock
D = Path(sys.argv[1]); S = Path(__file__).parent / "argvsmoke"
spec = importlib.util.spec_from_file_location("drv", D / "drive.py"); drive = importlib.util.module_from_spec(spec); spec.loader.exec_module(drive)
drive.RUN_TREE = S
seen = {}
def capture(argv, **kw):
    seen["argv"], seen["env"] = argv, kw.get("env")
    return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
line = ('Run this exact shell command as a single Bash tool call, verbatim, then report its output: '
        'cd gars && python3 _system/reg.py assays; echo "exit=$?"')
with mock.patch.object(drive.subprocess, "run", capture):
    drive.one_turn(line, str(uuid.uuid4()), "claude-haiku-4-5-20251001", True, 600)
argv = seen["argv"]
i = argv.index("--allowedTools"); print("argv tail after -p line:", argv[3:])
p = subprocess.run(argv, cwd=S, env=seen["env"], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=600)
(Path(__file__).parent / "argv-smoke.jsonl").write_text(p.stdout)
print("exit", p.returncode, "denials", p.stdout.count("Permission for this tool use was denied"),
      "modes", sorted(set(re.findall(r'"permissionMode":"([a-zA-Z]+)"', p.stdout))),
      "stage ran", "stage-ok" in p.stdout, "exit=0 seen", "exit=0" in p.stdout)
