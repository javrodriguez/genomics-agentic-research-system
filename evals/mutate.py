#!/usr/bin/env python3
"""R-164 sealed-mutation runner. See MUTANTS-INTERFACE.md; Python 3.6 stdlib."""
import argparse
import ast
import hashlib
import io
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
SUITE_TIMEOUT = 1800  # whole-suite runs only; probes and git keep execute()'s 300 s (0110)


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
    """Copy the tested tree with its repository (0110): tests may read history and HEAD."""
    shutil.copytree(str(source), str(target), symlinks=True)


def committed_tree(root, run_sha, target):
    """Materialize Git objects, never working-tree files or export attributes."""
    entries = subprocess.check_output(
        ['git', '-C', str(root), 'ls-tree', '-rz', '--full-tree', run_sha]).split(b'\0')
    blobs = []
    for entry in filter(None, entries):
        metadata, name = entry.split(b'\t', 1)
        mode, kind, oid = metadata.split()
        if kind != b'blob' or mode not in (b'100644', b'100755', b'120000'):
            raise ValueError('unsupported committed entry: ' + os.fsdecode(name))
        blobs.append((mode, oid, os.fsdecode(name)))
    result = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'],
                            input=b''.join(oid + b'\n' for mode, oid, name in blobs),
                            stdout=subprocess.PIPE, check=True)
    stream = io.BytesIO(result.stdout)
    target.mkdir()
    for mode, oid, name in blobs:
        actual_oid, kind, size = stream.readline().split()
        if actual_oid != oid or kind != b'blob':
            raise RuntimeError('committed blob lookup mismatch')
        content = stream.read(int(size))
        if len(content) != int(size) or stream.read(1) != b'\n':
            raise RuntimeError('truncated committed blob')
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == b'120000':
            path.symlink_to(os.fsdecode(content))
        else:
            path.write_bytes(content)
            path.chmod(0o755 if mode == b'100755' else 0o644)


def git_quiet(root, *args):
    return subprocess.run(['git', '-C', str(root)] + list(args), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True).stdout


def attach_history(root, run_sha, snapshot):
    """Give the materialized tree its repository (0110): the files stay exactly run_sha's
    committed objects (committed_tree); only a .git cloned from the source is added, with HEAD
    detached at run_sha and the index read from it, so the tree is clean at run_sha."""
    history = snapshot.parent / 'history'
    subprocess.run(['git', 'clone', '-q', '--no-local', '--no-checkout', str(root), str(history)],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    os.rename(str(history / '.git'), str(snapshot / '.git'))
    history.rmdir()
    git_quiet(snapshot, 'remote', 'remove', 'origin')
    git_quiet(snapshot, 'update-ref', '--no-deref', 'HEAD', run_sha)
    git_quiet(snapshot, 'read-tree', run_sha)
    subprocess.run(['git', '-C', str(snapshot), 'update-index', '-q', '--refresh'],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if git_quiet(snapshot, 'status', '--porcelain', '--untracked-files=all'):
        raise RuntimeError('materialized tree differs from run_sha')


MUTANT_IDENTITY = ['-c', 'user.name=GARS mutation runner', '-c', 'user.email=mutation-runner@invalid',
                   '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null']


def commit_mutant(target, mutant_id):
    """Commit the applied mutant inside the throwaway tested tree (0110), so the suite sees a clean
    checkout at a new HEAD: a test that reads git status or diffs the working tree cannot fail
    merely because the tree is dirty. A tree without a repository is left as it is."""
    if not (target / '.git').is_dir():
        return
    env_dates = ['env', 'GIT_AUTHOR_DATE=2000-01-01T00:00:00Z', 'GIT_COMMITTER_DATE=2000-01-01T00:00:00Z']
    for argv in (['git', 'add', '-A'],
                 env_dates + ['git'] + MUTANT_IDENTITY + ['commit', '-q', '--no-verify', '-m',
                                                         'mutant ' + mutant_id]):
        result = execute(argv, target)
        if result['returncode']:
            raise RuntimeError('mutant commit failed')
    if execute(['git', 'status', '--porcelain', '--untracked-files=all'], target)['stdout']:
        raise RuntimeError('tested tree not clean after the mutant commit')


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


def suite(root, log_path=None, binding=None):
    result = execute([sys.executable, 'tests/run_tests.py'], root, timeout=SUITE_TIMEOUT)
    if log_path is not None:
        evidence = dict(binding or {}, **result)
        log_path.write_text(json.dumps(evidence, sort_keys=True, indent=2) + '\n')
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


def measure_one(snapshot, target, mutant, run_sha, evidence_dir=None):
    snapshot, target = snapshot.resolve(), target.resolve()
    expected = json.loads((mutant / 'expected.json').read_text())
    validate_expected(expected)
    if expected['id'] != mutant.name:
        raise ValueError('id must match folder name')
    patch = (mutant / 'mutant.diff').read_text()
    paths = diff_paths(patch)
    before = tree_hash(target)
    record = {'id': mutant.name, 'requirement': expected['requirement'],
              'run_sha': run_sha, 'status': 'ineffective', 'test': None,
              'snapshot_hash': before,
              'mutant_diff_sha256': hashlib.sha256((mutant / 'mutant.diff').read_bytes()).hexdigest(),
              'expected_sha256': hashlib.sha256((mutant / 'expected.json').read_bytes()).hexdigest()}
    if evidence_dir is not None:
        record.update(baseline_log=str(evidence_dir / 'baseline.json'), suite_log=None)

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
        log_path = evidence_dir / ('mutant-' + mutant.name + '.json') if evidence_dir is not None else None
        binding = {key: record[key] for key in
                   ('id', 'requirement', 'run_sha', 'snapshot_hash',
                    'mutant_diff_sha256', 'expected_sha256')}
        binding.update(stage='mutant', tested_tree_hash=changed)
        commit_mutant(target, mutant.name)
        code, first = suite(target, log_path, binding)
        if log_path is not None:
            record['suite_log'] = str(log_path)
        record.update(status='killed' if code else 'survived', test=first)
        return record
    finally:
        restore_tree(snapshot, target)
        assert_unchanged(target, before)


def measure(root, directory):
    dirty = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain',
                                     '--untracked-files=all'])
    if dirty:
        raise ValueError('source checkout must be clean; only committed objects are tested')
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
    evidence_dir = Path(tempfile.mkdtemp(prefix='gars-mutation-logs-', dir=scratch)).resolve()
    print('mutation suite logs: ' + str(evidence_dir), file=sys.stderr, flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix='gars-mutants-', dir=scratch) as temporary:
            snapshot, target = Path(temporary) / 'snapshot', Path(temporary) / 'tree'
            committed_tree(root, run_sha, snapshot)
            attach_history(root, run_sha, snapshot)
            copy_tree(snapshot, target)
            baseline = tree_hash(target)
            code, first = suite(target, evidence_dir / 'baseline.json',
                                {'run_sha': run_sha, 'snapshot_hash': baseline,
                                 'stage': 'baseline', 'tested_tree_hash': baseline})
            assert_unchanged(target, baseline)
            if code:
                raise RuntimeError('baseline suite failed: ' + first)
            records = [measure_one(snapshot, target, mutant, run_sha, evidence_dir)
                       for mutant in mutants]
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
