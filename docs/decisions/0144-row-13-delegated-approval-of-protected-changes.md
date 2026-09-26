---
date: 2026-09-26
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/tool_call.py
  - gars/_system/tools/closed_output.py
  - gars/_system/tools/registry.json
  - gars/_system/pilot_log.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/tests/test_nonpublic_read_block.py
symptoms:
  - row 13 step B changes the guard hook, its settings, the dispatcher, the registry, a wrapper and a stage contract under the protected prefix gars/ with no owner approval record
  - row 13 opens doors onto closed non-public projects, and each door's allowed output needs an approval that names it
---
# Row 13 step B: approval of its protected changes, under the owner's delegation

Addendum to [0141](0141-row-13-closed-project-doors.md), which stays byte-identical.
Every path this record touches is under a protected prefix (§9.3, R-094), so its change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0108](0108-pg-delegated-approval-of-protected-changes.md).

## Context

Row 13 step B builds the closed-project doors, the pilot-log writer and `bring_home` (0141) on step A's instruments (0140).
It was built on its own branch by a headless Claude Code producer (Opus 5.5) in an isolated clone, and reviewed by fresh Claude Code contexts (Opus 5.5) from a separate checkout with no remote; producer and reviewer are the same model, a named cost (0013, 0014).
Producer commits, each under the repository's own identity: the build `1d4399a`; two lane ruling rounds, `e1fbeff` (D-vii) and `3e8f939` (D-viii); review fix round 2, `08fcdd5`; and fix round 3, `67b3263`, a test-only answer to a merge-interaction red (below).
Reviews: round 1 REJECT (one BLOCKER, two MAJOR, three MINOR, three NOTE); round 2 APPROVE WITH CHANGES (one MINOR, three NOTE), whose MINOR asked the lane's coordinator to confirm the round-2 rulings, which it did (below); round 3, narrowed by the lane's coordinator to fix round 3's diff, APPROVE (one NOTE: the mutation case appends a `local` row with `institutional_allocation`, a pairing row 8B's writer would refuse; the proof holds because the sheet reads the pair either way).
Step A (0140) was reviewed separately and approved at `9220877` (review round 4).
Every review of the lane is kept outside the repository.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged.

1. **`gars/_system/guard_hook.py`**:
   - one changed line, `CLOSED_PROJECT_DOORS`, from `()` to the eleven doors in the table below (the lane's ruling D-i);
   - the direct spelling of any registered helper naming a closed project, or a path outside the workspace while a non-public project exists, refused; the direct spelling of `pilot_log.py` refused in any agent session (0141's D5 additions 1-3);
   - while any closed project exists, a door's direct spelling refused whatever it names (D-vii b); a door admitted only after 0107's session-cwd rule (D-vii a), which replaces 0107's door `if` line;
   - `closed_edit_refusal` (0107's) refuses `Write` as well as the Edit family inside a closed project, body only, every constant byte-identical (review round 1 F-1/F-2, fix round 2);
   - exactly one `READ_ONLY` line, `"projects/*/pilot/*"`, after `"projects/*/00_data/*/files.csv"`.
2. **`gars/.claude/settings.json`**: exactly `Edit(projects/*/pilot/*)` and `Write(projects/*/pilot/*)`, after the `files.csv` pair, nothing removed.
3. **`gars/_system/tool_call.py`** and the new **`gars/_system/tools/closed_output.py`**: the dispatcher refuses a path outside the workspace (`path_outside_workspace`, except inside a source a human declared public in `data_sources.tsv`, ruling D-iv) or outside the closed project a call names (`path_outside_closed_project`) before running; on a closed project it accepts `rnaseq_de.check` and `prepare`'s `design` and `counts` only at their fixed machine-owned paths (`path_not_fixed_layout`); and it passes every door's output through that tool's keep-list.
4. **`gars/_system/tools/registry.json`**: a `closed_output` keep-list on every entry, and five new entries, `rnaseq_de.summary` and `pilot_log.begin`, `end`, `abort`, `check` (producer allow, reviewer refuse; the launch token `--launched-by-dispatcher` in `argv` only).
5. **`gars/_system/pilot_log.py`**: new, the pilot-log writer (0141, D1).
6. **`gars/_system/wrappers/rnaseq-de/rnaseq_de.py`**: the `summary` verb only; **its stage contract** gains the verb and its failure codes.
7. **`gars/tests/test_nonpublic_read_block.py`** (0107's module): the named expectation changes of rulings D-vii (c) and D-viii, each listed in 0141's R-042 list; no assertion removed.

## The doors, and what each may emit (the coordinator's condition)

A door is reached only through the dispatcher, from a session cwd outside every closed project, and only its keep-list's fields leave it; every other value becomes `withheld: non-public project (0141)`, stderr is withheld with its line count kept, and a failure keeps its code, never its detail.

| Door | May emit on a closed project |
|---|---|
| `resolve_artifact` | `ok`; `missing` (artifact types only); `resolved` only where it matches the fixed sub-stage layout |
| `rnaseq_de.check` | `ok`; failure codes; `wrote` (fixed file names) |
| `rnaseq_de.prepare` | `ok`; failure codes; `wrote` (fixed file names) |
| `rnaseq_de.collect` | `ok`; failure codes; `outputs[].type` and `.role` (codes); `template_version`; `model`; never `history_entry` |
| `rnaseq_de.summary` | `ok`, `command`, `assay`, `status`, failure codes, `gate` codes, and the aggregates `genes_tested`, `padj_lt_0.05` up/down, `padj_lt_0.1`, `na_padj`, `samples_in_design` |
| `executor.submit` | `ok`; `job_id`; `state`; `terminal`; refusal codes |
| `executor.status` | `ok`; `job_id`; `state`; `terminal`; refusal codes |
| `pilot_log.begin` | only the writer's fixed line `begin: span <id>; actor human\|agent` or `refused: <code>` |
| `pilot_log.end` | only `end: span <id>; minutes <m>` or `refused: <code>` |
| `pilot_log.abort` | only `abort: span <id>` or `refused: <code>` |
| `pilot_log.check` | only `rows: …; open spans: …; nonce: ok`, `check failed: <codes>` or `refused: <code>` |

Every other registered tool stays refused on a closed project, in both spellings; `executor.cancel` has a keep-list but is not a door.

## The lane's rulings, and the coordinator's confirmation

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: D-i to D-vi (the build's specification), D-vii and D-viii (answers to the build's own ruling requests), and fix round 2's rulings (review round 1's findings).
The lane's coordinator (glitch-09), writing under the owner's standing delegation and not in the owner's words, confirmed on 25 Sep 2026: "the fix-round-2 rulings in 0141's third addendum are the lane's rulings, accepted by me in full. That covers Write refused anywhere inside a closed project via the body of 0107's closed_edit_refusal (constants byte-identical), the fixed-layout rule for rnaseq_de check/prepare on closed projects, and the deferred F-2 remainder (a human or outside process changing the script between prepare and submit, named in D8 with binding the script hash into R-076 as the follow-up)."
It also confirmed D-viii as the lane's (review round 1 F-3).
The owner's words this step rests on are the two lines 0141 quotes (§21 Q4's default; typed calls that return only summaries).

## What this does not close

- 0141's D8 not-covered list and its residual gaps, each NOT met, including: a human or a process outside the agent session changing a closed project's generated script between `prepare` and job start (the script is not bound into the R-076 key; binding it, and a `READ_ONLY` line for the generated `scripts/`, is a named follow-up); a human reclassifying a project public between `prepare` and `submit`.
- Every residual 0107 names.
- Row 13's exit: no pilot has run; human-touch minutes are not measured and no re-run diff is explained.

## Test

Glitch verified the landing merge `09a6e77` (branch head `67b3263` merged onto public main `abab89a`) and its parents' evidence, each evidence run alone on its machine, with a process snapshot at its start and end.

- The build node's owner account (Linux, Python 3.13.5), fresh bundle clones: at step B's round-2 head `08fcdd5`, `Ran 791 tests`, `OK (skipped=80)` without containers and `OK (skipped=107)` with `TMPDIR` also unset; at the merge `bb80170` (the same branch head onto `abab89a`), `Ran 861 tests`, `FAILED (failures=1, skipped=81)` and `FAILED (failures=1, skipped=121)`, the skip figures matching the README's; contracts and counts clean.
- The owner's workstation (macOS, Python 3.8.2) with Docker answering and row 5's scratch folder set as CI sets it, at the merge `f48dfb6` (the same branch head onto `7a2228f`): `Ran 861 tests`, `FAILED (failures=1, skipped=14)`; canary 0/9; no temp-folder or container leak.
- Both failures were the same test, `test_bring_home.test_bench_binding_to_8b_real_header`: it pinned `read_bench` of the committed bench file to `{}`, true while the file was header-only and false once public main committed row 8B's first real row. Fix round 3 (`67b3263`) re-derives the expectation from the file by header name, red first against public main's file; the narrow review round 3 approved it.
- Carry-over to the landing merge, file by file: `git diff f48dfb6 bb80170` is exactly `evals/smoke/SEALS.md`, whose one reader, `tests/test_evaluator_planted_lie.py`, re-run at the landing tree gives `Ran 7 tests`, `OK (skipped=1)` (the sealed set unmeasured, as designed); `git diff bb80170 09a6e77` is exactly `gars/tests/test_bring_home.py`, 0141's fourth addendum and the change report, and that module at the landing tree gives `Ran 9 tests`, `OK`, with its reserved `EXIT` line, both in the CI mode A environment and with no container and `TMPDIR` unset. A Linux re-run of that module was not made (the lane's coordinator ruled it unnecessary: it reads a CSV through the standard library, with no platform branch).
- `evals/test_harness.py` under Python 3.12 at `bb80170`: `Ran 44 tests`, `OK`.
- At the landing tree: `check_counts` 861 clean; `check_contracts` 14 clean; decision links 415/415; `release_check.py --check` 13/13.
- The smoke delta (row 14's ceremony, 0120/0121): one run of three `claude-opus-5-5` sessions at `09a6e77`'s tree, `prompt_sha256` `cf32c619…` and `suite_sha256` `ea2f1cde…`, both equal to the activation floor's; run-1 3/3; `delta` `0/1`, `no change` against the floor `0/1`; `smoke.py score` verdict ok, 0 findings, 2 of 2 records read, 12 tasks regraded, 12 outputs hashed (`evals/runs/smoke/smoke-20260926-row-13-doors.json`).
- The outgoing range `abab89a..09a6e77` has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of row 13 step B's protected changes only.

## Date

2026-09-26
