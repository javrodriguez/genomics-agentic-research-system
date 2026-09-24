#!/usr/bin/env python3
"""Run current catalogue witnesses against archived BASE without touching Git state."""
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

REPO = Path(__file__).resolve().parents[2]
BASE = 'dc6b803fea84b8c2df8bb748e3312fc3220800a9'
BEHAVIOR = '''
import importlib.util
from pathlib import Path
import sys
import types
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'gars/tests'))
import support
original = support.module
def available(path, name):
    if not Path(path).is_file():
        return types.SimpleNamespace(main=lambda *a, **k: 3)
    return original(path, name)
support.module = available
runner = original(root / 'tests/test_planted_defects.py', 'baseline_runner')
plants = root / 'baseline-plants'
runner.generate.generate(plants)
caught = []
for cid in range(1, 10):
    try:
        result = runner.grade(plants / ('d%02d' % cid), cid, runner.FLAGS[cid][0])
    except Exception:
        result = False
    caught.append(result)
    print('BASE class %d: %s' % (cid, 'caught' if result else 'not caught'))
assert caught == [True, True, False, False, False, False, False, False, False], caught
print('BASE behavioral: 2/10; classes 3, 4, 5, 6, 7, 8, 9 not caught')
'''


def main():
    with tempfile.TemporaryDirectory(prefix='defect-base-') as folder:
        root = Path(folder)
        archive = subprocess.check_output(['git', 'archive', BASE])
        with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
            bundle.extractall(str(root))
        for relative in ('benchmarks/defects', 'gars/tests/fixtures/citations'):
            shutil.copytree(str(REPO / relative), str(root / relative))
        for relative in ('tests/test_planted_defects.py', 'gars/tests/test_citation_resolution.py',
                         'gars/tests/test_emit_report.py', 'gars/tests/test_integrity_records.py'):
            shutil.copy2(str(REPO / relative), str(root / relative))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([sys.executable, str(root / 'tests/test_planted_defects.py')],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        if result.returncode == 0 or 'gars/_system/resolve_citation.py' not in result.stdout:
            raise AssertionError('expected missing-module red absent')
        print('BASE import: RED (missing gars/_system/resolve_citation.py)')
        # Availability adapter only: absent entry points return nonzero with no catch code.
        # No new detector is supplied to the parent.
        result = subprocess.run([sys.executable, '-c', BEHAVIOR, str(root)], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True)
        print(result.stdout, end='')
        return result.returncode


if __name__ == '__main__':
    sys.exit(main())
