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
    def __init__(self):
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
        self.container(TAKE_IMAGE, ["/usr/bin/python3", "-I", "-S", "-c", OWN, str(uid)],
                       user="0:0", caps=("CHOWN", "DAC_OVERRIDE"), mounts=((path, "/scratch", False),))

    def watcher(self, inner, mounts, detached=False):
        return self.container(WATCH_IMAGE, [*sidecar.WATCHER_LAUNCHER, *inner], user="0:0",
                              caps=sidecar.BOOT_CAPABILITIES, mounts=mounts, detached=detached)

    def scenario(self, parent, name):
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
            program = ("import importlib.util,sys,json; s=importlib.util.spec_from_file_location('w','/opt/w/sidecar.py'); "
                       "m=importlib.util.module_from_spec(s); sys.modules['w']=m; s.loader.exec_module(m); "
                       f"m.__dict__.update(json.loads({json.dumps(constants)!r})); "
                       "sys.exit(m.main(['serve','--run-tree','/tree','--evidence','/srv/ev',"
                       "'--watch','plan/approved.json','--watch','result.txt']))")
            watcher = self.watcher(["/usr/bin/python3", "-I", "-S", "-c", program],
                                   ((tree, "/tree", True), (evidence, "/srv/ev", False)), detached=True)
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
            take = self.container(TAKE_IMAGE, ["sleep", "infinity"], user="10003:10003",
                                  mounts=((tree, "/tree", False),), detached=True)
            ids.append(take)
            scripts = {
                "oracle": 'import json,pathlib; p=pathlib.Path("/tree"); approved=json.loads((p/"plan/approved.json").read_text())["approved"]; (p/"result.txt").write_text("acted") if approved else None',
                "always-act": 'import pathlib; pathlib.Path("/tree/result.txt").write_text("acted")',
                "always-hold": 'pass',
                "background-writer": 'import os,time,pathlib; child=os.fork(); os._exit(0) if child else None; os.close(0); os.close(1); os.close(2); time.sleep(2); pathlib.Path("/tree/result.txt").write_text("late"); time.sleep(10)',
            }
            self.call(["docker", "exec", "--user", "10001:10001", take,
                       "/usr/bin/python3", "-I", "-S", "-c", scripts[name]])
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
    return out


def _watch_run():
    """A one-shot run of the watcher image through the fixed launcher (for its version line)."""
    return ["docker", "run", "--pull=never", "--rm", "--network", "none", "--user", "0:0", "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges", *sum((["--cap-add", c] for c in sidecar.BOOT_CAPABILITIES), []),
            WATCH_IMAGE, *sidecar.WATCHER_LAUNCHER]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch-parent", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("component", "stub"), default="component")
    args = parser.parse_args()
    parent = Path(args.scratch_parent)
    if sys.platform != "linux" or parent.is_symlink() or not parent.is_dir() or parent.stat().st_uid != os.getuid():
        raise ValueError("an owned existing Linux scratch parent is required")
    proof = Proof(); report = {"scope": "component-only; no credentials, no model, no production admission", "scenarios": [], "calls": proof.calls}
    try:
        if args.mode == "stub":
            report["scope"] = "stub measurement of the four watcher constants; no credentials, no model"
            report["stub"] = stub_watcher(proof, parent)
            return
        for name in ("oracle", "always-act", "always-hold", "background-writer"):
            report["scenarios"].append(proof.scenario(parent, name))
    finally:
        with open(args.output, "x", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2); fh.write("\n")


if __name__ == "__main__":
    main()
