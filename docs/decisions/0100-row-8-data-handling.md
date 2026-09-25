---
date: 2026-09-24
status: standing
kind: decision
touches:
  - gars/_references/data_policy.tsv
  - gars/_system/venue_policy.py
  - gars/_system/stage00_register.py
  - gars/_system/executorlib.py
symptoms:
  - a non-public dataset ingested with no recorded route
---
# Row 8: the data-handling record

Decided by Glitch under the owner's standing delegation of 23 Sep 2026.
This record is the spec's data-handling decision (§6.1, R-063), and it records the route each data class may take.

## Context

Spec §6.1 (R-063) requires the data-handling decision, recorded before any non-public dataset is ingested, under the filename `0001-data-handling.md`.
`0001` is `0001-layered-context-and-stage-ownership.md` (2026-08-08), and 0044 said this record takes "the next free number".
At the time of writing, 0072–0099 are reserved by other lanes (row 9 0072–0074, row 7 0075–0079, exit runs 0080–0084, row 3 0085–0089, row 2 0090–0094, row 6 0095–0099), so 0100 is the first number free of every reservation.
Every spec citation of `docs/decisions/0001` for data handling (§6.1, §6.2, §13.2, §13.6, row 13) reads as this record.
This answers D-3.

## Decision

### Who decided

Decided by Glitch under the owner's standing delegation of 23 Sep 2026.
No sentence in this record is attributed to the owner.
The spec's own line (§6.1) stands: "This guideline does not assert what any regulation requires."
This record likewise asserts no regulatory requirement.
It records a restrictive route consistent with the spec's defaults: `pilot_internal` on `slurm` is permitted only with a non-`none` `agreement_ref`, tying §6.2's "internal testing only until an agreement is recorded" to the dataset's own recorded agreement.
**Loosening any route below needs a new record carrying the owner's own words.**

### §21 Q4

Pilot-1 data is treated as `deidentified_under_agreement`, and only `public` enters a hosted-model prompt (the spec default, §21 Q4).

### The route table

This is the exit's "data route recorded 3/3".
`gars/_references/data_policy.tsv` carries the same rows, and a drift test binds them.

| data_class | permitted_backends (execution) | storage venues | enters a hosted-model prompt | backup second destination | retention / deletion | expiry | approval (R-074) |
|---|---|---|---|---|---|---|---|
| `public` | local (purpose `fixture` only), homelab (`fixture`, `internal`, `pilot_internal`), slurm (`fixture`, `internal`; `pilot_internal` only with a non-`none` `agreement_ref`) | any | yes | permitted: an encrypted copy at a destination the owner configures (none configured; HARDWARE.md stays "to be recorded") | per project; no deletion rule | none | none |
| `deidentified_under_agreement` | slurm only (`internal`; `pilot_internal` only with a non-`none` `agreement_ref`), under the institution's terms; `pilot_external`/`commercial` refused everywhere until a cloud/agreement record exists | institutional/HPC storage only; never local, never the homelab (R-136 not satisfied) | no: sample-level metadata and data never enter a prompt | none off institutional storage | delete derived copies outside institutional storage at project close; the agreement's own terms govern the rest | the agreement's expiry, recorded as `expiry` on the dataset row; no expiry recorded = refused | any send to a third party |
| `identifiable` | none: every run is refused | none | no | none | not held | — | would need one per run (R-074); no route exists in v0.1 |

### Venue rules carried from §6.2

- `local` accepts purpose `fixture` only, and refuses FASTQ inputs and any request above 8 GB memory (§6.2, spec line 144: "fixtures only; refused for FASTQ inputs or > 8 GB memory").
  The lane's delegated reading of §6.2, made under the same delegation: "§6.2's `local` row allows "small fixtures", and its FASTQ refusal protects non-fixture data."
  So on `local` the FASTQ clause does not apply when the dataset row is `data_class` = `public` AND `purpose` = `fixture`; every other dataset keeps the literal refusal.
  No size threshold is set: §6.2 states none.
- `fixture` is permitted on every venue for `public` data, so a test fixture or a bench workload runs anywhere without a policy exception.
- `slurm` is "internal testing only until an agreement is recorded", so `pilot_external` and `commercial` are refused there (the §21 Q5 default).
- `cloud` is out of v0.1: no priced row exists (§2.2).
- Memory, the lane's delegated reading: §6.2's "8 GB" is read as 8 GiB (8 × 1024³ bytes), the unit of Slurm's `--mem` suffix `G`.
  On `local`, a declared request above 8 GiB is refused.
  A missing declaration is allowed only for a `public`/`fixture` dataset, and refused (`resource_undeclared`) for any other.
  Any other pair is already refused on `local` by the route clause; the rule states it so no reader infers a gap.
- The venue is inferred, not attested.
  The venue is derived from the descriptor that actually executes (`venue_of`), not from a host attestation.
  Only the homelab is host-marked.
  A Slurm-described run executed on a host that is not the HPC (for example an approved `Runs: login-node (user-requested)` analysis run from a workstation) is graded `slurm`.

## What this does not close

- Enforcement of "never enters a hosted-model prompt" inside the agent harness (R-061 `test_metadata_sync_refused.py`, and a guard read-deny on non-public `00_data/`) is NOT met here.
  A delegated ruling of 23 Sep 2026 sends it to a row 4 addendum lane that lands before row 13 ingests pilot data.
- Row 13's operating mode under this record is not decided here.
  The producer model may not read pilot-1 sample-level metadata, so row 13 must plan aggregate-only tool output or a reclassification in the owner's words.
- The second backup destination is not configured: it needs the owner's configuration and credentials.
- No institutional agreement, IRB, DUA or BAA content is recorded or assessed here.
- Whether claim rows derived from a `deidentified_under_agreement` dataset take that dataset's class for R-136 is not ruled.
  Row 5's authoritative PostgreSQL, the claims database, is on the homelab, where this table stores no deidentified data.
  Until a record rules on it, row 13 must not write claims derived from pilot-1 data to the homelab database.
- `cloud` has no route.

## Test

`gars/tests/test_data_route.py` checks the three classes × every column above, present and equal to `gars/_references/data_policy.tsv`, and prints `data route recorded: 3/3`.
A cell changed on either side turns it red.
`gars/tests/test_venue_policy.py` covers the full purpose × class × venue grid.
Both tests are built by row 8's step B on top of this record.

## Status

standing

Decided by Glitch under the owner's standing delegation of 23 Sep 2026.
This record decides the route; its enforcement (`data_policy.tsv`, `venue_policy.py`, the `finalize` check and the executor's venue refusal) is row 8 step B's implementation and is not part of this record.

## Date

2026-09-24
