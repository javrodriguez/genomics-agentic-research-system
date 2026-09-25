"""Deterministic small bulk analyses; no benchmark imports or model execution."""
import argparse
import csv
import json
import statistics
import math
import random
from pathlib import Path
from bio_common import sha256

BASES = {'rna-a': ('rnaseq_bulk', 731947205861304921), 'rna-b': ('rnaseq_bulk', 731947205861304922),
         'atac-a': ('atacseq_bulk', 731947205861304923)}
LAYOUT = {'samples.csv': '1-design/samples.csv', 'config.yaml': '1-design/_config/{assay}.yaml',
          'PLAN.md': '1-design/PLAN.md', 'approval.json': '1-design/approval.json',
          'files.csv': '2-data/files.csv', 'counts.tsv': '2-data/counts.tsv',
          'provenance.csv': '2-data/provenance.csv', 'libraries': '2-data/libraries',
          'de_results.csv': '3-results/de_results.csv',
          'normalized_counts.csv': '3-results/normalized_counts.csv',
          'manifest.json': '3-results/manifest.json', 'qc.md': '3-results/qc.md',
          'snapshot.json': '4-report/snapshot.json'}


# Copied and adapted from benchmarks/defects/generate.py:16-17, 20-30,
# 33-65 and 68-94 at a779084: JSON/CSV writing, seeded sample generation
# and a claims export with hashed computational evidence. No runtime import.
def write_json(path, value):
    write_text(path, json.dumps(value, indent=2, sort_keys=True) + '\n')


def write_text(path, text):
    # Explicit UTF-8 and LF on every platform, including JSON hash inputs.
    path.write_bytes(text.encode('utf-8'))


def table(path, header, rows, delimiter=','):
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle, lineterminator='\n', delimiter=delimiter)
        writer.writerows([[format(value, '.12g') if isinstance(value, float) else value
                          for value in row] for row in [header] + rows])


def bh(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    result, previous = [None] * len(values), 1.0
    for rank in range(len(order), 0, -1):
        i = order[rank - 1]
        previous = min(previous, values[i] * len(values) / rank)
        result[i] = previous
    return result


FEATURES = 240
DISPERSION = 0.015


def beta_fraction(a, b, x):
    """Continued fraction for the regularised incomplete beta integral."""
    tiny = 1e-300
    c = 1.0
    d = 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 201):
        for numerator in (m * (b - m) * x / ((a + 2*m - 1) * (a + 2*m)),
                          -(a + m) * (a + b + m) * x / ((a + 2*m) * (a + 2*m + 1))):
            d = 1.0 + numerator * d
            c = 1.0 + numerator / c
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = c if abs(c) > tiny else tiny
            delta = d * c
            h *= delta
        if abs(delta - 1.0) < 3e-14:
            return h
    raise ValueError('beta fraction did not converge')


def regularized_beta(x, a, b):
    if x <= 0.0: return 0.0
    if x >= 1.0: return 1.0
    weight = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                      + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return weight * beta_fraction(a, b, x) / a
    return 1.0 - weight * beta_fraction(b, a, 1.0 - x) / b


def student_p(t, df=4):
    """Two-sided Student t tail, I[df/(df+t*t)](df/2, 1/2)."""
    return regularized_beta(df / (df + t * t), df / 2.0, 0.5)


def negative_binomial(rng, mean, dispersion):
    # Gamma-Poisson mixture: variance = mean + dispersion * mean**2.
    intensity = rng.gammavariate(1.0 / dispersion, mean * dispersion)
    elapsed, count = rng.expovariate(1.0), 0
    while elapsed < intensity:
        count += 1
        elapsed += rng.expovariate(1.0)
    return count


def simulate(seed):
    rng = random.Random(seed)
    affected = rng.sample(range(FEATURES), FEATURES // 10)
    effects = {i: (-1 if j % 2 else 1) * rng.uniform(1.0, 3.0)
               for j, i in enumerate(affected)}
    exposure = [0.75, 1.2, 0.9, 1.1, 0.8, 1.3]
    counts = []
    for i in range(FEATURES):
        mean = rng.lognormvariate(math.log(120.0), 0.8)
        counts.append([negative_binomial(rng, mean * size *
                       (2 ** effects.get(i, 0.0) if j >= 3 else 1.0), DISPERSION)
                       for j, size in enumerate(exposure)])
    return counts, effects


def analyse(counts):
    geometric = [math.exp(math.fsum(math.log(x) for x in row) / len(row))
                 if all(x > 0 for x in row) else None for row in counts]
    factors = [statistics.median(row[j] / gm for row, gm in zip(counts, geometric) if gm)
               for j in range(6)]
    normalized = [[x / size for x, size in zip(row, factors)] for row in counts]
    results = []
    for row in normalized:
        logs = [math.log(x + 1.0, 2) for x in row]
        left, right = logs[:3], logs[3:]
        means = [math.fsum(group) / len(group) for group in (left, right)]
        pooled = math.fsum((x - means[j // 3]) ** 2 for j, x in enumerate(logs)) / 4.0
        difference = means[1] - means[0]
        t = difference / math.sqrt(pooled * (2.0 / 3.0)) if pooled else 0.0
        results.append([math.fsum(row) / len(row), difference, t, student_p(t)])
    for row, q in zip(results, bh([row[3] for row in results])):
        row.append(q)
    return normalized, results


def generate(destination, base_project, seed=None):
    assay, fixed_seed = BASES[base_project]
    seed = fixed_seed if seed is None else seed
    rng = random.Random(seed)
    root = Path(destination)
    root.mkdir(parents=True, exist_ok=True)
    (root / 'libraries').mkdir()
    conditions = ['A'] * 3 + ['B'] * 3
    samples, files, provenance = [], [], []
    for i, condition in enumerate(conditions):
        sid = condition + '_REP' + str(conditions[:i].count(condition) + 1)
        samples.append([sid, condition, condition, conditions[:i].count(condition) + 1, 'seq%d' % (i % 3 + 1)])
        provenance.append([sid, 'donor%d' % (i + 1), 'run%d' % (i % 3 + 1)])
    table(root / 'samples.csv', ['sample_id', 'condition', 'group', 'replicate', 'batch'], samples)
    table(root / 'provenance.csv', ['sample_id', 'biological_source', 'processing_run'], provenance)
    config = (('strandedness: auto\n' if assay == 'rnaseq_bulk' else '') +
              'unit_of_replication: sample\nreference_release: synthetic-v1\n'
              'de:\n  formula: "' + chr(126) + ' condition"\n  contrast: "condition,B,A"\n')
    write_text(root / 'config.yaml', config)
    features = []
    position = 10000
    for i in range(FEATURES):
        if i % 80 == 0:
            position = 10000
        position += rng.randint(500, 25000)
        end = position + rng.randint(150, 900)
        features.append('g%d' % (i + 1) if assay == 'rnaseq_bulk' else
                        'chr%d:%d-%d' % (i // 80 + 1, position, end))
        position = end
    counts, unused_effects = simulate(seed)
    normalized, results = analyse(counts)
    names = [s[0] for s in samples]
    table(root / 'counts.tsv', ['gene'] + names,
          [[features[i]] + row for i, row in enumerate(counts)], '\t')
    table(root / 'normalized_counts.csv', ['gene'] + names,
          [[features[i]] + row for i, row in enumerate(normalized)])
    table(root / 'de_results.csv', ['gene', 'baseMean', 'log2FoldChange', 'stat', 'pvalue', 'padj'] + names,
          [[features[i]] + row + normalized[i] for i, row in enumerate(results)])
    for j, sid in enumerate(names):
        library = root / 'libraries' / (sid + '.tsv')
        table(library, ['gene', 'count'], [[features[i], row[j]] for i, row in enumerate(counts)], '\t')
        files.append([sid, sum(row[j] for row in counts), '2-data/libraries/' + library.name,
                      sha256(library.read_bytes())])
    table(root / 'files.csv', ['sample_id', 'read_count', 'count_file', 'count_sha256'], files)
    assay_method = ('Gene counts; no pathway analysis.\n' if assay == 'rnaseq_bulk' else
                    'Union consensus peaks; blacklist excluded. Global scaling assumes no global shift.\n')
    plan = ('# Analysis plan\nStatus: APPROVED\n\n## Goal\nCompare B with A in a small bulk study.\n'
            '## Inputs\nAnalysis starts from the supplied count matrix in 2-data/counts.tsv.\n'
            'No raw reads are supplied. files.csv lists each analysed library read count and the SHA-256\n'
            'of its feature-count column export in libraries/; read_count is the sum over supplied features.\n'
            'These are assigned reads, not a claim about total sequencing depth or upstream QC.\n'
            '## Method\nIndependent samples; condition-only model. Three biological replicates per arm.\n'
            'Processing runs balanced across arms; no pooling of subjects.\n'
            'Median-of-ratios size factors across features with positive counts in every sample.\n'
            'Transform log2(normalised count + 1); two-sided two-sample Student t-test, pooled variance, df = 4.\n'
            'BH across all 240 tested features; alpha 0.05; no filtering or shrinkage.\n'
            'Report mean normalised count and difference of mean log2 abundances (B minus A).\n'
            'Outliers retained; descriptive association only; no pathway or causal claims.\n' + assay_method +
            '## Outputs\n| File | Type | Description |\n|---|---|---|\n'
            '| de_results.csv | de_results | Differential table |\n\n## Execution\nRuns: batch\n')
    write_text(root / 'PLAN.md', plan)
    write_json(root / 'approval.json', {'actor': 'human', 'timestamp': '2026-09-25T00:00:00Z',
               'expiry': '2026-09-26T00:00:00Z', 'plan_sha256': sha256(plan.encode())})
    assay_qc = ('RNA QC: mapping rate, assigned-read fraction and inferred strandedness are unavailable from counts.\n'
                if assay == 'rnaseq_bulk' else
                'ATAC QC: FRiP, TSS enrichment and fragment-length periodicity are unavailable from counts.\n')
    write_text(root / 'qc.md', 'All six libraries retained. No outliers removed.\n' + assay_qc +
        'Count QC: 240 nonnegative integer features per library; library totals and checksums in files.csv.\n'
        'QC disposition DEGRADE: upstream read-level QC cannot be assessed; conclusions concern supplied counts only.\n'
        'QC disposition WARN: n = 3 per group limits precision and generalisation.\n')
    manifest = {'pipeline_commit': 'synthetic-v1', 'params': {'assay': assay,
                'unit_of_replication': 'sample', 'formula': 'condition',
                'execution_started_at': '2026-09-25T01:00:00Z', 'execution_finished_at': '2026-09-25T01:01:00Z',
                'contrast': 'B versus A', 'normalisation': 'median-of-ratios',
                'test': 'pooled Student t on log2(normalised count + 1)', 'df': 4,
                'alpha': '0.05', 'multiple_testing_scope': '240 tested features'}}
    write_json(root / 'manifest.json', manifest)
    evidence = {'id': 1, 'artifact_id': 1, 'source_id': None, 'kind': 'statistical',
                'relation': 'supports', 'source': None, 'artifact': {'id': 1,
                'path': '3-results/de_results.csv', 'sha256': sha256((root / 'de_results.csv').read_bytes())}}
    write_json(root / 'snapshot.json', {'run': {'id': 1, 'question': 'Is bulk abundance associated with condition?',
        'manifest_path': '3-results/manifest.json', 'manifest_sha256': sha256((root / 'manifest.json').read_bytes())},
        'claims': [{'id': 1, 'run_id': 1, 'type': 'OBSERVATION',
        'text': '%d of 240 features have BH adjusted p below 0.05: %d higher and %d lower in B; descriptive association, not causation.' % (sum(r[4] < .05 for r in results), sum(r[4] < .05 and r[1] > 0 for r in results), sum(r[4] < .05 and r[1] < 0 for r in results)),
        'bio_support': {'statistical_support': 'BH across 240 features', 'replication': 'n = 3 biological replicates per group',
                        'effect_size': 'See differential table', 'orthogonal_assay': 'none', 'literature': 'not used'},
        'process_risk': {'data_quality': 'All libraries retained', 'confounding_risk': 'Processing balanced',
            'provenance_completeness': 'Library origins in provenance.csv', 'qc_disposition': 'DEGRADE',
            'limitation': 'Upstream read-level QC unavailable; conclusions concern supplied counts only. n = 3 per group limits precision; associations do not establish causation. Global scaling assumes no global shift.'},
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
