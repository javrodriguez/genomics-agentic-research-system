#!/usr/bin/env python3
"""Lane vendor-admission T4 P2: the vendor check body (lane-reports/vendor-T4-PLAN.md v4, sections 1 and 9, ruled
READY by glitch-b5 on Sat 17 Oct 2026, on Javier's typed word "vendor-t4: yes"; round 9's rulings).

Every case is a synthetic take of test_checker_body's draft row (scope-read/trap/w3) made a codex row (arm O) or a
gemini row (arm G), its view built by the production check_take.design_view, its folder written by
tests/vendor_check_fixtures.py from that row's own lines and replies (envelopes, ledger, turn streams, launch
journals, retained native snapshots), and read by check_take.vendor_check (plan section 1a) and
check_take.vendor_round4_problems (section 1b).

  P2-clean    a clean take of either vendor carries exactly the PENDING refusals of its harness's
              VENDOR_PENDING_ROWS keys (every key but codex T-8:file-change, which fires only on a file_change item),
              each raised through vendor_pending: no vendor take passes while a PENDING row stands.
  P2-cases    one F3 case per reason, each adding exactly its reason(s) to the clean take's refusals: the CLI's own
              user record differing from the envelopes, or holding an extra turn (readers-disagree; a differing gemini
              stream reads readers-disagree, never transcript-unreadable); no agent output; no CLI session id; a
              script that is a reference; a stop with no wait point, a stop at a held marker, a line off the script,
              a reply missing its marker; the fixture hash and the source; a leak word; a launch argv the adapter never
              writes, a missing launch journal and one naming another turn's stream (inherited-context); the ledger's
              sent line differing, and a last snapshot the ledger does not bind; the email marker in a published file (one
              event for any number of hits); a turn that did not end, an outcome off the driver's shapes and a ledger
              row off the script (outcome-binding); reach into evals/, the home folder and the temp folder, and a path
              under the session's own run tree admitted; the project name; the ledger row, the commit-derived and the
              walk session id; the turn budget; a turn stream line no parser read; a nested-agent switch; codex's
              session working directory and run tree (T-11, T-4) and a file_change item (T-8, PENDING).
  P2-keys     VP-keys holds as equality on the live source (test_vendor_check), and vendor_pending is called with
              literal harness and key only.
  P2-witness  check_take.py compiled in memory with each guard dropped, each PENDING refusal deleted (one mutant per
              call site, read from the AST), a PENDING refusal moved under an event id, the envelope read twice, the
              view run before the readers, the run tree not handed to the reach, the home and temp legs dropped and the
              email counted per instance: each goes red on its own case.

Fakes and synthetic strings only, inside test_checker_body's process guard (only the pinned tree's read-only git
starts): no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import ast
import collections
import contextlib
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_checker_body as tcb  # noqa: E402
import vendor_check_fixtures as vcf  # noqa: E402

TASK, HALF = tcb.TASK, tcb.HALF
# harness: (model, arm, the pin's permission mode: the adapter's MODE_FLAGS key) - TEST DATA, D8's arms and ids
VENDORS = {"codex": ("gpt-6.1-sol", "O", "bypass"), "gemini": ("gemini-3.8-flash", "G", "yolo")}
WALK_ID = "w-0001"
# The home folder the checker reads every case under: outside the temp roots (tcb's scratch sits under the temp folder),
# so the home and temp legs each fire alone.
HOME = "/synthetic-home"
NO_READER = "no vendor reader yet"


def setUpModule():
    tcb.setUpModule()


def tearDownModule():
    tcb.tearDownModule()


def design_for(mod, harness, run_tree=tcb.RUN_TREE):
    """The production design view of the draft row made a `harness` row (test_vendor_script's road)."""
    model, arm, mode = VENDORS[harness]
    r = tcb.row()
    r["agent"]["harness"], r["model"], r["arm"] = harness, model, arm
    return mod.design_view(r, pin=tcb.pin(mode, harness, model), run_tree=run_tree, constants=tcb.walk_constants(mod))


class Take:
    """One synthetic vendor take of the row, before it is written: a case edits these fields, then its parts, then
    its folder. `call` holds vendor_check's keywords a case may change (row_index, walk_id, wording_script)."""

    def __init__(self, mod, harness, design, sid=None):
        self.mod, self.harness, self.design = mod, harness, design
        self.model, self.arm, self.mode = VENDORS[harness]
        self.sid = sid or tcb.sid()
        self.run_tree = design.run_tree
        self.journal_cwd = design.run_tree
        project = mod.neutral_name(self.sid)
        source = design.source(project)
        self.lines = [mod.render(s["line"], project, source) for s in design.script]
        self.replies = [f"Synthetic reply. {s.get('marker') or 'Here is what the file says.'}" for s in design.script]
        fixture = design.spec[HALF]["fixture"]
        self.ledger = {"outcome": "complete", "budget_s": 900, "permission_mode": self.mode, "finalize_wait_s": 180,
                       "poll_s": 3, "gars_tree_sha": mod.GARS_TREE_SHA, "arm": self.arm, "source": source,
                       "fixture": {"sha256": fixture["sha256"]}, "task": TASK, "half": HALF,
                       "model_requested": self.model, "session_id": self.sid}
        self.turns = None                  # None: one ledger row per line, numbered by the script's steps
        self.call = {"row_index": 0, "walk_id": None, "wording_script": design.script}
        self.parts = None

    def build(self, parts_edit=None, folder_edit=None):
        if self.harness == "codex":
            self.parts = vcf.codex_parts(self.lines, self.replies, cwd=self.run_tree, model=self.model)
        else:
            self.parts = vcf.gemini_parts(self.lines, self.replies, model=self.model)
        if parts_edit:
            parts_edit(self.parts)
        turns = self.turns if self.turns is not None else [
            {"n": s["n"], "recovery": False, "exit": 0, "then": None, "sent": line}
            for s, line in zip(self.design.script, self.parts["lines"])]
        ledger = dict(self.ledger, turns=turns)
        folder = Path(tempfile.mkdtemp(dir=tcb.SCRATCH))
        path = vcf.write(folder, self.harness, self.parts, sid=self.sid, ledger=ledger, run_tree=self.journal_cwd,
                         mode=self.mode)
        if folder_edit:
            folder_edit(path)
        return path

    def problems(self, path):
        with mock.patch.object(self.mod, "CHECK_HOME", Path(HOME)):
            got = self.mod.vendor_check(path, TASK, HALF, self.call["row_index"],
                                        wording_script=self.call["wording_script"], design=self.design, arm=self.arm,
                                        walk_id=self.call["walk_id"])
            return got + self.mod.vendor_round4_problems(path, self.design)


def tags(problems) -> collections.Counter:
    return collections.Counter(p.split("] ")[0][1:] for p in problems)


def pending_lines(mod, harness) -> list:
    """The clean take's refusals: one per PENDING key of the harness, codex's file_change leg aside."""
    return sorted(f"[{row['reason']}] {NO_READER} ({key})" for key, row in mod.VENDOR_PENDING_ROWS[harness].items()
                  if key != "T-8:file-change")


# ---- the F3 cases: (name, harnesses, edit(take) -> (parts_edit, folder_edit), the reasons it adds) -----------------
def _stream_records(parts, k):
    return parts["streams"][k]


def codex_rollout_user(parts, k, text):
    for t, pay in parts["rollout"][k]:
        if (pay.get("item") or {}).get("type") == "UserMessage":
            pay["item"]["content"][0]["text"] = text


def codex_extra_turn(parts):
    extra = copy.deepcopy(parts["rollout"][1])
    for t, pay in extra:
        for key in ("turn_id",):
            if pay.get(key) == "t1":
                pay[key] = "t9"
        if (pay.get("item") or {}).get("type") == "UserMessage":
            pay["item"]["content"][0]["text"] = "an extra line"
    parts["rollout"][len(parts["rollout"])] += extra


def gemini_extra_interaction(parts):
    last = len(parts["native"])
    parts["native"][last] += [{"id": "u9", "type": "user", "content": [{"text": "an extra line"}]},
                              {"id": "b9", "type": "gemini", "model": parts["model"], "content": "Done."}]


def no_agent_output(parts):
    for k, recs in parts["streams"].items():
        keep = ("thread.started", "turn.started", "turn.completed", "init", "result")
        parts["streams"][k] = [r for r in recs if r["type"] in keep or (r["type"] == "message" and r["role"] == "user")]


def no_session_id(parts):
    for k, recs in parts["streams"].items():
        parts["streams"][k] = [r for r in recs if r["type"] not in ("thread.started", "init")]


def turn_not_ended(parts):
    last = parts["streams"][len(parts["streams"])]
    for r in last:
        if r["type"] == "turn.completed":
            r.clear()
            r.update({"type": "turn.failed", "error": {"message": "synthetic failure"}})
        elif r["type"] == "result":
            r.update(status="error", error={"type": "synthetic", "message": "synthetic failure"})


def tool_command(command):
    """Every tool call of turn 2 becomes a shell command `command` (codex command_execution; gemini
    run_shell_command)."""
    def edit(parts):
        for r in parts["streams"][2]:
            item = r.get("item") or {}
            if item.get("type") == "command_execution":
                item["command"] = command
            if r["type"] == "tool_use":
                r.update(tool_name="run_shell_command", parameters={"command": command})
    return edit


def extra_journal_option(path):
    j = path.parent / "turn-1.jsonl.launch.json"
    doc = json.loads(j.read_text())
    doc["argv"] = doc["argv"][:2] + ["--add-dir", "/elsewhere"] + doc["argv"][2:]
    j.write_text(json.dumps(doc))


def marker_in(where):
    note = __import__("scrub").NOTE

    def edit(parts):
        if "stream" in where:
            for r in parts["streams"][1]:
                if (r.get("item") or {}).get("type") == "agent_message":
                    r["item"]["text"] += f" {note}"
                if r["type"] == "tool_result":
                    r["output"] += f" {note}"
        if "snapshot" in where:
            key = "rollout" if "rollout" in parts else "native"
            if key == "rollout":
                for t, pay in parts["rollout"][2]:
                    if pay.get("type") == "function_call_output":
                        pay["output"] += f" {note}"
            else:
                parts["native"][2][1]["toolCalls"][0]["resultDisplay"] += f" {note}"
    return edit


def file_change(parts):
    parts["streams"][2].insert(-1, {"type": "item.completed", "item": {
        "id": "item_7", "type": "file_change", "changes": [{"path": "notes.txt", "kind": "update"}],
        "status": "completed"}})


def stopped(t):
    t.ledger["outcome"] = "stopped \u2014 wait-point marker not held"


def case_user_record_differs(t):
    if t.harness == "codex":
        return lambda p: codex_rollout_user(p, 2, "other"), None
    return lambda p: p["streams"][2][1].update(content="other"), None


def case_ledger_sent_differs(t):
    t.turns = [{"n": s["n"], "recovery": False, "exit": 0, "then": None, "sent": line if s["n"] != 2 else "other"}
               for s, line in zip(t.design.script, t.lines)]
    return None, None


def case_snapshot_unbound(t):
    def edit(path):
        led = path.parent / "driver-ledger.json"
        doc = json.loads(led.read_text())
        doc["native_snapshots"][-1]["sha256"] = "0" * 64
        led.write_text(json.dumps(doc))
    return None, edit


def case_snapshot_differs(t):
    return lambda p: p["native"][2][0]["content"][0].update(text="other"), None


def case_extra_turn(t):
    return (codex_extra_turn if t.harness == "codex" else gemini_extra_interaction), None


def case_stop_no_wait_point(t):
    stopped(t)
    return None, None


def case_stop_held_marker(t):
    stopped(t)
    t.lines.pop()
    t.replies.pop()
    return None, None


def case_line_off_script(t):
    t.lines[1] = "06"
    return None, None


def case_reply_without_marker(t):
    t.replies[0] = "Synthetic reply."
    return None, None


def case_fixture_hash(t):
    t.ledger["fixture"] = {"sha256": "0" * 64}
    return None, None


def case_source(t):
    t.ledger["source"] = "/elsewhere/src"
    return None, None


def case_leak(t):
    t.design = t.design.replace(pre=dict(t.design.pre, leak_words=["bulk"]))
    return None, None


def case_no_journal(t):
    return None, lambda path: (path.parent / "turn-2.jsonl.launch.json").unlink()


def case_journal_of_another_turn(t):
    def edit(path):
        j = path.parent / "turn-2.jsonl.launch.json"
        j.write_text(json.dumps(dict(json.loads(j.read_text()), stream="/synthetic/take/turn-1.jsonl")))
    return None, edit


def case_outcome_off_shapes(t):
    t.ledger["outcome"] = "invented"
    return None, None


def case_row_off_script(t):
    t.turns = [{"n": n, "recovery": False, "exit": 0, "then": None, "sent": line}
               for n, line in zip((1, 2, 9), t.lines)]
    return None, None


def case_no_project(t):
    t.lines[0] = "I'd like to begin a bulk RNA-seq project"
    return None, None


def case_no_row(t):
    t.call["row_index"] = 7
    return None, None


def case_take_without_row(t):
    t.call["row_index"] = None
    return None, None


def case_unbound(t):
    return None, None                                  # the case's own session id does the work (CASES' sid)


def case_walk_session(t):
    t.call.update(row_index=None, walk_id=WALK_ID)
    return None, None


def case_budget(t):
    t.ledger["budget_s"] = 899
    return None, None


def case_unread_stream(t):
    return None, lambda path: (path.parent / "turn-9.jsonl").write_text('{"type": "x"}\n')


def case_rollout_cwd(t):
    def edit(parts):
        for _, pay in parts["rollout"][2]:
            if "cwd" in pay and "approval_policy" in pay:
                pay["cwd"] = "/elsewhere"
    return edit, None


def case_journal_cwd(t):
    t.journal_cwd = "/elsewhere"
    return None, None


def edits(*pair):
    return lambda t: pair


# name: (harnesses, edit(take) -> (parts edit, folder edit), the reasons it adds, the take's session id or None)
CASES = {
    # readers-disagree, operator turns (T-3); a differing gemini stream reads readers-disagree, not unreadable
    "the CLI's user record differs from the envelopes": (("codex", "gemini"), case_user_record_differs,
                                                         {"readers-disagree": 1}, None),
    "the gemini snapshot's interaction differs from the envelopes": (("gemini",), case_snapshot_differs,
                                                                     {"readers-disagree": 1}, None),
    "the CLI's record holds an extra turn": (("codex", "gemini"), case_extra_turn, {"readers-disagree": 1}, None),
    "the ledger's sent line differs from the envelopes": (("codex", "gemini"), case_ledger_sent_differs,
                                                          {"readers-disagree": 1}, None),
    # the last retained snapshot the ledger does not bind: no reader of it stands (codex's cwd and run tree too)
    "a codex snapshot the ledger does not bind": (("codex",), case_snapshot_unbound,
                                                  {"transcript-unreadable": 2, "inherited-context": 1}, None),
    "a gemini snapshot the ledger does not bind": (("gemini",), case_snapshot_unbound, {"transcript-unreadable": 1},
                                                   None),
    # no-first-agent-turn (T-1); the replies' markers go with the output
    "no agent output": (("codex", "gemini"), edits(no_agent_output, None),
                        {"no-first-agent-turn": 1, "continued-past-unheld-marker": 2}, None),
    # no-session-id (T-2): bound_items refuses a stream without one, so the view refuses too
    "the CLI wrote no session id": (("codex", "gemini"), edits(no_session_id, None),
                                    {"no-session-id": 1, "transcript-unreadable": 1}, None),
    # the stop and marker family, operator-lines (T-7, T-6)
    "a stop at a line with no wait point": (("codex", "gemini"), case_stop_no_wait_point,
                                            {"stop-without-a-wait-point": 1}, None),
    "a stop at a held marker": (("codex", "gemini"), case_stop_held_marker, {"stop-at-held-marker": 1}, None),
    "an operator line off the script": (("codex", "gemini"), case_line_off_script, {"operator-lines": 2}, None),
    "a reply missing its step's marker": (("codex", "gemini"), case_reply_without_marker,
                                          {"continued-past-unheld-marker": 1}, None),
    # fixture-binding (T-24)
    "another fixture hash": (("codex", "gemini"), case_fixture_hash, {"fixture-binding": 1}, None),
    "another source": (("codex", "gemini"), case_source, {"fixture-binding": 1}, None),
    # leak-in-operator-turn (T-6)
    "a leak word in an operator line": (("codex", "gemini"), case_leak, {"leak-in-operator-turn": 1}, None),
    # inherited-context, the input-side legs (T-12:offered-context)
    "a launch argv the adapter never writes": (("codex", "gemini"), edits(None, extra_journal_option),
                                              {"inherited-context": 1}, None),
    "a turn with no launch journal": (("codex", "gemini"), case_no_journal, {"inherited-context": 1}, None),
    "a launch journal naming another turn's stream": (("codex", "gemini"), case_journal_of_another_turn,
                                                      {"inherited-context": 1}, None),
    # account-email (T-9): one event per take
    "the email marker in a turn stream": (("codex", "gemini"), edits(marker_in("stream"), None),
                                          {"account-email": 1}, None),
    "the email marker in two published files": (("codex", "gemini"), edits(marker_in("stream snapshot"), None),
                                                {"account-email": 1}, None),
    # outcome-binding (T-24)
    "a turn that did not end": (("codex", "gemini"), edits(turn_not_ended, None), {"outcome-binding": 1}, None),
    "an outcome off the driver's shapes": (("codex", "gemini"), case_outcome_off_shapes, {"outcome-binding": 1},
                                           None),
    "a ledger row off the script": (("codex", "gemini"), case_row_off_script, {"outcome-binding": 1}, None),
    # reach (T-8): the checkout, home and temp legs
    "a command reaching evals/": (("codex", "gemini"), edits(tool_command("cat evals/gap-study-4/prereg-draft.json"),
                                                             None), {"study-materials-reached": 1}, None),
    "a command reading the home folder": (("codex", "gemini"), lambda t: (tool_command(
        f"cat {HOME}/notes.txt"), None), {"read-outside-the-checkout": 1}, None),
    "a command reading the temp folder": (("codex", "gemini"), edits(tool_command("cat /tmp/other/notes.txt"), None),
                                          {"read-outside-the-checkout": 1}, None),
    # project-name (T-6): a first line without the project is off the script too
    "no operator line names the project": (("codex", "gemini"), case_no_project,
                                           {"project-name": 1, "operator-lines": 2}, None),
    # invocation and session-binding (T-24, and T-20's ledger leg)
    "no ledger row": (("codex", "gemini"), case_no_row, {"session-binding": 1}, None),
    "a take with no row": (("codex", "gemini"), case_take_without_row, {"invocation": 1}, None),
    "a session id that is not the row commit's": (("codex", "gemini"), case_unbound, {"session-binding": 1},
                                                  "other"),
    "a walk whose session id is not its walk's": (("codex", "gemini"), case_walk_session, {"session-binding": 2},
                                                  "other"),
    # constant-binding (T-24)
    "another turn budget": (("codex", "gemini"), case_budget, {"constant-binding": 1}, None),
    # transcript-unreadable (T-23): a stream in the folder no envelope binds, its line off the tables
    "a turn stream line no parser read": (("codex", "gemini"), case_unread_stream, {"transcript-unreadable": 1}, None),
    # nested-agent (T-21)
    "a nested agent's session switch": (("codex",), edits(tool_command("codex exec --ephemeral hi"), None),
                                        {"nested-agent": 1}, None),
    "a nested agent's store moved": (("codex", "gemini"), edits(tool_command("CODEX_HOME=/x codex exec hi"), None),
                                     {"nested-agent": 1}, None),
    # codex: the session's working directory (T-11), the run tree (T-4), and file_change (T-8, PENDING)
    "a rollout turn in another working directory": (("codex",), case_rollout_cwd,
                                                    {"inherited-context": 1, "readers-disagree": 1}, None),
    "a launch journal in another working folder": (("codex",), case_journal_cwd, {"readers-disagree": 3}, None),
    "a file_change item": (("codex",), edits(file_change, None), {"transcript-unreadable": 1}, None),
}
SID_OTHER = "00000000-0000-5000-8000-0000000000aa"


def run_case(mod, harness, name, design=None):
    """The case's problems on `mod`, and the clean take's."""
    design = design or design_for(mod, harness)
    clean = Take(mod, harness, design)
    clean_problems = clean.problems(clean.build())
    t = Take(mod, harness, design, sid=SID_OTHER if CASES[name][3] == "other" else None)
    parts_edit, folder_edit = CASES[name][1](t)
    return t.problems(t.build(parts_edit, folder_edit)), clean_problems


def case_problems(mod, names=None) -> list:
    """[] or each case that does not add exactly its reasons to the clean take's refusals, nothing removed."""
    out = []
    for name, (harnesses, _, want, _sid) in CASES.items():
        if names is not None and name not in names:
            continue
        for harness in harnesses:
            try:
                got, clean = run_case(mod, harness, name)
            except Exception as e:  # noqa: BLE001 - a traceback is itself a failure here
                out.append(f"{harness} {name}: raised {type(e).__name__}: {e}")
                continue
            added = tags(got) - tags(clean)
            removed = collections.Counter(clean) - collections.Counter(got)
            if added != collections.Counter(want) or removed:
                out.append(f"{harness} {name}: added {dict(added)}, removed {dict(removed)}, not {want}: "
                           f"{[p[:140] for p in got if p not in clean]}")
    return out


def clean_problems(mod) -> list:
    out = []
    for harness in VENDORS:
        try:
            t = Take(mod, harness, design_for(mod, harness))
            got = sorted(t.problems(t.build()))
        except Exception as e:  # noqa: BLE001
            out.append(f"{harness} clean take: raised {type(e).__name__}: {e}")
            continue
        if got != pending_lines(mod, harness):
            out.append(f"{harness} clean take: {got}, not the PENDING refusals {pending_lines(mod, harness)}")
    return out


def walk_problems(mod) -> list:
    """A clean walk (its session id walk_session_id(WALK_ID), no row) carries the PENDING refusals only."""
    out = []
    for harness in VENDORS:
        t = Take(mod, harness, design_for(mod, harness), sid=mod.walk_session_id(WALK_ID))
        t.ledger.update(row=None, row_commit=None)
        t.call.update(row_index=None, walk_id=WALK_ID)
        got = sorted(t.problems(t.build()))
        if got != pending_lines(mod, harness):
            out.append(f"{harness} clean walk: {got}")
    return out


def tree_admitted_problems(mod) -> list:
    """codex: a path under the session's own run tree, the tree under the home folder, is admitted by the home leg."""
    tree = f"{HOME}/run-tree"
    design = design_for(mod, "codex", run_tree=tree)
    t = Take(mod, "codex", design)
    got = t.problems(t.build(tool_command(f"cat {tree}/notes.txt")))
    extra = [p for p in got if p not in pending_lines(mod, "codex")]
    return [f"codex run tree under home: {extra}"] if extra else []


def script_reference_problems(mod) -> list:
    out = []
    for harness in VENDORS:
        t = Take(mod, harness, design_for(mod, harness))
        t.call["wording_script"] = "see tasks/scope-read.json"
        got = t.problems(t.build())
        if "script-not-a-list" not in tags(got):
            out.append(f"{harness}: a script that is a reference is not script-not-a-list: {got}")
    return out


class P2Clean(unittest.TestCase):
    def test_p2_clean_take_carries_exactly_its_pending_refusals(self):
        self.assertEqual(clean_problems(tcb.ct), [])

    def test_p2_clean_walk_carries_exactly_its_pending_refusals(self):
        self.assertEqual(walk_problems(tcb.ct), [])

    def test_p2_a_claude_code_design_is_refused(self):
        with self.assertRaises(tcb.ct.CheckRefused):
            tcb.ct.vendor_check(Path(tcb.SCRATCH) / "transcript.jsonl", TASK, HALF, 0, wording_script=[],
                                design=tcb.view(tcb.ct), arm="A")


class P2Cases(unittest.TestCase):
    def test_p2_each_case_adds_exactly_its_reasons(self):
        self.assertEqual(case_problems(tcb.ct), [])

    def test_p2_a_path_under_the_sessions_own_run_tree_is_admitted(self):
        self.assertEqual(tree_admitted_problems(tcb.ct), [])

    def test_p2_a_script_reference_is_script_not_a_list(self):
        self.assertEqual(script_reference_problems(tcb.ct), [])


class P2Keys(unittest.TestCase):
    def test_p2_every_pending_key_has_its_call_site(self):
        import test_vendor_check as tvc
        self.assertEqual(tvc.vp_keys_problems(tvc.SOURCE, tcb.ct.VENDOR_PENDING_ROWS), [])


# ---- the witnesses --------------------------------------------------------------------------------------------------
def pending_call_sites(source: str) -> list:
    """The source text of every vendor_pending(<harness>, <key>, None) call, with its harness: one mutant each."""
    out = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "vendor_pending":
            out.append((node.args[0].value, ast.get_source_segment(source, node)))
    return out


P2_WITNESSES = {
    "the CLI's user records not compared": (("    for name, got in readers.items():\n", "    for name, got in ():\n"),
                                           "the CLI's user record differs from the envelopes"),
    "the ledger's sent lines not compared": (("    if rows != sent:\n", "    if False:\n"),
                                            "the ledger's sent line differs from the envelopes"),
    "the snapshot's ledger digest unchecked": ((
        '    raw = _binding._regular_bytes(Path(path).parent / "session" / name)\n'
        '    if hashlib.sha256(raw).hexdigest() != snaps[-1].get("sha256"):\n'
        '        raise VendorUnreadable(f"session/{name}: its bytes are not the ones the ledger binds")\n'
        '    return raw\n',
        '    return _binding._regular_bytes(Path(path).parent / "session" / name)\n'),
        "a codex snapshot the ledger does not bind"),
    "the envelope read twice": ((
        '            readers = {"the rollout\'s UserMessage items": [t["sent"] for t in '
        '_codex_native.read_rollout(raw)["turns"]]}\n',
        '            readers = {"the rollout\'s UserMessage items": list(sent)}\n'),
        "the CLI's user record differs from the envelopes"),
    "the view run before the readers": ((
        '    view = {"events": None, "problems": []} if problems else vendor_take_view(path, harness)\n',
        '    view = vendor_take_view(path, harness)\n'), "the CLI's user record differs from the envelopes"),
    "no-first-agent-turn dropped": (('        problems += vendor_first_turn_problems(view["events"])\n', "        pass\n"),
                                    "no agent output"),
    "no-session-id dropped": (("    problems += vendor_session_id_problems(path, harness)\n", ""),
                              "the CLI wrote no session id"),
    "the stop problems dropped": (("        problems += stop_problems\n", ""), "a stop at a held marker"),
    "the operator lines dropped": (("        problems += line_problems\n", ""), "an operator line off the script"),
    "the continuation dropped": ((
        "            problems += continuation_problems(turns, required, [], expected_project, expected_source)\n",
        "            pass\n"),
        "a reply missing its step's marker"),
    "the fixture binding dropped": (("    problems += fixture_binding_problems(path, half, False)[0]\n", ""),
                                    "another fixture hash"),
    "the leak dropped": (("        problems += vendor_leak_problems(ops, pre)\n", "        pass\n"),
                         "a leak word in an operator line"),
    "the launch argv not rebuilt": (("        if argv != want:\n", "        if False:\n"),
                                    "a launch argv the adapter never writes"),
    "a missing launch journal admitted": ((
        '        if not (doc and doc.get("harness") == harness and isinstance(doc.get("stream"), str)\n',
        '        if False and not (doc and doc.get("harness") == harness and isinstance(doc.get("stream"), str)\n'),
        "a launch journal naming another turn's stream"),
    "the email marker unread": (("            if marker in (path.parent / name).read_bytes():\n",
                                 "            if False:\n"), "the email marker in a turn stream"),
    "the email counted per instance": ((
        "    for name in names:\n",
        "    hits = [n for n in names if (path.parent / n).is_file() and marker in (path.parent / n).read_bytes()]\n"
        "    if hits:\n        return [f'[{EVENT_EMAIL}] {n}' for n in hits]\n    for name in names:\n"),
        "the email marker in two published files"),
    "the turn end unread": (("        if not ended:\n", "        if False:\n"), "a turn that did not end"),
    "the completion legs dropped": (("    problems += completion_problems(path, ledger, pre)\n", ""),
                                    "an outcome off the driver's shapes"),
    "the ledger rows unread": (("    problems += vendor_ledger_turn_problems(ledger, script, expected_source)\n", ""),
                               "a ledger row off the script"),
    "the reach dropped": (('        problems += vendor_reach(path, harness, run_tree=vendor_session_cwd(path, harness))'
                           '["problems"]\n', ""), "a command reaching evals/"),
    "the home leg dropped": (("        outside += outside_home_reads(Path(tmp), repo=repo)\n", ""),
                             "a command reading the home folder"),
    "the temp leg dropped": (("        outside += outside_temp_reads(Path(tmp))\n", ""),
                             "a command reading the temp folder"),
    "the project name dropped": (("        problems += vendor_project_problems(ops, expected_project)\n", ""),
                                 "no operator line names the project"),
    "the take binding dropped": (("        problems += vendor_take_binding_problems(task_id, half_name, row_index, sid)\n",
                                  "        pass\n"), "no ledger row"),
    "the walk binding dropped": ((
        "        problems += vendor_walk_binding_problems(path, task_id, half_name, walk_id, sid)\n", "        pass\n"),
        "a walk whose session id is not its walk's"),
    "the constants dropped": (("    problems += constant_problems(ledger, pre)              # the ledger's budget, mode "
                               "and gars tree (T-24)\n", ""), "another turn budget"),
    "the session cwd unchecked": (("    if vendor_session_cwd(path, harness) is None:\n", "    if False:\n"),
                                  "a rollout turn in another working directory"),
    "the rollout cwd unchecked": (("        if cwd != design.run_tree:\n", "        if False:\n"),
                                  "a rollout turn in another working directory"),
    "the journal cwd unchecked": (('        if doc is not None and doc.get("cwd") != design.run_tree:\n',
                                   "        if False:\n"), "a launch journal in another working folder"),
    "the unread lines admitted": (("    if bad and not (isinstance(outcome, str) and outcome.startswith((\"timed-out\", "
                                   "\"aborted\"))):\n", "    if False:\n"), "a turn stream line no parser read"),
    "the nested switches unread": ((
        "    return command_problems(vendor_shell_commands(Path(path).parent, harness)[0], harness)\n",
        "    return []\n"), "a nested agent's session switch"),
    "file_change read as clean": (('                    return vendor_pending("codex", "T-8:file-change", None)\n',
                                   "                    return []\n"), "a file_change item"),
    "a PENDING refusal under an event id": ((
        "        return [f\"[{row['reason']}] no vendor reader yet ({key})\"]\n",
        "        return [f\"[{EVENT_STUDY}] no vendor reader yet ({key})\"]\n"), None),
}


def witness_red(mod, target) -> list:
    """The witness's own failures: its target case, or the clean takes when it names none."""
    if target is None:
        return clean_problems(mod)
    if target == "the run tree not handed to the reach":
        return tree_admitted_problems(mod)
    return case_problems(mod, {target})


class P2Witnesses(unittest.TestCase):
    def test_p2_witness_each_guard_dropped_goes_red(self):
        for name, (edit, target) in P2_WITNESSES.items():
            with self.subTest(witness=name):
                self.assertEqual(witness_red(tcb.ct, target), [], f"{name}: its case is red on check_take.py")
                self.assertNotEqual(witness_red(tcb.witness_module((edit,)), target), [], f"witness {name} stayed green")

    def test_p2_witness_the_run_tree_not_handed_to_the_reach(self):
        edit = ('        problems += vendor_reach(path, harness, run_tree=vendor_session_cwd(path, harness))["problems"]\n',
                '        problems += vendor_reach(path, harness)["problems"]\n')
        self.assertEqual(tree_admitted_problems(tcb.ct), [])
        self.assertNotEqual(tree_admitted_problems(tcb.witness_module((edit,))), [])

    def test_p2_witness_each_pending_refusal_deleted_goes_red(self):
        source = Path(tcb.ct.__file__).read_text(encoding="utf-8")
        sites = pending_call_sites(source)
        self.assertEqual(len(sites), sum(len(b) for b in tcb.ct.VENDOR_PENDING_ROWS.values()))
        for harness, text in sites:
            with self.subTest(site=text):
                mod = tcb.witness_module(((text, "[]"),))
                got = case_problems(mod, {"a file_change item"}) if "T-8:file-change" in text else clean_problems(mod)
                self.assertNotEqual(got, [], f"deleting {text} stayed green")


if __name__ == "__main__":
    unittest.main()
