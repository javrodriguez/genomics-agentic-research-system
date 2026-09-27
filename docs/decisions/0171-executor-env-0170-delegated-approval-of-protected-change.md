---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
symptoms:
  - follow-up 0170 changes the executor under the protected prefix gars/_system/ with no owner approval record
---
# Executor env allow-list follow-up 0170: approval of its protected change, under the owner's delegation

Addendum to [0170](0170-executor-env-allow-list-read-from-gars-env.md), which stays byte-identical.
The file this record approves is protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0166](0166-guard-lexer-0165-delegated-approval-of-protected-change.md).

## Context

Follow-up 0170 makes the executor pass a job the names `gars-env.sh` itself reads from the environment, instead of a hand-kept list that carried two of its eight, so an operator's own `GARS_BIO` and `GARS_NXF` reach the job.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 27 Sep 2026, before the build, that this follow-up lands from the build Mac rather than as an overnight lane on the build node, with a Codex producer on the Mac's second account.
It was built on its own branch from public main `4597dd4` by that Codex producer in an isolated clone (session `01a0e308-fc95-7371-99ee-af3dc18f963c`, three rounds), and reviewed twice by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
Producer commits, each under the repository's own identity, red-first (the failing tests committed before each fix):
round 1 `d6fd142` (the new test module, red at `4597dd4`), `9b1a8f4` (the fix);
round 2 `24f7f70` (the replay fixture's `gars-env.sh` stub, which met the new refusal in all 17 of its setups, red at `9b1a8f4`);
round 3 `c9247d5` (the literal base set pinned, stub launchers on the C1 test's PATH, a reservation test red at `24f7f70`), `eac03c8` (the source check before any reservation; the comment reworded), `4f7ab6c` (two tests that asserted the old literal list).
The lane's own commit `77021d4` adds 0170 and the index; the landing merge carries the suite totals.
Reviews, kept outside the repository and cited by their kit folders:
`gars-env-allowlist/reviews/r1` APPROVE WITH CHANGES on `4597dd4..24f7f70` (three MAJOR, one MINOR, four NOTE). F-1 and F-2, MAJOR: `tests/run_tests.py` and `test_execution_policy.py` asserted the old literal list; answered in round 3. F-3, MAJOR on a refusal path: the test binding "nothing else passes" took its oracle from the module under test, so a credential name added to the base names stayed green; answered in round 3 with a literal set in the test. F-4, MINOR: a failed read after the R-076 reservation stranded the key; answered in round 3. F-5, NOTE: the C1 test ran the host's `nextflow`; answered in round 3. F-6, NOTE: exported defaults are not all operator-chosen; the comment reworded, and 0170's D4. F-7 and F-8, NOTE: the answers to 0170's R1 and R2.
`gars-env-allowlist/reviews/r2` APPROVE WITH CHANGES on `24f7f70..4f7ab6c` (one MINOR, four NOTE; no MAJOR, so the review loop ended). It found every r1 answer closed. F-1, MINOR: no test binds the local job's whole environment; deferred as 0170's D1. F-2, NOTE: the grammar fixture does not pin the line anchor; D2. F-3, NOTE: the reservation test runs with the ambient PATH; D3. F-4 and F-5, NOTE: R1 and R2 again.
Before the review, the lane checked with json-built hook payloads that an agent session cannot set these variables for the executor: `GARS_BIO=/x ls .`, `env …` and `export …` exit 2 (R-092) while `ls .` exits 0.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`gars/_system/executorlib.py`**: `BASE_NAMES`; `overridable_names()`; `EXPORT_NAMES` as the sorted union of the base names and the names read from the sibling `gars-env.sh` at import; `ExecutionEnvError`, raised by `execution_env()`, `submit_argv()` and `submit()` (before the records folder, lock and reservation) when that read or its parse failed; the comment above them. Every other line is as at `4597dd4`.

Outside the protected prefixes, recorded for completeness: the new `gars/tests/test_executor_env.py`, the changed assertions in `gars/tests/test_rerun_check.py`, `gars/tests/test_execution_policy.py` and `tests/run_tests.py` named in 0170, 0170 itself, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0170, the coordinator's road and producer rulings, the round 2 fixture ruling, the round 3 brief, and the review dispositions above.

## What this does not close

- 0170's R1, R2 and D1 to D4.
- The build node was not solo for the B and C runs: the row 9 test-speed lane disclosed that its own runs on the same owner account overlapped them (about 12:08 to 12:32 EDT), which this lane's process snapshot saw only at C's end; B and C both ended green with the same skip figures as the previous landing, and the harness step ran green beside them.
- The replay module `test_rerun_check` was never run on its own after its fixture was repaired; its 26 tests ran green inside each of the three full suites above.
- The mutation proof ran on this Mac, not on the build node (a module under one second, run while the build node's owner account was busy).

## Test

Glitch verified the landing merge `559d593` (branch head `77021d4` merged onto public main `37972d8`), each evidence run with a process snapshot at its start and end.

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1150 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all `str.removesuffix`, `str.removeprefix` or `ast.unparse`, which are Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change in this landing, 0156, 0161 and 0166 recorded the same red, and the build node's Python 3.13.5 ran the harness 44 OK at the merge, so the red is the interpreter's, not this change's. Only a sleeping waiter of another session and a read-only status command ran beside it.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge: `Ran 1150 tests`, `OK (skipped=82)` without containers, and `OK (skipped=124)` with `TMPDIR` also unset; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean; no other account ran a suite, Codex or Claude at the start or between the runs (the overlap at C's end is named above).
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with that Linux run's log: `plain run: Ran 1150 tests, OK, skipped 124` and `ok: 124 skips, at most 124 documented` (a planted 125 fails it).
- At the merge's tree: `check_counts` 1150 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- A mutation proof at the branch code head `4f7ab6c`: eleven mutants (the old hand tuple; the parser dropping the `export ` prefix, accepting only `:-`, or dropping the same-name rule; a failed read falling back to the base names; an empty parse accepted; `execution_env()` passing everything; `submit_argv()` or `submit()` skipping the source check; Slurm's list built from the base names only; a credential name added to `BASE_NAMES`), each killed, with the unchanged control green.
- The model-free reproduction at the branch head: with non-default `GARS_BIO` and `GARS_NXF` exported, both reach the local job, it exits 0 and `gars-env.sh` sources cleanly, where `4597dd4` dropped both and the job died on the fail-fast.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `559d593`'s tree, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260927-guard-lexer.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (record `smoke-20260927-env-allowlist`, superseded by the addendum's re-run at the rebuilt merge).
- The outgoing range `37972d8..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Addendum: carried over onto the row 9 test-speed landing

Public main moved, after the evidence above, from `37972d8` to `911f0b4` (the row 9 test-speed follow-up, [0180](0180-row-9-fault-module-one-control-per-case-and-a-bounded-pool.md)).
Under the coordinator's carry-over ruling (the lane's, under the owner's delegation), the merge was rebuilt as `2d28f2f` (first parent `911f0b4`, second parent the same branch head `77021d4`) and the suite evidence above is carried to it without a re-run, on three conditions, each checked:

- (a) The tree difference from the evidenced merge `559d593` to `2d28f2f` is exactly the test-speed landing's own change: `tests/test_review_faults_faults.py` and 0180 byte-identical to `37972d8..911f0b4`, and one added index row (0180's); no other file differs.
- (b) No file this follow-up adds or changes reads the fault module, 0180 or the decisions index.
- (c) 0180's own equivalence proof shows the new fault module gives the old one's verdicts, identical in content and order at one and four workers, and the old module ran green inside all three suites above.

Re-done at the rebuilt merge: the smoke ceremony (one run of three `claude-opus-5-5` sessions at `2d28f2f`'s tree, prompt and suite hashes unchanged, run-1 3/3, `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260927-guard-lexer.json` (the speed lane's merge touches nothing under `gars/_system/`, so that record stays the nearest earlier checked one), `smoke.py score` ok with 0 findings, `evals/runs/smoke/smoke-20260927-env-allowlist-2.json`; another session's short API test run was active on this Mac beside it), the trailer audit, the secret and privacy sweep over `911f0b4..` the records commit, and the Fresh-clone gate against this records commit's README with the Linux run's log (`plain run: Ran 1150 tests, OK, skipped 124`, `ok: 124 skips, at most 124 documented`; a planted 125 fails it).
The first smoke record, `smoke-20260927-env-allowlist`, was scored at `559d593` and never published; the published record is the one named by the rebuilt merge's `Bench:` trailer.

## Status

Standing. Approval of follow-up 0170's protected change only.

## Date

2026-09-27
