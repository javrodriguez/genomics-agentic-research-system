"""R-164: execute the shipped hook, including its known bypass-switch gap."""
import json
import sys
import unittest
from support import GARS, run


class GuardHookTests(unittest.TestCase):
    def call(self, tool=None, data=None, raw=None):
        payload = raw if raw is not None else json.dumps(
            {'tool_name': tool, 'tool_input': data, 'cwd': str(GARS)})
        return run([sys.executable, GARS / '_system/guard_hook.py'], GARS, payload,
                   {'CLAUDE_PROJECT_DIR': str(GARS)})

    def test_denied_shapes(self):
        for tool, data in [
                ('Write', {'file_path': '_system/guard_hook.py'}),
                ('Edit', {'file_path': '_references/genomes.md'}),
                ('Write', {'file_path': 'projects/p/00_data/rnaseq_bulk/files.csv'}),
                ('Bash', {'command': 'pip install package'}),
                ('Bash', {'command': 'echo x > _system/guard_hook.py'}),
                ('Bash', {'command': 'python3 -c "open(\'_system/x\',\'w\')"'}),
                ('Bash', {'command': 'echo x > _system/x; echo "'}),
                ('Bash', {'command': 'tee -a _templates/x'}),
                ('Bash', {'command': 'chmod -R a+w _system'}),
                ('Write', {'file_path': 'projects/p/03_custom_analysis/a/PLAN.md.approved'})]:
            with self.subTest(tool=tool, data=data):
                result = self.call(tool, data)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'Blocked', result.stderr)

    def test_allowed_shapes(self):
        for tool, data in [
                ('Read', {'file_path': '_system/guard_hook.py'}),
                ('Bash', {'command': 'cat _references/genomes.md'}),
                ('Bash', {'command': 'python3 _system/stage00_register.py assays'}),
                ('Edit', {'file_path': 'projects/p/00_data/rnaseq_bulk/samples.csv'}),
                ('Bash', {'command': 'git status'})]:
            with self.subTest(tool=tool, data=data):
                self.assertEqual(self.call(tool, data).returncode, 0)

    def test_bad_stdin_refused(self):
        for raw in ('', 'not json {', '[]', 'null', '{"tool_input": "bad"}'):
            with self.subTest(raw=raw):
                result = self.call(raw=raw)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertIn(b'could not read', result.stderr)

    def test_bypass_switch_as_shipped(self):
        # Characterization, NOT a security acceptance: row 4/15 owns these denies.
        for command in ('git push --no-verify', 'git -c core.hooksPath=/dev/null push',
                        'git config hooks.gitleaks false'):
            with self.subTest(command=command):
                self.assertEqual(self.call('Bash', {'command': command}).returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
