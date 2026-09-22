"""Row 15 disposable Git fixtures, fresh canaries, and explicit scratch (Python 3.6)."""
import base64
import binascii
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path
from support import REPO, mini_tree, run

HOOKS = REPO / 'gars/_system/hooks'
CONFIG = REPO / 'gars/.gitleaks.toml'
REAL_GITLEAKS = shutil.which('gitleaks')


def fresh_canary():
    return ('GARS_CANARY_' + secrets.token_hex(16)).encode('ascii')


def contains(data, canary):
    """Check raw bytes and decode embedded base64/hex tokens, up to five layers."""
    pending = [data]
    seen = set()
    for unused in range(6):
        following = []
        for block in pending:
            if canary in block:
                return True
            if block in seen:
                continue
            seen.add(block)
            for token in re.findall(rb'[A-Za-z0-9+/_-]{16,}={0,2}', block):
                for decoder in (lambda s: base64.b64decode(s, altchars=b'-_', validate=True),
                                binascii.unhexlify):
                    try:
                        following.append(decoder(token))
                    except (ValueError, binascii.Error):
                        pass
        pending = following
    return False


def scratch(case):
    folder = os.environ.get('TMPDIR')
    if not folder or not Path(folder).is_dir():
        case.skipTest('row 15 requires TMPDIR naming an existing scratch directory')
    temporary = tempfile.TemporaryDirectory(prefix='gars-secrets-', dir=folder)
    case.addCleanup(temporary.cleanup)
    return Path(temporary.name)


def checked(argv, root, stdin='', env=None):
    result = run(argv, root, stdin, env)
    if result.returncode:
        raise RuntimeError('fixture command failed: %s' % argv[0])
    return result.stdout.decode().strip()


def snapshot(root, parent=None):
    """Create objects without committing through any hook, only in disposable repos."""
    tree = checked(['git', 'write-tree'], root)
    argv = ['git', 'commit-tree', tree]
    if parent:
        argv += ['-p', parent]
    env = {'GIT_AUTHOR_NAME': 'Fixture', 'GIT_COMMITTER_NAME': 'Fixture',
           'GIT_AUTHOR_EMAIL': 'fixture', 'GIT_COMMITTER_EMAIL': 'fixture',
           'GIT_AUTHOR_DATE': '2000-01-01T00:00:00+0000',
           'GIT_COMMITTER_DATE': '2000-01-01T00:00:00+0000'}
    return checked(argv, root, 'disposable fixture\n', env)


def fixture(case):
    root = scratch(case) / 'repo'
    root.mkdir()
    mini_tree(root)
    shutil.copyfile(str(CONFIG), str(root / 'gars/.gitleaks.toml'))
    (root / 'clean.txt').write_text('ordinary input\n')
    checked(['git', 'add', '--', 'clean.txt'], root)
    base = snapshot(root)
    checked(['git', 'update-ref', 'refs/heads/fixture', base], root)
    checked(['git', 'symbolic-ref', 'HEAD', 'refs/heads/fixture'], root)
    hooks = root / 'hook-scripts'
    hooks.mkdir()
    for name in ('pre-commit', 'pre-push', 'install.py'):
        shutil.copyfile(str(HOOKS / name), str(hooks / name))
        (hooks / name).chmod(0o755)
    return root, hooks, base


def push_input(local, remote=None):
    return 'refs/heads/fixture %s refs/heads/fixture %s\n' % (local, remote or '0' * 40)


def standin(root, mode='scan'):
    """An isolated PATH: Git/Python plus a deterministic scanner, or no scanner."""
    folder = root / ('bin-' + mode)
    folder.mkdir(exist_ok=True)
    for name, target in [('git', shutil.which('git')), ('python3', sys.executable)]:
        path = folder / name
        if not path.exists():
            path.symlink_to(target)
    if mode != 'missing':
        script = folder / 'gitleaks'
        body = '''import base64, binascii, json, re, subprocess, sys, time
from pathlib import Path
args = sys.argv[1:]
Path('scanner-args.json').write_text(json.dumps(args))
if MODE == 'error': sys.exit(17)
if MODE == 'timeout': time.sleep(5)
if MODE == 'clean': sys.exit(0)
revision = next((a.split('=', 1)[1] for a in args if a.startswith('--log-opts=')), None)
cmd = ['git', 'log', '--format=', '-p', revision] if revision else ['git', 'diff', '--cached']
data = re.sub(rb'^\\+', b'', subprocess.check_output(cmd), flags=re.M)
blocks = [data]
for depth in range(6):
    more = []
    for block in blocks:
        if re.search(rb'GARS_CANARY_[0-9a-f]{32}', block): sys.exit(42)
        for token in re.findall(rb'[A-Za-z0-9+/=]{16,}', block):
            for decoder in (base64.b64decode, binascii.unhexlify):
                try: more.append(decoder(token))
                except (ValueError, binascii.Error): pass
    blocks = more
sys.exit(0)
'''
        script.write_text('#!' + sys.executable + '\nMODE = ' + repr(mode) + '\n' + body)
        script.chmod(0o755)
    return {'PATH': str(folder)}
