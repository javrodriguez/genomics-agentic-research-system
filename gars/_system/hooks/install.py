#!/usr/bin/env python3
"""Install into Git's current hook directory, preserving both existing hooks."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKER = b'GARS_ROW3_PRE_PUSH_V1'


def install(root):
    root = Path(root).resolve()
    configured = subprocess.run(['git', '-C', str(root), 'config', '--get', 'core.hooksPath'],
                                stdout=subprocess.PIPE)
    if configured.returncode not in (0, 1):
        raise RuntimeError('cannot read core.hooksPath')
    if configured.returncode == 0:
        folder = Path(configured.stdout.decode().strip())
    else:
        folder = Path(subprocess.check_output(
            ['git', '-C', str(root), 'rev-parse', '--git-path', 'hooks']).decode().strip())
    if not folder.is_absolute():
        folder = root / folder
    folder.mkdir(parents=True, exist_ok=True)
    # Preflight both before moving either; a differing marker always refuses.
    for name in ('pre-commit', 'pre-push'):
        target = folder / name
        source = Path(__file__).with_name(name)
        if target.is_file() and target.read_bytes() != source.read_bytes():
            if b'GARS_ROW' in target.read_bytes():
                raise RuntimeError('marker-bearing hook differs from shipped content; preserving it unchanged')
    for name in ('pre-push', 'pre-commit'):
        install_hook(folder, name)


def install_hook(folder, name):
    target = folder / name
    previous = folder / (name + '.gars-previous')
    source = Path(__file__).with_name(name)
    if target.is_symlink() and target.is_file() and b'GARS_ROW' in target.read_bytes():
        raise RuntimeError('existing GARS hook is a symlink; refusing a recursive chain')
    if target.exists() or target.is_symlink():
        if target.is_file() and not target.is_symlink() and target.read_bytes() == source.read_bytes():
            target.chmod(0o755)
            return
        if target.is_file() and b'GARS_ROW' in target.read_bytes():
            raise RuntimeError('marker-bearing hook differs from shipped content; preserving it unchanged')
        if previous.exists() or previous.is_symlink():
            raise RuntimeError('previous-hook backup exists; refusing to overwrite either hook')
        if not os.access(str(target), os.X_OK):
            raise RuntimeError('existing hook is not executable; refusing to change its meaning')
        target.rename(previous)  # same folder preserves relative symlink resolution
    try:
        shutil.copyfile(str(source), str(target))
        target.chmod(0o755)
    except OSError:
        if previous.exists() or previous.is_symlink():
            if target.exists():
                target.unlink()
            previous.rename(target)
        raise


if __name__ == '__main__':
    try:
        install(subprocess.check_output(['git', 'rev-parse', '--show-toplevel']).decode().strip())
        print('pre-commit and pre-push: installed; existing hooks preserved and chained')
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('pre-push installer: REFUSED (%s)' % exc, file=sys.stderr)
        sys.exit(1)
