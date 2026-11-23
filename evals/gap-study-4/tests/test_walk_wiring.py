#!/usr/bin/env python3
"""Lane w7b (Gap Study round 4, wave 7 piece P2): the CP6 walk wiring, and one end-to-end take on a FAKE runtime.

cp6-readiness-2026-10-11 row 3 and section 2: the production road a walk will use (drive.walk_driver), the take folder
fixed in one name both the driver and mode_binding.py read, the adapter's identity stamped on every persisted take,
and the end-to-end take S6c covered only in halves (D7 the records, D8 the checker).

  W1-strict  C6-strict (W6J-close-1's CP6 checklist item): walk_driver builds a WalkDriver whose script is strict;
             a bare operator line through the walk driver is refused (DriveRefused naming the bare line), never sent;
             walk_driver takes no strict_script, WalkDriver refuses one, and the attribute refuses any value but
             True. Witnesses: walk-not-strict (the property reads False), walk-strict-settable (the setter accepts
             False silently).
  W2-folder  Q-w6i-1: the production take folder is <root>/<mode_binding.TAKES_DIR>/<slot>/<k>, k the next unused
             attempt, a slot that is not one path segment refused; drive.TAKES_DIR is mode_binding.TAKES_DIR (one
             name) and the walk driver's take_folder is take_folder_in. Witness: folder-renamed (drive.py spells its
             own folder name).
  W3-identity W6B-R1-3: an adapter whose own name is not the row's harness (a stub under a claude-code row, or an
             adapter with no name) is refused before it starts (AdapterIdentityRefused, a stop, never a rehearsal);
             under its own row a stub's persisted evidence ledger names the stub. Witness: identity-unchecked.
  W4-root    W7B-R1-2: walk_driver refuses a root that is not mode_binding.HERE, the folder its --check reads.
             Witness: root-unchecked.
  W5-one-road W7B-R1-1: by AST, no non-test module under evals/gap-study-4 calls TakeDriver( or derives from it
             except WalkDriver. Witnesses: added-construction, added-subclass (one module's source extended).
  W6-pending W7B-R1-6: every walk-measured checker constant is PENDING (the two known values aside) and routing.json's
             pin_profiles are exactly CP5's registration (arm A's three, Javier 14 Oct 2026) and, since round 17 B7
             (moved by glitch-b5's ruling M, 18 Oct 2026), R4's O and G profiles. Witnesses: constant-filled,
             pin-filled, vendor-pin-drift.
  E1-take    the end-to-end take: batch.Batch drives the walk driver (TakeDriver through walk_driver, the REAL Claude
             Code adapter on a fake box that answers in the recorded stream shape and writes a session file, the
             REAL check4 on round 4's REAL design through take_checker), routing labels it, TakeRepo commits it into
             a scratch repository. It is GRADED, and the committed take folder holds the evidence ledger, launch,
             preflight, postflight, teardown, environment.json, driver-ledger.json, the session copy
             (transcript.jsonl with scrub.json), operator-check.json and the turn streams; mode_binding.py reads it
             from TAKES_DIR with no problem. Witnesses: folder-renamed, top-level-harness (mode_binding).
  E2-tree    Q-w6i-5 end to end: the same take whose session records that it opened somewhere other than the run
             tree the driver gave it is readers-disagree after the first agent turn, so routing labels it
             harness-error, never graded. Witness: tree-unchecked (check_take.py without the cross-check).

TEST DATA, NEVER PRODUCTION VALUES. The rig's own values are supplied here, labelled, and never written into a
production constant (check_take.CHECKER_CONSTANTS holds the bootstrap ruling's values since 15 Oct 2026):
  WALK_CONSTANTS  the six checker constants (test_checker_body's walk-shaped values; the turn budget equals the
                  driver's budget here; environment_record mirrors the vocabulary drive.py publishes, which is the
                  equality a walk must show; stripped_env empty, as drive.STRIPPED_ENV reads under this process);
  the routing pin one claude-code profile for the draft row's model (bypassPermissions, the fake harness version);
  the row          the draft's own scope-read / trap / w3 / arm A row, its agent version set to the fake harness's;
  the identity     one synthetic row commit (test_checker_body.COMMIT) and the session id takes.session_id_for derives
                  from it; the source rendered from the task's template with the take's run tree; the fixture record
                  from fixture_record(), a synthetic fixture builder that reads the half's pinned fixture hash.
The process guard, the fake box and the PENDING runtime spellings are test_box_integration's setUpModule; the
pinned tree's read-only git is admitted for design_view (test_checker_body's rule). Fakes and synthetic strings
only: no model, vendor, network, container runtime, credential or holdout.
"""

from __future__ import annotations

import contextlib
import copy
import inspect
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import prereg  # noqa: E402
import takes  # noqa: E402
import variants  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_checker_body as tcb  # noqa: E402
import test_drive_loop as tdl  # noqa: E402
from box import run_take as rt  # noqa: E402
from box import sidecar as sc  # noqa: E402
from graders import labels4  # noqa: E402

REAL_LOAD = prereg.load            # captured before test_box_integration patches it for drive.py's import
REAL_LOAD_ROWS, REAL_ROW_COMMITS = takes.load_rows, takes.row_commits
CC_VERSION = tdl.CC_VERSION
BYPASS = tcb.BYPASS
LOGIN_NAME = "CLAUDE_CODE_OAUTH_TOKEN"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


guarded = tbi.guarded


# ------------------------------------------------------------------------------------------------ the test data
def the_row() -> dict:
    """The draft's own row (scope-read / trap / w3 / arm A); its agent version is the fake harness's (TEST DATA)."""
    r = tcb.row()
    r["agent"] = {"harness": "claude-code", "version": CC_VERSION}
    return r


def the_table() -> dict:
    """routing.json with one claude-code pin for the row's model (TEST DATA: pin_profiles are PENDING)."""
    t = tbi.table()
    t["pin_profiles"] = {"claude-code": {the_row()["model"]: {"permission_mode": BYPASS, "version": CC_VERSION}}}
    return t


def walk_constants(ct, drive) -> dict:
    """The checker constants a walk measures (TEST DATA; production stays PENDING and check4 refuses it)."""
    c = tcb.walk_constants(ct)
    c["budgets"] = {"turn_timeout_s": 600,                     # the rig's budget_s
                    "finalize_wait_s": tbi.CAP_S, "poll_s": tbi.POLL_S}   # BOOTSTRAP B4: the rig's cap and poll
    c["environment_record"] = {
        "file": drive.ENVIRONMENT_RECORD_FILE, "schema": drive.ENVIRONMENT_SCHEMA,
        # BOOTSTRAP: the record's vocabulary is drive.py's RECORD_ names (round 3's, extended with 2.1.296's)
        "name_patterns": {"harness": list(drive.RECORD_HARNESS_NAME_PATTERNS),
                          "generic": list(drive.GENERIC_NAME_PATTERNS)},
        "api_key_variables": list(drive.RECORD_API_KEY_VARIABLES),
        "billing_route_variables": list(drive.RECORD_BILLING_ROUTE_VARIABLES),
        "subscription_token_variables": list(drive.RECORD_SUBSCRIPTION_TOKEN_VARIABLES),
        "credential_source_key": drive.CREDENTIAL_SOURCE_KEY}
    return c


def fixture_record(row: dict) -> dict:
    """The synthetic fixture builder: the record a built fixture of this half carries (its pinned hash). A project
    fixture records a variant and stage 01's exits instead, which this builder does not build (refused)."""
    fx = variants.load_task(row["task"])["halves"][row["half"]]["fixture"]
    if fx.get("kind") == "project" or not fx.get("sha256"):
        raise ValueError(f"the synthetic fixture builder builds hashed fixtures only, not {fx.get('kind')!r}")
    return {"sha256": fx["sha256"]}


# ------------------------------------------------------------------------------------------------ the fake box
class SessionBox(tdl.ClaudeBox):
    """ClaudeBox, answering each turn of the take's own script: the reply holds the step's marker, the model is the
    row's, and the session file is the shape check4 reads on the real design (test_checker_body's clean take: the
    environment attachment at the exec's --workdir, the pinned tree's instruction file, the session context with a
    planted account email that scrub.py must remove, the prompt snapshot). `opened_in` makes the session record
    another working directory than the exec's (E2-tree)."""

    def __init__(self, script, model, *, opened_in=None, **kw):
        replies = [{"text": f"Synthetic reply. {s.get('marker') or 'Here is what the file says.'}"} for s in script]
        super().__init__(replies, **kw)
        self.model, self.opened_in, self.per_take = model, opened_in, {}

    def turn(self, a):
        # Departure w12a-4: the container id is the exec's first full id (a launcher now stands before claude).
        cid = next(x for x in a[2:] if len(x) == 64 and all(c in "0123456789abcdef" for c in x))
        cid, line, sid = cid, a[a.index("-p") + 1], a[-1]
        n = self.per_take[cid] = self.per_take.get(cid, 0) + 1      # a re-run is a new container: its own turn 1
        wd = self.opened_in or a[a.index("--workdir") + 1]
        msg, req, model = f"msg_w{n}", f"req_w{n}", self.model
        content = [{"type": "text", "text": self.replies[n - 1]["text"]}]
        stream = [{"type": "system", "subtype": "init", "session_id": sid, "apiKeySource": "none", "model": model,
                   "permissionMode": BYPASS, "claude_code_version": CC_VERSION, "tools": ["Bash", "Read"]},
                  {"type": "assistant", "session_id": sid, "request_id": req,
                   "message": {"id": msg, "model": model, "role": "assistant", "content": content,
                               "usage": {"input_tokens": 7, "output_tokens": 2}}},
                  {"type": "result", "subtype": "success", "is_error": False, "session_id": sid,
                   "total_cost_usd": 0.01 * n, "num_turns": 1, "permission_denials": [],
                   "usage": dict(tdl.USAGE), "modelUsage": {model: {"costUSD": 0.01 * n}}}]
        recs = []
        if n == 1:
            git_status = (f"Current branch: main\n\nGit user: {tcb.IDENTITY}\n\nStatus:\n(clean)\n\nRecent commits:\n"
                          f"abc1234 {tcb.SUBJECT}")
            for att in ({"type": "environment", "snapshot": {"workingDirectory": wd, "additionalWorkingDirectories": []}},
                        {"type": "instructions", "files": [{"path": f"{wd}/{tcb.INSTRUCTION}",
                                                            "content": tcb.pinned_text(tcb.INSTRUCTION)}]},
                        {"type": "session_context", "context": {"userEmail": tbi.EMAIL, "gitStatus": git_status}},
                        {"type": "prompt_snapshot", "text": "a synthetic system prompt"}):
                recs.append({"type": "attachment", "sessionId": sid, "attachment": att})
        recs.append({"type": "user", "sessionId": sid, "permissionMode": BYPASS,
                     "message": {"role": "user", "content": line}})
        recs.append({"type": "assistant", "sessionId": sid, "requestId": req, "message": {
            "id": msg, "model": model, "role": "assistant", "content": content, "usage": dict(tdl.USAGE),
            "stop_reason": "end_turn"}})
        folder = Path(self.cfg_of(cid)) / "projects" / "-work-run"
        with tbi.FakeBox.as_container(self.cfg_of(cid)):     # Claude Code writes its own config folder (the P4 road)
            folder.mkdir(parents=True, exist_ok=True)
            with open(folder / f"{sid}.jsonl", "a", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r) + "\n" for r in recs))
        return tbi.ok("".join(json.dumps(r) + "\n" for r in stream))


# ------------------------------------------------------------------------------------------------ the world
@contextlib.contextmanager
def world():
    """check4's world inside test_box_integration's process guard (test_drive_loop.checker_world's, with one change):
    the real pre-registration draft; the row ledger and its commit as check() reads them (no arguments) answer the
    synthetic row and commit, while the registration's own reads (root=, repo=) stay real; the pinned tree's
    read-only git admitted."""
    run, popen = subprocess.run, subprocess.Popen

    def gate_popen(*args, **kw):
        if args and tcb._pinned_git(args[0]):
            return tcb._REAL_POPEN(*args, **kw)
        return popen(*args, **kw)

    def gate_run(*args, **kw):
        if args and tcb._pinned_git(args[0]):
            return tcb._REAL_RUN(*args, **kw)
        return run(*args, **kw)
    with contextlib.ExitStack() as st:
        st.enter_context(mock.patch.object(prereg, "load", REAL_LOAD))
        st.enter_context(mock.patch.object(takes, "load_rows",
                                           lambda **kw: REAL_LOAD_ROWS(**kw) if kw else [tcb.row()]))
        st.enter_context(mock.patch.object(takes, "row_commits",
                                           lambda **kw: REAL_ROW_COMMITS(**kw) if kw else {0: tcb.COMMIT}))
        st.enter_context(mock.patch.object(subprocess, "Popen", gate_popen))
        st.enter_context(mock.patch.object(subprocess, "run", gate_run))
        import check_take as ct
        home = tbi.SCRATCH / "check-home"
        home.mkdir(exist_ok=True)
        st.enter_context(mock.patch.object(ct, "CHECK_HOME", home))
        st.enter_context(mock.patch.object(tcb, "SCRATCH", tbi.SCRATCH))
        yield ct


class Wired:
    """One scratch repository, the walk driver built through walk_driver on a SessionBox, and a TakeRepo."""

    def __init__(self, mod, ct, root: Path, *, opened_in=None, mb=None):
        self.mod, self.ct, self.root = mod, ct, root
        r = the_row()
        self.row, self.table = r, the_table()
        self.tree = tbi.SCRATCH / f"tree-w7b-{root.name}"
        self.tree.mkdir(exist_ok=True)
        self.constants = walk_constants(ct, mod)
        self.sid = takes.session_id_for(tcb.COMMIT)
        self.project = mod.neutral_name(self.sid)
        self.source = variants.render_source(variants.load_task(r["task"])["source_template"], str(self.tree),
                                             self.project)
        script = self.design_for(r, str(self.tree)).script
        self.box = SessionBox(script, r["model"], opened_in=opened_in)
        self.clock = tbi.Clock()
        self.box.clock = self.clock
        self.cfg_parent = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        self.spy = tbi.Spy()
        login = tbi.SCRATCH / f"login-{root.name}"
        login.write_text(f"{LOGIN_NAME}={tbi.TOKEN}\n")
        os.chmod(login, 0o600)
        with mock.patch.object(mod._mode_binding, "HERE", Path(root)):   # W7B-R1-2: the study folder (the module
            self.driver = self._build(mod, login)                         # drive.py reads) is the scratch repository
        self.repo = mod.TakeRepo(runtime=self.box, record_files=self.driver.record_files,
                                 secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [], root=root,
                                 repo=root, on_published=self.driver.published)

    def _build(self, mod, login, root=None):
        root = self.root if root is None else root
        return mod.walk_driver(
            runtime=self.box, root=str(root), config_parent=str(self.cfg_parent), spec_for=self.spec_for,
            sidecar_for=self.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(tbi.SCRATCH / "proxy.conf"),
                conf_target="/etc/squid/x.conf", command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(tbi.SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"}, login_file=str(login),
            counters_for=lambda take: {"oom_kill": 0, "pids_max": 0}, pin_for=self.pin_for,
            design_for=self.design_for, project_for=lambda row: self.project, identity_for=self.identity_for,
            secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [], uid_map=tbi.UID_MAP,
            budget_s=600, finalize_wait_s=tbi.CAP_S, poll_s=tbi.POLL_S, clock=self.clock, sleep=self.clock.sleep,
            ownership=tbi.FakeOwnership(self.box), settings_guard=tbi.FakeSettingsGuard(),
            machine_gate=lambda: [])

    def pin_for(self, row):
        return batch.expected_pin(row, self.table)

    def design_for(self, row, run_tree):
        return self.ct.design_view(row, pin=self.pin_for(row), run_tree=run_tree, constants=self.constants)

    def identity_for(self, row):
        return {"session_id": self.sid, "row": 0, "row_commit": tcb.COMMIT, "source": self.source,
                "fixture": fixture_record(row), "gars_tree_sha": self.ct.GARS_TREE_SHA}

    def spec_for(self, row, cfg):
        return rt.TakeSpec(image=tbi.IMAGE, run_tree=str(self.tree), config_dir=cfg, network=tbi.PLACEHOLDER_NET,
                           memory_reservation=512 * 2 ** 20, memory=3 * 512 * 2 ** 20, cpus="2", pids_limit=256)

    def sidecar_for(self, row, ev):
        tree = str(self.tree)
        # The sidecar's accepted launch (0b6f60f9; its fake inspect is test_box_integration's, fixed in 5f1b33ee).
        expect = {"user": sc.BOOT_USER, "network_mode": "none", "cap_drop": ["ALL"],
                  "cap_add": list(sc.BOOT_INSPECT_CAPABILITIES), "security_opt": ["no-new-privileges"],
                  "privileged": False, "image": tbi.SIDECAR_IMAGE, "cmd": tbi.sidecar_cmd(tree), "entrypoint": [],
                  "pid_mode": "", "mounts": [{"source": tree, "destination": tree, "rw": False},
                                             {"source": ev, "destination": sc.EVIDENCE_MOUNT, "rw": True}]}
        return rt.SidecarLaunch(
            create_argv=("docker", "create", "--network", "none", "--label", "ev=" + ev, "--label", "tree=" + tree,
                         "side-image"),
            start_argv_for=lambda i: ["docker", "start", i],
            ctl_argv_for=lambda i, c, label=None: ["docker", "exec", i, "python3", "-I", "-B", "/opt/w/sidecar.py",
                                                   "ctl", c] + ([label] if label else []),
            rm_argv_for=lambda i: ["docker", "rm", "--force", i], expect=expect)

    def run(self):
        """One take through batch.Batch (register, launch, drive, remove, route, commit): its committed outcomes."""
        with tbi.spying(self.spy), tbi.planned(self.row):
            b = batch.Batch(self.driver, self.repo, tbi.Window(), table=self.table, serial=True)
            return b.run([self.row])


def take_dir(w) -> Path:
    return Path(w.root) / "takes" / w.row["slot"] / "1"


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("W1-strict")
def w1_strict(mod, p):
    out = tbi.missing_api(mod, p, "walk_driver", "WalkDriver")
    if out:
        return out
    if "strict_script" in inspect.signature(mod.walk_driver).parameters:
        out.append(f"{p}: walk_driver takes a strict_script")
    with world() as ct, tbi.scratch_repo() as root:
        w = Wired(mod, ct, root)
        if type(w.driver) is not mod.WalkDriver or w.driver.strict_script is not True:
            out.append(f"{p}: walk_driver built {type(w.driver).__name__} with strict_script "
                       f"{w.driver.strict_script!r}")
        for value in (False, None, 1):
            try:
                w.driver.strict_script = value
                if w.driver.strict_script is not True:
                    out.append(f"{p}: setting strict_script to {value!r} relaxed the walk driver")
                else:
                    out.append(f"{p}: setting strict_script to {value!r} was accepted silently")
            except mod.DriveRefused:
                pass
        try:
            mod.WalkDriver(strict_script=False)
            out.append(f"{p}: WalkDriver accepted strict_script=False")
        except TypeError:
            pass
        steps = w.driver.script_for(w.row)
        if not steps or not all(isinstance(s, dict) and isinstance(s.get("n"), int) for s in steps):
            out.append(f"{p}: the walk driver's script is not steps: {[type(s).__name__ for s in steps]}")
        w.driver.script_for = lambda row: ["a bare operator line"]          # a mis-wired script on the walk road
        # W9 (lane w9-cp6, K1-launch): the walk driver launches only a registered, planned take, so the row is
        # registered first, through the ledger's own door, against the same frozen rows the launch reads
        with tbi.spying(w.spy), tbi.planned(w.row):
            takes.commit_registration(w.row, 1, root=w.root, repo=w.root, pre={"rows": [w.row]})
            cid = w.driver.launch(w.row)
            try:
                w.driver.drive(w.row, cid)
                out.append(f"{p}: the walk driver sent a bare operator line")
            except mod.DriveRefused as e:
                if "bare line" not in str(e):
                    out.append(f"{p}: the walk driver refused for another reason: {str(e)[:120]}")
            except Exception as e:  # noqa: BLE001
                out.append(f"{p}: the walk driver raised {type(e).__name__} on a bare line: {str(e)[:120]}")
            w.driver.remove(cid)
        if w.box.turn_argv:
            out.append(f"{p}: {len(w.box.turn_argv)} turn(s) were sent before the bare line was refused")
    return out


@guarded("W2-folder")
def w2_folder(mod, p):
    out = tbi.missing_api(mod, p, "take_folder_in", "TAKES_DIR")
    if out:
        return out
    import mode_binding as mb
    if mod.TAKES_DIR != mb.TAKES_DIR or tuple(mb.TAKE_ROOTS) != (mb.TAKES_DIR,):
        out.append(f"{p}: the driver writes takes under {mod.TAKES_DIR!r} and mode_binding reads {mb.TAKE_ROOTS!r}")
    root = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
    fold = mod.take_folder_in(root)
    first = fold({"slot": "s-abc"})
    if first != str(root / mb.TAKES_DIR / "s-abc" / "1"):
        out.append(f"{p}: the first take folder is {first}")
    os.makedirs(first)
    second = fold({"slot": "s-abc"})
    if second != str(root / mb.TAKES_DIR / "s-abc" / "2"):
        out.append(f"{p}: the second attempt's folder is {second}")
    for bad in ("../s", "a/b", "", ".", None):
        try:
            fold({"slot": bad})
            out.append(f"{p}: the slot {bad!r} was accepted")
        except mod.DriveRefused:
            pass
    with world() as ct, tbi.scratch_repo() as r:
        w = Wired(mod, ct, r)
        got = w.driver.take_folder(w.row)
        if got != str(Path(r).resolve() / mb.TAKES_DIR / w.row["slot"] / "1"):
            out.append(f"{p}: the walk driver's take folder is {got}")
    return out


class NamedAdapter(tdl.LoopAdapter):
    """A LoopAdapter whose own name is given (the stub's, or none at all)."""

    def __init__(self, name, *a, **kw):
        super().__init__(*a, **kw)
        if name is None:
            self.__dict__["name"] = None
        else:
            self.name = name


@guarded("W3-identity")
def w3_identity(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver")
    if out:
        return out
    from box.stub_agents import agents as stubs
    for name, harness, refused in ((stubs.StubAgent.name, "claude-code", True), (None, "claude-code", True),
                                   (stubs.StubAgent.name, stubs.StubAgent.name, False)):
        with tbi.scratch_repo() as root:
            rig = tbi.Rig(mod, root)
            made = []

            def adapter_for(r, take, name=name, rig=rig):
                made.append(NamedAdapter(name, rig.box, take, [{"text": "x"}]))
                return made[-1]
            rig.driver.adapter_for = adapter_for
            r = tbi.row(1)
            r["agent"] = dict(r["agent"], harness=harness)
            if harness != "claude-code":
                rig.driver.pin_for = lambda row: {"harness": harness, "model": tbi.MODEL, "permission_mode": "stub",
                                                  "version": tbi.PROFILE["version"]}
            with tbi.spying(rig.spy):
                cid = rig.driver.launch(r)
                try:
                    rig.driver.drive(r, cid)
                    raised = None
                except Exception as e:  # noqa: BLE001 - read below by its type
                    raised = e
                rig.driver.remove(cid)
            take = rig.take()
            with open(os.path.join(take.evidence_dir, "ledger.jsonl"), encoding="utf-8") as fh:
                first = json.loads(fh.readline())
            if refused:
                if raised is None or type(raised).__name__ != "AdapterIdentityRefused":
                    out.append(f"{p}: an adapter named {name!r} under a {harness} row was not refused: {raised!r}")
                if made and (made[0].lines or made[0]._turns):
                    out.append(f"{p}: an adapter named {name!r} under a {harness} row was started")
            else:
                if raised is not None and type(raised).__name__ == "AdapterIdentityRefused":
                    out.append(f"{p}: a stub adapter under its own row was refused: {raised}")
                if first.get("agent", {}).get("harness") != stubs.StubAgent.name:
                    out.append(f"{p}: a stub take's evidence names {first.get('agent')}")
    return out


def committed(root: Path) -> list:
    got = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "--name-only", "HEAD"], capture_output=True,
                         text=True, check=True)
    return got.stdout.splitlines()


RECORDS = ("driver-ledger.json", "environment.json", "transcript.jsonl", "scrub.json", "operator-check.json",
           "launch.json", "preflight.json", "postflight.json", "teardown.json", "turn-1.jsonl")


@guarded("E1-take")
def e1_take(mod, p):
    out = tbi.missing_api(mod, p, "walk_driver", "take_folder_in")
    if out:
        return out
    import mode_binding as mb
    with world() as ct, tbi.scratch_repo() as root:
        w = Wired(mod, ct, root)
        got = w.run()
        o = got[0] if got else {}
        if o.get("state") != labels4.GRADED:
            return [f"{p}: the take was {o.get('state')!r}: {str(o.get('reason'))[:300]} "
                    f"{(o.get('records') or {}).get('checker_reasons')}"]
        folder = take_dir(w)
        rel = folder.relative_to(root).as_posix()
        files = committed(root)
        for name in RECORDS:
            if f"{rel}/{name}" not in files:
                out.append(f"{p}: {name} is not committed under {rel}")
        if f"{rel}/{mod.EVIDENCE_DIR}/ledger.jsonl" not in files:
            out.append(f"{p}: the evidence ledger is not committed under {rel}")
        if out:
            return out
        led = json.loads((folder / "driver-ledger.json").read_text())
        n = len(w.design_for(w.row, str(w.tree)).script)
        if (led["outcome"] != "complete" or led["cross_check"] != [] or led["agent"]["harness"] != "claude-code"
                or [t["n"] for t in led["turns"]] != list(range(1, n + 1)) or led["source"] != w.source):
            out.append(f"{p}: the ledger reads {led['outcome']!r}, cross-check {led['cross_check']}, turns "
                       f"{[t['n'] for t in led['turns']]}")
        if (led.get("finalize_wait_s"), led.get("poll_s")) != (tbi.CAP_S, tbi.POLL_S):     # BOOTSTRAP B4
            out.append(f"{p}: the ledger records cap {led.get('finalize_wait_s')!r} and poll {led.get('poll_s')!r}, "
                       f"not the driver's {tbi.CAP_S} and {tbi.POLL_S}")
        if tbi.EMAIL in (folder / "transcript.jsonl").read_text():
            out.append(f"{p}: the session copy still carries the account email")
        if json.loads((folder / "operator-check.json").read_text()) is None:
            out.append(f"{p}: operator-check.json is empty")
        rows = mb.rows(base=root, table=w.table)
        if len(rows) != 1 or rows[0]["problems"] or rows[0]["recorded"] != BYPASS:
            out.append(f"{p}: mode_binding read {[(r['attempt'], r['recorded'], r['problems']) for r in rows]}")
    return out


@guarded("E2-tree")
def e2_tree(mod, p):
    out = tbi.missing_api(mod, p, "walk_driver", "take_folder_in")
    if out:
        return out
    with world() as ct, tbi.scratch_repo() as root:
        w = Wired(mod, ct, root, opened_in="/work/elsewhere")
        got = w.run()
        if not got:
            return [f"{p}: no outcome was committed"]
        for o in got:                       # harness-error re-runs once in the same slot (the plan's cap)
            reasons = (o.get("records") or {}).get("checker_reasons") or []
            if o.get("state") != labels4.HARNESS_ERROR or "readers-disagree" not in reasons:
                out.append(f"{p}: a session that opened outside the driver's run tree was {o.get('state')!r} "
                           f"(attempt {o.get('attempt')}) with {reasons}")
    return out


@guarded("W4-root")
def w4_root(mod, p):
    """W7B-R1-2: walk_driver writes take records only under the study folder mode_binding --check reads; any other
    root is refused (a gate reading an empty folder would pass having graded nothing)."""
    out = tbi.missing_api(mod, p, "walk_driver")
    if out:
        return out
    import mode_binding as mb
    with world() as ct, tbi.scratch_repo() as root:
        w = Wired(mod, ct, root)                       # built with mode_binding.HERE at the scratch repository
        login = tbi.SCRATCH / f"login-{root.name}"
        for other in (tbi.SCRATCH, root / "takes", Path(tempfile.mkdtemp(dir=tbi.SCRATCH))):
            try:
                with mock.patch.object(mod._mode_binding, "HERE", Path(root)):
                    w._build(mod, login, root=other)
                out.append(f"{p}: walk_driver accepted the root {other}, which mode_binding does not read")
            except mod.DriveRefused:
                pass
        try:
            w._build(mod, login)                        # the real HERE, and the scratch root: refused too
            out.append(f"{p}: walk_driver accepted a root other than the real study folder {mb.HERE}")
        except mod.DriveRefused:
            pass
    return out


def constructions(sources: dict) -> list:
    """W7B-R1-1: every place non-test code builds a driver other than the walk driver, by AST: a call of TakeDriver
    (by name or attribute), or a class deriving from TakeDriver other than WalkDriver."""
    import ast
    out = []
    for path, src in sorted(sources.items()):
        for node in ast.walk(ast.parse(src, filename=path)):
            if isinstance(node, ast.Call):
                f = node.func
                name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
                if name == "TakeDriver":
                    out.append(f"{path}:{node.lineno} constructs TakeDriver")
            elif isinstance(node, ast.ClassDef) and node.name != "WalkDriver":
                for b in node.bases:
                    bn = b.id if isinstance(b, ast.Name) else b.attr if isinstance(b, ast.Attribute) else None
                    if bn == "TakeDriver":
                        out.append(f"{path}:{node.lineno} class {node.name} derives from TakeDriver")
    return out


def production_sources() -> dict:
    """Every non-test .py under evals/gap-study-4 (tests/ excluded), by its path relative to the study folder."""
    return {f.relative_to(HERE).as_posix(): f.read_text(encoding="utf-8") for f in sorted(HERE.rglob("*.py"))
            if "tests" not in f.relative_to(HERE).parts and "__pycache__" not in f.parts}


@guarded("W5-one-road")
def w5_one_road(sources, p):
    """W7B-R1-1: walk_driver (WalkDriver) is the only driver non-test code builds."""
    if "drive.py" not in sources or "class WalkDriver(TakeDriver)" not in sources["drive.py"]:
        return [f"{p}: the scan did not read drive.py's WalkDriver"]
    return [f"{p}: {x}" for x in constructions(sources)]


# BOOTSTRAP (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026): every checker constant now holds its ruled,
# sourced value (tests/test_checker_constants.py binds each to its source), so none is PENDING; superseding the list of
# six PENDING paths this check held until then. A constant set back to PENDING, or a key outside the block, is red.
PENDING_PATHS: list = []
KNOWN_VALUES = ("budgets", "driver_constants", "driver_outcome_shapes", "environment_record",
                "harness_delivered_user_records", "run_location", "system_under_test")


# CP5's registration, typed once from plans/gap-study-round-4/cp5-values-draft-2026-10-14.md (Javier: "CP5: all as
# recommended", 14 Oct 2026); test_routing's TestCP5ArmAProfiles binds the same values to the take-a lock.
CP5_PROFILES = {"claude-code": {m: {"permission_mode": "bypassPermissions", "version": "2.1.296"}
                                for m in ("claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-4-5-20251001")},
                # round 17 B7 (R4 of RULINGS-codex2-signin-road-2026-10-18.md; moved by glitch-b5's ruling M)
                "codex": {m: {"permission_mode": "bypass", "version": "0.162.1"} for m in ("gpt-6.1-sol", "gpt-6-luna")},
                "gemini": {m: {"permission_mode": "yolo", "version": "0.64.0"}
                           for m in ("gemini-3.8-flash", "gemini-3.5-flash-lite")}}


@guarded("W6-pending")
def w6_pending(world_, p):
    """W7B-R1-6, superseded by the bootstrap ruling (15 Oct 2026): no checker constant is PENDING in production and
    the block holds exactly KNOWN_VALUES (each bound to its source by tests/test_checker_constants.py), and
    routing.json's pin_profiles are exactly CP5's registration (Javier, 14 Oct 2026: arm A's three profiles) and R4's
    O and G profiles (round 17 B7, glitch-b5's ruling M), nothing else: the end-to-end take's values are test data
    only."""
    ct, table = world_
    out = []
    got = sorted(x for k, v in ct.CHECKER_CONSTANTS.items() for x in ct._pending_paths(v, k))
    if got != PENDING_PATHS:
        out.append(f"{p}: the PENDING checker constants are {got}, not {PENDING_PATHS}")
    others = sorted(set(ct.CHECKER_CONSTANTS) - set(KNOWN_VALUES) - {x.split('.')[0] for x in got})
    if others:
        out.append(f"{p}: checker constants {others} are outside the ruled block")
    if table.get("pin_profiles") != CP5_PROFILES:
        out.append(f"{p}: routing.json's pin_profiles are {table.get('pin_profiles')!r}, not CP5's and R4's registration")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestTheWalkWiring(unittest.TestCase):
    def test_w1_the_walk_driver_is_strict_and_stays_strict(self):
        self.assertEqual(w1_strict(tbi.drive), [])

    def test_w2_the_take_folder_is_one_name(self):
        self.assertEqual(w2_folder(tbi.drive), [])

    def test_w3_the_adapter_is_the_rows_harness(self):
        self.assertEqual(w3_identity(tbi.drive), [])

    def test_w4_the_root_is_the_folder_the_gate_reads(self):
        self.assertEqual(w4_root(tbi.drive), [])

    def test_w5_the_walk_driver_is_the_only_driver_built(self):
        self.assertEqual(w5_one_road(production_sources()), [])

    def test_w5_witness_an_added_construction_is_red(self):
        """Rule B for W5: the bound check is green on the tree, and red by its own line when one module builds a
        TakeDriver or derives from it."""
        real = production_sources()
        self.assertEqual(w5_one_road(real), [])
        for name, extra in (("added-construction", "\n\ndef _another():\n    return TakeDriver(**{})\n"),
                            ("added-subclass", "\n\nclass LooseDriver(TakeDriver):\n    pass\n")):
            got = w5_one_road(dict(real, **{"batch.py": real["batch.py"] + extra}))
            own = [x for x in got if x.startswith("W5-one-road:")]
            print(f"\nWITNESS {name}: {'red' if own else 'NOT KILLED'} by W5-one-road ({len(own)} own, 0 collateral, "
                  f"{len([x for x in got if x.startswith('ERROR')])} errors)", end=" ", file=sys.stderr, flush=True)
            self.assertTrue(own and not [x for x in got if x.startswith("ERROR")], f"{name}: {got}")


class TestTheEndToEndTake(unittest.TestCase):
    def test_e1_one_take_is_graded_and_leaves_every_record(self):
        self.assertEqual(e1_take(tbi.drive), [])

    def test_e2_a_session_outside_its_run_tree_is_never_graded(self):
        self.assertEqual(e2_tree(tbi.drive), [])

    def test_the_production_constants_are_the_ruled_block(self):
        import check_take as ct
        import routing
        self.assertEqual(w6_pending((ct, routing.load_table())), [])

    def test_w6_witness_a_filled_constant_or_pin_is_red(self):
        """Rule B for W6 (W7B-R1-6; bootstrap): one constant set back to PENDING, or one routing pin profile, is red
        by its own line."""
        import check_take as ct
        import routing
        table = routing.load_table()
        self.assertEqual(w6_pending((ct, table)), [])
        filled = copy.deepcopy(ct.CHECKER_CONSTANTS)
        filled["run_location"] = ct.PENDING
        cases = (("constant-pending", types.SimpleNamespace(CHECKER_CONSTANTS=filled, _pending_paths=ct._pending_paths),
                  table),
                 ("pin-filled", ct, dict(table, pin_profiles={"claude-code": {"m": {"permission_mode": "x",
                                                                                     "version": "0"}}})),
                 # round 17 B7 (ruling M): one of R4's vendor profiles drifted, the rest of the table as committed
                 ("vendor-pin-drift", ct, dict(table, pin_profiles=dict(table["pin_profiles"], codex=dict(
                     table["pin_profiles"]["codex"], **{"gpt-6-luna": {"permission_mode": "bypass",
                                                                         "version": "0.162.0"}})))))
        for name, mod, t in cases:
            got = w6_pending((mod, t))
            own = [x for x in got if x.startswith("W6-pending:")]
            print(f"\nWITNESS {name}: {'red' if own else 'NOT KILLED'} by W6-pending ({len(own)} own, 0 collateral, "
                  f"0 errors)", end=" ", file=sys.stderr, flush=True)
            self.assertTrue(own, f"{name}: {got}")


class TestSysPath(unittest.TestCase):
    def test_the_module_puts_sys_path_back(self):
        """Binding W6M1 (tests/test_wave6_bindings.py) for this module: it imports check_take.py through drive.py,
        so its tearDownModule must leave sys.path exactly as it found it (test_round4 runs every module in one
        process); the wave 6 probe, in a fresh interpreter."""
        import test_wave6_bindings as w6
        with mock.patch.object(subprocess, "run", tbi._REAL["run"]), \
                mock.patch.object(subprocess, "Popen", tbi._REAL["Popen"]):   # the probe's one fresh interpreter
            seen = w6.probe("test_walk_wiring")
        self.assertNotIn(str(w6.EVALS), [x for x in seen["after"] if x not in seen["before"]], "W6M1.evals-left")
        self.assertEqual(seen["after"], seen["before"], "W6M1.restored")


# name: (edits, the module the edits apply to, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    "walk-not-strict": ((("    def strict_script(self) -> bool:\n        return True",
                          "    def strict_script(self) -> bool:\n        return False"),), "drive", w1_strict,
                        "W1-strict"),
    "walk-strict-settable": ((("        if value is not True:\n            raise DriveRefused(\"the walk driver's script "
                               "is strict",
                               "        if False:\n            raise DriveRefused(\"the walk driver's script is strict"),),
                             "drive", w1_strict, "W1-strict"),
    "folder-renamed": ((("TAKES_DIR = _mode_binding.TAKES_DIR", "TAKES_DIR = \"records\""),), "drive", w2_folder,
                       "W2-folder"),
    "identity-unchecked": ((("                    adapter_identity_problems(adapter, row)   # W7B (W6B-R1-3): the "
                             "row's harness is the adapter's\n", ""),), "drive", w3_identity, "W3-identity"),
    "folder-renamed-end-to-end": ((("TAKES_DIR = _mode_binding.TAKES_DIR", "TAKES_DIR = \"records\""),), "drive",
                                  e1_take, "E1-take"),
    "top-level-harness-end-to-end": ((("    harness = ledger_harness(ledger)           # W7B: the driver ledger's own "
                                       "shape, agent.harness",
                                       "    harness = ledger.get(\"harness\") or \"?\""),), "mode_binding", e1_take,
                                     "E1-take"),
    "root-unchecked": ((("    if Path(root).resolve() != Path(_mode_binding.HERE).resolve():    # W7B-R1-2: the root the gate reads",
                         "    if False:"),), "drive", w4_root, "W4-root"),
    "tree-unchecked-end-to-end": ((("    problems += design_tree_problems(path, design)               # W7B "
                                    "(Q-w6i-5)\n", ""),), "check_take", e2_tree, "E2-tree"),
}
WITNESS_LOG: list = []


def compiled(name: str, edits: tuple) -> types.ModuleType:
    """`name`.py with `edits`, compiled in memory as its own module; check_take and mode_binding are swapped into
    sys.modules for the check's run (drive.py imports them by name), drive.py is test_box_integration's compiler."""
    if name == "drive":
        return tbi.witness_module(edits)
    real = sys.modules[name]
    with open(real.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise tbi.WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = real.__file__
    exec(compile(src, real.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


class TestWitnesses(unittest.TestCase):
    """Each witness is killed only by its bound check's own assertion, with the bound check green first; an ERROR
    line, a raise or an unperformed edit is never a kill."""

    def kill(self, name):
        edits, target, check, prefix = WITNESSES[name]
        self.assertEqual(check(tbi.drive), [], f"{name}: the bound check is not green")
        if target == "drive":
            got = check(compiled("drive", edits))
        else:
            import check_take  # noqa: F401 - loaded so the swap below has a module to stand in for
            import mode_binding  # noqa: F401
            witness = compiled(target, edits)
            if target == "check_take":
                witness.CHECK_HOME = sys.modules["check_take"].CHECK_HOME
            with mock.patch.dict(sys.modules, {target: witness}):
                got = check(tbi.drive)
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_walk_not_strict(self):
        self.kill("walk-not-strict")

    def test_witness_walk_strict_settable(self):
        self.kill("walk-strict-settable")

    def test_witness_folder_renamed(self):
        self.kill("folder-renamed")

    def test_witness_identity_unchecked(self):
        self.kill("identity-unchecked")

    def test_witness_folder_renamed_end_to_end(self):
        self.kill("folder-renamed-end-to-end")

    def test_witness_top_level_harness_end_to_end(self):
        self.kill("top-level-harness-end-to-end")

    def test_witness_root_unchecked(self):
        self.kill("root-unchecked")

    def test_witness_tree_unchecked_end_to_end(self):
        self.kill("tree-unchecked-end-to-end")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted([
            "walk-not-strict", "walk-strict-settable", "folder-renamed", "identity-unchecked",
            "folder-renamed-end-to-end", "top-level-harness-end-to-end", "tree-unchecked-end-to-end",
            "root-unchecked"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
