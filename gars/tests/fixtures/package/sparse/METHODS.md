# Methods

nf-core/atacseq v2.1.2 was run through the GARS workflow nfcore-atacseq-wrapper against the R64-1-1 reference genome (annotation release R64-1-1.fixture) with the bwa aligner.
The record for nf-core/atacseq names no agent model.
Parameters, software versions and container images are listed below, or marked not recorded; every value traces to the run's records (Provenance).

## Provenance

The run manifest of workflow `nfcore-atacseq-wrapper` records: version `2.1.2`; pipeline commit `<PIPELINE_COMMIT>`; GARS wrapper `atacseq_bulk`; GARS commit `<GARS_COMMIT>`; template version `v0.10.0`; status `COMPLETE`.
Its reference genome: build `R64-1-1`; annotation release `R64-1-1.fixture`; FASTA sha256 `38d8e6d3c76fbaaad4b7181a466774cf973cc851fba4b34f8d116542e7286816`; GTF sha256 `bb3cf3ecb15fd2e6e88503da04936b008b0d5e6fb9f49dbcb8d176663a31793a`.
Its configuration sha256 is not published, since the file names local paths.
Its thread count is `4`.
Its exact submission: `reproducibility/commands.sh`, sha256 not published, since the file names local paths.
Its agent model is `none`.
Each workflow's parameters, random seeds, software versions and container images are listed below.

### Parameters

- `nfcore-atacseq-wrapper` parameter `aligner`: `bwa`.
- `nfcore-atacseq-wrapper` parameter `fasta`: a path-like value, withheld.
- `nfcore-atacseq-wrapper` parameter `gtf`: a path-like value, withheld.
- `nfcore-atacseq-wrapper` parameter `input`: a path-like value, withheld.
- `nfcore-atacseq-wrapper` parameter `macs_gsize`: `11624332`.
- `nfcore-atacseq-wrapper` parameter `mito_name`: `MT`.
- `nfcore-atacseq-wrapper` parameter `narrow_peak`: `true`.
- `nfcore-atacseq-wrapper` parameter `outdir`: a path-like value, withheld.
- `nfcore-atacseq-wrapper` parameter `save_reference`: `true`.
- `nfcore-atacseq-wrapper` random seeds: `no-rng-in-code-path`.

### Software used

- GARS commit `<GARS_COMMIT>`, template version `v0.10.0` (workflow `nfcore-atacseq-wrapper`).
- Workflow `nfcore-atacseq-wrapper` version `2.1.2`, pipeline commit `<PIPELINE_COMMIT>`.
- `nfcore-atacseq-wrapper` software versions (file `run/results/pipeline_info/software_versions.yml`, sha256 `82eeb037211c42ccdd2101b9a81f6661bb6e1632ae361ce8770994aa99e5bf66`):
  - `BWA_MEM/bwa`: `0.7.17-r1188`.
  - `Workflow/Nextflow`: `26.04.6`.
  - `Workflow/nf-core/atacseq`: `v2.1.2`.
- `nfcore-atacseq-wrapper` container for process `NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BWA_MEM`: image `quay.io/biocontainers/bwa:0.7.17--hed695b0_7`, digest not recorded, image file sha256 not recorded.
- `nfcore-atacseq-wrapper` container for process `NFCORE_ATACSEQ:ATACSEQ:MULTIQC`: image `quay.io/biocontainers/multiqc:1.13--pyhdfd78af_0`, digest not recorded, image file sha256 not recorded.

### Citation

Cite GARS at commit `<GARS_COMMIT>`; the GARS repository's CITATION.cff file gives the preferred citation.

### Records read

- manifest 1: sha256 not published, since the record holds values this page does not print.

### Sources

- line 3: prose-run: `manifest1:/predicate_facts/wrapper_kind manifest1:/software_versions/0/versions#2.key manifest1:/software_versions/0/versions#2.value manifest1:/predicate_facts/status manifest1:/workflow_name manifest1:/reference/comparison manifest1:/reference/build manifest1:/params/gtf? manifest1:/reference/annotation_release manifest1:/params/aligner`.
- line 4: prose-agent-none: `manifest1:/predicate_facts/wrapper_kind manifest1:/software_versions/0/versions#2.key manifest1:/agent_model manifest1:/model_steps`.
- line 5: prose-closing.
- line 9: workflow: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit manifest1:/wrapper manifest1:/gars_commit manifest1:/template_version manifest1:/predicate_facts/status`.
- line 10: reference: `manifest1:/reference/build manifest1:/reference/annotation_release manifest1:/reference/fasta_sha256 manifest1:/reference/gtf_sha256`.
- line 11: config: `manifest1:/config_sha256`.
- line 12: threads: `manifest1:/threads`.
- line 13: command: `manifest1:/command/path manifest1:/command/sha256`.
- line 14: agent: `manifest1:/agent_model`.
- line 15: pointer.
- line 19: param: `manifest1:/workflow_name manifest1:/params#0.key manifest1:/params#0.value`.
- line 20: param: `manifest1:/workflow_name manifest1:/params#1.key manifest1:/params#1.value`.
- line 21: param: `manifest1:/workflow_name manifest1:/params#2.key manifest1:/params#2.value`.
- line 22: param: `manifest1:/workflow_name manifest1:/params#3.key manifest1:/params#3.value`.
- line 23: param: `manifest1:/workflow_name manifest1:/params#4.key manifest1:/params#4.value`.
- line 24: param: `manifest1:/workflow_name manifest1:/params#5.key manifest1:/params#5.value`.
- line 25: param: `manifest1:/workflow_name manifest1:/params#6.key manifest1:/params#6.value`.
- line 26: param: `manifest1:/workflow_name manifest1:/params#7.key manifest1:/params#7.value`.
- line 27: param: `manifest1:/workflow_name manifest1:/params#8.key manifest1:/params#8.value`.
- line 28: seeds-text: `manifest1:/workflow_name manifest1:/random_seeds`.
- line 32: gars: `manifest1:/gars_commit manifest1:/template_version manifest1:/workflow_name`.
- line 33: workflow-version: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit`.
- line 34: versions-file: `manifest1:/workflow_name manifest1:/software_versions/0/path manifest1:/software_versions/0/sha256`.
- line 35: version: `manifest1:/software_versions/0/versions#0.key manifest1:/software_versions/0/versions#0.value`.
- line 36: version: `manifest1:/software_versions/0/versions#1.key manifest1:/software_versions/0/versions#1.value`.
- line 37: version: `manifest1:/software_versions/0/versions#2.key manifest1:/software_versions/0/versions#2.value`.
- line 38: container: `manifest1:/workflow_name manifest1:/containers/0/process manifest1:/containers/0/image manifest1:/containers/0/digest manifest1:/containers/0/image_sha256`.
- line 39: container: `manifest1:/workflow_name manifest1:/containers/1/process manifest1:/containers/1/image manifest1:/containers/1/digest manifest1:/containers/1/image_sha256`.
- line 43: citation: `manifest1:/gars_commit`.
- line 47: record-unpublished: `manifest1:withheld`.
