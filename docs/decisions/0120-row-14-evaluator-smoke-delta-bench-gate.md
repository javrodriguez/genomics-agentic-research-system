---
date: 2026-09-25
status: standing
kind: decision
touches:
  - gars/_system/hooks/pre-push
  - gars/_system/hooks/audit_trailers.py
  - evals/smoke/smoke.py
  - evals/bench.py
  - evals/smoke/SMOKE.md
  - evals/smoke/LIE-INTERFACE.md
  - evals/smoke/SEALS.md
  - evals/smoke/fixtures/
  - evals/runs/smoke/
  - evals/runs/README.md
  - docs/reviews/records/README.md
  - .github/workflows/ci.yml
  - tests/test_smoke_delta.py
  - tests/test_evaluator_planted_lie.py
  - gars/tests/test_hooks_bench_smoke.py
  - gars/tests/test_hooks_records.py
  - docs/implementation/row_14_change_report.md
symptoms:
  - _system/ commits reached main without Review, Bench or Session trailers; row 11's gate never ran in the owner's push path
  - a Bench file's git_sha was the only thing checked, so a claimed score could not be re-derived from anything committed
  - the Bench trailers CI step is red on a build branch or a pull request that touches _system
  - the Bench trailers CI step refuses a landing made by merging main into the branch and fast-forwarding
  - changing evals/bench.py or evals/smoke/smoke.py makes every Bench check refuse with untrusted evaluator
---
# Row 14: the evaluator planted-lie test and a smoke delta per `_system/` merge

## Context

Spec §18 row 14 (line 403): "evaluator planted-lie test; smoke delta (three no-cluster tasks)
per `_system/` merge", exit "planted-lie catch 1/1; `Bench:` on every `_system/` merge".
It serves R-165 (§16.3: every commit touching `_system/**` carries `Review:`, `Bench:` and
`Session:` trailers, checked at pre-push), R-112 (§11.1: deltas only between runs with the same
model and prompt, "no change" inside the noise floor), §5 (the trusted base: the model is never
in it) and §10 (independence is engineered and measured, with sealed plants).
The gap assessment classed the row MISSING: 0 of 56 `_system/`-touching commits carried
`Bench:`. Row 11's gate (0061) existed but required only that a Bench file's `git_sha` equal the
commit, and it was never armed in the owner's push path.

This branch starts from public main `452fe3349627c6c2aabcab7e05b975266fc75e68`, after rows 9
and 6 landed. The producer is a headless Claude Code context (claude-opus-5-5) in an isolated
clone; the reviewer is a separate fresh Claude Code context (claude-opus-5-5) from a blind kit.

## Decision

### Rulings (Glitch under the owner's standing delegation of 23 Sep 2026)

These rulings were given by Glitch under the owner's standing delegation of 23 September 2026;
none of the sentences below is the owner's own.

> Q1 What "the evaluator" is: the deterministic evidence evaluator of a _system/ merge's smoke record (the trusted base, section 5; the model is never in it).

> Q2 The checked unit: main's first-parent line; the merge carries the evidence for its branch. 0120 names this as a deviation from R-165's literal text ("every commit touching _system/**").

> Q3 CI enforces all three trailers, by calling row 11's own validate_evidence; each landing commits a small Review stub under docs/reviews/records/.

> Q4 The activation boundary moves from 0061 to 0120, and 0120 lists the ungated commits (below).

> Q5 evals/bench.py and evals/smoke/smoke.py are pinned by sha256 in the protected hook (TRUSTED_EVALUATOR). Cost named: a later bench.py change (row 2's landing) must update the pin, itself a _system change that runs the ceremony.

> Q6 Producer venue: accepted as the Mac. Changed condition (25 Sep, the lane's): the Codex account is at its usage limit, so the producer is a headless Claude Code context (claude-opus-5-5) in this isolated clone, and the reviewer is a separate fresh Claude Code context (claude-opus-5-5) from a blind kit. 0120 states the same-model cost: producer and reviewer are the same model family, so review independence rests on a fresh context and a blind kit, not on model diversity (the precedent of the owner program's decisions on same-model review).

> Q7 The GARS pre-push hook is NOT armed in the owner's GARS workspace; CI is authoritative; the lane runs audit_trailers.py on the merge result before each push.

> Q8 Landing order: after rows 9 and 6 (both public at 452fe3349627c6c2aabcab7e05b975266fc75e68); later _system lanes adopt the ceremony at their landing.

> Q9 The smoke tasks' input generator (benchmarks/fixtures/generate.py) names each defect, and it is a task input: accepted as a named residual, and scoped. Smoke sessions can see their answers. The smoke DELTA (merge vs previous) stays a valid regression signal because both sides share the leak, but no record may present a smoke score as a measure of capability. 0120 says so in those words.

> Q10 The planted lie is the sealer's own free choice within LIE-INTERFACE (any provable lie, "other" allowed).

> CARRIED: row 11's trailer gate never ran in the owner's push path. 0120 records the commits that reached main through gars/_system without trailers as a gap list, never as a retroactive pass, and words it as "the gap as of <sha>" so the figure cannot go stale.

**The deviation Q2 names.** R-165's text says "every commit touching `_system/**`". This row
checks main's **first-parent line** instead: a side-branch commit reaches main only through a
merge, and that merge carries the evidence for its whole branch. The literal rule would demand
evidence for every build commit of every branch, which no landing has ever produced.

**The same-model cost Q6 names.** The producer (this context) and the reviewer are the same
model family, so review independence here rests on a fresh context and a blind kit, not on
model diversity.

**What Q9 means for every record.** Smoke sessions can see their answers. The smoke delta
stays a valid regression signal because both sides share the leak, but no record may present a
smoke score as a measure of capability.

### The gap as of 452fe33 (Q4 and CARRIED)

The activation boundary moves from 0061 to this record. Everything reachable from the first
parent of the first-parent commit that adds this record is exempt, including every commit that
reached main between 0061's activation and this row. Those commits are a **gap**, recorded here
and never a retroactive pass. The lane's measurement at CP0, over the range starting at
`4ddb06c^1` inclusive, at public main `452fe33`:

**The gap as of 452fe33, every parent** — `git log --format=%H 4ddb06c^1..452fe33 -- gars/_system`,
31 commits:
bc5f98e 9e55220 945dcee 12b26f7 75f0a90 ad70a1c a8b54e5 b98f298 7edc946 e367a41 2197242 e534198
b46e79b 6039276 9def5b3 94249c5 fbed6b9 554c984 9164bae 2429bc6 dcd11a9 992e9d4 71654fe aeac1e7
68f8346 7a8f967 4ddb06c b8be4eb 39f74a0 d3325a5 e33f34e

**The gap as of 452fe33, first parent** — `git rev-list --first-parent 4ddb06c^1..452fe33`,
each diffed against its first parent for a `_system/` path, 10 commits:
bc5f98e 30f682c fbed6b9 dcd11a9 992e9d4 71654fe aeac1e7 68f8346 7a8f967 4ddb06c

Four every-parent commits (b8be4eb 39f74a0 d3325a5 e33f34e) predate 4ddb06c and arrive through
later merges. Glitch re-measures at landing and adds the landing figure in its own record; this
list is never edited to match a later main.

### The lane's specification (the lane's, 25 Sep, under the owner's standing delegation)

Everything in this subsection is the lane's specification of the rulings above, as built.

- **The smoke suite** is exactly `batch-confounded`, `pseudoreplicates` and
  `single-replicate`, each loaded one by one with `bench.validate_task` against the bound tree
  (never `bench.load_tasks`: the two nf-core tasks' pins go stale whenever a wrapper changes),
  scored only with `bench.score_task`; `suite_sha256 = bench.digest({id: task})`.
- **The prompt bundle** `prompt_sha256` is the canonical-JSON sha256 of RESPONSE.md's hash and
  each task's question and hashed inputs, re-derivable from any tree (`smoke.py bundle`).
- **The record** is schema `gars-smoke/1`, closed, one file per landing at
  `evals/runs/smoke/<run_id>.json` with outputs under `outputs/<run_id>/`. A floor record has
  three runs at its `git_sha`; an ordinary record one. The rules R-112 becomes in code, the
  finding codes and the ceremony are in `evals/smoke/SMOKE.md`.
- **The evaluator** `smoke.evaluate(record_bytes, read_evidence, read_tree, bound_commit,
  bound_parent, expect_previous)` regrades every retained output against the task contracts at
  the bound commit, re-derives counts, floor, delta, interpretation and the predecessor, reports
  every finding and counts what it graded against what it saw.
- **The hook** (`gars/_system/hooks/pre-push`, protected): `ACTIVATION_RECORD` is this record;
  pushed commits are the first-parent commits of `remote..local` after an activation found as the
  earliest first-parent commit whose tree holds this record while its first parent's does not;
  "touches `_system/`" is decided by the diff against the first parent; `validate_evidence` keeps
  `required_trailers` and `review_session` and, for `Bench:`, requires `evals/runs/smoke/`, checks
  `TRUSTED_EVALUATOR` before loading anything, loads the evaluator with `runpy` from the
  repository root and refuses on any finding, naming each code; `previous_bench` is the one
  predecessor helper that `trailer_gate` and the audit share.
- **The audit** (`gars/_system/hooks/audit_trailers.py`, protected) walks the first-parent line
  from activation to `--rev` (default HEAD) and calls the hook's own `validate_evidence` for each
  checked commit; a zero-graded audit after activation fails. **A build branch is red by
  construction**: its round-1 commit adds this record and changes the hook, so it is the
  activation and a checked commit without trailers. The gate turns green only as a merge whose
  first parent is main.
- **CI**: one added step, "Bench trailers (R-165, row 14)", in the `tests` job.
- **The compatibility rule**: every CI run re-grades every past record with HEAD's `smoke.py` and
  `bench.py` (task files from each record's own `git_sha`). A change to either file or to the pin
  must leave every existing verdict unchanged, proved by the full audit walk before the push that
  carries it; a change that cannot needs a protected amendment to the audit with its own approval
  record, never an edited record.

### Choices this round made where the specification left room

1. **The committed-snapshot reader gains a listing.** `committed_reader` in the hook now also
   carries `read_record.listing(prefix)` (`committed_listing`, `git ls-tree -r` of the same
   snapshot), because item 6's "missing or extra files" cannot be decided from single-file reads.
   Its read behaviour is unchanged. A reader without a listing is an `UNREADABLE` finding.
2. **`evaluate()` takes an optional `record_path`.** The hook passes the Bench trailer's path, so
   `BINDING_MISMATCH path` compares the record's own `path` with the file it was read from.
3. **The record under test in a plant** is the one record that no other record in its evidence
   names as `previous` or `floor.record` (LIE-INTERFACE.md), because the closed `expected.json`
   field list names no record.
4. **The §18 exit line prints `met` only when L01 is caught and every clean control passes**: a
   refuse-everything evaluator would otherwise meet it.
5. **A schema-invalid record gets only its `SCHEMA` findings**; the semantic checks need a valid
   record. Comparison records are regraded with the bound tree's tasks only when their suite
   digest equals the bound tree's (the digest covers each task's contract and input hashes).
6. **The producer's development plants** carry `seal_type` `producer_development`, a value the
   sealed pass does not accept.

### Threat model

Covered: a producer (human or model) landing a `_system/` change must not be able to
(1) land it on main's first-parent line without a Bench record the evaluator accepts, as seen by
CI on the next push; (2) claim a smoke result the retained outputs do not regrade to under the
task contracts at the merge's own tree; (3) claim a floor, delta, interpretation or predecessor
the named records do not support; (4) compare across a model, prompt or suite change; (5) bind a
record to another commit; (6) weaken the scorer or evaluator without a protected hook change;
(7) hide a refusal as a pass (every finding printed; zero-graded audits fail).

What the checks bind, exactly: the retained `response.json` bytes, their grading under the
committed task contracts, the arithmetic, and the chain of records.

## What this does not close

- **That the outputs came from a model session at all.** Transcripts are private and bound only
  by their sha256; correct outputs typed by hand pass.
- **That the session received exactly the bundle.** The driver is owner-side tooling, pinned by
  sha in the reserved record 0121 (Glitch's, not this row's).
- **The task inputs' generator naming its fixtures** (Q9): a leak into the sessions, shared with
  row 2's cohort. A smoke score is never a measure of capability.
- **Review and Session semantics** are row 11's, unchanged: a label, with no session registry.
- **The local hook is not armed in the owner's push path** (Q7): CI enforces after the push, not
  before it.
- **Commits before activation**: the gap list above.
- **Public credibility**: an `independent_context` seal supports development only; public claims
  need `external_human_seal` (§21 Q9).
- **The row's exit** — planted-lie catch 1/1 on a sealed lie, and `Bench:` on the landing — is
  not met by this record; the sealed lie, its run and the landing are Glitch's. The approval of
  this row's protected changes is the reserved record 0122, not written by the producer.

## Test

- `python3 tests/test_evaluator_planted_lie.py` — the producer's development set prints
  `development set (producer-written; not the §18 exit): caught 11/11; clean controls passed 2/2`;
  the sealed pass refuses with 0 lies, 0 clean controls or a changed fingerprint, and prints the
  §18 exit line only on its first run. Fails if any guard of the evaluator is removed.
- `python3 tests/test_smoke_delta.py` — schema, every finding code with its plant and clean twin,
  arithmetic against `bench.noise_floor` and `bench.compare`, the CLI, the cohort glob, and ten
  red-on-fault plants (regrade skipped, counts, hashes, floor, delta, interpretation, previous,
  model/prompt/suite equality, `git_sha` binding, a recursive cohort glob), each red then green.
- `python3 gars/tests/test_hooks_bench_smoke.py` — first-parent semantics, activation, deletion,
  shallow history, `TRUSTED_EVALUATOR`, evidence placement, the audit's zero rule, the chain and
  the build-branch case, with four hook/audit red-on-fault plants.
- `python3 gars/tests/test_hooks_records.py` — row 11's assertions, amended to run against
  valid smoke evidence.
- `python3 gars/_system/hooks/audit_trailers.py --rev 452fe3349627c6c2aabcab7e05b975266fc75e68`
  prints `not applicable — not activated at 452fe33`; at this branch's head it refuses the
  round-1 commit (`missing Review, Bench or Session trailer`).

## Status

Standing. Implemented on `build/gars-row-14-smoke-delta` in round 1; not landed, not approved.
The protected changes (the hook, the audit, CI, `evals/smoke/fixtures/` and this record) await
the reserved approval record 0122.

## Date

2026-09-25

## Addendum 2026-09-25 — review round 2

Appended after the bytes above, which are unchanged. The blind review of the round-1 commit
(`f37cc17`) returned APPROVE WITH CHANGES: one MAJOR and six NOTEs. The producer and the
reviewer are the same model family (claude-opus-5-5), so review independence rests on a fresh
context and a blind kit, not on model diversity.

### Lane rulings for this round (the lane's, 25 Sep 2026, under the owner's standing delegation; not the owner's words)

- **L1 (voluntary re-floor).** The floor rule is enforced, not only documented. A record may be
  a floor record (three runs, `floor.record` its own path) only when `previous` is null (the
  first record after activation) or when at least one of `model`, `prompt_sha256` or
  `suite_sha256` differs from its predecessor's; otherwise the evaluator reports
  `FLOOR_MISMATCH` naming the rule.
- **L2 (past records re-read at HEAD).** Named here as a residual, in the lane's words: every
  audit re-reads each past record and its outputs from the audited commit, and
  `evals/runs/smoke/` is not a protected path, so a later non-_system commit could rewrite a
  past record chain self-consistently; protecting that folder is a guard change outside this
  row's boundaries. The guard is not changed.
- **L3 (the `--all` fault).** The activation test points a branch ref at the fixture tip, so a
  `log --all` spelling of the fault sees the history, and that spelling is shown red too.

### What changed

- **The oracle's defective rule (the MAJOR).** A plant is defective when *any* smoke record in
  its evidence set is not JSON or fails the closed schema, not only the record under test. A
  schema-invalid comparison record reaches the verdict as `PREVIOUS_MISMATCH` or
  `FLOOR_MISMATCH`, which the round-1 oracle counted as caught, so a first sealed run could
  have printed the §18 exit as met on a defective plant. `tests/test_evaluator_planted_lie.py`
  now reads the whole set (`schema_defects`); `evals/smoke/LIE-INTERFACE.md` says "a plant
  whose evidence fails the schema", matching the specification's item 12. The evaluator's
  verdict is unchanged by this fix.
- **The floor rule (L1)** is one added check in `evals/smoke/smoke.py`. The producer's
  development set gains `lies/L12` (a second `FLOOR_MISMATCH` plant: a self-floor with model,
  prompt and suite unchanged, whose 2/3 floor turns a -2/3 decrease into `no change`) and its
  clean twin `clean/C03` (a re-floor at a model change, delta uncomputable). The development
  line is now `caught 12/12; clean controls passed 3/3`.
- **`TRUSTED_EVALUATOR`** in `gars/_system/hooks/pre-push` is re-pinned to the new `smoke.py`
  bytes; `evals/bench.py` and its pin are unchanged. **Compatibility rule:** the audit over the
  full activation..HEAD walk refuses at this branch's head for the same reason before and after
  the change (the build-branch commits carry no trailers), and no smoke record exists on the
  line yet, so no record's verdict can change. The L1 check can refuse only a record that is a
  floor record with an unchanged predecessor; no such record exists.

### Residuals added

- The L2 residual above.
- The defective rule reads records only under `evals/runs/smoke/*.json` in the evidence set,
  which is the only place the closed schema lets a record path point.

### Status

Unchanged: standing, not landed, not approved. The protected changes, including this round's
`TRUSTED_EVALUATOR` pin and the new fixtures, await the reserved approval record 0122.
