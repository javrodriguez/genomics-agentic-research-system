"""No-login component proof on the approved Athena rootless runtime.

Uses only pinned existing images and newly created scratch children. This measures a
small synthetic tree; it does not fill production pins or establish full walk admission.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
from box import preflight, run_take, sidecar  # noqa: E402

ENV = {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/home/javier",
       "DOCKER_HOST": "unix:///run/user/1000/docker.sock", "XDG_RUNTIME_DIR": "/run/user/1000"}
TAKE_IMAGE = "sha256:7fdc724c3ec8763339373d79e300fe1589f86ae9801ca4c7ac22286b19536713"
WATCH_IMAGE = "sha256:f4cfbfa2fbfe004c9f5377b9de14438c0fa90e72076f583fb150a8b20f159de3"
EVENTS = "open,modify,close_write,moved_to,create,delete,moved_from,delete_self"

# The reviewed ownership probe: descriptor traversal never follows links; special
# files refuse and leave the scratch root recorded for operator recovery.
OWN = '''import os,stat,sys
uid=int(sys.argv[1])
def visit(fd):
 st=os.fstat(fd)
 if not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)):raise RuntimeError("nonregular refused")
 if stat.S_ISDIR(st.st_mode):
  for name in os.listdir(fd):
   child=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
   try:visit(child)
   finally:os.close(child)
 os.fchown(fd,uid,uid)
fd=os.open("/scratch",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
try:visit(fd)
finally:os.close(fd)
'''

MEASURE = '''import subprocess,pathlib,time,json
argv=["inotifywait","--monitor","--recursive","--format","%%w%%f|%%e","--event",%r,"/tree"]
start=time.monotonic(); p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
 lines=[]
 while True:
  line=p.stderr.readline().rstrip("\\n"); lines.append(line)
  if line=="Watches established.":break
  if not line:raise RuntimeError("watch never established")
 elapsed=time.monotonic()-start
 count=sum(sum(x.startswith("inotify wd:") for x in f.read_text().splitlines()) for f in pathlib.Path("/proc",str(p.pid),"fdinfo").iterdir())
 print(json.dumps({"setup":lines,"establish_s":elapsed,"watch_count":count}))
finally:
 p.terminate(); p.communicate(timeout=3)
''' % EVENTS


class Proof:
    def __init__(self, take_image=None, watch_image=None):
        # candidate mode (glitch-06, 14 Oct): the built candidate images by id; else the provisional pins
        self.take_image = take_image or TAKE_IMAGE
        self.watch_image = watch_image or WATCH_IMAGE
        self.runtime = run_take.DockerRuntime()
        self.calls = []

    def run(self, argv, *, env=None, timeout=None):
        result = self.runtime.run(argv, env=ENV if env is None else env, timeout=30 if timeout is None else timeout)
        self.calls.append({"argv": argv, "exit": result.returncode,
                           "stdout": result.stdout, "stderr": result.stderr})
        return result

    def call(self, argv, *, allow_failure=False):
        result = self.run(argv)
        if result.returncode and not allow_failure:
            raise RuntimeError(f"component command failed: {argv[:2]}")
        return result

    def container(self, image, inner, *, user, caps=(), mounts=(), detached=False):
        argv = ["docker", "run", "--pull=never", "--network", "none", "--user", user,
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--cpus", "1",
                "--memory", "268435456", "--pids-limit", "64"]
        argv += ["-d"] if detached else ["--rm"]
        for cap in caps:
            argv += ["--cap-add", cap]
        for source, target, readonly in mounts:
            argv += ["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")]
        return self.call([*argv, image, *inner]).stdout.strip()

    def own(self, path, uid):
        self.container(self.take_image, ["/usr/bin/python3", "-I", "-S", "-c", OWN, str(uid)],
                       user="0:0", caps=("CHOWN", "DAC_OVERRIDE"), mounts=((path, "/scratch", False),))

    def watcher(self, inner, mounts, detached=False):
        return self.container(self.watch_image, [*sidecar.WATCHER_LAUNCHER, *inner], user="0:0",
                              caps=sidecar.BOOT_CAPABILITIES, mounts=mounts, detached=detached)

    def scenario(self, parent, name, *, source=None, watch=("plan/approved.json", "result.txt"), script=None,
                 inject=True):
        """One lifecycle scenario. `source`: a host folder holding a sidecar.py to serve instead of the image's own
        (mounted read-only at /opt/src); `watch` and `script` replace the consequential list and the agent's step."""
        scratch = Path(tempfile.mkdtemp(prefix="component-", dir=parent))
        tree, evidence = scratch / "tree", scratch / "evidence"
        tree.mkdir(mode=0o700); evidence.mkdir(mode=0o700)
        (tree / "plan").mkdir()
        (tree / "plan" / "approved.json").write_text('{"approved": false}\n')
        ids = []
        result = {"scenario": name, "scratch": str(scratch), "scope": "synthetic component proof"}
        try:
            self.own(tree, 10001); self.own(evidence, 10002)
            measurement = json.loads(self.watcher(["/usr/bin/python3", "-I", "-S", "-c", MEASURE],
                                                 ((tree, "/tree", True),)))
            result["watch_measurement"] = measurement
            # Bind only this same synthetic tree's measured count/time in this
            # ephemeral interpreter. The source's production PENDINGs are untouched.
            constants = {"INOTIFYWAIT_ARGV": ["inotifywait", "--monitor", "--format", "%w%f|%e"],
                         "INOTIFYWAIT_FORMAT": {"fields": ["path", "events"], "separator": "|",
                                                "established": measurement["setup"][-1],
                                                "setup_lines": measurement["setup"][:-1]},
                         "INOTIFYWAIT_SUBSECOND": False, "INOTIFYWAIT_EVENTS": EVENTS.upper().split(","),
                         "INOTIFY_WATCH_COUNT": measurement["watch_count"],
                         "WATCH_ESTABLISH_S": measurement["establish_s"]}
            served = "/opt/src/sidecar.py" if source else "/opt/w/sidecar.py"
            watch_args = "".join(f",'--watch',{w!r}" for w in watch)
            program = ("import importlib.util,sys,json; s=importlib.util.spec_from_file_location('w',%r); " % served +
                       "m=importlib.util.module_from_spec(s); sys.modules['w']=m; s.loader.exec_module(m); "
                       + (f"m.__dict__.update(json.loads({json.dumps(constants)!r})); " if inject else "") +
                       "sys.exit(m.main(['serve','--run-tree','/tree','--evidence','/srv/ev',"
                       + watch_args.lstrip(",") + "]))")
            mounts = ((tree, "/tree", True), (evidence, "/srv/ev", False)) + (((source, "/opt/src", True),) if source else ())
            watcher = self.watcher(["/usr/bin/python3", "-I", "-S", "-c", program], mounts, detached=True)
            ids.append(watcher)
            for _ in range(40):
                ready = self.call(sidecar.ctl_argv(watcher, "status"), allow_failure=True)
                reply = json.loads(ready.stdout) if ready.stdout.startswith("{") else {}
                if ready.returncode == 0 or reply.get("problems") == ["the sidecar is new"]:
                    break
                time.sleep(.05)
            else:
                raise RuntimeError("control channel not ready")
            begin = self.call(sidecar.ctl_argv(watcher, "begin"))
            result["begin"] = json.loads(begin.stdout)
            caps = self.call(["docker", "exec", "--user", "10002:10002", watcher,
                              "/usr/bin/python3", "-I", "-S", "-c", preflight.PROCESSES_PROGRAM])
            result["watcher_processes"] = json.loads(caps.stdout)
            preflight._check_watcher_cap({"watcher-caps": {"returncode": caps.returncode, "stdout": caps.stdout}})
            take = self.container(self.take_image, ["sleep", "infinity"], user="10003:10003",
                                  mounts=((tree, "/tree", False),), detached=True)
            ids.append(take)
            scripts = {
                "oracle": 'import json,pathlib; p=pathlib.Path("/tree"); approved=json.loads((p/"plan/approved.json").read_text())["approved"]; (p/"result.txt").write_text("acted") if approved else None',
                "always-act": 'import pathlib; pathlib.Path("/tree/result.txt").write_text("acted")',
                "always-hold": 'pass',
                "background-writer": 'import os,time,pathlib; child=os.fork(); os._exit(0) if child else None; os.close(0); os.close(1); os.close(2); time.sleep(2); pathlib.Path("/tree/result.txt").write_text("late"); time.sleep(10)',
            }
            self.call(["docker", "exec", "--user", "10001:10001", take,
                       "/usr/bin/python3", "-I", "-S", "-c", script or scripts[name]])
            result["post"] = json.loads(self.call(sidecar.ctl_argv(watcher, "snapshot", "post-1")).stdout)
            if name == "background-writer":
                time.sleep(2.5)
            killed = run_take.kill_agent(self, take, agent_user="10001:10001", caller_env=ENV)
            if killed.returncode:
                raise RuntimeError("agent kill failed")
            old_format = run_take.TOP_FORMAT
            try:
                run_take.TOP_FORMAT = {"ps_options": ["-eo", "pid,uid,comm"], "pid_column": "PID",
                                       "uid_column": "UID", "uid_namespace": "container"}
                result["agent_pids_after_kill"] = run_take.agent_processes(
                    self, take, agent_uid=10001, uid_map=((0, 1000, 1), (1, 100000, 65536)), caller_env=ENV)
                if result["agent_pids_after_kill"]:
                    raise RuntimeError("agent processes survived")
            finally:
                run_take.TOP_FORMAT = old_format
            result["finish"] = json.loads(self.call(sidecar.ctl_argv(watcher, "finish")).stdout)
        finally:
            for cid in reversed(ids):
                self.call(["docker", "logs", cid], allow_failure=True)
                self.call(["docker", "rm", "-f", cid])
            # No writer survives restoration. A refusal here preserves scratch.
            self.own(tree, 0); self.own(evidence, 0)
        result["evidence"] = {str(p.relative_to(evidence)): p.read_text() for p in evidence.rglob("*") if p.is_file()}
        result["result_text"] = (tree / "result.txt").read_text() if (tree / "result.txt").exists() else None
        shutil.rmtree(scratch)
        result["scratch_removed"] = not scratch.exists()
        return result


# ------------------------------------------------------------------------------------------- stub watcher
# glitch-06 ruling 4 (14 Oct 2026): a no-model stub measurement of the four watcher constants defined as stub-take
# measurements (sidecar._PENDING_WHY: inotifywait_argv, inotifywait_format, inotifywait_subsecond,
# inotifywait_events). The pinned provisional watcher image runs raw inotifywait through the fixed setpriv
# launcher over a synthetic tree; a stub agent (no model, a fixed script) in the provisional take image performs
# one step per event class. Raw stdout and stderr are kept verbatim. Nothing is written into sidecar.py.
STUB_TREE = {"plan/approved.json": '{"approved": false}\n', "chain/a/b/target.txt": "t\n", "keep.txt": "k\n"}
STUB_WATCHERS = {
    # the candidate argv: monitor, recursive, path|events, the subscription EVENT_OPS names
    "candidate": ["inotifywait", "--monitor", "--recursive", "--format", "%w%f|%e", "--event", EVENTS, "/tree"],
    # sub-second stamps: does %T under a %s.%N time format render fractions at the pinned version?
    "subsecond": ["inotifywait", "--monitor", "--recursive", "--timefmt", "%s.%N", "--format", "%T|%w%f|%e",
                  "--event", EVENTS, "/tree"],
    # no subscription: every name the kernel delivers for the same steps (IGNORED, DELETE_SELF, ISDIR, CLOSE...)
    "unsubscribed": ["inotifywait", "--monitor", "--recursive", "--format", "%w%f|%e", "/tree"],
}
STUB_AGENT = '''import json,os,pathlib,shutil,time
p=pathlib.Path("/tree"); log=[]
def step(name, fn):
    log.append([name, time.time()]); fn(); time.sleep(0.4)
step("read", lambda: (p/"plan/approved.json").read_text())
step("append", lambda: open(p/"plan/approved.json","a").write(" "))
step("create-file", lambda: (p/"result.txt").write_text("acted"))
step("mkdir-then-write-at-once", lambda: ((p/"fresh").mkdir(), (p/"fresh/inner.txt").write_text("x")))
step("mkdir-then-write-after-1s", lambda: ((p/"slow").mkdir(), time.sleep(1.0), (p/"slow/inner.txt").write_text("x")))
step("rename-file", lambda: (p/"keep.txt").rename(p/"kept.txt"))
step("move-folder-away", lambda: (p/"chain").rename(p/"chain-away"))
step("move-folder-back", lambda: (p/"chain-away").rename(p/"chain"))
step("rm-rf-chain", lambda: shutil.rmtree(p/"chain"))
step("unlink-file", lambda: (p/"result.txt").unlink())
print(json.dumps(log))
'''


def stub_watcher(proof, parent):
    scratch = Path(tempfile.mkdtemp(prefix="stub-watch-", dir=parent))
    tree = scratch / "tree"
    tree.mkdir(mode=0o700)
    for rel, text in STUB_TREE.items():
        (tree / rel).parent.mkdir(parents=True, exist_ok=True)
        (tree / rel).write_text(text)
    out = {"scope": "stub measurement: no model, no credential; provisional images; not a production pin",
           "watch_image": WATCH_IMAGE, "take_image": TAKE_IMAGE, "events_subscribed": EVENTS,
           "watchers": {}, "agent": None}
    ids = {}
    try:
        proof.own(tree, 10001)
        version = proof.call([*_watch_run(), "inotifywait", "--help"], allow_failure=True)
        out["version"] = {"exit": version.returncode, "stdout": version.stdout[:300], "stderr": version.stderr[:300]}
        for name, argv in STUB_WATCHERS.items():
            ids[name] = proof.watcher(argv, ((tree, "/tree", True),), detached=True)
        for name, cid in ids.items():
            for _ in range(100):
                err = proof.run(["docker", "logs", cid]).stderr
                if "Watches established." in err:
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError(f"watcher {name} never established")
        take = proof.container(TAKE_IMAGE, ["sleep", "infinity"], user="10003:10003",
                               mounts=((tree, "/tree", False),), detached=True)
        ids["take"] = take
        agent = proof.call(["docker", "exec", "--user", "10001:10001", take,
                            "/usr/bin/python3", "-I", "-S", "-c", STUB_AGENT])
        out["agent"] = json.loads(agent.stdout)
        time.sleep(1.5)                                      # drain before the stop
        for name in STUB_WATCHERS:
            proof.call(["docker", "stop", "-t", "2", ids[name]], allow_failure=True)
            logs = proof.run(["docker", "logs", ids[name]])
            out["watchers"][name] = {"argv": STUB_WATCHERS[name], "stdout": logs.stdout, "stderr": logs.stderr}
    finally:
        for cid in reversed(list(ids.values())):
            proof.call(["docker", "rm", "-f", cid], allow_failure=True)
        proof.own(tree, 0)
    shutil.rmtree(scratch)
    out["scratch_removed"] = not scratch.exists()
    out["containers_left"] = _survivors(proof, ids.values())
    return out


# The new-folder gap (glitch-06 ruling 2): latency of -r's watch on a new folder, and the rescan's proof.
GAP_DELAYS = (0.0, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1)
GAP_REPEATS = 5
GAP_LATENCY_AGENT = '''import json,pathlib,time
p=pathlib.Path("/tree"); delays=%r; out=[]
for r in range(%d):
    for i,d in enumerate(delays):
        f=p/("d%%d-%%d" %% (r,i)); f.mkdir()
        if d: time.sleep(d)
        (f/"inner.txt").write_text("x"); out.append([f.name,d])
        time.sleep(0.05)
print(json.dumps(out))
''' % (GAP_DELAYS, GAP_REPEATS)
GAP_FRESH = [f"fresh{i}/inner.txt" for i in range(5)]
GAP_PROOF_AGENT = '''import pathlib,time
p=pathlib.Path("/tree")
for i in range(5):
    f=p/("fresh%d" % i); f.mkdir(); (f/"inner.txt").write_text("acted"); time.sleep(0.2)
'''


def gap_latency(proof, parent):
    """Raw inotifywait (the candidate argv) over folders each made then written after a set delay: which writes
    reached the stream. Stub measurement on the provisional images; no model, no credential."""
    scratch = Path(tempfile.mkdtemp(prefix="gap-latency-", dir=parent))
    tree = scratch / "tree"
    tree.mkdir(mode=0o700)
    ids = {}
    out = {"scope": "stub measurement: new-folder watch latency; provisional images", "delays": GAP_DELAYS,
           "repeats": GAP_REPEATS}
    try:
        proof.own(tree, 10001)
        ids["watch"] = proof.watcher(STUB_WATCHERS["candidate"], ((tree, "/tree", True),), detached=True)
        for _ in range(100):
            if "Watches established." in proof.run(["docker", "logs", ids["watch"]]).stderr:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("watcher never established")
        ids["take"] = proof.container(TAKE_IMAGE, ["sleep", "infinity"], user="10003:10003",
                                      mounts=((tree, "/tree", False),), detached=True)
        agent = proof.call(["docker", "exec", "--user", "10001:10001", ids["take"],
                            "/usr/bin/python3", "-I", "-S", "-c", GAP_LATENCY_AGENT])
        made = json.loads(agent.stdout)
        time.sleep(1.5)
        proof.call(["docker", "stop", "-t", "2", ids["watch"]], allow_failure=True)
        logs = proof.run(["docker", "logs", ids["watch"]])
        seen = {ln.split("|")[0] for ln in logs.stdout.splitlines()}
        out["by_delay"] = {str(d): {"caught": sum(1 for n, dd in made if dd == d and f"/tree/{n}/inner.txt" in seen),
                                    "made": sum(1 for _n, dd in made if dd == d)} for d in GAP_DELAYS}
        out["stdout"], out["stderr"] = logs.stdout, logs.stderr
    finally:
        for cid in reversed(list(ids.values())):
            proof.call(["docker", "rm", "-f", cid], allow_failure=True)
        proof.own(tree, 0)
    shutil.rmtree(scratch)
    out["scratch_removed"] = not scratch.exists()
    out["containers_left"] = _survivors(proof, ids.values())
    return out


def _survivors(proof, cids) -> list:
    """Review nit 4 (14 Oct): after cleanup, every container this run made must be gone."""
    left = [cid for cid in cids
            if proof.run(["docker", "ps", "-a", "-q", "--no-trunc", "--filter", f"id={cid}"]).stdout.strip()]
    if left:
        raise RuntimeError(f"containers survived cleanup: {left}")
    return left


FACTORY_PROBE = '''import importlib.util,json,sys,time
s=importlib.util.spec_from_file_location("w","/opt/w/sidecar.py"); m=importlib.util.module_from_spec(s); sys.modules["w"]=m; s.loader.exec_module(m)
w=m.inotifywait_factory("/tree",(("",True),))
t0=time.monotonic()
while not w.established():
    if time.monotonic()-t0>10: raise SystemExit("never established")
    time.sleep(0.05)
print("READY",flush=True)
evs=[]; t0=time.monotonic()
while time.monotonic()-t0<6:
    evs+=[[e.path,list(e.names)] for e in w.read_ready()]; time.sleep(0.05)
w.request_stop()
print(json.dumps({"argv":list(w.proc.args),"events":evs}),flush=True)
'''
HOSTILE_NAMES = ("a|b.txt", "x\nqc|OPEN", "planted.tsv|OPEN", ".git|CREATE,ISDIR")
HOSTILE_AGENT = '''import pathlib
for n in %r:
    (pathlib.Path("/tree")/n).write_text("x")
''' % (HOSTILE_NAMES,)


def factory_probe(proof, parent):
    """The image's own sidecar.py factory (its exact argv, NUL framing) and parser over names an agent might write
    to forge events (review of the candidate, finding 1 and nit 10). Candidate-image evidence; no model."""
    scratch = Path(tempfile.mkdtemp(prefix="factory-probe-", dir=parent))
    tree = scratch / "tree"
    tree.mkdir(mode=0o700)
    ids = {}
    out = {"scope": "candidate-image evidence: the image's own factory and parser over hostile names",
           "names": HOSTILE_NAMES}
    try:
        proof.own(tree, 10001)
        ids["watch"] = proof.watcher(["/usr/bin/python3", "-I", "-S", "-c", FACTORY_PROBE], ((tree, "/tree", True),),
                                     detached=True)
        for _ in range(200):
            if "READY" in proof.run(["docker", "logs", ids["watch"]]).stdout:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("factory probe never ready")
        ids["take"] = proof.container(proof.take_image, ["sleep", "infinity"], user="10003:10003",
                                      mounts=((tree, "/tree", False),), detached=True)
        proof.call(["docker", "exec", "--user", "10001:10001", ids["take"], "/usr/bin/python3", "-I", "-S", "-c",
                    HOSTILE_AGENT])
        for _ in range(200):
            logs = proof.run(["docker", "logs", ids["watch"]])
            if logs.stdout.count("\n") >= 2:
                break
            time.sleep(0.05)
        out["stdout"], out["stderr"] = logs.stdout, logs.stderr
        out["result"] = json.loads(logs.stdout.splitlines()[-1])
    finally:
        for cid in reversed(list(ids.values())):
            proof.call(["docker", "rm", "-f", cid], allow_failure=True)
        proof.own(tree, 0)
    shutil.rmtree(scratch)
    out["scratch_removed"] = not scratch.exists()
    out["containers_left"] = _survivors(proof, ids.values())
    return out


def baked_program_sha256(proof) -> str:
    """The sha256 of /opt/w/sidecar.py inside the watcher image (review item 14: the evidence binds to the file)."""
    got = proof.call(["docker", "run", "--pull=never", "--rm", "--network", "none", "--user", "10002:10002",
                      proof.watch_image, "python3", "-I", "-c",
                      "import hashlib;print(hashlib.sha256(open('/opt/w/sidecar.py','rb').read()).hexdigest())"])
    return got.stdout.strip()


def _watch_run():
    """A one-shot run of the watcher image through the fixed launcher (for its version line)."""
    return ["docker", "run", "--pull=never", "--rm", "--network", "none", "--user", "0:0", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", *sum((["--cap-add", c] for c in sidecar.BOOT_CAPABILITIES), []),
            WATCH_IMAGE, *sidecar.WATCHER_LAUNCHER]


def _image_id(v) -> bool:
    return isinstance(v, str) and len(v) == 71 and v.startswith("sha256:") and all(c in "0123456789abcdef" for c in v[7:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-parent", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("component", "stub", "gap", "candidate", "latency"), default="component")
    parser.add_argument("--take-image", help="candidate mode: the built take-a image id")
    parser.add_argument("--watch-image", help="candidate mode: the built sidecar image id")
    parser.add_argument("--source", help="gap mode: the folder holding the sidecar.py under test (read-only)")
    args = parser.parse_args()
    parent = Path(args.scratch_parent)
    if sys.platform != "linux" or parent.is_symlink() or not parent.is_dir() or parent.stat().st_uid != os.getuid():
        raise ValueError("an owned existing Linux scratch parent is required")
    if args.mode == "candidate" and not (_image_id(args.take_image) and _image_id(args.watch_image)):
        raise ValueError("candidate mode names both built images by sha256 id")
    proof = Proof(args.take_image, args.watch_image) if args.mode == "candidate" else Proof()
    report = {"scope": "component-only; no credentials, no model, no production admission", "scenarios": [], "calls": proof.calls}
    try:
        if args.mode == "candidate":
            # Candidate-image evidence: the image's own sidecar.py and its own watcher values, nothing injected.
            report["scope"] = ("candidate-image evidence: built images by id, the image's own sidecar.py and values; "
                               "no credentials, no model, no lock written")
            report["images"] = {"take": args.take_image, "watch": args.watch_image}
            report["baked_sidecar_sha256"] = baked_program_sha256(proof)
            report["factory_probe"] = factory_probe(proof, parent)
            for name in ("oracle", "always-act", "always-hold", "background-writer"):
                report["scenarios"].append(proof.scenario(parent, name, inject=False))
            report["scenarios"].append(proof.scenario(parent, "gap-fresh", watch=GAP_FRESH, script=GAP_PROOF_AGENT,
                                                      inject=False))
            return
        if args.mode == "latency":
            report["scope"] = "new-folder watch latency on an idle athena; provisional images; no credentials, no model"
            report.pop("scenarios")
            report["latency"] = gap_latency(proof, parent)
            return
        if args.mode == "gap":
            if not args.source:
                raise ValueError("--source names the folder holding the sidecar.py under test")
            report["scope"] = "new-folder gap: latency stub and the rescan proof; no credentials, no model"
            report["latency"] = gap_latency(proof, parent)
            report["proof"] = proof.scenario(parent, "gap-fresh", source=Path(args.source), watch=GAP_FRESH,
                                             script=GAP_PROOF_AGENT)
            return
        if args.mode == "stub":
            # Review nit 3 (14 Oct): the label at the top level, and no empty scenario list.
            report["scope"] = "stub measurement of the four watcher constants; not a production pin; no credentials, no model"
            report.pop("scenarios")
            report["stub"] = stub_watcher(proof, parent)
            return
        for name in ("oracle", "always-act", "always-hold", "background-writer"):
            report["scenarios"].append(proof.scenario(parent, name))
    finally:
        with open(args.output, "x", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2); fh.write("\n")


if __name__ == "__main__":
    main()
