# Smoke delta per `_system/` merge (row 14, R-165 and R-112)

Every commit on main's first-parent line that touches a `_system/` path (the diff against its
first parent decides) carries three trailers — `Review:`, `Bench:` and `Session:` — and its
`Bench:` names a smoke record that the deterministic evaluator `evals/smoke/smoke.py` accepts.
CI checks this on every push with `python3 gars/_system/hooks/audit_trailers.py`; the local
pre-push hook runs the same `validate_evidence` when it is armed. The rulings and their
reasoning are in `docs/decisions/0120-row-14-evaluator-smoke-delta-bench-gate.md`.

## What a smoke delta is, and what it does not claim

The smoke suite is exactly the three tuned-on refuse-and-flag tasks of `benchmarks/tasks/`:
`batch-confounded`, `pseudoreplicates` and `single-replicate`, each loaded one by one with
`bench.validate_task` against the tree being scored and graded with `bench.score_task`. Its
delta (this merge's run-1 value minus the previous record's run-1 value) is a **regression
signal, not a capability score**. The tasks are three synthetic design fixtures, and their
input generator (`benchmarks/fixtures/generate.py`, itself a task input) names each defect, so a
smoke session can see its answer. Both sides of a delta share that leak, which is why the delta
stays a valid regression signal; no record may present a smoke score as a measure of capability.

## The per-merge ceremony, in order

1. **Choose the run id**: `smoke-YYYYMMDD-<slug>` (lower-case letters, digits and hyphens).
   The record will be `evals/runs/smoke/<run_id>.json` and the review stub
   `docs/reviews/records/<run_id>.md`.
2. **Make the merge M** with the trailers, from a message file: `git commit -F <file>`, whose
   final paragraph is exactly
   ```
   Review: docs/reviews/records/<run_id>.md
   Bench: evals/runs/smoke/<run_id>.json
   Session: <producer session id>
   ```
   M's **first parent must be main's previous tip**. A "merge main into the branch, then
   fast-forward" landing puts the build commits on the first-parent line, and the audit refuses
   it (each build commit touching `_system/` would need its own evidence).
3. **Run the three sessions at M's tree**, one per task, each given the prompt bundle
   (`python3 evals/smoke/smoke.py bundle --tree <M's tree>` prints its `prompt_sha256`). Each
   session exports one `response.json`. The driver is owner-side tooling, outside this row.
4. **Score**: `python3 evals/smoke/smoke.py score --tree <M's tree> --outputs <dir> --run-id <id>
   --git-sha <M> --parent-sha <M^1> --model <model> --transcripts <json> --resource <json>
   --previous <path|none> --floor <path|self> --out-root <repository root>`. `<dir>` holds
   `run-1/<task>/response.json` (and `run-2`, `run-3` for a floor record); the two JSON files map
   each run label to its per-task transcript hashes and its `resource` block. `score` refuses to
   overwrite anything, writes the record and the retained outputs, then runs the evaluator on
   what it wrote and refuses (deleting nothing, printing the findings) if the verdict is not ok.
   `--previous` is the Bench path of the nearest earlier checked first-parent commit (`none`
   only for the first record after activation); `--floor` is that record's floor, or `self`.
5. **Commit the evidence in ONE child commit of M** holding the record, its outputs and the
   review stub, and touching nothing under `_system/`.
6. **Run `python3 gars/_system/hooks/audit_trailers.py`** on that child; it must print
   `verified` for M and exit 0.
7. **Push both.**

The review itself stays outside the repository; the stub's format is in
`docs/reviews/records/README.md`.

## The floor rule

A **floor record** carries three runs at its own `git_sha` and names itself as its floor
(`floor.record` is its own path); its floor value is the range of its three run values
(`bench.noise_floor`'s arithmetic). Run a floor at activation and whenever the model, the
prompt bundle or the suite changes, and **only** then: a record may be a floor record only when
`previous` is `null` (the first record after activation) or when at least one of `model`,
`prompt_sha256` or `suite_sha256` differs from its predecessor's. A voluntary re-floor, with all
three unchanged, would let a landing widen the floor its own delta is read against and turn a
real decrease into `no change`; the evaluator refuses it with `FLOOR_MISMATCH`. An **ordinary record** carries one run and names the floor
its predecessor names. Its value is its run-1 `numerator/denominator`.

## The rules the evaluator enforces (R-112, as code)

- `floor.value` is `max - min` of the floor record's three run values;
- `delta` is this record's run-1 value minus the previous record's run-1 value, as signed
  fraction text `a/b` in lowest terms (`0/1` for zero);
- `interpretation` is `no change` when `|delta| <= floor.value`, else `increase` or `decrease`
  (`bench.compare`'s rule);
- the floor record, the previous record and this record share `model`, `prompt_sha256` and
  `suite_sha256`; otherwise this record must itself be a floor record, its `delta` is
  `uncomputable: changed <field>[, <field>]` and its `interpretation` is `uncomputable`;
- a floor record whose predecessor shares all three of `model`, `prompt_sha256` and
  `suite_sha256` is refused (`FLOOR_MISMATCH`): a floor only at activation or at a change;
- `previous` is the Bench path of the nearest earlier checked first-parent commit (in dir mode,
  the `--expect-previous` argument), and `null` only for the first record after activation,
  whose `delta` is `uncomputable: no previous smoke record`;
- every value used above is the **regraded** value: each retained `response.json` is hashed
  against the manifest and graded again with `bench.score_task` against the task contracts at
  the record's own `git_sha`, never taken from the record's own counts. A comparison record is
  regraded the same way when its suite digest equals the bound tree's.

The evaluator reports every finding it can derive, never only the first, with one of these
codes: `SCHEMA`, `BINDING_MISMATCH` (`git_sha`, `parent_sha`, `path`, `run_id`),
`SUITE_MISMATCH`, `PROMPT_MISMATCH`, `MODEL_MISMATCH`, `OUTPUT_HASH_MISMATCH` (bytes against
the manifest, missing or extra files), `REGRADE_MISMATCH`, `COUNT_MISMATCH`, `FLOOR_MISMATCH`,
`DELTA_MISMATCH`, `INTERPRETATION_MISMATCH`, `PREVIOUS_MISMATCH`, `UNREADABLE`. A record that
fails the closed schema gets its `SCHEMA` findings only; the semantic checks need a valid record.
Its verdict also counts what it graded against what it saw (`records_read` of `records_named`,
`tasks_regraded`, `outputs_hashed`), and `ok` is true only with zero findings.

`python3 evals/smoke/smoke.py check --record <file> --evidence <dir> --tree <dir>
--bound-commit <sha> --bound-parent <sha> (--expect-previous <path> | --first)` runs the same
evaluator over folders: exit 0 ok, 1 findings, 2 unusable input.

## The record (schema `gars-smoke/1`, closed)

`schema`, `kind` (`smoke`), `path`, `run_id`, `git_sha`, `parent_sha`, `model`,
`prompt_sha256`, `suite {task_ids, suite_sha256}`, `runs` (1 or 3 of `{run_label, outputs,
tasks, numerator, denominator, transcript_sha256, resource}`), `floor {record, value}`,
`previous`, `delta`, `interpretation`. Unknown or missing fields are `SCHEMA` findings.
`prompt_sha256` is the sha256 of the canonical JSON (as `bench.canonical`)
`{"response_md_sha256": ..., "tasks": {id: {"question": ..., "inputs": [{"path", "sha256"}...]}}}`,
so any tree re-derives it. `suite_sha256` is `bench.digest({id: task})` of the three tasks.
Retained outputs live at `evals/runs/smoke/outputs/<run_id>/<run_label>/<task_id>/response.json`
and nothing else is under that folder.

**Naming deviation from R-112.** R-112 names a run file by its commit sha. A record committed
in M's child cannot carry M's sha in a name chosen before M exists, so the file is named by its
run id and `git_sha` binds the commit inside the record.

**Transcripts** stay private owner evidence. A record carries only each session transcript's
sha256, so the repository proves which transcript is claimed, not what it says.

## Red by design

- **A build branch** whose first commit adds 0120 and changes the hook is the activation *and* a
  checked commit without trailers: the audit at its head refuses it, and at its base prints
  `not applicable — not activated at <sha7>`. The gate turns green only at the landing, as a
  merge whose first parent is main.
- **A pull request's synthetic merge ref** that touches `_system/` is a checked commit with no
  trailers of its own, so CI's audit step is red there by design (fail-closed).

## The compatibility rule

Every CI run re-grades every past record with HEAD's `smoke.py` and `bench.py`; the task files
always come from each record's own `git_sha`. A change to either file, or to the
`TRUSTED_EVALUATOR` pin in `gars/_system/hooks/pre-push`, must leave every existing record's
verdict unchanged, proved by running `python3 gars/_system/hooks/audit_trailers.py` over the full
activation..HEAD walk before the push that carries the change. A change that cannot meet this
(for example a new `validate_task` field an old task file lacks) needs a protected amendment to
the audit — records before a named commit graded by the evaluator pinned at their own tree —
with its own approval record. It is never met by editing a record.

Coupling: `tests/test_smoke_delta.py` drives `bench.noise_floor` and `bench.compare` with
`bench.validate_record` patched. A change to `compatible()`, `validate_record()` or the bench
record schema must re-run that test and, if it goes red, amend its fixture helper.
