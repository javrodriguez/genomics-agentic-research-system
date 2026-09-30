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

Step 1 (a pre-check with UCSC's reader, run 30 Sep before this build) found that no exact basis reproduces the printed figures: they come from pyBigWig's approximate 10-kb tile mean (`stats(exact=False)`, basis B6), which the pre-registration forbids the instrument to implement.
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
   R5 (the addendum binding) is a test that skips with its reason until the row 3a addendum is in RESULTS.md; its logic runs now on a temporary copy carrying the approved wording.
6. **The regrade**: a new workflow `.github/workflows/geo-recompute.yml` (manual dispatch and a monthly schedule, 90-minute limit) runs the command exactly as printed and writes the report, exit code and wall time to the job summary.
7. **The README** gains one sub-bullet under the RESULTS.md evidence bullet, with no test count. RESULTS.md itself is not edited (lane brief, ruling 5): the plan's "Recompute the deposited half yourself" block is left for the orchestrator.

## The measurement (30 Sep 2026, this lane, on the cloud build machine)

- All four deposits downloaded and hashed: sizes and sha256 equal step1.md's pins.
- The stdlib reader against **libBigWig** (pyBigWig 0.3.26, lane-only), per chromosome on all four real files: records, bases with data, bases above 1 and above 2, NaN, exact 1.0 and 2.0, and 10-kb tiles above 1 and 2 by libBigWig's own exact mean. The per-file comparison and its exact counts are in the lane report.
- Against step 1's UCSC counts: bases 3,095,646,350 in every file, equal. Records: the files hold one item per 10-bp bin (309,564,635 per file, equal in both readers); step 1's 172,425,988 (GSM1415877) is the count of runs after merging abutting items of identical value, which is what UCSC's text dump printed, and the libBigWig reference's merged-run count equals it exactly.
- Two step-1 figures differ from the exact recompute by one rounding step:
  - GSM1420155's B1 z>2 fraction is 620,682 / 309,564,635 bins = 0.0020050…, which is 0.00201 at three figures under any rounding rule; step 1 printed 0.00200. libBigWig counts the same bases. PREREG-2 R3 binds step 1's printed figures; the binding holds this one cell to the recompute's own figure, names it in `STEP1_B1_DIFFERS`, and the report prints the difference. The orchestrator decides whether that needs a PREREG-3.
  - GSM1415877's B4 z>2 fraction is 6,060 / 309,579 tiles = 0.01957; step 1 printed 0.01958 (6,061 tiles). libBigWig's exact tile mean also gives 6,060. Step 1's counter read UCSC's `%g`-rounded text, which step1.md names as a limit. B4 is not bound to step 1's table.
- PREREG-2 R4's B4 ratio range "44-108×" is step 1's 43.5 rounded a second time; the exact lower ratio is 2,435 / 56 = 43.48. The report prints 43.5–108×.

## Rejected alternatives

- **Implementing B6** (pyBigWig's zoom-level approximation) in the stdlib instrument so the printed figures MATCH: PREREG.md P4 forbids it, and PREREG-2 withdrew the ruling that asked for it.
- **Committing the fixtures as binary `.bw` files**: the pre-commit gate refuses binary content it cannot scan; they are committed as hex text and decoded by the tests.
- **Rounding ratios to whole numbers**: it rounds twice and prints 44 for 43.48.
- **Binding the report's RESULTS.md line numbers**: the addendum will insert lines; the quotations are bound by content, exactly once.

## What this does not close

- **The per-library half** (FRiP 0.032, peaks per read, 28.8 M filtered reads, 2.6% duplication, Spearman 0.464) stays quoted; its outputs are not public.
- **The cause of the deposit's outlier**: the command cannot separate a failed IP from GEO's recorded ENCODE input (GSM945855) or the GAIIx 36-bp platform; it prints both as context.
- **The fixtures were written by pyBigWig, not UCSC's tools**: the cloud build machine's egress policy refused hgdownload.soe.ucsc.edu. Regenerating them with `bedGraphToBigWig`/`wigToBigWig` from the committed text sources is open for the orchestrator.
- **R5** runs on the real RESULTS.md only once the addendum lands.
- **NCBI's continued service** and GitHub's 60-day schedule limit.

## Test

`python3 reproduction/gse58638/test_recompute.py` and `python3 reproduction/gse58638/recompute.py --check-published` (CI job `geo-recompute-binding`, ubuntu, macOS and Windows).
The fault that must make them fail: a changed deposit byte or size, a short read, a zero-record file, a moved or duplicated quotation, a planted change to `expected.txt`, a script edit without a re-run, or `MATCH` under IN KIND. The lane's mutation witness (M1-M15 of the plan, plus two plants in the published files) is recorded in 0242 and the lane report.

## Status

Standing.
The implementation and this record are the lane's; the merge and every public push are the orchestrator's and the owner's.

## Date

2026-09-30
