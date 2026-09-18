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
| R-162; §16.1/§9.2 reviewer independence | `docs/decisions/0050-row-3-test-suite-gate-and-mutants.md`, this report | Separate checkout/context for sealing and independent review | Program practice retained; no producer approval, merge, or independent-review claim. |
| Discovery count consistency | `README.md`, `DEVELOPMENT.md` | `python3 tests/check_counts.py` | PASS after changing only the three current numeric counts from 125 to 148. Historical counts unchanged. Surrounding historical cluster/skip prose was not rewritten, as instructed; this report's actual run has 9 skips and is not Linux integration evidence. |
| Decision record and index | decision 0050; `docs/decisions/CONTEXT.md` | `bash docs/decisions/build_index.sh` | Index regenerated by the shipped builder. No hand-edited index. |

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
in 0050 rather than decided here. Both trees are discovered now. Decision numbers 0043–0045
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


## Review round 1 fixes

Date: **2026-09-15**. Producer: Codex. Reviewed base: `f76492b`.
Review: `docs/reviews/row_3_review.md`, left untracked and byte-identical (SHA-256
`2cc3f6eb90c0ac8a3aaa9edbf4175797e9c357ee0d0a1ec0e04902355ae17175`).
This dated addendum corrects the earlier report; its original bytes remain intact.
**Repository findings F-1–F-4 addressed; Row 3 exit remains NOT met.**

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F-1 BLOCKER: ignored tests alter the score at the same SHA | `evals/mutate.py`, `evals/MUTANTS-INTERFACE.md`, `gars/tests/test_mutation_runner.py` | `MutationRunnerTests.test_ignored_discovered_test_cannot_change_committed_score`; existing restoration controls | PASS. **Yes:** against the original runner, the ignored oracle changed the expected surviving mutant to `killed`, producing an assertion failure. After the fix, the mutant survives both with and without the ignored test at identical `run_sha` and committed snapshot hash; the original source tree remains unchanged. |
| F-2 MAJOR: installer erases marker-bearing vetoes | `gars/_system/hooks/install.py`, `gars/tests/test_pre_push.py` | `PrePushTests.test_marker_bearing_unrelated_hook_keeps_veto`, `test_extended_installed_hook_keeps_veto`; existing composition/collision tests | PASS. **Yes:** both new cases failed against the original installer. Complete shipped bytes now identify an unchanged installation; a modified marker-bearing hook is refused without altering it, and its veto still runs. Ordinary hook chaining, stdin/argument forwarding, repeat installation and collision refusal still pass. |
| F-3 MAJOR: unsupported cluster/skip claims | `README.md`, `DEVELOPMENT.md`, this addendum | Whole suite, `tests/check_counts.py`, manual evidence/prose comparison | PASS for the dated macOS result; cluster **unverified**. **No:** no planted environmental-claim test. The count guard only establishes numeric consistency; it does not establish platform provenance. Current claims state 151 collected, 142 executed successfully, 9 skipped on macOS. |
| F-4 MINOR: mutation suite evidence discarded | `evals/mutate.py`, `evals/MUTANTS-INTERFACE.md`, `gars/tests/test_mutation_runner.py` | `MutationRunnerTests.test_full_run_hashes_source_and_records_run_sha` | PASS. **Yes:** running the final assertion against the original runner gives `FAILED (failures=1)` because `baseline_log` is absent. The fixed runner retains baseline and mutant stdout/stderr, return codes, collection totals and skip reasons; the regression checks an explicit skipped toy test in both retained logs. |

F-1 correction: the earlier assertion that a clean working tree alone binds the tested source
to HEAD was false for ignored inputs. Snapshots now use `git ls-tree` and `git cat-file` to
materialize committed blobs, executable modes and symlinks. They never copy ignored project
data or ignored tests. Unsupported Git entry types refuse. The existing source-tree and
restored-tree integrity checks remain. These are source-provenance controls, not environment
pinning or an operating-system security boundary.

F-3 correction: updating the count inside “green on macOS and on the cluster” expanded a
claim without cluster evidence. Preserving surrounding prose did not justify that claim.
README now identifies the actual dated macOS result; DEVELOPMENT separates that result from
its historical component status and removes the obsolete six-skip qualifier from the suite
claim. Historical per-assay results were not rerun or independently revalidated here.

F-4 evidence: every measured mutant row points to retained `baseline.json` and, when the
suite runs, `mutant-<id>.json` under a unique `$TMPDIR/gars-mutation-logs-*` directory. Logs
bind `run_sha`, committed snapshot hash and tested-tree hash; mutant logs also bind the diff
and expected-observation SHA-256 hashes. The directory is announced before the baseline runs
and survives tested-tree cleanup. A suite log reports its return code, not a premature mutation
status. No sealed inputs were supplied, inspected or authored in this round.

The review's nonblocking observation about source extraction in `gars/tests/support.py`
remains: replacing that fixture mechanism is outside these four corrections; its use of the
production discovery function is still exercised by the gate tests.

### Round 1 verification

All shell invocations set `TMPDIR`, `TEMP` and `TMP` to the designated sibling scratch folder
before running commands. Test fixtures, logs, retained mutation evidence, the original-runner
red-control copy and the commit-message file stayed there. Tests used Python 3.13.2 on macOS,
`PYTHONDONTWRITEBYTECODE=1`, disabled global/system Git configuration, an empty scratch
`GARS_PIPELINES` directory and no sealed set. No other build folder, reviewer conversation or
external project data was read. Scratch writes used the approved sandbox escalation.

| Command | Exact summary lines | Exit | Scratch log |
|---|---|---|---|
| `python3 tests/run_tests.py` | `Ran 151 tests in 233.324s`<br>`OK (skipped=9)` | 0 | `round1-full-suite.log` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 275.561s`<br>`OK` | 0 | `round1-harness.log` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 | `round1-contracts.log` |
| `python3 tests/check_counts.py` | `suite: 151 tests, from unittest's loader`<br>`enforced=3`<br>`clean — every current claim matches the suite` | 0 | `round1-counts-final.log` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 | `round1-results.log` |
| `python3 evals/mutate.py` | `unmeasured` | 0 | `round1-unmeasured.log` |
| `python3 evals/mutate.py --require` | `unmeasured` | 1 | `round1-unmeasured-required.log` |
| `gars/_system/hooks/pre-push fixture-remote fixture-target` | `Ran 151 tests in 166.235s`<br>`OK (skipped=9)`<br>`pre-push: whole suite passed` | 0 | `round1-direct-hook.log` |
| `python3 -m unittest discover -s gars/tests -p test_pre_push.py -v` | `Ran 7 tests in 14.912s`<br>`OK` | 0 | `round1-hook.log` |
| `python3 -m unittest discover -s gars/tests -p test_mutation_runner.py -v` | `Ran 9 tests in 13.808s`<br>`OK` | 0 | `round1-mutation-final.log` |

Red and intermediate checks (logs also in `$SCRATCH`):

| Log / check | Exact summary lines | Exit |
|---|---|---|
| `round1-red-mutation.log` | `Ran 9 tests in 10.166s`<br>`FAILED (failures=1, errors=1)` | 1 |
| `round1-red-hook.log` | `Ran 7 tests in 15.640s`<br>`FAILED (failures=2)` | 1 |
| `round1-red-logs.log` | `Ran 1 test in 2.447s`<br>`FAILED (failures=1)` | 1 |
| `round1-mutation.log` | `Ran 9 tests in 9.155s`<br>`OK` | 0 |
| `round1-counts.log` | `suite: 151 tests, from unittest's loader`<br>`enforced=4`<br>`1 problem(s):` | 1 |

The initial count check exited 1 because “Row 3 test status” was parsed as a claim of three
tests. Only the prose changed to “Row 3 validation”; the guard was unchanged and its final
run enforces all three current claims. The initial old-runner mutation discovery had one
assertion failure for F-1 and one missing-log KeyError for F-4; F-4 was subsequently reproduced
as the explicit assertion failure above. The red hook run had two assertion failures.
These deliberate red controls are not sealed mutants and never contribute to a kill score.

The whole suite collects 125 cases from `tests/` and 26 from `gars/tests/`. Nine inherited
skips remain: seven pinned-pipeline cases, one unavailable registry reference, and one
`anndata` execution dependency. All Row 3 cases execute. The named wrapper-contract test
passes with `wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`; its structural
and missing-project coverage has the same limits stated in the original report.

The direct hook reran all 151 cases after the final suite-log metadata adjustment.

Additional checks: `Python 3.6 grammar: 4 changed files parsed`; `git diff --check` clean;
protected-tree diff against `c423366` empty. The report's original bytes remain an unchanged
prefix, decision/review/assessment records were not edited, and the review checksum above
is unchanged. Path-limited staging includes only the eight round files; no hook is installed
in the source clone, and no push, remote operation, merge or pull request occurs.

## Owner rulings needed

**No new ruling is needed for F-1–F-4.** The existing merge-time suite-location ruling remains
open: Row 1 under `tests/` versus the Row 3 specification's `gars/tests/`; the owner must settle
the final location when those branches meet. Both trees continue to run. The standing merge
condition also remains: wait for the separate study's done commit; do not alter the study or
CI to compensate for this row's source changes.

### Residual gaps still open

- Ten independently sealed semantic mutants and the ≥8/10 score remain **unmeasured**;
  external-human sealing for public claims remains absent.
- R-165 trailers, R-166 Linux/Apptainer/pinned-pipeline integration, actual Python 3.6
  execution, live Git/gitleaks deployment and full role/credential enforcement remain unverified.
- Full scientific wrapper workflows, Nextflow cache behavior and biological/numerical
  reproducibility are not established by these offline fixtures.
- The Row 1 branch and the separate study's done commit were not inspected or verified.
- Independent re-review of this corrective commit remains required. The producer does not
  approve its own changes, and **Row 3's exit is still NOT met**.


## Review round 2 fixes

Date: **2026-09-15**. Producer: Codex. Reviewed base: `5502db1`.
Review: `docs/reviews/row_3_review_round2.md`, unchanged and untracked; SHA-256
`70672ee5b434efcfa24994cd1efde35132ad144a2742f6b5794768717fb37182`.
This addendum preserves the exact 24,281-byte report at the reviewed base, including the
original 14,684-byte report. **F-5 addressed; Row 3 exit remains NOT met.** The supplied
independent review closed F-1–F-4; their implementation is unchanged in this round.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F-5 BLOCKER: owner identification and real-machine inventory in touched live documents | `README.md`, `DEVELOPMENT.md`, this addendum | Whole-file manual review; `$SCRATCH/round2/audit_docs.py`; shell examples parsed with `bash -n`; preservation audit | PASS. **Yes, for the content audit:** the same checks fail on the saved pre-fix documents (`F-5 content audit: FAIL (0/2 documents clean)`, exit 1) and pass on the final documents (`F-5 content audit: PASS (2/2 documents clean)`, exit 0). This is a document check against observed disclosure categories, not a sealed semantic mutant or a general privacy detector. |

README removes personal attribution, account-specific badges, demo and related-project links;
cloning uses a caller-supplied repository URL. DEVELOPMENT replaces installation paths and
present/deleted workspace inventories with generic deployment requirements, and removes local
job identifiers, private project labels, site quota details and measured storage claims across
the whole file. Historical scientific outcomes remain identified as historical; the dated
macOS suite evidence stays explicit. The existing proposed quota-warning threshold remains
unchanged and is labeled unimplemented. No runtime, test, guard, threshold or CI code changed.
Decision, review, specification and assessment records are preserved, with no status edits.

Cheap review observations: README's inherited assertion of green CI on every push now states
that CI was not verified in this round; the offline-test note names all three skip categories.
The round-1 note about `gars/tests/support.py` fixture extraction stays: redesigning that
mechanism is outside this documentation correction; its existing gate coverage still runs.
There are no disputed findings and no new policy exception is requested.

### Round 2 verification

Tests ran on **macOS, Python 3.13.2**, with `PYTHONDONTWRITEBYTECODE=1`, global/system Git
configuration disabled, `GARS_PIPELINES` pointing to an empty scratch directory, and no supplied
sealed set. Every shell invocation set `TMPDIR`, `TEMP` and `TMP` to the designated sibling
scratch folder before commands ran. Logs, snapshots, audit scripts, fixtures and the commit
message stayed there. The first shell invocation used the tool's default login setting;
subsequent shell invocations explicitly used `login=false`. No outside project, build folder,
reviewer conversation or external sealed input was inspected. No network operation occurred.

Independent command processes ran concurrently; timings are not performance evidence.
The direct hook used synthetic push stdin and a scratch interpreter link to Python 3.13.2;
it did not push or install a source-clone hook. Commands and runner summaries follow verbatim.
All paths in the log column are relative to `$SCRATCH/round2/`.

| Command | Exact summary lines | Exit | Log |
|---|---|---|---|
| `python3.13 tests/run_tests.py` | `Ran 151 tests in 239.632s`<br>`OK (skipped=9)` | 0 | `full-suite.log` |
| `python3.13 evals/test_harness.py` | `Ran 44 tests in 285.023s`<br>`OK` | 0 | `harness.log` |
| `python3.13 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 | `contracts.log` |
| `python3.13 tests/check_counts.py` | `suite: 151 tests, from unittest's loader`<br>`enforced=3`<br>`clean — every current claim matches the suite` | 0 | `counts.log` |
| `python3.13 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 | `results.log` |
| `python3.13 -m unittest discover -s gars/tests -p test_pre_push.py -v` | `Ran 7 tests in 12.491s`<br>`OK` | 0 | `hook-tests.log` |
| `python3.13 evals/mutate.py` | `unmeasured` | 0 | `mutation-report.log` |
| `python3.13 evals/mutate.py --require` | `unmeasured` | 1 | `mutation-required.log` |
| `gars/_system/hooks/pre-push fixture-remote fixture-target` | `Ran 151 tests in 204.369s`<br>`OK (skipped=9)`<br>`pre-push: whole suite passed` | 0 | `direct-hook.log` |

The whole suite collects 125 cases from `tests/` and 26 from `gars/tests/`; 142 execute
successfully and nine skip (seven pinned-pipeline cases, one unavailable registry reference,
one missing `anndata` dependency). All Row 3 cases execute. The named
`WrapperContractTests.test_all_wrapper_contracts` passes and prints
`wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`. This covers structure and
missing-project refusals, not complete scientific workflows. The mutation-required exit 1
correctly refuses the absent sealed set; no mutation score is claimed.

Additional document and boundary checks:

| Check | Exact summary / result | Exit | Log |
|---|---|---|---|
| `python3.13 "$SCRATCH/round2/audit_docs.py" --before` | `F-5 content audit: FAIL (0/2 documents clean)` | 1 (expected red) | `f5-red.log` |
| Initial post-edit content/shell audit | `F-5 content audit: PASS (2/2 documents clean)` followed by `AssertionError` on the inherited `<id>` scheduler example | 1 | `f5-green.log` |
| `python3.13 "$SCRATCH/round2/audit_docs.py"` | `F-5 content audit: PASS (2/2 documents clean)`<br>`Setup shell syntax and dated platform evidence: PASS` | 0 | `f5-green-final.log` |
| `python3.13 "$SCRATCH/round2/audit_preservation.py"` | `Change report: exact 24281-byte reviewed prefix preserved`<br>`Round 2 review: unchanged and untracked`<br>`Round scope: only README, DEVELOPMENT and change report differ`<br>`Decision, review, specification and assessment records: unchanged`<br>`Protected-tree diff against c423366: empty`<br>`git diff --check: clean` | 0 | `preservation.log` |

The syntax failure was fixed with generic `GARS_CLONE` and `GARS_JOB_ID` variables and quoted
paths; the audit was not weakened. `bash -n` parses the examples without executing their
clone, update or scheduler commands. The original documents themselves supply the red
control; no producer-created sealed faults or fault score is involved. The content patterns
check the observed categories; whole-file manual inspection supplements that bounded audit.

Inspection used repository-local `rg`, `cat`, `sed`, `git status`/`diff` and local Git objects;
Python scripts wrote only the two live documents, this append, and scratch artifacts.
Preservation and whitespace checks ran again after this append. Staging is limited to these
three documentation paths, with one round commit from a scratch message file. Both supplied
untracked review paths remain untracked; the round-1 review file was not read in this round.
No push, remote operation, merge, PR, hook installation or independent approval occurred.

## Owner rulings needed

**None for F-5:** generalizing the live documents implements the review's required fix, so no
amendment of the whole-file rule is needed. The existing merge-time suite-location ruling
remains open: Row 1 under `tests/` versus the Row 3 specification's `gars/tests/`. Both trees
continue to run; their final location is for the owner to decide when the branches meet.
The separate study's standing merge prerequisite remains unverified and unchanged.

### Residual gaps still open

- Ten independently sealed semantic mutants and the ≥8/10 score remain **unmeasured**;
  external-human sealing for public claims remains absent.
- R-165 trailers/session enforcement, R-166 Linux/Apptainer/pinned-pipeline integration,
  actual Python 3.6 execution, live Git/gitleaks deployment and role/credential enforcement
  remain unverified. No Python grammar check is newly needed: no Python source changed.
- Full scientific workflows, real Nextflow cache behavior, biological validity and numerical
  reproducibility are not established by the offline fixtures. Historical assay and CI
  results were not revalidated, and the inherited Python 3.8 harness limitation was not rerun.
- The Row 1 branch and the separate study's merge prerequisite were not inspected or verified.
- Independent re-review of this corrective commit remains required. The producer does not
  approve its own work, and **Row 3's exit remains NOT met**.


## Review round 3 fixes

Date: **2026-09-15**. Producer: Codex. Starting commit: `fe4157f`.
Review: `docs/reviews/row_3_review_round2.md`, unchanged and untracked; SHA-256
`70672ee5b434efcfa24994cd1efde35132ad144a2742f6b5794768717fb37182`.
The complete 32,888-byte pre-round report, including its round 2 section, remains an exact
prefix (SHA-256 `dbada1d0a30c56c7153b01f8b6e0a358de2075ce2460e1736bebe7dada4975d9`).

**Owner rulings applied (the owner, 2026-09-15):** 1A limits the owner/real-machine rule to
what a row introduces; content already present at `c423366` is inherited and out of scope.
Its presence is not a defect, and removing it is scope creep. **F-5 is withdrawn.**
2A freezes decision records, formal reviews, assessments and earlier change-report sections;
README, DEVELOPMENT, benchmarks/HOLDOUT and other implementation documents are living
documents whose counts and status must stay current. This addendum supersedes the round 2
claim that removing the inherited content was required; the historical section is not edited.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F-5 BLOCKER — withdrawn by owner ruling 1A; undo the round 2 removal | `README.md`, `DEVELOPMENT.md`, this addendum | `python3.13 "$SCRATCH/round3/audit_preservation.py"`; `python3.13 tests/check_counts.py`; whole suite | Restored both documents byte-for-byte from `5502db1`, including inherited author section, demo link, CI badge, related work, clone URL and live-run history. Counts already match the current suite, so no count/status adjustment was necessary. **Red-on-fault seen: no**; this is a historical-byte restoration verified against Git objects, not a new behavioral fix or sealed mutant. |
| F-1–F-4 — closed by the supplied independent review | No implementation changes | Whole suite, named hook and mutation regressions included | Existing regressions pass in this run. **Red-on-fault seen: no new replant for F-1/F-2/F-4**; prior independent red evidence is recorded in the supplied review. F-3's macOS count/skip statement matches this run; cluster status remains unverified. |

Evidence for inheritance: `git diff c423366 5502db1 -- README.md DEVELOPMENT.md` changes
only suite counts and status prose. The restored owner, link and machine-history material
therefore predates this row. The review's inherited CI/historical-assay observations remain
unverified: the restoration does not establish those historical claims. The fixture-extraction
note remains outside this documentation correction; existing gate tests continue to cover it.
No runtime, test, threshold, guard, CI, decision, review or assessment record changed.

### Round 3 verification

Checks ran on **macOS, Python 3.13.2**, with `PYTHONDONTWRITEBYTECODE=1`, global/system Git
configuration disabled, an empty scratch `GARS_PIPELINES` directory and no supplied sealed set.
Every shell invocation set `TMPDIR`, `TEMP` and `TMP` to the designated sibling scratch folder
before commands; the first used the tool's default login setting and subsequent calls used
`login=false`. Task scripts, snapshots, command logs and the commit message are in
`$SCRATCH/round3/`; test fixtures and retained mutation logs also use the scratch root. Independent command processes ran concurrently; timings are not
performance evidence. The direct hook used synthetic push stdin and a scratch interpreter
link; it did not push or install a hook in the source clone.

| Command | Exact summary lines | Exit | Log under `$SCRATCH/round3/` |
|---|---|---|---|
| `python3.13 tests/run_tests.py` | `Ran 151 tests in 132.887s`<br>`OK (skipped=9)` | 0 | `full-suite.log` |
| `python3.13 evals/test_harness.py` | `Ran 44 tests in 158.502s`<br>`OK` | 0 | `harness.log` |
| `python3.13 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 | `contracts.log` |
| `python3.13 tests/check_counts.py` | `suite: 151 tests, from unittest's loader`<br>`enforced=3`<br>`clean — every current claim matches the suite` | 0 | `counts.log` |
| `python3.13 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 | `results.log` |
| `python3.13 -m unittest discover -s gars/tests -p test_pre_push.py -v` | `Ran 7 tests in 6.369s`<br>`OK` | 0 | `hook-tests.log` |
| `python3.13 evals/mutate.py` | `unmeasured` | 0 | `mutation-report.log` |
| `python3.13 evals/mutate.py --require` | `unmeasured` | 1 | `mutation-required.log` |
| `gars/_system/hooks/pre-push fixture-remote fixture-target` | `Ran 151 tests in 142.405s`<br>`OK (skipped=9)`<br>`pre-push: whole suite passed` | 0 | `direct-hook.log` |

The whole suite collects 125 cases from `tests/` and 26 from `gars/tests/`: 142 execute
successfully and nine skip (seven pinned-pipeline cases, one unavailable registry reference,
one missing `anndata` dependency). All Row 3 cases execute. The named
`WrapperContractTests.test_all_wrapper_contracts` passes with
`wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`. This is structural and
missing-project coverage, not full scientific execution. Existing public planted-fault tests
still exercise their red controls; they do not contribute to the sealed score. Required
mutation mode exits 1 for the absent sealed set, as intended.

Preservation audit (`preservation.log`): both live documents are byte-identical to `5502db1`;
the exact pre-round report prefix is preserved; the supplied round 2 review is unchanged and
untracked; only the three authorized documentation paths differ; decision/review/specification/
assessment records are unchanged; the protected-tree diff against `c423366` is empty.

**Whitespace check retained as nonzero:** `git diff --check` exits **2** and reports verbatim
`DEVELOPMENT.md:393: new blank line at EOF.` (`whitespace.log`). The final blank line exists
in both `git show c423366:DEVELOPMENT.md` and `git show 5502db1:DEVELOPMENT.md`; both end in
`publish_dir_mode = 'copy'` followed by the existing Markdown punctuation and two newlines.
It is preserved under the explicit restoration instruction, which permits only necessary
count/status changes. No whitespace check is relabeled clean or weakened.

Inspection used local repository files/Git objects and the designated scratch folder; no
reviewer conversation, forbidden build folder, remote or external sealed set was accessed.
Staging is limited to README, DEVELOPMENT and this report. Both supplied review paths remain
untracked. One round commit uses a scratch message file; no push, merge, PR or approval occurs.

## Owner rulings needed

**None for this round's finding:** F-5 is withdrawn under the supplied ruling; no policy
exception remains to decide. The existing merge-time suite-location question remains open:
Row 1 under `tests/` versus the Row 3 specification's `gars/tests/`. Both trees run; the owner
chooses their final location when those branches meet. The separate study's standing merge
prerequisite remains unverified and unchanged.

### Residual gaps still open

- Ten independently sealed semantic mutants and the ≥8/10 score remain **unmeasured**;
  external-human sealing for public claims remains absent. **Row 3 exit remains NOT met.**
- R-165 trailers/session enforcement, R-166 Linux/Apptainer/pinned-pipeline integration,
  actual Python 3.6 execution, live Git/gitleaks deployment and role/credential enforcement
  remain unverified. No Python source changed; no new grammar-only claim is made.
- Full scientific workflows, real Nextflow cache behavior, biological validity and numerical
  reproducibility are not established by the offline fixtures. Restored historical assay,
  installation and CI claims were not revalidated; the inherited Python 3.8 harness limitation
  was not rerun. The inherited EOF whitespace diagnostic remains as documented above.
- The Row 1 branch and the separate study's done-or-BLOCKED merge prerequisite were not
  inspected or verified. Independent re-review remains required; the producer does not approve
  its own work.


## Review round 4 fixes

Date: **2026-09-15**. Producer: Codex. Starting commit: `6f680e8`.
Review: `docs/reviews/row_3_review_round3.md`, unchanged and untracked; SHA-256
`b19fae9ed5b95314fdd79b6a8549afef512f19432f1cc9ca14958b573e7ddac8`.

The owner authorizes one correction in the frozen round 3 section: its
"Owner rulings applied" heading now attributes the rulings to **the owner**.
Every other pre-round report byte is preserved, including the exact 24,281-byte prefix
at `5502db1` (SHA-256
`65c9d0a0b30a093340f74f6231e6f03197c5ec6af5c73f6320fdcc4ffce5d792`).
The owner's rulings 1A and 2A remain controlling: inherited content is out of scope;
living implementation documents retain current counts and status. F-5 stays withdrawn.
README and DEVELOPMENT remain byte-identical to their restored versions at `5502db1`.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F-6 BLOCKER: newly authored owner identification in the round 3 heading | `docs/implementation/row_3_change_report.md` only | `python3.13 "$SCRATCH/round4/check_heading.py" --before`; same command without `--before`; preservation audit | CLOSED. **Yes, document check:** the exact expected generic heading fails against the saved pre-fix report (exit 1), then passes against the corrected report (exit 0). This checks the specific attribution defect; it is not a behavioral mutant or a sealed score. Only the authorized heading line and this new section change. |

### Round 4 verification

Checks ran on **macOS, Python 3.13.2**, with `PYTHONDONTWRITEBYTECODE=1`, global/system Git
configuration disabled for test processes, an empty scratch `GARS_PIPELINES` directory and
an empty sealed-set variable. Every shell invocation set `TMPDIR`, `TEMP` and `TMP` to the
designated sibling scratch folder before commands ran. The first two shell invocations used
the tool's default login setting; subsequent invocations explicitly used `login=false`.
All scratch scripts, snapshots, logs, fixtures and the commit-message file stayed in that
scratch folder. Only the designated round 3 review was read among the untracked review copies;
no reviewer conversation, other build folder or external sealed set was accessed.

Independent check processes ran concurrently; timings are not performance measurements.
The direct hook used synthetic push stdin and a scratch interpreter link, without a push or
source-clone hook installation. Exact runner summaries follow; log names are relative to
`$SCRATCH/round4/`.

| Command | Exact summary lines | Exit | Log |
|---|---|---|---|
| `python3.13 tests/run_tests.py` | `Ran 151 tests in 284.573s`<br>`OK (skipped=9)` | 0 | `full-suite.log` |
| `python3.13 evals/test_harness.py` | `Ran 44 tests in 332.023s`<br>`OK` | 0 | `harness.log` |
| `python3.13 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0 | `contracts.log` |
| `python3.13 tests/check_counts.py` | `suite: 151 tests, from unittest's loader`<br>`enforced=3`<br>`clean — every current claim matches the suite` | 0 | `counts.log` |
| `python3.13 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0 | `results.log` |
| `python3.13 -m unittest discover -s gars/tests -p test_pre_push.py -v` | `Ran 7 tests in 11.918s`<br>`OK` | 0 | `hook-tests.log` |
| `python3.13 -m unittest discover -s gars/tests -p test_mutation_runner.py -v` | `Ran 9 tests in 8.099s`<br>`OK` | 0 | `mutation-tests.log` |
| `python3.13 evals/mutate.py` | `unmeasured` | 0 | `mutation-report.log` |
| `python3.13 evals/mutate.py --require` | `unmeasured` | 1 | `mutation-required.log` |
| `gars/_system/hooks/pre-push fixture-remote fixture-target` | `Ran 151 tests in 296.924s`<br>`OK (skipped=9)`<br>`pre-push: whole suite passed` | 0 | `direct-hook.log` |

The full suite collects 125 cases from `tests/` and 26 from `gars/tests/`; 142 execute
successfully and nine skip: seven unavailable pinned-pipeline cases, one unavailable registry
reference and one missing `anndata` execution dependency. All 26 Row 3 cases execute.
`WrapperContractTests.test_all_wrapper_contracts` passes with
`wrapper contracts: 7/7 found/expected nf-core; 10 total wrappers`.
This establishes structural contracts and missing-project refusals. Mutation report mode
remains `unmeasured`; required mode exits 1 as intended when no sealed set is supplied.
No sealed score or complete scientific workflow is established.

| Additional check | Exact summary lines | Exit | Log |
|---|---|---|---|
| `python3.13 "$SCRATCH/round4/check_heading.py" --before` | `F-6 heading check: FAIL` | 1 (expected red) | `f6-red.log` |
| `python3.13 "$SCRATCH/round4/check_heading.py"` | `F-6 heading check: PASS` | 0 | `f6-green.log` |
| `python3.13 "$SCRATCH/round4/audit_preservation.py"` | `Round scope: one authorized heading replacement plus round 4 append only`<br>`Report prefix: exact 24281 bytes preserved; SHA-256 65c9d0a0b30a093340f74f6231e6f03197c5ec6af5c73f6320fdcc4ffce5d792`<br>`Other tracked entries: 889 byte-identical with modes preserved against 5502db1; README and DEVELOPMENT unchanged`<br>`Supplied round 3 review: unchanged and untracked`<br>`Protected-tree diff against c423366: empty`<br>`git diff --check against HEAD, 5502db1 and c423366: clean` | 0 | `preservation.log` |

The preservation audit compares every other tracked entry's blob hash and executable or
symlink mode against `5502db1`; this includes every decision record, formal review and
assessment. It also checks that the entire pre-round report differs only at the authorized
heading before this append. The earlier round 3 whitespace diagnostic remains historical;
this round's diff checks against its starting HEAD, `5502db1` and `c423366` are clean.
The audit is rerun after this append. Path-limited staging contains only this report;
one round commit uses a scratch message file. No remote operation, push, merge or PR occurs.

## Owner rulings needed

**None for F-6:** the owner supplied the exact authorization and generic attribution.
No current finding waits on the owner. The existing merge-time suite-location question
remains open: Row 1 under `tests/` versus the Row 3 specification's `gars/tests/`.
Both trees continue to run; the owner decides their final location when those branches meet.

### Residual gaps still open

- Ten independently sealed semantic mutants and the >=8/10 score remain **unmeasured**;
  external-human sealing remains absent. **Row 3 exit remains NOT met.**
- R-165 trailers/session enforcement, R-166 Linux/Apptainer/pinned-pipeline integration,
  actual Python 3.6 execution, live Git/gitleaks deployment and role/credential enforcement
  remain unverified. No Python source changed; no new grammar-only claim is made.
- Full scientific workflows, real Nextflow cache behavior, biological validity, numerical
  reproducibility and inherited historical assay, installation and CI claims were not verified.
  The inherited Python 3.8 harness limitation was not rerun; current harness evidence uses
  Python 3.13.2. The fixture-extraction note remains outside this one-line correction.
- The Row 1 branch and the separate study's done-or-BLOCKED merge prerequisite were not
  inspected or verified. Independent re-review remains required; the producer does not
  approve its own work. F-1–F-4 remain closed and F-5 remains withdrawn.
