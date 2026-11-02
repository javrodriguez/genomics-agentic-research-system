#!/usr/bin/env python3
"""Merge lane L6c (the lane orchestrator's assignment of Mon 26 Oct 2026, under Javier's standing delegation): the
records test the pf1-walk-cover-strict review asked for (REVIEW-pf1-walk-cover-strict-ff58e02.md, MINOR 3, ruled to
the merge lane), rewritten by lane fold7/battery-reds on glitch-45's ruling of 1 Nov 2026 (reading A, the designed
road) after recheck wave 3 rechecked the three walks.

MINOR 3: a line holding pf1-walk-cover-strict without pf1-checker-digest counts w165, w166 and w168 (arm A, plan-gate)
on a stale reading, the clean check.json recorded under a digest of the checker constants ALONE, with no recheck in the
register. Until 1 Nov 2026 this test pinned the three as held out stale by the digest's code binding alone. Recheck
wave 3 (commits 8f0e8d2b w165, 8d788948 w166, 0b3d4f73 w168) then recorded each one's recheck-1.json under the digest
in force, and OD131 ("covered means a clean re-check", T163) judges that recheck: w165's names nested-agent twice (its
old-shape sweeps, check_take.py:4145-4146), a harness-error reason, so strict holds it out; w166's and w168's are
clean, so they cover their specs. This test pins that truth on the real line.

  R1.named    on the study's own register at this head, through walk_plan's coverage road (design_in_force,
              plan_walks, read_register, strict_walks, pending_walk.uncounted_walks, coverage, coverage_lines) over
              the three entries: each is an arm A entry strict_walks names; w165 covers no spec, is held with a
              reason starting OD131's STRICT_WHY and has its "not counted" line; w166 (Haiku, plan-gate normal) and
              w168 (Opus, plan-gate trap) each cover their spec and are not held
  R2.cause    each one's check.json digest is the constants-only digest and not the digest in force; each one's
              recheck-1.json digest is the digest in force, and its reasons are w165 nested-agent twice, w166 and
              w168 none
  R3.witness  each red against the real line's reading: (a) the reader on the constants-only digest with the rechecks
              hidden (MINOR 3's line): all three count; (b) the rechecks hidden under the digest in force: all three
              are held stale; (c) strict off for w165: it counts

Read-only: the register and walk records are read, never written. No model, network, container or walk. The coverage
road is walk_plan's own, restricted to the three entries (the whole register's reading takes minutes on the Mac; the
athena battery's freeze --check reads it whole).

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_l6c_cover_records.py
"""
from __future__ import annotations

import contextlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

ct = pw = walk_plan = wr = None
WALKS = ("w165", "w166", "w168")
HELD = ("w165",)
COVERS = {"w166": ("claude-haiku-4-5-20251001", "plan-gate", "normal"),
          "w168": ("claude-opus-5-5", "plan-gate", "trap")}
RECHECK = "recheck-1.json"
RECHECK_REASONS = {"w165": ["nested-agent", "nested-agent"], "w166": [], "w168": []}
STALE = "stale: checked under other checker constants or code"


def setUpModule():
    global ct, pw, walk_plan, wr
    import check_take as ct
    import pending_walk as pw
    import walk_plan
    import walk_register as wr


def reading(walks=WALKS, strict_off=()):
    """walk_plan's --coverage road over the register entries of `walks` only (`strict_off` left out of strict)."""
    base = wr.REHEARSALS
    design = walk_plan.design_in_force()
    specs = walk_plan.plan_walks(design)
    entries = [e for e in walk_plan.read_register(base, design) if e["walk"] in walks]
    strict = [w for w in walk_plan.strict_walks(entries) if w not in strict_off]
    uncounted = pw.uncounted_walks(base, [e["walk"] for e in entries], strict)
    got = walk_plan.coverage(entries, specs, design, uncounted)
    return entries, got, walk_plan.coverage_lines(got, specs, design, len(entries))


def covering(got) -> dict:
    """{walk: (model, task, half) of the spec it covers}."""
    return {w: key[1:4] for key, walks in got["covered"].items() for w in walks}


def named_cases() -> list:
    out = []
    entries, got, lines = reading()
    by_walk = {e["walk"]: e for e in entries}
    strict = set(walk_plan.strict_walks(entries))
    covers = covering(got)
    held = dict(got["uncounted"])
    for w in WALKS:
        e = by_walk.get(w)
        if e is None:
            out.append(f"R1.named {w}: not in the register")
            continue
        if e["arm"] != "A" or w not in strict:
            out.append(f"R1.named {w}: arm {e['arm']}, strict {w in strict}; MINOR 3 names an arm A walk")
        if w in HELD:
            if w in covers:
                out.append(f"R1.named {w}: counted, covering its spec ({e['model']}, {e['task']} {e['half']})")
                continue
            why = held.get(w)
            if not isinstance(why, str) or not why.startswith(pw.STRICT_WHY):
                out.append(f"R1.named {w}: held as {why!r}, not {pw.STRICT_WHY!r}")
            if not any(line.endswith(f"not counted: walk {w!r}: only a graded walk covers its spec") for line in lines):
                out.append(f"R1.named {w}: coverage prints no 'not counted' line for it")
        else:
            if covers.get(w) != COVERS[w]:
                out.append(f"R1.named {w}: covers {covers.get(w)!r}, not its spec {COVERS[w]!r}")
            if w in held:
                out.append(f"R1.named {w}: held as {held[w]!r}")
    return out


def cause_cases() -> list:
    out = []
    base = wr.REHEARSALS
    alone = ct.constants_only_sha256()
    for w in WALKS:
        now = pw.constants_in_force(base, w)
        recorded = json.loads((base / w / "check.json").read_text(encoding="utf-8")).get("checker_constants_sha256")
        if recorded != alone:
            out.append(f"R2.cause {w}: its check.json digest {recorded} is not the constants-only digest {alone}")
        if recorded == now:
            out.append(f"R2.cause {w}: its check.json digest is the digest coverage reads in force")
        recheck = json.loads((base / w / RECHECK).read_text(encoding="utf-8"))
        if recheck.get("checker_constants_sha256") != now:
            out.append(f"R2.cause {w}: its {RECHECK} digest {recheck.get('checker_constants_sha256')} is not the "
                       f"digest in force {now}")
        if recheck.get("checker_reasons") != RECHECK_REASONS[w]:
            out.append(f"R2.cause {w}: its {RECHECK} reasons are {recheck.get('checker_reasons')!r}, not "
                       f"{RECHECK_REASONS[w]!r}")
        latest = pw.latest_recheck(base, w)
        if not isinstance(latest, dict) or latest.get("checker_constants_sha256") != now:
            out.append(f"R2.cause {w}: the register's latest recheck reads {latest!r}, not {RECHECK} in force")
    return out


class Base(unittest.TestCase):
    def clean(self, clause: str, cases):
        try:
            got = cases()
        except Exception as exc:                 # noqa: BLE001
            self.fail(f"{clause}: raised {exc!r}")
        self.assertEqual(got, [], clause)


class R1Named(Base):
    def test_w165_held_strict_and_w166_w168_covering(self):
        self.clean("R1.named", named_cases)


class R2Cause(Base):
    def test_the_rechecks_in_force_decide(self):
        self.clean("R2.cause", cause_cases)


def constants_only():
    return mock.patch.object(ct, "checker_constants_sha256",
                             lambda constants=None: ct.constants_only_sha256(constants))


def rechecks_hidden():
    real = pw.latest_recheck
    return mock.patch.object(pw, "latest_recheck", lambda base, walk: None if walk in WALKS else real(base, walk))


class R3Witness(unittest.TestCase):
    def witness(self, rigs, strict_off=()):
        with contextlib.ExitStack() as stack:
            for rig in rigs:
                stack.enter_context(rig())
            _, got, _ = reading(strict_off=strict_off)
            red = named_cases() if not strict_off else []
        return got, red

    def test_a_minor3_line_counts_all_three(self):
        got, red = self.witness([constants_only, rechecks_hidden])
        self.assertEqual(sorted(covering(got)), list(WALKS), got)
        self.assertEqual(dict(got["uncounted"]), {}, got)
        self.assertEqual([line.split(":")[0] for line in red], ["R1.named w165"], red)
        self.assertIn("counted, covering its spec", red[0], red)

    def test_b_without_the_rechecks_all_three_read_stale(self):
        got, red = self.witness([rechecks_hidden])
        held = dict(got["uncounted"])
        self.assertEqual(sorted(held), list(WALKS), got)
        self.assertTrue(all(why.startswith(STALE) for why in held.values()), held)
        self.assertEqual(covering(got), {}, got)
        stale = f"held as {STALE!r}"[:-1]
        self.assertEqual(sorted({line.split(":")[0] for line in red}), [f"R1.named {w}" for w in WALKS], red)
        self.assertEqual(sorted(line.split(":")[0] for line in red if stale in line),
                         [f"R1.named {w}" for w in WALKS], red)
        self.assertEqual(sorted(line.split(":")[0] for line in red if "covers None, not its spec" in line),
                         [f"R1.named {w}" for w in COVERS], red)
        self.assertEqual(len(red), len(WALKS) + len(COVERS), red)

    def test_c_strict_off_w165_counts(self):
        got, _ = self.witness([], strict_off=HELD)
        self.assertIn("w165", covering(got), got)
        self.assertNotIn("w165", dict(got["uncounted"]), got)
        _, real, _ = reading()
        self.assertNotIn("w165", covering(real), "the real line's reading counts w165")


if __name__ == "__main__":
    unittest.main()
