"""Direct hook invocations only: these tests never push or arm the source clone."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from support import REPO, mini_tree, run
from secret_support import CONFIG, checked, snapshot, standin

HOOK = REPO / 'gars/_system/hooks/pre-push'
INSTALLER = REPO / 'gars/_system/hooks/install.py'
PUSH_INPUT = 'refs/heads/test %s refs/heads/test ' + '0' * 40 + '\n'


class PrePushTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='gars-hook-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        mini_tree(self.root)
        shutil.copyfile(str(CONFIG), str(self.root / 'gars/.gitleaks.toml'))
        checked(['git', 'add', '--', 'tests', 'gars'], self.root)
        self.push_input = PUSH_INPUT % snapshot(self.root)
        self.scanner_env = standin(self.root)
        (Path(self.scanner_env['PATH']) / 'cat').symlink_to(shutil.which('cat'))

    def invoke(self, hook=HOOK):
        return run([hook, 'fixture-remote', 'fixture-target'], self.root,
                   self.push_input, self.scanner_env)

    def test_whole_suite_passes_directly(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'collected 1 tests from tests', result.stdout)
        self.assertIn(b'collected 1 tests from gars/tests', result.stdout)

    def test_planted_failure_refuses(self):
        path = self.root / 'gars/tests/test_gate_gars_sample.py'
        path.write_text(path.read_text().replace('assertTrue(True)', 'assertTrue(False)'))
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'FAIL: test_positive', result.stderr)
        self.assertIn(b'pre-push: REFUSED', result.stdout)
        print('red-on-fault: planted failing test -> pre-push REFUSED', flush=True)

    def test_each_empty_tree_refuses(self):
        for relative in ('tests/test_gate_sample.py', 'gars/tests/test_gate_gars_sample.py'):
            with self.subTest(tree=relative):
                path = self.root / relative
                saved = path.read_bytes()
                path.unlink()
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'collected 0 tests', result.stderr)
                path.write_bytes(saved)
        print('red-on-fault: each empty test tree -> pre-push REFUSED', flush=True)

    def test_installer_preserves_both_gates_stdin_and_veto(self):
        for custom in (False, True):
            with self.subTest(custom_hooks_path=custom):
                hooks = self.root / ('custom-hooks' if custom else '.git/hooks')
                hooks.mkdir(exist_ok=True)
                if custom:
                    self.assertEqual(run(['git', 'config', 'core.hooksPath', 'custom-hooks'],
                                         self.root).returncode, 0)
                existing = hooks / 'pre-push'
                # A gitleaks stand-in records stdin and can refuse independently.
                original = ('#!/bin/sh\ncat > previous-input\n'
                            'printf "%s\\n" "$@" > previous-args\n'
                            'test ! -f refuse-previous\n')
                existing.write_text(original)
                existing.chmod(0o755)
                for unused in range(2):
                    result = run([sys.executable, INSTALLER], self.root)
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((hooks / 'pre-push.gars-previous').read_text(), original)
                self.assertEqual(self.invoke(existing).returncode, 0)
                self.assertEqual((self.root / 'previous-input').read_text(), self.push_input)
                self.assertEqual((self.root / 'previous-args').read_text(),
                                 'fixture-remote\nfixture-target\n')
                (self.root / 'refuse-previous').touch()
                result = self.invoke(existing)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
                (self.root / 'refuse-previous').unlink()
                sample = self.root / 'gars/tests/test_gate_gars_sample.py'
                good = sample.read_text()
                sample.write_text(good.replace('assertTrue(True)', 'assertTrue(False)'))
                (self.root / 'previous-input').unlink()
                self.assertNotEqual(self.invoke(existing).returncode, 0)
                self.assertEqual((self.root / 'previous-input').read_text(), self.push_input)
                sample.write_text(good)

    def test_marker_bearing_unrelated_hook_keeps_veto(self):
        hook = self.root / '.git/hooks/pre-push'
        original = '#!/bin/sh\n# GARS_ROW3_PRE_PUSH_V1 mentioned here\nexit 1\n'
        hook.write_text(original)
        hook.chmod(0o755)
        result = run([sys.executable, INSTALLER], self.root)
        # Either preserve and chain it, or refuse without altering it.
        saved = hook if result.returncode else hook.with_name('pre-push.gars-previous')
        self.assertTrue(saved.is_file())
        self.assertEqual(saved.read_text(), original)
        self.assertNotEqual(self.invoke(hook).returncode, 0)

    def test_extended_installed_hook_keeps_veto(self):
        self.assertEqual(run([sys.executable, INSTALLER], self.root).returncode, 0)
        hook = self.root / '.git/hooks/pre-push'
        extended = hook.read_text().replace('sys.exit(main())', 'main(); sys.exit(1)')
        hook.write_text(extended)
        result = run([sys.executable, INSTALLER], self.root)
        # An extended GARS hook cannot be chained to itself recursively.
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(hook.read_text(), extended)
        self.assertFalse(hook.with_name('pre-push.gars-previous').exists())
        self.assertNotEqual(self.invoke(hook).returncode, 0)

    def test_installer_refuses_backup_collision(self):
        hooks = self.root / '.git/hooks'
        for name in ('pre-push', 'pre-push.gars-previous'):
            (hooks / name).write_text('#!/bin/sh\nexit 0\n')
            (hooks / name).chmod(0o755)
        before = {p.name: p.read_bytes() for p in hooks.iterdir()}
        self.assertNotEqual(run([sys.executable, INSTALLER], self.root).returncode, 0)
        self.assertEqual(before, {p.name: p.read_bytes() for p in hooks.iterdir()})


if __name__ == '__main__':
    unittest.main(verbosity=2)
