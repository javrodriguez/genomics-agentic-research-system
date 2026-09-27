"""Operator paths follow gars-env.sh; unrelated environment values never pass."""
import importlib.util
import os
from pathlib import Path
import re
import shlex
import signal
import tempfile
import time
import unittest
from unittest.mock import patch

from support import GARS
import executorlib as ex

SOURCE = GARS / '_system/gars-env.sh'
FAILURE = ('gars-env.sh could not be read, so the executor cannot tell which '
           'variables it may pass (R-096)')


def expansion_names(text):
    """Scan all direct colon expansions, regardless of assignment or shell idiom."""
    return set(re.findall(r'\$\{([A-Za-z_][A-Za-z0-9_]*):[-?=+]', text))


def slurm_names(module=ex):
    return set(next(arg for arg in module.submit_argv(module.SLURM, 'submit.sh')
                    if arg.startswith('--export=')).split('=', 1)[1].split(','))


class ExecutorEnvTests(unittest.TestCase):
    def setUp(self):
        # Preserve process basics, isolate inherited site paths and credentials.
        env = {key: os.environ[key] for key in
               ('PATH', 'HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TMPDIR')
               if key in os.environ}
        self.environment = patch.dict(os.environ, env, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        scratch = tempfile.TemporaryDirectory(prefix='gars-executor-env-')
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)

    def test_operator_env_reaches_the_local_job(self):
        root = self.root / 'fake-root'
        bio, nxf = self.root / 'own-envs/bio', self.root / 'own-envs/nxf'
        for directory in (root / 'install', bio / 'bin', nxf / 'bin'):
            directory.mkdir(parents=True)
        os.environ.update(GARS_ROOT=str(root), GARS_BIO=str(bio), GARS_NXF=str(nxf))
        project = self.root / 'project'
        (project / '_config').mkdir(parents=True)
        dump = project / 'child-env.txt'
        script = project / 'submit.sh'
        script.write_text('#!/bin/bash\nset -euo pipefail\n'
                          'env > %s\nsource %s\necho SOURCED-OK\n' %
                          (shlex.quote(str(dump)), shlex.quote(str(SOURCE))))
        job = ex._local_submit(project, script)
        self.assertIsNotNone(job)
        exit_file = Path(str(script) + '.local.exit')
        completed = False
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if exit_file.is_file() and exit_file.read_text().strip():
                    completed = True
                    break
                time.sleep(0.02)
            self.assertTrue(completed, 'local job did not finish within five seconds')
            child = dict(line.split('=', 1) for line in dump.read_text().splitlines()
                         if '=' in line)
            log = Path(str(script) + '.local.log').read_text()
            self.assertEqual({key: child.get(key) for key in ('GARS_BIO', 'GARS_NXF')},
                             {'GARS_BIO': str(bio), 'GARS_NXF': str(nxf)}, log)
            self.assertEqual(exit_file.read_text().strip(), '0', log)
            self.assertNotIn('FATAL', log)
            self.assertIn('SOURCED-OK', log)
        finally:
            if not completed:
                try:
                    os.kill(int(job), signal.SIGTERM)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    if exit_file.is_file() and exit_file.read_text().strip():
                        break
                    time.sleep(0.02)
                else:
                    self.fail('local runner did not finish after termination')

    def test_every_overridable_name_is_exported(self):
        text = SOURCE.read_text()
        # The independent scan keeps the base failure about dropped names, not a
        # missing parser API. The parser must agree once that API exists.
        names = expansion_names(text)
        os.environ.update({name: str(self.root / name) for name in names})
        child, slurm = ex.execution_env(), slurm_names()
        self.assertEqual(names - set(child), set(), 'operator paths dropped locally')
        self.assertEqual(names - slurm, set(), 'operator paths dropped by Slurm')
        self.assertEqual(set(ex.overridable_names(text)), names)
        for name in names:
            self.assertEqual(child[name], os.environ[name])
        self.assertIsInstance(ex.EXPORT_NAMES, tuple)
        self.assertEqual(ex.EXPORT_NAMES, tuple(sorted(set(ex.BASE_NAMES) | names)))

    def test_the_list_is_read_not_kept(self):
        text = SOURCE.read_text()
        self.assertEqual(expansion_names(text), set(ex.overridable_names(text)))
        source = self.root / 'gars-env.sh'
        source.write_text(text + '\nexport FOO="${FOO:-x}"\n')
        self.assertEqual(set(ex.overridable_names(source.read_text())),
                         expansion_names(text) | {'FOO'})
        # Re-import against the extended sibling: both consumers must follow it.
        fresh = self.load_with_source(source)
        with patch.dict(os.environ, {'FOO': 'operator-value'}):
            self.assertEqual(fresh.execution_env()['FOO'], 'operator-value')
            self.assertIn('FOO', slurm_names(fresh))
        self.assertEqual(set(ex.overridable_names(
            'A="${A:-x}"\nexport B="${B:?required}"\n'
            'WRONG="${OTHER:-x}"\nC="${C:=x}"\nD="${D:+x}"\n'
            '# E="${E:-x}"\necho "${F:-x}"\nfor _v in A; do : "${!_v:-}"; done\n')),
            {'A', 'B'})

    def test_nothing_else_passes(self):
        with patch.dict(os.environ, {'SYNTHETIC_SECRET': 'secret',
                                     'GARS_SOMETHING': 'unlisted'}):
            allowed = set(ex.BASE_NAMES) | expansion_names(SOURCE.read_text()) if hasattr(
                ex, 'BASE_NAMES') else set(ex.EXPORT_NAMES)
            self.assertLessEqual(set(ex.execution_env()), allowed)
            self.assertEqual(slurm_names(), allowed)
            for name in ('SYNTHETIC_SECRET', 'GARS_SOMETHING'):
                self.assertNotIn(name, ex.execution_env())
                self.assertNotIn(name, slurm_names())

    def load_with_source(self, source):
        spec = importlib.util.spec_from_file_location('executor_env_fixture', ex.__file__)
        fresh = importlib.util.module_from_spec(spec)
        # Exercise import-time discovery without modifying the shared module.
        with patch.object(Path, 'with_name', return_value=source):
            spec.loader.exec_module(fresh)
        return fresh

    def test_unreadable_source_fails_loud(self):
        empty = self.root / 'empty.sh'
        empty.write_text('# no overridable declarations\n')
        invalid = self.root / 'invalid.sh'
        invalid.write_bytes(b'\xff')
        for source in (self.root / 'missing.sh', empty, invalid):
            with self.subTest(source=source.name):
                fresh = self.load_with_source(source)  # Import itself must succeed.
                self.assertIsInstance(fresh.EXPORT_NAMES, tuple)
                for call in (fresh.execution_env,
                             lambda: fresh.submit_argv(fresh.SLURM, 'submit.sh'),
                             lambda: fresh.submit_argv(fresh.LOCAL, 'submit.sh')):
                    with self.subTest(call=call):
                        with self.assertRaisesRegex(RuntimeError, re.escape(FAILURE)) as caught:
                            call()
                        self.assertEqual(type(caught.exception).__name__, 'ExecutionEnvError')


if __name__ == '__main__':
    unittest.main(verbosity=2)
