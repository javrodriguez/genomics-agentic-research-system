---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/_system/workspace.py
  - gars/_system/session_state.sh
  - gars/_system/codex_hook.py
  - gars/_system/stage00_register.py
  - gars/_system/stage01_samplesheet.py
  - gars/_system/stage03_analysis.py
  - gars/_system/wrappers/
  - gars/_system/authoring/create_bioinformatics_skill.py
  - gars/CLAUDE.md
  - gars/_references/contract_standard.md
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_history_model.py
  - gars/tests/test_manifest_groups.py
  - gars/tests/test_render_methods.py
  - tests/run_tests.py
  - .gitignore
symptoms:
  - HISTORY.md or a run record names a model the session was not running
  - "Model: unknown" in every history entry, or agent_model unknown in a run record
  - "note: --model is ignored (decision 0303)" on stderr
  - a model switched mid-session (/model) is not what the history names
---
# The model a record names comes from the harness, never the agent

Item G-model of the step map's fix list (`evals/step-map/FIXES.md`), agreed by the owner. Wording is the lane's (gars-t74), under the owner's standing delegation; the assertion changes, the `none` sentinel and the grading are glitch-b5's named rulings Q1-Q5 of Sat 17 Oct 2026 (`lanes/gars-t74/RULINGS.md`). The approval record for the `_system/` change is glitch-b5's at landing. It refines 0024 (the model is part of provenance): 0024 said what to record; this says where the value comes from.

## Context

Every history writer (stage 00 finalize, stage 01, stage 03 verify, the ten wrapper collects) and the run record a collect completes (`complete_manifest`, `collect_failure`) took the model from the agent's own `--model` flag, and every contract asked the agent for "the exact model id you are running as". The threat model, stated by glitch-b5: honest self-report errors, an agent naming a model it is not running, or a stale one. An agent deliberately under-claiming is outside this item and is named below, never hidden.

**Where the harness reports the model.** From the public Claude Code hooks reference, not from the installed package: reading the installed harness was refused by the building session's classifier and was not tried another way (ruling Q5). Only the SessionStart hook input carries the model, as the optional `model` key; it "can be omitted, for example after `/clear` or when a session is restored through conversation recovery". PreToolUse carries none. Codex's PreToolUse envelope carries `model` (`codex_hook.py`'s docstring); whether its SessionStart envelope does is unconfirmed.

**Reproduction.** At 3f125a34, `gars/tests/test_history_model.py` fails seven tests and errors in eight (`FAILED (failures=7, errors=8)`): each writer passed `--model claude-fake-9` with a session recording `claude-session-3` names the flag (`'claude-fake-9' != 'claude-session-3'`), and the recorder does not exist. At 8fecaefe its `ContractWordingTests` fails for thirteen contracts and `gars/CLAUDE.md`.

## Decision

1. `_system/session_state.sh` (the SessionStart hook of both harnesses) passes its stdin to `workspace.record_session_model`, which writes the input's `model`, or `unknown` when the key is absent, unreadable or off the guard's `MODEL_ID` shape, to the workspace's `.gars_session_model`. It writes `unknown` rather than keeping the file, so a stale model never carries over. Run from a terminal (a person, not a harness) it records nothing. `codex_hook.py`'s session start now passes Codex's input through on stdin, so a `model` Codex carries is recorded the same way.
2. `workspace.history_model(workspace, flag)` is what every writer records: `none` when the flag is `none`, else the session file's value or `unknown`. Every other flag value is ignored with a note on stderr (ruling Q2, option a). `--model` stays declared, default unset, so the pinned registry still validates: no registry change.
3. The writers of stage 00 finalize (the `HISTORY.md` stamp and its result), stage 01, stage 03 verify and the ten wrapper collects use it; each collect passes the same value to the run record it completes or fails. The authoring generator emits the same history line.
4. The contracts and `gars/CLAUDE.md` tell an agent never to pass `--model` (rnaseq-de's typed call drops its `model` key); `_references/contract_standard.md` says the helpers write the harness's model.
5. `unknown` grades a run record not ok, as the honest state; `manifest_check` group 15 does not change (ruling Q3).
6. Assertion changes under ruling Q1, quoted: "In tests/run_tests.py (the history_entry lines 300, 467, 857, 998, 1068, 2598 and the list at 3496) and gars/tests/test_manifest_groups.py::test_model_sentinels_and_known_prefix (lines 546-547), each assertion that the --model value reaches the history or the manifest becomes: the history and the manifest name the model the fixture's session file records, or unknown when there is none, and the flag's value never appears. Every changed test passes a flag value different from the session file's value, so the test tells them apart; every other assertion stays." The five run_tests fixture classes record `claude-session-1` and keep passing `claude-test-1`. Two render tests of `gars/tests/test_render_methods.py` read a real collect and a real verify; their fixtures record `claude-opus-5-5`, the value their unchanged assertions render (a fixture line, no assertion changed).

## What this does not close

- **`none` is still self-reported.** An agent passing `--model none` records a model-mediated step as scripted. G-model does not close that; a later guard item could (ruling Q2).
- **The session file is not guarded.** It is agent-writable until the frozen guard lists it; the one-line hunk is `lanes/gars-t74/guard-gmodel.patch`, applied by glitch-b5 at landing (ruling Q4).
- **One workspace, one file.** Two sessions sharing a workspace overwrite each other's file, and the history then names the later session's model (ruling Q4).
- **A mid-session switch is invisible.** `/model` changes the model without a SessionStart, so the history names the model the session started with; after `/clear` the field may be absent and the record says `unknown`.
- **Codex's SessionStart is unconfirmed.** If it carries no `model`, every Codex entry says `unknown`, which is still the fix; Codex's PreToolUse `model` is not read.
- **Pinned SKILL.md files still show `--model "<model id>"`** (five wrapper skills, and the authoring skill's checklist line). The flag is now ignored with a note, so the line is harmless, but editing a pinned skill means re-pinning it as reviewed, which is glitch-b5's to do; they are left unchanged.

## Test

`gars/tests/test_history_model.py` (15 tests): the recorder (a reported model; a start without the field records `unknown`, not the earlier model; off-shape or unreadable input; the render unchanged; Codex's input passed through; the reader's pattern equal to the guard's); stage 00 finalize, stage 01 (with and without the flag, the stderr note, `none` honoured) and stage 03 verify on the suite's own workspace chain; one wrapper collect (rnaseq-de), its history entry and its completed and failed run records, and `unknown` with no session file; and the contracts' wording.
Mutations: stage 03 verify reading the flag turns its test red (`FAILED (failures=1)`); the rnaseq-de manifest reading the flag turns two red (`FAILED (failures=2)`).

## Status

Standing.

## Date

2026-10-17
