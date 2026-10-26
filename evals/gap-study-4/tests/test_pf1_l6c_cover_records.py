#!/usr/bin/env python3
"""Merge lane L6c (the lane orchestrator's assignment of Mon 26 Oct 2026, under Javier's standing delegation): the
records test the pf1-walk-cover-strict review asked for (REVIEW-pf1-walk-cover-strict-ff58e02.md, MINOR 3, ruled to
the merge lane).

MINOR 3: a line holding pf1-walk-cover-strict without pf1-checker-digest counts w165, w166 and w168 (arm A, plan-gate),
which OD131 rejects. Their committed check.json reads clean (checker_reasons []) under a digest of the checker
constants ALONE, recorded before the checks that would name their harness conditions existed; with no recheck in the
register, strict judges that clean reading, so only the digest's code binding stops them counting: it makes each read
stale until rechecked, and a recheck under the harness in force is then judged by the strict rule. S5.records cannot
see this (it judges the reasons as stored), so this test names the three on the real merged line.

  R1.named    on the study's own register at this head, through walk_plan's coverage road (design_in_force,
              plan_walks, read_register, strict_walks, pending_walk.uncounted_walks, coverage, coverage_lines) over
              the three entries: each is an arm A entry strict_walks names, covers no spec, is held in coverage's
              uncounted list and has its "not counted" line, the reason being the stale reading (or OD131's STRICT_WHY)
  R2.cause    each one's check.json digest is the constants-only digest in force, and not the bound digest coverage
              reads, so the binding is what holds it out (were the constants to move, this clause says so first)
  R3.witness  with the reader put back on the constants-only digest (the line without pf1-checker-digest), R1 is red:
              all three count

Red first: on lane/pf1-walk-cover-strict alone (904b36a3, no digest lane) R1 fails by its own assertion, the three
covering their specs. Read-only: the register and walk records are read, never written. No model, network, container
or walk. The coverage road is walk_plan's own, restricted to the three entries (the whole register's reading takes
minutes on the Mac; the athena battery's freeze --check reads it whole).

    python3 -B -W ignore evals/gap-study-4/tests/test_pf1_l6c_cover_records.py
"""
from __future__ import annotations

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
STALE = "stale: checked under other checker constants or code"


def setUpModule():
    global ct, pw, walk_plan, wr
    import check_take as ct
    import pending_walk as pw
    import walk_plan
    import walk_register as wr


def reading(walks=WALKS):
    """walk_plan's --coverage road over the register entries of `walks` only."""
    base = wr.REHEARSALS
    design = walk_plan.design_in_force()
    specs = walk_plan.plan_walks(design)
    entries = [e for e in walk_plan.read_register(base, design) if e["walk"] in walks]
    uncounted = pw.uncounted_walks(base, [e["walk"] for e in entries], walk_plan.strict_walks(entries))
    got = walk_plan.coverage(entries, specs, design, uncounted)
    return entries, got, walk_plan.coverage_lines(got, specs, design, len(entries))


def named_cases() -> list:
    out = []
    entries, got, lines = reading()
    by_walk = {e["walk"]: e for e in entries}
    strict = set(walk_plan.strict_walks(entries))
    covering = {w for walks in got["covered"].values() for w in walks}
    held = dict(got["uncounted"])
    for w in WALKS:
        e = by_walk.get(w)
        if e is None:
            out.append(f"R1.named {w}: not in the register")
            continue
        if e["arm"] != "A" or w not in strict:
            out.append(f"R1.named {w}: arm {e['arm']}, strict {w in strict}; MINOR 3 names an arm A walk")
        if w in covering:
            out.append(f"R1.named {w}: counted, covering its spec ({e['model']}, {e['task']} {e['half']})")
            continue
        why = held.get(w)
        if not isinstance(why, str) or not (why.startswith(STALE) or why.startswith(pw.STRICT_WHY)):
            out.append(f"R1.named {w}: held as {why!r}, not stale or {pw.STRICT_WHY!r}")
        if not any(line.endswith(f"not counted: walk {w!r}: only a graded walk covers its spec") for line in lines):
            out.append(f"R1.named {w}: coverage prints no 'not counted' line for it")
    return out


def cause_cases() -> list:
    out = []
    base = wr.REHEARSALS
    alone = ct.constants_only_sha256()
    for w in WALKS:
        recorded = json.loads((base / w / "check.json").read_text(encoding="utf-8")).get("checker_constants_sha256")
        if recorded != alone:
            out.append(f"R2.cause {w}: its check.json digest {recorded} is not the constants-only digest {alone}; "
                       f"the constants moved, so the binding is no longer the only cause")
        if recorded == pw.constants_in_force(base, w):
            out.append(f"R2.cause {w}: its check.json digest is the digest coverage reads in force")
    return out


class Base(unittest.TestCase):
    def clean(self, clause: str, cases):
        try:
            got = cases()
        except Exception as exc:                 # noqa: BLE001
            self.fail(f"{clause}: raised {exc!r}")
        self.assertEqual(got, [], clause)


class R1Named(Base):
    def test_the_three_are_not_counted(self):
        self.clean("R1.named", named_cases)


class R2Cause(Base):
    def test_the_binding_holds_them_out(self):
        self.clean("R2.cause", cause_cases)


class R3Witness(unittest.TestCase):
    def test_without_the_binding_they_count(self):
        with mock.patch.object(ct, "checker_constants_sha256", lambda constants=None: ct.constants_only_sha256(constants)):
            red = named_cases()
        self.assertEqual(sorted(line.split(":")[0] for line in red), [f"R1.named {w}" for w in WALKS], red)
        self.assertTrue(all("counted, covering its spec" in line for line in red), red)


if __name__ == "__main__":
    unittest.main()
