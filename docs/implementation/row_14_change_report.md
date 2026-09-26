# Row 14 change report — evaluator planted-lie test and smoke delta per `_system/` merge

## Round 1

Branch `build/gars-row-14-smoke-delta`, from public main
`452fe3349627c6c2aabcab7e05b975266fc75e68`. Decision record:
[0120](../decisions/0120-row-14-evaluator-smoke-delta-bench-gate.md).

**Producer and reviewer.** The producer of this round is a headless Claude Code context
(claude-opus-5-5) in an isolated clone; the reviewer is a separate fresh Claude Code context
(claude-opus-5-5) from a blind kit. They are the same model family, so review independence
rests on a fresh context and a blind kit, not on model diversity.

**What this round does not claim.** Not the row's exit: planted-lie catch 1/1 needs the sealed
lie and its first run, and `Bench:` on every `_system/` merge needs the landing. Both are
Glitch's, later. No whole-suite result is claimed: the lane runs `python3 tests/run_tests.py`
in modes A, B and C (see "Checks run" below). No smoke session was run and no smoke record is
committed; every record in this commit is synthetic fixture data labelled as such.

### Changed files (THE LANE'S SPECIFICATION item 1)

| Path | New / changed | What it holds |
|---|---|---|
| `evals/smoke/smoke.py` | new | the evaluator `evaluate()`, the record builder, and the `bundle` / `check` / `score` CLI |
| `evals/smoke/SMOKE.md` | new | the ceremony, floor rule, R-112 rules as code, schema, naming deviation, what a smoke delta does not claim, red-by-design cases, compatibility rule |
| `evals/smoke/LIE-INTERFACE.md` | new | the sealer's handoff (mirrors `evals/MUTANTS-INTERFACE.md`) |
| `evals/smoke/SEALS.md` | new | slot L01, unsealed, every cell empty (mirrors `evals/mutants.md`) |
| `evals/smoke/fixtures/` | new (protected) | `generate.py`, `README.md` (SYNTHETIC), `tree/` (pinned copy of the three tasks, inputs, RESPONSE.md), `clean/C01`, `clean/C02`, `lies/L01`–`L11` |
| `evals/runs/smoke/README.md` | new | what lives in the smoke record folder |
| `evals/runs/README.md` | changed | one appended "Smoke records (row 14)" section |
| `docs/reviews/records/README.md` | new | the review stub format |
| `gars/_system/hooks/pre-push` | changed (protected) | item 8 (a)–(f); see "Hook diff" below |
| `gars/_system/hooks/audit_trailers.py` | new (protected) | item 9 |
| `.github/workflows/ci.yml` | changed (protected) | one added step, zero removed lines |
| `tests/test_smoke_delta.py` | new | schema, evaluator, arithmetic, cohort, CLI, ten evaluator red-on-fault plants |
| `tests/test_evaluator_planted_lie.py` | new | the oracle: development set, sealed pass, first-run marker |
| `gars/tests/test_hooks_bench_smoke.py` | new | hook and audit, four hook/audit red-on-fault plants |
| `gars/tests/test_hooks_records.py` | changed | row 11's tests amended to run against valid smoke evidence |
| `README.md`, `DEVELOPMENT.md` | changed | the three enforced count claims 579 → 621; one DEVELOPMENT paragraph |
| `docs/decisions/0120-…md`, `docs/decisions/CONTEXT.md` | new / regenerated | the record; the index by `bash docs/decisions/build_index.sh` |

`evals/bench.py` is not edited (its sha256 is pinned, unchanged:
`27888b8b73748628052b62375ff1eb3c54cead906f028f0d663f06681e948755`). `install.py` and
`pre-commit` are not touched.

### Requirement → changed files → acceptance test

| Requirement | Files | Test |
|---|---|---|
| R-165 Bench on every `_system/` first-parent commit, checked by CI | pre-push, audit_trailers.py, ci.yml | `test_hooks_bench_smoke`: ceremony, side branch, straight commit refused, build-branch case, zero rule, given-commit refusal |
| R-165 Review/Session (row 11's, unchanged) | pre-push `required_trailers`, `review_session` | `test_hooks_records` (all row 11 assertions still run) |
| R-112 same model/prompt/suite; "no change" inside the floor | smoke.py | `test_smoke_delta` ArithmeticTests (1024 cases against `bench.noise_floor`/`bench.compare`), plants MODEL/PROMPT/SUITE/FLOOR/DELTA/INTERPRETATION |
| §5 trusted base: evaluator deterministic, scorer is `bench.score_task` | smoke.py, TRUSTED_EVALUATOR | `test_score_task_is_the_scorer`, `test_trusted_evaluator_mismatch_and_absence` |
| §10/§18 planted-lie test, sealed, first run | test_evaluator_planted_lie.py, LIE-INTERFACE.md, SEALS.md | development set 11/11 and 2/2; SealedPassRulesTests |

### Hook diff (item 8)

- (a) `ACTIVATION_RECORD` names 0120.
- (b) `pushed_commits` lists `rev-list --first-parent` of each outgoing `remote..local` (or the
  whole first-parent line for a new ref), after `activation_of(root, tip)`: the earliest
  first-parent commit whose tree holds the record while its first parent's does not (one
  `rev-list` plus one `cat-file --batch-check`). Everything reachable from the activation's
  first parent is exempt; no activation means `[]`. The shallow refusal, stdin validation,
  deletion rule and per-ref snapshots are kept.
- (c) `touches_system` diffs against the first parent only (`--root` for a root commit);
  `trailer_gate` uses it.
- (d) `validate_evidence(root, commit, read_record, expect_previous)` keeps
  `required_trailers` and `review_session`, requires `evals/runs/smoke/`, then calls the
  evaluator with the committed-snapshot reader, `tree_reader(root, commit)` and
  `expect_previous`; any finding refuses with every code named. `previous_bench(root, commit)`
  is the one predecessor helper; `trailer_gate` and the audit both call it.
- (e) `TRUSTED_EVALUATOR` pins both files; `load_evaluator` refuses an absent, symlinked or
  different file before loading anything.
- (f) The evaluator is loaded with `runpy` from the repository root.
- **One addition beyond (a)–(f)**: `committed_reader` now also attaches
  `read_record.listing` (new helper `committed_listing`, `git ls-tree -r` of the same snapshot).
  Item 6 requires `OUTPUT_HASH_MISMATCH` for missing or **extra** files, which single-file reads
  cannot decide. The reader's read behaviour is byte-for-byte unchanged. Recorded in 0120 as a
  choice this round made; the reviewer should judge it against "Nothing else in the hook changes".

### Row 11's tests, amended (`gars/tests/test_hooks_records.py`)

Every old assertion still runs; each amendment:

1. **Imports and setUp**: imports `seed` and `smoke_evidence` from `test_hooks_bench_smoke`;
   `setUp` stages the pinned evaluator and the three smoke tasks (`seed`). New constants
   `RUN_ID`, `BENCH` (`evals/runs/smoke/smoke-20260922-row-eleven.json`) replace
   `evals/runs/run.json`.
2. **New helper `smoke()`** writes a smoke record bound to the commit (or to another sha).
3. **`test_bench_binding_and_na`**: the `{git_sha}` stub and dict reader become committed smoke
   evidence read by `committed_reader`; the wrong-sha case asserts `BINDING_MISMATCH git_sha`;
   the `n/a` case is unchanged.
4. **`test_activation_range_history_deletion_and_each_commit`**: the first `trailer_gate`
   assertion (tip over activation) changes from `True` to `False`: `previous_bench` now reaches
   the activation commit below `remote..local`, and its missing trailers refuse the range. The
   other assertions (range, tip-only miss, deletion, deletion push, new ref, invalid payloads)
   are unchanged; a positive range (the activation carrying its own evidence) is added at the end.
5. **`activate()`** defaults `bench` to `BENCH`; **`evidence()`** writes a smoke record instead of
   `{git_sha}`.
6. **`test_production_requires_later_committed_snapshot`** unlinks `BENCH` instead of
   `evals/runs/run.json`.
7. **`test_production_bad_committed_evidence_ignores_worktree_repairs`** expects
   `BINDING_MISMATCH git_sha` where it expected `Bench git_sha does not match`.
8. **`test_production_history_replacements_preserve_checks`**: the valid message names `BENCH`.
9. **`test_committed_reader_refuses_self_ancestors_paths_and_symlinks`**: the doubled-slash
   probe is `evals//runs/smoke/x.json` (was `evals//runs/run.json`); same rule exercised.

### Red first

The tests were written against the specification and driven red before the implementation
counted as done.

**The new hook tests against the base hook** (`git show 452fe33:gars/_system/hooks/pre-push` in
a scratch copy, `python3 gars/tests/test_hooks_bench_smoke.py BenchSmokeHookTests`):

```
FAIL: test_audit_not_applicable_and_given_commit (__main__.BenchSmokeHookTests)
FAIL: test_audit_previous_chain (__main__.BenchSmokeHookTests)
FAIL: test_audit_zero_rule (__main__.BenchSmokeHookTests)
FAIL: test_build_branch_is_red_by_construction (__main__.BenchSmokeHookTests)
FAIL: test_ceremony_and_first_parent_side_branch (__main__.BenchSmokeHookTests)
FAIL: test_evidence_same_commit_non_descendant_and_bench_location (__main__.BenchSmokeHookTests)
FAIL: test_previous_bench_below_pushed_range (__main__.BenchSmokeHookTests)
ERROR: test_activation_only_on_first_parent_line (__main__.BenchSmokeHookTests)
ERROR: test_deletion_and_readdition_cannot_move_activation (__main__.BenchSmokeHookTests)
ERROR: test_dir_and_git_readers_agree (__main__.BenchSmokeHookTests)
ERROR: test_trusted_evaluator_mismatch_and_absence (__main__.BenchSmokeHookTests)
Ran 12 tests in 8.609s
FAILED (failures=7, errors=4)
```

With this round's hook: `Ran 13 tests in 83.396s` / `OK` (the thirteenth is the fault test).

**During development**, the first run of the first-parent fault did not go red
(`AssertionError: 0 == 0 : first-parent rule replaced by all-parents`): `pushed_commits` then
filtered by first-parent chain membership, so an all-parents listing was filtered back out and
the fault was invisible. The filter was changed to the specification's rule ("everything
reachable from the activation's first parent is exempt"), and the fault goes red.

**Every guard, planted in a disposable copy with byte backups** (the named test goes red, then
green after the bytes are restored):

```
red-on-fault: regrade skipped -> EvaluatorTests.test_plant_REGRADE_MISMATCH red, then green after restore
red-on-fault: counts trusted -> EvaluatorTests.test_plant_COUNT_MISMATCH red, then green after restore
red-on-fault: output hashes trusted -> EvaluatorTests.test_plant_OUTPUT_HASH_MISMATCH red, then green after restore
red-on-fault: floor trusted -> EvaluatorTests.test_plant_FLOOR_MISMATCH red, then green after restore
red-on-fault: delta trusted -> EvaluatorTests.test_plant_DELTA_MISMATCH red, then green after restore
red-on-fault: interpretation trusted -> EvaluatorTests.test_plant_INTERPRETATION_MISMATCH red, then green after restore
red-on-fault: previous not checked -> EvaluatorTests.test_plant_PREVIOUS_MISMATCH red, then green after restore
red-on-fault: model/prompt/suite equality dropped -> EvaluatorTests.test_plant_MODEL_MISMATCH red, then green after restore
red-on-fault: git_sha binding dropped -> EvaluatorTests.test_plant_BINDING_MISMATCH red, then green after restore
red-on-fault: smoke glob made recursive in the cohort test -> CohortTests.test_smoke_record_not_collected_by_cohort_glob red, then green after restore
red-on-fault: first-parent rule replaced by all-parents -> BenchSmokeHookTests.test_ceremony_and_first_parent_side_branch red, then green after restore
red-on-fault: activation searched over --all -> BenchSmokeHookTests.test_deletion_and_readdition_cannot_move_activation red, then green after restore
red-on-fault: TRUSTED_EVALUATOR check removed -> BenchSmokeHookTests.test_trusted_evaluator_mismatch_and_absence red, then green after restore
red-on-fault: audit's zero rule removed -> BenchSmokeHookTests.test_audit_zero_rule red, then green after restore
```

### Choices made where the specification left room

Recorded in 0120 under "Choices this round made where the specification left room":
the committed reader's listing; `evaluate()`'s optional `record_path`; the record under test in
a plant (the one record no other names); the §18 exit line prints `met` only when L01 is caught
**and** every clean control passes; a schema-invalid record gets only `SCHEMA` findings; the
development plants' `seal_type` is `producer_development`. Also: every value the arithmetic
checks use is the **regraded** value (never the record's own counts), and comparison records are
regraded with the bound tree's tasks only when their suite digest equals it.

**README count sentence.** The lane conditions say not to edit README's cold-clone skip sentence
and to update the count claims `tests/check_counts.py` enforces. One enforced count (`579 tests`)
sits inside that sentence, so only that token changed (`579` → `621`); the skip figures and the
rest of the sentence are untouched. The sentence's "at the 2026-09-24 merge of row 6" context is
therefore stale until the lane re-derives both figures at landing.

### Checks run (by the producer, on this macOS machine; Python 3.8.2 unless stated)

`TMPDIR`, `TEMP` and `TMP` named the scratch folder for every command.

| Command | Summary line |
|---|---|
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `clean — every current claim matches the suite` (loader: 621 tests) |
| `python3 evals/test_harness.py` | `FAILED (errors=13)` under Python 3.8.2: every error is `AttributeError` for `str.removesuffix` / `str.removeprefix` / `ast.unparse` (Python ≥ 3.9 APIs in files this row does not touch) |
| `/usr/local/bin/python3.12 evals/test_harness.py` (CI's Python) | `Ran 44 tests in 181.042s` / `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 tests/test_evaluator_planted_lie.py` | `development set (producer-written; not the §18 exit): caught 11/11; clean controls passed 2/2`; `Ran 6 tests` / `OK (skipped=1)` (the sealed set: unset) |
| `python3 tests/test_smoke_delta.py` | `Ran 23 tests in 8.584s` / `OK` (also OK under Python 3.12) |
| `python3 gars/tests/test_hooks_bench_smoke.py` | `Ran 13 tests in 83.396s` / `OK` |
| `python3 gars/tests/test_hooks_records.py` | `Ran 14 tests in 46.929s` / `OK` |
| `python3 gars/_system/hooks/audit_trailers.py --rev 452fe33…` | `trailers audit: not applicable — not activated at 452fe33; graded 0 commits and claims nothing` |
| `python3 gars/_system/hooks/audit_trailers.py` at this round's head | run after the commit (the output names the commit's own sha); it must refuse the round-1 commit with `missing Review, Bench or Session trailer` — quoted in the producer's final message |
| `ast.parse(..., feature_version=(3, 6))` | `feature_version=(3, 6) parse: 8/8 files parsed` (smoke.py, fixtures/generate.py, pre-push, audit_trailers.py, the four test modules) |

**Run by the lane, not by the producer** (lane conditions: other lanes hold this machine): the
whole suite `python3 tests/run_tests.py` in modes A (macOS, solo slot), B and C (Linux, fresh
clone), which also covers the modules this round did not run individually and that drive the
changed hook (`gars/tests/test_pre_push.py`, `gars/tests/test_hooks_gitleaks.py`,
`gars/tests/test_secret_containment.py`) and the decision-record checker
(`tests/test_decision_links_resolve.py`, which reads 0120). A red there comes back as a lane
verification finding. The README cold-clone skip figures are re-derived by the lane.

The new hook tests need `TMPDIR` naming an existing folder (row 15's `scratch` helper) and skip
without it, like row 15's; the Linux-like cold-clone skip figure therefore moves.

### Boundary verification

`evals/bench.py`, `benchmarks/`, `scripts/`, `gars/_references/`, `install.py`, `pre-commit`,
`docs/ledger.csv` and every decision record other than 0120 and the regenerated index are
unchanged. `git diff --numstat 452fe33 HEAD -- .github`: `7	0	.github/workflows/ci.yml`
(to be re-read after the commit and quoted in the final message). Records 0121–0124 are not
written; 0122 (approval of this row's protected changes) is Glitch's.

### Residual gaps — each NOT met

- **Row 14 exit, planted-lie catch 1/1**: NOT met — no sealed lie exists; SEALS.md is unsealed.
- **Row 14 exit, `Bench:` on every `_system/` merge**: NOT met — needs the landing; this branch
  is red by construction until it lands as a merge whose first parent is main.
- **Model provenance of outputs**, **bundle delivery to sessions** (driver pinned in the
  reserved 0121), **the generator leak** (Q9), **Review/Session semantics** (row 11's label),
  **the unarmed local hook** (Q7), **the pre-activation gap** (0120's lists) and **public
  credibility** (`external_human_seal`) — named in 0120 as residuals.

## Owner rulings needed

None.

## Review round 2 fixes

These are the fixes for the blind review of the round-1 commit `f37cc17`
(`docs/reviews/row_14_review.md`: APPROVE WITH CHANGES, one MAJOR, six NOTEs). The producer (a
headless Claude Code context, claude-opus-5-5) and the reviewer (a fresh Claude Code context,
claude-opus-5-5, from a blind kit) are the same model family, so review independence rests on
a fresh context and a blind kit, not on model diversity. The lane's rulings L1–L3 for this
round are recorded as the lane's in 0120's addendum of 2026-09-25.

| Finding | Changed files | Test | Result | Red-on-fault seen |
|---|---|---|---|---|
| **MAJOR**: the oracle counted a plant with a schema-invalid comparison record as caught (the evaluator reports it as `PREVIOUS_MISMATCH`/`FLOOR_MISMATCH`), so a first sealed run could print the §18 exit as met | `tests/test_evaluator_planted_lie.py` (`schema_defects`: every `evals/runs/smoke/*.json` in the evidence set must parse and pass `schema_problems`, else defective); `evals/smoke/LIE-INTERFACE.md` ("a plant whose evidence fails the schema … any record in the evidence set") | `SealedPassRulesTests.test_schema_invalid_comparison_record_is_defective`: the reviewer's case (C01 copied as L01, `unexpected_field` added to the predecessor, `lie_class` `PREVIOUS_MISMATCH`, `independent_context`), then the predecessor made unparsable | `defective 1`, `caught 0/1`, `§18 row 14 exit: planted-lie catch 0/1 — not met` | **yes, red first**: before the fix the new test failed with `AssertionError: 'caught' != 'defective'` (finding `PREVIOUS_MISMATCH … is not a valid smoke record (unexpected_field)`); green after. Also a new fault in `tests/test_smoke_delta.py` (`comparison-record schema defects ignored by the oracle`) reverts the rule in a disposable copy: red, then green after restore |
| NOTE, voluntary re-floor (lane ruling **L1**: enforce the floor rule) | `evals/smoke/smoke.py` (one check in the floor branch: `FLOOR_MISMATCH` when a floor record's predecessor shares model, prompt and suite); `gars/_system/hooks/pre-push` (`TRUSTED_EVALUATOR` re-pinned to the new `smoke.py`); `evals/smoke/fixtures/generate.py` + new `lies/L12/` and `clean/C03/`; `evals/smoke/SMOKE.md` (the floor rule and the rules list); `evals/smoke/fixtures/README.md` | `EvaluatorTests.test_plant_voluntary_refloor` (L12 caught with exactly `FLOOR_MISMATCH` naming the rule; its record states floor 2/3, delta -2/3, `no change`; C03 passes); `DevelopmentSetTests` now expects 12 plants and 3 clean controls | `caught 12/12; clean controls passed 3/3` | **yes, red first**: round 1's `smoke.py` (from `git show HEAD:`) on L12 gave `ok=True findings=[] floor=2/3 delta=-2/3 interpretation=no change`. New fault `voluntary re-floor allowed` (the check replaced by `if False:`): red, then green after restore |
| NOTE, the `--all` fault pinned one spelling (lane ruling **L3**) | `gars/tests/test_hooks_bench_smoke.py` (`git update-ref refs/heads/fixture-tip <tip>` in `test_deletion_and_readdition_cannot_move_activation`; new fault `activation searched over --all, no tip, latest add`, the reviewer's spelling) | `BenchSmokeHookFaultTests.test_hook_guards_go_red` | both `--all` spellings red, then green after restore | yes, via the fault harness (five hook/audit faults now) |
| NOTE, past records re-read at HEAD (lane ruling **L2**) | `docs/decisions/0120-…` addendum: the residual named in the lane's words | none (a residual, no guard change) | named | n/a |
| NOTE, README count inside the lane's sentence | `README.md:322` and `DEVELOPMENT.md:166,185`: only the enforced count, 621 → 623 (two tests added this round); the rest of the sentence stays the lane's to rewrite at landing, as the review asked | `python3 tests/check_counts.py` | `clean — every current claim matches the suite` | n/a |
| NOTE, 0120's eighth residual bullet is a status non-claim | none; the review said no fix is needed | — | — | — |
| NOTE, `read_record.listing` and row 11 amendment 4 | none; the review accepted both and asked that the approver of 0122 see them (change report round 1, "Hook diff" and amendment 4) | — | — | — |

**Why the MAJOR fix is in the oracle, not the evaluator.** An invalid comparison record already
refuses the gate (`PREVIOUS_MISMATCH`/`FLOOR_MISMATCH`, `ok` false), so the gate needs no change.
What was wrong was the oracle's accounting. Fixing it where the accounting happens leaves the
evaluator's verdicts untouched and needs no pin change for this finding.

**Compatibility rule (SMOKE.md, item 5).** `smoke.py` changed, so `TRUSTED_EVALUATOR` changed.
The audit at this round's head refuses for the same reason as at `f37cc17`: the build-branch
commits carry no trailers. No smoke record exists on the first-parent line, so no record's
verdict can change. The output is quoted in the producer's final message.

### Checks run by the producer this round

The lane conditions apply: no whole-suite run. Each line below is the summary as printed.

| Command | Summary |
|---|---|
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `clean — every current claim matches the suite` (623) |
| `python3 evals/test_harness.py` | Python 3.8.2 (`python3` here): `Ran 44 tests` / `FAILED (errors=13)`. All 13 are `AttributeError`s for 3.9+ APIs (`removesuffix` ×11, `removeprefix`, `ast.unparse`) in files this row does not touch. Under `python3.12`: `Ran 44 tests in 176.732s` / `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 tests/test_evaluator_planted_lie.py` | `development set (producer-written; not the §18 exit): caught 12/12; clean controls passed 3/3`; `Ran 7 tests` / `OK (skipped=1)` (the sealed set: unset); also OK under 3.12 |
| `python3 tests/test_smoke_delta.py` | `Ran 24 tests in 10.355s` / `OK`, 12 red-on-fault plants each red then green; also OK under 3.12 |
| `python3 gars/tests/test_hooks_bench_smoke.py` | `Ran 13 tests in 93.363s` / `OK`, 5 hook/audit red-on-fault plants |
| `python3 gars/tests/test_hooks_records.py` | `Ran 14 tests in 50.766s` / `OK` |
| `python3 gars/_system/hooks/audit_trailers.py --rev 452fe33…` | `trailers audit: not applicable — not activated at 452fe33; graded 0 commits and claims nothing` |
| `python3 gars/_system/hooks/audit_trailers.py` at this round's head | run after the commit; it must refuse `f37cc17` and this round's commit with `missing Review, Bench or Session trailer`. Quoted in the producer's final message |
| `ast.parse(..., feature_version=(3, 6))` | 8/8 parse: smoke.py, fixtures/generate.py, pre-push, audit_trailers.py, the four test modules |

**Run by the lane, not by the producer:** the whole suite in modes A, B and C, including
`gars/tests/test_pre_push.py`, `gars/tests/test_hooks_gitleaks.py`,
`gars/tests/test_secret_containment.py` and `tests/test_decision_links_resolve.py`, which the
review also named. The README cold-clone skip figures are the lane's.

The test runs need `TMPDIR` set to an absolute folder. The fault harnesses start their
subprocesses from a disposable copy, where a relative `TMPDIR` does not resolve. The first
`test_smoke_delta.py` run this round used a relative `TMPDIR` and went red for that reason
alone (`FileNotFoundError` in `mkdtemp`). The run above sets `TMPDIR` to an absolute path built
at run time.

### Residual gaps — each NOT met

- **Row 14 exit, planted-lie catch 1/1**: NOT met. No sealed lie exists yet.
- **Row 14 exit, `Bench:` on every `_system/` merge**: NOT met. It needs the landing.
- **L2**: past records are re-read at the audited commit, and `evals/runs/smoke/` is
  unprotected (named in 0120's addendum).
- Round 1's residuals are unchanged.

## Owner rulings needed

None.

## Landing (the lane's, 2026-09-26)

Written by the lane under the owner's standing delegation of 23 September 2026; none of it is the owner's words.

- The merge `f3abe50` has main's previous tip `acd06bc` as its first parent and the branch head `0cee6df` as its second (a3216ae plus 0121 in two records commits: `973d5ee`, then `0cee6df`, which appends the Status and Date sections the decision-links check requires; the lane's own whole-suite run on its first candidate found the gap).
- It resolves only count and index conflicts: the decision index is regenerated, README and DEVELOPMENT state 771 tests, and README's skip figures are the landing's measurements (below). The pinned files `evals/bench.py` and `evals/smoke/` are byte-identical between `452fe33` and `acd06bc`.
- Evidence at the candidate `13138f8`, whose tree differs from `f3abe50` only in README's skip sentence: on a Linux host (Python 3.13.5, a fresh clone, the host running no other suite), `Ran 771 tests … OK (skipped=81)` with `TMPDIR` set and `OK (skipped=121)` with it unset; contracts, counts, the evaluation harness and the pre-registration checks clean; on macOS (Python 3.12), `OK (skipped=14)` with Docker answering, CI set and row 5's scratch folder named, and `OK (skipped=76)` as a cold clone.
- The activation smoke record `evals/runs/smoke/smoke-20260926-row-14-activation.json`: a floor record, nine sessions (three runs of the three smoke tasks) at `f3abe50`'s tree, `claude-opus-5-5`, driven as 0121 fixes, 2026-09-26 00:14:57 to 00:19; every session exported its answer in one turn. Graded: `3/3` in each run, floor `0/1`, delta `uncomputable: no previous smoke record`. Per 0120 and 0121 this is a regression baseline on three synthetic refuse-and-flag tasks, never a measure of capability.
- The ungated gap as of `acd06bc` (0120's two commands, from `4ddb06c^1` inclusive): 41 commits on every parent and 13 on the first-parent line (`0b132f3 19599ba 3b189bc bc5f98e 30f682c fbed6b9 dcd11a9 992e9d4 71654fe aeac1e7 68f8346 7a8f967 4ddb06c`). 0120's list, as of `452fe33`, stays as written.
- 0122 approves the protected changes under the delegation; the review stub `docs/reviews/records/smoke-20260926-row-14-activation.md` binds the final review.
- The row's exit is not claimed here: the sealed planted lie (0123) is still to come.
