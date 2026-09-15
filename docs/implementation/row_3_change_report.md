# Row 3 repository-side change report

Date: 2026-09-15. Producer: Codex. Branch: `build/gars-row-03-tests`.
Parent: `c423366`. One producer commit; independent review remains required.

**Row 3 exit: NOT met.** Wrapper contracts: **7/7 nf-core**, with **10/10 total wrappers**
checked. Sealed-mutant score: **unmeasured**; the ten slots remain **unsealed**. None of the
producer-visible fault controls is part of the sealed set or evidence for ≥ 8/10.

## Requirement → files → acceptance → result

| Requirement | Changed files | Acceptance test | Result and red-on-fault evidence |
|---|---|---|---|
| R-164: guard suite | `gars/tests/test_guard_hook.py`, `support.py` | `GuardHookTests`: shipped denies/allows, bad stdin, bypass-switch characterization | PASS. Red-on-fault seen: **yes**, `PlantedFaultTests.test_guard_allows_denied_shape` copies the shipped hook and makes its deny exit 0; `test_denied_shapes` fails. The shipped bypass-switch allows are labeled as known gaps, not policy passes. |
| R-164: prepare determinism | `gars/tests/test_wrapperlib_prepare.py` | `WrapperlibPrepareTests.test_prepare_twice_identical_bytes` | PASS for every pipeline pin. Compares all four emitted artifacts from the shared prepare writers, with a delay spanning second-resolution timestamps. Red-on-fault: **yes**, `test_prepare_timestamp_changes_bytes` adds a timestamp to emitted params and observes byte-comparison failures. |
| R-164: wrapper contracts | `gars/tests/test_wrapper_contract.py` | `WrapperContractTests.test_all_wrapper_contracts` | PASS: 7/7 nf-core; 10/10 total. Wrappers are enumerated from directories; each module's ASSAY/SUBSTAGE locates its contract. Checks eight sections/order and wait points, then all three verbs' JSON refusal on a nonexistent project. Red-on-fault: **yes**, a removed Scope Boundaries heading causes the actual contract test to fail. |
| R-164: interrupted resume | `gars/tests/test_executorlib_resume.py` | `ExecutorlibResumeTests.test_interrupted_resume_and_completed_reentry` | PASS. Real local executor starts the shipped generated script: first execution records one effect and exits 17 without completion; resume adds the second effect; completed reentry leaves run bytes identical. Synthetic pipeline body and environment only. Does not claim real Nextflow cache validation or duplicate-submit prevention. |
| R-164: whole-suite discovery and zero refusal | `tests/run_tests.py`, `gars/tests/test_pre_push.py` | `PrePushTests.test_each_empty_tree_refuses`, `test_planted_failure_refuses` | PASS. Existing embedded cases plus discovery under both trees use unittest's loader; `check_counts.py` sees the same collection. Red-on-fault: **yes**, empty each tree in turn and plant a failing discovered test; direct hook calls with fake push stdin refuse each. Explicit TMPDIR never silently falls back in the runner/new tests. |
| R-164; §9.2-related gate surface | `gars/_system/hooks/pre-push`, `install.py`, `gars/tests/test_pre_push.py` | `test_installer_preserves_both_gates_stdin_and_veto`, collision refusal, direct source-hook invocation | PASS in scratch clones with default and configured hook directories. Previous hook receives identical stdin/arguments; both gates run and either can veto. No real gitleaks hook exists here, so this is composition evidence with a stand-in. No hook armed in this clone. No §9.2 role/credential enforcement claimed. |
| R-164: mutation mechanics | `evals/mutate.py`, `gars/tests/test_mutation_runner.py` | killed/survived/ineffective controls, restoration drift, full source-hash/run-SHA control, malformed scope refusal, unmeasured modes | PASS on public toy controls. Red-on-fault: **yes**, a text-only diff is `ineffective` with no killing test; a broken restoration leaves an extra file and raises `tree differs after run; REFUSED`. A real semantic toy is killed with its failing test named; an effective change outside the toy assertion survives. These do not measure the sealed set. |
| R-164: separate sealing interface | `evals/MUTANTS-INTERFACE.md`, `evals/mutants.md` | Complete source-only handoff; ten empty slots; report/require modes | Interface delivered. **NOT met:** ten sealed semantic mutants and ≥ 8/10 kills. Report emits `unmeasured` (exit 0), `--require` emits `unmeasured` (exit 1). |
| R-162; §16.1/§9.2 reviewer independence | `docs/decisions/0046-row-3-test-suite-gate-and-mutants.md`, this report | Separate checkout/context for sealing and independent review | Program practice retained; no producer approval, merge, or independent-review claim. |
| Discovery count consistency | `README.md`, `DEVELOPMENT.md` | `python3 tests/check_counts.py` | PASS after changing only the three current numeric counts from 125 to 148. Historical counts unchanged. Surrounding historical cluster/skip prose was not rewritten, as instructed; this report's actual run has 9 skips and is not Linux integration evidence. |
| Decision record and index | decision 0046; `docs/decisions/CONTEXT.md` | `bash docs/decisions/build_index.sh` | Index regenerated by the shipped builder. No hand-edited index. |

`gars/tests/test_planted_faults.py` keeps the three behavioral/contract fault controls
repeatable. Each runs the acceptance case under a deliberate fault, asserts a real unittest
failure (not a swallowed error), and prints `red-on-fault` with that case's name. The gate
controls invoke the script directly; they never push. The mutation integrity control asserts
a refusal, not a kill. All seven requested fault classes were observed in the final run.

## Existing equivalents and suite placement

`guard_hook.py`, `wrapperlib.py` and `executorlib.py` all exist under their specified module
names. The callable seam differs from the spec shorthand: `wrapperlib` supplies the shared
prepare artifact writers; resume belongs to the generated `submit.sh` guard and native
Nextflow session detection, executed here through `executorlib.submit/status`. There is no
executor resume verb. No module or verb was invented to satisfy a test name; no shipped
runtime behavior was changed. Full wrapper prepare/check coverage needing pinned pipeline
checkouts remains subject to the inherited environment skips.

**No `test_stage01_design.py` was added.** Row 1 supplies it under `tests/` on another branch.
The ultimate `tests/` versus `gars/tests/` location is an **owner ruling at merge**, recorded
in 0046 rather than decided here. Both trees are discovered now. Decision numbers 0043–0045
are reserved on other branches and absent from this history.

## Hook inspection and installation ruling

Inspection found only `.git/hooks/*.sample`; repository `core.hooksPath` is unset. There is
no guard installer: `gars/.claude/settings.json` invokes the guard as a harness PreToolUse
command. There is no active gitleaks pre-commit/pre-push or trailer hook in this clone.
Decision 0042 also leaves bypass-switch denies for later work. The owner explicitly ruled:
“Use the existing Git hook directory and preserve/chains hooks.”

For a future authorized clone, `python3 gars/_system/hooks/install.py` uses the existing
Git hook directory, or the configured `core.hooksPath`, preserves an existing executable
pre-push as `pre-push.gars-previous`, and chains it. It refuses backup collisions and does
not overwrite unrelated hooks. Tests install only in scratch repositories, including a
custom hooks folder. The source clone is left with its original sample hooks only.

## Final command results

All commands below exited 0 except the deliberately required/unmeasured mutation check.
Summary lines are copied verbatim from the final logs:

```text
$ python3 tests/run_tests.py
Ran 148 tests in 102.915s
OK (skipped=9)

$ python3 tests/check_contracts.py
14 contracts clean: sections, wait points, vocabulary.

$ python3 tests/check_counts.py
suite: 148 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite

$ python3 evals/test_harness.py
Ran 44 tests in 133.150s
OK

$ python3 evals/check_results.py --controls --lexicon
clean — graded=1

$ python3 -m unittest discover -s gars/tests -p test_pre_push.py -v
Ran 5 tests in 4.525s
OK

$ gars/_system/hooks/pre-push fixture-remote fixture-target
Ran 148 tests in 110.688s
OK (skipped=9)
pre-push: whole suite passed

$ python3 evals/mutate.py
unmeasured

$ python3 evals/mutate.py --require
unmeasured
```

The last command exits 1, as required. Both hook tests and the direct source hook received
fake Git push stdin. The final malformed-metadata tightening was additionally verified by
`python3 -m unittest discover -s gars/tests -p test_mutation_runner.py -v`:

```text
Ran 8 tests in 1.913s
OK
```

Static compatibility check: `Python 3.6 grammar: 12 files parsed`. This checks grammar,
not execution on Python 3.6, which is unavailable.

Collection: `collected 125 tests from tests`; `collected 23 tests from gars/tests`.
Wrapper line: `wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`.
Nine inherited skips: seven pinned-pipeline tests, one missing registry reference,
and the spatial cluster-count
execution test because `anndata` is absent. The latter is a missing Python package, not a
missing pinned checkout (review m-9). The new Row 3 tests have no skips.

## Command environment and reproducibility

Every shell invocation began in the repository root and explicitly set `TMPDIR`, `TEMP`
and `TMP` to the owner's designated sibling scratch directory. In the commands below,
`$SCRATCH` denotes that supplied directory, without committing a machine-specific absolute
path. All fixtures, mutation copies, logs and the commit message are intended there:

```sh
export TMPDIR="$SCRATCH" TEMP="$SCRATCH" TMP="$SCRATCH"
export PYTHONDONTWRITEBYTECODE=1
export GARS_PIPELINES="$SCRATCH/absent-pipelines"
```

`GARS_SEALED_MUTANTS_DIR` was absent (the unmeasured-mode tests explicitly set it empty).
Mutation mechanics used only temporary public toy folders; no sealed set was read or created.
The source-only interface does not disclose the producer's tests. Mutation runs require a
clean source checkout so the recorded SHA identifies the tested source. Before/after hashes
include names, modes, directories, bytes and symlink targets, excluding `.git`. Probes must
be read-only and demonstrate behavior; the independent sealer/reviewer judges their meaning.

Commands and execution locations:

- Orientation/inspection: `pwd`, `git status`, `rg`/`rg --files`, `cat`, `head`, `tail`, `sed`,
  `ls`, `du`, `stat`, `date`, `python3 --version`, `command -v`; repository guidance, index,
  applicable decisions, the spec sections, Row 3 assessment/review, runner/count/lint,
  libraries/wrappers/contracts, `.git/config` and hook samples. Direct inspection stayed within the two
  permitted trees; tool executables were only located/invoked, not inspected as user data.
- File creation/edits: `mkdir`, `chmod`, patch tool and stdlib Python file writes; only the
  authorized repository paths. `bash docs/decisions/build_index.sh` regenerated the index.
- Required runners: commands in the results block, launched from the repository root. Final
  writable checks ran with approved scratch access; a stdlib thread-pool driver launched
  independent command lists (no model/network tools), captured logs in scratch and checked
  their return codes. Both full-suite and direct-hook runs exercised both test trees.
- Hook tests: miniature repositories under scratch, production discovery function and actual
  hook/installer scripts; fake stdin names/SHAs, no remote. The real source hook was also
  invoked directly with fake push stdin. Mutation toy fixtures used local `git init`,
  path-limited `git add -- tests gars`, and a fixture-only commit to test recorded run SHAs.
- Final verification: `git diff --check`, path-limited diff/status and protected-tree checks;
  Python 3.6 grammar parsing of added/changed Python; actual Python 3.6 execution is not
  available. Commit uses explicit paths and `git commit -F` with a scratch message file.
  No push, remote addition, PR, approval or merge.

Actual interpreter: **Python 3.13.2**, macOS. Added Python uses only stdlib and Python 3.6
syntax/APIs. `python3.6`, Apptainer and Nextflow were absent from PATH. Pinned checkouts were
explicitly unavailable via `GARS_PIPELINES`; no out-of-repository default pipeline tree was
read. `anndata` was not importable. A gitleaks executable was discoverable, but no active
Git gitleaks hook exists here and no installation was attempted.

**Execution deviation:** an early sandboxed attempt could not write to the designated scratch
folder. Before fallback was prevented, Python's tempfile selection silently used its default
location. Those results were discarded; the fallback also triggered mutation path/integrity
errors. No outside-tree inspection or cleanup was performed. The runner/new tests now honor
an explicit TMPDIR without fallback, and all required writable checks were rerun with approved
scratch access. The initial document count check also went red on the three stale 125 counts;
only those numbers were corrected to the loader's 148.

## Hours and residual gaps

Producer active work: **approximately 1.0 hour**, an estimate excluding the overnight scratch
permission wait; not cross-checked against a session registry. Human/reviewer time and API
costs were not measured. This is not an R-167 ledger claim.

- **NOT met:** ten independently sealed semantic mutants; ≥ 8/10 killed remains unmeasured.
- **NOT met:** `external_human_seal` required for public claims.
- **NOT met:** R-165 trailers (Row 11); no trailer check implemented.
- **NOT met:** R-166 Linux integration; no Linux runner implemented.
- **NOT met:** live gitleaks coexistence in this source clone; composition proved by stand-in.
- **NOT met:** full §9.2 role/credential enforcement and later policy bypass-switch denies.
- **Pending owner ruling:** final suite location when Row 1 merges.
- **Standing owner ruling:** this row merges only after the separate study's done commit.
  Its controls may go red because allowed additions change `gars/` and `evals/`. No study
  or CI source was changed to compensate, and no study pass is claimed here.

Boundary verification: `git diff --stat c423366 -- evals/gap-study evals/gap-study-2 evals/run.py
evals/graders evals/fixtures .github/` is empty. Under `evals/` only the three authorized files
were added. Under `gars/`, all changes are in `gars/tests/` and `gars/_system/hooks/` (R-164);
**no changes outside those directories**. The commit is ready for separate review, not
approved by its producer. Row 3's exit remains **NOT met**.
