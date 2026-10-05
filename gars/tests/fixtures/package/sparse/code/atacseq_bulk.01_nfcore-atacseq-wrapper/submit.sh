# Masked copy written by package_run.py render: absolute paths, buckets and account ids are replaced (PROVENANCE.md).
# The run recorded no sha256 of this file; harvest bound it by its input-key line, which the executor checks at submit.
#!/bin/bash
set -euo pipefail
WS="<WORKSPACE>/gars"
source "$WS/_system/gars-env.sh"
export NXF_SYNTAX_PARSER=v1
cd "<WORKSPACE>/gars/projects/yeast/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper"
nextflow run "<SCRATCH>/<TEST_ROOT>/w0/pipelines/atacseq-2.1.2" \
    -c "<WORKSPACE>/gars/projects/yeast/_config/nextflow.awsbatch.config" \
    -params-file "<WORKSPACE>/gars/projects/yeast/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/params.yaml" \
    -work-dir "s3://<BUCKET>/work/yeast-atacseq_bulk" \
    $RESUME
# idempotency_key=<withheld: PROVENANCE.md, hash oracle>
