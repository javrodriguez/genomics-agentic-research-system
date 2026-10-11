status: review passed (W6E-close-1), fold done; athena owed
head: 596071c1 (code commit; this report's own commit follows it). Base 4dd1e8e6 (S1's folded head), branch gap4/w6e-drive-commit, worktree /Users/javrodher/aegis-builds/gap4-w6e.

# Lane w6e-drive-commit: CP2 drive lifecycle, part 1, the commit step

_Gap Study round 4, slice S5 of next-slices-2026-10-11. Written Sun 11 Oct 2026 17:39 EDT (`date`) by the slice's sole writer (Claude Opus 5.5 sub-agent), assigned by glitch-1b under Javier's standing delegation._

No image or container was built or run.
No model was run.
No network was used by any test.
No login, `.env`, sealed, holdout, brief, grader-source or saved-output path was read.
Nothing was pushed, merged or dispatched.

## Scope

The commit step of the drive lifecycle: re-stage and re-hash every staged blob against `sha256_after` after masking (CP2-requirements, w4c Q3), chronological history (open question 10), and the restart refusal while leaked ids remain (open question 11).
Launch, turns, quiescence, routing, teardown and the finally-path cleanup stay S6.

## What changed

`drive.py` (moved from w1a to this lane under ruling S5-gap4-1).
The new code is appended after round 3's `main()`, and everything above the banner is round 3's file byte for byte.
So no line other files cite by number moves (drive.py:149, 158-186, 170, 241-242, 741, 750, 1346, 1348, and the constants test_run_take reads by ast).
The plan's named-changes block (R4-1 to R4-6) sits in that banner, not in the top docstring, for the same reason.

- `TakeRepo(runtime=, record_files=, secrets=, rules_scanner=, holdout_matcher=None, root=, repo=, caller_env=None)` is batch.Batch's repo.
- `commit_records(row, attempt, outcome)` works in this order:
  - checks the outcome's keys and its slot/attempt;
  - validates the take's record files (absolute, normalised, inside the repo, a regular file, a scan kind, listed once, never the ledger);
  - appends the outcome to `outcomes.json` from HEAD's bytes;
  - stages the take's files and the ledger, and requires the staged names to be exactly those;
  - scans the staged list with `scan_record.scan`, and refuses on any refusal;
  - **stages again**, re-checks the staged set, and refuses unless every staged blob's sha256 (`git cat-file blob :<path>`) equals the scan's `sha256_after`;
  - commits with `-F`, and returns the commit, the masked list, the event count and the holdout state.
- `history()` is `takes.read_history` (commit order).
- `leaked_ids()` lists the committed outcomes' `leaked_container` values.
- `register()` first calls `run_take.refuse_restart_if_leaked`, then `takes.commit_registration` with a process-local `RegistrationGuard`.
- `preflight_take(...)` passes every argument straight to S1's `preflight.collect_and_evaluate`.
  drive.py never names the lock loader, `LOCK_KEYS`, `load_take_lock` or the pure evaluator.

`tests/test_drive_commit.py` (new) has 23 tests.
Its setUpModule arms a process guard that admits only `git -C <its own scratch folder>`, gives git an empty HOME with no global or system config, patches `prereg.load` and `prereg.require_frozen` with synthetic values (this base has no pre-registration, and drive.py reads one at import), and only then imports drive.
Planted tests prove the guard is armed.

COPIED.d:
- `w6e-drive-commit.json` (new) claims drive.py as `edited` from evals/gap-study-3/drive.py, naming S5-gap4-1, plus the test, the fragment and the checks file.
- `w1a-cp1-scaffold.json` drops its drive.py entry, and its own self-entry records the transfer under S5-gap4-1.

`checks.d/w6e-drive-commit.txt` holds two lines:
- the test module;
- a check that drive.py is round 3's file at e2979b31 with only the appended section added.

## Guards, checks and witnesses

| guard | bound check | witness (one anchor edit, compiled in memory) | result |
|---|---|---|---|
| re-stage after masking | C1-restage: a planted value in a stream file is committed masked, the bytes on disk equal the committed ones, every line is still JSON, the tree is clean, and one event | omit-restage | red by C1-restage (1 own, 0 collateral, 0 errors) |
| re-hash vs sha256_after | C2-rehash: a writer appends after the scan, so the commit is refused, names the file, never carries the value, and HEAD is unchanged | omit-rehash | red by C2-rehash (2 own, 0 collateral, 0 errors) |
| chronological history | C3-history: outcome 1 (failed), then a re-run ruling, then outcome 2 come back in that order, and batch.history_problems is empty | concatenated-history | red by C3-history (1 own, 0 collateral, 0 errors) |
| restart refusal | C4-restart: a fresh repo whose history records a leaked id still listed refuses register with LeakedContainer naming it, commits nothing, and makes exactly one full listing; once the id is gone, it registers | omit-restart-refusal | red by C4-restart (3 own, 0 collateral, 0 errors) |
| staged set exact | C5-staged: a stray pre-staged file refuses the commit, naming it | admit-stray-staged | red by C5-staged (2 own, 0 collateral, 0 errors) |
| S1 entry point | C6-preflight: a spy on collect_and_evaluate gets every argument once, returns its record, and the pure evaluator, load_take_lock and the lock loader all trip | bypass-entry-point | red by C6-preflight (1 own, 0 collateral, 0 errors) |

Each witness counts only when its bound check is green on the real drive.py first; an ERROR line or an unperformed anchor is never a kill.
Further unwitnessed tests cover:
- a take with nothing to mask;
- a failed take with no records (the ledger alone);
- a value in an unmaskable `launch` file, which refuses with no value in the message;
- a rules-scanner finding, which refuses;
- seven bad record lists and three bad outcomes, which refuse before any write;
- a failing container listing, which refuses the restart unread.

## Red, then green (Mac, `mac_slot.py light-ok &&`, `env -u CONDA_PREFIX -u CONDA_DEFAULT_ENV`, Python 3.13, `-B -W ignore`)

Red on the unmodified drive.py: `Ran 23`, `FAILED (failures=20)`, 0 errors, rc 1.
The three tests green on the base are infrastructure: two planted guard tests and the witness-registry naming test.

Green at 596071c1:
- test_drive_commit: `Ran 23 ... OK`, rc 0, about 20 s; six WITNESS lines printed to stderr, inline, nothing after OK.
- test_round4's main over a folder holding only this module: `test_round4: 23 run, 0 skipped, 0 expected failures`, rc 0.
- test_preflight: `Ran 43 ... OK`.
- test_scaffold: `Ran 49 ... OK`, 605 s.
- test_run_take: `Ran 44 ... OK`.
- test_harness_bookkeeping: `Ran 14 ... OK`.
- test_task_explain_not_act: `Ran 76 ... OK`. The last three bind drive.py by line number or ast.
- `copy_manifest.py --check`: ok, 221 files, 28 fragments.
- The checks.d prefix line: rc 0.

`build_draft.py --check` exits 1 here, and it exits 1 identically on the unmodified base (stash probe).
The error is `git show bf065feedccc:evals/gap-study-3/prereg.json ... not in` that commit.
At this base build_draft.py is still round 3's copy; w5c's replacement lives only on the w5c merge (see Q1).

Not run: run_checks.py and the full battery (athena's).

## Departures and questions for glitch-1b

- **Q1 (base).** The brief says 4dd1e8e6 builds on the w5c merge 28e1be3e. It does not (`git merge-base --is-ancestor 28e1be3e HEAD` fails); its base is 89b54db4.
  The w5c merge touches none of drive.py, box/, takes.py or batch.py.
  It does edit `COPIED.d/w1a-cp1-scaffold.json` and `tests/test_scaffold.py` (BLOCKED emptied, copied_modules reading w5c's fragment), so merging this branch onto it conflicts in those two files.
  The resolution is mechanical: copied_modules reads all three fragments.
- **Departure w6e-1 (needs ratification).** Moving drive.py out of w1a's fragment and editing it turns two tests in w1a's `tests/test_scaffold.py` red: the identical-copy refusal case lists drive.py, and copied_modules reads only w1a's fragment.
  Two edits were made:
  - denials.py (identical, still w1a's) stands in for drive.py, so the case keeps four files;
  - copied_modules also reads w6e's fragment, so drive.py is still import-probed.
  Both are recorded in w1a's fragment entry for that file.
  The alternative is to keep drive.py's entry in w1a's fragment (w6a's precedent), but the brief asked for a transfer, and the first test breaks with any edit to drive.py anyway.
- **Q2.** A refused commit leaves the tree as it stands: the outcome is written, files are staged, and masks are on disk (takes.py's "a failed commit remains for human reconciliation").
  The next registration then refuses on the unclean tree.
  Should S6 instead roll back the ledger write?
- **Q3.** scan_record's masked `events` should reach `outside_reach_events` before routing, but the plan routes before the commit and the commit scans.
  commit_records returns `events`, and the order belongs to S6's drive step.
- **Q4.** The restart check runs on every `register` (one full listing each), not once per process.
  It is stricter and cheap; S6 may hoist it.

## Writer release

The sole writer releases the worktree at this report's commit.
The tree is clean, and no `__pycache__` is left: one, made by the commit, was removed.
Scratch outputs are in the session scratchpad (`w6e-*.txt`), outside the repository.

## Fold of review round 1 (W6E-close-1, glitch-1b, 11 Oct)

Round 1 found no MAJOR, three MINORs that each loosened a check, and two NITs; all are folded at 8d0ccb02 (written 17:50 EDT, `date`).

- W6E-R1-1: before the ledger is written, commit_records refuses an outcome that `batch.Batch.history_problems(history() + [outcome])` rejects. Check C7-duplicate commits the same (slot, attempt) twice: the second refuses, the ledger bytes and HEAD are unchanged, and history() still reads. Witness admit-duplicate-outcome: red by C7-duplicate (3 own, 0 collateral, 0 errors).
- W6E-R1-2: `_take_files` refuses outcomes.json, rulings.json and takes.json, and any path already tracked at HEAD, before anything is written.
  - C8-reserved covers an untracked rulings.json and a tracked takes.json. Witness admit-reserved-names: red by C8-reserved (1 own).
  - C9-tracked covers a tracked source file (README). Witness admit-tracked-paths: red by C9-tracked (1 own).
- W6E-R1-3: the commit is bound to the checked tree.
  - `git write-tree` writes the index once. The tree's change set against HEAD must be exactly the declared files, and each blob is hash-checked from `<tree>:<name>`.
  - The commit is then `commit-tree <tree> -p <head>` plus `update-ref HEAD <new> <head>`, so a file staged later never lands and a moved HEAD refuses.
  - C10-bound uses the no-op `_before_commit` seam, never a second process: an interloper staging a file is never in HEAD, and an actor moving HEAD makes the commit refuse with its HEAD kept. Witness commit-the-index (back to `git commit`): red by C10-bound (2 own).
  - Consequence: the stray-file guard now has two layers, the staged-set refusal before the scan and the tree's change set before the commit. Either alone refuses the stray, so the admit-stray-staged witness turns both off: red by C5-staged (2 own). Neither layer is credited alone.
- W6E-R1-4: the docstring names scan_record.ScanError and NotReady passing through, failing closed.
- W6E-R1-5: the checks.d comment states the Python 3.9 floor.

Red first on c96751c5 (the four new checks and four new witnesses): `Ran 31`, `FAILED (failures=8)`, 0 errors, rc 1. The 23 earlier tests stayed green.

Green at 8d0ccb02 (Mac, light-ok, Python 3.13, `-B -W ignore`), all rc 0:
- test_drive_commit: `Ran 31 ... OK`, about 66 s for the module; every single case is under 60 s. Ten WITNESS lines, each red by its own check with 0 errors.
- test_round4's main over this module alone: `31 run, 0 skipped, 0 expected failures`.
- test_preflight: `Ran 43 ... OK`.
- `copy_manifest.py --check`: ok.
- Two single test_scaffold cases, `TheManifest.test_check_passes_on_the_folder` (15 s) and `test_a_copy_that_differs_without_an_edited_entry_is_refused` (39 s). The whole test_scaffold module is athena's.
- The checks.d prefix line: rc 0.

Owed: athena run_checks on 8d0ccb02.

RESUME HERE: hand-back at 8d0ccb02
