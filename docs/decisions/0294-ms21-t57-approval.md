---
date: 2026-10-18
status: standing
kind: decision
touches:
  - gars/_references/config_schema.md
  - gars/_system/configure.py
  - gars/_system/executorlib.py
  - gars/_system/stage00_register.py
  - gars/_system/tools/registry.json
  - gars/_system/venue_policy.py
  - gars/_templates/config/atacseq_bulk.yaml
  - gars/_templates/config/chipseq_bulk.yaml
  - gars/_templates/config/cutandrun.yaml
  - gars/_templates/config/methylseq.yaml
  - gars/_templates/config/rnaseq_bulk.yaml
  - gars/_templates/config/scrnaseq.yaml
  - gars/_templates/config/spatialvi.yaml
symptoms:
  - T57 of lane gars-ms21 (0293) has no landing approval record
  - T57 and the configure.lower registry entry applied at its landing change files under the protected prefixes gars/_system/, gars/_references/ and gars/_templates/ with no owner-approval record
---
# Lane gars-ms21 T57: approval of its landing and its protected change

Approval of the landing of [0293](0293-compute-mem-seeded-from-the-venue-and-lowered-by-code.md), which stays as the lane wrote it, and of the one commit applied at the landing for it.
The landing changes files under protected prefixes (§9.3, R-094: `gars/_system/`, `gars/_references/` and `gars/_templates/` in `guard_hook.PROTECTED_PREFIXES`), so this record is both the landing's approval and the approval of its protected change.
Its shape follows [0320](0320-t74-gars-fixes-1-9-approval.md).
T57 lands in one combined landing with lane `gars-t74`'s runs 10-16, which merged it; [0322](0322-t74-runs-10-16-approval.md) approves that lane's part.

Two things approve it, and they are kept apart here:

- **The coordinating session, on the lane and the landing commit as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings are glitch-b5's, the lane's coordinating session, as is the landing commit: **approved by glitch-b5 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: PENDING

## Context

Lane `gars-ms21` (task 4, T57: the memory request seeded from the venue and lowered by code) was built red first on its own branch after the frozen Landings A and C head `2d819179`, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The landed commits, red first, re-created onto public main `faeb99dd` from the lane's commits, each with its tree change, message, author, committer and dates kept, and named here by its re-created id (the lane's own working files under `lanes/` do not land):

- Part 1 (0293 decisions 1-6): red `77bc4c8c`, fix `e506fa70`, record `e1a356dc`; the seven assay templates seed `compute.mem` from the venue's table in `venue_policy.py`, `configure.py lower` lowers the one `compute.mem` line to what the venue accepts and never raises it, and the local memory refusal names the remedy.
- Part 3 (0293 decisions 7-8): red `3673d787`, fix `4108c3bd`; a venue's input budget, held in code and empty until measured, so no submit is sized today.
- R2 (0293 decisions 9-11): red `9e7020bc`, fix `335e465b`; stage 02 fits `compute.mem` in its own step 3b with its own confirmations T12 and T13, and the preflight names the remedy.
- R4 (0293 decision 12): `27f8265a`; `configure.py lower`'s row in the writer-recovery table.
- R6 (0293 decision 13): red `a7b0b739`, red until the registry entry lands; `configure.lower` takes no value.
- Record `a9b204d2`: 0293's part 3, R2, R4 and R6.

The lane branch was merged into lane `gars-t74` at `6759fe60`; at this landing that merge is re-created as `1de40cce`, whose resolution of `gars/_system/configure.py` keeps both lanes' code whole (0322).

The one commit applied at the landing, by glitch-b5, from the lane's patch file and its rulings, applied after the lanes' commits, sixth of the landing's nine in the landing order lane `gars-t74` uses (0322):

- `4b333b76`: one `gars/_system/tools/registry.json` entry for `configure.lower` (argv `python3 _system/configure.py lower`; arguments `project`, `assay` and `dry-run`), so a guarded agent may run the lowering on a public project.
  The rulings let it land only in the same change as step 3b and T12, never with part 1's code alone; this landing carries all three.

Reviews of T57, of commits on the lane's own branch, kept outside the repository and cited by the sha256 of the review file as held on the lane branch at `7912999d`:

- round 4 (Landing C and the T57 design note v2), `45f60028..0ac4587a`: PASS on Landing C, and the T57 note v2 not ready to rule (two MAJOR), review_sha256 `ba8bf68cb1c1c53694f952496f52a5343f168a66a06663b4d2bb2b5a5d4daade` (also cited in [0296](0296-ms21-landing-c-0295-approval-of-protected-change.md)).
- round 5, design note v3 at `c1ecb2fe`: NOT READY (one MAJOR, six MINOR), review_sha256 `6886f3aa10aaf39b0727fb91b3eaf0922d6c4abd555043fe7a8b53513ff285b6`.
- round 6, design note v4 at `62044392`: NOT READY (two MAJOR, three MINOR), review_sha256 `596f0c178f786e45820a3f1c39191875bc327cdcad0c95cdbca97779ff23d95f`.
- round 7, design note v5 at `9b1edc31`: NOT READY (two MAJOR, two MINOR), review_sha256 `2a26799273bf1ffb17486affe581d668a3ede6e19f9fdb01494304ff5f56af53`.
- round 8, design note v6 at `4d631ae3`: READY TO RULE (four MINOR, no MAJOR), review_sha256 `fc46ac5d501c2e6606e99ef0027b12eacca468d019d28923f55a8f58e43994a4`; ruled by glitch-b5 in round 9, its findings folded at the build.
- round 10, the build, `29925e6f..f13d9548`: PASS (no finding at MINOR or above, three NIT, not folded), review_sha256 `ecf4abfa706a09dcd0722479cf9a82143ed079239a2f359338bdcf548559994f`, so the loop ended at round 10.
  It ran the touched modules and the registry's readers with the registry entry applied, re-drove each red claim at its commit, applied mutants of its own, and probed `configure.py lower` from a user's terminal on scratch projects.

## Decision

glitch-b5, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves landing on public main, as re-created at the commits named above:

1. **T57** (0293): the code, contract, reference, template and test changes of the lane commits listed above, as lane `gars-ms21` built them and its review passed them.
2. **The protected change** in the 13 files this record touches, which are all of T57's files under `gars/_system/`, `gars/_references/` and `gars/_templates/`: `venue_policy.py`'s table, the seed in `stage00_register.py`, `configure.py lower`, the remedy in `executorlib.py`, `gars/_references/config_schema.md`, the `mem:` slot in the seven assay templates, and the landing commit's `configure.lower` entry in `gars/_system/tools/registry.json`.
   `gars/_system/guard_hook.py`, `gars/_system/tools/policy.py`, `gars/_system/hooks/` and `gars/.claude/` are unchanged by T57.

Outside the protected prefixes, recorded for completeness: the stage 02 and stage 03 contracts, the tests under `gars/tests/` (among them the frozen Landing C file `gars/tests/test_r164_writer_recovery.py`, which gains `lower`'s row under the round 9 ruling), 0293, this record and the index.
T57 adds 19 tests to the suite; the combined landing's totals are in 0322.

## Test

- The landing's own checks (the merge, the full suite, the outgoing range's scans, the smoke delta and the trailer audit) are recorded in the landing's evidence commit, the merge's child.

## Status

Standing. Approval of T57's landing and of its protected change; the owner's typed push word is recorded above when he gives it.

## Date

2026-10-18
