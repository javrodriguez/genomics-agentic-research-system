#!/usr/bin/env python3
"""Suite-only instrument self-test; never a registered scientific wrapper."""
import argparse
import json
import os
from pathlib import Path
import random
import sys

WORKSPACE = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORKSPACE / '_system'))
import wrapperlib as wl

ASSAY = 'rerun-fixture'
SUBSTAGE = '01_rerun-fixture'


def worker(seed):
    rng = random.Random(seed)
    rows = [('a', 1), ('b', 2), ('c', 3), ('d', 4)]
    rng.shuffle(rows)
    reverse = rng.choice([False, True])
    text = ['value\tid' if reverse else 'id\tvalue']
    for key, base in rows:
        value = '%.12f' % (base + rng.uniform(-1e-7, 1e-7))
        text.append(value + '\t' + key if reverse else key + '\t' + value)
    Path('numeric.tsv').write_text('\n'.join(text) + '\n')
    Path('stable.txt').write_text('id\tvalue\na\t1\nb\t2\n')
    Path('versions.json').write_text(json.dumps({'python': sys.version.split()[0]}))
    Path('seed.json').write_text(json.dumps({'source': 'os.urandom(16)', 'seed': seed}))


def main():
    # Only the suite installs this under a disposable wrapper root with this marker.
    if not (WORKSPACE.parent / '.rerun-self-test').is_file():
        raise SystemExit('fixture is available only in the disposable instrument self-test')
    parser = argparse.ArgumentParser()
    parser.add_argument('verb', choices=['check', 'prepare', 'collect', 'worker'])
    parser.add_argument('--project', type=Path)
    parser.add_argument('--model', default='none')
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    if args.verb == 'worker':
        worker(args.seed)
        return
    project = args.project
    stage = project / '02_bioinformatics' / ASSAY / SUBSTAGE
    original_schema = wl.manifest_schema
    def schema():
        value = original_schema()
        value['wrappers'][ASSAY] = dict(name=ASSAY, assay=ASSAY, kind='local', substage=SUBSTAGE)
        return value
    wl.manifest_schema = schema
    seed = int.from_bytes(os.urandom(16), 'big')
    original_facts = wl.prepare_manifest_facts
    def facts(*values):
        result = original_facts(*values)
        result.update(random_seeds=[dict(call='random.Random', seed=seed, source='os.urandom(16)')],
                      **{'no-rng-in-code-path': False, 'seed_source': 'os.urandom(16)'})
        return result
    wl.prepare_manifest_facts = facts
    if args.verb in ('prepare', 'check'):
        config = project / '_config' / (ASSAY + '.yaml')
        sheet = project / '01_samplesheets' / (ASSAY + '_samplesheet.csv')
        failures = []
        wl.check_run_dir(stage, failures)
        if failures or not config.is_file() or not sheet.is_file():
            raise SystemExit('fixture preflight failed')
        if args.verb == 'check':
            return
        stage.mkdir(parents=True, exist_ok=True)
        (stage / 'logs').mkdir(exist_ok=True)
        body = '"%s" "%s" worker --seed %d' % (sys.executable, Path(__file__).resolve(), seed)
        wl.write_submit_sh(stage, WORKSPACE, wl.read_config(config), project.name, ASSAY, body)
        wl.write_reproducibility(stage, ASSAY, WORKSPACE,
                                 {'config': config, 'samplesheet': sheet}, [('noise', 'uniform_1e-7')])
    else:
        wl.require_collect_config(project, ASSAY, SUBSTAGE)
        (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n'
            'table\tnative\trun/stable.txt\nfixture_numeric\tnative\trun/numeric.tsv\n')
        wl.complete_manifest(stage, args.model, 'COMPLETE')
        wl.write_status(stage, 'COMPLETE')


if __name__ == '__main__':
    main()
