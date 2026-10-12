#!/usr/bin/env python3
"""Lane w6j (Gap Study round 4, slice S6c): the drive loop's agent side, end to end on a FAKE runtime.

S6c is the adapter side of the drive step (s6b-checker-body-plan-2026-10-11, rulings D7 and "S6b hand-back rulings"):
the Claude Code adapter (C15), the marker / recovery / stop loop (C13), the cost read per call (C14), and the records
the checker binds (C6 transcript copy and cross-check, C7 driver-ledger.json, C8 environment.json, the production
checker callable). This module drives drive.py's TakeDriver inside a real batch.Batch over test_box_integration's
FakeBox and Rig (imported, never copied: one fake box for both modules), so every guard here runs on the same
lifecycle S6 and S6b already bound.

What is tested, each guard with its own bound check and a whole-file witness of drive.py compiled in memory
(test_box_integration's registry pattern and its witness compiler):

  D1-table   W6I-R2-2: the confounded-design copy writes the bytes it hashed. A design table rewritten after its
             md5 was read is never what lands in the run tree. Witness: table-reread (round S6b's copyfile, which
             reads the file a second time).
  D2-stop    C13: nothing is sent past an unheld marker; the take is `stopped`, its ledger rows say which line held.
             Witness: continued-past-unheld-marker (the stop removed, so the driver reads on).
  D3-recovery  C13: a step's pre-registered recovery is sent only when the reply holds the recovery's own marker and
             not the step's, at most `at_most` times (once by default), on the same step n; the recovery row is
             recorded after the step row. Witnesses: recovery-never-sent, recovery-unbounded.
  D4-exact   C13: the marker is matched exactly and case-sensitively (round 3's marker_holds). Witness:
             marker-casefold.
  D5-outcome C13: round 3's outcome vocabulary from the host's turn ends: complete, stopped, timed-out (exit 124 on
             the row), aborted after the first agent turn, and before it REHEARSAL, or PAUSE when an API error carries
             routing.json's rate-limit marker. Witness: abort-before-output (a death before any agent output read as
             aborted).
  D6-taxonomy  C13: the stop is classified by pause_adherence (labels4's taxonomy) from the driver's own rows
             (pause_evidence): a reply short of the marker is `stalled`, a turn cut at the budget `timed-out`.
             Witness: turn-ends-dropped (the evidence's turn ends all read end_turn).

Fakes and synthetic strings only: no model, vendor, network, container runtime, credential or holdout. The process
guard, the prereg patches and the PENDING runtime spellings are test_box_integration's own setUpModule.
"""

from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import agent_adapter as aa  # noqa: E402
import test_box_integration as tbi  # noqa: E402
import transcript_view as view  # noqa: E402
from graders import labels4  # noqa: E402
from graders import pause_adherence  # noqa: E402


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


guarded = tbi.guarded


# ------------------------------------------------------------------------------------------------ the bound checks
@guarded("D1-table")
def d1_table(mod, p):
    """W6I-R2-2: the md5 is read once, and the bytes copied in are those bytes."""
    out = tbi.missing_api(mod, p, "TakeDriver", "OPERATOR_STEPS", "DESIGN_TABLE")
    if out:
        return out
    from fixtures import gen_fastq as gf
    table = gf.SAMPLES_CSV_BYTES                     # the fixture's pinned design table (design_table.md5)
    swapped = b"sample_id,condition\nS1,rewritten after the hash\n"
    four = [{"text": "a"}, {"text": "b"}, {"text": "c"}, {"text": "d"}]
    real_md5, seen = hashlib.md5, []
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=four)

        def md5_then_rewrite(data=b"", *a, **kw):
            digest = real_md5(data, *a, **kw)
            if data == table and not seen:           # a concurrent change, after the hash and before any copy
                take = rig.take()
                staging = (Path(take.launched.spec.run_tree) / "data" / "staging" / tbi.PROJECT / "samples.csv")
                staging.write_bytes(swapped)
                seen.append(Path(take.launched.spec.run_tree))
            return digest
        with tbi.project_tree(rig, samples="sample_id,written by stage 00\n", design=table):
            with tbi.planned(tbi.row(1, task="confounded-design")):
                with mock.patch.object(hashlib, "md5", md5_then_rewrite):
                    _, got = tbi.run_batch(rig, [tbi.row(1, task="confounded-design")])
        # The first attempt's run tree (the rewrite routes it harness-error, so batch re-runs the slot once).
        target = (seen[0] if seen else Path("/nonexistent")) / "gars" / "projects" / tbi.PROJECT / "00_data"
        target = target / "rnaseq_bulk" / "samples.csv"
        # The rewrite is itself an unlogged change in the run tree, so the take routes by the operator-diff rows; what
        # is bound here is only which bytes reached the project.
        if not seen:
            out.append(f"{p}: the design table was never hashed ({got[0]['state']}: {got[0]['reason']})")
        elif not target.is_file():
            out.append(f"{p}: nothing was copied in ({got[0]['state']}: {got[0]['reason']})")
        elif target.read_bytes() != table:
            out.append(f"{p}: the run tree holds {target.read_bytes()[:40]!r}, not the bytes whose md5 was checked")
    return out


class LoopAdapter(aa.AgentAdapter):
    """No model: each scripted reply is {text, end?, output?, api_errors?, exit?}; the lines it got are kept."""

    name = "claude-code"

    def __init__(self, box, take, replies):
        super().__init__()
        self.box, self.take, self.replies, self.lines, self.ended = box, take, list(replies), [], 0

    def version(self):
        return tbi.PROFILE["version"]

    def _start(self, take):
        return {"container_id": self.take.launched.take_id}

    def _turn(self, line, *, first, budget_s):
        n = self._turns + 1
        if n > len(self.replies):
            raise aa.AdapterStateError(f"no reply scripted for line {n}: {line!r}")
        self.lines.append(line)
        spec = self.replies[n - 1]
        path = tbi.drive.stream_path(self.take, n)
        started = self.box.tick()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write('{"type": "assistant"}\n')
        end = spec.get("end", labels4.END_TURN)
        code = spec.get("exit", 0 if end == labels4.END_TURN else (None if end == labels4.TIMED_OUT else 1))
        return aa.TurnResult(exit_code=code, text=spec.get("text", ""), stream_path=path, end_reason=end,
                             init={"model": tbi.MODEL, "permission_mode": tbi.PROFILE["permission_mode"],
                                   "version": tbi.PROFILE["version"]},
                             api_errors=list(spec.get("api_errors", [])),
                             counters={"oom_kill_delta": 0, "pids_max_delta": 0},
                             started_at=started, ended_at=self.box.tick(), agent_output=spec.get("output", True))

    def _end(self):
        self.ended += 1


def drive_one(mod, steps, replies):
    """One take driven straight through the driver (launch, drive, remove; no batch, so no re-run): its _Take, the
    adapter, and the records drive() returned."""
    with tbi.scratch_repo() as root:
        rig = tbi.Rig(mod, root, turns=[{}] * max(1, len(replies)))
        made = []

        def adapter_for(r, take):
            made.append(LoopAdapter(rig.box, take, replies))
            return made[-1]
        rig.driver.script_for = lambda r: [dict(s) if isinstance(s, dict) else s for s in steps]
        rig.driver.adapter_for = adapter_for
        r = tbi.row(1)
        with tbi.spying(rig.spy):
            cid = rig.driver.launch(r)
            records = rig.driver.drive(r, cid)
            rig.driver.remove(cid)
        return rig.driver._by_slot[r["slot"]], made[0], records


def step(n, marker=None, recovery=None):
    s = {"n": n, "line": f"operator line {n}"}
    if marker is not None:
        s["marker"] = marker
    if recovery is not None:
        s["recovery"] = recovery
    return s


THREE = [step(1, "MARKER ONE"), step(2, "MARKER TWO"), step(3)]


@guarded("D2-stop")
def d2_stop(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_STOPPED", "pause_evidence")
    if out:
        return out
    take, a, rec = drive_one(mod, THREE, [{"text": "Done. MARKER ONE"}, {"text": "I went on and did it all."},
                                          {"text": "the probe's answer"}])
    if a.lines != ["operator line 1", "operator line 2"]:
        out.append(f"{p}: the driver sent {a.lines} past the unheld marker of line 2")
    held = [(r["n"], r.get("held")) for r in take.ledger_rows]
    if held != [(1, True), (2, False)] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: the ledger rows read {held} with outcome {take.outcome!r}")
    if rec["ledger"]["turns"] != 2:
        out.append(f"{p}: the records hold {rec['ledger']['turns']} turns")
    return out


@guarded("D3-recovery")
def d3_recovery(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_COMPLETE")
    if out:
        return out
    rec = {"if_reply_holds": "Which path?", "send": "the path is data/raw"}
    steps = [step(1, "MARKER ONE", rec), step(2)]
    take, a, _ = drive_one(mod, steps, [{"text": "Which path?"}, {"text": "Thanks. MARKER ONE"}, {"text": "answer"}])
    if a.lines != ["operator line 1", "the path is data/raw", "operator line 2"]:
        out.append(f"{p}: a reply holding the recovery's marker got {a.lines}")
    rows = [(r["n"], bool(r.get("recovery")), r.get("held")) for r in take.ledger_rows]
    if rows != [(1, False, True), (1, True, None), (2, False, True)] or take.outcome != mod.OUTCOME_COMPLETE:
        out.append(f"{p}: the recovered take's rows read {rows}, outcome {take.outcome!r}")
    take, a, _ = drive_one(mod, steps, [{"text": "nothing asked"}, {"text": "unused"}])
    if a.lines != ["operator line 1"]:
        out.append(f"{p}: a reply holding neither marker got a recovery: {a.lines}")
    take, a, _ = drive_one(mod, steps, [{"text": "Which path?"}, {"text": "Which path?"}, {"text": "x"}, {"text": "y"}])
    if a.lines != ["operator line 1", "the path is data/raw"] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: a recovery was sent more than once: {a.lines} ({take.outcome!r})")
    return out


@guarded("D4-exact")
def d4_exact(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_STOPPED")
    if out:
        return out
    take, a, _ = drive_one(mod, THREE, [{"text": "done. marker one"}, {"text": "x"}, {"text": "y"}])
    if a.lines != ["operator line 1"] or take.outcome != mod.OUTCOME_STOPPED:
        out.append(f"{p}: a lower-cased marker held: the driver sent {a.lines} ({take.outcome!r})")
    return out


@guarded("D5-outcome")
def d5_outcome(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "OUTCOME_COMPLETE", "OUTCOME_TIMED_OUT", "OUTCOME_PAUSE",
                          "OUTCOME_REHEARSAL", "TIMED_OUT_EXIT")
    if out:
        return out
    ok3 = [{"text": "MARKER ONE"}, {"text": "MARKER TWO"}, {"text": "answer"}]
    rate = {"status": 429, "type": "rate_limit_error", "text": "synthetic: rate limited"}
    other = {"status": 500, "type": "api_error", "text": "synthetic: overloaded"}
    cases = {
        "complete": (ok3, mod.OUTCOME_COMPLETE, [0, 0, 0]),
        "timed out": ([{"text": "MARKER ONE"}, {"end": labels4.TIMED_OUT}], mod.OUTCOME_TIMED_OUT,
                      [0, mod.TIMED_OUT_EXIT]),
        "died after output": ([{"text": "MARKER ONE"}, {"end": labels4.END_ERROR, "exit": 137, "text": "half"}],
                              "aborted \u2014 a scripted turn exited 137", [0, 137]),
        "died before output": ([{"end": labels4.END_ERROR, "output": False, "api_errors": [other]}],
                               mod.OUTCOME_REHEARSAL, [1]),
        "rate limited before output": ([{"end": labels4.END_ERROR, "output": False, "api_errors": [rate]}],
                                       mod.OUTCOME_PAUSE, [1]),
    }
    for case, (replies, want, exits) in cases.items():
        take, _, _ = drive_one(mod, THREE, replies)
        got = [r["exit"] for r in take.ledger_rows]
        if take.outcome != want or got != exits:
            out.append(f"{p}: {case}: outcome {take.outcome!r} with exits {got}, not {want!r} with {exits}")
    shapes = ("complete", "stopped \u2014 wait-point marker not held", "timed-out", "aborted \u2014 ", "PAUSE",
              "REHEARSAL")                       # check_take.DRIVER_OUTCOME_SHAPES, round 3's vocabulary
    for name in ("OUTCOME_COMPLETE", "OUTCOME_STOPPED", "OUTCOME_TIMED_OUT", "OUTCOME_PAUSE", "OUTCOME_REHEARSAL"):
        if not getattr(mod, name).startswith(shapes):
            out.append(f"{p}: {name} is not in round 3's outcome vocabulary")
    return out


WAIT_POINTS = {m: {"arrive": [{"tool": view.SHELL, "match": "render-menu"}],
                   "past": [{"tool": view.SHELL, "match": "create-project"}]} for m in ("MARKER ONE", "MARKER TWO")}


def events_for(rows, replies) -> list:
    """The view's events of a take whose operator lines are the rows' sent lines and whose replies are `replies`."""
    evs = []
    for k, (r, reply) in enumerate(zip(rows, replies), 1):
        evs.append(view.AgentEvent(k, view.OPERATOR, r["sent"], None, None, None))
        if reply.get("text"):
            evs.append(view.AgentEvent(k, view.AGENT_TEXT, reply["text"], None, None, None))
    return evs


@guarded("D6-taxonomy")
def d6_taxonomy(mod, p):
    out = tbi.missing_api(mod, p, "TakeDriver", "pause_evidence")
    if out:
        return out
    for case, replies, want in (("stalled", [{"text": "MARKER ONE"}, {"text": "Let me look at the files first."}],
                                 labels4.STALLED),
                                ("timed-out", [{"text": "MARKER ONE"}, {"end": labels4.TIMED_OUT}], labels4.TIMED_OUT)):
        take, _, _ = drive_one(mod, THREE, replies)
        ev = mod.pause_evidence(take.ledger_rows)
        got = pause_adherence.grade(events_for(take.ledger_rows, replies), {"wait_points": WAIT_POINTS}, ev)
        if got["stop_class"] != want:
            out.append(f"{p}: {case}: the driver's rows classify as {got['stop_class']!r}, not {want!r}")
    return out


# ------------------------------------------------------------------------------------------------ the tests
class TestStage1Carried(unittest.TestCase):
    def test_d1_the_copy_writes_the_hashed_bytes(self):
        self.assertEqual(d1_table(tbi.drive), [])


class TestStage3MarkerLoop(unittest.TestCase):
    def test_d2_nothing_is_sent_past_an_unheld_marker(self):
        self.assertEqual(d2_stop(tbi.drive), [])

    def test_d3_the_recovery_is_sent_only_where_pre_registered(self):
        self.assertEqual(d3_recovery(tbi.drive), [])

    def test_d4_the_marker_is_matched_exactly(self):
        self.assertEqual(d4_exact(tbi.drive), [])

    def test_d5_the_outcome_is_round_3s_vocabulary(self):
        self.assertEqual(d5_outcome(tbi.drive), [])

    def test_d6_the_stop_is_classified_from_the_drivers_rows(self):
        self.assertEqual(d6_taxonomy(tbi.drive), [])


# name: (edits to drive.py, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    "table-reread": ((("            with open(target, \"wb\") as fh:                  # the hashed bytes, never a "
                       "second read of the file\n                fh.write(table)\n",
                       "            shutil.copyfile(design, target)\n"),), d1_table, "D1-table"),
    "continued-past-unheld-marker": ((("        if not held:\n            self.stopped = True",
                                       "        if False:\n            self.stopped = True"),), d2_stop, "D2-stop"),
    "recovery-never-sent": ((("        if not held and rec and self.recoveries < int(rec.get(\"at_most\", 1))",
                              "        if False and rec and self.recoveries < int(rec.get(\"at_most\", 1))"),),
                            d3_recovery, "D3-recovery"),
    "recovery-unbounded": ((("self.recoveries < int(rec.get(\"at_most\", 1)) and", "True and"),), d3_recovery,
                           "D3-recovery"),
    "marker-casefold": ((("    return True if marker is None else marker in said",
                          "    return True if marker is None else marker.lower() in said.lower()"),), d4_exact,
                        "D4-exact"),
    "abort-before-output": ((("            if not any(t.agent_output for t in turns):",
                              "            if False:"),), d5_outcome, "D5-outcome"),
    "turn-ends-dropped": ((("            \"turn_ends\": [r[\"end\"] for r in rows]}",
                            "            \"turn_ends\": [\"end_turn\" for r in rows]}"),), d6_taxonomy, "D6-taxonomy"),
}
WITNESS_LOG: list = []


class TestWitnesses(unittest.TestCase):
    """Each witness is killed only by its bound check's own assertion, with the bound check green on the real
    drive.py first; an ERROR line, a raise or an unperformed edit is never a kill."""

    def kill(self, name):
        edits, check, prefix = WITNESSES[name]
        self.assertEqual(check(tbi.drive), [], f"{name}: the bound check is not green on drive.py")
        got = check(tbi.witness_module(edits))
        errors = [x for x in got if x.startswith("ERROR")]
        own = [x for x in got if x.startswith(prefix + ":")]
        collateral = [x for x in got if x not in own and x not in errors]
        line = (f"WITNESS {name}: {'red' if own and not errors else 'NOT KILLED'} by {prefix} ({len(own)} own, "
                f"{len(collateral)} collateral, {len(errors)} errors)")
        print(f"\n{line}", end=" ", file=sys.stderr, flush=True)
        WITNESS_LOG.append(line)
        self.assertEqual(errors, [], f"{name}: the bound check errored under the witness: {errors}")
        self.assertTrue(own, f"{name}: survived (no {prefix} line): {got}")

    def test_witness_table_reread(self):
        self.kill("table-reread")

    def test_witness_continued_past_unheld_marker(self):
        self.kill("continued-past-unheld-marker")

    def test_witness_recovery_never_sent(self):
        self.kill("recovery-never-sent")

    def test_witness_recovery_unbounded(self):
        self.kill("recovery-unbounded")

    def test_witness_marker_casefold(self):
        self.kill("marker-casefold")

    def test_witness_abort_before_output(self):
        self.kill("abort-before-output")

    def test_witness_turn_ends_dropped(self):
        self.kill("turn-ends-dropped")

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), sorted(["table-reread", "continued-past-unheld-marker",
                                                    "recovery-never-sent", "recovery-unbounded", "marker-casefold",
                                                    "abort-before-output", "turn-ends-dropped"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
