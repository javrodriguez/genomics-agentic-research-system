---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_system/claims/render_methods.py
symptoms:
  - the Methods renderer (0236) adds gars/_system/claims/render_methods.py under the protected prefix gars/_system/ with no owner approval record
---
# The Methods renderer 0236: approval of its protected addition, under the owner's delegation

Addendum to [0236](0236-methods-paragraph-rendered-from-the-record.md), which stays byte-identical.
The one file this record approves is under a protected prefix (§9.3, R-094), so the addition needs an owner-approval record.
The owner delegated that approval on 23 September 2026, so this record is written by Glitch under that delegation and labelled as such: **approved by Glitch under Javier's 23 Sep delegation**; no sentence in it is the owner's.
The owner's go for the renderer itself is his reply "defaults" of 29 September 2026 to the launch plan (0236 names it; it reached the lane relayed by its coordinator).
Its shape follows [0156](0156-row-7-0155-delegated-approval-of-protected-change.md) and [0211](0211-gap-study-intervals-0210-delegated-approval-of-protected-change.md).

## Context

0236 was built on its own branch from public main `37a8d94` by a Claude Code producer (Opus 5.5) in an isolated clone with no remote, and reviewed by fresh Claude Code contexts (Opus 5.5), each from a separate checkout with no remote that never saw the producer's transcript.
**Same-model cost.** The producer and the reviewers are the same model; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent). The reviews were kept independent by fresh contexts, separate no-remote checkouts, a stated threat model, a brief that pointed the reviewer at blind spots the renderer and its oracle could share, and no access to the producer's transcript.
Producer commits, red first: `1f6cad3` (the tests and fixture inputs, red at `37a8d94`: `FAILED (errors=1)`, the renderer absent), `3d8fb59` (the renderer, its goldens, 0236 and the index), `0792b10` (the suite totals, 1208 to 1224), `f3fb9e6` (two witnesses the mutation run needs), `d760e7d` (wording that never reads "records … not recorded", and an output onto an input refused), then each review's findings red first and fixed: `9470ef9`/`74c0e04` (r1), `ce5be47`/`8e27ba6` (r2), `9be84f8`/`d7ce945` (r3), `6b70b31`/`da915ab` (r4), `b00f8d2` (the delta review's notes), `95e61d6` (a dead branch the mutation run found).
Those are the branch's original commits on `37a8d94`. On 30 Sep 2026 it was rebased onto public main `dbb434d` (head `c427630`; one new commit, 0236's base-commit sentence), and then, for the joint `gars/_system/` landing the coordinator ruled, onto the AWS Batch template follow-up's candidate `719bf5b` (0251/0252); the renderer, its tests and fixtures are byte-identical across both rebases, and only the suite totals and 0236's count sentence moved (1208 to 1224, then 1211 to 1227, then 1229 to 1245).
Reviews, kept outside the repository and cited by their kit folders; every actionable finding was reproduced before it was fixed:
`gars-methods/reviews/r1` APPROVE WITH CHANGES on `37a8d94..d760e7d` (one MAJOR, five MINOR, three NOTE): F-1 MAJOR, a number that overflows a double (`1e400`) printed as `Infinity`; now refused. F-3, the oracle compared lines as an unordered multiset; it now compares the sequence. F-4, paths after `:`, `>`, `|`, `@` were shown; F-5, deep nesting escaped as a traceback; F-6, a four-backtick fence was closed by three; F-8, the page was written mode 0600: all fixed. F-2 (numbers in canonical form), F-7 (`none` suppresses the steps' absence sentence) and F-9 (shared list labels, D10) recorded in 0236.
`gars-methods/reviews/r2` APPROVE WITH CHANGES on `37a8d94..74c0e04` (one MAJOR): on a case-insensitive filesystem `--out APPROVAL.JSON` replaced the approval record; the guard now also compares device and inode.
`gars-methods/reviews/r3` CHANGES on `37a8d94..8e27ba6` (one MAJOR, four MINOR, one NOTE): F-1 MAJOR, `1e-400` underflowed and printed as zero; now refused. F-2, a registry mismatch now also shows the observed hashes; F-3, the contract hash's algorithm is read, not assumed ("git blob" removed); F-4, `https:///x` withheld; F-5, both path rules ASCII-only; F-6 a wording note.
`gars-methods/reviews/r4` APPROVE WITH CHANGES on `37a8d94..d7ce945` (no MAJOR: three MINOR, one NOTE), so the loop ended at round 4: F-1, a home or drive path after a colon, fixed in `da915ab`; F-2 (a subnormal prints rounded) and F-3 (history entries inside HTML comments, D11) recorded in 0236.
`gars-methods/reviews/r5-delta` APPROVE on `d7ce945..da915ab`, the post-review fix alone (four NOTE, taken in `b00f8d2`); the fail-closed reader read CLEAN.
`gars-methods/reviews/r6-rebase` APPROVE, no finding, on the rebase onto `dbb434d` (`37a8d94..95e61d6` against `dbb434d..c427630`): the index rebuilt byte-identical, the counts clean, the renderer's bytes unchanged.
Beside the reviews, a second CommonMark implementation (pandoc 2.12's commonmark and gfm readers) parsed the complete golden and a page of 32 hostile values to exactly the page's layout, text and code inlines only, every value whole in one code span; and 300,000 random strings gave 0 disagreements between the renderer's path rule and the oracle's.
The lane's mutation run on `render_methods.py` at `b00f8d2` (booked alone on this Mac, 01:46-01:50 on 30 Sep): 47 mutants, 46 killed by the named test, the unmutated control green; the survivor M31 deleted a resolved-path check that the `samefile` check had made unreachable, so `95e61d6` removed that dead branch, and M40, which disables the `samefile` check, is killed by `test_refusals_preserve_existing_output` at `95e61d6`. The 46 mutants cover a guessed or `UNKNOWN` absence, path masking off or on everything and each path shape, the plan binding skipped, the actor printed, the approval time read from the expiry, a one-backtick fence, separators or format characters not flattened, each fence rule, the history match loosened, a Sources line dropped or mis-cited, the output touched before validation, a fifth input read, repeated keys, non-finite, overflowing and underflowing numbers, a true zero refused, file-order keys, wrong-type groups rendered, an impossible timestamp, the registry check and observed hashes dropped, the hash algorithm assumed, the citation repeated, a record hashed wrong, the last Model line winning, blank text counted, deep nesting escaping, the page's mode and an output onto an input under another spelling.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected addition as merged.

1. **`gars/_system/claims/render_methods.py`** (new): the Methods renderer 0236 describes; standard library only, no model, no network, no subprocess; it opens only the files named on its command line and is not a typed tool the agent can call.

Outside the protected prefix, recorded for completeness: `gars/tests/test_render_methods.py` (16 tests), `gars/tests/fixtures/methods/` (three manifests, a plan, an approval record, a history and two goldens), 0236, this record, the index, and the count sentences in README.md and DEVELOPMENT.md.
`gars/_system/claims/render_report.py`, its template and its golden are byte-identical.
The public push waits for the owner's own typed word.

## Test

Glitch verified the joint landing merge `95910e28b0e1f6d34342fdead1b2eb1ec26ca80f` (first parent public main `dbb434d`, second parent the joint branch head `c44f435`: the AWS Batch template follow-up's candidate `719bf5b`, 0251/0252, with this renderer's 16 commits rebased onto it), one `gars/_system/` landing for both changes by the coordinator's ruling.

- The combination: only the renderer's totals commit conflicted, in `README.md` and `DEVELOPMENT.md`, resolved to the loader's 1245 (1229 + this change's 16; `tests/check_counts.py` clean), with 0236's count sentence moved to "1229 to 1245"; `docs/decisions/CONTEXT.md` equals `build_index.sh`'s output; neither change's code, tests, fixtures or template differ from its own candidate (`c427630`, `719bf5b`), and `.github/` is as at `dbb434d`.
- Full suite at the merge's tree (macOS, Python 3.13.2, `GARS_TEST_NO_CONTAINER=1`, `TMPDIR` in the landing's own folder, no row 5 scratch folder), in thirteen loader-counted chunks inside the build Mac's heavy-work slots, summing to the loader's 1245: every chunk `OK`, 76 environment skips (own cases `Ran 125` skipped 9; `tests/` `Ran 120` skipped 3, `Ran 25`, `Ran 62`, `Ran 1`, `Ran 64`, `Ran 44` skipped 44, `Ran 82` skipped 1; `gars/tests` `Ran 156` skipped 19, `Ran 86`, `Ran 140`, `Ran 270`, `Ran 70`).
- Full suite at the merge on the build node (Linux), sent as a bundle of the merge after a gitleaks scan of the 41 commits the public remote does not yet serve (no finding): ran 1245, 0 failures, 0 errors, 82 skipped, PASS.
- At the joint branch head: `check_contracts` 14 clean; `check_counts` 1245 clean; `test_decision_links_resolve` OK; `test_release_check` OK and `release_check.py --check` 13/13; `evals/test_harness.py` `Ran 44` OK; `docs/validity/probes.py --check` 28 as stated; `reproduction/gse58638/test_recompute.py` `Ran 72` OK and `--check-published` as stated; `test_render_methods.py` `Ran 16` OK on Python 3.12 and 3.8; `test_executor_templates.py` `Ran 18` OK; ExecutorSeamTests `Ran 22` OK; `test_policy_attacks.py` `Ran 19` OK; the smoke bundle `prompt_sha256` `cf32c619…` and `suite_sha256` `ea2f1cde…`, equal to the previous record's.
- GARS's own Fresh-clone gate script, taken from `.github/workflows/fresh-clone.yml` and run against the merge's `README.md`: `ok: 124 skips, at most 124 documented`; a planted 125 fails it.
- The outgoing range `dbb434d..c44f435` (40 commits): no gitleaks finding under either ruleset, no canary, no private address, path or name.
- The smoke delta (row 14's ceremony), with the build Mac booked exclusively for it: one run of three `claude-opus-5-5` sessions at the merge's tree (30 Sep 2026, 23:54-23:55 EDT), prompt and suite hashes equal to the previous record's; run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20260928-small-fixes-r076.json` (the nearest earlier checked first-parent Bench, `cdd7d99`), floor `evals/runs/smoke/smoke-20260926-row-14-activation.json` (`0/1`); an ordinary record; `smoke.py score` verdict ok, 0 findings, 3 of 3 records read, 15 tasks regraded, 15 outputs hashed (`evals/runs/smoke/smoke-20260930-awsbatch-methods.json`).
- A fresh-context landing review (Claude Code, Opus 5.5, its own checkout with no remote, never shown the producer's transcript; threat model: a conflict resolution that changed either change's behaviour, counts or index drift, trailers or the record not binding the merge): APPROVE, one NOTE (0236's "base commit `dbb434d`" reads as the public main it lands on; on the joint branch the renderer's commits sit on `719bf5b`; wording only), review_sha256 `40a492dd17292499a1f5c6c1be86168a613ea4e5b210e9f8b831e53491ada72b`.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing clone's root at this records commit: `verified 95910e28b0e1f6d34342fdead1b2eb1ec26ca80f (Bench previous: evals/runs/smoke/smoke-20260928-small-fixes-r076.json)` and `trailers audit: 12/12 _system first-parent commits since activation f3abe50 verified; graded 12 of 12 seen`, exit 0 (run on this commit before its last amendment, which added only this line, and again after it).

## Status

Standing. Approval of the Methods renderer's protected addition only.

## Date

2026-09-30
