---
date: 2026-09-30
status: standing
kind: decision
touches:
  - reproduction/gse58638/
  - .github/workflows/ci.yml
  - .github/workflows/geo-recompute.yml
  - README.md
symptoms:
  - RESULTS.md row 3a's deposit-side figures ("0.0073 of bins above z>1 against 0.053–0.083", "40–100× below them at z>2") came from a 29 Aug analysis whose code and binning were never recorded
  - a stranger cannot re-derive any digit of the failed-replicate finding from the authors' public deposit
---
# The GSE58638 deposit recompute: one standard-library command, bound to RESULTS.md by tests

Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 and within glitch-14's lane brief and plan for the recompute (30 September 2026); no sentence in this record is the owner's.
The pre-registration is `reproduction/gse58638/PREREG.md` (frozen before any deposit byte was read, sha256 `1f1a9d59…`), the step-1 verdict is `VERDICT-step1.md`, and the binding under that verdict is `PREREG-2.md`, the orchestrator's dated rule; all three ship beside the script, byte-identical.
[0242](0242-gse58638-recompute-0241-delegated-approval-of-protected-change.md) approves the protected CI change; this record does not write it.

## Context

RESULTS.md row 3a identifies a failed immunoprecipitation (`GSM1420155`) from two halves: our pipeline's per-library QC (FRiP 0.032 and peaks per read), and the authors' own deposited z-score track, which the row says is an outlier: "0.0073 of bins above z>1 against 0.053–0.083 for the others, and **40–100× below them at z>2**".
The per-library half came from outputs on a cluster scratch that is gone and is not public.
The deposit half is public: four bigWigs in GEO GSE58638, 8,827,241,525 bytes.
The 29 Aug analysis that produced the deposit figures is unrecorded.

Step 1 (a pre-check with UCSC's reader, run 30 Sep before this build) found that no exact basis reproduces both printed figures: T1 ("0.0073 … 0.053–0.083") reproduces exactly only under pyBigWig's approximate 10-kb tile mean (`stats(exact=False)`, basis B6), which the pre-registration forbids the instrument to implement; T2 ("40–100×") also reproduces under the exact tile mean B4. That B6 was the 29 Aug method is an identification after the fact, not a record.
The verdict is therefore **IN KIND, adopted basis B1** (10-bp bins, base-weighted), and PREREG-2 fixes what the binding asserts under it.

## Decision

1. **A new folder `reproduction/gse58638/`** beside `evals/`: `recompute.py` (standard library only, Python 3.9 or later), `test_recompute.py`, `fixtures/`, `expected.txt` (written only by the script), `PREREG.md`, `PREREG-2.md`, `VERDICT-step1.md`, and a folder `.gitattributes` holding every text file at LF.
   `tests/run_tests.py` does not discover it, so the suite count and the count guard do not move.
2. **The command.** `python3 reproduction/gse58638/recompute.py` fetches small public metadata first (SRA run info, GEO brief records), then streams each deposit once over HTTPS, resuming with a `Range` request from the exact byte reached (at most five attempts), hashing every byte and parsing every data block as it arrives; nothing is stored.
   Per file it counts records, bases with data, bases strictly above z>1 and z>2 on the stored float32, NaN, ±inf, values exactly 1.0 and 2.0, spans that are not a multiple of 10, and 10-kb tiles whose exact mean over bases with data is above 1 and 2 (compared exactly: `math.fsum` of exact products, with exact rationals on a tie).
   It checks the data section ends exactly at the index offset with the header's block count, and grades against seen: the bases counted must equal the header's `basesCovered`.
   `--from DIR` reads local copies with the same checks; `--check-published` is the network-free binding.
3. **Exit codes.** 0 identical and matching; 1 a science difference (a deposit's size or sha256 changed, a quotation moved, the report differs from `expected.txt`), named; 2 refused (short read, bad format, zero records, the network on the deposits); 3 only a public-metadata context line changed or could not be fetched, labelled as leaving the science unaffected.
4. **The report** prints B1 (adopted) and B4 (the nearest exact basis, PREREG-2 R4) per deposit, the exact counts, the four sha256, graded against seen, and against RESULTS.md: `IN KIND`, never `MATCH` (PREREG-2 R1); P6 stated with its measured ratios and said plainly not to be met under B1 (R2); line 73 on B4 as context, never a gate (R4); and what is not recomputed.
   Ratios print at three significant figures, step 1's precision, not rounded again to whole numbers.
5. **The binding** (`--check-published`, run by CI on every push, and `PublishedBindingTests`): `expected.txt` names the committed script's git blob and is exactly what that script renders from the counts it records; the three quotations (T1, T2, C1) are each found in RESULTS.md exactly once, read as UTF-8; the relation printed is `IN KIND`; and PREREG-2 R3: GSM1420155 alone is lowest at z>1 and z>2 under B1, and the B1 fractions and ratios equal step 1's at their printed precision, with one named exception (below).
   The exact counts and the four sha256 in `expected.txt` (`COUNTS_SHA256`) and its public-metadata section (`METADATA_SHA256`) are pinned in the script, so a hand edit to either, even one re-rendered consistently, fails on push.
   R5 (the addendum binding) finds the addendum by its dated heading or by its content, requires it to state the reversal itself (the healthy HCT116 figure above DKO1's, the direction holding only when GSM1420155 is counted), accepts line 73's figures only inside their quotations, and requires every other decimal in it to be the bound B4 figure or a metadata figure the report prints; until it is found the test skips with its reason, and only while RESULTS.md is byte-identical to 37a8d94 (`RESULTS_MD_SHA256`): any other RESULTS.md without a detected addendum fails. Its logic runs now on a temporary copy carrying the approved wording.
6. **The regrade**: a new workflow `.github/workflows/geo-recompute.yml` (manual dispatch and a monthly schedule, 90-minute limit) runs the command exactly as printed and writes the report, exit code and wall time to the job summary.
7. **The README** gains one sub-bullet under the RESULTS.md evidence bullet, with no test count. RESULTS.md itself is not edited (lane brief, ruling 5): the plan's "Recompute the deposited half yourself" block is left for the orchestrator.

## The measurement (30 Sep 2026, this lane, on the cloud build machine)

**Inputs.** All four deposits downloaded from NCBI in 1 min 53 s and hashed: sizes and sha256 equal step1.md's pins.

**The reader against libBigWig** (pyBigWig 0.3.26, lane-only), per chromosome on all four real files: records, bases with data, bases above 1 and above 2 on each of 24 chromosomes, the file totals (also NaN, exact 1.0 and 2.0, spans not a multiple of 10), and the 10-kb tiles above 1 and 2 by libBigWig's own exact mean, `stats(type="mean", exact=True)`.

| Deposit | Comparisons | Differ | Records (both readers) | Bases (= header basesCovered) | Tiles with data / z>1 / z>2 (both) | libBigWig merged runs | step 1 UCSC records |
|---|---|---|---|---|---|---|---|
| GSM1415877 | 107 | 0 | 309,564,635 | 3,095,646,350 | 309,579 / 25,575 / 6,060 | 172,425,988 | 172,425,988 |
| GSM1420155 | 107 | 0 | 309,564,635 | 3,095,646,350 | 309,579 / 2,299 / 56 | 203,452,785 | 203,452,785 |
| GSM1415885 | 107 | 0 | 309,564,635 | 3,095,646,350 | 309,579 / 16,409 / 2,435 | 170,336,815 | 170,336,815 |
| GSM1420162 | 107 | 0 | 309,564,635 | 3,095,646,350 | 309,579 / 25,510 / 5,660 | 189,358,563 | 189,358,563 |

The files hold one item per 10-bp bin. Step 1's record counts are the number of runs after abutting items of identical value are merged: libBigWig's merged-run count equals them exactly in all four files, and bases equal step 1's 3,095,646,350.
No tile mean lies within 1e-6 of 1 or 2 in libBigWig's computation.

**Against UCSC's own reader: not done here.** The build machine's egress policy refused hgdownload.soe.ucsc.edu, so threat-model property (e), "the reader equals UCSC's reference reader on the fixtures and on the four real files", is **open**: the reader equals an independent C reader (libBigWig), and its merged-run counts reproduce UCSC's record counts, but no UCSC run was compared with it.

**Against step 1's printed figures**, two cells differ; both are consistent with step 1 printing the exact count rounded twice, first to one more figure and then half-even (review r3).
- **GSM1420155's B1 z>2 fraction** is 620,682 / 309,564,635 bins = 0.0020050159, which is 0.00201 at three figures under a single rounding; step 1 printed 0.00200, which is 0.002005 rounded half-even. libBigWig counts the same bases, and no GSM1420155 bin lies in (2, 2.00005]. PREREG-2 R3 binds step 1's printed figures; this one cell is held to the recompute's own figure (`STEP1_B1_DIFFERS`), printed in the report as a difference, and **awaits a PREREG-3**: asked in the lane session, the orchestrator chose this named exception over a binding that fails until PREREG-3 exists. It is not a ruling under R6.
- **GSM1415877's B4 z>2 fraction** is 6,060 / 309,579 tiles = 0.019574971…, which is 0.01957 under a single rounding; step 1 printed 0.01958. That is consistent with 0.019575 rounded again, or with a count of 6,061 from the one GSM1415877 tile step 1 recorded within 1e-5 of a threshold on `%g`-printed values; step 1's exact counts (`analysis.txt`) would settle it. libBigWig's exact tile mean gives 6,060. B4 is not bound to step 1's table.

PREREG-2 R4's B4 ratio range "44-108×" is step 1's 43.5 rounded a second time; the exact lower ratio is 2,435 / 56 = 43.48. The report prints 43.5–108×.

**The run behind the committed `expected.txt`** (review r5, F-3): `expected.txt` was deleted and re-written by `python3 reproduction/gse58638/recompute.py --from lane-work/data` at the script blob it names, `88584b1260f40d755ca071457532555a80505845` (commit `1e4b817`), 30 Sep 18:30-18:42 UTC, stderr `total 723.8 s`; every earlier review round likewise re-wrote it by a full run, so between rounds only its blob line changed, because the counts did not. Then the README's command, `python3 reproduction/gse58638/recompute.py`, ran in a fresh `--no-local` clone of `1e4b817`, streaming the four deposits from NCBI (757.3 s), and printed `Identical to reproduction/gse58638/expected.txt: yes` (exit 0).

**Run times** (4 vCPU cloud machine, Python 3.11): `--from` 727-797 s for the four files; the streamed run 755 s (8,827,241,525 bytes; about 11.7 MB/s, parse-bound). The fixture tests also pass under Python 3.9.23.

**The mutation witness** (lane-only harness; each mutant a fresh copy whose `expected.txt` names the mutant's own blob, so only behaviour can kill it; the unplanted copy passes every named test):

| Plant | Killed by |
|---|---|
| M1 `>=` for `>` | `CountTests.test_thresholds_are_strict` |
| M2 records weighted instead of bases | `CountTests.test_counts_are_base_weighted` |
| M3 the last block of a file skipped | `ReaderTests.test_bedgraph_fixture_equals_text_source` |
| M4 a short read accepted | `StreamTests.test_short_read_refuses_exit_2` |
| M5 the sha256 check disabled | `StreamTests.test_sha_mismatch_exits_1_naming_file` |
| M6 round-half-even | `RoundingTests.test_round_half_up_on_exact_rational_boundary` |
| M7 the binding compares a constant instead of parsing RESULTS.md | `QuotationTests.test_changed_figure_in_results_md_fails` |
| M8 a quotation accepted when found twice | `QuotationTests.test_quotation_found_twice_fails` |
| M9 a zero-record file passes (the empty file is then still refused by the index-offset check; the test requires the refusal to name zero records) | `ReaderTests.test_zero_records_refuses_exit_2` |
| M10 exit 0 on a report difference | `ReportTests.test_report_difference_exits_1` |
| M11 resume re-feeds overlapping bytes | `StreamTests.test_stream_resumes_after_drop` |
| M12 a chromosome silently dropped | `CountTests.test_graded_against_seen_matches_header` |
| M13 `MATCH` printed under IN KIND | `ReportTests.test_report_says_in_kind_never_match` |
| M14 a metadata-only change exits 1 instead of 3 | `ReportTests.test_metadata_only_change_exits_3` |
| M15 RESULTS.md read in the platform encoding | `QuotationTests.test_results_md_read_as_utf8` |
| M16 the header basesCovered comparison disabled | `RefusalTests.test_header_bases_covered_mismatch_refuses` |
| M17 the record order and bounds check disabled | `RefusalTests.test_out_of_order_record_refuses` |
| E1 one count digit changed in `expected.txt` | `PublishedBindingTests.test_results_md_figures_equal_the_recompute` |
| E2 RESULTS.md's 0.0073 changed | the same |
| E3 a metadata line changed in `expected.txt` | the same |
| M18 the counts pin disabled (a consistent re-rendered forgery then passes) | `PublishedBindingTests.test_consistent_forgery_of_the_counts_fails` |

21 of 21 killed.

## Rejected alternatives

- **Implementing B6** (pyBigWig's zoom-level approximation) in the stdlib instrument so the printed figures MATCH: PREREG.md P4 forbids it, and PREREG-2 withdrew the ruling that asked for it.
- **Committing the fixtures as binary `.bw` files**: the pre-commit gate refuses binary content it cannot scan; they are committed as hex text and decoded by the tests.
- **Rounding ratios to whole numbers**: it rounds twice and prints 44 for 43.48.
- **Binding the report's RESULTS.md line numbers**: the addendum will insert lines; the quotations are bound by content, exactly once.

## What this does not close

- **The per-library half** (FRiP 0.032, peaks per read, 28.8 M filtered reads, 2.6% duplication, Spearman 0.464) stays quoted; its outputs are not public.
- **The cause of the deposit's outlier**: the command cannot separate a failed IP from GEO's recorded ENCODE input (GSM945855) or the GAIIx 36-bp platform; it prints both as context.
- **Agreement with UCSC's reader** (threat-model property (e)): the fixtures were written by pyBigWig, and the real files were compared with libBigWig, because the cloud build machine's egress policy refused hgdownload.soe.ucsc.edu. Running `bigWigToBedGraph` on the four files, and regenerating the fixtures with `bedGraphToBigWig`/`wigToBigWig` from the committed text sources, is open for the orchestrator.
- **The one step-1 cell that differs** (GSM1420155's B1 z>2: step 1 printed 0.00200, the same count rounded twice) is bound to the recompute's own figure and awaits a PREREG-3.
- **The approved addendum's wording mixes bases**: "0.083 against DKO1's 0.067" sets the B4 figure against line 73's B6 figure (B4's DKO1 mean is 0.068). The binding accepts 0.067 there as a line-73 figure, as R5 reads it; the sentence is the owner's to revisit.
- **R5** runs on the real RESULTS.md only once the addendum lands.
- **The counts are bound to the deposit bytes only by a real run.** On push, the counts are pinned in the script (`COUNTS_SHA256`), so they cannot change without a script edit; but a changed reader that left the pinned counts in place would pass on push, and only `geo-recompute.yml` (or any stranger's run) re-derives the counts from the bytes.
- **NCBI's continued service** and GitHub's 60-day schedule limit.

## Test

`python3 reproduction/gse58638/test_recompute.py` and `python3 reproduction/gse58638/recompute.py --check-published` (CI job `geo-recompute-binding`, ubuntu, macOS and Windows).
The fault that must make them fail: a changed deposit byte or size, a short read, a zero-record file, a moved or duplicated quotation, a planted change to `expected.txt` (counts, metadata or rendering), a script edit that `expected.txt` does not name, or `MATCH` under IN KIND. Whether a real re-run happened is confirmed only by the regrade workflow or a stranger's run, never on push. The mutation witness above (the plan's M1-M15, three more from review, and three plants in the published files) is the evidence each named test can fail.

## Status

Standing.
The implementation and this record are the lane's; the merge and every public push are the orchestrator's and the owner's.

## Date

2026-09-30
