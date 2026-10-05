# Methods

rnaseq-de v0.10.0 was configured with the design formula `~ condition` and the contrast MT versus WT (factor condition); its run status is not recorded.
Parameters, software versions and container images are listed below; every value traces to the run's records (Provenance).

## Provenance

The run manifest of workflow `rnaseq-de` records: version `v0.10.0`; pipeline commit `c54a71584b1347937e4315cbbeb3f27371655228`; GARS wrapper `rnaseq-de`; GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`; template version `v0.10.0`; status not recorded.
Its reference genome is not recorded.
Its configuration sha256 is `d2b847628a098cb3dbd60aedd0477fdc640f17c47183bc47c873842d7625be4d`.
Its thread count is `4`.
Its exact submission is not recorded.
Its agent model is not recorded.
Its model-mediated steps are not recorded.
Each workflow's parameters, random seeds, software versions and container images are listed below.

### Parameters

- `rnaseq-de` parameter `contrast`: `condition,MT,WT`.
- `rnaseq-de` parameter `counts`: a path-like value, withheld.
- `rnaseq-de` parameter `design`: a path-like value, withheld.
- `rnaseq-de` parameter `formula`: `~ condition`.
- `rnaseq-de` random seed for `sklearn.decomposition.PCA`: `0`.
- `rnaseq-de` random seed for `pydeseq2.dds.DeseqDataSet.deseq2`: not recorded; seed supported `false`, determinism `unknown`.
- `rnaseq-de` random seed for `pydeseq2.ds.DeseqStats.summary`: not recorded; seed supported `false`, determinism `unknown`.

### Software used

- GARS commit `c54a71584b1347937e4315cbbeb3f27371655228`, template version `v0.10.0` (workflow `rnaseq-de`).
- Workflow `rnaseq-de` version `v0.10.0`, pipeline commit `c54a71584b1347937e4315cbbeb3f27371655228`.
- `rnaseq-de`: software versions are not recorded.
- `rnaseq-de`: container images are not recorded.

### Citation

Cite GARS at commit `c54a71584b1347937e4315cbbeb3f27371655228`; the GARS repository's CITATION.cff file gives the preferred citation.

### Records read

- manifest 1: sha256 `03ab0bc56158ad998db561fb2aca0d2fd81f9d806d6d534da270daa292d079fa`.

### Sources

- line 3: prose-configured: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/predicate_facts/status manifest1:/params/formula manifest1:/params/contrast`.
- line 4: prose-closing.
- line 8: workflow: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit manifest1:/wrapper manifest1:/gars_commit manifest1:/template_version manifest1:/predicate_facts/status`.
- line 9: reference-absent: `manifest1:/reference`.
- line 10: config: `manifest1:/config_sha256`.
- line 11: threads: `manifest1:/threads`.
- line 12: command-absent: `manifest1:/command`.
- line 13: agent: `manifest1:/agent_model`.
- line 14: model-steps-absent: `manifest1:/model_steps`.
- line 15: pointer.
- line 19: param: `manifest1:/workflow_name manifest1:/params#0.key manifest1:/params#0.value`.
- line 20: param: `manifest1:/workflow_name manifest1:/params#1.key manifest1:/params#1.value`.
- line 21: param: `manifest1:/workflow_name manifest1:/params#2.key manifest1:/params#2.value`.
- line 22: param: `manifest1:/workflow_name manifest1:/params#3.key manifest1:/params#3.value`.
- line 23: seed: `manifest1:/workflow_name manifest1:/random_seeds/0/call manifest1:/random_seeds/0/seed`.
- line 24: seed-unset: `manifest1:/workflow_name manifest1:/random_seeds/1/call manifest1:/random_seeds/1/seed_supported manifest1:/random_seeds/1/determinism manifest1:/random_seeds/1/seed`.
- line 25: seed-unset: `manifest1:/workflow_name manifest1:/random_seeds/2/call manifest1:/random_seeds/2/seed_supported manifest1:/random_seeds/2/determinism manifest1:/random_seeds/2/seed`.
- line 29: gars: `manifest1:/gars_commit manifest1:/template_version manifest1:/workflow_name`.
- line 30: workflow-version: `manifest1:/workflow_name manifest1:/workflow_version manifest1:/pipeline_commit`.
- line 31: versions-absent: `manifest1:/workflow_name manifest1:/software_versions`.
- line 32: containers-absent: `manifest1:/workflow_name manifest1:/containers`.
- line 36: citation: `manifest1:/gars_commit`.
- line 40: record: `manifest1:bytes`.
