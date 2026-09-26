---
date: 2026-09-26
status: standing
kind: decision
touches:
  - gars/_references/prompts/review_faults_science.md
  - evals/bio-faults/fixtures/P01/expected.json
  - evals/bio-faults/fixtures/P01/plant.diff
  - evals/bio-faults/fixtures/P02/expected.json
  - evals/bio-faults/fixtures/P02/plant.diff
  - evals/bio-faults/fixtures/C01/expected.json
  - evals/bio-faults/fixtures/C01/plant.diff
  - evals/bio-faults/fixtures/C02/expected.json
  - evals/bio-faults/fixtures/C02/plant.diff
symptoms:
  - row 10 adds a reviewer prompt under gars/_references and fixtures under evals/bio-faults/fixtures with no owner approval record
---
# Row 10: approval of its protected additions, under the owner's delegation

Addendum to [0136](0136-row-10-review-fault-harness-science-half.md), which stays byte-identical.
Every path this record touches is protected (`guard_hook.py` `READ_ONLY`: `_references/**/*` and `repo:evals/*/fixtures/*`), so its addition needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such; no sentence in it is the owner's.
Its shape follows [0073](0073-row-9-delegated-approval-of-protected-additions.md) and [0108](0108-pg-delegated-approval-of-protected-changes.md).

## Context

Row 10 is the science half of the review fault harness (§10, §18 row 10), scoped by [0135](0135-row-10-scope-rulings.md) and built as recorded in 0136.
It was built on its own branch from public main `a779084` plus the 0135 seed commit, through eleven commits under the repository's own identity.
The build rounds 1 to T1 were produced by Codex; rounds V1 and W1 and the merge-preparation commit were produced by headless Claude Opus 5.5 sessions because every Codex route was at its usage limit, as 0136's addenda state with the same-model cost.
Every round was reviewed by a fresh Claude Code context (Opus 5.5) on a separate checkout with no remote; the reviews are kept outside the repository.
The last build review, round W1, read APPROVE; a narrow review of the merge onto main `acb46dc` and of the merge-preparation commit read APPROVE.
A first attempt at round W was stopped when Claude Code's auto-mode permission classifier denied an edit narrowing the prompt's scoping passage ("Instruction Poisoning"); nothing was worked around, and the narrowing was dropped by glitch-09's ruling, as 0136 records.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected additions as merged, on 2026-09-26.

1. **`gars/_references/prompts/review_faults_science.md`**, new: the science reviewer's two-phase prompt (§10, §7.2, §14 and the case layout), including the scoping passage of glitch-09's ruling (c) (the renderer's literal `UNKNOWN (owned by …)` placeholders are outside the science review, a finding on one at most a NOTE), pinned byte for byte by `test_prompt_pinned`. The prompt has not been run on any case; the first measured run is first-run-at-sha.
2. **`evals/bio-faults/fixtures/P01/`** (`expected.json`, `plant.diff`), new: the producer's `batch-confounded-contrast` plant, public and `unsealed`.
3. **`evals/bio-faults/fixtures/P02/`** (`expected.json`, `plant.diff`), new: the producer's `pseudoreplicated-de` plant, public and `unsealed`.
4. **`evals/bio-faults/fixtures/C01/`** and **`C02/`** (`expected.json`, `plant.diff`, each diff empty), new: the producer's clean cases on the rna-a and atac-a bases.

A fresh Codex auditor judged the four producer cases on their built, reviewer-visible form: `audited 4/4 · real-flaw 2/2 · class-match 2/2 · single-flaw 2/2 · detectable 2/2 · clean-no-flaw 2/2`.
No path under `gars/_system/`, `.github/`, `benchmarks/`, `evals/review-faults/` or `docs/ledger.csv` changes in this landing, so the landing rule for `gars/_system/` merges (trailers and the smoke ceremony) does not apply.

## What this does not close

- Everything 0136 names as not covered, and its named residuals (the renderer gap in row 7's `render_report.py`; an absent-value plant uncatchable under the scoping cap, forbidden to the sealer).
- The three sealed plants and the sealed clean case: written later by a fresh Codex sealer against this merged head (0135 R10-3), recorded with the first measured run and its repeat in 0138.
- §17's science clause: NOT met (partial set). The README evidence row stays `unmeasured`.

## Test

The three-mode gate ran once, on the merge-preparation commit `792098d` (the merge of `c1fb9cb` onto `acb46dc` plus that commit), on 26 Sep 2026:
- macOS, true mode A (Docker answering, row 5's scratch set): `Ran 1111 tests in 3151.220s`, `OK (skipped=14)`, canary 0/9; contracts, counts (1111, enforced 3), harness (44) and prereg clean; no system-temp or container leak. Named caveat: another lane's runner test suites ran on the same Mac for about four minutes inside the run.
- Linux, the node owner account, from a fresh bundle clone: mode B `Ran 1111 tests in 636.102s`, `OK (skipped=81)`; mode C `Ran 1111 tests in 619.929s`, `OK (skipped=123)`; the row 10 modules alone took 0.2 s, 19 s and 43 s, within the 120 s budget (the Mac's 197 s for the fault module is load-bound, not the budget's host).
- `.github/workflows/fresh-clone.yml`'s own gate script against the Linux mode C log and the README: `ok: 123 skips, at most 123 documented`.
- Mutation proofs at `c1fb9cb`, each fault planted in a disposable clone and restored from a byte backup: 16 of 18 turned their named test red and back to green; the other two turned other tests red (a redundant adapter check whose launcher-side twin is proven, and a uid rule caught by other tests). A code-half alteration against the re-pinned release-reader test turned it red, and restoring it turned it green.
The sweep over the landing range and the scanned push door carry the secret checks.

## Status

Standing. Approval of protected additions only; the measurement is 0138's.

## Date

2026-09-26
