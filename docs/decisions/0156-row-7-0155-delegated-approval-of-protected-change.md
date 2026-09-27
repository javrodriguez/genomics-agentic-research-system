---
date: 2026-09-26
status: standing
kind: decision
touches:
  - gars/_system/claims/render_report.py
symptoms:
  - row 7 follow-up 0155 changes the report renderer under the protected prefix gars/_system/ with no owner approval record
---
# Row 7 follow-up 0155: approval of its protected change, under the owner's delegation

Addendum to [0155](0155-row-7-report-shows-manifest-values.md), which stays byte-identical.
The one file this record approves is under a protected prefix (§9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0152](0152-row-13-0151-delegated-approval-of-protected-changes.md).

## Context

Follow-up 0155 makes the report show the values the manifest already supplies for four sections that were fixed `UNKNOWN (owned by …)` placeholders: data and classification, the reference and model steps in methods, the `commands.sh` reproduce line, and cost.
The lane's coordinator (glitch-a1, writing under the owner's standing delegation and not in the owner's words) ruled on 26 Sep 2026 that it lands on its own gates, without waiting for row 10's measured runs, which ship from row 10's own frozen clone at `9896512`.
It was built on its own branch from public main `9896512` by a Codex producer in an isolated clone (session `01a0e09a-2cf6-7111-a833-caee6a4eda71`, two rounds), and reviewed by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
Producer commits, each under the repository's own identity: `435e8f0` (the renderer, its tests and the regenerated golden), `e2b6cbe` (row 10's pipeline tests), `9d7fdaf` (the suite totals), `8e96c8e` (round 2: the lane's four corrections before review: the reproduce path out of a code span, the two methods paragraphs, the DEVELOPMENT total's clause, and the one `FAULTS` entry naming the renamed row 10 test). The lane's own commit `31c17f8` adds 0155 and the index.
Review, kept outside the repository and cited by its kit folder: `gars-row7-values/reviews/r1` APPROVE WITH CHANGES (two MINOR, two NOTE) on `8e96c8e`. F-1 (a present but non-string `cost` or non-list `model_steps` renders the absence sentence) is deferred by the lane's stop rule as 0155's D4, since only a manifest outside the schema reaches it; F-2 (0155 cited before it existed) is answered by `31c17f8`; F-3 (README's "these 1111 tests") is answered by this landing's skip sentence; F-4 (an empty object counts as empty) is named in 0155. No MAJOR was found, so the review loop ended at round 1.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`gars/_system/claims/render_report.py`**: `render()` reads `data_class`, `venue`, `purpose` and `agreement_ref`; `reference` (build, annotation release, FASTA and GTF hashes, and the registry comparison when it is not `matched`); `agent_model` and `model_steps`; the `command` path and sha256 (never opened); and the manifest's `cost` string and scheduler `resources`. A missing value renders the constant ``not recorded (the manifest has no `<key>`)``; every supplied value passes through the unchanged `display()`; `unknown()` and `display()` are byte-identical to `9896512`.

Outside the protected prefix, recorded for completeness: `gars/tests/test_render_report.py` (six new tests), the regenerated golden `gars/tests/fixtures/claims/report.md`, row 10's `tests/test_bio_faults_pipeline.py` and the one string in `tests/test_bio_faults_faults.py`, 0155, the index, and the README and DEVELOPMENT counts and skip figures.

## The lane's rulings

All are the lane's, under the owner's standing delegation of 23 Sep 2026; none is the owner's: ruling 0155, the four round-2 corrections, and the review r1 dispositions above.

## What this does not close

- 0155's D1 to D4.
- Row 10's measured runs and its instrument text, which this landing does not touch.

## Test

Glitch verified the landing merge `8ce8003` (branch head `31c17f8` merged onto public main `9896512`), each evidence run alone on its machine, with a process snapshot at its start and end.

- This Mac (macOS, Python 3.8.2), a fresh clone of the merge, with Docker answering and row 5's scratch folder and `TMPDIR` set as CI sets them: `Ran 1117 tests`, `OK (skipped=14)`, README's mode-A figure; contracts, counts and the pre-registration check clean; the repository status clean after the run. Its `evals/test_harness.py` step ended with 13 errors, all `str.removesuffix`, `str.removeprefix` or `ast.unparse`, which are Python 3.9 APIs this Mac's Python 3.8.2 lacks; `evals/` has no change in this landing and those calls are present at `9896512`, and the build node's Python 3.13.5 ran the harness 44 OK at the merge, so the red is the interpreter's, not this change's. Another session's heavy jobs were queued behind this run's machine booking and waiting, not running, at its start and its end.
- The build node's owner account (Linux, Python 3.13.5), fresh bundle clone of the merge: `Ran 1117 tests`, `OK (skipped=81)` without containers, and `OK (skipped=123)` with `TMPDIR` also unset; contracts and counts clean; the evaluation harness 44 OK and the pre-registration check clean; no other account ran a suite, Codex or Claude at the start or the end.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the records commit's `README.md` with that Linux run's log: `plain run: Ran 1117 tests, OK, skipped 123` and `ok: 123 skips, at most 123 documented` (a planted 124 fails it).
- At the merge's tree: `check_counts` 1117 clean; `check_contracts` 14 clean; `test_decision_links_resolve` OK; `release_check.py --check` 13/13.
- A mutation proof at the branch head `8e96c8e` on the build node: nine mutants of `render_report.py` (each section not reading the manifest, a value passed without `display()`, an empty value shown as `UNKNOWN`, the methods paragraphs joined, the registry check dropped), each killed by `test_render_report.py`, with the unchanged control green.
- The smoke delta (row 14's ceremony): one run of three `claude-opus-5-5` sessions at `8ce8003`'s tree, prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260926-row-13-0151.json`, floor `evals/runs/smoke/smoke-20260926-row-14-activation.json`; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260926-row-7-values.json`).
- The outgoing range `9896512..` the records commit has no gitleaks finding under either ruleset, no canary and no private address or path.

## Status

Standing. Approval of follow-up 0155's protected change only.

## Date

2026-09-26
