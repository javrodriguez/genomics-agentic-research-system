#!/usr/bin/env python3
"""CP2's real-box step as a MEASUREMENT road: one no-model stub take on athena's box (glitch-06's rulings, 14 Oct 2026).

NOT A STUDY TAKE. This road measures the values the box defines as "measured at the stub take" (run_take's TOP_FORMAT,
INSPECT_STATUS and TakeSpec resources; scan_record's rules-scanner adapter and pinned version; preflight's
VERSION_PATTERNS) and records raw observations. It never writes a module constant, a lock, a register entry, a take or
walk folder, or anything batch, the walk register or the checker reads:
  - every record it writes carries RECORD_KIND at its top, and its one output file sits in a folder whose name starts
    with FOLDER_PREFIX, outside the study's record folders (STUDY_RECORD_DIRS), never over an existing file;
  - no production module imports it (tests/test_stub_take.py binds that by ast), and the production driver keeps
    refusing every adapter but its own class (drive.adapter_class_problems, unchanged);
  - it has no adapter, no harness exec, no login: a turn is a FIXED stub script run as the agent through
    run_take.agent_exec_argv (preflight's existing plain-exec seam, which carries no variable and reads no login).
    run_take.exec_argv, run_turn and read_login are never called (bound by ast).

WHAT RUNS UNMODIFIED. run_take: DockerRuntime, check_spec, create_argv, proxy_create_argv, network_name, _step, _new_id,
_inspect, refuse_env_files, make_config_dir, teardown, leaked, kill_agent, counters, counter_delta, agent_exec_argv.
sidecar: create_argv, expect_from_argv, start_argv, ctl_argv, rm_argv, parse_completed (and the sidecar image's own
program). preflight: load_take_lock, load_sidecar_lock, load_egress_lock, probes, run, evaluate,
collect_and_evaluate, postflight. scan_record: scan. proxy_conf: render, check.

WHAT DOES NOT, AND WHY (each recorded in the output's `departures`):
  - run_take.launch refuses (NotReady) while INSPECT_STATUS is PENDING, and INSPECT_STATUS is defined as confirmed
    when the stub take reads one inspect. So `launch_mirror` runs launch's body, step for step through run_take's own
    step functions, without `_check_launch_ready` and without the two `inspect_mismatches` comparisons (which return
    the PENDING message while INSPECT_STATUS is PENDING); each inspect is recorded raw instead. A test binds the
    mirror's steps to launch's, argv for argv, on a fake runtime. Once INSPECT_STATUS is filled, this road calls
    run_take.launch itself (`use_launch`).
  - sidecar.expect_from_argv leaves `cap_add` PENDING by design; the road fills it from
    sidecar_contract.BOOT_INSPECT_CAPABILITIES (the committed, measured spelling preflight's own check requires).
  - squid's package user is read again from the locked egress image (getent) and must equal proxy_conf.USER (13:13,
    filled 14 Oct 2026 from these readings); the road passes proxy_conf.USER as ProxyLaunch.user.
  - TakeSpec's resources are the documented caller parameter: the run's values are passed on the command line and
    recorded; the candidates are derived on the Mac by a written rule, never here.

No model, no login, no credential, no network but preflight's own egress probes (a CONNECT to the arm's host through
the take's proxy: a TCP tunnel opened and closed, no request inside it). Linux only; rootless Docker as the caller.

    python3 -B evals/gap-study-4/box/stub_take.py --box <box folder> --scratch-parent <owned folder>
        --output <.../stub-take-<x>/stub-take.json> --gitleaks <binary> --gitleaks-sha256 <hex>
        --take-image sha256:<64> --sidecar-image sha256:<64> --egress-image sha256:<64>
        --codex-image sha256:<64> --gemini-image sha256:<64>
        --memory-reservation <bytes> --cpus <decimal> --pids-limit <n>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import string
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from box import ownership, preflight, rules_scanner, run_take, scan_record, sidecar, sidecar_contract  # noqa: E402
from box.egress import proxy_conf  # noqa: E402
import mode_binding  # noqa: E402  (the record roots' one home; shipped beside box/ to athena)

RECORD_KIND = "stub-take-measurement"
NOT_A_STUDY_RECORD = ("a no-model measurement of the box (CP2's real-box step); never a study take, walk, rehearsal, "
                      "cell or registered attempt")
FOLDER_PREFIX = "stub-take-"
# The study's record folders, imported from the one place the layout rule allows (mode_binding.RECORD_ROOTS:
# TAKES_DIR and WALKS_DIR; test_walk_layout L1). The output may not sit under a folder of either name.
STUDY_RECORD_DIRS = mode_binding.RECORD_ROOTS
HARNESS = run_take.CLAUDE_CODE
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
IMAGE_ROLES = ("take", "sidecar", "egress", "codex", "gemini")
# The take lock of each take image, relative to the box folder (preflight.TAKE_LOCK_DIRS' folders).
TAKE_LOCKS = {"take": (run_take.CLAUDE_CODE, "image.lock"), "codex": (run_take.CODEX, "codex/image.lock"),
              "gemini": (run_take.GEMINI, "gemini/image.lock")}
WATCH = ("plan/approved.json", "result.txt")
PLANTED = {"plan/approved.json": '{"approved": false}\n'}
LAUNCH_STEPS = ("network-create", "proxy-create", "proxy-connect", "proxy-start", "sidecar-create", "sidecar-inspect",
                "sidecar-start", "take-create", "take-inspect", "take-start")

# The fixed stub scripts (no model): each runs as the agent, `python3 -I -S -c <script> <args>`, in the run tree.
TURNS = (
    ("reads-nothing", "pass", ()),
    ("reads-planted", "import sys\nopen(sys.argv[1]).read()", ("plan/approved.json",)),
    ("background-writer", "import os,sys,time\nif os.fork():\n os._exit(0)\nos.setsid()\nfor fd in (0,1,2):\n os.close(fd)\n"
                          "time.sleep(3)\nopen(sys.argv[1],'w').write('late')\ntime.sleep(120)", ("result.txt",)),
)
TURN_TIMEOUT_S = 60
LATE_WAIT_S = 4.5
# `docker top` forms measured while the background writer lives (TOP_FORMAT's ps_options are chosen from these).
TOP_FORMS = {"default": [], "eo-pid-uid-comm": ["-eo", "pid,uid,comm"], "o-pid-uid-comm": ["-o", "pid,uid,comm"],
             "eo-pid-user-uid-args": ["-eo", "pid,user,uid,args"]}
CGROUP_FILES = ("cpu.max", "memory.max", "memory.low", "memory.min", "memory.high", "pids.max", "memory.current",
                "memory.peak", "pids.current", "pids.peak", "memory.events", "pids.events", "cpu.stat")
FALLBACK_PROGRAM = r'''import json,os,re,sys
root=sys.argv[1]; names={}; files=0; skipped=[]
pat=re.compile(rb"[A-Z][A-Z0-9_]*FALLBACK[A-Z0-9_]*")
for base,dirs,fs in os.walk(root):
    dirs.sort()
    for f in sorted(fs):
        p=os.path.join(base,f)
        try:
            if os.path.islink(p): continue
            if os.path.getsize(p)>200*1024*1024: skipped.append([os.path.relpath(p,root),os.path.getsize(p)]); continue
            data=open(p,"rb").read()
        except OSError: continue
        files+=1
        for m in pat.finditer(data):
            n=m.group().decode()
            e=names.setdefault(n,{"count":0,"files":[],"contexts":[]})
            e["count"]+=1
            rel=os.path.relpath(p,root)
            if rel not in e["files"]: e["files"].append(rel)
            if len(e["contexts"])<3:
                s=data[max(0,m.start()-120):m.end()+120].decode("latin-1")
                e["contexts"].append("".join(c if 32<=ord(c)<127 else "." for c in s))
print(json.dumps({"root":root,"files_read":files,"skipped_over_200MiB":skipped,"names":names},sort_keys=True))
'''
CLAUDE_PACKAGE = "/usr/local/lib/node_modules/@anthropic-ai/claude-code"
VERSION_HOME = "/tmp"


class StubTakeRefused(ValueError):
    """The road refuses before any runtime call: a missing or short image id, a lock that disagrees, an output folder
    off its rule. The message names the rule."""


def _labelled(doc: dict) -> dict:
    """The record with its label; a record that carries a label of its own is refused, never relabelled."""
    if set(doc) & {"record_kind", "not_a_study_record"}:
        raise StubTakeRefused("the record carries a label of its own")
    return {"record_kind": RECORD_KIND, "not_a_study_record": NOT_A_STUDY_RECORD, **doc}


def check_images(images: dict) -> dict:
    """Every role's image named by a full sha256 id: no tag, no short id, no default."""
    if not isinstance(images, dict) or set(images) != set(IMAGE_ROLES):
        raise StubTakeRefused(f"the images are named for exactly {list(IMAGE_ROLES)}")
    for role, image in images.items():
        if not isinstance(image, str) or not IMAGE_ID.fullmatch(image):
            raise StubTakeRefused(f"the {role} image must be a full image id, sha256:<64 hex>, never a tag or a "
                                  f"short id")
    return dict(images)


def check_output(path: str) -> str:
    """The output is one new file in a folder named stub-take-*, outside the study's record folders."""
    if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
        raise StubTakeRefused("the output is a normalised absolute path")
    folder = os.path.dirname(path)
    if not os.path.basename(folder).startswith(FOLDER_PREFIX):
        raise StubTakeRefused(f"the output's folder is named {FOLDER_PREFIX}*, so no reader takes it for a take")
    if set(path.split(os.sep)) & set(STUDY_RECORD_DIRS):
        raise StubTakeRefused(f"the output never sits under a study record folder ({', '.join(STUDY_RECORD_DIRS)})")
    if os.path.lexists(path):
        raise StubTakeRefused("the output already exists: a record is never written over")
    return path


def load_locks(box: str, images: dict) -> dict:
    """Each lock through preflight's own loaders; each must name the image id given on the command line."""
    box = run_take._abs_path(box, "box")
    take_lock = os.path.join(box, TAKE_LOCKS["take"][1])
    out = {"take_lock_path": take_lock,
           "take": preflight.load_take_lock(take_lock, harness=HARNESS),
           "sidecar": preflight.load_sidecar_lock(take_lock, harness=HARNESS),
           "egress": preflight.load_egress_lock(take_lock, harness=HARNESS)}
    for role in ("codex", "gemini"):
        harness, rel = TAKE_LOCKS[role]
        out[role] = preflight.load_take_lock(os.path.join(box, rel), harness=harness)
    for role in IMAGE_ROLES:
        if out[role]["image_id"] != images[role]:
            raise StubTakeRefused(f"the {role} image given is not its committed lock's image id")
    return out


def sidecar_launch(*, image: str, run_tree: str, evidence: str) -> run_take.SidecarLaunch:
    """The sidecar's launch, from sidecar.py's own create_argv and expect_from_argv. Departure: expect_from_argv's
    cap_add stays PENDING by design; it is filled with sidecar_contract.BOOT_INSPECT_CAPABILITIES."""
    argv = sidecar.create_argv(image=image, run_tree=run_tree, evidence=evidence, watch=list(WATCH))
    expect = sidecar.expect_from_argv(argv)
    expect["cap_add"] = list(sidecar_contract.BOOT_INSPECT_CAPABILITIES)
    return run_take.SidecarLaunch(create_argv=tuple(argv), start_argv_for=sidecar.start_argv,
                                  ctl_argv_for=sidecar.ctl_argv, rm_argv_for=sidecar.rm_argv, expect=expect)


def use_launch() -> bool:
    """run_take.launch itself, once INSPECT_STATUS is no longer PENDING."""
    return not run_take._is_pending(run_take.INSPECT_STATUS)


def launch_mirror(runtime, spec, *, sidecar: run_take.SidecarLaunch, proxy: run_take.ProxyLaunch, record_dir: str,
                  caller_env=None) -> run_take.Launched:
    """run_take.launch's body, step for step, without _check_launch_ready and the two inspect comparisons (each
    inspect is recorded raw in its step). Every other check and every step is run_take's own."""
    run_take.check_spec(spec)
    run_take.refuse_env_files(workdir=spec.run_tree, run_tree=spec.run_tree, config_dir=spec.config_dir)
    run_take._check_proxy(proxy)
    run_take._check_sidecar(sidecar)
    record_dir = run_take._abs_path(record_dir, "record_dir")
    if not os.path.isdir(record_dir) or os.path.lexists(os.path.join(record_dir, run_take.LAUNCH_RECORD)):
        raise run_take.Refused("the record folder must exist and hold no launch record yet")
    if not os.path.isdir(spec.config_dir) or not run_take.outside_every_repository(spec.config_dir):
        raise run_take.Refused("the per-take config folder must exist outside every repository")
    env = run_take.runtime_env(caller_env)
    launched = run_take.Launched(config_dir=spec.config_dir)
    client = run_take.RUNTIME_CLIENT
    try:
        c = run_take._step(runtime, launched, "network-create",
                           [client, "network", "create", "--internal", run_take.network_name()], env)
        launched.network_id = run_take._new_id(c, "network-create")
        c = run_take._step(runtime, launched, "proxy-create", run_take.proxy_create_argv(launched.network_id, proxy),
                           env)
        launched.proxy_id = run_take._new_id(c, "proxy-create")
        run_take._step(runtime, launched, "proxy-connect",
                       [client, "network", "connect", run_take.DEFAULT_NETWORK, launched.proxy_id], env)
        run_take._step(runtime, launched, "proxy-start", [client, "start", launched.proxy_id], env)
        c = run_take._step(runtime, launched, "sidecar-create", run_take.sidecar_create_argv(sidecar), env)
        launched.sidecar_id = run_take._new_id(c, "sidecar-create")
        run_take._inspect(runtime, launched, "sidecar-inspect", launched.sidecar_id, env)
        run_take._step(runtime, launched, "sidecar-start", list(sidecar.start_argv_for(launched.sidecar_id)), env)
        launched.spec = spec = run_take._on_network(spec, launched.network_id)
        c = run_take._step(runtime, launched, "take-create", run_take.create_argv(spec), env)
        launched.take_id = run_take._new_id(c, "take-create")
        run_take._inspect(runtime, launched, "take-inspect", launched.take_id, env)
        run_take._step(runtime, launched, "take-start", [client, "start", launched.take_id], env)
    except Exception as exc:  # as launch: tear down by recorded id, record, carry the record out
        launched.failure = str(exc) if isinstance(exc, (run_take._StepFailed, run_take.Refused,
                                                        run_take.NotReady)) else type(exc).__name__
        run_take._teardown_partial(runtime, launched, sidecar, record_dir, env)
        run_take._write_json(os.path.join(record_dir, run_take.LAUNCH_RECORD), launched.to_record())
        raise run_take.LaunchError(f"launch failed: {launched.failure}", launched) from exc
    launched.ok = True
    run_take._write_json(os.path.join(record_dir, run_take.LAUNCH_RECORD), launched.to_record())
    return launched


# ------------------------------------------------------------------------------------------------ the athena side
class Recorder:
    """run_take.DockerRuntime, every call recorded (argv, exit, output). The caller's env is used as given."""

    def __init__(self):
        self.inner = run_take.DockerRuntime()
        self.calls = []

    def run(self, argv, *, env=None, timeout=None):
        at = time.time()
        try:
            c = self.inner.run(argv, env=env, timeout=timeout)
        except TimeoutError as e:
            self.calls.append({"argv": list(argv), "at": at, "timed_out": True})
            raise e
        self.calls.append({"argv": list(argv), "at": at, "returncode": c.returncode, "stdout": c.stdout,
                           "stderr": c.stderr})
        return c


def _client_env() -> dict:
    uid = os.getuid()
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
            "DOCKER_HOST": f"unix:///run/user/{uid}/docker.sock", "XDG_RUNTIME_DIR": f"/run/user/{uid}"}


def _own(runtime, env, image: str, path: str, uid: int) -> None:
    """Chown a scratch folder's whole tree to a container uid through a one-shot root container of the take image
    (measure_live's reviewed descriptor walk: never follows a link, refuses a special file)."""
    from box import measure_live
    c = runtime.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", "0:0", "--cap-drop", "ALL",
                     "--cap-add", "CHOWN", "--cap-add", "DAC_OVERRIDE", "--security-opt", "no-new-privileges",
                     "--mount", f"type=bind,source={path},target=/scratch", image,
                     "/usr/bin/python3", "-I", "-S", "-c", measure_live.OWN, str(uid)], env=env, timeout=120)
    if c.returncode != 0:
        raise RuntimeError(f"the ownership step failed for {path} (exit {c.returncode})")


def _host_read(path: str):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError as e:
        return {"error": type(e).__name__}


def _inspect_paths(obj: dict) -> dict:
    out = {}
    for key, dotted in run_take.INSPECT_PATHS.items():
        try:
            v = run_take._path_get(obj, dotted)
            out[key] = {"path": dotted, "found": True, "type": type(v).__name__,
                        "value": v if not isinstance(v, (list, dict)) or len(json.dumps(v)) < 2000 else "<long>"}
        except (KeyError, TypeError):
            out[key] = {"path": dotted, "found": False}
    return out


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _turn(runtime, env, take_id: str, run_tree: str, name: str, script: str, args) -> dict:
    inner = ["/usr/bin/python3", "-I", "-S", "-c", script, *[os.path.join(run_tree, a) for a in args]]
    argv = run_take.agent_exec_argv(take_id, inner, workdir=run_tree)
    started = time.time()
    c = runtime.run(argv, env=env, timeout=TURN_TIMEOUT_S)
    return {"turn": name, "argv_seam": "run_take.agent_exec_argv", "returncode": c.returncode, "stdout": c.stdout,
            "stderr": c.stderr, "started_at": started, "ended_at": time.time()}


def _ctl(runtime, env, sidecar_id: str, command: str, label=None) -> dict:
    c = runtime.run(sidecar.ctl_argv(sidecar_id, command, label), env=env, timeout=run_take.STEP_TIMEOUT_S)
    try:
        return {"parsed": sidecar.parse_completed(c), "returncode": c.returncode}
    except Exception as e:  # recorded: a ctl reply off its shape is a finding
        return {"error": type(e).__name__, "detail": str(e)[:300], "returncode": c.returncode, "stdout": c.stdout,
                "stderr": c.stderr}


def _top(runtime, env, take_id: str) -> dict:
    out = {}
    for name, opts in TOP_FORMS.items():
        c = runtime.run(["docker", "top", take_id, *opts], env=env, timeout=60)
        rows = [ln.split() for ln in c.stdout.splitlines() if ln.strip()]
        host = {}
        if rows and "PID" in rows[0]:
            pi = rows[0].index("PID")
            for r in rows[1:]:
                if len(r) > pi and r[pi].isdigit():
                    st = _host_read(f"/proc/{r[pi]}/status")
                    uid = [ln.split()[1:] for ln in st.splitlines() if ln.startswith("Uid:")] if isinstance(st, str) \
                        else st
                    host[r[pi]] = uid
        out[name] = {"options": opts, "returncode": c.returncode, "stdout": c.stdout, "stderr": c.stderr,
                     "host_proc_uid_by_pid": host}
    return out


def _cgroup(pid: int) -> dict:
    raw = _host_read(f"/proc/{pid}/cgroup")
    out = {"proc_cgroup": raw, "uid_map": _host_read(f"/proc/{pid}/uid_map"),
           "gid_map": _host_read(f"/proc/{pid}/gid_map")}
    if isinstance(raw, str):
        lines = [ln for ln in raw.splitlines() if ln.startswith("0::")]
        if len(lines) == 1:
            d = "/sys/fs/cgroup" + lines[0][3:]
            out["cgroup_dir"] = d
            out["files"] = {f: _host_read(os.path.join(d, f)) for f in CGROUP_FILES}
    return out


def _evidence_files(evidence: str) -> dict:
    out = {}
    for base, dirs, files in os.walk(evidence):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(base, f)
            rel = os.path.relpath(p, evidence)
            out[rel] = {"sha256": _sha256_file(p), "bytes": os.path.getsize(p),
                        "text": _host_read(p) if os.path.getsize(p) < 200_000 else "<large>"}
    return out


def _scan_kind(rel: str) -> str:
    top = rel.split(os.sep)[0]
    return {"snapshots": "snapshot", "blobs": "blob"}.get(top, "evidence")


def run_stub_take(a) -> dict:
    images = check_images({r: getattr(a, f"{r}_image") for r in IMAGE_ROLES})
    output = check_output(a.output)
    locks = load_locks(a.box, images)
    if sys.platform != "linux":
        raise StubTakeRefused("the stub take runs on athena's Linux box only")
    parent = run_take._abs_path(a.scratch_parent, "scratch_parent")
    if os.path.islink(parent) or not os.path.isdir(parent) or os.stat(parent).st_uid != os.getuid() \
            or not run_take.outside_every_repository(parent):
        raise StubTakeRefused("the scratch parent is an owned folder outside every repository")
    if run_take._inside(output, parent):
        raise StubTakeRefused("the output never sits in the scratch it removes")
    env = _client_env()
    runtime = Recorder()
    rec = {"started_at": time.time(), "images": images, "box": a.box, "harness": HARNESS,
           "locks": {k: v for k, v in locks.items() if k != "take_lock_path"}, "departures": [],
           "unmodified": ["run_take.DockerRuntime", "run_take.check_spec", "run_take.create_argv",
                          "run_take.proxy_create_argv", "run_take._step", "run_take._inspect", "run_take.teardown",
                          "run_take.leaked", "run_take.kill_agent", "run_take.counters", "run_take.counter_delta",
                          "run_take.agent_exec_argv", "run_take.make_config_dir", "run_take.refuse_env_files",
                          "sidecar.create_argv", "sidecar.expect_from_argv", "sidecar.ctl_argv",
                          "sidecar.parse_completed", "preflight.collect_and_evaluate", "preflight.probes",
                          "preflight.run", "preflight.evaluate", "preflight.postflight", "scan_record.scan",
                          "proxy_conf.render", "proxy_conf.check", "ownership.grant", "ownership.restore",
                          "run_take.launch (when use_launch())"]}
    rec["runtime"] = {"version": runtime.run(["docker", "version", "--format", "{{json .}}"], env=env, timeout=60).stdout,
                      "driver_status": runtime.run(["docker", "info", "--format", "{{json .DriverStatus}}"], env=env,
                                                   timeout=60).stdout,
                      "cgroup_version": runtime.run(["docker", "info", "--format", "{{.CgroupVersion}} {{.CgroupDriver}}"],
                                                    env=env, timeout=60).stdout.strip(),
                      "meminfo": _host_read("/proc/meminfo"), "nproc": os.cpu_count(),
                      "pid_max": _host_read("/proc/sys/kernel/pid_max"),
                      "max_user_watches": _host_read("/proc/sys/fs/inotify/max_user_watches"),
                      # review finding 3: the user slice's pids.max, read raw (the resources policy divides it)
                      "user_slice_pids_max": _host_read(f"/sys/fs/cgroup/user.slice/user-{os.getuid()}.slice/pids.max")}
    # squid's package user, read again from the locked egress image: it must be proxy_conf.USER
    g = runtime.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--cap-drop", "ALL",
                     "--security-opt", "no-new-privileges", "--entrypoint", "getent", images["egress"], "passwd",
                     "proxy"], env=env, timeout=120)
    fields = g.stdout.strip().split(":")
    if g.returncode != 0 or len(fields) != 7 or not fields[2].isdigit() or not fields[3].isdigit():
        raise RuntimeError("squid's package user could not be read from the egress image")
    proxy_user = f"{fields[2]}:{fields[3]}"
    if proxy_user != proxy_conf.USER:
        raise StubTakeRefused(f"squid's user in the egress image is {proxy_user}, not proxy_conf.USER")
    rec["squid_user"] = {"getent": g.stdout, "user": proxy_user}
    # --version forms of the three take images (no network, no login: a fresh one-shot container as the agent)
    rec["versions"] = {}
    for role, (harness, _rel) in TAKE_LOCKS.items():
        home = {k: VERSION_HOME for k in preflight._config_home_values(harness)}
        argv = ["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", run_take.AGENT_USER,
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "-e", f"HOME={VERSION_HOME}"]
        for k, v in sorted(home.items()):
            argv += ["-e", f"{k}={v}"]
        cmd = preflight.VERSION_COMMANDS[harness]
        c = runtime.run([*argv, "--entrypoint", cmd[0], images[role], *cmd[1:]], env=env, timeout=120)
        rec["versions"][harness] = {"image": images[role], "lock_version": locks[role]["harness.version"],
                                    "returncode": c.returncode, "stdout": c.stdout, "stderr": c.stderr}
    # Claude Code's fallback variables, read from the pinned package in the take image (names only, with context)
    c = runtime.run(["docker", "run", "--rm", "--pull=never", "--network", "none", "--user", run_take.AGENT_USER,
                     "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--entrypoint", "/usr/bin/python3",
                     images["take"], "-I", "-S", "-c", FALLBACK_PROGRAM, CLAUDE_PACKAGE], env=env, timeout=300)
    rec["fallback_names"] = {"returncode": c.returncode, "stdout": c.stdout, "stderr": c.stderr[:2000]}
    # gitleaks, the rules scanner candidate
    rec["gitleaks"] = {"binary": a.gitleaks, "sha256": _sha256_file(a.gitleaks),
                       "version": runtime.run([a.gitleaks, "version"], env=env, timeout=60).stdout.strip()}

    base = tempfile.mkdtemp(prefix="st-", dir=parent)
    run_tree, evidence, records = (os.path.join(base, n) for n in ("t", "e", "r"))
    if a.seed_tree:   # an admitted run tree already on the box, copied (links kept as links) to size the snapshots
        seed = run_take._abs_path(a.seed_tree, "seed_tree")
        shutil.copytree(seed, run_tree, symlinks=True)
        os.chmod(run_tree, 0o755)
        rec["seed_tree"] = {"source": seed, "files": sum(len(f) for _b, _d, f in os.walk(run_tree)),
                            "folders": sum(len(d) for _b, d, _f in os.walk(run_tree))}
    else:
        os.mkdir(run_tree, 0o755)
    os.mkdir(evidence, 0o755)
    os.mkdir(records, 0o755)
    for rel, text in PLANTED.items():
        os.makedirs(os.path.dirname(os.path.join(run_tree, rel)), exist_ok=True)
        with open(os.path.join(run_tree, rel), "w", encoding="utf-8") as fh:
            fh.write(text)
    cfg = run_take.make_config_dir(base)
    conf = os.path.join(base, "proxy.conf")
    text = proxy_conf.render(HARNESS)
    rec["proxy_conf_check"] = proxy_conf.check(text, HARNESS)
    with open(conf, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(conf, 0o644)
    rec["scratch"] = {"base": base, "run_tree": run_tree, "evidence": evidence, "records": records, "config": cfg}
    sl = sidecar_launch(image=images["sidecar"], run_tree=run_tree, evidence=evidence)
    rec["departures"].append("sidecar expect cap_add filled from sidecar_contract.BOOT_INSPECT_CAPABILITIES "
                             "(expect_from_argv leaves it PENDING by design)")
    proxy = run_take.ProxyLaunch(image=images["egress"], conf_source=conf, conf_target=proxy_conf.CONF_PATH,
                                 command=tuple(proxy_conf.COMMAND), user=proxy_user, alias=run_take.PROXY_ALIAS)
    spec = run_take.TakeSpec(image=images["take"], run_tree=run_tree, config_dir=cfg, network="0" * 64,
                             memory_reservation=a.memory_reservation, memory=3 * a.memory_reservation, cpus=a.cpus,
                             pids_limit=a.pids_limit)
    rec["spec_resources"] = {"memory_reservation": spec.memory_reservation, "memory": spec.memory, "cpus": spec.cpus,
                             "pids_limit": spec.pids_limit, "source": "the run's command line (TakeSpec's documented "
                                                                     "caller parameter); not a candidate"}
    launched = None
    try:
        # the ownership road, as production will run it (review finding 9; box/ownership.py)
        rec["grant"] = ownership.grant(runtime, image=images["take"], run_tree=run_tree, config_dir=cfg,
                                       evidence_dir=evidence, caller_env=env)
        if use_launch():
            launched = run_take.launch(runtime, spec, sidecar=sl, proxy=proxy, record_dir=records, caller_env=env)
            rec["launch_road"] = "run_take.launch"
        else:
            rec["departures"].append("run_take.launch refuses while INSPECT_STATUS is PENDING: launch_mirror ran its "
                                     "steps through run_take's own step functions, inspects recorded raw")
            launched = launch_mirror(runtime, spec, sidecar=sl, proxy=proxy, record_dir=records, caller_env=env)
            rec["launch_road"] = "stub_take.launch_mirror"
        rec["launch"] = launched.to_record()
        take_inspect = [s for s in launched.steps if s.get("step") == "take-inspect"][0]["inspect"]
        side_inspect = [s for s in launched.steps if s.get("step") == "sidecar-inspect"][0]["inspect"]
        rec["inspect_paths"] = {"take": _inspect_paths(take_inspect), "sidecar": _inspect_paths(side_inspect)}
        # the sidecar's control channel, then begin (pre-1)
        for _ in range(400):
            st = runtime.run(sidecar.ctl_argv(launched.sidecar_id, "status"), env=env, timeout=60)
            reply = json.loads(st.stdout) if st.stdout.startswith("{") else {}
            if st.returncode == 0 or reply.get("problems") == ["the sidecar is new"]:
                break
            time.sleep(0.05)
        begin = _ctl(runtime, env, launched.sidecar_id, "begin")
        rec["begin"] = begin
        begin_reply = begin.get("parsed")
        # preflight: the drive step's one entry point, then its parts for the raw records
        rec["preflight"] = preflight.collect_and_evaluate(runtime, launched=launched, sidecar=sl,
                                                          lock_path=locks["take_lock_path"], harness=HARNESS,
                                                          hosts=dict(proxy_conf.HOSTS), evidence_dir=evidence,
                                                          begin_reply=begin_reply, caller_env=env)
        probe_list = preflight.probes(launched.spec, take_id=launched.take_id, sidecar_id=launched.sidecar_id,
                                      harness=HARNESS, hosts=dict(proxy_conf.HOSTS), evidence_dir=evidence,
                                      sidecar_image=sl.expect["image"], proxy_id=launched.proxy_id,
                                      proxy_image=preflight._proxy_launch_image(launched))
        raw = preflight.run(runtime, probe_list, begin_reply=begin_reply, caller_env=env)
        rec["preflight_raw"] = raw
        rec["preflight_parts"] = preflight.evaluate(raw, spec=launched.spec, lock=locks["take"], sidecar_expect=sl.expect,
                                                    harness=HARNESS, hosts=dict(proxy_conf.HOSTS), evidence_dir=evidence,
                                                    sidecar_lock=locks["sidecar"], egress_lock=locks["egress"])
        pid = take_inspect.get("State", {}).get("Pid")
        live = runtime.run(["docker", "container", "inspect", launched.take_id], env=env, timeout=60)
        live_obj = json.loads(live.stdout)[0]
        rec["take_inspect_running"] = {"inspect": live_obj, "paths": _inspect_paths(live_obj)}
        pid = live_obj.get("State", {}).get("Pid") or pid
        rec["cgroup_before"] = _cgroup(pid)
        cg = rec["cgroup_before"].get("cgroup_dir")
        before = run_take.counters(cg) if cg else None
        rec["turns"] = []
        for k, (name, script, args) in enumerate(TURNS, start=1):
            if k > 1:
                rec["turns"].append({"snapshot": f"pre-{k}", **_ctl(runtime, env, launched.sidecar_id, "snapshot",
                                                                    f"pre-{k}")})
            rec["turns"].append(_turn(runtime, env, launched.take_id, run_tree, name, script, args))
            if name == "background-writer":
                rec["top_live"] = _top(runtime, env, launched.take_id)
                rec["cgroup_live"] = _cgroup(pid)
                time.sleep(LATE_WAIT_S)
                killed = run_take.kill_agent(runtime, launched.take_id, agent_user=run_take.AGENT_USER,
                                             caller_env=env)
                rec["kill"] = {"returncode": killed.returncode, "stdout": killed.stdout, "stderr": killed.stderr}
                time.sleep(0.5)
                rec["top_after_kill"] = _top(runtime, env, launched.take_id)
            rec["turns"].append({"snapshot": f"post-{k}", **_ctl(runtime, env, launched.sidecar_id, "snapshot",
                                                                 f"post-{k}")})
        rec["cgroup_after"] = _cgroup(pid)
        # the sidecar's and the proxy's caps and peaks (P-2): their own cgroups, read host-side
        rec["companions"] = {}
        for role, cid in (("sidecar", launched.sidecar_id), ("proxy", launched.proxy_id)):
            obj = json.loads(runtime.run(["docker", "container", "inspect", cid], env=env, timeout=60).stdout)[0]
            cgc = _cgroup(obj.get("State", {}).get("Pid"))
            rec["companions"][role] = {"HostConfig.Memory": obj.get("HostConfig", {}).get("Memory"),
                                       "cgroup": {k: (cgc.get("files") or {}).get(k) for k in
                                                  ("memory.max", "memory.peak", "memory.current", "memory.events")}}
        after = run_take.counters(cg) if cg else None
        rec["counters"] = {"before": before, "after": after,
                           "delta": run_take.counter_delta(before, after) if before and after else None}
        state = runtime.run(["docker", "container", "inspect", launched.take_id], env=env, timeout=60)
        rec["take_state_after_turns"] = json.loads(state.stdout)[0].get("State")
    except Exception as e:  # recorded; the teardown below still runs on whatever was launched
        rec["failure"] = {"type": type(e).__name__, "detail": str(e)[:2000]}
        if isinstance(e, run_take.LaunchError):
            rec["launch"] = e.launched.to_record()
    finally:
        if launched is not None and launched.ok:
            try:
                rec["teardown"] = run_take.teardown(runtime, launched, sidecar=sl, record_dir=records, caller_env=env)
            except run_take.TeardownError as e:
                rec["teardown"] = {"error": str(e), **e.record}
            ids = launched.ids()
            rec["leaked_after_teardown"] = run_take.leaked(runtime, ids, caller_env=env)
            nets = runtime.run(["docker", "network", "ls", "--no-trunc", "-q", "--filter", f"id={launched.network_id}"],
                               env=env, timeout=60)
            rec["network_left"] = nets.stdout.strip()
        rec["ownership_before_restore"] = {n: {"uid": os.stat(p).st_uid, "mode": oct(os.stat(p).st_mode & 0o7777)}
                                           for n, p in (("run_tree", run_tree), ("evidence", evidence),
                                                        ("config", cfg))}
        try:   # after teardown, before postflight, the scan and the removal: production's order
            rec["restore"] = ownership.restore(runtime, image=images["take"], run_tree=run_tree, config_dir=cfg,
                                               evidence_dir=evidence, ids=launched.ids() if launched else [],
                                               caller_env=env)
        except ownership.OwnershipError as e:
            rec["restore"] = {"error": str(e), **e.record}
            for p in (run_tree, cfg, evidence):   # the scratch is still removed; the failure stays recorded
                _own(runtime, env, images["take"], p, 0)
        rec["postflight"] = preflight.postflight(cfg, HARNESS)
        rec["evidence"] = _evidence_files(evidence)
        rec["run_tree_after"] = {os.path.relpath(os.path.join(b, f), run_tree): _host_read(os.path.join(b, f))
                                 for b, _d, fs in os.walk(run_tree) for f in fs}
        rec["records"] = {f: _host_read(os.path.join(records, f)) for f in sorted(os.listdir(records))}
    # the scan: scan_record.scan over the stub's records with the candidate gitleaks adapter and a planted fake value
    fake = secrets.token_hex(16)
    stream = os.path.join(records, "turn-1.stub.jsonl")
    with open(stream, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "stub", "text": "planted " + fake + " end"}) + "\n")
    files = [(os.path.join(records, f), "launch" if f == run_take.LAUNCH_RECORD else "proxy-log")
             for f in sorted(os.listdir(records)) if f in (run_take.LAUNCH_RECORD, run_take.PROXY_LOG)]
    files += [(os.path.join(evidence, rel), _scan_kind(rel)) for rel in sorted(rec.get("evidence", {}))]
    files.append((stream, "stream"))
    reports = os.path.join(base, "gl")
    os.mkdir(reports, 0o700)
    if a.gitleaks_sha256 != rules_scanner.GITLEAKS_SHA256:
        raise StubTakeRefused("the gitleaks sha256 given is not the production pin")
    scanner = rules_scanner.gitleaks_scanner(runtime, reports, binary=a.gitleaks, caller_env=env)
    clean = scan_record.scan(files, [("token", fake)], rules_scanner=scanner)
    with open(stream, encoding="utf-8") as fh:
        rec["scan_clean"] = {"result": clean, "value_gone": fake not in fh.read(),
                             "files": [[p, k] for p, k in files]}
    probe = os.path.join(records, "turn-2.stub.jsonl")
    shaped = "ghp_" + "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(36))
    with open(probe, "w", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "stub", "text": "token " + shaped}) + "\n")
    rule = scan_record.scan([(probe, "stream")], [("token", fake)], rules_scanner=scanner)
    rec["scan_rule_probe"] = {"result": rule, "note": "a GitHub-token-shaped fake made at run time; the value is never "
                                                      "recorded (gitleaks --redact, the result names path/line/rule)"}
    del fake, shaped
    rec["gitleaks_reports"] = {f: _host_read(os.path.join(reports, f)) for f in sorted(os.listdir(reports))}
    shutil.rmtree(base)
    rec["scratch_removed"] = not os.path.lexists(base)
    rec["calls"] = runtime.calls
    rec["ended_at"] = time.time()
    return rec


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--box", required=True)
    p.add_argument("--scratch-parent", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--gitleaks", required=True)
    p.add_argument("--gitleaks-sha256", required=True)
    for r in IMAGE_ROLES:
        p.add_argument(f"--{r}-image", required=True)
    p.add_argument("--memory-reservation", type=int, required=True)
    p.add_argument("--cpus", required=True)
    p.add_argument("--pids-limit", type=int, required=True)
    p.add_argument("--seed-tree", help="an admitted run tree on the box, copied into the stub's run tree")
    a = p.parse_args(argv)
    check_images({r: getattr(a, f"{r}_image") for r in IMAGE_ROLES})
    output = check_output(a.output)
    rec = _labelled(run_stub_take(a))
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True, default=str)
        fh.write("\n")
    print(json.dumps({"record_kind": RECORD_KIND, "output": output, "sha256": _sha256_file(output),
                      "failure": rec.get("failure"), "preflight_ok": (rec.get("preflight") or {}).get("ok")}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
