---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/mutate.py
  - evals/MUTANTS-INTERFACE.md
  - gars/tests/test_mutation_runner.py
  - README.md
  - DEVELOPMENT.md
symptoms:
  - at public main a779084 the mutation runner's own baseline suite is red, because its tested tree carries no repository and tests added since need a checkout with history
  - the runner caps every subprocess at 300 s, the whole-suite runs included, and one timeout refuses the whole run
  - row 3's follow-up needs a second sealed run that the runner can actually score
---
# Row 3: the mutation runner tests a checkout with history, and its whole-suite cap rises, under the owner's delegation

Approval record for a change to evaluation code, required before any sealed run uses it (§7.3, R-074: "changing evaluation criteria or a sealed fixture" always needs an approval record), as [0085](0085-row-3-first-run-preregistration.md) anticipated for the runner's limit.
The owner delegated such approvals on 23 September 2026 ("I delegate every decision to you, use your best judgement … just get things done", recorded in aegis STATE under Carried rules), so this record is written by Glitch under that delegation and labelled as such; it is not in the owner's words.
Its shape follows row 12's [0070](0070-row-12-fix-round-owner-approval-of-protected-changes.md) and row 7's [0079](0079-row-7-delegated-approval-of-protected-additions.md).
This commit carries the change, its tests, the count lines, this record and the regenerated decision index, and nothing else; it sits directly on public main `e589ce8` (the landing of lane pg, 0107).
The measurements below were taken at the previous main `a779084`, before pg landed; pg added 20 tests and changed neither `evals/` nor `tests/run_tests.py`.

## Context

Row 3 exits on "≥ 8/10 mutants killed; 7/7 wrapper contracts" (§18).
Its first sealed run, [0086](0086-row-3-first-sealed-run.md), killed 5/10 at `2a65dbf` under the runner as then shipped.
A follow-up strengthens the suite and measures it with a new, separately sealed run; that seal does not exist at this commit, and no census, timing gate or run of any seal has used this change.

**The tested tree had no repository.** The runner (`evals/mutate.py`, byte-identical from `2a65dbf` to `e589ce8`) materializes the run commit's blobs into a scratch folder (`committed_tree`) and copies it without `.git` (`copy_tree`).
Since row 3's first run, tests that need a checkout with history have been added: row 9's review-fault case builder reads `git ls-tree` at an older commit, row 8's backend bench records `HEAD`, and the decision-link check reads the repository's file list.
A full run of the suite at `a779084` in such a folder, measured on 2026-09-25 as the follow-up's first timing (a `git archive` copy, the runner's tree shape, in 0085 rule 5's environment on macOS), took 1468.6 s and ended `FAILED (failures=9, errors=7, skipped=79)`; every failing case needs `.git`.
The runner refuses a run whose baseline suite is red, so from `a779084` on it could not score any seal: the follow-up's second seal would have been spent on a refusal.

**The 300 s limit.** The runner sends every command through `execute(argv, root, stdin='', timeout=300)`, and `suite()` used the default, so each whole-suite run was capped at 300 s; a `TimeoutExpired` is `mutation runner: REFUSED` with exit 2, and the runner runs the suite up to eleven times.
The suite has 681 tests at `a779084` and 701 at `e589ce8` (703 with the two runner tests this commit adds).
The macOS run above took 1468.6 s, and the follow-up's evidence runs move to the homelab's Linux node (Node 1) for that reason (0088 pre-registers it).
On that node, five sequential runs at `a779084` in the tree shape this record approves (a fresh clone detached at the commit and checked clean, which writes the same bytes as the runner's materialization because GARS has no `.gitattributes`; `env -i PATH=/usr/bin:/bin HOME=<home> TMPDIR=TEMP=TMP=<scratch> GARS_TEST_NO_CONTAINER=1 PYTHONDONTWRITEBYTECODE=1`, Python 3.13.5, git 2.47.3, 32 threads, the node owner's account with no other suite running), on 2026-09-25 (17:05–18:05 UTC): 501.9, 502.3, 502.0, 551.5 and 517.3 s; slowest **551.5 s**.
Every run was green (`Ran 681`, `OK (skipped=79)`, `wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`), and a process snapshot at each run's start and end showed no other suite, build or model session above 10 % CPU, so none was re-timed.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following changes to evaluation code, on 2026-09-25.
Only the quoted sentences in this record are the owner's words.

1. **The tested tree carries its repository.** `attach_history()` runs after `committed_tree()`: the files stay exactly the run commit's committed blobs, and a `.git` cloned from the source (`git clone --no-local --no-checkout`) is moved in, its remote removed, `HEAD` detached at `run_sha` and the index read from it; the runner refuses unless `git status --porcelain --untracked-files=all` is then empty.
   `copy_tree` (and so every restore) now copies `.git` with the tree; `tree_hash` still excludes `.git`, so every hash the runner records keeps its meaning.
   Ignored and untracked files still never enter the tested tree: the clone carries committed history only.
2. **A dirty tree can never kill a mutant.** A `.git`-bearing tree opens a new way to "kill": a test that reads `git status` or diffs the working tree would fail on any applied mutant merely because the tree is dirty.
   Two shapes were weighed: running the suite on the dirty tree and naming such tests, or committing the applied mutant first.
   The runner takes the second: `commit_mutant()` commits the applied mutant inside the throwaway tree (a fixed runner identity and dates, hooks off, `--no-verify`) just before the suite, so the suite always sees a clean checkout at a new `HEAD`, by construction and whatever tests are added later.
   What remains possible is a test that asserts `HEAD` itself; the inert control below shows the current suite has none.
   The same inert line left uncommitted also ran green on that node, so no current test fails on a dirty tree alone; the commit makes that hold for tests added later.
3. **The whole-suite cap.** One named module constant, `SUITE_TIMEOUT = 1800`, which `suite()` passes to `execute(...)`; `execute`'s own default stays 300, so every probe and every `git` call keeps its 300 s cap.
   Why 1800 s: about 3.3 times the slowest measured run (551.5 s); the old cap's margin over row 7's 242 s run (about 1.2 times) proved too thin as the suite grew.
   A sealed run's go threshold is set by its own pre-registration; the follow-up fixes it at 1080 s, 60 % of the cap, the ratio of 0085's 180/300.
   A mutant that hangs the suite still ends in a refusal, now after 30 minutes.
4. **The interface** (`evals/MUTANTS-INTERFACE.md`) states both limits, the repository in the tested tree and the commit of each mutant; no other sentence changes.
5. **The first run is untouched.** 0086 stands as graded under the 300 s cap; the new cap is never applied to seal 1, and 0086's result is never re-read under it.
   The same holds for the tested-tree change: seal 1 was scored at `2a65dbf`, whose suite needed no repository, and it is never run again.

## What this does not close

- A mutant-induced timeout remains a refusal, never a kill and never a survivor (0085 rule 7).
- A future test that asserts the exact `HEAD` commit would fail on every committed mutant; the inert control is re-run by any later sealed run's timing gate.
- The probes' 300 s cap is unchanged.
- The exit (≥ 8/10) needs the second sealed run (0088, 0089); public claims need an `external_human_seal`.
- A record written by Glitch under a delegation on the same machine is not the owner's own review of the change.

## Test

At this commit, on 2026-09-25:
`python3 gars/tests/test_mutation_runner.py` printed `Ran 11 tests` and `OK`; its two new tests were watched red first — `test_tested_tree_carries_history_at_run_sha` errors on the previous runner (baseline refused), and `test_a_dirty_tree_never_kills_an_untested_mutant` fails when `commit_mutant` is removed.
A recorder that replaces `execute` in a `git archive` copy of this commit (asserting `execute`'s default is still 300) and drives `suite()` and `measure_one` on the runner test's own toy mutant printed `suite 1800`, `probe default 300` and `git default 300`; on a copy of `e589ce8` it printed `suite default 300`, so the check can fail.
On Node 1, the inert control (a comment line appended to `gars/_system/wrapperlib.py`, committed as the runner commits a mutant) ran the whole suite green (`Ran 681`, `OK (skipped=79)`, 502.4 s), so no current test asserts the exact `HEAD`.
`python3 tests/check_counts.py` is clean at 703 tests; `python3 tests/test_decision_links_resolve.py` printed `Ran 3 tests`, `OK` and `citations: 376/376 resolve` after `bash docs/decisions/build_index.sh`.

## Status

standing

## Date

2026-09-25
