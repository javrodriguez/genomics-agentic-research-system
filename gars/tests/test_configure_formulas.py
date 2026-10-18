"""Formula choices built from the design's own columns (FIXES.md item R-formula).

`configure.py formulas --project P --assay A` offers numbered design formulas built from the
columns of `01_samplesheets/<assay>_design.csv`: the condition alone, then the condition adjusted
for each other column that varies (batch "adjusted for batch", subject "paired by subject").
A column nested in the condition cannot be separated from it and is shown `estimable: false`
with the reason, never as a choice. `apply --formula <n>` writes the menu's formula; a formula
typed instead is still checked term by term and written with a `formula_warning` that it was
not chosen from the menu (0315).
"""
import contextlib
import io
import json
import unittest

from support import GARS
import configure
import test_r164_params_mapping as mapping
from tools import policy

DE_TEMPLATE = ('reference:\n  fasta: <REQUIRED>\n  gtf: <REQUIRED>\n'
               'de:\n  formula: <REQUIRED>\n  contrast: <REQUIRED>\n')
# Batch crosses the conditions; each subject gives one sample to each condition (paired).
DESIGN = ('sample_id,condition,group,replicate,batch,subject\n'
          'A1,x,x,1,b1,d1\nA2,x,x,2,b2,d2\nB1,y,y,1,b1,d1\nB2,y,y,2,b2,d2\n')
# Batch nested in condition: b1 only under x, b2 only under y.
NESTED = ('sample_id,condition,group,replicate,batch\n'
          'A1,x,x,1,b1\nA2,x,x,2,b1\nB1,y,y,1,b2\nB2,y,y,2,b2\n')


class FormulaMenuTests(unittest.TestCase):
    def setUp(self):
        self.case = mapping.ConfigureApplyMappingTests('setUp')
        self.case.setUp()
        self.addCleanup(self.case.tearDown)
        self.project = self.case.project
        self.sheets = self.project / '01_samplesheets'
        self.sheets.mkdir()
        self.design(DESIGN)
        self.cfg = self.project / '_config/rnaseq_bulk.yaml'
        self.cfg.write_text(DE_TEMPLATE)

    def design(self, text):
        (self.sheets / 'rnaseq_bulk_design.csv').write_text(text)

    def call(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = configure.main(['--workspace', str(self.case.root)] + list(argv))
            except SystemExit as exc:
                return exc.code, {}
        return code, json.loads(out.getvalue())

    def formulas(self):
        return self.call('formulas', '--project', str(self.project), '--assay', 'rnaseq_bulk')

    def apply(self, *options):
        return self.call('apply', '--project', str(self.project), '--assay', 'rnaseq_bulk',
                         '--genome', 'G1', '--contrast', 'condition,x,y', *options)

    def test_the_menu_is_built_from_the_design_columns(self):
        code, result = self.formulas()
        self.assertEqual(code, 0, result)
        menu = result['formulas']
        self.assertEqual([f['formula'] for f in menu],
                         ['~ condition', '~ batch + condition', '~ subject + condition'])
        self.assertEqual([f['n'] for f in menu], ['01', '02', '03'])
        self.assertEqual([f['meaning'] for f in menu],
                         ['condition only', 'condition, adjusted for batch',
                          'condition, paired by subject'])
        self.assertTrue(all(f['estimable'] for f in menu), menu)

    def test_a_column_nested_in_the_condition_is_not_a_choice(self):
        self.design(NESTED)
        code, result = self.formulas()
        self.assertEqual(code, 0, result)
        nested = [f for f in result['formulas'] if f['formula'] == '~ batch + condition']
        self.assertEqual(len(nested), 1, result['formulas'])
        self.assertFalse(nested[0]['estimable'])
        self.assertIn('batch', nested[0]['reason'])
        before = self.cfg.read_bytes()
        code, result = self.apply('--formula', nested[0]['n'], '--dry-run')
        self.assertEqual(code, configure.EXIT_REFUSED, result)
        self.assertEqual(self.cfg.read_bytes(), before)

    def test_a_column_with_one_value_is_not_offered(self):
        self.design('sample_id,condition,group,replicate,batch\n'
                    'A1,x,x,1,b1\nA2,x,x,2,b1\nB1,y,y,1,b1\nB2,y,y,2,b1\n')
        code, result = self.formulas()
        self.assertEqual(code, 0, result)
        self.assertEqual([f['formula'] for f in result['formulas']], ['~ condition'])

    def test_a_menu_number_writes_that_formula(self):
        code, result = self.apply('--formula', '2', '--dry-run')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['formula'], '~ batch + condition')
        self.assertIn('formula: "~ batch + condition"', result['config_preview'])
        self.assertNotIn('formula_warning', result)

    def test_a_number_off_the_menu_is_refused_with_the_menu(self):
        """Run 11 ruling 2: an all-digit token that is not a menu number is answered with the
        numbered menu, never written as the formula "4" (REVIEW-a745042 finding 2)."""
        before = self.cfg.read_bytes()
        for token in ('4', '0', '00', '004', '12'):
            with self.subTest(token=token):
                code, result = self.apply('--formula', token, '--dry-run')
                self.assertEqual(code, configure.EXIT_REFUSED, result)
                self.assertIn('not a number on the formula menu', result.get('error', ''))
                self.assertEqual([f['n'] for f in result.get('formulas', [])],
                                 ['01', '02', '03'])
                self.assertNotIn('config_preview', result)
                self.assertEqual(self.cfg.read_bytes(), before)
        for token in ('3', '03', ' 3 '):
            with self.subTest(token=token):
                code, result = self.apply('--formula', token, '--dry-run')
                self.assertEqual(code, 0, result)
                self.assertEqual(result['formula'], '~ subject + condition')
                self.assertNotIn('formula_warning', result)

    def test_a_typed_formula_is_written_with_a_warning(self):
        code, result = self.apply('--formula', '~ batch + condition', '--dry-run')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['formula'], '~ batch + condition')
        self.assertIn('configure.py formulas', result['formula_warning'])
        code, result = self.apply('--formula', '~ donor + condition', '--dry-run')
        self.assertEqual(code, configure.EXIT_REFUSED, result)

    def test_the_guard_admits_the_formulas_command(self):
        """Fails until glitch-b5 applies lanes/gars-t74/R-formula-registry.patch."""
        tool, args = policy.parse_argv(
            ['python3', '_system/configure.py', 'formulas', '--project', 'projects/p',
             '--assay', 'rnaseq_bulk'], root=GARS)
        self.assertEqual(tool['name'], 'configure.formulas')
        self.assertEqual(args, {'project': 'projects/p', 'assay': 'rnaseq_bulk'})


class ContractTests(unittest.TestCase):
    def test_the_router_offers_and_passes_the_formula_menu(self):
        text = (GARS / '02_bioinformatics/CONTEXT.md').read_text()
        process = ' '.join(text.split('## Process', 1)[1].split('## Response Format', 1)[0].split())
        step = process.split('3a. ', 1)[1].split(' 4. ', 1)[0]
        self.assertIn('configure.py formulas --project', step)
        self.assertIn('--formula <n>', step)
        self.assertNotIn('--formula "<theirs>"', step)
        scope = ' '.join(text.split('## Scope Boundaries', 1)[1].split('## Definitions', 1)[0].split())
        self.assertNotIn('Change it only to a formula the user gave you', scope)
        render = text.split('**T9 — ', 1)[0].split('**T8 — ', 1)[-1]
        self.assertIn('`formulas`', render, 'T8 must say how the formula menu is rendered')


if __name__ == '__main__':
    unittest.main()
