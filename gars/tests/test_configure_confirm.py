"""A config write must equal the dry run the user was shown (FIXES.md item R-confirm).

`configure.py apply --dry-run` prints the config it would write and records that text's sha256
under the project; `apply` without `--dry-run` writes only when a recorded dry run of the same
assay would have written exactly the same bytes. A write with other settings than the dry run,
or with no dry run, or after the config changed underneath it, is refused (exit 1) and the
config keeps its bytes, so the agent cannot write a setting the user never saw in T9.
"""
import contextlib
import io
import json
import unittest

import support  # noqa: F401  -- puts gars/_system on the path, honours TMPDIR
import configure
import test_r164_params_mapping as mapping

DE_TEMPLATE = ('reference:\n  fasta: <REQUIRED>\n  gtf: <REQUIRED>\n'
               'de:\n  formula: <REQUIRED>\n  contrast: <REQUIRED>\n')
SC_TEMPLATE = ('reference:\n  fasta: <REQUIRED>\n  gtf: <REQUIRED>\n'
               'protocol: <REQUIRED>\naligner: simpleaf\n')


class ConfigureConfirmTests(unittest.TestCase):
    def setUp(self):
        self.case = mapping.ConfigureApplyMappingTests('setUp')
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.project = self.case.project
        sheets = self.project / '01_samplesheets'
        sheets.mkdir()
        (sheets / 'rnaseq_bulk_design.csv').write_text(
            'sample_id,condition,batch\nA1,x,b1\nA2,x,b2\nB1,y,b1\nB2,y,b2\nC1,z,b1\nC2,z,b2\n')
        self.cfg = self.project / '_config/rnaseq_bulk.yaml'
        self.cfg.write_text(DE_TEMPLATE)
        (self.project / '_config/scrnaseq.yaml').write_text(SC_TEMPLATE)

    def apply(self, assay, *options):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = configure.main(['--workspace', str(self.case.root), 'apply', '--project',
                                   str(self.project), '--assay', assay] + list(options))
        return code, json.loads(out.getvalue())

    def de(self, *options):
        return self.apply('rnaseq_bulk', '--genome', 'G1', *options)

    def assertRefusedUnchanged(self, code, result, path, before):
        self.assertEqual(code, configure.EXIT_REFUSED, result)
        self.assertFalse(result['ok'])
        self.assertNotIn('wrote', result)
        self.assertEqual(path.read_bytes(), before)

    def test_write_with_another_contrast_than_the_dry_run_is_refused(self):
        code, shown = self.de('--contrast', 'condition,x,y', '--dry-run')
        self.assertEqual(code, 0, shown)
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,z')
        self.assertRefusedUnchanged(code, result, self.cfg, before)
        self.assertIn('condition,x,y', result['error'], 'the refusal names the dry run shown')
        self.assertIn('condition,x,z', result['error'], 'the refusal names this write')

    def test_write_with_another_formula_than_the_dry_run_is_refused(self):
        code, shown = self.de('--contrast', 'condition,x,y', '--dry-run')
        self.assertEqual(code, 0, shown)
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,y', '--formula', '~ batch + condition')
        self.assertRefusedUnchanged(code, result, self.cfg, before)
        self.assertIn('~ condition', result['error'])
        self.assertIn('~ batch + condition', result['error'])

    def test_write_with_another_chemistry_than_the_dry_run_is_refused(self):
        sc = self.project / '_config/scrnaseq.yaml'
        code, shown = self.apply('scrnaseq', '--genome', 'G1', '--protocol', '10XV3',
                                 '--aligner', 'star', '--dry-run')
        self.assertEqual(code, 0, shown)
        before = sc.read_bytes()
        code, result = self.apply('scrnaseq', '--genome', 'G1', '--protocol', '10XV2',
                                  '--aligner', 'star')
        self.assertRefusedUnchanged(code, result, sc, before)
        self.assertIn('10XV3', result['error'])
        self.assertIn('10XV2', result['error'])

    def test_write_with_no_dry_run_is_refused(self):
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,y')
        self.assertRefusedUnchanged(code, result, self.cfg, before)
        self.assertIn('--dry-run', result['error'])

    def test_a_dry_run_of_another_assay_does_not_clear_this_one(self):
        code, shown = self.apply('scrnaseq', '--genome', 'G1', '--protocol', '10XV3',
                                 '--dry-run')
        self.assertEqual(code, 0, shown)
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,y')
        self.assertRefusedUnchanged(code, result, self.cfg, before)

    def test_a_refused_dry_run_records_nothing(self):
        code, shown = self.de('--contrast', 'condition,x,w', '--dry-run')
        self.assertEqual(code, configure.EXIT_REFUSED, shown)
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,y')
        self.assertRefusedUnchanged(code, result, self.cfg, before)

    def test_write_after_the_config_changed_since_the_dry_run_is_refused(self):
        code, shown = self.de('--contrast', 'condition,x,y', '--dry-run')
        self.assertEqual(code, 0, shown)
        self.cfg.write_text(DE_TEMPLATE + 'qc:\n  min_counts: 5\n')
        before = self.cfg.read_bytes()
        code, result = self.de('--contrast', 'condition,x,y')
        self.assertRefusedUnchanged(code, result, self.cfg, before)
        self.assertIn('changed since the dry run', result['error'])

    def test_a_hand_made_record_of_another_shape_is_refused_as_none(self):
        code, shown = self.de('--contrast', 'condition,x,y', '--dry-run')
        self.assertEqual(code, 0, shown)
        record = self.project / configure.dry_run_record('rnaseq_bulk')
        before = self.cfg.read_bytes()
        for forged in ('[]', '{"sha256": 7}', '{"assay": "rnaseq_bulk"}', 'not json'):
            with self.subTest(record=forged):
                record.write_text(forged)
                code, result = self.de('--contrast', 'condition,x,y')
                self.assertRefusedUnchanged(code, result, self.cfg, before)
                self.assertIn('--dry-run', result['error'])

    def test_same_arguments_write_the_bytes_the_dry_run_showed(self):
        code, shown = self.de('--contrast', '02', '--dry-run')
        self.assertEqual(code, 0, shown)
        self.assertEqual(self.cfg.read_text(), DE_TEMPLATE, 'the dry run wrote no config')
        code, result = self.de('--contrast', '02')
        self.assertEqual(code, 0, result)
        self.assertEqual(self.cfg.read_text(), shown['config_preview'])
        self.assertEqual(result['wrote'], '_config/rnaseq_bulk.yaml')
        # Re-applying the same settings to the written file yields the same bytes, so the
        # dry run the user saw still matches: the write is idempotent, not a replay of others.
        code, again = self.de('--contrast', '02')
        self.assertEqual(code, 0, again)
        self.assertEqual(self.cfg.read_text(), shown['config_preview'])


if __name__ == '__main__':
    unittest.main()
