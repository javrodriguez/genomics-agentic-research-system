---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/.claude/settings.json
symptoms:
  - follow-up 0160 changes the guard under the protected prefix gars/_system/, a stage contract and the workspace settings with no owner approval record
---
# Front-door defects follow-up 0160: approval of its protected change, under the owner's delegation

Addendum to [0160](0160-front-door-defects.md), which stays byte-identical.
The three files this record approves are protected (`gars/_system/`, a stage contract and `.claude/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0156](0156-row-7-0155-delegated-approval-of-protected-change.md).

## Context

Follow-up 0160 lets the guard accept the model id Claude Code reports (`claude-opus-5-5[1m]`) without weakening any refusal, runs stage 00's finalize in the foreground, and removes 46 permission rules Claude Code never consults.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 27 Sep 2026, before the build, that any other contract instruction sending a step to the background is the same defect and in scope; the search found none, and a test keeps it so.
It was built on its own branch from public main `1cb2e01` by a Codex producer in an isolated clone (session `01a0e139-c641-7c42-a7e9-2698e072bcd9`, four rounds), and reviewed twice by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
Producer commits, each under the repository's own identity, red-first (the failing tests committed before each fix):
round 1 `90582fd`, `8951c84` (the model-id rule), `d92d4dd`, `d1b8baa` (the foreground contract), `1429df4`, `e864162` (the settings), then three model-id follow-ups the producer found itself: `9a26a60`, `0770fe9` (0141's direct-call check also judged an existing sibling name by the glob branch), `343ca82`, `3e271c2` (an `=` inside the value), `8fa32a6`, `2802c44`, `8d89a50` (model-like text in another argument);
round 2 `86fe216`, `1abd11a`, `6c9f30c`, `958c8ff`, `c367e08` (review r1 and the lane's mutation proof);
round 3 `94abec0`; round 4 `72d58e8` (one test row each, from the lane).
The lane's own commit `3c54093` adds 0160, the index and the suite totals.
Reviews, kept outside the repository and cited by their kit folders:
`gars-front-door/reviews/r1` APPROVE WITH CHANGES on `1cb2e01..8d89a50` (one MAJOR, three MINOR, one NOTE). F-1, MAJOR: the model-id rule's no-slash property had no test; answered in round 2. F-2, MINOR on a refusal path: 0141's check judged a model literal non-recursively, so `--model projects` went from refused to allowed; fixed in round 2 with `_hit(…, True, …)`. F-3: README figures, answered by the lane's commits. F-4: the contract tests accepted a background instruction that also said "not"; answered in round 2. F-5, NOTE: the build's two steps beyond the literal spec are in scope and correct.
`gars-front-door/reviews/r2` APPROVE WITH CHANGES on `8d89a50..72d58e8` (one MINOR, two NOTE; no MAJOR, so the review loop ended). F-1, MINOR: the background-instruction check reads only clauses holding `run`; deferred as 0160's D4. F-2, NOTE: a moved line with no effect, left. F-3, NOTE: a suffix that expands to an existing name is judged as that name, written into 0160.
Before review, the lane's own probe found that the first version checked a value's shape after an `=`, so `~/x=abc` and `p*=x` would have passed where the base refused them; the producer found the same gap independently and fixed it red-first in round 1 (`343ca82`, `3e271c2`).

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected changes as merged.

1. **`gars/_system/guard_hook.py`**: the `MODEL_ID` allow-list and `_model_spellings()`; the `model` key recorded for `--model X` and `--model=X`; a word that is the parsed model value (or `--model=` and it) and matches the allow-list judged literally plus every name its bracket class can expand to, in 0107's final check and in 0141's direct-call check (recursively there, keeping its raw-link and outside-workspace refusals); every other value judged as at `1cb2e01`.
2. **`gars/00_initialize_project/CONTEXT.md`**: step 15's opening says to run finalize in the foreground, never in the background, and why; the rest of the step is byte-identical.
3. **`gars/.claude/settings.json`**: the 46 `Write(...)` deny rules removed; the 46 `Edit(...)` rules, `WebSearch`, `WebFetch`, their order and the hooks block unchanged.

Outside the protected prefixes, recorded for completeness: the eight new tests and the changed assertions in `gars/tests/` named in 0160, 0160 itself, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0160, the coordinator's D4 scope ruling, the round 2 to 4 briefs, and the review dispositions above.

## What this does not close

- 0160's D1 to D5.

## Test

Glitch verified the landing merge `cba758e` (branch head `3c54093` merged onto public main `1cb2e01`), each evidence run alone on its machine, with a process snapshot at its start and end.

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1125 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all `str.removesuffix`, `str.removeprefix` or `ast.unparse`, which are Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change in this landing, 0156 recorded the same red at `8ce8003`, and the build node's Python 3.13.5 ran the harness 44 OK at the merge, so the red is the interpreter's, not this change's. Other sessions' heavy jobs were queued behind this run's machine booking and waiting, not running, at its start; another session's short API test run started about a minute before the suite ended, and the suite still ended green with the mode-A figure.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge: `Ran 1125 tests`, `OK (skipped=81)` without containers, and `OK (skipped=123)` with `TMPDIR` also unset; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean; no other account ran a suite, Codex or Claude at the start, between the runs or at the end.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with that Linux run's log: `plain run: Ran 1125 tests, OK, skipped 123` and `ok: 123 skips, at most 123 documented` (a planted 124 fails it).
- At the merge's tree: `check_counts` 1125 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- A mutation proof at the branch head `72d58e8` on the build node: twelve mutants (the bracket expansion dropped; the allow-list widened to a slash or to any suffix; the `--model` or `--model=` key tracking removed; the shape checked after an `=` only; the exception not bound to the parsed value; 0141's check not judging a model literal, judging it non-recursively, or dropping its outside-workspace refusal; the contract sending finalize to the background; an inert `Write(...)` rule re-added), each killed, with the unchanged control green.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `cba758e`'s tree, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260926-row-7-values.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260927-front-door.json`).
- The outgoing range `1cb2e01..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of follow-up 0160's protected changes only.

## Date

2026-09-27
