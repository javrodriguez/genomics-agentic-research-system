---
date: 2026-10-17
status: standing
kind: decision
touches:
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/CONTEXT.md
  - gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md
  - gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md
  - gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md
  - gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/test_closed_project_contracts.py
  - gars/tests/test_mutation_runner.py
  - gars/tests/test_temp_hygiene.py
  - tests/test_bio_faults_pipeline.py
symptoms:
  - Landing A of lane gars-ms21 (0190, 0291 and the T73 test helper fix) has no landing approval record
---
# Lane gars-ms21 Landing A: approval of its landing

Approval of the landing of [0291](0291-stage-01-03-contracts-name-a-door-or-the-user-on-a-non-public-project.md) and [0190](0190-mutation-runner-tests-keep-their-logs-in-their-own-scratch.md), which stay as the lane wrote them, and of the T73 test helper fix, which has no record of its own (a DEVELOPMENT.md log row).
Landing A touches no protected path (§9.3, R-094: nothing under `_system/`, `_references/`, `_templates/`, `.claude/` or `.codex/`), so this is the landing's approval record, not the approval of a protected change.
Its shape follows [0282](0282-reproduction-package-0281-delegated-approval-of-protected-additions.md) and [0277](0277-methods-journal-paragraph-0276-approval-of-protected-change.md).

Two things approve it, and they are kept apart here:

- **The coordinating session, on the lane as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings are glitch-b5's, the lane's coordinating session: **approved by glitch-b5 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: PENDING

## Context

Lane `gars-ms21` (tasks G1 T49, G2 T73 and G3 T44a for this landing) was built red first on its own branch from public main `a97fa9cd`, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The landed commits, red first, re-created onto `a97fa9cd` from the lane's commits, each with its tree change, message, author, committer and dates kept, and named here by its re-created id (the lane's own working files under `lanes/` do not land):

- T49 (0190): red `830a9276`, fix `71af6760`; the mutation runner's tests keep their suite logs in a scratch of their own, so a module run leaves no `gars-*` folder in TMPDIR, and under CI with TMPDIR unset nothing is patched.
- T73: red `a333316f`, fix `2f346f94`; the science launch tests' temp helper returns only a neutral root, and fails naming TMPDIR when the base itself is flagged.
- T44a (0291): red `adca4ce3`, fix `574cc599`; round 2 red `f51525da`, fix `b0f9fea1`; red `aee26e60`, fix `9c00c19a`; wording `58c2af41`; record `849b91c4`.

Reviews, of commit ranges on the lane's own branch, kept outside the repository and cited by the sha256 of the owner's held review file:

- round 1, `a97fa9cd..d699112`: CHANGES (one MAJOR: stage 02 step 3a stopped every non-public run, and T10 and the sub-stage templates promised routing that could not happen), review_sha256 `7fa30f22390be064279514dead0125cbc20f2264142666b6367d0b9c6c4bfb62`; folded in round 2 as glitch-b5 ruled.
- round 2, `743120c1..0e777e74`: PASS (no finding at MINOR or above), review_sha256 `58c80f0b1f0d61cb914f4dac8558610486df96a1830756514096acbbd670ba6a`, so the loop ended at round 2. It ran the named modules and the four gates, re-drove both red claims at their commits, applied mutants of its own (each red), and walked stage 02 on a non-public project against the real guard.

## Decision

glitch-b5, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves landing on public main, as re-created at the build-branch commits named above:

1. **0291** (contract prose in the 13 stage 01-03 contracts, and `gars/tests/test_closed_project_contracts.py`): every in-project read step on a non-public project names its door's dispatcher spelling or the user's message, and stage 02 step 3a asks the user (T11) instead of stopping every run.
2. **0190** (`gars/tests/test_mutation_runner.py`, `gars/tests/test_temp_hygiene.py`): `evals/mutate.py` is untouched.
3. **T73** (`tests/test_bio_faults_pipeline.py`, one DEVELOPMENT.md log row).

The suite totals in README.md and DEVELOPMENT.md move with the lane (1403 to 1415, both landings together); the skip figures do not move.

## Test

- Full suite at the lane head `2d819179` (whose tree equals the landing's outside `lanes/` and the landing's records) on a separate test machine (Linux): run `gars-ms21-land-ac-2d819179-2d81917-20261017T041958Z`, `PASS kind=gars commit=2d819179add8 state=done rc=0 ran=1415 passed=1333 failures=0 errors=0 skipped=82`.
- The landing's own checks, on 17 October 2026, for Landings A and C together (one merge carries both, and [0296](0296-ms21-landing-c-0295-approval-of-protected-change.md) points here), recorded in the landing's evidence commit, the merge's child:

Glitch verified the landing merge `e62fa864997d939b79dd3779c7b10c30bcd4fef1` (first parent public main `a97fa9cd`, second parent the build branch's head `a48154db`), a true merge.
The build branch is the lane's 22 commits outside `lanes/`, re-created in lane order with the same patches, authors, committers, dates and messages, and then the records commit.

- The merge's tree equals the lane head's outside `lanes/` and `docs/decisions` (`git diff 2d819179 e62fa864 -- . ':!lanes' ':!docs/decisions'` is empty), and `docs/decisions` adds only 0292, 0296 and their two index lines; at the merge, `tests/check_counts.py` is clean, `tests/check_contracts.py` has 14 contracts clean, `test_decision_links_resolve` passes (579 of 579 links resolve) and `build_refusal_corpus --check` passes.
- The full suite ran at the lane head, not at the merge (the first landing review's NIT 6): the two trees differ only by `lanes/` and these records, whose readers pass at the merge, and public CI runs the whole suite on main's new tip after the push.
- The README's skip bar: fresh-clone.yml's own gate script, run on the test machine's log against the merge's README, prints `ok: 82 skips, at most 124 documented` and exits 0; 82 is the figure with TMPDIR set, and no Linux figure with TMPDIR unset was measured for this landing.
- The outgoing range `a97fa9cd..e62fa864` (24 commits: the build branch's 23 and the merge): no gitleaks finding under either ruleset (gitleaks 8.30.0, its default rules and the build machine's push rules, 23 non-merge commits); no home path, user name, private e-mail address or internal machine or project name appears in any added line (1295 read) or message; the identities are `Claude <noreply@anthropic.com>` (22) and the owner's GitHub noreply address (2).
- The smoke delta (row 14's ceremony), with the build Mac booked exclusively for it (a timed booking from 20:48:42 to 21:04:07 EDT, in the machine scheduler's log): one run of three `claude-opus-5-5` sessions at the merge's tree (17 October 2026, 20:48-20:50 EDT), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261007-repro-package.json`, floor `0/1` from `evals/runs/smoke/smoke-20260926-row-14-activation.json`; the evaluator found nothing (15 outputs hashed, 15 tasks regraded).
  Two earlier attempts that morning ran no model turn and were not scored: the driver refused the first, planned at 09:21 EDT against the second merge `51d8be7e` under the run id `smoke-20261017-ms21-landing-ac`, before any session started (its source checkout was in the wrong place), and the second, under this run id at 09:44 EDT, failed on a revoked login.
- Fresh-context reviews of the landing (Claude Code, Opus 5.5, one reviewer in its own clone with no remote, never shown the producer's transcript; threat model: the landing carries more than the approved lane, a cited fact is false, a private value leaks, or the merge has the wrong shape), each review_sha256 a hash of the owner's held evidence:
  - round 1, on the landing's first merge `179522a5`: PASS (no MAJOR, 3 MINOR, 3 NIT), review_sha256 `d3df06036cff42f5cc55c5dc186ab88d43d2bf0f928dd41e6d0283880f2c1e07`; the three MINORs and NIT 4 folded in the records commit;
  - round 2, a one-round check of that fold on the second merge `51d8be7e`: PASS (one NIT, on the records commit's message, not folded), review_sha256 `fe10e311695b8480677fa1e5c73a25b9e28588e87c1e66b7818656c399ab11bf`; the landing merge `e62fa864` differs from `51d8be7e` in the run id inside its Review and Bench trailers and in its author and committer time (09:21:36 against 09:18:43 EDT); the tree, the parents and the rest of the message are the same.
- The first landing review's NIT 5: the suite-total sentences in README.md and DEVELOPMENT.md still name the reproduction package as the newest landing in the 1415; the next landing, which moves the total again, names the landings since and the CI run on main after this push.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing worktree's root at this records commit: `verified e62fa864997d939b79dd3779c7b10c30bcd4fef1 (Bench previous: evals/runs/smoke/smoke-20261007-repro-package.json)` and `trailers audit: 16/16 _system first-parent commits since activation f3abe50 verified; graded 16 of 16 seen`, exit 0 (re-run after each amendment of this commit, with the same output).

## Status

Standing. Approval of Landing A's landing; the public push waits for the owner's typed word.

## Date

2026-10-17
