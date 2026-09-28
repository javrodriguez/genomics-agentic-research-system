"""R-076 binds the generated analysis script (0205).

Prepare writes a downstream stage's analysis script under scripts/, and submit.sh runs it.
A script changed between prepare and submit, by hand or by an outside process, must be
refused at submit, never run; one changed after submit must be refused at collect.
"""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, write_fixture_dataset
import executorlib as ex
import wrapperlib as wl

WRAPPERS = {'rnaseq-de': 'run_de.py', 'scrna-qc-cluster': 'run_scrna.py',
            'spatial-cluster-count': 'count_clusters.py'}
REFUSAL = 'R-076: idempotency_key_missing_or_changed; run prepare'


def load_wrapper(name):
    source = GARS / '_system/wrappers' / name / (name.replace('-', '_') + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), str(source))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Prepared:
    """One real downstream prepare in a disposable project (the test_downstream_keys fixture)."""

    def __init__(self, name, tmp):
        self.module = module = load_wrapper(name)
        self.root = root = Path(tmp)
        (root / '_config').mkdir()
        write_fixture_dataset(root)
        cfg_path = root / '_config' / (module.ASSAY + '.yaml')
        cfg_path.write_text('fixture: declared\n')
        self.stage = root / '02_bioinformatics' / module.ASSAY / module.SUBSTAGE
        sheet = root / 'sheet.csv'
        sheet.write_text('sample\ns1\n')
        data = root / 'data'
        data.write_text('declared input\n')
        design = (root / '01_samplesheets/rnaseq_bulk_design.csv'
                  if name == 'rnaseq-de' else root / 'design')
        design.parent.mkdir(exist_ok=True)
        design.write_text('sample,condition\ns1,A\n')
        self.paths = {'substage': self.stage, 'config': cfg_path, 'samplesheet': sheet,
                      'inputs': [('s1', data)]}
        self.cfg = {'de.formula': '~condition', 'de.contrast': 'condition,A,B',
                    'qc.min_genes': '1', 'qc.min_cells': '1', 'qc.max_mito_pct': '20',
                    'n_hvg': '2000', 'cluster_resolution': '1'}
        self.args = argparse.Namespace(project=str(root), counts=str(data), design=str(design),
                                       h5ad=str(data))
        self.script = self.stage / 'scripts' / WRAPPERS[name]
        self.prepare()

    def prepare(self):
        with patch.object(self.module, 'run_checks', return_value=([], self.cfg, self.paths)), \
                contextlib.redirect_stdout(io.StringIO()):
            assert self.module.cmd_prepare(self.args) == 0

    def submit(self, job='42'):
        with patch.object(ex, '_submit_once', return_value=(job, None)) as backend:
            result = ex.submit(self.root, self.stage / 'submit.sh')
        return result, backend.call_count

    def manifest(self):
        return json.loads((self.stage / 'reproducibility/manifest.json').read_text())


class ScriptBindingTests(unittest.TestCase):
    def assertRefusedPrepare(self, case, message):
        """A refused prepare is a named JSON refusal with EXIT_REFUSED, never a traceback."""
        out = io.StringIO()
        with patch.object(case.module, 'run_checks', return_value=([], case.cfg, case.paths)), \
                contextlib.redirect_stdout(out), self.assertRaises(SystemExit) as caught:
            case.module.cmd_prepare(case.args)
        self.assertEqual(caught.exception.code, wl.EXIT_REFUSED)
        result = json.loads(out.getvalue())
        self.assertEqual((result['command'], result['ok']), ('prepare', False))
        self.assertIn(message, result['error'])
        self.assertNotIn('# idempotency_key=', (case.stage / 'submit.sh').read_text())

    def each_wrapper(self, check):
        for name in WRAPPERS:
            with self.subTest(wrapper=name), tempfile.TemporaryDirectory() as tmp:
                check(Prepared(name, tmp))

    def test_script_changed_after_prepare_is_refused_at_submit(self):
        """C1: one changed byte in the generated script, then submit: refused, nothing run."""
        def check(case):
            body = case.script.read_bytes()
            changed = body.replace(b'import', b'imp0rt', 1)
            self.assertEqual(len(changed), len(body))
            self.assertNotEqual(changed, body)
            case.script.write_bytes(changed)  # same size: only the bytes differ
            result, calls = case.submit()
            self.assertEqual(result, (None, REFUSAL))
            self.assertEqual(calls, 0)
            self.assertEqual(list(ex._records(case.root).glob('*.json')), [])
        self.each_wrapper(check)

    def test_file_added_beside_the_script_is_refused_at_submit(self):
        """C2: the script's own folder is first on its import path, so an added module counts."""
        def check(case):
            (case.script.parent / 'pandas.py').write_text('raise SystemExit(0)\n')
            result, calls = case.submit()
            self.assertEqual(result, (None, REFUSAL))
            self.assertEqual(calls, 0)
        self.each_wrapper(check)

    def test_script_removed_or_replaced_by_a_link_is_refused(self):
        """C2b: a missing script, or the same bytes behind a symlink, is not the prepared script."""
        def check(case):
            body = case.script.read_bytes()
            case.script.unlink()
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
            elsewhere = case.root / 'elsewhere.py'
            elsewhere.write_bytes(body)
            os.symlink(str(elsewhere), str(case.script))
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
        self.each_wrapper(check)

    def test_unchanged_script_submits_and_a_later_change_blocks_collect(self):
        """C3: the prepared script submits once; changed after submit, collect cannot bind it."""
        def check(case):
            self.assertEqual(case.submit(), (('42', None), 1))
            key = case.manifest()['idempotency_key']
            self.assertEqual(ex.stage_record(case.root, case.stage)['idempotency_key'], key)
            case.script.write_bytes(case.script.read_bytes() + b'# changed while queued\n')
            with self.assertRaises(ValueError):
                ex.stage_record(case.root, case.stage)
        self.each_wrapper(check)

    def test_prepare_again_restores_the_script_and_the_key(self):
        """C4 (control): re-running prepare regenerates the script, and submit accepts it."""
        def check(case):
            key = case.manifest()['idempotency_key']
            case.script.write_bytes(b'# replaced\n')
            case.prepare()
            self.assertEqual(case.manifest()['idempotency_key'], key)
            self.assertEqual(case.submit(), (('42', None), 1))
        self.each_wrapper(check)

    def test_added_file_is_never_folded_into_a_new_key(self):
        """C6 (review r1 F-2): the refusal says "run prepare"; prepare then refuses to bind the
        added module, and only its removal lets the stage prepare and submit."""
        def check(case):
            added = case.script.parent / 'pandas.py'
            added.write_text('raise SystemExit(0)\n')
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
            self.assertRefusedPrepare(case, 'prepare refused: scripts/ holds 1 entries')
            self.assertTrue(added.exists())
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
            added.unlink()
            case.prepare()
            self.assertEqual(case.submit(), (('42', None), 1))
        self.each_wrapper(check)

    def test_an_input_named_inside_scripts_is_not_an_allowance(self):
        """C6b (review r2 F-6): a caller-supplied input path inside scripts/ appears in
        submit.sh's text; the allow-list is the wrapper's own, so prepare still refuses."""
        def check(case):
            added = case.script.parent / 'pandas.py'
            added.write_text('raise SystemExit(0)\n')
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
            case.args.counts = case.args.h5ad = str(added)
            self.assertRefusedPrepare(case, 'prepare refused: scripts/ holds 1 entries')
            if case.module.ASSAY == 'rnaseq_bulk':  # the route review r2 reproduced
                self.assertIn('"%s"' % added.resolve(), (case.stage / 'submit.sh').read_text())
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
        self.each_wrapper(check)

    def test_scripts_folder_linked_before_prepare_is_refused(self):
        """C7 (review r1 F-1): a scripts/ that is a link when prepare runs never gets a key,
        so an edit behind the link cannot submit."""
        def check(case):
            elsewhere = case.root / 'elsewhere'
            case.script.parent.rename(elsewhere)
            os.symlink(str(elsewhere), str(case.stage / 'scripts'))
            self.assertRefusedPrepare(case, 'prepare refused: scripts/ is not a real folder')
            (elsewhere / case.script.name).write_text('raise SystemExit(0)\n')
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
        self.each_wrapper(check)

    def test_legacy_formula_is_refused_at_submit_but_still_collects(self):
        """C5: a stage prepared before 0205 (downstream-v1) is re-prepared, not submitted;
        a job already submitted under it still binds at collect."""
        def check(case):
            manifest_path = case.stage / 'reproducibility/manifest.json'
            submit_sh = case.stage / 'submit.sh'
            manifest = case.manifest()
            legacy = dict(manifest, key_formula='downstream-v1')
            legacy['idempotency_key'] = wl.input_key(case.stage, legacy)
            self.assertNotEqual(legacy['idempotency_key'], manifest['idempotency_key'])
            manifest_path.write_text(json.dumps(legacy))
            submit_sh.write_text(submit_sh.read_text().replace(
                manifest['idempotency_key'], legacy['idempotency_key']))
            self.assertEqual(ex.prepared_key(case.root, case.stage), legacy['idempotency_key'])
            self.assertEqual(case.submit(), ((None, REFUSAL), 0))
            # A v1 job submitted before the landing: its record still binds collect.
            records = ex._records(case.root)
            records.mkdir(exist_ok=True)
            (records / (legacy['idempotency_key'] + '.json')).write_text(json.dumps({
                'idempotency_key': legacy['idempotency_key'], 'script': str(submit_sh.resolve()),
                'state': 'COMPLETED', 'executor': 'local', 'job_id': '7'}))
            self.assertEqual(ex.stage_record(case.root, case.stage)['job_id'], '7')
        self.each_wrapper(check)


class AllowListTests(unittest.TestCase):
    def test_the_allow_list_is_each_wrappers_generated_script(self):
        """C8: GENERATED_SCRIPTS names exactly what each downstream prepare writes (C4 would
        refuse otherwise); an unknown wrapper may hold no scripts."""
        self.assertEqual({k: set(v) for k, v in wl.GENERATED_SCRIPTS.items()},
                         {k: {v} for k, v in WRAPPERS.items()})
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp)
            wl.require_generated_scripts_only(stage, 'another-wrapper')
            (stage / 'scripts').mkdir()
            wl.require_generated_scripts_only(stage, 'another-wrapper')
            (stage / 'scripts/run_de.py').write_text('')
            with self.assertRaisesRegex(ValueError, 'holds 1 entries'):
                wl.require_generated_scripts_only(stage, 'another-wrapper')
            wl.require_generated_scripts_only(stage, 'rnaseq-de')
            elsewhere = stage / 'real'
            elsewhere.mkdir()
            (stage / 'scripts/run_de.py').unlink()
            (stage / 'scripts').rmdir()
            os.symlink(str(elsewhere), str(stage / 'scripts'))
            with self.assertRaisesRegex(ValueError, 'prepare refused: scripts/ is not a real folder'):
                wl.require_generated_scripts_only(stage, 'another-wrapper')


class ScriptFormulaTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.stage = self.root / 'stage'
        (self.stage / 'scripts').mkdir(parents=True)
        counts = self.root / 'counts'
        counts.write_bytes(b'gene\n')
        self.manifest = {'key_formula': 'downstream-v2', 'params': {'n': 1},
                         'inputs': {'counts': str(counts)}}

    def key(self):
        return wl.input_key(self.stage, self.manifest)

    def test_every_script_tree_difference_changes_the_key(self):
        """G1: content, name, a new file, a nested file, a link and an empty folder each count."""
        script = self.stage / 'scripts/run.py'
        script.write_bytes(b'print(1)\n')
        seen = {self.key()}
        script.write_bytes(b'print(2)\n'); seen.add(self.key())
        script.rename(self.stage / 'scripts/ran.py'); seen.add(self.key())
        (self.stage / 'scripts/extra.py').write_bytes(b''); seen.add(self.key())
        (self.stage / 'scripts/pkg').mkdir(); seen.add(self.key())
        (self.stage / 'scripts/pkg/__init__.py').write_bytes(b''); seen.add(self.key())
        os.symlink('ran.py', str(self.stage / 'scripts/link.py')); seen.add(self.key())
        self.assertEqual(len(seen), 7)

    def test_same_tree_same_key_and_v1_ignores_scripts(self):
        """G2: the key is a function of bytes and names only; v1 is unchanged by 0205."""
        (self.stage / 'scripts/run.py').write_bytes(b'print(1)\n')
        first = self.key()
        self.assertEqual(self.key(), first)
        legacy = dict(self.manifest, key_formula='downstream-v1')
        before = wl.input_key(self.stage, legacy)
        (self.stage / 'scripts/run.py').write_bytes(b'print(2)\n')
        self.assertEqual(wl.input_key(self.stage, legacy), before)
        self.assertNotEqual(self.key(), first)

    def test_missing_or_linked_scripts_folder_is_its_own_state(self):
        """G3: no scripts/ folder differs from the real one; a link to an identical folder has
        no key at all (review r1 F-1)."""
        (self.stage / 'scripts/run.py').write_bytes(b'print(1)\n')
        real = self.key()
        copy = self.root / 'copy'
        copy.mkdir()
        (copy / 'run.py').write_bytes(b'print(1)\n')
        (self.stage / 'scripts/run.py').unlink()
        (self.stage / 'scripts').rmdir()
        self.assertNotEqual(self.key(), real)
        os.symlink(str(copy), str(self.stage / 'scripts'))
        with self.assertRaisesRegex(ValueError, 'scripts/ is not a real folder'):
            self.key()

    @unittest.skipIf(os.geteuid() == 0, 'root lists every folder')
    def test_a_folder_the_walk_cannot_list_has_no_key(self):
        """G4 (review r1 F-3): Python can import from a folder it cannot list, so the walk
        raises rather than frame such a folder as empty."""
        package = self.stage / 'scripts/pandas'
        package.mkdir()
        (package / '__init__.py').write_bytes(b'')
        os.chmod(str(package), 0o311)
        self.addCleanup(os.chmod, str(package), 0o755)
        with self.assertRaises(PermissionError):
            self.key()


if __name__ == '__main__':
    unittest.main(verbosity=2)
