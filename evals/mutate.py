#!/usr/bin/env python3
"""R-164 sealed-mutation runner. See MUTANTS-INTERFACE.md; Python 3.6 stdlib."""
import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def tree_hash(root):
    """Names, file bytes, modes and symlink targets; never follow symlinks or hash .git."""
    digest = hashlib.sha256()
    digest.update(str(stat.S_IMODE(root.lstat().st_mode)).encode())
    def visit(folder):
        for path in sorted(folder.iterdir()):
            if path == root / '.git':
                continue
            info = path.lstat()
            digest.update(json.dumps([str(path.relative_to(root)),
                                     stat.S_IMODE(info.st_mode)], sort_keys=True).encode())
            if path.is_symlink():
                digest.update(b'L' + os.readlink(str(path)).encode())
            elif path.is_dir():
                digest.update(b'D')
                visit(path)
            elif path.is_file():
                digest.update(b'F' + hashlib.sha256(path.read_bytes()).digest())
            else:
                raise ValueError('unsupported filesystem entry')
    visit(root)
    return digest.hexdigest()


def assert_unchanged(root, before):
    if tree_hash(root) != before:
        raise RuntimeError('tree differs after run; REFUSED')


def copy_tree(source, target):
    shutil.copytree(str(source), str(target), symlinks=True,
                    ignore=lambda folder, names: ['.git'] if Path(folder) == source else [])


def restore_tree(snapshot, target):
    shutil.rmtree(str(target))
    copy_tree(snapshot, target)


def execute(argv, root, stdin='', timeout=300):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    env.pop('GARS_SEALED_MUTANTS_DIR', None)
    argv = [sys.executable if arg == '{python}' else arg for arg in argv]
    result = subprocess.run(argv, cwd=str(root), input=stdin.encode(), env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    return {'returncode': result.returncode,
            'stdout': result.stdout.decode('utf-8', 'replace'),
            'stderr': result.stderr.decode('utf-8', 'replace')}


def suite(root):
    result = execute([sys.executable, 'tests/run_tests.py'], root)
    text = result['stdout'] + '\n' + result['stderr']
    counts = re.findall(r'^collected (\d+) tests from (tests|gars/tests)$', text, re.M)
    if set(tree for count, tree in counts if int(count) > 0) != {'tests', 'gars/tests'}:
        raise RuntimeError('suite did not collect both nonempty trees')
    if not re.search(r'^Ran [1-9]\d* tests?\b', text, re.M):
        raise RuntimeError('suite printed no nonzero unittest summary')
    failure = (re.search(r'^first failing test: (.+)$', result['stderr'], re.M) or
               re.search(r'^(?:FAIL|ERROR): (.+)$', result['stderr'], re.M))
    if result['returncode'] and not failure:
        raise RuntimeError('suite failed without a failing test name')
    return result['returncode'], failure.group(1) if failure else None


def diff_paths(text):
    """Only existing, ordinary, in-scope files; no renames or traversal."""
    if re.search(r'^(?:diff --git|index |old mode|new mode|rename |copy |deleted file|new file|Binary|GIT binary)', text, re.M):
        raise ValueError('use plain unified diff without Git extended headers')
    old = re.findall(r'^--- a/(\S+)$', text, re.M)
    new = re.findall(r'^\+\+\+ b/(\S+)$', text, re.M)
    if not old or old != new or len(set(old)) != len(old):
        raise ValueError('diff needs matching --- a/path and +++ b/path headers')
    if len(re.findall(r'^--- ', text, re.M)) != len(old) or \
            len(re.findall(r'^\+\+\+ ', text, re.M)) != len(new):
        raise ValueError('unsupported diff headers')
    for name in old:
        path = Path(name)
        if '..' in path.parts or path.is_absolute() or not (
                name.startswith('gars/_system/') or name.startswith('gars/02_bioinformatics/')):
            raise ValueError('diff outside mutant scope')
    return old


def syntax(path):
    if path.suffix != '.py':
        return None
    # Docstrings/comments/formatting alone are never a semantic mutation.
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.body and isinstance(node.body[0], ast.Expr) and \
                    ast.get_docstring(node, clean=False) is not None:
                node.body.pop(0)
    return ast.dump(tree, include_attributes=False)


def validate_expected(expected):
    if not isinstance(expected, dict) or \
            set(expected) != {'id', 'requirement', 'description', 'probe', 'before', 'after'}:
        raise ValueError('expected.json fields do not match interface')
    for field in ('id', 'requirement', 'description'):
        if not isinstance(expected[field], str) or not expected[field].strip():
            raise ValueError('expected.json needs nonempty ' + field)
    if not re.match(r'^R-\d{3}$', expected['requirement']):
        raise ValueError('requirement must be R-NNN')
    probe = expected['probe']
    if not isinstance(probe, dict) or set(probe) != {'argv', 'stdin'} or \
            not isinstance(probe['stdin'], str) or \
            not isinstance(probe['argv'], list) or not probe['argv'] or \
            not all(isinstance(arg, str) for arg in probe['argv']):
        raise ValueError('invalid semantic probe')
    for key in ('before', 'after'):
        observation = expected[key]
        if not isinstance(observation, dict) or \
                set(observation) != {'returncode', 'stdout', 'stderr'} or \
                type(observation['returncode']) is not int or \
                not all(isinstance(observation[k], str) for k in ('stdout', 'stderr')):
            raise ValueError('invalid probe observation')
    if expected['before'] == expected['after']:
        raise ValueError('semantic probe must predict different behaviour')


def measure_one(snapshot, target, mutant, run_sha):
    snapshot, target = snapshot.resolve(), target.resolve()
    expected = json.loads((mutant / 'expected.json').read_text())
    validate_expected(expected)
    if expected['id'] != mutant.name:
        raise ValueError('id must match folder name')
    patch = (mutant / 'mutant.diff').read_text()
    paths = diff_paths(patch)
    before = tree_hash(target)
    record = {'id': mutant.name, 'requirement': expected['requirement'],
              'run_sha': run_sha, 'status': 'ineffective', 'test': None}
    try:
        original_syntax = {}
        for name in paths:
            path = target / name
            lineage = [target.joinpath(*Path(name).parts[:i])
                       for i in range(1, len(Path(name).parts) + 1)]
            if not path.is_file() or any(p.is_symlink() for p in lineage):
                raise ValueError('mutant target must be an ordinary existing file')
            original_syntax[name] = syntax(path)
        probe = expected['probe']
        observed_before = execute(probe['argv'], target, probe['stdin'])
        # Probes are read-only: side effects cannot masquerade as mutant behaviour.
        assert_unchanged(target, before)
        if observed_before != expected['before']:
            raise ValueError('baseline semantic probe does not match expected.json')
        applied = execute(['git', 'apply', '--check', '-'], target, patch)
        if applied['returncode']:
            raise ValueError('mutant diff does not apply')
        applied = execute(['git', 'apply', '-'], target, patch)
        if applied['returncode']:
            raise ValueError('mutant diff application failed')
        # Extended headers were refused; plain unified diffs must retain each target.
        for name in paths:
            if not (target / name).is_file():
                raise ValueError('mutant deleted a target')
        changed = tree_hash(target)
        if all(original_syntax[name] is not None and
               original_syntax[name] == syntax(target / name) for name in paths):
            record['reason'] = 'text-only Python change'
            return record
        observed_after = execute(probe['argv'], target, probe['stdin'])
        assert_unchanged(target, changed)
        if observed_after == observed_before:
            record['reason'] = 'semantic probe unchanged'
            return record
        if observed_after != expected['after']:
            raise ValueError('mutated semantic probe does not match expected.json')
        code, first = suite(target)
        record.update(status='killed' if code else 'survived', test=first)
        return record
    finally:
        restore_tree(snapshot, target)
        assert_unchanged(target, before)


def measure(root, directory):
    dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain',
                                     '--untracked-files=all'])
    if dirty:
        raise ValueError('source checkout must be clean so run_sha identifies the tested tree')
    source_hash = tree_hash(root)
    run_sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD']).decode().strip()
    mutants = sorted(p for p in directory.iterdir() if p.is_dir())
    if not mutants:
        raise ValueError('sealed directory is empty')
    scratch = os.environ.get('TMPDIR')
    if not scratch or not Path(scratch).is_dir():
        raise ValueError('TMPDIR must name an existing scratch directory')
    if root == Path(scratch).resolve() or root in Path(scratch).resolve().parents:
        raise ValueError('scratch must be outside the source tree')
    try:
        with tempfile.TemporaryDirectory(prefix='gars-mutants-', dir=scratch) as temporary:
            snapshot, target = Path(temporary) / 'snapshot', Path(temporary) / 'tree'
            copy_tree(root, snapshot)
            copy_tree(snapshot, target)
            baseline = tree_hash(target)
            code, first = suite(target)
            assert_unchanged(target, baseline)
            if code:
                raise RuntimeError('baseline suite failed: ' + first)
            records = [measure_one(snapshot, target, mutant, run_sha) for mutant in mutants]
    finally:
        assert_unchanged(root, source_hash)
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require', action='store_true')
    args = parser.parse_args()
    directory = os.environ.get('GARS_SEALED_MUTANTS_DIR')
    if not directory:
        print('unmeasured')
        return 1 if args.require else 0
    try:
        records = measure(REPO, Path(directory).resolve())
        for record in records:
            print(json.dumps(record, sort_keys=True))
        killed = sum(record['status'] == 'killed' for record in records)
        print('%d/%d killed/total' % (killed, len(records)))
        return 1 if args.require and (len(records) != 10 or killed < 8 or
                                     any(r['status'] == 'ineffective' for r in records)) else 0
    except (OSError, ValueError, SyntaxError, RuntimeError, subprocess.SubprocessError) as exc:
        print('mutation runner: REFUSED (%s)' % exc, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
