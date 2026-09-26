---
date: 2026-09-26
status: standing
kind: decision
touches:
  - gars/_system/project_state.py
  - gars/_system/build_projects_index.sh
  - gars/CLAUDE.md
symptoms:
  - row 13 follow-up 0151 changes the session-start render and the projects index under the protected prefix gars/_system/ with no owner approval record
---
# Row 13 follow-up 0151: approval of its protected changes, under the owner's delegation

Addendum to [0151](0151-row-13-session-state-closed-projects.md), which stays byte-identical.
Every file this record approves is under a protected prefix (§9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0144](0144-row-13-delegated-approval-of-protected-changes.md).

## Context

Follow-up 0151 closes the session-start leak the row 13 runbook review found: the SessionStart hook printed a closed project's sample count, config key names, artifact types and HISTORY headers into the agent's context, and the generated `projects/_index.md` carried its design and stage state.
The lane's coordinator (glitch-09, writing under the owner's standing delegation and not in the owner's words) ruled on 26 Sep 2026 that it lands before the pilot.
It was built on its own branch from public main `1a009a4` by a headless Claude Code producer (Opus 5.5) in an isolated clone, and reviewed by fresh Claude Code contexts (Opus 5.5) from a separate checkout with no remote; producer and reviewer are the same model, a named cost (0013, 0014).
Producer commits, each under the repository's own identity: `7ef73bd` (the build), `352e49f` (the lane gate's exit-line fix), `a2429b1` (review round 1's fixes), `51b0931` (review round 2's fixes).
Reviews, kept outside the repository and cited by their kit folders: `gars-row-13-0151-review-claude-2026-09-26` APPROVE WITH CHANGES (one MAJOR: an unprintable project name made the index fail open; three MINOR; two NOTE); `gars-row-13-0151-rereview2-claude-2026-09-26` APPROVE WITH CHANGES (two MINOR, two NOTE); `gars-row-13-0151-rereview3-claude-2026-09-26`, narrowed to round 3's diff, APPROVE (one NOTE, answered here by naming these folders).

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged.

1. **`gars/_system/project_state.py`**: each project is judged by the guard's own `closed_projects` (0107), imported, never copied, and fail closed; a closed project renders as `## <name> — closed (<class label>)` and one line per stage 02 sub-stage whose state is a value the STATUS writer produces (anything else reads `unrecognized`); a project whose name holds a control character renders as `## (unprintable project name) — closed (unclassified)`; `--project` names and judges its unresolved entry; a new read-only `--closed-list` feeds the index; a public project's render is byte-identical to before (R-042).
2. **`gars/_system/build_projects_index.sh`**: a closed project's row is its name and `closed (<class label>)` with `—` elsewhere; an unprintable name gets one fixed row decided in bash before the list is read; a list that cannot be read makes every row `closed (unclassified)`; a public row is byte-identical to before.
3. **`gars/CLAUDE.md`**: one sentence in "State" saying a closed project shows only its name, class label and sub-stage states.

Outside the protected prefix, recorded for completeness: the new test module `gars/tests/test_session_state_closed.py`, 0151, the index, the change report and the README/DEVELOPMENT counts.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0151 (the rule), the exit-line gate fix, review round 1's F-1 to F-6 (F-5 adopted, fail closed), review round 2's N-1 to N-4, each recorded in 0151's dated addenda.

## What this does not close

- 0151's own list: what a human types or pastes into a session; STATUS values and sub-stage names stay visible by design; a STATUS written by hand is judged by its value only.
- Every residual 0107 names.
- Row 13's exit: no pilot has run.

## Test

Glitch verified the landing merge `cb4242d` (branch head `51b0931` merged onto public main `757c66c`), each evidence run alone on its machine, with a process snapshot at its start and end.

- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge: `Ran 1051 tests`, `OK (skipped=81)` without containers, and `OK (skipped=123)` with `TMPDIR` also unset; contracts and counts clean; the repository status clean after the run. A separate reviewer account's model session ran beside it and was recorded as present; no other suite ran.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the merge's `README.md` with that Linux run's log: `plain run: Ran 1051 tests, OK, skipped 123` and `ok: 123 skips, at most 123 documented`.
- At the merge's tree: `check_counts` 1051 clean; `check_contracts` 14 clean; decision links 424/424; `release_check.py --check` 13/13.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `cb4242d`'s tree, prompt and suite hashes equal to the activation floor's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260926-row-13-doors.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260926-row-13-0151.json`).
- The outgoing range `757c66c..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of follow-up 0151's protected changes only.

## Date

2026-09-26
