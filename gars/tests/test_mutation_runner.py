"""Runner mechanics use public toy faults; none is a sealed scoring mutant."""
import difflib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from support import REPO, mini_tree, module, run

mutate = module(REPO / 'evals/mutate.py', 'row3_mutate')


class MutationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='gars-mutation-test-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.snapshot = self.base / 'snapshot'
        mini_tree(self.snapshot)
        self.target = self.base / 'tree'
        mutate.copy_tree(self.snapshot, self.target)
        self.before = mutate.tree_hash(self.target)

    def mutant(self, replacement, expected_stdout='2\n'):
        folder = self.base / 'toy'
        folder.mkdir()
        name = 'gars/_system/subject.py'
        patch = ''.join(difflib.unified_diff('print(1)\n'.splitlines(True),
                        replacement.splitlines(True), 'a/' + name, 'b/' + name))
        (folder / 'mutant.diff').write_text(patch)
        expected = {'id': 'toy', 'requirement': 'R-164', 'description': 'Public runner control',
                    'probe': {'argv': ['{python}', name], 'stdin': ''},
                    'before': {'returncode': 0, 'stdout': '1\n', 'stderr': ''},
                    'after': {'returncode': 0, 'stdout': expected_stdout, 'stderr': ''}}
        (folder / 'expected.json').write_text(json.dumps(expected))
        return folder

    def test_semantic_mutant_killed_and_restored(self):
        record = mutate.measure_one(self.snapshot, self.target, self.mutant('print(2)\n'), 'toy-sha')
        self.assertEqual(record['status'], 'killed')
        self.assertIn('test_value', record['test'])
        self.assertEqual(mutate.tree_hash(self.target), self.before)

    def test_unchanged_observation_is_ineffective(self):
        record = mutate.measure_one(self.snapshot, self.target,
                                   self.mutant('print(1)\nraise SystemExit(0)\n'), 'toy-sha')
        # Syntax changes alone are insufficient: the observation did not change.
        self.assertEqual(record['status'], 'ineffective')
        self.assertEqual(mutate.tree_hash(self.target), self.before)

    def test_semantic_mutant_survives_and_restores(self):
        mutant = self.mutant('import sys\nprint(1)\nprint("note", file=sys.stderr)\n')
        expected = json.loads((mutant / 'expected.json').read_text())
        expected['after'].update(stdout='1\n', stderr='note\n')
        (mutant / 'expected.json').write_text(json.dumps(expected))
        record = mutate.measure_one(self.snapshot, self.target, mutant, 'toy-sha')
        self.assertEqual(record['status'], 'survived')
        self.assertIsNone(record['test'])
        self.assertEqual(mutate.tree_hash(self.target), self.before)

    def test_full_run_hashes_source_and_records_run_sha(self):
        result = run(['git', 'add', '--', 'tests', 'gars'], self.snapshot)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = run(['git', '-c', 'user.name=Fixture', '-c',
                      'user.email=fixture', 'commit', '-q',
                      '--allow-empty', '-m', 'Fixture'], self.snapshot)
        self.assertEqual(result.returncode, 0, result.stderr)
        directory = self.base / 'sealed-control'
        directory.mkdir()
        mutant = self.mutant('print(2)\n')
        mutant.rename(directory / mutant.name)
        before = mutate.tree_hash(self.snapshot)
        records = mutate.measure(self.snapshot, directory)
        self.assertEqual([r['status'] for r in records], ['killed'])
        sha = run(['git', 'rev-parse', 'HEAD'], self.snapshot).stdout.decode().strip()
        self.assertEqual(records[0]['run_sha'], sha)
        self.assertEqual(mutate.tree_hash(self.snapshot), before)

    def test_text_only_mutant_is_ineffective_never_killed(self):
        record = mutate.measure_one(self.snapshot, self.target,
                                   self.mutant('# changed words\nprint(1)\n'), 'toy-sha')
        self.assertEqual(record['status'], 'ineffective')
        self.assertIsNone(record['test'])
        self.assertEqual(mutate.tree_hash(self.target), self.before)
        print('red-on-fault: text-only mutant -> ineffective, never killed', flush=True)

    def test_restore_drift_refuses(self):
        mutant = self.mutant('print(2)\n')
        real_restore = mutate.restore_tree
        def broken_restore(snapshot, target):
            real_restore(snapshot, target)
            (target / 'unexpected-file').write_text('drift\n')
        with mock.patch.object(mutate, 'restore_tree', broken_restore):
            with self.assertRaisesRegex(RuntimeError, 'tree differs after run; REFUSED'):
                mutate.measure_one(self.snapshot, self.target, mutant, 'toy-sha')
        print('red-on-fault: restoration leaves tree drift -> runner REFUSED', flush=True)

    def test_malformed_diff_refused_without_source_changes(self):
        mutant = self.mutant('print(2)\n')
        diff = mutant / 'mutant.diff'
        diff.write_text(diff.read_text().replace('gars/_system/subject.py', '../escape.py'))
        with self.assertRaises(ValueError):
            mutate.measure_one(self.snapshot, self.target, mutant, 'toy-sha')
        self.assertEqual(mutate.tree_hash(self.target), self.before)
        expected = json.loads((mutant / 'expected.json').read_text())
        for malformed in (None, [], dict(expected, probe=[]), dict(expected, before=None)):
            with self.subTest(metadata=malformed):
                with self.assertRaises(ValueError):
                    mutate.validate_expected(malformed)

    def test_unsealed_report_and_required_modes(self):
        for args, code in (([], 0), (['--require'], 1)):
            result = run([sys.executable, REPO / 'evals/mutate.py'] + args,
                         env={'GARS_SEALED_MUTANTS_DIR': ''})
            self.assertEqual(result.returncode, code)
            self.assertEqual(result.stdout, b'unmeasured\n')


if __name__ == '__main__':
    unittest.main(verbosity=2)
