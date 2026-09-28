---
date: 2026-09-28
status: standing
kind: decision
touches:
  - gars/_system/executorlib.py
symptoms:
  - follow-up 0200 changes how the local job record and the stage-03 launcher are written, under the protected prefix gars/_system/, with no owner approval record
---
# Small-fixes follow-up 0200: approval of its protected change, under the owner's delegation

Addendum to [0200](0200-local-job-record-and-launcher-published-by-rename.md), which stays byte-identical.
The file this record approves is protected (`gars/_system/`; §9.3, R-094), so the change needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
Its shape follows [0196](0196-exit-record-0195-delegated-approval-of-protected-change.md).

## Context

Follow-up 0200 publishes the local job record and the stage-03 launcher by rename.
The lane's coordinator (glitch-31, writing under the owner's standing delegation and not in the owner's words) ruled on 28 Sep 2026 that the lane builds on `0d9954c` (the local main after 0195), that no Codex seat is used, and that the evidence runs once, on the final merge.
It was built on its own branch by a Claude Code producer (Opus 5.5) in an isolated clone (session `975c72c7-a724-4ec8-b4b9-01326bbbffa4`), and reviewed by a fresh Claude Code context (Opus 5.5) from a separate checkout with no remote that never saw the producer's transcript.
**Same-model cost.** The producer and the reviewer are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The review was kept independent by a fresh context, a separate no-remote checkout, a stated threat model, and no access to the producer's transcript.
Producer commits, red-first: `a09b829` (two writer-recovery rows, red at `0d9954c`), `03ea07c` (the fix), `c852e41` (0200 and the build log), `7f82317` (review r1's F-1 and F-2).
It lands jointly with the R-076 follow-up 0205 (approved in 0206), by the coordinator's ruling: one candidate, evidence once. The integration merge `31268e5` joins this branch with 0205's head `50502ca` off the first-parent line; the landing merge `cdd7d99` (first parent `0d9954c`) is the one `gars/_system` commit it adds to main's first-parent line, carries the Review/Bench/Session trailers, moves the suite totals from 1192 to 1208 and adds 0200 and 0205 to the index. The two branches edit `executorlib.py` in disjoint hunks, merged with no hand resolution.
Reviews, kept outside the repository and cited by their kit folders:
`gars-small-fixes/reviews/r1` APPROVE WITH CHANGES on `0d9954c..c852e41` (one MINOR, four NOTE): F-1 MINOR, 0200 placed the R-135 refusal later and attributed it to 0087; reworded. F-2 NOTE, the non-UTF-8 directive byte was not asserted on success; the launcher row now asserts it. F-3 to F-5 NOTE, accepted without change.
`gars-small-fixes/reviews/r2` APPROVE on the fix `c852e41..7f82317` (one NOTE: the new assertion fails the row as "the clean run must succeed" rather than naming the bytes; accepted). The fail-closed reader read CLEAN, so the loop ended.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged.

1. **`gars/_system/executorlib.py`**: `_local_submit` writes its job record through `wl.ws.atomic_open`; the new `_publish_bytes` (sibling `.tmp`, fsync, `os.replace`, temp removed on failure); `_analysis_launcher` writes through it. Every other line is as at `0d9954c`.

Outside the protected prefixes, recorded for completeness: the two rows in `gars/tests/test_r164_writer_recovery.py`, 0200, `docs/implementation/small_fixes_build_log.md`, the index, and the README and DEVELOPMENT counts.

## Residuals of the bundle (glitch-31's rulings, 28 Sep, under the owner's delegation)

- **Study regeneration flags, not built.** `evals/gap-study-2/controls/run_controls.py` and `evals/gap-study-2/fixtures/gen_project.py` still call stage 00 `finalize` without `--data-class` and `--purpose`, so regenerating those projects on current GARS is refused (R-060). Both are frozen with gap-study-2's pre-registration (`prereg.json` pins each by git blob and sha256; `freeze.py` lists them). Regenerating needs a pre-registered follow-up, never an edit to a pinned file.
- **Gap-study status lines, not edited.** The frozen pre-freeze README reads as ungraded; the graded results live in docs/EVALS.md. `evals/gap-study/` and `evals/gap-study-2/` are pinned whole by round 3's `copy_manifest.py` (to `bf065fe`), and a pinned instrument is never amended, a dated note included. The visitor route was checked instead: the top-level README links both studies to `docs/EVALS.md` ("The Gap Study", "The Gap Study, round 2"), and no README or docs index links into `evals/gap-study*` other than `docs/EVALS.md` itself, so nothing was changed.

## Evidence

Measured once, on the landing merge `cdd7d99`, 28 September 2026 (clock times US Eastern, read from `date`):
- **Development Mac, mode A** (Docker answering, row 5's scratch folder and `TMPDIR` set, as CI runs it; the Mac booked 10:49:46-11:52:50): `Ran 1208 tests`, `OK (skipped=14)`; `check_contracts` 14 clean, `check_counts` 1208 clean, `evals/test_harness.py` 44 OK, `evals/check_results.py --controls --lexicon` clean; no file left in the clone. Another lane's own test run shared the Mac during the booking; no timing check went red, and the result stands as measured.
- **Build node, owner account, solo** (a process listing of every account at the start, between the modes and at the end showed only the system's own upgrade watcher): mode B (`TMPDIR` set) `Ran 1208 tests`, `OK (skipped=82)`; mode C (`TMPDIR` unset) `Ran 1208 tests`, `OK (skipped=124)`; contracts, counts, harness (44 OK) and the pre-registration check exit 0.
- **Mutations**, on the build node from a clean copy of the landing merge: this record's five, 5 of 5 killed; 0205's twelve, 12 of 12 killed by the named test.
- **Smoke ceremony** at the landing merge: `smoke-20260928-small-fixes-r076`, one run of three sessions, run-1 3/3, delta 0/1 against the local exit-record landing's record, interpretation "no change", scored ok with 0 findings.
- **Before the evidence**, at the landing merge, one module at a time: both lanes' 21 affected modules OK; `check_counts`, `check_contracts` and `scripts/release_check.py --check` (13/13) exit 0.
- **Sweep** over `0d9954c` to the records commit, the fresh-clone gate and `audit_trailers.py` are read on the records commit and named in its landing report.

## Status

Standing.

## Date

2026-09-28
