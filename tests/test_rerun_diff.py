"""Row 13 step A: the re-run diff summary (decision 0140, D4).

The comparison layout is built under the scratch folder at test time from committed synthetic
tables; no machine path is committed. Every check drives the real CLI.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))
import rerun_diff as rd  # noqa: E402 -- red at the parent: the script does not exist there
import pilot_emulation as emulation  # noqa: E402

FIXTURES = REPO / 'tests/fixtures/pilot'
SCRIPT = REPO / 'scripts/rerun_diff.py'
TABLE = 'run/tables/de_results.csv'

EXPECTED = """runs: 2
run 1
rows original/re-run: 8/8
genes matched: 8
genes only in original: 0
genes only in re-run: 0
byte_equal: yes
max_abs_delta log2FoldChange: 0
max_rel_delta padj: 0
spearman log2FoldChange: 1
crossings padj<0.05 (gained/lost): 0/0
sign flips: 0
na_padj original/re-run: 1/1
na_log2FoldChange original/re-run: 0/0
graded 16 of 16 rows
run 2
rows original/re-run: 8/8
genes matched: 8
genes only in original: 0
genes only in re-run: 0
byte_equal: no
max_abs_delta log2FoldChange: 1e-06
max_rel_delta padj: 0.0201476
spearman log2FoldChange: 1
crossings padj<0.05 (gained/lost): 0/1
sign flips: 0
na_padj original/re-run: 1/1
na_log2FoldChange original/re-run: 0/0
graded 16 of 16 rows
"""


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class RerunDiffTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix='row13-rd-')
        self.root = Path(self._temp.name)
        self.stage = self.root / 'project/02_bioinformatics/rnaseq_bulk/02_rnaseq-de'
        (self.stage / 'reproducibility').mkdir(parents=True)
        (self.stage / 'run/tables').mkdir(parents=True)
        shutil.copyfile(str(FIXTURES / 'de_original.csv'), str(self.stage / TABLE))
        self.out = self.root / 'out'
        for n in (1, 2):
            target = self.replay(n) / TABLE
            target.parent.mkdir(parents=True)
            shutil.copyfile(str(FIXTURES / ('de_run%d.csv' % n)), str(target))
        template = (FIXTURES / 'comparison.template.json').read_text()
        self.data = json.loads(template.replace('@ORIGINAL_STAGE@', str(self.stage))
                               .replace('@WRAPPERS_ROOT@', str(self.root / 'wrappers')))
        self.write()

    def tearDown(self):
        self._temp.cleanup()

    def replay(self, n):
        return self.out / ('run-%d' % n) / '02_bioinformatics/rnaseq_bulk/02_rnaseq-de'

    def write(self):
        self.comparison = self.out / 'comparison.json'
        self.comparison.write_text(json.dumps(self.data, indent=2))

    def de_artifact(self, run_index):
        return [a for a in self.data['runs'][run_index]['artifacts']
                if a['path'].endswith('de_results.csv')][0]

    def run_diff(self):
        return subprocess.run([sys.executable, str(SCRIPT), '--comparison', str(self.comparison)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True)

    def assert_clean(self, text):
        forbidden = ['GENEFIX', 'SAMPLEFIX', str(self.root), str(REPO), 'de_results',
                     'normalized_counts', 'identical;', 'crossed 0.05']
        for word in forbidden:
            self.assertNotIn(word, text)
        self.assertIsNone(re.search(r'(^|\s)/[A-Za-z]', text, re.M), 'a path was printed')

    def assert_refused(self, reason):
        self.write()
        result = self.run_diff()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stderr, 'refused: %s\n' % reason)
        self.assertEqual(result.stdout, '')

    def test_fixture_aggregates_only(self):
        result = self.run_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED)
        self.assert_clean(result.stdout + result.stderr)
        print('EXIT rerun diff (fixture): aggregates only')

    def test_graded_equals_seen_and_one_side_genes_counted(self):
        text = (FIXTURES / 'de_run2.csv').read_text().splitlines()
        # Drop one gene, add another: both counted, neither printed.
        text = [l for l in text if not l.startswith('GENEFIX0008,')] + [
            'GENEFIX0099,5.0,NA,1.0,']
        path = self.replay(2) / TABLE
        path.write_text('\n'.join(text) + '\n')
        self.de_artifact(1)['replay_sha256'] = sha(path)
        self.write()
        result = self.run_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        block = result.stdout.split('run 2\n')[1].splitlines()
        self.assertIn('genes matched: 7', block)
        self.assertIn('genes only in original: 1', block)
        self.assertIn('genes only in re-run: 1', block)
        self.assertIn('na_padj original/re-run: 1/2', block)
        self.assertIn('na_log2FoldChange original/re-run: 0/1', block)
        self.assertIn('graded 16 of 16 rows', block)
        self.assert_clean(result.stdout)

    def test_runs_order_is_kept(self):
        self.data['runs'].reverse()
        self.write()
        result = self.run_diff()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(re.findall(r'^run (\d+)$', result.stdout, re.M), ['2', '1'])

    def test_sign_flip_and_gained_crossing(self):
        text = (FIXTURES / 'de_original.csv').read_text()
        text = text.replace('GENEFIX0008,300.0,0.25,0.5,0.71', 'GENEFIX0008,300.0,-0.25,0.01,0.04')
        path = self.replay(1) / TABLE
        path.write_text(text)
        self.de_artifact(0)['replay_sha256'] = sha(path)
        self.write()
        block = self.run_diff().stdout.split('run 2\n')[0].splitlines()
        self.assertIn('byte_equal: no', block)
        self.assertIn('sign flips: 1', block)
        self.assertIn('crossings padj<0.05 (gained/lost): 1/0', block)

    def test_refusals_never_name_what_they_refuse(self):
        artifact = self.de_artifact(1)
        saved = dict(artifact)
        artifact['replay_sha256'] = '1' * 64
        self.assert_refused('table_sha256_mismatch')
        artifact.update(saved)
        artifact['original_sha256'] = '2' * 64
        self.assert_refused('table_sha256_mismatch')
        artifact.update(saved)
        artifact['path'] = '../escape/de_results.csv'
        self.assert_refused('artifact_path')
        artifact.update(saved)
        self.data['runs'][1]['artifacts'].append(dict(saved, path='other/de_results.csv'))
        self.assert_refused('de_artifact_count')
        self.data['runs'][1]['artifacts'] = [a for a in self.data['runs'][1]['artifacts']
                                             if not a['path'].endswith('de_results.csv')]
        self.assert_refused('de_artifact_count')
        self.data['runs'][1]['artifacts'].append(saved)
        self.data['runs'][1]['run'] = 'two'
        self.assert_refused('comparison_run_number')
        self.data['runs'][1]['run'] = 2
        # Ruling L5: neither an empty list nor a run compared twice is a re-run diff.
        self.data['runs'][1]['run'] = 1
        self.assert_refused('comparison_run_duplicate')
        self.data['runs'][1]['run'] = 2
        runs, self.data['runs'] = self.data['runs'], []
        self.assert_refused('comparison_runs_empty')
        self.data['runs'] = runs
        original = self.data['original']
        self.data['original'] = original.replace('02_rnaseq-de', '02_rnaseq\x00-de')
        self.assert_refused('table_unreadable')
        self.data['original'] = 'relative/manifest.json'
        self.assert_refused('comparison_original')
        self.data['original'] = original
        self.comparison.write_text('[' * 100000)
        result = self.run_diff()
        self.assertEqual((result.returncode, result.stderr, result.stdout),
                         (2, 'refused: comparison_unreadable\n', ''))
        print('red-on-fault: sha mismatch, unsafe path, zero or two DE artifacts, no runs, a '
              'repeated run -> REFUSED')

    def test_malformed_tables_are_refused(self):
        path = self.replay(2) / TABLE
        good = (FIXTURES / 'de_run2.csv').read_text()
        for reason, text in (
                ('table_duplicate_gene', good + 'GENEFIX0001,1,1,1,1\n'),
                ('table_empty_gene', good + ',1,1,1,1\n'),
                ('table_value', good.replace('0.577216', 'high')),
                ('table_columns', good.replace('padj', 'qvalue')),
                ('table_row_shape', good + 'GENEFIX0100,1,1\n'),
                # a parser crash is a named refusal, never a traceback naming a host path
                ('table_malformed', good + 'GENEFIX0100,1,1,1,\x00\n'),
                # a field past the csv module's limit (131072 characters on every version)
                ('table_malformed', good + 'GENEFIX0100,' + 'x' * 200000 + ',1,1,1\n')):
            path.write_text(text)
            self.de_artifact(1)['replay_sha256'] = sha(path)
            self.assert_refused(reason)

    def test_refusal_codes_do_not_depend_on_the_interpreter(self):
        # The lane's 3.13 host refused a NUL table row as `table_value` where 3.8 said
        # `table_malformed`: csv reads NUL as data from 3.11. A long integer, carried or as a run
        # number, must not be `comparison_unreadable` on one Python and read on another.
        path = self.replay(2) / TABLE
        good = (FIXTURES / 'de_run2.csv').read_text()
        for name, table, long_key, long_run, expected in (
                ('nul', good + 'GENEFIX0100,1,1,1,\x00\n', False, False,
                 (2, '', 'refused: table_malformed\n')),
                ('carried', good, True, False, (0, EXPECTED, '')),
                ('run', good, True, True, (2, '', 'refused: table_unreadable\n'))):
            path.write_text(table)
            self.de_artifact(1)['replay_sha256'] = sha(path)
            data = json.loads(json.dumps(self.data))
            if long_key:
                data['carried'] = '@LONG@'
            if long_run:
                data['runs'][1]['run'] = '@LONG@'
            self.comparison.write_text(json.dumps(data).replace('"@LONG@"', '9' * 5000))
            seen = []
            for side in ('old', 'new'):
                with emulation.emulating(side, [rd]):
                    seen.append(emulation.outcome(rd.main, ['--comparison', str(self.comparison)]))
            self.assertEqual(seen, [expected, expected], name)
        print('red-on-fault guard: every refusal code is the same on both sides of each '
              'Python-version split')

    def test_spearman_and_ranks(self):
        self.assertEqual(rd.ranks([3.0, 1.0, 3.0, 2.0]), [3.5, 1.0, 3.5, 2.0])
        self.assertAlmostEqual(rd.spearman([(1, 3), (2, 2), (3, 1)]), -1.0)
        self.assertIsNone(rd.spearman([(1, 1)]))
        self.assertIsNone(rd.spearman([(1, 1), (1, 2)]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
