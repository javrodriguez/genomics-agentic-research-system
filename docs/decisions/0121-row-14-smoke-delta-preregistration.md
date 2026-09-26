---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/smoke/SMOKE.md
  - evals/runs/smoke/
symptoms:
  - row 14's first smoke record (the activation floor) has not been run, and nothing fixes how its sessions are driven before a result exists
  - a smoke session needs a login under a fresh Claude Code config folder, which on this Mac only the owner's token file provides
---
# Row 14's smoke delta: the rules, fixed before the first recorded session

Every sentence in this record is the lane's, under the owner's standing delegation of 23 September 2026; none is the owner's words.

Pre-registration for [0120](0120-row-14-evaluator-smoke-delta-bench-gate.md)'s smoke delta; 0120 stays as written.
This record is committed before any recorded smoke session, and its sha, its SHA-256 and the bundle hash are anchored outside the Mac (aegis `evidence/gars-row-14-prereg-<date>.txt`) before the first session starts, so no choice below can follow a result.
The first record it governs is row 14's own activation floor, at row 14's landing merge.

## Context

0120 built the evaluator, the `Bench:` gate and the ceremony (`evals/smoke/SMOKE.md`).
What 0120 left to the lane is how the three sessions per run are driven, which is owner-side tooling outside this repository.
The Q9 ruling, quoted in 0120, stands: the smoke tasks' input generator names each defect, so smoke sessions can see their answers; the smoke delta stays a valid regression signal because both sides share the leak, but no record may present a smoke score as a measure of capability.

## Decision

1. **Model.** `claude-opus-5-5`, every session, every run (the owner program's review-model pin, aegis decision 0014).
2. **The bundle.** Each session receives exactly `benchmarks/RESPONSE.md`, one task's question and that task's inputs, as `smoke.py bundle` defines them at the merge's own tree.
   The record's `prompt_sha256` is `smoke.py bundle`'s output at M's tree; at the reviewed head `a3216ae` it is `cf32c619d3064aed8a9dbd11df260f0ad8366134b3bdb39bda1eed3f0ff5f202`, with suite `ea2f1cde3342e085b95d7081b1ecbf69b64274b6834eed63d7d4b6a47dfe31b1` (unchanged since round 1). The landing merge's own values are re-derived at M and must match unless main's merge changed a task file, RESPONSE.md or an input, which would itself be recorded.
   The driver delivers the inputs as `inbox/input-<k><suffix>` read-only copies, with one fixed note (where to write `export/response.json`, foreground only) and the fixed continuation line `Continue.`; both are part of the driver bytes pinned below.
3. **The driver.** `drive_smoke.py`, a byte copy of row 2's driver, SHA-256 `d25f82669274a3196118cbe5719655db79d4842992bdbc4e73c26845e313a56b`, wrapped by `smoke_mode.py`, SHA-256 `d1919154f44dbcb4406ea4c3953cd191e78ba87e19ba55d7f949a98f052516fa` (private, owner-side; aegis `ops/gars-smoke/`, commit `ce1277d`).
   The wrapper replaces only the driver's task loader, in memory, with one that validates the three smoke tasks one by one (`bench.validate_task`), so the two nf-core tasks' pins never gate a smoke run.
4. **Run-tree exclusions.** Each session's tree is `git archive <M>` with `evals/`, `benchmarks/`, `docs/`, `.github/`, `tests/`, `scripts/`, `README.md` and `DEVELOPMENT.md` removed before the agent starts, re-initialised as one neutral commit, under a neutral folder name derived from the session id; the session starts in `<tree>/gars` so `gars/.claude/settings.json` loads.
5. **Isolation and login.** A fresh `CLAUDE_CONFIG_DIR` per session, an environment built from a short list of names, `--setting-sources project,local --strict-mcp-config`, an imposed `--session-id`, foreground turns only.
   On macOS the login lives in the Keychain per config folder, so each session authenticates with the owner's subscription token file (`claude setup-token`, one line, mode 600); the wrapper refuses to start without it and neither script prints, logs or copies the value.
   Row 2's B5 cohort uses the same driver and shares this credential dependency.
6. **The activation floor.** Row 14's landing merge M is the activation; its record is a FLOOR record: three runs (`run-1`..`run-3`) × three tasks = nine sessions at M's tree, `--previous none --floor self`.
7. **Ordinary merges.** Every later `_system/` merge runs one run (three sessions) with `--previous` = the Bench path of the nearest earlier checked first-parent commit and `--floor` = the current floor record; a model, prompt or suite change requires a new floor record (0120's floor rule, enforced by the evaluator since round 2).
8. **Naming.** The record is `evals/runs/smoke/<run_id>.json`, not R-112's `<sha>-<model>-<prompt_sha>.json`, because the file cannot name the commit that carries the trailer naming it; `git_sha` binds inside the record (0120).
9. **A session that exports nothing** is retained as an empty `response.json` and grades as failed.
10. **Results publish exactly as graded.** A decrease is the finding, never a reason to re-run; a changed or repeated run is a separate record with the first retained.
11. **The ceremony order** is SMOKE.md's: run id → M with its trailers from a message file → the sessions at M's tree → `smoke.py score` → ONE records child commit touching nothing under `_system/` → `audit_trailers.py` on that child, run from the repository root → push both.

## Residuals (in addition to 0120's)

- **A model change is a claim, not a measurement.** The record's `model` is bound only by the private, hash-bound transcripts; the repository cannot re-derive it.
  So a landing that relabels the model can legitimately re-floor (the evaluator accepts a floor record at a model change, as `clean/C03` shows), turning a decrease into `uncomputable: changed model`, after which later deltas read against the new floor.
  It is visible in the record, and it rests on 0120's residual that the outputs are not bound to a model session (review round 2, NOTE 1).
- **Delivery.** The driver's first-turn text wraps the bundle in fixed driver prose (the inbox note, the continuation line); that prose is pinned by the driver's hash, not by `prompt_sha256`.
- **One smoke task id is readable in the session tree.** The tree keeps `gars/` whole, and `gars/tests/test_hooks_bench_smoke.py` (this row's own test) names `pseudoreplicates` once, with no expected answer (it reads answers from `benchmarks/`, which the tree removes); the driver's leak sweep records it on every session. It is a smaller leak than Q9's, which already names each defect in a delivered input.
- **The audit reads the working folder's repository.** `audit_trailers.py` resolves the repository from the current working folder (`git rev-parse --show-toplevel`), so the ceremony runs it from the landing clone's root; CI runs it from the repository root.

## Test

The first recorded session happens only after this record's commit is anchored in aegis; the anchor's commit time precedes every session record's `driver.start_utc`.
The dummy drive (the driver's own `smoke-echo` task, in neither partition) ran end to end with this driver and wrapper at `a3216ae` on 25 Sep 2026, 21:48:25-21:49:00 (Mac): `{"state": "finished", "stop_reason": "export_complete", "turns": 1}`; session record: model `claude-opus-5-5` recorded in the transcript, permission mode `default`, the SessionStart hook seen, 0 background task calls, the token recorded as `set` only, a fresh config folder inside the scratch root; its echoed `response.json` scored as all three smoke tasks by `smoke.py score` (a floor record of three identical runs, in a throwaway root) gave `0/3` per run (`artifact contract failed` on each, as an echo of the dummy's object must), and `smoke.py check` returned `ok; 0 findings; graded 1 of 1 records seen; 9 tasks regraded; 9 outputs hashed`.

## Status

standing

This record fixes the rules before the first recorded smoke session; it approves nothing by itself, and the protected changes it relies on are approved in 0122.
The first commit of this record (`973d5ee`) omitted this section and the next, which the decision-links check requires of new records; they are appended here, and every earlier byte is unchanged.

## Date

2026-09-25
