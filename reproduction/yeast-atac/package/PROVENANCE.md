# Provenance

## Labels

Every value in this package's tables carries one of six labels:
- `recorded at run`: a field of a run record, named; only these are the run's attestation.
- `computed at harvest`: hashed on the run's machine from the unmasked file, after the run and before teardown.
- `supplied at packaging from <source>`: read from a named file at a pinned commit (`<repository>@<commit>:<path>`), or from a lane file shipped in this package.
- `computed at packaging from <source>`: derived when the package was rendered: a normalised form of a recorded output from harvested bytes whose sha256 equals the record, or a recorded value whose path was replaced by the re-run's own folder.
- `not recorded by the run`: the run record lacks the field; nothing fills it.
- `withheld`: a recorded sha256 this package does not print (see "Hash oracle").

## Masked values

Absolute paths, storage buckets and account ids are replaced; the originals are not in this package.

| Placeholder | Spans replaced |
|---|---|
| `<WORKSPACE>` | 2 |

Two further rewrites keep a re-run's inputs and outputs in its own folder: each input path in the shipped samplesheet becomes `<INPUTS>/<file name>`, and each path a parameter held becomes a path under `<RERUN>` (params/params.tsv labels each such value `computed at packaging`).

## Hash oracle

A sha256 of a run record holding a masked value would let anyone confirm a guessed user name, path or bucket, so this package prints no such hash; the fields below are cited by name only and are not checkable from the package.
Output sha256 values are printed, since the comparison needs them, with three exceptions: no `presence` member's sha256 is printed (it compares no hash), no directory output's tree hash is printed when it holds a withheld member, and render refuses to print the sha256 of an output whose bytes hold a bucket, an account id, the approver or a user name.
A result table holding only a path is left out of outputs/small/ (named under "Result tables not shipped"), but its sha256 is still printed: a path is not one of the values that check refuses.
submit.sh is not shipped: no run record binds its bytes. code/<stage>/commands.sh, the recorded submission line, is.
Limit: GARS records no sha256 of submit.sh. On the run's machine, harvest compared the launch line Nextflow itself logged (run/.nextflow.log) with the nextflow run line in submit.sh and refused on any difference; the rest of submit.sh (its environment lines) is bound by nothing.

- atacseq_bulk.01_nfcore-atacseq-wrapper: `outputs: run/results/multiqc/narrow_peak/multiqc_report.html sha256`, not printed: the file holds a run bucket name and an account id; presence compares no hash.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `outputs: the sha256 of 54 presence member(s)`, not printed: presence compares no hash, so none is published; each row reads withheld.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `command.sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `config_sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `samplesheet_sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `idempotency_key`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `design_check.sha256`, not printed: the file it hashes is not in this package.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `execution_config[executor_descriptor]`, not printed: executor descriptor values beyond the backend name never ship.
- The sweep is armed with every user name the run's records carry, except stock cloud logins, which name no person: `root`, the user the SSM agent's environment reports on the pad; `ubuntu`, the stock login of the launch pad's Ubuntu cloud image.

## Not recorded

- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:INPUT_CHECK:SAMPLESHEET_CHECK: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:CUSTOM_GETCHROMSIZES: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:GET_AUTOSOMES: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:GTF2BED: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:BWA_INDEX: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:GENOME_BLACKLIST_REGIONS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_FASTQC_UMITOOLS_TRIMGALORE:FASTQC: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_FASTQC_UMITOOLS_TRIMGALORE:TRIMGALORE: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PREPARE_GENOME:TSS_EXTRACT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BWA_MEM: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_INDEX: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PICARD_MERGESAMFILES_LIBRARY: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_IDXSTATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_FLAGSTAT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_STATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_MARKDUPLICATES_PICARD:PICARD_MARKDUPLICATES: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_MARKDUPLICATES_PICARD:SAMTOOLS_INDEX: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAMTOOLS_FILTER: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_IDXSTATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_FLAGSTAT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_STATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:SAMTOOLS_SORT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_REMOVE_ORPHANS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_SORT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_SORT_STATS_SAMTOOLS:SAMTOOLS_INDEX: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:PICARD_MERGESAMFILES_REPLICATE: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_PICARD_COLLECTMULTIPLEMETRICS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_MARKDUPLICATES_PICARD:PICARD_MARKDUPLICATES: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:MACS2_CALLPEAK: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_DEEPTOOLS_PLOTFINGERPRINT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_STATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_IDXSTATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_FILTER_BAM:BAM_SORT_STATS_SAMTOOLS:BAM_STATS_SAMTOOLS:SAMTOOLS_FLAGSTAT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:FRIP_SCORE: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_MARKDUPLICATES_PICARD:SAMTOOLS_INDEX: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:MACS2_CALLPEAK: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_ATAQV_ATAQV: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BAM_TO_BIGWIG:BEDTOOLS_GENOMECOV: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:FRIP_SCORE: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:PLOT_MACS2_QC: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CONSENSUS_PEAKS:MACS2_CONSENSUS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:MULTIQC_CUSTOM_PEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BAM_TO_BIGWIG:UCSC_BEDGRAPHTOBIGWIG: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_ATAQV_MKARV: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CALL_ANNOTATE_PEAKS:PLOT_HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_IDXSTATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_FLAGSTAT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:PLOT_MACS2_QC: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_MARKDUPLICATES_PICARD:BAM_STATS_SAMTOOLS:SAMTOOLS_STATS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CONSENSUS_PEAKS:SUBREAD_FEATURECOUNTS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CONSENSUS_PEAKS:MACS2_CONSENSUS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CONSENSUS_PEAKS:HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:MULTIQC_CUSTOM_PEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BIGWIG_PLOT_DEEPTOOLS:DEEPTOOLS_COMPUTEMATRIX_REFERENCE_POINT: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BIGWIG_PLOT_DEEPTOOLS:DEEPTOOLS_COMPUTEMATRIX_SCALE_REGIONS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_BAM_TO_BIGWIG:BEDTOOLS_GENOMECOV: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CONSENSUS_PEAKS:HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CONSENSUS_PEAKS:SUBREAD_FEATURECOUNTS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BIGWIG_PLOT_DEEPTOOLS:DEEPTOOLS_PLOTHEATMAP: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_CONSENSUS_PEAKS:DESEQ2_QC: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CALL_ANNOTATE_PEAKS:PLOT_HOMER_ANNOTATEPEAKS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_BAM_TO_BIGWIG:UCSC_BEDGRAPHTOBIGWIG: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_LIBRARY_BIGWIG_PLOT_DEEPTOOLS:DEEPTOOLS_PLOTPROFILE: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:IGV: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MERGED_REPLICATE_CONSENSUS_PEAKS:DESEQ2_QC: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:CUSTOM_DUMPSOFTWAREVERSIONS: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MULTIQC: not recorded by the run.
- every stage: the input files' checksums and URLs (G5): not recorded by the run.
- every stage: the timezone of the trace timestamps.

## Gaps

- G1: container images are pinned by the tag the trace recorded; no digest was recorded at run, and none is resolved here.
- G4: the run's records hold absolute paths; the package masks them (above).
- G5: no run record holds an input URL or an input FASTQ checksum; inputs/inputs.tsv labels each value it carries.

## Comparison modes and tolerance entries

Every member is compared `exact` unless an entry below declares another mode with a cause read from its bytes (decision 0283).

- entries of origin `S2b-preregistered`: 10
- entries of origin `pass-1`: 0

The declared modes (each applies only to the file kinds named here):
- `presence`: the file exists and is not empty; counted as P, never as a match. For PDF, SVG, zip, gzip and R data files, and MultiQC outputs.
- `sorted_table`: a text file's lines, less the lines its entry's listed patterns drop, sorted, then compared exactly.
- `column_matched_table`: a featureCounts table compared exactly after its columns are matched by name; its `#` comment lines (featureCounts' program and command line) are dropped first.
- `sign_aligned_numeric`: a PCA table's numbers compared per sample after each component's sign is aligned, every value within 1e-9 (absolute); its header row and `#` comment lines are not compared.
A normalised match is reported as `match after <mode>`, apart from a byte-identical `match`.
A file a re-run holds inside a recorded directory output that the run did not record counts that output as differing (F).

- atacseq_bulk.01_nfcore-atacseq-wrapper, 34 members, mode `presence`, origin `S2b-preregistered`: each PDF embeds its own creation time: the two runs' files are byte-identical once /CreationDate and /ModDate are blanked (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; every one of these 34 PDFs compared equal with its dates blanked).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 1 members, mode `presence`, origin `S2b-preregistered`: the DESeq2 plots draw the PCA, whose component sign is arbitrary, with samples in completion order; besides its dates the PDF differs in the plotted coordinates (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; the PCA table itself matches under sign_aligned_numeric).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 16 members, mode `presence`, origin `S2b-preregistered`: gzip files (some named .tab) whose header carries the write time, and whose rows come in completion order: decompressed, the two runs hold the same lines (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; each decompressed pair compared equal as content or as sorted lines).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 3 members, mode `presence`, origin `S2b-preregistered`: serialized R (DESeq2) objects built from the counts table, whose sample columns come in completion order; the objects' bytes differ with that order (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; the counts table they are built from matches under column_matched_table).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 1 members, mode `presence`, origin `S2b-preregistered`: the MultiQC report embeds its generation time and the run's launch folder (4 occurrences), so it differs between any two runs (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; names.tsv counts the launch folder in the report 4 times).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 9 members, mode `sorted_table`, origin `S2b-preregistered`: the same lines in a different order: rows are written as parallel tasks finish (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; equal as sorted lines (the four computeMatrix.vals.mat.tab, over 5 MB, checked on the pad before down)).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 24 members, mode `sorted_table`, origin `S2b-preregistered`: Picard writes its start time in a "# Started on:" header line (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; equal once that one line is dropped).
  - a line matching `^# Started on: ` is dropped before the comparison.
- atacseq_bulk.01_nfcore-atacseq-wrapper, 4 members, mode `sorted_table`, origin `S2b-preregistered`: ataqv writes its run time in one "timestamp" field (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; equal once that one line is dropped (exactly one line in each file)).
  - a line matching `^\s*"timestamp": "[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z",?$` is dropped before the comparison.
- atacseq_bulk.01_nfcore-atacseq-wrapper, 2 members, mode `column_matched_table`, origin `S2b-preregistered`: featureCounts orders its sample columns as the BAM files arrive; the counts are identical once columns are matched by sample name (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; equal under column_matched_table).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 2 members, mode `sign_aligned_numeric`, origin `S2b-preregistered`: DESeq2 PCA: samples in completion order, a principal component's sign is arbitrary, and the last float digits vary (about 1e-15) (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; equal per sample after per-component sign alignment, every |difference| at most 1e-9).

## Findings

Outputs that differ between two runs of the same code on the same machine type, for a reason no comparison mode declares; each counts as differing (F).

- atacseq_bulk.01_nfcore-atacseq-wrapper, 6 members: nf-core/atacseq 2.1.2's HOMER peak annotation is not deterministic: for a peak equally near two genes it names one or the other between runs (for example YOL103W-A or YOL103W-B), because genome/genes.bed lists tied genes in a different order each run (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; every differing line is such a tie, and genome/genes.bed differs only in the order of rows with equal coordinates).
- atacseq_bulk.01_nfcore-atacseq-wrapper, 2 members: the DESeq2 sample-distance tables hold the same distances with samples in completion order; no comparison mode is declared for them (decision 0283), so they count as differing (evidence: S2b probe, 5 Oct 2026: plain nf-core/atacseq 2.1.2 (1a1dbe52) run twice on one fresh m5.xlarge pad (lifetime 4, i-0521feb575ad6ee3d), local executor in Docker, the recorded clamp; results tarball sha256 919a275be40cff204bd7376ed0c0b2d927efbb175abea1cc985980db9daf4bb0; the same pairwise distances, rows and columns permuted).

## Result tables not shipped

- none.

## Environment

- env/gars-bio.pins.txt is the pip pin list at the GARS commit, with no hashes; it is not the run's recorded environment.
- env/rerun.config pins each process to the image tag the run recorded, on 4 CPUs and the run's own resource clamp; the original ran on AWS Batch, so a re-run here is cross-platform.

## Sources

- code/, env/containers.tsv, params/, outputs/outputs.tsv, records/: read from the run's manifests; records/ carries only the allowlisted fields (agent_model, backend, containers, data_class, execution, execution_config, failure_class, gars_commit, model_steps, outputs, pipeline_commit, predicate_facts, purpose, random_seeds, reference, software_versions, template_version, threads, venue, workflow_name, workflow_version, wrapper), masked, with the hashes named above withheld.
- inputs/inputs.tsv: checksums computed at harvest; URLs from inputs/lane-sources.tsv.
- inputs/reference.tsv: checksums recorded at run; URLs from inputs/lane-sources.tsv.
- METHODS.md: the GARS Methods renderer of the render's checkout (code/GARS.txt), run over the same records.
- code/GARS.txt: the harvest record (the package_run.py checkout and the clone status).
