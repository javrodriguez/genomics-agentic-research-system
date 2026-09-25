"""Deterministic small bulk analyses; no benchmark imports or model execution."""
import argparse
import csv
import json
import itertools
import math
import random
from pathlib import Path
from bio_common import sha256

BASES = {'rna-a': ('rnaseq_bulk', 1001), 'rna-b': ('rnaseq_bulk', 1002),
         'atac-a': ('atacseq_bulk', 1003)}
LAYOUT = {'samples.csv': '1-design/samples.csv', 'config.yaml': '1-design/_config/{assay}.yaml',
          'PLAN.md': '1-design/PLAN.md', 'approval.json': '1-design/approval.json',
          'files.csv': '2-data/files.csv', 'counts.tsv': '2-data/counts.tsv',
          'provenance.csv': '2-data/provenance.csv', 'raw': '2-data/raw',
          'de_results.csv': '3-results/de_results.csv',
          'normalized_counts.csv': '3-results/normalized_counts.csv',
          'manifest.json': '3-results/manifest.json', 'qc.md': '3-results/qc.md',
          'snapshot.json': '4-report/snapshot.json'}


# Copied and adapted from benchmarks/defects/generate.py:16-17, 20-30,
# 33-65 and 68-94 at a779084: JSON/CSV writing, seeded sample/FASTQ generation
# and a claims export with hashed computational evidence. No runtime import.
def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def table(path, header, rows, delimiter=','):
    with path.open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n', delimiter=delimiter)
        writer.writerows([header] + rows)


def bh(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result, previous = [None] * len(values), 1.0
    for rank in range(len(order), 0, -1):
        i = order[rank - 1]
        previous = min(previous, values[i] * len(values) / rank)
        result[i] = previous
    return result


def generate(destination, base_project, seed=None):
    assay, fixed_seed = BASES[base_project]
    seed = fixed_seed if seed is None else seed
    rng = random.Random(seed)
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'raw').mkdir()
    conditions = ['A'] * 3 + ['B'] * 3
    samples, files, provenance = [], [], []
    for i, condition in enumerate(conditions):
        sid = condition + '_REP' + str(conditions[:i].count(condition) + 1)
        samples.append([sid, condition, condition, conditions[:i].count(condition) + 1, 'seq%d' % (i % 3 + 1)])
        raw = root / 'raw' / (sid + '.fastq')
        raw.write_text('@READ:1:FLOW:1:1:1:1 1:N:0:ACGTACGT\nACGT\n+\nIIII\n')
        files.append([sid, '1', '2-data/raw/' + raw.name, ''])
        provenance.append([sid, 'donor%d' % (i + 1), 'run%d' % (i % 3 + 1)])
    table(root / 'samples.csv', ['sample_id', 'condition', 'group', 'replicate', 'batch'], samples)
    table(root / 'files.csv', ['sample_id', 'lane', 'fastq_1', 'fastq_2'], files)
    table(root / 'provenance.csv', ['sample_id', 'biological_source', 'processing_run'], provenance)
    config = ('strandedness: auto\nunit_of_replication: sample\nreference_release: synthetic-v1\n'
              'de:\n  formula: "' + chr(126) + ' condition"\n  contrast: "condition,B,A"\n')
    (root / 'config.yaml').write_text(config)
    feature = lambda i: ('g%d' % i if assay == 'rnaseq_bulk' else 'chr1:%d-%d' % (i * 100, i * 100 + 99))
    rows = [[feature(i)] + [rng.randrange(50, 151) for unused in samples] for i in range(1, 5)]
    table(root / 'counts.tsv', ['gene'] + [s[0] for s in samples], rows, '\t')
    table(root / 'normalized_counts.csv', ['gene'] + [s[0] for s in samples], rows)
    probabilities = []
    for row in rows:
        values = row[1:]
        observed = abs(sum(values[3:]) - sum(values[:3]))
        probabilities.append(sum(abs(2 * sum(values[i] for i in group) - sum(values)) >= observed
                                 for group in itertools.combinations(range(6), 3)) / 20.0)
    table(root / 'de_results.csv', ['gene', 'baseMean', 'log2FoldChange', 'pvalue', 'padj'] + [row[0] for row in samples],
          [[feature(i + 1), sum(rows[i][1:]) / 6.0,
            math.log(sum(rows[i][4:]) / sum(rows[i][1:4]), 2), p, q] + rows[i][1:] for i, (p, q) in enumerate(zip(probabilities, bh(probabilities)))])
    plan = ('# Analysis plan\nStatus: APPROVED\n\n## Goal\nCompare B with A in a small bulk study.\n'
            '## Method\nIndependent samples; condition-only model. Three biological replicates per arm.\n'
            'Processing runs balanced across arms; no pooling of subjects.\n'
            'Exact two-sided permutation tests of mean abundance; all 20 three-versus-three assignments; BH across four features.\n'
            'Equal library exposure; counts already on a common scale. No filtering or shrinkage; alpha 0.05; report effect sizes.\n'
            'Outliers retained; descriptive inference only; no pathway or causal claims.\n'
            'ATAC uses union consensus, blacklist exclusion and global scaling; no global shift assumed.\n'
            '## Outputs\n| File | Type | Description |\n|---|---|---|\n'
            '| de_results.csv | de_results | Differential table |\n\n## Execution\nRuns: batch\n')
    (root / 'PLAN.md').write_text(plan)
    write_json(root / 'approval.json', {'actor': 'human', 'timestamp': '2026-09-25T00:00:00Z',
               'expiry': '2026-09-26T00:00:00Z', 'plan_sha256': sha256(plan.encode())})
    (root / 'qc.md').write_text('All six libraries retained. No outliers removed.\n'
        'Count summaries are seeded illustrative measurements; tiny FASTQs test file integrity and are not their source.\n'
        'RNA: inferred strandedness agrees with declared auto inference.\n'
        'ATAC: FRiP 0.35, TSS enrichment 9, nucleosomal fragment periodicity retained.\n'
        'QC disposition WARN: small illustrative study; no population or causal generalization.\n')
    manifest = {'pipeline_commit': 'synthetic-v1', 'params': {'assay': assay, 'seed': seed,
                'unit_of_replication': 'sample', 'formula': 'condition',
                'execution_started_at': '2026-09-25T01:00:00Z', 'execution_finished_at': '2026-09-25T01:01:00Z', 'contrast': 'B versus A',
                'alpha': .05, 'multiple_testing_scope': 'four tested features'}}
    write_json(root / 'manifest.json', manifest)
    evidence = {'id': 1, 'artifact_id': 1, 'source_id': None, 'kind': 'statistical',
                'relation': 'supports', 'source': None, 'artifact': {'id': 1,
                'path': '3-results/de_results.csv', 'sha256': sha256((root / 'de_results.csv').read_bytes())}}
    write_json(root / 'snapshot.json', {'run': {'id': 1, 'question': 'Is bulk abundance associated with condition?',
        'manifest_path': '3-results/manifest.json', 'manifest_sha256': sha256((root / 'manifest.json').read_bytes())},
        'claims': [{'id': 1, 'run_id': 1, 'type': 'OBSERVATION',
        'text': 'No tested feature meets BH adjusted p below 0.05.',
        'bio_support': {'statistical_support': 'BH across four features', 'replication': 'Three samples per arm',
                        'effect_size': 'See differential table', 'orthogonal_assay': 'none', 'literature': 'not used'},
        'process_risk': {'data_quality': 'All libraries retained', 'confounding_risk': 'Processing balanced',
            'provenance_completeness': 'Library origins in provenance.csv', 'qc_disposition': 'WARN',
            'limitation': 'Small descriptive study; lack of significance does not establish equivalence.'},
        'reference_release': 'synthetic-v1', 'workflow_version': 'synthetic-v1', 'evidence': [evidence]}]})
    return root


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', choices=sorted(BASES), required=True)
    parser.add_argument('--seed', type=int)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    generate(args.out, args.base, args.seed)
    print('base generated: ' + args.base)


if __name__ == '__main__':
    main()
