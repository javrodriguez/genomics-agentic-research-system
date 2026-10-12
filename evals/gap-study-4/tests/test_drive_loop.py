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

import test_box_integration as tbi  # noqa: E402
from graders import labels4  # noqa: E402


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


# ------------------------------------------------------------------------------------------------ the tests
class TestStage1Carried(unittest.TestCase):
    def test_d1_the_copy_writes_the_hashed_bytes(self):
        self.assertEqual(d1_table(tbi.drive), [])


# name: (edits to drive.py, the bound check, the line prefix that is its own assertion)
WITNESSES = {
    "table-reread": ((("            with open(target, \"wb\") as fh:                  # the hashed bytes, never a "
                       "second read of the file\n                fh.write(table)\n",
                       "            shutil.copyfile(design, target)\n"),), d1_table, "D1-table"),
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

    def test_the_witnesses_are_named_and_each_bound_to_its_own_check(self):
        self.assertEqual(sorted(WITNESSES), ["table-reread"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
