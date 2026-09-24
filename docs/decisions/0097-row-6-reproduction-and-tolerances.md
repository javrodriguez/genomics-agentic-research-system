---
date: 2026-09-24
status: standing
kind: decision
touches:
  - scripts/rerun_check.py
  - gars/_references/tolerances.yaml
  - gars/_system/wrapperlib.py
  - gars/_references/manifest_schema.json
  - gars/_system/manifest_check.py
  - gars/tests/test_rerun_check.py
  - gars/tests/fixtures/rerun-fixture/rerun_fixture.py
symptoms:
  - a completed manifest cannot bind mutable execution configuration during replay
  - fixture self-tests must not be mistaken for real Slurm reproduction evidence
---
# Row 6 step B: reproduction instrument and tolerances

## Context

The owner's words, 23 September 2026, verbatim:

> GARS row 6 (manifest completeness + reproduction) on the Mac Codex queue, decisions 0095-0099

The owner's D-9 answer, 23 September 2026, verbatim:

> D-9: yes, the n = 2 is my two Slurm re-runs; the fixture 2/2 is the instrument's self-test

Everything else in this record is the lane's specification and implementation
account, not additional words attributed to the owner. R-091 governs the
instrument; R-042 governs changes to the existing writer. The lane's D-16 answer
in 0095 remains open to the owner's confirmation in 0099.

## Decision

`scripts/rerun_check.py <manifest.json> --runs <n> --out <dir>` calls
`manifest_check.grade` directly. It refuses incomplete evidence, changed GARS or
pipeline HEAD (the manifest's own checkout), changed input hashes, missing or
changed execution configuration, and a status other than COMPLETE. It verifies
original OUTPUTS.tsv against both bytes and manifest before replay. An unavailable
`sbatch --version` produces `second backend unavailable`, without submitting.

Each re-run gets a fresh project and sub-stage under a previously nonexistent
output folder. Config and input symlinks retain the recorded input identities;
the real wrapper prepare and collect verbs run, with the real executor's submit
and status between them. Prepare's params must match, except the exact relocation
of Nextflow's output directory. Hashes, inputs, pipeline identity and execution
configuration must match before submit. The recorded pipeline checkout supplies
GARS_PIPELINES. No bio environment is installed or synthesized by the instrument.

Wrapper paths use the directory and underscore filename spelling used by the tool
registry and `gars-env.sh`. `--wrappers-root` is a test-only override; its default
is the real `gars/_system/wrappers` root. The fixture is absent from the production
registry and only runs when installed in a disposable suite checkout carrying its
self-test marker. It supplies the real check/prepare/collect verbs via wrapperlib;
a generated submit script sources the suite's stub gars-env.sh and executes under
the real local executor. No bio environment or scheduler is reachable in the suite.

The suite's numeric output shuffles rows and columns and adds noise bounded by
1e-7 per cell, with `random.Random` seeded from `os.urandom(16)` at each prepare.
The manifest records the actual seed and its source, and records
`no-rng-in-code-path` as false. The execution retains the consumed seed in seed.json
for audit; a re-run deliberately prepares a new seed for this fixture only.

### Comparison modes and pre-committed tolerances

`byte_stable` compares exact SHA-256, including directory member hashes and
symlink inventory. Every unlisted artifact defaults to this mode. Every original
OUTPUTS.tsv row must be compared; the replay inventory must match exactly.
`comparison.json` retains each run's job identity, artifact hashes, mode, metric,
value and match, plus the tolerance-file hash and requested run count.

The supported YAML subset is **JSON syntax only**: one object with an `entries`
array, quoted keys/strings, finite numeric thresholds, no YAML aliases, tags or
implicit scalars. Every entry needs wrapper, artifact, mode, nonempty cause and
second-re-run evidence. Numeric entries additionally require the named metric and
threshold. Missing fields, unknown modes/metrics and ambiguous matching entries
refuse. The on-disk tolerance file must equal its committed HEAD version before
execution. This check supplements the protected-path approval boundary.

The fixture-only metric is `max_absolute_error` on finite Decimal TSV cells.
Rows have unique `id` values; column names are unique. Both row identifiers and
columns are sorted. UTF-8 BOM, CRLF, blank lines and `#` metadata comments are
normalized; numeric serialization is parsed as Decimal without rounding. Missing
rows/columns, duplicate identities, non-numeric or non-finite cells cannot pass.
The fixture threshold is 0.000001. SHA-256 is recorded but never decides numeric
acceptance. Real wrappers receive no invented tolerance entries.

Measured instrument self-test on 2026-09-24: both re-runs differed in numeric
SHA-256, with max_absolute_error **5.6488E-8** and **1.65754E-7**, respectively.
Their byte-stable outputs matched exactly. These are this row's measured local
fixture re-runs, not biological or Slurm reproduction evidence. The second run
shows the same deliberate ordering/last-digit-noise class as the first. The
subsequent required verification's independently sampled values are in the report.

### How the owner's re-run is made

Choose a COMPLETE real run prepared with execution-configuration evidence whose
manifest grades complete. In the same GARS and pipeline revisions and installed
execution environment, on the institutional Slurm backend, run:

```text
python3 scripts/rerun_check.py <manifest> --runs 2 --out <folder>
```

Use a new output folder. Bring home all printed artifact/graded/reproduction lines
and the folder's comparison.json, together with retained re-run evidence. The
owner records the result in 0098. A refused older manifest is not repaired from
today's configuration: prepare and complete a new original run first. Failures
retain their output folder and executor records for diagnosis.

### Threat model

Covered: a producer or agent session running `rerun_check`, and any code path in this repository. It must not be able to:
  - report a reproduction that did not run n times from the manifest alone;
  - pass a byte-stable artifact that differs, or a numeric artifact outside its pre-committed threshold;
  - widen a tolerance without a cause and a second re-run on record;
  - re-run a manifest that is incomplete or no longer matches its inputs or pipeline commit;
  - drop an output from the comparison.
Not covered, named in 0097: an edit to `tolerances.yaml` itself (it is under `_references/`, protected; the owner's approval is that line); scientific adequacy of a metric or threshold; real-backend and second-backend behaviour.

## What this does not close

- The owner's two real Slurm re-runs and the whole row's exit remain unmeasured.
- §8.4's second backend, §17's ≥ 4/5 on test data and the external pilot-1 re-run
  are NOT met.
- Real-wrapper re-execution is NOT met: the suite has no bio environment. Its
  real-wrapper checks exercise prepare and synthetic collect on both fixture
  backends, with separate real local execution for the instrument self-test.
- Model-mediated steps compared as typed claim-set equality need row 7's claims.
- README's manifest/re-run evidence row stays unmeasured. Step A's other residuals
  remain; no real-run manifest completeness or benchmark-pin result is promoted.

## Test

`gars/tests/test_rerun_check.py` checks the local instrument self-test, two actual
submissions, numeric byte differences, threshold boundaries, exact-byte/default
behavior, every refusal, output coverage, Python 3.6 grammar and all ten real
wrapper re-preparations. The shared checker and reproduction refusal see the same
mutated manifests. R9 checks include Groovy slurm-to-local drift, descriptor drift,
unchanged keys and execution evidence preserved through collect on both paths.
The report records nine disposable fault plants, historical red checks and the
required full-suite/direct-module results.

## Status

Implementation evidence is separate from approval and real-run measurement.
Record 0098 is the owner's n = 2 re-run result; record 0099 is the owner's approval of `gars/_references/tolerances.yaml` and step A's protected changes.
The producer never writes either record, approves, merges or pushes this work.

## Date

2026-09-24

## Addendum — step B (the reproduction build), 2026-09-24

**R9 — the lane, under the owner's standing delegation of 23 September 2026.**
This is the lane's ruling, never additional words attributed to the owner.
Option A of B-1 is authorized in the narrowed form supplied for this round.
Execution configuration becomes immutable, hash-bound prepare evidence.

The common submit-script writer captures the descriptor it loaded and the actual
Nextflow config/profile argv supplied by prepare. It does not guess a sibling or
change a wrapper call site. This also records the two wrappers' literal apptainer
profile and the local path's actual fallback config accurately. The evidence is
handed to write_reproducibility in the same preparation process, then consumed;
no existing key, input hash, signature, command or script byte is changed.
The two new prepare keys are `execution_config` (role, repo-relative path, SHA-256)
and `execution_config_resolved` (backend and, for Nextflow, profile/config name).
Collect retains those values. A deleted optional descriptor still has the old
prepare behavior, but cannot supply the required file evidence and grades missing.

Under R-042, group 3 gains only execution_config in its required field list.
The checker requires well-formed nonempty entries, an executor_descriptor, and a
nextflow_config for a Nextflow wrapper. Other fields, classifications, predicates
and sentinels are unchanged. An older manifest grades group 3 missing and the
instrument refuses with `no execution config recorded`. Drift is refused with
`execution config drifted: <path>` before any re-run. The existing idempotency
formula remains byte-identical and excludes this additional evidence.

R9 authorizes wrapperlib.py, group 3's field list in manifest_schema.json,
manifest_check.py only for that field, and tests beyond brief B's allowed files.
Records 0095/0096, evals/bench.py, guard_hook.py and settings.json stay byte-identical
in this round. The owner's 0099 covers the protected files at merge.

### Newly measured replay boundary: scrna-qc-cluster

The fresh-project probe exposes a separate missing input: scrna-qc-cluster's real
prepare and collect require `01_samplesheets/scrnaseq_samplesheet.csv`, but its
writer records only `h5ad` and `config`. Repeating prepare inside the original
project passes equality checks without establishing replay from the manifest.
A fresh project reconstructed from the recorded inputs makes the real wrapper
refuse `no samplesheet` on both fixture backends. The instrument explicitly
refuses `manifest lacks required samplesheet input: scrna-qc-cluster` before
creating an output directory. It never copies unrecorded sibling state.

This input fix is stopped for the owner's ruling B-2 in the change report:
adding a manifest input changes the downstream key formula's result. R9 preserves
that behavior and only adds execution-configuration evidence. No scrna wrapper
call site or existing key behavior is changed in this round. Fresh replay prepare
is verified for the other nine wrappers on both fixture backends; biological
execution remains outside the suite.

### Original output identity at comparison

Comparison rechecks the original artifact against its manifest hash and symlink
inventory after execution, so a worker changing that artifact cannot move the
baseline to its new output. The strict-default regression plants this condition
and requires `original output drifted`. The comparison file retains the hash of
the tolerance file checked before execution, rather than re-reading its identity
at result-writing time.


## Addendum — step B's ruling round b (the reproduction build), 2026-09-24

**R10 — the lane, under the owner's standing delegation of 23 September 2026.**
This is the lane's ruling, not the owner's words. Option A of B-2 is authorized:
a consumed input absent from the manifest is a false "complete", so it is recorded.
Round ruling-b2 builds on `9def5b3`. The original bytes of this record and records
0095/0096 are preserved; 0098/0099 remain exclusively the owner's records.

### B-2 implementation and migration (R-042)

The only wrapper edit adds `samplesheet: paths["samplesheet"]` to
scrna-qc-cluster's existing `write_reproducibility` inputs. The unchanged writer
supplies `samplesheet_sha256` and `input_data_location.samplesheet`, retains them
through collect, and includes its bytes in `downstream-v1`. The formula is unchanged;
the new declared input changes this wrapper's key. The other nine wrappers retain
their base preparation keys, measured by running their `9def5b3` source and current
source against identical fixture paths and bytes on both fixture backends.

**Migration:** an existing prepared-but-unsubmitted scrna-qc-cluster stage must
re-run its normal `prepare --project <project> --h5ad <recorded matrix>` command
under the new code before submission. The regenerated manifest and submit-script
comment carry the new key. An unchanged legacy preparation can still satisfy the
unchanged `prepared_key` check: there is no automatic legacy-submit refusal or
retrofit. The new preparation satisfies that same check and real submit path.
Do not rewrite a manifest or key comment by hand. A completed legacy manifest
without the input still receives `manifest lacks required samplesheet input:
scrna-qc-cluster` from the instrument; prepare and complete a new original run.
This addendum does not authorize resetting a running or terminal stage.

No instrument edit is needed: its existing conditional B-2 guard admits the now
recorded case and continues refusing the missing-input case. Changed samplesheet
bytes refuse with `input hash changed: samplesheet` before an output folder or job
exists; submit independently refuses `prepared key differs from input bytes`.

`RealWrapperReplayTests.test_scrna_samplesheet_replay_and_drift` exercises fresh
projects through rerun_check, real prepare, submit key/record checks, local status,
collect and output comparison, with only the biological worker replaced by synthetic
artifacts and local completion evidence. It is not biological execution. The
all-wrapper test covers fresh prepare and execution-evidence preservation on both
fixture backends, comparing keys to the base behavior. The manifest invariant sweep
rehashes every declared input, checks each location and removes each input hash to
require group 1 to fail. Dropping the samplesheet declaration is step B's tenth
red-on-fault plant. Required commands and measured summaries are in the report.

### Survey stop: B-3, rnaseq-de's alternate design

The survey of the other nine wrappers found another consumed project file:
`rnaseq_de.py` prepare accepts `--design` and records that path, but collect reads
`01_samplesheets/rnaseq_bulk_design.csv` independently. When these paths differ,
the canonical file is absent from inputs, config and execution_config. A disposable
real-verb probe accepted the alternate design, changed only the canonical file
while every recorded input hash remained equal, and got collect exit 1 with
`normalized_counts.csv lacks sample(s): UNRECORDED`.

R10 requires stopping this part and raising the question, so no rnaseq-de or
instrument policy change is made here. B-3 in the report asks whether collect must
use the recorded design, or prepare must require canonical-path identity (with
migration and behavior tests), or the canonical collect input must be recorded
separately with its key/migration consequence. B-2 is answered; full Step B closure
is not claimed. The owner's real Slurm result and protected-path approval remain
unmeasured/pending, separate from this implementation ruling.


## Addendum — step B's ruling round b2 (the reproduction build), 2026-09-24

**R11 — the lane, under the owner's standing delegation of 23 September 2026.**
Round **ruling-b3**, parent `6039276`, applies option B of B-3. This is the lane's
ruling, never additional words attributed to the owner. The existing bytes of
0095, 0096 and this record are preserved; 0098/0099 belong solely to the owner.

### Canonical design identity (R-042)

The canonical design is the file collect already derives as the project directory
plus `01_samplesheets/rnaseq_bulk_design.csv`. Prepare compares resolved real paths
before any writes. A different file, even with identical content, returns exit 2
with `fail("design_not_canonical", "design is not the canonical project design")`.
Relative spellings and symlinks resolving to the canonical file remain accepted.
Collect is unchanged. The accepted inputs, manifest, generated scripts and key
are unchanged from the parent for each accepted spelling; the key formula is not
changed. The contract adds only this new failure code and refusal semantics.

**Migration:** an existing prepared-but-unsubmitted rnaseq-de stage naming an
alternate design must be re-prepared against the canonical project design before
submission. There is no new submit-time legacy detector in this scope; do not
hand-edit the manifest or generated key. This ruling does not authorize resetting
running or terminal stages. An existing COMPLETE run whose manifest records a
non-canonical design is refused by `rerun_check` with the named reason
`design is not the canonical project design`, before creating replay output or
submitting a job. It is never replayed; prepare and complete a new canonical
original for reproduction evidence.

### Verification and survey disposition

`RealWrapperReplayTests.test_rnaseq_design_prepare_identity` checks refusal with
no project writes for both empty and already prepared stages, and compares the
canonical, symlink and relative accepted cases with the real parent source.
`test_rnaseq_design_replay_and_legacy_refusal` produces a legacy COMPLETE manifest
with the parent wrapper and verifies the named pre-submission refusal, then uses
a separate canonical original for two fresh replays through real prepare,
submit/status, collect and comparison with a synthetic worker. This is not
biological execution or the owner's two Slurm re-runs.

Step B adds plant 11: **rnaseq-de prepare accepts a non-canonical design**; removal
of the refusal must fail the prepare-identity test. The report records observed
fault results and all required runner summaries.

The R10 re-survey of the other nine wrappers is **COMPLETE**; **B-3 was its only
finding**, as recorded in the preceding report's wrapper-by-wrapper survey.
R11 answers it. No new owner ruling is needed for this implementation round.
The existing real-execution gaps and the owner's separate 0098/0099 remain.
