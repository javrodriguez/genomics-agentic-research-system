"""Stage 01's declarations come from numbered menus, written by the script (FIXES.md item S01-declare).

`configure.py declare --project P --assay A` lists the declarations stage 01 needs for that assay
(RNA strandedness; RNA/ATAC replication unit, reference release and experimental pairing) with
which are still undeclared; `--key K` prints that key's numbered menu, each value with what it
means; `--key K --select N` writes exactly the menu's value into `_config/<assay>.yaml` as a
top-level key, keeping every other line, and appends the declaration line to `HISTORY.md`. A
value not on the menu ("the libraries are dUTP") is refused with nothing written. The reference
release is offered from the genome registry's rows, never typed (0313).
"""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from support import GARS
import configure
import stage01_samplesheet as stage01
from tools import policy


class DeclareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='stage01-declare-')
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'gars'
        self.workspace.mkdir()
        (self.workspace / '_references').symlink_to(GARS / '_references', target_is_directory=True)
        self.project = self.workspace / 'projects/p'
        (self.project / '_config').mkdir(parents=True)
        for assay in ('rnaseq_bulk', 'atacseq_bulk'):
            (self.project / '00_data' / assay).mkdir(parents=True)
            shutil.copy(str(GARS / '_templates/config' / (assay + '.yaml')),
                        str(self.project / '_config' / (assay + '.yaml')))
        self.history = self.project / 'HISTORY.md'
        self.history.write_text('# History\n')
        self.cfg = self.project / '_config/rnaseq_bulk.yaml'

    def declare(self, assay, *options):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            try:
                code = configure.main(['--workspace', str(self.workspace), 'declare',
                                       '--project', str(self.project), '--assay', assay]
                                      + list(options))
            except SystemExit as exc:
                return exc.code, {}
        return code, json.loads(out.getvalue())

    def test_the_overview_names_the_undeclared_keys(self):
        code, result = self.declare('rnaseq_bulk')
        self.assertEqual(code, 0, result)
        self.assertEqual([k['key'] for k in result['keys']],
                         ['strandedness', 'unit_of_replication', 'reference_release', 'paired'])
        self.assertEqual(result['undeclared'], ['unit_of_replication', 'reference_release'])
        code, result = self.declare('atacseq_bulk')
        self.assertEqual(code, 0, result)
        self.assertNotIn('strandedness', [k['key'] for k in result['keys']])

    def test_each_menu_offers_exactly_the_values_stage01_accepts(self):
        for key in ('strandedness', 'unit_of_replication', 'paired'):
            with self.subTest(key=key):
                code, result = self.declare('rnaseq_bulk', '--key', key)
                self.assertEqual(code, 0, result)
                options = result['options']
                self.assertEqual({o['value'] for o in options},
                                 set(stage01.CONFIG_RULES[key]['values']))
                self.assertEqual([o['n'] for o in options],
                                 ['%02d' % i for i in range(1, len(options) + 1)])
                self.assertTrue(all(o['meaning'] for o in options), options)

    def test_a_number_writes_exactly_the_menu_value_and_the_history_line(self):
        code, menu = self.declare('rnaseq_bulk', '--key', 'strandedness')
        self.assertEqual(code, 0, menu)
        chosen = menu['options'][0]
        before = self.cfg.read_text().splitlines()
        code, result = self.declare('rnaseq_bulk', '--key', 'strandedness', '--select', '1')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['value'], chosen['value'])
        after = self.cfg.read_text().splitlines()
        changed = [(a, b) for a, b in zip(before, after) if a != b]
        self.assertEqual(len(before), len(after))
        self.assertEqual(changed, [('strandedness: auto', 'strandedness: %s' % chosen['value'])])
        value, err = stage01.read_config_scalar(self.cfg, 'strandedness')
        self.assertEqual((value, err), (chosen['value'], None))
        self.assertIn(result['history_entry'], self.history.read_text().splitlines())
        record = stage01.declaration_record(self.project, 'rnaseq_bulk')['strandedness']
        self.assertIsNotNone(record['history_ref'], record)

    def test_free_text_is_refused_and_nothing_is_written(self):
        cfg, history = self.cfg.read_bytes(), self.history.read_bytes()
        for answer in ('the libraries are dUTP', 'dUTP', 'Reverse', '0', '9'):
            with self.subTest(answer=answer):
                code, result = self.declare('rnaseq_bulk', '--key', 'strandedness',
                                            '--select', answer)
                self.assertEqual(code, configure.EXIT_REFUSED, result)
                self.assertIn('options', result, 'a refusal shows the same menu again')
                self.assertEqual(self.cfg.read_bytes(), cfg)
                self.assertEqual(self.history.read_bytes(), history)

    def test_the_reference_release_comes_from_the_genome_registry(self):
        rows, err = configure.read_genomes(self.workspace)
        self.assertIsNone(err)
        code, menu = self.declare('rnaseq_bulk', '--key', 'reference_release')
        self.assertEqual(code, 0, menu)
        self.assertEqual(len(menu['options']), len(rows))
        for option, row in zip(menu['options'], sorted(rows, key=lambda r: r['id'])):
            self.assertTrue(option['value'].startswith(row['id']), (option, row['id']))
        code, result = self.declare('rnaseq_bulk', '--key', 'reference_release', '--select', '1')
        self.assertEqual(code, 0, result)
        value, err = stage01.read_config_scalar(self.cfg, 'reference_release')
        self.assertEqual((value, err), (menu['options'][0]['value'], None))

    def test_pairing_is_added_when_the_config_has_no_such_key(self):
        cfg = self.project / '_config/atacseq_bulk.yaml'
        self.assertNotIn('\npaired:', cfg.read_text())
        code, result = self.declare('atacseq_bulk', '--key', 'paired', '--select', 'paired')
        self.assertEqual(code, 0, result)
        self.assertEqual(stage01.read_config_scalar(cfg, 'paired'), ('paired', None))
        record = stage01.declaration_record(self.project, 'atacseq_bulk')['paired']
        self.assertIsNotNone(record['history_ref'], record)

    def test_a_key_the_assay_does_not_take_is_a_usage_error(self):
        before = (self.project / '_config/atacseq_bulk.yaml').read_bytes()
        code, result = self.declare('atacseq_bulk', '--key', 'strandedness', '--select', '1')
        self.assertEqual(code, configure.EXIT_USAGE, result)
        self.assertEqual((self.project / '_config/atacseq_bulk.yaml').read_bytes(), before)

    def test_the_guard_admits_the_declare_command(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S01-declare-registry.patch."""
        tool, args = policy.parse_argv(
            ['python3', '_system/configure.py', 'declare', '--project', 'projects/p',
             '--assay', 'rnaseq_bulk', '--key', 'strandedness', '--select', '1'], root=GARS)
        self.assertEqual(tool['name'], 'configure.declare')
        self.assertEqual(args, {'project': 'projects/p', 'assay': 'rnaseq_bulk',
                                'key': 'strandedness', 'select': '1'})


class ContractTests(unittest.TestCase):
    def test_stage01_declares_through_the_menu(self):
        text = (GARS / '01_prepare_samplesheets/CONTEXT.md').read_text()
        process = ' '.join(text.split('## Process', 1)[1].split('## Response Format', 1)[0].split())
        step2 = process.split('2. ', 1)[1].split(' 3. ', 1)[0]
        self.assertIn('configure.py declare', step2, 'step 2 must run the declaration menu')
        self.assertNotIn('Write exactly their supplied values', step2)
        self.assertRegex(step2, r'[Aa]ny other reply[^.]*T9 again',
                         'a reply that is not a menu number re-sends T9')
        t9 = text.split('**T9 — ', 1)[1].split('```', 2)[1]
        self.assertIn('<n>.', t9, 'T9 shows each key as a numbered menu')
        self.assertNotIn('nonblank release name', t9)


if __name__ == '__main__':
    unittest.main()
