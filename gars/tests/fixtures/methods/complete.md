# Methods

nfcore-rnaseq-wrapper (workflow version 3.26.0) was run against the fixture-build reference genome (annotation release fixture-release) with the star_salmon aligner.
rnaseq-de (workflow version v0.10.0) was run with the design formula `~ condition` and the contrast MT versus WT (factor condition).
The agent model recorded for every workflow was claude-opus-5-5.
A separate custom analysis was planned, and its plan was approved on 29 September 2026 by the approver named in its approval record.
The project's history records that custom analysis as complete on 29 September 2026, with the agent model claude-opus-5-5.
Parameters, software versions and container images are listed below, or marked not recorded; every value traces to the run's records (Provenance).

## Provenance

The run manifest of workflow `nfcore-rnaseq-wrapper` records: version `3.26.0`; pipeline commit `72c5d4006f3610a00223bd368f28ed650d649a54`; GARS wrapper `rnaseq_bulk`; GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`; template version `v0.10.0`; status `COMPLETE`.
Its reference genome: build `fixture-build`; annotation release `fixture-release`; FASTA sha256 `99724deab54039707cfdd57d24710a39412ecbd8ed85fb8a5d4c1f70706d637b`; GTF sha256 `aac372d27c1a6c729d38fa73dac6febfa75a76a57bc42613a33fd7b3f0fb960f`.
Its configuration sha256 is not published, since the file names local paths.
Its thread count is `4`.
Its exact submission: `reproducibility/commands.sh`, sha256 not published, since the file names local paths.
Its agent model is `claude-opus-5-5`.
It records a model-mediated step: model `claude-opus-5-5`; provider `anthropic`; contract `gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md`; contract hash `69b7a0d66c1ecf9822481b2d99b83b9f43c0cf73` (algorithm `git-sha1`).
The run manifest of workflow `rnaseq-de` records: version `v0.10.0`; pipeline commit `c54a71584b1347937e4315cbbeb3f27371655228`; GARS wrapper `rnaseq-de`; GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`; template version `v0.10.0`; status `COMPLETE`.
Its reference genome: build `fixture-build`; annotation release `fixture-release`; FASTA sha256 `99724deab54039707cfdd57d24710a39412ecbd8ed85fb8a5d4c1f70706d637b`; GTF sha256 `aac372d27c1a6c729d38fa73dac6febfa75a76a57bc42613a33fd7b3f0fb960f`.
Its configuration sha256 is not published, since the file names local paths.
Its thread count is `4`.
Its exact submission: `reproducibility/commands.sh`, sha256 not published, since the file names local paths.
Its agent model is `claude-opus-5-5`.
It records a model-mediated step: model `claude-opus-5-5`; provider `anthropic`; contract `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`; contract hash `a8ce7d799e79733b8e1d41a26c9e8c597f773987` (algorithm `git-sha1`).
The analysis plan with sha256 `b2fad3e6dd46adfbb19ab0ec2ee525ecc04cfa72a74758d1dc8439602c0e04c6` was approved at `2026-09-29T18:04:05Z` by the approver the run recorded.
The project's history records `03_custom_analysis/01_fixture-followup` as `analysis complete` on `2026-09-29`, with model `claude-opus-5-5` and template version `v0.10.0`.
Each workflow's parameters, random seeds, software versions and container images are listed below.

### Parameters

- `nfcore-rnaseq-wrapper` parameter `aligner`: `star_salmon`.
- `nfcore-rnaseq-wrapper` parameter `fasta`: a path-like value, withheld.
- `nfcore-rnaseq-wrapper` parameter `gtf`: a path-like value, withheld.
- `nfcore-rnaseq-wrapper` parameter `input`: a path-like value, withheld.
- `nfcore-rnaseq-wrapper` parameter `outdir`: a path-like value, withheld.
- `nfcore-rnaseq-wrapper` random seeds: `no-rng-in-code-path`.
- `rnaseq-de` parameter `contrast`: `condition,MT,WT`.
- `rnaseq-de` parameter `counts`: a path-like value, withheld.
- `rnaseq-de` parameter `design`: a path-like value, withheld.
- `rnaseq-de` parameter `formula`: `~ condition`.
- `rnaseq-de` random seed for `sklearn.decomposition.PCA`: `0`.
- `rnaseq-de` random seed for `pydeseq2.dds.DeseqDataSet.deseq2`: not recorded; seed supported `false`, determinism `unknown`.
- `rnaseq-de` random seed for `pydeseq2.ds.DeseqStats.summary`: not recorded; seed supported `false`, determinism `unknown`.

### Software used

- GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`, template version `v0.10.0` (workflow `nfcore-rnaseq-wrapper`).
- Workflow `nfcore-rnaseq-wrapper` version `3.26.0`, pipeline commit `72c5d4006f3610a00223bd368f28ed650d649a54`.
- `nfcore-rnaseq-wrapper` software versions (file `run/results/pipeline_info/software_versions.yml`, sha256 `63dd8ca50d35f240082f303872ab4452dfcb6a37f7fd0d71240c754df58f393f`):
  - `FIXTURE_PROCESS/fixture-tool`: `1.0.0`.
- `nfcore-rnaseq-wrapper` container for process `DIGEST`: image `fixture/tool@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, digest `sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, image file sha256 not recorded.
- `nfcore-rnaseq-wrapper` container for process `LOCAL_IMAGE`: image `pipeline_info/fixture.sif`, digest not recorded, image file sha256 `e06238fb1730648111061cff3969740304d8f8359883f6ce261f44a880731071`.
- GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`, template version `v0.10.0` (workflow `rnaseq-de`).
- Workflow `rnaseq-de` version `v0.10.0`, pipeline commit `c54a71584b1347937e4315cbbeb3f27371655228`.
- `rnaseq-de` software versions (file `run/versions.json`, sha256 `d487470fda47c20c1a6249644de0d15d52fb5e818fc03faa35ebcadd3fdf451d`):
  - `pandas`: `fixture-1`.
  - `python`: `3.9.0`.
- `rnaseq-de`: container images are not recorded.

### Citation

Cite GARS at commit `c54a71584b1347937e4315cbbeb3f27371655228`; the GARS repository's CITATION.cff file gives the preferred citation.

### Records read

- manifest 1: sha256 not published, since the record holds values this page does not print.
- manifest 2: sha256 not published, since the record holds values this page does not print.
- plan: sha256 `b2fad3e6dd46adfbb19ab0ec2ee525ecc04cfa72a74758d1dc8439602c0e04c6`.
- approval record: sha256 not published, since the record holds values this page does not print.
- history: sha256 not published, since the record holds values this page does not print.

### Sources

- line 3: prose-run: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/predicate_facts/status manifest1:/predicate_facts/wrapper_kind manifest1:/reference/comparison manifest1:/reference/build manifest1:/reference/annotation_release manifest1:/params/aligner`.
- line 4: prose-run: `manifest2:/workflow_name manifest2:/workflow_version manifest2:/predicate_facts/status manifest2:/params/formula manifest2:/params/contrast`.
- line 5: prose-agent-all: `manifest1:/agent_model manifest2:/agent_model`.
- line 6: prose-approval: `approval:/plan_sha256 approval:/plan_path? approval:/timestamp approval:/actor?`.
- line 7: prose-history: `history:#3/stage history:#3/outcome history:#3/date history:#3/model`.
- line 8: prose-closing.
- line 12: workflow: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit manifest1:/wrapper manifest1:/gars_commit manifest1:/template_version manifest1:/predicate_facts/status`.
- line 13: reference: `manifest1:/reference/build manifest1:/reference/annotation_release manifest1:/reference/fasta_sha256 manifest1:/reference/gtf_sha256`.
- line 14: config: `manifest1:/config_sha256`.
- line 15: threads: `manifest1:/threads`.
- line 16: command: `manifest1:/command/path manifest1:/command/sha256`.
- line 17: agent: `manifest1:/agent_model`.
- line 18: model-step: `manifest1:/model_steps/0/model_id manifest1:/model_steps/0/provider manifest1:/model_steps/0/prompt_id manifest1:/model_steps/0/prompt_sha256/value manifest1:/model_steps/0/prompt_sha256/algorithm`.
- line 19: workflow: `manifest2:/workflow_name manifest2:/workflow_version manifest2:/pipeline_commit manifest2:/wrapper manifest2:/gars_commit manifest2:/template_version manifest2:/predicate_facts/status`.
- line 20: reference: `manifest2:/reference/build manifest2:/reference/annotation_release manifest2:/reference/fasta_sha256 manifest2:/reference/gtf_sha256`.
- line 21: config: `manifest2:/config_sha256`.
- line 22: threads: `manifest2:/threads`.
- line 23: command: `manifest2:/command/path manifest2:/command/sha256`.
- line 24: agent: `manifest2:/agent_model`.
- line 25: model-step: `manifest2:/model_steps/0/model_id manifest2:/model_steps/0/provider manifest2:/model_steps/0/prompt_id manifest2:/model_steps/0/prompt_sha256/value manifest2:/model_steps/0/prompt_sha256/algorithm`.
- line 26: approval: `approval:/plan_sha256 approval:/timestamp approval:/actor?`.
- line 27: history: `history:#3/stage history:#3/outcome history:#3/date history:#3/model history:#3/template_version`.
- line 28: pointer.
- line 32: param: `manifest1:/workflow_name manifest1:/params#0.key manifest1:/params#0.value`.
- line 33: param: `manifest1:/workflow_name manifest1:/params#1.key manifest1:/params#1.value`.
- line 34: param: `manifest1:/workflow_name manifest1:/params#2.key manifest1:/params#2.value`.
- line 35: param: `manifest1:/workflow_name manifest1:/params#3.key manifest1:/params#3.value`.
- line 36: param: `manifest1:/workflow_name manifest1:/params#4.key manifest1:/params#4.value`.
- line 37: seeds-text: `manifest1:/workflow_name manifest1:/random_seeds`.
- line 38: param: `manifest2:/workflow_name manifest2:/params#0.key manifest2:/params#0.value`.
- line 39: param: `manifest2:/workflow_name manifest2:/params#1.key manifest2:/params#1.value`.
- line 40: param: `manifest2:/workflow_name manifest2:/params#2.key manifest2:/params#2.value`.
- line 41: param: `manifest2:/workflow_name manifest2:/params#3.key manifest2:/params#3.value`.
- line 42: seed: `manifest2:/workflow_name manifest2:/random_seeds/0/call manifest2:/random_seeds/0/seed`.
- line 43: seed-unset: `manifest2:/workflow_name manifest2:/random_seeds/1/call manifest2:/random_seeds/1/seed_supported manifest2:/random_seeds/1/determinism manifest2:/random_seeds/1/seed`.
- line 44: seed-unset: `manifest2:/workflow_name manifest2:/random_seeds/2/call manifest2:/random_seeds/2/seed_supported manifest2:/random_seeds/2/determinism manifest2:/random_seeds/2/seed`.
- line 48: gars: `manifest1:/gars_commit manifest1:/template_version manifest1:/workflow_name`.
- line 49: workflow-version: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit`.
- line 50: versions-file: `manifest1:/workflow_name manifest1:/software_versions/0/path manifest1:/software_versions/0/sha256`.
- line 51: version: `manifest1:/software_versions/0/versions#0.key manifest1:/software_versions/0/versions#0.value`.
- line 52: container: `manifest1:/workflow_name manifest1:/containers/0/process manifest1:/containers/0/image manifest1:/containers/0/digest manifest1:/containers/0/image_sha256`.
- line 53: container: `manifest1:/workflow_name manifest1:/containers/1/process manifest1:/containers/1/image manifest1:/containers/1/digest manifest1:/containers/1/image_sha256`.
- line 54: gars: `manifest2:/gars_commit manifest2:/template_version manifest2:/workflow_name`.
- line 55: workflow-version: `manifest2:/workflow_name manifest2:/workflow_version manifest2:/pipeline_commit`.
- line 56: versions-file: `manifest2:/workflow_name manifest2:/software_versions/0/path manifest2:/software_versions/0/sha256`.
- line 57: version: `manifest2:/software_versions/0/versions#0.key manifest2:/software_versions/0/versions#0.value`.
- line 58: version: `manifest2:/software_versions/0/versions#1.key manifest2:/software_versions/0/versions#1.value`.
- line 59: containers-absent: `manifest2:/workflow_name manifest2:/containers`.
- line 63: citation: `manifest1:/gars_commit`.
- line 67: record-unpublished: `manifest1:withheld`.
- line 68: record-unpublished: `manifest2:withheld`.
- line 69: record: `plan:bytes`.
- line 70: record-unpublished: `approval:withheld`.
- line 71: record-unpublished: `history:withheld`.
