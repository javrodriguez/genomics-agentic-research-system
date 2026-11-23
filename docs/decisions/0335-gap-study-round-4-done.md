---
date: 2026-11-20
status: standing
kind: decision
touches:
  - evals/gap-study-4/verification/verify-1.md
  - evals/gap-study-4/verification/verify-2.md
  - evals/gap-study-4/verification/verify-3.md
  - evals/gap-study-4/SECONDARY.md
  - evals/gap-study-4/SECONDARY-published-20261120.md
  - docs/gap-study-4/REPORT.md
  - docs/gap-study-4/secondary/README.md
  - docs/EVALS.md
symptoms:
  - round 4 had no done record, and the evaluations page still called the round unverified after final verifiers 2 and 3 had returned PASS
---
# Gap Study round 4 is done: three final verifications, the verified head 1ded8e9a2ada, and the publication tail after it

The rulings in this record are the Gap Study round 4 publication lane's, under the owner's answers quoted below.
The quoted words are the owner's, copied from the records named beside each quote; no other sentence here is his.
The publication itself waits for his own push word, which does not exist yet and is not cited here.

## Context

Round 4 of the Gap Study was frozen at `c485a9598` on 5 Nov 2026.
Three fresh agent sessions then verified it in turn, each blind to operator material, the blindness checked from its own session file.
Each report names on its line 1 the head it checked ("checked at"), and each was committed unedited by a later commit ("committed at"):

| Report | Checked at (line 1) | Verdict (line 5) | Committed at | Blindness file |
|---|---|---|---|---|
| `evals/gap-study-4/verification/verify-1.md` | `2596336289d1` | FAIL, two blockers | `65f07144a` | `verify-1-blindness.txt` |
| `evals/gap-study-4/verification/verify-2.md` | `01479891509b` | PASS | `79d9e45a8` | `verify-2-blindness.txt` |
| `evals/gap-study-4/verification/verify-3.md` | `79d9e45a8d8b` | PASS | `1ded8e9a2` | `verify-3-blindness.txt` |

Final verifier 1's two blockers were that two published pages stated the model panel's reading as a person's, and that the language check was red on one amendment commit's body.
Three recorded amendments followed it, all on 17 Nov 2026: `v4fix-commitlint-20261117` (`54d5a9cca`) and `v4fix-panel-wording-20261117` (`431d8876b`, the owner's OD222), which answer the two blockers, and `v4fix-golden-20261117` (`14db16d3f`), which carries that wording change into a test (`tests/test_labelling.py`).
No number changed: between the head verifier 1 checked and `1ded8e9a2ada`, `RESULT.md` changes only in its wording on who read the flagged list, and `labelling/AGREEMENT.md` only in who it names as the labeller.
`1ded8e9a2ada68ecf3ececc1c6c33dd0634f7ca3` (H) adds only review records to the head verifier 3 checked: `verify-3.md`, `verify-3-blindness.txt` and `review_kit/rounds.json`, insertions only (`git diff --stat 79d9e45a8 1ded8e9a2ada`).
H is the verified head; the report's section 11 is run at it.

The owner's words on the report and its publication, typed in the orchestrator's window, his own terminal `claude` window:

- Fri 20 Nov 2026, 16:03 EST: "I approve the gap study report v2" (the owner-step register `owner-steps.json`, line 2612, step `gap4-report-v2-read`, and the lane orchestration log `orchestrator-night-2026-10-13-claude.md`, line 3072). Both records say it accepts the report's text only, and is not a publication word.
- Fri 20 Nov 2026, 19:03 EST, his answers to the publication choices: "1: sign · 2: publish · 3: cut · 4: publish · 5: byline top only · 6: refresh · 7: build the package · 8a: leave · 8b: use section 8 · 8c: later · 8d: draft it" (`owner-steps.json`, line 2640, step `gap4-publication-choices`; orchestration log, line 3080). Both records say it is not a push word.
- Fri 20 Nov 2026, evening (22:01 EST in the orchestration log, line 3105; "about 22:05 EST" in `owner-steps.json`, line 2732): "cards: 1 add · 2 keep · 3 keep · 4 keep · 5 keep · 6 keep · 7 keep · 8 keep · 9 keep · 10 keep · 11 keep · 12 keep · 13 keep · 14 keep · 15 keep · 16 keep · 17 keep · 18 seen". Card 1 was the limitations sentence on the connected tools offered to arm O, drafted for him to accept or change; "1 add" is his ruling of 20 Nov to add it, as the card words it; the orchestration log records it as that sentence alone, without the card's optional second sentence on the pre-registration.

These records are in the owner's private repositories, not in this one.

## Decision

1. **Round 4 is done at H.** Final verifiers 2 and 3 each returned PASS, and H holds all three reports, committed unedited. The study publishes exactly as graded; no take is regraded, and no number moves.
2. **Everything published with the round comes after H, on a tail of labelled commits, and changes no number:**
   - `65deb5eec` and `f565ca181`: the report (`docs/gap-study-4/REPORT.md`, revision 3: revision 2 as accepted, with the publication edits his answers call for), its trace and its build scripts, and the exploratory action reading (answer 2), all under `docs/gap-study-4/`;
   - `bd23467b1`: the pre-registered secondary analysis (answer 4), `evals/gap-study-4/SECONDARY.md` byte-identical to the analysis branch at `dcc3538d5` (sha256 `b09bc48f746610cfa85bdaaeaefa09a6fd8a061833e855cf29be0b5e027ebaa7`) with a dated note beside it, and its code, pre-registration copy and five recorded inputs under `docs/gap-study-4/secondary/`;
   - `1c61897de`: the report's limitations sentence on arm O's connected tools (his "1 add"), with the script that recounts its figures from the records at H;
   - `4aec1bc5c`: the round's section of `docs/EVALS.md` (answers 6, 4 and 8b): its status line, the secondary's published location, the same limitations sentence, and "The comparison", which holds the report's section 8, his signed conclusions (answer 1), word for word.
   Under `evals/gap-study-4/` the tail adds only `SECONDARY.md` and its dated note, so the study tree's other files are as H holds them.
3. **The report's notes he chose to leave (answer 8a) stay unfolded**, and round 3's section of the evaluations page (answer 8d) is drafted and placed by its own step, on his accept.

## What this does not close

- The publication is not pushed. It waits for: round 3's section, accepted by the owner and placed on the publication branch; the merge of this tail onto public main and the round 4 CI job's pin to H; the scans of the commits to be pushed and his ruling on each finding; the full test gate on the exact candidate; a fresh visitor-style review from a clone; and his own push word.
- The secondary's code was not on the line the final verifiers checked; its check is the staged command in `docs/gap-study-4/secondary/README.md`, not a verifier's.
- The action reading is exploratory and post hoc; no verifier read it.

## Test

From a clone of the repository, checked out at `1ded8e9a2ada`, the report's section 11 commands, each exit 0:

```bash
git log --oneline --reverse -- evals/gap-study-4/prereg.json
python3 evals/gap-study-4/result.py --check
python3 evals/gap-study-4/completeness.py --check
python3 evals/gap-study-4/check_results.py --regrade
python3 evals/gap-study-4/labelling/agreement.py --check
python3 evals/gap-study-4/labelling/flagged_verdicts.py --check
```

`result.py --check` must fail when one committed record is flipped from right to wrong, as final verifier 3 recorded.

The secondary, by the staged command in `docs/gap-study-4/secondary/README.md`, from scratch trees at `1e097b2f5f99`: its two tests pass; the frozen and the patched grade files are re-derived, each equal to the published file in `docs/gap-study-4/secondary/inputs/` in every field but `tree` (the absolute path of the checkout `grades` graded), shown by comparing the two documents with `tree` removed and by showing that `tree` is the only key that differs; the blind check (`check.json`) is re-derived byte for byte; and `SECONDARY.md` is regenerated byte for byte from the five published inputs. The first attempt's check and the shapes file are recorded inputs, and the first attempt cannot be re-run.

At the tail tip: `python3 docs/gap-study-4/report-build/assemble.py` and `python3 docs/gap-study-4/report-build/check_trace.py` exit 0 and leave `docs/gap-study-4/` unchanged; `python3 evals/gap-study-4/lint_language.py --section-of docs/EVALS.md` and `python3 evals/gap-study-4/lint_pooling.py --section-of docs/EVALS.md` exit 0; and the repository's own tests, `python3 tests/run_tests.py`, `python3 tests/check_contracts.py` and `python3 tests/check_counts.py`, pass.

## Status

Standing.
The round's results are done and verified at H; this record and the tail are implemented, and their publication is not yet approved: it waits for the owner's push word.

## Date

2026-11-20
