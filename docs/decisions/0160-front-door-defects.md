---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/.claude/settings.json
  - gars/tests/test_nonpublic_read_block.py
  - gars/tests/test_lifecycle_contracts.py
  - gars/tests/test_protected_paths.py
  - gars/tests/test_stage03_execution.py
  - gars/tests/test_data_class_required.py
  - gars/tests/test_pilot_log.py
  - gars/tests/test_lifecycle_faults.py
  - README.md
  - DEVELOPMENT.md
symptoms:
  - stage 00 finalize, run as its contract says with the model id Claude Code reports (claude-opus-5-5[1m]), is refused as an ancestor of a closed project
  - a session that follows stage 00's contract runs finalize in the background, cannot read the result, and runs it again
  - Claude Code warns at launch that the workspace's Write(...) permission rules are never consulted
---
# Front-door defects: a bracketed model id, a background finalize, and inert `Write(...)` rules

Follow-up to [0107](0107-pg-nonpublic-projects-closed-to-reads.md) and [0141](0141-row-13-closed-project-doors.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 27 September 2026; no sentence in this record is the owner's.
0161 is the lane's delegated approval of the protected change; this record does not write it.

## Context

The launch pad's first real take (27 Sep 2026, stages 00 and 01 of a public ATAC-seq project, in Claude Code, at public main `1cb2e01`) met three defects in its first minutes, each visible to any visitor who runs GARS the way its contracts say.

1. **A bracketed model id is read as a shell glob.**
   Stage 00's contract asks for `--model "<model id>"`, exactly as the harness reports it, and Claude Code reports `claude-opus-5-5[1m]`.
   The guard's closed-project rule (0107) judges any word holding a glob character by the folder before its first glob character, recursively, from the session's folder; for `claude-opus-5-5[1m]` that folder is `.`, the workspace root, an ancestor of every project.
   The stage 00 project is closed until finalize writes its dataset row, so finalize was refused every time, as were the 12 other registry tools that take `--model` whenever any other project was not public.
   Reproduced with the guard fed json-built hook payloads: `--model claude-opus-5-5`, `gpt-6-astra`, `claude-sonnet-4-5@20250929` and `us.anthropic.claude-x-v1:0` exit 0; `--model claude-opus-5-5[1m]`, `--model=claude-opus-5-5[1m]` and the dispatcher form exit 2 with "… is an ancestor of project …".
   The script itself was fine: a person running the same finalize writes `Model: claude-opus-5-5[1m]` to `HISTORY.md`.
2. **Stage 00 sent finalize to the background.**
   Step 15 of `gars/00_initialize_project/CONTEXT.md` called finalize "the slow step" and said to run it in the background.
   Claude Code writes a background command's output to a file under the system temp folder, outside the workspace, and the guard refuses a session's read there (R-073), so a session following the contract never saw its own result and ran finalize again.
   The premise was stale: finalize at its default `--integrity quick` took 0.64 s on a synthetic 1,000-sample, 2,000-file cohort.
3. **46 permission rules were inert.**
   `gars/.claude/settings.json` denied every protected path twice, as `Edit(...)` and `Write(...)`.
   Claude Code's permissions documentation says it checks file paths against `Edit(path)` and `Read(path)` rules only, accepts a `Write(path)` rule but never consults it, and warns at startup; and that `Edit` rules apply to every built-in tool that edits files.
   So the 46 `Write(...)` rules protected nothing, and the launch warning was the visitor's first sight of the workspace.
   The enforcement for all four write tools is the guard's own `check_write_tool()`, which the settings never replaced.

## Decision

**Ruling 0160 (the lane's).**

1. **A model id is a value, not a pattern** (`gars/_system/guard_hook.py`).
   One allow-list, `MODEL_ID`: letters, digits and `. _ : @ -`, no slash, with at most one trailing context suffix of 1 to 4 digits and one lower-case letter in brackets (`[1m]`).
   The guard now records the key `model` for `--model X` and `--model=X` as it did for `--project`, and the dispatcher already carried it.
   A word gets the new judgment only when it is the parsed `model` value itself (or `--model=` and that value) and the whole value matches `MODEL_ID`; it is then judged literally, plus every name its bracket class can expand to (`claude-opus-5-5[1m]` → `claude-opus-5-51`, `claude-opus-5-5m`), each by the non-recursive closed-project check, in both 0107's final check and 0141's direct-call check, which keeps its raw-link and outside-workspace refusals.
   That is exactly what a shell could make of the word, so nothing the guard refused for a reason is now allowed.
   Any other value (a slash, `*`, `?`, braces, a second bracket, `~`, an `=` inside the value) keeps the judgment it had at `1cb2e01`.
   0141's direct-call check keeps judging a model literal recursively, as `closed()` does, so a value that names an ancestor of a closed project stays refused there.
   A suffix can expand to an existing name (`project[1s]` at the workspace root names `projects`); the value is then judged exactly as that name typed out, which is the equivalence the rule intends (review r2 F-3).
   The registry is unchanged; the rejected alternative, a `pattern` on the 13 registry `model` schemas, would have moved path-shaped refusals from 0107 to R-092 and churned 13 entries and their expectations.
2. **Finalize runs in the foreground** (`gars/00_initialize_project/CONTEXT.md`, step 15's opening only).
   The step now says to run finalize as an ordinary foreground call with the longest timeout the harness allows, never in the background, because a background task's output file lies outside the workspace where the guard does not let a session read, and that a timeout-killed finalize is deterministic and re-run once in the foreground.
   The rejected alternative, letting a session read the harness's task-output folder, would have widened R-073 to an undocumented, harness-owned folder shared by every background command.
   The coordinator ruled before the build that the same class of defect anywhere else is in scope: every agent-facing contract (`gars/**/CONTEXT.md` outside `projects/`, and every wrapper `SKILL.md`) was searched at `1cb2e01` for `in the background`, `run_in_background`, `nohup`, `detach`, `disown` and a trailing `&`, and stage 00 step 15 was the only instruction; the other hits were the local executor's own detachment (read back through its tool) and a "detached commit" in git prose. A test now keeps every contract that way.
3. **The inert rules are gone** (`gars/.claude/settings.json`).
   The 46 `Write(...)` entries are removed; the 46 `Edit(...)` entries, `WebSearch`, `WebFetch`, their order and the hooks block are unchanged.
   This supersedes, going forward, the `Edit`/`Write` pair convention recorded in 0107, 0108, 0141 and 0144, whose text stays as written.
   Protection does not move: the guard refuses every protected path for `Write`, `Edit`, `MultiEdit` and `NotebookEdit` independent of the settings, and a new test proves it for every protected pattern and all four tools.

Tests move with the change: `test_nonpublic_read_block.py` gains four (the bracketed id allowed in every spelling on every registry tool that takes a model wherever the call without it is allowed; path-, slash-, glob-, tilde-, ancestor- and `=`-shaped values still refused; a name a bracket class can expand to, or the literal itself, refused when it reaches a closed project, a closed project's raw-link target, or a folder outside the workspace); `test_lifecycle_contracts.py` gains three (step 15 says `never in the background`; no contract sends a step to the background; the phrase check refuses planted instructions that also say "not"); `test_protected_paths.py` gains one (every protected pattern × all four write tools) and its settings test now requires `Edit(...)` rules only and no `Write(`, `MultiEdit(` or `NotebookEdit(` rule; three tests that asserted `Write(...)` pairs now assert `Edit(...)`, each keeping its guard assertion; the lifecycle fault table loses the three rows that deleted a `Write(...)` line that no longer exists.
The suite total moves from 1117 to 1125.

## What this does not close

- **D1** A model id with a slash (a provider-prefixed `vendor/model`) is still judged as a path. Revisit only if a real harness reports one.
- **D2** The `Edit(../…)` deny entries lie outside their anchor per Claude Code's documentation and are probably inert, silently (no warning); the guard's `repo:` patterns enforce those paths. Correcting them needs the anchor semantics checked in a live session.
- **D3** R-073's refusal text says "human approval store" for any read outside the workspace, which misleads when the path is a harness task-output file; wording only.
- **D4** (review r2 F-1, MINOR, deferred by the lane's stop rule) The background-instruction check reads only clauses holding the word `run`, so wording such as "start finalize in the background" or "launch it as a background task" would pass it. No contract holds such wording today (the only `background` in any contract is step 15's negated sentence); a fail-closed allow-list of the negated sentences would close it.
- **D5** The dispatcher spelling of a model value that names an ancestor of a closed project (`projects/.`, `projects`) is allowed, as it was at `1cb2e01`, because 0141's dispatcher filters the door's output; only the direct spellings are refused and tested. Pre-existing, not changed here.

## Test

The acceptance is `test_nonpublic_read_block.py` (the model tests), `test_lifecycle_contracts.py`, `test_protected_paths.py` and `test_lifecycle_faults.py`.
They must fail when the bracket expansion check is dropped, when the suffix allow-list widens, when the `--model` or `--model=` key tracking is removed, when the value's shape is checked after an `=` only, when the exception is not bound to the parsed model value, when 0141's outside-workspace refusal is dropped for a model literal, when an inert `Write(...)` rule returns, when 0141's check stops judging a model literal, or judges it non-recursively, when the contract sends finalize to the background again.
The lane's mutation proof at the branch head killed 12 of 12 such mutants with the unchanged control green; the reviewers' own mutation runs agreed.
The landing's evidence is recorded in 0161.

## Status

Standing. The change record for the front-door defects follow-up; its protected-change approval is 0161.

## Date

2026-09-27
