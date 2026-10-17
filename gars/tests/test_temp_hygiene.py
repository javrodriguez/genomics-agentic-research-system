"""A module run leaves nothing of its own in the caller's TMPDIR (decision 0190)."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from support import GARS

MODULE = GARS / 'tests/test_mutation_runner.py'
LOGS = 'mutation suite logs: '


def run_module(env):
    return subprocess.run([sys.executable, str(MODULE)], cwd=str(MODULE.parent), env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=600)


class TempHygieneTests(unittest.TestCase):
    def test_no_gars_dir_survives_a_module_run(self):
        """measure() keeps its suite logs in TMPDIR by design; the module must point TMPDIR at a
        scratch of its own, so the caller's TMPDIR ends the run as it began."""
        with tempfile.TemporaryDirectory(prefix='hygiene-') as fresh:
            env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE='1')
            result = run_module(env)
            stderr = result.stderr.decode()
            self.assertEqual(result.returncode, 0, stderr[-2000:])
            # Five measure() calls ran, so the check below is not satisfied by skipped tests.
            self.assertEqual(stderr.count(LOGS), 5, stderr[-2000:])
            left = sorted(p.name for p in Path(fresh).iterdir() if p.name.startswith('gars-'))
            self.assertEqual(left, [])

    def test_ci_without_tmpdir_still_refuses(self):
        """With TMPDIR unset the module patches nothing, so under CI measure() still refuses
        (decisions 0050, 0051) and a lost setting cannot pass hollowly."""
        env = dict(os.environ, CI='true', PYTHONDONTWRITEBYTECODE='1')
        env.pop('TMPDIR', None)
        result = run_module(env)
        stderr = result.stderr.decode()
        self.assertNotEqual(result.returncode, 0, stderr[-2000:])
        refusal = 'ValueError: TMPDIR must name an existing scratch directory'
        self.assertEqual(stderr.count(refusal), 4, stderr[-2000:])
        self.assertNotIn(LOGS, stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
