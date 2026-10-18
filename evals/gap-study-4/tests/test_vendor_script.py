#!/usr/bin/env python3
"""Lane vendor-admission T0 (glitch-b5, Fri 16 Oct 2026, on Javier's typed word "T0: yes", 22:25 EDT): a Codex or a
Gemini walk gets its operator script from the production design view, and check4 still refuses its take; since T4
(R-1, plan v4 section 5; P3, glitch-b5's round 12) vendor takes are read by the vendor entries through checker_for.

  V0-script   check_take.design_view, the body of walk_builders' production design_for and so of the walk driver's
              script_for (drive.py's walk_driver), builds the view of a codex row (arm O) and of a gemini row (arm G):
              the view's harness is the row's, its script is the wording's own steps (variants.operator_steps), and
              drive.script_from_design renders it. Before T0 both rows raised CheckRefused before turn 1, so even the
              walks that register the vendors' readers could not start.
  V0-checker  check4 and check4_walk on that real vendor view refuse, naming "check4 reads claude-code only" (R4C-9,
              reworded by T4 R-1 from "no record readers"): a script is not a reader, and no vendor take is read with
              Claude Code's readers.
  V0-dispatch drive.take_checker on that view (take and walk roads) reaches check4 only through checker_for: the
              vendor take is handed to the vendor entry's side, never to check4 or check4_walk, and a claude-code take
              reaches check4 or check4_walk through checker_for (T4 R-1's witness).
  V0-unknown  design_view still refuses a harness it has no script for ("synthetic-harness"), naming it.

Witnesses (check_take.py compiled in memory by tests/test_checker_body.py's witness_module, never written):
script-guard-dropped (design_view's harness check made `if False:`; V0-unknown goes red), check4-guard-dropped and
check4-walk-guard-dropped (each checker's harness_guard line removed; V0-checker goes red for that entry), and
vendor-on-claude-entry (checker_for handing a vendor harness claude-code's entry and side; V0-dispatch goes red).

Fakes and synthetic strings only: no model, vendor, network, Docker, credential or holdout. It runs inside
tests/test_checker_body.py's process guard and reuses its draft row, pins and walk constants.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_checker_body as tcb  # noqa: E402

VENDORS = (("codex", "gpt-6.1-sol", "O"), ("gemini", "gemini-3.8-flash", "G"))
WALK_ID = "w-0001"


def setUpModule():
    tcb.setUpModule()


def tearDownModule():
    tcb.tearDownModule()


def vendor_row(harness, model, arm) -> dict:
    """The draft's own row for test_checker_body's cell, made a vendor row (TEST DATA: the arm and model of D8)."""
    r = tcb.row()
    r["agent"]["harness"], r["model"], r["arm"] = harness, model, arm
    return r


def vendor_view(mod, harness, model, arm):
    r = vendor_row(harness, model, arm)
    return r, mod.design_view(r, pin=tcb.pin(harness=harness, model=model), run_tree=tcb.RUN_TREE,
                              constants=tcb.walk_constants(mod))


@tcb.guarded("V0-script")
def v0_script(mod, p):
    import drive
    import variants
    out = []
    for harness, model, arm in VENDORS:
        try:
            r, design = vendor_view(mod, harness, model, arm)
        except mod.CheckRefused as e:
            out.append(f"{p}: design_view refused the {harness} row before turn 1: {e}")
            continue
        want = variants.operator_steps(r["task"], r["half"], r["wording"], pressure=r.get("pressure"))
        if design.harness != harness:
            out.append(f"{p}: the {harness} row's view names harness {design.harness!r}")
        if design.script != want or not want:
            out.append(f"{p}: the {harness} row's view does not carry its wording's own steps")
        lines = drive.script_from_design(design, tcb.project(), tcb.source())
        if len(lines) != len(want) or any("{project}" in s["line"] or "{source}" in s["line"] for s in lines):
            out.append(f"{p}: drive.script_from_design did not render the {harness} row's {len(want)} steps")
    return out


@tcb.guarded("V0-checker")
def v0_checker(mod, p):
    out = []
    for harness, model, arm in VENDORS:
        try:
            _, design = vendor_view(mod, harness, model, arm)
        except mod.CheckRefused as e:
            out.append(f"{p}: no {harness} view to check (design_view refused it: {e})")
            continue
        entries = (
            ("check4", lambda: tcb.quiet(mod.check4, tcb.take_folder(design.script), tcb.TASK, tcb.HALF, 0, False,
                                         wording_script=design.script, arm=arm, design=design)),
            ("check4_walk", lambda: tcb.quiet(mod.check4_walk, tcb.take_folder(design.script), tcb.TASK, tcb.HALF,
                                              WALK_ID, wording_script=design.script, arm=arm, design=design)),
        )
        for name, call in entries:
            try:
                call()
                out.append(f"{p}: {name} read a {harness} take with Claude Code's readers")
            except mod.CheckRefused as e:
                if "check4 reads claude-code only" not in str(e):       # T4 R-1: reworded
                    out.append(f"{p}: {name} refused the {harness} take, but not for its readers: {e}")
    return out


@tcb.guarded("V0-dispatch")
def v0_dispatch(mod, p):
    import contextlib
    import types
    from unittest import mock

    import drive
    out = []
    claude = tcb.view(mod)
    cases = [(h, a, vendor_view(mod, h, m, a)[1]) for h, m, a in VENDORS] + [("claude-code", "A", claude)]
    for harness, arm, design in cases:
        for records in ("takes", "walks"):
            seen = []

            def spy(name, real=None):
                def call(*a, **k):
                    seen.append(name)
                    return real(*a, **k) if real else {"reasons": [], "events": dict.fromkeys(mod.event_ids(), 0)}
                return call
            row = dict(tcb.row(), arm=arm, walk=WALK_ID)
            take = types.SimpleNamespace(folder=str(tcb.take_folder(design.script).parent), identity={"row": 0},
                                         cross_check=[])
            with contextlib.ExitStack() as st:
                st.enter_context(mock.patch.dict(sys.modules, {"check_take": mod}))
                st.enter_context(mock.patch.object(mod, "checker_for", spy("checker_for", mod.checker_for)))
                for name in ("check4", "check4_walk"):
                    st.enter_context(mock.patch.object(mod, name, spy(name)))
                for name, value in (("design_constants_sha256", "0" * 64), ("no_output_nudges", 0),
                                    ("agent_summary", {})):
                    st.enter_context(mock.patch.object(mod, name, lambda *a, value=value, **k: value))
                try:
                    drive.take_checker(design_for=lambda r, t, d=design: d, records=records)(row, take, [])
                    refused = None
                except mod.CheckRefused as e:
                    refused = str(e)
            reached = [n for n in seen if n in ("check4", "check4_walk")]
            if not seen or seen[0] != "checker_for":
                out.append(f"{p}: take_checker did not ask checker_for first on the {harness} {records} road: {seen}")
            if harness != "claude-code" and (reached or refused is None or harness not in refused):
                out.append(f"{p}: a {harness} take on the {records} road reached {reached} (refused: {refused})")
            want = ["check4_walk" if records == "walks" else "check4"]
            if harness == "claude-code" and reached != want:
                out.append(f"{p}: a claude-code take on the {records} road reached {reached}, not {want}")
    return out


@tcb.guarded("V0-unknown")
def v0_unknown(mod, p):
    r = vendor_row("synthetic-harness", tcb.row()["model"], "A")
    try:
        mod.design_view(r, pin=tcb.pin(harness="synthetic-harness", model=r["model"]), run_tree=tcb.RUN_TREE,
                        constants=tcb.walk_constants(mod))
        return [f"{p}: design_view built a view for a harness it has no script for"]
    except mod.CheckRefused as e:
        return [] if "'synthetic-harness'" in str(e) else [f"{p}: the refusal does not name the harness: {e}"]


class TestVendorScript(unittest.TestCase):
    def test_v0_a_vendor_row_gets_its_wordings_script(self):
        self.assertEqual(v0_script(tcb.ct), [])

    def test_v0_check4_still_refuses_a_vendor_take(self):       # renamed by T4 R-1 (plan v4 section 5)
        self.assertEqual(v0_checker(tcb.ct), [])

    def test_v0_take_checker_reaches_check4_only_through_checker_for(self):
        self.assertEqual(v0_dispatch(tcb.ct), [])

    def test_v0_an_unknown_harness_gets_no_script(self):
        self.assertEqual(v0_unknown(tcb.ct), [])


WITNESSES = {
    "script-guard-dropped": ((("    if harness not in HARNESSES_WITH_SCRIPTS:\n", "    if False:\n"),),
                             v0_unknown, "V0-unknown"),
    "check4-guard-dropped": ((("    harness_guard(design.harness)\n    if design.pending:\n",
                               "    if design.pending:\n"),), v0_checker, "V0-checker"),
    "check4-walk-guard-dropped": ((("    harness_guard(design.harness)\n    pending = list(design.pending)\n",
                                    "    pending = list(design.pending)\n"),), v0_checker, "V0-checker"),
    "vendor-on-claude-entry": ((("CHECKER_ENTRIES.update({h: (_vendor_entry, _vendor_side) for h in VENDOR_HARNESSES})",
                                 "CHECKER_ENTRIES.update({h: CHECKER_ENTRIES[CLAUDE_CODE] for h in VENDOR_HARNESSES})"),),
                               v0_dispatch, "V0-dispatch"),
}


class TestVendorScriptWitnesses(unittest.TestCase):
    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(tcb.ct), [], f"{name}: the bound check is not green on check_take.py")
        got = check(tcb.witness_module(edits))
        own = [x for x in got if x.startswith(prefix + ":")]
        errors = [x for x in got if x.startswith("ERROR")]
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_script_guard_dropped(self):
        self.kill("script-guard-dropped")

    def test_witness_check4_guard_dropped(self):
        self.kill("check4-guard-dropped")

    def test_witness_check4_walk_guard_dropped(self):
        self.kill("check4-walk-guard-dropped")

    def test_witness_vendor_on_claude_entry(self):
        self.kill("vendor-on-claude-entry")


if __name__ == "__main__":
    unittest.main(verbosity=2)
