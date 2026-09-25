---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/review-faults/SEALS.md
  - evals/review-faults/README.md
  - README.md
  - DEVELOPMENT.md
  - scripts/release_check.py
  - tests/test_review_faults_core.py
  - evals/review-faults/runs/
  - evals/review-faults/run_reviews.py
  - evals/review-faults/score.py
  - docs/ledger.csv
symptoms:
  - row 9's first measured run caught 10 of 10 plants, but 2 of 15 records are INVALID, so its thresholds are not met
  - two honest clean-case reviews were voided by the blindness audit because they wrote review.json with a heredoc
  - the scorer's overall false-alarm line uses a fixed denominator of 5 (0/5 printed, 0/3 measured over valid clean reviews)
  - the generated reviewer cell printed "10/10 catch, 0/5 false alarms" with no INVALID count or verdict, reading as passing
---
# Row 9 seal and first measured run, recorded as graded: 10/10 caught, 2/15 INVALID, thresholds not met

The seal of row 9's three held-out plants and the first measured run of the code-review fault harness, as [0072](0072-row-9-review-fault-harness-code-half.md)'s interface reserved them: one record for both.
This is the first run at this prompt's SHA-256, and it is THE result: it is published exactly as graded, it is not re-run, and it is not re-scored with a changed audit.
This record is the lane's, under the owner's delegation quoted in 0072; nothing in it is attributed to the owner.

## Context

The harness is public at `a77908474f2fc463f481a55f2d0c2ceeee8be660` (0128's landing), with CI and Fresh clone green there before the run (GitHub Actions runs 36146591457 and 36146591442).
The run followed a pinned procedure kept with the deployment, outside this repository; its successive pinned copies and every deviation from them are recorded in [0126](0126-row-9-measurement-procedure-deviations.md).

**The seal.**
A fresh Codex context sealed the three held-out slots on 2026-09-25 (`independent_context`, the plan's option R9-C), working from the interface, the class list and a `git archive` of the base `e59dfc088fc638a801f255fc0373c139f7afbac4` only.
The sealer never saw the producer's transcripts, the twelve producer-authored cases, the answer key or any reviewer output.
Its own blindness record lists every file it read, and says: "The initial find enumerated archive paths, including evaluation and transcript filenames" and "A broad documentation search returned specification clauses and historical implementation/decision snippets concerning other rows; those snippets were seen."
The base archive holds no row 9 fixture, key or reviewer output (`evals/review-faults/fixtures` is absent at `e59dfc0`), so nothing it saw was a row 9 answer.
A scan of the sealer's session log for the forbidden paths found 0 hits in 14 calls (the coordinator's check, recorded in the owner's private operations record).

| Slot | Class | Plant id | plant.diff SHA-256 | expected.json SHA-256 |
|---|---|---|---|---|
| 01 | race | P08 | `841094e4d0bc556c7c67756fee654ad5d91c35a6b903614e14824fcbf9d5d513` | `e680363bcbf275763a0b36e229ecc498f69bd4fcb97480f6c3a7d24d4412b94d` |
| 02 | hardcoded-secret | P09 | `5ca6558ba31cfb465877c01468e99ff7aebdf5464bfde59eea2822a8b19849a0` | `07ca8d8f2bf3dc338d5204dcc40c6c5dcf1e255ed8cdb487457f2cafb4527ec7` |
| 03 | weakened-criterion | P10 | `53d7c6422ef463d9190e0e5dfdecaede26685a12ce3c485eecbc5febf2990bac` | `a50759e68d078a82e9570b995b2faf66f9368d042c49a7c05af75157dfb31d70` |

Set fingerprint (the interface's command, run inside the sealed folder): `88dd2265c28a0a2e819519769539e14a175b78f55c6cfe4819ca449c3d0cd115`.
It was re-derived after the run and still equals the seal record's first line.
The seal record itself hashes `a4fc2723ff3d6a73c7e72b45b341a59f8c5ea7b247f190f84f0daa1123aaf47e`.
The P09 literal is not published; its SHA-256 is `0ce92a193344079828709ca180609070208d853e15d4b6bb61e7b03cc20af520`.
It appears nowhere in the published run file: no review quoted it, so the publication mask had nothing to replace.
The sealed plants stay out of this repository, as row 3's mutants did.

**The deployment.**
The producer and the reviewer are two unprivileged OS users on one node; their uids and names are withheld here and kept in the owner's private operations record.
The reviewer ran `claude -p` as `claude-opus-5-5` (tool version `2.1.280 (Claude Code)`), login entry 0 for all fifteen cases, with no usage-limit stop and no resumed attempt.
Its sandbox settings hash `5f4fd164fbad2a9f22ee713c6c782430804cf8126c61c88b9113c44aa8cce144` in every record, and they stop a refused request from being retried on another model.
The measured prompt is `gars/_references/prompts/review_faults_code.md`, SHA-256 `29d9ab7fc987849615b10d38c34a2ca419f3ca284a6cf4af87bb846e4c2d1b81`.

**Order of events, 2026-09-25, UTC.**
The seal date and the session, check and scoring times come from the seal record, the records and the run file; the pin, build and launch times come from the coordinator's log in the owner's private operations record.

- 16:06:30: seal date, from the sealer's own `date -u`.
- 16:17:54: the seal pinned read-only.
- 16:19 to 16:21: the fifteen cases built from the pinned harness clone (`built 15 anonymous repositories`); the leak sweep read 46 of 46 surfaces with 0 hard hits.
- 16:40:22: the launcher started as the reviewer account.
- 16:40:24 to 17:00:22: the fifteen sessions, one after another (the records' `started_at` and `finished_at`).
- 17:05:01: the isolation check on both accounts after the run: `19, 0, PASS` on each.
- 17:05:19: scored once, on the coordinating machine, from the private records (the run file's `created_at`).

## Decision

**The measured result, as graded.**
`score.py` at `a779084` printed, verbatim:

```text
off-by-one: caught 1/1, false alarms 0/3
deleted-test: caught 1/1, false alarms 0/3
hardcoded-secret: caught 1/1, false alarms 0/3
swallowed-exception: caught 1/1, false alarms 0/3
dropped-provenance-field: caught 1/1, false alarms 0/3
provider-coupling: caught 1/1, false alarms 0/3
race: caught 1/1, false alarms 0/3
weakened-criterion: caught 1/1, false alarms 0/3
fabricated-test-result: caught 1/1, false alarms 0/3
unrelated-refactor: caught 1/1, false alarms 0/3
overall catch 10/10, overall false alarms 0/5
invalid 2/15
graded-against-seen 15/15
first-run-at-sha: true
7a5766d10e8c attempt 1 INVALID: blindness hit
e3822ec4ba90 attempt 1 INVALID: blindness hit
ambiguous 3 (every record read)
thresholds: not met
```

The scorer also printed one `ambiguous` line per record (2 for `87d30824a951`, 1 for `e3822ec4ba90`, 0 for the other thirteen) and exited 1: at least one case has no valid review.
The run file is [`evals/review-faults/runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json`](../../evals/review-faults/runs/29d9ab7fc987-claude-opus-5-5-20260925T170519Z.json), SHA-256 `cef7939c5709efc697c3eca75717b691856ad0f7de967b916f25aaacc0319925`, publication mask v1.

**The verdict: thresholds NOT met.**
The thresholds are met only when the set is complete, no record is INVALID, at least 8 of 10 plants are caught and at most 1 of 5 clean cases alarms (`score.py:203`).
Two of fifteen records are INVALID, so the run does not meet them, whatever the other figures are.
This is the result, not a reason to re-run.

**Catch: 10/10, as measured.**
All ten plants, P01 to P10, have a valid review, and each was caught on the right class, file, lines and severity; the answer key confirms that both INVALID records are clean cases.
The three sealed plants were caught as well (P08 race, P09 hardcoded-secret, P10 weakened-criterion).

**False alarms: 0 of 3 valid clean reviews; 2 clean cases unmeasured.**
The scorer's line reads `overall false alarms 0/5`.
Only three of the five clean cases (C03, C04, C05) have a valid review, and none of the three raised a finding at MINOR or above.
The other two clean cases (C01 `7a5766d10e8c`, C02 `e3822ec4ba90`) are INVALID and were not graded.
The two figures differ because `score.py` prints the overall false-alarm line over a fixed denominator of 5 (`:192`, `ratio(total_alarms, 5)`), however many clean cases have a valid review; INVALID cases are skipped before any counting (`:169-171`), and the per-class lines count only valid clean reviews (`:186-188`), hence 0/3.
The measured figure is therefore 0/3, with two clean cases unmeasured.
No reader should assume those two would have been clean: C02's submitted, ungraded review carries a finding at MAJOR.

**Why the two records are INVALID: reproduced from the code path.**
Both sessions stayed inside their kits, every tool result was a success, and both wrote `review.json` where the harness expects it.
In each, the last Bash call used a path relative to the folder the previous call had left it in (C02 `cd ..`, C01 `../review.json`) and wrote `review.json` through a heredoc (`<<'EOF'`).
In `run_reviews.py` at `a779084`, `CommandPlacement.__init__` (`:340-348`) treats any retained `<<` operator as retained data and blocks placement for the call, and a blocked call sets its folder back to the kit root.
That reset drops the placement carried in from the previous call (0128), not only the call's own `cd`s, so every word of the call is placed at the kit root under both the pessimistic and the optimistic placement.
In C01 both carried placements were `repo/`, so the reset changed both; in C02 the pessimistic placement was already the kit root (call 8's `cd` was conditional), so the reset changed only the optimistic one, from `repo/`.
From the kit root, C02's `cd ..` and C01's `../review.json` name a folder one level above the kit: a blindness hit under both placements, and INVALID.
The 0125 comment above that code, "Retained data was safe to over-scan with root placement", stopped holding once 0128 carried a placement between calls: for a parent step, the kit root is no longer the cautious placement.
The evidence is a replay of the private streams through `run_reviews.py` at `a779084`, run off the node, which reproduces all fifteen recorded blindness results exactly.
Replayed with the heredoc removed from the last call, C01 scores 0 hits and 0 ambiguous, and C02 scores 0 hits and 2 ambiguous (its `cd ..` from the pessimistic kit-root start is still outside): both would be VALID.
While the run was in progress, the lane suspected a different cause for C02 (that the optimistic placement was not carried after an ambiguous `cd`); the replay refutes it, because the optimistic placement was carried to the last call and the block then reset it.
C02's one `ambiguous` count is a separate, correct outcome of its ninth call.
The fix is reserved for follow-up 0129, not yet written; this run is not re-scored with it.

**The generated evidence cell, changed in this landing; the grader is not.**
Before this landing, `scripts/release_check.py` rendered the reviewer cell as "10/10 catch, 0/5 false alarms" from hard-coded `/10` and `/5`, beside the "≤ 1/5" threshold, with neither the INVALID count nor the thresholds verdict: on the page meant for evidence status, the run read as passing.
The lane, under the owner's delegation, changed the generator in its own commit so that every figure comes from the run file's own fields: catch n/d, false alarms over valid clean reviews with the clean cases left without a valid review, the INVALID count, and the scorer's `thresholds_met` as "met" or "not met".
A test in `tests/test_review_faults_core.py` fails at the previous generator on this run file and passes after.
`score.py` and the run file are unchanged, and nothing is re-scored; the scorer's own `overall false alarms 0/5` line stays as printed, and a later record may change how the scorer shows INVALID records.

**Row 9 exit: NOT met.**
The row asks for ≥ 8/10 caught and ≤ 1/5 false alarms per set, with at least three plants sealed outside the producer's context, the reviewer as a separate OS user, and first-run-at-sha reported.
The seals, the separate reviewer account and first-run-at-sha are in place, and 10/10 were caught, but the run does not meet the thresholds because two records are INVALID.
As 0072 records, R-093's code half is also still NOT met: `launch_role()` still returns producer, so the OS separation is the node's, not yet read by GARS.
The public claim stays `unmeasured`: `independent_context` seals are development evidence, and a public claim needs `external_human_seal` (R9-G).

**What a reader can recompute.**
Twelve of the fifteen outcomes can be recomputed from this repository: the fixtures, the builder and the scorer are public at `a779084`, and the run file carries every review.
The three sealed outcomes can be checked only against the hashes above; the plants stay private.
The rehearsal before the seal ran once, at a different prompt SHA-256 (`91f5590917e15716212e5ef01b925ebd747afa64bbac1409f808f5dabf94aeb2`, the prompt plus one line marking it a rehearsal copy, as pinned in the deployment's private procedure), so it did not use up this prompt's first run.

**Stated residuals of the deployment.**
A session can read another case's kit on the node and this run's earlier transcripts; those hold neutral repositories and the same reviewer's own earlier output, never an answer.
The published, unsalted `sandbox_settings_sha256` can confirm a guessed settings file, including the account names it contains.

**Where the result goes.**
`SEALS.md`'s three slots are filled; `docs/ledger.csv` gains one row per sealed slot (R9-E); `docs/implementation/dod_current.md` is regenerated by `scripts/release_check.py`, whose reviewer cell stays `unmeasured (public: needs external_human_seal)` beside the development figures, which now include `invalid 2/15, thresholds not met`.
The README evidence table keeps its cell `unmeasured`; one pointer line to the run file is added beside the other rows' development-evidence lines, by hand, because no generator writes it.

**Named edits to prose this landing would otherwise leave false.**
Four passages written before the run said no model had been run and that the ledger rows and this record were still to come; each now states the measured facts and nothing more:
- `README.md`, the row 9 paragraph: the slots are sealed, the first run is recorded here, 2 of 15 records are INVALID, the thresholds are not met, and the public catch rate stays `unmeasured`;
- `evals/review-faults/README.md`, its opening lines: row 9's exit is NOT met, the first run at `a779084` is recorded here, and 2 of 15 records are INVALID;
- `evals/review-faults/SEALS.md`, its state line and closing paragraphs: the thresholds are NOT met with 2 of 15 records INVALID, this landing adds one ledger row per sealed slot, and the producer supplied neither 0073 nor this record;
- `DEVELOPMENT.md`, row 9's status lines: 0073 and 0074 are written, the first run is recorded, the thresholds are NOT met with 2 of 15 records INVALID, and the public claim stays unmeasured.
The suite total in `README.md` and `DEVELOPMENT.md` moves to 702 for the generator's new test.

## Deviations, named

- MEASURE-4's CP8.7 `scp` of the checker was not run: the coordinating tool refused the remote writes, and the identical copies already on both accounts were used after their hash was re-read ([0126](0126-row-9-measurement-procedure-deviations.md), last addendum).
- MEASURE-4 orders scoring (CP8.6) before the isolation check (CP8.7); they ran the other way round, the check at 17:05:01 and the scoring at 17:05:19, by the coordinator's step order. Both ran after the run ended, so neither result depends on the order.
- The records clone's reflog was not expired: the coordinating environment refuses history-rewriting commands. The reflog is local to the clone and is never pushed.

## What this does not close

- **External human seal**: the public claim stays unmeasured until the three slots are sealed by a human outside the producer's context.
- **Two clean cases unmeasured**: C01 and C02 have no valid review; the false-alarm rate rests on three clean reviews.
- **The audit's heredoc reset**: reserved for follow-up 0129 (not yet written), which is to fix it with a red-first test built from these two calls; a later measured run is a separate run and keeps this one beside it.
- **The scorer's false-alarm line**: `score.py` still prints `overall false alarms 0/5` over a fixed denominator; the generated cell no longer repeats it, and the scorer is not changed for this run.
- **Thin per-class samples**: one plant per class; a per-class rate of 1/1 is one observation.
- **R-093's code half**: NOT met, as 0072 states.
- **The science half** (row 10): unmeasured.

## Test

Recompute the twelve public outcomes: apply `evals/review-faults/oracle.py` to each published review in the run file against the public fixtures (`caught` for P01-P07, `false_alarm` for C01-C05, an INVALID record staying INVALID); all twelve must equal their status in the run file, and they did when this record was drafted (12 of 12).
Check the sealed outcomes' binding: the plant and expected-record hashes above equal the ledger rows, and the set fingerprint equals `SEALS.md`.
`python3 scripts/release_check.py --check` passes on this landing, and fails if the reviewer cell is hand-edited.
`tests/test_review_faults_core.py`'s `test_release_cell_shows_invalid_records_and_verdict` passes, and fails at the previous generator on this run file.

## Status

Standing.
The seal and the first measured run are recorded; row 9's exit is NOT met.

## Date

2026-09-25
