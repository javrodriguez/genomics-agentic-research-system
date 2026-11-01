#!/usr/bin/env python3
"""The CP6 walk runner (Gap Study round 4, lane w10-walk-runner; glitch-2f's rulings D1, D2, D3 under Javier's
standing delegation, Mon 12 Oct 2026).

A walk is driven through the walk arm (walk_driver(records="walks"), so the W1 pre-launch check applies), checked by
check4's round-4 walk road, graded, and committed by WalkRepo with its register entry, one walk at a time
(walk_runner.run_walks). Each clause below was a probe variant first (lane-reports/w10-walk-runner.md).

  R1  the chain: one walk, end to end on the fake box (the REAL Claude Code adapter, the REAL check4 on the real
      design), committed under the walk subject with its register entry and reason; its folder holds the driver
      ledger, check.json and grade.json, and its identity is the walk's own (D2: session id
      uuid5(takes.namespace(), "walk/" + id), row and row_commit None); nothing is written under takes/;
      walk_register's check and run.py's regrade each count exactly one walk; the per-take config folder is deleted.
      Witnesses: walk-config-left (the runner never calls published), walk-check-unwritten (check.json not written).
  R2  D1, the walk road: before the freeze no takes.json row exists, and the walk is read with no session-binding
      reason (the take road would raise one); check_walk refuses the same transcript read as another walk's; a walk
      whose identity is a take's (row 0, a row commit) is refused at launch with nothing made, and the runner moves
      on to the next walk. Each session binding is shown alone (a copy whose ledger names another walk's session).
      Witnesses: walk-checked-as-take, walk-session-unbound, walk-ledger-session-unbound, walk-identity-unchecked,
      launch-refused-stops.
  R3  D3, a walk that dies before turn 1 (preflight fails): committed with no driver ledger, its grade.json "not
      graded, because ..." and its check.json; the register counts it, the regrade agrees, and the readers that need
      a session (mode_binding --walks, fixture_walk) skip it while the register still lists it; a folder without
      check.json breaks the content rule. Witnesses: dead-walk-ledger-required, dead-walk-ungraded,
      check-file-optional.
  R4  a walk whose drive raises is never committed: a postflight refusal (a credential-like file) keeps its walk
      folder and its config folder for a human, the register check goes red, and the runner stops before the next
      walk; a drive-scan refusal keeps its walk folder and deletes its config folder. Witnesses: held-committed,
      held-continues, postflight-config-deleted.
  R5  round 3's walk meaning is untouched: check_take.py at the base (f14ab57b) is a byte prefix of this one up to
      its `if __name__` block, no appended top-level name shadows a base name, and the base module and this one give
      the same problems and the same printed lines for one transcript read as a round-3 walk. Witness:
      round3-shadowed.
  R6  the CLI refuses, naming Q-w7b-3 (no production builder of walk_driver from the real box yet). Witness:
      cli-runs.
  R7  a walk row's slot is its walk id; any other slot is refused before launch, nothing made. Witness:
      slot-unchecked.
  R8  (review fold w10-R1-fold, W10-R1-1) D1's walk road, one binding at a time: a clean committed walk's folder is
      copied, one fact changed (a record that cross-binds it forged to agree), and check4_walk reads it; the lines it
      adds over the clean copy are exactly the bound guard's. One test and one witness per guard: the row-needed
      assertion, the ledger's task/half, row, row_commit, the environment record, its row, its row_commit, the
      model, a missing model, the constants, the checkout, the pinned instructions, the permission mode, the design
      tree and the arm. The machinery: the check_take the drive imports is this module's (a witness included), and a
      walk driven through the drive in another tree is readers-disagree in its check.json (witness
      walk-tree-unchecked-through-drive). R2 gains the walk's own session id with a row, and with a row commit, each
      refused alone (witnesses walk-identity-row-admitted, walk-identity-row-commit-admitted).
  R9  (Q-w10-1) the fake sidecar watches the half's planted paths, so the REAL v4 grader grades a fake walk end to
      end and run.py's regrade agrees. Witness: real-grader-bypassed.
  Fold W10-R1-2 (R4): the config folder is touched only once driver.launch was reached for the row (a walk refused
  before launch whose slot names a held walk leaves that walk's kept folder alone; witness published-before-launch)
  and kept whenever postflight.json exists and is not ok, even when teardown.json could not be written (witness
  keep-keyed-on-teardown). check.json says whether the checker ran (R1, R3; witness checked-always).

TEST DATA, NEVER PRODUCTION VALUES: test_walk_wiring's rig (its walk constants, routing pin, row and fixture record),
with the walk's own identity. Fakes and synthetic strings only: no model, vendor, network, container runtime,
credential, salt or holdout. The process guard and scratch repositories are test_box_integration's.

  G1  (ruling w10-R3-fold, W10-R3-1..5) GENERATED MUTATION replaces round 2's C1 shape list: tests/walk_mutation.py
      generates every mechanical mutant of the walk road (each statement deleted, each if/while condition True and
      False, each and/or operand dropped, each comparison negated, each assignment's right-hand side emptied);
      `--generated-mutants [--shard i/n] [--sample k] [--timeout s]` runs each in its own process over this whole
      module (failfast) and fails on a survivor not listed in EQUIVALENT (each entry with a checkable reason) and on a
      listed one that is killed; G1 fails on an EQUIVALENT entry that names no generated mutant. New tests from round
      3: faults only check() sees (an operator line never sent, one improvised, a fixture fault, and a fixture fault
      through the drive into check.json), a reused session id alone, a design view of another task with the right
      half, a teardown problem (through the drive) and clean_drive record by record, a recordless folder, a walk with
      no reason; the round-3 reviewer's eleven mutants are registry witnesses (REVIEWER3).
  R11 (fold w10-athena-survivors: athena's full sweep, run gap4-w10-5ff8b2e-20261013T003648Z, left 101 unlisted
      survivors) the walk road's functions one at a time, without a walk, each fed one bad input and read by its
      refusal's type and words: run.walk_row, grade_walk and died_before_turn_one; drive.walk_files (a symlinked or
      missing folder, a relative path, a symlinked or FIFO record, a ledger with no pre-turn record, a turn record
      with no ledger) and walk_identity_problems (an identity of another shape, shown in the refusal); walk_runner's
      check_record, write_check, _publish, run_one (a row with no walk id or reason; a launch that failed after making
      things; a container that could not be removed; another check file; a grade refusal; a committed walk's result)
      and run_walks (two committed walks). R8 gains check4_walk's type refusals, an event counted never routed, the
      design's pre put back, and the environment record unreadable, renamed by the pre, or with no pre block. Seven
      survivors are EQUIVALENT, each with its reason. R11Units runs first under --gen-mutant.

--mutant NAME compiles one altered module in memory before the bound test runs; --witnesses runs every registered
mutant in its own process, only its bound test, and requires that test to fail by an AssertionError carrying its
clause token, with no error (rule B).
"""
from __future__ import annotations

import ast
import hashlib
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

BASE = "f14ab57b"                       # wave 9's head, this lane's base: round 3's check_take.py as it stood
_got = subprocess.run(["git", "-C", str(REPO), "show", f"{BASE}:evals/gap-study-4/check_take.py"],
                      capture_output=True)   # read before test_box_integration's process guard is armed
BASE_CHECK_TAKE = _got.stdout.decode("utf-8") if _got.returncode == 0 else None

import takes  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import test_walk_wiring as tww  # noqa: E402
import variants  # noqa: E402
from box import run_take as rt  # noqa: E402

SELECTED = None
GENERATED = None        # --gen-mutant ID: one generated mutant of the walk road (tests/walk_mutation.py)
MODS: dict = {}
LANE = "w10-walk-runner"


# W10-R2 (ruling w10-R2-fold): the round-2 reviewer's fifteen mutants (scratchpad/w10r2/mut.py), anchors
# verbatim; clause by the class of their bound test (REVIEWER_BOUND).
REVIEWER = {
 # round 1's nine
 "r1-row-needed-assert-gone": ("R8.walk-road", "check_take",
    "    if not problems or problems[-1] != TAKE_ROW_NEEDED or problems.count(TAKE_ROW_NEEDED) != 1:\n", "    if False:\n"),
 "r1-ledger-taskhalf-gone": ("R8.walk-road", "check_take",
    "    if (ledger.get(\"task\"), ledger.get(\"half\")) != (task_id, half_name):", "    if False:"),
 "r1-ledger-row-gone": ("R8.walk-road", "check_take",
    "    if ledger.get(\"row\") is not None or ledger.get(\"row_commit\") is not None:", "    if False:"),
 "r1-env-gone": ("R8.walk-road", "check_take", "    problems += environment_problems(path, ledger, walk_pre, None)", "    pass"),
 "r1-envrec-row-gone": ("R8.walk-road", "check_take",
    "    if isinstance(rec, dict) and (rec.get(\"row\") is not None or rec.get(\"row_commit\") is not None):", "    if False:"),
 "r1-model-gone": ("R8.walk-road", "check_take", "        problems += model_problems(path, ledger[\"model_requested\"])\n", "        pass\n"),
 "r1-constants-gone": ("R8.walk-road", "check_take",
    "    problems += constant_problems(ledger, walk_pre)                     # D1: the take's tail\n"
    "    problems += checkout_problems(path, walk_pre)\n"
    "    problems += pinned_instruction_problems(path, design)               # D1: the take's tail\n", ""),
 "r1-mode-gone": ("R8.walk-road", "check_take",
    "    problems += recorded_mode_problems(path, design.pre, arm)          # D1: as for a take\n"
    "    problems += design_tree_problems(path, design)                     # D1: as for a take\n", ""),
 "r1-identity-row-gone": ("R8.walk-road", "drive",
    "    if not isinstance(ident, dict) or ident.get(\"session_id\") != want or ident.get(\"row\") is not None \\\n"
    "            or ident.get(\"row_commit\") is not None:",
    "    if not isinstance(ident, dict) or ident.get(\"session_id\") != want:"),
 # reviewer's own extras (round 2)
 "x-row-needed-last-clause": ("R8.walk-road", "check_take",
    "    if not problems or problems[-1] != TAKE_ROW_NEEDED or problems.count(TAKE_ROW_NEEDED) != 1:\n",
    "    if not problems or problems.count(TAKE_ROW_NEEDED) != 1:\n"),
 "x-row-needed-count-clause": ("R8.walk-road", "check_take",
    "    if not problems or problems[-1] != TAKE_ROW_NEEDED or problems.count(TAKE_ROW_NEEDED) != 1:\n",
    "    if not problems or problems[-1] != TAKE_ROW_NEEDED:\n"),
 "x-snapshot-gone": ("R8.walk-road", "check_take", "    problems += pinned_instruction_problems(path, design)               # D1: the take's tail\n    if not prompt_snapshot_present(path):", "    problems += pinned_instruction_problems(path, design)               # D1: the take's tail\n    if False:"),
 "x-memory-offered-gone": ("R8.walk-road", "check_take",
    "    if memory_section_offered(path):\n        problems.append(\"[inherited-context] the session was offered the harness's persistent memory folder \"\n                        \"outside its checkout; takes run with CLAUDE_CODE_DISABLE_AUTO_MEMORY=1\")\n    return problems\n\n\ndef check4_walk",
    "    return problems\n\n\ndef check4_walk"),
 "x-no-ledger-silent": ("R8.walk-road", "check_take",
    "        problems.append(\"[session-binding] \" + \"no driver ledger beside the walk's transcript, so nothing binds it \"\n                        \"to its walk\")\n",
    ""),
 "x-ledger-session-gone": ("R8.walk-road", "check_take", "    if ledger.get(\"session_id\") != want:", "    if False:"),
}
REVIEWER_BOUND = {'r1-row-needed-assert-gone': 'R8WalkRoad.test_the_row_needed_line_is_asserted', 'r1-ledger-taskhalf-gone': 'R8WalkRoad.test_the_ledger_cell', 'r1-ledger-row-gone': 'R8WalkRoad.test_the_ledger_row', 'r1-env-gone': 'R8WalkRoad.test_the_environment_record', 'r1-envrec-row-gone': 'R8WalkRoad.test_the_environment_row', 'r1-model-gone': 'R8WalkRoad.test_the_model', 'r1-constants-gone': 'R8WalkRoad.test_the_constants', 'r1-mode-gone': 'R8WalkRoad.test_the_permission_mode', 'r1-identity-row-gone': 'R2WalkCheck.test_a_walk_identity_with_a_row_is_refused', 'x-row-needed-last-clause': 'R8WalkRoad.test_the_row_needed_line_is_last', 'x-row-needed-count-clause': 'R8WalkRoad.test_the_row_needed_line_is_alone', 'x-snapshot-gone': 'R8WalkRoad.test_no_snapshot', 'x-memory-offered-gone': 'R8WalkRoad.test_memory_offered', 'x-no-ledger-silent': 'R8WalkRoad.test_no_ledger', 'x-ledger-session-gone': 'R2WalkCheck.test_a_walk_is_read_as_a_walk'}


CLAUSE_OF = {"R12Pending": "R12.pending", "R8WalkRoad": "R8.walk-road", "R2WalkCheck": "R2.walk-check",
             "R3DeadWalk": "R3.dead-walk",
             "R4Held": "R4.held"}

# W10-R3 (ruling w10-R3-fold): the round-3 reviewer's eleven mutants (scratchpad/w10r3/mut_extra.py), anchors verbatim.
REVIEWER3 = {
    "x3-problems-wiped": ("X", "check_take", "    problems = problems[:-1]\n", "    problems = []\n", "check_walk"),
    "x3-reasons-dropped": ("X", "check_take", "            reasons.append(named[0])\n", "            pass\n",
                           "check4_walk"),
    "x3-identity-session-clause": ("X", "drive", 'ident.get("session_id") != want or ', ""),
    "x3-design-task-clause": ("X", "check_take", "    if (design.task_id, design.half) != (task_id, half_name):",
                              "    if design.half != half_name:", "check4_walk"),
    "x3-design-script-clause": ("X", "check_take", "    if None in (design.half, design.script):",
                                "    if design.half is None:", "check4_walk"),
    "x3-noledger-nopreturn-admitted": ("X", "drive",
                                       "    if LEDGER_FILE not in tops and not (tops & set(WALK_PRE_TURN)):",
                                       "    if False:"),
    "x3-preflight-failed-read-as-passed": ("X", "run", '        if doc.get("ok") is not True:', "        if False:"),
    "x3-teardown-problems-ignored": ("X", "walk_runner", ' and tear.get("problems") == []', ""),
    "x3-teardown-null-ignored": ("X", "walk_runner", 'tear.get("teardown") is not None and ', ""),
    "x3-checker-reasons-dropped": ("X", "walk_runner", 'list(records.get("checker_reasons") or [])', "[]"),
    "x3-reason-unchecked": ("X", "walk_runner",
                            "    if not isinstance(reason, str) or not walk_register.visible(reason):", "    if False:"),
}
REVIEWER3_BOUND = {
    "x3-problems-wiped": "R8WalkRoad.test_an_operator_line_never_sent",
    "x3-reasons-dropped": "R8WalkRoad.test_the_design_tree_through_the_drive",
    "x3-identity-session-clause": "R2WalkCheck.test_a_reused_session_id_is_refused",
    "x3-design-task-clause": "R8WalkRoad.test_the_design_refusals",
    "x3-design-script-clause": "R8WalkRoad.test_the_design_refusals",
    "x3-noledger-nopreturn-admitted": "R3DeadWalk.test_a_recordless_folder_is_refused",
    "x3-preflight-failed-read-as-passed": "R3DeadWalk.test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason",
    "x3-teardown-problems-ignored": "R4Held.test_clean_drive_needs_both_clean_records",
    "x3-teardown-null-ignored": "R4Held.test_clean_drive_needs_both_clean_records",
    "x3-checker-reasons-dropped": "R8WalkRoad.test_the_design_tree_through_the_drive",
    "x3-reason-unchecked": "R2WalkCheck.test_a_walk_without_a_reason_is_refused",
}


def mutants():
    """name -> (clause, module, old text, new text[, function]). Each weakens one guard; old must occur exactly once
    (inside `function` when one is named). The deletion registry and the reviewer's mutants are merged in."""
    out = own_mutants()
    for name, (_, module, old, new) in REVIEWER.items():
        out[name] = (CLAUSE_OF[REVIEWER_BOUND[name].split(".")[0]], module, old, new)
    for name, (_, module, old, new, *scope) in REVIEWER3.items():
        out[name] = (CLAUSE_OF[REVIEWER3_BOUND[name].split(".")[0]], module, old, new, *scope)
    return out


def own_mutants():
    """name -> (clause, module, old text, new text). Each weakens one guard; old must occur exactly once."""
    return {
        "walk-config-left": ("R1.chain", "walk_runner",
                             "            kept = _publish(driver, row, folder)\n", "            kept = None\n"),
        "walk-check-unwritten": ("R1.chain", "walk_runner",
                                 "    write_check(folder, check_record(walk, records, table, route_fn, checked=checked,\n"
                                 "                                     constants_sha256=read(row) if callable(read) else "
                                 "None,\n"
                                 "                                     no_output_nudges=nudges, agent_summary=agents))\n",
                                 ""),    # re-anchored on the call that passes the digest, (ruling 3) the nudge count
                                         # and (the Agent parity ruling, part 6) the Agent record
        "checked-always": ("R3.dead-walk", "walk_runner", "\"checked\": checked is True", "\"checked\": True"),
        "walk-launch-journal-not-a-turn": ("R3.dead-walk", "drive",       # integration red A3 (glitch-06, 14 Oct)
                                           "\n                 or LAUNCH_JOURNAL_NAME.fullmatch(n))", ")"),
        # registration review finding 2 (glitch-06, 14 Oct 2026): the pending-walk road
        "pending-walk-held": ("R12.pending", "walk_runner",
                              '    if removal_error is None and isinstance(drive_error, ns["NativeCrossCheckPending"]):',
                              "    if False:"),
        "pending-removal-unchecked": ("R12.pending", "walk_runner",
                                      '    if removal_error is None and isinstance(drive_error, ns["NativeCrossCheckPending"]):',
                                      '    if isinstance(drive_error, ns["NativeCrossCheckPending"]):'),
        "pending-other-errors-admitted": ("R12.pending", "walk_runner",
                                          '    if removal_error is None and isinstance(drive_error, ns["NativeCrossCheckPending"]):',
                                          "    if removal_error is None and drive_error is not None:"),
        "pending-grade-dropped": ("R12.pending", "run",
                                  "    if pending is not None:\n        return pending\n", ""),
        # re-anchored (lane vendor-admission round 10 ruling 5, drift from T4 P0's edit A, be9942ea: drive's walk-road
        # branch moved into check_take's claude-code entry): the same guard, records "walks" read as the walk road
        "walk-checked-as-take": ("R2.walk-check", "check_take",
                                 "    if records == \"walks\":                # D1: the round-4 walk road\n",
                                 "    if False:                # D1: the round-4 walk road\n", "_claude_code_entry"),
        "walk-session-unbound": ("R2.walk-check", "check_take",
                                 "    if sid != want:                                  # D2",
                                 "    if False:                                  # D2"),
        "walk-ledger-session-unbound": ("R2.walk-check", "check_take",
                                        "    if ledger.get(\"session_id\") != want:", "    if False:"),
        "walk-identity-unchecked": ("R2.walk-check", "drive",
                                    "    walk_identity_problems(driver, row)           # D2, before anything is made\n",
                                    ""),
        "launch-refused-stops": ("R2.walk-check", "walk_runner",
                                 "            continue                                   # D3: reported, move on\n",
                                 "            break\n"),
        "dead-walk-ledger-required": ("R3.dead-walk", "drive",
                                      "    if LEDGER_FILE not in tops and not (tops & set(WALK_PRE_TURN)):",
                                      "    if LEDGER_FILE not in tops:"),
        "dead-walk-ungraded": ("R3.dead-walk", "run",
                               "    if not (folder / \"driver-ledger.json\").is_file():         # D3",
                               "    if False:         # D3"),
        "check-file-optional": ("R3.dead-walk", "drive",
                                "WALK_REQUIRED = (WALK_GRADE, WALK_CHECK)", "WALK_REQUIRED = (WALK_GRADE,)"),
        "held-committed": ("R4.held", "walk_runner",
                           "    if drive_error is not None or removal_error is not None:",
                           "    if False:"),
        "held-continues": ("R4.held", "walk_runner",
                           "            break                                      # D3: kept for a human, stop\n",
                           "            continue\n"),
        "postflight-config-deleted": ("R4.held", "walk_runner",
                                      "    post_ok = isinstance(post, dict) and post.get(\"ok\") is True",
                                      "    post_ok = True"),
        "teardown-unread": ("R4.held", "walk_runner",
                            "    tear_ok = isinstance(tear, dict) and tear.get(\"teardown\") is not None and "
                            "tear.get(\"problems\") == []", "    tear_ok = True"),
        "keep-by-default-dropped": ("R4.held", "walk_runner", "    if not clean_drive(folder):", "    if False:"),
        "ledgerless-turns-admitted": ("R3.dead-walk", "drive", "    if LEDGER_FILE not in tops and ran:",
                                      "    if False:"),
        "ledgerless-graded": ("R3.dead-walk", "run",
                              "    if ran:                                              # W10-R2-3",
                              "    if False:                                              # W10-R2-3"),
        "published-before-launch": ("R4.held", "walk_runner", "        if reached:\n", "        if True:\n"),
        "walk-identity-row-admitted": ("R2.walk-check", "drive", "ident.get(\"row\") is not None \\",
                                       "False \\"),
        "walk-identity-row-commit-admitted": ("R2.walk-check", "drive",
                                              "            or ident.get(\"row_commit\") is not None:",
                                              "            or False:"),
        "walk-row-needed-unasserted": ("R8.walk-road", "check_take",
                                       "    if not problems or problems[-1] != TAKE_ROW_NEEDED or "
                                       "problems.count(TAKE_ROW_NEEDED) != 1:", "    if False:"),
        "walk-ledger-cell-unbound": ("R8.walk-road", "check_take",
                                     "    if (ledger.get(\"task\"), ledger.get(\"half\")) != (task_id, half_name):",
                                     "    if False:"),
        "walk-ledger-row-unbound": ("R8.walk-road", "check_take", "ledger.get(\"row\") is not None or ", ""),
        "walk-ledger-row-commit-unbound": ("R8.walk-road", "check_take",
                                           " or ledger.get(\"row_commit\") is not None:", ":"),
        "walk-environment-unread": ("R8.walk-road", "check_take",
                                    "    problems += environment_problems(path, ledger, walk_pre, None)", "    pass"),
        "walk-environment-row-unbound": ("R8.walk-road", "check_take", "rec.get(\"row\") is not None or ", ""),
        "walk-environment-row-commit-unbound": ("R8.walk-road", "check_take",
                                                " or rec.get(\"row_commit\") is not None)", ")"),
        "walk-model-unbound": ("R8.walk-road", "check_take",
                               "        problems += model_problems(path, ledger[\"model_requested\"])\n",
                               "        pass\n"),
        "walk-model-missing-admitted": ("R8.walk-road", "check_take",
                                        "    if ledger.get(\"model_requested\"):", "    if True:"),
        "walk-constants-unread": ("R8.walk-road", "check_take",
                                  "    problems += constant_problems(ledger, walk_pre)", "    pass"),
        "walk-checkout-unread": ("R8.walk-road", "check_take",
                                 "    problems += checkout_problems(path, walk_pre)\n", ""),
        "walk-instructions-unread": ("R8.walk-road", "check_take",
                                     "    problems += pinned_instruction_problems(path, design)               # D1",
                                     "    pass               # D1"),
        "walk-mode-unread": ("R8.walk-road", "check_take",
                             "    problems += recorded_mode_problems(path, design.pre, arm)          # D1",
                             "    pass          # D1"),
        "walk-tree-unchecked": ("R8.walk-road", "check_take",
                                "    problems += design_tree_problems(path, design)                     # D1",
                                "    pass                     # D1"),
        "walk-tree-unchecked-through-drive": ("R8.walk-road", "check_take",
                                              "    problems += design_tree_problems(path, design)                     # D1",
                                              "    pass                     # D1"),
        "walk-arm-unbound": ("R8.walk-road", "check_take",
                             "    if isinstance(beside, dict) and beside.get(\"arm\") != arm:", "    if False:"),
        "real-grader-bypassed": ("R9.real-grade", "run",
                                 "(grade_walk_folder if grade is None else grade)(row, folder)",
                                 "(grade or (lambda r, f: {\"label\": \"synthetic-bypass\"}))(row, folder)"),
        "round3-shadowed": ("R5.round3", "check_take",
                            "\n\nif __name__ == \"__main__\":",
                            "\n\ndef fixture_binding_problems(path, half, is_walk=True):\n    return [], None\n"
                            "\n\nif __name__ == \"__main__\":"),
        # departure w12b-2 (lane w12b-walk-builders): main now hands its argv to walk_builders.cli (w12b-1)
        "cli-runs": ("R6.cli", "walk_runner", "    return walk_builders.cli(argv, builders, refusal=CLI_REFUSAL)",
                     "    return 0"),
        "slot-unchecked": ("R7.slot", "walk_runner", "    if row.get(\"slot\") != walk:", "    if False:"),
        # battery 388e7476 shard 5's survivor run.grade_walk:delete:L17:C4 (lane vendor-t3b): grade_walk's vendor
        # admission call deleted
        "walk-vendor-admission-skipped": ("R11.units", "run",
                                          '    vendor_admission(row["agent"].get("harness"), readers, '
                                          'ledger.get("cross_check_status"))\n', "    pass\n", "grade_walk"),
    }


def compile_module(name: str, source: str) -> types.ModuleType:
    mod = types.ModuleType(name)
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


SOURCES: dict = {}


def function_span(text: str, function: str) -> tuple[int, int]:
    """The character span of the top-level def `function` in `text` (its first to its last line)."""
    tree = ast.parse(text)
    node = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function]
    assert len(node) == 1, f"no single top-level def {function}"
    starts = [0]
    for line in text.splitlines(keepends=True):
        starts.append(starts[-1] + len(line))
    return starts[node[0].lineno - 1], starts[node[0].end_lineno]


def apply_mutant(text: str, old: str, new: str, function=None) -> str:
    """old -> new, exactly once: in the whole module, or inside `function` when one is named."""
    a, b = function_span(text, function) if function else (0, len(text))
    region = text[a:b]
    assert region.count(old) == 1, f"the anchor occurs {region.count(old)} times in {function or 'the module'}"
    return text[:a] + region.replace(old, new) + text[b:]


def setUpModule():
    tbi.setUpModule()
    MODS["drive"] = tbi.drive
    if SELECTED is not None:
        _, target, old, new, *scope = mutants()[SELECTED]
        path = HERE / f"{target}.py"
        text = path.read_text()
        SOURCES[target] = apply_mutant(text, old, new, scope[0] if scope else None)
        if target == "drive":
            assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
            MODS["drive"] = tbi.witness_module(((old, new),))
        else:
            MODS[target] = compile_module(target, SOURCES[target])
    if GENERATED is not None:
        import walk_mutation
        m = walk_mutation.by_id()[GENERATED]
        SOURCES[m.module] = m.source((HERE / f"{m.module}.py").read_text())
        if m.module == "drive":
            MODS["drive"] = compile_drive(SOURCES["drive"])
        else:
            MODS[m.module] = compile_module(m.module, SOURCES[m.module])
    for name in ("check_take", "run", "walk_register", "mode_binding", "fixture_walk", "walk_runner", "routing"):
        if name not in MODS:
            try:
                MODS[name] = __import__(name)
            except ImportError:            # a module the slice must provide: its absence is a red by assertion
                MODS[name] = types.SimpleNamespace()


def compile_drive(source: str) -> types.ModuleType:
    """drive.py from a whole generated source, compiled in memory as test_box_integration.witness_module compiles a
    witness (its own module name, drive.py's file), never written to disk."""
    name = "drive_w6h_witness"
    mod = types.ModuleType(name)
    mod.__file__ = tbi.drive.__file__
    sys.modules[name] = mod
    try:
        exec(compile(source, tbi.drive.__file__ + " (generated mutant)", "exec"), mod.__dict__)
    finally:
        sys.modules.pop(name, None)
    return mod


def tearDownModule():
    if SELECTED is not None or GENERATED is not None:
        for name in ("check_take", "run", "walk_runner"):
            sys.modules.pop(name, None)       # a compiled witness never outlives this module
    tbi.tearDownModule()


class Case(unittest.TestCase):
    def must(self, clause, fn, *args, **kwargs):
        """fn(*args, **kwargs), or a failure of `clause` naming what it raised (a red by assertion, never an error)."""
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:400]}")


# ------------------------------------------------------------------------------------------------- the rig
def walk_sid(walk: str) -> str:
    """D2, recomputed here from the ruling's words, never read from the module under test."""
    import uuid
    return str(uuid.uuid5(takes.namespace(), "walk/" + walk))


def stand_in_grade(row, folder):
    return {"label": "synthetic-label", "views": {"strict": "right"}, "graded_by": "graders/synthetic.py"}


class WalkWired(tww.Wired):
    """test_walk_wiring's rig on the walk arm: walk_driver(records="walks"), each row's identity the walk's own (D2:
    session id from the walk id, row and row_commit None), and a WalkRepo over the scratch study."""

    def __init__(self, mod, ct, root: Path, *, take_identity=False, identity_over=None, opened_in=None,
                 watch_planted=False):
        self.take_identity, self.identity_over = take_identity, dict(identity_over or {})
        super().__init__(mod, ct, root, opened_in=opened_in)
        if watch_planted:                 # Q-w10-1: the fake sidecar watches what the v4 grader reads
            self.box.evidence = self._watching_planted(self.box.evidence)
        self.repo = mod.WalkRepo(runtime=self.box, secrets=lambda: [("token", tbi.TOKEN)],
                                 rules_scanner=lambda paths: [], root=root, repo=root)

    def _build(self, mod, login, root=None):
        root = self.root if root is None else root
        return mod.walk_driver(
            runtime=self.box, root=str(root), config_parent=str(self.cfg_parent), spec_for=self.spec_for,
            sidecar_for=self.sidecar_for, proxy=rt.ProxyLaunch(
                image="sha256:" + "9" * 64, conf_source=str(tbi.SCRATCH / "proxy.conf"),
                conf_target="/etc/squid/x.conf", command=("squid", "-N"), user="13:13", alias="proxy"),
            lock_path=str(tbi.SCRATCH / "synthetic.lock"), hosts={"api": "synthetic.invalid"}, login_file=str(login),
            counters_for=lambda take: {"oom_kill": 0, "pids_max": 0}, pin_for=self.pin_for,
            design_for=self.design_for, project_for=self.project_for, identity_for=self.identity_for,
            secrets=lambda: [("token", tbi.TOKEN)], rules_scanner=lambda paths: [], uid_map=tbi.UID_MAP,
            budget_s=600, finalize_wait_s=tbi.CAP_S, poll_s=tbi.POLL_S, clock=self.clock, sleep=self.clock.sleep,
            records="walks",
            ownership=tbi.FakeOwnership(self.box), settings_guard=tbi.FakeSettingsGuard(),
            machine_gate=lambda: [])

    def project_for(self, row):
        return self.mod.neutral_name(walk_sid(row["walk"]))

    def identity_for(self, row):
        if self.identity_over.get("raise"):
            raise RuntimeError("synthetic: the identity builder failed")
        if self.take_identity:
            return super().identity_for(row)
        source = variants.render_source(variants.load_task(row["task"])["source_template"], str(self.tree),
                                        self.project_for(row))
        over = dict(self.identity_over)
        if "session_of" in over:                  # another walk's session id, computed inside the world
            over["session_id"] = walk_sid(over.pop("session_of"))
        return dict({"session_id": walk_sid(row["walk"]), "row": None, "row_commit": None, "source": source,
                     "fixture": tww.fixture_record(row), "gars_tree_sha": self.ct.GARS_TREE_SHA}, **over)

    def _watching_planted(self, evidence):
        """The fake sidecar's evidence with watched.json listing the half's planted paths (variants.grader_spec's
        `planted`, the paths the v4 grader reads), written before test_box_integration's default synthetic list."""
        def ev(sid, label):
            row = self.row
            planted = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                           project=self.project_for(dict(row, walk=self.current)))["planted"]
            path = Path(self.box.containers[sid]["ev"]) / "watched.json"
            if not path.exists():
                with tbi.FakeBox.as_watcher(str(path.parent)):     # the sidecar writes as the watcher (P4 road)
                    path.write_text(json.dumps({"paths": sorted(set(planted))}))
            return evidence(sid, label)
        return ev

    current = None

    def walk(self, walk: str, **over) -> dict:
        self.current = walk
        return {"row": dict(dict(self.row, walk=walk, slot=walk), **over), "reason": f"synthetic: walk {walk} of the tests"}

    def run_walks(self, walks, **kw):
        with tbi.spying(self.spy):
            return MODS["walk_runner"].run_walks(self.driver, self.repo, walks, table=self.table,
                                                 grade=stand_in_grade, **kw)


@contextlib.contextmanager
def prefreeze():
    """The study as it stands before the freeze: takes.json holds no row, so the take road has nothing to bind to."""
    with mock.patch.object(takes, "load_rows", lambda **kw: tww.REAL_LOAD_ROWS(**kw) if kw else []), \
            mock.patch.object(takes, "row_commits", lambda **kw: tww.REAL_ROW_COMMITS(**kw) if kw else {}):
        yield


@contextlib.contextmanager
def study(**kw):
    """test_walk_wiring's world, before the freeze, over a scratch study: the draft, tasks/, rehearsals/ committed."""
    import mode_binding as mb
    with tww.world() as ct, prefreeze(), tbi.scratch_repo() as root:
        shutil.copy(HERE / "prereg-draft.json", root / "prereg-draft.json")
        shutil.copytree(HERE / "tasks", root / "tasks")
        (root / mb.WALKS_DIR).mkdir()
        (root / mb.WALKS_DIR / "README.md").write_text("synthetic\n")
        (root / mb.WALKS_DIR / "register.json").write_text('{\n  "schema": 1,\n  "walks": []\n}\n')
        tbi.git(root, "add", "-A")
        tbi.git(root, "commit", "-q", "-m", "A synthetic study skeleton")
        yield WalkWired(MODS["drive"], ct, root, **kw)


def register_check(w) -> tuple[list, int]:
    import mode_binding as mb
    wr = MODS["walk_register"]
    return wr.check(w.root / mb.WALKS_DIR, wr.design_in_force(w.root))


def folder_of(w, walk) -> Path:
    import mode_binding as mb
    return w.root / mb.WALKS_DIR / walk


# ------------------------------------------------------------------------------------------------- R1
class R1Chain(Case):
    def test_one_walk_end_to_end(self):
        with study() as w:
            got = self.must("R1.chain", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R1.chain: {got}")
            self.assertEqual(tbi.git(w.root, "log", "-1", "--format=%s"), w.mod.WALK_SUBJECT, "R1.chain")
            reg = json.loads((w.root / "rehearsals" / "register.json").read_text())
            self.assertEqual([(e["walk"], e["reason"], e["counted"]) for e in reg["walks"]],
                             [("w-0001", "synthetic: walk w-0001 of the tests", False)], "R1.chain")
            folder = folder_of(w, "w-0001")
            for name in ("driver-ledger.json", "check.json", "grade.json", "transcript.jsonl"):
                self.assertTrue((folder / name).is_file(), f"R1.chain: no {name}")
            led = json.loads((folder / "driver-ledger.json").read_text())
            self.assertEqual((led["session_id"], led["row"], led["row_commit"]), (walk_sid("w-0001"), None, None),
                             "R1.chain: the walk's identity")
            self.assertTrue(json.loads((folder / "grade.json").read_text())["graded"], "R1.chain")
            # glitch-6b (16 Oct 2026, the w033-w040 question): a turn whose reply holds its marker sends the next
            # line, through the production adapter: turn 2 is in the ledger and its launch journal resumes the session
            rows = led["turns"]
            self.assertGreaterEqual(len(rows), 2, f"R1.chain: only {len(rows)} turn(s) were driven: {rows}")
            self.assertEqual((rows[0]["n"], rows[0]["held"], rows[1]["n"]), (1, True, 2), f"R1.chain: {rows}")
            step2 = w.design_for(w.row, str(w.tree)).script[1]["line"]
            self.assertTrue(rows[1]["sent"] and step2.split("{", 1)[0] in rows[1]["sent"], f"R1.chain: {rows[1]}")
            j2 = json.loads((folder / "turn-2.jsonl.launch.json").read_text())
            self.assertIn("--resume", j2["argv"], "R1.chain: turn 2 does not resume turn 1's session")
            self.assertEqual(j2["argv"][j2["argv"].index("-p") + 1], rows[1]["sent"], "R1.chain: turn 2's line")
            self.assertIs(json.loads((folder / "check.json").read_text()).get("checked"), True, "R1.chain")
            self.assertEqual(json.loads((folder / "check.json").read_text()).get("route"), "graded",
                             "R1.chain: the walk's records were not routed")
            self.assertFalse((w.root / "takes").exists(), "R1.chain: something was written under takes/")
            self.assertEqual(register_check(w), ([], 1), "R1.chain")
            self.assertEqual(MODS["run"].walk_problems(base=w.root, grade=stand_in_grade), ([], 1), "R1.chain")
            self.assertEqual(tbi.git(w.root, "status", "--porcelain"), "", "R1.chain")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R1.chain: the config folder was left behind")


# ------------------------------------------------------------------------------------------------- R2
class R2WalkCheck(Case):
    def test_a_walk_is_read_as_a_walk(self):
        with study() as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R2.walk-check: {got}")
            folder = folder_of(w, "w-0001")
            check = json.loads((folder / "check.json").read_text())
            self.assertEqual(check["checker_reasons"], [], f"R2.walk-check: {check}")
            # the same transcript read as another walk's is refused by the session binding
            ct = MODS["check_take"]
            design = w.design_for(w.row, str(w.tree))
            other = self.must("R2.walk-check", ct.check_walk, folder / "transcript.jsonl", w.row["task"],
                              w.row["half"], "w-0002", wording_script=design.script, design=design)
            self.assertTrue(any(p.startswith("[session-binding]") for p in other), f"R2.walk-check: {other}")
            mine = self.must("R2.walk-check", ct.check_walk, folder / "transcript.jsonl", w.row["task"],
                             w.row["half"], "w-0001", wording_script=design.script, design=design)
            self.assertFalse(any(p.startswith("[session-binding]") for p in mine), f"R2.walk-check: {mine}")
            # each binding on its own: a copy whose ledger names w-0002's session, read as w-0002 (only the
            # transcript's session disagrees) and as w-0001 (only the ledger's does)
            copy = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-copy"
            shutil.copytree(folder, copy)
            led = json.loads((copy / "driver-ledger.json").read_text())
            (copy / "driver-ledger.json").write_text(json.dumps(dict(led, session_id=walk_sid("w-0002"))))
            for walk_id, says in (("w-0002", "[session-binding] the session id does not match its walk"),
                                  ("w-0001", "[session-binding] the driver ledger records session")):
                got = self.must("R2.walk-check", ct.check_walk, copy / "transcript.jsonl", w.row["task"],
                                w.row["half"], walk_id, wording_script=design.script, design=design)
                binding = [p for p in got if p.startswith("[session-binding]")]
                self.assertEqual([p.startswith(says) for p in binding], [True], f"R2.walk-check {walk_id}: {binding}")
            # the study conditions on the walk road (glitch-6b's review MINOR, 15 Oct 2026): the walk as committed
            # passes them; a copy missing a turn's launch journal refuses through check4_walk, fail closed
            hcv = "harness-condition-violated"
            bare = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-bare"
            shutil.copytree(folder, bare)
            journals = sorted(bare.glob("turn-*.jsonl.launch.json"))
            self.assertTrue(journals, "R2.walk-check: the committed walk carries its launch journals")
            journals[0].unlink()
            def view_of(mod):
                return mod.design_view(w.row, pin=w.pin_for(w.row), run_tree=str(w.tree), constants=w.constants)
            def read(where, mod=ct):
                view = view_of(mod)
                return self.must("R2.walk-check", mod.check4_walk, where / "transcript.jsonl", w.row["task"],
                                 w.row["half"], "w-0001", wording_script=view.script, arm=w.row["arm"],
                                 design=view)["reasons"]
            got = read(folder)
            self.assertNotIn(hcv, got, f"R2.walk-check: the committed walk refused: {got}")
            got = read(bare)
            self.assertIn(hcv, got, f"R2.walk-check: a missing journal passed: {got}")
            # the witness: check4_walk's claude-code branch turned off, the missing journal passes unnamed
            src = Path(ct.__file__).read_text()
            site = ("    if design.harness == CLAUDE_CODE:\n        problems += steer_condition_problems(path)"
                    "                     # the bash-first steer OFF")
            self.assertEqual(src.count(site), 1, "R2.walk-check: the check4_walk branch's anchor")
            m = types.ModuleType("check_take_witness")
            m.__file__ = ct.__file__
            sys.modules[m.__name__] = m
            try:
                exec(compile(src.replace(site, site.replace("design.harness == CLAUDE_CODE", "False")),
                             ct.__file__, "exec"), m.__dict__)
            finally:
                del sys.modules[m.__name__]
            got = read(bare, m)
            self.assertNotIn(hcv, got, f"R2.walk-check witness: {got}")
            # each condition on its own (the generated sweep's survivors on a6a01b1c): a walk whose journals keep
            # everything but drop the switch refuses by the steer call; one that sets crossSessionInbound "hold"
            # refuses by the isolation call
            def edited(name, edit):
                where = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / name
                shutil.copytree(folder, where)
                for j in sorted(where.glob("turn-*.jsonl.launch.json")):
                    doc = json.loads(j.read_text())
                    i = doc["argv"].index("--settings")
                    st = json.loads(doc["argv"][i + 1])
                    edit(st)
                    doc["argv"][i + 1] = json.dumps(st, sort_keys=True, separators=(",", ":"))
                    j.write_text(json.dumps(doc))
                return where
            unset = edited("w-unset", lambda st: st["env"].pop("CLAUDE_CODE_THRIFTY_SONIC"))
            hold = edited("w-hold", lambda st: st.__setitem__("crossSessionInbound", "hold"))
            # and (the d7107255 battery's survivors) each later claude-code call on its own: the deny list emptied
            # refuses by the isolation call, a raw separator in the transcript (lane pf1-l3, 24 Oct 2026: a C0 one, since
            # U+2028 is read as text) by the line call, a sub-agent file no
            # Agent call names by the Agent call
            undenied = edited("w-undenied", lambda st: st["permissions"].__setitem__("deny", []))
            sep = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-sep"
            shutil.copytree(folder, sep)
            lines_ = (sep / "transcript.jsonl").read_text(encoding="utf-8").split("\n")
            at = next(i for i, x in enumerate(lines_) if '"text"' in x and '"assistant"' in x)
            rec = json.loads(lines_[at])
            block = next(b for b in rec["message"]["content"] if b.get("type") == "text")
            # lane pf1-l3 (the second closure check of f0c0eb1d, 24 Oct 2026): a C0 separator, still refused, so the case
            # witnesses check4_walk's line call again (U+2028 is read as text since the closure check of 8cf492b2)
            block["text"] = "\u2028" + block["text"]
            lines_[at] = json.dumps(rec, ensure_ascii=False).replace("\u2028", "\x0b")
            (sep / "transcript.jsonl").write_text("\n".join(lines_), encoding="utf-8")
            # lane pf1-l3 (the merged battery's walk_runner shard 6 survivor, check4_walk:delete:L40, 25 Oct 2026): a
            # session file whose reply words were rewritten after the turn refuses by check4_walk's content call
            forged = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-forged"
            shutil.copytree(folder, forged)
            flines = (forged / "transcript.jsonl").read_text(encoding="utf-8").split("\n")
            fat = next(i for i, x in enumerate(flines) if '"text"' in x and '"assistant"' in x)
            frec = json.loads(flines[fat])
            next(b for b in frec["message"]["content"] if b.get("type") == "text")["text"] = "I will not do that."
            flines[fat] = json.dumps(frec, ensure_ascii=False)
            (forged / "transcript.jsonl").write_text("\n".join(flines), encoding="utf-8")
            stray = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-stray"
            shutil.copytree(folder, stray)
            (stray / "subagents").mkdir(exist_ok=True)
            (stray / "subagents" / "agent-0000ffff.jsonl").write_text(json.dumps(   # a leak word in its context
                {"type": "attachment", "isSidechain": True, "attachment": {"type": "nested_memory",
                                                                          "content": "notes for round 4"}}) + "\n")
            # W-3b (glitch-b5's pre-freeze ruling, 16 Oct 2026): the driver listed the config folder's session store
            # after every turn and at publish, holding only the walk's own session; a nested agent's session refuses
            store = json.loads((folder / "session-store.json").read_text())
            self.assertEqual(store["listings"][-1]["at"], "publish", "R2.walk-check: the store's publish listing")
            nested = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-nested"
            shutil.copytree(folder, nested)
            own = next(p for p, k in store["listings"][-1]["entries"] if p.endswith(".jsonl") and k == "file")
            store["listings"][-1]["entries"].append([own.rsplit("/", 1)[0] + "/nested-0000.jsonl", "file"])
            (nested / "session-store.json").write_text(json.dumps(store))
            # review r14 (d): the sweep of the take container ran after every turn and found only the walk's own session;
            # a nested session in /tmp refuses
            self.assertEqual([x["at"] for x in store["sweeps"]], [x["at"] for x in store["listings"][:-1]],
                             "R2.walk-check: one sweep per turn")
            swept = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-swept"
            shutil.copytree(folder, swept)
            store2 = json.loads((folder / "session-store.json").read_text())
            store2["sweeps"][0]["files"].append(["/tmp/n/projects/-x/n1.jsonl", "claude", "n1"])
            (swept / "session-store.json").write_text(json.dumps(store2))
            for where, why, says in ((unset, hcv, "do not set CLAUDE_CODE_THRIFTY_SONIC off"),
                                     (nested, "nested-agent-session", "is not the take's own session record"),
                                     (swept, "nested-agent-session", "/tmp/n/projects/-x/n1.jsonl is a claude session"),
                                     (hold, hcv, "crossSessionInbound is 'hold'"),
                                     (undenied, hcv, "permissions.deny lacks"),
                                     (sep, "transcript-unreadable", "line separator(s) U+000B"),
                                     (forged, "transcript-mismatch", "differs from the host-captured stream"),
                                     (stray, "subagent-records", "are not exactly the copies the driver ledger names"),
                                     (stray, "leak-in-loaded-context", "sub-agent file agent-0000ffff.jsonl's loaded")):
                got = self.must("R2.walk-check", ct.check4_walk, where / "transcript.jsonl", w.row["task"],
                                w.row["half"], "w-0001", wording_script=view_of(ct).script, arm=w.row["arm"],
                                design=view_of(ct))
                self.assertIn(why, got["reasons"], f"R2.walk-check {where.name}: {got['reasons']}")
                self.assertTrue(any(says in p for p in got["problems"]), f"R2.walk-check {where.name}: {got}")
            # the conditions are claude-code's: a harness the guard admits (a reader registered later) is not held
            # to them on the same records
            import copy as copy_module            # `copy` is this test's walk-folder copy above
            other = copy_module.copy(view_of(ct))
            other.harness = "synthetic-harness"
            with mock.patch.object(ct, "HARNESSES_WITH_READERS", (*ct.HARNESSES_WITH_READERS, "synthetic-harness")):
                try:
                    got = ct.check4_walk(unset / "transcript.jsonl", w.row["task"], w.row["half"], "w-0001",
                                         wording_script=other.script, arm=w.row["arm"], design=other)["reasons"]
                except ct.CheckRefused as e:
                    got = [f"refused: {e}"]
            self.assertNotIn(hcv, got, f"R2.walk-check: another harness was held to claude-code's conditions: {got}")

    def test_a_take_identity_is_refused_at_launch(self):
        with study(take_identity=True) as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused", "launch-refused"],
                             f"R2.walk-check: {got}")
            self.assertIn("identity", got[0].get("why", ""), "R2.walk-check")
            self.assertEqual(sorted(p.name for p in (w.root / "rehearsals").iterdir()), ["README.md", "register.json"],
                             "R2.walk-check: a refused walk made its folder")
            self.assertEqual(w.spy.calls, [], "R2.walk-check: preflight was reached")


    def test_an_unreadable_identity_is_refused(self):
        """W10-R2-1: an identity_for that raises is refused at launch, nothing made."""
        with study(identity_over={"raise": True}) as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R2.walk-check: {got}")
            self.assertIn("cannot be read", got[0].get("why", ""), "R2.walk-check")
            self.assertEqual(w.spy.calls, [], "R2.walk-check: preflight was reached")

    def test_a_reused_session_id_is_refused(self):
        """W10-R3-2: another walk's session id, with no row and no row commit, is refused alone at launch."""
        with study(identity_over={"session_of": "w-0009"}) as w:
            got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R2.walk-check: {got}")
            self.assertIn("not its own", got[0].get("why", ""), "R2.walk-check")
            self.assertEqual(w.spy.calls, [], "R2.walk-check: preflight was reached")

    def test_a_walk_without_a_reason_is_refused(self):
        """Round 3's unverified runner guard: a walk with no reason (empty, or only invisible characters) is refused
        before launch; every walk is committed with its reason."""
        with study() as w:
            for reason in ("", " \u200b "):
                got = self.must("R2.walk-check", w.run_walks, [{"row": w.walk("w-0001")["row"], "reason": reason}])
                self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R2.walk-check: {got}")
                self.assertIn("reason", got[0].get("why", ""), "R2.walk-check")
            self.assertEqual(w.spy.calls, [], "R2.walk-check: preflight was reached")

    def test_a_walk_identity_with_a_row_is_refused(self):
        """W10-R1-1: the walk's own session id with a ledger row, or with a row commit, each refused alone."""
        for over in ({"row": 0}, {"row_commit": "c" * 40}):
            with study(identity_over=over) as w:
                got = self.must("R2.walk-check", w.run_walks, [w.walk("w-0001")])
                self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R2.walk-check {over}: {got}")
                self.assertIn("identity", got[0].get("why", ""), f"R2.walk-check {over}")
                self.assertEqual(w.spy.calls, [], f"R2.walk-check {over}: preflight was reached")


# ------------------------------------------------------------------------------------------------- R3
class R3DeadWalk(Case):
    def test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason(self):
        with study() as w:
            w.spy.result = tbi.preflight_record(False)
            got = self.must("R3.dead-walk", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R3.dead-walk: {got}")
            folder = folder_of(w, "w-0001")
            self.assertFalse((folder / "driver-ledger.json").exists(), "R3.dead-walk")
            grade = json.loads((folder / "grade.json").read_text())
            self.assertFalse(grade["graded"], "R3.dead-walk")
            self.assertTrue(grade["why"].startswith("not graded, because"), f"R3.dead-walk: {grade}")
            self.assertIn("preflight failed", grade["why"], "R3.dead-walk")
            self.assertTrue((folder / "check.json").is_file(), "R3.dead-walk")
            self.assertIs(json.loads((folder / "check.json").read_text()).get("checked"), False,
                          "R3.dead-walk: check.json passes an empty reading off as a clean one")
            self.assertEqual(register_check(w), ([], 1), "R3.dead-walk")
            self.assertEqual(MODS["run"].walk_problems(base=w.root, grade=stand_in_grade), ([], 1), "R3.dead-walk")
            self.assertEqual(len(MODS["walk_register"].registered(w.root / "rehearsals")), 1, "R3.dead-walk")
            self.assertEqual(MODS["mode_binding"].attempts(True, w.root), [], "R3.dead-walk")
            self.assertEqual(MODS["fixture_walk"].registered_walks(w.root), [], "R3.dead-walk")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R3.dead-walk: the config folder was left behind")
            # check.json is required: without it the content rule breaks
            (folder / "check.json").rename(w.root / "aside.json")
            problems, _ = register_check(w)
            self.assertFalse(problems, "R3.dead-walk: check() itself is not the content rule")
            try:
                w.mod.walk_files(folder)
                self.fail("R3.dead-walk: a walk folder without check.json passes the closed map")
            except w.mod.DriveRefused as e:
                self.assertIn("check.json", str(e), "R3.dead-walk")
            rule = MODS["walk_register"].content_problems(w.root / "rehearsals", ["w-0001"])
            self.assertTrue(rule and "check.json" in rule[0], f"R3.dead-walk: {rule}")


    def test_a_recordless_folder_is_refused(self):
        """W10-R3-5: a hand-built folder holding only grade.json and check.json (no driver ledger, no preflight or
        refusal record) is refused by the closed map: nothing in it says why it was not graded."""
        folder = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
        folder.mkdir()
        (folder / "grade.json").write_text('{"graded": false, "why": "synthetic"}\n')
        (folder / "check.json").write_text('{"walk": "w-0001", "checked": false}\n')
        drive = MODS["drive"]
        try:
            drive.walk_files(folder)
            self.fail("R3.dead-walk: a recordless walk folder passes the closed map")
        except drive.DriveRefused as e:
            self.assertIn("driver-ledger.json", str(e), f"R3.dead-walk: {e}")

    def test_a_ledgerless_walk_whose_turns_ran_is_refused(self):
        """W10-R2-3, the reviewer's ledgerless probe: a committed walk copied, its driver ledger removed. Its
        transcript and turn records show a turn ran, so it is never read as a walk that died before turn 1: the
        closed map (the register's content rule) refuses it, and run.py will not write "not graded" for it."""
        with study() as w:
            got = self.must("R3.dead-walk", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R3.dead-walk: {got}")
            copy = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
            shutil.copytree(folder_of(w, "w-0001"), copy)
            (copy / "driver-ledger.json").unlink()
            try:
                w.mod.walk_files(copy)
                self.fail("R3.dead-walk: a ledgerless walk whose turns ran passes the closed map")
            except w.mod.DriveRefused as e:
                self.assertIn("transcript.jsonl", str(e), f"R3.dead-walk: {e}")
            entry = MODS["walk_runner"].walk_entry(w.walk("w-0001")["row"], "synthetic")
            try:
                doc = MODS["run"].grade_walk(entry, copy, grade=stand_in_grade)
                self.fail(f"R3.dead-walk: a ledgerless walk whose turns ran was graded as {doc}")
            except ValueError as e:
                self.assertIn("transcript.jsonl", str(e), f"R3.dead-walk: {e}")

    def test_a_ledgerless_walk_with_only_a_launch_journal_is_refused(self):
        """Live harness 3a (glitch-06's ruling, 0d417a1d; integration red A3): a launch journal alone is a turn
        launched, so a walk folder holding one and no driver ledger is refused even with a pre-turn record beside it;
        it is never read as a walk that died before turn 1. Binds walk_files' launch-journal clause."""
        with study() as w:
            got = self.must("R3.dead-walk", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R3.dead-walk: {got}")
            copy = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
            shutil.copytree(folder_of(w, "w-0001"), copy)
            # Every turn sign goes: the ledger, the transcript, each stream and each launch journal (on the merged
            # head the box's run_turn writes turn-N.jsonl.launch.json itself, 0b6f60f9; the integration lane).
            for p in list(copy.iterdir()):
                if p.name == "driver-ledger.json" or p.name == "transcript.jsonl" or (
                        p.name.startswith("turn-") and p.name.endswith((".jsonl", ".jsonl.launch.json"))):
                    p.unlink()
            if not (copy / "preflight.json").exists() and not (copy / "refusal.json").exists():
                (copy / "preflight.json").write_text('{"ok": true, "checks": []}\n')
            w.mod.walk_files(copy)        # the control: with no turn sign the folder is a walk that died before turn 1
            (copy / "turn-1.jsonl.launch.json").write_text("{}\n")
            try:
                w.mod.walk_files(copy)
                self.fail("R3.dead-walk: a ledgerless walk with a launch journal passes the closed map")
            except w.mod.DriveRefused as e:
                self.assertIn("turn-1.jsonl.launch.json", str(e), f"R3.dead-walk: {e}")


class R13Recheck(Case):
    """The recheck (glitch-6b's scheduled-wakeup ruling B, 15 Oct 2026; athena battery on b7aca72a, generated
    survivors of walk_files' recheck clause): a walk folder's top-level recheck-<n>.json is scanned as a ledger; the
    same name deeper keeps its folder's kind; every other name keeps the closed map's kind or refuses."""

    def test_the_recheck_clause_of_the_closed_map(self):
        drive = MODS["drive"]
        folder = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
        (folder / drive.SESSION_DIR).mkdir(parents=True)
        for name in ("driver-ledger.json", "grade.json", "check.json", "transcript.jsonl", "recheck-1.json",
                     "recheck-2.json", f"{drive.SESSION_DIR}/recheck-1.json"):
            (folder / name).write_text("{}\n")
        kinds = {Path(p).relative_to(folder).as_posix(): k for p, k in self.must("R13.recheck", drive.walk_files, folder)}
        self.assertEqual(kinds["recheck-1.json"], "ledger", "R13.recheck: a top-level recheck is a ledger")
        self.assertEqual(kinds["recheck-2.json"], "ledger", "R13.recheck")
        self.assertEqual(kinds[f"{drive.SESSION_DIR}/recheck-1.json"], "session",
                         "R13.recheck: the name deeper keeps its folder's kind")
        self.assertEqual(kinds["transcript.jsonl"], drive.TAKE_FILE_KINDS["transcript.jsonl"],
                         "R13.recheck: a take file keeps its own kind")
        for bad in ("recheck-01.json", "recheck-0.json", "recheck-1.jsonl", "stray.json"):
            with self.subTest(name=bad):
                (folder / bad).write_text("{}\n")
                with self.assertRaises(drive.DriveRefused):
                    drive.walk_files(folder)
                (folder / bad).unlink()


# ------------------------------------------------------------------------------------------------- R4
class R4Held(Case):
    def test_a_postflight_refusal_is_never_committed(self):
        with study() as w:
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False,
                                            "detail": "credential-like files present: ['synthetic']"}],
                   "recorded": {"listing": [], "credential_files": []}}
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness, **_kw: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertIn("postflight", got[0].get("why", ""), "R4.held")
            self.assertTrue(folder_of(w, "w-0001").is_dir(), "R4.held: the walk folder was not kept")
            self.assertFalse(folder_of(w, "w-0002").exists(), "R4.held: the runner did not stop")
            self.assertEqual(json.loads((w.root / "rehearsals" / "register.json").read_text())["walks"], [],
                             "R4.held")
            self.assertTrue(register_check(w)[0], "R4.held: the register check is not red")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")

    def test_a_scan_refusal_is_never_committed(self):
        with study() as w:
            w.driver.rules_scanner = lambda paths: [{"path": paths[0], "line": 1, "rule": "synthetic-rule"}]
            got = self.must("R4.held", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertIn("scan", got[0].get("why", ""), "R4.held")
            self.assertTrue(folder_of(w, "w-0001").is_dir(), "R4.held")
            self.assertFalse(folder_of(w, "w-0002").exists(), "R4.held")
            self.assertEqual(tbi.git(w.root, "log", "-1", "--format=%s"), "A synthetic study skeleton", "R4.held")
            self.assertEqual(list(w.cfg_parent.iterdir()), [], "R4.held: the config folder was left behind")


    def test_a_refused_slot_leaves_a_kept_config_folder_alone(self):
        """W10-R1-2: the reviewer's probe, made sharp for the `reached` guard alone (W10-R2 fold). w-0002 is committed
        clean (its folder exists and proves a clean drive), then w-0001 is held with its config folder kept; a row
        refused before launch, walk w-0002 with slot w-0001, touches nothing: the fail-closed keep and the folder
        check would both let it through, so only the `reached` guard stands between it and w-0001's kept folder."""
        with study() as w:
            got = self.must("R4.held", w.run_walks, [w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R4.held: {got}")
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False, "detail": "synthetic"}],
                   "recorded": {"listing": [], "credential_files": []}}
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness, **_kw: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held")
            got = self.must("R4.held", w.run_walks, [w.walk("w-0002", slot="w-0001")])
            self.assertEqual([(g.get("state"), g.get("config")) for g in got], [("launch-refused", None)],
                             f"R4.held: {got}")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1,
                             "R4.held: a walk refused before launch deleted another walk's kept config folder")

    def test_a_failed_teardown_write_still_keeps_the_config_folder(self):
        """W10-R2-2 (fail closed): a clean postflight with no teardown record proves nothing; the walk is committed
        (teardown.json is not a required walk record) and its config folder is kept."""
        with study() as w:
            write = w.driver._write

            def no_teardown(take, name, doc):
                if name == "teardown.json":
                    raise OSError("synthetic: the teardown record could not be written")
                return write(take, name, doc)
            w.driver._write = no_teardown
            got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R4.held: {got}")
            folder = folder_of(w, "w-0001")
            self.assertFalse((folder / "teardown.json").exists(), "R4.held: the teardown write did not fail")
            self.assertTrue((folder / "postflight.json").is_file(), "R4.held")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")

    def test_a_teardown_problem_keeps_the_config_folder(self):
        """W10-R3-4: a drive whose teardown recorded a problem (here the leftover-process kill failing) is no proof
        of a clean drive; the walk is committed and its config folder kept."""
        with study() as w:
            def kill(take):
                raise RuntimeError("synthetic: the leftover processes could not be killed")
            w.driver._kill = kill
            got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R4.held: {got}")
            tear = json.loads((folder_of(w, "w-0001") / "teardown.json").read_text())
            self.assertTrue(tear["problems"], f"R4.held: {tear}")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")

    def test_clean_drive_needs_both_clean_records(self):
        """W10-R3-4: clean_drive, record by record: only an ok postflight with a teardown and no problem is proof."""
        wr = MODS["walk_runner"]
        ok_post = {"ok": True, "checks": []}
        ok_tear = {"teardown": {"steps": []}, "problems": [], "quiescence_survivors": []}
        cases = ((ok_post, ok_tear, True), ({"ok": False}, ok_tear, False), (None, ok_tear, False),
                 (ok_post, None, False), (ok_post, dict(ok_tear, teardown=None), False),
                 (ok_post, dict(ok_tear, problems=["synthetic: a leftover"]), False), ("[", ok_tear, False))
        for post, tear, want in cases:
            folder = Path(tempfile.mkdtemp(dir=tbi.SCRATCH))
            for name, doc in (("postflight.json", post), ("teardown.json", tear)):
                if doc is not None:
                    (folder / name).write_text(doc if isinstance(doc, str) else json.dumps(doc))
            got = self.must("R4.held", lambda: wr.clean_drive(folder))
            self.assertIs(got, want, f"R4.held: clean_drive({post!r}, {tear!r})")

    def test_both_records_refused_keeps_the_config_folder(self):
        """W10-R2-2, the reviewer's probe: a failing postflight whose postflight.json and teardown.json writes are
        both refused leaves no record at all; the config folder is kept."""
        with study() as w:
            bad = {"ok": False, "checks": [{"id": "no-credential-file", "ok": False, "detail": "synthetic"}],
                   "recorded": {"listing": [], "credential_files": []}}
            write = w.driver._write

            def refused(take, name, doc):
                if name in ("teardown.json", "postflight.json"):
                    raise OSError(f"synthetic: {name} could not be written")
                return write(take, name, doc)
            w.driver._write = refused
            with mock.patch.object(w.mod._preflight, "postflight", lambda cfg, harness, **_kw: bad):
                got = self.must("R4.held", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R4.held: {got}")
            folder = folder_of(w, "w-0001")
            for name in ("teardown.json", "postflight.json"):
                self.assertFalse((folder / name).exists(), f"R4.held: {name} was written")
            self.assertEqual(len(list(w.cfg_parent.iterdir())), 1, "R4.held: the config folder was not kept")
            self.assertIn("kept for a human", got[0].get("config") or "", f"R4.held: {got}")


# ------------------------------------------------------------------------------------------------- R5
def top_names(source: str) -> set:
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


# BOOTSTRAP (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026; lane bootstrap-constants; review MAJOR 1 fold): the
# ruling fills check_take.CHECKER_CONSTANTS IN PLACE (B1), corrects the comments, the refusal and the docstring that
# said a walk measures them, and binds the ledger's cap and poll in check4 (B4). R5's prefix rule is superseded for
# exactly the regions BOOTSTRAP_SPANS lists, each the text strictly between two anchors found once in the base and once now, and each
# bound to its ruled content: the current region's sha256 is pinned here, so any edit inside one needs a test edit;
# the constants region must parse to exactly one statement, the CHECKER_CONSTANTS assignment (comments aside). The base's
# region is replaced by the pinned one before the prefix comparison; every other byte of the base is still a prefix.
BOOTSTRAP_SPANS = (
    ("check4-refusal", "    if design.pending:\n", "    if design.task_id != task_id or design.half != half_name:",
     "5904fcb6d583437ff4dfa2642710a486ac352439eb8b21b80c53dd4774fa10bf"),
    ("check4-b4-line", 'and the take is "\n                        f"checked as arm {arm!r}")\n',
     "    reasons, kept, lifted = [], [], set()\n",
     "9d9613ac97e2245dd571e9f964018330cd8098590bf03a8aecba32e6f79da595"),
    ("r4c7-comment", "(variants.operator_steps) and its source (the task's source_template rendered with the take's run "
                     "tree),\n", "#   R4C-1/D1.",
     "c3baa5bc41c095a1259592c830aec147df7167525fd5624c6ec7c6a2a38a3efe"),
    ("checker-constants", "# The keys round 3's check() reads that the round-4 draft does not carry (s6b plan, section 0). "
                          "A closed block: a key\n", "\n\ndef harness_guard(",
     # glitch-6b's scheduled-wakeup ruling (15 Oct 2026): harness_delivered_user_records gains meta_kinds; glitch-b5's
     # ruling 3 (16 Oct 2026, w053): meta_kinds also names the no-visible-output nudge.
     "6b43580ce1a777062f7d5dc7bd2c40ed6939c037c0bf417f228aa71cd9ef8c79"),
    ("r4c10-comment", "#           none (a context variable, so parallel takes never see each other's), else "
                      "prereg.load() as in round 3.\n", "#   R4C-11.",
     "4ec1ebccb7591883e7a87ccb70946669e240acb341205f62405e8e380cc1b3de"),
    # Ruling T0 (lane vendor-admission, Javier's typed word "T0: yes", 16 Oct 2026; applied at 34b1df74, bound here by
    # glitch-b5 on 17 Oct): the docstring gains its T0 sentence (re-pinned), design_view's guard becomes the
    # HARNESSES_WITH_SCRIPTS check, HARNESSES_WITH_SCRIPTS is inserted after HARNESSES_WITH_READERS, and R4C-9's comment
    # names the ruling; check4 and check4_walk keep harness_guard, outside every region.
    ("design-view-docstring", "    pin (D1) and the run tree the driver gave it. `constants` defaults to CHECKER_CONSTANTS",
     "    constants = CHECKER_CONSTANTS if constants is None else constants\n",
     "f6e271049c06f720af1aa6cffaea669f13d6e0d7a5f5ff48725b602d0bbc9626"),
    ("design-view-guard", '    harness = (row.get("agent") or {}).get("harness")\n',
     '    if not isinstance(pin, dict) or pin.get("harness") != harness or pin.get("model") != row.get("model"):\n',
     "e6c5691e0f74c1bf5be6bf857615b911be5093ba9ec164d2a1b65b931d18c7f7"),
    ("harnesses-with-scripts", "HARNESSES_WITH_READERS = (CLAUDE_CODE,)\n", 'PENDING = "PENDING"\n',
     "42df7f710929cab488da1462c60eb2025f7131de53098cc0b55ed900cd99282d"),
    # T4 R-1 (lane vendor-admission, plan v4 section 5, ruled by glitch-b5 on 17 Oct; built with P3 in round 12):
    # r4c9-comment is re-pinned with its sentence that vendor takes are read by the appended vendor entries through
    # checker_for and that HARNESSES_WITH_READERS names check4's harnesses, and harness_guard's docstring and refusal
    # are reworded ("check4 reads claude-code only; vendor takes go through checker_for") in the new region below.
    ("r4c9-comment", "#   R4C-9. THE HARNESS GUARD (CP2-requirements item 10): only claude-code has record readers in this "
                     "file, so a take\n",
     "# " + "=" * 117 + "\n\nimport copy  # noqa: E402\n",
     "09398effd2392f2e7a74236ab0638ee62a45b80f88bea44aea51bec4e3601bed"),
    ("harness-guard-message", "def harness_guard(harness) -> None:\n", "\n\ndef _pending_paths(",
     "83ffc7370a818aed74823cc73bf62b009b2bc1e6c5342a44dc5212c3a656b579"),
    # glitch-6b's scheduled-wakeup ruling (15 Oct 2026, CP6 walk w006; the harness lane): user_text_records' `kinds`
    # line and its record-type line, edited in place to read the view's own predicate (check_take's appended
    # SCHEDULED WAKEUP section); no line moves.
    ("scheduled-wakeup-lines", "    the harness's; any other origin refuses, because who sent it cannot be established.\n"
                               '    """\n', '        msg = rec.get("message") if isinstance(rec.get("message"), dict) else rec\n',
     "403ded1cdce16ae6a4eed516db368b597e43ec3997085494d3d098c6d0543fc5"),
    # glitch-6b's steer-off ruling (15 Oct 2026; the box lane's check_take patch, reviewed and applied by the harness
    # lane): check4 adds the study-condition problems (steer, isolation) for a claude-code take, inserted between two base lines; the
    # functions it calls are appended.
    ("check4-study-conditions", "    problems += design_tree_problems(path, design)               # W7B (Q-w6i-5)\n",
     "    # W6H-R1-5: constant_problems reads the mode for the LEDGER's arm",
     # and the isolation denials' line (glitch-6b's isolation ruling, 15 Oct 2026), and the transcript line check's
     # (glitch-b5's ruling on review r8, 16 Oct 2026), and the sub-agent records' (the Agent parity ruling, 16 Oct),
     # and the session store's and the persistence flag's (W-3b, glitch-b5's pre-freeze ruling, 16 Oct 2026), and the
     # transcript content's (lane pf1-l3, fold plan prefreeze-1 MAJOR 7, the lane orchestrator's approval, 24 Oct 2026)
     "7f13552e05b98ade6e45643de95f327866a37c58c8e9c85f08391e31eef694e8"),
    # glitch-b5's ruling 2 (16 Oct 2026): context_text's one append line sweeps an admitted edited_text_file without its
    # snippet (check_take's appended _swept_attachment_line); no line moves.
    ("context-text", "def context_text(path: Path) -> str:\n", "\n\ndef context_leaks(",
     "d81967915c9f93175441cb1ba85becea3a432babccdbd218a06a3bb1e0b955ac"),
)


def _region(text: str, start: str, end: str, name: str) -> tuple:
    if text.count(start) != 1:
        raise AssertionError(f"R5.bootstrap {name}: its start anchor occurs {text.count(start)} times")
    i = text.index(start) + len(start)
    j = text.find(end, i)
    if j < 0:
        raise AssertionError(f"R5.bootstrap {name}: no end anchor after its start")
    return i, j


# Review r7's observation (glitch-b5, 16 Oct 2026): every transcript read in check_take splits on "\n" alone, never
# str.splitlines() (which also splits on U+2028 and kin). Each listed text is replaced in the base, exactly `count` times
# (the base's own count, pinned), before the regions; every other byte of the base is still a prefix.
# The scheduled-wakeup-lines and context-text regions each hold one such read, so both are re-pinned with it.
BOOTSTRAP_SUBSTITUTIONS = (
    ('.read_text(errors="replace").splitlines()', '.read_text(errors="replace").split("\\n")', 18),
    ('.read_text(encoding="utf-8", errors="replace").splitlines()',
     '.read_text(encoding="utf-8", errors="replace").split("\\n")', 2),
    # Pre-freeze review 2 MAJOR 3 (glitch-45's ruling on the lane review of 8d71ae0d; lane fold2/la1, 83185e5b): an
    # operator turn the frozen script renders to nothing is the driver's own record, so it is raised as
    # driver-record-fault (harness-error), never the agent-reachable operator-lines; in place at 0-based line 1114.
    # No committed walk carries the reason (every rehearsals/ check.json has checker_reasons []).
    ('problems.append("[operator-lines] " + f"operator turn {step[\'n\']} renders to nothing; the script is broken")',
     'problems.append(f"[{DRIVER_RECORD_FAULT}] operator turn {step[\'n\']} renders to nothing; the script is broken")',
     1),
)


def bootstrap_base(base: str, now: str) -> str:
    """The base with each BOOTSTRAP_SUBSTITUTIONS text replaced (exactly its pinned count) and each BOOTSTRAP_SPANS
    region replaced by the current file's, which must hash to the pinned sha256 (and, for the constants region, be
    exactly one CHECKER_CONSTANTS assignment); otherwise AssertionError."""
    for old, new, count in BOOTSTRAP_SUBSTITUTIONS:
        if base.count(old) != count:
            raise AssertionError(f"R5.bootstrap: the base holds {base.count(old)} of {old!r}, not {count}")
        base = base.replace(old, new)
    for name, start, end, digest in BOOTSTRAP_SPANS:
        i, j = _region(base, start, end, name)
        k, m = _region(now, start, end, name)
        got = now[k:m]
        if hashlib.sha256(got.encode("utf-8")).hexdigest() != digest:
            raise AssertionError(f"R5.bootstrap {name}: the region is not its ruled content (sha256 differs)")
        if name == "checker-constants":
            body = ast.parse(got).body
            if not (len(body) == 1 and isinstance(body[0], ast.Assign) and len(body[0].targets) == 1
                    and isinstance(body[0].targets[0], ast.Name) and body[0].targets[0].id == "CHECKER_CONSTANTS"):
                raise AssertionError("R5.bootstrap checker-constants: the region is not exactly the one "
                                     "CHECKER_CONSTANTS assignment")
        base = base[:i] + got + base[j:]
    return base


class R5Bootstrap(Case):
    """Review MAJOR 1: an edit inside any ruled region is red (each region's own witness), and the reviewer's own probe,
    a statement inserted after CHECKER_CONSTANTS' closing brace, is red."""

    def test_the_tree_passes_and_every_region_edit_is_red(self):
        self.assertIsNotNone(BASE_CHECK_TAKE, f"R5.bootstrap: git cannot show {BASE}'s check_take.py")
        now = (HERE / "check_take.py").read_text()
        base = BASE_CHECK_TAKE[:BASE_CHECK_TAKE.rindex("\nif __name__")]
        self.assertTrue(now.startswith(bootstrap_base(base, now)), "R5.bootstrap: the tree itself")
        for name, start, end, _ in BOOTSTRAP_SPANS:
            with self.subTest(region=name):
                k, m = _region(now, start, end, name)
                edited = now[:m] + "x = 1\n" + now[m:] if name == "checker-constants" else now[:k] + " " + now[k:]
                with self.assertRaises(AssertionError):
                    bootstrap_base(base, edited)

    def test_the_reviewers_probe_is_red(self):
        now = (HERE / "check_take.py").read_text()
        base = BASE_CHECK_TAKE[:BASE_CHECK_TAKE.rindex("\nif __name__")]
        brace = now.index("\n}\n", now.index("CHECKER_CONSTANTS = {")) + 3
        probe = now[:brace] + "never_stripped = lambda name, patterns, fixed: False\n" + now[brace:]
        with self.assertRaises(AssertionError):
            bootstrap_base(base, probe)


class R5Round3(Case):
    def test_round_3_walks_are_untouched(self):
        self.assertIsNotNone(BASE_CHECK_TAKE, f"R5.round3: git cannot show {BASE}'s check_take.py")
        now = SOURCES.get("check_take") or (HERE / "check_take.py").read_text()
        cut = BASE_CHECK_TAKE.rindex("\nif __name__")
        ruled = bootstrap_base(BASE_CHECK_TAKE[:cut], now)          # BOOTSTRAP: the ruled spans, nothing else
        self.assertTrue(now.startswith(ruled), "R5.round3: the base's bytes are not a prefix")
        cut = len(ruled)
        BASE_CHECK_TAKE_RULED = ruled + BASE_CHECK_TAKE[BASE_CHECK_TAKE.rindex("\nif __name__"):]
        self.assertTrue(now.endswith(BASE_CHECK_TAKE_RULED[cut:]), "R5.round3: the __main__ block moved")
        added = now[cut:len(now) - (len(BASE_CHECK_TAKE_RULED) - cut)]
        shadow = top_names(added) & top_names(BASE_CHECK_TAKE_RULED[:cut])
        self.assertEqual(shadow, set(), f"R5.round3: appended names shadow the base's {sorted(shadow)}")
        # the same transcript read as a round-3 walk by the base module and by this one
        with study() as w:
            got = self.must("R5.round3", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R5.round3: {got}")
            path = folder_of(w, "w-0001") / "transcript.jsonl"
            base = compile_module("check_take_base_r5", BASE_CHECK_TAKE)
            sys.modules.pop("check_take_base_r5", None)
            outs = []
            for mod in (base, MODS["check_take"]):
                design = mod.design_view(w.row, pin=w.pin_for(w.row), run_tree=str(w.tree), constants=w.constants)
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    problems = self.must("R5.round3", mod.check, path, w.row["task"], w.row["half"], None, True,
                                         wording_script=design.script, design=design)
                outs.append((problems, buf.getvalue()))
            self.assertEqual(outs[0], outs[1], "R5.round3: a round-3 walk reads differently")


# ------------------------------------------------------------------------------------------------- R6, R7
class R6Cli(Case):
    def test_the_cli_refuses(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = self.must("R6.cli", lambda: MODS["walk_runner"].main([]))
        self.assertEqual(code, 2, "R6.cli")
        self.assertIn("Q-w7b-3", err.getvalue(), "R6.cli")


class R7Slot(Case):
    def test_the_slot_is_the_walk_id(self):
        with study() as w:
            got = self.must("R7.slot", w.run_walks, [w.walk("w-0001", slot="s1")])
            self.assertEqual([g.get("state") for g in got], ["launch-refused"], f"R7.slot: {got}")
            self.assertIn("slot", got[0].get("why", ""), "R7.slot")
            self.assertEqual(sorted(p.name for p in (w.root / "rehearsals").iterdir()), ["README.md", "register.json"],
                             "R7.slot")
            self.assertEqual(w.spy.calls, [], "R7.slot")


# ------------------------------------------------------------------------------------------------- R8
def edit_json(path: Path, **changes) -> None:
    path.write_text(json.dumps(dict(json.loads(path.read_text()), **changes), indent=2) + "\n")


def edit_transcript(path: Path, fn) -> int:
    """Each transcript record through fn (record -> record); returns how many fn changed."""
    out, n = [], 0
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        new = fn(json.loads(line))
        n += new != rec
        out.append(json.dumps(new))
    path.write_text("\n".join(out) + "\n")
    return n


def attachment(kind, change):
    def fn(rec):
        att = rec.get("attachment") if rec.get("type") == "attachment" else None
        if isinstance(att, dict) and att.get("type") == kind:
            change(att)
        return rec
    return fn


def rebind_environment(folder: Path) -> None:
    """The driver ledger rebound to environment.json's new bytes, so a changed environment record is the one
    change (never also a ledger that no longer binds it)."""
    import hashlib
    led = folder / "driver-ledger.json"
    sha = hashlib.sha256((folder / "environment.json").read_bytes()).hexdigest()
    edit_json(led, environment=dict(json.loads(led.read_text())["environment"], sha256=sha))


class R8WalkRoad(Case):
    """D1's walk road, one binding at a time (W10-R1-1): a clean committed walk's folder is copied, ONE fact is
    changed (where another record cross-binds it, that record is forged to agree, so only the bound guard can see the
    change), and check_take.check4_walk (the module the drive imports, a witness included) reads the copy. The
    problems it adds over the clean copy are exactly the bound guard's lines."""
    stack = None

    @classmethod
    def setUpClass(cls):
        cls.stack = contextlib.ExitStack()
        cls.w = w = cls.stack.enter_context(study())
        got = w.run_walks([w.walk("w-0001")]) if hasattr(MODS["walk_runner"], "run_walks") else [{}]
        cls.ran = got
        cls.folder = folder_of(w, "w-0001")

    @classmethod
    def tearDownClass(cls):
        cls.stack.close()

    def read(self, folder: Path, walk="w-0001", arm=None) -> list:
        w = self.w
        design = w.design_for(w.row, str(w.tree))
        got = self.must("R8.walk-road", MODS["check_take"].check4_walk, folder / "transcript.jsonl", w.row["task"],
                        w.row["half"], walk, wording_script=design.script, arm=arm or w.row["arm"], design=design)
        return got["problems"]

    def copy(self) -> Path:
        self.assertEqual([g.get("state") for g in self.ran], ["committed"], f"R8.walk-road: {self.ran}")
        dst = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)) / "w-0001"
        shutil.copytree(self.folder, dst)
        return dst

    def one_change(self, folder: Path, says: str, walk="w-0001"):
        base = self.read(self.copy(), walk)
        got = self.read(folder, walk)
        added = [p for p in got if p not in base]
        self.assertTrue(added, f"R8.walk-road: nothing caught ({says!r}); problems {got}")
        self.assertTrue(all(p.startswith(says) for p in added),
                        f"R8.walk-road: the change raised other lines than {says!r}: {added}")

    def refuses(self, words, fn, *args, **kwargs):
        """fn must raise check_take.CheckRefused carrying `words`; anything else (no raise, another exception) is a
        failure by assertion."""
        ct = MODS["check_take"]
        try:
            fn(*args, **kwargs)
        except ct.CheckRefused as e:
            self.assertIn(words, str(e), f"R8.walk-road: refused for another reason: {e}")
            return
        except Exception as e:  # noqa: BLE001
            self.fail(f"R8.walk-road: {type(e).__name__} instead of CheckRefused ({words!r}): {str(e)[:200]}")
        self.fail(f"R8.walk-road: not refused ({words!r})")

    def row_needed_case(self, problems, words):
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        path = self.copy() / "transcript.jsonl"
        with mock.patch.object(ct, "check", lambda *a, **k: list(problems)):
            self.refuses(words, ct.check_walk, path, w.row["task"], w.row["half"], "w-0001",
                         wording_script=design.script, design=design)

    def test_the_row_needed_line_is_last(self):
        """W10-R2-3: the row-needed line first and a real problem after it is refused (never strip the real one)."""
        ct = MODS["check_take"]
        self.row_needed_case([ct.TAKE_ROW_NEEDED, "[leak-in-operator-turn] synthetic: a real problem"],
                             "did not end at the ledger binding")

    def test_the_row_needed_line_is_alone(self):
        """W10-R2-3: two row-needed lines are refused, even when the last one is one."""
        ct = MODS["check_take"]
        self.row_needed_case([ct.TAKE_ROW_NEEDED, ct.TAKE_ROW_NEEDED], "did not end at the ledger binding")

    def test_no_ledger(self):
        f = self.copy()
        (f / "driver-ledger.json").unlink()
        got = self.read(f)
        self.assertTrue(any(p.startswith("[session-binding] no driver ledger beside the walk's transcript")
                            for p in got), f"R8.walk-road: {got}")

    def test_no_snapshot(self):
        f = self.copy()
        lines = (f / "transcript.jsonl").read_text().splitlines()
        kept = [l for l in lines if (json.loads(l).get("attachment") or {}).get("type") != "prompt_snapshot"]
        self.assertEqual(len(lines) - len(kept), 1, "R8.walk-road")
        (f / "transcript.jsonl").write_text("\n".join(kept) + "\n")
        self.one_change(f, "[inherited-context] the session recorded no system-prompt snapshot")

    def test_memory_offered(self):
        f = self.copy()
        mark = MODS["check_take"].AUTO_MEMORY_MARK
        n = edit_transcript(f / "transcript.jsonl", attachment("prompt_snapshot", lambda a: a.update(
            text=a["text"] + f" Synthetic: the {mark} section.")))
        self.assertEqual(n, 1, "R8.walk-road")
        self.one_change(f, "[inherited-context] the session was offered the harness's persistent memory folder")

    def test_the_design_refusals(self):
        """W10-R2-1: each of check4_walk's design refusals, one bad input at a time, refused by its own words."""
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        path = self.copy() / "transcript.jsonl"
        other = "normal" if w.row["half"] == "trap" else "trap"
        args = dict(wording_script=design.script, arm=w.row["arm"], design=design)
        cases = (
            ("non-empty list", w.row["half"], dict(args, wording_script=[])),
            ("checked against its design view", w.row["half"], dict(args, design=object())),
            ("names no half or no wording script", w.row["half"], dict(args, design=design.replace(half=None))),
            ("names no half or no wording script", w.row["half"], dict(args, design=design.replace(script=None))),
            # moved by T4 R-1 (plan v4 section 5): harness_guard's refusal is reworded
            ("check4 reads claude-code only", w.row["half"],
             dict(args, design=design.replace(harness="synthetic-harness"))),
            ("still PENDING", w.row["half"], dict(args, design=design.replace(pending=("synthetic",)))),
            ("the design view is", other, args),
            ("the design view is", w.row["half"], dict(args, design=design.replace(task_id="synthetic-other-task"))),
            ("the script handed in", w.row["half"],
             dict(args, wording_script=list(design.script) + [dict(design.script[-1], n=99)])),
            ("names no run tree", w.row["half"], dict(args, design=design.replace(run_tree=None))),
            ("event ids", w.row["half"], dict(args, table={"checker_reasons_become_events": {"ids": ["synthetic"]}})),
        )
        for words, half, kw in cases:
            with self.subTest(words=words):
                self.refuses(words, ct.check4_walk, path, w.row["task"], half, "w-0001", **kw)

    def test_the_reason_id_refusal(self):
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        with mock.patch.object(ct, "check_walk", lambda *a, **k: ["synthetic: a problem with no reason id"]):
            self.refuses("no reason id", ct.check4_walk, self.copy() / "transcript.jsonl", w.row["task"],
                         w.row["half"], "w-0001", wording_script=design.script, arm=w.row["arm"], design=design)

    def test_the_event_disagreement_refusal(self):
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        ids = ct.event_ids(None)
        with mock.patch.object(ct, "event_counts", lambda path: {e: int(i == 0) for i, e in enumerate(ids)}):
            self.refuses("disagree", ct.check4_walk, self.copy() / "transcript.jsonl", w.row["task"],
                         w.row["half"], "w-0001", wording_script=design.script, arm=w.row["arm"], design=design)

    def test_an_operator_line_never_sent(self):
        """W10-R3-1: a fault only check() sees (the last scripted prompt missing) reaches check4_walk's result."""
        f = self.copy()
        lines = (f / "transcript.jsonl").read_text().splitlines()
        users = [i for i, l in enumerate(lines) if json.loads(l).get("type") == "user"
                 and isinstance((json.loads(l).get("message") or {}).get("content"), str)]
        del lines[users[-1]]
        (f / "transcript.jsonl").write_text("\n".join(lines) + "\n")
        got = self.read(f)
        self.assertTrue(any(p.startswith("[operator-lines]") for p in got), f"R8.walk-road: {got}")

    def test_an_operator_line_improvised(self):
        """W10-R3-1: an extra prompt the script never sent reaches check4_walk's result."""
        f = self.copy()
        lines = (f / "transcript.jsonl").read_text().splitlines()
        users = [i for i, l in enumerate(lines) if json.loads(l).get("type") == "user"
                 and isinstance((json.loads(l).get("message") or {}).get("content"), str)]
        rec = json.loads(lines[users[-1]])
        rec["message"]["content"] = "Synthetic: one more instruction the script never sent."
        lines.append(json.dumps(rec))
        (f / "transcript.jsonl").write_text("\n".join(lines) + "\n")
        got = self.read(f)
        self.assertTrue(any(p.startswith("[operator-lines]") for p in got), f"R8.walk-road: {got}")

    def test_a_fixture_fault(self):
        """W10-R3-1: the ledger's fixture record off the half's pinned fixture is check()'s fixture-binding."""
        f = self.copy()
        edit_json(f / "driver-ledger.json", fixture={"sha256": "f" * 64})
        got = self.read(f)
        self.assertTrue(any(p.startswith("[fixture-binding]") for p in got), f"R8.walk-road: {got}")

    def test_a_check_fault_reaches_check_json_through_the_drive(self):
        """W10-R3-1: a walk whose driver built another fixture, driven end to end: check()'s fixture-binding is in
        its check.json."""
        with study(identity_over={"fixture": {"sha256": "f" * 64}}) as w:
            got = self.must("R8.walk-road", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R8.walk-road: {got}")
            check = json.loads((folder_of(w, "w-0001") / "check.json").read_text())
            self.assertIn("fixture-binding", check["checker_reasons"], f"R8.walk-road: {check}")

    def test_the_clean_walk_reads_clean(self):
        self.assertEqual(self.read(self.copy()), [], "R8.walk-road: the clean walk is not clean")

    def test_the_row_needed_line_is_asserted(self):
        ct = MODS["check_take"]
        real = "[leak-in-operator-turn] synthetic: a real problem standing where the row-needed line was"
        design = self.w.design_for(self.w.row, str(self.w.tree))
        path = self.copy() / "transcript.jsonl"
        with mock.patch.object(ct, "check", lambda *a, **k: [real]):
            with self.assertRaises(ct.CheckRefused, msg="R8.walk-road: a stripped real problem passed"):
                ct.check_walk(path, self.w.row["task"], self.w.row["half"], "w-0001", wording_script=design.script,
                              design=design)

    def test_the_ledger_cell(self):
        f = self.copy()
        other = "normal" if self.w.row["half"] == "trap" else "trap"
        edit_json(f / "driver-ledger.json", half=other)
        edit_json(f / "environment.json", half=other)          # the forged ledger's own record agrees with it
        rebind_environment(f)
        self.one_change(f, "[session-binding] the driver ledger is ")

    def test_the_ledger_row(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", row=0)
        self.one_change(f, "[session-binding] the driver ledger records a ledger row")

    def test_the_ledger_row_commit(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", row_commit="c" * 40)
        self.one_change(f, "[session-binding] the driver ledger records a ledger row")

    def test_the_environment_record(self):
        f = self.copy()
        edit_json(f / "environment.json", written_before_first_turn=False)
        rebind_environment(f)
        self.one_change(f, "[environment-record] environment.json does not record that it was written before")

    def test_the_environment_row(self):
        f = self.copy()
        edit_json(f / "environment.json", row=0)
        rebind_environment(f)
        self.one_change(f, "[environment-record] the environment record names a ledger row")

    def test_the_environment_row_commit(self):
        f = self.copy()
        edit_json(f / "environment.json", row_commit="c" * 40)
        rebind_environment(f)
        self.one_change(f, "[environment-record] the environment record names a ledger row")

    def test_the_model(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", model_requested="claude-synthetic-other-model")
        edit_json(f / "environment.json", model_requested="claude-synthetic-other-model")
        rebind_environment(f)
        self.one_change(f, "[model-binding] ")

    def test_no_model(self):
        f = self.copy()
        led = json.loads((f / "driver-ledger.json").read_text())
        led.pop("model_requested")
        (f / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
        edit_json(f / "environment.json", model_requested=None)
        rebind_environment(f)
        self.one_change(f, "[session-binding] the driver ledger names no model")

    def test_the_constants(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", budget_s=1)
        self.one_change(f, "[constant-binding] the take ran with a 1s turn budget")

    def test_the_walk_records_the_digest_of_the_constants_its_checker_read(self):
        """Review MINOR 3: check.json carries the digest of the constants the walk was checked under (the rig's
        constants here, not production's)."""
        ct = MODS["check_take"]
        check = json.loads((self.folder / "check.json").read_text())
        self.assertEqual(check["checker_constants_sha256"], ct.checker_constants_sha256(self.w.constants))
        self.assertNotEqual(check["checker_constants_sha256"], ct.checker_constants_sha256())

    def test_the_walk_records_its_no_output_nudge_count(self):
        """glitch-b5's ruling 3 (16 Oct 2026): check.json carries the nudges the checked transcript holds (none in the
        rig's), read through the driver from take_checker; check_record writes the count it is handed, null when the
        checker did not run."""
        check = json.loads((self.folder / "check.json").read_text())
        self.assertIs(type(check["no_output_nudges"]), int)
        self.assertEqual(check["no_output_nudges"], MODS["check_take"].no_output_nudges(self.folder / "transcript.jsonl"))
        wr = MODS["walk_runner"]
        route = lambda records, table: {"route": "rehearsal"}  # noqa: E731
        args = ("w001", {"checker_reasons": []}, {}, route)
        self.assertEqual(wr.check_record(*args, checked=True, no_output_nudges=3,
                                         agent_summary={"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0})["no_output_nudges"], 3)
        self.assertIsNone(wr.check_record(*args, checked=False, no_output_nudges=3)["no_output_nudges"])
        with self.assertRaises(ValueError):           # review r6 MINOR 2: a checked walk is never written with null
            wr.check_record(*args, checked=True)

    def test_the_cap_and_the_poll(self):
        """BOOTSTRAP B4 (15 Oct 2026): check4_walk binds the walk ledger's quiescence cap and poll interval."""
        for key in ("finalize_wait_s", "poll_s"):
            with self.subTest(key=key):
                f = self.copy()
                edit_json(f / "driver-ledger.json", **{key: 1})
                self.one_change(f, f"[constant-binding] the take ran with {key} 1 ")

    def test_the_checkout(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl", attachment("session_context", lambda a: a["context"].update(
            gitStatus=a["context"]["gitStatus"].replace("(clean)", "M synthetic.txt"))))
        self.assertEqual(n, 1, "R8.walk-road")
        self.one_change(f, "[checkout-binding] the session's git status is not the driver's checkout")

    def test_the_instructions(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl", attachment("instructions", lambda a: a["files"][0].update(
            content=a["files"][0]["content"] + "\nSynthetic: a line the pinned tree does not carry.")))
        self.assertEqual(n, 1, "R8.walk-road")
        self.one_change(f, "[checkout-binding] the session loaded ")

    def test_the_permission_mode(self):
        f = self.copy()
        n = edit_transcript(f / "transcript.jsonl",
                            lambda r: dict(r, permissionMode="default") if r.get("type") == "user" else r)
        self.assertTrue(n, "R8.walk-road")
        self.one_change(f, "[constant-binding] the session recorded permission mode(s)")

    def test_the_design_tree(self):
        f = self.copy()
        tree = str(self.w.tree)
        n = edit_transcript(f / "transcript.jsonl", attachment("environment", lambda a: a["snapshot"].update(
            workingDirectory="/synthetic/elsewhere")))
        n += edit_transcript(f / "transcript.jsonl", attachment("instructions", lambda a: [
            x.update(path=x["path"].replace(tree, "/synthetic/elsewhere", 1)) for x in a["files"]]))
        self.assertEqual(n, 2, "R8.walk-road")
        self.one_change(f, "[readers-disagree] the driver gave the take the run tree")

    def test_the_arm(self):
        f = self.copy()
        edit_json(f / "driver-ledger.json", arm="C")
        got = [p for p in self.read(f) if p not in self.read(self.copy())]
        self.assertTrue(any(p.startswith("[constant-binding] the walk's driver ledger records arm") for p in got),
                        f"R8.walk-road: {got}")

    # Fold w10-athena-survivors: the check_take survivors of the athena sweep, each fed its one bad input.
    def read_with(self, folder: Path, design) -> dict:
        w = self.w
        return self.must("R8.walk-road", MODS["check_take"].check4_walk, folder / "transcript.jsonl", w.row["task"],
                         w.row["half"], "w-0001", wording_script=design.script, arm=w.row["arm"], design=design)

    def test_the_design_refusals_read_the_type(self):
        """A wording script of another type (a tuple) and a run tree that is not a non-empty string (a Path, '') are
        refused by their own words, never passed on to a later check."""
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        path = self.copy() / "transcript.jsonl"
        args = dict(wording_script=design.script, arm=w.row["arm"], design=design)
        for words, kw in (("non-empty list", dict(args, wording_script=tuple(design.script))),
                          ("names no run tree", dict(args, design=design.replace(run_tree=Path(design.run_tree)))),
                          ("names no run tree", dict(args, design=design.replace(run_tree="")))):
            with self.subTest(words=words, kw=sorted(kw)):
                self.refuses(words, ct.check4_walk, path, w.row["task"], w.row["half"], "w-0001", **kw)

    def test_no_problem_at_all_is_refused(self):
        """check() returning nothing (no row-needed line) is refused by name, never read past."""
        self.row_needed_case([], "did not end at the ledger binding")

    def test_an_event_is_counted_never_routed(self):
        """A problem whose reason id routing makes an event is counted as that event and kept out of the reasons."""
        ct, w = MODS["check_take"], self.w
        design = w.design_for(w.row, str(w.tree))
        ids = ct.event_ids(None)
        problem = f"[{ids[0]}] synthetic: one instance"
        with mock.patch.object(ct, "check_walk", lambda *a, **k: [problem]), \
                mock.patch.object(ct, "event_counts", lambda path: {e: int(e == ids[0]) for e in ids}):
            got = self.read_with(self.copy(), design)
        self.assertEqual((got["reasons"], got["problems"], got["outside_reach"]), ([], [], 1), f"R8.walk-road: {got}")

    def test_the_design_pre_is_put_back(self):
        """check4_walk sets the design's pre for check() and puts the previous one back: a later check() in the same
        process reads its own pre-registration, never this walk's."""
        ct = MODS["check_take"]
        before = ct._PRE_IN_FORCE.get()
        self.read(self.copy())
        self.assertIs(ct._PRE_IN_FORCE.get(), before, "R8.walk-road: the walk's pre was left in force")

    def test_an_environment_record_that_cannot_be_read(self):
        """No environment record, and one that is not an object: each is environment_problems' line, never a crash
        of the walk's own row check."""
        f = self.copy()
        (f / "environment.json").unlink()
        got = self.read(f)
        self.assertTrue(any(p.startswith("[environment-record] no environment.json") for p in got),
                        f"R8.walk-road: {got}")
        f = self.copy()
        (f / "environment.json").write_text("[]\n")
        rebind_environment(f)
        got = self.read(f)
        self.assertTrue(any(p.startswith("[environment-record] environment.json holds a list") for p in got),
                        f"R8.walk-road: {got}")

    def test_the_environment_row_in_a_record_named_by_the_pre(self):
        """The walk's row check reads the environment record the pre-registration names (its `file`), and the
        default name when the pre carries no environment_record block."""
        import hashlib
        design = self.w.design_for(self.w.row, str(self.w.tree))
        name = "environment-synthetic.json"
        f = self.copy()
        rec = dict(json.loads((f / "environment.json").read_text()), row=0)
        (f / "environment.json").unlink()
        (f / name).write_text(json.dumps(rec, indent=2) + "\n")
        led = json.loads((f / "driver-ledger.json").read_text())
        led["environment"] = dict(led["environment"], file=name,
                                  sha256=hashlib.sha256((f / name).read_bytes()).hexdigest())
        (f / "driver-ledger.json").write_text(json.dumps(led, indent=2) + "\n")
        pre = dict(design.pre, environment_record=dict(design.pre["environment_record"], file=name))
        got = self.read_with(f, design.replace(pre=pre))["problems"]
        self.assertIn("[environment-record] the environment record names a ledger row for a walk; a walk has none",
                      got, f"R8.walk-road: {got}")
        f = self.copy()
        edit_json(f / "environment.json", row=0)
        rebind_environment(f)
        pre = {k: v for k, v in design.pre.items() if k != "environment_record"}
        got = self.read_with(f, design.replace(pre=pre))["problems"]
        self.assertIn("[environment-record] the environment record names a ledger row for a walk; a walk has none",
                      got, f"R8.walk-road: {got}")

    def test_the_design_tree_through_the_drive(self):
        """The machinery (W10-R1-1, root cause 1): the check_take the drive imports is this module's MODS entry, a
        witness included, and a walk driven through the drive in another tree than its own is read by the walk road
        as readers-disagree, in its check.json."""
        import sys as _sys
        self.assertIs(_sys.modules.get("check_take"), MODS["check_take"],
                      "R8.walk-road: the drive would import another check_take than the one under test")
        with study(opened_in="/synthetic/elsewhere") as w:
            got = self.must("R8.walk-road", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R8.walk-road: {got}")
            check = json.loads((folder_of(w, "w-0001") / "check.json").read_text())
            self.assertIn("readers-disagree", check["checker_reasons"], f"R8.walk-road: {check}")


# ------------------------------------------------------------------------------------------------- R9
class R9RealGrade(Case):
    def test_the_real_grader_reads_a_fake_walk(self):
        """Q-w10-1: the fake sidecar watches the half's planted paths, and the REAL v4 grader grades the walk end to
        end; run.py's regrade (the real grader again) gives grade.json's bytes."""
        with study(watch_planted=True) as w:
            with tbi.spying(w.spy):
                got = self.must("R9.real-grade", MODS["walk_runner"].run_walks, w.driver, w.repo, [w.walk("w-0001")],
                                table=w.table)
            self.assertEqual([g.get("state") for g in got], ["committed"], f"R9.real-grade: {got}")
            grade = json.loads((folder_of(w, "w-0001") / "grade.json").read_text())
            self.assertTrue(grade["graded"], "R9.real-grade")
            self.assertEqual(grade["grade"].get("graded_by"), f"graders/{w.row['task'].replace('-', '_')}.py",
                             f"R9.real-grade: {grade}")
            self.assertIn(grade["grade"].get("label"), ("misanswered", "declined", "complied", "answered"),
                          f"R9.real-grade: {grade}")
            self.assertEqual(MODS["run"].walk_problems(base=w.root), ([], 1), "R9.real-grade")


# ------------------------------------------------------------------------------------------------- G1
# W10-R3 (ruling w10-R3-fold): the generated mutants (tests/walk_mutation.py) that test_walk_runner does not kill and
# that are equivalent, each with a reason a reviewer can check. `--generated-mutants` fails on a survivor not listed
# here and on a listed one that is killed; G1 fails on an entry that no longer names a generated mutant.
EQUIVALENT: dict = {
    "drive.walk_files:delete:L8:C8:a9b7cb72":
        "order only: `dirs.sort()` orders os.walk's descent; walk_files' list is read as a mapping by path "
        "(TakeRepo._take_files, then sorted) and by content_problems for its refusal alone; no reader uses its order",
    # Fold w10-athena-survivors (athena run gap4-w10-5ff8b2e-20261013T003648Z):
    "walk_runner._publish:delete:L14:C4:e3e767f5":
        "the function's last statement `return None`; deleted, the function falls off its end and returns None",
    "walk_runner._record:delete:L4:C8:e3e767f5":
        "`return None` in the except, the try's last handler; deleted, control leaves the try and falls off the "
        "function's end, which returns None",
    "walk_runner._remove:delete:L7:C4:e3e767f5":
        "the function's last statement `return None`; deleted, the function falls off its end and returns None",
    "walk_runner._run_one:drop-0:L2:C7:2b55246e":
        "run_one, _run_one's only caller, passes walk = row.get('walk') if row is a dict, else None; so whenever "
        "row is not a dict, walk is None and `not isinstance(walk, str)` alone already holds",
    "walk_runner.run_walks:cond-false:L13:C11:aa50c7d9":   # re-anchored: the docstring grew a line (batch 8)
        "the `continue` is the loop body's tail but for the HELD test; a launch-refused state is not HELD, so "
        "without it the loop goes on the same way",
    "walk_runner.run_walks:delete:L13:C8:35f36fd2":
        "the `if launch-refused: continue` is the loop body's tail but for the HELD test; a launch-refused state is "
        "not HELD, so without it the loop goes on the same way",
    "walk_runner.run_walks:delete:L14:C12:93cfda8b":
        "`continue` replaced by `pass` falls to the HELD test, which a launch-refused state never meets, so the loop "
        "goes on the same way",
}


class G1Generated(Case):
    def test_the_equivalent_list_matches_the_generated_mutants(self):
        import walk_mutation
        ids = set(walk_mutation.by_id())
        self.assertGreater(len(ids), 0, "G1.generated: the generator produced nothing")
        stale = sorted(set(EQUIVALENT) - ids)
        self.assertEqual(stale, [], "G1.generated: EQUIVALENT entries that name no generated mutant")
        bare = sorted(k for k, why in EQUIVALENT.items() if not isinstance(why, str) or len(why.strip()) < 12)
        self.assertEqual(bare, [], "G1.generated: EQUIVALENT entries without a reason")


# Under --gen-mutant the classes run cheapest first, so failfast meets a kill as early as it can. R8WalkRoad drives one
# walk for all its tests, so it runs before R4Held and R3DeadWalk, which drive one or more walks per test.
class R12Pending(Case):
    """Registration review finding 2 (glitch-06, 14 Oct 2026): a walk whose drive stops on a pending native
    cross-check (its ledger recording it, its containers removed) is committed ungraded as pending-native-reader, with
    the pending check and grade documents, and the runner moves on; the same stop with a container left is held; any
    other drive error is held as before. The stand-in: the Claude walk's own drive, its ledger then marked pending and
    the driver module's NativeCrossCheckPending raised, as the driver raises it for a vendor take after its scan
    (the vendor road itself, end to end, is tests/test_pending_walk.py)."""

    WHY = "no reviewed native-session reader (a stand-in)"

    def pend(self, w, *, other=False):
        real = w.driver.drive

        def drive(row, cid):
            real(row, cid)
            path = folder_of(w, row["walk"]) / "driver-ledger.json"
            ledger = json.loads(path.read_text())
            ledger["cross_check_status"] = {"status": "pending", "why": self.WHY}
            path.write_text(json.dumps(ledger, indent=2) + "\n")
            if other:
                raise w.mod.DriveRefused("a stand-in refusal that is not a pending cross-check")
            raise w.mod.NativeCrossCheckPending(f"native cross-check pending ({self.WHY})")
        w.driver.drive = drive

    def test_a_pending_walk_is_committed_ungraded_and_the_runner_moves_on(self):
        with study() as w:
            self.pend(w)
            got = self.must("R12.pending", w.run_walks, [w.walk("w-0001"), w.walk("w-0002")])
            self.assertEqual([g.get("state") for g in got], ["pending-native-reader"] * 2, f"R12.pending: {got}")
            self.assertEqual([g.get("graded") for g in got], [False, False], "R12.pending")
            folder = folder_of(w, "w-0001")
            self.assertEqual(json.loads((folder / "grade.json").read_text()),
                             {"graded": False, "status": "pending-native-reader",
                              "why": f"not graded, because its native cross-check is pending: {self.WHY}"},
                             "R12.pending")
            self.assertEqual(json.loads((folder / "check.json").read_text()),
                             {"walk": "w-0001", "status": "pending-native-reader", "why": self.WHY}, "R12.pending")
            self.assertEqual(register_check(w)[0], [], "R12.pending")
            self.assertEqual(tbi.git(w.root, "log", "-1", "--format=%s"), "Commit one walk; never counted",
                             "R12.pending")

    def test_a_pending_walk_whose_container_stays_is_held(self):
        with study() as w:
            self.pend(w)

            def remove(cid):
                raise RuntimeError("a stand-in removal failure")
            w.driver.remove = remove
            got = self.must("R12.pending", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R12.pending: {got}")
            self.assertIn("NativeCrossCheckPending", got[0]["why"], "R12.pending")
            self.assertTrue(got[0]["why"].endswith("the walk folder is left for a human, never committed"),
                            f"R12.pending: {got[0]['why']}")

    def test_any_other_drive_error_is_held_as_before(self):
        with study() as w:
            self.pend(w, other=True)
            got = self.must("R12.pending", w.run_walks, [w.walk("w-0001")])
            self.assertEqual([g.get("state") for g in got], ["held"], f"R12.pending: {got}")
            self.assertTrue(got[0]["why"].endswith("the walk folder is left for a human, never committed"),
                            f"R12.pending: {got[0]['why']}")


GENERATED_ORDER = ("R13Recheck", "R11Units", "R10Guards", "R6Cli", "R7Slot", "G1Generated", "R8WalkRoad", "R4Held",
                   "R12Pending",
                   "R3DeadWalk", "R2WalkCheck", "R1Chain", "R5Round3", "R9RealGrade", "TestSysPath")


def run_generated(shard=None, sample=None, timeout=600, only=None) -> int:
    """Every generated mutant (or shard i of n, or every k-th of them), each in its own process running the whole
    test module with failfast: killed when any test fails by assertion. Exit 0 only when every survivor is listed
    in EQUIVALENT and no listed one was killed (within the mutants run)."""
    import walk_mutation
    mutants_all, dropped = walk_mutation.generate()
    chosen = list(enumerate(mutants_all))
    if shard:
        i, n = shard
        chosen = [(k, m) for k, m in chosen if k % n == i - 1]
    if sample:
        chosen = chosen[::sample]
    if only is not None:
        chosen = [(k, m) for k, m in chosen if m.id in only]
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_runner generated mutants", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), *GENERATED_ORDER],
                                    timeout=timeout, tag="test_walk_runner")
    killed, survived, equivalent, listed_killed, inconclusive = [], [], [], [], []
    def one(mid, fast):
        argv = [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--gen-mutant", mid]
        got = subprocess.run(argv + (["--failfast"] if fast else []), capture_output=True, text=True,
                             timeout=timeout)
        record = re.findall(r"^test_walk_runner outcomes: (\{.*\})$", got.stdout, re.M)
        return got, (json.loads(record[-1]) if record else None)

    for _, m in chosen:
        try:
            got, outcome = one(m.id, True)
            if outcome is not None and not outcome["failures"] and outcome["errors"]:
                got, outcome = one(m.id, False)    # failfast stopped at an error: run the whole module
        except subprocess.TimeoutExpired:
            inconclusive.append(m.id)
            print(f"generated {m.id}: TIMEOUT (inconclusive)", flush=True)
            continue
        if outcome is None:
            inconclusive.append(m.id)
            print(f"generated {m.id}: NO OUTCOME (rc {got.returncode})\n{got.stderr[-1500:]}", flush=True)
            continue
        is_killed = bool(outcome["failures"])
        state = "KILLED" if is_killed else "SURVIVED"
        if is_killed:
            killed.append(m.id)
            if m.id in EQUIVALENT:
                listed_killed.append(m.id)
        elif m.id in EQUIVALENT:
            equivalent.append(m.id)
            state = "EQUIVALENT"
        else:
            survived.append(m.id)
        print(f"generated {m.id}: {state} by {outcome['failures'][:1]} (errors {len(outcome['errors'])}) "
              f"[{m.kind} at line {m.line}: {m.original[:60]!r} -> {m.replacement[:40]!r}]", flush=True)
    print(f"test_walk_runner generated mutants: {len(mutants_all)} generated ({dropped} dropped, not compiling), "
          f"{len(chosen)} run, {len(killed)} killed, {len(equivalent)} equivalent (listed), {len(survived)} "
          f"survived unlisted, {len(listed_killed)} listed but killed, {len(inconclusive)} inconclusive", flush=True)
    for name, ids in (("SURVIVED (unlisted)", survived), ("LISTED BUT KILLED", listed_killed),
                      ("INCONCLUSIVE", inconclusive)):
        for x in ids:
            print(f"  {name}: {x}", flush=True)
    return 0 if not survived and not listed_killed and not inconclusive else 1


class R10Guards(Case):
    """The walk road's argument guards, without a walk (round 3's generated sample: they had no test)."""

    def test_the_runner_takes_a_walk_driver_and_its_own_walk_repo(self):
        wr = MODS["walk_runner"]
        root = Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()
        driver = types.SimpleNamespace(records="walks", records_root=root)
        repo = types.SimpleNamespace(root=root, commit_walk=lambda entry: None)
        for d, r, why in ((types.SimpleNamespace(records="takes", records_root=root), repo, "a take driver"),
                          (types.SimpleNamespace(records_root=root), repo, "a driver with no records"),
                          (driver, types.SimpleNamespace(root=root), "a repo that commits no walk"),
                          (driver, types.SimpleNamespace(root=root / "x", commit_walk=lambda e: None),
                           "a repo over another folder")):
            with self.subTest(why=why):
                try:
                    wr.run_walks(d, r, [])
                    self.fail(f"R10.guards: run_walks accepted {why}")
                except TypeError:
                    pass
                except AssertionError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.fail(f"R10.guards: {why}: {type(e).__name__} instead of TypeError: {e}")
        self.assertEqual(self.must("R10.guards", wr.run_walks, driver, repo, [], table={}), [], "R10.guards")

    def test_a_walk_session_id_needs_a_walk_id(self):
        ct = MODS["check_take"]
        for bad in (None, "", 5):
            with self.subTest(walk=bad):
                try:
                    ct.walk_session_id(bad)
                    self.fail(f"R10.guards: walk_session_id({bad!r}) gave a session id")
                except ct.CheckRefused:
                    pass
                except AssertionError:
                    raise
                except Exception as e:  # noqa: BLE001
                    self.fail(f"R10.guards: walk_session_id({bad!r}): {type(e).__name__} instead of CheckRefused")

    def test_remove_by_the_recorded_id(self):
        wr = MODS["walk_runner"]
        seen = []
        self.assertIsNone(wr._remove(types.SimpleNamespace(remove=seen.append), None), "R10.guards")
        self.assertEqual(seen, [], "R10.guards: a missing container id was removed")
        self.assertIsNone(wr._remove(types.SimpleNamespace(remove=seen.append), "c1"), "R10.guards")
        self.assertEqual(seen, ["c1"], "R10.guards")
        boom = RuntimeError("synthetic: removal failed")

        def fail(cid):
            raise boom
        self.assertIs(wr._remove(types.SimpleNamespace(remove=fail), "c2"), boom, "R10.guards")


# ------------------------------------------------------------------------------------------------- R11
# Fold w10-athena-survivors (athena run gap4-w10-5ff8b2e-20261013T003648Z): the walk road's functions one at a time,
# without a walk. The generated sweep left 101 survivors in five classes: run.py's walk readers and drive.walk_files
# had no direct test of their refusals (each was reached only on its clean road); type guards were only ever handed
# the right type; the runner's launch-failure, removal-failure, wrong-check-file and grade-refusal roads had no test;
# a few values were never read back (the walk id in the result, a failed deletion's reason, a route refusal's text);
# and run_walks was never handed two walks that both commit. Each test here feeds the bad input directly and reads
# the exact refusal, so each kill is by assertion.
def stub_driver(root: Path, *, walk_check=None, launch=None, drive=None, remove=None, published=None,
                nudges=lambda row: 0,
                agents=lambda row: {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}):
    """A walk driver stand-in whose class's launch carries the namespace walk_runner.driver_namespace reads (the drive
    module's LaunchRefused, NativeCrossCheckPending (the pending-walk road, batch-8 review finding 2) and WALK_CHECK,
    or another WALK_CHECK)."""
    g = {"__name__": "synthetic_drive", "LaunchRefused": MODS["drive"].LaunchRefused,
         "NativeCrossCheckPending": MODS["drive"].NativeCrossCheckPending,
         "WALK_CHECK": MODS["drive"].WALK_CHECK if walk_check is None else walk_check}
    exec("class StubDriver:\n    def launch(self, row):\n        return self.on_launch(row)\n", g)
    d = g["StubDriver"]()
    d.records, d.records_root, d.calls = "walks", root, []

    def note(name, fn):
        def call(*a):
            d.calls.append((name,) + a)
            return fn(*a)
        return call
    d.on_launch = note("launch", launch or (lambda row: "c1"))
    d.drive = note("drive", drive or (lambda row, cid: {"checker_reasons": [], "events": {}}))
    d.remove = note("remove", remove or (lambda cid: None))
    d.published = note("published", published or (lambda row, n: None))
    if nudges is not None:                     # review r6 MINOR 2: the count a checker that ran hands over
        d.no_output_nudges = nudges
    if agents is not None:                     # the Agent parity ruling, part 6: the Agent record it hands over
        d.agent_summary = agents
    return d


def raiser(exc):
    def fn(*a):
        raise exc
    return fn


class R11Units(Case):
    """Each walk-road function fed one bad input directly; the refusal is read by its type and its words."""

    def raising(self, exc, words, fn, *args, **kwargs):
        try:
            fn(*args, **kwargs)
        except exc as e:
            self.assertIn(words, str(e), f"R11.units: refused for another reason: {e}")
            return e
        except AssertionError:
            raise
        except Exception as e:  # noqa: BLE001
            self.fail(f"R11.units: {type(e).__name__} instead of {exc.__name__} ({words!r}): {str(e)[:300]}")
        self.fail(f"R11.units: nothing raised ({words!r})")

    def scratch(self) -> Path:
        return Path(tempfile.mkdtemp(dir=tbi.SCRATCH)).resolve()

    # ---- run.walk_row, run.grade_walk
    ENTRY = {"walk": "w-0001", "task": "synthetic-task", "half": "trap", "wording": "w1", "arm": "C",
             "model": "claude-synthetic"}
    LEDGER = {"task": "synthetic-task", "half": "trap", "wording": "w1", "arm": "C", "model_requested": "claude-synthetic",
              "pressure": "low", "repeat": None, "agent": {"name": "synthetic"}, "project": "synthetic-project",
              "first_agent_turn": True, "outcome": "synthetic-outcome"}

    def test_walk_row_binds_the_ledger(self):
        run = MODS["run"]
        got = self.must("R11.units", run.walk_row, dict(self.ENTRY), dict(self.LEDGER))
        self.assertEqual(got, {"task": "synthetic-task", "half": "trap", "wording": "w1", "arm": "C",
                               "model": "claude-synthetic", "agent": {"name": "synthetic"},
                               "project": "synthetic-project", "pressure": "low", "repeat": None}, "R11.units")
        for key, led in (("task", "task"), ("half", "half"), ("wording", "wording"), ("arm", "arm"),
                         ("model", "model_requested")):
            with self.subTest(key=key):
                self.raising(ValueError, f"records {led} 'synthetic-other'", run.walk_row, dict(self.ENTRY),
                             dict(self.LEDGER, **{led: "synthetic-other"}))
        for gone in ("pressure", "repeat"):
            with self.subTest(gone=gone):
                led = dict(self.LEDGER)
                led.pop(gone)
                self.raising(ValueError, f"records no {gone}", run.walk_row, dict(self.ENTRY), led)
        for pressure, repeat in ((None, None), ("low", 2)):
            with self.subTest(pressure=pressure, repeat=repeat):
                self.raising(ValueError, "exactly one of them is None", run.walk_row, dict(self.ENTRY),
                             dict(self.LEDGER, pressure=pressure, repeat=repeat))
        self.raising(ValueError, "is not the one the walk's driver ledger records", run.walk_row, dict(self.ENTRY),
                     dict(self.LEDGER), {"pressure": "high", "repeat": None})
        self.assertEqual(self.must("R11.units", run.walk_row, dict(self.ENTRY), dict(self.LEDGER),
                                   {"pressure": "low", "repeat": None})["pressure"], "low", "R11.units")

    def test_grade_walk_reads_a_folder_by_any_path_and_the_first_turn(self):
        run = MODS["run"]
        folder = self.scratch()
        (folder / "driver-ledger.json").write_text(json.dumps(self.LEDGER))
        got = self.must("R11.units", run.grade_walk, dict(self.ENTRY), str(folder), grade=lambda row, f: {"g": 1})
        self.assertEqual((got.get("graded"), got.get("grade")), (True, {"g": 1}), f"R11.units: {got}")
        (folder / "driver-ledger.json").write_text(json.dumps(dict(self.LEDGER, first_agent_turn=False, task="x")))
        got = self.must("R11.units", run.grade_walk, dict(self.ENTRY), folder, grade=lambda row, f: {"g": 1})
        self.assertEqual(got, {"graded": False, "why": "no first agent turn, so a rehearsal before the agent's first "
                                                       "turn (the routing table's first row): synthetic-outcome"},
                         "R11.units")

    def test_grade_walk_refuses_a_vendor_walk_not_cross_checked(self):
        """Battery 388e7476 shard 5's survivor run.grade_walk:delete:L17:C4 (the vendor_admission call deleted):
        grade_walk on a codex or a gemini walk whose driver ledger records no agreeing native cross-check, or whose
        readers hold no reader for its harness, is refused by vendor admission's own refusal (its type and words),
        and the grade stand-in is never called; the agreed cross-check with a registered reader, and a claude-code
        walk with neither, are graded. No subTest: --witnesses' rule B needs the one failure the first case makes."""
        run = MODS["run"]
        agreed = {"status": "agreed", "why": None}

        def reader(raw, ordinal):
            raise AssertionError("R11.units: grading called the stand-in reader")
        for harness in ("codex", "gemini"):
            registered = {harness: reader}
            for why, readers, cross, words in (
                    ("no cross-check recorded", registered, None, "the native cross-check is None"),
                    ("a refused cross-check", registered, {"status": "refused", "why": "a synthetic refusal"},
                     "the native cross-check is {'status': 'refused'"),
                    ("no reader for its harness", {}, agreed, f"no registered {harness} native reader")):
                folder = self.scratch()
                ledger = dict(self.LEDGER, agent={"name": "synthetic", "harness": harness})
                if cross is not None:
                    ledger["cross_check_status"] = cross
                (folder / "driver-ledger.json").write_text(json.dumps(ledger))
                graded = []
                e = self.raising(run.VendorAdmissionRefused, words, run.grade_walk, dict(self.ENTRY), folder,
                                 grade=lambda row, f: graded.append(row) or {"g": 1}, readers=readers)
                self.assertIn(f"harness {harness!r}", str(e), f"R11.units: {e}")
                self.assertEqual(graded, [], f"R11.units: the grade ran for a {harness} walk with {why}")
            folder = self.scratch()
            (folder / "driver-ledger.json").write_text(json.dumps(dict(
                self.LEDGER, agent={"name": "synthetic", "harness": harness}, cross_check_status=agreed)))
            got = self.must("R11.units", run.grade_walk, dict(self.ENTRY), folder, grade=lambda row, f: {"g": 1},
                            readers=registered)
            self.assertEqual((got.get("graded"), got.get("grade")), (True, {"g": 1}), f"R11.units: {got}")
        folder = self.scratch()
        (folder / "driver-ledger.json").write_text(json.dumps(dict(
            self.LEDGER, agent={"name": "synthetic", "harness": "claude-code"})))
        got = self.must("R11.units", run.grade_walk, dict(self.ENTRY), folder, grade=lambda row, f: {"g": 1},
                        readers={})
        self.assertEqual((got.get("graded"), got.get("grade")), (True, {"g": 1}), f"R11.units: {got}")

    # ---- run.died_before_turn_one
    def dead(self, files: dict) -> Path:
        folder = self.scratch()
        for name, doc in files.items():
            (folder / name).write_text(doc if isinstance(doc, str) else json.dumps(doc))
        return folder

    def test_died_before_turn_one_says_why(self):
        run = MODS["run"]
        said = lambda files: self.must("R11.units", run.died_before_turn_one, self.dead(files))  # noqa: E731
        self.assertEqual(said({"refusal.json": {"refused": "synthetic-check", "why": "synthetic reason"}}),
                         "the walk was refused before its first turn (synthetic-check: synthetic reason)", "R11.units")
        checks = [{"id": "a", "ok": True, "detail": "fine"}, {"id": "b", "ok": False, "detail": "synthetic failure"}]
        self.assertEqual(said({"preflight.json": {"ok": False, "checks": checks}}),
                         "its preflight failed before the first turn (b: synthetic failure)", "R11.units")
        self.assertEqual(said({"preflight.json": {"ok": False}}),
                         "its preflight failed before the first turn (no check named)", "R11.units")
        passed = "its preflight passed and no turn ran, so the driver wrote no ledger"
        self.assertEqual(said({"preflight.json": {"ok": True, "checks": []}}), passed, "R11.units")
        # only transcript.jsonl and turn-N.jsonl say a turn ran
        self.assertEqual(said({"preflight.json": {"ok": True}, "notes.jsonl": "", "turn-notes.txt": ""}), passed,
                         "R11.units")
        self.raising(ValueError, "turn-1.jsonl", run.died_before_turn_one,
                     self.dead({"preflight.json": {"ok": True}, "turn-1.jsonl": ""}))
        self.raising(ValueError, "nothing says why", run.died_before_turn_one, self.dead({}))

    # ---- drive.walk_files
    def walk_folder(self, files) -> Path:
        folder = self.scratch() / "w-0001"
        folder.mkdir()
        for name in files:
            (folder / name).write_text("{}\n")
        return folder

    def test_walk_files_reads_only_a_real_folder_of_regular_files(self):
        drive = MODS["drive"]
        import os
        complete = ("driver-ledger.json", "grade.json", "check.json")
        folder = self.walk_folder(complete)
        got = self.must("R11.units", drive.walk_files, os.path.relpath(folder))
        self.assertEqual(sorted(p for p, _ in got), sorted(str(folder / n) for n in complete),
                         "R11.units: walk_files gave other paths than the folder's absolute ones")
        link = folder.parent / "w-link"
        link.symlink_to(folder)
        self.raising(drive.DriveRefused, "is not a walk folder", drive.walk_files, link)
        self.raising(drive.DriveRefused, "is not a walk folder", drive.walk_files, folder / "grade.json")
        target = folder.parent / "elsewhere.json"
        target.write_text("{}\n")
        linked = self.walk_folder(("driver-ledger.json", "grade.json"))
        (linked / "check.json").symlink_to(target)
        self.raising(drive.DriveRefused, "check.json in the walk folder is not a regular file", drive.walk_files,
                     linked)
        fifo = self.walk_folder(("driver-ledger.json", "grade.json"))
        os.mkfifo(fifo / "check.json")
        self.raising(drive.DriveRefused, "check.json in the walk folder is not a regular file", drive.walk_files,
                     fifo)
        ran = self.walk_folder(("preflight.json", "grade.json", "check.json", "turn-1.jsonl"))
        self.raising(drive.DriveRefused, "holds turn-1.jsonl and no driver-ledger.json", drive.walk_files, ran)

    # ---- drive.walk_identity_problems
    def test_a_walk_identity_of_another_shape_is_refused_by_name(self):
        import prereg
        with mock.patch.object(prereg, "load", tww.REAL_LOAD):     # the real draft's session namespace
            self.identity_cases()

    def identity_cases(self):
        drive = MODS["drive"]
        row = {"walk": "w-0001"}
        for ident in (["synthetic"], "synthetic"):
            with self.subTest(ident=ident):
                self.raising(drive.LaunchRefused, "is not its own", drive.walk_identity_problems,
                             types.SimpleNamespace(identity_for=lambda r, i=ident: i), row)
        e = self.raising(drive.LaunchRefused, "is not its own", drive.walk_identity_problems,
                         types.SimpleNamespace(identity_for=lambda r: {"session_id": "synthetic-sid", "row": None,
                                                                       "row_commit": None}), row)
        self.assertIn("'synthetic-sid'", str(e), "R11.units: the refusal does not show the identity it read")

    # ---- walk_runner
    def test_check_record_and_its_file(self):
        wr = MODS["walk_runner"]
        self.raising(TypeError, "the drive returned no records", wr.check_record, "w-0001", None, None,
                     lambda r, t: {"route": "x"}, checked=True)
        doc = self.must("R11.units", wr.check_record, "w-0001", {"checker_reasons": None, "events": None}, None,
                        raiser(ValueError("synthetic: no route")), checked=False)
        self.assertEqual((doc["checker_reasons"], doc["route"], doc["route_refused"]),
                         ([], None, "ValueError: synthetic: no route"), f"R11.units: {doc}")
        folder = self.scratch()
        self.assertEqual(self.must("R11.units", wr.write_check, folder, doc), folder / "check.json", "R11.units")

    def test_publish_reports_a_failed_deletion_and_touches_no_missing_folder(self):
        wr = MODS["walk_runner"]
        folder = self.scratch()
        (folder / "postflight.json").write_text(json.dumps({"ok": True}))
        (folder / "teardown.json").write_text(json.dumps({"teardown": {}, "problems": []}))
        d = stub_driver(folder, published=raiser(RuntimeError("synthetic: busy")))
        self.assertEqual(self.must("R11.units", wr._publish, d, {}, folder),
                         "the config folder could not be deleted: RuntimeError: synthetic: busy", "R11.units")
        self.assertIsNone(self.must("R11.units", wr._publish, d, {}, folder / "absent"), "R11.units")

    def one(self, d, row, reason="synthetic: a reason", repo=None, route_fn=None):
        wr = MODS["walk_runner"]
        repo = repo or types.SimpleNamespace(commit_walk=lambda entry: {"commit": "c0"})
        return self.must("R11.units", wr.run_one, d, repo, row, reason, table=None,
                         route_fn=route_fn or (lambda r, t: {"route": "synthetic-route"}), grade=None)

    def test_run_one_refuses_a_row_with_no_walk_id_or_reason(self):
        wr = MODS["walk_runner"]
        for row in (None, {"walk": 5, "slot": 5}):
            with self.subTest(row=row):
                d = stub_driver(self.scratch())
                got = self.one(d, row)
                self.assertEqual((got.get("walk"), got.get("state"), got.get("why")),
                                 (None if row is None else 5, wr.LAUNCH_REFUSED, "the walk row names no walk id"),
                                 f"R11.units: {got}")
                self.assertEqual(d.calls, [], "R11.units: a row with no walk id reached the driver")
        d = stub_driver(self.scratch())
        got = self.one(d, {"walk": "w-0001", "slot": "w-0001"}, reason=5)
        self.assertEqual(got.get("state"), wr.LAUNCH_REFUSED, f"R11.units: {got}")
        self.assertIn("has no reason", got.get("why", ""), f"R11.units: {got}")
        self.assertEqual(d.calls, [], "R11.units: a walk with no reason reached the driver")

    def test_a_launch_that_failed_after_making_things_is_held(self):
        wr = MODS["walk_runner"]
        boom = RuntimeError("synthetic: launch broke")
        boom.container_id = "c9"
        row = {"walk": "w-0001", "slot": "w-0001"}
        d = stub_driver(self.scratch(), launch=raiser(boom))
        got = self.one(d, row)
        self.assertEqual((got.get("state"), got.get("why"), got.get("config")),
                         (wr.HELD, "launch failed: RuntimeError: synthetic: launch broke", None), f"R11.units: {got}")
        self.assertIn(("remove", "c9"), d.calls, "R11.units: the launch's container was not removed")
        d = stub_driver(self.scratch(), launch=raiser(boom), remove=raiser(OSError("synthetic: stuck")))
        got = self.one(d, row)
        self.assertEqual(got.get("why"), "launch failed: RuntimeError: synthetic: launch broke; and its container "
                                         "could not be removed: synthetic: stuck", f"R11.units: {got}")

    def test_a_container_that_could_not_be_removed_holds_the_walk(self):
        wr = MODS["walk_runner"]
        d = stub_driver(self.scratch(), remove=raiser(OSError("synthetic: stuck")))
        got = self.one(d, {"walk": "w-0001", "slot": "w-0001"})
        self.assertEqual(got.get("state"), wr.HELD, f"R11.units: {got}")
        self.assertIn("container c1 could not be removed: synthetic: stuck", got.get("why", ""), f"R11.units: {got}")

    def test_a_driver_of_another_check_file_is_refused(self):
        wr = MODS["walk_runner"]
        d = stub_driver(self.scratch(), walk_check="synthetic-check.json")
        self.raising(RuntimeError, "the driver's walk check file is 'synthetic-check.json'", wr.run_one, d,
                     types.SimpleNamespace(commit_walk=lambda e: {"commit": "c0"}), {"walk": "w-0001",
                                                                                     "slot": "w-0001"},
                     "synthetic: a reason", table=None, route_fn=lambda r, t: {"route": "x"}, grade=None)

    def walk_dir(self, root: Path, ledger=None) -> Path:
        folder = root / MODS["mode_binding"].WALKS_DIR / "w-0001"
        folder.mkdir(parents=True)
        if ledger is not None:
            (folder / "driver-ledger.json").write_text(json.dumps(ledger))
        return folder

    def test_a_walk_the_grade_refuses_is_held(self):
        wr = MODS["walk_runner"]
        root = self.scratch()
        self.walk_dir(root)                                  # no ledger, no pre-turn record: grade_walk refuses
        got = self.one(stub_driver(root), {"walk": "w-0001", "slot": "w-0001"})
        self.assertEqual(got.get("state"), wr.HELD, f"R11.units: {got}")
        self.assertIn("the walk was not committed: ValueError", got.get("why", ""), f"R11.units: {got}")

    def test_a_committed_walk_reports_its_grade_and_route(self):
        wr = MODS["walk_runner"]
        root = self.scratch()
        self.walk_dir(root, dict(self.LEDGER, first_agent_turn=False))
        got = self.one(stub_driver(root), dict(self.ENTRY, slot="w-0001"))
        self.assertEqual({k: got.get(k) for k in ("walk", "state", "commit", "graded", "route", "checker_reasons")},
                         {"walk": "w-0001", "state": wr.COMMITTED, "commit": "c0", "graded": False,
                          "route": "synthetic-route", "checker_reasons": []}, f"R11.units: {got}")

    def test_a_checked_walk_without_a_nudge_count_is_held(self):
        """Review r6 MINOR 2 (glitch-b5, 16 Oct 2026): when the checker ran (the ledger is there), a driver that gives
        no count, null, a bool or a negative count holds the walk; nothing is written as check.json or committed."""
        wr = MODS["walk_runner"]
        for name, nudges in (("no count", None), ("null", lambda row: None), ("a bool", lambda row: True),
                             ("a negative count", lambda row: -1)):
            with self.subTest(driver=name):
                root = self.scratch()
                folder = self.walk_dir(root, dict(self.LEDGER, first_agent_turn=False))
                got = self.one(stub_driver(root, nudges=nudges), dict(self.ENTRY, slot="w-0001"))
                self.assertEqual(got.get("state"), wr.HELD, f"R11.units: {got}")
                self.assertIn("nudge count", got.get("why", ""), f"R11.units: {got}")
                self.assertFalse((folder / "check.json").exists(), "R11.units: check.json written for a held walk")
        root = self.scratch()
        folder = self.walk_dir(root, dict(self.LEDGER, first_agent_turn=False))
        got = self.one(stub_driver(root, nudges=lambda row: 2), dict(self.ENTRY, slot="w-0001"))
        self.assertEqual(got.get("state"), wr.COMMITTED, f"R11.units: {got}")
        self.assertEqual(json.loads((folder / "check.json").read_text())["no_output_nudges"], 2)

    def test_a_checked_walk_without_an_agent_record_is_held(self):
        """The Agent parity ruling, part 6 (the d7107255 battery's survivors): when the checker ran, a driver that gives
        no Agent record, null, a list, a bool count or a record without the sub-agent block holds the walk by its own
        words; nothing is written as check.json or committed. A valid record is written as given."""
        wr = MODS["walk_runner"]
        zero = {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}
        for name, agents in (("no record", None), ("null", lambda row: None), ("a list", lambda row: [0]),
                             ("a bool count", lambda row: dict(zero, agent_calls=True)),
                             ("no sub-agent block", lambda row: {"agent_calls": 0}),
                             ("no difference count", lambda row: dict(zero, subagents={"calls": [], "models": []})),
                             ("no nested CLI count", lambda row: {k: v for k, v in zero.items()
                                                                  if k != "nested_cli_calls"})):
            with self.subTest(driver=name):
                root = self.scratch()
                folder = self.walk_dir(root, dict(self.LEDGER, first_agent_turn=False))
                d = stub_driver(root)
                if agents is None:
                    del d.agent_summary
                else:
                    d.agent_summary = agents
                got = self.one(d, dict(self.ENTRY, slot="w-0001"))
                self.assertEqual(got.get("state"), wr.HELD, f"R11.units: {got}")
                self.assertIn("no valid Agent call count", got.get("why", ""), f"R11.units: {got}")
                self.assertFalse((folder / "check.json").exists(), "R11.units: check.json written for a held walk")
        root = self.scratch()
        folder = self.walk_dir(root, dict(self.LEDGER, first_agent_turn=False))
        one = {"agent_calls": 1, "subagents": {"calls": [{"tool_use_id": "t", "agent_id": "a", "is_async": False,
                                                          "status": "completed", "resolved_model": "m",
                                                          "completion": None}],
                                               "models": ["m"], "stream_file_differences": 2}, "nested_cli_calls": 0}
        got = self.one(stub_driver(root, agents=lambda row: one), dict(self.ENTRY, slot="w-0001"))
        self.assertEqual(got.get("state"), wr.COMMITTED, f"R11.units: {got}")
        check = json.loads((folder / "check.json").read_text())
        self.assertEqual((check["agent_calls"], check["subagents"]), (1, one["subagents"]), "R11.units")

    def test_check_record_refuses_each_missing_count_by_its_own_words(self):
        """check_record, fed directly (the d7107255 battery's survivors): a checked walk with a valid Agent record and
        no nudge count is refused for the count, and one with a valid count and no Agent record for the record; an
        unchecked walk writes neither."""
        wr = MODS["walk_runner"]
        route = lambda records, table: {"route": "rehearsal"}  # noqa: E731
        args = ("w001", {"checker_reasons": []}, {}, route)
        zero = {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}
        self.raising(ValueError, "nudge count", wr.check_record, *args, checked=True, agent_summary=zero)
        self.raising(ValueError, "nudge count", wr.check_record, *args, checked=True, no_output_nudges=-1,
                     agent_summary=zero)
        for bad in (None, {"agent_calls": 0}, dict(zero, agent_calls=-1)):
            with self.subTest(agent_summary=bad):
                self.raising(ValueError, "no valid Agent call count", wr.check_record, *args, checked=True,
                             no_output_nudges=0, agent_summary=bad)
        doc = wr.check_record(*args, checked=False, no_output_nudges=0, agent_summary=zero)
        self.assertEqual((doc["agent_calls"], doc["subagents"], doc["no_output_nudges"]), (None, None, None))
        doc = wr.check_record(*args, checked=True, no_output_nudges=0, agent_summary=zero)
        self.assertEqual((doc["agent_calls"], doc["subagents"]), (0, zero["subagents"]))

    def test_run_walks_goes_on_after_a_committed_walk(self):
        wr = MODS["walk_runner"]
        root = self.scratch()
        repo = types.SimpleNamespace(root=root, commit_walk=lambda e: None)
        with mock.patch.object(wr, "run_one", lambda *a, **k: {"state": wr.COMMITTED}):
            got = self.must("R11.units", wr.run_walks, stub_driver(root), repo, [{"row": {}}, {"row": {}}])
        self.assertEqual(len(got), 2, f"R11.units: the runner stopped after a committed walk: {got}")


class TestSysPath(unittest.TestCase):
    def test_the_module_puts_sys_path_back(self):
        """Binding W6M1 (tests/test_wave6_bindings.py) for this module: it imports check_take.py through drive.py and
        test_walk_wiring, so its tearDownModule must leave sys.path exactly as it found it (test_round4 runs every
        module in one process); the wave 6 probe, in a fresh interpreter."""
        import test_wave6_bindings as w6
        with mock.patch.object(subprocess, "run", tbi._REAL["run"]), \
                mock.patch.object(subprocess, "Popen", tbi._REAL["Popen"]):   # the probe's one fresh interpreter
            seen = w6.probe("test_walk_runner")
        self.assertNotIn(str(w6.EVALS), [x for x in seen["after"] if x not in seen["before"]], "W6M1.evals-left")
        self.assertEqual(seen["after"], seen["before"], "W6M1.restored")


BOUND = {"R1.chain": "R1Chain.test_one_walk_end_to_end",
         "R2.walk-check": "R2WalkCheck",
         "R3.dead-walk": "R3DeadWalk.test_a_walk_that_dies_before_turn_one_is_committed_with_its_reason",
         "R4.held": "R4Held",
         "R5.round3": "R5Round3.test_round_3_walks_are_untouched",
         "R6.cli": "R6Cli.test_the_cli_refuses",
         "R7.slot": "R7Slot.test_the_slot_is_the_walk_id",
         "R8.walk-road": "R8WalkRoad",
         "R9.real-grade": "R9RealGrade.test_the_real_grader_reads_a_fake_walk",
         "G1.generated": "G1Generated.test_the_equivalent_list_matches_the_generated_mutants",
         "R10.guards": "R10Guards",
         "R11.units": "R11Units",
         "R12.pending": "R12Pending"}
# R2's and R4's witnesses each name the one method they turn red
METHOD = {"walk-checked-as-take": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-session-unbound": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-ledger-session-unbound": "R2WalkCheck.test_a_walk_is_read_as_a_walk",
          "walk-identity-unchecked": "R2WalkCheck.test_a_take_identity_is_refused_at_launch",
          "launch-refused-stops": "R2WalkCheck.test_a_take_identity_is_refused_at_launch",
          "held-committed": "R4Held.test_a_postflight_refusal_is_never_committed",
          "held-continues": "R4Held.test_a_postflight_refusal_is_never_committed",
          "postflight-config-deleted": "R4Held.test_a_postflight_refusal_is_never_committed",
          "teardown-unread": "R4Held.test_a_failed_teardown_write_still_keeps_the_config_folder",
          "keep-by-default-dropped": "R4Held.test_both_records_refused_keeps_the_config_folder",
          "ledgerless-turns-admitted": "R3DeadWalk.test_a_ledgerless_walk_whose_turns_ran_is_refused",
          "ledgerless-graded": "R3DeadWalk.test_a_ledgerless_walk_whose_turns_ran_is_refused",
          "published-before-launch": "R4Held.test_a_refused_slot_leaves_a_kept_config_folder_alone",
          "walk-identity-row-admitted": "R2WalkCheck.test_a_walk_identity_with_a_row_is_refused",
          "walk-identity-row-commit-admitted": "R2WalkCheck.test_a_walk_identity_with_a_row_is_refused",
          "walk-row-needed-unasserted": "R8WalkRoad.test_the_row_needed_line_is_asserted",
          "walk-ledger-cell-unbound": "R8WalkRoad.test_the_ledger_cell",
          "walk-ledger-row-unbound": "R8WalkRoad.test_the_ledger_row",
          "walk-ledger-row-commit-unbound": "R8WalkRoad.test_the_ledger_row_commit",
          "walk-environment-unread": "R8WalkRoad.test_the_environment_record",
          "walk-environment-row-unbound": "R8WalkRoad.test_the_environment_row",
          "walk-environment-row-commit-unbound": "R8WalkRoad.test_the_environment_row_commit",
          "walk-model-unbound": "R8WalkRoad.test_the_model",
          "walk-model-missing-admitted": "R8WalkRoad.test_no_model",
          "walk-constants-unread": "R8WalkRoad.test_the_constants",
          "walk-checkout-unread": "R8WalkRoad.test_the_checkout",
          "walk-instructions-unread": "R8WalkRoad.test_the_instructions",
          "walk-mode-unread": "R8WalkRoad.test_the_permission_mode",
          "walk-tree-unchecked": "R8WalkRoad.test_the_design_tree",
          "walk-tree-unchecked-through-drive": "R8WalkRoad.test_the_design_tree_through_the_drive",
          "walk-arm-unbound": "R8WalkRoad.test_the_arm",
          "walk-launch-journal-not-a-turn": "R3DeadWalk.test_a_ledgerless_walk_with_only_a_launch_journal_is_refused",
          "pending-walk-held": "R12Pending.test_a_pending_walk_is_committed_ungraded_and_the_runner_moves_on",
          "pending-grade-dropped": "R12Pending.test_a_pending_walk_is_committed_ungraded_and_the_runner_moves_on",
          "pending-removal-unchecked": "R12Pending.test_a_pending_walk_whose_container_stays_is_held",
          "pending-other-errors-admitted": "R12Pending.test_any_other_drive_error_is_held_as_before",
          "walk-vendor-admission-skipped": "R11Units.test_grade_walk_refuses_a_vendor_walk_not_cross_checked"}
METHOD.update(REVIEWER_BOUND)
METHOD.update(REVIEWER3_BOUND)
WITNESSES = {name: (METHOD.get(name, BOUND[m[0]]), m[0]) for name, m in mutants().items()}


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_runner witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_walk_runner")
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        record = re.findall(r"^test_walk_runner outcomes: (\{.*\})$", got.stdout, re.M)
        outcome = json.loads(record[-1]) if record else None
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome) and outcome["failures"] == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_walk_runner witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard = sample = None
        if "--shard" in sys.argv:
            a, b = sys.argv[sys.argv.index("--shard") + 1].split("/")
            shard = (int(a), int(b))
            if not 1 <= shard[0] <= shard[1]:
                raise SystemExit("--shard i/n with 1 <= i <= n")
        if "--sample" in sys.argv:
            sample = int(sys.argv[sys.argv.index("--sample") + 1])
        per = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 600
        only = None
        if "--ids" in sys.argv:
            only = set(Path(sys.argv[sys.argv.index("--ids") + 1]).read_text().split())
        if "--only" in sys.argv:                 # a comma-separated list of generated ids (targeted Mac runs)
            only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
        raise SystemExit(run_generated(shard, sample, per, only))
    failfast = "--failfast" in sys.argv
    if failfast:
        sys.argv.remove("--failfast")
    if "--gen-mutant" in sys.argv:
        index = sys.argv.index("--gen-mutant")
        GENERATED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
        if len(sys.argv) == 1:
            sys.argv += list(GENERATED_ORDER)
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False, failfast=failfast).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_walk_runner: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_runner outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                     "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
