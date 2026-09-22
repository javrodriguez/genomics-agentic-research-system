"""R-096/R-161: direct calls in scratch, never commit/push or install in this clone."""
import base64
import json
import sys
import unittest
from pathlib import Path
from support import run
from secret_support import (CONFIG, REAL_GITLEAKS, checked, fixture, fresh_canary,
                            push_input, snapshot, standin)


class GitleaksHookTests(unittest.TestCase):
    def setUp(self):
        self.root, self.hooks, self.base = fixture(self)
        self.env = standin(self.root)

    def invoke(self, name, env=None, payload=None):
        return run([sys.executable, self.hooks / name, 'fixture-remote', 'fixture-target'],
                   self.root, push_input(self.tip(), self.base) if payload is None else payload,
                   env or self.env)

    def tip(self):
        return snapshot(self.root, self.base)

    def plant(self, encoding):
        value = fresh_canary()
        if encoding == 'base64':
            value = base64.b64encode(value)
        elif encoding == 'hex':
            value = value.hex().encode()
        (self.root / 'candidate.txt').write_bytes(value + b'\n')
        checked(['git', 'add', '--', 'candidate.txt'], self.root)

    def assert_refused(self, result, reason):
        self.assertNotEqual(result.returncode, 0, 'hook accepted a forbidden operation')
        self.assertIn(reason.encode(), result.stdout + result.stderr)

    def test_clean_and_explicit_configuration(self):
        for name in ('pre-commit', 'pre-push'):
            result = self.invoke(name)
            self.assertEqual(result.returncode, 0, result.stderr)
            args = json.loads((self.root / 'scanner-args.json').read_text())
            self.assertEqual(args[args.index('--config') + 1], str(self.root / 'gars/.gitleaks.toml'))
            self.assertIn('--max-decode-depth=5', args)
            self.assertIn('--ignore-gitleaks-allow', args)
            self.assertIn('--staged' if name == 'pre-commit' else
                          '--log-opts=' + self.base + '..' + self.tip(), args)

    def test_plain_base64_hex_and_staged_content_refused(self):
        for encoding in ('plain', 'base64', 'hex'):
            self.plant(encoding)
            # A clean worktree cannot conceal the already-staged secret.
            (self.root / 'candidate.txt').write_text('clean working copy\n')
            for name in ('pre-commit', 'pre-push'):
                self.assert_refused(self.invoke(name), 'found secrets')

    def test_missing_gitleaks_refused(self):
        env = standin(self.root, 'missing')
        for name in ('pre-commit', 'pre-push'):
            self.assert_refused(self.invoke(name, env), 'absent from PATH')

    def test_unreadable_and_outside_config_refused(self):
        config = self.root / 'gars/.gitleaks.toml'
        config.unlink()
        for name in ('pre-commit', 'pre-push'):
            self.assert_refused(self.invoke(name), 'config is unreadable')
        outside = self.root.parent / 'outside.toml'
        outside.write_bytes(CONFIG.read_bytes())
        config.symlink_to(outside)
        for name in ('pre-commit', 'pre-push'):
            self.assert_refused(self.invoke(name), 'config resolves outside repository')

    def test_unclassified_exit_and_timeout_refused(self):
        for name in ('pre-commit', 'pre-push'):
            self.assert_refused(self.invoke(name, standin(self.root, 'error')), 'unclassified exit 17')
        script = self.hooks / 'pre-commit'
        script.write_text(script.read_text().replace('SCAN_TIMEOUT = 60', 'SCAN_TIMEOUT = 0.05'))
        for name in ('pre-commit', 'pre-push'):
            self.assert_refused(self.invoke(name, standin(self.root, 'timeout')), 'timeout')

    def test_previous_hook_receives_stdin_arguments_and_keeps_veto(self):
        for name in ('pre-commit', 'pre-push'):
            previous = self.hooks / (name + '.gars-previous')
            previous.write_text('#!' + sys.executable + '\nimport sys\nfrom pathlib import Path\n'
                                'Path("previous-input").write_bytes(sys.stdin.buffer.read())\n'
                                'Path("previous-args").write_text("\\n".join(sys.argv[1:]))\n'
                                'sys.exit(19)\n')
            previous.chmod(0o755)
            payload = push_input(self.tip(), self.base)
            self.assert_refused(self.invoke(name, payload=payload), name + ': REFUSED')
            self.assertEqual((self.root / 'previous-input').read_text(), payload)
            self.assertEqual((self.root / 'previous-args').read_text(), 'fixture-remote\nfixture-target')
            self.assertTrue((self.root / 'scanner-args.json').exists())
            (self.root / 'scanner-args.json').unlink()

    def test_installer_preserves_both_and_refuses_different_markers(self):
        checked(['git', 'config', 'core.hooksPath', '.githooks'], self.root)
        folder = self.root / '.githooks'
        folder.mkdir()
        for name in ('pre-commit', 'pre-push'):
            (folder / name).write_text('#!/bin/sh\nexit 19\n')
            (folder / name).chmod(0o755)
        for unused in range(2):
            result = run([sys.executable, self.hooks / 'install.py'], self.root)
            self.assertEqual(result.returncode, 0, result.stderr)
        for name in ('pre-commit', 'pre-push'):
            self.assertEqual((folder / (name + '.gars-previous')).read_text(), '#!/bin/sh\nexit 19\n')
            path = folder / name
            original = path.read_bytes()
            path.write_bytes(original + b'\n# differing marker-bearing content\n')
            before = {p.name: p.read_bytes() for p in folder.iterdir()}
            result = run([sys.executable, self.hooks / 'install.py'], self.root)
            self.assert_refused(result, 'marker-bearing hook differs')
            self.assertEqual(before, {p.name: p.read_bytes() for p in folder.iterdir()})
            path.write_bytes(original)

    def test_push_new_ref_deletion_and_invalid_input(self):
        self.plant('plain')
        self.assert_refused(self.invoke('pre-push', payload=push_input(self.tip())), 'found secrets')
        result = self.invoke('pre-push', payload=push_input('0' * 40, self.base))
        self.assertEqual(result.returncode, 0, result.stderr)
        for payload in ('bad\n', push_input('f' * 40, self.base)):
            self.assert_refused(self.invoke('pre-push', payload=payload), 'gitleaks: REFUSED')

    @unittest.skipUnless(REAL_GITLEAKS, 'real gitleaks absent from PATH: clean integration not measured')
    def test_real_binary_pass(self):
        env = {'PATH': str(Path(REAL_GITLEAKS).parent) + ':' + self.env['PATH']}
        for name in ('pre-commit', 'pre-push'):
            result = self.invoke(name, env)
            self.assertEqual(result.returncode, 0, result.stderr)

    @unittest.skipUnless(REAL_GITLEAKS, 'real gitleaks absent from PATH: secret integration not measured')
    def test_real_binary_refusal(self):
        env = {'PATH': str(Path(REAL_GITLEAKS).parent) + ':' + self.env['PATH']}
        for encoding in ('plain', 'base64', 'hex'):
            self.plant(encoding)
            # Even an allowlisted documentation path must retain the canary rule.
            reference = self.root / 'gars/_references/environment.md'
            reference.parent.mkdir(exist_ok=True)
            reference.write_bytes((self.root / 'candidate.txt').read_bytes())
            checked(['git', 'add', '--', 'gars/_references/environment.md'], self.root)
            for name in ('pre-commit', 'pre-push'):
                self.assert_refused(self.invoke(name, env), 'found secrets')

    def test_planted_hook_and_installer_faults_are_red(self):
        script = self.hooks / 'pre-commit'
        original = script.read_text()
        missing = standin(self.root, 'missing')
        script.write_text(original.replace("raise RuntimeError('gitleaks absent from PATH')", 'return True'))
        with self.assertRaises(AssertionError):
            self.assert_refused(self.invoke('pre-commit', missing), 'absent from PATH')
        print('red-on-fault: missing-gitleaks hook exits 0 -> refusal assertion FAILED')
        script.write_text(original)
        for name in ('pre-commit', 'pre-push'):
            hook = self.hooks / name
            saved = hook.read_text()
            previous = self.hooks / (name + '.gars-previous')
            previous.write_text('#!/bin/sh\nexit 19\n')
            previous.chmod(0o755)
            hook.write_text(saved.replace('failed = code != 0', 'failed = False'))
            with self.assertRaises(AssertionError):
                self.assert_refused(self.invoke(name), name + ': REFUSED')
            hook.write_text(saved)
            previous.unlink()
        print('red-on-fault: previous-hook veto ignored -> refusal assertion FAILED')
        outside = self.root.parent / 'outside.toml'
        outside.write_bytes(CONFIG.read_bytes())
        (self.root / 'gars/.gitleaks.toml').unlink()
        (self.root / 'gars/.gitleaks.toml').symlink_to(outside)
        script.write_text(original.replace("raise RuntimeError('gitleaks config resolves outside repository')", 'pass'))
        with self.assertRaises(AssertionError):
            self.assert_refused(self.invoke('pre-commit'), 'outside repository')
        print('red-on-fault: outside-repository config accepted -> refusal assertion FAILED')
        script.write_text(original)
        installer = self.hooks / 'install.py'
        saved = installer.read_text()
        # Disable both marker checks: the changed hook gets overwritten and chained.
        installer.write_text(saved.replace("b'GARS_ROW' in target.read_bytes()", 'False'))
        installed = self.root / '.git/hooks/pre-commit'
        planted = original + '\n# differing content\n'
        installed.write_text(planted)
        installed.chmod(0o755)
        result = run([sys.executable, installer], self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        with self.assertRaises(AssertionError):
            self.assertEqual(installed.read_text(), planted)
        print('red-on-fault: differing marker hook overwritten -> preservation assertion FAILED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
