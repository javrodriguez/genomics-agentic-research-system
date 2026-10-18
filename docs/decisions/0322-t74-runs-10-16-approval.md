---
date: 2026-10-18
status: standing
kind: decision
touches:
  - gars/.claude/settings.json
  - gars/_references/config_schema.md
  - gars/_system/configure.py
  - gars/_system/guard_hook.py
  - gars/_system/migrate_data_class.py
  - gars/_system/stage00_register.py
  - gars/_system/stage03_analysis.py
  - gars/_system/tools/registry.json
  - gars/_system/venue_policy.py
symptoms:
  - Runs 10-16 of lane gars-t74 (0312-0315, 0321 and the merge of T57) have no landing approval record
  - Runs 10-16 and the eight commits applied at their landing change files under the protected prefixes gars/_system/, gars/_references/ and gars/.claude/ with no owner-approval record
---
# Lane gars-t74 runs 10-16: approval of their landing and their protected change

Approval of the landing of [0312](0312-stage03-inputs-name-their-assay.md), [0313](0313-stage01-declarations-from-menus.md), [0314](0314-one-sample-name-pattern-per-assay.md), [0315](0315-formula-choices-from-the-design.md) and [0321](0321-registration-asks-test-or-analysis.md), which stay as the lane wrote them, of the lane's merge of lane `gars-ms21`'s T57, and of the eight commits applied at the landing.
The landing changes files under protected prefixes (§9.3, R-094: `gars/_system/`, `gars/_references/` and `gars/.claude/` in `guard_hook.PROTECTED_PREFIXES`), so this record is both the landing's approval and the approval of its protected change.
Its shape follows [0320](0320-t74-gars-fixes-1-9-approval.md).
T57 itself, and its registry entry, are approved in [0294](0294-ms21-t57-approval.md).

Two things approve it, and they are kept apart here:

- **The coordinating session, on the lane and the landing commits as reviewed.** The owner delegated approval of protected changes on 23 September 2026, and since 6 October 2026 every non-money build decision is the lane coordinator's, reported to him after; the lane was built and reviewed under that delegation, and its rulings are glitch-b5's, the lane's coordinating session, as are the eight landing commits: **approved by glitch-b5 under Javier's standing delegation; to land only on Javier's typed word.**
  No sentence in this record is the owner's.
- **The owner's own word, on the push.** Landing on public main waits for the owner's own typed push word; it is recorded on the line below when he gives it, and nothing else here records it.

Javier's word: PENDING

## Context

Lane `gars-t74`'s runs 10-16 (the next fixes of the step map's fix list, after GARS fixes 1-9 of [0320](0320-t74-gars-fixes-1-9-approval.md)) were built red first on the lane's own branch after its run 9 head `ddd978e7`, by Claude Code producers, and reviewed by fresh-context reviewers, each in a separate checkout, never shown a producer's transcript.
**Same-model cost.** Producers and reviewers are Claude Code sessions; a same-model reviewer shares the producer's blind spots more than a different model would (the 0009/0013/0014 precedent).
The reviews were kept independent by fresh contexts, separate checkouts and no access to the producer's transcript.

The landed commits, red first, re-created from the lane's commits after the GARS fixes 1-9 landing, each with its tree change, message, author, committer and dates kept, except that a commit that moves the suite total carries it in the new base's suite-total sentences of README.md and DEVELOPMENT.md, and a commit that adds an index row adds it at its place in the new base's generated decision index `docs/decisions/CONTEXT.md` (the row's text unchanged), and named here by its re-created id (the lane's own working files under `lanes/` do not land):

- Run 10, S03-assay (0312): red `aeb9119c`, fix `04c8a5eb`, contract and record `6eb96267`; stage 03 lists every assay's results, and approve refuses an input that names no assay or one the project lacks.
- Run 10, S01-declare (0313): red `1cdc7091`, fix `14693a93`, contract and record `33f71e8e`; `configure.py declare` asks stage 01's declarations as numbered menus and writes them.
- Run 10, S00-onepattern (0314): red `25ad3b32`, fix `a16c1d49`, contract and record `dbeeb390`; link records each assay's sample-name pattern, and finalize reads it.
- Run 10, R-formula (0315): red `675c1465`, fix `99d70c5a`, router and record `804a0158`; `configure.py formulas` builds the formula choices from the design's own columns, and `apply --formula <n>` writes one.
- Run 11, the fold of the run 10 review: red `58cbce8a`, fix `aadc992e` (a number off the formula menu is refused with the menu); `0245806c` (0313 says `--select` is stripped before the menu compare); red `aac636f9`, fix `91fbdc25` (a typed formula checks every column it names); `98d528a4` (0315 records the registry entry's assay enum, rnaseq_bulk only).
- Run 13, the merge of lane `gars-ms21` at its T57 head: `1de40cce`, a true merge whose resolution keeps `gars/_system/configure.py` as the union of both sides, each kept whole (the command list, the declare and formulas blocks, `cmd_lower`, and the dispatch with declare, formulas and lower); then `6dd214ce`, T57's apply test running its dry run first, as 0302 requires of every apply.
- Run 13, S00-class (0321): red `d084fd07`, fix `ec359f49` (1c: a new registration writes fixture or internal, and a legacy purpose is read only where a row has it); red `2c7590f2`, fix `e1eb9c8c` (2a: finalize reads test or analysis from the declaration); red `c00b9a52`, fix `bc82540d` (3a: terms of use are never asked); red `719cf794`, fix `f0f719f5` (5a: restricted data stops at T5r, and an agent's finalize registers public data only); red `c6ead3e3`, fix `b01ec477` (`migrate_data_class.py` reports and writes nothing); red `593b33b8`, record `53ecdab1` (routes never widen).
- Run 14, the landing dry run's blocker and the runs 12-13 review's NITs: red `bbfdcefa`, fix `558d10d9` (the route test pins its base by content, the two blobs of `venue_policy.py` and `data_policy.tsv`, so it holds in a history that carries no lane commit id); `42f670b9` (finalize's declaration check said as it is, in `stage00_register.py`'s docstring and 0321); `b31a40e3` (the index rebuilt); red `679eb49e`, fix `7e319070` (`migrate_data_class.py` lists an unknown purpose for a person, never calling it legacy).
- Run 15 changed no commit on the branch: its fix, one Next line per data-class refusal, is in hunk G2's patch, landed below.
- Run 16, the two NITs of the runs 14-15 review: `dbc82e68` (0321's decision 4 says that a data-class refusal's one Next line names T5r in place of the enum's generic alternative); its other fix, G2's comment citing decision 0321, is in hunk G2's patch, landed below.

Six of these commits are re-created with one departure from the lane's message: `58cbce8a`, `aadc992e`, `0245806c`, `aac636f9`, `91fbdc25` and `98d528a4` (from the lane's `90044abe`, `daf877a8`, `34776391`, `5ebec57b`, `6106b4f8` and `2d7c072d`) each drop the lane's one `Claude-Session:` line, and nothing else, as glitch-b5 ruled, because public history carries no session link.
Otherwise each re-created commit keeps its original's author, committer and message bytes; a signature does not carry over: all 49 originals re-created for this landing, the lane's merge of T57 among them, carry an SSH signature, and no re-created commit carries one.

The eight commits applied at the landing, by glitch-b5, from the lane's patch files and its rulings, applied after the lanes' commits in the landing order the lane uses, with T57's registry entry of 0294 (`4b333b76`) sixth among the nine:

- `f99bfc12`: the `gars/_system/tools/registry.json` entry for `configure.formulas`, its assay enum rnaseq_bulk only (0315).
- `8c06036a`: the `gars/_system/tools/registry.json` entry for `configure.declare` (0313).
- `368afc07`: link's `--sample-id-pattern` argument in `gars/_system/tools/registry.json` (0314).
- `5b48f3fc`: one `guard_hook.py` READ_ONLY line for `projects/*/00_data/*/sample_id_pattern.txt`, and stage 00's allowed outputs gain that file per assay (0314).
- `106185e7`: the `gars/.claude/settings.json` deny entry that mirrors that line (the fold of the run 10 review, its finding 1).
- `8034bf1e`: hunk R1 of S00-class; finalize's `--purpose` enum in `gars/_system/tools/registry.json` is fixture or internal (0321).
- `44721cc0`: hunk G1 of S00-class; `guard_hook.py` reads the optional use column of `data_sources.tsv` (0321).
- `26ef6ac6`: hunk G2 of S00-class with its witnesses, in one commit as ruled: `guard_hook.py` refuses an agent's finalize whose `--data-class` is not exactly `public`, or that gives none, and points to T5r, in one Next line that stands in for the enum's generic alternative (run 15) and a comment that cites decision 0321 (run 16); the four decision-pin rows `test_nonpublic_read_block-535`, `-536`, `-539` and `-540` and two assertions of `gars/tests/test_nonpublic_read_block.py` move from allowed to refused for that reason (0321).

Reviews of the lane, of commit ranges on the lane's own branch, kept outside the repository and cited by the sha256 of the review file as held on the lane branch at `ea0a099c`:

- run 10 (S03-assay, S01-declare, S00-onepattern, R-formula, and the S00-class design), `ddd978e7..a7450422`: CHANGES (two MINOR, five NIT), review_sha256 `c54e8bfdc081a575bdc1708573601e5a5de8855047f0ddc13beda5fd6a8e1474`; folded in run 11 as glitch-b5 ruled (the lane's rulings file, section "Run 11: the fold of REVIEW-a745042, and the S00-class design ruled").
- run 11 (the fold), `d50f5ad1..71079cf0`: PASS (no finding at MINOR or above, five NIT, not folded), review_sha256 `3aad56b67faf993e948478ef562784ba84df0e755a689f53ac761a66e31be3c3`.
- runs 12-13 (the merge of T57, its ruled test adaptation and S00-class), `faed4cdc..f047180c`: PASS (no finding at MINOR or above, four NIT), review_sha256 `87d60c5a9d51356c0343afb4aeba2916ecc4c8830685b494fb15c8dead325795`; its four NITs are folded in run 14, its third as the landing's blocker.
- runs 14-15 (the route test pinned by content, the NITs, and one Next per data-class refusal), `3a226fd0..81fddd1d`: PASS (no finding at MINOR or above, two NIT), review_sha256 `9b18b11eb9736d2bb3db4e4a8166d7ad993bba607b43fe77487c37c5d098d1b4` (`lanes/gars-t74/REVIEW-81fddd1.md`), so the loop ended at runs 14-15; its two NITs are folded in run 16, two text fixes with no code change.
  It ran the named modules and the four gates with the ten landing patches of both lanes applied together.

glitch-b5's rulings for these runs are in the lane's rulings file, in its sections "Run 11: the fold of REVIEW-a745042, and the S00-class design ruled", "Run 12: T57 merged, S00-class built", "Run 13: the T57 merge ruled", "Runs 12-13's points for glitch-b5, ruled before their review", "Run 14: the landing dry run's blocker and REVIEW-f047180's NITs", "Run 15: one Next per refusal" and "Run 16: REVIEW-81fddd1's two NITs"; the fourth rules that G2 and its witnesses apply together, never one without the other.

## Decision

glitch-b5, under the owner's 23 September 2026 delegation as extended on 6 October 2026, approves landing on public main, as re-created at the commits named above:

1. **Runs 10-16** (0312-0315, 0321, the merge of T57 with its ruled test adaptation, and the folds of runs 14-16): the code, contract, reference and test changes of the lane commits listed above, as lane `gars-t74` built them and its reviews passed them.
2. **The protected change** in the 9 files this record touches, which are all of these runs' and the eight landing commits' files under `gars/_system/`, `gars/_references/` and `gars/.claude/`: the lane's changes to `configure.py`, `stage00_register.py`, `stage03_analysis.py`, `venue_policy.py`, the new `migrate_data_class.py` and `gars/_references/config_schema.md`; the merge's union in `configure.py`; and the landing commits' registry entries and enum, the `guard_hook.py` READ_ONLY line and hunks G1 and G2, and the `gars/.claude/settings.json` deny entry.
   `gars/_system/tools/policy.py`, `gars/_system/hooks/` and `gars/_templates/` are unchanged by these runs.

Outside the protected prefixes, recorded for completeness: the stage contracts, the tests and fixtures under `gars/tests/` (among them the decision-pin fixture `gars/tests/fixtures/refusal_decisions.jsonl` and `gars/tests/test_nonpublic_read_block.py`, changed by the G2 commit under glitch-b5's ruling), the suite totals in README.md and DEVELOPMENT.md, 0312-0315, 0321, this record and the index.
With T57, the suite totals move from 1507 to 1603 tests.

## Test

- The landing's own checks, on 18 October 2026, for T57 and lane gars-t74's runs 10-16 together (one merge carries both, and [0294](0294-ms21-t57-approval.md) points here), recorded in the landing's evidence commit, the merge's child:

Glitch verified the landing merge `ae35f2c7ce685911ad99681dcb280f092117d959` (first parent public main `d0b42319`, second parent the build branch's head `44884b96`), a true merge.
The build branch is lane gars-t74's 38 build and record commits since its run 9 head, its merge of T57 and lane gars-ms21's 10 T57 commits, re-created as named above and in 0294, then the nine commits applied at the landing, the approval records and the suite-total sentences.

- Full suite at the merge itself on a separate test machine (Linux): run `gars-combined-land-ae35f2c-20261018T121440Z`, `PASS kind=gars commit=ae35f2c7ce68 state=done rc=0 ran=1603 passed=1521 failures=0 errors=0 skipped=82`.
- At the merge: `tests/check_counts.py` is clean, `tests/check_contracts.py` has 14 contracts clean, `test_decision_links_resolve` passes (647 of 647 citations resolve), `build_refusal_corpus --check` passes (its decision pin: 1999 refused, 607 allowed) and `gars/tests/test_protected_paths.py` passes; the README's skip bar (fresh-clone.yml's own gate script, run on that run's log against the merge's README) prints `ok: 82 skips, at most 124 documented` and exits 0.
- The outgoing range `d0b42319..ae35f2c7` (61 commits): no gitleaks finding under either ruleset (gitleaks 8.30.0, its default rules and the build machine's push rules, 59 non-merge commits); no home path, user name, private e-mail address or internal machine or project name appears in any added line (4088 read) or message, beyond the coordinating session's name and the plan's name, which are already public; the identities are `Claude <noreply@anthropic.com>` (49) and the owner's GitHub noreply address (12).
- The smoke delta (row 14's ceremony), with the build Mac booked exclusively for it (a timed booking from 08:39:46 to 08:42:00 EDT, in the machine scheduler's log): one run of three `claude-opus-5-5` sessions at the merge's tree (18 October 2026, 08:40-08:42 EDT), prompt and suite hashes equal to the previous record's (`prompt_sha256` `cf32c619…`, `suite_sha256` `ea2f1cde…`); run-1 3/3; `delta` `0/1`, `no change` against `evals/runs/smoke/smoke-20261017-t74-fixes.json`, floor `0/1` from `evals/runs/smoke/smoke-20260926-row-14-activation.json`; the evaluator found nothing (15 outputs hashed, 15 tasks regraded).
  An earlier attempt under this run id, at 08:39 EDT, ran no model turn and was not scored: the driver refused all three sessions before any started (its source checkout was in the wrong place).
- A fresh-context review of the landing merge (Claude Code, Opus 5.5, read-only on the landing worktree, never shown the producer's transcript; threat model: the landing carries more than the reviewed lane and landing commits, a cited fact is false, a private value leaks, or the merge differs from its rehearsal or has the wrong shape; it did not re-run the full suite): PASS (no MAJOR or MINOR, two NIT), review_sha256 `adcfdec8fd8d9074f17d08363d131920215d4b9ea1035dd69bc0dc8a72c3d97c`.
  Its NIT 1 (this record said each re-created commit kept its tree change, where the merge's message names the suite-total and decision-index exception) is folded in this evidence commit; its NIT 2 (a lane record names the private plan's milestone) is not folded, because that word is already public and lane records land verbatim.
- `python3 gars/_system/hooks/audit_trailers.py`, from the landing worktree's root at this records commit: `verified ae35f2c7ce685911ad99681dcb280f092117d959 (Bench previous: evals/runs/smoke/smoke-20261017-t74-fixes.json)` and `trailers audit: 18/18 _system first-parent commits since activation f3abe50 verified; graded 18 of 18 seen`, exit 0 (re-run after each amendment of this commit, with the same output).

## Status

Standing. Approval of lane gars-t74 runs 10-16's landing and of its protected change; the owner's typed push word is recorded above when he gives it.

## Date

2026-10-18
