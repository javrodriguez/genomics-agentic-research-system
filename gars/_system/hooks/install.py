#!/usr/bin/env python3
"""Install into Git's current hook directory, preserving its existing pre-push."""
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
    target = folder / 'pre-push'
    previous = folder / 'pre-push.gars-previous'
    source = Path(__file__).with_name('pre-push')
    if target.is_symlink() and target.is_file() and MARKER in target.read_bytes():
        raise RuntimeError('existing GARS hook is a symlink; refusing a recursive chain')
    if target.exists() or target.is_symlink():
        if target.is_file() and not target.is_symlink() and MARKER in target.read_bytes():
            target.write_bytes(source.read_bytes())
            target.chmod(0o755)
            return
        if previous.exists() or previous.is_symlink():
            raise RuntimeError('previous-hook backup exists; refusing to overwrite either hook')
        if not os.access(str(target), os.X_OK):
            raise RuntimeError('existing pre-push is not executable; refusing to change its meaning')
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
        print('pre-push: installed; any existing hook preserved and chained')
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('pre-push installer: REFUSED (%s)' % exc, file=sys.stderr)
        sys.exit(1)
