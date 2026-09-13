---
date: 2026-09-13
status: standing
kind: defect
touches:
  - gars/_system/guard_hook.py
  - gars/_system/stage03_analysis.py
  - gars/03_custom_analysis/CONTEXT.md
  - tests/run_tests.py
symptoms:
  - guard hook exits 0 on a tool call it cannot parse
  - python3 -c writes into _system/ while echo > _system/ is blocked
  - hand-written "Status: APPROVED" passes stage03 verify
  - PLAN.md edited after approval still verifies
---
# A call the guard cannot judge is refused, and an approval is bound to the plan it approved

Number note: 0041 is taken on the sibling branch `task/aegis-v1-0-1-audit` (the v1.0.1 gap assessment); this record takes 0042 so the numbers never collide when both land.

## Context

The v1.0.1 gap assessment (on `task/aegis-v1-0-1-audit`, `docs/implementation/v1.0.1_gap_assessment.md`, row 4) probed the mechanical scope boundaries of decision 0022 at baseline `fc4749a` and found three live defects:

1. **Fail-open on an unreadable call.** `guard_hook.py` `main()` did `except Exception: sys.exit(0)  # nothing to judge; allow`. A payload that is not JSON, or a crash inside the checks, allowed the call.
2. **Writes the scanner cannot see.** The Bash target scan covers redirections, `tee`, `rm`, `mv`, `cp` and `sed -i`. An inline interpreter (`python3 -c "open('_system/x','w')"`, `perl -e`, `Rscript -e`, `bash -c "echo > _system/x"`), `dd of=`, `ln`, `install`, `touch`, `truncate`, `chmod`, and any command `shlex` cannot parse all passed, while `echo x > _system/x` was blocked.
3. **A forgeable approval.** `stage03_analysis.py verify` accepted any `PLAN.md` carrying a line matching `^Status: APPROVED`. A hand-written line with no `approve` run passed, and so did a plan edited after approval, despite the contract's "Do not edit PLAN.md after approval".

The v1.0.1 guideline's §18 schedules these in row 4.
On 2026-09-13 the owner ruled to pull a minimal fix ahead of rows 1–3, because the tree is public and the defects are live (gap assessment, question D-1).

The guideline names Codex as the implementation producer (R-162).
This fix was produced by Claude Code in Glitch, as decision 0041 was for the assessment, and reviewed by a separate fresh context before merge; that is a deliberate, recorded deviation for this change only.

## Decision

**Decision 0022's stance is unchanged for everything it already covers: a deny is still only an action no contract instructs.** Two shapes are added to that set, because they are exactly the shapes a bypass takes and no contract instructs either:

- **A call the guard cannot read is refused.** A payload that is not a JSON object, a `tool_input` that is not an object, or an exception inside the checks → exit 2 with a message that says the guard could not judge the call. A hook that crashes must not become a hook that allows.
- **A write the scanner cannot see is refused when it names a protected path.**
  - `bash`/`sh`/`zsh`/`dash` `-c <code>`: the code string gets the same Bash checks, recursively. A read of `_system/` inside `bash -c` stays allowed.
  - `python*`/`perl`/`ruby`/`node`/`Rscript`/`R` with inline code (`-c`, `-e`, `-E`, perl/ruby `-i`): refused if any of its arguments names `_system/`, `_references/`, `_templates/`, `.claude/`, or an approval record. No contract runs inline interpreter code (checked with a grep over `gars/`), so no instructed step is lost.
  - `dd of=`, `ln`, `install`, `touch`, `truncate`, `chmod`, `chown` join the target scan.
  - A command `shlex` cannot parse is refused if it names a protected path; otherwise it is allowed as before.

**An approval is a record bound to the plan's bytes.**
- `approve` stamps `Status: APPROVED <date>` as before, **and** writes `PLAN.md.approved` beside it: `{plan_sha256, approved_at, actor, tool, template_version}`, where `plan_sha256` is the sha256 of the stamped `PLAN.md` exactly as written.
- `verify` refuses (exit 2) when the record is missing, unreadable, or its `plan_sha256` differs from the current `PLAN.md`. A `Status: APPROVED` line alone is no longer an approval.
- `approve` on a plan that already carries the stamp but has no matching record refuses instead of reporting `already_approved`.
- The guard denies writing `projects/*/03_custom_analysis/*/PLAN.md.approved` by Write/Edit and by any Bash write target.

**Migration.** An analysis approved before this change and not yet verified has no record, and `verify` will refuse it. The recovery is the contract's own rule for a changed plan: `create` a new analysis and approve it. Completed analyses are unaffected: `verify` already ran for them.

## What this does not close (stated, not implied)

- The agent can still run `stage03_analysis.py approve` itself before the user says yes. The gate remains the contract's prose (step 6). Closing it needs an approval command the agent cannot reach, which is §9.1's typed tool surface (gap assessment D-5), not this fix.
- A write through indirection the hook never sees is not caught: a script file written outside protected paths and then executed, command substitution, or decoded payloads. The full R-098 attack list and R-092 (Bash removed) remain row 4 work.
- Bypass-switch denies (`--no-verify`, `hooks.gitleaks false`) remain with row 15.

## Test

In `tests/run_tests.py`, each red at `fc4749a` and green at this change:

- `GuardHookTests.test_unreadable_call_is_refused`: non-JSON stdin, a JSON array, and a non-object `tool_input` → exit 2.
- `GuardHookTests.test_denies_writes_the_scan_could_not_see`: `python3 -c` / `perl -e` / `Rscript -e` naming `_system/`, `bash -c "echo x > _system/y"`, `dd of=_system/x`, `ln -sf … _system/x`, `touch _references/x`, an unparseable command naming `_system/`, and Write/Bash to `PLAN.md.approved` → exit 2.
- `GuardHookTests.test_allows_after_hardening`: `python3 -c "print(1)"`, inline code reading a project file, `bash -c "python3 _system/stage00_register.py assays"`, and an unparseable command naming no protected path → exit 0.
- `Stage03Tests` (in `WorkspaceFixture`): `test_12c_hand_written_approval_is_refused` and `test_12d_plan_edited_after_approval_is_refused` → `verify` exit 2; `test_12a` still passes end to end with the record written.

## Status

standing

## Date

2026-09-13
