---
date: 2026-09-25
status: standing
kind: decision
touches:
  - evals/bio-faults/
  - gars/_references/prompts/review_faults_science.md
  - tests/test_bio_faults_core.py
  - tests/test_bio_faults_faults.py
  - docs/implementation/row_10_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - the required science prompt path fails the inherited code-only schema enum
  - required public manifest fields contain tokens forbidden by the science sweep
---
# Row 10 science review contracts and stopped construction

## Context

Round 1 starts from public main a77908474f2fc463f481a55f2d0c2ceeee8be660
plus the seed record 0135. Specification sections 7.2, 7.3, 7.5, 7.8, 10,
11.2, 11.3, 14, 17, row 10 of section 18 and section 21 Q3/Q9/Q10 govern
this lane. The gap assessment's Row 10 and D-11 explain the missing measurement
and partial-set threshold conflict. No round-1 review was supplied.

## Decision

**THE LANE'S SPECIFICATION: Glitch under the owner's standing delegation.**
Record 0135's rulings are Glitch's decisions under that delegation; none is
attributed to the owner. R10-5a states:

> The resume is the only path built in round 1.

Resume is the specified phase-B mechanism. Neither it nor a fresh-session
alternative has run here. No model has been run against any case.

The independent parts implemented here are the science vocabulary, row 9
imports under private aliases with safe canonical bare-name bindings, the
schema document with only the permitted differences, the pre-normalising
any-of oracle, and the two-phase prompt. The existing row 9 implementation,
all system gates, benchmarks and all base decision records remain unchanged.
The prompt is protected; this producer neither writes nor claims record 0137.
Records 0138 and 0139 remain reserved and unwritten.

Two incompatible contracts stop dependent implementation under the supplied
lane's explicit escalation rule. The inherited reviewer.prompt_path enum
admits only the code prompt, while the required science record names the
science prompt. The allowed schema differences do not include this enum.
Separately, the required public manifest's harness_commit key and prompt path
contain the forbidden substrings harness and fault. These are wholly new
manifest bytes, so row 9 item 15's unchanged-line exception cannot apply.
The change report records numbered options; no exception is silently chosen.
The builder, gate integration, base/case handoff, record adapter, launcher,
scorer and dependent release reader are not delivered as operational tools.

### Threat model

The supplied threat model is the acceptance contract, not a claim that this
partial implementation already establishes all its protections.

Covered by the required design: a measured reviewer, a model session in a kit,
must not learn class, plant/clean kind or the answer from folder names, filenames,
file stat, BRIEF.md or project bytes the plant did not add. Narrative must remain
absent until phase A ends. Model text must never supply the envelope. A reviewer
whose uid equals the producing account's uid on the same host must not be scored.
A vague finding must never count as caught: class, file, line interval and
severity must match an entry of match_any. The oracle tests establish the last
primitive; this round does not establish construction or launch protections.

Reads beyond the kit are enforced by the deployment sandbox. The harness must
bind the settings bytes used and run row 9's static audit. Its named residuals
in 0072 items 20–23 and 0125 apply unchanged, with 0127 and 0128's subsequent
data and session-placement rulings. Indirection, unparsed program text,
failed directory changes and audit-time symlink state remain sandbox concerns;
an ambiguous conditional read remains visible without becoming a hit. Import
identity and a stub stream demonstrate reuse, not sandbox efficacy.

Covered by the required reporting design: the harness reports only what it
measured. Invalid records, uncomputable zero denominators, a tampered key,
mixed prompts or models and the partial set remain visible, never silently
dropped. Invalid records count in all denominators, never caught or clean.
No scoring implementation or measured reporting is claimed in this round.

Not covered: inference from case style; sealer, auditor and producer all being
Codex contexts while the reviewer is Claude; independent_context seals being
development evidence only; the thin one-plant-per-class sample, with per-class
rates 0/1 or 1/1 (0/2 through 2/2 across the repeat); four sealed outcomes
checkable only by hash, so a stranger recomputes four of eight outcomes from
the repository; the five unplanted classes; R-093's code half, where
launch_role() still returns producer. These are the specified eventual set's
limitations, not a claim that an eight-case set exists in this commit.

## What this does not close

The two contract rulings, the rest of the implementation and its acceptance
remain open. No producer plant or clean case is published before construction
can satisfy its contract. The two required statistical rationales are therefore
not supplied. The sealer interface is not published as complete without its
base trees, fixed ids/seeds, layout and working gate integration.

Row 10 exit remains NOT met: sealed slots, honesty audit, deployment and a
scored first run and repeat remain later work. Section 17 cannot be met by the
partial set. No public README evidence cell is changed. Protected approval,
independent review, native Python 3.6, mode A and merge-result CI remain outside
this producer evidence. The change report states exact verification outcomes.

## Test

`tests/test_bio_faults_core.py`: vocabulary, schema drift, same-object imports,
a stub-stream audit, both import orders in one interpreter, oracle any-of grid,
pre-normalisation drift, repo-prefix rejection, shared alarms/ratios, prompt
constraints, and concrete witnesses for both stopped contracts.
`tests/test_bio_faults_faults.py`: seven isolated mutations, each with an unchanged
green control and a named red witness. These do not substitute for the remaining
lane acceptance or red-on-fault requirements. Full command summaries and direct
module wall times are recorded in the change report.

## Status

Standing partial implementation account, pending the two rulings and independent
review. This is not an approval, seal, measured run or row-exit claim.

## Date

2026-09-25
