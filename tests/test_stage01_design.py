#!/usr/bin/env python3
"""Row 1 design checks; development fixtures are synthetic and UNSEALED.

Run from repository root: python3 tests/test_stage01_design.py
Sealer interface (producer must not inspect or construct sealed cases):
GARS_SEALED_DESIGN_FIXTURES names a directory with exactly three subdirectories,
one complete stage-00 fixture project per directory. Each project contains
00_data/<assay>/{samples.csv,files.csv,raw/}, _config/<assay>.yaml, and expected.json:
{"reason": "<failure.check>", "detail_contains": "<required diagnostic substring>",
 "seal_type": "independent_context" or "external_human_seal"}.
Every RNA/ATAC project needs unit_of_replication and reference_release; RNA also needs strandedness; crossing subjects need paired: paired.
Paths in files.csv are project-relative; raw inputs must be synthetic, with no
patient-derived identifiers. Expected reasons use the stage-01 JSON failures'
check vocabulary. detail_contains distinguishes specific invalid_design refusals.
The runner invokes stage01_samplesheet.py --check, requires exit 1, ok=false,
and the named reason AND detail in the same failure; unrelated errors do not count.
Only recall, seal counts and per-project counts of failures outside the expected reason
are printed, never fixture contents.
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
        (self.project / '_config' / (assay + '.yaml')).write_text('strandedness: auto\nunit_of_replication: sample\nreference_release: synthetic-v1\n')
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

    def config(self, text):
        (self.project / '_config/rnaseq_bulk.yaml').write_text(text)

    def test_required_declarations(self):
        self.fixture()
        for key in ('unit_of_replication', 'reference_release'):
            for value in ('', "''", 'null', '<REQUIRED>'):
                self.config('strandedness: auto\nunit_of_replication: sample\nreference_release: synthetic-v1\n' + key + ': ' + value + '\n')
                self.refusal(key + '_undeclared')
        self.config('strandedness: auto\n')
        self.refusal('unit_of_replication_undeclared')
        self.refusal('reference_release_undeclared')

    def test_subject_nesting_and_pairing(self):
        self.fixture(extra={'subject': ['donor1', 'donor2', 'donor1', 'donor2']})
        self.refusal('subject_nesting')
        for paired in ('unpaired', 'paired'):
            self.config('strandedness: auto\nunit_of_replication: subject\nreference_release: synthetic-v1\npaired: ' + paired + '\n')
            if paired == 'unpaired':
                self.refusal('subject_nesting')
            else:
                self.assertEqual(check(self.project, write=True)[0], 0)
                self.assertIn('subject', (self.project / '01_samplesheets/rnaseq_bulk_design.csv').read_text())

    def test_subject_required_and_blank(self):
        self.fixture()
        self.config('strandedness: auto\nunit_of_replication: subject\nreference_release: synthetic-v1\n')
        self.refusal('subject_undeclared')
        self.fixture(extra={'subject': ['d1', '', 'd3', 'd4']})
        self.refusal('subject_undeclared')

    def test_declaration_values(self):
        self.fixture(extra={'subject': ['d1', 'd2', 'd3', 'd4']})
        for unit in ('sample', 'subject', 'cell_pseudobulk'):
            self.config('strandedness: auto\nunit_of_replication: ' + unit + '\nreference_release: arbitrary-synthetic-release\n')
            self.assertEqual(check(self.project)[0], 0)
        for declaration in ('unit_of_replication: guessed', 'paired: yes'):
            self.config('strandedness: auto\nunit_of_replication: sample\nreference_release: synthetic-v1\n' + declaration + '\n')
            self.refusal('config')

    def test_seeded_declarations(self):
        for assay in ('rnaseq_bulk', 'atacseq_bulk'):
            self.fixture(assay)
            seed = (REPO / 'gars/_templates/config' / (assay + '.yaml')).read_text()
            (self.project / '_config' / (assay + '.yaml')).write_text(seed)
            code, result = check(self.project)
            self.assertEqual(code, 1)
            entries = result['assays'][assay]['design_check']['declarations']
            for key in ('unit_of_replication', 'reference_release'):
                self.assertIn(key + ': <REQUIRED:', seed)
                self.assertEqual(entries[key], dict(value='', provenance='seeded_default', history_ref=None))
            self.assertEqual(entries['paired'], dict(value='', provenance='absent', history_ref=None))
            if assay == 'rnaseq_bulk':
                self.assertEqual(entries['strandedness'], dict(value='auto', provenance='seeded_default', history_ref=None))
            else:
                self.assertNotIn('strandedness', entries)

    def test_declared_provenance(self):
        self.fixture()
        code, result = check(self.project, write=True)
        self.assertEqual(code, 0)
        entries = result['assays']['rnaseq_bulk']['design_check']['declarations']
        for key, value in (('unit_of_replication', 'sample'), ('reference_release', 'synthetic-v1')):
            self.assertEqual(entries[key], dict(value=value, provenance='declared_in_config', history_ref=None))

    def test_paired_history_provenance(self):
        self.fixture(extra={'subject': ['d1', 'd2', 'd1', 'd2']})
        self.config('strandedness: auto\nunit_of_replication: subject\nreference_release: synthetic-v1\npaired: paired\n')
        line = '2026-09-14 rnaseq_bulk paired: paired; user answer: "These samples are paired."'
        (self.project / 'HISTORY.md').write_text(line + '\n')
        code, result = check(self.project, write=True)
        self.assertEqual(code, 0)
        record = result['assays']['rnaseq_bulk']['design_check']
        self.assertEqual(record['declarations']['paired']['history_ref'], 'HISTORY.md:1: ' + line)
        self.assertNotIn('provenance_warning', record)

    def test_paired_without_history_warning(self):
        self.fixture(extra={'subject': ['d1', 'd2', 'd1', 'd2']})
        self.config('strandedness: auto\nunit_of_replication: subject\nreference_release: synthetic-v1\npaired: paired\n')
        (self.project / 'HISTORY.md').write_text('paired: unpaired; user answer: "Unpaired."\n')
        code, result = check(self.project, write=True)
        self.assertEqual(code, 0)
        record = result['assays']['rnaseq_bulk']['design_check']
        self.assertIsNone(record['declarations']['paired']['history_ref'])
        self.assertEqual(record['provenance_warning'], 'paired declared without a HISTORY entry quoting the user')
        self.assertEqual(json.loads((self.project / '01_samplesheets/rnaseq_bulk_design_check.json').read_text()), record)

    def test_history_requires_exact_key(self):
        self.fixture(extra={'subject': ['d1', 'd2', 'd1', 'd2']})
        self.config('strandedness: auto\nunit_of_replication: subject\nreference_release: synthetic-v1\npaired: paired\n')
        (self.project / 'HISTORY.md').write_text('not-paired: paired\n')
        code, result = check(self.project, write=True)
        self.assertEqual(code, 0)
        record = result['assays']['rnaseq_bulk']['design_check']
        self.assertIsNone(record['declarations']['paired']['history_ref'])
        self.assertEqual(record['provenance_warning'], 'paired declared without a HISTORY entry quoting the user')

    def test_history_requires_exact_value(self):
        self.fixture()
        for value in ('synthetic-v1.1', 'synthetic-v1 extra', 'synthetic-v1/patch'):
            with self.subTest(value=value):
                (self.project / 'HISTORY.md').write_text('reference_release: ' + value + '\n')
                code, result = check(self.project)
                self.assertEqual(code, 0)
                entry = result['assays']['rnaseq_bulk']['design_check']['declarations']['reference_release']
                self.assertIsNone(entry['history_ref'])

    def test_history_selects_last_exact_entry(self):
        self.fixture()
        line = '2026-09-15 rnaseq_bulk reference_release: synthetic-v1; user answer: "synthetic-v1"'
        (self.project / 'HISTORY.md').write_text(
            'reference_release: synthetic-v1\n' + line + '\n'
            'reference_release: synthetic-v1.1\nnot-reference_release: synthetic-v1\n')
        code, result = check(self.project)
        self.assertEqual(code, 0)
        entry = result['assays']['rnaseq_bulk']['design_check']['declarations']['reference_release']
        self.assertEqual(entry['history_ref'], 'HISTORY.md:2: ' + line)

    def test_record_write_gates_and_contents(self):
        self.fixture()
        record = self.project / '01_samplesheets/rnaseq_bulk_design_check.json'
        self.assertEqual(check(self.project)[0], 0)
        self.assertFalse(record.exists())
        code, result = check(self.project, write=True)
        self.assertEqual(code, 0)
        saved = record.read_bytes()
        payload = json.loads(saved)
        self.assertEqual(payload, result['assays']['rnaseq_bulk']['design_check'])
        self.assertEqual(payload['unit_of_replication'], 'sample')
        self.assertEqual(payload['reference_release'], 'synthetic-v1')
        self.assertEqual(payload['paired'], '')
        self.assertTrue(payload['checks'])
        self.assertTrue(all(c['outcome'] == 'pass' for c in payload['checks']))
        self.assertIn('reference_release_declaration', [c['check'] for c in payload['checks']])
        self.assertEqual(check(self.project, write=True)[0], 2)
        self.assertEqual(record.read_bytes(), saved)
        for path in record.parent.glob('*.csv'):
            path.unlink()
        self.assertEqual(check(self.project, write=True)[0], 2)

    def test_demo_metadata(self):
        import shutil
        import gzip
        shutil.copytree(REPO / 'examples/demo-project', self.project, dirs_exist_ok=True)
        with (self.project / '00_data/rnaseq_bulk/files.csv').open() as fh:
            rows = csv.DictReader(line for line in fh if not line.startswith('#'))
            for row in rows:
                for key in ('fastq_1', 'fastq_2'):
                    path = self.project / row[key]
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(gzip.compress(b'@synthetic\nACGT\n+\nIIII\n', mtime=0))
        self.assertEqual(check(self.project)[0], 0)
        proc = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), '--force'],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        record = Path('01_samplesheets/rnaseq_bulk_design_check.json')
        self.assertEqual((self.project / record).read_bytes(),
                         (REPO / 'examples/demo-project' / record).read_bytes())

    def test_record_exit_gate_detects_tampering(self):
        import importlib.util
        from unittest.mock import patch
        spec = importlib.util.spec_from_file_location('stage01_record_test', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.fixture()
        result = module.validate_assay(self.project, 'rnaseq_bulk')
        original = Path.read_text
        def tampered(path, *args, **kwargs):
            if path.name.endswith('_design_check.json'):
                payload = json.loads(original(path, *args, **kwargs))
                payload['declarations']['paired']['history_ref'] = 'forged'
                return json.dumps(payload)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', tampered):
            _, failures = module.write_assay(self.project, 'rnaseq_bulk', result)
        self.assertTrue(any(f['check'] == 'exit_gate' for f in failures))


class SealedDesignTests(unittest.TestCase):
    def test_row_1_recall(self):
        root = os.environ.get('GARS_SEALED_DESIGN_FIXTURES')
        if not root:
            self.skipTest('GARS_SEALED_DESIGN_FIXTURES unset; sealed design recall unmeasured')
        projects = sorted(p for p in Path(root).iterdir() if p.is_dir())
        self.assertEqual(len(projects), 3, 'Row 1 requires exactly three sealed projects')
        caught, human = 0, 0
        for project_number, project in enumerate(projects, 1):
            expected = json.loads((project / 'expected.json').read_text())
            self.assertIn(expected['seal_type'], ('independent_context', 'external_human_seal'))
            self.assertTrue(isinstance(expected['reason'], str) and expected['reason'])
            self.assertTrue(isinstance(expected['detail_contains'], str) and expected['detail_contains'])
            code, result = check(project)
            failures = [f for a in result.get('assays', {}).values() for f in a['failures']]
            outside = sum(f['check'] != expected['reason'] for f in failures)
            print('Sealed project %d: failures outside expected reason: %d' % (project_number, outside))
            caught += int(code == 1 and result.get('ok') is False and any(
                f['check'] == expected['reason'] and expected['detail_contains'] in f['detail']
                for f in failures))
            human += int(expected['seal_type'] == 'external_human_seal')
        print('Sealed design recall: %d/3; external_human_seal: %d/3' % (caught, human))
        self.assertEqual(caught, 3, 'Row 1 sealed design recall requires 3/3')


if __name__ == '__main__':
    unittest.main(verbosity=2)
