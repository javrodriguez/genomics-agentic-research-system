"""R8: benchmark registry width compatibility does not change artifact scoring."""
from pathlib import Path
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'evals'))
import bench


class RegistryColumnsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='gars-registry-columns-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / 'outputs'
        stage = self.output / 'stage'
        stage.mkdir(parents=True)
        roster = self.root / 'roster.csv'
        roster.write_text('sample\ncontrol\ntreated\n')
        (self.output / 'samplesheet.csv').write_bytes(roster.read_bytes())
        self.counts = stage / 'counts.tsv'
        self.counts.write_text('gene_id\tcontrol\ttreated\ngene_a\t1\t2\n')
        reference = self.root / 'reference.tsv'
        reference.write_bytes(self.counts.read_bytes())
        (stage / 'qc.txt').write_text('synthetic interface fixture\n')
        self.registry = stage / 'OUTPUTS.tsv'
        self.rows = [('counts_gene', 'native', 'counts.tsv'),
                     ('qc_report', 'native', 'qc.txt')]
        self.contract = {
            'types': {'counts_gene': 'counts', 'qc_report': 'file'},
            'samplesheet': 'samplesheet.csv', 'sample_mode': 'rnaseq',
            'expected_samplesheet': 'roster.csv',
            'reference_counts': {'counts_gene': 'reference.tsv'}}
        self.task = {
            'question': 'Check registry-reader compatibility on synthetic files.',
            'inputs': [{'path': p.name, 'sha256': bench.file_sha(p)}
                       for p in (roster, reference)],
            'expected_workflow': 'Read artifact routing and check content.',
            'expected_outputs': {'stage/OUTPUTS.tsv': {'artifact_registry': self.contract}},
            'known_pitfalls': 'Trailing provenance fields are not scored here.',
            'reference_answer': 'Counts match the independent synthetic reference.',
            'reference_source': 'synthetic_with_generator_seed',
            'scorer': 'pytest', 'holdout': False}

    def write_registry(self, trailing=()):
        self.registry.write_text('\n'.join('\t'.join(row + tuple(trailing))
                                           for row in self.rows) + '\n')

    def grade(self):
        return bench.score_partition({'synthetic': self.task},
                                     self.root / 'partition', self.root)

    def test_three_and_five_columns_pass(self):
        for trailing in ((), ('0' * 64, 'durable')):
            with self.subTest(columns=3 + len(trailing)):
                self.write_registry(trailing)
                bench.assert_registry(self, self.registry, self.contract,
                                      self.output, self.root)
                self.assertTrue(bench.score_task(self.task, self.output, self.root)['passed'])

    def test_four_and_six_columns_are_refused(self):
        for trailing in (('extra',), ('sha', 'durable', 'extra')):
            with self.subTest(columns=3 + len(trailing)):
                self.write_registry(trailing)
                with self.assertRaisesRegex(AssertionError, 'registry needs 3 or 5 columns'):
                    bench.assert_registry(self, self.registry, self.contract,
                                          self.output, self.root)
                self.assertFalse(bench.score_task(self.task, self.output, self.root)['passed'])

    def test_trailing_values_never_change_scores(self):
        # Exercise full partition scores, including failures from altered content.
        partition = self.root / 'partition'
        partition.mkdir()
        self.output.rename(partition / 'synthetic')
        self.output = partition / 'synthetic'
        self.registry = self.output / 'stage/OUTPUTS.tsv'
        self.counts = self.output / 'stage/counts.tsv'
        for contents, passed in (
                ('gene_id\tcontrol\ttreated\ngene_a\t1\t2\n', True),
                ('gene_id\tcontrol\ttreated\ngene_a\t1\t3\n', False),
                ('gene_id\tcontrol\ngene_a\t1\n', False)):
            self.counts.write_text(contents)
            self.write_registry()
            baseline = self.grade()
            self.assertEqual(baseline['numerator'], int(passed))
            self.assertEqual(baseline['denominator'], 1)
            for trailing in (('0' * 64, 'durable'),
                             ('wrong-hash', 'wrong-artifact-class'),
                             ('unknown', 'unknown'), ('', '')):
                with self.subTest(passed=passed, trailing=trailing):
                    self.write_registry(trailing)
                    self.assertEqual(self.grade(), baseline)


if __name__ == '__main__':
    unittest.main(verbosity=2)
