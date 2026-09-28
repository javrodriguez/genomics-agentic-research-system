---
date: 2026-09-28
status: standing
kind: decision
touches:
  - tests/test_bio_faults_faults.py
symptoms:
  - tests/test_bio_faults_faults.py ran 43.5-68.6 s on the build node in three runs (0180) and 222-245 s on the Mac, one child at a time
  - its fixed 20 s per-child cap sat only about three times above its slowest child (7 s) on a loaded Mac
---
# The science fault module runs one control per case and a bounded pool, with the same verdicts

## Context

The science fault module plants 50 faults into disposable copies of the science review kit and requires each fault to turn its named acceptance case red.
For every entry it copied the layout, ran that case once unfaulted, then once faulted, one child at a time: 100 test children.
[0180](0180-row-9-fault-module-one-control-per-case-and-a-bounded-pool.md) made the same change to the review-faults fault module and named this one as the next candidate (43.5 s, 47.6 s and 68.6 s on the build node).

Measured on the Mac (16 threads, Python 3.8.2), the module unchanged at `a80df2d`: 245 s plain and 222.0 s under a timing driver that logs every child, both `OK`.
Where the time went:

1. The children are nearly all of it: 208.3 s of 222 s (the pipeline acceptance module 201.8 s over 76 children, the core module 6.5 s over 24); the per-entry layout copy and its git plumbing 13.6 s in total.
2. Repeated unfaulted controls: the 50 entries name only 35 distinct (module, case) pairs; repeats cost 30.5 s (14%).
3. Everything serial; the slowest single child took 7.0 s, so there is no long pole and a pool scales nearly linearly.

## Decision

`tests/test_bio_faults_faults.py` changes, and nothing else.
The `FAULTS` table is byte-identical and the module keeps exactly one test method, so the suite total and skip counts do not move.

1. **One unfaulted control per (module, case), bound to its inputs.**
   The scratch layout (four copied trees, five copied files, a minimal git store holding only HEAD's commit object) is a function; each control runs once in its own copy and records a SHA-256 digest of it (every file and symlink outside `.git/`, path and bytes, links hashed as links, plus the copy's HEAD).
   Each entry builds its own copy exactly as before, computes the same digest before applying its fault, and its subtest asserts the digest equals its control's, so a control stands in only for byte-identical inputs.
   The control now also asserts that its case's `... ok` line appears in its output, so it can never stand in for a different case.
2. **A bounded pool.**
   Controls and faulted runs, layout copies included, go to a `ThreadPoolExecutor`; workers = `GARS_FAULT_WORKERS` if set (an integer of at least 1, anything else fails loudly), else `max(1, min(4, cpu_count // 4))`, the rule and the variable of 0180.
   Workers make no assertions and return plain results; an exception inside a run becomes that result's error.
   The main thread walks `FAULTS` in table order, one `subTest(fault=label)` each, and applies the same assertions as before (the `old` text found once, control return code 0, faulted return code not 0, `FAIL: <case>` and no `ERROR:`, and the looser `FAIL: ` for `envelope from stub text`), printing the same `science fault red:` lines in the same order.
   Every control is queued before any entry that waits on it, and the pipeline module's build and launch cases are submitted first (the review's F-3 asked that this scheduling choice be named).
3. **The cap follows the measured cost.**
   A faulted child's timeout is `max(20, 4 × its control's seconds)`, never tighter than the old 20 s; a control's is 120 s as a hang guard.
   A timeout fails that entry's subtest with its label and the seconds, never a module-level error that hides the other entries.
4. **One summary line**, so every evidence log carries the timing: `science faults: 50 entries, 35 controls, workers N, wall W s, slowest control <case> S s`.

One behaviour is different by design, as in 0180: a faulted run no longer follows its control inside the same copy, so nothing a control leaves behind reaches it; E1 below shows no verdict depended on that.

Rejected: raising the 20 s cap alone (it hides the cost); sharing one copy across entries (every entry mutates its copy); a process pool (the threads only wait on children); a helper shared with the review-faults fault module (it would touch a landed module for a few lines of reuse).

Built from `a80df2d` on branch `bio-test-speed` by a Codex producer (account b) in one round: `0b75d88` (the digest, case-name and timeout-reporting guards on a serial skeleton, each shown red first on an eight-entry subset through a driver that altered only the imported module: control keyed by module only → five named case-name failures; one copied file left out of an entry's layout → one named digest mismatch; a 0.01 s cap → eight named timeouts, no module error) and `e973292` (the pool and the summary line).
The producer's static audit found no shared writable state that parallel children could collide on: the real repository is only read (`cat-file`), and every acceptance path writes under its own copy or TMPDIR.
The lane merged it under the owner's standing delegation (23 Sep); nothing here needs an owner record, and nothing under `gars/` or `evals/` changes.

## Review

One fresh Claude Opus 5.5 review on a separate checkout without the producer's transcript, bound by the threat model of 0180: (a) every entry's assertions are the old assertions, applied to a run of its own faulted copy; (b) a control is reused only for byte-identical inputs and the same case; (c) no result is lost or reordered by the pool, and a timeout or worker exception fails that entry by name.
Out of scope: the acceptance modules' own strength and `evals/bio-faults/`.
Verdict **APPROVE**: 0 BLOCKER, 0 MAJOR, 0 MINOR, 4 NOTE.

- **F-1 (NOTE, tests)** No listed mutant showed that the digest covers file bytes rather than paths alone. Taken up: mutant M9 below.
- **F-2 (NOTE, c)** Freedom from deadlock at one worker rests on every control being queued before any entry that waits on it (FIFO); the wait on a control has no bound of its own (0180's F-2, same shape).
- **F-3 (NOTE, spec)** The build-and-launch-first submit order was not listed in the plan's description; it is named above. Results are re-indexed and walked in table order, so it cannot reorder verdicts.
- **F-4 (NOTE, b)** The control's case check needs `<case> (` and ` ... ok` on one line; a write to the child's stderr mid-line would false-red it. None exists today; both the Python 3.8 and 3.12 forms match.

The reviewer's own subset run used a scratch path holding one of the kit's forbidden words, so two launch controls refused as the acceptance tests require; the runner failed their entries by name, as designed.

## Test

The equivalence proofs, on the merge candidate (its tree is the branch head's), TMPDIR outside the clone on a neutral path:

- **E1, same verdicts, on both hosts.** The base module (`a80df2d`'s file, placed beside the new one so both see the same repository) and the new module at `GARS_FAULT_WORKERS=1` and `=4`: every run `OK`, and the 50 extracted `science fault red:` lines are identical in content and order across all three (sha256 `948fd909c1880e26…` on both hosts).
  Build node (Linux, 32 threads, Python 3.13.5, solo): base **43.6 s**, new at 1 worker **38.5 s**, new at 4 workers **10.4 s** (4.2×).
  Mac (16 threads, Python 3.8.2, shared): base **156.5 s**, new at 1 worker **161.9 s**, new at 4 workers **51.2 s** (3.1×).
  At one worker the digest work roughly cancels what the dedupe saves; the gain is the pool.
- **E2, every fault still red**: the module's own 50 `science fault red:` lines, and M1 below.
- **E3, mutants of the new runner** (build node, each pattern asserted to occur exactly once, a byte backup and a SHA-256-verified restore after each, run at 4 workers):
  - M1, the faulted run sees an unfaulted copy (the layout rebuilt after the fault is applied): all 50 named reds on the faulted return code.
  - M2, the control keyed by module only: 45 named reds on the control's case-name assertion (the 5 entries whose case happened to be their module's first stay green, as they should).
  - M3, one copied file left out of each entry's layout: all 50 red on the named digest mismatch.
  - M4, M3 with the digest assertion removed: the module stays `OK` with the same verdicts; a documented survivor, because no named case reads that file, and M3 alone is red, which is what the plan requires.
  - M5, each entry's result replaced by its control's: all 50 red on the faulted return code.
  - M6, one result replaced by a passing stub (`repo drop removed`, return code 0, `OK`, the control's digest): that entry red.
  - M7, the fault cap forced to 0.01 s: all 50 red as named `timeout after 0.01 s`, and no module-level error.
  - M8, results walked in submission order: the module stays `OK`, and E1's order diff catches it (the same 50 lines, reordered).
  - M9 (the review's F-1), one byte appended to a copied file in each entry's layout: all 50 red on the named digest mismatch, so the digest covers bytes, not paths alone.
  No mutant produced a module-level ERROR.
- **E4, red first**: the producer's three reds above, committed before the pool.

## Evidence at the merge candidate

Merge candidate `2a93c65` (first parent `868a1b2`, public main; second parent `e973292`), the records commit following it.
It is the first candidate `6e9e2ba` (first parent `a80df2d`) rebuilt after the filesystem-tool vocabulary change ([0185](0185-filesystem-tool-vocabulary.md)) landed first: the tree diff from `6e9e2ba` to `2a93c65` is byte-for-byte the diff `a80df2d..868a1b2`, and `2a93c65` differs from `868a1b2` only in `tests/test_bio_faults_faults.py`.
That change touches `gars/_system/tools/policy.py` and `gars/_system/tools/registry.json`, which this module copies into every scratch layout with the rest of `gars/_system` (so both are inside the digest); neither this module, its two acceptance modules nor the science kit names either file, and the `gars/_system` code the kit loads imports only `tools.execution`, which imports the standard library alone.
Mac mode A and build-node mode C ran on `6e9e2ba` and carry; mode B and E1 were re-run on `2a93c65`.

| Host, mode, candidate | Suite | This module inside the suite | Module alone, before → after (4 workers) |
|---|---|---|---|
| build node (Linux, 32 threads, Python 3.13.5), owner account, mode B (TMPDIR set), `2a93c65` | 1172 tests, OK, skipped 82, 439 s | 10.4 s | 43.5 s → 10.4 s (E1 repeated: the same 50 lines, sha256 `948fd909c1880e26…`) |
| build node, mode B, `6e9e2ba`, solo re-run | 1150 tests, OK, skipped 82, 431 s | 10.4 s | |
| build node, mode B, `6e9e2ba`, first run | 1150 tests, 1 failure (below), skipped 82, 434 s | 10.5 s | |
| build node, mode C (plain), `6e9e2ba` | 1150 tests, OK, skipped 124, 432 s | 10.4 s | 43.6 s → 10.4 s |
| Mac (16 threads, Python 3.8.2), mode A (Docker, `GARS_ROW5_SCRATCH` + TMPDIR), `6e9e2ba` | 1150 tests, OK, skipped 14, 3008 s | 121.7 s | 156.5 s → 51.2 s |

On the build node every run was solo: process snapshots at the start, between modes, before E1, before E3 and at the end showed no other suite on any account, and each run started only after three clean polls or the other lanes' runs there had ended. The mode-independent checks (contracts, counts, harness, pre-registration) are clean, and no temporary file was left in the system temp folders.
The first mode B run's one failure was `test_execution_policy …test_prepared_local_failure_refuses_unclassified_retry`, which read a bare `FAILED` instead of `FAILED:EXIT_17`. It is not this change: nothing it runs differs between `a80df2d` and the candidate, and the filesystem-tool vocabulary lane traced the same failure the same night to a pre-existing race in the local executor's exit record (the file is truncated before it is written, and a read in that window sees it empty; recorded in [0186](0186-fs-vocabulary-0185-delegated-approval-of-protected-change.md)). Under the carried rule for a timing-class red it was re-run solo, on the same candidate, and passed; it also passed in modes A and C and on `2a93c65`.
On the Mac, which is shared, another lane's producer ran its own test classes throughout (load 14 at the start, 4-8 later), so the Mac walls are high; the results passed and stand.
Measured before the change on the same Mac at a lower load: 245 s plain and 222 s under the timing driver.
The suite total and skip figures are those of `868a1b2` (1172; 14 / 82 / 124) and do not move; this change adds no test.

## What this does not close

- F-2 and F-4 above, deferred by name.
- The local executor's exit-record race behind the first mode B run's failure, which belongs to its own lane.
- A scratch path that holds one of the science kit's forbidden words (`bio`, `fault`, `review`, `case`, `eval` and others) turns the launch cases red, in this module and in the pipeline module alike; that is the kit's rule, not this change, and every evidence path in this lane was chosen neutral.
- The Mac figures are single runs on a shared machine; the saving per evidence set is an estimate from them.

## Status

Standing. Implemented on `bio-test-speed` and merged by the lane under the owner's 23 Sep delegation; this is a test-infrastructure change and carries no owner approval record.

## Date

2026-09-28
