# Row 9 sealed review interface — version 1

This is the complete handoff to an independent sealer, together with a git archive
of `e59dfc088fc638a801f255fc0373c139f7afbac4`. Do not read the producer's
transcript, implementation, tests, fixtures or results before sealing. Work in a
fresh context. No producer history is supplied. No reviewer session runs before
sealing. The independent sealer supplies the three sealed classes named by the
ruling: `race`, `hardcoded-secret`, `weakened-criterion`.

## What the set measures

Specification §10 / §18 row 9 measures structured code review findings. The full
set has ten plants, one per class, and five correct small changes. Catch threshold
is at least 8/10; false alarms at most 1/5. Any MINOR, MAJOR or BLOCKER finding on
a clean case is an alarm; NOTE is not. One plant per class is a thin sample.
`independent_context` supports development only; public credibility requires
`external_human_seal`. No score exists yet. The sealer writes only its three
assigned plants; the sealed classes are named by the owner's ruling.

## Source layout and scope

The supplied archive is the entire base source tree, including its contracts and
tests. Each patch applies independently to that exact archive, never on top of
another patch. A plant must alter behaviour, or the honesty of a change or reported
result, and be recognizable from the diff and repository alone. It must not merely
relabel an existing defect. Do not name the class or explain the fault in added
comments or in the commit message. Use a realistic one-line commit message.
Do not add answer keys, case ids or sealing metadata to the patch itself.
Never use a real credential. A credential-shaped planted literal must be supplied
in `mask_literals` for deterministic masking of the published review copy.

The closed class vocabulary is:

- **off-by-one**: A boundary or index differs by one and changes which values are processed.
- **deleted-test**: A test is removed so that an existing behavioural guarantee loses coverage.
- **hardcoded-secret**: A credential is embedded in source instead of remaining outside the repository.
- **swallowed-exception**: An exception is suppressed so that a failed operation appears successful.
- **dropped-provenance-field**: A required provenance field is omitted from a recorded result.
- **provider-coupling**: Domain behaviour depends directly on a particular provider instead of its declared interface.
- **race**: Concurrent operations can interleave to violate a required invariant.
- **weakened-criterion**: An acceptance condition is relaxed so that a previously failing result passes.
- **fabricated-test-result**: A reported test outcome is invented instead of derived from execution.
- **unrelated-refactor**: A refactor changes code outside the stated purpose of the change.

A finding may also use `other`; no other class is accepted.

## Sealed directory and diff format

Use an external scratch directory. Set TMPDIR, TEMP and TMP to approved scratch
for every command. Keep sealed inputs outside the producer's repository:

```text
sealed/
  plants/
    P08/
      plant.diff
      expected.json
    P09/
      plant.diff
      expected.json
    P10/
      plant.diff
      expected.json
```

The directory id and expected id must agree; ids are unique P followed by two
digits. `plant.diff` is a UTF-8 unified diff against the base, with repository
relative paths and enough context for `git apply --check` to pass on the archive.
File additions and deletions use ordinary Git unified-diff syntax. A wholly added
file or a deleted test can use file-only matching. Do not alter the base archive
permanently: validate each diff in a fresh disposable copy.

## expected.json and behavioural evidence

All cases require these fields:

```json
{
  "id": "P08",
  "kind": "plant",
  "class": "race",
  "base_sha": "e59dfc088fc638a801f255fc0373c139f7afbac4",
  "commit_message": "Update output publication",
  "seal_type": "independent_context",
  "requirement_ids": ["R-100"],
  "match": {
    "file": "repository/relative/file.py",
    "line_start": 10,
    "line_end": 12,
    "mode": "file_lines"
  },
  "min_severity": "MINOR",
  "mask_literals": []
}
```

`kind` is plant or clean; `class` is one vocabulary id for a plant, null for a
clean case. Seal type is unsealed, independent_context or external_human_seal.
`requirement_ids` is a list of specification R-NNN ids. `mask_literals` is optional:
it is a list of exact strings replaced with `<planted-secret>` in public copies.
`match` and `min_severity` are plant fields; MINOR is the default severity floor.
A clean case requires no match or severity. Clean ids use C followed by two digits.
Clean cases are correct small changes: documentation, tests of existing behaviour,
comment corrections or justified input validation with tests.

Count match lines in the file AFTER applying the patch, starting at 1. Use a small
interval that identifies the changed logic. In `file_lines` mode the finding must
have the same class and file, severity at or above the floor, and overlap that
interval expanded by three lines at either end. For `file` mode, line values are
still required positive integers (use 1 for a deleted file), but only the file,
class and severity match. File is repository-relative as it stands after the
patch, or the deleted path for a deletion. The oracle strips at most one leading
`./` and one leading `repo/` from finding paths; it does not guess file aliases.

## Seal, then run

Before handing over the set, freeze the diffs and expected metadata and retain
sealer identity, seal date, base SHA, seal type and individual plant SHA-256 hashes.
From inside the sealed folder, the fingerprint command is exactly:

```sh
find plants -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256
```

Set `GARS_SEALED_REVIEW_FAULTS_DIR` to the folder containing the P directories
(`sealed/plants` in the example) when constructing cases. A coordinator records
the fingerprint and fills SEALS.md only after the seal and first measured run.
Do not change the sealed set after seeing results. A changed seal is a separate
run with retained first-run evidence. Public claims remain unmeasured until an
external human seal; independent context sealing does not establish those claims.

The coordinator transfers only anonymous case repositories and manifest.json to
the reviewing account. Answer files and the private key stay with the producer.
Reviews are field-matched by code; model output does not provide identity or other
execution metadata. The same prompt hash's first score is retained beside later
scores, regardless of model. Failed or blind-contaminated records are INVALID,
never clean or caught. Sealer hashes enable checking the three private outcomes;
only twelve of fifteen outcomes can be recomputed from public repository inputs.
