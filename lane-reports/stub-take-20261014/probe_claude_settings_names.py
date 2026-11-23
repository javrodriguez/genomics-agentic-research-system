"""Step 1b evidence (box lane, 14 Oct 2026): does the pinned Claude Code 2.1.296 binary in the take-a image carry the
names the docs give for its model-switch controls? Counts and short printable contexts of each exact name. Run on
athena, fed over ssh stdin: python3 - <take-a image id>. One-shot container, no network, as the agent; writes nothing."""
import json
import subprocess
import sys

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": "/nonexistent"}
PROGRAM = r'''import json
p="/usr/local/lib/node_modules/@anthropic-ai/claude-code/bin/claude.exe"
data=open(p,"rb").read(); out={}
for n in ("CLAUDE_CODE_DISABLE_REFUSAL_FALLBACK","switchModelsOnFlag","fallbackModel","--fallback-model","availableModels"):
    b=n.encode(); i=data.find(b); ctx=[]; k=0; c=0
    while i!=-1:
        c+=1
        if len(ctx)<3:
            s=data[max(0,i-140):i+len(b)+140].decode("latin-1"); ctx.append("".join(ch if 32<=ord(ch)<127 else "." for ch in s))
        i=data.find(b,i+1)
    out[n]={"count":c,"contexts":ctx}
print(json.dumps({"file":p,"bytes":len(data),"names":out},sort_keys=True))
'''
p = subprocess.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", "10001:10001",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--entrypoint", "/usr/bin/python3",
                    sys.argv[1], "-I", "-S", "-c", PROGRAM], env=ENV, capture_output=True, text=True, timeout=600)
print(json.dumps({"image": sys.argv[1], "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr[:2000]}))
