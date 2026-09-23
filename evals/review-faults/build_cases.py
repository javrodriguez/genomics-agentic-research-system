"""Build anonymous two-commit repositories and keep the answer key separate."""
import argparse
import io
import os
import re
import secrets
import subprocess
import sys
import tarfile
from pathlib import Path
from common import BASE_SHA, HERE, PROMPT_PATH, REPO, git, load_cases, sha256, write_json


def neutral_id(salt, case_id):
    return sha256((salt + case_id).encode('ascii'))[:12]


def refuse_worktree(output):
    parent = Path(output).resolve()
    while not parent.exists():
        parent = parent.parent
    probe = subprocess.run(['git', '-C', str(parent), 'rev-parse', '--is-inside-work-tree'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if probe.returncode == 0 and probe.stdout.strip() == b'true':
        raise ValueError('output is inside a git work tree')


def base_archive(source, base_sha):
    entries = git(source, 'ls-tree', '-r', '--name-only', base_sha).decode().splitlines()
    if any(p.startswith('evals/review-faults/') for p in entries):
        raise ValueError('base contains answer-key-in-case tree')
    return git(source, 'archive', base_sha)


def export(archive, repo):
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        for member in tree.getmembers():
            path = repo / member.name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(tree.extractfile(member).read())
                path.chmod(member.mode)
            elif member.issym():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.symlink_to(member.linkname)
            else:
                raise ValueError('unsupported base archive entry')


def commit(repo, message, parent=None):
    git(repo, 'add', '--force', '--', '.')
    tree = git(repo, 'write-tree').decode().strip()
    env = dict(os.environ)
    for role in ('AUTHOR', 'COMMITTER'):
        env['GIT_' + role + '_NAME'] = 'GARS producer'
        env['GIT_' + role + '_EMAIL'] = 'producer@example.invalid'
        env['GIT_' + role + '_DATE'] = '2000-01-01T00:00:00+0000'
    args = ['commit-tree', tree, '-m', message]
    if parent:
        args += ['-p', parent]
    oid = git(repo, *args, env=env).decode().strip()
    git(repo, 'update-ref', 'refs/heads/main', oid)
    return oid


def build(output, roots=None, run_salt=None, source=REPO, base_sha=BASE_SHA):
    output = Path(output)
    refuse_worktree(output)
    if output.exists():
        raise ValueError('output already exists')
    roots = roots or [HERE / 'fixtures']
    cases = load_cases(roots)
    salt = run_salt or secrets.token_hex(16)
    if not re.fullmatch('[0-9a-f]{32}', salt):
        raise ValueError('salt must be 32 random hex digits')
    ids = {cid: neutral_id(salt, cid) for cid in cases}
    if len(set(ids.values())) != len(ids):
        raise ValueError('neutral id collision')
    archive = base_archive(source, base_sha)
    output.mkdir(parents=True)
    key = {'run_salt': salt, 'cases': {}}
    for cid in sorted(cases):
        answer = cases[cid]
        expected = answer['expected']
        neutral = ids[cid]
        repo = output / 'cases' / neutral / 'repo'
        repo.mkdir(parents=True)
        export(archive, repo)
        git(repo, 'init', '--quiet', '--template=')
        git(repo, 'symbolic-ref', 'HEAD', 'refs/heads/main')
        parent = commit(repo, 'Initial source snapshot')
        patch = (answer['path'] / 'plant.diff').read_bytes()
        try:
            git(repo, 'apply', '--check', '-', input=patch)
            git(repo, 'apply', '-', input=patch)
        except subprocess.CalledProcessError:
            raise ValueError('plant does not apply: ' + cid)
        commit(repo, expected['commit_message'], parent)
        # Rebuild the stat-free index; default index cache times otherwise vary.
        (repo / '.git/index').unlink()
        git(repo, 'read-tree', 'HEAD')
        # update-ref's reflogs can contain launch identity and wall-clock time.
        import shutil
        if (repo / '.git/logs').exists():
            shutil.rmtree(str(repo / '.git/logs'))
        key['cases'][neutral] = dict(
            {k: expected[k] for k in ('id', 'class', 'kind', 'seal_type')},
            expected_sha256=answer['expected_sha256'], plant_sha256=answer['plant_sha256'],
            mask_literals=expected.get('mask_literals', []))
    # A salt-keyed sort is a portable deterministic shuffle, with no salt in manifest.
    order = sorted(ids.values(), key=lambda n: sha256((salt + ':order:' + n).encode('ascii')))
    manifest = {'cases': order, 'base_sha': base_sha, 'prompt_path': PROMPT_PATH,
                'prompt_sha256': sha256((REPO / PROMPT_PATH).read_bytes()),
                'harness_commit': git(REPO, 'rev-parse', 'HEAD').decode().strip()}
    write_json(output / 'key.json', key)
    (output / 'key.json').chmod(0o600)
    write_json(output / 'manifest.json', manifest)
    return key, manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    roots = [HERE / 'fixtures']
    if os.environ.get('GARS_SEALED_REVIEW_FAULTS_DIR'):
        roots.append(Path(os.environ['GARS_SEALED_REVIEW_FAULTS_DIR']))
    try:
        key, manifest = build(args.out, roots)
        print('built %d anonymous repositories; keep key.json private' % len(manifest['cases']))
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print('build cases: REFUSED (' + str(exc) + ')', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
