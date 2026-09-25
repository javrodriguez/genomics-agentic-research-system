"""Disposable unittest support; synthetic data is never published as evidence."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import build_cases
from common import BASE_SHA, PROMPT_PATH, REPO, git, sha256, write_json
import run_reviews


def temporary(test):
    resource = tempfile.TemporaryDirectory(prefix='t-')
    test.addCleanup(resource.cleanup)
    return Path(resource.name).resolve()


def finding(**changes):
    result = dict(id='f1', severity='MINOR', file='gars/sample.py',
                  line_start=10, line_end=10, summary='Incorrect boundary', evidence='Concrete witness')
    result['class'] = 'off-by-one'
    result.update(changes)
    return result


def record(neutral, prompt_sha, model='stub-model', attempt=1):
    return {'review': {'verdict': 'APPROVE', 'findings': []}, 'envelope': {
        'schema_version': 1, 'case': neutral, 'repo_head': 'a' * 40, 'repo_parent': 'b' * 40,
        'host_digest': 'c' * 64, 'sandbox_settings_sha256': 'd' * 64,
        'reviewer': {'uid': 41231, 'os_user': 'synthetic-reviewer', 'model_id': model,
                     'prompt_path': PROMPT_PATH, 'prompt_sha256': prompt_sha,
                     'session_id': 'synthetic-session', 'tool': 'claude', 'tool_version': 'stub-1',
                     'login_entry': 1, 'attempt': attempt},
        'producer': {'uid': 41232, 'os_user': 'synthetic-producer'},
        'started_at': '2000-01-01T00:00:00Z', 'finished_at': '2000-01-01T00:00:01Z',
        'exit_code': 0, 'ended_on_usage_limit': False, 'blindness': {'calls': 0, 'hits': 0, 'ambiguous': 0}}}


def launcher_fixture(test, count=2):
    root = temporary(test)
    cases = root / 'input'
    ids = ['%012x' % (n + 1) for n in range(count)]
    for neutral in ids:
        repo = cases / neutral / 'repo'
        repo.mkdir(parents=True)
        git(repo, 'init', '--quiet', '--template=')
        git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        (repo / 'module.py').write_text('value = 1\n')
        parent = build_cases.commit(repo, 'Initial source snapshot')
        (repo / 'module.py').write_text('value = 2\n')
        build_cases.commit(repo, 'Adjust default value', parent)
    prompt = root / 'brief'
    prompt.write_text('Synthetic brief for a stub executable.\n')
    manifest = {'cases': ids, 'prompt_path': PROMPT_PATH, 'prompt_sha256': sha256(prompt.read_bytes()),
                'base_sha': BASE_SHA, 'harness_commit': 'd' * 40}
    write_json(root / 'manifest.json', manifest)
    settings = root / 'settings.json'
    settings.write_text('{}\n')
    args = SimpleNamespace(cases=str(cases), manifest=str(root / 'manifest.json'), prompt=str(prompt),
                           kits_root=str(root / 'k'), records=str(root / 'r'), model='stub-model',
                           producer_account='synthetic-producer', login_entry=1, only=None, settings=str(settings))
    return root, args, manifest


def stub(root, review=None, events=None, symlink=False):
    folder = root / 'bin'
    folder.mkdir(exist_ok=True)
    review = review or {'verdict': 'APPROVE', 'findings': []}
    events = events if events is not None else [{'type': 'system', 'subtype': 'init', 'model': 'stub-model'}]
    source = '#!' + sys.executable + '\nimport json, os, sys\nfrom pathlib import Path\n'
    source += "if '--version' in sys.argv:\n    print('stub-1')\n    sys.exit(0)\n"
    source += "Path('invocation.json').write_text(json.dumps({'argv':sys.argv, 'env':dict(os.environ), 'stdin':sys.stdin.read()}))\n"
    source += "Path('payload.json').write_text(%r)\n" % json.dumps(review)
    if symlink:
        source += "Path('review.json').symlink_to('payload.json')\n"
    else:
        source += "Path('review.json').write_bytes(Path('payload.json').read_bytes())\n"
    for event in events:
        source += 'print(%r)\n' % json.dumps(event)
    executable = folder / 'claude'
    executable.write_text(source)
    executable.chmod(0o755)


@contextlib.contextmanager
def launch_context(root):
    uid = os.getuid()
    env = {'PATH': str(root / 'bin') + os.pathsep + os.defpath,
           'TMPDIR': str(root), 'TMP': str(root), 'TEMP': str(root),
           'CLAUDE_POISON': 'removed', 'ANTHROPIC_POISON': 'removed', 'TMP_POISON': 'removed'}
    with mock.patch.dict(os.environ, env, clear=True), \
            mock.patch.object(run_reviews.pwd, 'getpwnam', return_value=SimpleNamespace(
                pw_uid=uid + 1, pw_name='synthetic-producer')), \
            mock.patch.object(run_reviews, 'host_digest', return_value='c' * 64):
        yield


def score_fixture(test):
    root = temporary(test)
    answers = root / 'answers'
    answers.mkdir()
    salt = 'e' * 32
    mapping = {}
    for cid, kind, cls in [('P01', 'plant', 'off-by-one'), ('C01', 'clean', None)]:
        path = answers / cid
        path.mkdir()
        expected = {'id': cid, 'kind': kind, 'class': cls, 'base_sha': BASE_SHA,
                    'commit_message': 'Adjust matrix handling', 'seal_type': 'unsealed',
                    'requirement_ids': ['R-100'], 'mask_literals': ['PLACEHOLDER_ONLY_LITERAL']}
        if kind == 'plant':
            expected['match'] = dict(file='gars/sample.py', line_start=10, line_end=10, mode='file_lines')
            expected['min_severity'] = 'MINOR'
        write_json(path / 'expected.json', expected)
        (path / 'plant.diff').write_text('synthetic scorer input, never applied\n')
        neutral = build_cases.neutral_id(salt, cid)
        mapping[neutral] = {k: expected[k] for k in ('id', 'kind', 'class', 'seal_type', 'mask_literals')}
        mapping[neutral].update(expected_sha256=sha256((path / 'expected.json').read_bytes()),
                                plant_sha256=sha256((path / 'plant.diff').read_bytes()))
    manifest = dict(cases=list(mapping), base_sha=BASE_SHA, harness_commit='d' * 40,
                    prompt_path=PROMPT_PATH, prompt_sha256='f' * 64)
    key = dict(run_salt=salt, cases=mapping)
    records = root / 'r'
    records.mkdir()
    for neutral, entry in mapping.items():
        item = record(neutral, manifest['prompt_sha256'])
        if entry['kind'] == 'plant':
            item['review']['findings'] = [finding()]
        write_json(records / (neutral + '.record.json'), item)
    return root, key, manifest, answers, records


from case_sweep import base_blobs, case_leaks
