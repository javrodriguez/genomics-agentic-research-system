# Row 1 change report

2026-09-13 · branch `build/gars-row-01-design` · producer implementation, not approval.

**Row 1 exit is NOT PASS:** sealed design recall is SKIPPED because
`GARS_SEALED_DESIGN_FIXTURES` is unset. No sealed fixture was created, searched for,
or inspected. Full §7.2 acceptance (9/9) is also unmeasured. The Row 1 threshold
remains 3/3. The cold-session exit passes.

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
| `python3 evals/gap-study-2/check_results.py --ledger` | current | 0 |
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
- **The other four failed only in this local replay, not on GitHub's run of the
  parent:** “a failed recovery that drops its step row”; “a budget above the
  registered one accepted”; “the harness's own report unread by the pause branch”;
  and “a fixture-owned test that reads the live COSTS.md”. The Round 2 study's own session reports that it fixed these controls in its
  later commit, slice 04; the live COSTS.md guard needed git history and Round 1's
  data. That explains why these four failed only in the local replay of the parent.
  This attribution is to the study's session, as relayed by the owner; the fixes
  were not independently replayed here. They are **not attributed to this row**.

No frozen evaluation file was changed to make these controls pass.

The initial Gap Study 2 mutation run was interrupted to comply with the new scratch-location
instruction, then rerun to completion. Retained clones and logs were moved to
`~/aegis-builds/gars-row-1-scratch/`; subsequent runs set `TMPDIR`, `TEMP`, and `TMP` there.
Command records: `gars-row1-workflows.log` and `gars-row1-resumed-results.json` in that directory.
No overall CI PASS is claimed.

## Residual gaps

- D-23: formula and contrast selection/checks stay in stage 02. Rank validation is not
  newly implemented. Existing RNA formula-column and contrast-level refusals remain intact.
- D-24: explicit `strandedness: auto` remains accepted; absent/blank declaration is refused.
- Decision 0043 is standing, owner 2A. Subject/pairing, replication unit, release
  declaration and stage-01 record are implemented. Arbitrary covariate/identifier
  roles remain unspecified; only explicit `batch` is a candidate covariate here.
  Full R-072 is not claimed; no manifest is built.
- No sealed fixtures supplied: neither 3/3 nor 9/9 recall, nor external-human sealing,
  has been demonstrated. Public evidence remains unmeasured.
- Ledger hours, costs and session-registry cross-check unavailable; the unmetered share
  is all work recorded here. Blank commit cells refer to the introducing Git commit via
  `git log -- docs/ledger.csv`; no self-referential commit hash is fabricated.
- Gap Study 2 mutation validation has three Row 1 checkout-binding failures and four
  controls fixed later by the study session, as attributed above. No new replay was required.
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
Current stage-01 wording now requires declaration, and historical default claims
in decisions/reviews are explicitly dated or corrected. Explicit `auto` remains
accepted; the existing template's explicit value is not a validator fallback.
Missing new-project declarations are requested through T9 and written only from
user-supplied values to the existing project config path.
