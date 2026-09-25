---
date: 2026-09-24
status: standing
kind: decision
touches:
  - scripts/unit_economics.py
  - scripts/rerun_diff.py
  - scripts/session_turns.py
  - docs/pilot/
  - tests/test_unit_economics.py
  - tests/test_rerun_diff.py
  - tests/test_session_turns.py
  - tests/pilot_red_on_fault.py
  - tests/fixtures/pilot/
  - README.md
  - DEVELOPMENT.md
  - docs/implementation/row_13_change_report.md
symptoms:
  - a cost typed into the pilot log or bench sheet
  - verification minutes counted in a stage and again on their own line
  - a margin printed with no price
  - a gene id, sample name or path printed in a re-run diff
  - a tool_result or isMeta record counted as a human turn
  - a human turn outside every logged span silently absorbed
---
# Row 13 step A: the pilot instruments

## Context

§18 row 13 is a timed pilot 1 on the DE stage of the author's own analysis, one re-run of that
stage from its manifest, and a generated unit-economics sheet; its exit is "human-touch minutes
measured; re-run diff explained". The governing requirements are R-190 (pilot dimensions bound
to log columns), R-193 (a sheet with no hand-entered cost cell, margin stated, no price before
the pilot is timed), R-153 (human-touch events logged with timestamps and reason codes), §11.3
(every ratio printed with numerator and denominator, `0/0` as `uncomputable`) and §16.4 (the
unmetered share stated in every cost report).

The row is split. **Step A** (this record) builds the instruments that read the pilot's
artifacts and proves them on synthetic fixtures. **Step B** builds the closed-project doors,
the pilot-log writer and `bring_home`; it is a separate brief and is not built here.

Everything below — D1, D2, D3, D4, D4b, D7 and ruling L1 — is **the lane's specification,
decided under the owner's standing delegation of 23 Sep 2026**. It is not the owner's ruling
and is not attributed to the owner. Ruling L1 was answered by the lane on 24 Sep 2026 after the
first producer pass raised it.

**Deviation — the producer and the review.** This step was produced by a headless Claude Code
context (Claude Opus 5.5) because the lane's usual producer was unavailable, and it is reviewed
by a separate fresh Claude Code context on the same model. Producer and reviewer are therefore
the same model family: the review's independence rests on a fresh context and a blind review
kit, not on model diversity.

## Decision

**D1 — the pilot log's format** (the writer is step B). `pilot1_log.csv` has exactly the §19
columns `ts,stage,actor,action,reason_code,minutes`, preceded by one header comment
`# gars-pilot-log v1 nonce=<32 hex>` (lowercase hex). `ts` is UTC ISO-8601 to the second with
`Z`; `minutes` has exactly two decimals and is computed by the writer from clock readings, never
typed. The stage, actor, action and reason_code vocabularies and the column list are defined
once, in [`docs/pilot/pilot_log_vocabulary.json`](../pilot/pilot_log_vocabulary.json), which
both step-A readers load at run time; step B embeds it in the writer with a drift test.
**The log has no free-text column**, so it cannot carry a sample name, a gene or a note; a
seventh column is refused, because it would be a place to type a cost.

**D2 — the baseline.** `pilot1_baseline.csv`, columns `stage,action,hours,basis`,
`basis ∈ {measured_prior, estimate}`, the same vocabularies. Written by the owner before the
session and kept privately.

**D3 — `scripts/unit_economics.py`.** Inputs: the log, the baseline, row 8B's bench CSV, the
private `owner_inputs.json` and the bring-home quantities file; outputs `unit_economics.csv`
and `.md`, with each input's SHA-256 (by role, never by path) at the head. Identical inputs give
byte-identical outputs.

- `owner_inputs.json` is schema-closed: `hourly_value_usd` (number), `hourly_value_source`,
  `project_definition` (strings, hashed, never printed), `liability` (only `unpriced`),
  `price_usd` (only `null`). Fixtures use `hourly_value_usd = 1`.
- Quantities are never typed. Only three bring-home line shapes are read (documented and tested
  in [`docs/pilot/README.md`](../pilot/README.md)); every other line is counted and ignored, and
  the sheet prints `quantities: graded <k> of <n> lines`. A conflicting repeat is refused; a
  missing `samples_in_design` makes every per-sample figure `uncomputable`, never zero.
- Hours by stage are human minutes excluding `review_output`/`verify_result`; verification hours
  are those two actions on their own line. Each human minute lands in exactly one of the two.
- Compute by backend comes from the bench row: every accepted row is `unmetered` under
  `owned_hardware` or `institutional_allocation`, printed with its CPU-hour quantity; a backend
  with no row is `unmeasured`. The agent is `unmetered (subscription)` with its minutes; the
  liability is `unpriced`; the cost line is `cost: $<x> + unmetered compute + unmetered agent +
  unpriced liability`; the unmetered share is its own line (§16.4); the margin is
  `uncomputable: no price (R-193)`.
- Time saved (baseline − human hours, per stage and total), interventions (human rows) and row
  coverage per actor are printed; a stage with no baseline row is `unmeasured`.
- The M4 cross-check line comes from the session_turns quantity; `o > 0` prints
  `DISCREPANCY: <o> human turns outside any logged span`, and no minute changes.
- Refused with a named reason, writing nothing: a seventh log column, an unknown or missing
  inputs key, a typed liability, a non-null price, and a bench row whose derived fields do not
  recompute (numeric cost, other basis, status not `COMPLETED`, non-numeric counts).
- **The bench binding is to 8B's plan, not 8B's code.** `benchmarks/backend_bench.csv` does not
  exist at this row's parent; the sheet reads it by header name only, and the binding is
  re-checked when step B rebases onto 8B.

**D4 — `scripts/rerun_diff.py`.** Reads row 6's `comparison.json` (its shape as the lane read
it at row 6's build head; `scripts/rerun_check.py` does not exist at this row's parent), locates
the original and each re-run stage folder, takes the one `de_results.csv` artifact per run,
verifies both tables' SHA-256 against the record, and prints one block of aggregates per run in
`runs` order. It never prints a gene identifier, a sample name, a path or `reason` text, and
changes no tolerance (§8.4 needs a cause and a second re-run). **Substitution named:** the DE
table has no Wald `stat` column, so D4's `spearman stat` is computed as Spearman's rank
correlation of `log2FoldChange` over matched genes and printed as `spearman log2FoldChange`.
`NA`/empty `padj` is counted as `na_padj`; genes in one table only are counted, never printed.

**D4b — `scripts/session_turns.py` and ruling L1.** Counts human turns (`type == "user"`, not
`isMeta`, content not all `tool_result`), the session wall span and the agent-active span, and
whether each human turn falls inside a `human` span of the stage; prints numbers only. A record
that does not classify — another type, a missing or unparseable timestamp, `tool_result` mixed
with other content, a blank line — exits 2; none is skipped. Per **ruling L1 (the lane's)**,
`outside minutes` is the union of each outside turn's attention interval — from the latest
record strictly earlier in time to the turn, clipped to the part outside every human span of
the stage — rounded half-up to two decimals once. It is a **lower bound** on unlogged human
attention and is never added to or subtracted from any logged minute. Timestamps are parsed
without `datetime.fromisoformat`.

**D7 — where each result lives.**

| Artifact | Where | Public? |
|---|---|---|
| code, fixtures, tests, 0140, 0141, 0144 | GARS | yes (on the owner's push word) |
| 0142: baseline SHA-256, protocol, class/purpose/venue, "agreement ref recorded: yes/no", "expiry recorded: yes", the **salted** commitment `sha256(salt ‖ question file)` | GARS | yes (the owner's record) |
| 0143: human minutes and interventions per stage, agent/tool minutes, the M4 cross-check numbers and any discrepancy, `reproduction: k/n`, `rerun_diff` aggregates, "sheet generated privately, sha …", "no price published (R-193)", NOT-met list | GARS | yes (the owner's record) |
| `bring_home.txt`, `pilot1_baseline.csv`, `owner_inputs.json`, `contrast_salt.txt`, `unit_economics.*` | aegis `evidence/gars-pilot1/` | no |
| data, counts, design, DE tables, raw console, `comparison.json`, transcript, report | the cluster only | never |

Records 0141 to 0144 are reserved for this row's later steps; this step writes none of them.

## What this does not close

- **NOT met: the pilot.** No human-touch minute has been measured and no re-run diff has been
  explained on real data; every number here is a synthetic fixture.
- **NOT met: the writer and its actor binding** (`pilot_log.py`, the `--launched-by-dispatcher`
  token, the guard refusal, the machine-owned log folder) — step B.
- **NOT met: the closed-project doors** — step B.
- **NOT met: `bring_home`** (step B). The quantities interface is fixed here; its emitter is not.
- **NOT met: the real sheet** — generated privately after the pilot, never committed.
- **NOT met: the report**, **R-192's engagement terms**, and **any price** (R-193).
- **NOT met: a forgotten span with no human turn in it** (a manual step outside the agent
  session) is invisible to the session cross-check.
- **Unverified against the real producers:** the bench CSV binding (8B's plan) and the
  comparison shape (row 6's build head); both are re-checked when step B rebases. Real session
  transcripts may carry record kinds beyond `user` and `assistant`; they exit 2 until a later
  recorded ruling widens the closed set.
- Python 3.6.8 execution is not observed here: the scripts parse under
  `ast.parse(feature_version=(3, 6))` and run on the machine's Python 3.8.2.

## Test

`python3 tests/test_unit_economics.py`, `python3 tests/test_rerun_diff.py`,
`python3 tests/test_session_turns.py` (each prints its reserved `EXIT` line when green), and
`python3 tests/pilot_red_on_fault.py`, which plants eight faults in a scratch copy and requires
each to go red: a hand-typed cost accepted; verification counted twice; margin computed with no
price; a gene id printed by `rerun_diff`; a `tool_result` record counted as a human turn; a
discrepancy auto-corrected; a record silently skipped; a non-deterministic ordering. The three
modules are red at the parent `ef5c8af` (`ModuleNotFoundError`, an `ImportError`, naming each
script).

## Status

Standing. Implemented on `build/gars-row-13-pilot`; subject to the fresh-context review named
above. Not approved or merged by its producer. Row 13's exit is not met.

## Date

2026-09-24
