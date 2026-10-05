# Provenance

## Labels

Every value in this package's tables carries one of three labels:
- `recorded at run`: a field of a run record, named; only these are the run's attestation.
- `computed at harvest`: hashed on the run's machine from the unmasked file, after the run and before teardown.
- `supplied at packaging from <repository>@<commit>:<path>`: read from a named file at a pinned commit.

## Masked values

Absolute paths, storage buckets and account ids are replaced; the originals are not in this package.

| Placeholder | Spans replaced |
|---|---|
| `<WORKSPACE>` | 1 |

## Hash oracle

A sha256 of a run record holding a masked value would let anyone confirm a guessed user name, path or bucket, so this package prints no such hash; the fields below are cited by name only and are not checkable from the package.
Output sha256 values are printed, since the comparison needs them; render refuses an output holding a bucket, account id, approver or user name, and a result table holding a path is named under "Result tables not shipped".
submit.sh is not shipped: no run record binds its bytes. code/<stage>/commands.sh, the recorded submission line, is.
Limit: GARS records no sha256 of submit.sh. On the run's machine, harvest compared the launch line Nextflow itself logged (run/.nextflow.log) with the nextflow run line in submit.sh and refused on any difference; the rest of submit.sh (its environment lines) is bound by nothing.

- atacseq_bulk.01_nfcore-atacseq-wrapper: `command.sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `config_sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `samplesheet_sha256`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `idempotency_key`, not printed: it hashes a file holding values the package masks.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `design_check.sha256`, not printed: the file it hashes is not in this package.
- atacseq_bulk.01_nfcore-atacseq-wrapper: `execution_config[executor_descriptor]`, not printed: executor descriptor values beyond the backend name never ship.

## Not recorded

- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BWA_MEM: not recorded by the run.
- atacseq_bulk.01_nfcore-atacseq-wrapper: container digest of process NFCORE_ATACSEQ:ATACSEQ:MULTIQC: not recorded by the run.
- every stage: the input files' checksums and URLs (G5): not recorded by the run.
- every stage: the timezone of the trace timestamps.

## Gaps

- G1: container images are pinned by the tag the trace recorded; no digest was recorded at run, and none is resolved here.
- G4: the run's records hold absolute paths; the package masks them (above).
- G5: no run record holds an input URL or an input FASTQ checksum; inputs/inputs.tsv labels each value it carries.

## Comparison modes and tolerance entries

Every member is compared `exact` unless an entry below declares another mode with a cause read from its bytes (decision 0283).

- entries of origin `S2b-preregistered`: 0
- entries of origin `pass-1`: 0

## Result tables not shipped

- `atacseq_bulk.01_nfcore-atacseq-wrapper/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.featureCounts.txt`: it holds a path, which a byte-exact table cannot mask.

## Environment

- env/gars-bio.pins.txt is the pip pin list at the GARS commit, with no hashes; it is not the run's recorded environment.
- env/rerun.config pins each process to the image tag the run recorded, on 4 CPUs and the run's own resource clamp; the original ran on AWS Batch, so a re-run here is cross-platform.

## Sources

- code/, env/containers.tsv, params/, outputs/outputs.tsv, records/: the run's manifests, as harvested.
- inputs/inputs.tsv: checksums computed at harvest; URLs from inputs/lane-sources.tsv.
- inputs/reference.tsv: checksums recorded at run; URLs from inputs/lane-sources.tsv.
- METHODS.md: the GARS Methods renderer, run over the same records.
- code/GARS.txt: the harvest record (the package_run.py checkout and the clone status).
