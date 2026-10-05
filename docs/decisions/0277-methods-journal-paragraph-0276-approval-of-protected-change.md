---
date: 2026-10-05
status: standing
kind: decision
touches:
  - gars/_system/claims/render_methods.py
symptoms:
  - the Methods journal paragraph (0276) changes gars/_system/claims/render_methods.py under the protected prefix gars/_system/ with no owner approval record
---
# The Methods journal paragraph 0276: approval of its protected change

Addendum to [0276](0276-methods-journal-paragraph-over-a-provenance-section.md), which stays byte-identical.
The one file this record approves is under a protected prefix (§9.3, R-094), so the change needs an owner-approval record.
Its shape follows [0237](0237-methods-renderer-0236-delegated-approval-of-protected-change.md), the approval of the renderer this change amends.

Two things approve it, and they are kept apart here:

- **The owner's own words, on the wording.** On 5 October 2026 Javier typed "approve methods" in the Row-orchestrator glitch-e7's VS Code window, after seeing the paragraph rendered at the lane's head `19c7490` (with its full suite on the build node: 1303 run, 1221 passed, 0 failures, 0 errors, 82 skipped) and its four deviations from the frames first proposed: the approver is "the approver named in its approval record"; the paragraph does not say "approved before execution"; the paragraph states no dates; tool names are as recorded.
  Those two words approve the paragraph's wording and sentence frames, which 0276 D4 left to him before any public use.
  They reached this record relayed by glitch-e7, the window where he typed them; this record was not written in that window.
- **Glitch, on the code change, under the owner's delegation.** The owner delegated approval of protected changes on 23 September 2026, so the approval of the change to `render_methods.py` as merged is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**.
  No sentence in this record is the owner's except the two quoted words.

**Not given yet: the public push.** Landing this change on public main waits for the owner's own typed push word; nothing here records it.
The renderer itself had his go in 0236 ("defaults", 29 September 2026), and the direction for the paragraph was his "B" of 5 October 2026 (0276).

## Context

0276 was built on the branch `lane/methods-prose` from public main `d6963f7` by a Claude Code producer (Opus 5.5) in its own worktree, and reviewed by fresh Claude Code contexts (Opus 5.5), each in a separate checkout, never shown the producer's transcript.
**Same-model cost.** The producer and the reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The reviews were kept independent by fresh contexts, separate checkouts, a stated threat model and no access to the producer's transcript.
Producer commits, red first: `c04ccb0` (the tests and both goldens for the journal paragraph, red), `189e7fc` (the renderer writes the journal paragraph), `58e6c66` (two workflows recording no agent model stay apart), `adbb1df` (a storage URI is withheld like a local path), `0274ecd` (review r1, and record hashes that would be oracles), `93f2d65` (a deeply nested record refused by the hash rule too), `66e07b8` (review r2), `86cbbf7` (review r3), `19c7490` (review r4).
Reviews, kept outside the repository and cited by their sha256; every actionable finding was reproduced before it was fixed:
`r1` CHANGES (two MAJOR, seven MINOR, nine NOTE), review_sha256 `df69ec0e4f511cbeb87f6ca1b81a1d467807739353dd595ebcd0acd74dbe6523`: F-1 MAJOR, the approval and history sentences read as if the workflows were approved; they now name a separate custom analysis.
`r2` CHANGES (one MAJOR, two MINOR, eight NOTE), review_sha256 `f1f49e5791cd2a89ba0cd8ce83f8781fe4e58016e6fbf475b8862ecd26cfec7d`: F-1 MAJOR, the sha256 of `commands.sh` and of the assay config confirmed a guessed home path offline; neither is printed now.
`r3` CHANGES (one MAJOR, two MINOR, three NOTE), review_sha256 `855d5b7a1854dc546168ce30580550d8a4e45a640a81f4e80893c4097b844ed4`: F-1 MAJOR, a UTC approval date beside a local completion date could read as the analysis completing before its plan was approved; the paragraph now states no date.
`r4` APPROVE WITH CHANGES (no MAJOR: two MINOR, five NOTE), review_sha256 `1f3ddff82c9b850f89616d596e3cbaff30ba45e5e6077ebdcc7971af576a76a3`, so the loop ended at round 4. In `19c7490`: its check-loosening MINOR F-2 (the reference clause's path guards were driven only on a manifest where the clause never appears) was fixed, and its mutants Q11 and Q12 are killed; F-6 (leftovers from removing the dates) was taken. F-1, F-3 and F-5 are 0276's residuals D15 to D17. F-4 is not fixed and is recorded here: two guards hold in the code but no test drives them, a path-like key nested inside a value (mutant Q6) and the stage 03 plan test (mutant Q7, a frame unreachable from `cmd_approve`, 0276 D4); the landing review re-ran both mutants at the merge's tree and both still survive. F-7 is the reviewer's list of checks that held.
The lane's mutation runs on `render_methods.py` named in its commits ended with no survivor, each with the unmutated control green and a byte backup restored and sha-verified (run 2: 53 mutants; run 3: 58, M58 killed after its case was added; run 5: 57).

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected change as merged; its paragraph's wording and frames are the ones the owner approved in his own words above.

1. **`gars/_system/claims/render_methods.py`** (changed): the journal paragraph over a Provenance section that 0276 describes, the storage-URI rule, and the hashes no longer printed; standard library only, no model, no network, no subprocess; it opens only the files named on its command line and is not a typed tool the agent can call.

Outside the protected prefix, recorded for completeness: `gars/tests/test_render_methods.py` (still 16 tests), `gars/tests/fixtures/methods/complete.md` and `sparse.md` (the goldens), 0276, this record, the index, the smoke record and its review stub.
`gars/_system/claims/render_report.py`, its template and its golden are byte-identical, and the suite totals in README.md and DEVELOPMENT.md do not move.
The public push waits for the owner's own typed word.

## Test

Glitch verified the landing merge `1a6e4a772044481396221288e6d83611ec543092` (first parent public main `d6963f7`, second parent the lane head `19c7490`), a true merge that keeps the lane's commits as built.

- The combination: public main had not moved past the lane's base, so the merge has no conflict and its tree is the lane head's tree byte for byte; `docs/decisions/CONTEXT.md` equals `build_index.sh`'s output; `tests/check_counts.py` clean; `.github/` is as at `d6963f7`.
- Full suite at the merge on the build node (Linux), sent as a bundle after a gitleaks scan of the commits the public remote does not yet serve: run `land-methods-1a6e4a7-20261005T172601Z`, verdict derived on the Mac: `PASS kind=gars commit=1a6e4a772044 state=done rc=0 ran=1303 passed=1221 failures=0 errors=0 skipped=82` (the same figures as the lane head's own run; the merge's tree is the lane head's).
- The outgoing range `d6963f7..1a6e4a7` (10 commits: the lane's 9 and the merge): no gitleaks finding under either ruleset, no canary, no private address, path or name (one address-shaped hit is a test's fictitious `abfss://secret@acct…` URI).
- The smoke delta (row 14's ceremony), with the build Mac booked exclusively for it: one run of three `claude-opus-5-5` sessions at the merge's tree (5 Oct 2026, 15:27-15:30 EDT, booking `land-methods-smoke`), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261001-codex-port.json` (the nearest earlier checked first-parent Bench, `f814518`), floor `evals/runs/smoke/smoke-20260926-row-14-activation.json` (`0/1`); an ordinary record; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20261005-methods-prose.json`).
- A fresh-context landing review (Claude Code, Opus 5.5, never shown the producer's transcript; threat model: the landing carries anything beyond the approved lane and its records, or a record states an approval the owner did not give): APPROVE WITH CHANGES, no MAJOR, so the review stopped at round 1; its two MINORs were errors in this record's draft (the lane's first, red commit `c04ccb0` left out; r4's survivors and residuals misstated), both corrected above; its NOTE is on the merge message's wording only. review_sha256 `ac337baa4bf77e2c19f8b28163e3ea0976d2ab9c167fb230b4812af8923d5117`.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing worktree's root at this records commit: `verified 1a6e4a772044481396221288e6d83611ec543092 (Bench previous: evals/runs/smoke/smoke-20261001-codex-port.json)` and `trailers audit: 14/14 _system first-parent commits since activation f3abe50 verified; graded 14 of 14 seen`, exit 0 (run on this commit before its last amendment, which added only this line, and again after it).

## Status

Standing. Approval of the Methods journal paragraph's protected change only; the public push is not approved here.

## Date

2026-10-05
