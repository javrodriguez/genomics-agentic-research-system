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
