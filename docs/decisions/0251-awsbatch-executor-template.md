---
date: 2026-09-30
status: standing
kind: decision
touches:
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/_templates/config/nextflow.awsbatch.config
  - gars/tests/test_executor_templates.py
  - gars/tests/fixtures/executor/nextflow.awsbatch.d-generator.config
symptoms:
  - an AWS Batch venue's _config/nextflow.awsbatch.config is refused with "R-098/§9.6 unregistered Groovy grammar; use the seeded executor config" whatever it holds
  - a descriptor whose nextflow_config names sub/x or ../x makes preflight check one file while the wrapper passes another with -c
---
# One protected executor template per descriptor config name: the AWS Batch template

Follow-up to [0039](0039-the-executor-is-a-workspace-setting.md) (the executor seam) and to row 4's typed policy surface ([0058](0058-row-4-typed-surface-and-attack-list.md), ruling 3A), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and ruled by the lane's coordinator on 30 September 2026; no sentence in this record is the owner's.
0252 is the delegated approval of the protected change; this record does not write it.

## Context

`check_groovy` (added on 21 Sep 2026 in `6c4b631`, row 4) admits an executor config only when, with comments stripped, each single-quoted literal replaced after an R-075 charset check, and whitespace removed, it equals the shape of `_templates/config/nextflow.slurm.config`.
It compared with that one file whatever the descriptor's `nextflow_config` named, so the launch pad's `nextflow.awsbatch.config` (written by the demo's `gen_executor_config.sh --head local`) was refused at `a80df2d` and at `37a8d94` with "R-098/§9.6: unregistered Groovy grammar; use the seeded executor config".
The slurm grammar cannot say what the config of the demo's run on Batch of 3 Sep 2026 carried: `aws.region`, `aws.batch.cliPath`, `aws.batch.maxSpotAttempts`, the transfer settings, `process.resourceLimits`, `process.resourceLabels`, and the null-exit arm of `errorStrategy`.
The lane's coordinator ruled option (b) on 30 Sep 2026: one fixed protected template per descriptor config name, a missing template refused, slurm unchanged, the shape lock and the literal check kept.

Reading the code for the widening found a defect at `37a8d94`, reproduced without a model.
The nf-core wrappers pass `ex.nextflow_config_path(project)` with `-c`, which is `<project>/_config/<name>`; `check_executor_config` re-derived the file from the base name.
For a descriptor naming `sub/nextflow.slurm.config`, preflight read `_config/sub/sub/nextflow.slurm.config` while the wrapper passed `_config/sub/nextflow.slurm.config`; for `../nextflow.slurm.config`, preflight read a file two levels up and the wrapper one level up.
A slurm-shaped decoy at the checked path let a config with `process.beforeScript` through (both names printed ADMITTED with the evil file at the wrapper's path).

## Decision

**Ruling 0251 (the lane's).**

1. **The template** (`gars/_templates/config/nextflow.awsbatch.config`, protected under `_templates/`).
   Its single-quoted literals are exactly the four site values: `process.queue`, the `goal` value of `process.resourceLabels`, `aws.region` and `aws.batch.cliPath`.
   Every other token is grammar, including double-quoted strings, which the shape keeps verbatim: `executor = "awsbatch"`, the `errorStrategy` outcomes `"retry"` and `"finish"`, `submitRateLimit = "10/1min"`, and the trace `file` and `fields`.
   Line by line:
   - `executor`, `queue`, `resourceLimits = [ cpus: 4, memory: 14.GB, time: 8.h ]`, `errorStrategy` with the null arm, `maxRetries = 3`, `aws.region`, `aws.batch.cliPath`, `maxSpotAttempts = 5`, `maxParallelTransfers = 4`, `maxTransferAttempts = 3`, `queueSize = 20` and `submitRateLimit` are the 3 Sep config's lines, with the reasons its generator's comments give (the clamp to the largest instance type, the reclaimed host reporting no exit status, the CLI path that must equal the hosts' install path, spot reclamation as normal weather).
   - The clamp values are fixed grammar, not site values: both Batch compute environments the demo defines use the same instance types, largest `m5.xlarge`, so no known site needs another value, and a site that does changes a protected template with its own record.
   - `resourceLabels = [ goal: '…' ]` is always present with exactly one key, so a job's cost-allocation tag can never be forgotten; a rehearsal and a take differ only in the value. The 3 Sep config's second key (`project`) is not admitted.
   - The `errorStrategy` outcomes are double-quoted, which departs from the 3 Sep form (`'retry' : 'finish'`): as single-quoted literals they would be site values, and `'retry' : 'retry'` or `'ignore'` would pass (the investigation's candidate showed the first passes under the slurm grammar). The closure is the 3 Sep closure otherwise, token for token.
   - The `trace` block is the slurm template's, with its file double-quoted: collect's manifest reads `run/pipeline_info/gars_trace.txt` for each process's container, start and complete (`trace_evidence`), and the 3 Sep config had no trace block. `report`, `timeline` and `apptainer.pullTimeout` are left out: nothing in the manifest reads the first two, and Batch supplies each container itself.
   - No `params`, `workDir`, `beforeScript`, `includeConfig` or `$` appears in it (a test pins this).
2. **The check** (`gars/_system/wrapperlib.py`).
   `check_executor_config` hands the descriptor's name to `check_groovy`, which compares with `executor_template(name)`.
   `executor_template` is the one door from a name to a template: the name must fully match `nextflow\.[a-z0-9]+\.config`, and the template must be a regular file, not a symlink, directly in `_templates/config/` as reached without a symlink (its resolved parent equals the folder's path); anything else is refused as "R-098/§9.6: <name> names no protected executor template; use the seeded executor config".
   The shape function, the R-075 literal check and the refusal text for a grammar mismatch are unchanged, and `check_groovy` called with no name still compares with the slurm template.
3. **The file checked is the file passed.**
   `check_executor_config` refuses a config that does not sit directly in its project's `_config/` ("R-098/§9.6: <file> is not a file directly in the project's _config/; use the seeded executor config"), and `executorlib.validate` refuses a descriptor whose `nextflow_config` contains `/` or is `.` or `..` ("R-075: nextflow_config must be a bare file name in _config/").
   The second rule also reaches an absolute name that lands in another project's `_config/`, where preflight reads that other project's descriptor: `write_submit_sh` validates the requesting project's descriptor and raises before `submit.sh` is written, as it already does for a backend outside the enum.

Slurm is unchanged for every descriptor whose name is the seeded `nextflow.slurm.config`, including no descriptor at all: the same verdicts and the same refusal texts (ExecutorSeamTests, `test_09` untouched, and the trace-grammar test of `test_manifest_groups.py`).
What changes on a slurm workspace is only the refusals above, of names that were never seeded.

Rejected alternatives: a union of both grammars under any name (a slurm workspace would admit the Batch grammar under its own name); admitting any file in `_templates/config/` (the assay YAML templates live there); a site value for the clamp or the retry outcomes (no site needs one, and each would widen what an agent-written file can change); `$NXF_HOME` or an `includeConfig` for the missing options (ruled out: a road around the audited surface).

## Threat model of the widening

The widening lets a second grammar through, selected by a name in an agent-writable file (`_config/executor.yaml`), so these are the properties it must keep, each with its code and test:

- **No config outside the two templates is admitted.** Admission is equality with `shape(template)` (`wrapperlib.py:407`), the template comes only from `executor_template` (`:406`), which admits only a bare `nextflow.<venue>.config` regular file directly in `_templates/config/` (`:373-388`); today that is two files. Tests 04 and 05 refuse eight additions (one line or one block each) and fourteen changes of fixed tokens; test 09 refuses each grammar under the other's name.
- **A name cannot escape `_templates/config/`.** The name pattern has no separator and no dot-dot (`:374`, `:385`), the resolved parent must equal the folder (`:386`), and the descriptor may not name a path (`executorlib.py:266-268`). Test 06 (a missing template, a case-folded name, a `.bak` name, an assay YAML template) and test 07.
- **A template cannot be a file the agent wrote.** `_templates/` is a protected prefix the guard refuses writes to (`guard_hook.py:106`), and a symlink or a folder reached through one is refused (`wrapperlib.py:385-386`). Test 08, with a control proving a regular file of the same bytes selects, so it is the link that refuses.
- **The file checked is the file passed with -c.** `wrapperlib.py:354` and `executorlib.py:266-268`. Test 07 plants the evil config at the wrapper's path and a clean decoy where `37a8d94`'s check read, for a subdirectory, a dot-dot and two absolute names, each refused.
- **The manifest still records the config bytes.** `execution_evidence` hashes the path the submit body passes after `-c` (`wrapperlib.py:573-579`), unchanged. Test 10 asserts the recorded sha256 equals the fixture's bytes and the path equals the `-c` token of the generated `submit.sh`.
- **Site values stay values.** Each single-quoted literal passes R-075's charset or the config is refused (`wrapperlib.py:401`). Test 03.

## What this does not close

- **R1 (found, not in the ruling).** A descriptor with `name: local` and no `nextflow_config` demands no config, yet the nf-core wrappers then pass `_config/nextflow.slurm.config` with `-c` (their `paths_for` fallback), which preflight never checks; at `37a8d94` and here a `beforeScript` in it passes `check_executor_config`. The local venue is fixture-only under [0100](0100-row-8-data-handling.md)'s route policy, which bounds it but does not close it. Raised with the lane's coordinator.
- **R2.** The Batch grammar is selectable by name on any workspace, including a slurm one (`name: slurm` with `nextflow_config: nextflow.awsbatch.config` validates). On a host holding AWS credentials, task files would then move through S3 under a slurm venue's route. Pairing the template with the `local` backend is a one-line rule the coordinator may rule on; it is not in this change.
- **R3.** The bytes are checked at prepare and hashed into the manifest; a rewrite of the config between prepare and the job's start is visible in the manifest's hash, not refused (unchanged from row 6's R9).
- **R4.** Whitespace is removed everywhere before comparison, inside double-quoted strings too, so `"aws batch"` has the shape of `"awsbatch"`; such a change can only produce a config Nextflow rejects (unchanged from 0058's grammar).
- **R5.** No Nextflow parsed this template in this lane (no Nextflow on the build Mac, and no AWS use); the first parse is the launch pad's.
- The demo's generator (`gen_executor_config.sh`) is matched to this template by its own lane, not here; until it is, the pad's generated config is still refused.

## Test

`gars/tests/test_executor_templates.py` is new, 11 tests, with the fixture `gars/tests/fixtures/executor/nextflow.awsbatch.d-generator.config`, the shape the demo's generator must write.
At `37a8d94`'s code they fail in tests 01 to 10 (19 failures and 1 error, each for the missing selection, the missing name gate, the missing seam or the slurm grammar admitted under the Batch name); test 11 pins the template's own content.
They must fail when `check_groovy` compares with slurm only, when either grammar passes under either name, when the name pattern, the symlink check or the resolved-folder check is dropped, when the `_config/` fence or the bare-name rule is dropped, when the manifest hashes anything but the `-c` file, when the literal check is dropped, and when the template's outcomes become site values or its tag gains a key.
The landing's evidence is recorded in 0252.

## Status

Standing. The change record for the AWS Batch executor template; its protected-change approval is 0252. Records 0253 to 0255 stay reserved for this lane.

## Date

2026-09-30
