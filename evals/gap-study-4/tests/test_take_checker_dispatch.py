#!/usr/bin/env python3
"""Lane vendor-admission T4 P0 (lane-reports/vendor-T4-PLAN.md v4 section 6, ruled READY by glitch-b5 on Sat 17 Oct
2026, about 12:35 EDT; R-3: edit A is the one drive.py edit, before Javier's acceptance commit): drive.take_checker
asks check_take.checker_for(design) for the take's (entry, side) right after design_for, before any reading of the
take, and a harness with no entry refuses there.

  P0-vendor   a codex and a gemini take, on the real vendor design view (test_vendor_script's), through take_checker
              on the take road and the walk road, with check_take's design_constants_sha256, no_output_nudges,
              agent_summary, check4 and check4_walk patched to raise: CheckRefused, before any of them is called.
  P0-claude   a claude-code take on the real design (test_drive_loop's D8 world): take_checker's checker_reasons,
              checker_events and three side readings equal what check4 (take road) and check4_walk (walk road, a take
              with no identity, as walk_regrade.production_checker builds it) and the three readers return called
              directly, as take_checker called them before edit A; a failed cross-check still adds readers-disagree.
  P0-witness  drive.py compiled in memory with the side readings moved before checker_for, and check_take.py with
              the claude-code entry's two roads swapped, each go red.

Fakes and synthetic strings only, inside test_box_integration's process guard: no model, network, Docker or vendor.
"""

from __future__ import annotations

import contextlib
import io
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_box_integration as tbi  # noqa: E402
import test_checker_body as tcb  # noqa: E402
import test_drive_loop as tdl  # noqa: E402
import test_vendor_script as tvs  # noqa: E402

WALK = "w-0001"
READERS = ("design_constants_sha256", "no_output_nudges", "agent_summary", "check4", "check4_walk")


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def take(folder, cross, *, walk=False):
    if walk:                                   # walk_regrade.production_checker's take: no identity
        return types.SimpleNamespace(folder=str(folder), cross_check=cross)
    return types.SimpleNamespace(folder=str(folder), identity={"row": 0}, cross_check=cross)


def outcome(fn, *a, **kw):
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return ("ok", fn(*a, **kw))
    except Exception as e:  # noqa: BLE001 - the refusal itself is compared
        return ("raised", type(e).__name__, str(e))


def vendor_problems(drive, ct) -> list:
    out = []
    for harness, model, arm in tvs.VENDORS:
        r, design = tvs.vendor_view(ct, harness, model, arm)
        folder = tcb.take_folder(design.script).parent
        called = []

        def reader(name):
            def read(*a, **k):
                called.append(name)
                raise AssertionError(f"{name} read the {harness} take")
            return read
        for records, row in (("takes", r), ("walks", dict(r, walk=WALK))):
            checker = drive.take_checker(design_for=lambda row_, t: design, records=records)
            with contextlib.ExitStack() as st:
                for name in READERS:
                    st.enter_context(mock.patch.object(ct, name, reader(name)))
                got = outcome(checker, row, take(folder, [], walk=records == "walks"), [])
            if got[:2] != ("raised", "CheckRefused") or called:
                out.append(f"{harness} on the {records} road: {got[:3]}, readers called {called}")
            elif harness not in got[2]:
                out.append(f"{harness} on the {records} road: the refusal does not name the harness: {got[2]}")
            called.clear()
    return out


def claude_problems(drive, ct) -> list:
    out = []
    design = tcb.view(ct)
    path = tcb.take_folder(design.script)
    r = tcb.row()
    for records, row in (("takes", r), ("walks", dict(r, walk=WALK))):
        walk = records == "walks"
        for cross in ([], ["the streams and the session file hold different model calls"]):
            t = take(path.parent, cross, walk=walk)
            got = outcome(drive.take_checker(design_for=lambda row_, t_: design, records=records), row, t, [])
            if walk:
                want = outcome(ct.check4_walk, path, r["task"], r["half"], WALK, wording_script=design.script,
                               arm=r["arm"], design=design)
            else:
                want = outcome(ct.check4, path, r["task"], r["half"], 0, False, wording_script=design.script,
                               arm=r["arm"], design=design)
            if want[0] == "ok":
                reasons = list(want[1]["reasons"])
                if cross and drive.READERS_DISAGREE not in reasons:
                    reasons.append(drive.READERS_DISAGREE)
                want = ("ok", {"checker_reasons": reasons, "checker_events": dict(want[1]["events"])})
            if got != want:
                out.append(f"claude-code on the {records} road, cross {cross}: {str(got)[:240]} != {str(want)[:240]}")
            side = (ct.design_constants_sha256(design), ct.no_output_nudges(path), ct.agent_summary(path))
            have = tuple(getattr(t, n, None) for n in ("checker_constants_sha256", "no_output_nudges", "agent_summary"))
            if have != side:
                out.append(f"claude-code on the {records} road: side readings {have} != {side}")
    return out


def compiled(path: str, name: str, edits: tuple) -> types.ModuleType:
    src = Path(path).read_text(encoding="utf-8")
    for old, new in edits:
        if src.count(old) != 1:
            raise tbi.WitnessNotPerformed(f"the anchor occurs {src.count(old)} times: {old[:60]!r}")
        src = src.replace(old, new)
    mod = types.ModuleType(name)
    mod.__file__ = path
    sys.modules[name] = mod
    try:
        exec(compile(src, path + " (witness)", "exec"), mod.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(name, None)
    return mod


SIDE = "        take.checker_constants_sha256, take.no_output_nudges, take.agent_summary = side(path, design)\n"
DISPATCH = "        entry, side = _ct.checker_for(design)"
DRIVE_WITNESS = ((DISPATCH, "        _ct.design_constants_sha256(design), _ct.no_output_nudges(path), "
                            "_ct.agent_summary(path)\n" + DISPATCH),)
TAKE_ROAD = "    return check4(path, row[\"task\"], row[\"half\"], take.identity[\"row\"], False,"
CHECK_TAKE_WITNESS = (("    if records == \"walks\":                # D1: the round-4 walk road\n",
                       "    if records != \"walks\":                # D1: the round-4 walk road\n"),)


class Dispatch(unittest.TestCase):
    def test_p0_vendor_refuses_before_any_reading(self):
        with tdl.checker_world() as ct:
            self.assertEqual(vendor_problems(tbi.drive, ct), [])

    def test_p0_claude_code_reads_as_before(self):
        with tdl.checker_world() as ct:
            self.assertEqual(claude_problems(tbi.drive, ct), [])

    def test_p0_checker_for_admits_claude_code_and_the_vendor_entries(self):
        # moved by T4 P3 (plan v4 section 9, "checker_for admits them"; glitch-b5 round 12): codex and gemini map to
        # the vendor entry and its side, which reads a vendor view only since P5 (tests/test_vendor_constants.py)
        with tdl.checker_world() as ct:
            self.assertEqual(sorted(ct.CHECKER_ENTRIES), ["claude-code", "codex", "gemini"])
            entry, side = ct.checker_for(tcb.view(ct))
            self.assertEqual((entry, side), ct.CHECKER_ENTRIES["claude-code"])
            self.assertEqual((entry, side), (ct._claude_code_entry, ct._claude_code_side))
            for harness in ("codex", "gemini"):
                self.assertEqual(ct.CHECKER_ENTRIES[harness], (ct._vendor_entry, ct._vendor_side))
            for harness in ("synthetic-harness", None):
                with self.subTest(harness=harness), self.assertRaises(ct.CheckRefused):
                    ct.checker_for(types.SimpleNamespace(harness=harness))


class Witnesses(unittest.TestCase):
    def test_p0_witness_the_side_read_before_the_dispatch_goes_red(self):
        mutant = compiled(tbi.drive.__file__, "drive_p0_witness", DRIVE_WITNESS)
        with tdl.checker_world() as ct:
            self.assertNotEqual(vendor_problems(mutant, ct), [], "the drive.py witness stayed green")

    def test_p0_witness_the_claude_code_entry_swapped_goes_red(self):
        with tdl.checker_world() as ct:
            mutant = compiled(ct.__file__, "check_take_p0_witness", CHECK_TAKE_WITNESS)
            mutant.CHECK_HOME = ct.CHECK_HOME
            with mock.patch.dict(sys.modules, {"check_take": mutant}):
                self.assertNotEqual(claude_problems(tbi.drive, mutant), [], "the check_take.py witness stayed green")


if __name__ == "__main__":
    unittest.main()
