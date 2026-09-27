---
date: 2026-09-27
status: standing
kind: decision
touches:
  - tests/test_review_faults_faults.py
symptoms:
  - tests/test_review_faults_faults.py is the slowest module in every evidence run (244 s on a 32-thread Linux host, about 800-1000 s on the Mac)
  - its fixed 180 s per-child cap turned one or two entries red in each mode of row 8A's busy candidate run and one in row 9's mode A, each costing a solo re-run
---
# The review-faults fault module runs one control per case and a bounded pool, with the same verdicts

## Context

Row 9's fault module ([0074](0074-row-9-seal-and-first-measured-run.md)) plants 147 faults, plus 2 green controls, into disposable copies of the review-faults instrument and requires each fault to turn its named acceptance case red.
For every one of its 149 entries it ran that case once unfaulted, then once faulted, one child at a time: 298 children.
It is the slowest module in every lane's evidence run, and its fixed 180 s per-child cap produced false reds on loaded machines (one or two entries in each mode of row 8A's busy candidate run, [0104](0104-row-8-delegated-approval-of-protected-changes.md); one in row 9's mode A, [0074](0074-row-9-seal-and-first-measured-run.md)), each costing a solo re-run.

Measured on the build node (Linux, 32 threads, Python 3.13.5), the module unchanged at `4597dd4`: `Ran 1 test in 244.289s`, `OK`; child time 243.7 s, all of the wall time.
Where the time went:

1. Repeated unfaulted controls: the 149 entries name only 41 distinct (module, case) pairs (`LaunchTests.test_blindness_every_spelling` alone is the control for 49 entries); controls cost 149.7 s, of which 93.4 s repeated a control whose inputs were byte-identical.
2. A few full case builds: `test_plant_match_intervals_cover_changed_lines` builds all 12 fixture repositories (27.7 s per run), `test_external_case_leak_refused` 15.0 s, `test_determinism_history_and_private_key` 6.0 s.
3. Everything serial, although every child already had its own scratch copy.

A planning prototype (same scratch layout, same per-entry checks, one control per pair, a bounded pool) on the same host: serial original 244.3 s; one worker with the dedupe 151.4 s; 4 workers 48.5 s; 8 workers 37.6 s; 0 entries failing in each.

## Decision

`tests/test_review_faults_faults.py` changes, and nothing else.
The `FAULTS`, `GREEN_CONTROLS` and `EXPECTED_FAILURES` tables are byte-identical and the module keeps exactly one test method, so the suite total and skip counts do not move.

1. **One unfaulted control per (module, case), bound to its inputs.**
   The scratch layout is a function; each control runs once in its own copy and records a SHA-256 digest of its copied source tree (every file and symlink, path and bytes, links hashed as links).
   Each entry builds its own copy exactly as before, computes the same digest before applying its fault, and its subtest asserts the digest equals its control's, so a control stands in only for byte-identical inputs.
   The control now also asserts that its case name appears in its output, so it can never stand in for a different case.
2. **A bounded pool.**
   Controls and faulted runs go to a `ThreadPoolExecutor`; workers = `GARS_FAULT_WORKERS` if set (an integer of at least 1, anything else fails loudly), else `max(1, min(4, cpu_count // 4))`: 4 on the Mac (16 threads) and on the build node (32), 1 on a 4-vCPU CI runner.
   `GARS_FAULT_WORKERS=1` reproduces the old one-at-a-time load.
   Workers make no assertions and return plain results; an exception inside a run becomes that result's error.
   The main thread walks `FAULTS + GREEN_CONTROLS` in table order, one `subTest(fault=label)` each, and applies the same assertions as before, printing the same `fault red:` / `exemption green:` / `corpus witness:` lines in the same order.
   Build-module work is submitted first so the 28 s build does not land at the tail; every control is queued before any entry that waits on it.
3. **The cap follows the measured cost.**
   A faulted child's timeout is `max(180, 4 × its control's seconds)`; a control's is 600 s as a hang guard.
   A timeout fails that entry's subtest with its label and the seconds, never a module-level error that hides the other 148.
4. **One summary line**, so every evidence log carries the timing: `faults: 149 entries, 41 controls, workers N, wall W s, slowest control <case> S s`.

Rejected: raising the 180 s cap alone (it hides the cost); caching case builds across runs by content hash (it would change `build_cases.py`, row 9's pinned instrument, and the faulted build must be rebuilt anyway); splitting the module into several test methods (moves README counts and the fresh-clone gate for no speed gain); the same pattern in the sibling fault modules (timed below: none needs it).

Built from `4597dd4` on branch `row9-test-speed` by a Codex producer (account b) in one round: `a7321ff` (the digest, case-name and timeout-reporting guards on a serial skeleton, each shown red first on a five-entry light subset in a scratch copy: control keyed by module only → one named case-name failure; the corpus layout without `tests/data` → one named digest mismatch; a 0.01 s cap → five named timeouts, no module error) and `ce6adc8` (the pool and the summary line).
The lane merged it under the owner's standing delegation (23 Sep); nothing here needs an owner record, and nothing under `gars/_system/` or `evals/review-faults/` changes.

## Review

One fresh Claude Opus 5.5 review on a separate checkout without the producer's transcript, bound by this threat model: (a) every entry's assertions are the old assertions, applied to a run of its own faulted copy; (b) a control is reused only for byte-identical inputs and the same case; (c) no result is lost or reordered by the pool, and a timeout or worker exception fails that entry by name.
Out of scope: the acceptance modules' own strength and the instrument under `evals/review-faults/`.
Verdict **APPROVE WITH CHANGES**: 0 BLOCKER, 0 MAJOR, 1 MINOR, 5 NOTE.
Under the lane's stop rule (only a MAJOR on (a)-(c) is fixed) all six are deferred by name:

- **F-1 (MINOR, c)** An exception raised outside the `try` in `run_entry` / `run_control` (for example in `run_after_control`) would surface as a module-level ERROR rather than one named entry. No such path exists in the code as written; the guarantee rests on layout. Smallest fix: wrap `run_after_control`'s call the same way.
- **F-2 (NOTE, c)** Freedom from deadlock at one worker rests on every control being queued before any entry that waits on it (FIFO); the wait on a control has no bound of its own. A reordering of the two submit loops would hang at `GARS_FAULT_WORKERS=1` rather than fail by name.
- **F-3 (NOTE, tests)** A result is not bound to the child that produced it: a forged stub shaped like a real red result would pass. Out of scope by the threat model; mutant M6 below uses a passing stub.
- **F-4 (NOTE, c)** If cleaning a timed-out entry's scratch folder raises, the cleanup error replaces the "timeout after N s" text; the entry is still red and named.
- **F-5 (NOTE, a)** `assertIn(old, original)` runs only when the file was read; the reviewer traced every path where it was not and each fails on the entry's error instead, so no entry can pass that way.
- **F-6 (NOTE, spec)** Cosmetic spacing in the rewritten test body and `import time` out of alphabetical order; no behaviour change.

## Test

The equivalence proofs, all on the build node's owner account, TMPDIR outside the clone, solo. E1 and E3 ran on a first merge candidate built on `4597dd4`; public main then moved to `37972d8`, which changes none of this module's inputs (the module, the instrument, its acceptance modules and `tests/data` are byte-identical), and E1's order diff was repeated on the new base:

- **E1, same verdicts.** The base module (`4597dd4`'s file, placed beside the new one so both see the same repository) and the new module at `GARS_FAULT_WORKERS=1` and `=4`: every run `OK`, and the extracted verdict lines (147 `fault red:`, 2 `exemption green:`, 50 `corpus witness:`) are identical in content and order across all three (sha256 `4749ca19a34327c0…`).
  Walls: base **245.9 s**, new at 1 worker **152.3 s**, new at 4 workers **57.5 s**.
  Repeated on the final merge candidate against `37972d8`'s module: the same 199 lines, identical in content and order (sha256 `f0ea2702a66866ae…`).
- **E2, every fault still red**: the module's own 147 `fault red:` lines, and M1 below.
- **E3, mutants of the new runner** (each pattern asserted to occur exactly once, a byte backup and a SHA-256-verified restore after each, run at 4 workers):
  - M1, the fault is not written: 147 named reds.
  - M2, the control keyed by module only: 129 named reds on the control's case-name assertion (the 20 entries whose case happened to be their module's first stay green, as they should).
  - M3, the faulted copy of the corpus module without `tests/data`: all 7 corpus entries red on the named digest mismatch.
  - M4, M3 with the digest assertion removed: the same 7 entries red on their own checks (the child errors), so no survivor.
  - M5, the green controls judged as faults: both red.
  - M6, one result replaced by a passing stub (`invalid case hidden`, return code 0, `OK`, the control's digest): that entry red.
  - M7, the fault cap forced to 0.01 s: all 149 entries red as named `timeout after 0.01 s`, and no module-level error.
  - M8, results walked in completion order: the module stays `OK`, and E1's order diff catches it (the same 199 verdict lines, 284 diff lines of reordering).
  No mutant produced a module-level ERROR.
- **E4, red first**: the producer's three reds above, committed before the pool.

## Evidence at the merge candidate

Merge candidate `02f72ed` (first parent `37972d8`, public main; second parent `ce6adc8`), the records commit following it.

| Host, mode | Suite | Module alone, before → after |
|---|---|---|
| build node (Linux, 32 threads, Python 3.13.5), owner account, mode B (TMPDIR set) | 1144 tests, OK, skipped 82, 490 s | |
| build node, mode C (plain) | 1144 tests, OK, skipped 124, 450 s | 246.1 s → 57.5 s (4.3×) |
| Mac (16 threads, Python 3.8.2), mode A (Docker, `GARS_ROW5_SCRATCH` + TMPDIR) | 1144 tests, OK, skipped 14, 2683 s | 948.8 s → 321.8 s (2.9×) |

On the build node the run was solo (process snapshots at the start, between modes, before the module runs and at the end showed no other suite on any account); the mode-independent checks (contracts, counts, harness, pre-registration) are clean.
A first build-node run on this candidate is not cited: another lane's evidence run started at the same moment and shared the host for its whole length (it passed too).
On the Mac, which is shared, the snapshots show another lane's idle waiter; load 3-6. Named caveat: another process ran a CPU-bound test class on the Mac from about 14:05:30 to 14:07:40, inside the "after" module run (14:02-14:08), so that figure is somewhat high; the result passed and stands.
Inside the Mac's mode A run the module took 310 s and its slowest control (`test_plant_match_intervals_cover_changed_lines`, a full 12-case build) 167 s: 13 s under the old fixed 180 s cap, where its entries now get 670 s.
An earlier candidate on `4597dd4` measured the same way gave build node 245.6 s → 57.3 s and Mac 892.8 s → 295.7 s.
The sibling fault modules, timed on the build node over three runs: `test_review_faults_cd_faults` 4.3 s, `…_session_faults` 3.0 s, `…_heredoc_faults` 1.7 s, and `test_bio_faults_faults` 43.5 s, 47.6 s and 68.6 s; the last is named below.
The suite total and skip figures are those of `37972d8` (1144; 14 / 82 / 124) and do not move; `fresh-clone.yml`'s own gate script reads `ok: 124 skips` against the build node's plain log (a planted 125 reads FAIL).

## What this does not close

- F-1 to F-6 above, deferred by name.
- `test_bio_faults_faults` (row 10's fault module) ran 43.5-68.6 s on the build node; if it grows it is the next candidate for the same pattern, in a lane of its own.
- The Mac figures are one run each on a shared machine; the saving per evidence set is an estimate from them, not a guarantee.
- A timing red on a heavily loaded machine is still possible when a control itself runs past 600 s or a faulted child past its cap; it now fails one named entry, and is re-run solo exactly as before.

## Status

Standing. Implemented on `row9-test-speed` and merged by the lane under the owner's 23 Sep delegation; this is a test-infrastructure change and carries no owner approval record.

## Date

2026-09-27
