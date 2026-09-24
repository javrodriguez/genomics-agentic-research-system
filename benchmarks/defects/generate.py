#!/usr/bin/env python3
"""Seeded producer-authored development inputs; never constructs sealed fixtures."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import random

SEED = 801
REAL_DOI = '10.1038/nmeth.1618'
DATACITE_DOI = '10.5281/zenodo.3727209'
FAKE_DOI = '10.5555/gars-fabricated-801-1'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')


def table(path, pairs=None, precision=False, note=False):
    pairs = pairs if pairs is not None else [(0.01, 0.02), (0.04, 0.04)]
    with path.open('w', newline='') as handle:
        writer = csv.writer(handle, lineterminator='\n')
        writer.writerow(['gene', 'baseMean', 'log2FoldChange', 'pvalue', 'padj'] +
                        (['plant_note'] if note else []))
        for i, (p, q) in enumerate(pairs):
            values = [('%.6g' % x if precision else repr(x)) if x is not None else ''
                      for x in (p, q)]
            writer.writerow(['g%d' % i, 10, 2] + values + (['synthetic'] if note else []))


def project(root, assay='rnaseq_bulk', extra=None, conditions=None, zipped=False, lanes=1):
    conditions = conditions or ['A', 'A', 'B', 'B']
    extra = extra or {}
    rng = random.Random(SEED)
    data = root / '00_data' / assay
    (data / 'raw').mkdir(parents=True, exist_ok=True)
    (root / '_config').mkdir(exist_ok=True)
    (root / '_config' / (assay + '.yaml')).write_text(
        'strandedness: auto\nunit_of_replication: sample\nreference_release: synthetic-v1\n')
    samples, files = [], []
    for i, condition in enumerate(conditions):
        sid = 'DEV%04d' % rng.randrange(1000, 9999)
        samples.append([sid, condition, condition, conditions[:i].count(condition) + 1] +
                       [v[i] for v in extra.values()])
        index = extra.get('library_index', ['ACGTACGT'] * len(conditions))[i]
        for lane in range(1, lanes + 1):
            path = data / 'raw' / ('%s_L%03d_R1.fastq%s' % (sid, lane, '.gz' if zipped else ''))
            content = ('@DEV:1:FLOW:%d:1:1:1 1:N:0:%s\nACGT\n+\nIIII\n' % (lane, index)).encode()
            if zipped:
                with path.open('wb') as handle:
                    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as gz:
                        gz.write(content)
            else:
                path.write_bytes(content)
            files.append([sid, str(lane), path.relative_to(root).as_posix(), ''])
    for name, header, rows in (
            ('samples.csv', ['sample_id', 'condition', 'group', 'replicate'] + list(extra), samples),
            ('files.csv', ['sample_id', 'lane', 'fastq_1', 'fastq_2'], files)):
        with (data / name).open('w', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerows([header] + rows)
    return data


def claims(root, reference=REAL_DOI, missing=False):
    tree = root / 'project'
    tree.mkdir(exist_ok=True)
    artifact = tree / 'evidence.tsv'
    artifact.write_text('gene\tvalue\ng1\t1\n')
    snapshot = {
        'run': {'id': 1, 'question': 'Synthetic development question', 'exploratory': False},
        'claims': [{'id': 1, 'run_id': 1, 'type': 'OBSERVATION',
                    'text': 'Synthetic table has one row.', 'bio_support': {},
                    'process_risk': {}, 'reference_release': 'synthetic-v1',
                    'workflow_version': 'synthetic-v1',
                    'links': [{'claim_id': 1, 'evidence_id': 1}, {'claim_id': 1, 'evidence_id': 2}],
                    'evidence': [
                        {'id': 1, 'kind': 'computational', 'relation': 'supports',
                         'artifact_id': 1, 'source_id': None, 'source': None,
                         'artifact': {'id': 1, 'path': 'missing.tsv' if missing else 'evidence.tsv',
                                      'sha256': hashlib.sha256(artifact.read_bytes()).hexdigest()}},
                        {'id': 2, 'kind': 'literature', 'relation': 'supports',
                         'artifact_id': None, 'artifact': None, 'source_id': 1,
                         'source': {'id': 1, 'reference': reference}}]}]}
    write_json(root / 'snapshot.json', snapshot)
    write_json(root / 'manifest.json', {})
    return snapshot


def generate(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for cid in range(1, 10):
        root = destination / ('d%02d' % cid)
        root.mkdir(exist_ok=True)
        if cid <= 6:
            extras = {1: {'batch': ['x', 'x', 'y', 'y']},
                      3: {'sex': ['F', 'F', 'M', 'M']},
                      4: {'cell_barcode': ['c1', 'c2', 'c3', 'c4']},
                      5: {'library_index': ['ACGTACGT'] * 4}}.get(cid)
            data = project(root, extra=extras, conditions=['A', 'B', 'B'] if cid == 2 else None,
                           assay='atacseq_bulk' if cid == 2 else 'rnaseq_bulk', zipped=cid == 6)
            if cid == 5:
                for path in (data / 'raw').iterdir():
                    path.write_bytes(path.read_bytes().replace(b'ACGTACGT', b'TTGACCAA'))
            if cid == 6:
                path = sorted((data / 'raw').iterdir())[0]
                with path.open('wb') as handle:
                    with gzip.GzipFile(filename='', mode='wb', fileobj=handle, mtime=0) as gz:
                        gz.write(b'@DEV\nACGT\n+\n')
        elif cid == 8:
            table(root / 'de_results.csv', [(0.01, 0.01), (0.04, 0.04)])
        else:
            claims(root, reference=FAKE_DOI if cid == 9 else REAL_DOI, missing=cid == 7)
    extras = [
        {}, {'batch': ['x', 'y', 'x', 'y']},
        {'subject': ['d1', 'd2', 'd3', 'd4']},
        {'biological_unit': ['d1', 'd2', 'd3', 'd4']},
        {'sex': ['F', 'M', 'F', 'M']}, {'age': ['20', '22', '22', '24']},
        {'library_index': ['ACGTACGT'] * 4},
        {'sex': ['unknown'] * 4, 'age': [''] * 4},
        {'library_index': ['ACGTACGT+TTGACCAA'] * 4},
        {'batch': ['x', 'y', 'x', 'y'], 'subject': ['d1', 'd2', 'd3', 'd4'],
         'sex': ['F', 'M', 'F', 'M'], 'age': ['20', '22', '22', '24'],
         'library_index': ['ACGTACGT'] * 4}]
    for i, extra in enumerate(extras):
        root = destination / ('c%02d' % (i + 1))
        project(root, assay='rnaseq_bulk' if i % 2 == 0 else 'atacseq_bulk',
                extra=extra, zipped=i % 3 == 0, lanes=2 if i == 8 else 1)
        pairs = [(0.0041234567, 0.0123703701), (0.037654321, 0.0564814815), (0.8, 0.8)]
        if i == 2:
            pairs = [(0.1, 0.1)]
        table(root / 'de_results.csv', pairs, precision=i == 1, note=i == 9)
        claims(root, reference=DATACITE_DOI if i == 9 else REAL_DOI)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    generate(parser.parse_args().destination)
