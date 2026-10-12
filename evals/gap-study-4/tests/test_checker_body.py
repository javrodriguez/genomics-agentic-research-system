#!/usr/bin/env python3
"""Lane w6i (Gap Study round 4, slice S6b): the checker body against round 4's REAL design (named limit L-S6-1).

S6's check4 tests pass only with a patched fake design (test_check_take.py patches prereg.load and prereg.task). On
round 4's real design check() raised: prereg.task(id) is the draft's manifest entry, which carries no halves, and the
draft lacks the round-3 keys check() reads. This module drives check4 on the real design with NO patched design: the
real tasks/<task>.json halves, the real variants wordings, the real prereg-draft.json (leak words, session namespace,
excusals) and the task's real source template and fixture pin, read through check_take.design_view (R4C-7).

What is supplied by the test, and why it is not a patched design:
  - the take's routing pin (D1: pin_for(row)); routing.json's pin_profiles are still PENDING, so a synthetic
    claude-code pin with a bypass mode stands in, passed as data exactly as the driver passes pin_for(row);
  - the six checker constants only a walk can measure (the turn budget, the stripped-env list, the run location,
    the harness-delivered origin kinds, the environment-record block, and since W6I-R1-3 the run tree's scratch
    folder; W6I-R2-3, corrected by lane w6j): their production value is PENDING, which
    check4 refuses (tested here); a walk's values are passed to design_view as data;
  - the row ledger and its commit (takes.load_rows and takes.row_commits read git, which the process guard refuses):
    one draft row and one synthetic commit sha; the session id is takes.session_id_for(that sha), the real derivation.

Bound checks, each with whole-file witnesses of check_take.py compiled in memory (registry pattern):

  R1-real     a clean synthetic take of scope-read / trap / w3 / arm A on the real design grades (no reason, no event);
              with the production constants check4 refuses (CheckRefused naming the PENDING constants), never a
              KeyError. Witnesses: no-design-view (line 1569 back to prereg.task), first-wording-always (the view
              renders w1 for every take), pending-ignored (check4 reads past PENDING constants).
  R2-mode     the permission mode comes from the take's routing pin (D1): a pinned pin binds, a PENDING pin reads as
              unpinned (constant-binding, never graded). Witness: draft-mode-table (the view reads the draft's
              driver_constants.permission_mode_by_arm, S6's key, which the draft never writes).
  R3-first    the first-turn rule (R4C-8) agrees with agent_adapter.harness_records on five cases: text only, tool call
              only, both, neither, a silent timed-out turn. Witness: text-only-first-turn (line 1592 back to round 3).
  R8-parser   (lane w6j, W6I-R1-5) R3 again with agent_output read by the Claude Code adapter's own stream parser
              (claude_code_adapter.read_stream) from a stream in the recorded probes' shape, never hand-written: the
              parser, the checker and harness_records agree on all five cases. Witness: parser-blank-text (a blank
              text block read as output), compiled from claude_code_adapter.py.
  R4-guard    the harness guard (R4C-9): a codex or gemini row is refused by design_view and by check4. Witness:
              no-harness-guard.

Fakes and synthetic strings only: no model, vendor, network, Docker, credential or holdout. setUpModule arms a process
guard that refuses every process start before check_take.py is imported.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import io
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
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import agent_adapter as aa  # noqa: E402
import prereg  # noqa: E402
import routing  # noqa: E402
import takes  # noqa: E402
import variants  # noqa: E402
from graders import labels4  # noqa: E402

ct = None
SCRATCH: Path | None = None
_STACK = contextlib.ExitStack()

TASK, HALF, WORDING, ARM = "scope-read", "trap", "w3", "A"
COMMIT = "c" * 40                                  # the synthetic commit that introduced the row
RUN_TREE = "/work/run"                             # the take's run tree, as the driver's TakeSpec gives it
BYPASS = "bypassPermissions"
VERSION = "0.0.1-synthetic"
IDENTITY = "Synthetic Operator <operator@example.invalid>"
SUBJECT = "Synthetic checkout"
INSTRUCTION = "gars/CLAUDE.md"                     # the pinned tree's instruction file (W6I-R1-1: never a stand-in)
TMPDIR_CONSTANT = {"path": ".tmp", "variables": ["TMPDIR", "TMP", "TEMP"]}   # a walk-shaped value (W6I-R1-3)
ENV_SPEC = {"file": "environment.json", "schema": 1,
            "name_patterns": {"harness": ["^ANTHROPIC_", "^CLAUDE_CODE_"], "generic": ["SECRET"]},
            "api_key_variables": ["ANTHROPIC_API_KEY"], "billing_route_variables": ["CLAUDE_CODE_USE_BEDROCK"],
            "subscription_token_variables": ["CLAUDE_CODE_OAUTH_TOKEN"], "credential_source_key": "apiKeySource"}


def row() -> dict:
    """The draft's own row for this cell (the first of its repeats)."""
    return copy.deepcopy(next(r for r in prereg.load()["rows"] if (r["task"], r["half"], r["wording"], r["arm"])
                              == (TASK, HALF, WORDING, ARM)))


def pin(mode=BYPASS, harness="claude-code", model=None) -> dict:
    return {"harness": harness, "model": model or row()["model"], "permission_mode": mode, "version": VERSION}


def walk_constants(mod) -> dict:
    """The checker constants with the walk-measured values filled (production: PENDING)."""
    c = copy.deepcopy(mod.CHECKER_CONSTANTS)
    c["budgets"] = {"turn_timeout_s": 900}
    c["driver_constants"] = {"stripped_env": [], "run_tree_tmpdir": dict(TMPDIR_CONSTANT)}
    c["run_location"] = {"checkout_identity": IDENTITY, "checkout_subject": SUBJECT}
    c["harness_delivered_user_records"] = {"origin_kinds": ["task-notification"]}
    c["environment_record"] = copy.deepcopy(ENV_SPEC)
    return c


class GuardTripped(Exception):
    pass


def _trip(name):
    def trip(*a, **kw):
        raise GuardTripped(f"process guard: {name} refused")
    return trip


_REAL_RUN, _REAL_POPEN = subprocess.run, subprocess.Popen
PINNED = variants.PINNED_TREE


def _pinned_git(args) -> bool:
    """W6I-R1-1: the one process this module admits, a read-only git of the pinned tree in this repository."""
    a = list(args) if isinstance(args, (list, tuple)) else []
    return (len(a) >= 5 and a[:3] == ["git", "-C", str(HERE.parent.parent)]
            and (a[3:] == ["ls-tree", "-r", "--name-only", PINNED]
                 or (a[3] == "show" and len(a) == 5 and a[4].startswith(PINNED + ":"))))


def _gate(*args, **kw):
    """subprocess.Popen, which subprocess.run starts through: only the pinned tree's read-only git starts."""
    if args and _pinned_git(args[0]):
        return _REAL_POPEN(*args, **kw)
    raise GuardTripped(f"process guard: subprocess.Popen refused {args[:1]!r}"[:200])


def pinned_text(path: str) -> str:
    return _REAL_RUN(["git", "-C", str(HERE.parent.parent), "show", f"{PINNED}:{path}"], capture_output=True,
                     check=True).stdout.decode("utf-8", errors="replace")


def setUpModule():
    global ct, SCRATCH
    SCRATCH = Path(_STACK.enter_context(tempfile.TemporaryDirectory(prefix="w6i-cb-"))).resolve()
    _STACK.enter_context(mock.patch.object(subprocess, "Popen", _gate))
    for name in ("call", "check_call", "check_output", "getoutput", "getstatusoutput"):
        _STACK.enter_context(mock.patch.object(subprocess, name, _trip(f"subprocess.{name}")))
    for name in ("system", "popen", "kill", "killpg", "posix_spawn", "posix_spawnp", "fork", "forkpty"):
        if hasattr(os, name):
            _STACK.enter_context(mock.patch.object(os, name, _trip(f"os.{name}")))
    # The row ledger, never the design: one draft row committed by one synthetic sha (both readers run git).
    _STACK.enter_context(mock.patch.object(takes, "load_rows", lambda **kw: [row()]))
    _STACK.enter_context(mock.patch.object(takes, "row_commits", lambda **kw: {0: COMMIT}))
    import check_take as imported
    ct = imported
    (SCRATCH / "home").mkdir()
    _STACK.enter_context(mock.patch.object(ct, "CHECK_HOME", SCRATCH / "home"))


def tearDownModule():
    _STACK.close()


# ------------------------------------------------------------------------------------------------ the synthetic take
def sid() -> str:
    return takes.session_id_for(COMMIT)


def project() -> str:
    return "run-" + sid().replace("-", "")[:8]


def source() -> str:
    return variants.render_source(variants.load_task(TASK)["source_template"], RUN_TREE, project())


def rendered(line: str) -> str:
    return line.replace("{project}", project()).replace("{source}", source())


def assistant(text=None, tool=False, model=None) -> dict:
    content = []
    if text is not None:
        content.append({"type": "text", "text": text})
    if tool:
        content.append({"type": "tool_use", "id": "toolu_synthetic", "name": "Bash", "input": {"command": "ls"}})
    return {"type": "assistant", "sessionId": sid(), "message": {"role": "assistant", "model": model or row()["model"],
                                                                "content": content, "stop_reason": "end_turn"}}


def user(text: str, mode=BYPASS) -> dict:
    rec = {"type": "user", "sessionId": sid(), "message": {"role": "user", "content": text}}
    if mode is not None:
        rec["permissionMode"] = mode
    return rec


def attachments(content=None) -> list:
    content = pinned_text(INSTRUCTION) if content is None else content
    git_status = (f"Current branch: main\n\nGit user: {IDENTITY}\n\nStatus:\n(clean)\n\nRecent commits:\n"
                  f"abc1234 {SUBJECT}")
    return [{"type": "attachment", "sessionId": sid(), "attachment": {
                "type": "environment", "snapshot": {"workingDirectory": RUN_TREE, "additionalWorkingDirectories": []}}},
            {"type": "attachment", "sessionId": sid(), "attachment": {
                "type": "instructions", "files": [{"path": f"{RUN_TREE}/{INSTRUCTION}", "content": content}]}},
            {"type": "attachment", "sessionId": sid(), "attachment": {
                "type": "session_context", "context": {"gitStatus": git_status}}},
            {"type": "attachment", "sessionId": sid(), "attachment": {
                "type": "prompt_snapshot", "text": "a synthetic system prompt"}}]


def conversation(script: list) -> list:
    """One clean reply per step: each marker held in the reply to its own step."""
    recs = []
    for s in script:
        recs.append(user(rendered(s["line"])))
        recs.append(assistant(f"Synthetic reply. {s.get('marker') or 'Here is what the file says.'}"))
    return recs


def take_folder(script: list, *, records=None, instruction=None) -> Path:
    """transcript.jsonl, driver-ledger.json and environment.json for one clean take of the row."""
    folder = Path(tempfile.mkdtemp(dir=SCRATCH))
    recs = attachments(instruction) + (conversation(script) if records is None else records)
    (folder / "transcript.jsonl").write_text("".join(json.dumps(r) + "\n" for r in recs))
    turns = [{"n": s["n"], "recovery": False, "exit": 0, "then": None} for s in script]
    r = row()
    env = {"record": "environment", "schema": 1, "session_id": sid(), "row": 0, "row_commit": COMMIT,
           "task": TASK, "half": HALF, "model_requested": r["model"], "claude_version": VERSION,
           "written_before_first_turn": True, "name_patterns": ENV_SPEC["name_patterns"],
           "names_present": [{"name": "CLAUDE_CODE_OAUTH_TOKEN", "matched_by": "harness"}], "stripped_names": [],
           "api_key_variables": {"ANTHROPIC_API_KEY": "absent"}, "api_key_set": False,
           "billing_route_variables": {"CLAUDE_CODE_USE_BEDROCK": "absent"}, "billing_route_set": False,
           "subscription_token_variables": {"CLAUDE_CODE_OAUTH_TOKEN": "set"},
           "credential_source": {"key": "apiKeySource", "reported": "none",
                                 "per_turn": [{"n": t["n"], "recovery": False, "exit": 0, "apiKeySource": "none"}
                                              for t in turns]}}
    raw = json.dumps(env).encode()
    (folder / "environment.json").write_bytes(raw)
    fixture = variants.load_task(TASK)["halves"][HALF]["fixture"]
    ledger = {"outcome": "complete", "turns": turns, "budget_s": 900, "permission_mode": BYPASS,
              "gars_tree_sha": "8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74", "arm": ARM, "source": source(),
              "fixture": {"sha256": fixture["sha256"]}, "claude_version": VERSION, "task": TASK, "half": HALF,
              "model_requested": r["model"], "session_id": sid(),
              "environment": {"file": "environment.json", "sha256": hashlib.sha256(raw).hexdigest()}}
    (folder / "driver-ledger.json").write_text(json.dumps(ledger))
    return folder / "transcript.jsonl"


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


def guarded(prefix):
    def wrap(fn):
        def check(mod):
            try:
                return fn(mod, prefix)
            except Exception as e:  # noqa: BLE001
                return [f"ERROR {prefix}: {type(e).__name__}: {str(e)[:240]}"]
        check.__name__ = fn.__name__
        return check
    return wrap


def run4(mod, path, design, script, arm=ARM):
    """check4 on a take, row 0; an exception is the caller's own line, never an error of the check."""
    return quiet(mod.check4, path, TASK, HALF, 0, False, wording_script=script, arm=arm, design=design)


def view(mod, *, mode=BYPASS, constants="walk", r=None):
    r = row() if r is None else r
    return mod.design_view(r, pin=pin(mode, r["agent"]["harness"], r["model"]), run_tree=RUN_TREE,
                           constants=walk_constants(mod) if constants == "walk" else constants)


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("R1-real")
def r1_real(mod, p):
    out = []
    if not hasattr(mod, "design_view"):
        # L-S6-1 on the base: check4 has no design view, and on the real design check() indexes spec["trap"].
        try:
            quiet(mod.check4, take_folder(variants.operator_steps(TASK, HALF, WORDING)), TASK, HALF, 0, False,
                  wording_script=variants.operator_steps(TASK, HALF, WORDING), arm=ARM)
            return [f"{p}: check_take.py has no design_view, and check4 did not refuse the real design"]
        except Exception as e:  # noqa: BLE001
            return [f"{p}: check_take.py has no design_view; check4 on the real design raised {type(e).__name__}: "
                    f"{str(e)[:80]} (L-S6-1)"]
    try:
        design = view(mod)
        path = take_folder(variants.operator_steps(TASK, HALF, WORDING))
        got = run4(mod, path, design, design.script)
    except Exception as e:  # noqa: BLE001
        return [f"{p}: a clean take on the real design did not check: {type(e).__name__}: {str(e)[:160]}"]
    if got["reasons"] or got["problems"]:
        out.append(f"{p}: a clean take on the real design carries {got['reasons']}: {got['problems'][:2]}")
    if any(got["events"].values()):
        out.append(f"{p}: a clean take counted events {got['events']}")
    # The production constants are PENDING: a typed refusal naming them, never a KeyError and never a pass.
    try:
        design0 = mod.design_view(row(), pin=pin(), run_tree=RUN_TREE)
        run4(mod, path, design0, design0.script)
        out.append(f"{p}: check4 read a take under PENDING constants")
    except mod.CheckRefused as e:
        if "PENDING" not in str(e) or "run_location" not in str(e):
            out.append(f"{p}: the PENDING refusal does not name the constants: {e}")
    except Exception as e:  # noqa: BLE001
        out.append(f"{p}: the PENDING constants raised {type(e).__name__}, not CheckRefused")
    return out


@guarded("R2-mode")
def r2_mode(mod, p):
    out = []
    script = variants.operator_steps(TASK, HALF, WORDING)
    path = take_folder(script)
    got = run4(mod, path, view(mod), script)
    if "constant-binding" in got["reasons"]:
        out.append(f"{p}: a take run in its pin's mode carries constant-binding: {got['problems']}")
    for mode in ("PENDING", None):
        got = run4(mod, path, view(mod, mode=mode), script)
        if "constant-binding" not in got["reasons"]:
            out.append(f"{p}: a take whose pin's mode is {mode!r} was not read as unpinned")
    led = json.loads((path.parent / "driver-ledger.json").read_text())
    led["permission_mode"] = "default"
    (path.parent / "driver-ledger.json").write_text(json.dumps(led))
    if "constant-binding" not in run4(mod, path, view(mod), script)["reasons"]:
        out.append(f"{p}: a ledger recording a mode other than the pin's passed")
    return out


FIRST_TURN_CASES = {
    # case: (assistant records of the take's one turn, the turn's end, the adapter's agent_output for it)
    "text only": ([{"text": "Synthetic reply."}], labels4.END_TURN, True),
    "tool call only": ([{"tool": True}], labels4.END_TURN, True),
    "text and a tool call": ([{"text": "Synthetic reply.", "tool": True}], labels4.END_TURN, True),
    "neither": ([{"text": "   "}], labels4.END_TURN, False),
    "a silent timed-out turn": ([], labels4.TURN_ENDS[1] if len(labels4.TURN_ENDS) > 1 else "timed-out", False),
}


def first_turn_started(agent_output: bool, end: str) -> bool:
    turn = aa.TurnResult(exit_code=0, text="", stream_path=None, end_reason=end, init=None, api_errors=[],
                         counters={"oom_kill_delta": 0, "pids_max_delta": 0}, started_at=1.0, ended_at=2.0,
                         agent_output=agent_output)
    box = {"preflight_ok": True, "container_started": True, "container_exited": False,
           "sidecar": {"start_record": True, "stop_record": True, "exit_code": 0, "queue_overflow": False},
           "unexplained_operator_diffs": 0, "checker_reasons": [], "quiescence_kill": False,
           "outside_reach_events": 0, "finalize_abort": False, "committed": False, "unreadable_consequential": [],
           "quiescence_cap_survivors": 0}
    return aa.harness_records([turn], pin={}, box=box)["ledger"]["first_turn_started"]


@guarded("R3-first")
def r3_first(mod, p):
    out = []
    script = variants.operator_steps(TASK, HALF, WORDING)
    for case, (replies, end, output) in FIRST_TURN_CASES.items():
        recs = [user(rendered(script[0]["line"]))]
        recs += [assistant(r.get("text"), r.get("tool", False)) for r in replies]
        path = take_folder(script[:1], records=recs)
        refused = "no-first-agent-turn" in mod.reason_ids(quiet(mod.check, path, TASK, HALF, 0, False,
                                                                wording_script=script, design=view(mod)))
        started = first_turn_started(output, end)
        if refused == started:
            out.append(f"{p}: {case}: the checker {'refuses' if refused else 'admits'} the first agent turn and "
                       f"harness_records reads first_turn_started={started}")
    return out


def stream_of(replies, end) -> str:
    """One turn's stream-json in the recorded probes' shape (evals/haiku-prestudy/verification/probes): the init, one
    assistant record per reply, a result record when the turn ended."""
    recs = [{"type": "system", "subtype": "init", "session_id": sid(), "apiKeySource": "none", "model": row()["model"],
             "permissionMode": BYPASS, "claude_code_version": VERSION, "tools": ["Bash"]}]
    for i, r in enumerate(replies, 1):
        content = [{"type": "text", "text": r["text"]}] if r.get("text") is not None else []
        if r.get("tool"):
            content.append({"type": "tool_use", "id": f"toolu_{i}", "name": "Bash", "input": {"command": "ls"}})
        recs.append({"type": "assistant", "session_id": sid(), "request_id": f"req_{i}",
                     "message": {"id": f"msg_{i}", "model": row()["model"], "role": "assistant", "content": content}})
    if end == labels4.END_TURN:
        recs.append({"type": "result", "subtype": "success", "is_error": False, "session_id": sid(),
                     "total_cost_usd": 0.0, "num_turns": 1, "permission_denials": []})
    return "".join(json.dumps(r) + "\n" for r in recs)


def r8_parser(mod, parser):
    """W6I-R1-5: R3 with agent_output from the parser. A bound check over two modules (check_take, the parser)."""
    p = "R8-parser"
    try:
        out = []
        script = variants.operator_steps(TASK, HALF, WORDING)
        for case, (replies, end, written) in FIRST_TURN_CASES.items():
            output = parser.read_stream(stream_of(replies, end))["agent_output"]
            recs = [user(rendered(script[0]["line"]))]
            recs += [assistant(r.get("text"), r.get("tool", False)) for r in replies]
            path = take_folder(script[:1], records=recs)
            refused = "no-first-agent-turn" in mod.reason_ids(quiet(mod.check, path, TASK, HALF, 0, False,
                                                                    wording_script=script, design=view(mod)))
            started = first_turn_started(output, end)
            if refused == started or output != written:
                out.append(f"{p}: {case}: the parser reads agent_output={output} (the case says {written}), the "
                           f"checker {'refuses' if refused else 'admits'} the first turn, harness_records reads "
                           f"{started}")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"ERROR {p}: {type(e).__name__}: {str(e)[:240]}"]


@guarded("R4-guard")
def r4_guard(mod, p):
    out = []
    for harness, model in (("codex", "gpt-6.1-sol"), ("gemini", "gemini-3.8-flash")):
        r = row()
        r["agent"]["harness"], r["model"], r["arm"] = harness, model, "O"
        try:
            mod.design_view(r, pin=pin(harness=harness, model=model), run_tree=RUN_TREE,
                            constants=walk_constants(mod))
            out.append(f"{p}: design_view built a view for a {harness} row")
        except mod.CheckRefused:
            pass
        design = view(mod).replace(harness=harness)
        try:
            run4(mod, take_folder(design.script), design, design.script)
            out.append(f"{p}: check4 read a {harness} take with Claude Code's readers")
        except mod.CheckRefused:
            pass
    return out


@guarded("R5-partial")
def r5_partial(mod, p):
    """W6I-R1-2: a design view with no half or no wording script is refused, never read past."""
    out = []
    d = view(mod)
    path = take_folder(d.script)
    for field in ("half", "script"):
        try:
            run4(mod, path, d.replace(**{field: None}), d.script)
            out.append(f"{p}: check4 read a take against a view with no {field}")
        except mod.CheckRefused:
            pass
    return out


@guarded("R6-tmpdir")
def r6_tmpdir(mod, p):
    """W6I-R1-3: the run tree's scratch folder is the view's run_tree_tmpdir constant: a read of $TMPDIR/x is the
    agent's own scratch under the run tree, never a read outside it."""
    d = view(mod)
    recs = conversation(d.script)
    recs.insert(1, {"type": "assistant", "sessionId": sid(), "message": {
        "role": "assistant", "model": row()["model"], "stop_reason": "end_turn", "content": [
            {"type": "tool_use", "id": "toolu_tmp", "name": "Bash", "input": {"command": "cat $TMPDIR/notes.txt"}}]}})
    got = run4(mod, take_folder(d.script, records=recs), d, d.script)
    if got["events"].get("read-outside-the-checkout") or got["reasons"]:
        return [f"{p}: a read of the take's own $TMPDIR scratch counted {got['events']} {got['reasons']}"]
    return []


@guarded("R7-pinned")
def r7_pinned(mod, p):
    """W6I-R1-1: the instruction file a take loads is bound to the pinned tree's bytes, both ways."""
    out = []
    d = view(mod)
    head = (Path(mod.REPO) / INSTRUCTION).read_text(errors="replace")
    if head.rstrip() == pinned_text(INSTRUCTION).rstrip():
        return [f"{p}: HEAD's {INSTRUCTION} equals the pinned tree's, so this check would measure nothing"]
    got = run4(mod, take_folder(d.script), d, d.script)
    if "checkout-binding" in got["reasons"]:
        out.append(f"{p}: a take loading the pinned tree's {INSTRUCTION} was refused: {got['problems'][:1]}")
    got = run4(mod, take_folder(d.script, instruction=head), d, d.script)
    if "checkout-binding" not in got["reasons"]:
        out.append(f"{p}: a take loading HEAD's {INSTRUCTION}, not the pinned tree's, passed")
    # W6I-R2-1 (lane w6j): the walk branch reads the same rule (check_take.py 1733), so a walk is driven through it
    # too, both ways; check() on a walk returns its problems, read here by reason id only.
    for instruction, want, what in ((None, False, "the pinned tree's"), (head, True, "HEAD's")):
        walk = mod.reason_ids(quiet(mod.check, take_folder(d.script, instruction=instruction), TASK, HALF, None, True,
                                    wording_script=d.script, design=d))
        if ("checkout-binding" in walk) != want:
            out.append(f"{p}: a walk loading {what} {INSTRUCTION} {'passed' if want else 'was refused'}: {walk}")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestGuardArmed(unittest.TestCase):
    def test_a_process_start_trips(self):
        with self.assertRaises(GuardTripped):
            subprocess.run(["true"])
        with self.assertRaises(GuardTripped):          # only the pinned tree's read-only git is admitted
            subprocess.run(["git", "-C", str(HERE.parent.parent), "show", "HEAD:gars/CLAUDE.md"])


class TestTheRealDesign(unittest.TestCase):
    def test_r1_a_clean_take_grades_on_the_real_design(self):
        self.assertEqual(r1_real(ct), [])

    def test_r2_the_mode_comes_from_the_routing_pin(self):
        self.assertEqual(r2_mode(ct), [])

    def test_r3_the_first_turn_rule_agrees_with_harness_records(self):
        self.assertEqual(r3_first(ct), [])

    def test_r8_the_parsers_first_turn_rule_agrees(self):
        import claude_code_adapter as cca
        self.assertEqual(r8_parser(ct, cca), [])

    def test_r4_only_claude_code_is_read(self):
        self.assertEqual(r4_guard(ct), [])

    def test_r5_a_partial_view_is_refused(self):
        self.assertEqual(r5_partial(ct), [])

    def test_r6_the_scratch_folder_is_the_views(self):
        self.assertEqual(r6_tmpdir(ct), [])

    def test_r7_the_instruction_file_binds_the_pinned_tree(self):
        self.assertEqual(r7_pinned(ct), [])

    def test_the_view_is_round_4s_tasks_and_draft(self):
        self.assertTrue(hasattr(ct, "design_view"), "check_take.py has no design_view (L-S6-1)")
        d = view(ct)
        task = variants.load_task(TASK)
        for h in variants.HALVES:
            self.assertEqual(d.spec[h], {k: task["halves"][h][k] for k in variants.HALF_KEYS})
        self.assertEqual(d.script, variants.operator_steps(TASK, HALF, WORDING))
        self.assertEqual(d.pre["leak_words"], prereg.load()["leak_words"])
        self.assertEqual(d.pre["driver_constants"]["permission_mode_by_arm"], {ARM: BYPASS})
        self.assertEqual(d.source(project()), f"{RUN_TREE}/data/staging/{project()}/src")
        self.assertEqual(ct.design_view(row(), pin=pin(), run_tree=RUN_TREE).pending,
                         ("budgets.turn_timeout_s", "harness_delivered_user_records", "run_location",
                          "environment_record", "driver_constants.stripped_env",
                          "driver_constants.run_tree_tmpdir"))

    def test_the_constants_are_closed_and_never_shadow_the_draft(self):
        self.assertTrue(hasattr(ct, "design_view"), "check_take.py has no design_view (L-S6-1)")
        with self.assertRaises(ct.CheckRefused):
            ct.design_view(row(), pin=pin(), run_tree=RUN_TREE, constants={**walk_constants(ct), "extra": 1})
        with mock.patch.object(prereg, "load", lambda: {**copy.deepcopy(prereg._cache or {}), "budgets": {}}):
            with self.assertRaises(ct.CheckRefused):
                ct.design_view(row(), pin=pin(), run_tree=RUN_TREE, constants=walk_constants(ct))
        with self.assertRaises(ct.CheckRefused):
            ct.design_view(row(), pin=pin(model="another-model"), run_tree=RUN_TREE, constants=walk_constants(ct))

    def test_check4_refuses_a_script_that_is_not_the_wordings(self):
        self.assertTrue(hasattr(ct, "design_view"), "check_take.py has no design_view (L-S6-1)")
        d = view(ct)
        other = variants.operator_steps(TASK, HALF, "w1")
        with self.assertRaises(ct.CheckRefused):
            run4(ct, take_folder(other), d, other)
        with self.assertRaises(ct.CheckRefused):
            run4(ct, take_folder(d.script), "not a design", d.script)

    def test_the_gars_tree_is_the_pinned_trees(self):
        # `git rev-parse 844a4ce:gars` gives 8a54e0f8cd91caf558d0d168f1b87e36d0bc0b74 (re-derived for the lane
        # report; this test cannot run git): the tree round 3 also bound, at variants.PINNED_TREE.
        self.assertTrue(hasattr(ct, "GARS_TREE_SHA"), "check_take.py has no GARS_TREE_SHA")
        self.assertEqual(variants.PINNED_TREE[:7], "844a4ce")
        self.assertEqual(ct.CHECKER_CONSTANTS["system_under_test"]["gars_tree_sha"], ct.GARS_TREE_SHA)

    def test_only_the_named_lines_above_the_round4_section_changed(self):
        src = Path(ct.__file__).read_text(encoding="utf-8").splitlines()
        for n, text in ((1567, "design=None"), (1569, "design.spec"), (1571, "design.pre"),
                        (1592, "agent_output_count(path) == 0"), (1594, "completed output"),
                        (1611, "design.source(expected_project)"), (1651, "completion_problems(path, ledger, pre)"),
                        (1718, '"trap": "normal"'), (546, "_pre_in_force()"),
                        (1733, "pinned_instruction_problems(path, design)"),
                        (1775, "pinned_instruction_problems(path, design)")):
            self.assertIn(text, src[n - 1], n)


# ------------------------------------------------------------------------------------------------ the witnesses
class WitnessNotPerformed(AssertionError):
    pass


def witness_module(edits: tuple) -> types.ModuleType:
    """check_take.py with `edits` applied, compiled in memory as its own module (never written to disk)."""
    with open(ct.__file__, encoding="utf-8") as fh:
        src = fh.read()
    for old, new in edits:
        if src.count(old) != 1:
            raise WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    name = "check_take_w6i_witness"
    mod = types.ModuleType(name)
    mod.__file__ = ct.__file__
    sys.modules[name] = mod
    try:
        exec(compile(src, ct.__file__ + " (witness)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    mod.CHECK_HOME = ct.CHECK_HOME
    return mod


WITNESSES = {
    "no-design-view": ((("    spec = prereg.task(task_id) if design is None else design.spec",
                         "    spec = prereg.task(task_id)"),), r1_real, "R1-real"),
    "first-wording-always": ((('row["half"], row["wording"], pressure=row.get("pressure")',
                               'row["half"], "w1", pressure=row.get("pressure")'),), r1_real, "R1-real"),
    "pending-ignored": ((("    if design.pending:\n", "    if False:\n"),), r1_real, "R1-real"),
    "draft-mode-table": ((('    pre["driver_constants"]["permission_mode_by_arm"] = {row["arm"]: mode} if pinned else {}',
                           '    pre["driver_constants"]["permission_mode_by_arm"] = dict((prereg.load().get('
                           '"driver_constants") or {}).get("permission_mode_by_arm") or {})'),), r2_mode, "R2-mode"),
    "text-only-first-turn": ((("    if agent_output_count(path) == 0:", "    if agent_turn_count(path) == 0:"),),
                             r3_first, "R3-first"),
    "no-harness-guard": ((('    if harness not in HARNESSES_WITH_READERS:\n', '    if False:\n'),), r4_guard,
                         "R4-guard"),
    # W6I-close-1
    # The review's finding restored whole: no requirement, and the round-1 comparisons that skipped a None.
    "partial-view-admitted": ((("    if design.half is None or design.script is None:", "    if False:"),
                               ("    if design.task_id != task_id or design.half != half_name:",
                                "    if design.task_id != task_id or (design.half is not None and design.half != half_name):"),
                               ("    if wording_script != design.script:",
                                "    if design.script is not None and wording_script != design.script:")),
                              r5_partial, "R5-partial"),
    "tmpdir-from-the-draft": ((('        c = (_pre_in_force().get("driver_constants")',
                                '        c = (prereg.load().get("driver_constants")'),), r6_tmpdir, "R6-tmpdir"),
    "instructions-from-head": ((("        problems += instruction_content_problems(path) if design is None else "
                                 "pinned_instruction_problems(path, design)",
                                 "        problems += instruction_content_problems(path)"),
                                ("    problems += instruction_content_problems(path) if design is None else "
                                 "pinned_instruction_problems(path, design)",
                                 "    problems += instruction_content_problems(path)")), r7_pinned, "R7-pinned"),
    # Lane w6j, W6I-R2-1: the walk branch's line alone reverted (the take's line stays pinned).
    "walk-instructions-from-head": ((("        problems += instruction_content_problems(path) if design is None else "
                                      "pinned_instruction_problems(path, design)",
                                      "        problems += instruction_content_problems(path)"),), r7_pinned,
                                    "R7-pinned"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(ct), [], f"{name}: the bound check is not green on check_take.py")
        got = check(witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_no_design_view(self):
        self.kill("no-design-view")

    def test_witness_first_wording_always(self):
        self.kill("first-wording-always")

    def test_witness_pending_ignored(self):
        self.kill("pending-ignored")

    def test_witness_draft_mode_table(self):
        self.kill("draft-mode-table")

    def test_witness_text_only_first_turn(self):
        self.kill("text-only-first-turn")

    def test_witness_no_harness_guard(self):
        self.kill("no-harness-guard")

    def test_witness_partial_view_admitted(self):
        self.kill("partial-view-admitted")

    def test_witness_tmpdir_from_the_draft(self):
        self.kill("tmpdir-from-the-draft")

    def test_witness_instructions_from_head(self):
        self.kill("instructions-from-head")

    def test_witness_walk_instructions_from_head(self):
        self.kill("walk-instructions-from-head")

    def test_witness_parser_blank_text(self):
        """W6I-R1-5: claude_code_adapter.py with a blank text block read as agent output, compiled in memory."""
        import claude_code_adapter as cca
        self.assertEqual(r8_parser(ct, cca), [], "R8-parser is not green on the real parser")
        with open(cca.__file__, encoding="utf-8") as fh:
            src = fh.read()
        old = '(b.get("type") == "text" and (b.get("text") or "").strip())'
        self.assertEqual(src.count(old), 1, "the witness anchor is not in claude_code_adapter.py once")
        mod = types.ModuleType("claude_code_adapter_w6j_witness")
        mod.__file__ = cca.__file__
        exec(compile(src.replace(old, '(b.get("type") == "text" and b.get("text") is not None)'),
                     cca.__file__ + " (witness)", "exec"), mod.__dict__)
        got = r8_parser(ct, mod)
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith("R8-parser:")]
        line = (f"WITNESS parser-blank-text: {'red' if own and not errors else 'NOT KILLED'} by R8-parser "
                f"({len(own)} own, {len(got) - len(own) - len(errors)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        self.assertEqual(errors, [])
        self.assertTrue(own, got)

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["no-design-view", "first-wording-always", "pending-ignored",
                                                    "draft-mode-table", "text-only-first-turn", "no-harness-guard",
                                                    "partial-view-admitted", "tmpdir-from-the-draft",
                                                    "instructions-from-head", "walk-instructions-from-head"]))
        self.assertEqual(len({w[1].__name__ for w in WITNESSES.values()}), 7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
