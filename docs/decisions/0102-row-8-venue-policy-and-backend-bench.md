---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_references/data_policy.tsv
  - gars/_system/venue_policy.py
  - gars/_system/executorlib.py
  - gars/_system/stage00_register.py
  - gars/_system/wrapperlib.py
  - gars/_system/tools/registry.json
  - gars/00_initialize_project/CONTEXT.md
  - gars/02_bioinformatics/CONTEXT.md
  - gars/03_custom_analysis/CONTEXT.md
  - gars/tests/support.py
  - gars/tests/test_venue_policy.py
  - gars/tests/test_venue_policy_faults.py
  - gars/tests/test_data_route.py
  - gars/tests/test_approval_forgery.py
  - gars/tests/test_downstream_keys.py
  - gars/tests/test_execution_policy.py
  - gars/tests/test_lifecycle_executor.py
  - gars/tests/test_manifest_groups.py
  - gars/tests/test_stage03_execution.py
  - gars/tests/test_rerun_check.py
  - tests/run_tests.py
  - scripts/rerun_check.py
  - scripts/backend_bench.py
  - tests/test_backend_bench.py
  - benchmarks/backend_bench.csv
  - benchmarks/backend_bench/
  - docs/implementation/row_8_change_report.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - executor submission accepts datasets without a permitted data route
  - no instrument binds backend rows to retained measurement evidence
  - replay omits the agreement expiry required by finalize
---
# Row 8 step B: venue policy and backend bench

## Context

Starting commit: `1cce53614843646fee0de32100c1117ff45d80ab`.
This implements 0100 without changing that record or step A. The brief's
DELEGATED RULINGS were decided under the owner's standing delegation (23 Sep 2026).
No additional words are attributed to the owner. Implementation and verification
are recorded in `docs/implementation/row_8_change_report.md`.

The replay writer boundary remains unresolved: the brief requires expiry and
permitted_backends in replay's manifest input but limits wrapperlib to its venue
line. Prepare currently records neither additional field. The replay reader is
implemented, but the writer addition is stopped for the ruling in the report.
The complete step and its whole-suite gate are therefore NOT met.

## Decision

The route table in `gars/_references/data_policy.tsv` has exactly the three
classes and all eight columns. Its execution column serializes venue:purpose
pairs separated by a pipe. `none` means an empty route. Storage, backup,
retention, expiry and approval cells retain 0100's text. Exposure is yes/no.
An independent test parses 0100, binds every cell and prints the recorded count.
Slurm pilot_internal additionally requires a non-none agreement reference.

The full grid has five purposes in this order: fixture, internal,
pilot_internal, pilot_external, commercial. With a recorded agreement and a
future expiry, allowed cells are:

| Class | local | homelab | slurm |
|---|---|---|---|
| public | fixture | fixture, internal, pilot_internal | fixture, internal, pilot_internal |
| deidentified_under_agreement | none | none | internal, pilot_internal |
| identifiable | none | none | none |

Local memory above 8 GiB is refused. The interpretation was decided under the
owner's standing delegation (23 Sep 2026):

> §6.2's `local` row allows "small fixtures", and its FASTQ refusal protects non-fixture data.

The FASTQ exemption requires exactly data_class public AND dataset purpose
fixture, without trimming or case folding and with no size threshold. FASTQ
refusals accumulate independently of route and purpose refusals. This retains
the row-6 gap: a hand-forged dataset row outside the guarded verbs can assert
public/fixture. There is no environment, flag, file or test-mode bypass.

### Homelab venue and executed evidence

There are still only the built-in local and slurm backends. `venue_of` returns
slurm for slurm and otherwise tests the module constant's operator-owned marker.
The operator creates the marker using sudo; agent accounts have none. Its
location is assembled in code from the filesystem separator and components,
without an environment override. Tests patch the constant to scratch files.
Finalize on a marked host accepts public only (`storage_venue_not_permitted`).

Venue comes from the descriptor submit actually receives, or load(config_root)
when no descriptor was supplied. On stage 03 it is captured before the approved
login-node swap. A login-node analysis in a Slurm workspace thus records
executor local and venue slurm. This intended difference follows ruling Q-R1,
decided under the owner's standing delegation (23 Sep 2026). Custom descriptor
names still refuse R-075 before policy; check_executor_config is unchanged.

The residual remains: venue is inferred from the descriptor, not attested by
the host. The operator marker identifies only homelab. Another host running a
Slurm-described login-node analysis is graded slurm.

### Backend instrument

W1 is 24 gzip blobs, w1-01.bin.gz through w1-24.bin.gz, each with 8 MiB of
incompressible seeded bytes. SHAKE-256 expands the fixed seed and file index;
explicit stored DEFLATE blocks and a fixed gzip header remove compression-library
and timestamp differences between venues. The workload digest hashes the ordered
filename and file-SHA-256 listing. W1 measures GARS's integrity-and-hash path,
not FASTQ analysis and not per-sample biological cost. Samples means blobs.

Run refuses an existing output directory and creates its own public/fixture
project, built-in executor descriptor and rnaseq_bulk config with compute.mem 2G.
It generates a stage-02 script using header_lines, records every blob and config
with write_reproducibility, then submits one job through the real submit door.
Neither config_holds nor prepared_key is modified. The dataset writer's second
production caller is this fresh bench project: its fixed public/fixture constants
cannot widen an existing dataset, and stage 00 cannot derive FASTQ units from
these blobs. Run writes submitted.json and measures nothing.

The worker calls integrity.check_many(paths, "full"), hashes each blob and writes
its wall time, RUSAGE_SELF CPU time and maximum RSS. RSS is normalized from bytes
on macOS and KiB on Linux. Collect polls executor status with a bounded timeout;
timeout writes no evidence. On Slurm it reads Submit, Start, End, Elapsed,
TotalCPU, MaxRSS and State, querying the batch step explicitly for RSS. Queue
wait is Start minus Submit, or zero for local/homelab. Failed jobs produce FAILED
evidence, with unknown timing fields null if the worker could not write them;
no retry is performed, and append requires COMPLETED.

The evidence allowlist is backend, venue, status, workload_id, workload_sha256,
samples, wall_s, cpu_s, max_rss_mb, queue_wait_s, python_version, gars_commit,
measured_at, cost_usd_per_sample and cost_basis. Values have closed vocabularies,
numeric checks and version/hash/UTC syntax checks. No hostname, username, path,
partition or IP field is retained. The benchmark backend label distinguishes
local, homelab and slurm; it does not add an executor backend.

Append validates the workload and derived workload/sample/cost fields, retains
the exact evidence bytes under their SHA-256 name and appends one CSV row.
Every row regenerates from evidence; an edited CSV wall_s, missing evidence or
changed evidence bytes fails. An existing backend/workload requires --supersede
with the current evidence SHA; supersession appends and preserves history.
Source-clock truth remains a residual; arbitrary timing fabrication in a new
source evidence file is not independently attested.

Costs are unmetered: owned_hardware for local/homelab and
institutional_allocation for slurm. These are R-193 inputs, not prices. The CSV
is header only. No venue was benchmarked here; all three rows arrive later from
their actual venues. Glitch and the owner bring the homelab and slurm rows home.

## R-042

The brief's changes were decided under the owner's standing delegation (23 Sep 2026).

- Stage-02 policy preflight is inside the records lock, immediately after the
  last R-152 retry_policy_unresolved refusal and before record construction and
  reservation. Existing config_holds, prepared-key, validate, R-076 and retry
  refusals remain first.
- Stage-03 policy preflight is after approval, descriptor validation and the
  R-077/R-076 prior-job block, immediately before script_hash and launcher
  generation. Validation additionally checks the pre-swap descriptor, retaining
  the closed backend enum even for a login-node plan.
- The invariant: a policy refusal happens before the reservation (`<key>.json`), the launcher write, `ANALYSIS_SUBMISSIONS` and `_submit_once`.
  Pre-existing side effects remain: the records folder and its .lock; the
  analysis run folder and .submission.lock; and, only on an analysis resubmit,
  the existing _scheduler_status query required by R-077/R-076. Tests inspect
  job JSON, launchers, submission lines and scheduler calls, never an empty tree.
- Both submission dict literals gain venue beside executor. All 45 pinned
  executor source strings remain byte-identical and first-occurring. BUILTINS,
  validate and every existing local-name comparison remain unchanged. No fault
  harness expectation was changed.
- Group 11's venue line calls venue_of(load(config_root)). Its residual is:
  "group 11 records the prepare-time venue; the policy grades the executed one".
  Both values remain available in manifest and submission evidence.
- Finalize appends permitted_backends, provider_exposure, retention and expiry.
  Narrowing is permitted, widening is refused, provider exposure is derived,
  agreement expiry is required and identifiable has no route. Changed base
  classification is refused before the identifiable refusal. Re-finalize with
  different route values refuses dataset_classification_locked.
- The one sanctioned rewrite of an existing dataset.tsv is migration of a
  row-6-only row with the same base values, appending route columns while
  preserving the old serialized fields. Policy uses class defaults for old
  rows and requires absent expiry only for agreement data. The row stays 0444.
- No memory declaration allows local only for exact public/fixture and allows
  homelab/slurm. Unparseable declarations refuse resource_unparseable. No
  samplesheet input with fastq_1/fastq_2 means no FASTQ. A missing listed FASTQ
  refuses input_missing. Stage 02 reads compute.mem from the assay config;
  stage 03 reads its script's SBATCH memory declaration and has artifact inputs.
- The delegated local reading, verbatim: "§6.2's `local` row allows "small fixtures", and its FASTQ refusal protects non-fixture data".
  Only exact public/fixture is exempt; hand-forged dataset.tsv remains the
  row-6 guarded-session residual. The bench uses the shared writer only in a
  new output project; its fixed class/purpose cannot widen another dataset.
- Replay passes recorded expiry and permitted_backends to finalize and compares
  recorded classification/route values with the original and replayed row.
  Differences produce replay_dataset_mismatch. Public legacy manifests can use
  their class-default route and no expiry. Private manifests without recorded
  route fields are refused. The required writer addition is still stopped.

Every existing expectation change is named below; assertions remain unchanged.

| Fixture or helper | Old | New | Requirement |
|---|---|---|---|
| support.write_fixture_dataset | absent helper | finalize-equivalent 0444 row, same-value no-op | R-060/R-062 |
| tests/run_tests.py completed_fixture_submission | unclassified direct submit | shared public/fixture row before submit, inherited by all callers including unchanged planted-defect tests | R-062 |
| tests/run_tests.py completed_fixture_submission config | template or class memory up to 96G | compute.mem 2G before manifest hashing | R-064 |
| test_lifecycle_executor.prepared | unclassified fixture | shared public/fixture row; inherited by failure_classification, lifecycle_cancel, no_false_completion and execution_policy | R-062 |
| test_approval_forgery.setUp | unclassified analysis fixture | shared public/fixture row | R-062 |
| test_stage03_execution.setUp | unclassified analysis fixture | shared public/fixture row | R-062 |
| test_downstream_keys.check_wrapper | unclassified downstream fixture | shared public/fixture row | R-062 |
| test_execution_policy direct collect fixture | unclassified completed job | shared public/fixture row | R-062 |
| test_manifest_groups.setUp | class config mem 32G on local | fixture mem 2G before preparation; real finalize already supplies classification | R-064 |
| test_rerun_check.setUp | agreement class without expiry on local | future expiry, Slurm stub, fixture-patched marker constant | R-060/R-062 |
| scripts/rerun_check.py | only class/purpose/agreement replayed | recorded expiry and permitted backends passed and compared; writer dependency remains open | R-042/R-060 |

The executorlib_resume out-of-door fixture still refuses R-073 before policy;
it requires no helper. Lifecycle_faults inherits builders from its copied test
tree and changes no pinned string or assertion. Synthetic FASTQ fixtures pass
through the on-disk public/fixture row; collect never submits and needs no
special exemption transport.

## Threat model

Covered: an agent session running the typed tools, stage helpers, wrapper verbs and executor CLI; any code path in this repository. It must not be able to:
  - submit, by either submit path, a run whose class/venue/purpose the route table does not permit for the descriptor that actually executes (an explicit `descriptor=ex.LOCAL` included; the login-node swap excepted, which is graded on the descriptor before the swap, ruling Q-R1), or on an unclassified, expired or identifiable dataset;
  - submit FASTQ inputs on `local` for any dataset other than exactly `public`/`fixture` (R2-Q1), or declare a memory request above 8 GiB on `local`, or run on `local` with no memory declaration for any dataset other than `public`/`fixture`;
  - widen a dataset's permitted backends, or change its class, by re-running finalize;
  - select the `homelab` venue on a host without the machine-owned marker;
  - add a bench row that does not regenerate from its evidence, or evidence carrying a host name, path or user.
Not covered, named as residual in 0102: a session with sudo on the homelab (can create the marker; agent accounts have none); edits to `_system/`, `_references/` or `dataset.tsv` outside the verbs (the guard and 0444 are that line; row 6's plan adds a guard `READ_ONLY` entry for `dataset.tsv`, so the residual is re-derived at `B_BASE` and stated as it then stands: a process outside the guarded session, or one that deletes and rewrites the file, is not stopped by the guard); what a model reads in its own context (0100 names it); the truth of a measured timing beyond the machine's own clocks; memory actually used beyond the declared request, or used by a `public`/`fixture` run that declares none; FASTQ inputs listed outside `fastq_1`/`fastq_2` (a `fastq_dir`-style samplesheet), where only the route clause refuses (review NOTE-2); the venue being inferred from the descriptor rather than attested by the host (0100).

The base's existing dataset READ_ONLY entry and settings denies were verified by
row 6's unchanged test. They protect guarded tool calls, not another process or
an unseen delete-and-rewrite operation. This implementation does not strengthen
that boundary.

## What this does not close

- NOT met: the writer boundary ruling and the complete passing suite for step B.
- NOT met: all three measured backend rows, including the Mac local row and the
  homelab and Slurm rows brought home later by Glitch and the owner.
- NOT met: R-193 priced unit economics; unmetered inputs are not prices.
- NOT met: per-sample cost of real FASTQ analyses; row 13's sacct actuals supply it.
- NOT met: cloud; R-061 and prompt-exposure enforcement from 0100; the second
  backup destination; any institutional agreement.
- NOT met: actual Python 3.6.8 execution, real Slurm accounting and real venue
  timing evidence. Syntax and synthetic controls do not establish those facts.
- NOT met: Docker-backed database classes from rows 5 and 7 on this host.
- NOT met: independent review, protected-change approval, merge or row 8 exit.
  Records 0103 and 0104 belong to Glitch and are unchanged.

## Test

`python3 gars/tests/test_venue_policy.py`, `python3 gars/tests/test_data_route.py`,
`python3 gars/tests/test_venue_policy_faults.py`, `python3 tests/test_backend_bench.py`.
The report records all required commands, parent import failures, the parent's
behavioral acceptance of private data on local, and disposable fault outcomes.
No benchmark row or sealed catch-rate measurement is claimed.

## Status

Standing implementation record with replay completion stopped for the explicit
boundary ruling. This is not approval, merge authorization or a completed row.

## Date

2026-09-25


## Addendum — retry round B1, 2026-09-25

Starting commit: `efbe369003ea21fb211e7cdabb92d83eccdf354d`.
The retry rulings were decided under the owner's standing delegation (23 Sep 2026).
Ruling 7 selects option (a) of round 1's replay-fields question. It authorizes
exactly two additional entries in `prepare_manifest_facts`, taken from the
registered dataset row: `expiry` and `permitted_backends`. Missing source values
remain missing; collect preserves the recorded prepare values. This answers the
writer-boundary ruling above; the historical stopped-status account remains
unchanged. The retry verification is in `docs/implementation/row_8_change_report.md`.

### R-042

Under R-042, the manifest gains two recorded facts; none removed. Group 11's field list in
`gars/_references/manifest_schema.json` names both facts, and
`gars/_system/manifest_check.py` checks their presence using its existing
placeholder rules and the dataset's literal `none`. Group numbering, predicates,
required-group denominators and idempotency formulas are unchanged. Historical
public manifests that lack both fields retain their prior completeness and
replay behavior; a present null or placeholder is not substituted with a default.

`scripts/rerun_check.py` refuses a deidentified_under_agreement manifest lacking
either field with `manifest_predates_expiry_recording`, before generic
completeness grading and before any replay output directory or comparison is
created. Direct replay binding uses the same check. Prepare and complete a new
original to record missing facts; do not repair historical evidence from today's
dataset row. Recorded route values still pass through round 1's comparison with
the dataset, producing `replay_dataset_mismatch` on drift, and through real
finalize on replay. Public legacy replay retains its existing class-default
route and absent-expiry handling.

`gars/tests/test_rerun_check.py` adds capture/preservation/schema assertions,
agreement replay 2/2, missing-field refusal before execution, each recorded-field
mismatch, and public/fixture replay 2/2 with both historical fields absent. The
existing replay and manifest assertions are retained. The historical-fixture
variant extends the existing RNASEQ replay helper without changing its normal
callers. The named old-manifest fault disables the new refusal: its test goes
red on all three missing-field combinations. Removing the writer entries and
removing public legacy fallback also make their respective tests red.

Ruling 6's source spelling correction changes one launcher glob and four
embedded script shebang strings in `gars/tests/test_venue_policy.py` and
`scripts/backend_bench.py`. Path components are joined at runtime. Generated
script bytes and the glob's meaning are unchanged; no policy, scheduler,
workload or test assertion is weakened. README and DEVELOPMENT change only the
three current suite-count claims, from 603 to 607, after the count gate reports
the four new regression tests.

### What this does not close

No backend was measured: all three rows remain NOT met, and the CSV stays header
only. R-193 priced economics, real FASTQ costs, cloud, R-061/prompt enforcement,
second backup destination and institutional agreements remain NOT met. Actual
Python 3.6.8, live Slurm accounting, live resource measurements and the rows 5/7
Docker database classes remain unverified here. The existing threat-model
residuals stand. Independent review, protected approval, merge and row 8's exit
are not claimed. Records 0100, 0101, 0103 and 0104 remain unchanged.
