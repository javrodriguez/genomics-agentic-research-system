---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
symptoms:
  - follow-up 0205 changes the R-076 key and submit under the protected prefix gars/_system/ with no owner approval record
---
# R-076 script binding 0205: approval of its protected change, under the owner's delegation

Addendum to [0205](0205-r076-binds-the-generated-analysis-script.md), which stays byte-identical.
The files this record approves are protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows 0176 and 0196.

## Context

Built from public main `81c0d71` by a Claude Opus 5.5 producer for the Row-orchestrator glitch-31, in a clone with no remote: red `25011b6`, fix `668daa1`, docs `54135b4`, review-1 fix `d10fc08` + docs `80800c9`, review-2 fix `70dbfe0` + docs `50502ca`.
Producer and reviewer are the same model family; review independence rests on a fresh context, a separate checkout with no remote and a stated threat model, not model diversity (the same-model cost is stated here).
Lane reviews (fresh `claude -p --model claude-opus-5-5`, verdicts read fail-closed): r1 CHANGES (BLOCKER 1, MAJOR 2, NOTE 2: a linked scripts/ at prepare, a re-prepare binding an added module, an unlistable folder framed as empty); r2 CHANGES (MAJOR 1, MINOR 1, NOTE 1: an allow-list read from submit.sh text, a traceback refusal, a check-to-walk window); r3 APPROVE, NOTE 1, STATUS CLEAN.
Dispositions: every BLOCKER, MAJOR and MINOR fixed red-first with a mutation; r1 F-5 needs nothing; r2 F-8 is 0205's residual R4; r3 F-9 (the refusal's JSON keys are `wrapper`/`error`, not the wrappers' `assay`/`failures`) is deferred by name: `ok`, `error` and the exit code match the existing refusals.

## Decision

Approved by Glitch under Javier's 23 Sep delegation: the downstream-v2 key formula, the v1 refusal at submit, and the tests named in 0205.

## A deliberate assertion change (row 6's replay test)

A `downstream-v2` key is tied to the stage's location, because the generated script names its own project and stage; the coordinator (glitch-31, under the owner's delegation, not the owner's words) accepted this, and the change to row 6's replay assertion, on 28 Sep 2026.
In `gars/tests/test_rerun_check.py`, both replay checks (the rnaseq-de and the scrna replay) asserted:

```
self.assertEqual(replay['idempotency_key'], original['idempotency_key'])
```

and now call `self.assert_same_prepared_job(stage, replay, original)`, which asserts:

```
self.assertEqual((replay['key_formula'], original['key_formula']),
                 ('downstream-v2', 'downstream-v2'))
self.assertEqual(replay['idempotency_key'], wl.input_key(stage, replay))
legacy = lambda m: wl.input_key(stage, dict(m, key_formula='downstream-v1'))
self.assertEqual(legacy(replay), legacy(original))
```

The old claim (same inputs and params) is kept exactly by the v1 part; the replay's generated script matching the original apart from its location is not asserted.

## Evidence

It lands jointly with the small-fixes follow-up 0200 (approved in [0201](0201-small-fixes-0200-delegated-approval-of-protected-change.md)), by the coordinator's ruling (glitch-31, under the owner's delegation, not the owner's words): one candidate, evidence once. The integration merge `31268e5` joins 0200's head `7f82317` with this branch's head `50502ca` off the first-parent line; the landing merge `cdd7d99` (first parent `0d9954c`, the public tip) is the one `gars/_system` commit it adds to main's first-parent line and carries the Review/Bench/Session trailers. Both follow-ups edit `executorlib.py` in disjoint hunks, merged with no hand resolution.

Measured once, on the landing merge `cdd7d99`, 28 September 2026 (clock times US Eastern, read from `date`):
- **Development Mac, mode A** (Docker answering, row 5's scratch folder and `TMPDIR` set, as CI runs it; the Mac booked 10:49:46-11:52:50): `Ran 1208 tests`, `OK (skipped=14)`; `check_contracts` 14 clean, `check_counts` 1208 clean, `evals/test_harness.py` 44 OK, `evals/check_results.py --controls --lexicon` clean. Another lane's own test run shared the Mac during the booking; no timing check went red, and the result stands as measured.
- **Build node, owner account, solo**: mode B `Ran 1208 tests`, `OK (skipped=82)`; mode C `Ran 1208 tests`, `OK (skipped=124)`; contracts, counts, harness (44 OK) and the pre-registration check exit 0.
- **Mutations**, on the build node from a clean copy of the landing merge: this follow-up's twelve, 12 of 12 killed by the named test (0200's five, 5 of 5).
- **Smoke ceremony** at the landing merge: `smoke-20260928-small-fixes-r076`, run-1 3/3, delta 0/1, "no change", scored ok with 0 findings.
- **Before the evidence**, at the landing merge, one module at a time: both lanes' 21 affected modules OK; `check_counts`, `check_contracts` and `scripts/release_check.py --check` (13/13) exit 0.

## Status

Standing.

## Date

2026-09-28

## Test

Appended 28 September 2026 after the landing: the record reached main without this section, which the decision-link check requires of a new record; the bytes above are unchanged, and nothing here is new evidence.

- The tests that bind 0205: `gars/tests/test_r076_script_binding.py` (14 tests), red at base and green at the fix; the changed assertions in `gars/tests/test_downstream_keys.py` and `gars/tests/test_rerun_check.py`; the affected modules `test_r076_script_binding`, `test_downstream_keys`, `test_r164_exact_bytes`, `test_r164_writer_recovery`, `test_r164_params_mapping`, `test_wrapper_contract`, `test_wrapperlib_prepare`, `test_bring_home`, `test_planted_defects`, `test_manifest_groups`, `test_pilot_doors` and `test_rerun_check` OK one at a time at the branch head and at the landing merge.
- The mutation proof on `wrapperlib.py` and `executorlib.py`: twelve mutants, each killed by its named test, 12 of 12 on this Mac at the branch head and 12 of 12 on the build node from a clean copy of the landing merge `cdd7d99`.
- The suite at the landing merge `cdd7d99`, 1208 tests, in the three modes named in Evidence: macOS mode A `OK (skipped=14)`, Linux with `TMPDIR` set `OK (skipped=82)`, Linux with it unset `OK (skipped=124)`; the fresh-clone gate `ok: 124 skips` against the records commit's README.
