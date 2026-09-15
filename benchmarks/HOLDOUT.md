# Row 2 benchmark: owner run and independent sealing interface

**Row 2 exit: NOT met.** This repo supplies five tuned-on tasks and deterministic
scorers. No agent run, noise-floor observation, or held-out seal is supplied here.
The scored agent is a fresh Claude Code session driven by `gars/CLAUDE.md`.
`evals/bench.py` consumes an exported folder; it never starts that agent or a pipeline.

## The five tuned-on tasks

| Task id | Question being tested | Reference source | Scorer |
|---|---|---|---|
| `batch-confounded` | Refuse a condition completely confounded with batch | `synthetic_with_generator_seed` | `exact` |
| `single-replicate` | Refuse one independent replicate per condition | `synthetic_with_generator_seed` | `exact` |
| `pseudoreplicates` | Refuse libraries treated as independent biological replicates | `synthetic_with_generator_seed` | `exact` |
| `bulk-rnaseq` | Complete a bulk RNA fixture project on the pinned nf-core test profile | `nfcore_test_data_expected_output` | `pytest` |
| `bulk-atacseq` | Complete a bulk ATAC fixture project on the pinned nf-core test profile | `nfcore_test_data_expected_output` | `pytest` |

`benchmarks/fixtures/generate.py`, seed **110112**, reconstructs the three synthetic
CSV inputs. These are tuned-on plants, not the row 1 sealed fixtures. Only these
three design tasks are introduced; this is not a later-row defect catalogue.

**Named provenance gaps: NOT met:** `NFCORE_RNASEQ_EXPECTED_OUTPUT_NOT_OBTAINED`
and `NFCORE_ATACSEQ_EXPECTED_OUTPUT_NOT_OBTAINED`. The source descriptors name
nf-core/rnaseq 3.26.0 and nf-core/atacseq 2.1.2 and their `conf/test.config` references.
No test data or expected numerical outputs were fetched. Before owner execution,
retrieve those profiles in the owner's execution environment, resolve the
nf-core/test-datasets commit, hash every downloaded input, and preserve the
retrieval and pipeline provenance with the exported project. Versioned URL
references alone are not verified file hashes. Adding materialized inputs to the
task schema changes the suite digest and requires all comparison runs to use that
same revised suite. Until an independent expected output is obtained, a pass is
an **artifact-contract pass only**, not reproduction of a numerical reference.
The source enum identifies the intended source, not a claim that the gap is closed.

Reuse existing project shapes and wrappers by the paths hashed in each task;
`examples/demo-project/` is a synthetic illustration, not nf-core truth. The
planted-effect matrices and frozen Gap Study transcripts are not substituted for
nf-core outputs. No second copy of an existing fixture is maintained.

## Task wire format (also the complete sealing contract)

Use one `tasks/<id>.yaml` per task, with a unique id matching
`[A-Za-z0-9][A-Za-z0-9_.-]*`. Each file is **strict JSON, the JSON subset of YAML**:
UTF-8, double-quoted keys/strings, no comments, tags, anchors, duplicate keys,
NaN, or Infinity. Existing repo YAML readers only handle flat/two-level config
scalars; they cannot read this nested schema. Python's stdlib `json` loader is
therefore the documented minimal parser; no PyYAML dependency is introduced.

Exactly these nine top-level fields are required, with no extra keys:

| Field | Type and meaning |
|---|---|
| `question` | Nonempty text given to the agent |
| `inputs` | Nonempty list of objects with exactly `path` and `sha256`; path is a relative file path, sha256 is 64 lowercase hex digits and must match the file bytes |
| `expected_workflow` | Nonempty text explaining stages, expected stop/approval gates and outcome |
| `expected_outputs` | Nonempty mapping from relative output file paths to the single-assertion objects below |
| `known_pitfalls` | Nonempty text, including provenance gaps if any |
| `reference_answer` | Nonempty text; the three design tasks use exactly `refuse and flag` |
| `reference_source` | Exactly one of the four enum strings below |
| `scorer` | `exact`, `regex`, `pytest`, or `human`; only the first three have executable scorers |
| `holdout` | JSON boolean; `false` in the repo's task directory, `true` in the sealed directory |

The four `reference_source` values, verbatim:

- `public_dataset_with_published_result(DOI)`
- `nfcore_test_data_expected_output`
- `synthetic_with_generator_seed`
- `sealed_human_answer(author ≠ builder)`

Put the actual DOI, generator seed, or independent author attribution in the
reference answer/source input file. The enum value itself never changes.
Hash every input file; a directory or unchecked remote URL is not an input file.
For tuned-on tasks, paths resolve from the repository root. For held-out tasks,
paths resolve from `GARS_BENCH_HOLDOUT_DIR`. Absolute paths, parent traversals,
input symlinks escaping that root, and task-file symlinks are refused.

### Executable output assertions

Each output path maps to exactly one assertion:

- `exact`: `{"json_equals": <JSON value>}` or `{"text_equals": "literal"}`.
  JSON comparison is structural equality. Text comparison strips leading/trailing
  whitespace. Use structured refusal fields, not a grep of narrative.
- `regex`: `{"regex": "Python regular expression"}`; full match of stripped UTF-8
  text, not a substring. No executable code is accepted from task files.
- `pytest`: Python assertions compatible with pytest, executed with stdlib
  `unittest.TestCase` assertions, **without importing or requiring pytest**.
  Supports `json_equals`, `text_equals`, `{"nonempty": true}`, and
  `artifact_registry` as specified below. All assertions must pass for the task
  to earn its one point. No task-supplied Python file is executed.
- `human`: recognized enum but refused by this scorer. Use only when no
  deterministic scorer applies; leave that candidate outside the executable
  suite and record the unmeasured gap until an independently approved manual
  protocol exists. No model, of any family, can substitute for a scorer.

Example design output contract (the other top-level fields still required):

```json
{
  "response.json": {
    "json_equals": {
      "answer": "refuse and flag",
      "flag": "batch_fully_confounded",
      "stage": "01_prepare_samplesheets",
      "execution_started": false
    }
  }
}
```

The JSON records what the session reports. It does not independently prove that
execution never occurred; the owner retains the session trace for review. Missing,
malformed, contradictory, or incorrectly flagged responses fail the contract.

`artifact_registry` takes exactly `types`, `samplesheet`, `sample_mode`:

```json
{
  "artifact_registry": {
    "types": {"counts_gene": "counts", "qc_multiqc": "file"},
    "samplesheet": "project/01_samplesheets/rnaseq_bulk_samplesheet.csv",
    "sample_mode": "rnaseq"
  }
}
```

The output at this path is GARS `OUTPUTS.tsv`: optional `#` comment/header lines,
then three tab-separated fields `type`, `role`, `path`. Types are unique, roles
must be `native`, and artifact paths resolve relative to the registry. Each
required type is tested with one of:

- `file`: nonempty file;
- `directory`: directory with at least one nonempty file;
- `counts`: nonempty tab-separated table with header, unique nonempty feature
  identifiers, distinct columns, equal row lengths, finite nonnegative sample
  values, and every samplesheet sample present as a complete token in a sample
  column (RNA `sample`, ATAC `sample_REP<replicate>`). Accepted metadata prefixes:
  one feature-id column, `gene_id/gene_name`, or featureCounts'
  `Geneid, Chr, Start, End, Strand, Length`;
- `bed`: nonempty tab-separated intervals with chromosome and integer coordinates
  satisfying `0 <= start < end`.

`samplesheet` resolves relative to this task's output directory and is a CSV with
`sample`, plus integer-text `replicate` for `sample_mode: atacseq` (`rnaseq` is the
other value). Project contracts use the existing native artifact type lists and
require `STATUS` text `COMPLETE`. This validates the artifact interface, not BAM
integrity, full nf-core scientific validity, or numerical expected-output truth.
Every artifact must remain within the exported task directory. The overall export
must contain no symlinks; dereference only the intended public/synthetic artifacts
when exporting. Do not export secrets or machine-specific paths.

## Separate sealing session: procedure

1. Start a fresh reviewer session that has never tuned the producer prompt and
   does not receive the producer transcript. The development default is
   `independent_context`; public credibility requires `external_human_seal`.
2. Choose new, independent tasks/inputs covering the same kinds of design refusal
   and RNA/ATAC work. Do not copy tuned-on answers and call them held out. The
   spec does not fix a held-out task count; document the chosen coverage and count
   in a private `SEAL_NOTES.md`, with author, date and reference provenance.
3. Create a private root outside the producer-readable repository, containing
   `tasks/*.yaml`, hashed `inputs/` (and a generator/seed where synthetic),
   `seal.json`, and private `SEAL_NOTES.md`. Use `holdout: true` in every task.
   Do not put the private root, tasks, answers, or seal notes in this repo.
4. Enforce producer read denial with credentials/ACLs or an isolated environment.
   Verify a read attempt using the producer credential fails, and retain that
   evidence in `SEAL_NOTES.md`. A boolean in a manifest is not an ACL. This
   producer session must never read or create that slice. Scoring is performed
   later by a separately authorized evaluation session that can read it.
5. Validate the tasks using this interface from the authorized session. The
   equivalent Python API is `bench.load_tasks(root / 'tasks', root, True)`, with
   `evals/` on `sys.path`. Compute `bench.digest(tasks)` on that returned mapping.
   The digest is SHA-256 of UTF-8 JSON of the task-id mapping with sorted keys,
   separators `(',', ':')`, and `ensure_ascii=True`; task inputs bind file hashes.
6. Write `seal.json` with **exactly** `seal_type` (`independent_context` or
   `external_human_seal`), `suite_sha256` (computed above), and
   `producer_access_denied: true`. Only attest true after step 4. The scorer
   checks this declaration and the digest; operational denial remains the
   sealer's independently retained evidence.
7. Freeze the slice before prompt tuning. Set `GARS_BENCH_HOLDOUT_DIR` only in
   the authorized scoring session. Supply questions/inputs to the agent through
   the owner-controlled task runner, withholding references/contracts that would
   reveal answers. Preserve the complete benchmark prompt bytes and their hash.
   Export responses under `held_out/<id>/`. Keep task-level results private where
   they could inform tuning. Reseal with new tasks if answers become exposed.

An unset variable prints and records `held_out: unmeasured`; it never adds zero
points or silently skips the partition. An empty/invalid directory, malformed
seal, mismatched digest, or `holdout: false` task in the sealed suite is an error.
A `holdout: true` task in `benchmarks/tasks/` is refused, even if a caller attempts
to load that directory as the held-out slice. This interface is not evidence that
an actual seal exists yet.

## Owner run and record format

Run the five tasks in fresh Claude Code sessions governed by `gars/CLAUDE.md`.
Use the same exact model and benchmark prompt bytes for all repeats and the
comparison. Retain prompt, transcript and provenance in the private owner archive.
The degraded arm has **design check disabled and reviewer disabled**, as §11.1
states; the owner implements and attests that arm, not this repo-side scorer.
Use three intact repeats at one GARS commit; do not relabel helper/unit-test
outputs as agent runs. Record the degraded commit separately if it differs.

Export layout:

```text
outputs/
  tuned_on/<task-id>/response.json                 # design tasks
  tuned_on/<task-id>/project/...                   # nf-core tasks
  held_out/<sealed-task-id>/...                    # when measured
```

The owner supplies a separate metadata JSON file, outside `outputs/`, with exactly:

```json
{
  "run_id": "intact-1",
  "git_sha": "FULL_40_LOWERCASE_HEX_COMMIT_HASH",
  "model": "EXACT_MODEL_ID",
  "prompt_sha256": "FULL_64_LOWERCASE_HEX_PROMPT_HASH",
  "configuration": "intact",
  "resource": {
    "wall_time_seconds": "unknown",
    "tokens": "unknown",
    "cost_usd": "unknown"
  }
}
```

Replace placeholders; they deliberately do not validate. Resource numbers describe
**the agent run**, not scoring time. Values are nonnegative measured numbers or
`unknown`; tokens, if known, are integers. Model/run ids must match the task-id
character set. Use `intact-1`, `intact-2`, `intact-3`, `degraded-1` for the first
acceptance cohort, and `configuration: degraded` for the last. Run ids must be
unique. Further cohorts should use separate run directories and explicit
comparison arguments; the acceptance test reads this initial cohort from
`evals/runs/`.

From the repository root, with temp variables pointing at an owner-approved
scratch directory:

```bash
python3 evals/bench.py validate
python3 evals/bench.py score --outputs OWNER_OUTPUTS --metadata OWNER_METADATA.json
python3 evals/noise_floor.py INTACT_1.json INTACT_2.json INTACT_3.json --output evals/runs/noise-floor-tuned_on.txt
python3 evals/bench.py delta INTACT_1.json DEGRADED_1.json --intact INTACT_1.json INTACT_2.json INTACT_3.json
python3 tests/test_benchmark_discriminates.py
```

Replace file placeholders with the actual record paths printed by `score`.
Use `--partition held_out` for a separate noise report and delta when measured.
The noise report uses exclusive creation; archive the old report before creating
another. Fewer than three intact records prints `uncomputable` and exits nonzero.
No report is written on that failure.

`score` writes `evals/runs/<sha>-<model>-<prompt_sha>.json` (or an explicitly supplied
`--runs` directory), refusing overwrites or duplicate run ids. **Owner-approved
naming:** `<sha>` is SHA-256 of canonical JSON `{"run_id": ..., "outputs": ...}`,
where `outputs` maps every relative export file path to its SHA-256; it is not the
commit hash. `git_sha` stores the scored GARS commit. The run id keeps byte-identical
repeats separate. The file contains metadata above, `schema_version: 1`,
`run_sha256`, the `outputs` mapping, and `scores`:

- `tuned_on`: `state: measured`, integer `numerator` and `denominator`,
  `suite_sha256`, and `tasks` mapping id to boolean `passed` and a generic `reason`;
- `held_out`: same shape plus `seal` when measured, otherwise `state: unmeasured`
  and `reason`, **without** a numerator or denominator.

Task content and input hashes bind each suite digest. Missing task outputs fail
and remain in the denominator. No weighted aggregate across the two partitions
is published. Every printed ratio includes numerator and denominator; `0/0` is
`uncomputable`. No measured zero denominator is accepted into a run record.

**Owner-approved calculations:** equal binary task weights; noise floor is the
range (max minus min) of exactly three distinct intact repeats; intact baseline
is their arithmetic mean. Calculations use exact fractions. Compare only the
same model, prompt hash and task suite within each partition. Intact repeats
also share a GARS commit. A delta whose absolute value is at or below the floor
is `no change`. Discrimination is strictly
`degraded < mean(intact) - noise_floor`, independently per measured partition.
The committed acceptance test names each missing record in its SKIP reason;
helper fixtures used to test the arithmetic never enter `evals/runs/`.
