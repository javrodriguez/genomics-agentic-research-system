"""Shared byte, path and fixture contracts (Python 3.6, standard library)."""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

BASE_SHA = 'e59dfc088fc638a801f255fc0373c139f7afbac4'
PROMPT_PATH = 'gars/_references/prompts/review_faults_code.md'
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CLASSES = json.loads((HERE / 'classes.json').read_text(encoding='utf-8'))
SEALED = ('race', 'hardcoded-secret', 'weakened-criterion')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key')
            result[key] = value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=unique)


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n')


def git(root, *args, **kw):
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(root)] + list(args),
                                   stderr=subprocess.PIPE, **kw)


def within(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def relative_path(value):
    return (isinstance(value, str) and bool(value) and not os.path.isabs(value) and
            not value.startswith(chr(126)) and '\\' not in value and
            all(part not in ('', '.', chr(46) * 2) for part in value.split('/')))


def load_cases(roots):
    """Read answer directories; provenance hashes bind exactly these private inputs."""
    found = {}
    for root in roots:
        root = Path(root)
        paths = sorted(root.glob('P[0-9][0-9]')) + sorted(root.glob('C[0-9][0-9]'))
        for group in ('plants', 'clean'):
            paths += sorted((root / group).glob('[PC][0-9][0-9]'))
        for path in paths:
            expected = read_json(path / 'expected.json')
            required = {'id', 'kind', 'class', 'base_sha', 'commit_message',
                        'seal_type', 'requirement_ids'}
            if not isinstance(expected, dict) or not required.issubset(expected):
                raise ValueError('expected.json required fields')
            cid = expected['id']
            if cid != path.name or not re.fullmatch('[PC][0-9]{2}', cid) or cid in found:
                raise ValueError('duplicate or malformed case id')
            if expected['base_sha'] != BASE_SHA:
                raise ValueError('case base_sha differs from pinned base')
            kind = expected['kind']
            if kind not in ('plant', 'clean') or cid[0] != ('P' if kind == 'plant' else 'C'):
                raise ValueError('case kind mismatch')
            if expected['seal_type'] not in ('unsealed', 'independent_context', 'external_human_seal'):
                raise ValueError('invalid seal type')
            message = expected['commit_message']
            if not isinstance(message, str) or not message.strip() or '\n' in message or '\r' in message:
                raise ValueError('commit_message must be one nonempty line')
            if not isinstance(expected['requirement_ids'], list) or not all(
                    isinstance(x, str) and re.fullmatch('R-[0-9]{3}', x)
                    for x in expected['requirement_ids']):
                raise ValueError('invalid requirement ids')
            if not isinstance(expected.get('mask_literals', []), list) or not all(
                    isinstance(x, str) and x for x in expected.get('mask_literals', [])):
                raise ValueError('invalid mask literals')
            if kind == 'clean':
                if expected['class'] is not None:
                    raise ValueError('clean class must be null')
            else:
                if expected['class'] not in CLASSES:
                    raise ValueError('unknown plant class')
                match = expected.get('match', {})
                if set(match) != {'file', 'line_start', 'line_end', 'mode'}:
                    raise ValueError('plant match required')
                if not relative_path(match['file']) or match['mode'] not in ('file', 'file_lines'):
                    raise ValueError('invalid match file or mode')
                if not all(type(match[x]) is int and match[x] > 0 for x in ('line_start', 'line_end')):
                    raise ValueError('match lines must be positive integers')
                if match['line_end'] < match['line_start']:
                    raise ValueError('reversed match lines')
                if expected.get('min_severity', 'MINOR') not in ('NOTE', 'MINOR', 'MAJOR', 'BLOCKER'):
                    raise ValueError('invalid min_severity')
            found[cid] = {'expected': expected, 'path': path,
                          'expected_sha256': sha256((path / 'expected.json').read_bytes()),
                          'plant_sha256': sha256((path / 'plant.diff').read_bytes())}
    if not found:
        raise ValueError('no cases')
    return found
