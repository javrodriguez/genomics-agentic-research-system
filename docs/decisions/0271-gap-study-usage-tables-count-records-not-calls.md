---
date: 2026-10-02
status: standing
kind: defect
touches:
  - evals/gap-study-costs-by-call/
  - tests/test_gap_study_costs_by_call.py
  - tests/data/costs_by_call_duplicate_records.jsonl
  - docs/EVALS.md
symptoms:
  - the Gap Study token tables count each model call about twice
  - costs.py sums message.usage over every transcript record, and one API call is written as several records
---
# The Gap Study token tables count records, not calls: a dated correction beside them

The owner approved a dated public correction on 2 October 2026 (he typed "defaults" at 14:58 EDT in the Row-orchestrator window, taking that item's "correction yes").
Every other ruling here is the lane's, made under the owner's standing delegation of 23 September 2026; no other sentence in this record is the owner's.

## Context

Each Gap Study round publishes its token use in a `COSTS.md` written by that round's `costs.py`: `evals/gap-study/`, `evals/gap-study-2/` and `evals/gap-study-3/`.
Each `costs.py` adds `message.usage` over every transcript record that carries one.
Claude Code writes one record per content block of a model reply (thinking, text, tool use), and every one of those records carries the whole reply's usage.
So the tables count usage records, not model calls, and a reply with three blocks is counted three times.

The error was found by the GARS face v3 token-cost research lane on 2 October 2026 and reproduced independently by the lane that built this correction, on public main `a272d95`.
On the row it was found on (round 2, `number-fidelity`, control, `claude-opus-5`, take 1), the transcript holds 16 usage records and 10 distinct calls.
The pinned reader returns the published 32 / 437,281 / 48,901 / 4,494 (input / cache read / cache write / output); counted once per call the figures are 20 / 286,108 / 26,023 / 2,820.
Across the three rounds, 8,399 usage records hold 4,136 calls, and the tables published 386,064,019 tokens, 1.98 times the 195,353,721 the calls used (per class: input 2.25, cache read 1.95, cache write 2.35, output 2.17).
Every record of one call carries the same usage as the others of that call, and `message.id` and `requestId` are one to one in every committed transcript, so counting each call once is unambiguous.

What can and cannot be changed:
- Each round's `costs.py` is pinned by sha256 in its `prereg.json` (`pinned_files`), and `check_results.py` verifies the pin, so editing it would amend a pinned instrument.
- Each `COSTS.md` is bound byte for byte to its pinned reader by `costs.py --check`.
- Round 2's `copy_manifest.py --check` requires `evals/gap-study/` unchanged since `ac8662b`, and round 3's requires rounds 1 and 2 unchanged since `bf065fe`, so a note inside rounds 1 or 2 would turn those checks red.
- The rule this project holds: a pinned instrument or a published record is never amended in place.

## Decision

1. **A dated reader beside the rounds, never inside them.** `evals/gap-study-costs-by-call/costs_by_call.py` (standard library only) counts usage once per pair of `message.id` and `requestId`.
   Two records of one key with different usage raise `Disagreement` rather than one being picked.
   A record missing either half of the key is never merged with another; it counts as a call of its own and is reported (none in the committed transcripts).
   The published column comes from importing each round's own pinned `read_one`, unmodified.
2. **The correction page.** `--write` writes `evals/gap-study-costs-by-call/CORRECTION-2026-10-02.md`: what was wrong, its size overall and per round, what is wrong in each table (per take, pre-freeze walks, per model; the recorded pauses carry no token figure), every take and walk counted once per call beside its published cells, round 1's two prose ranges re-derived, and every line in the repository that quotes the figures, as `path:line`.
3. **Bound, not typed.** `--check` exits 1 unless the page is exactly what the reader writes, every published figure on it is found in that round's `COSTS.md` (each per-take, walk and per-model row, and round 1's two prose ranges), and every cited line still carries the text it is cited for.
4. **Nothing published is edited.** The three `COSTS.md` files, the pinned `costs.py` files, the verifier reports, the allowlists and `prereg.json` stay as they are.
   The lines that quote the figures are all inside the study folders; they are listed on the correction page rather than annotated, because those folders are records and rounds 1 and 2 are bound by the later rounds' copy checks.
   The public pointer is a dated paragraph at the top of `docs/EVALS.md`, beside the 28 September intervals paragraph.
5. **No graded result depends on it.** Verified on `a272d95`: no grader, label, count, interval, analysis or result reads usage.
   `grep` over each round's `analyse.py`, `check_results.py`, `graders/`, `observations.py`, `takes.py`, `evals/transcript.py` and `evals/gap-study-intervals/` finds no read of `usage`, `tokens` or `costs`; the shared transcript parser keeps what the agent said and ran and discards usage, by design (`costs.py`'s own docstring).
   Wall clock (first to last timestamp), the recorded pauses and each round's dollar line do not read usage and are unchanged.
6. **The test runs where the suite runs.** `tests/test_gap_study_costs_by_call.py` is collected by `tests/run_tests.py`, so CI's suite step and the athena suite run it; no CI workflow file changes, so no protected path is touched.

## Rejected alternatives

- **Fix `costs.py` and re-render each `COSTS.md`.** Amends three pinned instruments and three published records, and breaks `check_results.py`'s pin check and the later rounds' copy checks.
- **A dated note under its own heading in each `COSTS.md`.** Rounds 2 and 3 allow one, but it turns round 2's and round 3's copy checks red for rounds 1 and 2, and a note in round 3 alone would be inconsistent.
- **Key by `message.id` alone.** Works on this data, but `requestId` is what tells two requests apart if one response id ever recurred; the pair is the stricter key, and the data shows the two agree.

## What this does not close

- No dollar figure at list price is published here; the rounds never converted tokens to money, and each round's dollar line (billed beyond the standing subscription) is unchanged.
- Sub-agent usage: none of the 293 committed take and walk transcripts calls a sub-agent tool or carries a sidechain record, so there is none to add; a later instrument whose sessions spawn sub-agents must read their transcripts too.
- The earlier Layer B evaluation's figure quoted in round 1's prose (`evals/transcripts/confounded-refusal/`) is re-derived on the page, but that evaluation publishes no token table of its own.

## Test

`python3 tests/test_gap_study_costs_by_call.py` runs 12 tests OK, and `python3 evals/gap-study-costs-by-call/costs_by_call.py --check` exits 0.
Red first: the test was committed alone at `8c4cece` and failed there (`Ran 11 tests`, `FAILED (errors=10)`; the one passing test is the pinned reader overcounting the fixture).
The fixture `tests/data/costs_by_call_duplicate_records.jsonl` holds one call written as three records and one written as one; the pinned round 1 reader sums four records' worth and the corrected reader counts two calls.
Faults that must fail: two records of one call with different usage (raises), a record missing half its key merged (counted apart), a changed figure on the page, a changed figure in a round's `COSTS.md`, and a cited line that moved.

## Status

Standing.
The implementation and this record are the lane's; the owner approved the correction itself, and the public push waits on his own typed word.

## Date

2026-10-02
