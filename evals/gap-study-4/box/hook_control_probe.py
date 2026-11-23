#!/usr/bin/env python3
"""Lane hook-control (glitch-f1's rulings on lane-reports/hook-control-DESIGN.md, Wed 21 Oct 2026): D8's hook positive
control for arms O (Codex) and G (Gemini). A MEASUREMENT on athena's walk box, on B27's stub-model road: a hook planted
in the harness's own user configuration must run when the study's switch is on, and must not run when only the switch
differs (Codex: features.hooks in config.toml; Gemini: hooksConfig.enabled in settings.json).

NOT A STUDY TAKE. It never touches a counted walk, a record, the register, a module constant or a lock: every record
carries B27's RECORD_KIND (so walk_launch's fetch-probe reads its manifest) with this lane's own not-a-study-record
text, its output is one new stub-probe-* folder outside the study's record folders, and no production module imports
it (tests/test_hook_control_probe.py binds that by ast). run_take.exec_argv, _codex_exec_argv, run_turn, read_login and
place_lease are never called (bound by ast): there is no login and no lease, ever.

THE RUNS (RUNS below; each its own config folder, run tree, network, container, teardown and restore):
  HG     Gemini on B27's stub road (B27's three environment changes, stub_model_probe.process_argv): G-on (the study's
         settings plus `hooks`, the switch true) and G-off (the study's settings byte for byte plus `hooks`); two
         processes, the second a resume.
  HO-C0  Codex with no model and no login on the internal network; HO-C1 the same plus a dead local provider in
         config.toml (C1_PROVIDER, the same in all four runs). Four runs per road: O-on-bypass (switch true, the study
         argv plus --dangerously-bypass-hook-trust), O-off-bypass (study bytes, the same flag), O-off-study (study bytes,
         the walk's argv exactly) and O-on-study (switch true, the walk's argv exactly; informational). The resume runs
         only when process 1's stream names a thread id.
  Before any CLI process, the probe runs the exact marker command once as the agent through /bin/bash -c with the event
  name `selftest`; the pre-run check (marker_precheck) then requires fired.log to read exactly that one line, or no
  CLI process of that run is started (a broken marker can never read as a silent off twin).

THE VERDICT (hook_verdict, glitch-f1's ruling): PASS only when every on twin (G-on; O-on-bypass on every road run)
logged SessionStart in process 1 after a good self-test and every off twin (G-off; O-off-bypass and O-off-study on every
road run) logged nothing but the self-test's line after every process; INCONCLUSIVE when an on twin stayed silent, a
self-test or a log failed, or a run is missing (never a pass); FAIL when any off twin logged an event (that arm's
counted runs wait). The informational run never moves it. The probe exits 0 only on PASS with no run problem.

WHAT RUNS UNMODIFIED: run_take.create_argv (the locked take image by id, --pull=never, read-only root, the two bind
mounts), make_config_dir, _step, _new_id, _inspect, network_name, _teardown_partial, leaked, take_environment,
launcher_argv (NO_LOGIN for Codex, the walk's no-login launcher over exactly the Codex row), check_codex_turn,
agent_exec_argv; take_config.files_for (the study's bytes); codex_adapter.argv; stub_model_probe's environment, exec form,
cli_inner, stub start and run tree for Gemini; ownership.grant, operator_list, operator_read and restore.

DEPARTURES (each written into every probe.json): see DEPARTURES below.

    python3 -B evals/gap-study-4/box/hook_control_probe.py --box <box folder> --scratch-parent <owned folder>
        --output <.../stub-probe-<id>> [--gemini-image sha256:<64>] [--codex-image sha256:<64>]
        --scenarios HG[,HO-C0,HO-C1] [--reason <why>] [--dry-run]
Each image is required exactly when one of its scenarios is named, and must equal its committed lock's image id.
With --dry-run it prints every argv it would run, per run, as JSON lines and runs nothing; it is the one mode that runs
off Linux.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from box import ownership, preflight, run_take, take_config  # noqa: E402
from box import stub_model_probe as smp  # noqa: E402
from box import stub_model_server  # noqa: E402
import codex_adapter  # noqa: E402

RECORD_KIND = smp.RECORD_KIND          # walk_launch.probe_manifest_problems reads this kind
NOT_A_STUDY_RECORD = ("a hook positive-control observation of the pinned Codex and Gemini CLIs (lane hook-control); "
                      "never a study take, walk, rehearsal, cell or registered attempt")
GEMINI, CODEX = run_take.GEMINI, run_take.CODEX
ARM = {GEMINI: "G", CODEX: "O"}
IMAGE_ID = smp.IMAGE_ID
LOCKS = {GEMINI: ("gemini", "image.lock"), CODEX: ("codex", "image.lock")}

# The marker hook (the design's section 1): one command that appends its event name to <run tree>/.hookctl/fired.log,
# with the image's own python3, printing nothing (so it adds no hook context to a prompt).
HOOK_DIR = ".hookctl"
FIRED_REL = f"{HOOK_DIR}/fired.log"
SELFTEST = "selftest"
MARKER_PROGRAM = ("import os,sys;fd=os.open(sys.argv[1],os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o644);"
                  "os.write(fd,(sys.argv[2]+chr(10)).encode());os.close(fd)")
MARKER_PYTHON = "/usr/bin/python3"
SHELL = "/bin/bash"
_EVENT = re.compile(r"[A-Za-z][A-Za-z0-9]{0,39}")
_PATH = re.compile(r"/[A-Za-z0-9._@+/-]+")
# Gemini CLI 0.64.0's HookEventName, all eleven (bundle/chunk-NR7L3FXV.js:336623-336636), in the bundle's order.
GEMINI_EVENTS = ("BeforeTool", "AfterTool", "BeforeAgent", "Notification", "AfterAgent", "SessionStart", "SessionEnd",
                 "PreCompress", "BeforeModel", "AfterModel", "BeforeToolSelection")
# Codex: GARS's own Codex hooks file's two events, the only shape seen working (gars/.codex/hooks.json:1-28).
CODEX_EVENTS = ("SessionStart", "PreToolUse")
PASS_EVENT = "SessionStart"
# Recorded before any run, never a pass condition (the design's section 1, G-on).
PREDICTED_G_ON = ("SessionStart", "BeforeAgent", "BeforeModel", "AfterModel", "BeforeTool", "AfterTool", "AfterAgent",
                  "SessionEnd")

# The switches, as the study writes them (take_config.CODEX_FEATURES, GEMINI_SETTINGS).
GEMINI_SWITCH = "hooksConfig.enabled"
CODEX_SWITCH = "features.hooks"
CODEX_SWITCH_OFF, CODEX_SWITCH_ON = "hooks = false", "hooks = true"
CODEX_HOOKS_FILE = "hooks.json"        # CODEX_HOME/hooks.json, the user layer's hooks file (run_take.py:230-231)

# The Codex road (glitch-f1's ruling: C0 and C1 in one athena trip). C1's dead local provider: Codex's documented
# provider keys of earlier versions, NOT verified at 0.162.1 (the design's inference), on a closed port.
C1_PROVIDER = "local"
C1_BASE_URL = "http://127.0.0.1:9"
_C1_TOP = f'model_provider = "{C1_PROVIDER}"\n'
_C1_TABLE = (f"\n[model_providers.{C1_PROVIDER}]\n", f'name = "{C1_PROVIDER}"\n', f'base_url = "{C1_BASE_URL}"\n',
             'wire_api = "responses"\n', "requires_openai_auth = false\n")
ROADS = {"HG": None, "HO-C0": "C0", "HO-C1": "C1"}
SCENARIOS = tuple(ROADS)
SCENARIO_HARNESS = {"HG": GEMINI, "HO-C0": CODEX, "HO-C1": CODEX}

Run = collections.namedtuple("Run", "name harness twin bypass role")
RUNS = {
    "HG": (Run("G-on", GEMINI, "on", False, "on"), Run("G-off", GEMINI, "off", False, "off")),
    **{s: (Run("O-on-bypass", CODEX, "on", True, "on"), Run("O-off-bypass", CODEX, "off", True, "off"),
           Run("O-off-study", CODEX, "off", False, "off"), Run("O-on-study", CODEX, "on", False, "info"))
       for s in ("HO-C0", "HO-C1")},
}
TRUST_FLAG = "--dangerously-bypass-hook-trust"   # codex exec and exec resume help, 0.162.1 (codex-*-help.json)
CODEX_MODEL = run_take.CODEX_MODELS[0]
CODEX_MODE = "bypass"
CODEX_PROMPTS = ("List the files in this folder.", "Thanks.")
CODEX_PROCESS_TIMEOUT_S = 120     # a probe value (B27's PROCESS_TIMEOUT_S is 600): a departure
GEMINI_PROCESS_TIMEOUT_S = smp.PROCESS_TIMEOUT_S
_THREAD_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")

# The Gemini script, B27's stub rules (stub_model_server.check_script): process 1 reads one file then answers, so the
# tool events can fire in G-on; process 2 answers with text only.
HG_SCENARIO = {
    "schema": stub_model_server.SCHEMA, "scenario": "HG", "model": "gemini-3.8-flash",
    "road": "the hook control's Gemini pair: one read_file call then text, then a resume with text only",
    "processes": ["Read the file n01.txt.", "Thanks."],
    "files": {"n01.txt": {"kind": "small", "lines": 20, "width": 30}},
    "requests": [
        {"endpoint": "stream", "match": {"kind": "user_text", "text": "Read the file n01.txt."},
         "respond": {"calls": [{"name": "read_file", "args": {"file_path": smp.RUN_TREE_TOKEN + "/n01.txt"}}]}},
        {"endpoint": "stream", "match": {"kind": "function_response"},
         "respond": {"text": "n01.txt holds twenty numbered lines."}},
        {"endpoint": "stream", "match": {"kind": "user_text", "text": "Thanks."},
         "respond": {"text": "You are welcome."}},
    ],
}

GIT_IDENTITY = ("dana", "dana@localhost")     # the image's agent user name; never a study word
GIT_DATE = "2026-01-01T00:00:00+00:00"
DRY_ROOT = "/scratch/hc-dryrun"
DRY_THREAD = "00000000-0000-0000-0000-000000000000"

DEPARTURES = (
    "a measurement on B27's stub-model road, never a walk: each run has its own config folder, run tree, fresh "
    "--internal network and take container, with no proxy and no sidecar (so run_take.launch and teardown are not "
    "used; _teardown_partial removes the take and the network by id)",
    "the twin's files are written here with O_EXCL (hook_twins, refused by check_twins unless the off twin is the "
    "study's bytes plus the planted hook only and the on twin differs from it by the switch alone), not by "
    "take_config.write; the study files' set hash is recorded beside the twin's",
    "Gemini: B27's exactly three environment changes (the stub's base URL on 127.0.0.1, a fixed dummy key, no "
    "HTTPS_PROXY); the run tree is B27's (not a git checkout, no GEMINI.md) plus .hookctl/",
    "Codex: the Codex row exactly under the walk's no-login launcher (launcher_argv admits only the row's names, so "
    "HTTPS_PROXY stays, naming a proxy that does not exist on the internal network; the design said the row less "
    "HTTPS_PROXY), no login and no lease; the run tree is git init plus one empty commit (a walk's is the pinned "
    "checkout) plus .tmp, .home and .hookctl, and holds no AGENTS.md",
    "Codex: CODEX_HOME/hooks.json is planted; the walk road's per-turn config-folder audit (run_take.check_config_folder) "
    "would refuse it by name and is not run (the control isolates the switch); census_names records that refusal",
    "Codex: --dangerously-bypass-hook-trust is appended after run_take.check_codex_turn reads the study argv, on the two "
    "bypass runs only; the per-process cap is 120 s (B27: 600 s); a non-zero exit is expected on C0 and C1",
    "the diff rule is checked per run on the twin pair built at that run's own run tree, so the files actually run "
    "differ from run to run also in the paths that name the tree (the Codex trust table's key, every marker command's "
    "fired.log path); twin_sha256 therefore differs across runs, while study_sha256 is computed at the same path",
    "Codex C1: config.toml carries a dead local provider (model_provider and [model_providers.local], base_url "
    "http://127.0.0.1:9, requires_openai_auth = false) in all four runs; its key names are not verified at 0.162.1",
)


class HookRefused(ValueError):
    """The hook control refuses before any runtime call (or a twin, a marker or an environment off its rule)."""


def labelled(doc: dict) -> dict:
    if set(doc) & {"record_kind", "not_a_study_record"}:
        raise HookRefused("the record carries a label of its own")
    return {"record_kind": RECORD_KIND, "not_a_study_record": NOT_A_STUDY_RECORD, **doc}


# ------------------------------------------------------------------------------------------------ the marker
def marker_command(fired_path: str, event: str) -> str:
    """The planted command for one event: no `$`, no quote but the program's two, no backquote or backslash."""
    if not isinstance(event, str) or not _EVENT.fullmatch(event):
        raise HookRefused(f"an event name is letters and digits only, not {event!r}")
    if not isinstance(fired_path, str) or not _PATH.fullmatch(fired_path) or os.path.normpath(fired_path) != fired_path:
        raise HookRefused("the marker's log is a normalised absolute path of plain characters")
    return f'{MARKER_PYTHON} -I -S -c "{MARKER_PROGRAM}" {fired_path} {event}'


# Gemini CLI 0.64.0 matches a SessionStart or SessionEnd entry against its trigger by exact string equality
# (bundle/chunk-NR7L3FXV.js:365647-365648 and 365666-365668, read in the pinned copy whose sha256 is d566e81b...), so a
# regex matcher such as ".*" matches no trigger; an empty matcher matches every one (365637-365639: `!entry.matcher`).
# The per-turn events keep ".*", which the tool-name road reads as a regex (365655-365662). Codex keeps GARS's shape.
# PreCompress matches its trigger the same way (365807; the closure review of d07561f6): armed, never exercised,
# since the stub never compresses.
GEMINI_TRIGGER_EVENTS = ("SessionStart", "SessionEnd", "PreCompress")


def _entry(fired_path: str, event: str, matcher: str = ".*") -> list:
    return [{"matcher": matcher, "hooks": [{"type": "command", "command": marker_command(fired_path, event)}]}]


def hooks_doc(harness: str, fired_path: str) -> dict:
    """Gemini: settings.json's `hooks` value, all eleven events; Codex: hooks.json, SessionStart and PreToolUse."""
    if harness == GEMINI:
        return {ev: _entry(fired_path, ev, "" if ev in GEMINI_TRIGGER_EVENTS else ".*") for ev in GEMINI_EVENTS}
    if harness == CODEX:
        return {"hooks": {ev: _entry(fired_path, ev) for ev in CODEX_EVENTS}}
    raise HookRefused(f"no hook control for {harness!r}")


def marker_precheck(raw) -> list:
    """The fail-safe pre-run check: after the self-test, fired.log reads exactly `selftest` and a newline."""
    if raw is None:
        return ["the self-test left no fired.log"]
    if raw != (SELFTEST + "\n").encode("ascii"):
        return [f"fired.log after the self-test is not exactly one {SELFTEST!r} line ({len(raw)} bytes)"]
    return []


# ------------------------------------------------------------------------------------------------ the twins
def files_sha256(files: dict) -> str:
    """take_config.config_sha256's formula over {relative path: bytes} (bound to it by a test)."""
    h = hashlib.sha256()
    for rel, data in sorted((rel, hashlib.sha256(b).hexdigest()) for rel, b in files.items()):
        h.update(f"{rel}\0{data}\n".encode("utf-8"))
    return h.hexdigest()


def c1_lines_added() -> tuple:
    return (_C1_TOP,) + _C1_TABLE


def road_base(harness: str, study: dict, road) -> dict:
    """The road's base files: the study's own bytes (HG, C0), or for C1 the study's config.toml with the dead provider
    (one top-level line before the first table, one table at the end)."""
    if harness == GEMINI or road == "C0":
        return dict(study)
    if road != "C1":
        raise HookRefused(f"no Codex road {road!r}")
    text = study[take_config.CODEX_CONFIG].decode("ascii")
    first_table = text.index("\n[") + 1
    text = text[:first_table] + _C1_TOP + text[first_table:] + "".join(_C1_TABLE)
    return dict(study, **{take_config.CODEX_CONFIG: text.encode("ascii")})


def _flat(doc, prefix="") -> dict:
    out = {}
    if isinstance(doc, dict) and doc:
        for k, v in doc.items():
            out.update(_flat(v, f"{prefix}{k}."))
    else:
        out[prefix[:-1]] = json.dumps(doc, sort_keys=True)
    return out


def _section_of(lines: list, i: int):
    for j in range(i, -1, -1):
        if lines[j].startswith("["):
            return lines[j]
    return None


def check_twins(harness: str, study: dict, base: dict, off: dict, on: dict, *, hooks: dict, road=None) -> dict:
    """The diff rule (the design's section 1): the base is the road's derivation of the study's bytes; the off twin is
    the base plus the planted hook only, with the switch off as the study writes it; the on twin differs from the off
    twin in exactly one value, the switch. Returns the diff record; refuses by name."""
    if base != road_base(harness, study, road):
        raise HookRefused("the base is not the road's derivation of the study's bytes")
    if harness == GEMINI:
        rel = take_config.GEMINI_SETTINGS_PATH
        if set(base) != {rel} or set(off) != {rel} or set(on) != {rel}:
            raise HookRefused("a Gemini twin is the one settings file")
        b, o, n = (json.loads(x[rel]) for x in (base, off, on))
        if "hooks" in b or o.get("hooks") != hooks or n.get("hooks") != hooks:
            raise HookRefused("each Gemini twin carries exactly the planted hooks, the study none")
        if {k: v for k, v in o.items() if k != "hooks"} != b:
            raise HookRefused("the off twin is not the study's settings plus the hooks only")
        if off[rel] != take_config._json_bytes(o) or on[rel] != take_config._json_bytes(n):
            raise HookRefused("a twin's bytes are not the study's serialisation")
        fo, fn = _flat(o), _flat(n)
        changed = sorted(k for k in set(fo) | set(fn) if fo.get(k) != fn.get(k))
        if changed != [GEMINI_SWITCH] or fo[GEMINI_SWITCH] != "false" or fn[GEMINI_SWITCH] != "true":
            raise HookRefused(f"the on twin differs from the off twin by {changed}, not the switch alone")
        return {"switch": GEMINI_SWITCH, "off": False, "on": True, "planted": rel + " hooks"}
    if harness != CODEX:
        raise HookRefused(f"no hook control for {harness!r}")
    cfg = take_config.CODEX_CONFIG
    if set(base) != {cfg} or set(off) != {cfg, CODEX_HOOKS_FILE} or set(on) != {cfg, CODEX_HOOKS_FILE}:
        raise HookRefused("a Codex twin is config.toml plus hooks.json, the base config.toml alone")
    planted = (json.dumps(hooks, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")
    if off[CODEX_HOOKS_FILE] != planted or on[CODEX_HOOKS_FILE] != planted:
        raise HookRefused("each Codex twin's hooks.json is exactly the planted hooks")
    if off[cfg] != base[cfg]:
        raise HookRefused("the off twin's config.toml is not the base's bytes")
    lo, ln = off[cfg].decode("ascii").split("\n"), on[cfg].decode("ascii").split("\n")
    changed = [i for i in range(max(len(lo), len(ln))) if (lo[i:i + 1] or [None]) != (ln[i:i + 1] or [None])]
    if len(lo) != len(ln) or len(changed) != 1:
        raise HookRefused(f"the on twin's config.toml differs from the off twin's in {len(changed)} lines, not one")
    i = changed[0]
    if (lo[i], ln[i]) != (CODEX_SWITCH_OFF, CODEX_SWITCH_ON) or _section_of(lo, i) != "[features]":
        raise HookRefused("the one changed line is not [features] hooks = false -> true")
    return {"switch": CODEX_SWITCH, "off": False, "on": True, "planted": CODEX_HOOKS_FILE, "line": i + 1}


def hook_twins(harness: str, study: dict, *, fired_path: str, road=None) -> dict:
    """{base, off, on, hooks, diff}: both twins built from the study's bytes, then held to the diff rule."""
    hooks = hooks_doc(harness, fired_path)
    base = road_base(harness, study, road)
    if harness == GEMINI:
        rel = take_config.GEMINI_SETTINGS_PATH
        doc = json.loads(base[rel])
        if "hooks" in doc or doc.get("hooksConfig", {}).get("enabled") is not False:
            raise HookRefused("the study's Gemini settings carry no hooks and the switch false")
        off_doc = dict(doc, hooks=hooks)
        on_doc = json.loads(json.dumps(off_doc))
        on_doc["hooksConfig"]["enabled"] = True
        off = {rel: take_config._json_bytes(off_doc)}
        on = {rel: take_config._json_bytes(on_doc)}
    else:
        cfg = base[take_config.CODEX_CONFIG].decode("ascii")
        lines = cfg.split("\n")
        idx = [i for i, ln in enumerate(lines) if ln == CODEX_SWITCH_OFF and _section_of(lines, i) == "[features]"]
        if len(idx) != 1 or any(ln == CODEX_SWITCH_ON for ln in lines):
            raise HookRefused("the study's config.toml carries [features] hooks = false exactly once")
        on_lines = list(lines)
        on_lines[idx[0]] = CODEX_SWITCH_ON
        planted = (json.dumps(hooks, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode("ascii")
        off = {take_config.CODEX_CONFIG: base[take_config.CODEX_CONFIG], CODEX_HOOKS_FILE: planted}
        on = {take_config.CODEX_CONFIG: "\n".join(on_lines).encode("ascii"), CODEX_HOOKS_FILE: planted}
    diff = check_twins(harness, study, base, off, on, hooks=hooks, road=road)
    return {"base": base, "off": off, "on": on, "hooks": hooks, "diff": diff}


def write_twin(config_dir: str, files: dict) -> None:
    """The twin's files into the fresh, empty config folder, each with O_EXCL (take_config.write's own form)."""
    if os.path.islink(config_dir) or not os.path.isdir(config_dir) or os.listdir(config_dir):
        raise HookRefused("the config folder must exist and be empty")
    for rel, data in sorted(files.items()):
        path = os.path.join(config_dir, rel)
        os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)


def census_names(harness: str, rels) -> list:
    """Descriptive (the design's open call 7): which twin files the walk road's config-folder census refuses by name
    (run_take.CONFIG_FOLDER_NAMED), with the rule's text."""
    out = []
    for rel in sorted(rels):
        for rx, why in run_take.CONFIG_FOLDER_NAMED.get(harness, ()):
            if re.fullmatch(rx, rel):
                out.append((rel, why))
                break
    return out


# ------------------------------------------------------------------------------------------------ argv and env
def codex_inner(k: int, thread_id, *, bypass_trust: bool) -> list:
    """Process k's argv: codex_adapter.argv, checked by run_take.check_codex_turn, then (bypass runs only) the trust
    flag: before the prompt in process 1, right after `resume` in process 2 (both help captures list it)."""
    inner = codex_adapter.argv(CODEX_PROMPTS[k - 1], model=CODEX_MODEL, mode=CODEX_MODE, session_id=thread_id,
                               first=k == 1)
    run_take.check_codex_turn(inner)
    if not bypass_trust:
        return inner
    at = inner.index(codex_adapter.RESUME) + 1 if k > 1 else len(inner) - 1
    return inner[:at] + [TRUST_FLAG] + inner[at:]


def codex_environment_changes(values: dict, run_tree: str) -> dict:
    """The Codex process's pairs against the Codex row: refuses any difference at all."""
    row = run_take.take_environment(CODEX, run_tree)
    got = {"added": sorted(set(values) - set(row)), "removed": sorted(set(row) - set(values)),
           "replaced": sorted(k for k in set(values) & set(row) if values[k] != row[k])}
    if got != {"added": [], "removed": [], "replaced": []}:
        raise HookRefused(f"the Codex process's environment differs from the Codex row by {got}")
    return got


def codex_process_argv(take_id: str, inner, *, run_tree: str, caller_env=None) -> tuple:
    """The walk's Codex exec form (run_take._codex_exec_argv's argv) without its lease: the no-login launcher over
    exactly the Codex row."""
    run_take._check_id(take_id, "container id")
    values = run_take.exec_values(CODEX, run_tree)
    codex_environment_changes(values, run_tree)
    argv = [run_take.RUNTIME_CLIENT, "exec", "--user", run_take.AGENT_USER, "--workdir", run_tree, take_id,
            *run_take.launcher_argv(run_take.NO_LOGIN, values, list(inner), harness=CODEX)]
    return argv, run_take.runtime_env(caller_env)


def gemini_process_argv(take_id: str, inner, *, run_tree: str, port: int, caller_env=None) -> tuple:
    """B27's Gemini exec, unchanged (stub_model_probe.process_argv: its three environment changes)."""
    return smp.process_argv(take_id, inner, run_tree=run_tree, port=port, caller_env=caller_env)


def selftest_argv(take_id: str, run_tree: str) -> list:
    """The exact marker command, as the agent, through bash -c (the way Gemini spawns a command hook)."""
    return run_take.agent_exec_argv(take_id, [SHELL, "-c", marker_command(f"{run_tree}/{FIRED_REL}", SELFTEST)],
                                    workdir=run_tree)


def git_argvs(run_tree: str) -> list:
    """The Codex run tree's `git init` and one empty commit (so the trust table's key and Codex's git-root lookup
    match a walk's, take_config.py:79-88), on the host, before the grant."""
    name, email = GIT_IDENTITY
    cfg = ["-c", f"user.name={name}", "-c", f"user.email={email}", "-c", "init.defaultBranch=main",
           "-c", "commit.gpgsign=false"]
    return [("git-init", ["git", *cfg, "-C", run_tree, "init", "-q"]),
            ("git-commit", ["git", *cfg, "-C", run_tree, "commit", "-q", "--allow-empty", "-m", "start"])]


def git_env(run_tree: str) -> dict:
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": os.path.join(run_tree, run_take.RUN_TREE_HOMEDIR),
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "LANG": "C.UTF-8",
            "GIT_AUTHOR_DATE": GIT_DATE, "GIT_COMMITTER_DATE": GIT_DATE}


def network_argv() -> list:
    return [run_take.RUNTIME_CLIENT, "network", "create", "--internal", run_take.network_name()]


def take_resources() -> dict:
    return smp.take_resources()


def check_image(box: str, harness: str, image: str) -> dict:
    if not isinstance(image, str) or not IMAGE_ID.fullmatch(image):
        raise HookRefused(f"the {harness} image must be a full image id, sha256:<64 hex>")
    lock = preflight.load_take_lock(os.path.join(run_take._abs_path(box, "box"), *LOCKS[harness]), harness=harness)
    if lock["image_id"] != image:
        raise HookRefused(f"the {harness} image given is not its committed lock's image id")
    return lock


def scenario_names(spec: str) -> list:
    names = [s for s in (spec or "").split(",") if s]
    if not names or any(n not in SCENARIOS for n in names) or len(set(names)) != len(names):
        raise HookRefused(f"scenarios are a comma list of distinct names from {list(SCENARIOS)}")
    return names


def study_files(harness: str, run_tree: str) -> dict:
    if harness == CODEX:
        return take_config.files_for(CODEX, model=CODEX_MODEL, run_tree=run_tree)
    return take_config.files_for(GEMINI, model=HG_SCENARIO["model"])


def twins_row(harness: str, study: dict, twins: dict, run: Run) -> dict:
    files = twins[run.twin]
    return {"diff": twins["diff"], "study_sha256": files_sha256(study), "base_sha256": files_sha256(twins["base"]),
            "twin_sha256": files_sha256(files),
            "files": {rel: hashlib.sha256(b).hexdigest() for rel, b in sorted(files.items())},
            "walk_census_refuses": [list(x) for x in census_names(harness, files)]}


# ------------------------------------------------------------------------------------------------ the verdict
def events_of(selftest_read, reads) -> dict:
    """The marker log read per process: {selftest_ok, events (per process), anomalies}. A read that is not an append
    of the one before is read whole, less one leading self-test line; a missing read is an anomaly."""
    ok = selftest_read == SELFTEST + "\n"
    prev = selftest_read if isinstance(selftest_read, str) else ""
    events, anomalies = [], []
    for k, r in enumerate(reads, 1):
        if not isinstance(r, str):
            anomalies.append(f"process {k}: no fired.log")
            events.append([])
            continue
        if r.startswith(prev):
            new = r[len(prev):]
        else:
            anomalies.append(f"process {k}: fired.log is not an append of the read before")
            new = r[len(SELFTEST) + 1:] if r.startswith(SELFTEST + "\n") else r
        events.append([ln for ln in new.split("\n") if ln])
        prev = r
    return {"selftest_ok": ok, "events": events, "anomalies": anomalies}


EXEC_FAILED_CODES = (125, 126, 127)      # docker exec's own failures: the CLI never ran


def exit_class(code, timed_out: bool) -> str:
    """A process's exit, classed for the liveness comparison (REVIEW M1)."""
    if timed_out:
        return "timeout"
    if code is None or code in EXEC_FAILED_CODES:
        return "exec-failed"
    return "ok" if code == 0 else "error"


def first_type(stdout):
    """The `type` of a stream's first JSON record, or None."""
    for line in (stdout or "").split("\n"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            return rec.get("type") if isinstance(rec.get("type"), str) else None
    return None


def liveness_problem(harness: str, off_live, on_live):
    """REVIEW M1 (glitch-f1's ruling): an off twin counts as silent only with the same liveness as its on twin, per
    process. Gemini: the stub served at least one request in that process (a model request comes after SessionStart).
    Codex: the same exit class, never a docker exec failure, and the same first stream record type. None when live."""
    off_live, on_live = list(off_live or []), list(on_live or [])
    if not off_live or len(off_live) != len(on_live):
        return f"{len(off_live)} process(es) ran against its on twin's {len(on_live)}"
    for k, (o, n) in enumerate(zip(off_live, on_live), 1):
        if harness == GEMINI:
            if type(o.get("served")) is not int or o["served"] < 1:
                return f"process {k}: the stub served no request"
        else:
            if o.get("exit_class") == "exec-failed":
                return f"process {k}: the CLI never ran (a docker exec failure)"
            if (o.get("exit_class"), o.get("first_type")) != (n.get("exit_class"), n.get("first_type")):
                return (f"process {k}: exit {o.get('exit_class')}/{o.get('first_type')} against its on twin's "
                        f"{n.get('exit_class')}/{n.get('first_type')}")
    return None


def unit_blockers(u: dict) -> list:
    """REVIEW m1 and M1: what keeps any run (the informational one too) from supporting a PASS: a failure (the pre-run
    check's included), a `--version` that did not exit 0, a Gemini resume that did not run."""
    out = []
    if u.get("failure"):
        out.append(f"the run failed ({(u['failure'] or {}).get('type') if isinstance(u['failure'], dict) else u['failure']})")
    if u.get("cli_version_rc") != 0:
        out.append(f"the CLI's --version exited {u.get('cli_version_rc')}")
    if u.get("harness") == GEMINI and u.get("resume_skipped"):
        out.append("the Gemini resume did not run")
    return out


def hook_verdict(units: list, arms) -> dict:
    """glitch-f1's verdict (the rulings on the review of d9d9b79e). Per arm: FAIL if any off twin logged an event in
    a per-process read or the host's read after teardown; else INCONCLUSIVE if any run (on, off or informational) has
    a blocker or a required run is missing; else per road: a road passes when its on twin logged SessionStart in
    process 1 after a good self-test and each off twin is live (liveness_problem), had a good self-test, a final read
    and no event. Gemini (one road) passes with its road; Codex passes when at least one road passes; otherwise
    INCONCLUSIVE. Overall: the worst arm."""
    out = {}
    for arm in arms:
        mine = [u for u in units if ARM.get(u.get("harness")) == arm]
        fail, inc, runs, roads, road_why = [], [], {}, {}, []
        scenarios = sorted({u["scenario"] for u in mine})
        if not mine:
            inc.append("no run of this arm")
        for s in scenarios:
            have = {u["run"] for u in mine if u["scenario"] == s}
            need = {r.name for r in RUNS.get(s, ()) if r.role in ("on", "off")}
            for missing in sorted(need - have):
                inc.append(f"{s}/{missing}: not run")
        judged = {}
        for u in mine:
            key = f"{u['scenario']}/{u['run']}"
            reads = list(u.get("reads") or [])
            e = events_of(u.get("selftest_read"), reads)
            final = u.get("final_read")
            ef = events_of(u.get("selftest_read"), reads + [final]) if isinstance(final, str) else e
            judged[key] = (u, e, ef)
            runs[key] = dict(e, role=u["role"], late=ef["events"][len(e["events"]):] if ef is not e else None)
            if u["role"] == "off" and any(ef["events"]):
                fail.append(f"{key}: an off twin logged {sorted({x for p in ef['events'] for x in p})}")
            inc += [f"{key}: {b}" for b in unit_blockers(u)]
        for s in scenarios:
            in_s = [judged[k] for k in judged if k.startswith(s + "/")]
            on = [x for x in in_s if x[0]["role"] == "on"]
            offs = [x for x in in_s if x[0]["role"] == "off"]
            why = []
            if len(on) != 1:
                why.append("no on twin")
            else:
                u, e, _ef = on[0]
                if not e["selftest_ok"]:
                    why.append(f"{u['run']}: the self-test failed")
                elif not e["events"] or PASS_EVENT not in e["events"][0]:
                    why.append(f"{u['run']}: the on twin did not log {PASS_EVENT} in process 1")
            need = sum(1 for r in RUNS.get(s, ()) if r.role == "off")
            if len(offs) != need:
                why.append("an off twin is missing")
            for u, e, ef in offs:
                if not e["selftest_ok"]:
                    why.append(f"{u['run']}: the self-test failed")
                elif not e["events"]:
                    why.append(f"{u['run']}: no process ran")
                elif e["anomalies"]:
                    why.append(f"{u['run']}: {'; '.join(e['anomalies'])}")
                elif not isinstance(u.get("final_read"), str):
                    why.append(f"{u['run']}: no host read after teardown")
                elif on:
                    lp = liveness_problem(u["harness"], u.get("liveness"), on[0][0].get("liveness"))
                    if lp:
                        why.append(f"{u['run']}: not live: {lp}")
            roads[s] = not why
            road_why += [f"{s}: {w}" for w in why]
        if fail:
            verdict = "FAIL"
        elif inc:
            verdict = "INCONCLUSIVE"
        elif arm == ARM[CODEX]:
            verdict = "PASS" if any(roads.values()) else "INCONCLUSIVE"
        else:
            verdict = "PASS" if roads and all(roads.values()) else "INCONCLUSIVE"
        out[arm] = {"verdict": verdict, "reasons": fail + inc + road_why, "roads": roads, "runs": runs}
    order = {"PASS": 0, "INCONCLUSIVE": 1, "FAIL": 2}
    overall = max((r["verdict"] for r in out.values()), key=order.get, default="INCONCLUSIVE")
    return {"verdict": overall, "arms": out}


# ------------------------------------------------------------------------------------------------ dry run
def dry_run(names: list, images: dict, resources: dict) -> list:
    out = []
    for s in names:
        harness = SCENARIO_HARNESS[s]
        image = images[harness]
        for run in RUNS[s]:
            run_tree, cfg, evidence = f"{DRY_ROOT}/t", f"{DRY_ROOT}/cfg-dryrun", f"{DRY_ROOT}/e"
            take_id = net_id = "0" * 64
            study = study_files(harness, run_tree)
            twins = hook_twins(harness, study, fired_path=f"{run_tree}/{FIRED_REL}", road=ROADS[s])
            rows = [dict(step="twins", **twins_row(harness, study, twins, run))]
            steps = list(git_argvs(run_tree)) if harness == CODEX else []
            steps += [("grant-run_tree", ownership.own_argv(image, run_tree, ownership.AGENT_UID, strict=True)),
                      ("grant-config_dir", ownership.own_argv(image, cfg, ownership.AGENT_UID, strict=True)),
                      ("grant-evidence_dir", ownership.own_argv(image, evidence, ownership.WATCHER_UID, strict=True)),
                      ("network-create", network_argv()),
                      ("take-create", run_take.create_argv(smp.take_spec(image, run_tree, cfg, net_id, resources))),
                      ("take-inspect", [run_take.RUNTIME_CLIENT, "container", "inspect", take_id]),
                      ("take-start", [run_take.RUNTIME_CLIENT, "start", take_id])]
            if harness == GEMINI:
                port = 40000
                steps.append(("stub-start", smp.stub_start_argv(take_id, run_tree)))
                steps.append(("selftest", selftest_argv(take_id, run_tree)))
                steps.append(("cli-version", gemini_process_argv(take_id, ["gemini", "--version"], run_tree=run_tree,
                                                                 port=port, caller_env={})[0]))
                for k in (1, 2):
                    inner = smp.cli_inner(HG_SCENARIO, k, None if k == 1 else smp.DRY_SESSION)
                    steps.append((f"process-{k}", gemini_process_argv(take_id, inner, run_tree=run_tree, port=port,
                                                                      caller_env={})[0]))
                env = {"step": "environment", "process_environment": smp.probe_environment(run_tree, port),
                       "changes": smp.environment_changes(smp.probe_environment(run_tree, port), run_tree)}
            else:
                steps.append(("selftest", selftest_argv(take_id, run_tree)))
                steps.append(("cli-version", codex_process_argv(take_id, ["codex", "--version"], run_tree=run_tree,
                                                                caller_env={})[0]))
                for k in (1, 2):
                    inner = codex_inner(k, None if k == 1 else DRY_THREAD, bypass_trust=run.bypass)
                    steps.append((f"process-{k}", codex_process_argv(take_id, inner, run_tree=run_tree,
                                                                     caller_env={})[0]))
                values = run_take.exec_values(CODEX, run_tree)
                env = {"step": "environment", "process_environment": values,
                       "changes": codex_environment_changes(values, run_tree)}
            steps += [("take-rm", [run_take.RUNTIME_CLIENT, "rm", "--force", take_id]),
                      ("network-rm", [run_take.RUNTIME_CLIENT, "network", "rm", net_id])]
            rows += [{"step": name, "argv": argv} for name, argv in steps] + [env]
            out += [dict(r, scenario=s, run=run.name) for r in rows]
    return out


# ------------------------------------------------------------------------------------------------ the athena side
def _write_new(path: str, data: bytes) -> None:
    smp._write_new(path, data)


def _json(doc) -> bytes:
    return (json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n").encode("utf-8")


def thread_id_of(stdout: str):
    """The first thread.started thread id of a Codex stream (codex_adapter's own shape), or None."""
    for line in (stdout or "").split("\n"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict) and rec.get("type") == "thread.started" and isinstance(rec.get("thread_id"), str) \
                and _THREAD_ID.fullmatch(rec["thread_id"]):
            return rec["thread_id"]
    return None


def build_codex_run_tree(run_tree: str, *, host_run) -> dict:
    os.mkdir(run_tree, 0o755)
    for d in (run_take.RUN_TREE_TMPDIR, run_take.RUN_TREE_HOMEDIR):
        os.mkdir(os.path.join(run_tree, d), 0o700)
    steps = []
    for name, argv in git_argvs(run_tree):
        p = host_run(argv, env=git_env(run_tree), capture_output=True, text=True, timeout=60)
        steps.append({"step": name, "argv": argv, "returncode": p.returncode, "stderr": (p.stderr or "")[-500:]})
        if p.returncode != 0:
            raise HookRefused(f"{name} exited {p.returncode}")
    head = host_run(["git", "-C", run_tree, "rev-parse", "HEAD"], env=git_env(run_tree), capture_output=True,
                    text=True, timeout=60)
    return {"steps": steps, "head": head.stdout.strip() if head.returncode == 0 else None}


def run_unit(runtime, env: dict, scenario: str, run: Run, *, image: str, scratch_parent: str, out_root: str,
             resources: dict, host_run=subprocess.run) -> dict:
    """One run on the box: its twin, run tree, grant, network, take, (Gemini) the stub, the self-test and its pre-run
    check, the CLI processes with fired.log read after each, then teardown, restore and the records copied into
    <out_root>/<scenario>/<run>."""
    harness = run.harness
    out = os.path.join(out_root, scenario, run.name)
    os.makedirs(out, 0o755)
    base = os.path.realpath(tempfile.mkdtemp(prefix="hc-", dir=scratch_parent))
    run_tree, evidence = os.path.join(base, "t"), os.path.join(base, "e")
    os.mkdir(evidence, 0o755)
    cfg = run_take.make_config_dir(base)
    fired = f"{run_tree}/{FIRED_REL}"
    rec = {"scenario": scenario, "run": run.name, "harness": harness, "role": run.role, "twin": run.twin,
           "bypass_trust": run.bypass, "road": ROADS[scenario], "image": image, "started_at": time.time(),
           "departures": list(DEPARTURES), "scratch": {"base": base, "run_tree": run_tree, "config": cfg},
           "processes": [], "reads": [], "selftest_read": None, "precheck": None, "inner": [], "liveness": [],
           "cli_version_rc": None, "resume_skipped": None, "final_read": None,
           "predicted_events": list(PREDICTED_G_ON) if (harness == GEMINI and run.twin == "on") else None}
    study = study_files(harness, run_tree)
    twins = hook_twins(harness, study, fired_path=fired, road=ROADS[scenario])
    files = twins[run.twin]
    rec["twins"] = twins_row(harness, study, twins, run)
    write_twin(cfg, files)
    rec["twins"]["config_sha256"] = take_config.config_sha256(cfg, harness)
    os.mkdir(os.path.join(out, "twin"), 0o755)
    for rel, data in sorted(files.items()):
        _write_new(os.path.join(out, "twin", rel.replace("/", "__")), data)
    if harness == GEMINI:
        smp.build_run_tree(run_tree, HG_SCENARIO)
    else:
        rec["git"] = build_codex_run_tree(run_tree, host_run=host_run)
    os.mkdir(os.path.join(run_tree, HOOK_DIR), 0o755)
    launched = run_take.Launched(config_dir=cfg)
    restored = False

    def read_fired():
        raw = ownership.operator_read(runtime, image=image, root_kind="run_tree", run_tree=run_tree, config_dir=cfg,
                                      rel_path=FIRED_REL, caller_env=env)
        return raw

    def listing(rel_dir):
        try:
            return ownership.operator_list(runtime, image=image, root_kind="config", run_tree=run_tree,
                                           config_dir=cfg, rel_dir=rel_dir, caller_env=env)
        except Exception as e:  # noqa: BLE001 - recorded only
            return {"error": f"{type(e).__name__}: {str(e)[:300]}"}
    try:
        rec["grant"] = ownership.grant(runtime, image=image, run_tree=run_tree, config_dir=cfg, evidence_dir=evidence,
                                       caller_env=env)
        c = run_take._step(runtime, launched, "network-create", network_argv(), env)
        launched.network_id = run_take._new_id(c, "network-create")
        launched.spec = spec = smp.take_spec(image, run_tree, cfg, launched.network_id, resources)
        c = run_take._step(runtime, launched, "take-create", run_take.create_argv(spec), env)
        launched.take_id = run_take._new_id(c, "take-create")
        run_take._inspect(runtime, launched, "take-inspect", launched.take_id, env)
        run_take._step(runtime, launched, "take-start", [run_take.RUNTIME_CLIENT, "start", launched.take_id], env)
        launched.ok = True
        port = None
        if harness == GEMINI:
            c = runtime.run(smp.stub_start_argv(launched.take_id, run_tree), env=env, timeout=smp.STUB_START_TIMEOUT_S)
            ready = json.loads(c.stdout.strip().splitlines()[-1]) if c.returncode == 0 and c.stdout.strip() else {}
            if ready.get("ready") is not True or type(ready.get("port")) is not int:
                raise HookRefused(f"the stub did not start (exit {c.returncode})")
            port = ready["port"]
            rec["stub"] = {"port": port, "base_url": f"http://{smp.STUB_HOST}:{port}"}
        # the self-test, then the fail-safe pre-run check: no CLI process unless fired.log reads exactly `selftest`
        st = runtime.run(selftest_argv(launched.take_id, run_tree), env=env, timeout=60)
        raw = read_fired()
        rec["selftest"] = {"returncode": st.returncode, "stderr": st.stderr[-1000:]}
        rec["selftest_read"] = raw.decode("utf-8", "replace") if raw is not None else None
        _write_new(os.path.join(out, "fired-after-selftest.log"), raw or b"")
        rec["precheck"] = marker_precheck(raw)
        if rec["precheck"]:
            raise HookRefused(f"the pre-run marker check failed: {rec['precheck'][0]}")

        def argv_for(inner):
            if harness == GEMINI:
                return gemini_process_argv(launched.take_id, inner, run_tree=run_tree, port=port, caller_env=env)
            return codex_process_argv(launched.take_id, inner, run_tree=run_tree, caller_env=env)
        argv, cenv = argv_for(["gemini" if harness == GEMINI else "codex", "--version"])
        v = runtime.run(argv, env=cenv, timeout=120)
        rec["cli_version"] = {"returncode": v.returncode, "stdout": v.stdout[-500:], "stderr": v.stderr[-1000:]}
        rec["cli_version_rc"] = v.returncode
        served_before = 0
        session = None
        for k in (1, 2):
            if k == 2 and session is None:
                rec["resume_skipped"] = "process 1's stream named no session or thread id"
                break
            if harness == GEMINI:
                inner = smp.cli_inner(HG_SCENARIO, k, session)
                cap = GEMINI_PROCESS_TIMEOUT_S
            else:
                inner = codex_inner(k, session, bypass_trust=run.bypass)
                cap = CODEX_PROCESS_TIMEOUT_S
            argv, cenv = argv_for(inner)
            rec["inner"].append(inner)
            started = time.time()
            try:
                p = runtime.run(argv, env=cenv, timeout=cap)
                code, stdout, stderr, timed_out = p.returncode, p.stdout, p.stderr, False
            except TimeoutError as e:
                code, stdout, stderr, timed_out = None, getattr(e, "stdout", "") or "", "", True
            _write_new(os.path.join(out, f"turn-{k}.jsonl"), stdout.encode("utf-8", "surrogateescape"))
            _write_new(os.path.join(out, f"turn-{k}.stderr.txt"), stderr.encode("utf-8", "surrogateescape"))
            raw = read_fired()
            rec["reads"].append(raw.decode("utf-8", "replace") if raw is not None else None)
            _write_new(os.path.join(out, f"fired-after-process-{k}.log"), raw or b"")
            prow = {"process": k, "returncode": code, "timed_out": timed_out, "started_at": started,
                    "ended_at": time.time(), "config_listing": listing(".")}
            if harness == GEMINI:
                prow["config_listing_gemini"] = listing(".gemini")
                state = ownership.operator_read(runtime, image=image, root_kind="run_tree", run_tree=run_tree,
                                                config_dir=cfg, rel_path=f"{smp.STUB_OUT}/state.json", caller_env=env)
                prow["stub_state"] = json.loads(state) if state else None
                total = (prow["stub_state"] or {}).get("requests")
                served = total - served_before if type(total) is int else None
                served_before = total if type(total) is int else served_before
                rec["liveness"].append({"served": served})
            else:
                rec["liveness"].append({"exit_class": exit_class(code, timed_out), "first_type": first_type(stdout)})
            if k == 1:
                session = smp.session_id_of(stdout) if harness == GEMINI else thread_id_of(stdout)
                prow["session_or_thread_id"] = session
            rec["processes"].append(prow)
    except Exception as e:  # recorded; the teardown below still runs on whatever was made
        rec["failure"] = {"type": type(e).__name__, "detail": str(e)[:2000]}
    finally:
        run_take._teardown_partial(runtime, launched, None, base, env)
        rec["launch"] = launched.to_record()
        ids = launched.ids()
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
            except Exception as e:  # noqa: BLE001
                rec["network_left"] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
        try:
            rec["restore"] = ownership.restore(runtime, image=image, run_tree=run_tree, config_dir=cfg,
                                               evidence_dir=evidence, ids=ids, caller_env=env)
            restored = True
        except ownership.OwnershipError as e:
            rec["restore"] = {"error": str(e), **e.record}
        except Exception as e:  # noqa: BLE001
            rec["restore"] = {"error": f"{type(e).__name__}: {str(e)[:500]}"}
    if restored:
        # REVIEW m2: every writer is dead now; the host's own read of fired.log judges the off twins
        final = os.path.join(run_tree, FIRED_REL)
        if os.path.isfile(final) and not os.path.islink(final):
            with open(final, "rb") as fh:
                raw = fh.read()
            rec["final_read"] = raw.decode("utf-8", "replace")
            _write_new(os.path.join(out, "fired-after-teardown.log"), raw)
        if harness == GEMINI and os.path.isdir(os.path.join(run_tree, smp.STUB_OUT)):
            shutil.copytree(os.path.join(run_tree, smp.STUB_OUT), os.path.join(out, "stub"))
            shutil.copyfile(os.path.join(run_tree, smp.STUB_DIR, "scenario.json"), os.path.join(out, "scenario.json"))
        shutil.rmtree(base)
        rec["scratch_removed"] = not os.path.lexists(base)
    else:
        rec["scratch_removed"] = False
        rec["scratch_kept_why"] = "the ownership restore failed: the scratch is kept for a human"
    rec["ended_at"] = time.time()
    rec["events"] = events_of(rec["selftest_read"], rec["reads"])
    rec["problems"] = unit_problems(rec)
    _write_new(os.path.join(out, "probe.json"), _json(labelled(rec)))
    return rec


def unit_problems(rec: dict) -> list:
    """What keeps a run's records from being whole (never the CLI's exit: C0 and C1 exit non-zero by design): a failure
    other than the pre-run check, anything left after teardown, a failed restore, a kept scratch."""
    out = []
    if rec.get("failure") and not rec.get("precheck"):
        out.append(f"failure: {rec['failure'].get('type')}")
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
            files[os.path.relpath(p, out_root)] = {"sha256": smp._sha256_file(p), "bytes": os.path.getsize(p)}
    return labelled({"files": files})


def run_probe(a, names: list, *, runtime=None, env=None, host_run=subprocess.run) -> dict:
    if sys.platform != "linux":
        raise HookRefused("the probe runs on athena's Linux box only (use --dry-run elsewhere)")
    parent = run_take._abs_path(a.scratch_parent, "scratch_parent")
    if os.path.islink(parent) or not os.path.isdir(parent) or os.stat(parent).st_uid != os.getuid() \
            or not run_take.outside_every_repository(parent):
        raise HookRefused("the scratch parent is an owned folder outside every repository")
    if run_take._inside(a.output, parent):
        raise HookRefused("the output never sits in the scratch it removes")
    os.mkdir(a.output, 0o755)
    env = smp.client_env() if env is None else env
    runtime = smp.Recorder() if runtime is None else runtime
    resources = take_resources()
    images = {GEMINI: getattr(a, "gemini_image", None), CODEX: getattr(a, "codex_image", None)}
    units, recs = [], []
    for s in names:
        for run in RUNS[s]:
            rec = run_unit(runtime, env, s, run, image=images[run.harness], scratch_parent=parent, out_root=a.output,
                           resources=resources, host_run=host_run)
            recs.append(rec)
            units.append({k: rec.get(k) for k in ("scenario", "run", "harness", "role", "selftest_read", "reads",
                                                  "final_read", "liveness", "cli_version_rc", "failure",
                                                  "resume_skipped")})
    arms = sorted({ARM[SCENARIO_HARNESS[s]] for s in names})
    verdict = hook_verdict(units, arms)
    summary = {"verdict": verdict, "images": images, "reason": getattr(a, "reason", ""), "resources": resources,
               "predicted_g_on_events": list(PREDICTED_G_ON),
               "problems": {f"{r['scenario']}/{r['run']}": r["problems"] for r in recs if r["problems"]},
               "units": [{"scenario": r["scenario"], "run": r["run"], "role": r["role"], "precheck": r["precheck"],
                          "events": r["events"]["events"], "selftest_ok": r["events"]["selftest_ok"],
                          "returncodes": [p["returncode"] for p in r["processes"]], "failure": r.get("failure"),
                          "twin_sha256": r["twins"]["twin_sha256"], "study_sha256": r["twins"]["study_sha256"]}
                         for r in recs]}
    calls = getattr(runtime, "calls", None)
    if calls is not None:
        _write_new(os.path.join(a.output, "calls.json"), _json(labelled({"calls": calls})))
    _write_new(os.path.join(a.output, "summary.json"), _json(labelled(summary)))
    _write_new(os.path.join(a.output, "manifest.json"),
               (json.dumps(manifest(a.output), indent=1, sort_keys=True) + "\n").encode("utf-8"))
    return summary


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--box", required=True)
    p.add_argument("--scratch-parent", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--gemini-image")
    p.add_argument("--codex-image")
    p.add_argument("--scenarios", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--reason", default="")
    a = p.parse_args(argv)
    names = scenario_names(a.scenarios)
    images = {GEMINI: a.gemini_image, CODEX: a.codex_image}
    for harness in (GEMINI, CODEX):
        wanted = any(SCENARIO_HARNESS[s] == harness for s in names)
        if wanted:
            check_image(a.box, harness, images[harness])
        elif images[harness] is not None:
            raise HookRefused(f"a {harness} image is given but no {harness} scenario is named")
    if a.dry_run:
        for row in dry_run(names, images, take_resources()):
            print(json.dumps(row, sort_keys=True))
        return 0
    smp.check_output(a.output)
    summary = run_probe(a, names)
    print(json.dumps({"record_kind": RECORD_KIND, "output": a.output, "verdict": summary["verdict"]["verdict"],
                      "problems": summary["problems"]}, sort_keys=True))
    return 0 if summary["verdict"]["verdict"] == "PASS" and not summary["problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
