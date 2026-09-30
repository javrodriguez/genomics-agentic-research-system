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
  - text after a // inside a double-quoted string of an executor config left preflight's shape (security fix, present on public main since row 6's landing), and a nested _config/_config/executor.yaml changed the project preflight read (review r1)
---
# Security fix and the AWS Batch executor template: strings read before comments in the executor-config check, and one protected template per descriptor config name

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

## Disclosed pre-existing finding: the security fix in this change

This change is a security fix as well as a widening, so that an approval of it is an approval of the fix, knowingly (the coordinator's ruling of 30 Sep 2026, under the owner's delegation).
- **What.** `check_groovy`'s shape stripped `//` comments before it read any string, so text after a `//` inside a double-quoted string left the shape while staying in the file, and whitespace inside a double-quoted string was dropped; the R-075 check never saw the hidden text (item 4, L5-R1-1 and L5-R1-2).
- **When it entered.** The comment strip came with `check_groovy` itself, in `6c4b631` (21 Sep 2026, row 4), landed on main by `9b76e3f` (22 Sep 2026).
  At `6c4b631` the slurm template held no double-quoted string outside its comments, so, by the lane's reading of those bytes (not probed at that commit), there was no string to hide text in yet.
- **The ways in.** The slurm template's `fields` string, added by `94249c5` (row 6) and landed by `bc5f98e` (24 Sep 2026), is on public main `37a8d94`.
  Measured by the lane at `37a8d94`'s own code (`check_groovy` on the seeded slurm template with one inert change in `fields`): a `//` followed by a second `process.maxRetries` statement, the string closed on the next line, was ADMITTED, and so was one added space; at this change both are refused.
  The AWS Batch template adds five more double-quoted strings (`"awsbatch"`, `"retry"`, `"finish"`, `"10/1min"` and the trace file), besides its own `fields`, so without the fix the widening would have multiplied the places the defect could sit.
  The review's probes (in the trace `file` string, `submitRateLimit` and slurm's `fields`) were admitted too; whether Nextflow would run hidden text was not measured here (R5).
- **The fix.** Item 4: `shape` reads strings before comments and keeps each double-quoted string byte for byte; test 12 refuses both changes in every double-quoted string of both templates.

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
   - The `trace` block is the slurm template's, with its file double-quoted and two fields added: collect's manifest reads `run/pipeline_info/gars_trace.txt` for each process's container, start and complete (`trace_evidence`), and the 3 Sep config had no trace block.
     The added fields are `native_id` (the launch pad's `jobs` finds the Batch job ids there; D `scripts/launchpad.sh:893` in the demo workspace, `:940` in the pad lane's worktree requires it with `task_id` and `name`) and `exit` (the pad's smoke verdict stops without it, D `scripts/batch_smoke.sh:124-128`); the rest keep the slurm order (F-L3-3, the lane executor's in-spec ruling of 30 Sep 2026, open to the coordinator's review).
     That a `-c` config's trace scope replaces nf-core's own is the pad lane's inference, not measured here (R5); `trace_evidence` reads columns by header name (`wrapperlib.py:1024`), so the added columns are read past (test 14). `report`, `timeline` and `apptainer.pullTimeout` are left out: nothing in the manifest reads the first two, and Batch supplies each container itself.
   - No `params`, `workDir`, `beforeScript`, `includeConfig` or `$` appears in it (a test pins this).
2. **The check** (`gars/_system/wrapperlib.py`).
   `check_executor_config` hands the descriptor's name to `check_groovy`, which compares with `executor_template(name)`.
   `executor_template` is the one door from a name to a template: the name must fully match `nextflow\.[a-z0-9]+\.config`, and the template must be a regular file, not a symlink, directly in `_templates/config/` as reached without a symlink (its resolved parent equals the folder's path); anything else is refused as "R-098/§9.6: <name> names no protected executor template; use the seeded executor config".
   The R-075 literal check and the refusal text for a grammar mismatch are unchanged, and `check_groovy` called with no name still compares with the slurm template.
   The shape function changed after review r1 (item 4).
3. **The file checked is the file passed.**
   `check_executor_config` refuses a config that does not sit directly in a `_config/` folder ("R-098/§9.6: <file> is not a file directly in the project's _config/; use the seeded executor config"), and `executorlib.validate` refuses a descriptor whose `nextflow_config` contains `/` or is `.` or `..` ("R-075: nextflow_config must be a bare file name in _config/").
   The second rule also reaches an absolute name that lands in another project's `_config/`, where preflight reads that other project's descriptor: `write_submit_sh` validates the requesting project's descriptor and raises before `submit.sh` is written, as it already does for a backend outside the enum.
   The project whose descriptor preflight reads is the parent of the passed file's `_config/` folder, never found by walking up, and the fence runs before the descriptor is read (item 4).
4. **Review r1's findings (fixed in this change).**
   - **L5-R1-1 (MAJOR), a `//` inside a double-quoted string.** The shape stripped `//[^\n]*` before it read any string, as it had since `6c4b631`, but in Groovy a `//` inside a string literal is string text, not a comment.
     So string text after a `//` left the shape while staying in the file, and a later line that shaped to the missing closing quote made the comparison equal again; the R-075 check never saw the hidden text, because it ran only on single-quoted spans that survived the strip.
     The reviewer's probes were admitted in the trace `file` string, `submitRateLimit` and the slurm template's own `fields` string, so the defect was already in the slurm grammar at `37a8d94`; the Batch template's six double-quoted strings would have multiplied the places it could sit.
     `shape` now reads the text left to right: a quoted string is read whole before any comment is considered, each single-quoted literal passes R-075 and becomes one site-value token, each double-quoted string is one token kept byte for byte, whitespace included, and only outside strings are `//` comments and whitespace dropped; token lists, not joined text, are compared (`wrapperlib.py:400-425`).
     An unterminated quote is refused.
   - **L5-R1-2 (MINOR), whitespace inside a double-quoted string** was dropped before comparison; the same change keeps it, so `"aws batch"` no longer has the shape of `"awsbatch"`.
   - **L5-R1-3 (MINOR, from before this change), a nested `_config/`.** Preflight found its project with `config_root_for(<the config's folder>)`, which walks up to the nearest folder holding a `_config/`.
     A `<project>/_config/_config/executor.yaml` made that walk stop at `<project>/_config`, so preflight read that descriptor (`name: local`, no config demanded) and returned early, while the wrapper still passed the project's own `_config/nextflow.awsbatch.config` with `-c`, unchecked.
     The project is now the passed file's `_config/` folder's parent (`wrapperlib.py:349-354`), which is the project the wrapper built the path from; closed.

Slurm is unchanged for every descriptor whose name is the seeded `nextflow.slurm.config`, including no descriptor at all, for every config the seeded template admits: the same verdicts and the same refusal texts (ExecutorSeamTests, `test_09` untouched, and the trace-grammar test of `test_manifest_groups.py`).
What changes on a slurm workspace is only the refusals above, of names that were never seeded, and, since review r1, of a config whose `fields` string differs from the template's byte for byte (a `//` or whitespace inside it).

Rejected alternatives: a union of both grammars under any name (a slurm workspace would admit the Batch grammar under its own name); admitting any file in `_templates/config/` (the assay YAML templates live there); a site value for the clamp or the retry outcomes (no site needs one, and each would widen what an agent-written file can change); `$NXF_HOME` or an `includeConfig` for the missing options (ruled out: a road around the audited surface).

## Threat model of the widening

The widening lets a second grammar through, selected by a name in an agent-writable file (`_config/executor.yaml`), so these are the properties it must keep, each with its code and test:

- **No config outside the two templates is admitted.** Admission is equality with `shape(template)` (`wrapperlib.py:428`), the template comes only from `executor_template` (`:427`), which admits only a bare `nextflow.<venue>.config` regular file directly in `_templates/config/` (`:379-390`); today that is two files. Tests 04 and 05 refuse eight additions (one line or one block each) and fourteen changes of fixed tokens; test 09 refuses each grammar under the other's name.
- **Nothing hides inside a fixed string.** `shape` reads strings before comments and keeps each double-quoted string byte for byte (`wrapperlib.py:400-425`). Test 12 refuses, in each double-quoted string of both templates, a `//` followed by an extra statement and one added space.
- **A name cannot escape `_templates/config/`.** The name pattern has no separator and no dot-dot (`:376`, `:387`), the resolved parent must equal the folder (`:388`), and the descriptor may not name a path (`executorlib.py:266-268`). Test 06 (a missing template, a case-folded name, a `.bak` name, an assay YAML template) and test 07.
- **A template cannot be a file the agent wrote.** `_templates/` is a protected prefix the guard refuses writes to (`guard_hook.py:106`), and a symlink or a folder reached through one is refused (`wrapperlib.py:387-388`). Test 08, with a control proving a regular file of the same bytes selects, so it is the link that refuses.
- **The file checked is the file passed with -c.** `wrapperlib.py:349-354` and `executorlib.py:266-268`. Test 07 plants the evil config at the wrapper's path and a clean decoy where `37a8d94`'s check read, for a subdirectory, a dot-dot and two absolute names, each refused. Test 13 refuses an extra statement behind a nested `_config/_config/executor.yaml`.
- **The manifest still records the config bytes.** `execution_evidence` hashes the path the submit body passes after `-c` (`wrapperlib.py:594-600`), unchanged. Test 10 asserts the recorded sha256 equals the fixture's bytes and the path equals the `-c` token of the generated `submit.sh`.
- **Site values stay values.** Each single-quoted literal passes R-075's charset or the config is refused (`wrapperlib.py:416`). Test 03.

## What this does not close

- **R1 (found, not in the ruling).** A descriptor with `name: local` and no `nextflow_config` demands no config, yet the nf-core wrappers then pass `_config/nextflow.slurm.config` with `-c` (their `paths_for` fallback), which preflight never checks; at `37a8d94` and here a `beforeScript` in it passes `check_executor_config`. The local venue is fixture-only under [0100](0100-row-8-data-handling.md)'s route policy, which bounds it but does not close it. Raised with the lane's coordinator.
- **R2.** The Batch grammar is selectable by name on any workspace, including a slurm one (`name: slurm` with `nextflow_config: nextflow.awsbatch.config` validates). On a host holding AWS credentials, task files would then move through S3 under a slurm venue's route. Pairing the template with the `local` backend is a one-line rule the coordinator may rule on; it is not in this change.
- **R3.** The bytes are checked at prepare and hashed into the manifest; a rewrite of the config between prepare and the job's start is visible in the manifest's hash, not refused (unchanged from row 6's R9).
- **R4 (amended after review r1).** Whitespace outside strings is still removed before comparison, so the check does not see a token split by whitespace (for example a number broken by a space or a line break); the lane has not proved that every such split is a config Nextflow rejects, and none was parsed here (R5). Whitespace inside a double-quoted string is no longer free (item 4).
  This item first said that whitespace inside double-quoted strings was free and that such a change "can only produce a config Nextflow rejects"; the second half was never measured and is withdrawn.
- **R5.** No Nextflow parsed this template in this lane (no Nextflow on the build Mac, and no AWS use); the first parse is the launch pad's.
- The demo's generator (`gen_executor_config.sh`) is matched to this template by its own lane, not here; until it is, the pad's generated config is still refused.

## Test

`gars/tests/test_executor_templates.py` is new, 14 tests, with the fixture `gars/tests/fixtures/executor/nextflow.awsbatch.d-generator.config`, the shape the demo's generator must write.
At `37a8d94`'s code they fail in tests 01 to 10 (19 failures and 1 error, each for the missing selection, the missing name gate, the missing seam or the slurm grammar admitted under the Batch name); test 11 pins the template's own content.
Tests 12 and 13 answer review r1: at `2a144e1`'s code they fail with 15 failures (fourteen admitted cases of test 12, one of test 13), each an admission where a refusal is due.
Test 14 pins the Batch trace fields (F-L3-3) and that `trace_evidence` reads a trace carrying them; at `a36c96e` it fails on the pin alone.
They must fail when `check_groovy` compares with slurm only, when either grammar passes under either name, when the name pattern, the symlink check or the resolved-folder check is dropped, when the `_config/` fence or the bare-name rule is dropped, when the manifest hashes anything but the `-c` file, when the literal check is dropped, when `shape` strips comments before it reads strings or drops whitespace inside them, when preflight walks up for its project, and when the template's outcomes become site values or its tag gains a key.
The landing's evidence is recorded in 0252.

## Status

Standing. The change record for the AWS Batch executor template; its protected-change approval is 0252. Records 0253 to 0255 stay reserved for this lane.

## Date

2026-09-30
