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


## Round 2: provisional owner rulings

Date: **2026-09-22**. This section supersedes the round-1 work-in-progress status above;
all earlier report bytes remain an exact prefix. Producer work only: no review has run,
no approval by an independent reviewer is asserted, and no merge/push/remote operation occurred.
All five option-A instructions are applied as **provisional rulings, to be confirmed by
the owner**, attributed to the owner in [0054](../decisions/0054-row-4-provisional-rulings.md).
Decision 0053 remains byte-identical. All commands set TMPDIR, TEMP and TMP to the designated
sibling scratch folder; logs, scripts and disposable fixtures stay there. Python checks use
PYTHONDONTWRITEBYTECODE=1 and the scratch absent-pipelines path. No other build/review tree,
reviewer conversation, or sealed held-out slice was accessed.

### Ruling → changed files → test → result

| Ruling | Changed files | Test and result | Red-on-fault seen: yes/no, how |
|---|---|---|---|
| 1: human-owned approval store, UTC expiry, process actor | `stage03_analysis.py`, `executorlib.py`, `guard_hook.py`, `.claude/settings.json`, `tools/policy.py`; `test_approval_forgery.py`, `test_protected_paths.py`, `test_policy_faults.py` | `test_approval_forgery.py` passes: `forgeable approvals: 0/1`; forged status, workspace record after hook bypass, changed plan, expired genuine record and copied identical-plan record all refuse. Valid record succeeds. Store permissions, symlinks, malformed expiry, CLI actor/store overrides, env actor spoof, and submit expiry tested. Protected store read/write and resolved symlink access refuse. | yes: round-1 behavior reproduced the handwritten/expired-record failures; expiry and plan-check bypass mutants produce assertion failures in the current fault runner. |
| 2: changed-requirement expectations and derived benchmark pins | `tests/run_tests.py`, `gars/tests/test_guard_hook.py`, `gars/tests/test_executorlib_resume.py`, `benchmarks/tasks/{bulk-atacseq,bulk-rnaseq}.yaml`; README/DEVELOPMENT count claims; row-4 companion `test_execution_policy.py` | Full-suite result below. Each expectation update appears in the table below. Benchmark loader verifies all public input pins. Prepared content companion reruns all 19 affected collect cases with real helper-written fixture manifests; no production gate is mocked. Prepared local submit/failure/resume/completed re-entry succeeds. | yes: pre-fix characterization runs failed on these changed behaviors and stale pins; interim run had 19 missing-manifest failures. No unrelated failure was waived. |
| 3: direct collect gate in all ten wrappers | `wrapperlib.py`, exactly one added call per wrapper; `test_execution_policy.py`, `test_policy_faults.py` | Every direct collect checks the current hash before output access/writes; post-baseline edits refuse with the config_sha256 reason, unchanged configs pass the helper. Missing project retains exit 3. | yes: replacing the shared entry gate with a no-op makes the all-ten-wrapper witness fail an assertion. |
| 4: literal registered wrapper command paths | Eleven `gars/02_bioinformatics/**/CONTEXT.md` files, command spellings only; `test_tool_schema_refusal.py` | `14 contracts clean: sections, wait points, vocabulary.` All ten literal wrapper paths occur in contracts and match registry paths; variable forms absent from the command lines. | no mutation test; exact before/after command-only diff plus literal-path coverage and contract lint passed. |
| 5: cancel stays unavailable until row 12 | `tools/registry.json`, `tools/policy.py`; `test_role_profiles.py` | Producer, reviewer and human all receive the declared refusal naming row 12. Registry role metadata remains unchanged. | no mutation test; actual authorization calls for all three roles checked the row-12 reason. |

Runtime paths above are under `gars/_system/` unless explicitly qualified. The store is
`<workspace parent>/.gars-approvals/`, mode 0700; records are mode 0600 and bind both the
resolved plan identity and current SHA-256. Actor uses the OS UID/password database at launch.
UTC lifetime is 24 hours, to bound approval to a working-day execution window plus queue delay;
there is no implicit renewal. The addendum describes the long-job tradeoff and same-user limit.
The main CLI refuses a --workspace override that would move the store. Read/Glob/Grep are now
hooked, and registered filesystem reads are workspace-contained, including symlink resolution.

Three code corrections preserve behavior rather than changing tests: the shared collect helper
keeps nonexistent-project usage exit 3, and executor submit now uses the protected store instead
of its old sidecar path. A final positive control caught workspace-root Read/Glob/Grep
being misclassified as outside the workspace (Glob/Grep both exited 2 before the fix);
the guard now accepts the root itself, and the protected-path positive controls cover it.
No content-gate, golden submit-script fixture, benchmark acceptance
threshold, evaluation grader or frozen study assertion was weakened. The local executor fixtures
that lack prepare now expect refusal; the separate prepared positive test retains actual local
execution coverage. The 19 legacy collect tests retain their original downstream assertions;
the new missing-manifest expectation returns only for an unprepared fixture, while the prepared
companion runs those same assertions through the real wrapper CLIs. Those nested cases are
assertion coverage, not extra tests added to the loader's reported total.

### Updated expectations

Line numbers refer to the round-2 tree. Each row identifies one changed existing test;
multiple related assertions in that test share the row. Original fixture setup is unchanged.

| Test name | File and line | Old expectation | New expectation | Requirement that changed it |
|---|---|---|---|---|
| `WorkspaceFixture.test_12c_hand_written_approval_is_refused` | `tests/run_tests.py:469` | Error names PLAN.md.approved | Error names the human-owned store | R-073; ruling 1 |
| `WorkspaceFixture.test_12d_plan_edited_after_approval_is_refused` | `tests/run_tests.py:490` | Read record beside PLAN.md | Read returned protected store record; hash/edit assertions unchanged | R-073; ruling 1 |
| `WorkspaceFixture.test_12e_reapproval_after_reset_is_refused` | `tests/run_tests.py:515` | Snapshot and compare workspace sidecar bytes | Snapshot and compare the returned store record bytes | R-073; ruling 1 |
| `WorkspaceFixture.test_12f_stamp_words_in_prose_are_not_a_stamp` | `tests/run_tests.py:540` | Workspace sidecar exists after approve | Returned store record exists after approve | R-073; ruling 1 |
| `AtacseqWrapperTests.test_04_collect_gates` | `tests/run_tests.py:771` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `RnaseqGarsWrapperTests.test_02_collect_gates_on_content` | `tests/run_tests.py:914` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ExecutorSeamTests.test_03_descriptor_replaces_the_directives_block` | `tests/run_tests.py:1513` | Custom AWS descriptor emits its directives | R-075 backend-enum ValueError | R-075/R-098 |
| `ExecutorSeamTests.test_04_reproducibility_records_the_real_submission` | `tests/run_tests.py:1521` | sbatch SCRIPT | sbatch --export=PATH,HOME,USER,LOGNAME,LANG,LC_ALL,TMPDIR,TEMP,TMP,GARS_ROOT,GARS_PIPELINES SCRIPT | R-096 explicit export allowlist |
| `ExecutorSeamTests.test_05_local_backend_walks_submit_to_completed` | `tests/run_tests.py:1531` | Unprepared script gets PID, RUNNING and COMPLETED | No job, named R-073 refusal and no effect | R-073 submit precondition |
| `ExecutorSeamTests.test_06_local_backend_reports_a_failure_as_failed` | `tests/run_tests.py:1539` | Unprepared script runs and reports FAILED | No job and named R-073 refusal | R-073 submit precondition |
| `ExecutorSeamTests.test_07b_literal_braces_in_a_descriptor_survive` | `tests/run_tests.py:1561` | Custom submit/header JSON braces render | Custom submit/header refuse by backend enum; read-only status substitution unchanged | R-075/R-098 |
| `ExecutorSeamTests.test_07d2_every_nfcore_wrapper_takes_its_profile_from_the_venue` | `tests/run_tests.py:1615` | Source seam formats profile directly | Source seam formats wl.shell_value(profile, "nextflow_profile"); safe rendered bytes unchanged | R-075 charset and quoting |
| `ExecutorSeamTests.test_07g_work_dir_cannot_carry_shell_expansion` | `tests/run_tests.py:1745` | Plain work_dir containing a space passes | Space-containing value refuses R-075; safe paths still pass | R-075 charset |
| `ExecutorSeamTests.test_09_the_descriptor_names_which_nextflow_config_is_demanded` | `tests/run_tests.py:1831` | Only absent config fails; arbitrary process block then passes | Unsupported backend also fails; arbitrary Groovy grammar refuses after file exists | R-075/R-098 |
| `GuardHookTests.test_allows` | `tests/run_tests.py:2069` | Shell redirection, bash index-builder and raw sbatch allowed | Those three spellings denied; registered/read-only positive controls unchanged | R-092/R-098 |
| `GuardHookTests.test_allows_after_hardening` | `tests/run_tests.py:2109` | Inline Python, shell -c, malformed echo and ln allowed | All five unregistered/shell spellings denied | R-092/R-098 |
| `GuardHookTests.test_allows_reads_that_mention_a_writer_verb` | `tests/run_tests.py:2146` | cp from protected file to /tmp allowed | cp denied; both grep reads remain allowed (payload only, no /tmp write) | R-092/R-098 |
| `ScrnaseqWrapperTests.test_05_collect_gates_on_every_sample` | `tests/run_tests.py:2474` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaseqWrapperTests.test_06_the_raw_matrix_is_never_substituted_for_the_filtered_one` | `tests/run_tests.py:2525` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaseqWrapperTests.test_07_empty_combined_matrix_is_refused` | `tests/run_tests.py:2571` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialviTests.test_04_collect_gates_per_sample_and_never_takes_the_raw_h5ad` | `tests/run_tests.py:2769` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialviTests.test_05_a_missing_report_is_refused` | `tests/run_tests.py:2810` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_02_collect_accepts_a_well_formed_run` | `tests/run_tests.py:2943` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_03_an_anonymous_gene_is_refused` | `tests/run_tests.py:2964` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_04_a_renamed_identifier_column_is_refused` | `tests/run_tests.py:2981` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_05_a_sample_with_no_cells_is_refused_and_named` | `tests/run_tests.py:2999` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_06_the_nfcore_sample_suffix_is_matched_not_reported_lost` | `tests/run_tests.py:3018` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_07_a_label_matching_no_sample_is_refused` | `tests/run_tests.py:3038` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_08_zero_cells_or_zero_clusters_are_refused` | `tests/run_tests.py:3055` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `ScrnaQcClusterTests.test_09_collect_refuses_before_the_run_finished` | `tests/run_tests.py:3072` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialClusterCountTests.test_05_collect_refuses_before_the_run_finished` | `tests/run_tests.py:3278` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialClusterCountTests.test_06_collect_refuses_a_sample_set_that_differs_from_the_samplesheet` | `tests/run_tests.py:3297` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialClusterCountTests.test_07_collect_refuses_a_table_that_disagrees_with_the_summary` | `tests/run_tests.py:3326` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `SpatialClusterCountTests.test_08_collect_accepts_a_good_run_and_registers_only_table_and_report` | `tests/run_tests.py:3355` | Content success/failure or run-completion reason without a prepared manifest | When manifest absent: exit 2, config_sha256 missing reason, no OUTPUTS.tsv; prepared content expectations retained and rerun | R-073; ruling 3 (collect checks first) |
| `GuardHookTests.test_allowed_shapes` | `gars/tests/test_guard_hook.py:40` | git status allowed | git status denied; other read/edit/registered-call controls unchanged | R-092 registered surface |
| `GuardHookTests.test_bypass_switch_as_shipped` | `gars/tests/test_guard_hook.py:55` | Three git/bypass forms exit 0 | All three exit 2 | R-092/R-096 |
| `ExecutorlibResumeTests.test_interrupted_resume_and_completed_reentry` | `gars/tests/test_executorlib_resume.py:31` | Unprepared stage submits and changes effects across resume | No job, named R-073 refusal, no effect/marker; prepared resume covered separately | R-073 submit precondition |

The seven benchmark errors were seven callers of the same public task loader, not seven
distinct stale values: `test_coherent_forgery_and_missing_artifacts_are_red`,
`test_strict_reference_readiness_rejects_placeholders`,
`test_json_boolean_numeric_substitutions_are_red`, `test_missing_outputs_fail_not_skip`,
`test_nfcore_artifact_contracts_accept_and_reject_content`, `test_refusal_scorers_discriminate`,
and `test_task_schema_and_input_hashes` in `tests/test_benchmark_discriminates.py` (unchanged).
Two wrapper-source pins and two additionally affected contract pins are the complete changed
set in the public task inputs. There are no seven distinct wrapper values to list in this tree.
Re-derivation imported `evals/bench.py` and called `bench.file_sha(Path(input["path"]))`;
only a differing input's sha256 text was replaced. No other task-file line changed.

| Test/input pin | File and line | Old expectation | New expectation | Requirement that changed it |
|---|---|---|---|---|
| Public benchmark loader: `gars/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md` | `benchmarks/tasks/bulk-atacseq.yaml:10` | `e32ea7c7baa9ebcdf612c8052da705ff6ffaf2a11fd276743e605e75666c2a26` | `7c1871bfc681b1e4e65d721f16c03a8c2a95b1aafd99803d4c0d1fefd63b683b` | R-092; ruling 4 literal contract commands |
| Public benchmark loader: `gars/_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py` | `benchmarks/tasks/bulk-atacseq.yaml:14` | `beab610a01a430fa5eddf221322f140e9436b243d33af2ad1c102946c0e3ee06` | `62844f2bb1ef583611fbdd7f3a440d20d9cec77d316c2afe07b3e4539dab6fe9` | R-073/R-075; wrapper source changed |
| Public benchmark loader: `gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md` | `benchmarks/tasks/bulk-rnaseq.yaml:10` | `0aa735407c9f54ef09f9ebabb20f493d7a633613dc5c716ed560b0bc5510ee37` | `f62937e2b8f72b775583a53c71b44b2222105967f4b4c067221bdc1628b01780` | R-092; ruling 4 literal contract commands |
| Public benchmark loader: `gars/_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py` | `benchmarks/tasks/bulk-rnaseq.yaml:14` | `cd86380f31a6c1ed70513d576582dab0a2ba9099cf41ca97b42e348f6a4ffc60` | `b21b10fe1f097b149eacb6fcaa9337360348d34d38029216be006a7d1bd75558` | R-073/R-075; wrapper source changed |

README and DEVELOPMENT current count claims are updated from the loader to 305, with the
current collection date and report link so the new total is not attributed to the old merge.
No historical record is rewritten.

### Runner results (this run)

`python3 tests/run_tests.py`

```text
collected 210 tests from tests
collected 95 tests from gars/tests
forgeable approvals: 0/1
bypasses: 0/5
Ran 305 tests in 139.899s
OK (skipped=50)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
collected 210 tests from tests
collected 95 tests from gars/tests
suite: 305 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 163.579s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 gars/tests/test_policy_attacks.py`

```text
bypasses: 0/5
Ran 19 tests in 3.996s
OK
```

`python3 gars/tests/test_approval_forgery.py`

```text
forgeable approvals: 0/1
Ran 11 tests in 0.284s
OK
```

`python3 gars/tests/test_protected_paths.py`

```text
Ran 5 tests in 24.896s
OK
```

`python3 gars/tests/test_tool_schema_refusal.py`

```text
Ran 8 tests in 0.424s
OK
```

`python3 gars/tests/test_role_profiles.py`

```text
Ran 6 tests in 0.017s
OK
```

`python3 gars/tests/test_policy_pins.py`

```text
Ran 3 tests in 0.165s
OK
```

`python3 gars/tests/test_execution_policy.py`

```text
Ran 7 tests in 23.717s
OK
```

`python3 gars/tests/test_policy_faults.py`

```text
Ran 10 tests in 1.101s
OK
```

### Boundary and preservation audit

`git diff --stat c934f6d -- evals/gap-study evals/gap-study-2 evals/gap-study-3 evals/haiku-prestudy evals/transcript.py .github/ gars/_system/hooks` is empty.
The entire `evals/` tree, gitleaks configuration and secret-containment test are unchanged.
All ten round-2 wrapper diffs are one added shared-helper call. Contract diffs are only
literal command-path substitutions. Task diffs contain four sha256 replacements and nothing
else. Decision 0053 matches HEAD bytes; the report's previous bytes are an exact prefix.
Decision index regenerated using `bash docs/decisions/build_index.sh`. `git diff --check`
passes. One round-2 commit stages only the enumerated changed paths, with its message file
in scratch. No push, remote or merge.

## Owner rulings needed

None for further implementation in this round. The owner still confirms or reverses all
five **provisional** option-A rulings recorded in 0054. This is not independent review approval.

## Residual gaps still open (round 2)

- **NOT met:** injection resistance 20/20 with its positive control; no agent-scoring run.
  `bypasses: 0/5` measures the separate deterministic attack list only.
- **NOT met:** R-093 separate OS user/read-only reviewer credential. The same OS user can
  bypass the harness, alter its own approval store or invoke approve directly; the process
  UID does not distinguish an agent from a human. See 0054, “What this does not close”.
- **NOT met:** external-harness R-099 load enforcement/global inventory/pre-hook loading;
  shipped pins remain unreviewed pending independent review.
- Contract-prose follow-up: `gars/03_custom_analysis/CONTEXT.md:58` still describes the
  workspace sidecar and its process still directs dialogue-triggered agent approval. Only
  wrapper command substitutions are authorized in contracts this round, so those lines stay
  untouched. The new protected-store/human-CLI behavior is documented in 0054; contract lint
  does not establish semantic agreement for this legacy prose.
- Actual Python 3.6.8 execution and Slurm/Nextflow/cluster validation remain unmeasured.
  The local resume test is not the spec's Slurm acceptance. Existing named environment,
  row-5 scratch, sealed-data and owner-evidence skips are not promoted to passes.
- New explicit limitation: the 24-hour approval expires even if queue/runtime delays defer
  verification; no renewal or deployment isolation is invented. A new analysis requires a
  new approval. The owner may revise the provisional lifetime.
- `cancel` is deliberately unavailable until row 12. No row-15 hook/gitleaks/secret-containment
  exit claim, lifecycle writer, additional manifest group or independent review is supplied.
- The standing merge-after-study condition remains. The tested deterministic exits pass;
  the broader row acceptance still has the unmeasured gaps above.

## Review round 3 fixes

Date: **2026-09-22**. Reviewed baseline: `a78f8b19a8b460f29678884432763b65bc57fe1d`.
The sole supplied review, `docs/reviews/row_4_review.md`, gives **APPROVE WITH CHANGES**;
its heading says repository-side round 1, while this producer response is round 3 as
instructed. The review remains untracked and byte-identical. The owner's 22 September
provisional rulings recorded in 0054 **stand** under this round's explicit instruction;
the historical requests to reconfirm them are not reopened. Earlier report sections and
all decision/review/assessment records remain unchanged.

The finding labels below identify the review's two MINORs and three NOTEs in their order.
Both MINOR implementations stop at the review's explicit owner boundary. No finding is
disputed, and no test, threshold, pin status or guard is weakened. DEVELOPMENT receives
only a new current-status paragraph pointing here; inherited claims remain out of scope.

| Finding | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| M1 — MINOR documentation, R-073: legacy stage-03 sidecar/agent-approval prose | This report; `DEVELOPMENT.md` status only | Read `gars/03_custom_analysis/CONTEXT.md:58-64,99-102`; rerun `test_approval_forgery.py` and contract lint | **Open: owner edit plus approval record required by review.** Protected contract unchanged; lint does not prove semantic agreement. Red-on-fault seen: **no** for prose; the implementation's plan/expiry witnesses are separately reported below. |
| M2 — MINOR policy, R-099: all unreviewed pins refuse session initialization | This report; `DEVELOPMENT.md` status only | `test_policy_pins.py`, including `test_session_start_refuses_unreviewed`; `test_policy_faults.py` | **Open: owner scope ruling required.** All eleven pins remain unreviewed and startup remains fail-closed. Red-on-fault seen: **yes**, the existing unreviewed-pin mutant makes its refusal assertion fail; that does not settle the session-scope choice. |
| N1 — NOTE provenance, R-170: inherited cluster claims | This report | Compare the cited phrases in `git show c934f6d:DEVELOPMENT.md` / `git show c934f6d:README.md` with the working files | Answered: claims stay because they are inherited and expressly out of scope; no cluster evidence is asserted by this round. Red-on-fault seen: **no**, provenance comparison only. |
| N2 — NOTE security, R-093: same-UID store forgery | This report | `test_approval_forgery.py`, `test_role_profiles.py`; review and 0054 limitation | Answered: separate-OS-user deployment remains **NOT met**, so guarded forgery results do not close the same-UID gap. Red-on-fault seen: **no** for deployment isolation; no isolation was installed or tested. |
| N3 — NOTE test gap, R-092: actual Python 3.6.8 / cluster execution | This report | Current runners use Python 3.13.2; `command -v python3.6` found no executable | Answered: actual 3.6.8 and live Slurm/Nextflow execution remain **NOT met** because the required environment was not exercised. Red-on-fault seen: **no**, these runtime measurements were not performed. |

### Verification conditions and results

Commands ran from the repository root with TMPDIR, TEMP and TMP set to the designated
sibling scratch folder before execution. Logs and disposable fixtures stay there under
`round-3/` or the test runners' scratch prefixes. Python checks set
`PYTHONDONTWRITEBYTECODE=1` and `GARS_PIPELINES=$SCRATCH/absent-pipelines` as in round 2.
The login-shell `python3` is **3.13.2**; a read-only non-login version probe returned
3.8.2, but that interpreter was not used for the verification runners. No Python 3.6
executable was found on PATH. Existing environment/owner-evidence skips are not passes.
No reviewer conversation, other build folder, network service or held-out data was read.

The following are verbatim runner summary lines from this round; every listed command
must have exit 0 for its passing claim. The fault runner's ten `red-on-fault` lines record
assertion failures under planted faults, not failures of the unmodified implementation.

`python3 tests/run_tests.py` (exit 0)

```text
collected 210 tests from tests
collected 95 tests from gars/tests
forgeable approvals: 0/1
red-on-fault: missing wrapper contract section -> test_wrapper_contract.WrapperContractTests.test_all_wrapper_contracts (wrapper='nfcore-methylseq-wrapper')
bypasses: 0/5
Ran 305 tests in 132.334s
OK (skipped=50)
```

`python3 tests/check_contracts.py` (exit 0)

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py` (exit 0)

```text
collected 210 tests from tests
collected 95 tests from gars/tests
suite: 305 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/check_results.py --controls --lexicon` (exit 0)

```text
clean — graded=1
```

`python3 gars/tests/test_policy_attacks.py` (exit 0)

```text
bypasses: 0/5
Ran 19 tests in 2.935s
OK
```

`python3 gars/tests/test_approval_forgery.py` (exit 0)

```text
forgeable approvals: 0/1
Ran 11 tests in 0.234s
OK
```

`python3 gars/tests/test_protected_paths.py` (exit 0)

```text
Ran 5 tests in 21.068s
OK
```

`python3 gars/tests/test_tool_schema_refusal.py` (exit 0)

```text
Ran 8 tests in 0.274s
OK
```

`python3 gars/tests/test_role_profiles.py` (exit 0)

```text
Ran 6 tests in 0.012s
OK
```

`python3 gars/tests/test_policy_pins.py` (exit 0)

```text
Ran 3 tests in 0.108s
OK
```

`python3 gars/tests/test_execution_policy.py` (exit 0)

```text
Ran 7 tests in 14.404s
OK
```

`python3 gars/tests/test_policy_faults.py` (exit 0)

```text
Ran 10 tests in 0.632s
OK
```

`python3 gars/tests/test_guard_hook.py` (exit 0)

```text
Ran 4 tests in 1.673s
OK
```

`python3 gars/tests/test_executorlib_resume.py` (exit 0)

```text
Ran 1 test in 0.004s
OK
```

`python3 evals/test_harness.py` (exit 0)

```text
Ran 44 tests in 143.517s
OK
```

Fault witnesses from `python3 gars/tests/test_policy_faults.py`:

```text
red-on-fault: direct collect config gate is omitted
red-on-fault: config edit after prepare is accepted
red-on-fault: expired approval is accepted
red-on-fault: unquoted value reaches header_lines
red-on-fault: guard allows --no-verify equals
red-on-fault: plan edited after approval is accepted
red-on-fault: schema accepts out-of-vocabulary field
red-on-fault: guard allows separator
red-on-fault: guard allows unregistered helper
red-on-fault: unreviewed pin is accepted
```

### Preservation checks

Round-3 changes are limited to this append-only report and a current-status insertion in
DEVELOPMENT.md. The previous report bytes are an exact prefix; the supplied review's
SHA-256 is unchanged and it stays untracked. No decisions, formal reviews, assessments,
runtime code, tests, pins, contracts, benchmark tasks, protected study trees or `.github/`
files are changed. `git diff --check` is clean. The final staged-path and commit-identity
checks ensure only these two document paths and a generic producer identity enter the
single round commit; the commit message is read from a file in sibling scratch.

## Owner rulings needed

1. **M1 — R-073 protected stage-03 contract correction.** The review's requested action is
   to correct the prose to the protected-store, human-CLI model as **the owner's edit plus
   an approval record**. This includes the Approved definition and the process step that
   currently directs the agent to run `approve`. The review provides no alternative model;
   the question is authorization/delivery of that protected-contract edit and its approval
   record. The 0054 approval-store ruling already stands; this does not ask to reconsider
   its schema, actor binding or expiry. No contract edit or approval record is fabricated.
2. **M2 — R-099 session-refusal scope.** The review's options are: confirm that refusing
   every session until independent review is the intended fail-closed stance; **or** scope
   refusal to loading the unreviewed resource rather than the whole session. Which scope
   is intended? Pending that ruling, SessionStart still exits 2 for unreviewed pins. No
   shipped pin is promoted by the producer, and pre-hook/external-harness enforcement is
   not claimed. Any implementation requiring row-15 files must remain on that other
   branch and needs the owner's routing; none is attempted here.

Only these two new review items await owner action. The five existing provisional rulings
stand; this response neither reverses them nor makes a new policy choice.

## Residual gaps still open (round 3)

- M1's misleading protected contract prose and M2's session-wide startup refusal remain
  open pending the owner actions above. Neither MINOR is reported as closed.
- Injection resistance **20/20 with its positive control remains NOT met**: no agent-scored
  injection run. The deterministic `bypasses: 0/5` test is a separate measurement.
- R-093 separate OS user/read-only reviewer credentials remain **NOT met**; an unguarded
  process with the launching UID can forge store contents or invoke the human CLI.
- R-099 external-harness loading enforcement, global inventory and pre-hook loading remain
  **NOT met**. The supplied row review is not treated as promotion of individual skill pins.
- Actual Python 3.6.8, live cluster/Slurm/Nextflow and skipped environment/owner-evidence
  cases remain unverified. Inherited cluster claims are not revalidated by these local tests.
- The 24-hour expiry and lack of implicit renewal remain as ruled; `cancel` remains
  unavailable until row 12. No row-15 hook, gitleaks or secret-containment exit is claimed.
- The standing merge-after-study condition remains. No merge, push, remote operation or
  pull request occurred. Passing named deterministic exits do not establish broader
  deployment or release acceptance.
