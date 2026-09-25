"""Fault controls for the implemented contracts, each in a disposable copy."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
# Row 9 list shape: label, file, old bytes, replacement, module, named test.
FAULTS = [
    ('any-of ignores class', 'evals/review-faults/oracle.py',
     "if finding['class'] != expected['class']:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('any-of ignores file', 'evals/review-faults/oracle.py',
     "if normalize_file(finding['file']) != target['file']:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('line tolerance widened', 'evals/review-faults/oracle.py',
     "target['line_end'] + 3", "target['line_end'] + 4",
     'core', 'OracleTests.test_any_of_grid'),
    ('severity ignored', 'evals/review-faults/oracle.py',
     "if SEVERITY[finding['severity']] < SEVERITY[expected.get('min_severity', 'MINOR')]:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('repo drop removed', 'evals/bio-faults/bio_oracle.py',
     "if name.startswith('repo/'):", 'if False:',
     'core', 'OracleTests.test_repo_never_matches'),
    ('science name reimplemented', 'evals/bio-faults/bio_common.py',
     'ratio = rf_score.ratio', "ratio = lambda n, d: {'n': n, 'd': d}",
     'core', 'ContractTests.test_same_objects'),
    ('science module renamed to bare name', 'evals/bio-faults/bio_oracle.py',
     None, 'evals/bio-faults/oracle.py',
     'core', 'ContractTests.test_one_process_both_import_orders'),
]


class FaultTests(unittest.TestCase):
    def test_faults(self):
        for label, relative, old, new, module, name in FAULTS:
            with self.subTest(fault=label), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for directory in ('evals/review-faults', 'evals/bio-faults'):
                    shutil.copytree(str(REPO / directory), str(root / directory),
                                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'runs'))
                for relative_file in ('tests/test_bio_faults_core.py',
                                      'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md',
                                      'gars/_references/prompts/review_faults_science.md'):
                    target = root / relative_file
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(REPO / relative_file), str(target))
                script = root / ('tests/test_bio_faults_' + module + '.py')
                argv = [sys.executable, '-B', str(script), name]
                control = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
                self.assertEqual(control.returncode, 0, control.stdout.decode())
                path = root / relative
                if old is None:
                    path.rename(str(root / new))
                else:
                    source = path.read_text()
                    self.assertEqual(source.count(old), 1)
                    path.write_text(source.replace(old, new))
                failed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
                self.assertNotEqual(failed.returncode, 0, label)
                evidence = failed.stdout.decode()
                if old is None:
                    self.assertIn('ModuleNotFoundError', evidence)
                else:
                    self.assertIn('FAIL: ' + name.split('.')[-1], evidence)
                    self.assertNotIn('ERROR:', evidence)
                print('science fault red: ' + label)


if __name__ == '__main__':
    unittest.main(verbosity=2)
