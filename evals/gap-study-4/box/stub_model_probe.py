#!/usr/bin/env python3
"""Lane vendor-b27 (glitch-f1's rulings 1 and 4 on the B27 design, 21 Oct 2026): the stub-model probe, a MEASUREMENT
road on athena's walk box that lets the pinned Gemini CLI's own recorder write the three refused history-rewrite roads
(a resume after a masking re-record, true chat compression, content truncation) against a scripted stub model.

NOT A STUDY TAKE. It never touches a counted walk, a record, the register, a module constant or a lock:
  - every record it writes carries RECORD_KIND at its top, and its output is one new folder whose name starts with
    FOLDER_PREFIX, outside the study's record folders (STUDY_RECORD_DIRS), never over an existing path;
  - no production module imports it (tests/test_stub_model_probe.py binds that by ast; walk_launch names its path only
    in the `probe` entry's remote command);
  - run_take.exec_argv, run_turn and read_login are never called (bound by ast): there is no login. The production take
    road stays closed to the base URL: run_take refuses GOOGLE_GEMINI_BASE_URL for every arm (GEMINI_PACKAGE_SWEEP_REFUSED,
    run_take.check_environment), and nothing here changes that.

WHAT RUNS UNMODIFIED (the walks' code): run_take.create_argv (the locked take-g image by id, `--pull=never`, a read-only
root with the run tree and the config folder as the two bind mounts), run_take.check_spec, make_config_dir, _step,
_new_id, _inspect, network_name, leaked, take_environment (the arm G row), launcher_argv (the agent starts from an
empty environment plus exactly the probe's row, as every walk turn does), check_model, agent_exec_argv;
take_config.write and config_sha256 (the study's own settings file for the model, byte for byte); gemini_adapter.argv
(`gemini -p <line> -o stream-json -m <model> --approval-mode yolo`, `-r <session id>` after process 1);
native_snapshot.gemini_session_rel and retain_bytes (the session file located and retained after each process, before
the next exec); ownership.grant, operator_list, operator_read and restore.

WHAT DOES NOT, AND WHY (each recorded in the output's `departures`):
  - exactly three environment changes from the arm G row (glitch-f1's ruling 1): GOOGLE_GEMINI_BASE_URL is the stub on
    127.0.0.1 inside the container, GEMINI_API_KEY is DUMMY_KEY (a fixed dummy string, never a credential), and
    HTTPS_PROXY is absent; probe_environment computes them from run_take.take_environment and environment_changes
    refuses any other difference;
  - no proxy and no sidecar: the take container sits alone on a fresh `docker network create --internal` network, so it
    has no route out at all (loopback inside it is all the stub needs), and nothing watches the run tree;
  - so run_take.launch is not used (it creates the proxy and the sidecar), and run_take.teardown is not either (it
    removes both and captures the proxy's log, and refuses a record without them): the teardown is run_take's own
    by-recorded-id remover for a partial launch, _teardown_partial, which removes the take container, then the network,
    followed by run_take.leaked and a network listing;
  - the exec argv is exec_argv's form (`docker exec --user <agent> --workdir <run tree> -e GEMINI_API_KEY <id>
    <launcher>`), built here because exec_argv reads a login file and refuses the base URL; a test binds the two forms;
  - the A1-fake cross-check (ruling 4) appends the CLI's hidden `--fake-responses <file>` flag (Q2G:8205-8216), which
    check_model refuses as off the study argv, so check_model reads the study argv before the flag is appended;
    the pinned CLI's FakeContentGenerator replays its file from response 1 in every process, so each process gets
    its own file, fake-responses-<k>.jsonl, the script split at each process's user_text match (fake_groups; stage 8,
    glitch-f1's B27 ruling 4), refused unless the split gives exactly the scenario's processes, in order, each group
    non-empty.

    python3 -B evals/gap-study-4/box/stub_model_probe.py --box <box folder> --scratch-parent <owned folder>
        --output <.../stub-probe-<id>> --gemini-image sha256:<64> --scenarios A1[,A2,...|all] [--reason <why>]
        [--dry-run]
It exits 1 when any scenario fails its own checks (scenario_problems: a failure, a stop, a non-zero process, an
unretained snapshot, anything left after teardown, a failed restore), so walk.exit 0 means every scenario ran as
scripted (REVIEW-vendor-b27-25ffff5 MINOR 3); summary.json and each probe.json keep the detail.
With --dry-run it prints every container argv it would run (ownership, network, take, stub, version, each process)
as JSON lines and runs nothing; it is the one mode that runs off Linux.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from box import ownership, preflight, run_take, take_config  # noqa: E402
from box import stub_model_server  # noqa: E402
import gemini_adapter  # noqa: E402
import mode_binding  # noqa: E402
import native_snapshot  # noqa: E402

RECORD_KIND = "stub-model-probe"
NOT_A_STUDY_RECORD = ("a scripted stub-model observation of the pinned Gemini CLI's own recorder (lane vendor-b27); "
                      "never a study take, walk, rehearsal, cell or registered attempt")
FOLDER_PREFIX = "stub-probe-"
STUDY_RECORD_DIRS = mode_binding.RECORD_ROOTS
HARNESS = run_take.GEMINI
MODE = "yolo"
IMAGE_ID = re.compile(r"sha256:[0-9a-f]{64}")
GEMINI_LOCK = ("gemini", "image.lock")
SCENARIO_DIR = Path(__file__).resolve().parent / "stub_model_scenarios"
SCENARIOS = ("A1", "A2", "A3", "B1", "B2", "C1", "C2")
FAKE = "A1-fake"                       # glitch-f1's ruling 4: A1 again through the CLI's FakeContentGenerator
FAKE_OF = "A1"
FAKE_FLAG = "--fake-responses"
FAKE_FILE = "fake-responses-{k}.jsonl"  # stage 8 (glitch-f1's B27 ruling 4): one fake file per CLI process
ALL = SCENARIOS + (FAKE,)
# The three environment changes (glitch-f1's ruling 1), and nothing else.
BASE_URL_NAME = "GOOGLE_GEMINI_BASE_URL"
KEY_NAME = run_take.LOGIN_VARIABLE[run_take.GEMINI]          # GEMINI_API_KEY
PROXY_NAME = "HTTPS_PROXY"
DUMMY_KEY = "dummydummydummydummydummydummy"                 # a fixed dummy string, recorded as such; never a key
STUB_HOST = stub_model_server.HOST
STUB_DIR = ".stub-probe"
STUB_OUT = f"{STUB_DIR}/out"
STUB_FILE = "stub_model_server.py"
RUN_TREE_TOKEN = "${RUN_TREE}"
PROCESS_TIMEOUT_S = 600
STUB_START_TIMEOUT_S = 60
DRY_ROOT = "/scratch/sp-dryrun"
DRY_SESSION = "dry-run-session-0000"


class ProbeRefused(ValueError):
    """The probe refuses before any runtime call: an image id off its lock, an output folder off its rule, a scenario
    not named, an environment that is not the three changes. The message names the rule."""


def labelled(doc: dict) -> dict:
    """The record with its label; a record carrying a label of its own is refused, never relabelled."""
    if set(doc) & {"record_kind", "not_a_study_record"}:
        raise ProbeRefused("the record carries a label of its own")
    return {"record_kind": RECORD_KIND, "not_a_study_record": NOT_A_STUDY_RECORD, **doc}


# ----------------------------------------------------------------------------------------------- checks
def check_output(path: str) -> str:
    """One new folder named stub-probe-*, absolute and normalised, outside the study's record folders."""
    if not isinstance(path, str) or not os.path.isabs(path) or os.path.normpath(path) != path:
        raise ProbeRefused("the output is a normalised absolute path")
    if not os.path.basename(path).startswith(FOLDER_PREFIX):
        raise ProbeRefused(f"the output folder is named {FOLDER_PREFIX}*, so no reader takes it for a take or a walk")
    if set(path.split(os.sep)) & set(STUDY_RECORD_DIRS):
        raise ProbeRefused(f"the output never sits under a study record folder ({', '.join(STUDY_RECORD_DIRS)})")
    if os.path.lexists(path):
        raise ProbeRefused("the output already exists: a record is never written over")
    return path


def check_image(box: str, image: str) -> dict:
    """The gemini image named by its full id, equal to the committed take-g lock's (preflight's own loader)."""
    if not isinstance(image, str) or not IMAGE_ID.fullmatch(image):
        raise ProbeRefused("the gemini image must be a full image id, sha256:<64 hex>, never a tag or a short id")
    lock = preflight.load_take_lock(os.path.join(run_take._abs_path(box, "box"), *GEMINI_LOCK), harness=HARNESS)
    if lock["image_id"] != image:
        raise ProbeRefused("the gemini image given is not its committed lock's image id")
    return lock


def scenario_names(spec: str) -> list:
    names = list(ALL) if spec == "all" else [s for s in (spec or "").split(",") if s]
    if not names or any(n not in ALL for n in names) or len(set(names)) != len(names):
        raise ProbeRefused(f"scenarios are a comma list of distinct names from {list(ALL)}, or all")
    return names


def load_scenario(name: str) -> dict:
    """The committed scenario file (A1-fake reads A1's), checked by the stub's own rule."""
    src = FAKE_OF if name == FAKE else name
    with open(SCENARIO_DIR / f"{src}.json", encoding="utf-8") as fh:
        doc = json.load(fh)
    stub_model_server.check_script(doc)
    if doc["scenario"] != src:
        raise ProbeRefused(f"{src}.json names scenario {doc['scenario']!r}")
    return doc


def check_fake_groups(processes: list, groups: list, n: int) -> list:
    """The split's own rule: one group per process, each non-empty, together every record 0..n-1 once, in order."""
    if len(groups) != len(processes):
        raise ProbeRefused(f"the fake split gives {len(groups)} groups for {len(processes)} processes")
    for k, g in enumerate(groups, 1):
        if not g:
            raise ProbeRefused(f"the fake split leaves process {k}'s group empty")
    if [i for g in groups for i in g] != list(range(n)):
        raise ProbeRefused("the fake split does not cover every record exactly once, in order")
    return groups


def fake_groups(doc: dict) -> list:
    """The script's request indices per CLI process (glitch-f1's B27 ruling 4): a boundary is an entry matching
    `user_text`; the boundaries' texts must be exactly the scenario's process prompts, in order, the first entry a
    boundary; each group runs from its boundary to the next. Any other split refuses, by name."""
    reqs, procs = doc["requests"], list(doc["processes"])
    bounds = [i for i, e in enumerate(reqs) if e["match"]["kind"] == "user_text"]
    texts = [reqs[i]["match"]["text"] for i in bounds]
    if texts != procs:
        if sorted(texts) == sorted(procs):
            why = "a process prompt is out of order"
        elif len(texts) < len(procs):
            why = "a missing boundary"
        elif len(texts) > len(procs):
            why = "an extra boundary"
        else:
            why = "the boundaries are not the scenario's prompts"
        raise ProbeRefused(f"the fake split refuses: {why} (user_text matches {texts}, processes {procs})")
    if not bounds or bounds[0] != 0:
        raise ProbeRefused("the fake split refuses: a record before process 1's prompt belongs to no process")
    groups = [list(range(b, (bounds + [len(reqs)])[j + 1])) for j, b in enumerate(bounds)]
    return check_fake_groups(procs, groups, len(reqs))


def check_fake(names: list) -> None:
    """Refuse a bad fake split before any runtime call (the dry run and the run both call it)."""
    if FAKE in names:
        fake_groups(load_scenario(FAKE))


def materialise(doc: dict, run_tree: str) -> dict:
    """The script with ${RUN_TREE} filled by the run tree's absolute path (the file the stub reads and the probe keeps)."""
    return json.loads(json.dumps(doc).replace(RUN_TREE_TOKEN, run_tree))


def synthetic_file(name: str, spec: dict) -> str:
    """`lines` lines of exactly `width` characters plus a newline, each naming its file and number (distinct)."""
    lines, width = spec["lines"], spec["width"]
    out = []
    for i in range(lines):
        head = f"{name} line {i:04d} "
        out.append((head + "abcdefghijklmnopqrstuvwxyz" * 3)[:width] + "\n")
    return "".join(out)


# ------------------------------------------------------------------------------------------- environment
def probe_environment(run_tree: str, port: int) -> dict:
    """The CLI process's whole environment: the arm G row (run_take.take_environment) with exactly the three changes."""
    row = run_take.take_environment(HARNESS, run_tree)
    env = {k: v for k, v in row.items() if k != PROXY_NAME}
    env[KEY_NAME] = DUMMY_KEY
    env[BASE_URL_NAME] = f"http://{STUB_HOST}:{int(port)}"
    environment_changes(env, run_tree)
    return env


def environment_changes(env: dict, run_tree: str) -> dict:
    """The difference from the arm G row; refuses unless it is exactly the three changes of ruling 1."""
    row = run_take.take_environment(HARNESS, run_tree)
    added = sorted(set(env) - set(row))
    removed = sorted(set(row) - set(env))
    replaced = sorted(k for k in set(env) & set(row) if env[k] != row[k])
    got = {"added": added, "removed": removed, "replaced": replaced}
    want = {"added": [BASE_URL_NAME], "removed": [PROXY_NAME], "replaced": [KEY_NAME]}
    if got != want:
        raise ProbeRefused(f"the probe's environment differs from the arm G row by {got}, not exactly {want}")
    if env[KEY_NAME] != DUMMY_KEY:
        raise ProbeRefused("the probe's key is the fixed dummy string, never another value")
    url = env[BASE_URL_NAME]
    if not re.fullmatch(rf"http://{re.escape(STUB_HOST)}:[1-9][0-9]{{0,4}}", url):
        raise ProbeRefused("the base URL is the stub on 127.0.0.1 inside the container, never another host")
    return got


def process_argv(take_id: str, inner, *, run_tree: str, port: int, caller_env=None) -> tuple:
    """One CLI process's `docker exec`, exec_argv's form, and the client environment (the dummy key by name only)."""
    run_take._check_id(take_id, "container id")
    env = probe_environment(run_tree, port)
    values = {k: v for k, v in env.items() if k != KEY_NAME}
    argv = [run_take.RUNTIME_CLIENT, "exec", "--user", run_take.AGENT_USER, "--workdir", run_tree, "-e", KEY_NAME,
            take_id, *run_take.launcher_argv(KEY_NAME, values, list(inner), harness=HARNESS)]
    client = run_take.runtime_env(caller_env)
    client[KEY_NAME] = DUMMY_KEY
    return argv, client


def cli_inner(doc: dict, k: int, session_id, *, fake_file=None) -> list:
    """Process k's argv inside the box: gemini_adapter.argv (checked by run_take.check_model), then, for the fake
    cross-check only, the hidden --fake-responses flag."""
    inner = gemini_adapter.argv(doc["processes"][k - 1], model=doc["model"], mode=MODE, session_id=session_id,
                                first=k == 1)
    run_take.check_model(HARNESS, inner)
    return inner + [FAKE_FLAG, fake_file] if fake_file else inner


def stub_start_argv(take_id: str, run_tree: str) -> list:
    """The stub started as the agent (a plain exec, no variable), daemonised once it listens on 127.0.0.1."""
    return run_take.agent_exec_argv(take_id, ["/usr/bin/python3", "-I", "-S", f"{run_tree}/{STUB_DIR}/{STUB_FILE}",
                                              "--scenario", f"{run_tree}/{STUB_DIR}/scenario.json",
                                              "--dir", f"{run_tree}/{STUB_OUT}", "--daemon"], workdir=run_tree)


def network_argv() -> list:
    return [run_take.RUNTIME_CLIENT, "network", "create", "--internal", run_take.network_name()]


def take_spec(image: str, run_tree: str, config_dir: str, network: str, resources: dict) -> run_take.TakeSpec:
    return run_take.TakeSpec(image=image, run_tree=run_tree, config_dir=config_dir, network=network,
                             memory_reservation=resources["memory_reservation"], memory=resources["memory"],
                             cpus=resources["cpus"], pids_limit=resources["pids_limit"])


def take_resources() -> dict:
    """The walks' take resources (walk_builders.TAKE_RESOURCES), never a probe-chosen value."""
    import walk_builders
    return dict(walk_builders.TAKE_RESOURCES)


# ---------------------------------------------------------------------------------------------- dry run
def dry_run(names: list, image: str, resources: dict) -> list:
    """Every argv a real run would send, in order, for each scenario, with placeholder paths and ids; runs nothing."""
    out = []
    check_fake(names)
    for name in names:
        doc = load_scenario(name)
        run_tree, cfg, evidence = f"{DRY_ROOT}/t", f"{DRY_ROOT}/cfg-dryrun", f"{DRY_ROOT}/e"
        take_id = net_id = "0" * 64
        steps = [("grant-run_tree", ownership.own_argv(image, run_tree, ownership.AGENT_UID, strict=True)),
                 ("grant-config_dir", ownership.own_argv(image, cfg, ownership.AGENT_UID, strict=True)),
                 ("grant-evidence_dir", ownership.own_argv(image, evidence, ownership.WATCHER_UID, strict=True)),
                 ("network-create", network_argv()),
                 ("take-create", run_take.create_argv(take_spec(image, run_tree, cfg, net_id, resources))),
                 ("take-inspect", [run_take.RUNTIME_CLIENT, "container", "inspect", take_id]),
                 ("take-start", [run_take.RUNTIME_CLIENT, "start", take_id]),
                 ("stub-start", stub_start_argv(take_id, run_tree))]
        port = 40000
        version, _ = process_argv(take_id, ["gemini", "--version"], run_tree=run_tree, port=port, caller_env={})
        steps.append(("cli-version", version))
        for k in range(1, len(doc["processes"]) + 1):
            fake = f"{run_tree}/{STUB_DIR}/{FAKE_FILE.format(k=k)}" if name == FAKE else None
            argv, client = process_argv(take_id, cli_inner(doc, k, None if k == 1 else DRY_SESSION, fake_file=fake),
                                        run_tree=run_tree, port=port, caller_env={})
            steps.append((f"process-{k}", argv))
        steps += [("take-rm", [run_take.RUNTIME_CLIENT, "rm", "--force", take_id]),
                  ("network-rm", [run_take.RUNTIME_CLIENT, "network", "rm", net_id])]
        for step, argv in steps:
            out.append({"scenario": name, "step": step, "argv": argv})
        out.append({"scenario": name, "step": "client-environment", "names": sorted(client),
                    "process_environment": probe_environment(run_tree, port),
                    "changes": environment_changes(probe_environment(run_tree, port), run_tree)})
    return out


# ------------------------------------------------------------------------------------------- the athena side
class Recorder:
    """run_take.DockerRuntime, every call recorded (argv, exit, output; the client env's names only)."""

    def __init__(self, inner=None):
        self.inner = inner or run_take.DockerRuntime()
        self.calls = []

    def run(self, argv, *, env=None, timeout=None):
        at = time.time()
        try:
            c = self.inner.run(argv, env=env, timeout=timeout)
        except TimeoutError:
            self.calls.append({"argv": list(argv), "env_names": sorted(env or {}), "at": at, "timed_out": True})
            raise
        self.calls.append({"argv": list(argv), "env_names": sorted(env or {}), "at": at, "returncode": c.returncode,
                           "stdout": c.stdout if len(c.stdout) < 20000 else f"<{len(c.stdout)} chars, kept as a file>",
                           "stderr": c.stderr[-4000:]})
        return c


def client_env() -> dict:
    """The rootless Docker client's environment on athena (as the CP2 stub take's road builds it)."""
    uid = os.getuid()
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/nonexistent",
            "DOCKER_HOST": f"unix:///run/user/{uid}/docker.sock", "XDG_RUNTIME_DIR": f"/run/user/{uid}"}


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_new(path: str, data: bytes, mode: int = 0o644) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)


def session_id_of(stdout: str):
    """The init event's session id from process 1's stream-json (gemini_adapter.read_stream's own reading)."""
    for line in stdout.split("\n"):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "init" and isinstance(rec.get("session_id"), str):
            return rec["session_id"]
    return None


def build_run_tree(run_tree: str, doc: dict, *, fake_records=None) -> None:
    """The run tree: the arm's .tmp and .home folders, the scenario's synthetic files, and the stub's read-only copy,
    its materialised script and (A1-fake only) one fake-responses file per process (fake_records: a list of lists)."""
    os.mkdir(run_tree, 0o755)
    for d in (run_take.RUN_TREE_TMPDIR, run_take.RUN_TREE_HOMEDIR):
        os.mkdir(os.path.join(run_tree, d), 0o700)
    for name, spec in sorted(doc["files"].items()):
        if "/" in name or name.startswith("."):
            raise ProbeRefused(f"a synthetic file is one plain name, not {name!r}")
        _write_new(os.path.join(run_tree, name), synthetic_file(name, spec).encode("ascii"))
    stub_dir = os.path.join(run_tree, STUB_DIR)
    os.mkdir(stub_dir, 0o755)
    os.mkdir(os.path.join(run_tree, STUB_OUT), 0o755)
    shutil.copyfile(stub_model_server.__file__, os.path.join(stub_dir, STUB_FILE))
    _write_new(os.path.join(stub_dir, "scenario.json"),
               (json.dumps(materialise(doc, run_tree), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    for k, group in enumerate(fake_records or [], 1):
        _write_new(os.path.join(stub_dir, FAKE_FILE.format(k=k)),
                   "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in group).encode("utf-8"))
    for f in os.listdir(stub_dir):
        p = os.path.join(stub_dir, f)
        if os.path.isfile(p):
            os.chmod(p, 0o444)


def run_scenario(runtime, env: dict, name: str, *, image: str, scratch_parent: str, out_root: str,
                 resources: dict) -> dict:
    """One scenario on the box: config, run tree, grant, network, take, stub, the CLI processes with each snapshot
    retained before the next exec, then teardown, restore and the records copied into <out_root>/<name>."""
    doc = load_scenario(name)
    fake = name == FAKE
    # REVIEW-vendor-b27-49c350a NIT 1 (folded in vendor-b28): the fake split is taken before anything is made, so a
    # refused split leaves neither <out_root>/<name> nor an sp-* scratch folder behind
    groups = fake_groups(load_scenario(FAKE_OF)) if fake else None
    out = os.path.join(out_root, name)
    os.mkdir(out, 0o755)
    base = tempfile.mkdtemp(prefix="sp-", dir=scratch_parent)
    run_tree, evidence = os.path.join(base, "t"), os.path.join(base, "e")
    os.mkdir(evidence, 0o755)
    cfg = run_take.make_config_dir(base)
    rec = {"scenario": name, "road": doc["road"], "expect": doc["expect"], "started_at": time.time(), "image": image,
           "departures": list(DEPARTURES), "dummy_key": {"name": KEY_NAME, "value": DUMMY_KEY,
                                                         "note": "a fixed dummy string, never a credential"},
           "scratch": {"base": base, "run_tree": run_tree, "config": cfg}, "processes": [],
           "processes_scripted": list(doc["processes"])}
    rec["config"] = take_config.write(cfg, HARNESS, model=doc["model"])
    fake_records = None
    if fake:
        script = materialise(load_scenario(FAKE_OF), run_tree)
        records = stub_model_server.fake_records(script)
        fake_records = [[records[i] for i in g] for g in groups]
    build_run_tree(run_tree, doc, fake_records=fake_records)
    launched = run_take.Launched(config_dir=cfg)
    restored = False
    try:
        rec["grant"] = ownership.grant(runtime, image=image, run_tree=run_tree, config_dir=cfg, evidence_dir=evidence,
                                       caller_env=env)
        c = run_take._step(runtime, launched, "network-create", network_argv(), env)
        launched.network_id = run_take._new_id(c, "network-create")
        launched.spec = spec = take_spec(image, run_tree, cfg, launched.network_id, resources)
        c = run_take._step(runtime, launched, "take-create", run_take.create_argv(spec), env)
        launched.take_id = run_take._new_id(c, "take-create")
        run_take._inspect(runtime, launched, "take-inspect", launched.take_id, env)
        run_take._step(runtime, launched, "take-start", [run_take.RUNTIME_CLIENT, "start", launched.take_id], env)
        launched.ok = True
        c = runtime.run(stub_start_argv(launched.take_id, run_tree), env=env, timeout=STUB_START_TIMEOUT_S)
        ready = json.loads(c.stdout.strip().splitlines()[-1]) if c.returncode == 0 and c.stdout.strip() else {}
        if ready.get("ready") is not True or type(ready.get("port")) is not int:
            raise ProbeRefused(f"the stub did not start (exit {c.returncode})")
        port = ready["port"]
        rec["stub"] = {"port": port, "pid": ready.get("pid"), "base_url": f"http://{STUB_HOST}:{port}"}
        rec["environment"] = {"process": probe_environment(run_tree, port),
                              "changes": environment_changes(probe_environment(run_tree, port), run_tree)}
        argv, cenv = process_argv(launched.take_id, ["gemini", "--version"], run_tree=run_tree, port=port,
                                  caller_env=env)
        v = runtime.run(argv, env=cenv, timeout=120)
        rec["cli_version"] = {"returncode": v.returncode, "stdout": v.stdout, "stderr": v.stderr[-2000:]}

        def lister(rel_dir):
            return ownership.operator_list(runtime, image=image, root_kind="config", run_tree=run_tree,
                                           config_dir=cfg, rel_dir=rel_dir, caller_env=env)
        session_id = None
        for k in range(1, len(doc["processes"]) + 1):
            fake_file = f"{run_tree}/{STUB_DIR}/{FAKE_FILE.format(k=k)}" if fake else None
            inner = cli_inner(doc, k, session_id, fake_file=fake_file)
            argv, cenv = process_argv(launched.take_id, inner, run_tree=run_tree, port=port, caller_env=env)
            started = time.time()
            try:
                p = runtime.run(argv, env=cenv, timeout=PROCESS_TIMEOUT_S)
                code, stdout, stderr, timed_out = p.returncode, p.stdout, p.stderr, False
            except TimeoutError as e:
                code, stdout, stderr, timed_out = None, getattr(e, "stdout", "") or "", "", True
            _write_new(os.path.join(out, f"turn-{k}.jsonl"), stdout.encode("utf-8", "surrogateescape"))
            _write_new(os.path.join(out, f"turn-{k}.stderr.txt"), stderr.encode("utf-8", "surrogateescape"))
            prow = {"process": k, "inner": inner, "returncode": code, "timed_out": timed_out, "started_at": started,
                    "ended_at": time.time()}
            if k == 1:
                session_id = session_id_of(stdout)
                prow["session_id"] = session_id
            if session_id is not None:
                try:
                    rel = native_snapshot.gemini_session_rel(lister, session_id)
                    raw = ownership.operator_read(runtime, image=image, root_kind="config", run_tree=run_tree,
                                                  config_dir=cfg, rel_path=rel, caller_env=env)
                    prow["snapshot"] = dict(native_snapshot.retain_bytes(out, k, raw), source=rel)
                except (native_snapshot.SnapshotRefused, ownership.OwnershipError) as e:
                    prow["snapshot"] = {"refused": str(e)[:500]}
            state = ownership.operator_read(runtime, image=image, root_kind="run_tree", run_tree=run_tree,
                                            config_dir=cfg, rel_path=f"{STUB_OUT}/state.json", caller_env=env)
            prow["stub_state"] = json.loads(state) if state else None
            rec["processes"].append(prow)
            if code != 0 or session_id is None or (prow["stub_state"] or {}).get("held") \
                    or "refused" in prow.get("snapshot", {}):
                rec["stopped_after"] = {"process": k, "why": "a non-zero exit, no session id, a held stub or an "
                                                             "unretained snapshot: the later processes are not run"}
                break
    except Exception as e:  # recorded; the teardown below still runs on whatever was made
        rec["failure"] = {"type": type(e).__name__, "detail": str(e)[:2000]}
    finally:
        run_take._teardown_partial(runtime, launched, None, base, env)
        rec["launch"] = launched.to_record()
        ids = launched.ids()
        # REVIEW-vendor-b27-25ffff5 MINOR 1: each check in its own try, so a failed listing (leaked() raises Refused on
        # a non-zero `docker ps`; a listing can time out) is recorded and the restore and the records still follow
        try:
            rec["leaked_after_teardown"] = run_take.leaked(runtime, ids, caller_env=env) if ids else []
        except Exception as e:  # noqa: BLE001 - recorded, never stops the restore
            rec["leaked_after_teardown"] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
        if launched.network_id:
            try:
                nets = runtime.run([run_take.RUNTIME_CLIENT, "network", "ls", "--no-trunc", "-q", "--filter",
                                    f"id={launched.network_id}"], env=env, timeout=60)
                rec["network_left"] = nets.stdout.strip() if nets.returncode == 0 else \
                    {"error": f"network ls exited {nets.returncode}"}
            except Exception as e:  # noqa: BLE001 - recorded, never stops the restore
                rec["network_left"] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
        try:
            rec["restore"] = ownership.restore(runtime, image=image, run_tree=run_tree, config_dir=cfg,
                                               evidence_dir=evidence, ids=ids, caller_env=env)
            restored = True
        except ownership.OwnershipError as e:
            rec["restore"] = {"error": str(e), **e.record}
        except Exception as e:  # noqa: BLE001 - recorded; the scratch is kept for a human below
            rec["restore"] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
    if restored:
        shutil.copytree(os.path.join(run_tree, STUB_OUT), os.path.join(out, "stub"))
        shutil.copyfile(os.path.join(run_tree, STUB_DIR, "scenario.json"), os.path.join(out, "scenario.json"))
        for k in range(1, len(fake_records or []) + 1):
            shutil.copyfile(os.path.join(run_tree, STUB_DIR, FAKE_FILE.format(k=k)),
                            os.path.join(out, FAKE_FILE.format(k=k)))
        shutil.rmtree(base)
        rec["scratch_removed"] = not os.path.lexists(base)
    else:
        rec["scratch_removed"] = False
        rec["scratch_kept_why"] = "the ownership restore failed: the scratch is kept for a human"
    ledger = {"turns": [{"turn": p["process"], "sent": doc["processes"][p["process"] - 1]} for p in rec["processes"]]}
    _write_new(os.path.join(out, "ledger.json"), (json.dumps(labelled(ledger), indent=1, sort_keys=True) + "\n")
               .encode("utf-8"))
    rec["ended_at"] = time.time()
    rec["problems"] = scenario_problems(rec)
    _write_new(os.path.join(out, "probe.json"), (json.dumps(labelled(rec), indent=1, sort_keys=True, default=str)
                                                 + "\n").encode("utf-8"))
    return rec


DEPARTURES = (
    "exactly three environment changes from the arm G row: GOOGLE_GEMINI_BASE_URL is the stub on 127.0.0.1, "
    "GEMINI_API_KEY is a fixed dummy string, HTTPS_PROXY is absent (glitch-f1's ruling 1)",
    "no proxy and no sidecar: the take container alone on a fresh --internal network; so run_take.launch and "
    "run_take.teardown are not used, and run_take._teardown_partial removes the take container and the network by id",
    "the exec argv is exec_argv's form built here (exec_argv reads a login file and refuses the base URL)",
    # glitch-f1's ruling 3 and REVIEW-vendor-b27-25ffff5 MINOR 6: every difference from a walk's workspace, by name
    "the workspace differs from a walk's in content only: it holds .stub-probe/ (the stub's read-only copy, its "
    "materialised script, its log and state) and the scenario's synthetic files; the run tree is not a git checkout "
    "(a walk's is the pinned checkout); and there is no GEMINI.md (a walk places the instruction file beside every "
    "CLAUDE.md, walk_builders.place_instruction_file)",
)


def scenario_problems(rec: dict) -> list:
    """What keeps a scenario from having run as scripted (REVIEW-vendor-b27-25ffff5 MINOR 3): a failure, a stop, a
    process with a non-zero exit or an unretained snapshot, fewer processes than the script names, anything left after
    teardown, a failed restore or a kept scratch. Empty means it ran as scripted; the reading judges the records."""
    out = []
    if rec.get("failure"):
        out.append(f"failure: {rec['failure'].get('type')}")
    if rec.get("stopped_after"):
        out.append(f"stopped after process {rec['stopped_after'].get('process')}")
    want = len(rec.get("processes_scripted") or [])
    if want and len(rec.get("processes") or []) != want:
        out.append(f"{len(rec.get('processes') or [])} of {want} processes ran")
    for p in rec.get("processes") or []:
        if p.get("returncode") != 0:
            out.append(f"process {p.get('process')} exited {p.get('returncode')}")
        if "file" not in (p.get("snapshot") or {}):
            out.append(f"process {p.get('process')}: no snapshot retained")
        if (p.get("stub_state") or {}).get("held"):
            out.append(f"process {p.get('process')}: the stub is held")
    if rec.get("leaked_after_teardown") not in ([], None):
        out.append(f"after teardown: {rec['leaked_after_teardown']}")
    if rec.get("network_left") not in ("", None):
        out.append(f"network left: {rec['network_left']}")
    if not isinstance(rec.get("restore"), dict) or rec["restore"].get("error") or not rec["restore"].get("ok", False):
        out.append("the ownership restore failed or did not run")
    if not rec.get("scratch_removed"):
        out.append("the scratch is kept")
    return out


def manifest(out_root: str) -> dict:
    files = {}
    for b, dirs, fs in os.walk(out_root):
        dirs.sort()
        for f in sorted(fs):
            p = os.path.join(b, f)
            files[os.path.relpath(p, out_root)] = {"sha256": _sha256_file(p), "bytes": os.path.getsize(p)}
    return labelled({"files": files})


def run_probe(a, names: list, *, runtime=None, env=None) -> dict:
    if sys.platform != "linux":
        raise ProbeRefused("the probe runs on athena's Linux box only (use --dry-run elsewhere)")
    parent = run_take._abs_path(a.scratch_parent, "scratch_parent")
    if os.path.islink(parent) or not os.path.isdir(parent) or os.stat(parent).st_uid != os.getuid() \
            or not run_take.outside_every_repository(parent):
        raise ProbeRefused("the scratch parent is an owned folder outside every repository")
    if run_take._inside(a.output, parent):
        raise ProbeRefused("the output never sits in the scratch it removes")
    os.mkdir(a.output, 0o755)
    env = client_env() if env is None else env
    runtime = Recorder() if runtime is None else runtime
    resources = take_resources()
    summary = {"scenarios": {}, "resources": resources, "image": a.gemini_image, "reason": getattr(a, "reason", "")}
    for name in names:
        rec = run_scenario(runtime, env, name, image=a.gemini_image, scratch_parent=parent, out_root=a.output,
                           resources=resources)
        summary["scenarios"][name] = {"failure": rec.get("failure"), "stopped_after": rec.get("stopped_after"),
                                      "problems": rec.get("problems"),
                                      "processes": [{"process": p["process"], "returncode": p["returncode"],
                                                     "snapshot": p.get("snapshot"), "stub": p.get("stub_state")}
                                                    for p in rec["processes"]]}
    calls = getattr(runtime, "calls", None)
    if calls is not None:
        _write_new(os.path.join(a.output, "calls.json"), (json.dumps(labelled({"calls": calls}), indent=1,
                                                                     default=str) + "\n").encode("utf-8"))
    _write_new(os.path.join(a.output, "summary.json"), (json.dumps(labelled(summary), indent=1, sort_keys=True,
                                                                   default=str) + "\n").encode("utf-8"))
    _write_new(os.path.join(a.output, "manifest.json"), (json.dumps(manifest(a.output), indent=1, sort_keys=True)
                                                         + "\n").encode("utf-8"))
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--box", required=True)
    p.add_argument("--scratch-parent", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--gemini-image", required=True)
    p.add_argument("--scenarios", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reason", default="")
    a = p.parse_args(argv)
    names = scenario_names(a.scenarios)
    check_image(a.box, a.gemini_image)
    check_fake(names)
    if a.dry_run:
        for row in dry_run(names, a.gemini_image, take_resources()):
            print(json.dumps(row, sort_keys=True))
        return 0
    check_output(a.output)
    summary = run_probe(a, names)
    problems = {n: s.get("problems") for n, s in summary["scenarios"].items() if s.get("problems")}
    print(json.dumps({"record_kind": RECORD_KIND, "output": a.output, "problems": problems,
                      "failures": {n: s["failure"] for n, s in summary["scenarios"].items() if s["failure"]}},
                     sort_keys=True))
    # REVIEW-vendor-b27-25ffff5 MINOR 3: exit 0 (walk.exit, `status` exit=0) only when every scenario ran as
    # scripted; summary.json and each probe.json keep the detail
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
