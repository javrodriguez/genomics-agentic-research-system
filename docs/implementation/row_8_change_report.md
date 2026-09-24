## Step A: catalogue

Started from `dc6b803fea84b8c2df8bb748e3312fc3220800a9` on
`build/gars-row-8-catalogue`, with a clean working tree.
Step A code and offline witnesses are implemented. Captured live DOI response
fixtures remain **NOT met**, pending the ruling below. No sealed exit is claimed.
No push, remote, approval or merge was performed.

**DELEGATED RULINGS (label kept exactly; review round 5 NOTE-2).**
Every brief ruling was decided under the owner's standing delegation (23 Sep 2026).
The brief is Glitch's delegated specification, not the owner's words.

### Requirement → files → acceptance → result

| Requirement | Changed files | Acceptance | Result / red-on-fault |
|---|---|---|---|
| R-114, §17, D-18 | `benchmarks/defects/`, `tests/test_planted_defects.py` | DevelopmentCatalogueTests; list-order table, SHA pins, 19 projects all graded, placeholder fixed in denominator | 9/10 development; 0/10 false flags; yes, denominator and unavailable-check faults go red |
| §7.2 sex check, R-141, R-042 | `gars/_system/stage01_samplesheet.py`, stage 00/01 contracts | test_sex_age_thresholds; case/whitespace/order sweep | green; yes, removed sex refusal and 0.9 threshold go red |
| R-145, R-042 | stage 01 helper and contracts | test_subject_replication, development class 4 | green; yes, cell and subject-count removals go red |
| R-114 label swaps, R-042 | stage 01 helper and contracts | test_case_whitespace_lanes_and_order; test_not_checkable_is_not_pass | green; yes, inverted index and unavailable-as-pass go red |
| R-114 FASTQ truncation, R-042 | `gars/_system/integrity.py`, `gars/tests/test_integrity_records.py`, contracts | whole/plain/gzip records, default-vs-full CLI; development class 6 | green; yes, both plain and gzip-valid record-truncation faults go red |
| R-114 evidence paths | `gars/_system/claims/evidence_check.py`, `gars/_system/claims/emit_report.py`, `gars/tests/test_emit_report.py` | absent, altered, absolute, parent-component and escaping-symlink evidence; absent/existing output preservation | green; yes, removed hash check and absolute-path acceptance go red |
| R-114 emission wiring | new evidence/emission modules and emission tests | clean bytes equal unchanged renderer; export once; same checked/rendered snapshot | green; yes, early write and --from-db forwarding go red |
| R-114 raw p-values, R-042 | `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`, its contract, `tests/run_tests.py` | test_collect_diagnostic_drift drives real collect and check-table, including full/6-significant-digit and one-row clean tables | green; yes, padj-below-p, removed BH and tightened tolerance go red |
| DOI half of R-125 | `gars/_system/resolve_citation.py`, `gars/tests/test_citation_resolution.py`, `gars/tests/fixtures/citations/` | five real/five fabricated replay cases, DataCite fallback, transient refusal, parser/import whitelist | offline protocol tests green; yes, Crossref-only, network-as-success, env and suppressed-option faults go red; captured response provenance NOT met |
| R-114 sealed interface | runner; `benchmarks/defects/SEALED-INTERFACE.md`; 0101 | SealedOutputDisciplineTests; row-1 mapping/detail family; actual sealed TestCase with malformed synthetic control | green; yes, leaked stdout, skipped errors and wrong mapping go red; actual sealed measurement SKIPPED |
| R-167 reporting | `docs/ledger.csv`, README, DEVELOPMENT, 0101 and this report | 19 unsealed ledger rows; count check; README metric/date unchanged | hours and dollars unknown, blank; public evidence remains unmeasured |

`catalogue.yaml` uses JSON-compatible YAML, following row 2's stdlib pattern.
The generator uses seed 801. Committed development copies are generated once
and pinned by SHA-256. Test generation uses scratch only. Clean projects span
RNA/ATAC, optional metadata, gzip/plain and multiple lanes, full and six-digit
BH tables, a lone BH-consistent row, extra plant_note, and artifact/DOI evidence.
The schema block is identical in both stage contracts, the interface, the
runner docstring and 0101.

### Protected files touched (one per line)

- `gars/_system/stage01_samplesheet.py`
- `gars/_system/integrity.py`
- `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`
- `gars/_system/claims/evidence_check.py`
- `gars/_system/claims/emit_report.py`
- `gars/_system/resolve_citation.py`
- `gars/00_initialize_project/CONTEXT.md`
- `gars/01_prepare_samplesheets/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`

0104 is the separate delegated approval record and is not written here.
No config keys, templates, registry, executor, registrar, wrapper library,
row-7 existing claim files, frozen benchmarks, evals or release-check files change.

### Development EXIT lines (verbatim)

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

Actual sealed fixtures were neither constructed, searched for nor inspected.
The required synthetic output-discipline controls are producer-authored test inputs,
not seals. Actual SealedCatalogueTests skips with “sealed catalogue unmeasured”.
There are no actual sealed EXIT measurements to report.

### Expectation changes at BASE

| BASE location | Old expectation/fixture | Change | Why / unchanged assertions |
|---|---|---|---|
| `tests/run_tests.py:1034`, RnaseqGarsWrapperTests.test_04_de_prepare_and_collect | one row: g1,1,2,0.1,0.2, expected collect success | two rows: g1,1,2,0.01,0.02 and g2,1,2,0.04,0.04 | A one-row BH adjustment is p itself. Every success assertion is retained. |

The BASE pvalue,padj grep finds only :1019 and :1034. The anonymous-gene
refusal at :1019 remains unchanged. The broader integrity grep finds only
direct integrity calls at :584/:587 on whole/gzip-framing-truncated data;
their verdicts do not change. No existing stage-00 finalize/full or stage-01
full synthetic FASTQ call was found, so no such fixture expectation changes.
New full-mode tests cover both plain and record-truncated gzip; both callers
are named in 0101's R-042 section.

The additional optional metadata columns are accepted under this brief's
open-schema contract, with header names trimmed and case-normalized.
Existing row-1 development fixtures and row-2 non-pseudoreplicate inputs keep
their verdicts. Row-7 renderer inputs/template and existing claim SQL remain
byte-identical to BASE.

### Commands and execution conditions

Every shell command ran from the repository root. No command changed directory.
Every invocation set the scratch-twin environment first:

```bash
export TMPDIR="$(pwd)-scratch" TEMP="$(pwd)-scratch" TMP="$(pwd)-scratch"
```

No system temp folder was used. Reads used cat/sed/grep and git show/grep/status;
rg was attempted first but is unavailable. Source and fixture writes used
quoted heredocs and Python pathlib; no shell-expanded source text was used.
All test subprocesses inherited the same scratch settings. Fault and baseline
drivers use TemporaryDirectory under that scratch twin and restore byte backups,
never a Git checkout restore. No model or network enters development grading.

The recorded startup command was `git rev-parse HEAD`; result is the starting
hash above. `git branch --show-current` returned the named build branch.
The BASE audit used:

```bash
git grep -n -E "pvalue,padj|verify-integrity|integrity.*full|full.*integrity" dc6b803 -- tests gars/tests
```

The row-7 invariant check is empty:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

`bash docs/decisions/build_index.sh` regenerated the index.
`git diff --check` is clean. AST parsing with feature_version=(3,6) accepts
all step-A Python files; actual execution used **Python 3.13.5**, including
the eval harness (>=3.9). This does not claim execution on Python 3.6.

### Parent red and disposable faults

`python3 benchmarks/defects/baseline_check.py` archives BASE in scratch,
copies the new tests/catalogue there and first observes the missing-module
import failure. Its second phase uses only an availability adapter for absent
new modules (returns nonzero with no catch code); it does not supply a detector
to BASE. Every available stage is the real parent entry point.

```text
BASE import: RED (missing gars/_system/resolve_citation.py)
BASE class 1: caught
BASE class 2: caught
BASE class 3: not caught
BASE class 4: not caught
BASE class 5: not caught
BASE class 6: not caught
BASE class 7: not caught
BASE class 8: not caught
BASE class 9: not caught
BASE behavioral: 2/10; classes 3, 4, 5, 6, 7, 8, 9 not caught
```

The corresponding current runner is green. Class 6's parent plant is record-truncated
inside a valid gzip stream. `python3 benchmarks/defects/red_on_fault.py`
copies only the known source/test trees into scratch, plants each fault separately,
checks its named unittest assertion fails and restores byte-identical backups.
The production checkout is never mutated by that driver.

| Fault | Named test | Red-on-fault seen |
|---|---|---|
| sex confounding removed | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_sex_age_thresholds` | yes |
| imbalance threshold 0.9 | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_sex_age_thresholds` | yes |
| cell pseudoreplication removed | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_development_exit` | yes |
| subject count removed | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_subject_replication` | yes |
| index comparison inverted | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_case_whitespace_lanes_and_order` | yes |
| not_checkable counted pass | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_not_checkable_is_not_pass` | yes |
| evidence hash not compared | `gars/tests/test_emit_report.py EmitReportTests.test_changed_hash` | yes |
| absolute evidence accepted | `gars/tests/test_emit_report.py EmitReportTests.test_path_containment` | yes |
| padj below pvalue allowed | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_collect_diagnostic_drift` | yes |
| BH recompute removed | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_collect_diagnostic_drift` | yes |
| Crossref 404 alone unresolved | `gars/tests/test_citation_resolution.py CitationResolutionTests.test_prefixes_and_datacite_fallback` | yes |
| network error resolved | `gars/tests/test_citation_resolution.py CitationResolutionTests.test_transient_refuses` | yes |
| unparseable plant skipped | `tests/test_planted_defects.py SealedOutputDisciplineTests.test_sentinel_and_error_accounting` | yes |
| unmapped folded into class | `tests/test_planted_defects.py SealedOutputDisciplineTests.test_unmapped_outside_arithmetic` | yes |
| Hi-C denominator removed | `tests/test_planted_defects.py SealedOutputDisciplineTests.test_sentinel_and_error_accounting` | yes |
| truncated plain FASTQ passes | `gars/tests/test_integrity_records.py IntegrityRecordTests.test_stage01_plain_truncation_and_default` | yes |
| gzip-valid record truncation passes | `gars/tests/test_integrity_records.py IntegrityRecordTests.test_records_plain_and_gzip` | yes |
| report written before preflight | `gars/tests/test_emit_report.py EmitReportTests.test_missing_path` | yes |
| sealed stdout leaked | `tests/test_planted_defects.py SealedOutputDisciplineTests.test_sentinel_and_error_accounting` | yes |
| invalid_design mapped without family | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_row1_mapping_detail_family` | yes |
| BH tolerance 1e-6 | `tests/test_planted_defects.py DevelopmentCatalogueTests.test_collect_diagnostic_drift` | yes |
| environment replay switch | `gars/tests/test_citation_resolution.py CitationResolutionTests.test_no_replay_switch` | yes |
| suppressed replay option | `gars/tests/test_citation_resolution.py CitationResolutionTests.test_no_replay_switch` | yes |
| renderer receives from-db | `gars/tests/test_emit_report.py EmitReportTests.test_database_export_once_same_snapshot` | yes |

`red-on-fault: 24/24`

### Verification summaries

Final command summaries below are from completed runs.
One full suite ran at a time. The first run, before the new decision record was
in Git's inventory, ended `Ran 482 tests in 79.257s`,
`FAILED (failures=1, skipped=79)`; its sole failure was dangling decision 0101.
Adding the new record to the index made the decision-link test green. The next
run ended `Ran 484 tests in 79.286s`, `OK (skipped=79)`.
An explicit row-2 non-pseudoreplication control was then added. An optional
attempt setting GARS_ROW5_SCRATCH to the allowed scratch twin ended
`Ran 467 tests in 88.418s`, `FAILED (failures=8, errors=13, skipped=35)`.
All failures/errors were in Row05OfflineTests; its existing external-path guard
returned local_dir_in_repo. That optional scratch setting cannot establish
row-5 evidence on this deployment. No row-5 assertion or code was changed.
The final requested command uses the default environment, where decision 0051
skips row-5 tests without a qualifying named scratch. It ends OK below.
The database classes for rows 5 and 7 are skipped, not verified here.

An opt-in `GARS_NETWORK_TESTS=1` invocation of
`CitationResolutionTests.test_ten_live_dois` through unittest attempted to capture
live bodies, and ended `Ran 1 test in 0.007s`, `FAILED (failures=1)`.
The first real DOI returned citation_unverifiable. No live response recording
was produced. The failed attempt did not update the replay fixture.
Its capture wrapper called the same live test and transport, wrote responses
only if all ten cases passed, and made no other network requests.

The committed response fixture explicitly says its minimal bodies are synthetic
protocol examples based on the supplied CP0.9 behavior. Its URL/status/body SHA-256
records are internally checked, but they are **not claimed to be captured service
responses**. The five-real/five-fabricated replay tests verify protocol handling,
not the truth or current registration of those ten identifiers.

### Final required command summaries (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
Ran 485 tests in 79.391s
OK (skipped=79)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 237 tests from tests
collected 248 tests from gars/tests
suite: 485 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py` (Python 3.13.5):

```text
Ran 44 tests in 37.341s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
  published=3 graded=1
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 14 tests in 3.288s
OK (skipped=1)
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 gars/tests/test_citation_resolution.py`:

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

Additional targeted commands: `python3 gars/tests/test_emit_report.py`
(`Ran 8 tests in 0.085s`, `OK`);
`python3 gars/tests/test_integrity_records.py`
(`Ran 2 tests in 0.068s`, `OK`);
`python3 -m unittest discover -s tests -p test_decision_links_resolve.py -v`
(`Ran 3 tests in 0.147s`, `OK`, `citations: 299/299 resolve`, before final staging).
The final boundary audit reports `staged fixture pins: 162/162` and
`changed-path boundary: clean (189 staged files)`.
The ignored synthetic FASTQ files were added by their exact catalogue-pinned
paths with git add -f; no real data or unrelated ignored file was staged.

### Hours and cost

Hours: unknown. Metered dollars: unknown. No session-meter measurement was supplied.
All nineteen appended ledger rows leave both fields blank, never zero.
The commit field is blank until the containing commit exists; the row notes
identify this step's containing commit. No self-referential commit hash is fabricated.

### Residual gaps

- **NOT met:** captured live HTTP response fixtures; ruling below.
- **NOT met:** live DOI resolution (opt-in attempt refused unverifiably).
- **NOT met:** sealed >=9/10 across all ten catalogue classes and actual sealed
  clean measurement; no sealed fixture was accessed.
- **NOT met:** external_human_seal/public credibility; README number/date remain unmeasured.
- **NOT met:** PMID/E-utilities and literature-role typed-tool wiring of R-125.
- **NOT met:** stage-03/pilot integration of emission; direct render_report bypass is unguarded.
- **NOT met:** R-069 liveness beyond claim evidence.
- **NOT met:** class-10 detector; Hi-C remains planted/not caught.
- **NOT met:** pilot-1 measurement.
- **NOT met:** step B's venue/data-policy/backend work.
- **NOT met:** actual Python 3.6 execution, live pipelines/HPC and cluster acceptance.
- **NOT met:** Docker database tests (rows 5 and 7); skipped on this host.
- **NOT met:** optional row-5 offline execution with the allowed scratch twin;
  its existing external-path guard refuses that setting. The requested default
  suite follows the existing environment-skip policy, unchanged.
- **NOT met:** independent review, delegated protected-change approval, and merge.

## Owner rulings needed

1. **Captured DOI responses (deliverable 5).** The brief requires recorded HTTP
   responses, but the permitted opt-in live test returned citation_unverifiable
   immediately and could not capture them. This part is stopped; synthetic
   protocol fixtures are labeled as such and are not promoted to live evidence.
   Options: supply captured request URL/status/body records for the five real
   (including DataCite) and five fabricated cases, with body SHA-256; or explicitly
   accept the labeled synthetic replay fixtures for this step and retain live
   registration/capture as NOT met. The question was submitted while independent
   offline work continued; no answer or approval is inferred from elapsed time.
