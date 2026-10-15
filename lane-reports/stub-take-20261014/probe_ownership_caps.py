"""Review minor 6 and note 8 (box lane, 14 Oct 2026), run on athena from a shipped copy of the box:
  (6) does the ownership walk work with CHOWN + DAC_READ_SEARCH (no DAC_OVERRIDE), over a tree the agent made
      restrictive (folders 0700 and 0000, files 0600 and 0000)?
  (8) does a grant and a restore over a tree holding an agent-planted link to a host-owned file outside it change only
      the link's owner, never the target's?
Usage: python3 -B probe_ownership_caps.py <box parent> <scratch parent> <take image id> [both|committed].
"committed" (run after the restore-permission change) probes the module's own CAPS only. Prints one JSON object.
CAPS is set in this probe's own interpreter only (a measurement); nothing is written into the module."""
import json, os, sys, tempfile
sys.path.insert(0, sys.argv[1])
from box import ownership as ow, run_take as rt
parent, image = sys.argv[2], sys.argv[3]
uid = os.getuid()
env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
       "DOCKER_HOST": f"unix:///run/user/{uid}/docker.sock", "XDG_RUNTIME_DIR": f"/run/user/{uid}"}
runtime = rt.DockerRuntime()
AGENT_SCRIPT = r'''import os,sys
t=sys.argv[1]
os.makedirs(t+"/deep/er"); open(t+"/deep/er/f600","w").write("x"); os.chmod(t+"/deep/er/f600",0o600)
open(t+"/deep/f000","w").write("x"); os.chmod(t+"/deep/f000",0)
os.makedirs(t+"/locked/inner"); open(t+"/locked/inner/g","w").write("x")
os.chmod(t+"/locked/inner",0); os.chmod(t+"/locked",0o700); os.chmod(t+"/deep/er",0o700)
os.symlink(sys.argv[2], t+"/to-outside")
'''
out = {"image": image, "variants": {}}
VARIANTS = {"both": (("CHOWN+DAC_READ_SEARCH", ("CHOWN", "DAC_READ_SEARCH")), ("CHOWN+DAC_OVERRIDE", ("CHOWN", "DAC_OVERRIDE"))),
            "committed": (("committed", tuple(ow.CAPS)),)}[sys.argv[4] if len(sys.argv) > 4 else "both"]
COMMITTED_CAPS = tuple(ow.CAPS)
for name, caps in VARIANTS:
    ow.CAPS = caps
    base = tempfile.mkdtemp(prefix="ownp-", dir=parent)
    tree, cfg, ev = (os.path.join(base, n) for n in ("t", "c", "e"))
    for p in (tree, cfg, ev):
        os.mkdir(p, 0o755)
    outside = os.path.join(base, "outside.txt")
    open(outside, "w").write("host-owned\n")
    rec = {"caps": caps, "outside_uid_before": os.lstat(outside).st_uid}
    try:
        rec["grant"] = ow.grant(runtime, image=image, run_tree=tree, config_dir=cfg, evidence_dir=ev, caller_env=env)
        a = runtime.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", rt.AGENT_USER,
                         "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--mount",
                         f"type=bind,source={tree},target={tree}", image, "/usr/bin/python3", "-I", "-S", "-c",
                         AGENT_SCRIPT, tree, outside], env=env, timeout=120)
        rec["agent"] = {"returncode": a.returncode, "stderr": a.stderr[-300:]}
        rec["link_uid_after_agent"] = os.lstat(os.path.join(tree, "to-outside")).st_uid
        try:
            rec["restore"] = ow.restore(runtime, image=image, run_tree=tree, config_dir=cfg, evidence_dir=ev, ids=[],
                                        caller_env=env)
        except ow.OwnershipError as e:
            rec["restore"] = {"error": str(e), **e.record}
        rec["link_uid_after_restore"] = os.lstat(os.path.join(tree, "to-outside")).st_uid
        rec["outside_uid_after"] = os.lstat(outside).st_uid
        rec["outside_text_after"] = open(outside).read()
    finally:
        ow.CAPS = COMMITTED_CAPS
        try:
            ow.restore(runtime, image=image, run_tree=tree, config_dir=cfg, evidence_dir=ev, ids=[], caller_env=env)
        except Exception as e:
            rec["cleanup_restore"] = type(e).__name__
        for root, dirs, files in os.walk(base):
            for d in dirs:
                try: os.chmod(os.path.join(root, d), 0o700)
                except OSError: pass
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        rec["scratch_removed"] = not os.path.exists(base)
    out["variants"][name] = rec
print(json.dumps(out, indent=1, sort_keys=True, default=str))
