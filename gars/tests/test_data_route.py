"""R-063: every route-table column remains bound to decision 0100."""
import csv
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO

# Independent transcription of the execution cells: changing either side requires review.
EXECUTION = {
    'public': ('local (purpose `fixture` only), homelab (`fixture`, `internal`, `pilot_internal`), slurm (`fixture`, `internal`; `pilot_internal` only with a non-`none` `agreement_ref`)',
               'local:fixture|homelab:fixture|homelab:internal|homelab:pilot_internal|slurm:fixture|slurm:internal|slurm:pilot_internal'),
    'deidentified_under_agreement': ('slurm only (`internal`; `pilot_internal` only with a non-`none` `agreement_ref`), under the institution\'s terms; `pilot_external`/`commercial` refused everywhere until a cloud/agreement record exists',
                                    'slurm:internal|slurm:pilot_internal'),
    'identifiable': ('none: every run is refused', 'none'),
}


class DataRouteTests(unittest.TestCase):
    def test_every_cell_matches_record(self):
        path = GARS / '_references/data_policy.tsv'
        with path.open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle, delimiter='\t')
            rows = list(reader)
        fields = ['data_class', 'permitted_backends', 'storage_venues', 'provider_exposure',
                  'backup_second_destination', 'retention_rule', 'expiry_rule', 'approval_rule']
        self.assertEqual(reader.fieldnames, fields)
        self.assertEqual(len(rows), 3)
        self.assertEqual({r['data_class'] for r in rows}, set(EXECUTION))
        text = (REPO / 'docs/decisions/0100-row-8-data-handling.md').read_text()
        recorded = [[c.strip() for c in line.split('|')[1:-1]] for line in text.splitlines()
                    if line.startswith('| `')]
        self.assertEqual(len(recorded), 3)
        for actual, cells in zip(rows, recorded):
            name = cells[0].strip('`')
            self.assertEqual(cells[1], EXECUTION[name][0])
            exposure = {'yes': 'yes', 'no': 'no',
                        'no: sample-level metadata and data never enter a prompt': 'no'}[cells[3]]
            expected = [name, EXECUTION[name][1], cells[2], exposure] + cells[4:]
            self.assertEqual([actual[key] for key in fields], expected)
            self.assertTrue(all(actual.values()))
        print('data route recorded: 3/3')


if __name__ == '__main__':
    unittest.main(verbosity=2)
