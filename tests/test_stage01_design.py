#!/usr/bin/env python3
"""Row 1 design checks; development fixtures are synthetic and UNSEALED.

Run from repository root: python3 tests/test_stage01_design.py
Sealer interface (producer must not inspect or construct sealed cases):
GARS_SEALED_DESIGN_FIXTURES names a directory with exactly three subdirectories,
one complete stage-00 fixture project per directory. Each project contains
00_data/<assay>/{samples.csv,files.csv,raw/}, _config/<assay>.yaml, and expected.json:
{"reason": "<failure.check>", "detail_contains": "<required diagnostic substring>",
 "seal_type": "independent_context" or "external_human_seal"}.
Paths in files.csv are project-relative; raw inputs must be synthetic, with no
patient-derived identifiers. Expected reasons use the stage-01 JSON failures'
check vocabulary. detail_contains distinguishes specific invalid_design refusals.
The runner invokes stage01_samplesheet.py --check, requires exit 1, ok=false,
and the named reason AND detail in the same failure; unrelated errors do not count.
Only aggregate recall and seal counts are printed, never fixture contents.
Exactly 3/3 is Row 1's exit threshold (full §7.2 remains 9/9). Unset variable is
SKIPPED, never PASS. Empty/malformed fixture sets fail. Public claims additionally
require all three external_human_seal fixtures; this runner never edits README.
"""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / 'gars/_system/stage01_samplesheet.py'


def check(project, write=False):
    proc = subprocess.run([sys.executable, str(SCRIPT), '--project', str(project)]
                          + ([] if write else ['--check']), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    return proc.returncode, json.loads(proc.stdout)


class DevelopmentDesignTests(unittest.TestCase):
    """Unsealed development cases, excluded from design recall; deterministic seed 0."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gars-design-dev-')
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)

    def fixture(self, assay='rnaseq_bulk', extra=None, conditions=None):
        conditions = conditions or ['A', 'A', 'B', 'B']
        data = self.project / '00_data' / assay
        data.mkdir(parents=True, exist_ok=True)
        (self.project / '_config').mkdir(exist_ok=True)
        (self.project / '_config' / (assay + '.yaml')).write_text('strandedness: auto\n')
        fields = ['sample_id', 'condition', 'group', 'replicate'] + list(extra or {})
        rows = []
        for i, condition in enumerate(conditions):
            row = ['DEV%d' % i, condition, condition, str(conditions[:i].count(condition) + 1)]
            row += [values[i] for values in (extra or {}).values()]
            rows.append(row)
        with (data / 'samples.csv').open('w', newline='') as fh:
            csv.writer(fh).writerows([fields] + rows)
        with (data / 'files.csv').open('w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['sample_id', 'lane', 'fastq_1', 'fastq_2'])
            for i in range(len(rows)):
                raw = data / ('DEV%d.fastq' % i)
                raw.write_text('@synthetic\nACGT\n+\nIIII\n')
                writer.writerow(['DEV%d' % i, '1', str(raw.relative_to(self.project)), ''])
        return data

    def refusal(self, reason):
        code, result = check(self.project)
        self.assertEqual(code, 1)
        self.assertFalse(result['ok'])
        failures = [f for a in result['assays'].values() for f in a['failures']]
        self.assertIn(reason, [f['check'] for f in failures])
        self.assertEqual(result['wrote'], [])
        code, result = check(self.project, write=True)
        self.assertEqual(code, 1)
        self.assertEqual(result['wrote'], [])
        self.assertFalse((self.project / '01_samplesheets').exists())

    def test_clean_and_auto_preserved(self):
        self.fixture()
        self.assertEqual(check(self.project)[0], 0)

    def test_batch_confounding(self):
        self.fixture(extra={'batch': ['x', 'x', 'y', 'y']})
        self.refusal('confounded_condition')

    def test_crossed_batch_preserved_in_output(self):
        self.fixture(extra={'batch': ['x', 'y', 'x', 'y']})
        self.assertEqual(check(self.project, write=True)[0], 0)
        output = self.project / '01_samplesheets/rnaseq_bulk_design.csv'
        self.assertIn('batch', output.read_text().splitlines()[0])
        self.assertEqual(check(self.project)[0], 0)

    def test_constant_batch_is_not_confounded(self):
        self.fixture(extra={'batch': ['x'] * 4})
        self.assertEqual(check(self.project)[0], 0)

    def test_atac_floor_per_condition(self):
        self.fixture('atacseq_bulk', conditions=['A', 'B', 'B'])
        self.refusal('insufficient_biological_replicates')

    def test_atac_clean(self):
        self.fixture('atacseq_bulk')
        self.assertEqual(check(self.project)[0], 0)

    def test_missing_strandedness(self):
        self.fixture()
        (self.project / '_config/rnaseq_bulk.yaml').write_text('# undeclared\n')
        self.refusal('strandedness_undeclared')

    def test_duplicate_sample_id(self):
        data = self.fixture()
        path = data / 'samples.csv'
        path.write_text(path.read_text().replace('DEV1,', 'DEV0,'))
        self.refusal('invalid_design')


class SealedDesignTests(unittest.TestCase):
    def test_row_1_recall(self):
        root = os.environ.get('GARS_SEALED_DESIGN_FIXTURES')
        if not root:
            self.skipTest('GARS_SEALED_DESIGN_FIXTURES unset; sealed design recall unmeasured')
        projects = sorted(p for p in Path(root).iterdir() if p.is_dir())
        self.assertEqual(len(projects), 3, 'Row 1 requires exactly three sealed projects')
        caught, human = 0, 0
        for project in projects:
            expected = json.loads((project / 'expected.json').read_text())
            self.assertIn(expected['seal_type'], ('independent_context', 'external_human_seal'))
            self.assertTrue(isinstance(expected['reason'], str) and expected['reason'])
            self.assertTrue(isinstance(expected['detail_contains'], str) and expected['detail_contains'])
            code, result = check(project)
            failures = [f for a in result.get('assays', {}).values() for f in a['failures']]
            caught += int(code == 1 and result.get('ok') is False and any(
                f['check'] == expected['reason'] and expected['detail_contains'] in f['detail']
                for f in failures))
            human += int(expected['seal_type'] == 'external_human_seal')
        print('Sealed design recall: %d/3; external_human_seal: %d/3' % (caught, human))
        self.assertEqual(caught, 3, 'Row 1 sealed design recall requires 3/3')


if __name__ == '__main__':
    unittest.main(verbosity=2)
