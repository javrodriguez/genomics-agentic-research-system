---
date: 2026-09-26
status: standing
kind: decision
touches:
  - .github/workflows/ci.yml
  - docs/decisions/0120-row-14-evaluator-smoke-delta-bench-gate.md
  - docs/decisions/0121-row-14-smoke-delta-preregistration.md
  - docs/decisions/CONTEXT.md
  - evals/smoke/fixtures/
  - gars/_system/hooks/audit_trailers.py
  - gars/_system/hooks/pre-push
symptoms:
  - row 14's hook, audit, CI step, evaluator fixtures and decision records are protected paths with no owner approval record
  - 0120 reserves 0122 for the approval of row 14's protected changes at landing; the owner delegated it on 23 September 2026
---
# 0122 — Row 14: delegated approval of protected changes

Addendum to [0120](0120-row-14-evaluator-smoke-delta-bench-gate.md) and [0121](0121-row-14-smoke-delta-preregistration.md), which stay byte-identical, including their dated addenda.
Every file this record touches is a protected path (R-094, spec §9.3), so it needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by the lane under that delegation and labelled as such; it is not in the owner's words.
Its shape follows row 6's [0099](0099-row-6-delegated-approval-of-protected-changes.md) and row 7's [0079](0079-row-7-delegated-approval-of-protected-additions.md).
The changes arrive with row 14's merge `f3abe50`; this record rides in that merge's one evidence child commit, beside the activation smoke record and the review stub.

## Context

Row 14 (the evaluator planted-lie test and the smoke delta per `_system/` merge) was built on branch `build/gars-row-14-smoke-delta` from public main `452fe33` in two producer commits, `f37cc17` (the build) and `a3216ae` (review round 2's fixes), followed by the lane's records commits `973d5ee` and `0cee6df` (0121).
The producer and both reviewers were headless Claude Code contexts on `claude-opus-5-5`; 0120 states that same-model cost.
The owner's delegation, as quoted in 0099, in the owner's words, verbatim:

> I follow your recommendations. I  delegate every decision to you for the work happening in this session, use your best judgement. I don't want to intervene, we already have plans, specs, etc, just get things done, use your best judgment, you know all the context, i dont, you are capable of taking the paths that best fit our goals. Coordinate with the other sessions if you have to, you can agree the best route together.

Every other sentence in this record is the lane's, under that delegation.
The first independent review (fresh context, on `f37cc17`) was APPROVE WITH CHANGES with one MAJOR (the planted-lie oracle counted a plant whose comparison record failed the schema as caught), closed red-first in `a3216ae`, and six NOTEs, three of which the lane settled by ruling (L1 the floor rule enforced, L2 a named residual, L3 a fault fixture fix).
The final review (round 2, on `a3216ae`) was APPROVE, with 0 BLOCKER, 0 MAJOR and 0 MINOR findings and four NOTEs; its SHA-256 is `e17d1134203aaf00e8e28ed43685438ba336854e06ce921cbaf282d3f4c2526e`, and it is kept outside the repository.
The lane's own verification at `a3216ae`: the whole suite in two modes on a Linux host from a fresh clone (623 tests OK in each), contracts, counts, the evaluation harness and pre-registration checks clean, eighteen fault plants each red then green (the fourteen head item 16 names, the floor-rule guard, the MAJOR's guard, and two of the lane's own), a secret and privacy sweep with no findings, and the audit driven on real history.
The merge's own evidence is listed in the change report's landing section.

## Decision

The lane, under the owner's 23 September 2026 delegation, approves the following protected changes as they stand at `a3216ae` and `0cee6df`, merged as `f3abe50`, on 2026-09-26.
Only the quoted sentences in this record are the owner's words.

1. **The pre-push hook (`gars/_system/hooks/pre-push`).** The activation record moves from 0061 to 0120; the checked unit becomes main's first-parent line; `Bench:` must name a smoke record under `evals/runs/smoke/` that the evaluator accepts; one shared `previous_bench` helper; `TRUSTED_EVALUATOR` pins the SHA-256 of `evals/smoke/smoke.py` and `evals/bench.py` and is checked before anything loads.
   Two departures from head item 8's "nothing else in the hook changes", disclosed in 0120 and accepted by both reviews: `committed_reader` gains a `listing` so the evaluator can detect missing and extra output files, and one row-11 assertion is flipped because `previous_bench` now reaches an activation below `remote..local`.
2. **The audit (`gars/_system/hooks/audit_trailers.py`).** New; it walks main's first-parent line from the activation to the given commit through the hook's own functions, prints graded-against-seen, fails an empty walk, and prints "not applicable" before activation.
   It audits the repository of its working folder, so the ceremony runs it from the repository root, as CI does (0121 names this).
3. **CI (`.github/workflows/ci.yml`).** One added step in the `tests` job, "Bench trailers (R-165, row 14)", after "Pre-registration integrity"; zero lines removed.
4. **The evaluator fixtures (`evals/smoke/fixtures/`).** The producer's synthetic development set: twelve lies, one per finding code other than SCHEMA and UNREADABLE plus the floor rule, and three clean twins, with their generator; labelled synthetic.
5. **The records.** 0120 as written by the producer with its dated addendum, 0121 as written by the lane, and the regenerated index.

## What this does not close

Copied from 0120 and 0121:

- That the outputs came from a model session at all; transcripts are private and hash-bound.
- That a session received exactly the bundle beyond what the pinned driver guarantees, and that a model change is a measurement rather than a claim.
- The smoke tasks' input generator names each defect (Q9), and one smoke task id is readable in the session tree; a smoke score is never a measure of capability.
- Review and Session semantics are row 11's: a label, with no session registry.
- The local hook is not armed in the owner's push path; CI enforces after the push.
- Past records are re-read at the audited commit from an unprotected folder.
- Commits before activation: 0120's gap list, and the landing figure in the change report.
- Public credibility: the planted lie's seal will be `independent_context`; public claims need `external_human_seal` (§21 Q9).
- The row's exit: the sealed planted lie (0123) is still to come.

## Test

`python3 gars/_system/hooks/audit_trailers.py` at the evidence child commit prints `trailers audit: 1/1 _system first-parent commits since activation f3abe50 verified; graded 1 of 1 seen` and exits 0, and CI's step "Bench trailers (R-165, row 14)" prints the same line on the pushed main; the audit at `f3abe50` alone refuses ("later committed evidence snapshot required"), and dropping M's `Bench:` trailer in a scratch copy makes it refuse.

## Status

standing

This record is the lane's approval of row 14's protected changes under the owner's 23 September 2026 delegation; implementation evidence stays in 0120, 0121 and the change report.
Records 0123 (the sealed planted lie and its first run) and 0124 (in reserve) are not written here.

## Date

2026-09-26
