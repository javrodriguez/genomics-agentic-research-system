# Row 1 change report

2026-09-13 · branch `build/gars-row-01-design` · producer implementation, not approval.

**Producer run, 13 Sep:** sealed design recall was SKIPPED because
`GARS_SEALED_DESIGN_FIXTURES` is unset. No sealed fixture was created, searched for,
or inspected. Full §7.2 acceptance (9/9) is also unmeasured. The Row 1 threshold
remains 3/3. The reviewer's subsequent fresh-agent run is the R-160 evidence of record (see 14 Sep withdrawal below).

The following requirement table and regression details retain the 13 Sep ec2006c
snapshot. Current review-round evidence and totals appear at the end.

| Requirement | Changed files | Acceptance test | Result |
|---|---|---|---|
| R-072 | Stage-01 helper/contract, config schema, decision 0043, both test files, demo config | `DevelopmentDesignTests` (15 unsealed cases); `SealedDesignTests.test_row_1_recall` | Owner 2A implemented: subject nesting with explicit pairing, required replication unit and release, no inferred defaults or registry validation, design-check JSON with write gates and content re-read. Existing batch/strandedness/duplicate checks retained. Development cases pass; sealed recall SKIPPED; full 9/9 remains unmeasured. |
| R-143 | Stage-01 helper/contract, both test files | `test_atac_floor_per_condition`, `test_atac_clean`, `AtacseqWrapperTests` | Development checks pass: two distinct biological sample IDs per ATAC condition. Existing wrapper positive fixture now has two per condition and corresponding REP1/REP2 outputs. Pipeline-dependent prepare test skips. |
| R-114 (Row 1 only) | `tests/test_stage01_design.py`, `docs/ledger.csv` | `SealedDesignTests.test_row_1_recall` | Interface implemented; sealed acceptance SKIPPED. Docstring specifies project layout and expected.json. Checks exact reason plus diagnostic, exit 1, and ok=false; unrelated refusal cannot count. Seal types recorded by runner; public evidence requires 3 external-human seals. |
| R-160 | `gars/AGENTS.md`, `gars/CLAUDE.md` | Fresh collaboration process `/root/cold_session_2a`, no inherited turns; supplied only two entry file paths | Answered the documented commands and repository-root directory; producer executed those commands successfully. Exact procedure below. |
| R-167 (ledger startup) | `docs/ledger.csv` | CSV inspection | Required seven columns present, plus fixture/seal metadata. Every new development fixture and the expanded ATAC fixture is explicitly unsealed. Hours and dollars are unknown/unmetered, not zero. |
| R-117 (empty table only) | `README.md` | Fixed-row table inspection | All seven metric rows present, numbers/dates unmeasured. No public score claimed. Regeneration and demo belong to later work. |
| R-041 | `gars/_system/executorlib.py`, `gars/_system/wrapperlib.py` | `ExecutorSeamTests.test_00_slurm_default_is_byte_identical` | PASS. Removed the two “golden-bytes test” references per §21 Q11 default; preserved the existing test and both golden files unchanged. |

`DEVELOPMENT.md` records current state; README and development suite counts now match
141 collected tests. `docs/decisions/0043-row-1-open-design-schema.md` records standing
owner ruling 2A; `docs/decisions/CONTEXT.md` was regenerated with its existing script.
The constitution is 30 lines, with exactly the ten specified headings.

## Regression evidence

Before behavioral changes, the new development file ran nine cases: five failures,
one skip. Failing cases were ATAC floor, batch confounding, crossed-batch emission,
constant-batch acceptance, and missing strandedness. After changes, eight development
cases pass and the sealed case skips. Development fixtures never contribute to recall.

The full suite initially caught a fixture integration error: the expanded ATAC project
had REP2 samples but its fake count matrix only had REP1. The fake outputs were updated
to match the four biological samples. The test still checks refusal for a missing condition
in the count matrix and acceptance for complete outputs; no assertion was removed.

Owner 2A final checks (2026-09-13), from repository root:
- `python3 tests/run_tests.py`: exit 0, 141 tests, 10 skips.
- `python3 tests/check_contracts.py`: exit 0, 14 contracts clean.
- `python3 tests/check_counts.py`: exit 0, three current count claims match 141.
- `python3 tests/test_stage01_design.py`: exit 0, 16 cases, one sealed-fixture skip.
Logs: `2a-final-suite.log`, `2a-final-contracts.log`, `2a-final-counts.log`, and
`2a-final-design.log` under `~/aegis-builds/gars-row-1-scratch/`.

The earlier cold-session claim did not retain a sufficiently precise process record,
so it was replaced with this run: the producer spawned a fresh collaboration agent
`/root/cold_session_2a` with `fork_turns: none`, starting in
`/Users/javrodher/aegis-builds/gars-row-1/gars`. Its task supplied only
`gars/CLAUDE.md` and `gars/AGENTS.md` as entry-file paths and the question
“what runs the tests?”. It was instructed to read only those files and perform no
edits or test execution. Its first read used a login shell whose startup attempted
Conda initialization; that attempt is not claimed as isolated. It repeated the read
using `exec_command(login:false)` in the same directory with this exact command:

```bash
TMPDIR=/Users/javrodher/aegis-builds/gars-row-1-scratch TEMP=/Users/javrodher/aegis-builds/gars-row-1-scratch TMP=/Users/javrodher/aegis-builds/gars-row-1-scratch /bin/cat CLAUDE.md AGENTS.md
```

The clean read exited 0. The agent answered `cd ..`, then
`python3 tests/run_tests.py` and `python3 tests/check_contracts.py`, plus
`python3 tests/test_stage01_design.py` for Row 1 and the absent-seal skip caveat.
The producer, not the cold agent, executed these commands from
`/Users/javrodher/aegis-builds/gars-row-1`; final exits are recorded above.
No claim is made that the cold agent itself ran the suite.

Suite skips: seven pinned-pipeline environment checks; one missing GRCh38 reference;
one unavailable `anndata`; one unset sealed-design-fixture directory. An exit-zero
suite with this skip is not evidence that sealed design recall passed.

## Workflow commands

The following workflow evidence is from the prior Row 1 run, not a new 2A replay.
Per the owner, the Gap Study workflows did not need to be replayed and were not rerun
for 2A. All commands in `.github/workflows/ci.yml` were run during that prior run.
Gap Study 1 used the workflow-pinned `b735229f5c9213bb20c7e49fb7ceddddbcac7abc`.
Other evaluation checks used a disposable local checkout based on parent
`f7cf4d6d35478c9f6717ea298d1509e1f679485d` with the Row 1 working-tree changes overlaid.
These are pre-commit checks; Git-history-dependent results describe that parent plus overlay.
No evaluation files in the source checkout were edited. Existing mutation commands were
validation only; no mutants were added.

| Command | Checkout | Exit |
|---|---|---|
| `python3 evals/test_harness.py` | current | 0 |
| `python3 evals/check_results.py --controls --lexicon` | current | 0 |
| `python3 evals/gap-study/test_harness.py` | frozen | 0 |
| `python3 evals/gap-study/contracts.py --check` | frozen | 0 |
| `python3 evals/gap-study/fixtures/check_fixture.py --all` | frozen | 0 |
| `python3 evals/gap-study/lint_language.py evals/gap-study/` | frozen | 0 |
| `python3 evals/gap-study/check_results.py --ledger` | frozen | 0 |
| `python3 evals/gap-study/test_harness.py --mutations` | frozen | 0 |
| `Gap Study 1 controls-as-published shell block (verbatim workflow commands)` | frozen | 0 |
| `python3 evals/gap-study-2/test_harness.py` | current | 0 |
| `python3 evals/gap-study-2/contracts.py --check` | current | 0 |
| `python3 evals/gap-study-2/fixtures/check_fixture.py --all` | current | 0 |
| `python3 evals/gap-study-2/lint_language.py evals/gap-study-2/` | current | 0 |
| `python3 evals/gap-study-2/check_results.py --ledger` | committed trees 77a12be and ec2006c (reviewer); parent overlay was not a committed-row check | 1 at both: "HEAD carries gars tree … and the pre-registration pins 8a54e0f8cd91". Earlier overlay exit 0 saw parent HEAD and cannot establish row CI success. |
| `python3 evals/gap-study-2/test_harness.py --mutations` | current | 1 |
| `python3 evals/gap-study-2/copy_manifest.py --check` | current | 0 |
| `python3 evals/gap-study-2/costs.py --check` | current | 0 |
| `Gap Study 2 controls-as-published shell block (verbatim workflow commands)` | current | 0 |

**Local mutation failure:** `python3 evals/gap-study-2/test_harness.py --mutations`
exited 1 in this local replay on **Python 3.13.2**, using a **`git clone --shared`
copy** with Row 1 changes overlaid. CI uses **Python 3.12** and does run this command
(`.github/workflows/ci.yml:157`). Per the owner's correction, the mutation step
succeeded on parent commit `f7cf4d6` in GitHub run `34788401992` (owner-provided
evidence, not independently queried during this task).

- **Three controls are red because of this row:** “a take with no agent turn”,
  “a leaked word in an operator turn”, and “a published walk carrying the email
  field”. The `[checkout-binding]` guard reports that `gars/CLAUDE.md` now differs
  from the tree Gap Study 2 pins.
- **The other four failed in the local replay; cause not established here:**
  “a failed recovery that drops its step row”; “a budget above the registered one
  accepted”; “the harness's own report unread by the pause branch”; and
  “a fixture-owned test that reads the live COSTS.md”.
  The study session's slice-04 fix attribution is relayed by the owner and was not
  independently replayed here. The reviewer reproduced these four at the parent
  and ec2006c; they are not attributed to this row.

The ledger step and all three named `[checkout-binding]` mutation controls above
have the same cause: Row 1 changes the gars tree while Gap Study 2 pins its
pre-registered tree. Owner ruling **1A, 13 Sep**, recorded in GARS `STATE.md`
and supplied by the owner for this round: **“row 1 merges only after Gap Study
round 2's done commit or BLOCKED”**. This quotes the ruling; it does not re-decide it.
The red is expected until then. No CI scope or pin changes are made here.
`STATE.md` is outside this repository and was not read in this round.

F7 generator impact (code reading, also recorded by the reviewer):
`evals/gap-study-2/fixtures/gen_project.py:138` expects stage 01 `--check`
exit 0 for a seeded project. The new required replication-unit/release placeholders
make that project exit 1 until declared. This impact falls under the same owner
ruling; nothing under `evals/` is edited.

No frozen evaluation file was changed to make these controls pass.

The initial Gap Study 2 mutation run was interrupted to comply with the new scratch-location
instruction, then rerun to completion. Retained clones and logs were moved to
`~/aegis-builds/gars-row-1-scratch/`; subsequent runs set `TMPDIR`, `TEMP`, and `TMP` there.
Command records: `gars-row1-workflows.log` and `gars-row1-resumed-results.json` in that directory.
No overall CI PASS is claimed.

## Residual gaps

- D-23: formula and contrast selection/checks stay in stage 02. Rank validation is not
  newly implemented. Existing RNA formula-column and contrast-level refusals remain intact.
- D-27: floors still count distinct sample_id even when unit_of_replication is subject;
  subject-level pseudoreplication can pass. Owner ruling 1A, 14 Sep, defers distinct-subject
  counting to a later row with its own planted fixture (0043).
- D-24: explicit `strandedness: auto` remains accepted; absent/blank declaration is refused.
- Decision 0043 is standing, owner 2A. Subject/pairing, replication unit, release
  declaration and stage-01 record are implemented. Arbitrary covariate/identifier
  roles remain unspecified; only explicit `batch` is a candidate covariate here.
  Full R-072 is not claimed; no manifest is built.
- Reviewer evidence in `docs/reviews/row_1_review.md`: independent_context sealed recall
  3/3, external_human_seal 0/3. These fixtures predate the updated interface; the owner
  must reseal them independently (F4 open). Full 9/9 and public values remain unmeasured
  until three external_human_seal fixtures exist.
- Ledger hours, costs and session-registry cross-check unavailable; the unmetered share
  is all work recorded here. Known introducing hashes are now filled;
  R-160 names the reviewed ec2006c tree and its method limits.
- Gap Study 2 mutation validation has three Row 1 checkout-binding failures and four
  controls whose later slice-04 fixes are relayed, as attributed above. No new replay was required.
- No later-row benchmark, manifest, policy hardening, commit trailers, new mutants,
  release tooling, or evidence regeneration was implemented.

No push, pull request, remote change, self-approval or merge is authorized or performed.

## Owner 2A implementation evidence

New unsealed tests exercise missing/blank/null declarations, invalid enum values,
all three allowed replication units, subject absence/blankness, nested subjects,
cross-condition refusal and explicit pairing acceptance, arbitrary declared releases,
record content, check-only/overwrite gates, and a tampered record at the exit gate.
The demo test materializes only synthetic reads in a scratch copy of the example.
No sealed interface or existing refusal name was changed; no assertion was removed.
The new tests are development evidence only.

The strandedness concept search covered contracts and docs across the repository.
Stage 00 still seeds RNA strandedness: auto, and stage 01 accepts it; only missing
or blank strandedness is refused. Historical decisions and reviewed documents are
restored; the correction is in 0043 and separate dated addenda.
Missing new-project declarations are requested through T9 and written only from
user-supplied values to the existing project config path.

## Withdrawal — 14 Sep 2026 (F5)

The `77a12be` cold-session claim that the agent independently ran the documented
commands is withdrawn, including its unverifiable test counts and timings: 134 tests, 10 skips and
80.616 seconds for the suite, 14 clean contracts, and nine design cases with one skip.
The `ec2006c` procedure description above is retained as a record of the producer's
method and limits, not independent evidence. The reviewer's own fresh-agent run in
`docs/reviews/row_1_review.md` is the evidence of record for R-160. Its agent cited
AGENTS.md and named the commands that passed; the harness also loaded repository
CLAUDE.md, so this does not isolate AGENTS.md alone.

## Review round 1 fixes — 14 Sep 2026

| Finding | Changed files | Test / evidence | Result |
|---|---|---|---|
| F1 | This report | Review's committed-tree ledger runs at 77a12be/ec2006c and checkout-binding controls | Corrected to exit 1 at both; parent-overlay limitation stated beside the result; same pin cause named together. Owner 1A quoted; no pin/CI change. |
| F2 | Decisions 0011/0019/0020, appended 0043, generated decisions/CONTEXT.md; restored gap assessment and review; dated addenda beside each | Byte comparison with f7cf4d6; compare decision bodies excluding status; 0043 prefix comparison; build_index.sh | PASS: reviewed documents have empty diffs against f7cf4d6, only status lines differ in historical decisions, original 0043 is unchanged. |
| F3 | Appended 0043; this report's residual gaps | Owner ruling 1A, 14 Sep | Recorded as D-27 for a later row and its own planted fixture; floors unchanged. |
| F4 | tests/test_stage01_design.py | Runner inspection; sealed test conditional on owner environment | Per-project counts outside expected reason added without exposing contents or changing catches. Sealed run SKIPPED (variable unset). Reseal remains OPEN and the owner's. |
| F5 | This report; docs/ledger.csv | Dated withdrawal; review's fresh-agent method and limits | 77a12be claim, counts and timings withdrawn; ec2006c description retained; reviewer run is evidence of record. |
| F6 | This report | Compare wording with review F6 | Four controls “failed in the local replay; cause not established here”; slice-04 attribution remains relayed. |
| F7 | Both RNA/ATAC config templates; tests/run_tests.py; this report; appended 0043 | test_seeded_declarations; WorkspaceFixture.test_05_samplesheet_check_then_write; AtacseqWrapperTests | Placeholders surface early; RNA still seeds auto. Existing positive fixtures fill the new placeholders, preserving assertions. Generator impact recorded under owner 1A; evals untouched. |
| F8 | gars/_system/stage01_samplesheet.py; stage-01 CONTEXT.md step 2 and T9; tests/test_stage01_design.py; appended 0043; docs/ledger.csv | test_seeded_declarations, test_declared_provenance, test_paired_history_provenance, test_paired_without_history_warning, test_record_exit_gate_detects_tampering | Implemented under owner ruling 2A: declarations, HISTORY references and non-refusing warning; full-record re-read retained. All five tests pass and each failed on its targeted planted fault. |
| F9 | docs/ledger.csv; DEVELOPMENT.md; README.md | CSV inspection; check_counts.py; full suite | Known prior hashes filled, R-160/R-041 and four unsealed development rows added. New rows' introducing hash is unavailable before this commit. Current count 145, local skips 10; no row cluster evidence claimed. |
| N2 | This report; DEVELOPMENT.md | docs/reviews/row_1_review.md | Reviewer independent_context recall 3/3, external_human_seal 0/3 recorded; README public metric values remain unmeasured until three external_human_seal fixtures exist. |

Planted faults were applied one at a time to the local helper and restored in a
finally block. The seeded test went red when seed provenance was mislabeled;
the declared test when config provenance was marked absent; the paired-history test
when history_ref was forced null; the missing-history test when warning emission
was disabled. The tampering test went red when the full-record comparison was
disabled; its tamper changes only declarations.paired.history_ref. Each targeted
run exited 1. Logs are review-mutant-test_*.log in the designated scratch directory.

The first full run exposed two ATAC integration failures because the development
fixture appended declarations after the new required placeholders. The fixture now
replaces those placeholders (RNA likewise); no production configure.py behavior or
existing assertion was changed. Final verification follows.

Final checks from repository root, 14 Sep 2026:
- `python3 tests/run_tests.py` (Python 3.8.2): exit 0, 145 tests, 10 skipped.
- `/usr/local/bin/python3.13 tests/check_contracts.py`: exit 0, 14 contracts clean.
- `/usr/local/bin/python3.13 tests/check_counts.py`: exit 0, three enforced claims clean.
- `/usr/local/bin/python3.13 tests/test_stage01_design.py`: exit 0, 20 tests, one skipped.
- Sealed test: SKIPPED because the owner has not set GARS_SEALED_DESIGN_FIXTURES.
- `git diff --check`: clean; no changes under `evals/`.

TMPDIR, TEMP and TMP were set to `~/aegis-builds/gars-row-1-scratch/` for code
execution. Final logs are review-suite.log, review-contracts.log, review-counts.log
and review-design.log there. No remote access, push, approval or merge was performed.
The owner-supplied review file is unchanged and remains untracked, as supplied.
