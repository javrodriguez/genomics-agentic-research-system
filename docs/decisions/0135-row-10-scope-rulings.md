---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/bio-faults/
  - gars/_references/prompts/review_faults_science.md
  - scripts/release_check.py
symptoms:
  - the README evidence row for the reviewer catch rate has no science source
  - spec row 10's "5 fixtures + 3 clean" cannot be scored against §17's "at least 8/10 per set, at most 1/5" (D-11)
  - "one repeat" is undefined in the spec
---
# Row 10: scope rulings for the review fault harness, science half

Decided by Glitch under the owner's standing delegation of 23 Sep 2026.
No sentence in this record is attributed to the owner.

## Context

Spec §18 row 10 names the artifact "review fault harness, science half (5 fixtures + 3 clean, one repeat)", with the exit "science catch rate per class", 12 to 25 hours, and "at-risk tier" if hours collapse.
Spec §10 names `evals/bio-faults/`, ten science fault classes and five clean projects, and fixes the rules the measurement must keep: a fresh reviewing context that receives data, design and results before any narrative (the `JudgeInput` pattern), a read-only credential, `model_id` and `prompt_sha256` on every review, Codex producing and Claude reviewing for science until measured otherwise, at least three of every ten plants sealed outside the producer context before the prompt is tuned, a deterministic field-match oracle, and per-class catch and false-alarm rates with the first-run-at-prompt-sha value beside the current one.
§11.3 (R-115) requires every ratio printed with numerator and denominator, and `0/0` printed as `uncomputable`.
§17 (R-170) sets the science reviewer clause at "≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported".
The gap assessment records row 10 as missing and names D-11, the conflict between row 10's "5 + 3" and §17's thresholds.
Row 9's code half (`evals/review-faults/`, records 0072, 0073, 0125, 0127, 0128) is the machinery this row reuses by import.

The rulings below settle the questions the spec leaves open, before any code is written, so the producer and every reviewer read the same scope.
Where a ruling says "NOTES" or "the seeded draw", it means the lane plan's seeded hash-order draw over the five planted classes; which classes are sealed is recorded in the seal record (0138), after the seal.
Where a ruling says "the door", it means the sealing tool that runs on the owner's workstation outside this repository.

## Decision

Each ruling below is decided by Glitch under the owner's standing delegation of 23 Sep 2026.

| # | Question | Ruling |
|---|---|---|
| R10-1 (D-11) | Which governs v0.1: row 10's "5 + 3" or §17's "≥ 8/10, ≤ 1/5"? | Row 10's set is five plants and three clean projects. §17's science clause is printed on every run and reads **NOT met (partial set: 5 of 10 classes planted, 3 of 5 clean)** until the at-risk tier ("the deferred halves of rows 10 and 13", §18) completes the ten and five. Row 10's exit, "science catch rate per class", is met by a **scored first measured run**: every case in the manifest has a record (graded-against-seen 8/8), and invalid n/8 is printed beside the rates. An INVALID record counts in every denominator and never as caught, and never as a clean pass. A clean case with an INVALID record prints as "k invalid, not clean" beside the false-alarm ratio. A false INVALID is final: only a usage-limit attempt resumes, and nothing is re-run to replace an invalid record. An exit with invalid > 0 is still the exit, and 0138 states the count and each reason. It never claims §17's threshold. |
| R10-2 | Which five classes? | The five whose flaw is statistical or design-level and plantable on GARS's existing project surfaces: `swapped-condition-labels`, `replicate-dropped-after-approval`, `pseudoreplicated-de`, `batch-confounded-contrast`, `causal-language-on-correlational-da`. The other five (`wrong-reference-in-params`, `fabricated-citation`, `p-value-edited-in-report`, `missing-n2-limitation`, `contradictory-literature-omitted`) are provenance, integrity or reporting classes; they stay in the vocabulary, are unplanted in v0.1, and are the at-risk tier's. **Detector adjacency, stated:** three chosen classes sit beside active deterministic checks: `pseudoreplicated-de` beside row 8's catalogue #4 `pseudoreplication` and stage 01's `subject_nesting`; `batch-confounded-contrast` beside catalogue #1/#3 (`confounded_condition`, `covariate_imbalance`) and stage 01's `batch_confounding`; `swapped-condition-labels` beside catalogue #5 `sample_label_mismatch`. `replicate-dropped-after-approval` sits beside §7.5's `<GROUP>_REP<N>` exit gate and stage 03's `verify` (R10-6). A plant of these classes must be a real instance of the flaw in a form those checks do not see; whether it is still detectable from the case's own files is the honesty audit's main question (R10-7). |
| R10-3 | How many are sealed, and which? | Three of the five plants (§10's "at least three of every ten", read as a floor that the full set must also meet) plus one of the three clean projects (so false alarms have a held-out half, row 8's precedent). The three plant classes are the seeded draw in NOTES, re-derived at CP0 from the base sha; the producer writes the other two plants and two clean projects. **The seal runs after the harness merge (CP6)**, with the merged head's generated base trees, base ids and seeds, the builder's layout map and the gate names as its inputs; their sha256s are recorded in the door's manifest and in 0138. §10's "sealed before the reviewer prompt is tuned" holds because the prompt is never tuned in this row. **Correction cap:** a sealed case that fails `validate` or the honesty audit gets at most two correction rounds; `correct` receives the door's `validate` output and the audit's lines for its own ids. **Replacement:** a sealed plant still failing after two rounds is dropped, unread by Glitch, and replaced once by a new seeded draw (NOTES, "the replacement draw") under the next free id (P06, then P07). That draw is over the five classes minus the dropped class and minus classes already holding a valid sealed plant. The replacement goes through `validate` and the audit under the same cap. A dropped C03 is replaced by a sealed clean C04. If a replacement also fails, the run proceeds with the sealed cases that passed, and the printed "sealed n/5" line and 0138 say so (the "≥ 3 sealed" condition then reads NOT met for this run). Per-class denominators follow the key, so a class can have d = 0 (uncomputable) or d = 2. |
| R10-4 | What is "one repeat"? | The whole eight-case set is measured twice at the same prompt sha and model: run 1 is the first run at that sha (§10's first-run value); run 2, the repeat, is the current value printed beside it. Per case, the scorer prints caught in both / one / neither, as counts, labelled a repeatability observation, not a metric (§10 withdraws "reviewer disagreement"). |
| R10-5 | How is "data, design and results before any narrative" engineered? | Two phases in one reviewer session. Phase A's kit holds design, data and results only; the reviewer writes `notes.json`. Only after phase A exits does the launcher copy the narrative (report and claims) into the kit and resume the same session for phase B, which writes `review.json`. The envelope records both phases. If CP5's rehearsal shows the resume cannot be driven, phase B is a fresh session that reads its own phase-A `notes.json` first; the choice is recorded in 0136 before any sealed case is built, and the prompt sha is fixed after it. |
| R10-5a | Which phase-B path is the default? | The resume is the only path built in round 1. The fresh-session alternative is pre-decided as the fallback, but it is not implemented unless CP5.6's rehearsal shows the resume cannot be driven; then a fix round replaces the resume, and 0136 records which ran. Phase B's session id is read from phase B's own init event, never assumed. |
| R10-6 | Must a plant pass GARS's deterministic gates? | Yes, **all of the gates a real project passes before `REVIEWING`, with no omission**: stage 01's design check; row 8's catalogue detectors for the files present; §7.5's wrapper exit gates (the `<GROUP>_REP<N>` presence check through `wrapperlib.samplesheet_group_rep_tokens`, `wrapperlib.py:511-525` at this record's base, decision 0035, against the count-matrix header and the de_results identifiers; the count-matrix header content check; the `de_results` identifier gate); stage 03's `verify` (the approval record's sha256 equals the approved plan's, and every declared output exists and is non-empty, `stage03_analysis.py:20` at this record's base); and row 7's renderer emitting the report. Each gate is called by import from `gars/_system/`, read-only, in a scratch copy of the project. A gate that cannot run outside a real project (stage 03's protected store) is driven with that record supplied as data in the scratch copy; if it still cannot run, the producer writes a restatement plus a drift test driving it and the real function on the same inputs. A case any gate refuses is refused by the builder, with the gate named in the private key, never in the case and never on the door's screen. The gate NAMES (names only, no rule text) are part of the sealer's and the auditor's inputs, so no plant is built into a gate by accident. The reviewer is measured on what deterministic code lets through. |
| R10-7 | Is every plant scientifically honest? | Each plant carries exactly one flaw of its class that a competent statistician would call real, detectable from the case's own files alone (no network, no outside knowledge); each clean project carries none. A second fresh Codex context audits all eight cases before sealing is pinned (CP7.4); a "no" on a sealed case gets a correction round by the sealer, a "no" on a producer case gets a Codex fix round. |
| R10-8 | Where does each role run? | The producer and the measured reviewer run on the build node, each under its own OS account. The sealed sources (plants, their `expected.json`, generator, the key file) never leave the owner's workstation and are opened only through the door. Only neutral built cases and the manifest reach the reviewer account's measurement folders; nothing measured reaches the producer account. |
| R10-9 | How does the harness relate to row 9's? | Reuse by import from `evals/review-faults/`, which row 10 never edits. Every science module has a unique name (`bio_*.py`), and row 9's modules are loaded through `importlib.util.spec_from_file_location` under private aliases, so one test process can hold both harnesses. Two things are restated rather than imported, each with a drift test: the record-validity rules (an adapter that runs row 9's `invalid_reasons` on a row-9-shaped view of the science record, plus the science-only rules), and the oracle's file pre-normalisation (strip one `./` and one `project/`; a `repo/`-prefixed science finding never matches). |
| R10-10 | What does the public README row say? | The public cell stays `unmeasured` (§10, §21 Q9: `independent_context` seals are development evidence only). One pointer is added beside it, as row 9's R9-G shape: "development evidence, science (sealed n/5 <seal types as the run file records them>, partial set): `<run file>`". The seal count and type come from the run file, never typed. |
| R10-11 | Record numbers | 0135 this record · 0136 the producer's harness record · 0137 the delegated approval of protected additions · 0138 the seal, the honesty audit, the first measured run and the repeat, in one record · 0139 held for a harness follow-up (0125's role) and otherwise unused. |

Three things in the lane plan's table are restated here, and nothing else is changed: R10-8 names the roles and machines by what they are rather than by their host and account names, because no committed file names a machine or an account; R10-6's two line citations are moved to where the functions sit at this record's base; and R10-3's "NOTES" is explained in the Context above.

## What this does not close

- A reviewer that guesses it is being measured from a case's style.
- The sealer, the auditor and the producer are all Codex contexts (the reviewer is Claude).
- `independent_context` seals are development evidence only; public claims need `external_human_seal`.
- One plant per class makes a per-class rate 0/1 or 1/1 (0/2 to 2/2 across the repeat), a thin sample stated as such.
- The sealed outcomes are checkable by hash only, so a stranger recomputes the producer's four of eight outcomes from the repository.
- The five unplanted classes (`wrong-reference-in-params`, `fabricated-citation`, `p-value-edited-in-report`, `missing-n2-limitation`, `contradictory-literature-omitted`).
- §17's science clause, which reads NOT met (partial set) until the at-risk tier completes ten plants and five clean projects.
- R-093's code half: `launch_role()` still returns producer.

## Test

0136's tests and 0138's run files.

## Status

Standing.
These are scope rulings only; nothing is implemented by this record.
The implementation is 0136's, the approval of protected additions is 0137's, and the measurement is 0138's.

## Date

2026-09-25

## Appendix: THE SEALED INTERFACE

This is the case format; the producer implements exactly it, and the sealer writes to it after the merge, against the merged head's own base trees.

- A case folder is `P<nn>/` (plant) or `C<nn>/` (clean) with `plant.diff` (a unified diff against the base project tree the merged head's `bio_generate_base.py` writes for `base_project` and `base_seed`; an empty diff is legal only for a clean case) and `expected.json`.
- `expected.json`, all required: `id`; `kind` (`plant` | `clean`); `class` (a science class id, or null for clean); `base_project` (a base id the merged head's `bio_generate_base.py` knows; the sealer receives the list, the generated trees and their seeds as data); `base_seed` (int); `base_sha` (the full 40-hex harness base); `seal_type` (`unsealed` | `independent_context` | `external_human_seal`); `requirement_ids`; for a plant `match_any` = a non-empty list of `{"file": <case-relative path>, "line_start": int, "line_end": int, "mode": "file_lines" | "file"}` and `min_severity` (default `MINOR`).
  Optional: `mask_literals`.
- Every `file` in `match_any` is relative to the case's `project/` folder (e.g. `1-design/samples.csv`, `3-results/de_results.csv`, `4-report/report.md`), following the builder's layout map (which base file lands at which case path); line numbers are in the post-plant file as the builder lays it out.
- Files the builder renders rather than copies (`4-report/report.md`, rendered by row 7's renderer) may be matched in `mode: file`; a `file_lines` entry on a rendered file is allowed only when the sealer has seen its own built case through the door's `validate`, whose built copy stays inside the seal folder.
- A plant has exactly one flaw of its class; a clean case has none.
  The flaw is detectable by a careful reviewer from the case's own files alone.
  The flaw is real under the class definition and §14's assay rules, and the plant passes every deterministic gate the builder runs (R10-6).
- A plant never names its class, a flaw, a fault, a plant, a seal or a harness in any byte it adds.
- The reviewer-facing layout after building: `project/1-design/` (the design: `samples.csv`, `_config/<assay>.yaml`, the approved plan and its approval record), `project/2-data/` (`files.csv`, a count or peak matrix summary), `project/3-results/` (`de_results.csv`, `manifest.json`, QC summary), `project/4-report/` (`report.md` rendered by row 7's renderer, `snapshot.json`); `4-report/` is withheld until phase B.
- The sealer's inputs (copied by the door at `launch`, each sha256 recorded): the merged head's `INTERFACE.md`, `classes.json`, the generated base trees under `input/bases/<base id>/` with their seeds, the layout map, and the list of gate names from R10-6 (names only).
- Seal folder layout (the sealer's): `plants/P03/`, `P04/`, `P05/`, `clean/C03/` (and `P06`/`P07`/`C04` only for a replacement), `generator/` (seeded scripts), `SEAL.md` (line 1 `fingerprint <sha256 over the sorted (relative path, sha256) list of plants/ and clean/>`, then date, seal type, counts per class; no content description), `BLINDNESS.md`, `tmp/`.
- Case ids: the producer writes `P01`, `P02`, `C01`, `C02`; the sealer writes `P03`–`P05` and `C03` (replacements `P06`, `P07`, `C04`); `P90` and `C90` are reserved for Glitch's rehearsal and never enter a measured run; the ids are assigned to classes only inside `expected.json`.
