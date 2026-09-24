---
date: 2026-09-24
status: standing
kind: decision
touches:
  - gars/_references/prompts/review_faults_code.md
  - evals/review-faults/fixtures/plants/
  - evals/review-faults/fixtures/clean/
symptoms:
  - row 9's reviewer prompt lives under the protected prefix gars/_references/ with no owner approval record
  - row 9's plant and clean fixtures live under the protected evals/*/fixtures/ paths with no owner approval record
  - 0072 reserves 0073 for the owner's approval at merge; the owner delegated it on 23 September 2026
---
# Row 9: approval of its protected additions, under the owner's delegation

Addendum to [0072](0072-row-9-review-fault-harness-code-half.md), which stays byte-identical.
Every file this record touches is new under a protected path (R-094): the reviewer prompt under `gars/_references/`, and the answer-keyed fixtures under `evals/review-faults/fixtures/`, so it needs an owner-approval record.
The owner delegated that approval on 23 September 2026 ("I delegate every decision to you, use your best judgement. I don't want to intervene, we already have plans, specs, etc, just get things done", recorded in the owner's private operations record), so this record is written by Glitch under that delegation and labelled as such; it is not in the owner's words.
Its shape follows row 7's [0079](0079-row-7-delegated-approval-of-protected-additions.md) and row 12's [0066](0066-row-12-owner-approval-of-protected-changes.md).
The files themselves arrive with row 9's merge; this commit adds only this record and the regenerated decision index.

## Context

Row 9 (the review fault harness, code half; spec §18 line 398) was built on its own branch from public main `e59dfc0` by a producer (Codex) running as one unprivileged OS account, and reviewed by a fresh-context reviewer (Claude Opus 5.5) running as a second, separate unprivileged OS account on the same node, through an unattended queue runner.
The accounts, the runner and every step's evidence are recorded in the owner's private operations record, not in this repository; the repository shows the launcher's own refusal to score a review run from the producing account.
The owner's rulings for the row are quoted in 0072 and its addenda: R9-A to R9-G at their defaults ("defaults"), D-22 ("D-22 answered by the two OS users"), and Q1-Q4.
Everything else in the row's specification is labelled in 0072 as the lane's, under the owner's delegation.
The row took fourteen producer commits, `767a986` to `251c54e`; 0072's addenda record every round.
The final independent review (round AC1 on `251c54e`) was APPROVE, with one NOTE.
Its SHA-256 is `b2434bcb0efaaf877b5201c3fe4b5559d204e1384c4ceaf80b6be6a9fdcfb2f6`; every review of the row is kept outside the repository.

## Decision

Glitch, under the owner's 23 September 2026 delegation, approves the following protected additions as merged, on 2026-09-24. Only the quoted sentences in this record are the owner's words.

1. **The reviewer prompt (`gars/_references/prompts/review_faults_code.md`, §10, §21 Q10's default location).**
   Written from §10 and the case format only; it tells the reviewer its whole world is its folder, to review the last commit's diff in the context of the repository, to run tests only inside the repository with its temp folder inside the kit, and to write `review.json` with the review part of the record schema and the closed class vocabulary.
   It never mentions planted faults, a harness, catch rates or evaluation, and no model was run against any case in this row, so the first measured run will be first-run-at-sha for this prompt.
2. **The producer's seven plants (`evals/review-faults/fixtures/plants/P01`-`P07`, §10).**
   One plant each for `unrelated-refactor`, `provider-coupling`, `off-by-one`, `dropped-provenance-field`, `deleted-test`, `fabricated-test-result` and `swallowed-exception`, each a `plant.diff` against `e59dfc0` with an `expected.json` answer key (`match` by file and post-plant lines, `min_severity`, `seal_type: unsealed`).
   The three sealed classes (`race`, `hardcoded-secret`, `weakened-criterion`, the owner's R9-B default) have no plant here: their slots stay empty in `SEALS.md` for an independent sealer.
3. **The five clean cases (`evals/review-faults/fixtures/clean/C01`-`C05`, §17's false-alarm denominator).**
   Genuine, correct small changes with `kind: clean` and no class; a finding of MINOR or above on one is a false alarm (the owner's R9-D default).

## What this does not close

Copied from 0072:

- The row 9 exit: the three sealed slots, the seal hashes in the ledger, and one real measured run with its per-class catch and false-alarm rates at first-run-at-sha.
- Public credibility: `independent_context` seals are development evidence only; `external_human_seal` remains required by §10 and §21 Q9, so the README's public cell stays `unmeasured`.
- R-093's code half: `launch_role()` still returns producer until a later record.
- The science half (row 10).
- Trailer-gate consumption of JSON review records (row 11 reads one session line).
- A statistically broad per-class estimate: one plant per class gives only 0/1 or 1/1.
- Public recomputation of the three sealed outcomes: a stranger recomputes twelve of fifteen outcomes from the repository; the sealed three are hash-checkable only.
- The blindness audit is a detector, not the enforcement: reads outside the kit are refused by the reviewer's sandbox, which the record binds by its settings hash; shell constructs the audit does not parse are its named residual (0072, items 20 to 23 of the lane's specification).
- Execution on Python 3.6.8 and on the cluster is not evidenced.

## Test

Glitch verified the row independently on the owner's machine, each evidence run alone on it:

- At row 9's reviewed head `251c54e`, the suite in its three documented modes: `Ran 439 tests`, `OK` with 11, 55 and 86 skips; `tests/check_contracts.py` clean; `tests/check_counts.py` clean; `evals/test_harness.py` `Ran 44 tests` `OK`; `evals/check_results.py --controls --lexicon` clean; no file left in the system temp folders.
- At this merge's tree: `Ran 498 tests`, `OK` with 11, 73 and 104 skips (the README's documented figures, unchanged by row 9), canary 0 of 9, the same checks clean.
- Fifteen independent mutations of the harness's guards (the oracle's class, file, line and severity tests; the launch-owned envelope; the reviewer-is-not-producer refusal in the launcher and the scorer; the answer key kept out of every case; the salted neutral id; first-run-at-sha; the honest-call corpus and the fail-closed text removal of the lane's items 22 and 23) each turned their named test red and passed again once the bytes were restored.
- A leak sweep of the cases the builder makes found no case id and no class id on any surface a case adds.
- gitleaks over `e59dfc0..251c54e` under the push door's ruleset and under `gars/.gitleaks.toml`: 0 findings; no canary; commit metadata carries only the noreply identity; no account, host, address or home path in any added line.
- `.github/workflows/fresh-clone.yml` replayed at this merge in a Linux `python:3.12` container as a plain user: `Ran 498 tests` with 104 skips, and the workflow's own skip gate passes at its documented bar of 104.
  The replay's other reds came from the container, not the repository (git refusing a bind-mounted folder, no rsync, no IPv6 loopback); rerun in a container set up like the hosted runner, row 9's build and fault-control modules and the decision-link check pass in both the plain and the scratch environment.

## Status

Standing. Approval of the protected additions only; it does not claim the row's exit.

## Date

2026-09-24
