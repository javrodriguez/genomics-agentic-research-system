---
date: 2026-09-23
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/02_bioinformatics/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
symptoms:
  - the row 12 fix round's guard, settings and stage-contract changes are protected paths with no owner approval record
  - 0069 requires that record as a separate owner commit, record 0070, in the shape of 0066
---
# Row 12 fix round: the owner's approval of its protected changes

Addendum to [0069](0069-row-12-fix-round-minors.md), which stays byte-identical, including its round 6 and round 7 addenda.
Every file this record touches is a protected path (R-094, spec §9.3), so their approval is the owner's own commit with this record as its approval record, in the shape of row 12's [0066](0066-row-12-owner-approval-of-protected-changes.md).
The changes themselves arrived with the producer's commits `71654fe` (guard, settings and both stage contracts) and `992e9d4` (the stage-03 contract's execution-evidence boundary); `dcd11a9` touches no protected path, and this commit adds only this record and the regenerated decision index.
The round was built on public main `e59dfc0` and replayed onto main `c1c8c43` after decision 0068 (the evals round 2 correction) took that number there; the replay renumbered this round's record from 0068 to 0069 and this approval from 0069 to 0070 and changed nothing else, which a file-by-file comparison of every replayed commit against its original confirmed.

## Context

The row 12 fix round started from public main `e59dfc0` to close the four MINORs and three NOTEs that 0066 left open.
The owner chose its options on 23 September 2026, quoted verbatim in 0069: "1B · 2A · 3A".
0069's own section on owner rulings keeps the protected-path approval out of the producer's hands: guard_hook.py, settings.json and both changed CONTEXT.md contracts "require a separate owner commit, record **0070**, in the shape of 0066. The producer never writes 0070 and never claims that approval."
The round was reviewed in fresh contexts in rounds 5, 6 and 7; round 6 answered round 5's findings and round 7 answered round 6's, each as a dated addendum to 0069.
Round 7 changed no protected path, so the changes approved here are those of `71654fe` and `992e9d4` as they stand at `dcd11a9`.

## Decision

The owner approves the following protected changes as they stand at `dcd11a9`, on 23 September 2026.

1. **The guard makes stage-03 execution evidence executor-owned (0069 MINOR-4, owner option 1B).** `guard_hook.py` adds three read-only patterns to `READ_ONLY`: `projects/*/03_custom_analysis/*/run/*`, `projects/*/03_custom_analysis/*/run/**/*` and `projects/*/03_custom_analysis/*/.gars_submissions.jsonl`.
   They cover the run marker, the generated launchers, the local exit and log files, nested run files and the append-only submission record, through the same guard machinery that already protects stage 02's marker.
2. **Settings mirror the guard.** `.claude/settings.json` adds the same three paths as `Edit` and `Write` denies: three deny pairs, six lines.
3. **The stage-02 parent contract names every state code writes (0069 MINOR-3).** The STATUS paragraph now enumerates eight states: SUBMITTED, RUNNING, VALIDATING, ARTIFACT_MISSING, STALE, COMPLETE, FAILED:<reason> and CANCELLED.
   Steps 5 to 9 and templates T2 and T3 route VALIDATING, ARTIFACT_MISSING and STALE to step 10 and the sub-stage's collect step; CANCELLED follows FAILED:<reason> to the user's decision in T6, retitled "Sub-stage failed or cancelled", which now says corrected inputs need prepare again before another submission.
   The Response Format hand-off is corrected from step 9 to step 10.
4. **The stage-03 contract hands execution evidence to the executor (0069 MINOR-4 and round 5 review MINOR-1).** A new rule forbids writing `run/` or `.gars_submissions.jsonl`, directly or from a script.
   **Complete** now requires the executor launcher's marker after exit 0 and, for every script, a latest submission record binding unchanged script and launcher SHA-256 values to a scheduler COMPLETED job; `verify` alone writes `OUTPUTS.tsv` and `STATUS`.
   A new **Execution evidence boundary** paragraph states that executed scripts share the agent's OS user and can alter that evidence, so the prohibition is a contract instruction, not isolation.
   Step 7 is rewritten: every script uses `set -euo pipefail` and is submitted through `executorlib.py submit`, which checks the analysis directory's PLAN.md, generates the launcher and records the hashes; the launcher clears, writes or removes the marker, and the login-node route uses the local backend through the same call.
   Step 9's exit 2 now covers missing or invalid execution evidence; T4 and T5 point to `executorlib.py status` and the scheduler log, since verify alone writes STATUS; the artifact table restricts STATUS to `COMPLETE` written by `verify` and adds `run/` and `.gars_submissions.jsonl` as executor-owned.

## What this does not close

- **Executed scripts can alter executor-owned evidence (round 5 review MINOR-1, answered in 0069's round 6 addendum).** They share the agent's OS user, so a script can change the submission record or other scripts' evidence under `run/`, and a later successful script can remove an earlier failed script's record; plan approval binds PLAN.md, not script bodies.
  The guard and settings approved here stop agent tool calls, not script processes; separate-user execution with evidence inaccessible to script processes is what closes this, and this round does not implement it.
- An approved script body that does no real work and exits 0; the plan's declared-output gate still applies.
- The window between cancel's poll and its signal, and PID reuse while a local job still reads RUNNING; resubmit may refuse R-076 while an unrelated live process occupies the old PID (round 6 NOTE-1).
- Round 5 NOTE-1: the broad fnmatch `run/` matching stays conservative and unchanged, and the nested-glob plant is a static inventory witness, not independent behavioral coverage.
- Real Slurm, `sacct` and `scancel` output shapes, Python 3.6.8 execution, separate OS users, and the harness's native settings-glob semantics remain unverified.
- Ambiguous submission recovery (ruling 9): stop, retain evidence and work; no reconciliation or reservation release is invented, and old null-job entries cannot be reclassified from their error text.
- Published benchmark pins (ruling 10) and live scheduler acceptance, including R-076, remain open and untouched.
- Round 4 NOTE-1: accounting loss can leave VALIDATING → STALE; durable completion and unattended reconciliation need the owner's later ruling on the durable state table.
- **Round 7 review NOTEs.** Under the login-node route, `executorlib.py status <PID>` can report a colliding stage-02 Slurm job's state, because status queries give a stage-02 record on the caller's backend precedence.
  DEVELOPMENT's label sentence ("CLI executor labels follow that selection") is broader than 0069's round 7 clarification that submit reports the recorded executor directly.
  A test's `patch.dict` cleanup relies on Python 3.8 or later; on 3.6 and 3.7 it leaks a benign PATH change.
- Row 12's exit is NOT met as a whole, as 0069 states; row 15's files and separate-user deployment stay outside this round.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

The full checks ran at head `dcd11a9`, with every protected change this record approves in place, on 23 September 2026:
`python3 tests/run_tests.py` in the three CI suite modes printed `Ran 421 tests` and `OK` in each (skipped 11, 55 and 86; `canary: 0/9` in modes A and B); `python3 tests/check_contracts.py`: `14 contracts clean`; `python3 tests/check_counts.py`: 421, `enforced=3`, clean; the harness `Ran 44 tests`, `OK`; the pre-registration check clean with `graded=1`.
This record changes no code; with it placed and `bash docs/decisions/build_index.sh` re-run, row 11's record checker (`decision_links` in `gars/_system/hooks/pre-commit`) accepts every record and prints `citations: 293/293 resolve`, and the contracts and counts checks stay clean.
The fix round's own acceptance and red-on-fault evidence is in the round 5, 6 and 7 sections of [the change report](../implementation/row_12_change_report.md).

## Status

standing

## Date

2026-09-23
