"""Build anonymous science cases; private answers never enter a review folder."""
import argparse
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from bio_common import (HERE, REPO, BASE_SHA, PROMPT_PATH, CLASSES, sha256,
                        read_json, write_json, load_cases)
from bio_generate_base import BASES, LAYOUT, generate
from bio_gates import run_gates, GATE_NAMES

WORDS = ('plant', 'seal', 'fault', 'flaw', 'defect', 'fixture', 'expected', 'canary', 'harness')
FIXED_TIME = 946684800
CASE_IDS = ['%s%02d' % (kind, n) for kind in ('P', 'C') for n in range(100)]


def sweep(data, ids, manifest=False):
    """R2 exemptions are exact top-level JSON tokens, never substring removals."""
    if manifest:
        value = json.loads(data.decode('utf-8'))
        cleaned = []
        for key, item in value.items():
            target = 'commit' if key == 'harness_commit' else key
            if key == 'prompt_path' and item == PROMPT_PATH:
                item = 'brief'
            cleaned.append([target, item])
        data = json.dumps(cleaned, sort_keys=True).encode('utf-8')
    return [token for token in list(CLASSES) + list(set(ids) | set(CASE_IDS)) + list(WORDS) if token.encode() in data]


def fixed_tree(root):
    for path in sorted([root] + list(root.rglob('*'))):
        if path.is_symlink():
            raise ValueError('symlink refused')
        path.chmod(0o755 if path.is_dir() else 0o644)
        os.utime(str(path), (FIXED_TIME, FIXED_TIME))


def outside_git(path):
    for parent in [path] + list(path.parents):
        if (parent / '.git').exists():
            result = subprocess.run(['git', '-C', str(parent), 'rev-parse', '--is-inside-work-tree'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0 and result.stdout.strip() == b'true':
                return False
    return True


def build(out, roots=None, salt=None, log=None, quiet_ids=False):
    out = Path(out)
    if out.exists() or not outside_git(out.resolve()):
        raise ValueError('output exists or is inside a git work tree')
    roots = roots or [HERE / 'fixtures']
    cases = load_cases(roots)
    salt = salt or os.urandom(16).hex()
    if not re.fullmatch('[0-9a-f]{32}', salt):
        raise ValueError('invalid salt')
    mapping = {}
    for cid, case in sorted(cases.items()):
        neutral = sha256((salt + cid).encode('ascii'))[:12]
        if neutral in mapping:
            raise ValueError('neutral collision')
        expected = case['expected']
        mapping[neutral] = dict((k, expected[k]) for k in ('id', 'class', 'kind', 'seal_type'))
        mapping[neutral].update(expected_sha256=case['expected_sha256'], plant_sha256=case['plant_sha256'],
                                mask_literals=expected.get('mask_literals', []), gates={})
    out.mkdir(parents=True)
    (out / 'private').mkdir()
    key = {'run_salt': salt, 'cases': mapping}
    ids = list(cases)
    refused = False
    log_rows = []
    for neutral, entry in sorted(mapping.items()):
        case = cases[entry['id']]
        expected = case['expected']
        with tempfile.TemporaryDirectory(prefix='bb-') as folder:
            base = generate(Path(folder) / 'base', expected['base_project'], expected['base_seed'])
            patch = (case['path'] / 'plant.diff').read_bytes()
            if patch:
                result = subprocess.run(['git', 'apply', '-p1', '-'], cwd=str(base),
                                        input=patch, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode:
                    raise ValueError('patch does not apply')
            # Only mapped files may enter a case. Explicitly refuse answer files even if unmapped.
            for path in base.rglob('*'):
                if path.is_symlink() or path.name in ('expected.json', 'plant.diff', 'key', 'key.json'):
                    raise ValueError('answer file or symlink in case')
                if path.is_file() and path.relative_to(base).parts[0] not in LAYOUT:
                    raise ValueError('unmapped case file')
            gates, report = run_gates(base, BASES[expected['base_project']][0])
            entry['gates'] = gates
            failed = [name for name in GATE_NAMES if not gates.get(name)]
            log_rows.append({'id': entry['id'], 'gates': gates})
            if failed:
                refused = True
                if not quiet_ids:
                    print(entry['id'] + ': gate refused')
                continue
            project = out / 'cases' / neutral / 'project'
            for source, destination in LAYOUT.items():
                target = project / destination.format(assay=BASES[expected['base_project']][0])
                target.parent.mkdir(parents=True, exist_ok=True)
                if (base / source).is_dir():
                    shutil.copytree(str(base / source), str(target))
                else:
                    shutil.copyfile(str(base / source), str(target))
            (project / '4-report/report.md').write_text(report, encoding='utf-8')
    order = sorted(mapping)
    random.Random(salt).shuffle(order)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()
    manifest = {'cases': order, 'base_sha': BASE_SHA, 'prompt_path': PROMPT_PATH,
                'prompt_sha256': sha256((REPO / PROMPT_PATH).read_bytes()), 'harness_commit': commit}
    manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    hits = sweep(manifest_bytes, ids, manifest=True)
    hits.extend(sweep(out.name.encode(), ids))
    # Answer metadata is private. Sweep all public bytes and created names before writing the key.
    for path in out.rglob('*'):
        hits.extend(sweep(path.relative_to(out).as_posix().encode(), ids))
        if path.is_file():
            hits.extend(sweep(path.read_bytes(), ids))
    if log:
        write_json(log, {'cases': log_rows, 'sweep_hits': len(hits)})
    if hits:
        raise ValueError('forbidden case bytes')
    (out / 'manifest.json').write_bytes(manifest_bytes)
    write_json(out / 'private/key.json', key)
    fixed_tree(out)
    if refused:
        raise ValueError('gate refused')
    return manifest, key


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--log', required=True)
    parser.add_argument('--quiet-ids', action='store_true')
    args = parser.parse_args(argv)
    roots = [HERE / 'fixtures']
    sealed = os.environ.get('GARS_SEALED_BIO_FAULTS_DIR')
    if sealed:
        roots.append(Path(sealed))
    try:
        manifest, key = build(args.out, roots, log=args.log, quiet_ids=args.quiet_ids)
        print('cases %d; sweep hits 0' % len(manifest['cases']))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('build refused: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
