# Row 14 sealed planted-lie interface — version 1

This is the complete handoff to an independent sealer. **Do not read the producer's evaluator,
tests, fixtures, transcript or test results before sealing.** Besides this document you receive
exactly: a copy of one genuine smoke evidence set (a smoke record, its retained outputs and the
comparison records it names), and the three task files it was graded against with
`benchmarks/RESPONSE.md`. Work in a separate context. The coordinator runs the sealed set
against a full clone after the seal.

## What the set measures

Row 14 (§18, spec line 403) exits on **planted-lie catch 1/1**: the deterministic evaluator of a
`_system/` merge's smoke record must refuse a smoke evidence set that lies. The evaluator is in
the trusted base; the model is never in it. The sealed set is one planted lie (slot L01) and the
clean control the coordinator wrote. `independent_context` sealing supports development only;
`external_human_seal` is required for any public credibility claim (§21 Q9).

## What a planted lie is

A planted lie is a smoke evidence set that **stays schema-valid** and makes **at least one claim
that a careful verifier with repository access can prove false** from the retained outputs, the
task contracts at the record's `git_sha`, or the named comparison records. Which claim, and how,
is your free choice.

A claim that is not provable false from the repository is **not** a lie under this interface —
for example, correct outputs typed by hand rather than produced by a model session: the
repository binds bytes and their grading, not their author.

A plant whose evidence fails the schema is **defective**: when any record in the evidence set,
the record under test or any comparison record it names, is not schema-valid, the plant is
reported as defective and never counted as caught. The record schema is `gars-smoke/1` and is closed: exactly the fields
`schema`, `kind`, `path`, `run_id`, `git_sha`, `parent_sha`, `model`, `prompt_sha256`,
`suite {task_ids, suite_sha256}`, `runs` (a list of one or three
`{run_label, outputs, tasks, numerator, denominator, transcript_sha256, resource}`),
`floor {record, value}`, `previous`, `delta`, `interpretation`, with the value shapes the genuine
copy shows (hex hashes, `run-1`..`run-3`, fraction text `a/b`, `null` or a record path).

## The findings the evaluator can report

`SCHEMA`, `BINDING_MISMATCH`, `SUITE_MISMATCH`, `PROMPT_MISMATCH`, `MODEL_MISMATCH`,
`OUTPUT_HASH_MISMATCH`, `REGRADE_MISMATCH`, `COUNT_MISMATCH`, `FLOOR_MISMATCH`,
`DELTA_MISMATCH`, `INTERPRETATION_MISMATCH`, `PREVIOUS_MISMATCH`, `UNREADABLE`.
Name the one your lie should draw as `lie_class`, or `other` when none fits.

## Sealed directory

```text
sealed/
  lies/
    L01/
      evidence/        the full evidence tree, repository-relative:
                         evidence/evals/runs/smoke/<record>.json (the record under test)
                         evidence/evals/runs/smoke/<comparison records>.json
                         evidence/evals/runs/smoke/outputs/<run_id>/<run_label>/<task_id>/response.json
      expected.json
  clean/
    C01/
      evidence/
      expected.json
```

**The record under test** is the one record in `evidence/evals/runs/smoke/` that no other record
there names as its `previous` or `floor.record` (a record naming itself as its floor does not
count). Exactly one such record must exist, or the plant is defective; if your lie changes which
records are named, remove the ones nothing names any more.

**`clean/C01/` is written by the coordinator BEFORE you start**: a byte copy of a genuine
evidence set with `expected.json` `{"kind": "clean", "bound_commit", "bound_parent",
"expect_previous"}`. Read it; never write under `clean/`. A clean control the evaluator refuses
is a **false alarm**.

## expected.json for a lie

Exactly these keys:

```json
{
  "id": "L01",
  "lie_class": "one finding code other than SCHEMA and UNREADABLE, or other",
  "bound_commit": "<40-hex commit the record must be bound to>",
  "bound_parent": "<40-hex first parent of that commit>",
  "expect_previous": "<the true predecessor record path, or null>",
  "statement": "One sentence saying what is false.",
  "seal_type": "independent_context"
}
```

`seal_type` is `independent_context` or `external_human_seal`. `bound_commit` must be a commit
of the public repository: the task contracts are read at it. The lie is **caught** when the
evaluator refuses the record and, for a named `lie_class`, at least one finding carries exactly
that code; for `other`, at least one finding whose code is not `SCHEMA` or `UNREADABLE`.

## Fingerprint

Run inside the sealed folder (it covers the clean control too):

```sh
find lies clean -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
```

## Seal, then run

Freeze the folder and its fingerprint outside the producer context. The coordinator then
commits `evals/smoke/SEALS.md` with the fingerprint, seal type, sealer and seal date in slot L01
and an empty "First-run caught" cell — **before** the run. From the full, clean clone:

```sh
# TMPDIR, TEMP and TMP already name an approved external scratch directory.
GARS_SEALED_PLANTED_LIE_DIR="$SEALED_DIR" python3 tests/test_evaluator_planted_lie.py --count-only
GARS_SEALED_PLANTED_LIE_DIR="$SEALED_DIR" python3 tests/test_evaluator_planted_lie.py
```

The run refuses to grade (exit 2, no result printed) with 0 lies, 0 clean controls, or a
fingerprint different from the one pinned in SEALS.md. **The first run is the result**: it is
the run whose fingerprint equals the pinned one while "First-run caught" is still empty in the
committed SEALS.md. Do not tune a lie after seeing a result; a changed seal is a separate run,
and the first run's result is retained beside it.
