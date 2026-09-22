# Row 4 change report — work in progress

Parent `c934f6d`; branch `build/gars-row-04-policy`. Producer implementation only;
not reviewed, approved, merged or pushed. **Row exit NOT met.** Implementation is stopped
on the material choices and file-boundary exceptions in decision
[0053](../decisions/0053-row-4-typed-surface-and-attack-list.md#owner-rulings-needed),
following the owner's explicit rule 5. No choice is inferred from an unanswered question.
The requested single row commit records this partial implementation and its live red
tests. It does not claim completed Row 4 acceptance; the pending rulings must be resolved
before completion. No review or approval is asserted by the producer.

Measured directly in this run:

```text
bypasses: 0/5
forgeable approvals: 1/1
```

There is deliberately no `forgeable approvals: 0/1` claim. A fully hand-written record
still authenticates by hash alone; expired records still pass. The regression tests are
red on both and will remain red until the missing approval trust/expiry decision is made.
The injection half is **NOT met**: twenty synthetic planted-instruction documents, their
manifest, and a positive control exist; no agent-scoring run occurred.

## Requirements, implementation and evidence

| Requirement | Changed files | Acceptance test and result | Red-on-fault seen |
|---|---|---|---|
| R-092 | `_system/tools/{registry.json,policy.py,__init__.py}`, `_system/tool_call.py`, `_system/guard_hook.py`, `docs/tools/EXAMPLE.md` | Schema refusal precedes execution and names its field; direct module green. Registry has 58 entries, enumerated below. Literal registered helper calls and restricted filesystem calls pass; shell composition and unknown helpers refuse. | yes: separator, unregistered helper, out-of-vocabulary assay |
| R-093 | registry and policy; `test_role_profiles.py` | Producer prepare enters preflight; reviewer prepare refuses on the workflow-parameter attack route. Human approve alone has allow; producer/reviewer refuse. No role CLI/environment override. Human/reviewer launch binding awaits ruling; OS-user deployment **NOT met**. | schema/guard faults tested; OS isolation not measured |
| R-094 | guard, `.claude/settings.json`; `test_protected_paths.py` | Exact equality of deny patterns; every enumerated write spelling against each protected target refuses; symlink escape outside workspace refuses and names Row 15. | yes: protected edit among five attacks; outside escape exercised |
| R-096 (this row's halves) | guard; executorlib | Explicit bypass-switch reasons including equals spelling; subprocess environment restricted to named exports and sbatch receives explicit names rather than ALL. No gitleaks hook or containment claim. | yes: equals-switch mutant |
| R-098 | guard; wrapperlib; `test_policy_attacks.py`; injection fixture | Five named classes denied by guard and every nf-core wrapper's real preflight, checking the attack-specific failure rather than unrelated missing prerequisites. `bypasses: 0/5`. Injection score **NOT met**. | yes: guard faults; live malicious config fixtures |
| R-099 | `_references/tool_pins.json`, `_system/tools/pins.py`, session_state.sh; `test_policy_pins.py` | Eleven shipped skill documents pinned by sha256; no workspace MCP servers declared. Inventory drift, altered/unreviewed/rejected pin refuses. Session initialization refuses shipped unreviewed pins. External-harness loading enforcement **NOT met**. | yes: unreviewed-pin mutant |
| R-073 (plan gates) | stage03_analysis; registry; `test_approval_forgery.py` | verify repeats vocabulary, venue, skeleton, output and relative/resolved-path gates; forged stamp and changed plan refuse; agent approve refuses in guard. Complete handwritten record and expired record remain **NOT met**. Issuance of expiry/timestamp and authenticated launch actor are stopped pending ruling. | yes: actual handwritten/expired records produce red tests; edited-plan mutant produces red |
| R-073 (config) | tools/execution.py, tools/policy.py, executorlib; `test_execution_policy.py` | Submit re-hashes before scheduler invocation. Registered collect is checked at guard/dispatcher boundary. Direct wrapper collect gate is **NOT met**, awaiting the render-only boundary exception. | yes: config-hash mutant and post-prepare edit |
| R-075 | wrapperlib, executorlib, tools/execution.py; seven nf-core render points | Charset plus shlex.quote at checks and render points; unsafe supplied header values refuse. Free-form backend argv/directives refuse; unfamiliar Groovy grammar refuses. Direct module green. | yes: header validator/quoting mutant |
| R-095 | none | Not applicable: no Docker configuration exists in gars; `_references/environment.md` records the constraint. | not applicable |

Paths abbreviated `_system/`, `_references/`, `.claude/` above are under `gars/`.
All additions under `gars/` are in the authorized new-module, tools, pin-file or injection
fixture locations. The seven modified wrappers are only the nf-core render points:
atacseq, chipseq, cutandrun, methylseq, rnaseq, scrnaseq, spatialvi. None of the three
downstream wrappers is modified. No other `gars/` path is changed.
README and DEVELOPMENT change only the count literals that `check_counts.py` reported,
from the derived runner count. Decision CONTEXT is regenerated, never hand-edited.

## Differences from the parent and the gap assessment

- **Already closed at c934f6d by 0042:** malformed hook payload fail-open; the specific
  inline-interpreter/write spellings enumerated in 0042; the bare `Status: APPROVED` line;
  plan hash mismatch and reapproval after reset; `$`, backticks, quotes, backslashes and
  line breaks through work_dir and scheduler config. M-3's executing work_dir vector was
  already closed, per the assessment's dated final addendum and owner ruling D-25.
- **This row closes further n-2/attack spellings:** `>|`, command-position changes through
  `cd &&`, stdin/inline interpreter routes, unregistered helper files and all unsupported
  executables. `dd of=`, `ln -sf`, truncate/install/chmod had already been narrowed by 0042;
  they now refuse independent of target-scanner recognition. Two bypass switches explicitly
  refuse. This replaces the incomplete denylist with a declared positive surface.
- **M-1:** resolved outside-workspace writes now refuse. Repo-root and non-agent builders
  still need Row 15's git hooks; this row does not claim those hooks exist.
- **M-2:** guard now refuses agent approval and verify repeats content gates. Full record
  authenticity after hook bypass and expiry remain red pending the owner ruling.
- **m-8:** settings/guard path equality is tested; pins and startup checks now exist, with
  their harness enforcement limits stated. R-095 remains not applicable.
- **R-075:** the charset is stronger than 0042; spaces in work_dir now refuse by the
  explicit required regex. Existing scientific formula/contrast values remain Python repr
  literals and are not incorrectly subjected to a shell-value regex. Every other supplied
  config scalar is checked. Safe nf-core job-body/header values retain their former bytes.
  Executor submission command bytes change under R-096 to include the export-name allowlist;
  existing tests expecting an unqualified sbatch command need the pending boundary ruling.
  No golden fixture under tests/fixtures was edited; no generated submit.sh golden-byte
  assertion failed in the first run. A source-text assertion for the profile seam does fail
  because quoting at that render point changes Python source without changing safe output.
- **Behavior restricted by R-075/R-098:** arbitrary backend descriptors and arbitrary
  Groovy code no longer execute. Only slurm/local backend argv and the seeded Groovy grammar
  are admitted. No later-row backend, lifecycle writer or manifest group is introduced.

## Fault witnesses

`test_policy_faults.py` makes disposable copies for guard mutations and scoped unittest
mocks for function/declaration faults. It executes an assertion witness and requires an
assertion failure, never merely a crash. Production source is not mutated. These are
producer-visible development controls, not sealed evaluation evidence.

| Planted fault | Witness | Observed |
|---|---|---|
| guard allows a separator | mutated guard takes only text before semicolon, guard witness expects refusal | red |
| guard allows unregistered helper | mutated guard returns early for unregistered.py | red |
| schema accepts out-of-vocabulary field | remove assay enum, field-refusal assertion fails | red |
| hand-written approval record | real complete fabricated record passes verify | red; fix blocked |
| expired approval | real expired record passes verify | red; fix blocked |
| plan edited after approval | replace approval_holds with accepting result | red |
| config edit after prepare | suppress config_holds comparison | red |
| unquoted value reaches header_lines | replace shell_value with identity | red |
| --no-verify with equals sign | mutated guard allows equals form | red |
| unreviewed pin | suppress the unreviewed-status refusal | red |

The two live red approval cases are not counted as fixed or as killed mutants. The eight
implemented regression witnesses print their `red-on-fault:` lines in the direct runner.

## Execution conditions

Every command ran from the repository root unless explicitly stated. All command invocations
set `TMPDIR`, `TEMP`, and `TMP` to the owner-designated sibling scratch directory. This report
calls that location `$SCRATCH`, and the checkout `$REPO`, to avoid committing machine paths.
Python verification invocations additionally set `PYTHONDONTWRITEBYTECODE=1` and
`GARS_PIPELINES=$SCRATCH/absent-pipelines`, so pipeline probes stay inside the allowed roots.
Guard subprocesses run with cwd `$REPO/gars` and `CLAUDE_PROJECT_DIR=$REPO/gars`; disposable
mutant guards use their scratch workspace for both. The direct filesystem commands never
execute attack payloads; tests submit payload text to the guard or preflight only.

Runtime: Python 3.13.2. Python 3.6 executable is absent; new runtime modules pass the
Python 3.6 grammar parser, but actual 3.6.8 execution is **NOT met**. sbatch, sacct,
Nextflow, Apptainer and pinned pipeline checkouts are absent. gitleaks and Rscript are
available but unused. GARS_ROW5_SCRATCH and CI are unset, so Row 5's existing named-scratch
skips apply. No Docker/cluster run, network download, push, remote addition or PR occurred.
The unchanged legacy tests include path-literal probes outside the checkout; no audit of
system temporary directories was performed and no new test creates fixtures there.

Hours: approximately 0.3 h measured from the first scratch implementation script to the
initial full verification pass; preliminary reading and owner/reviewer time are unmeasured.
This is elapsed implementation time, not a claimed 14–20 h budget expenditure.

## Runner results

Exact summaries are appended below from this run. A failed whole-suite result is not a
passing Row 4 exit. Expected study hash failures remain visible: the owner's standing ruling
is that this row merges only after the separate study's done commit. Its data/graders and
controls are not modified to conceal changed gars bytes.

`python3 tests/run_tests.py` (exit 1)

```text
collected 210 tests from tests
collected 82 tests from gars/tests
forgeable approvals: 1/1
bypasses: 0/5
Ran 292 tests in 138.301s
FAILED (failures=19, errors=9, skipped=50)
```

The 19 failures comprise the two live approval gaps, restricted submission for two old
unprepared local-executor fixtures, and existing expectations for formerly allowed shell,
work-dir, descriptor or source-text behavior. The nine errors comprise two unrestricted
custom-descriptor expectations and seven benchmark input-sha256 checks pinned to changed
wrapper source. None is relabelled a pass or hidden by a skip.

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 292 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 144.590s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_policy_attacks.py`

```text
bypasses: 0/5
Ran 19 tests in 3.707s
OK
```

`python3 gars/tests/test_approval_forgery.py`

```text
forgeable approvals: 1/1
Ran 6 tests in 0.152s
FAILED (failures=2)
```

`python3 gars/tests/test_protected_paths.py`

```text
Ran 4 tests in 28.046s
OK
```

`python3 gars/tests/test_tool_schema_refusal.py`

```text
Ran 7 tests in 0.383s
OK
```

`python3 gars/tests/test_role_profiles.py`

```text
Ran 5 tests in 0.017s
OK
```

`python3 gars/tests/test_policy_pins.py`

```text
Ran 3 tests in 0.175s
OK
```

`python3 gars/tests/test_execution_policy.py`

```text
Ran 4 tests in 0.040s
OK
```

`python3 gars/tests/test_policy_faults.py`

```text
Ran 8 tests in 0.637s
OK
```

## Surface enumeration from the tree

Commands actually run (repository root):

```sh
rg --no-ignore --hidden -n 'python3 ' gars -g CONTEXT.md
rg -n 'add_parser|add_argument|for name, needs_model' gars/_system/wrappers/*/*.py gars/_system/executorlib.py
```

The first grep without `--no-ignore --hidden` omitted the ignored stage-00 contract;
the complete enumeration below includes it. An additional pathlib walk confirmed every
CONTEXT.md occurrence. Argparse definitions were inspected from the existing modules by
intercepting parse_args in scratch; no helper was modified for enumeration.

Every occurrence, including repeated submit/status examples and variable wrapper spellings:

```text
gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md:48:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py <subcommand> \
gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md:86:5. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md:90:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md:129:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md:137:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/CONTEXT.md:96:python3 "$GARS_WRAPPERS/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py" ...   # wrappers run from anywhere
gars/02_bioinformatics/CONTEXT.md:114:   python3 _system/configure.py genomes --assay <Assay ID>
gars/02_bioinformatics/CONTEXT.md:115:   python3 _system/configure.py contrasts --project projects/<title> --assay <Assay ID>   # de assays
gars/02_bioinformatics/CONTEXT.md:116:   python3 _system/configure.py peaks                                                     # peaks assays
gars/02_bioinformatics/CONTEXT.md:123:   python3 _system/configure.py apply --project projects/<title> --assay <Assay ID> \
gars/02_bioinformatics/CONTEXT.md:146:   python3 _system/resolve_artifact.py --project projects/<title> --assay <Assay ID> \
gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md:49:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py <subcommand> \
gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md:95:5. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md:99:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md:137:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md:145:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/00_initialize_project/CONTEXT.md:173:   python3 _system/stage00_register.py assays
gars/00_initialize_project/CONTEXT.md:183:   python3 _system/stage00_register.py assays --select "<exactly what the user replied>"
gars/00_initialize_project/CONTEXT.md:194:   python3 _system/stage00_register.py create --title "<title>" --assays <assay_id> [<assay_id> ...]
gars/00_initialize_project/CONTEXT.md:209:   python3 _system/stage00_register.py inspect --assay <Assay ID> --source <path>
gars/00_initialize_project/CONTEXT.md:221:    python3 _system/stage00_register.py link --project projects/<title> --assay <Assay ID> --source <path>
gars/00_initialize_project/CONTEXT.md:233:    python3 _system/stage00_register.py finalize --project projects/<title> --model "<model id>"
gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md:58:python3 "${GARS_WRAPPERS:-_system/wrappers}"/spatial-cluster-count/spatial_cluster_count.py check   \
gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md:60:python3 "${GARS_WRAPPERS:-_system/wrappers}"/spatial-cluster-count/spatial_cluster_count.py prepare \
gars/02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md:62:python3 "${GARS_WRAPPERS:-_system/wrappers}"/spatial-cluster-count/spatial_cluster_count.py collect \
gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md:48:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py <subcommand> \
gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md:91:5. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md:95:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md:134:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md:142:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/01_prepare_samplesheets/CONTEXT.md:138:contract and differs per pipeline. `python3 _system/stage01_samplesheet.py --list-formats` prints
gars/01_prepare_samplesheets/CONTEXT.md:231:   python3 _system/stage01_samplesheet.py --project projects/<title> --check
gars/01_prepare_samplesheets/CONTEXT.md:253:   python3 _system/stage01_samplesheet.py --project projects/<title> --model "<model id>" [--confirm-exclusions] [--force]
gars/02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md:50:python3 "${GARS_WRAPPERS:-_system/wrappers}"/scrna-qc-cluster/scrna_qc_cluster.py <subcommand> \
gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md:49:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py <subcommand> \
gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md:98:5. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md:102:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md:140:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md:148:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md:48:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py <subcommand> \
gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md:113:5. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md:117:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md:156:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md:164:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:50:python3 "${GARS_WRAPPERS:-_system/wrappers}"/rnaseq-de/rnaseq_de.py <subcommand> --project projects/<title> \
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:86:   python3 _system/resolve_artifact.py --project projects/<title> --assay rnaseq_bulk \
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:97:6. Submit with `python3 <workspace>/_system/executorlib.py submit --workspace <project dir>
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:100:7. **On a later invocation** where STATUS is `SUBMITTED` or `RUNNING`: ask `python3 <workspace>/_system/executorlib.py
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:141:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md:149:Check progress: python3 <workspace>/_system/executorlib.py status --workspace <project dir> <job_id>
gars/02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md:55:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py <subcommand> \
gars/02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md:53:python3 "${GARS_WRAPPERS:-_system/wrappers}"/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py <subcommand> \
gars/03_custom_analysis/CONTEXT.md:84:   `python3 _system/resolve_artifact.py --project projects/<title> --assay <Assay ID> --list`
gars/03_custom_analysis/CONTEXT.md:87:2. Run `python3 _system/stage03_analysis.py create --project projects/<title> --slug <slug>`,
gars/03_custom_analysis/CONTEXT.md:100:   `python3 _system/stage03_analysis.py approve --project projects/<title> --analysis <NN_slug>`.
gars/03_custom_analysis/CONTEXT.md:105:   `python3 <workspace>/_system/executorlib.py submit --workspace <project dir> <script>` —
gars/03_custom_analysis/CONTEXT.md:113:   `python3 _system/stage03_analysis.py verify --project projects/<title> --analysis <NN_slug> --model "<model id>"`.
```

Declared calls (all JSON argument properties are in registry.json):

| Tool | Existing argv prefix | Arguments |
|---|---|---|
| `stage00_register.assays` | `python3 _system/stage00_register.py assays` | `select` |
| `stage00_register.create` | `python3 _system/stage00_register.py create` | `assays`, `title` |
| `stage00_register.inspect` | `python3 _system/stage00_register.py inspect` | `assay`, `sample-id-pattern`, `source` |
| `stage00_register.link` | `python3 _system/stage00_register.py link` | `assay`, `force`, `project`, `source` |
| `stage00_register.finalize` | `python3 _system/stage00_register.py finalize` | `date`, `integrity`, `model`, `project`, `sample-id-pattern` |
| `stage01_samplesheet` | `python3 _system/stage01_samplesheet.py` | `check`, `confirm-exclusions`, `force`, `list-formats`, `model`, `project`, `verify-integrity` |
| `configure.genomes` | `python3 _system/configure.py genomes` | `assay`, `select` |
| `configure.peaks` | `python3 _system/configure.py peaks` | `select` |
| `configure.protocols` | `python3 _system/configure.py protocols` | `aligner`, `select` |
| `configure.contrasts` | `python3 _system/configure.py contrasts` | `assay`, `factor`, `project` |
| `configure.apply` | `python3 _system/configure.py apply` | `aligner`, `assay`, `contrast`, `dry-run`, `factor`, `formula`, `genome`, `peaks-type`, `project`, `protocol` |
| `stage03_analysis.create` | `python3 _system/stage03_analysis.py create` | `project`, `slug` |
| `stage03_analysis.approve` | `python3 _system/stage03_analysis.py approve` | `analysis`, `date`, `project` |
| `stage03_analysis.verify` | `python3 _system/stage03_analysis.py verify` | `analysis`, `model`, `project` |
| `resolve_artifact` | `python3 _system/resolve_artifact.py` | `assay`, `consumes`, `list`, `prefer-adapted-from`, `project`, `type` |
| `nfcore_atacseq_wrapper.check` | `python3 _system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py check` | `project` |
| `nfcore_atacseq_wrapper.prepare` | `python3 _system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py prepare` | `project` |
| `nfcore_atacseq_wrapper.collect` | `python3 _system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py collect` | `model`, `project` |
| `nfcore_chipseq_wrapper.check` | `python3 _system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py check` | `project` |
| `nfcore_chipseq_wrapper.prepare` | `python3 _system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py prepare` | `project` |
| `nfcore_chipseq_wrapper.collect` | `python3 _system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py collect` | `model`, `project` |
| `nfcore_cutandrun_wrapper.check` | `python3 _system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py check` | `project`, `resume-refresh` |
| `nfcore_cutandrun_wrapper.prepare` | `python3 _system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py prepare` | `project`, `resume-refresh` |
| `nfcore_cutandrun_wrapper.collect` | `python3 _system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py collect` | `model`, `project` |
| `nfcore_methylseq_wrapper.check` | `python3 _system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py check` | `project` |
| `nfcore_methylseq_wrapper.prepare` | `python3 _system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py prepare` | `project` |
| `nfcore_methylseq_wrapper.collect` | `python3 _system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py collect` | `model`, `project` |
| `nfcore_rnaseq_wrapper.check` | `python3 _system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py check` | `project` |
| `nfcore_rnaseq_wrapper.prepare` | `python3 _system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py prepare` | `project` |
| `nfcore_rnaseq_wrapper.collect` | `python3 _system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py collect` | `model`, `project` |
| `nfcore_scrnaseq_wrapper.check` | `python3 _system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py check` | `project` |
| `nfcore_scrnaseq_wrapper.prepare` | `python3 _system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py prepare` | `project` |
| `nfcore_scrnaseq_wrapper.collect` | `python3 _system/wrappers/nfcore-scrnaseq-wrapper/nfcore_scrnaseq_wrapper.py collect` | `model`, `project` |
| `nfcore_spatialvi_wrapper.check` | `python3 _system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py check` | `project` |
| `nfcore_spatialvi_wrapper.prepare` | `python3 _system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py prepare` | `project` |
| `nfcore_spatialvi_wrapper.collect` | `python3 _system/wrappers/nfcore-spatialvi-wrapper/nfcore_spatialvi_wrapper.py collect` | `model`, `project` |
| `rnaseq_de.check` | `python3 _system/wrappers/rnaseq-de/rnaseq_de.py check` | `counts`, `design`, `project` |
| `rnaseq_de.prepare` | `python3 _system/wrappers/rnaseq-de/rnaseq_de.py prepare` | `counts`, `design`, `project` |
| `rnaseq_de.collect` | `python3 _system/wrappers/rnaseq-de/rnaseq_de.py collect` | `counts-from`, `model`, `project` |
| `scrna_qc_cluster.check` | `python3 _system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py check` | `h5ad`, `project` |
| `scrna_qc_cluster.prepare` | `python3 _system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py prepare` | `h5ad`, `project` |
| `scrna_qc_cluster.collect` | `python3 _system/wrappers/scrna-qc-cluster/scrna_qc_cluster.py collect` | `h5ad-from`, `model`, `project` |
| `spatial_cluster_count.check` | `python3 _system/wrappers/spatial-cluster-count/spatial_cluster_count.py check` | `h5ad`, `project` |
| `spatial_cluster_count.prepare` | `python3 _system/wrappers/spatial-cluster-count/spatial_cluster_count.py prepare` | `h5ad`, `project` |
| `spatial_cluster_count.collect` | `python3 _system/wrappers/spatial-cluster-count/spatial_cluster_count.py collect` | `h5ad-from`, `model`, `project` |
| `executor.submit` | `python3 _system/executorlib.py submit` | `script`, `workspace` |
| `executor.status` | `python3 _system/executorlib.py status` | `job-id`, `workspace` |
| `executor.cancel` | `python3 _system/executorlib.py cancel` | `job-id`, `workspace` |
| `fs.list` | `ls` | `flags`, `paths` |
| `fs.read` | `cat` | `flags`, `paths` |
| `fs.head` | `head` | `flags`, `paths` |
| `fs.tail` | `tail` | `flags`, `paths` |
| `fs.metadata` | `stat` | `flags`, `paths` |
| `fs.checksum` | `shasum` | `flags`, `paths` |
| `fs.lines` | `wc` | `flags`, `paths` |
| `fs.search` | `grep` | `flags`, `paths`, `pattern` |
| `fs.inspect` | `rg` | `flags`, `paths`, `pattern` |
| `fs.find` | `find` | `flags`, `paths` |

`executor.cancel` is a declared refusal: the underlying verb does not yet exist. Header
and describe were enumerated in the executor source but are outside ruling 2A's named
executor surface. Wrapper shell-variable spellings remain an explicit owner ruling needed;
contracts are byte-identical. Stage03 approve is declared human-only.

## Boundary audit

```sh
git diff --stat c934f6d -- evals/ .github/ gars/_system/hooks tests/fixtures
```

Output is empty. No gitleaks hooks/configuration, secret-containment test, trailer check,
new lifecycle writer, or extra manifest groups were added. No existing acceptance threshold,
formal review or gap assessment was edited. The decision index was rebuilt with
`bash docs/decisions/build_index.sh`. `git diff --check` is clean.
