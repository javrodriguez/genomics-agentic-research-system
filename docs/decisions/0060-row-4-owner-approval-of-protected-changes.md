---
date: 2026-09-22
status: standing
kind: decision
touches:
  - gars/03_custom_analysis/CONTEXT.md
  - gars/_system/authoring/SKILL.md
  - gars/_system/wrappers/nfcore-atacseq-wrapper/SKILL.md
  - gars/_system/wrappers/nfcore-scrnaseq-wrapper/SKILL.md
  - gars/_system/wrappers/nfcore-spatialvi-wrapper/SKILL.md
  - gars/_system/wrappers/scrna-qc-cluster/SKILL.md
  - gars/_system/wrappers/spatial-cluster-count/SKILL.md
  - gars/_references/tool_pins.json
  - gars/tests/test_policy_pins.py
symptoms:
  - the stage 03 contract tells the agent to run approve, which the guard refuses
  - every governed session refuses at start because pinned skills are unreviewed
  - a wrapper skill tells the agent to run sbatch around executor.submit
---
# Row 4: the owner's approval of three protected changes

Addendum to [0058](0058-row-4-typed-surface-and-attack-list.md) and [0059](0059-row-4-provisional-rulings.md), which stay byte-identical.
Every file this record touches is a protected path (R-094, spec §9.3), so each change is the owner's own commit with this record as its approval record.

## Context

The owner confirmed on 22 September 2026 all eight rulings that were applied provisionally overnight: rows 15 and 4's rulings 1A to 8A, including 0059's five for this row.
Row 4's third review (Claude Code, APPROVE WITH CHANGES) left two MINOR findings that only the owner could close.
The first was that `gars/03_custom_analysis/CONTEXT.md` still defined approval as a `Status: APPROVED` line plus a workspace `PLAN.md.approved`, and told the agent to run `approve`, which the guard now refuses for an agent session.
The second was that `session_state.sh` refuses every governed session while any pinned skill is not `reviewed`, and all eleven were `unreviewed`.

## Decision

The owner ruled 2A and 3A, then 4A, on 22 September 2026.

1. **The stage 03 contract follows the approval store (2A).** The agent never runs `approve`; T2 hands the user the exact command to run in their own terminal, outside the session.
   The Approved paragraph names the `.gars-approvals/` store beside the workspace, the record `{actor, timestamp, plan_sha256, expiry, plan_path}`, and the 24-hour lifetime.
   Steps 6, 7 and 9 name the refusals the store produces (no record, a changed plan, an expired record).
   Nothing else in the contract changed.
2. **The session-wide refusal stays, and the pins are reviewed (3A).** R-099's check keeps refusing the whole session on any unreviewed, rejected or altered pin.
   The eleven skills were reviewed in three fresh contexts with no access to the producer, the build folder or the owner's memory, each reading only a kit of the skill copies, `registry.json` and 0058.
   Round 1 reviewed five and rejected six.
   Round 2 reviewed all eleven after the fixes below, and listed seven command lines whose spelling the guard would refuse.
   Round 3 reviewed all eleven on their final bytes, with zero command lines refused once placeholders are filled.
3. **Six skills were corrected to earn review (4A).** In five wrapper skills the raw `sbatch <substage>/submit.sh` is now the registered `executor.submit` call, and every helper call uses its full registered path.
   A trailing comment on the submit line and two backslash continuations were removed, because the guard refuses both spellings.
   The `scrna-qc-cluster` skill's environment note now says the owner rebuilds the environment by hand, outside any agent session, and that an agent never installs anything.
   The authoring skill stays at `_system/authoring/` as decision 0040 placed it, and it now opens with a scope statement: it is a human procedure, and the guard refuses its writes and unregistered commands in an agent session.
4. `gars/_references/tool_pins.json` records the eleven final digests with `review_status: reviewed`; each digest was re-derived from the live file and matched against the round 3 review before it was written.

## What this does not close

- The two reviewed skills whose `prepare` step writes `submit.sh` (`scrna-qc-cluster`, `spatial-cluster-count`) no longer say so beside the submit call; round 3 recommends adding it and judged it not blocking; adding it changes their digests and needs a fresh review.
- Whether `<substage>/submit.sh` resolves relative to `--workspace` is not shown by the skills themselves; the contracts carry the resolved path.
- The injection fixture's 20/20 and the reviewer as a separate OS user (R-093) remain NOT met, as 0058 and 0059 state.
- A review in a fresh context on the same machine and OS user is `independent_context`, not `external_human_seal`.

## Test

- `python3 tests/run_tests.py`: `Ran 306 tests`, `OK (skipped=50)`, printing `forgeable approvals: 0/1` and `bypasses: 0/5`, with every change of this record in place; `python3 tests/check_counts.py` is clean after README and DEVELOPMENT were brought to 306.
- `python3 tests/check_contracts.py`: `14 contracts clean`.
- `python3 gars/_system/tools/pins.py`: `R-099: workspace pins reviewed and intact`, exit 0; `session_state.sh` exits 0.
- `gars/tests/test_policy_pins.py`: `test_session_start_refuses_unreviewed` asserted a refusal on the shipped workspace, which held only while the shipped pins were unreviewed; it now proves the refusal, and the reviewed positive control, on a disposable workspace running the shipped `session_state.sh` and `pins.py` unchanged, and `test_shipped_pins_are_reviewed_and_intact` asserts the shipped pins pass.
  Mutation: with `|| exit 2` in `session_state.sh` changed to `|| true`, the test fails; restored byte-identical.
- Every command line in the five wrapper skills, with placeholders filled, was sent to `guard_hook.py` as a Bash tool call: each parses as one registered call; a raw `sbatch` and the old trailing-comment and continuation spellings are refused (exit 2).
- The three skill reviews are kept outside the repository; their sha256 digests are `caef60ab179d023ce6cbbd4ee3793928ec1b8bd5a1261f7f0bbc8c58327fd939` (round 1), `4488b3414e8d975a81157084dc45d175be7f952e22b4334539028d545aa9ca4f` (round 2) and `ad8ade8d24d9b3e2f3f18a51ebf718c33db9df045d964de853c4f27507657a90` (round 3).

## Status

standing

## Date

2026-09-22

_Renumbered at merge, 2026-09-22: this record was written as 0056 on its branch and takes 0060 on main, because the row-5 fix and rows 15, 4, 11 and 12 numbered their decisions independently (merge order: row-5 fix, 15, 4, 11, 12). Its number, link targets and the numbers of other rows' records it cites are the only edits; branch-time number notes are left as written._
