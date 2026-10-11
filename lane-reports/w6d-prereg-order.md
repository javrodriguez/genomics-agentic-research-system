status: stopped

# Lane w6d-prereg-order: slice S3, `prereg.py --order` names freeze.planned_order

Written Sun 11 Oct 2026, 17:14 EDT (`date`), by the slice's sole builder (Claude Opus 5.5), assigned by glitch-1b.
Branch `gap4/w6d-prereg-order`, base `28e1be3e` (the w5c merge).
Code commit `447fab0835d13e114bf9cdab107e3c5376d86b83`.
Nothing was pushed or merged, and no model, vendor, network or take ran.

RESUME HERE: hand-back at 447fab0835d13e114bf9cdab107e3c5376d86b83; athena owns the exact-head run_checks (with `checks.d/w6d-prereg-order.txt`, including `--witnesses`) and a fresh opus-medium review follows.

## What closed

The w5c carry (its report lines 606, 2479, 4014): `--order` named round 3's per-axis positive/control order.
`prereg.order(seed)` now calls `freeze.planned_order(load(), seed)`, the one permutation of the design's whole planned rows that `freeze.prepare` writes as `take_order`.
`--order <sha>` prints `take order: freeze.planned_order, one permutation of N whole planned rows, seeded by <sha12>` and the first eight rows with their slots.
`AXES` and `axis_of` existed only for the per-axis order and are removed; nothing in gap-study-4 imported them.
The short-seed refusal is kept unchanged.

## A finding the carry surfaced

On the committed draft, `freeze.planned_order` refuses: every row's `agent.version` is still `null` (the CP6 version pins), and `check_results.validate_ledger` rejects it.
Each row's bytes, version included, feed the permutation, so no order exists until the pins land.
`--order` therefore prints `take order: freeze.planned_order refuses the design in force (prereg-draft.json): <the ledger message>` and exits 1.
This door never fills or skips a pending version; the test binds that.
The order tests run on a fake-pinned copy of the draft (every version set to `0.0.0-fake`).

## Files

- `prereg.py` (edited copy of round 3's file): the order change above, docstrings aligned.
- `COPIED.d/w1a-cp1-scaffold.json`: the `prereg.py` entry goes from `identical` to `edited` with a reason. Ownership does not move: the entry stays in w1a's fragment as the copy's provenance, as w4h did for files it edited.
- `COPIED.d/w6d-prereg-order.json` (new): claims this lane's three new files.
- `checks.d/w6d-prereg-order.txt` (new): the test module, and on athena its witnesses.
- `tests/test_prereg_order.py` (new): clauses O1 (equals freeze.planned_order, and the freeze's own sha256 key computed separately), O2.whole_rows, O2.interleaved, O3.cli, O4.seed, O5.pending (committed draft refused, exit 1).
- `tests/test_scaffold.py` (w1a's, one test): `test_a_copy_recorded_as_new_is_refused` used `prereg.py` as its byte-identical example; it now uses `round2.py`, still identical. Without that change the test fails, since an edited copy is no longer "a copy and must say so". Named departure: a test-only edit to another lane's file, needed by the carry.

## Evidence (Mac, light-ok gated, Python 3.13, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`)

- Red first: the final test file against base `prereg.py`: 6 run, 5 failures (O1, O2.whole_rows, O2.interleaved, O3, O5; all assertion failures), exit 1. O4 passed, as the seed check was kept.
- Green: `tests/test_prereg_order.py` 6 run, 0 failures, exit 0.
- Witnesses: `--witnesses` 8 of 8 RED by their bound method and clause (per-axis, other-seed, dropped-row, duplicated-row, arm-blocks, cli-label, short-seed, versions-defaulted), exit 0; collateral was listed and not credited. Departure: these eight small subprocesses ran on the Mac (light-ok) as well; athena's run is the one of record.
- `tests/test_scaffold.py`: 49 tests OK, exit 0 (first run before the test_scaffold change: 1 failure, exit 1, the case above).
- `tests/test_pipeline.py`: 85 tests OK, exit 0 (its rehearsal clone copies the `prereg.py` claim).
- `build_draft.py --check`: exit 0, draft bytes unchanged. `freeze.py --check`: exit 0. `copy_manifest.py --check`: exit 0 (38 identical, 15 edited, 173 new).
- `lint_language.py` and `lint_pooling.py` exit 1 with 25 and 8 findings, none in this slice's files (grep for w6d, prereg, w1a-cp1, test_scaffold, checks.d found none). This slice did not run either lint on the base, so it does not claim the counts are unchanged; every finding listed is in a file it did not touch.

## OPEN

OPEN carry for build_draft's owner (S4 or after): the draft's `order_carry` line ("prereg.py --order is the earlier per-axis positive/control order; CP2 must replace it.") is now stale, and test_build_draft's R3.order binds its wording. Changing it changes the draft bytes, so it goes only through the w5c owner's writer.
OPEN, not this carry: `cells()` and `--status`'s "planned takes" count still use round 3's (task, half, model, take) shape, which does not match round 4's rows.
Not read: grader source, sealed, holdout, brief or saved-output paths, and nothing under round 3 was opened directly.
