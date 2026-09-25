# Row 10 science review harness — round 1

**Partial implementation; construction and measurement are blocked.** Two
contradictions in the supplied lane contract are reproduced below. No requirement
has been weakened to hide them. This round does not claim the harness complete
or row 10's exit. No model has been run against any case.

The governing scope rulings in record 0135 are **Glitch's decisions under the
owner's standing delegation**, never the owner's words. The producer account is
record 0136. Records 0135 and all base decision records are unchanged; 0137–0139
are reserved and unwritten. No review file was supplied for round 1.

## Delivered and stopped work

| Item | Implemented | Not implemented or not verified |
|---|---|---|
| 2 | Private row 9 imports, same-object contracts, stub audit, both import orders in one interpreter | Two-launcher comparison awaits a science launcher |
| 3 | Exactly ten science classes, definitions, other admitted in findings | P01, P02, C01, C02 and their statistical rationales; no producer or sealed case authored |
| 4–6 | Concrete witness that required manifest bytes fail the required sweep | Bases, complete INTERFACE/layout map, gates and builder; no passing construction or sweep-zero claim |
| 7 | Schema document with only the permitted enum/envelope differences; full remaining-tree drift check | Operational validation adapter, blocked by code-only prompt pin |
| 8 | Resume-only choice recorded from 0135 R10-5a | Launcher, stub two-phase integration, phase-B audit/session/usage-limit acceptance |
| 9 | Imported field matcher, any-of wrapper, path pre-normalisation, repo-prefix rejection, shared alarms and ratios | Scorer, denominator/invalid/repeat/first-run/publication integration |
| 10 | Prompt from the prescribed scientific requirements and case layout | No case execution or prompt tuning |
| 11 | Existing release script rendered DoD; no evidence values promoted | Science run reader awaits an operational run-file producer |
| 12 | Independent contract module and seven mutation controls | Remaining builder, gate, adapter, launcher, scoring and masking integration requirements |
| 13 | Count claims updated from suite collection; short DEVELOPMENT paragraph | Mode A and macOS remeasurement unavailable |

The blocked construction includes its case publication and sealer handoff. A
partial handoff without fixed base trees and verified gate integration is not
represented as the standalone INTERFACE that a sealer may rely on. Empty sealed
slots are recorded in SEALS.md. No C03 or other reserved case is supplied.

The schema inherits row 9's title and prompt_path pin unchanged, as the exact
drift contract requires. Its phases use JSON Schema cardinality and prefixItems
for exactly A then B and A-only notes_sha256; row 9's limited validator does not
implement those array keywords. A future authorized adapter must enforce the
phase shape as well as its science validity rules. The present schema document
is not claimed to establish operational science-record acceptance.

No existing test, guard or red-on-fault entry changed. No existing expectation
was made wrong by this change, so there are no old/new expectation rows to report.
The README evidence row is unchanged. The DoD renderer produced unchanged bytes.

## Verification

Python is 3.13.5; evaluation checks use a runtime newer than 3.9. No network,
remote, push, pull request, merge or approval is performed. Scratch logs and
disposable copies use the scratch twin. For nested subprocesses, its environment
value must be resolved at runtime, keeping relative literals in commands:

```sh
row10_scratch="$(realpath ../gars-row-10-scratch)"
export TMPDIR="$row10_scratch" TEMP="$row10_scratch" TMP="$row10_scratch"
```

Mode C unsets TMPDIR while keeping TEMP and TMP set to that folder.
The first mode-B attempt used a relative TMPDIR. The existing lifecycle fault
runner changes its child process working directory, and its support module
assigns that relative value directly to tempfile.tempdir. Child temporary-folder
creation then raised FileNotFoundError instead of reaching the expected mutation
assertion. Its superseded full-suite summary was:

```text
Ran 694 tests in 482.341s
FAILED (failures=59, skipped=79)
```

No test was changed to repair this setup error. With runtime-resolved scratch,
`python3 gars/tests/test_lifecycle_faults.py` confirmed the correction:

```text
Ran 1 test in 18.207s
OK
```

Final full-suite results, with the scratch folder resolved at runtime:

| Command and mode | Verbatim summary |
|---|---|
| `python3 tests/run_tests.py`, B: TMPDIR, TEMP and TMP set | `Ran 694 tests in 565.300s`; `OK (skipped=79)` |
| `python3 tests/run_tests.py`, C: TMPDIR unset, TEMP and TMP set | `Ran 694 tests in 559.056s`; `OK (skipped=106)` |

The other required summaries are:

| Command | Verbatim summary |
|---|---|
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 694 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 37.925s`; `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` |
| `python3 tests/test_bio_faults_core.py` | `Ran 12 tests in 0.053s`; `OK`; `wall time: 0.101 s; exit 0` |
| `python3 tests/test_bio_faults_faults.py` | `Ran 1 test in 0.719s`; `OK`; `wall time: 0.748 s; exit 0` |
| Python grammar check | `Python feature_version=(3, 6): 4/4 new Python files parse` |

Both new modules are below 120 seconds individually in mode B. Seven science
mutation witnesses printed `science fault red:` after unchanged controls passed.
The initial count check correctly refused the old 681 claims; the documents
were updated to the loader's 694 without changing the checker.

The generated reviewer row reads exactly:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository pre-commit hook was invoked on the staged additions:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 363/363 resolve
pre-commit: REFUSED
hook exit: 1
```

The secret scan is NOT verified; no scanner was installed, substituted or bypassed.
The required manual hook check remains refused. Scope verification found no
out-of-lane tracked changes and confirmed every base decision record's bytes.

The builder invocation was attempted with repository defaults and an output in
scratch; Python exited 2 because bio_build_cases.py is not implemented. Case
count, per-case gates and sweep hits are **not measured**, not zero. There are
no new fixtures over which to claim a fixture secret scan. The repository hook
was separately attempted on the staged additions; its result is recorded above.

Mode A needs Docker, which this account cannot reach. Native Python 3.6,
macOS cold-clone execution, cluster execution, deployment sandbox efficacy,
independent scientific audit, protected approval and merge-result CI remain
unverified. Science measurement, sealed slots and repeat remain later work.

## Owner rulings needed

1. **Code-only prompt path in the inherited schema (item 7).**
   `evals/review-faults/schema/review_record.schema.json` pins
   `envelope.reviewer.prompt_path` to
   `gars/_references/prompts/review_faults_code.md`. The specified science
   path is rejected by row 9's validate, and item 7 permits no change to this
   enum. Even rewriting only the adapter's view to the code path would fail
   row 9's prompt-path comparison against the required science manifest.
   `ContractTests.test_prompt_schema_conflict_witness` reproduces this.
   Options: (a) authorize the additional science schema enum change and an
   explicit prompt-path adapter rule that verifies science path/hash before
   projecting both record and manifest to the code path; (b) change row 9's
   code-only schema pin in a separate authorized lane, then inherit that
   revised contract without restating its validity rules. Record validity,
   launch, scoring and their release integration are stopped pending this
   choice, as item 7 explicitly directs.

2. **Required manifest bytes fail the literal sweep (item 6).**
   The required key `harness_commit` contains `harness`; the required science
   prompt path contains `fault`. Both are case-sensitive substrings forbidden
   in every public manifest byte. These are added manifest bytes, not unchanged
   base lines; no row 9 item-15 exemption resolves it.
   `ContractTests.test_manifest_sweep_conflict_witness` reproduces both hits.
   Options: (a) authorize narrowly named exemptions for these fixed,
   case-independent manifest key/value bytes, with every case-derived byte
   still swept; (b) revise the manifest field/path contract so the public
   manifest can avoid those tokens. Construction and the dependent case/base
   handoff are stopped; no exemption, encoding trick or weakened sweep is used.


## Rulings round R1

R1 and R2 are glitch-09's rulings, **Glitch under the owner's standing delegation
of 23 Sep 2026**, never the owner's words. They settle the two questions in the
preceding round-1 section. There is no review to answer. The surrounding work is
implemented; the old stopped-work account above remains historical and unchanged.

**Round invocation compliance: FAILED.** Three commands used literal rooted
null-device redirects: the initial workspace check, a hook-location inspection,
and the manual fixture-hook invocation. These breached the explicit relative-path
command rule. Passing functional checks and later correct invocations cannot
undo that breach. No command-path compliance is claimed for this round.

| Head item | Changed files | Test | Result | Red-on-fault seen | How |
|---|---|---|---|---|---|
| 1, records | 0136 addendum, regenerated decision index, this appended report; allowed paths only | scope/prefix audit | pass | no | Existing decision bytes and this report's prior bytes retained |
| 2, reuse | bio_common.py and the six added science modules | core same-object and both-order one-process tests; pipeline audit identity | pass | yes | Reimplemented ratio and a bare-name science module each turn the named control red |
| 3, cases | classes unchanged; fixtures/P01, P02, C01, C02 | closed vocabulary; all four built cases | pass | no | Only the four authorized public ids exist; no reserved case is supplied |
| 4, bases | bio_generate_base.py | bases and independently recomputed BH; deterministic construction | pass | no | Three ids/seeds, copied generator primitives with source-line citations; no benchmark import |
| 5, handoff | INTERFACE.md, SEALS.md | sealed appendix byte inclusion; generated trees and layout inspection | pass | no | Appendix copied verbatim; complete classes, bases, map, gates, matching and fingerprint command; reserved slots empty |
| 6, builder and R2 | bio_build_cases.py, bio_gates.py | every named gate refusal, quiet output, bytes/stats, all builder refusals, exact sweep exemptions | pass | yes | Answer entry, salt, mtime, refusal, omitted verify/token gates and substring exemption mutations all go red |
| 7, adapter and R1 | bio_review_record.py, schema, README schema comment | schema drift, pure projection, three-way path check, envelope-fault drift and phase rules | pass | yes | Skipping science equality and accepting the code path each fail a named test |
| 8, launch | bio_run_reviews.py | runtime two-phase stub, own session audits, uid/root refusal, usage limit, only, no overwrite | pass | yes | Narrative in A, ignored B hit, model envelope, missing uid check and wrong audit session each go red |
| 9, oracle and score | bio_oracle.py, bio_score.py | any-of grid, prefix drift, invalid denominators, sealed 2/5, tampering, first-run/repeat and masked publication | pass | yes | Class/file/tolerance/severity, repo prefix, invalid caught, first-run, threshold and mask mutations all go red |
| 10, instructions | existing science prompt unchanged | core prompt contract | pass | no | No model run or prompt tuning; first measured run remains later |
| 11, release | reviewer_measurement in scripts/release_check.py; regenerated dod_current.md | code-output pin and science file reader | pass | yes, through scorer | Science remains development/partial and never completes the threshold; mutation printing met goes red |
| 12, acceptance | test_bio_faults_core.py, test_bio_faults_pipeline.py, test_bio_faults_faults.py | direct modules and full suite | pass | yes | 25 separate mutations; each unchanged control green before its named red witness |
| 13, usage/counts | README.md count only; DEVELOPMENT.md count and science paragraph | loader/check_counts and B/C runs | pass | no | 721 collected; 79 B skips, 106 C skips; no new science skips |

### Statistical rationales — public producer cases only

P01 changes only the processing-run assignments in provenance.csv: all three A
libraries share one processing run and all three B libraries share another.
The samples table still has six independent biological sources and balanced
sequencing batches, and the fitted condition-only indicator matrix has full
rank. The upstream processing effect is nevertheless inseparable from condition.
A condition contrast cannot identify a biological condition effect separately
from that processing effect; rank alone does not establish identifiability of
the scientific contrast. The processing assignments, condition labels and
analysis plan are all in the case. The design detector does not consume this
separate library-origin table. No sample, result p-value, approval or report
number is edited. This is one batch-confounded contrast, not a gate-breaking
invalid matrix or a numerical reporting discrepancy.

P02 changes only biological-source assignments in provenance.csv: three A
libraries are aliquots of one donor, and three B libraries are aliquots of a
second donor. Six library/sample rows therefore represent two biological units,
with one unit per condition. The differential analysis treats those six rows as
independent, permuting library observations across all 20 three-versus-three
assignments. Technical aliquots do not supply independent biological replication;
those permutations cannot support biological condition inference. The source
mapping and independent-sample method are visible inside the case, while the
stage-01 table has distinct library ids and lacks the repeated subject column
that its detector consumes. The inferential error is pseudoreplication; the BH
arithmetic and reported numerical results remain unchanged and internally
consistent with the stated, inappropriate library-level analysis.

These rationales occur only in this change report, never in copied case bytes.
C01 is the unmodified RNA base; C02 is the unmodified ATAC base. They have six
independent sources, balanced processing, no exclusions, exact two-sided
permutation p-values, BH over the tested rows, matching evidence hashes and a
qualified descriptive claim. ATAC consensus/blacklist/global-scaling assumptions
and QC metadata are stated. Count summaries are explicitly illustrative; tiny
FASTQs are integrity inputs, not claimed sources of those count summaries.
The cases do not claim a real pipeline or experimental execution.

### Gate and launch limits

All nine named gates run on disposable copies. Stage 01, wrapper collectors,
row-8 evidence emission and row-7 rendering are imported production functions.
The group/replicate check reads the count matrix, differential-table sample
columns and normalized table using wrapperlib's token function. Stage 03 runs
its real verify against supplied historical approval data and a scratch
protected store, at the recorded execution-finish time. Actor/path bindings and
synthetic content-execution sidecars are local scaffold data; the original
approval hash/timestamp/expiry are preserved. No approval command or real job
runs. Missing/unreadable inputs yield named refusals and a private key/log.
These checks establish content-gate behaviour, not production execution evidence.

The launcher implements resume only. A is launch-owned; B's id is read from
B's stream and used for B's audit. Session equality and narrative withholding
are code-stamped. Runtime stubs exercise this path; actual Claude resume,
sandbox enforcement and CP5.6 deployment rehearsal remain unverified. The
oracle rejects leftover dot prefixes as well as repo prefixes so the imported
normalizer cannot silently widen a science match.

### Verification

All temporary data and logs are in the scratch twin. B sets TMPDIR, TEMP and
TMP to its runtime-resolved location. C unsets TMPDIR and leaves TEMP/TMP there.
Full B/C suites started before the final narrow oracle/absent-input hardening;
after those edits all science tests were rerun directly in B and together in C.
No test count or non-science implementation changed in those final corrections.
The full-run and final targeted summaries below are kept distinct.

| Command | Verbatim summary |
|---|---|
| `python3 tests/run_tests.py (B)` | `FAILED COLLECT nfcore-atacseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-atacseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-chipseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-chipseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-cutandrun-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-cutandrun-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-methylseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-methylseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT rnaseq-de local: group 15 present; prepare keys unchanged`; `FAILED COLLECT rnaseq-de slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-rnaseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-rnaseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT scrna-qc-cluster local: group 15 present; prepare keys unchanged`; `FAILED COLLECT scrna-qc-cluster slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-scrnaseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-scrnaseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT spatial-cluster-count local: group 15 present; prepare keys unchanged`; `FAILED COLLECT spatial-cluster-count slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-spatialvi-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-spatialvi-wrapper slurm: group 15 present; prepare keys unchanged`; `Ran 721 tests in 515.475s`; `OK (skipped=79)` |
| `python3 tests/run_tests.py (C)` | `FAILED COLLECT nfcore-atacseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-atacseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-chipseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-chipseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-cutandrun-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-cutandrun-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-methylseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-methylseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT rnaseq-de local: group 15 present; prepare keys unchanged`; `FAILED COLLECT rnaseq-de slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-rnaseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-rnaseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT scrna-qc-cluster local: group 15 present; prepare keys unchanged`; `FAILED COLLECT scrna-qc-cluster slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-scrnaseq-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-scrnaseq-wrapper slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT spatial-cluster-count local: group 15 present; prepare keys unchanged`; `FAILED COLLECT spatial-cluster-count slurm: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-spatialvi-wrapper local: group 15 present; prepare keys unchanged`; `FAILED COLLECT nfcore-spatialvi-wrapper slurm: group 15 present; prepare keys unchanged`; `Ran 721 tests in 516.305s`; `OK (skipped=106)` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` |
| `python3 tests/check_counts.py` | `suite: 721 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 39.109s`; `OK` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` |
| `tests/test_bio_faults_core.py` | `Ran 12 tests in 0.122s`; `OK`; `wall time: 0.159 s; exit 0` |
| `tests/test_bio_faults_faults.py` | `Ran 1 test in 14.806s`; `OK`; `wall time: 14.835 s; exit 0` |
| `tests/test_bio_faults_pipeline.py` | `Ran 27 tests in 5.692s`; `OK`; `wall time: 5.761 s; exit 0` |
| `grammar` | `Python feature_version=(3, 6): 11/11 Python files parse` |
| `python3 -m unittest discover -s tests -p 'test_bio_faults_*.py' (final C)` | `Ran 40 tests in 20.536s`; `OK` |
| `bio_build_cases.py (repository fixtures)` | `cases 4; sweep hits 0` |

All three new test modules are under 120 seconds alone in mode B. The final
fault module observed all 25 named mutations red, each after a green control.

The build log reports the following private gate results; sweep hits are zero:

```text
C01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
C02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
```

The generated reviewer row remains:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository hook was run over the staged new fixtures:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 363/363 resolve
pre-commit: REFUSED
hook exit: 1
```

The secret scan is NOT verified: gitleaks is absent. No scanner was installed,
substituted or bypassed. The manual hook remains refused. The README evidence
row is unchanged; the release renderer leaves the reviewer cell unmeasured.
The cold-clone Linux skip figure remains 106. The existing macOS figure of 75
was not remeasured; no science test introduces a skip.

Scope verification preserves every base decision record and 0135, checks 0136
and this report as byte-prefix append-only, and permits only the lane's listed
paths. The three command-path breaches above remain an explicit failure of
invocation discipline despite that file-scope result. The index was regenerated.
No reserved record was written, no model was run, and no network, push, remote,
merge, pull request or self-approval operation was performed.

Mode A needs Docker, which this account cannot reach. Native Python 3.6, macOS
cold-clone execution, live scheduler/analysis execution, deployment sandbox and
real resume, independent honesty audit, protected approval, sealed slots,
measured first run and repeat, and merge-result CI remain unverified. The full
science threshold is always NOT met for this partial set; row 10's exit is not
claimed. Record 0137 belongs to Glitch's later delegated merge approval.

## Owner rulings needed

None.

## Review round R2 fixes

2026-09-25. The review's F1–F6 are addressed below; F7–F12 are answered or
fixed. The additional R1/R2, scope-of-stop, F1 and F5 rulings are **Glitch's
rulings under the owner's standing delegation of 23 Sep 2026**, never the
owner's words. Earlier sections remain historical, byte-identical prefixes.

| Finding | Changed files | Test | Result; red-on-fault seen and how |
|---|---|---|---|
| F1 MAJOR | bio_generate_base.py, INTERFACE.md, four expected.json seeds | test_student_reference_and_analysis; test_bases_and_bh; all case gates | PASS; yes: halving the Student tail fails the independent reference-value test |
| F2 MINOR | bio_build_cases.py; pipeline/fault tests | test_build_from_outside_repository | PASS; yes: restoring caller-cwd git lookup fails the named test |
| F3 MINOR | bio_gates.py; pipeline/fault tests | test_each_gate_refuses, including arm-separated age | PASS; yes: ignoring design flags fails the covariate_imbalance assertion |
| F4 MINOR | bio_generate_base.py; private seeds and INTERFACE.md; pipeline/fault tests | test_base_identity_not_visible | PASS; yes: restoring params.seed fails the case-byte test |
| F5 MINOR | bio_review_record.py, bio_score.py; pipeline/fault tests | test_phase_b_session_audit; test_resume_id_differs_count | PASS; yes: either restoring invalidation or dropping the count line fails the named count test |
| F6 MINOR | test_bio_faults_faults.py | test_one_process_both_import_orders | PASS; yes: live renamed-module shim reaches the named FAIL, with no import ERROR |
| F7 NOTE | 0136 addendum | same-object, stub-stream and phase-B call-site tests | Answered: direct comparison reduces to (a); yes for the distinct call site: B audited with A's id fails |
| F8 NOTE | bio_build_cases.py; pipeline test | test_refusals_and_quiet | PASS; private key/log retained and no public manifest; no new mutation specifically targets publication timing |
| F9 NOTE | bio_run_reviews.py; pipeline test | test_phase_a_created_report_recorded | PASS; all ids receive INVALID records, named reason retained, B unstarted; no dedicated mutation |
| F10 NOTE | pipeline test; 0136 addendum | test_group_rep_collector_drift | PASS; intact and missing-token inputs agree with the real ATAC collector; existing omitted-token-gate mutation remains red |
| F11 NOTE | 0136 addendum; this report | append-only and scope audit | PASS; pipeline test path named here and in 0136, required R2 heading used; no mutation |
| F12 NOTE | no identity/config change | no fix requested | Answered: configured commit identity retained; no mutation |

### Statistical rationales against the R2 bases

Each base has 240 features drawn from a gamma-Poisson negative binomial with
variance mean + 0.015 × mean². Baselines are lognormal with log location
log(120) and log standard deviation 0.8. Library exposures are
0.75, 1.2, 0.9, 1.1, 0.8 and 1.3; 24 seeded features carry balanced positive
and negative log2 effects with absolute sizes between 1 and 3. These are
synthetic analysis inputs, not evidence of a real experiment or pipeline run.
The base ids stay fixed; INTERFACE.md lists new long fixed seeds so the literal
identity check is not confused by an ordinary small integer count. Seed keys,
base ids and complete seed strings are absent from every built case byte.
No draw is selected by a measured reviewer, and no prompt tuning occurs.

The plan specifies median-of-ratios factors over features with all positive
counts, log2(normalised count + 1), independent two-sample pooled-variance
Student t-tests with df = 4, and BH over all 240 tests at alpha 0.05. The
reported log2 effect is the difference in mean transformed abundance, as the
plan states. A standard-library incomplete beta calculation gives the two-sided
tail; an independent df=4 formula and the 2.776/8.61 reference values pin it.
Tests recompute the factors, statistic, tail, BH, directions and claim counts.
Unlike the old discrete permutation test, this pre-specified test can reject
at the stated alpha with three versus three.

C01 (RNA) has 22 significant features: 12 higher and 10 lower in B. C02
(ATAC) has 21: 12 higher and 9 lower. The other RNA base has 24: 12 higher
and 12 lower. These are computed results, not required catch-rate thresholds.
Both clean cases retain six independent biological sources and balanced
processing assignments. Their rendered claims report the computed counts and
directions, descriptive association, and n = 3 per group limitations. RNA QC
contains mapping, assigned-read and strandedness information; ATAC QC contains
FRiP, TSS enrichment and fragment periodicity, with consensus/blacklist/global
scaling assumptions in its plan. Neither case carries the old illustrative
count disclaimer or any causal conclusion.

P01 changes only processing_run in provenance.csv: all A libraries use one
processing run and all B libraries another. The condition-only fitted matrix
remains full rank, but a condition effect cannot be separated from processing.
The pooled t-test compares transformed group means without estimating the
confounded processing contribution; the 22 reported associations therefore
cannot identify a biological condition contrast independently of that run
assignment. This is one batch-confounded contrast, visible from the plan,
conditions and library provenance together. Results, report numbers, approval
and samples remain unchanged; no gate-breaking design mutation is introduced.

P02 changes only biological_source in provenance.csv: three A libraries are
aliquots of one donor and three B libraries aliquots of another. The pooled
t-test still estimates within-group variance from aliquot-to-aliquot variation,
divides it as though each group had three independent biological replicates,
and uses df = 4. Biological replication is actually one donor per condition;
there is no estimable between-donor residual variance for a biological
condition comparison. Counting aliquots as independent understates that
uncertainty and gives the 24 reported significant features unjustified
biological inference. The numerical t/BH calculation is unchanged and internally
consistent with the inappropriate declared library-level test. The single
scientific flaw is pseudoreplication, detectable from the source mapping and
plan; it is not an added p-value or report-integrity discrepancy.

Both provenance-only diffs were re-derived against the new bases and are
byte-identical to their prior patch files. Only P01, P02, C01 and C02 are
published. These rationales occur only in this report, never in copied case
bytes. Independent scientific honesty review remains later work.

### Verification

Final direct checks use runtime-resolved scratch for TMPDIR, TEMP and TMP.
Mode C unsets only TMPDIR. The initial targeted pipeline probe supplied
relative temporary-directory values: its outside-cwd child could not resolve
those values and fell back to the system temporary folder. That breached the
scratch-containment rule; later correct verification does not undo it. The
first targeted pipeline run also exposed a test-only exclusive-create mistake
when replacing a synthetic record; it was fixed before the final checks.

| Command | Verbatim summary |
|---|---|
| `python3 tests/test_bio_faults_core.py` | `Ran 12 tests in 0.126s`; `OK`; `wall time: 0.161 s; exit 0` |
| `python3 tests/test_bio_faults_pipeline.py` | `Ran 33 tests in 12.448s`; `OK`; `wall time: 12.516 s; exit 0` |
| `python3 tests/test_bio_faults_faults.py` | `Ran 1 test in 29.424s`; `OK`; `wall time: 29.452 s; exit 0` |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.`; `wall time: 0.017 s; exit 0` |
| `python3 tests/check_counts.py` | `suite: 727 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite`; `wall time: 0.177 s; exit 0` |
| `python3 evals/test_harness.py` | `Ran 44 tests in 38.980s`; `OK`; `wall time: 39.015 s; exit 0` |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1`; `wall time: 0.206 s; exit 0` |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13`; `wall time: 0.021 s; exit 0` |
| Python 3.6 grammar | `Python feature_version=(3, 6): 11/11 Python files parse` |
| bio_build_cases.py, repository fixtures | `cases 4; sweep hits 0` |

Every new test module is under 120 seconds alone in mode B. All 31 isolated
mutations went red after their unchanged controls passed. The generated
builder log contains:

```text
C01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
C02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
sweep hits 0
```

The release script regenerated this reviewer row (the README evidence row was
not edited):

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository pre-commit hook ran with the four changed fixture definitions
staged, without a bypass or scanner substitution:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 365/365 resolve
pre-commit: REFUSED
hook exit: 1
```

The secret scan remains unverified because gitleaks is absent.

Full mode B: `Ran 727 tests in 536.662s`; `OK (skipped=79)`.

Full mode C: `Ran 727 tests in 571.252s`; `OK (skipped=106)`.

The earlier targeted pipeline probe was superseded: `Ran 33 tests in 15.011s`;
`FAILED (errors=1)` from the test-only record replacement noted above. The first
mutation probe printed `Ran 1 test in 44.579s`; `OK`. The final direct results
in the table and final full B/C summaries are the acceptance evidence.
The full runners' `FAILED COLLECT ... group 15 present; prepare keys unchanged`
lines are successful negative controls from test_manifest_groups.py: each
removes a required output and asserts the collector refuses with failure
provenance intact. They are not unittest failures.

The suite loader and count checker agree on 727 tests. README.md and
DEVELOPMENT.md count claims now match. No science test skips. The Linux
cold-clone figure remains 106; the existing macOS figure of 75 was not
remeasured. The release renderer made no evidence promotion. The code-half
release output remains pinned by the unchanged regression.

Scope checks preserve every existing decision record, including 0135, and
verify 0136 and this report as byte-prefix additions. The index was regenerated.
The supplied review remains untracked and unchanged. No reserved record,
protected approval, sealed case, measured run, network operation, push, remote,
merge or pull request was produced. The commit uses the configured identity
and a scratch message file, with explicit path-limited staging.

Residual gaps: mode A needs Docker, which this account cannot reach. Gitleaks
and therefore the fixture secret scan remain unverified. Native Python 3.6
execution, macOS cold-clone execution, live analysis/scheduler execution,
deployment sandbox behavior and actual Claude resume, independent scientific
honesty audit, delegated protected approval, sealed slots, measured first run
and repeat, and merge-result CI remain unverified. The initial scratch-containment
breach remains a round invocation failure. Row 10's exit and the full science
threshold are not claimed.

F1–F6 closed by fixes; F7–F12 fixed or explicitly answered; no finding waits
on an owner ruling.

## Owner rulings needed

None.

## Review round S1 fixes

2026-09-25. This answers the supplied round-R2 review. The continuation guidance
and lane rulings are **Glitch under the owner's standing delegation of
23 Sep 2026**, never the owner's words. Earlier report and decision bytes remain
unchanged. Option (ii) is implemented: analysis begins with counts, with no raw
reads. No in-scope planted class requires raw reads, so option (i) is not used.

| Finding | Changed files | Test | Result; red-on-fault seen and how |
|---|---|---|---|
| F1 MAJOR | bio_generate_base.py, bio_gates.py, INTERFACE.md, P01/P02 expected.json, pipeline/fault tests | test_count_inputs_consistent; test_each_gate_refuses; test_student_reference_and_analysis; four-case build | PASS; yes: inventing measured RNA QC or dropping count integrity fails the named consistency test after a green control |
| F2 MAJOR | bio_generate_base.py; pipeline/fault tests; INTERFACE.md; 0136 addendum | test_base_fingerprints; test_determinism_stats_neutral; test_bases_and_bh | PASS on Python 3.13.5; yes: restoring built-in floating sum or dropping fixed formatting fails the fingerprint test; other interpreters/platforms remain unverified |
| F3 MINOR | bio_score.py; pipeline/fault tests | test_resume_id_differs_count | PASS; yes: counting unstarted B fails the extended test; also checks missing-init, 0/0, disagreement staying valid and the printed count |
| F4 NOTE | bio_generate_base.py; INTERFACE.md; pipeline/fault tests | test_atac_peak_coordinates | PASS; yes: restoring abutting single-chromosome tiles fails the named coordinate test |
| F5 NOTE | append-only 0136 and this report | no repository fix requested | Answered: the prior round's disclosed scratch-containment breach remains a process fact; no mutation applies |

### Statistical rationales against the S1 bases

The three fixed seeds still draw 240 negative-binomial features, dispersion
0.015, skewed lognormal baselines, differing library exposures and 24 effects
of absolute log2 size 1–3 in both directions. All six libraries are retained.
Each library's count export exactly matches its matrix column, its read_count
is the sum over the supplied features, and its SHA-256 is verifiable locally.
No file claims that these are total sequencing depths. There are no raw reads,
real-experiment claims or measured upstream QC values. Analysis begins at the
count matrix; unavailable RNA or ATAC read-level QC is explicitly DEGRADE,
with the resulting limitation next to the report claim. This removes the
contradiction identified by F1 without manufacturing sequencing evidence.

Median-of-ratios normalization, log2(normalized count + 1), pooled two-sided
Student t with df = 4, and BH over 240 tests at alpha 0.05 remain pre-specified
and recomputed. C01 has 22 significant features, 12 higher and 10 lower in B;
C02 has 21, 12 higher and 9 lower. Both have six independent donors and balanced
processing assignments. Their reports state descriptive association, n = 3
per group, unavailable upstream QC and the global-scaling limitation. The
ATAC feature universe now has seeded widths and gaps across three chromosomes;
its counts and test statistics retain the same draws. These clean analyses
make claims only about the supplied count evidence.

P01 changes only processing_run in provenance.csv: all A libraries share one
run and all B libraries another. The condition-only matrix is full rank,
but the contrast cannot separate a condition effect from the processing effect.
The t-test compares group means without estimating that inseparable processing
contribution. Its 22 numerical discoveries cannot identify a biological
condition contrast independently of run. The plan, conditions and origin table
expose this one batch-confounded contrast. No count, QC value, result, approval
or rendered number is altered by the patch.

P02 changes only biological_source in provenance.csv: the three A libraries
are aliquots of one donor, and the three B libraries aliquots of another.
The pooled t-test uses aliquot-level variance and df = 4 as though there were
three independent biological replicates per group. There is actually one donor
per condition and no estimable between-donor residual variance for the
biological contrast. Treating the aliquots as independent understates that
uncertainty, giving the 24 significant features unjustified biological
inference. This is one pseudoreplication error, visible from the plan and source
mapping, with the numerical computation and report internally consistent.

Both patches were re-derived with difflib against the S1 bases and matched
their existing plant.diff bytes exactly. The expanded plan moved the method
match ranges from lines 7–11 to 12–16; expected.json is updated accordingly.
The provenance ranges remain 2–7. No extra case or planted class is authored.
These rationales are confined to this report; independent honesty audit remains
later work.

### Reproducibility and gate scope

The generator uses math.fsum for floating reductions, twelve significant digits
for numeric CSV values, and UTF-8/LF for every base file. test_base_fingerprints
pins all three tree hashes recorded in the S1 addendum to 0136, using the sorted
(relative path, file SHA-256) compact-JSON hash. Python 3.13.5 produced these
hashes repeatedly. No different Python interpreter is available here, so
3.6–3.12 and cross-platform byte equality have not been verified. Grammar
compatibility is reported separately below.

Stage 01's unchanged real checker receives the case design/config and a scratch
registration view with the count registry's sample ids and empty FASTQ fields.
There are no asserted raw paths or manufactured reads. The imported integrity
checker processes the actual supplied count artifacts; catalogue_integrity also
checks library checksums, totals and matrix-column agreement. Every previously
named gate still runs. Raw-read-specific checks have no applicable raw files.
Existing wrapper/approval execution scaffolds are content-check data, never
claims of a real run. Missing, corrupted or contradictory count artifacts
refuse. Gate refusal, import drift, fixed stats, visibility and oracle tests
remain intact.

### Verification

All final runs resolve the scratch twin for TMPDIR, TEMP and TMP before running
children. Mode C unsets TMPDIR only. No model, network, remote, push, merge or
pull request ran. The direct modules ran individually in mode B; each is under
120 seconds. All 37 mutations went red after unchanged green controls, including
six added for S1. No existing guard, threshold or test assertion was weakened.
The first pipeline probe had two failures in newly added assertions: rendered
Markdown escapes were not decoded, and the expected 0/0 line omitted its ratio.
Those test-only expectations were corrected to assert the complete rendered
content and the existing formatter contract. Its superseded summary was
`Ran 36 tests in 11.462s`; `FAILED (failures=2)`. The targeted correction printed
`Ran 2 tests in 1.160s`; `OK`. Final acceptance results follow.

The first full mode-B run printed `Ran 730 tests in 538.231s`;
`FAILED (failures=1, skipped=79)`. Its sole failure was the unchanged
ExecutionPolicyTests.test_prepared_local_failure_refuses_unclassified_retry:
the local executor returned FAILED instead of FAILED:EXIT_17. An unchanged
isolated rerun printed `Ran 1 test in 0.074s`; `OK`. No system code or test
was edited to obtain that result. The final full rerun is recorded below;
the earlier failure remains disclosed.

| Command | Verbatim summary | Wall time |
|---|---|---|
| `python3 tests/run_tests.py (B, final rerun)` | `Ran 730 tests in 538.191s`; `OK (skipped=79)` | 538.398 s |
| `python3 tests/run_tests.py (C)` | `Ran 730 tests in 558.161s`; `OK (skipped=106)` | 558.356 s |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | 0.017 s |
| `python3 tests/check_counts.py` | `suite: 730 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | 0.180 s |
| `python3 evals/test_harness.py` | `Ran 44 tests in 38.522s`; `OK` | 38.556 s |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | 0.210 s |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` | 0.021 s |
| `python3 tests/test_bio_faults_core.py` | `Ran 12 tests in 0.119s`; `OK` | 0.155 s |
| `python3 tests/test_bio_faults_pipeline.py` | `Ran 36 tests in 11.978s`; `OK` | 12.050 s |
| `python3 tests/test_bio_faults_faults.py` | `Ran 1 test in 31.892s`; `OK` | 31.921 s |
| `python3 evals/bio-faults/bio_build_cases.py (repository fixtures)` | `cases 4; sweep hits 0` | 0.474 s |
| Python 3.6 grammar | `Python feature_version=(3, 6): 11/11 Python files parse` | n/a |

The initial narrow generator probe printed `Ran 3 tests in 0.917s`; `OK`.
The preliminary mutation probe printed `Ran 1 test in 31.906s`; `OK`, with all
37 red witnesses. Final direct module results above supersede these probes.
The full runners' FAILED COLLECT messages are intentional negative controls
from test_manifest_groups.py; the unittest summary determines suite success.
The actual initial B unittest failure is separately disclosed above.

The builder emitted `cases 4; sweep hits 0`. Its private log records:

```text
C01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
C02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
sweep hits 0
```

The release script regenerated this reviewer row; the README evidence row was
not edited:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository pre-commit hook ran with P01/P02 fixture changes staged:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 365/365 resolve
pre-commit: REFUSED
hook exit: 1
```

Gitleaks is absent, so the hook refused and the secret scan is unverified.
No scanner was installed, substituted or bypassed. The citation check passed.
The suite and count checker agree on 730 tests; README.md and DEVELOPMENT.md
match. Mode B has 79 environment skips, mode C 106, and no science test skips.
The Linux cold-clone skip figure remains 106. The existing macOS figure of
75 is unchanged and was not remeasured. The decision index was regenerated;
the append-only addition does not change its generated table.

Scope/prefix checks preserve all earlier decision records, including 0135,
and preserve the prior bytes of 0136 and this report. The supplied R2 review
remains unchanged and untracked; the pre-existing R1 review is left unread,
unchanged and untracked. The science prompt is unchanged. No reserved decision
or seal is written. Staging names only allowed paths, and the single round
commit uses the configured identity and the scratch message file.

Residual gaps: mode A needs Docker, which this account cannot reach. Gitleaks,
native Python 3.6–3.12, cross-platform base hashes, macOS cold-clone execution,
live analysis/scheduler execution, deployment sandbox efficacy and actual
Claude resume, independent honesty audit, protected approval, sealed slots,
measured first run and repeat, and merge-result CI remain unverified. The first
B execution-policy failure remains an observed transient failure in unchanged
code; no cause or system fix is claimed. The prior round's scratch-containment
breach remains disclosed. Row 10's exit and the full science threshold are not
claimed.

F1–F4 are closed by implementation and named regression/mutation tests; F5 is
answered as a retained process fact. No finding waits on an owner ruling.

## Owner rulings needed

None.

## Review round T1 fixes

2026-09-25. This answers the supplied S1 review. The continuation-T ruling is
**Glitch under the owner's standing delegation of 23 Sep 2026**, as coordinator,
never the owner's words. This round is a continuation beyond the lane's stop
rule of at most one continuation, ruled to protect the clean half of the
measurement. Its implementation scope is S1 NOTE F2 only.

| Finding | Changed files | Test | Result; red-on-fault seen: yes/no, how |
|---|---|---|---|
| S1 F1 NOTE | 0136 addendum and this report; no numerical change | BuildTests.test_base_fingerprints before editing and after the QC-only hash update | PASS on Linux / Python 3.13.5; no new mutation for platform libm variation; existing floating-sum and formatting mutations remain red. Residual retained because the Linux pin passes and the review requires no fix in that case. |
| S1 F2 NOTE | evals/bio-faults/bio_generate_base.py; tests/test_bio_faults_pipeline.py; tests/test_bio_faults_faults.py; 0136 addendum; README.md and DEVELOPMENT.md counts | BuildTests.test_single_qc_disposition_matches_report; BuildTests.test_base_fingerprints; FaultTests.test_faults; four-case build | PASS; yes: restoring the second QC disposition in a disposable copy makes the named disposition test fail after its unchanged control passes. |

Each base's qc.md now has exactly one QC disposition, DEGRADE, equal to its
rendered report's QC summary. The n = 3 per group sentence remains verbatim
apart from its label becoming Limitation. Comparing every file generated by
the previous and current generators found only qc.md changed, and only that
label, in all three bases. The new tree hashes are recorded in 0136's T1
addendum and pinned in test_base_fingerprints. The pre-edit Linux fingerprint
check printed `Ran 1 test in 0.085s`; `OK`. The initial post-edit targeted check
printed `Ran 2 tests in 0.509s`; `OK`.

P01, P02, C01 and C02 retain the S1 flaws and statistical rationales above.
No analysis, input count, result, claim, plan, approval or provenance was
re-derived. Both provenance-only plant.diff files and every expected.json
remain byte-identical; no fixture diff needs a moved-line adjustment.
The science prompt is unchanged and no model has run against any case.

**Round invocation compliance: FAILED.** The first command mistakenly used a
rooted null-device redirect. This breached the explicit command-path rule.
Passing checks and subsequent relative commands do not erase that failure.
TMPDIR, TEMP and TMP were set before that command; later commands resolve the
scratch twin at runtime before children run. Mode C unsets TMPDIR only.

### Verification

| Command | Verbatim summary | Wall time |
|---|---|---|
| `python3 tests/run_tests.py (B)` | `Ran 731 tests in 539.032s`; `OK (skipped=79)` | wall time: 539.237 s; exit 0 |
| `python3 tests/run_tests.py (C)` | `Ran 731 tests in 554.056s`; `OK (skipped=106)` | wall time: 554.264 s; exit 0 |
| `python3 tests/check_contracts.py` | `14 contracts clean: sections, wait points, vocabulary.` | wall time: 0.018 s; exit 0 |
| `python3 tests/check_counts.py` | `suite: 731 tests, from unittest's loader`; `enforced=3`; `clean — every current claim matches the suite` | wall time: 0.173 s; exit 0 |
| `python3 evals/test_harness.py` | `Ran 44 tests in 39.322s`; `OK` | wall time: 39.355 s; exit 0 |
| `python3 evals/check_results.py --controls --lexicon` | `clean — graded=1` | wall time: 0.219 s; exit 0 |
| `python3 scripts/release_check.py` | `DoD cells regenerated: 13/13` | wall time: 0.023 s; exit 0 |
| `python3 tests/test_bio_faults_core.py` | `Ran 12 tests in 0.123s`; `OK` | wall time: 0.158 s; exit 0 |
| `python3 tests/test_bio_faults_pipeline.py` | `Ran 37 tests in 12.405s`; `OK` | wall time: 12.475 s; exit 0 |
| `python3 tests/test_bio_faults_faults.py` | `Ran 1 test in 32.910s`; `OK` | wall time: 32.938 s; exit 0 |
| Python 3.6 grammar | `Python feature_version=(3, 6): 11/11 Python files parse` | n/a |
| bio_build_cases.py, repository fixtures | `cases 4; sweep hits 0` | n/a |

Each science module ran alone in mode B and took under 120 seconds. All 38
mutations went red after unchanged green controls, including the restored
second-disposition mutation. No test, gate or threshold was weakened.
The full runners' FAILED COLLECT lines and embedded mutation FAIL witnesses
are expected negative controls; both final unittest summaries are green.

The builder's private log records:

```text
C01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
C02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P01: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
P02: catalogue_evidence=pass, catalogue_integrity=pass, catalogue_probabilities=pass, count_matrix_header=pass, de_identifiers=pass, group_rep_presence=pass, render_report=pass, stage01_design=pass, stage03_verify=pass
sweep hits 0
```

The release renderer produced this reviewer row, without changing the README
evidence row:

```text
| reviewer catch rate (code; science) | `evals/review-faults/`, `evals/bio-faults/` runners | ≥ 8/10 per set, ≤ 1/5 false alarms; first-run-at-sha reported (§21 Q3) | unmeasured |
```

The repository pre-commit hook was invoked with a disposable scratch index
based on the pre-lane tree and explicit staging of the four public fixture
additions. This exercises the requested fixture check without changing the
real index or any fixture byte:

```text
gitleaks: REFUSED (gitleaks absent from PATH)
citations: 363/363 resolve
pre-commit: REFUSED
hook exit: 1
```

Gitleaks is absent, so the hook refused and the fixture secret scan is not
verified. No scanner or hook was installed, substituted or bypassed.
README.md and DEVELOPMENT.md now match the 731-test loader count. Mode B has
79 environment skips and mode C has 106, with no science test skips. The Linux
cold-clone skip figure remains 106; the existing macOS figure of 75 is unchanged
and was not remeasured here. The decision index and DoD table were regenerated
by their scripts and remain byte-identical.

The supplied S1 review stays untracked and unchanged; the pre-existing R1 and
R2 reviews remain unread, unchanged and untracked. Scope and prefix checks
preserve every prior decision record, including 0135, and every earlier byte
of 0136 and this report. Only permitted paths are staged for one round commit,
using the configured identity and a scratch message file. No reserved record,
protected approval, sealed slot, model run, prompt tuning, network operation,
push, remote, merge or pull request is produced.

Residual gaps: mode A needs Docker, which this account cannot reach. Gitleaks
and the fixture secret scan, native Python 3.6 execution, cross-platform libm
byte equality for the new hashes, macOS cold-clone execution, real scheduler
and analysis execution, deployment sandbox efficacy and actual Claude resume,
independent scientific honesty audit, delegated protected approval, sealed
slots, measured first run and repeat, and merge-result CI remain unverified.
The initial command-path breach remains a round invocation failure. Row 10's
exit and the full science threshold are not claimed.

S1 F2 is closed by the fix and its regression/mutation tests; S1 F1 is answered
with the Linux fingerprint evidence and its residual retained. No finding
waits on an owner ruling.

## Owner rulings needed

None.
