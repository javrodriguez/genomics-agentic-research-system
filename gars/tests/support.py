"""Disposable fixtures shared by the Row 3 unittest modules (Python 3.6)."""
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

if os.environ.get('TMPDIR'):
    tempfile.tempdir = os.environ['TMPDIR']

REPO = Path(__file__).resolve().parents[2]
GARS = REPO / 'gars'
sys.path.insert(0, str(GARS / '_system'))


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def run(argv, cwd=REPO, stdin='', env=None):
    settings = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    if env:
        settings.update(env)
    return subprocess.run([str(a) for a in argv], cwd=str(cwd), env=settings,
                          input=stdin.encode(), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=120)


def bytes_in(tree):
    return {str(p.relative_to(tree)): p.read_bytes()
            for p in tree.rglob('*') if p.is_file()}


def mini_tree(root):
    """Small real discovery fixture using the production load_tests implementation."""
    for relative in ('tests', 'gars/tests', 'gars/_system'):
        (root / relative).mkdir(parents=True, exist_ok=True)
    source = (REPO / 'tests/run_tests.py').read_text()
    protocol = source[source.index('\ndef load_tests('):source.index(
        '\nif __name__ == "__main__":', source.index('\ndef load_tests('))]
    (root / 'tests/run_tests.py').write_text(
        'import unittest\nfrom pathlib import Path\n'
        'REPO = Path(__file__).resolve().parents[1]\n' + protocol +
        '\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n')
    (root / 'gars/_system/subject.py').write_text('print(1)\n')
    (root / 'tests/test_gate_sample.py').write_text(
        'import unittest, subprocess, sys\nfrom pathlib import Path\n'
        'class Behaviour(unittest.TestCase):\n'
        '    def test_value(self):\n'
        '        root = Path(__file__).resolve().parents[1]\n'
        '        value = subprocess.check_output([sys.executable, str(root / "gars/_system/subject.py")])\n'
        '        self.assertEqual(value, b"1\\n")\n')
    (root / 'gars/tests/test_gate_gars_sample.py').write_text(
        'import unittest\nclass Control(unittest.TestCase):\n'
        '    def test_positive(self):\n        self.assertTrue(True)\n')
    result = run(['git', 'init', '-q', root])
    if result.returncode:
        raise RuntimeError(result.stderr)


def write_fixture_dataset(root, data_class="public", purpose="fixture"):
    """The same immutable row and mode as finalize; repeated fixture setup is a no-op."""
    import json
    from stage00_register import dataset_values, write_dataset_record
    root = Path(root)
    base = {'data_class': data_class, 'purpose': purpose, 'agreement_ref': 'none',
            'input_data_location': json.dumps(sorted({str(p.resolve()) for p in
                (root / '00_data').glob('*/raw/*')}), separators=(',', ':'))}
    row = dataset_values(root, base)
    write_dataset_record(root, row)
