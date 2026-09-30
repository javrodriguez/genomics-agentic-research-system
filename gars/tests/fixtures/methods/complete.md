# Methods

The run manifest of workflow `nfcore-rnaseq-wrapper` records: version `3.26.0`; pipeline commit `72c5d4006f3610a00223bd368f28ed650d649a54`; GARS wrapper `rnaseq_bulk`; GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`; template version `v0.10.0`; status `COMPLETE`.
Its reference genome: build `fixture-build`; annotation release `fixture-release`; FASTA sha256 `99724deab54039707cfdd57d24710a39412ecbd8ed85fb8a5d4c1f70706d637b`; GTF sha256 `aac372d27c1a6c729d38fa73dac6febfa75a76a57bc42613a33fd7b3f0fb960f`.
Its configuration sha256 is `57fc7ebe7584cba1a50e195979f889f43f973f4e8726fc512d8dd92abd4abd4a`.
Its thread count is `4`.
Its exact submission: `reproducibility/commands.sh`, sha256 `c7941ece64f3fe877e99ddb38c537e0acb0acdcbc0ca69dd948de39e9a4d8783`.
Its agent model is `claude-opus-5-5`.
It records a model-mediated step: model `claude-opus-5-5`; provider `anthropic`; contract `gars/02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md`; git blob `69b7a0d66c1ecf9822481b2d99b83b9f43c0cf73`.
The run manifest of workflow `rnaseq-de` records: version `v0.10.0`; pipeline commit `c54a71584b1347937e4315cbbeb3f27371655228`; GARS wrapper `rnaseq-de`; GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`; template version `v0.10.0`; status `COMPLETE`.
Its reference genome: build `fixture-build`; annotation release `fixture-release`; FASTA sha256 `99724deab54039707cfdd57d24710a39412ecbd8ed85fb8a5d4c1f70706d637b`; GTF sha256 `aac372d27c1a6c729d38fa73dac6febfa75a76a57bc42613a33fd7b3f0fb960f`.
Its configuration sha256 is `d2b847628a098cb3dbd60aedd0477fdc640f17c47183bc47c873842d7625be4d`.
Its thread count is `4`.
Its exact submission: `reproducibility/commands.sh`, sha256 `f27f37e1575b2494fb3e98ac6a09e31b2faf7f67222e6ab0bc4b90b279da2a8d`.
Its agent model is `claude-opus-5-5`.
It records a model-mediated step: model `claude-opus-5-5`; provider `anthropic`; contract `gars/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md`; git blob `a8ce7d799e79733b8e1d41a26c9e8c597f773987`.
The analysis plan with sha256 `b2fad3e6dd46adfbb19ab0ec2ee525ecc04cfa72a74758d1dc8439602c0e04c6` was approved at `2026-09-29T18:04:05Z` by the approver the run recorded.
The project's history records `03_custom_analysis/01_fixture-followup` as `analysis complete` on `2026-09-29`, with model `claude-opus-5-5` and template version `v0.10.0`.
Each workflow's parameters, random seeds, software versions and container images are listed below.

## Parameters

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

## Software used

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

## Citation

Cite GARS at commit `c54a71584b1347937e4315cbbeb3f27371655228`; the GARS repository's CITATION.cff file gives the preferred citation.

## Records read

- manifest 1: sha256 `2f062673be291f9ef5c247bfb0d76bdf381f9f02d1b5e4e0a904999b3b19bff3`.
- manifest 2: sha256 `1dcbf73179636cfead6ca263d2a3ab5293f911785226891059f52897a37c0970`.
- plan: sha256 `b2fad3e6dd46adfbb19ab0ec2ee525ecc04cfa72a74758d1dc8439602c0e04c6`.
- approval record: sha256 `f667db231c6b3c8e01fd333beb8e0989d0f83fa9bb82946b0abdb388be67aa42`.
- history: sha256 `e104223b599ce04059e4e30e66e2c78e0b98289ffadc870db02860e763cc7d83`.

## Sources

- line 3: workflow: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit manifest1:/wrapper manifest1:/gars_commit manifest1:/template_version manifest1:/predicate_facts/status`.
- line 4: reference: `manifest1:/reference/build manifest1:/reference/annotation_release manifest1:/reference/fasta_sha256 manifest1:/reference/gtf_sha256`.
- line 5: config: `manifest1:/config_sha256`.
- line 6: threads: `manifest1:/threads`.
- line 7: command: `manifest1:/command/path manifest1:/command/sha256`.
- line 8: agent: `manifest1:/agent_model`.
- line 9: model-step: `manifest1:/model_steps/0/model_id manifest1:/model_steps/0/provider manifest1:/model_steps/0/prompt_id manifest1:/model_steps/0/prompt_sha256/value`.
- line 10: workflow: `manifest2:/workflow_name manifest2:/workflow_version manifest2:/pipeline_commit manifest2:/wrapper manifest2:/gars_commit manifest2:/template_version manifest2:/predicate_facts/status`.
- line 11: reference: `manifest2:/reference/build manifest2:/reference/annotation_release manifest2:/reference/fasta_sha256 manifest2:/reference/gtf_sha256`.
- line 12: config: `manifest2:/config_sha256`.
- line 13: threads: `manifest2:/threads`.
- line 14: command: `manifest2:/command/path manifest2:/command/sha256`.
- line 15: agent: `manifest2:/agent_model`.
- line 16: model-step: `manifest2:/model_steps/0/model_id manifest2:/model_steps/0/provider manifest2:/model_steps/0/prompt_id manifest2:/model_steps/0/prompt_sha256/value`.
- line 17: approval: `approval:/plan_sha256 approval:/timestamp approval:/actor?`.
- line 18: history: `history:#3/stage history:#3/outcome history:#3/date history:#3/model history:#3/template_version`.
- line 19: pointer.
- line 23: param: `manifest1:/workflow_name manifest1:/params#0.key manifest1:/params#0.value`.
- line 24: param: `manifest1:/workflow_name manifest1:/params#1.key manifest1:/params#1.value`.
- line 25: param: `manifest1:/workflow_name manifest1:/params#2.key manifest1:/params#2.value`.
- line 26: param: `manifest1:/workflow_name manifest1:/params#3.key manifest1:/params#3.value`.
- line 27: param: `manifest1:/workflow_name manifest1:/params#4.key manifest1:/params#4.value`.
- line 28: seeds-text: `manifest1:/workflow_name manifest1:/random_seeds`.
- line 29: param: `manifest2:/workflow_name manifest2:/params#0.key manifest2:/params#0.value`.
- line 30: param: `manifest2:/workflow_name manifest2:/params#1.key manifest2:/params#1.value`.
- line 31: param: `manifest2:/workflow_name manifest2:/params#2.key manifest2:/params#2.value`.
- line 32: param: `manifest2:/workflow_name manifest2:/params#3.key manifest2:/params#3.value`.
- line 33: seed: `manifest2:/workflow_name manifest2:/random_seeds/0/call manifest2:/random_seeds/0/seed`.
- line 34: seed-unset: `manifest2:/workflow_name manifest2:/random_seeds/1/call manifest2:/random_seeds/1/seed_supported manifest2:/random_seeds/1/determinism manifest2:/random_seeds/1/seed`.
- line 35: seed-unset: `manifest2:/workflow_name manifest2:/random_seeds/2/call manifest2:/random_seeds/2/seed_supported manifest2:/random_seeds/2/determinism manifest2:/random_seeds/2/seed`.
- line 39: gars: `manifest1:/gars_commit manifest1:/template_version manifest1:/workflow_name`.
- line 40: workflow-version: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit`.
- line 41: versions-file: `manifest1:/workflow_name manifest1:/software_versions/0/path manifest1:/software_versions/0/sha256`.
- line 42: version: `manifest1:/software_versions/0/versions#0.key manifest1:/software_versions/0/versions#0.value`.
- line 43: container: `manifest1:/workflow_name manifest1:/containers/0/process manifest1:/containers/0/image manifest1:/containers/0/digest manifest1:/containers/0/image_sha256`.
- line 44: container: `manifest1:/workflow_name manifest1:/containers/1/process manifest1:/containers/1/image manifest1:/containers/1/digest manifest1:/containers/1/image_sha256`.
- line 45: gars: `manifest2:/gars_commit manifest2:/template_version manifest2:/workflow_name`.
- line 46: workflow-version: `manifest2:/workflow_name manifest2:/workflow_version manifest2:/pipeline_commit`.
- line 47: versions-file: `manifest2:/workflow_name manifest2:/software_versions/0/path manifest2:/software_versions/0/sha256`.
- line 48: version: `manifest2:/software_versions/0/versions#0.key manifest2:/software_versions/0/versions#0.value`.
- line 49: version: `manifest2:/software_versions/0/versions#1.key manifest2:/software_versions/0/versions#1.value`.
- line 50: containers-absent: `manifest2:/workflow_name manifest2:/containers`.
- line 54: citation: `manifest1:/gars_commit`.
- line 58: record: `manifest1:bytes`.
- line 59: record: `manifest2:bytes`.
- line 60: record: `plan:bytes`.
- line 61: record: `approval:bytes`.
- line 62: record: `history:bytes`.
