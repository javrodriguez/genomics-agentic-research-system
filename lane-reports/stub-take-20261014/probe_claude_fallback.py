"""FALLBACK_ENV source read (stub-take lane, 14 Oct 2026): where the take-a image's `claude` resolves, and every
[A-Z_]*FALLBACK[A-Z_]* identifier in the files of the pinned package, with short printable contexts. Run on athena,
fed over ssh stdin: python3 - <take-a image id>. One-shot container, no network, as the agent; writes nothing."""
import json
import subprocess
import sys

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "DOCKER_HOST": "unix:///run/user/1000/docker.sock",
       "XDG_RUNTIME_DIR": "/run/user/1000", "HOME": "/nonexistent"}
PROGRAM = r'''import json,os,re,shutil
c=shutil.which("claude"); real=os.path.realpath(c) if c else None
roots=sorted({os.path.dirname(real)} | {"/usr/local/lib/node_modules/@anthropic-ai"}) if real else []
pat=re.compile(rb"[A-Z][A-Z0-9_]*FALLBACK[A-Z0-9_]*"); names={}; files=[]
for root in roots:
    for base,dirs,fs in os.walk(root):
        dirs.sort()
        for f in sorted(fs):
            p=os.path.join(base,f)
            if os.path.islink(p): continue
            files.append([p,os.path.getsize(p)])
            data=open(p,"rb").read()
            for m in pat.finditer(data):
                n=m.group().decode(); e=names.setdefault(n,{"count":0,"files":[],"contexts":[]}); e["count"]+=1
                if p not in e["files"]: e["files"].append(p)
                if len(e["contexts"])<4:
                    s=data[max(0,m.start()-160):m.end()+160].decode("latin-1")
                    e["contexts"].append("".join(ch if 32<=ord(ch)<127 else "." for ch in s))
print(json.dumps({"which":c,"realpath":real,"roots":roots,"files":files,"names":names},sort_keys=True))
'''
image = sys.argv[1]
p = subprocess.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", "10001:10001",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--entrypoint", "/usr/bin/python3",
                    image, "-I", "-S", "-c", PROGRAM], env=ENV, capture_output=True, text=True, timeout=600)
print(json.dumps({"image": image, "returncode": p.returncode, "stdout": p.stdout, "stderr": p.stderr[:2000]}))
