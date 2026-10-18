"""S00-class migration (0321, choice 1c): `migrate_data_class.py --dry-run` reports, writes nothing.

Under 1c no existing value changes meaning, so the migration is the identity: the script walks
`projects/*/00_data/dataset.tsv`, prints what each row's class and purpose now mean, lists for a
person every row with `pilot_external` or `commercial` (no route ever served them), and has no
live mode.
"""
import json
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

from support import GARS, bytes_in

HEADER = ['data_class', 'purpose', 'agreement_ref', 'input_data_location',
          'permitted_backends', 'provider_exposure', 'retention', 'expiry']
# Every pair the old vocabulary could register, and what it means under 1c.
PAIRS = {
    ('public', 'fixture'): 'public, test',
    ('public', 'internal'): 'public, analysis',
    ('public', 'pilot_internal'): 'public, legacy pilot_internal, cluster needs its agreement',
    ('public', 'pilot_external'): 'public, legacy pilot_external, no route',
    ('public', 'commercial'): 'public, legacy commercial, no route',
    ('deidentified_under_agreement', 'fixture'): 'restricted (deidentified_under_agreement), '
                                                 'test, no route',
    ('deidentified_under_agreement', 'internal'): 'restricted (deidentified_under_agreement), '
                                                  'analysis',
    ('deidentified_under_agreement', 'pilot_internal'):
        'restricted (deidentified_under_agreement), legacy pilot_internal, '
        'cluster needs its agreement',
    ('deidentified_under_agreement', 'pilot_external'):
        'restricted (deidentified_under_agreement), legacy pilot_external, no route',
    ('deidentified_under_agreement', 'commercial'):
        'restricted (deidentified_under_agreement), legacy commercial, no route',
    ('identifiable', 'fixture'): 'restricted (identifiable), test, no route',
    ('identifiable', 'internal'): 'restricted (identifiable), analysis, no route',
}


class MigrationDryRunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='migrate-data-class-'))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.ws = self.tmp / 'gars'
        shutil.copytree(str(GARS / '_system'), str(self.ws / '_system'),
                        ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(str(GARS / '_references'), str(self.ws / '_references'))
        self.names = {}
        for i, (pair, _) in enumerate(sorted(PAIRS.items())):
            name = 'p%02d' % i
            self.names[name] = pair
            data = self.ws / 'projects' / name / '00_data'
            data.mkdir(parents=True)
            row = [pair[0], pair[1], 'none', '[]', 'slurm:internal', 'no', 'x', '2027-12-31']
            (data / 'dataset.tsv').write_text('\t'.join(HEADER) + '\n' + '\t'.join(row) + '\n')
        (self.ws / 'projects/unregistered/00_data').mkdir(parents=True)

    def run_script(self, *args):
        done = subprocess.run([sys.executable, str(self.ws / '_system/migrate_data_class.py'),
                               '--workspace', str(self.ws)] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=120)
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            return done.returncode, {'stderr': done.stderr, 'stdout': done.stdout}

    def test_the_dry_run_prints_every_rows_meaning_and_writes_nothing(self):
        before = bytes_in(self.tmp)
        code, result = self.run_script('--dry-run')
        self.assertEqual(code, 0, result)
        self.assertEqual(bytes_in(self.tmp), before)
        rows = {r['project']: r for r in result['rows']}
        self.assertEqual(sorted(rows), sorted(self.names))
        for name, pair in self.names.items():
            with self.subTest(project=name, pair=pair):
                self.assertEqual((rows[name]['data_class'], rows[name]['purpose']), pair)
                self.assertEqual(rows[name]['means'], PAIRS[pair])
        self.assertEqual(result['written'], [])

    def test_pilot_external_and_commercial_rows_are_listed_for_a_person(self):
        code, result = self.run_script('--dry-run')
        self.assertEqual(code, 0, result)
        expected = sorted(n for n, p in self.names.items()
                          if p[1] in ('pilot_external', 'commercial'))
        self.assertEqual(sorted(r['project'] for r in result['for_a_person']), expected)

    def test_there_is_no_live_mode(self):
        before = bytes_in(self.tmp)
        code, result = self.run_script()
        self.assertEqual(code, 2, result)
        self.assertIn('no live mode', result.get('error', ''))
        self.assertEqual(bytes_in(self.tmp), before)

    def test_an_unreadable_row_is_listed_never_skipped(self):
        bad = self.ws / 'projects/p00/00_data/dataset.tsv'
        bad.write_text('data_class\tpurpose\n')
        code, result = self.run_script('--dry-run')
        self.assertEqual(code, 0, result)
        self.assertIn('p00', [r['project'] for r in result['for_a_person']])
        self.assertEqual([r['means'] for r in result['rows'] if r['project'] == 'p00'],
                         ['unreadable'])


if __name__ == '__main__':
    unittest.main()
