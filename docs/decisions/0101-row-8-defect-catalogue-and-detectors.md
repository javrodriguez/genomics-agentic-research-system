---
date: 2026-09-24
status: standing
kind: decision
touches:
  - benchmarks/defects/
  - tests/test_planted_defects.py
  - tests/run_tests.py
  - gars/_system/stage01_samplesheet.py
  - gars/_system/integrity.py
  - gars/_system/wrappers/rnaseq-de/rnaseq_de.py
  - gars/_system/claims/evidence_check.py
  - gars/_system/claims/emit_report.py
  - gars/_system/resolve_citation.py
  - gars/00_initialize_project/CONTEXT.md
  - gars/01_prepare_samplesheets/CONTEXT.md
  - gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md
  - gars/tests/test_citation_resolution.py
  - gars/tests/fixtures/citations/
  - gars/tests/test_emit_report.py
  - gars/tests/test_integrity_records.py
  - README.md
  - DEVELOPMENT.md
  - docs/ledger.csv
  - docs/implementation/row_8_change_report.md
symptoms:
  - cell-level rows and swapped library indexes pass stage 01
  - gzip-valid record truncation passes full integrity
  - raw or incorrect adjusted p-values pass collect
  - evidence paths and DOI registrations are unchecked at report emission
---
# Row 8 step A: defect catalogue and detectors

## Context

Starting commit: `dc6b803fea84b8c2df8bb748e3312fc3220800a9`.
§18 row 8 step A implements R-114, R-145, the DOI half of R-125,
§7.2 check 1 for sex, R-141's DEGRADE flag, R-042 and §17's design-defect clause.
Step B, sealed measurement and protected-change approval are separate work.
The change report is `docs/implementation/row_8_change_report.md`.

## Decision

**DELEGATED RULINGS (label kept exactly; review round 5 NOTE-2).**
Every ruling in the supplied brief was decided under the owner's standing delegation (23 Sep 2026).
These are Glitch's delegated rulings, never the owner's words. This record implements
them and does not approve its own protected changes.

D-18 is answered by §11.2's list order, IDs 1–10. The conflicting prose about
the “first three” does not reorder the list. The JSON subset of YAML follows
0048 and decision 0011's stdlib-only Python 3.6 constraint.

| id | class (§11.2) | expected flag | expected stage | status |
|---|---|---|---|---|
| 1 | batch fully confounded with condition | `confounded_condition` | `01_prepare_samplesheets` | active |
| 2 | n = 1 per group | `insufficient_biological_replicates` (ATAC) / `invalid_design` with the group-of-one detail (RNA) | `01_prepare_samplesheets` | active |
| 3 | sex/age imbalance across arms | `confounded_condition` (a perfectly confounded `sex`) / `covariate_imbalance` | `01_prepare_samplesheets` | active |
| 4 | cells treated as replicates | `pseudoreplication` | `01_prepare_samplesheets` | active |
| 5 | sample labels swapped between `samples.csv` and FASTQ | `sample_label_mismatch` | `01_prepare_samplesheets` | active |
| 6 | truncated FASTQ | `integrity` | `01_prepare_samplesheets` | active |
| 7 | fabricated output path in a finding | `evidence_missing` / `evidence_hash_mismatch` | `report_emit` | active |
| 8 | DE table with raw p-values, no correction | `uncorrected_pvalues` | `02_collect` | active |
| 9 | claim citing a non-existent DOI | `citation_unresolved` | `report_emit` | active |
| 10 | Hi-C resolution mismatch (placeholder) | — | — | placeholder |

### Stage entry points and arithmetic

Classes 1–6 run `python3 gars/_system/stage01_samplesheet.py --project <plant> --check --verify-integrity full`.
A refusal scores only exit 1, JSON ok false, the named failure and required
detail together. A class-3 DEGRADE scores only the named flag in the CLI's
`design_check.flags`. A not_checkable outcome is never a catch.
Class 8 uses the real collect after real prepare and the suite's
`completed_fixture_submission`; check-table is diagnosis only.
Classes 7 and 9 call `emit_report.main(argv, transport=replay)`, the CLI's entry,
and require refusal, named code and no output. No bare detector earns a catch.
Ten clean projects each run stage 01, collect and emission. Every seen project is graded.

Class 10 has neither fixture nor recipe and counts planted, not caught:
the development headline has denominator ten and maximum nine.
Its returns_when is copied from §2.2:
“two benchmark tasks with cited references and one defect class exist for it”.

### Detector rules and pre-committed constants

1. Existing batch confounding and group-size checks remain. Existing §7.2
   checks are retained. Identifier columns are not covariates.
2. Only supplied sex/age columns are checked. Exclude unknown sex.
   Every arm having one different sex refuses confounded_condition naming sex.
   Otherwise female proportions differing by **>= 0.5** or median ages by
   **>= 10 years** add covariate_imbalance with disposition DEGRADE.
   All sex unknown / all ages blank records not_checkable for that half.
   SEX_PROPORTION_THRESHOLD=0.5 and AGE_MEDIAN_THRESHOLD=10 were fixed by
   the delegated brief before any development run; no tuning is permitted.
3. For bulk RNA/ATAC, cell_barcode always refuses pseudoreplication: no registered
   pseudobulk path. If subject or biological_unit exists, any condition with >=2
   rows but <2 distinct units also refuses. Subject wins. Without either column,
   that half does not apply. No de_method or other config key is introduced.
4. library_index enables streamed first-1,000-record CASAVA 1.8 index reading
   from every included FASTQ, including gzip and every lane. Compare the whole
   majority index per sample, including both dual indexes. Mismatch refuses
   sample_label_mismatch; detail contains only the check name and sample count.
   Column absence or non-CASAVA input is not_checkable, recorded in the assay's
   sample_label_check outcome, never a pass or a catch.
5. Full integrity streams all records of fastq/fq, plain or gzip. Require four
   newline-terminated lines, @ first line, + third line and equal sequence/quality
   lengths. Failures return “truncated record N”, never record content.
   Quick and skip remain unchanged. Non-FASTQ gzip full decompression is retained.
   Both callers receive this: stage 01 --verify-integrity full (default none)
   and stage 00 finalize --integrity full (default quick).
   **class 6: measured with --verify-integrity full; stage 01 default is none**.
   Default stage 01 does not catch record truncation; stage 00 quick sees gzip
   framing/magic only, not whole records.
6. evidence_check reads only the snapshot and named artifact files, against
   BASE's claims[].evidence[] nested artifact or source shape. Paths must be
   project-relative, have no parent component (os.pardir), stay inside after
   symlink resolution, exist as files and match artifact.sha256.
   Missing/escaping paths produce evidence_missing; differing bytes produce
   evidence_hash_mismatch, one line per offending claim ID and code.
7. emit_report is the supported preflight path. From-db exports once through
   render_report.database_snapshot's existing container client into a unique
   temporary file in the output folder. Snapshot mode uses the given file.
   Evidence preflight runs in process on that file with the injected transport.
   Only success invokes unchanged render_report in a subprocess with --snapshot
   naming that same file. It never forwards --from-db. Refusal preserves any
   existing output byte-for-byte. Temporary exports are removed on all exits.
8. The collect gate's tested set is the m rows with both pvalue and padj nonmissing.
   Refuse a nonempty table with m=0 (“no tested rows”), any padj<pvalue,
   m>=2 with all padj=pvalue and any pvalue<1, or recomputed BH disagreement
   greater than relative **1e-4**. A lone row has BH(p)=p and must match it.
   BH_RELATIVE_TOLERANCE=1e-4 is fixed before runs, including CSVs written at
   six significant digits. The same function backs check-table and collect;
   the runner grades collect only.
9. Normalize doi:, https://doi.org/ and https://dx.doi.org/ and remove one
   trailing period, comma or semicolon. Query Crossref works; on 404 query the
   DOI handle API. Only both not found gives citation_unresolved. A registered
   DataCite DOI returning Crossref 404 and handle responseCode 1 is resolved.
   A network exception, 429 or 5xx gives citation_unverifiable and refuses
   emission. Evidence sources whose reference parses as DOI are checked.
   Only in-process callers can pass transport. The three shipped CLIs have no
   replay flag, file or environment switch. An exact parser-action/import
   whitelist and environment-access AST check enforce this boundary.
   Only the test module reads GARS_NETWORK_TESTS=1 for the five real/five fake
   live test. Replay fixture provenance distinguishes modeled bodies from
   actual live captures; the current capture limitation is in the change report.
10. Hi-C remains placeholder. No detector is introduced.

### Sealed interface

**The sealed interface (fixed here so the seal can run beside the build).**
`GARS_SEALED_DEFECT_FIXTURES` names a directory holding one subdirectory per plant, named `p01`, `p02`, … (never a descriptive name; review MINOR-4), each with one of three layouts:
- (a) a complete stage-00 project for classes 3–6: `00_data/<assay>/{samples.csv,files.csv,raw/}` and `_config/<assay>.yaml`, exactly as row 1's sealed interface, with the columns of "The schema the detectors read";
- (b) for class 8, `de_results.csv` (the schema `gene,baseMean,log2FoldChange,pvalue,padj`), which the runner places into its own scaffold and grades through the real `collect`;
- (c) for classes 7 and 9, `snapshot.json` in row 7's `claims_export` shape plus a `project/` tree, graded through `emit_report.py`.
- A plant with `class_id: 0` is a sealed **clean** project in layout (a), expected to raise no flag.

Every plant carries `expected.json`: `{"class_id": <0-10>, "expected_flag": "<flag or none>", "expected_stage": "<stage>", "seal_type": "independent_context" | "external_human_seal", "canary": "<32 hex characters>"}`.
The `canary` is a random token the sealer also writes into one data cell the plant's layout carries, where no detector reads it (review NOTE-A): an extra `samples.csv` column named `plant_note` in layout (a) (the open schema, 0043, allows it, and no detector reads that column; never in a sample id, which stage 00 derives from file names); an extra trailing column `plant_note` in `de_results.csv` for layout (b) (the collect gate reads columns by name; Brief A's clean projects include one table with that extra column, proving it changes no verdict); a claim's `text` in `snapshot.json` for layout (c). The runner never prints it; `seal_ops.py complete` copies it once into the manifest, and every later leak count reads the manifest (below).

The runner routes by `class_id`, grades through the stage entry point, and counts a catch only when the named flag appears there.
Output discipline (review MINOR-4), enforced by a test:
- each plant runs in a `try/except`, with the entry point's stdout and stderr captured and discarded;
- a plant that raises is counted `error` (graded, not caught), never skipped;
- it prints only `sealed <id>: <caught>/<planted>` per class, `sealed clean: <flagged>/<n>`, the seal-type counts, `sealed graded <g> of <s> plants seen`, and `row 1 mapped: <m>` / `row 1 unmapped: <u>`;
- a test builds a synthetic sealed folder whose sample ids, file names, folder names and `expected.json` extras all carry a sentinel string, runs the sealed class, and asserts the sentinel appears 0 times in the captured output.

It also accepts row 1's `GARS_SEALED_DESIGN_FIXTURES` (`tests/test_stage01_design.py:8-16` interface), mapping through a committed map that keeps row 1's own `detail_contains` requirement (review MAJOR-5):
- `confounded_condition` → class 1;
- `insufficient_biological_replicates` → class 2;
- `invalid_design` → class 2 **only** when `detail_contains` falls in the group-of-one message family (the runner matches `detail_contains` against the committed family, the literal fragments of the stage 01 messages at `:588-590` and the ATAC floor; for example "cannot be tested for differential expression");
- anything else → `unmapped`: printed on its own line, never counted as caught, and kept out of the catalogue arithmetic, because it is one of row 1's §7.2 checks outside §11.2's ten classes.
A mapped plant is caught only when the stage 01 CLI's failure carries both the reason and `detail_contains`, exactly as `SealedDesignTests` grades it.

**The schema the detectors read (review MAJOR-2).**
It is a contract, not detector rule text.
The same block is copied verbatim into the sealed interface, into `benchmarks/defects/SEALED-INTERFACE.md`, and into the stage 00/01 contracts (`gars/00_initialize_project/CONTEXT.md`, `gars/01_prepare_samplesheets/CONTEXT.md`), so a sealer and a user read the same words.
All columns are optional `samples.csv` columns under the open schema (decision 0043); no config key is added (review MAJOR-9).
- `subject`: the independent biological unit (donor, patient, animal); rows sharing a value are not independent replicates.
- `biological_unit`: a synonym of `subject` kept for row 2's fixtures; when both are present, `subject` wins.
- `cell_barcode`: present only when each row is a single cell (or a cell-level sub-sample); its presence marks the design as cell-level.
- `library_index`: the library's i7 index sequence, or `i7+i5` for dual indexing, in the exact form the CASAVA 1.8 FASTQ header carries after the last `:` (for example `ACGTACGT` or `ACGTACGT+TTGACCAA`); never a library name.
- `sex`: one of `F`, `M`, `unknown` (case-sensitive).
- `age`: age in years, a non-negative number; blank means unknown.

### THREAT MODEL

Covered: a producer or agent session that writes project inputs (samples.csv, FASTQ, config, DE tables, a claims snapshot) and runs the stage helpers, the rnaseq-de verbs and the report preflight; any code path in this repository. It must not be able to:
  - get a planted defect of classes 1-9 past its detector by renaming a column's case, adding whitespace, reordering rows, gzip framing (including a record-truncated FASTQ inside a valid gzip stream, or a plain `.fastq`), or splitting a sample across lanes;
  - emit a report through `emit_report.py` while `evidence_check.py` fails;
  - get a sealed plant's content (a sample id, a path, a table cell) into the sealed runner's output;
  - make a detector read "not checkable" as "clean" in the P(caught) arithmetic, or drop a project from the denominator (graded must equal seen);
  - pass `padj` equal to, or smaller than, `pvalue`, or a `padj` that is not BH of the tested `pvalue`s;
  - cite an evidence file that does not exist, sits outside the project, or has changed since its sha256 was recorded;
  - cite a DOI that no registration agency resolves, or turn a network failure into a pass;
  - count the Hi-C placeholder as caught or remove it from the denominator.
Not covered, named as residual in 0101: a session that edits `_system/` or the catalogue itself (the guard, the owner-side approval and the sealed plants are that line); a correct-looking but scientifically wrong DE model (R-142 calibration is not this row); a real but irrelevant DOI (relevance is the reviewer's, §10); a report emitted by calling `render_report.py` directly, bypassing `emit_report.py` (wiring emission into stage 03 and the pilot flow is not this row's); samples without `library_index` (swap is `not_checkable` there, and the report says so); real patient data (none enters this repo).

## R-042

| Existing behavior changed | New acceptance, red under old behavior |
|---|---|
| Stage 01 extra-column restriction becomes open metadata; column names are trimmed and case-normalized | DevelopmentCatalogueTests.test_case_whitespace_lanes_and_order; unknown plant_note clean fixture |
| Stage 01 sex confounding refusal and imbalance DEGRADE flags | DevelopmentCatalogueTests.test_sex_age_thresholds |
| Stage 01 cell and subject-count refusals | DevelopmentCatalogueTests.test_subject_replication; class 4 development plant |
| Stage 01 index comparison and explicit unavailable result | DevelopmentCatalogueTests.test_not_checkable_is_not_pass; class 5 development plant |
| integrity.check_one full checks plain FASTQ structure | IntegrityRecordTests.test_records_plain_and_gzip; test_stage01_plain_truncation_and_default |
| integrity.check_one full checks gzip-valid record truncation | IntegrityRecordTests.test_records_plain_and_gzip; class 6 development plant |
| rnaseq-de collect requires BH-consistent adjusted p-values | DevelopmentCatalogueTests.test_collect_diagnostic_drift |
| Existing collect-success fixture with one row p=.1, padj=.2 becomes two BH-consistent rows | RnaseqGarsWrapperTests.test_04_de_prepare_and_collect; only the fixture changes, every assertion retained |

The integrity change reaches **stage 01 --verify-integrity full (default none)**
and **stage 00 finalize --integrity full (default quick)**. BASE suite grep found
no stage-00 finalize/full or stage-01 full calls on synthetic FASTQ; no existing
caller's fixture verdict changes. The direct integrity test at
tests/run_tests.py:579 uses whole records and keeps its verdict.
The BASE pvalue,padj sweep found exactly tests/run_tests.py:1019 and :1034.
The anonymous-gene refusal at :1019 remains unchanged. Only the success fixture
at :1034 changes. No other existing test expectation is edited.

## What this does not close

- NOT met: sealed >=9/10 over all ten classes; 0103 is the separate sealer's record.
- NOT met: >=3 external_human_seal plants; public number/date remain unmeasured.
- NOT met: PMID/E-utilities and literature-role typed-tool wiring of R-125.
- NOT met: R-069 artifact liveness beyond claim evidence.
- NOT met: any detector for class 10.
- NOT met: pilot-1 measurement.
- NOT met: report emission wiring into stage 03 or the pilot flow; emission
  other than through emit_report.py is unguarded.
- NOT met: containment of a session editing the system or catalogue, scientific
  model validity (R-142), relevance of a real DOI, and swaps without library_index.
- NOT met: live DOI capture and actual Python 3.6 execution on this host.
- NOT met: step B's data route and backend bench.
- NOT met: protected-change approval (0104), independent review or merge.
  This producer writes neither 0102, 0103 nor 0104 and creates no real sealed plant.

## Test

`python3 tests/test_planted_defects.py`, `python3 gars/tests/test_citation_resolution.py`,
`python3 gars/tests/test_emit_report.py`, `python3 gars/tests/test_integrity_records.py`.
The change report records commands, measured summaries, expectation changes,
baseline red and disposable red-on-fault outcomes. Development plants are
producer-authored, unsealed, generated with seed 801 and pinned by SHA-256.
Sealed-output tests use producer-authored interface controls, never a real seal.
README's evidence number/date remain unmeasured.

## Status

Standing implementation specification, subject to independent review and separate
protected-change approval. This record does not claim row 8's sealed exit.
The response-capture limitation remains a ruling request in the change report.

## Date

2026-09-24

## Addendum — synthetic DOI protocol evidence, 2026-09-24

The response-capture ruling was decided under the owner's standing delegation (23 Sep 2026).
This addendum resolves the ruling request above and in the original change report;
all preceding bytes remain unchanged.

The replay records remain labelled **synthetic protocol fixtures**. They prove
protocol logic only. Replay remains in-process through the `transport=` argument;
no production CLI option, environment variable or file switches to replay.
Class 9's P(caught) from replay is never reported as a live measurement.

**NOT met:** live DOI capture in this step; this host's sandbox has no network.
The live evidence of record is a later networked run of
`GARS_NETWORK_TESTS=1 python3 gars/tests/test_citation_resolution.py` outside
this step, covering the same five real DOIs (including a DataCite DOI) and five
fabricated DOIs. Its record must contain request URL, status and body SHA-256
per DOI. That later record is not this producer's work. No live run or capture
is claimed here, and no sealed or public catch-rate claim is promoted.

## Addendum — review round C2, 2026-09-24

The brief's rulings were decided under the owner's standing delegation (23 Sep 2026).
This addendum implements review findings F2–F8 within the existing schema and
threat model; it does not supply the missing F1 sealing decision. All earlier
bytes remain preserved. Details and measured checks are in
`docs/implementation/row_8_change_report.md`.

DOI tokens are extracted throughout a source reference, including citation prose
and alternative resolver URL spellings. Every extracted token is checked. A DOI
marker with no parseable token refuses as citation_unverifiable. Service lookup,
fallback, transient refusal, parser options, imports and in-process replay stay
unchanged. Replay records remain **synthetic protocol fixtures**, proving protocol
logic only; live DOI capture and live class-9 measurement remain NOT met.

Evidence entries must carry exactly one non-null artifact or source dictionary,
with its matching integer parent ID and a null other parent ID. An artifact needs
a nonblank path and a SHA-256 digest; a source needs a nonblank string reference.
Malformed entries refuse evidence_missing before rendering. Existing path/hash
checks and the row-7 renderer remain unchanged.

Stage 01 validates optional sex and age against the existing schema before the
covariate calculation: sex is F, M or unknown; age is blank or a finite,
non-negative number. Invalid values refuse invalid_design with the column named,
without echoing the value. They never become not_checkable or checked. This uses
an existing failure code and adds no config key, threshold or schema column.

Collect and check-table refuse uncorrected_pvalues when padj is present but pvalue
is missing. The tested-row BH rule and relative 1e-4 tolerance are unchanged.

Class-2 invalid_design credit requires a catalogue group-of-one detail, and
class-3 confounded_condition credit requires the word sex in the same failure.
Row-1 mapped plants must also retain their supplied detail_contains. Sealed
accounting records a terminal verdict (caught, not_caught, clean, flagged,
unmapped or error) before counting a plant as graded. Errors preserve the parsed
class when available and use an unknown class when parsing fails. The printed
line prefixes and arithmetic thresholds are unchanged; graded equals seen is
asserted by the sealed test. Development accounting already counts completed
stage verdicts and retains its graded-equals-seen assertion.

### R-042 — C2 changes and acceptance

| Existing behavior changed | Acceptance red against the starting code, green after repair |
|---|---|
| Stage 01 crashes on nonnumeric age or silently drops invalid sex/nonfinite age | DevelopmentCatalogueTests.test_covariate_schema_refusals; both bulk assays, same JSON refusal contract |
| Collect ignores nonmissing padj with missing pvalue | DevelopmentCatalogueTests.test_collect_diagnostic_drift; real collect and check-table on the same table |
| DOI references in prose or alternative URL forms pass unexamined | EmitReportTests.test_doi_reference_forms; absent/existing output preserved |
| Malformed evidence parents pass preflight | EmitReportTests.test_malformed_evidence; null, empty, ambiguous or inconsistent parents refuse |
| Class-2/3 catch credit lacks the required detail | DevelopmentCatalogueTests.test_class_specific_details and test_sealed_grading_uses_class_details |
| Sealed graded count increments before a verdict | SealedOutputDisciplineTests and test_sealed_grading_uses_class_details assert concrete verdicts and totals |

No existing acceptance expectation is weakened. Tests add adverse inputs and
assertions; the ten committed clean projects and their hashes remain unchanged.

### F1 stop and residuals

NOT met: sealed class-9 measurement on sealer-authored DOIs outside the fixed
replay fixture set. Such a DOI produces citation_unverifiable, not the required
citation_unresolved catch. With Hi-C also not caught, that set cannot reach
9/10. Choosing between plant-supplied recorded responses in layout (c) and a
live sealed class-9 run on a networked host changes the sealed interface or run
contract. That part is stopped and the alternatives are recorded under the last
Owner rulings needed section of the change report. No option is implemented.
All prior residuals remain NOT met, including public sealing, PMID/literature
wiring, stage-03/pilot emission wiring, pilot measurement and protected approval.
