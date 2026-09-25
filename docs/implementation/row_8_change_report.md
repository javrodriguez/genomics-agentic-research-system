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

## Step A retry round B1 (path scan)

Date: 2026-09-24. The first command recorded starting commit
`e367a41272af65557d46cb5d7ab2f2c5d56e9c5a`; the working tree was clean,
on `build/gars-row-8-catalogue`. Round 1 remains the parent.
The retry scope was decided under the owner's standing delegation (23 Sep 2026).

This retry replaces every literal U+007E in the files round 1 edited by hand:
41 lines in seven files. Executable values are assembled with `chr(126)`;
prose, examples and docstrings use the same character notation. No detector,
threshold, test assertion or fixture verdict changes. No Rule 5 command failed,
so no additional implementation change was needed. This section is appended
after the original report's last byte; all its previous text, including its
unresolved captured-response ruling, remains unchanged. Decision 0101 remains
byte-identical; no addendum or index regeneration is needed. The sole remaining
match among round-1 changed files is in the generated decision index, which
was not edited by hand and is left unchanged.

### Every replacement (line numbers unchanged)

Old shapes name U+007E without writing the literal character. Each row identifies
one complete changed line; multiple occurrences on that line share the replacement.

| File | Line | Old shape | New shape |
|---|---|---|---|
| `DEVELOPMENT.md` | 194 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 213 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 251 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 255 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 259 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 269 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 275 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 292 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 300 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 305 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 324 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 342 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 344 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 356 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 360 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 370 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 376 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 402 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 403 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 405 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 406 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 415 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 416 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 417 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 418 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 425 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 460 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 462 | literal character in prose or example | `chr(126) notation` |
| `DEVELOPMENT.md` | 469 | literal character in prose or example | `chr(126) notation` |
| `gars/00_initialize_project/CONTEXT.md` | 111 | literal character in prose or example | `chr(126) notation` |
| `gars/01_prepare_samplesheets/CONTEXT.md` | 168 | literal character in prose or example | `chr(126) notation` |
| `gars/01_prepare_samplesheets/CONTEXT.md` | 401 | literal character in prose or example | `chr(126) notation` |
| `gars/_system/integrity.py` | 14 | literal character in prose or example | `chr(126) notation` |
| `gars/_system/integrity.py` | 16 | literal character in prose or example | `chr(126) notation` |
| `gars/_system/stage01_samplesheet.py` | 271 | single-character null token | `chr(126) expression` |
| `gars/_system/stage01_samplesheet.py` | 974 | character embedded in CLI help | `concatenation with chr(126)` |
| `tests/run_tests.py` | 870 | literal R formula in config string | `runtime replacement with chr(126)` |
| `tests/run_tests.py` | 1773 | literal character in shell-expansion refusal fixture | `concatenation with chr(126)` |
| `tests/run_tests.py` | 1791 | literal character in scheduler refusal fixture | `concatenation with chr(126)` |
| `tests/run_tests.py` | 2536 | literal character in prose or example | `chr(126) notation` |
| `tests/test_planted_defects.py` | 90 | literal R formula in config string | `concatenation with chr(126)` |

### Execution and checks

Every command ran from the repository root with these inherited scratch settings:

```bash
export TMPDIR="$(pwd)-scratch" TEMP="$(pwd)-scratch" TMP="$(pwd)-scratch"
```

Search used `git grep -n -F` with its character argument built by `chr(126)`,
over the file list from `git diff --name-only dc6b803 HEAD`. The unavailable
`rg` command was replaced by Git/Python reads. Replacements used a short Python
read/replace/write command, never a patch containing removed literal characters.
Logs and the line-change inventory were written only under the scratch twin.
One full suite ran, with containers disabled; no second full suite ran concurrently.
All seven required commands exited zero. Execution used Python 3.13.5,
including the eval harness. Python 3.6 AST parsing accepted all four edited
Python files. A constant-folded AST comparison against the parent confirmed
identical executable expressions, excluding documentation strings.
`git diff --check` passed. Character search confirmed no literal U+007E in
hand-edited files. Staging names only the eight retry paths; the commit message
is read from a file in the scratch twin. No push, approval or merge occurs.

### Rule 5 summaries (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
Ran 485 tests in 79.320s
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

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.422s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
  published=3 graded=1
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 14 tests in 3.344s
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

### What was not verified in this retry

- NOT met: actual sealed measurement, external-human sealing and the row-8 exit;
  the sealed catalogue test skipped. No sealed fixture was accessed.
- NOT met: live DOI resolution and captured service-response provenance; the live
  citation test skipped. Replay remains the parent's labeled synthetic protocol
  fixture, and its existing ruling request remains open. No network test ran.
- NOT met: Docker database test classes for rows 5 and 7; these were skipped.
  Other environment skips remain as reported by the suite (79 total).
- NOT met: actual Python 3.6 execution, live pipelines or cluster acceptance.
- NOT rerun: the separate baseline-red and 24-fault drivers; round 1's recorded
  evidence is unchanged, with no new claim of reproducing those runs here.
- NOT met: independent review, protected-change approval, deployment path-scan
  acceptance and merge. Step B and all other residuals remain outside this retry.

Hours and metered cost: unknown; no new measurement is inferred.

## Step A round C1 (retry scope corrected)

Date: 2026-09-24. The first command, `git rev-parse HEAD`, recorded starting hash
`7edc946017a3195d2ce6d88bbca4c67923371c50`. The working tree was clean on
`build/gars-row-8-catalogue`. This round adds one commit on that parent.
The scope correction and DOI ruling were decided under the owner's standing delegation (23 Sep 2026).

The over-wide rewrite was caused by the wording of item 2, which the lane wrote,
not by the producer. Item 3 corrects that scope: 40 inherited lines return to
exact `e367a41` bytes, including readable prose, examples, docstrings and help.
Only `tests/test_planted_defects.py:90`, an added line in
`git diff dc6b803 e367a41`, keeps the retry's runtime `chr(126)` expression.
No detector rule, threshold, assertion or expected verdict changes.

### Every restored line

Line numbers are unchanged. U+007E names the character without typing it.
Restoration used a short Python command reading both versions through
`git show`; zero-context Git diff hunks identify round 1's added lines.
Each file is rebuilt from original bytes except those added lines, which keep
the retry's bytes. The report is append-only and preserves the earlier retry record.

| File | Line at e367a41 | Retry form | Restored form |
|---|---|---|---|
| `DEVELOPMENT.md` | 194 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 213 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 251 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 255 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 259 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 269 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 275 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 292 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 300 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 305 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 324 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 342 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 344 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 356 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 360 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 370 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 376 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 402 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 403 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 405 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 406 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 415 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 416 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 417 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 418 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 425 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 460 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 462 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `DEVELOPMENT.md` | 469 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/00_initialize_project/CONTEXT.md` | 111 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/01_prepare_samplesheets/CONTEXT.md` | 168 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/01_prepare_samplesheets/CONTEXT.md` | 401 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/_system/integrity.py` | 14 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/_system/integrity.py` | 16 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/_system/stage01_samplesheet.py` | 271 | runtime expression using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `gars/_system/stage01_samplesheet.py` | 974 | runtime expression using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `tests/run_tests.py` | 870 | runtime expression using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `tests/run_tests.py` | 1773 | runtime expression using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `tests/run_tests.py` | 1791 | runtime expression using `chr(126)` | exact e367a41 bytes (literal U+007E) |
| `tests/run_tests.py` | 2536 | character notation in prose or example using `chr(126)` | exact e367a41 bytes (literal U+007E) |

### DOI ruling resolved

The replay records remain labelled **synthetic protocol fixtures**, proving
protocol logic only. The only fixture edit makes that exact label explicit in
`gars/tests/fixtures/citations/responses.json:2`; request URLs, statuses, bodies
and body SHA-256 values are unchanged. Replay stays in-process through
`transport=`; no production flag, environment variable or file enables it.
Decision 0101 records the ruling in a dated addendum after its previous last byte.
Its frontmatter and index entry do not change; index regeneration is unnecessary.

Live DOI capture in this step is **NOT met**: this host's sandbox has no network.
The live evidence of record will be a later networked
`GARS_NETWORK_TESTS=1 python3 gars/tests/test_citation_resolution.py` run outside
this step, for the same five real DOIs (one DataCite) and five fabricated DOIs,
recording request URL, status and body SHA-256 per DOI in a record that is not
this producer's work. Class 9's replay P(caught) is never a live measurement.
The historical ruling request and retry statement that it remained open are
superseded by this resolution; their original bytes remain preserved.

### Execution and verification

Every command runs from the repository root with `TMPDIR`, `TEMP` and `TMP`
set to the scratch twin using the following prefix:

```bash
export TMPDIR="${PWD}-scratch" TEMP="${PWD}-scratch" TMP="${PWD}-scratch"
```

Reads use Git and Python; `rg` is unavailable (the initial attempt exited 127).
All file restoration uses Git blobs read by Python, with no patch containing
removed characters. Logs and the restoration inventory are confined to the
scratch twin. Tests inherit those scratch settings. No sealed fixture is
created, searched for or inspected; no network test is enabled.

All seven Rule 5 commands exited zero. One full suite ran at a time; no
Rule 5 failure required any additional change. Execution used **Python 3.13.5**,
including `evals/test_harness.py` (Python >=3.9).

### Rule 5 summaries (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
collected 237 tests from tests
collected 248 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
Ran 485 tests in 79.515s
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

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.374s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
  published=3 graded=1
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 14 tests in 3.257s
OK (skipped=1)
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 gars/tests/test_citation_resolution.py`:

```text
Ran 5 tests in 0.006s
OK (skipped=1)
```

### Scope and byte checks

- Inherited restoration: six files byte-identical to `e367a41`.
- Round-1 runtime formula: `tests/test_planted_defects.py:90` retains `7edc946` bytes.
- Scope audit: every changed original line outside this report was added by round 1.
  Against `e367a41`, only that formula line, the fixture's provenance label,
  the appended 0101 addendum and this appended report differ.
- Decision and change report: all bytes preceding these appendices preserved.
- DOI fixture: only the provenance label changes; every response record is unchanged.
- `git diff --check`: clean.
- Python 3.6 AST parsing: four Python files accepted; actual Python 3.6 execution NOT met.
- Row-7 renderer, SQL and report template: unchanged from `dc6b803`.

The scope audit derives added-line membership from
`git diff --unified=0 dc6b803 e367a41` and checks every changed original line
in `git diff --unified=0 e367a41` against that set. It excludes only this
append-only change report. Byte checks read historical content with `git show`.
The character search uses `git grep -n -F`, with the character argument built
at runtime by `chr(126)`, over files from `git diff --name-only dc6b803 HEAD`.
It finds 41 inherited matches (40 restored lines plus the generated index);
none is a newly typed literal. No patch was used for the restoration.

Protected files restored in this round (one per line):

- `gars/00_initialize_project/CONTEXT.md`
- `gars/01_prepare_samplesheets/CONTEXT.md`
- `gars/_system/integrity.py`
- `gars/_system/stage01_samplesheet.py`

Test expectation changes in this round: none. The earlier R-042 fixture change
and every assertion remain as recorded in round 1. The fixture provenance edit
changes no input or verdict. Staging names only the nine changed paths with
`git add --`; the commit message is read from a file in the scratch twin.
No push, remote addition, self-approval or merge is performed.

### What was not verified in this round

- **NOT met:** live DOI capture and live resolution. The opt-in live test skipped;
  synthetic protocol fixtures prove only protocol logic, and class 9's replay
  catch rate is not a live measurement. The later networked record is separate work.
- **NOT met:** sealed measurement, external-human sealing and row-8 exit. The sealed
  catalogue test skipped; no sealed fixture was created, searched for or inspected.
- **NOT met:** Docker database test classes for rows 5 and 7; skipped. The full
  suite reports 79 environment skips in total.
- **NOT met:** actual Python 3.6 execution, live pipelines and cluster acceptance.
- **NOT rerun:** baseline-red and the separate 24-fault driver; their historical
  results remain unchanged and are not claimed as reproduced in this round.
- **NOT met:** independent review, delegated protected-change approval, deployment
  path-scan acceptance and merge. Step B and all other residuals remain outside scope.

Hours and metered cost: unknown; no new measurement is inferred.

## Owner rulings needed

None.

## Review round C2 fixes

Date: 2026-09-24. Starting commit: `b98f2982bf087cb66ffbe7d42d0538cdff152672`.
This round adds one commit on `build/gars-row-8-catalogue` in response to
`docs/reviews/row_8_review_C1.md`, SHA-256
`fa33698e1366d70381345219ca3a2fc0fe28519b57ea31ef99e7159a939a916f`.
The review remains untracked and byte-identical. The earlier retry-scope
restoration is already present at the starting commit; no restoration is repeated.
The brief's rulings were decided under the owner's standing delegation (23 Sep 2026).
The response-capture ruling stays resolved; F1 is a different, newly identified
sealed-transport decision. The implementation does not choose an option for it.

| Finding → requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| F1 BLOCKER → R-114 | This report; appended 0101 addendum only | Scratch development snapshot with an unrecorded DOI, through emission | Reproduced citation_unverifiable, output absent, class-9 catch false; stopped for ruling; red-on-fault: no repair claimed |
| F2 MAJOR → R-125 | `gars/_system/resolve_citation.py`, `gars/_system/claims/evidence_check.py`, `gars/tests/test_emit_report.py` | EmitReportTests.test_doi_reference_forms | Green for all five evasion forms and three malformed markers; absent/existing output preserved; red-on-fault: yes, start-only extraction and ignored markers both go red |
| F3 MAJOR → R-042 | `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`, its sub-stage contract, `tests/test_planted_defects.py` | DevelopmentCatalogueTests.test_collect_diagnostic_drift | Real collect and check-table refuse present padj without pvalue; red-on-fault: yes, removing the new refusal goes red |
| F4 MAJOR → R-114 | `gars/_system/claims/evidence_check.py`, `gars/tests/test_emit_report.py` | EmitReportTests.test_malformed_evidence | Null/empty/ambiguous parents, missing fields and inconsistent IDs refuse evidence_missing; red-on-fault: yes, accepting malformed parents goes red |
| F5 MAJOR → R-042 | `gars/_system/stage01_samplesheet.py`, stage-01 contract, `tests/test_planted_defects.py` | DevelopmentCatalogueTests.test_covariate_schema_refusals | Nonnumeric age refuses invalid_design in the single JSON response, with no writes; red-on-fault: yes, removing age refusal goes red |
| F6 MINOR → R-141 | Same stage-01 files | DevelopmentCatalogueTests.test_covariate_schema_refusals | Invalid sex, negative/nonfinite age refuse for both bulk assays; red-on-fault: yes, removing sex or age refusal goes red |
| F7 MAJOR → R-114 | `tests/test_planted_defects.py` | DevelopmentCatalogueTests.test_class_specific_details; test_sealed_grading_uses_class_details | Duplicate-ID invalid_design and batch-only confounding earn no class-2/3 credit; positive controls still count; red-on-fault: yes, each omitted detail gate goes red |
| F8 MINOR → R-114 | `tests/test_planted_defects.py` | SealedOutputDisciplineTests; test_sealed_grading_uses_class_details | Graded derives from terminal verdicts; errors retain a class when parseable; graded equals seen asserted; red-on-fault: yes, dropping a verdict or skipping an error goes red |
| F9 NOTE → documentation | This report's expectation table; README count only | `python3 tests/check_counts.py` | The earlier sentence rewrite is explicitly recorded below, choosing the review's documentation option; red-on-fault: no, documentation-only |
| F10 NOTE → provenance | New commit metadata; this report | `git log -1 --format='%an <%ae> / %cn <%ce>'` | This round uses neutral GARS Producer author/committer metadata; historical commits are not rewritten; red-on-fault: no, metadata-only |

All detector thresholds are unchanged. No config key, schema column or new failure
code is introduced. The strict sex/age refusals enforce the schema already specified
in the brief, using the existing invalid_design code; no new scientific choice is
made. The new R-042 behavior and its red/green witnesses are appended to 0101.
The ten committed clean projects, fixture hashes and existing ledger rows are unchanged.

F8's development-loop allegation does not match the starting code: its increment
already follows grade/clean. Reading
`git show b98f298:tests/test_planted_defects.py` produced, in order:

```text
caught += int(grade(self.root / ('d%02d' % cid), cid, FLAGS[cid][0]))
graded += 1
false_flags += int(not clean(self.root / ('c%02d' % i), all_stages=True))
graded += 1
self.assertEqual(graded, seen)
```

That loop retains its existing verdict-based accounting. The sealed loop was
incorrect; it now records content-free class/outcome pairs at terminal branches,
and derives graded from those records. A parse error has unknown class and still
counts as an error verdict. Unknown and unmapped cases cannot earn catch credit.
No new sealed data was created or inspected: the added accounting regression uses
producer development projects and in-memory declarations. Existing synthetic
sentinel controls remain the required interface tests, never real seals.

### Protected files touched in C2

- `gars/_system/resolve_citation.py`
- `gars/_system/claims/evidence_check.py`
- `gars/_system/stage01_samplesheet.py`
- `gars/_system/wrappers/rnaseq-de/rnaseq_de.py`
- `gars/01_prepare_samplesheets/CONTEXT.md`
- `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`

### Expectation and documentation changes

| File / location | Earlier shape | C2 disposition | Reason |
|---|---|---|---|
| `README.md:314` at round 1 | Historical 456-test row-7 sentence, including 11 skips, macOS, 2026-09-23 and Docker/scratch conditions | The prior replacement with a current collection count and change-report pointer is recorded explicitly; only 485 to 490 changes this round | F9's allowed documentation option; assigning historical platform/run conditions to an expanded current suite would imply evidence not measured |
| `README.md` and two current counts in `DEVELOPMENT.md` | 485 collected tests | 490 collected tests | Five new test methods; unittest discovery confirms 240 plus 250 |
| Existing test expectations | All prior verdicts and thresholds | No changes | Added adverse tables, metadata and references; existing assertions retained and strengthened |

### Commands and execution conditions

All commands ran from the repository root. Each set the following environment
before reading, editing or testing; no command changed directory:

```bash
export TMPDIR="${PWD}-scratch" TEMP="${PWD}-scratch" TMP="${PWD}-scratch"
```

Python was **3.13.5**, including the eval harness (at least 3.9).
Reads used Git, Python, cat and sed; the previous round established that rg is
unavailable. Edits used short Python read/replace/write commands and append-only
record writes. All scratch scripts, logs, temporary projects, fault copies and
the commit-message file stayed in the scratch twin. Production code still has no
replay switch; no network mode was enabled. Only one full suite ran at a time.
Staging uses named paths and the message is read from the scratch file with `-F`.
Neutral author/committer metadata is supplied for this commit; no remote, push,
self-approval or merge is performed.

Before production edits, the new regressions ran against the starting code:

- `python3 tests/test_planted_defects.py DevelopmentCatalogueTests.test_covariate_schema_refusals DevelopmentCatalogueTests.test_class_specific_details DevelopmentCatalogueTests.test_collect_diagnostic_drift SealedOutputDisciplineTests`: `Ran 6 tests in 0.950s`; `FAILED (failures=22, errors=8)`.
- `python3 gars/tests/test_emit_report.py EmitReportTests.test_doi_reference_forms EmitReportTests.test_malformed_evidence`: `Ran 2 tests in 0.432s`; `FAILED (failures=17)`.

Those reds include the reported bypasses and the missing verdict records; their
later green results are below. The fault driver's first invocation found a string
quoting SyntaxError in a newly added mutation. That driver was repaired before
any fault result was recorded; its final run executed all 33 mutations. An early
count check found the second DEVELOPMENT count still at 485; that count was
corrected to 490 and the final count check is clean. No test or guard was weakened.

`bash docs/decisions/build_index.sh` regenerated the index with no byte change,
because 0101's frontmatter is unchanged. `git diff --check` is clean; all changed
Python files parse with `ast.parse(feature_version=(3, 6))`. Existing decision and
report bytes are prefixes of their updated files. No added line contains U+007E;
character checks build the character with chr(126). Row-7 invariance was checked
with the following command, whose output is empty:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

### Rule 5 summaries and development EXIT lines (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
collected 240 tests from tests
collected 250 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
Ran 490 tests in 80.522s
OK (skipped=79)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 240 tests from tests
collected 250 tests from gars/tests
suite: 490 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.557s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 17 tests in 4.375s
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

`python3 gars/tests/test_emit_report.py`:

```text
Ran 10 tests in 0.095s
OK
```

`python3 gars/tests/test_integrity_records.py`:

```text
Ran 2 tests in 0.062s
OK
```

### Parent and disposable-fault verification

`python3 benchmarks/defects/baseline_check.py` ran against archived dc6b803:

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

`python3 benchmarks/defects/red_on_fault.py` used disposable copies and byte
backups, restoring every modified file without a checkout restore. Every one
of the original 24 faults was rerun, plus nine C2 faults:

```text
RED: sex confounding removed
RED: imbalance threshold 0.9
RED: cell pseudoreplication removed
RED: subject count removed
RED: index comparison inverted
RED: not_checkable counted pass
RED: evidence hash not compared
RED: absolute evidence accepted
RED: padj below pvalue allowed
RED: BH recompute removed
RED: Crossref 404 alone unresolved
RED: network error resolved
RED: unparseable plant skipped
RED: unmapped folded into class
RED: Hi-C denominator removed
RED: truncated plain FASTQ passes
RED: gzip-valid record truncation passes
RED: report written before preflight
RED: sealed stdout leaked
RED: invalid_design mapped without family
RED: BH tolerance 1e-6
RED: environment replay switch
RED: suppressed replay option
RED: DOI tokens restricted to whole reference
RED: malformed DOI marker ignored
RED: malformed evidence accepted
RED: padj without pvalue allowed
RED: invalid sex treated unknown
RED: invalid age allowed
RED: class 2 detail ignored
RED: class 3 detail ignored
RED: graded verdict dropped
RED: renderer receives from-db
red-on-fault: 33/33
```

F1 was reproduced with a scratch development snapshot whose DOI is outside the
committed replay set, imported through the existing emission helper:

```text
F1 reproduction: citation_unverifiable; report absent; class-9 catch false
```

The DOI protocol fixtures remain labelled **synthetic protocol fixtures**.
These results demonstrate protocol logic, never live DOI resolution or sealed
class-9 P(caught). Hours and metered cost: unknown, not zero.

## Owner rulings needed

1. **F1 — sealed class-9 transport (R-114), stopped.** The fixed development
   replay has no response for a sealer-authored DOI outside its ten identifiers.
   Emission correctly refuses citation_unverifiable, but the sealed class-9
   contract requires citation_unresolved for a catch. Hi-C also remains not
   caught, so such a set is capped at 8/10. Choose the review's alternatives:
   **A:** layout (c) carries the plant's own recorded responses, including request
   URL, status and body SHA-256, replayed in-process by the runner;
   **B:** sealed class-9 runs use live transport on a networked host.
   Both need a specified sealed run contract and a regression using a DOI outside
   the committed development fixtures. Neither is selected or implemented here.
   The delegated synthetic-fixture provenance ruling does not choose this transport.

## Residual gaps after C2

- **NOT met:** F1 sealed class-9 transport and sealed >= 9/10 over all ten classes;
  external_human_seal and public catch-rate evidence. Actual sealed tests skipped.
- **NOT met:** live DOI capture or live resolution; the network test skipped.
  Class-9 replay catch rate remains development protocol evidence only.
- **NOT met:** Docker database classes of rows 5 and 7 (Row05DatabaseTests and
  ClaimConstraintTests), skipped on this host. The full suite has 79 total skips.
- **NOT met:** actual Python 3.6 execution, live pipelines or cluster acceptance.
- **NOT met:** PMID/E-utilities, literature-role wiring of R-125, R-069 artifact
  liveness beyond claim evidence, and report emission wiring into stage 03 or
  pilot flow. Direct renderer calls remain unguarded by the new preflight.
- **NOT met:** class-10 detector, pilot-1 measurement, step B's data route and
  backend bench, scientific model calibration, real-DOI relevance, swap checks
  without library_index, and containment of system/catalogue editors.
- **NOT met:** fresh review acceptance, separate protected-change approval,
  deployment path-scan acceptance and merge; 0102, 0103 and 0104 remain untouched.

F2–F8 closed by code and regressions; F9 answered by the expectation table;
F10 addressed prospectively by neutral commit metadata; F1 waits on the owner.

## Step A round D1 (sealed class-9 transport and commit identity)

Starting commit: `a8b54e53b62123f49c7674c54083fe49d4a78568`.
This round implements only added delegated rulings 5 and 6 and review C1 F1,
plus the count correction required by a failing Rule 5 count check.
The transport and identity rulings were decided under the owner's standing delegation (23 Sep 2026).

Sealed class 9 now selects the production live lookup with `transport=None` in
`sealed_measure`, through `grade`, `emission` and the actual `emit_report.main`
entry point. Measurement requires a networked host. Development plants retain
in-process replay, and default tests use replay or in-process stubs without
opening the network. No CLI option, environment variable or file selects a
transport. Class 9 is never scored as a sealed measurement from replay.
The committed DOI responses remain **synthetic protocol fixtures**, proving
protocol logic only.

`benchmarks/defects/SEALED-INTERFACE.md` preserves every inherited byte and
appends the dated transport sentence. The schema equality test compares the
original interface block before that dated addendum; its contract assertions
are retained. No protected file is touched in this round.

| Requirement | Changed files | Acceptance | Result |
|---|---|---|---|
| R-114, R-125; delegated ruling 5; C1 F1 | `tests/test_planted_defects.py`, `benchmarks/defects/SEALED-INTERFACE.md` | `SealedOutputDisciplineTests.test_sealed_class9_uses_live_transport` drives a producer-authored layout (c) control through sealed grading and actual emission, with an unrecorded DOI and a stub answering not-found at both services | Red on inherited transport, green with live selection; requests reach both services through the stub, `transport=None` reaches emission, citation_unresolved is caught, and development still uses replay |
| Delegated ruling 6 | Commit metadata; this report | Repository-configured author and committer, no overrides | The configured identity is used exactly; no personal identity is copied into this report |

Commit `a8b54e5` used another identity; it is not rewritten and stays as it is
(append-only). This round uses this repository's own configured identity, as
printed by `git config user.name` and `git config user.email`, without setting
or overriding either author or committer. No approval, merge, push or remote
operation is performed.

### D1 checks and expectation changes

Every command ran from the repository root, with TMPDIR, TEMP and TMP set to
the scratch twin. Python: `Python 3.13.5`. Full-suite execution used
`GARS_TEST_NO_CONTAINER=1`; only one full suite ran at a time. Logs were written
in the scratch twin. No live DOI command or actual sealed fixture was used.
Source and index reads used repository-relative paths; ripgrep was unavailable,
so Python text reads were used. Edits used Python with exact replacements and
append-only writes; the report and interface preserve inherited byte prefixes.

The targeted command was
`python3 tests/test_planted_defects.py SealedOutputDisciplineTests.test_sealed_class9_uses_live_transport`.
Before the transport fix it printed `Ran 1 test in 0.002s` and
`FAILED (failures=1)` because class 9 had counts `[0, 1]` instead of `[1, 1]`.
After the fix it printed `Ran 1 test in 0.005s` and `OK`.
This is the observed red-on-fault for retaining the inherited replay transport.
The rest of the inherited mutation campaign was not rerun in this narrow round.

`python3 tests/check_counts.py` initially reported `suite: 491 tests, from unittest's loader`
and `3 problem(s):`; all three were inherited claims of 490 after adding the
required regression. Only those three numbers were changed, then the check passed.

| File and line | Old expectation | New expectation | Reason |
|---|---|---|---|
| `README.md:314` | 490 tests | 491 tests | Added transport regression; count check failure |
| `DEVELOPMENT.md:119` | 490 tests | 491 tests | Same count check failure |
| `DEVELOPMENT.md:138` | 490 tests | 491 tests | Same count check failure |
| `tests/test_planted_defects.py`, `test_schema_contracts_match` | Entire interface document equals the inherited block | Original block before the required dated sentence equals the inherited block | Ruling 5 explicitly appends a sentence; all original contract/schema comparisons remain |

Rule 5 summary lines, copied from the captured logs:

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 491 tests in 80.524s
OK (skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 491 tests, from unittest's loader
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.521s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.362s
OK (skipped=1)
```

`python3 gars/tests/test_citation_resolution.py`

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

Development EXIT lines only:

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

Additional checks: the changed Python module parses with
`ast.parse(..., feature_version=(3, 6))`; this is syntax validation, not an
actual Python 3.6 run. The sealed interface's inherited bytes remain its exact
prefix. Added lines contain no literal home marker. Git diff scope and whitespace
are checked before path-limited staging; the commit message comes from a file in
the scratch twin. The supplied untracked review is left uncommitted.

Hours and metered cost: unknown, not zero.

### D1 residuals

- **NOT met:** actual sealed measurement, sealed >= 9/10 and external_human_seal;
  the real sealed test skipped. The synthetic layout regression is not a seal.
- **NOT met:** live DOI resolution/capture or live class-9 P(caught); the live
  citation test skipped. Networked measurement remains separate work.
- **NOT met:** database verification for rows 5 and 7 on this host;
  Row05DatabaseTests (17 tests) and ClaimConstraintTests (18 tests) skipped,
  among the full suite's 79 environment skips.
- **NOT met:** actual Python 3.6 execution, protected-change approval, fresh review,
  deployment path-scan acceptance, merge and the pre-existing row-8 residuals.
  No row exit is claimed; this round only resolves F1's transport selection.

## Owner rulings needed

None.


## Review round D2 fixes

Date: 2026-09-24. Starting commit: `86d9b47d92aa6323f76faaa8bceba3485e50577f`.
One new commit on `build/gars-row-8-catalogue` answers
`docs/reviews/row_8_review_D1.md`, SHA-256
`c40559446a525f8f3e8d61496d5ff4fbbe77bf43c394ba898ee22c908c50679d`.
The supplied review remains untracked and unchanged. Earlier scope corrections
are already present; no historical restoration or commit rewrite is repeated.
The brief's rulings were decided under the owner's standing delegation (23 Sep 2026).

| Finding → requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 MINOR → R-114 | `docs/decisions/0101-row-8-defect-catalogue-and-detectors.md` | Byte-prefix and exact dated interface-sentence comparison | Closed; D1 transport ruling appended, C2 stop superseded; red-on-fault: no, documentation only |
| F2 MINOR → R-125, R-042 | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | EmitReportTests.test_doi_reference_forms through actual emission | Closed; subdivided fabricated DOI refused at both lookups, parenthesised real DOI accepted, balanced suffixes preserved, Doi author needs no lookup; red-on-fault: yes, each of the three corrections independently reversed in disposable copies |
| F3 MINOR → R-114, R-042 | `gars/_system/claims/evidence_check.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | EmitReportTests.test_malformed_evidence | Closed; extra/missing keys in entries and both parent kinds refuse evidence_missing and preserve absent/existing output; red-on-fault: yes, independently remove entry-key and parent-key checks |
| F4 MINOR → R-114, R-042 | `tests/test_planted_defects.py`, `benchmarks/defects/red_on_fault.py` | SealedOutputDisciplineTests.test_sentinel_and_error_accounting | Closed; real stage CLI crashes on producer-authored non-UTF-8 samples.csv, error stays graded and counts as flagged, sentinel appears zero times; red-on-fault: yes, excluding error from flagged count fails the regression |
| F5 NOTE → R-125 | This report; appended 0101 residual | Existing test_sealed_class9_uses_live_transport | Answered; stub proves transport selection only, never network behavior; red-on-fault: no new change required, networked sealed measurement stays NOT met |

All code changes implement the review's required fixes. No acceptance threshold,
config key, closed failure vocabulary, catalogue entry, committed development
fixture or ledger row changes. Tests extend existing methods, so the collection
count remains 491 and README/DEVELOPMENT need no count edits.
Decision 0101 receives dated addenda only. The index was regenerated with
`bash docs/decisions/build_index.sh` and remains byte-identical.

### Protected files touched in D2

- `gars/_system/resolve_citation.py`
- `gars/_system/claims/evidence_check.py`

### Expectation changes

| Test / location | Old shape | New shape | Reason |
|---|---|---|---|
| EmitReportTests.test_doi_reference_forms | `DOI missing` refused as an unparseable marker | `DOI: missing` retains the malformed-marker refusal; `DOI missing` explicitly emits with no lookup | F2 requires markers only as doi: or doi.org; a bare word is not a DOI marker |
| SealedOutputDisciplineTests.test_sentinel_and_error_accounting | Two synthetic controls, both errors | Three synthetic controls, all errors, including class 0; flagged/clean is 1/1 | F4 adds a crashing clean control; all previous verdict, denominator and sentinel assertions remain |

### Execution and red/green evidence

Every shell command ran from the repository root without changing directory,
with TMPDIR, TEMP and TMP set to the scratch twin before execution:

```bash
export TMPDIR="$(pwd)-scratch" TEMP="$(pwd)-scratch" TMP="$(pwd)-scratch"
```

Python: `Python 3.13.5`, including the eval harness (at least 3.9). Logs, byte
backups, temporary projects, disposable fault copies and the commit-message
file remain in the scratch twin. No network test was enabled and no real sealed
plant was created, searched for or inspected. The layout controls are synthetic
producer-authored regression inputs, not seals. One full suite ran at a time.
Reads used Git, Python, cat and sed after confirming rg was unavailable. Edits
used patches without literal home markers, and Python append-only record writes.

Before production repairs, the expanded tests ran against the D1 code:

`python3 gars/tests/test_emit_report.py EmitReportTests.test_doi_reference_forms`

```text
Ran 1 test in 0.033s
FAILED (failures=1)
```

`python3 gars/tests/test_emit_report.py EmitReportTests.test_malformed_evidence`

```text
Ran 1 test in 0.363s
FAILED (failures=14)
```

`python3 tests/test_planted_defects.py SealedOutputDisciplineTests.test_sentinel_and_error_accounting`

```text
Ran 1 test in 0.031s
FAILED (failures=1)
```

All three are green with the repairs. The initial focused green runs printed
`Ran 10 tests in 0.364s` / `OK` for `python3 gars/tests/test_emit_report.py`, and
`Ran 1 test in 0.031s` / `OK` for the same sentinel command above.

`python3 benchmarks/defects/red_on_fault.py` reran the inherited 33 faults plus
six D2 faults in disposable copies, restoring byte backups after every fault.
The inherited malformed-parent mutation now names its condition as well as its
body so its target stays unique after adding a second refusal branch; its
semantic fault and acceptance are unchanged. Every named fault went red:

```text
RED: sex confounding removed
RED: imbalance threshold 0.9
RED: cell pseudoreplication removed
RED: subject count removed
RED: index comparison inverted
RED: not_checkable counted pass
RED: evidence hash not compared
RED: absolute evidence accepted
RED: padj below pvalue allowed
RED: BH recompute removed
RED: Crossref 404 alone unresolved
RED: network error resolved
RED: unparseable plant skipped
RED: unmapped folded into class
RED: Hi-C denominator removed
RED: truncated plain FASTQ passes
RED: gzip-valid record truncation passes
RED: report written before preflight
RED: sealed stdout leaked
RED: invalid_design mapped without family
RED: BH tolerance 1e-6
RED: environment replay switch
RED: suppressed replay option
RED: DOI tokens restricted to whole reference
RED: malformed DOI marker ignored
RED: malformed evidence accepted
RED: subdivided DOI prefix ignored
RED: unmatched DOI closing bracket retained
RED: author Doi treated as DOI marker
RED: extra evidence keys accepted
RED: extra evidence parent keys accepted
RED: erroring clean plant counted clean
RED: padj without pvalue allowed
RED: invalid sex treated unknown
RED: invalid age allowed
RED: class 2 detail ignored
RED: class 3 detail ignored
RED: graded verdict dropped
RED: renderer receives from-db
red-on-fault: 39/39
```

`python3 benchmarks/defects/baseline_check.py` repeated the original BASE
import and behavioral checks with the runner/catalogue copied into scratch:

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

### Required and additional command summaries (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 491 tests in 80.808s
OK (skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 491 tests, from unittest's loader
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.495s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.412s
OK (skipped=1)
```

`python3 gars/tests/test_citation_resolution.py`

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

`python3 gars/tests/test_emit_report.py`

```text
Ran 10 tests in 0.359s
OK
```

`python3 gars/tests/test_integrity_records.py`

```text
Ran 2 tests in 0.066s
OK
```

Development EXIT lines only:

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

The class-9 development result uses **synthetic protocol fixtures**, proving
protocol logic only. It is never reported as a live or sealed measurement.

### Scope, provenance and verification limits

`git diff --check` is clean. Changed Python files parse with
`ast.parse(feature_version=(3, 6))`; that does not prove actual Python 3.6 execution.
The original decision/report bytes remain exact prefixes. The copied D1
transport sentence matches the sealed interface exactly. Added-line checks use
`chr(126)` and find no literal home marker. The row-7 invariant command remains
empty:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

The full suite's 79 skips include Row05DatabaseTests (17) and
ClaimConstraintTests (18); database behavior for rows 5 and 7 is not verified
on this host. Actual sealed and live citation tests each skip explicitly.

Commit `a8b54e5` used another identity; it is not rewritten and stays as it is
(append-only). This round uses this repository's configured identity exactly
as `git config user.name` and `git config user.email` print it, without author
or committer overrides. Staging names only the seven changed paths; the commit
message is read from a scratch-twin file. No push, remote, approval or merge.

Hours and metered dollars: unknown, not zero.

## Owner rulings needed

None.

## D2 residual gaps

- **NOT met:** actual sealed catalogue and clean measurements, sealed >=9/10,
  external_human_seal and public credibility; no row-8 exit is claimed.
- **NOT met:** live DOI capture/resolution and the live sealed class-9 path.
  Ruling 5's later networked measurement supplies that evidence; stubs do not.
- **NOT met:** database verification for rows 5 and 7 on this host, live
  pipelines/HPC, actual Python 3.6 execution and the other environment skips.
- **NOT met:** PMID/E-utilities, literature-role typed-tool wiring, R-069 liveness
  beyond claim evidence, a class-10 detector, stage-03/pilot emission wiring,
  pilot-1 measurement and step B's data route/backend work.
- **NOT met:** containment of system/catalogue edits, scientific DE-model
  validity, DOI relevance, swaps without library_index, fresh independent
  review of D2, protected-change approval, deployment path-scan acceptance
  and merge. Direct renderer invocation remains unguarded.

D1 F1–F4 closed; F5 answered as a measurement limit; no finding waits on a ruling.


## Review round D3 fixes

Date: 2026-09-24. Starting commit: `ad70a1c993ad952197ee7be93dbdfdbb14fc9c0f`.
One new commit on `build/gars-row-8-catalogue` answers
`docs/reviews/row_8_review_D2.md`, SHA-256
`61e68b560ebc1c302863ae2a61c7072d60f0cc81c0afc1f3e7f5025da9de14a8`. The supplied review stays untracked and unchanged.
The brief's rulings were decided under the owner's standing delegation (23 Sep 2026).
The earlier retry-scope correction and sealed transport ruling are already
present; no restoration or historical commit rewrite is repeated.

| Finding → requirement | Changed files | Test | Result (red-on-fault seen: yes/no, how) |
|---|---|---|---|
| F1 MINOR → R-125, R-042 | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | EmitReportTests.test_doi_reference_forms | Closed; case-insensitive DOI followed by whitespace and 10. or 10/ marks an unverifiable citation when extraction fails; author-named-Doi control still emits. Red-on-fault: yes, removing the short-form marker fails the test in a disposable copy |
| F2 MINOR → R-114, R-042 | `gars/_system/claims/evidence_check.py`, `gars/tests/test_emit_report.py`, `benchmarks/defects/red_on_fault.py` | EmitReportTests.test_malformed_evidence; test_clean_bytes_and_snapshot_shape | Closed; integer ID and the BASE kind/relation vocabularies enforced for both parents; every permitted kind/relation combination emits. Red-on-fault: yes, independently disabling each of the three value checks fails the test in disposable copies |

Decision 0101 receives only a dated append-only addendum naming the changed
behavior and R-042 acceptance. The index was regenerated and remains unchanged.
No threshold, catalogue entry, committed fixture, ledger row, config key or
failure code changes. No test method is added; the suite remains 491 tests,
so README and DEVELOPMENT counts remain unchanged.

### Protected files touched in D3

- `gars/_system/resolve_citation.py`
- `gars/_system/claims/evidence_check.py`

### Expectation changes

| Existing test expectation | Change | Reason |
|---|---|---|
| All earlier inputs and assertions | None | Only adverse inputs and positive vocabulary controls added; no assertion, threshold or guard weakened |

Both new refusals run through actual report emission. Every adverse input is
checked with output absent and with a pre-existing output that must remain
byte-identical. ID negatives include strings, booleans, floating-point values,
null, arrays and objects. Kind and relation negatives include arbitrary path
text and wrong case. The permitted vocabularies come directly from the existing
claims.sql schema, not a new schema decision. Short-form DOI markers refuse
citation_unverifiable; this does not claim short-DOI registration resolution.

### Execution conditions and parent red

Every shell command ran from the repository root, without changing directory,
with these settings before execution:

```bash
export TMPDIR="$(pwd)-scratch" TEMP="$(pwd)-scratch" TMP="$(pwd)-scratch"
```

Logs, temporary projects, disposable fault copies, this report's append script
and the commit-message file stay in the scratch twin. Reads used Git, Python,
cat, sed and grep after confirming rg is unavailable. Edits used Python exact
replacements and append-only writes. One full suite ran at a time. No network
mode was enabled and no real sealed plant was created, searched for or read.
Python was **3.13.5**, including the eval harness (at least 3.9).

The expanded tests were run before changing production code, against D2:

`python3 gars/tests/test_emit_report.py EmitReportTests.test_doi_reference_forms`

```text
Ran 1 test in 0.378s
FAILED (failures=5)
```

`python3 gars/tests/test_emit_report.py EmitReportTests.test_malformed_evidence`

```text
Ran 1 test in 1.198s
FAILED (failures=48)
```

The same tests pass with the repairs. The full emission module result is below.
The 43-fault campaign restores byte backups after each disposable mutation.
The inherited author-Doi mutation is re-anchored to the expanded regex; its
semantic fault is unchanged. Every inherited and added fault went red:

`python3 benchmarks/defects/red_on_fault.py`

```text
RED: sex confounding removed
RED: imbalance threshold 0.9
RED: cell pseudoreplication removed
RED: subject count removed
RED: index comparison inverted
RED: not_checkable counted pass
RED: evidence hash not compared
RED: absolute evidence accepted
RED: padj below pvalue allowed
RED: BH recompute removed
RED: Crossref 404 alone unresolved
RED: network error resolved
RED: unparseable plant skipped
RED: unmapped folded into class
RED: Hi-C denominator removed
RED: truncated plain FASTQ passes
RED: gzip-valid record truncation passes
RED: report written before preflight
RED: sealed stdout leaked
RED: invalid_design mapped without family
RED: BH tolerance 1e-6
RED: environment replay switch
RED: suppressed replay option
RED: DOI tokens restricted to whole reference
RED: malformed DOI marker ignored
RED: malformed evidence accepted
RED: subdivided DOI prefix ignored
RED: unmatched DOI closing bracket retained
RED: author Doi treated as DOI marker
RED: short-form DOI marker ignored
RED: noninteger evidence id accepted
RED: arbitrary evidence kind accepted
RED: arbitrary evidence relation accepted
RED: extra evidence keys accepted
RED: extra evidence parent keys accepted
RED: erroring clean plant counted clean
RED: padj without pvalue allowed
RED: invalid sex treated unknown
RED: invalid age allowed
RED: class 2 detail ignored
RED: class 3 detail ignored
RED: graded verdict dropped
RED: renderer receives from-db
red-on-fault: 43/43
```

`python3 benchmarks/defects/baseline_check.py`

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

The BASE check retains the expected import red and behavioral 2/10 after copying
the runner and catalogue into scratch; classes 3–9 are not caught. The original
BASE evidence is not mistaken for the D2 parent regressions above.

### Required and additional command summaries (verbatim)

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 491 tests in 81.488s
OK (skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 491 tests, from unittest's loader
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.633s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.578s
OK (skipped=1)
```

`python3 gars/tests/test_citation_resolution.py`

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

`python3 gars/tests/test_emit_report.py`

```text
Ran 10 tests in 0.598s
OK
```

`python3 gars/tests/test_integrity_records.py`

```text
Ran 2 tests in 0.061s
OK
```

Development EXIT lines only:

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

Replay uses **synthetic protocol fixtures**, proving protocol logic only.
Class 9's replay catch rate is never a live or sealed measurement. Actual
sealed and live DOI tests explicitly skip as unmeasured.

### Scope and provenance checks

`git diff --check` is clean. All four changed Python files parse with
`ast.parse(feature_version=(3, 6))`; actual Python 3.6 execution is NOT met.
The decision and report preserve their starting bytes as exact prefixes.
The added-line check builds its character with chr(126) and finds no literal
home marker. No row-7 SQL, renderer or template change is present:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

The full suite skips Row05DatabaseTests (17 tests) and ClaimConstraintTests
(18 tests), among its 79 environment skips. Database behavior for rows 5 and 7
is not verified on this host.

Commit `a8b54e5` used another identity; it is not rewritten and stays as it is
(append-only). This round uses the repository's configured identity exactly
as `git config user.name` and `git config user.email` print it, without author
or committer overrides. Staging names only the six changed paths; the message
is read from a scratch-twin file. No push, remote, self-approval or merge.
Hours and metered dollars: unknown, not zero.

## Owner rulings needed

None.

## D3 residual gaps

- **NOT met:** actual sealed catalogue/clean measurements, sealed >=9/10,
  external_human_seal and public catch-rate evidence. No row-8 exit is claimed.
- **NOT met:** live DOI capture/resolution and live sealed class-9 measurement.
  The later networked run remains separate work; replay and stubs do not prove it.
- **NOT met:** database verification for rows 5 and 7, live pipelines/HPC,
  actual Python 3.6 execution and the other environment-dependent checks.
- **NOT met:** PMID/E-utilities, literature-role typed-tool wiring, R-069
  liveness beyond claim evidence, class 10, stage-03/pilot emission wiring,
  pilot-1 measurement and step B's data route/backend work.
- **NOT met:** containment of system/catalogue edits, scientific DE-model
  validity, real-DOI relevance and swaps without library_index. Direct renderer
  calls remain unguarded. Short-form DOI registration resolution is not added.
- **NOT met:** fresh independent review of D3, protected-change approval,
  deployment path-scan acceptance and merge.

D2 F1 and F2 closed; no finding waits on a ruling.


## Step A round E1 (general DOI marker rule)

Starting hash, recorded before reading or editing:
`75f0a900b41455aa7dc6aaf7e16fc86427134f27`.
This round implements only item 7 of the added delegated rulings: review D3 F1,
the third round of the same separator-bypass shape. It was decided under the
owner's standing delegation (23 Sep 2026). No approval or row exit is claimed.

The general predicate recognizes a case-insensitive DOI word and any numeric
`10.` or `10/` token anywhere in either order; a reference without a parseable
DOI refuses `citation_unverifiable`. Underscore and direct numeric adjacency
also delimit the marker, covering the required empty-separator combinations.
Existing explicit DOI/resolver markers still refuse when malformed. Parsed
DOIs keep the existing Crossref/handle lookup and network-failure semantics.

The emission regression covers the three reviewer forms and 392 generated
combinations (seven separators on either side of four enclosure choices, with
two malformed numeric DOI forms), plus distant and reversed tokens. Every
refusal preserves both absent and existing output. Existing author-named-Doi
controls still emit. Title/journal prose with Doi and page 10. emits with a
valid recorded DOI; without one it intentionally refuses as unverifiable under
the delegated general rule. The test states this expected outcome and reason.
The ten existing clean projects and their pinned bytes remain unchanged.

| Requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| DOI half of R-125; D3 F1 | `gars/_system/resolve_citation.py`, `gars/tests/test_emit_report.py` | `EmitReportTests.test_doi_reference_forms` through emission | Green; yes, expanded test on parent failed with 325 failures; removing the general predicate is red |
| R-042; preserve author controls | `benchmarks/defects/red_on_fault.py` | Existing ignored-short-marker and author-Doi faults | Green; yes, both faults red after re-anchoring their mutations to the general predicate |
| Decision and evidence provenance | `docs/decisions/0101-row-8-defect-catalogue-and-detectors.md`, `docs/implementation/row_8_change_report.md` | Prefix-byte assertions; required checks below | Original bytes preserved; dated addenda only |

Protected file touched, one per line:

- `gars/_system/resolve_citation.py`

### Expectation changes

| Existing test or fixture | Change | Reason |
|---|---|---|
| None | None | Existing assertions retained; cases added within the existing test method |

No test methods or count claims changed. The two mutation anchors retain their
original fault meanings; the campaign still contains 43 faults. The decision
index was regenerated with `bash docs/decisions/build_index.sh` and has no diff.

### Commands and results

Every command ran from the repository root. Each shell invocation first set
`TMPDIR`, `TEMP` and `TMP` to the scratch twin with `"$(pwd)-scratch"`.
No command changed directory. Logs, disposable projects and the commit-message
file are in that twin. Python exact replacements edited code; append-only
writes extended the decision and this report. Reads used Git, cat, sed, grep
and Python; the initial `rg` discovery returned `rg: command not found`, so
subsequent searches used grep. Git recorded HEAD, status, branch and configured
identity before implementation. Python version: **3.13.5**, including the eval
harness (at least 3.9). Only one full suite ran at a time. No network mode was
enabled; no real sealed plant was created, searched for or inspected.

The regression was run before changing production code:

`python3 gars/tests/test_emit_report.py EmitReportTests.test_doi_reference_forms`

```text
Ran 1 test in 8.334s
FAILED (failures=325)
```

The same expanded regression passes in the full emission module below.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 491 tests in 83.370s
OK (skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 491 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.691s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.444s
OK (skipped=1)
```

`python3 gars/tests/test_citation_resolution.py`

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

`python3 gars/tests/test_emit_report.py`

```text
Ran 10 tests in 0.986s
OK
```

Development EXIT lines only:

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 benchmarks/defects/red_on_fault.py`

```text
RED: sex confounding removed
RED: imbalance threshold 0.9
RED: cell pseudoreplication removed
RED: subject count removed
RED: index comparison inverted
RED: not_checkable counted pass
RED: evidence hash not compared
RED: absolute evidence accepted
RED: padj below pvalue allowed
RED: BH recompute removed
RED: Crossref 404 alone unresolved
RED: network error resolved
RED: unparseable plant skipped
RED: unmapped folded into class
RED: Hi-C denominator removed
RED: truncated plain FASTQ passes
RED: gzip-valid record truncation passes
RED: report written before preflight
RED: sealed stdout leaked
RED: invalid_design mapped without family
RED: BH tolerance 1e-6
RED: environment replay switch
RED: suppressed replay option
RED: DOI tokens restricted to whole reference
RED: malformed DOI marker ignored
RED: malformed evidence accepted
RED: subdivided DOI prefix ignored
RED: unmatched DOI closing bracket retained
RED: author Doi treated as DOI marker
RED: short-form DOI marker ignored
RED: noninteger evidence id accepted
RED: arbitrary evidence kind accepted
RED: arbitrary evidence relation accepted
RED: extra evidence keys accepted
RED: extra evidence parent keys accepted
RED: erroring clean plant counted clean
RED: padj without pvalue allowed
RED: invalid sex treated unknown
RED: invalid age allowed
RED: class 2 detail ignored
RED: class 3 detail ignored
RED: graded verdict dropped
RED: renderer receives from-db
red-on-fault: 43/43
```

The mutation campaign used disposable copies and byte backups, restoring bytes
after every fault. None mutated the source checkout. Replay records remain
**synthetic protocol fixtures**, proving protocol logic only. Class 9's replay
result is never reported as a live measurement.

Additional checks: `git diff --check` is clean; all three changed Python files
parse with `ast.parse(feature_version=(3, 6))`; added lines contain no literal
home-marker character (built for the check with `chr(126)`). The decision and
report preserve their starting bytes as exact prefixes. The row-7 invariant
command returns no diff:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

Commit `a8b54e5` used another identity; it is not rewritten and stays as it is
(append-only). This round uses exactly the repository's configured identity
from `git config user.name` and `git config user.email`, without overrides.
Path-limited staging names only the five changed paths; the commit message is
read from a scratch-twin file. No push, remote, self-approval or merge.
Hours and metered dollars: unknown, not zero.

### Residual gaps

- **NOT met:** live DOI capture/resolution and live sealed class-9 measurement.
  Synthetic replay and in-process stubs prove no live registration outcome.
- **NOT met:** actual sealed catalogue/clean measurement, sealed >=9/10,
  external_human_seal and public catch-rate evidence; row 8 exit is not claimed.
- **NOT met:** database verification for rows 5 and 7. The full suite skips
  Row05DatabaseTests (17 tests) and ClaimConstraintTests (18 tests), among
  79 environment skips. Live pipelines/HPC and actual Python 3.6 execution
  also remain unverified.
- **NOT met:** PMID/E-utilities, literature-role typed-tool wiring, R-069 beyond
  claim evidence, class 10, stage-03/pilot emission wiring, pilot measurement
  and step B's data route/backend work.
- **NOT met:** containment of system/catalogue edits, scientific DE-model
  validity, real-DOI relevance and swaps without library_index. Direct renderer
  calls remain unguarded; short-form DOI registration resolution is not added.
- **NOT met:** fresh independent review, protected-change approval, deployment
  path-scan acceptance and merge.

## Owner rulings needed

None.


## Step A round F1 (review E1 corrections)

Starting commit, recorded before edits:
`12b26f7843a1cb6d48495279656b3c985f6a2e75`.
Item 8 was decided under the owner's standing delegation (23 Sep 2026).
This round applies only E1 F1, F2 and F3. No preceding report or decision bytes
are rewritten. No catalogue, fixture hash, acceptance threshold or test count
changes. The decision index was regenerated and remains byte-identical.

| Requirement / finding | Changed files | Acceptance | Result / red-on-fault |
|---|---|---|---|
| R-125 DOI half, E1 F1 | gars/_system/resolve_citation.py; gars/tests/test_emit_report.py | EmitReportTests.test_doi_reference_forms: author/title Doi plus period/slash year endings; existing adjacent DOI token sweep | Green; numeric boundary removal red, 3 failures |
| R-125 DOI half, E1 F2 | gars/_system/resolve_citation.py; gars/_system/claims/evidence_check.py; gars/tests/test_emit_report.py | Same test: remove parsed identifiers and check remaining markers; mixed valid/malformed references in both orders; absent/existing output preserved | Green; residual check bypass red, 4 failures |
| R-125 DOI half, E1 F3 | gars/_system/resolve_citation.py; gars/tests/test_emit_report.py | Same test: x_doi and ref_doi with equals, colon and underscore separators | Green; original leading word boundary restored red, 3 failures |
| R-042 | docs/decisions/0101-row-8-defect-catalogue-and-detectors.md; this report | Dated append-only addendum and expectation table | Recorded; old bytes preserved |

Protected files touched, one per line:

- `gars/_system/resolve_citation.py`
- `gars/_system/claims/evidence_check.py`

The numeric boundary excludes a preceding letter or digit. Removing the recognized
DOI marker before that check retains the explicitly required `DOI10/abcfake`
refusal. The marker's leading boundary now admits underscores. After parsed
identifiers are removed, remaining marker/numeric pairs refuse emission;
registration lookup still checks every parsed identifier. Clean author/title
controls include APA-style `(2010).`, direct `2010.` and `2010/2011` endings.

### Expectation changes

| File / test | Prior expectation | Required expectation and reason |
|---|---|---|
| gars/tests/test_emit_report.py / test_doi_reference_forms: Title mentions DOI; pages 10. plus registered DOI | Emit and perform one lookup | Refuse citation_unverifiable: the remaining title marker and page token still trigger item 8 F2; the real DOI is still looked up for both absent/existing output trials |
| gars/tests/test_emit_report.py / test_doi_reference_forms: Journal of Doi Studies, p. 10. plus registered DOI | Emit and perform one lookup | Same required residual-text refusal and lookup assertions |

These two lexical controls do not change the ten pinned clean projects, which
still produce zero false flags. No scientific relevance judgment is inferred.

### Commands and measured summaries

Every command ran from the repository root, without changing directory.
`TMPDIR`, `TEMP` and `TMP` were set to the scratch twin using `${PWD}-scratch`.
Python: `Python 3.13.5` (including the evaluation harness, satisfying >=3.9).
Only one full suite ran. No network or actual sealed fixtures were used.
`rg` was unavailable; repository reads used grep and direct file reads instead.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
Ran 491 tests in 81.865s
OK (skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 491 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.607s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.468s
OK (skipped=1)
```

`python3 gars/tests/test_citation_resolution.py`

```text
Ran 5 tests in 0.007s
OK (skipped=1)
```

`python3 gars/tests/test_emit_report.py`

```text
Ran 10 tests in 1.084s
OK
```

Development EXIT lines only:

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

The focused command is
`python3 gars/tests/test_emit_report.py EmitReportTests.test_doi_reference_forms`.
A scratch-only driver, `python3 "${TMPDIR}/f1_e1_regressions.py"`, copied the
named emission modules, generator, test support and synthetic response fixture
into a disposable tree. It loaded the two production modules from the parent
with `git show`, ran the current regression, restored byte backups, then
independently reversed each fix and restored bytes again. No source checkout
was mutated, no Git checkout/reset was used, and no live transport was selected.
Its exact summaries follow:

```text
parent with current regressions: RED
Ran 1 test in 0.850s
FAILED (failures=11)
F1 numeric boundary removed: RED
Ran 1 test in 0.674s
FAILED (failures=3)
F2 residual check bypassed: RED
Ran 1 test in 0.827s
FAILED (failures=4)
F3 leading boundary restored: RED
Ran 1 test in 0.817s
FAILED (failures=3)
restored current code: GREEN
Ran 1 test in 0.733s
OK
E1 regression faults: 3/3 RED; parent RED; restored GREEN
```

The first in-place test-only probe reported `FAILED (failures=9)` on the parent.
The first implementation probe reported `FAILED (failures=2)` because the
updated refusal control had not removed its preceding trial's output; that test
setup was corrected. The final disposable parent probe above uses all final
controls and reports eleven behavioral failures; the restored code is green.

Additional verification: `git diff --check` clean; all changed Python files
parse as Python 3.6 syntax with `ast.parse(feature_version=(3, 6))`; added
lines contain no literal home-marker character (checked with `chr(126)`).
The decision and report preserve their parent bytes as exact prefixes. The
row-7 invariant command returns no diff:

```bash
git diff dc6b803 -- gars/_system/claims/render_report.py gars/_system/claims/claims.sql gars/_system/claims/report_template.md
```

Commit `a8b54e5` used another identity; it is not rewritten and stays as it is
(append-only). This commit uses exactly the repository-configured identity,
read with `git config user.name` and `git config user.email`, without overrides.
Only the five named changed files are staged; the commit message is read from
a scratch-twin file. No push, remote, self-approval or merge.
Hours and metered dollars: unknown, not zero.

### Residual gaps

- **NOT met:** live DOI capture/resolution or live sealed class-9 measurement.
  Replay records remain **synthetic protocol fixtures**, proving protocol logic
  only; class 9's replay result is never a live measurement.
- **NOT met:** actual sealed catalogue measurement, sealed >=9/10,
  external_human_seal and public catch-rate evidence. Row 8 exit is not claimed.
- **NOT met:** database verification for rows 5 and 7. Row05DatabaseTests and
  ClaimConstraintTests were skipped with containers disabled. Live pipelines,
  HPC and actual Python 3.6 execution remain unverified.
- **NOT met:** rerun of the earlier 43-fault campaign. This round ran only the
  three E1 reversal faults. The unchanged campaign helper's malformed-marker
  mutation still names the pre-F2 conditional; it needs an anchor update before
  that campaign can run again, outside this round's item-8-only changes.
- **NOT met:** PMID/E-utilities, literature-role wiring, R-069 beyond claim
  evidence, class 10, stage-03/pilot emission wiring, pilot measurement and
  step B. Direct renderer calls remain unguarded.
- **NOT met:** system/catalogue edit containment, scientific DE-model validity,
  real-DOI relevance, swaps without library_index, fresh independent review,
  protected-change approval, deployment path-scan acceptance and merge.

## Owner rulings needed

None.


## Step B: data route, venues, bench

Starting hash, recorded before editing: `1cce53614843646fee0de32100c1117ff45d80ab`.
Branch: `build/gars-row-8-venues`. Round 1; no supplied review. All brief rulings
were decided under the owner's standing delegation (23 Sep 2026). Implementation
record: `docs/decisions/0102-row-8-venue-policy-and-backend-bench.md`.
Step A's existing report bytes and frozen files are preserved.

**Status: implementation blocked on the replay writer boundary, not complete.**
The route table, both submission doors, dataset additions and benchmark instrument
are implemented. No benchmark job was measured and the CSV is header only.
The private-data replay cannot pass because the explicitly permitted one-line
wrapperlib edit does not record expiry/permitted_backends. The proposed two-line
addition was tested only in a scratch copy: all 21 replay tests passed, with
all existing assertions retained. It is not present in this branch.

Producer effort: approximately 0.75 hours (estimate, not stopwatch evidence).
Measured production or benchmark execution: zero hours.

### Requirements and acceptance

| Requirement | Changed files | Acceptance | Result and red-on-fault seen |
|---|---|---|---|
| R-060 remainder | gars/_system/stage00_register.py; gars/_system/tools/registry.json; gars/_references/data_policy.tsv | test_venue_policy route lock/migration, expiry and homelab tests; unchanged test_data_class_required | PASS; yes, widening and expiry faults killed; frozen 4-test module OK |
| R-062 | gars/_system/venue_policy.py; gars/_system/executorlib.py; gars/tests/test_venue_policy.py | full 45-cell grid, exact FASTQ adversary, explicit descriptor, both doors and ordering | PASS; yes, removed gates, widened/case-folded exemption, suppressed reason and reordered checks killed |
| R-063 / 0100 | gars/_references/data_policy.tsv; gars/tests/test_data_route.py | all three classes and every table cell bound to parsed 0100 | data route recorded: 3/3; yes, table drift killed |
| R-064/R-065 | gars/_system/executorlib.py; gars/_system/venue_policy.py; gars/_system/wrapperlib.py | venue_of, 8 GiB/8.5 GiB, absent/unparseable memory, manifest versus executed venue | PASS; yes, all named resource/venue faults killed; existing check_executor_config unchanged |
| R-136 | gars/_system/stage00_register.py | patched marker refuses non-public storage; public passes | PASS; marker override mutation killed |
| R-193 input | scripts/backend_bench.py; tests/test_backend_bench.py; benchmarks/backend_bench.csv; benchmarks/backend_bench/README.md | prepared stage-02 submit, terminal-only collect, evidence regeneration, privacy, supersession and RSS units | PASS instrument; backend rows: 0/3 (); yes, missing evidence, privacy, edited wall, early evidence and FAILED append faults killed |
| R-042 | executor, finalize, shared venue line, fixture builders, scripts/rerun_check.py, 0102 and contracts | refusal order and immutable bytes; replay with recorded route | policy changes PASS; private replay NOT met pending the writer scope ruling; scratch candidate 21 tests OK |

### Preflight and protected scope

All commands were launched from the repository root. TMPDIR, TEMP and TMP were
set to the scratch twin for every command; logs and disposable trees stayed there.
No network, remote, push, pull request, merge or approval action was used.
`rg` was absent; Git grep, grep and Python were used instead. The base greps were
repeated with HEAD as a separate revision argument, covering submit callers,
local fixtures, memory, completed_fixture_submission and finalize flags.
The frozen row-6 test's identifiable case is only an immutable-classification
re-finalize, so its old refusal remains first and the lane does not edit it.

Pre-list disposition:

- approval_forgery, downstream_keys, execution_policy, lifecycle_executor and
  stage03_execution gain shared fixture-dataset calls in their builders.
- failure_classification, lifecycle_cancel and no_false_completion inherit the
  call through lifecycle_executor.prepared. Their files remain unchanged.
- lifecycle_faults copies and runs those same builders. Its file, pinned strings
  and expectations remain unchanged.
- executorlib_resume submits outside either allowed door and still expects
  R-073; it remains unchanged.
- manifest_groups already calls real public/fixture finalize; its fixture-only
  32G config becomes 2G before preparation.
- rerun_check gets the authorized expiry and Slurm stub fixture. Marker constants
  are patched in the test process and disposable executor copy, never selected
  through an environment override. The existing fixture exit label is corrected
  to say stub slurm; every assertion is retained.
- replay-baseline fixtures, templates and tests/test_planted_defects.py are
  unchanged. The planted-defect runner inherits the one completed fixture helper.

Protected files touched, one per line:

- `gars/_system/executorlib.py`
- `gars/_system/stage00_register.py`
- `gars/_system/wrapperlib.py` (only the group-11 venue line)
- `gars/_system/venue_policy.py`
- `gars/_references/data_policy.tsv`
- `gars/_system/tools/registry.json` (finalize only)
- `gars/00_initialize_project/CONTEXT.md`
- `gars/02_bioinformatics/CONTEXT.md`
- `gars/03_custom_analysis/CONTEXT.md`

The source audit prints `lifecycle fault anchors preserved: 45/45`,
`validate byte-identical`, `registry scope: finalize only`,
`executor pins and wrapperlib one-line boundary preserved`, and
`frozen files byte-identical: 4/4`. BUILTINS and every existing local-name
comparison are unchanged. No template or detector changed. Contracts describe
every new literal fail code. The decision index was regenerated with
`bash docs/decisions/build_index.sh`.

### Expectation changes

No existing assertion was changed or removed. These are the complete fixture
and behavior changes; line references name the implementation after this step.

| Test/helper | File and line | Old | New | Requirement |
| fixture dataset helper | `gars/tests/support.py:65` | no dataset helper | idempotent finalize-equivalent 0444 public/fixture writer | R-060/R-062 |
| completed_fixture_submission | `tests/run_tests.py:70` | unclassified submission possible | shared dataset row before real submit; all callers inherit | R-062 |
| completed_fixture_submission memory | `tests/run_tests.py:71` | class/template memory 32G to 96G | 2G before write_reproducibility hashes config | R-064 |
| lifecycle prepared builder | `gars/tests/test_lifecycle_executor.py:15` | unclassified fixtures | shared public/fixture row, inherited by failure/cancel/no-false-completion tests | R-062 |
| approval fixture | `gars/tests/test_approval_forgery.py:40` | unclassified analysis | public/fixture dataset | R-062 |
| stage03 fixture | `gars/tests/test_stage03_execution.py:29` | unclassified analysis | public/fixture dataset | R-062 |
| downstream fixture | `gars/tests/test_downstream_keys.py:23` | unclassified prepared stage | public/fixture dataset | R-062 |
| execution policy collect fixture | `gars/tests/test_execution_policy.py:46` | unclassified synthetic completion | public/fixture dataset | R-062 |
| manifest groups setup | `gars/tests/test_manifest_groups.py:43` | 32G declared on local | 2G before prepare; existing real finalize retained | R-064 |
| replay setup | `gars/tests/test_rerun_check.py:107` | local agreement dataset with no expiry | future expiry, Slurm stub and patched marker constants | R-060/R-062 |
| replay fixture exit label | `gars/tests/test_rerun_check.py:216` | fixture, local | fixture, stub slurm (assertions unchanged) | R-042 |
| replay reader | `scripts/rerun_check.py:200` | class/purpose/agreement only | recorded expiry/route passed and checked; missing private fields refused | R-042/R-060 |

### Parent red and fault evidence

A disposable archive of the starting HEAD received the new tests. The venue
import failed naming `gars/_system/venue_policy.py`; the bench import failed
naming `scripts/backend_bench.py`. A separate behavioral probe using the parent's
real prepare and submit, with only scheduler execution stubbed, failed its refusal
assertion: `AssertionError: deidentified_under_agreement submitted on local: 42`.
Current ExecutedDescriptorTests is green on the same private/local route.

`python3 gars/tests/test_venue_policy_faults.py` compiles each mutated source
before invoking its behavioral witness in a fresh scratch tree. Import and syntax
errors are not counted as policy kills. It prints the following observed controls;
each is red-on-fault seen **yes**, restored source green:

```text
fault red: CSV row without evidence
fault red: host name in evidence
fault red: hand-edited wall_s
fault red: evidence before terminal
fault red: FAILED evidence appended
fault red: route table drift
fault red: stage02 skips policy
fault red: stage03 skips policy
fault red: FASTQ exemption widened
fault red: class case insensitive
fault red: purpose case insensitive
fault red: FASTQ reason suppressed
fault red: absent memory refused
fault red: unparseable memory allowed
fault red: 8.5 GiB accepted
fault red: homelab without marker
fault red: grade load instead of executed descriptor
fault red: grade prepare-time group 11
fault red: analysis submission venue missing
fault red: submission venue missing
fault red: widen permitted backends
fault red: missing expiry accepted
fault red: marker environment override
fault red: identifiable accepted
fault red: login-node graded after swap
fault red: test-mode bypass
fault red: policy after reservation
fault red: policy after analysis launcher
fault red: policy before config refusal
fault red: policy before approval refusal
```

The reservation move is also the requested idempotency-reservation fault. The
load-versus-executed and group-11 faults are tested separately. Both submission
record venue keys have separate faults. Case folding of class and purpose has
separate faults. The env-bypass control has a real submit witness. These are
producer-visible controls, not sealed reviewer or catch-rate measurements.

### Commands and measured summaries

Commands below ran from the repository root with all three temp variables set
to the scratch twin. The Python was **3.13.5**, including evals/test_harness.py
(the required minimum is 3.9). Full suites ran one at a time. Database classes
for rows 5 and 7 were skipped under GARS_TEST_NO_CONTAINER=1; Docker is unavailable.
No row 8 threshold was changed.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`

```text
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
Ran 603 tests in 410.014s
FAILED (failures=2, errors=5, skipped=79)
```

`python3 tests/check_contracts.py`

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`

```text
suite: 603 tests, from unittest's loader
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`

```text
Ran 44 tests in 37.507s
OK
```

`python3 evals/check_results.py --controls --lexicon`

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`

```text
Ran 18 tests in 4.810s
OK (skipped=1)
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 gars/tests/test_venue_policy.py`

```text
Ran 15 tests in 1.192s
OK
```

`python3 gars/tests/test_data_route.py`

```text
Ran 1 test in 0.000s
OK
data route recorded: 3/3
```

`python3 gars/tests/test_data_class_required.py`

```text
Ran 4 tests in 0.661s
OK
```

`python3 tests/test_backend_bench.py`

```text
Ran 6 tests in 1.493s
OK
backend rows: 0/3 ()
```

`python3 gars/tests/test_venue_policy_faults.py`

```text
Ran 2 tests in 5.872s
OK
```

`python3 gars/tests/test_rerun_check.py`

```text
Ran 21 tests in 19.888s
FAILED (failures=2, errors=5)
```

The earlier full run, before the authorized replay fixture update, printed
`Ran 593 tests in 423.121s` and `FAILED (failures=14, skipped=79)`. All 14
were the agreement fixture lacking expiry. The latest run above is authoritative.

Additional checks: Python 3.6 grammar parses for the six changed production
Python modules; actual Python 3.6.8 is unavailable. `git diff --check` is clean.
Repository-local configured Git identity was inspected and is used unchanged.
Scratch probes used Python subprocesses to execute the archived parent and to
run the two-line writer candidate; no candidate writer edit enters this commit.
Source reads used cat/sed/grep and Python; scope checks used git status, git diff,
git show, git ls-files and AST/JSON comparisons. New files and edits used Python
and shell heredocs. Parent sources came from `git archive HEAD` into the scratch
twin. No command changed directory before running. Git staging is path-limited;
the commit message comes from a scratch file.

### Residual gaps

- **NOT met:** passing whole-suite gate and private-data replay, pending ruling 1.
- **NOT met:** row 8's three measured backend rows; local, homelab and slurm are
  all unmeasured. Instrument tests print 0/3 and no row exit is claimed.
- **NOT met:** actual Python 3.6.8 execution, real Slurm accounting, live resource
  normalization and live venue measurements. Synthetic tests are not those facts.
- **NOT met:** R-193 priced unit economics; costs are unmetered inputs only.
- **NOT met:** real FASTQ per-sample cost, row 13's sacct actuals; cloud routing.
- **NOT met:** R-061 and hosted-prompt exposure enforcement; second backup
  destination; any institutional agreement.
- **NOT met:** OS isolation from privileged or unguarded writers; host attestation
  beyond the marker; actual memory rather than declarations; FASTQ columns other
  than fastq_1/fastq_2; truth of machine clock readings.
- **NOT met:** Docker-backed rows 5/7 database verification on this host.
- **NOT met:** independent review, protected approval, merge and row 8 exit.

## Owner rulings needed

1. **Record replay route fields at prepare.** The brief requires replay to pass
   manifest-recorded expiry and permitted_backends but permits only the venue
   derivation line in wrapperlib.py. The existing prepare_manifest_facts records
   neither field. Options: authorize the two additional dictionary entries
   `'expiry': dataset.get('expiry')` and
   `'permitted_backends': dataset.get('permitted_backends')` in that function;
   or keep the one-line boundary and leave private replay/step B stopped for a
   separate writer change. The first option was tested only in the scratch twin:
   `Ran 21 tests in 26.025s`, `OK`, with all existing assertions retained.
   No unrecorded value is inferred for private replay and no policy is weakened.


## Step B retry round B1

Starting commit, recorded before editing: `efbe369003ea21fb211e7cdabb92d83eccdf354d`.
The working tree was clean on `build/gars-row-8-venues`. This retry implements
only added rulings 6–8, decided under the owner's standing delegation (23 Sep 2026).
Round 1 remains the parent; its report and decision bytes remain intact. The
previous writer-boundary question is answered by ruling 7 option (a). No backend
measurement, step-A change, policy relaxation, approval or merge is performed.

### Requirement, implementation and acceptance

| Requirement / ruling | Changed files | Acceptance | Result; red-on-fault seen |
|---|---|---|---|
| R-042 / ruling 6 | `gars/tests/test_venue_policy.py`, `scripts/backend_bench.py` | Runtime-joined launcher glob and four shebangs; venue and bench tests | PASS; assertions and generated bytes preserved. The original deployment failure is supplied evidence, not a locally rerun deployment scan. Local added-line scan is clean. |
| R-042, R-060 / ruling 7 | `gars/_system/wrapperlib.py`, `gars/_references/manifest_schema.json`, `gars/_system/manifest_check.py` | `test_route_facts_recorded_preserved_and_required`; manifest suite | PASS; yes: two facts absent in parent writer, parent schema assertion fails; removing the new writer entries in a disposable candidate is red. |
| R-042 / legacy agreement path | `scripts/rerun_check.py`, `gars/tests/test_rerun_check.py` | `test_legacy_agreement_manifest_refused_before_replay` | PASS; yes: missing expiry, missing permitted backends, and both missing refuse before replay with `manifest_predates_expiry_recording`; disabling the check yields three assertion failures. |
| R-042 / recorded facts | `gars/tests/test_rerun_check.py` | `test_recorded_route_mismatch_refused` | PASS; each changed recorded fact refuses `replay_dataset_mismatch` before any replay output. Parent lacks the route facts and gives the generic missing-route reason. |
| R-042 / public compatibility | `gars/tests/test_rerun_check.py` | `test_legacy_public_fixture_manifest_replays_two_of_two` | PASS, 2/2; compatibility control also passed before implementation; yes: removing public fallback in a disposable candidate makes it red. |
| Ruling 8 / full verification | `README.md`, `DEVELOPMENT.md`; appended decision and report | All Rule 5 commands; replay and manifest suites | PASS. Count check first found 603 versus 607; exactly three current claims updated to the derived total. |

The manifest gains two recorded facts; none removed. The writer copies only the
dataset row's expiry and permitted_backends. Collect preserves them. Schema and
checker retain the eighteen groups and their applicability rules; group 11
requires recorded route facts except for historical public manifests lacking
both. New null or placeholder facts do not satisfy completeness. Agreement
manifests lacking either field refuse before generic completeness grading and
before an output directory, comparison result or submission. No historical
agreement value is inferred from today's row. Existing equality checks and
finalize's route/expiry validation still apply.

### Every changed line

The following inclusive line spans cover every insertion and replacement against
the starting commit, including blank lines. No pre-existing report or 0102 line
is replaced. The regenerated decision index is byte-identical because its
frontmatter inputs are unchanged.

| File | Parent lines | Retry lines | Change |
|---|---|---|---|
| `DEVELOPMENT.md` | 156–156 | 156–156 | Current count only: 603 to 607. |
| `DEVELOPMENT.md` | 175–175 | 175–175 | Current count only: 603 to 607. |
| `README.md` | 322–322 | 322–322 | Current count only: 603 to 607. |
| `docs/decisions/0102-row-8-venue-policy-and-backend-bench.md` | after 268 | 269–327 | Dated append-only ruling, R-042 and residual account. |
| `gars/_references/manifest_schema.json` | after 116 | 117–118 | Group 11 lists the two recorded route facts. |
| `gars/_system/manifest_check.py` | after 134 | 135–140 | Check route-fact presence; retain legacy public compatibility. |
| `gars/_system/manifest_check.py` | 136–136 | 142–142 | Check route-fact presence; retain legacy public compatibility. |
| `gars/_system/wrapperlib.py` | after 770 | 771–772 | Exactly two dataset-derived dictionary entries. |
| `gars/tests/test_rerun_check.py` | after 159 | 160–200 | Four additional regressions and the explicit historical-public variant of the existing helper; existing assertions retained. |
| `gars/tests/test_rerun_check.py` | 562–562 | 603–606 | Four additional regressions and the explicit historical-public variant of the existing helper; existing assertions retained. |
| `gars/tests/test_rerun_check.py` | after 582 | 627–632 | Four additional regressions and the explicit historical-public variant of the existing helper; existing assertions retained. |
| `gars/tests/test_venue_policy.py` | 52–52 | 52–52 | Runtime path-component spelling; identical generated script or glob meaning. |
| `gars/tests/test_venue_policy.py` | 76–76 | 76–76 | Runtime path-component spelling; identical generated script or glob meaning. |
| `gars/tests/test_venue_policy.py` | 241–241 | 241–241 | Runtime path-component spelling; identical generated script or glob meaning. |
| `gars/tests/test_venue_policy.py` | 260–260 | 260–260 | Runtime path-component spelling; identical generated script or glob meaning. |
| `scripts/backend_bench.py` | 123–123 | 123–123 | Runtime-joined shebang; identical emitted bytes. |
| `scripts/rerun_check.py` | after 116 | 117–122 | Shared historical-agreement refusal before grading and direct binding. |
| `scripts/rerun_check.py` | after 120 | 127–127 | Shared historical-agreement refusal before grading and direct binding. |
| `scripts/rerun_check.py` | after 202 | 210–210 | Shared historical-agreement refusal before grading and direct binding. |
| `docs/implementation/row_8_change_report.md` | after 2390 | 2391–2633 | This appended retry report, tables and verbatim verification summaries. |

### Protected files touched

`gars/_system/wrapperlib.py`

`gars/_system/manifest_check.py`

`gars/_references/manifest_schema.json`

The latter two are explicitly authorized by ruling 7's consistency condition.
Executor source, pinned fault strings, dataset finalizer, route table, registry,
step A, row 6's frozen data-class test and existing manifest tests are unchanged.

### Expectation changes

| Test / file and retry line | Old | New | Requirement |
|---|---|---|---|
| `test_route_facts_recorded_preserved_and_required`, `gars/tests/test_rerun_check.py:161` | Prepare omitted both route facts; agreement replay could not complete | Exact dataset values recorded at prepare, preserved at collect and replay; schema completeness checked; reproduction 2/2 | R-042, R-060; ruling 7 |
| `test_legacy_agreement_manifest_refused_before_replay`, same file line 185 | Generic missing-route refusal for a historical agreement manifest | Named `manifest_predates_expiry_recording` for either or both missing fields, no replay artifacts | R-042; ruling 7 |
| `test_recorded_route_mismatch_refused`, same file line 195 | Parent manifest did not supply the facts to compare | Each recorded expiry/route drift explicitly tested; existing mismatch comparison unchanged | R-042; ruling 7 |
| `test_legacy_public_fixture_manifest_replays_two_of_two`, same file line 603; helper line 606 and lines 627–632 | Existing normal/relative RNASEQ helper had no historical-route variant | Explicit variant removes both facts, retains every existing replay assertion and reproduces 2/2 | R-042; ruling 7 |
| `PolicyFixture.no_effects`, `gars/tests/test_venue_policy.py:76` | Literal composite launcher glob | Same assertion using runtime-joined components; no verdict change | Ruling 6 |
| Script fixtures, `gars/tests/test_venue_policy.py:52,241,260`; `scripts/backend_bench.py:123` | Embedded absolute shebang string | Same bytes assembled from components; no verdict change | Ruling 6 |

No existing test assertion is weakened or removed. The four-test pre-implementation
probe printed `Ran 4 tests in 1.849s` and `FAILED (failures=6)`: the new schema
capture assertion and missing-route/mismatch reasons were red; the public legacy
control was already green. After implementation the same probe printed
`Ran 4 tests in 2.489s` and `OK`. The source-spelling edits did not affect those
replay behaviors. Disposable syntax-checked fault copies independently confirmed
red on removal of the old-manifest refusal, public fallback, and writer entries;
these were behavioral failures, not import or syntax failures. All scratch trees
were built from the parent archive plus the candidate files and removed afterward.

### Commands and verbatim summaries

All commands were launched from the repository root. `TMPDIR`, `TEMP` and `TMP`
were set to the scratch twin for every shell command; logs, archive copies,
fixtures and the commit message stayed there. No system temp folder was used.
The full suite ran once, with `GARS_TEST_NO_CONTAINER=1`; no two full suites ran
concurrently. Ancillary checks used isolated fixtures. Python was 3.13.5,
including the evaluation harness (satisfying its 3.9-or-later requirement).

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
collected 292 tests from tests
collected 315 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
Ran 607 tests in 455.430s
OK (skipped=79)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 292 tests from tests
collected 315 tests from gars/tests
suite: 607 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 38.175s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 18 tests in 4.847s
OK (skipped=1)
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 gars/tests/test_venue_policy.py`:

```text
Ran 15 tests in 1.227s
OK
```

`python3 gars/tests/test_data_route.py`:

```text
Ran 1 test in 0.000s
OK
data route recorded: 3/3
```

`python3 gars/tests/test_data_class_required.py`:

```text
Ran 4 tests in 0.673s
OK
```

`python3 tests/test_backend_bench.py`:

```text
Ran 6 tests in 1.504s
OK
backend rows: 0/3 ()
```

`python3 gars/tests/test_rerun_check.py`:

```text
Ran 25 tests in 27.966s
OK
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
```

`python3 gars/tests/test_manifest_groups.py`:

```text
Ran 18 tests in 14.749s
OK
```

Rows 5 and 7 database classes were skipped because Docker is unavailable.
Other environment and sealed-input skips remain as reported by the suite.
No development result is promoted to a sealed result or a row exit.

The earlier count command reported three stale claims; its rerun above is green.
Reads and scope checks used git rev-parse/status/show/diff, Python, cat and sed;
`rg` was unavailable, so Python searches were used. Changes used short Python
rewriters, never a patch containing the forbidden old strings. Added-line path
component checks, U+007E checks, Python 3.6 grammar parsing, append-only byte-prefix
checks and `git diff --check` passed. These local checks do not claim execution
of the deployment's external scan. `bash docs/decisions/build_index.sh` regenerated
the index without a byte change. Git identity was read from this repository's
configuration and used unchanged; staging names individual files and the commit
message is read from a scratch file. No network, remote change, push, approval or
merge was performed.

### Hours and residual gaps

Approximate producer effort for this retry: 0.5 hours, including verification;
no human review or venue measurement time is included.

- **NOT met:** all three measured backend rows. CSV remains header only, 0/3;
  actual local, homelab and Slurm measurements arrive later. Row 8 exit is not claimed.
- **NOT met:** Python 3.6.8 runtime execution, live Slurm accounting, actual resource
  normalization and live venue measurements. Grammar and synthetic tests are not
  evidence of those runs.
- **NOT met:** rows 5/7 Docker database verification on this host.
- **NOT met:** R-193 priced economics, real FASTQ per-sample costs, cloud routing,
  R-061 and prompt-exposure enforcement, second backup destination, institutional
  agreements, and the prior threat-model residuals.
- **NOT met:** independent review, protected approval, merge and external deployment
  path-scan verification. Only the local added-line spelling check ran here.

The historical private-replay and whole-suite blockers in the earlier section
are closed by ruling 7 and the passing commands above; the older account remains
append-only evidence of round 1.

## Owner rulings needed

None.


## Step B retry round C1

2026-09-25. Starting commit: `633778af004752158c1d10431352e5c04b5f031b`.
This continuation keeps both earlier step-B commits and adds one C1 commit.
The B1 retry already implemented rulings 6 and 7; their historical records are
preserved. This round answers `docs/reviews/row_8_review_stepB_B1.md`, which
remains untracked and unchanged. The rulings were decided under the owner's standing delegation (23 Sep 2026).
Only the review corrections below are added. Step A's report prefix is intact.

### Every changed line block

Line numbers below name the final candidate files. An inserted block includes
its separating blank lines; no unlisted source line is changed.

| File | Candidate lines | Change |
|---|---|---|
| `DEVELOPMENT.md` | 156; 175 | Current suite counts 607 to 610 only |
| `README.md` | 322 | Current suite count 607 to 610 only |
| `gars/_system/manifest_check.py` | 142–143 | Accept the three specified backend/venue pairs in group 11 |
| `gars/tests/test_manifest_groups.py` | 12 | Import patch for the optional marker fixture |
| `gars/tests/test_manifest_groups.py` | 44–54 | Optional scratch marker in the calling process and copied executor |
| `gars/tests/test_manifest_groups.py` | 523–539 | Valid, invalid and predicate-mismatched backend/venue pairs |
| `gars/tests/test_rerun_check.py` | 606–611 | Both-marker-state replay test and optional helper argument |
| `gars/tests/test_rerun_check.py` | 616–617 | Pass the optional marker state to the existing manifest fixture |
| `gars/tests/test_rerun_check.py` | 634–639 | Assert original prepare/collect completeness and executed venue |
| `gars/tests/test_rerun_check.py` | 684–686 | Assert both replay manifests and submission records carry that venue |
| `gars/tests/test_venue_policy.py` | 279–302 | Stage-03 memory boundary, over-limit and duplicate-declaration cases |
| `gars/tests/test_venue_policy_faults.py` | 24–26 | Behavioral fault that removes stage-03 memory extraction |
| `docs/decisions/0102-row-8-venue-policy-and-backend-bench.md` | 328–381 | Dated append-only C1 addendum and R-042 account |
| `docs/implementation/row_8_change_report.md` | Appended C1 sections through end of file | This line table, finding/expectation account, commands and residuals |

The decision index was regenerated with `bash docs/decisions/build_index.sh`;
its bytes did not change. No manifest-schema edit was necessary. The added-line
path-spelling check passed, including the parent-step and U+007E exclusions.
The deployment's external scan itself is not available to this producer.

## Step B review round C1 fixes

2026-09-25. Producer effort: approximately 0.75 hours including verification;
no benchmark or production venue measurement was performed. The implementation
uses the existing mapping and ruling 7(i)'s manifest-consistency authorization.
It introduces no new route, schema field, threshold or backend.

| Finding / requirement | Changed files | Acceptance test | Result; red-on-fault seen |
|---|---|---|---|
| F1 BLOCKER / R-042 | `gars/_system/manifest_check.py`; `gars/tests/test_manifest_groups.py`; `gars/tests/test_rerun_check.py`; 0102 | `test_backend_venue_pairs`; `test_marker_venues_prepare_grade_and_replay`; full suites | PASS; yes: both new tests failed with the starting backend-equals-venue checker, then passed after its correction; both marker states replay 2/2 with complete manifests and the expected executed venue |
| F2 MINOR / R-062 | `gars/tests/test_venue_policy.py`; `gars/tests/test_venue_policy_faults.py`; 0102 | `test_analysis_memory_declarations` and the stage03 memory-source fault | PASS; yes: replacing script-derived memory with None turns the witness red; the unmodified path allows 8G, refuses 16G naming the memory rule and refuses duplicate declarations as resource_unparseable, with no refused-submit effects |
| F3 NOTE / R-042 | This appended report and 0102 | Source inheritance/door survey below | Closed by the five explicit module lines; red-on-fault seen: no, documentation only |

Protected file touched in C1, one per line:

- `gars/_system/manifest_check.py`

The checker validates historical prepare evidence against the three permitted
backend/venue pairs without consulting today's marker. Its backend/predicate
binding, required fields and applicability remain intact. Source comparison with
the starting commit confirms no executor, policy, finalize, route table, replay
instrument, schema, benchmark instrument, template, step-A or frozen classification
test changed. All lifecycle fault anchors therefore remain byte-identical.

### Expectation changes and pre-list disposition

| Test / file and line | Old | New | Requirement |
|---|---|---|---|
| `ManifestGroupsTests` fixture, `gars/tests/test_manifest_groups.py:44` | No optional controlled marker at prepare | Optional scratch marker patches the constant in the parent process and copied executor; default callers unchanged | R-042 |
| `test_backend_venue_pairs`, same file line 523 | Homelab manifest incompleteness untested | Three valid pairs accepted; all tested invalid pairs and backend/predicate mismatches refused | R-042 |
| `test_marker_venues_prepare_grade_and_replay`, `gars/tests/test_rerun_check.py:606`; helper line 611 | No marked prepare/grade/replay control | Explicit absent/present states each preserve every existing replay assertion and reproduce 2/2; original and replay manifests/records have the expected venue | R-042 |
| `test_analysis_memory_declarations`, `gars/tests/test_venue_policy.py:279` | No direct stage-03 script-memory witness | Real submit enforces 8G/16G and duplicate-declaration cases before side effects | R-062 |
| Fault table, `gars/tests/test_venue_policy_faults.py:24` | Memory source could be disabled without a step-test failure | Syntax-valid memory=None fault is killed by the stage-03 witness | R-062 |

No existing assertion is removed or weakened. The normal replay helper path and
all prior legacy-manifest assertions are retained. The five pre-listed modules
need no builder change, for these source-derived reasons:

- `gars/tests/test_executorlib_resume.py`: its submit targets an unprepared stage outside both permitted doors, so it retains R-073 before policy; its other test executes the generated guard directly.
- `gars/tests/test_failure_classification.py`: imports `test_lifecycle_executor.prepared`, which already calls `write_fixture_dataset` before preparation.
- `gars/tests/test_lifecycle_cancel.py`: its fixture and direct prepared runs use `test_lifecycle_executor.prepared`, inheriting the same public/fixture row.
- `gars/tests/test_lifecycle_faults.py`: copies the test tree and invokes the already-classified lifecycle and stage-03 builders; no separate submit builder or pinned-string change is needed.
- `gars/tests/test_no_false_completion.py`: imports `test_lifecycle_executor.prepared`, inheriting its public/fixture dataset for each submit-reaching case.

Source survey commands read these five modules and their shared builder with
`cat` and `sed`, and reviewed the resulting diff with `git diff`. All five run
unchanged in each complete suite. The original report used abbreviated module
names; these full names make that inheritance explicit and searchable.

The six-module `git grep -n -E` survey used the pattern
`from test_lifecycle_executor import prepared|write_fixture_dataset|shutil.copytree|R-073: submit requires`
and printed:

```text
gars/tests/test_executorlib_resume.py:56:                self.assertIn('R-073: submit requires a prepared stage or approved analysis', error)
gars/tests/test_failure_classification.py:10:from test_lifecycle_executor import prepared
gars/tests/test_lifecycle_cancel.py:12:from test_lifecycle_executor import prepared
gars/tests/test_lifecycle_executor.py:9:from support import GARS, write_fixture_dataset
gars/tests/test_lifecycle_executor.py:15:    write_fixture_dataset(root)
gars/tests/test_lifecycle_faults.py:219:                    shutil.copytree(str(GARS / directory), str(root / directory),
gars/tests/test_no_false_completion.py:13:from test_lifecycle_executor import prepared
```

### Commands and verbatim summaries

All shell commands launched from the repository root with `TMPDIR`, `TEMP` and
`TMP` set to the scratch twin. Logs, copied trees, fixtures and the commit message
stayed there. Python was 3.13.5, including the evaluation harness (3.9 or later).
Full suites ran sequentially, never concurrently. Unit-module and static checks
could run alongside a suite. No network, remote, push, pull request or merge was
used. The review stayed untracked; its SHA-256 was checked before staging.

The required suite runs directly from the workspace. The additional full-suite
probes use a scratch snapshot of the same candidate with only its marker constant
patched to a fixed scratch path, shared by subprocess copies. One setup probe was
interrupted after noticing its relative marker expression moved when copied; it
has no completed-suite result and is not counted. The corrected setup first
printed `subprocess prepare with shared scratch marker: local/homelab`.
The fixture-controlled marker tests never inspect or create the host marker.

`GARS_TEST_NO_CONTAINER=1 python3 tests/run_tests.py`:

```text
collected 292 tests from tests
collected 318 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
Ran 610 tests in 461.155s
OK (skipped=79)
```

`Same full-suite runner in scratch, marker present`:

```text
collected 292 tests from tests
collected 318 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
Ran 610 tests in 413.800s
OK (skipped=79)
```

`Same full-suite runner in scratch, marker absent`:

```text
collected 292 tests from tests
collected 318 tests from gars/tests
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
Ran 610 tests in 474.371s
OK (skipped=79)
```

`python3 tests/check_contracts.py`:

```text
14 contracts clean: sections, wait points, vocabulary.
```

`python3 tests/check_counts.py`:

```text
collected 292 tests from tests
collected 318 tests from gars/tests
suite: 610 tests, from unittest's loader
enforced=3
clean — every current claim matches the suite
```

`python3 evals/test_harness.py`:

```text
Ran 44 tests in 37.515s
OK
```

`python3 evals/check_results.py --controls --lexicon`:

```text
clean — graded=1
```

`python3 tests/test_planted_defects.py`:

```text
Ran 18 tests in 4.881s
OK (skipped=1)
planted-defects development (producer-authored, unsealed): 9/10 classes (placeholder 10 counted planted, not caught)
false flags (producer-authored clean projects): 0/10
graded 19 of 19 development projects seen
class 6: measured with --verify-integrity full; stage 01 default is none
```

`python3 gars/tests/test_venue_policy.py`:

```text
Ran 16 tests in 1.246s
OK
```

`python3 gars/tests/test_data_route.py`:

```text
Ran 1 test in 0.000s
OK
data route recorded: 3/3
```

`python3 gars/tests/test_data_class_required.py`:

```text
Ran 4 tests in 0.661s
OK
```

`python3 tests/test_backend_bench.py`:

```text
Ran 6 tests in 1.521s
OK
backend rows: 0/3 ()
```

`python3 gars/tests/test_manifest_groups.py`:

```text
Ran 19 tests in 14.454s
OK
```

`python3 gars/tests/test_rerun_check.py`:

```text
Ran 26 tests in 27.865s
OK
EXIT instrument self-test (fixture, stub slurm): reproduction 2/2
```

`python3 gars/tests/test_venue_policy_faults.py`:

```text
Ran 2 tests in 5.854s
OK
```

Both full-suite marker probes patch only the constant in a scratch source
snapshot; the fixed path stays identical when the suite copies executorlib into
subprocess fixtures. The same marker file is then removed for the absent probe.
Neither probe creates the machine-owned marker or changes production routing.
The full workspace suite and both copied-suite runs retain the 79 environment
skips; rows 5 and 7 database classes are skipped because Docker is unavailable.

The pre-implementation F1 pair test printed `Ran 1 test in 0.229s` and
`FAILED (failures=1)` for local/homelab. The replay test printed
`Ran 1 test in 1.004s` and `FAILED (failures=1)` for its marker-present case;
the missing-marker control already replayed 2/2. With the fix, the same tests
printed `Ran 1 test in 0.241s` / `OK` and `Ran 1 test in 1.317s` / `OK`.
The latter prints the labelled synthetic-worker 2/2 line for each marker state.
The direct stage-03 memory test printed `Ran 1 test in 0.005s` / `OK`.
The fault harness above additionally prints `fault red: stage03 memory source ignored`.
All 30 earlier step-B fault controls remain green as a harness; their planted
faults remain red. No syntax/import error is counted as the new behavioral kill.

The first count check correctly reported three stale 607 claims; the count-only
README/DEVELOPMENT edits make its recorded rerun clean at 610. Ancillary source
reads and scope checks used cat, sed, Git grep/diff/status/show/log/branch/config,
and Python. Short Python rewriters performed edits; no forbidden removed-line
spelling was reintroduced through a patch. Scratch snapshots used Git archive,
tarfile and a local copy of Git metadata, with no remote added. Marker probes
and targeted tests used Python subprocesses or the same runner by its runtime-
resolved scratch path, all launched from the repository root. Python 3.6 grammar
parsing, append-only prefix checks, unchanged-file scope checks, added-line
spelling checks and `git diff --check` passed. These do not claim the external
path scan. Staging names each changed file, and Git reads the commit message
from scratch using the repository's configured identity without an override.

## Owner rulings needed

None.

## Residual gaps — C1

- **NOT met:** all three measured backend rows; `backend rows: 0/3 ()`. The CSV
  remains header only, and all venue measurements arrive later. Row 8 exit is
  not claimed.
- **NOT met:** actual Python 3.6.8 execution, live Slurm accounting, real timing
  and platform RSS measurements, and per-sample real FASTQ costs.
- **NOT met:** Docker-backed database verification for rows 5 and 7 on this host.
- **NOT met:** R-193 priced unit economics; the instrument records unmetered
  inputs. Cloud, R-061/prompt-exposure enforcement, the second backup destination
  and institutional agreements remain open.
- **NOT met:** prior threat-model residuals: privileged or unguarded rewrites,
  host attestation beyond the marker, actual rather than declared memory,
  FASTQ paths outside the named columns, and independent timing attestation.
- **NOT met:** independent acceptance of this C1 commit, protected-change
  approval, merge, external deployment path-scan verification or any sealed exit.

F1, F2 and F3 are closed by this producer response; no finding waits on a ruling.
