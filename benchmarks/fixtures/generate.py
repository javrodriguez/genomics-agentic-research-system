#!/usr/bin/env python3
"""Rebuild only tuned-on synthetic design fixtures. No FASTQs or external data."""
import csv
import random
from pathlib import Path

SEED = 110112


def generate(destination):
    rng = random.Random(SEED)
    ids = ['S%04d' % n for n in rng.sample(range(1000, 9999), 8)]
    cases = {
        'batch-confounded': [(ids[i], 'control' if i < 4 else 'treated',
                              'batch_a' if i < 4 else 'batch_b', ids[i]) for i in range(8)],
        'single-replicate': [(ids[i], group, 'batch_a', ids[i])
                             for i, group in enumerate(['control', 'treated'])],
        'pseudoreplicates': [(ids[i], 'control' if i < 4 else 'treated', 'batch_a',
                              'donor_a' if i < 4 else 'donor_b') for i in range(8)],
    }
    destination.mkdir(parents=True, exist_ok=True)
    for name, rows in sorted(cases.items()):
        with (destination / (name + '.csv')).open('w', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            writer.writerow(['sample_id', 'condition', 'batch', 'biological_unit'])
            writer.writerows(rows)


if __name__ == '__main__':
    generate(Path(__file__).resolve().parent)
