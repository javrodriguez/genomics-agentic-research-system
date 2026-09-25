"""R-062: full grid, exact FASTQ exemption, executed venue and refusal ordering."""
import csv
import datetime
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, write_fixture_dataset
if not (GARS / '_system/venue_policy.py').is_file():
    raise ImportError('missing gars/_system/venue_policy.py')
import venue_policy as vp
import executorlib as ex
import wrapperlib as wl
import stage00_register as register

PURPOSES = ('fixture', 'internal', 'pilot_internal', 'pilot_external', 'commercial')
# Each cell is independently specified in purpose order, with an agreement recorded.
GRID = {
    'public': {'local': (1, 0, 0, 0, 0), 'homelab': (1, 1, 1, 0, 0), 'slurm': (1, 1, 1, 0, 0)},
    'deidentified_under_agreement': {'local': (0, 0, 0, 0, 0), 'homelab': (0, 0, 0, 0, 0), 'slurm': (0, 1, 1, 0, 0)},
    'identifiable': {'local': (0, 0, 0, 0, 0), 'homelab': (0, 0, 0, 0, 0), 'slurm': (0, 0, 0, 0, 0)},
}


def row(data_class='public', purpose='fixture'):
    return dict(data_class=data_class, purpose=purpose, agreement_ref='fixture-agreement',
                input_data_location='[]', expiry='2099-01-01')


def write_row(root, values):
    path = root / '00_data/dataset.tsv'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.chmod(0o644)
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(values), delimiter='\t', lineterminator='\n')
        writer.writeheader(); writer.writerow(values)
    path.chmod(0o444)


def prepare(root, dataset=None, memory=None, fastq=False):
    (root / '_config').mkdir(exist_ok=True)
    config = root / '_config/rnaseq_bulk.yaml'
    config.write_text('compute:\n  cpus: 1\n' + ('  mem: ' + memory + '\n' if memory is not None else ''))
    stage = root / '02_bioinformatics/rnaseq_bulk/99_fixture'
    stage.mkdir(parents=True)
    (stage / 'submit.sh').write_text('#!' + os.path.join(os.sep, 'bin', 'bash') + '\nexit 0\n')
    inputs = {'config': config}
    if fastq:
        blob = root / 'w1-01.fq.gz'; blob.write_bytes(b'fixture')
        sheet = root / 'samplesheet.csv'
        sheet.write_text('sample,fastq_1,fastq_2\ns1,' + str(blob) + ',\n')
        inputs['samplesheet'] = sheet
    if dataset is not None:
        write_row(root, dataset)
    wl.write_reproducibility(stage, 'rnaseq_bulk', root, inputs, [])
    return stage


class PolicyFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        marker = patch.object(ex, 'HOMELAB_MARKER', str(self.root / 'operator-marker'))
        marker.start(); self.addCleanup(marker.stop)

    def no_effects(self, root, backend):
        backend.assert_not_called()
        self.assertFalse(list(ex._records(root).glob('*.json')))
        self.assertFalse(list(root.glob(os.path.join('03_custom_analysis', '*', 'run', 'launch-*.sh'))))
        self.assertFalse(list(root.glob('03_custom_analysis/*/' + ex.ANALYSIS_SUBMISSIONS)))


class VenuePolicyTests(PolicyFixture):
    def test_full_grid(self):
        self.assertEqual(set(vp.routes()), set(GRID))
        self.assertEqual(vp.PURPOSES, PURPOSES)
        for data_class in vp.routes():
            for venue in vp.VENUES:
                for index, purpose in enumerate(PURPOSES):
                    with self.subTest(data_class=data_class, venue=venue, purpose=purpose):
                        self.assertEqual(not vp.check(row(data_class, purpose), venue, purpose, 2*1024**3, []),
                                         bool(GRID[data_class][venue][index]))
        for data_class in ('public', 'deidentified_under_agreement'):
            candidate = row(data_class, 'pilot_internal'); candidate['agreement_ref'] = 'none'
            self.assertIn('agreement_ref', str(vp.check(candidate, 'slurm', 'pilot_internal', None, [])))

    def test_memory_boundary_absence_and_unparseable(self):
        for memory, allowed, code in ((None, True, ''), ('8G', True, ''), ('8.5G', False, 'venue_not_permitted'),
                                      ('garbage', False, 'resource_unparseable')):
            root = self.root / str(memory); root.mkdir()
            stage = prepare(root, row(), memory)
            with patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                job, why = ex.submit(root, stage / 'submit.sh', ex.LOCAL)
                self.assertEqual(job == '42', allowed, why)
                if not allowed:
                    self.assertIn(code, why); self.no_effects(root, backend)
        self.assertIn('resource_undeclared', str(vp.check(row('public', 'internal'), 'local', 'internal', None, [])))
        self.assertFalse(vp.check(row('public', 'internal'), 'slurm', 'internal', None, []))
        self.assertFalse(vp.check(row('public', 'internal'), 'homelab', 'internal', None, []))

    def test_expiry_unclassified_narrowing_and_widening(self):
        for expiry in (None, '', 'none', '2000-01-01', 'not-a-date'):
            candidate = row('deidentified_under_agreement', 'internal'); candidate['expiry'] = expiry
            self.assertIn('dataset_expired', str(vp.check(candidate, 'slurm', 'internal', None, [])))
        stage = prepare(self.root)
        with patch.object(ex, '_submit_once') as backend:
            job, why = ex.submit(self.root, stage / 'submit.sh')
            self.assertIsNone(job); self.assertIn('dataset_unclassified', why)
            self.no_effects(self.root, backend)
        candidate = row(); candidate['permitted_backends'] = 'slurm:fixture'
        self.assertTrue(vp.check(candidate, 'local', 'fixture', None, []))
        self.assertFalse(vp.check(candidate, 'slurm', 'fixture', None, []))
        candidate['permitted_backends'] = 'slurm:commercial'
        self.assertTrue(vp.check(candidate, 'slurm', 'commercial', None, []))
        with self.assertRaisesRegex(ValueError, 'permitted_backends_widened'):
            vp.narrowed('public', 'local:internal')

    def test_marker_is_constant_not_environment(self):
        self.assertEqual(ex.venue_of(ex.LOCAL), 'local')
        with patch.dict(os.environ, {'GARS_HOMELAB': '1', 'GARS_HOMELAB_MARKER': '1', 'GARS_TEST_MODE': '1',
                                    'GARS_SKIP_VENUE_POLICY': '1', 'GARS_VENUE': 'homelab'}):
            self.assertEqual(ex.venue_of(ex.LOCAL), 'local')
            self.assertTrue(vp.check(row('identifiable'), 'local', 'fixture', None, []))
        Path(ex.HOMELAB_MARKER).touch()
        self.assertEqual(ex.venue_of(ex.LOCAL), 'homelab')
        self.assertEqual(ex.venue_of(ex.SLURM), 'slurm')
        # No environment read may supply a production policy decision.
        import ast
        for source in (GARS / '_system/venue_policy.py',):
            tree = ast.parse(source.read_text(), feature_version=(3, 6))
            self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr in ('environ', 'getenv') for n in ast.walk(tree)))

    def test_w1_blobs_and_renamed_fastq(self):
        from support import module
        bench = module(REPO / 'scripts/backend_bench.py', 'venue_bench')
        stage = prepare(self.root, row())
        blobs = self.root / 'workload'; blobs.mkdir()
        bench.workload(blobs)
        inputs = {'config': self.root / '_config/rnaseq_bulk.yaml'}
        inputs.update({path.name: path for path in blobs.glob('*.bin.gz')})
        wl.write_reproducibility(stage, 'rnaseq_bulk', self.root, inputs, [])
        with patch.object(ex, '_submit_once', return_value=('42', None)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh', ex.LOCAL), ('42', None))
        other = self.root / 'renamed'; other.mkdir()
        candidate = row(purpose='internal')
        second = prepare(other, candidate)
        lines = ['sample,fastq_1,fastq_2']
        for number, path in enumerate(sorted(blobs.glob('*.bin.gz'))):
            target = other / (path.name.replace('.bin.gz', '.fq.gz'))
            path.rename(target)
            lines.append('s%d,%s,' % (number, target))
        sheet = other / 'sheet.csv'; sheet.write_text('\n'.join(lines)+'\n')
        wl.write_reproducibility(second, 'rnaseq_bulk', other,
                                 {'config': other / '_config/rnaseq_bulk.yaml', 'samplesheet': sheet}, [])
        with patch.object(ex, '_submit_once') as backend:
            job, why = ex.submit(other, second / 'submit.sh', ex.LOCAL)
            self.assertIsNone(job); self.assertIn('FASTQ rule', why); self.no_effects(other, backend)

    def test_environment_cannot_bypass_submit(self):
        stage = prepare(self.root, row('identifiable'))
        with patch.dict(os.environ, {'GARS_TEST_MODE': '1', 'GARS_SKIP_VENUE_POLICY': '1'}), \
                patch.object(ex, '_submit_once') as backend:
            job, why = ex.submit(self.root, stage / 'submit.sh', ex.LOCAL)
            self.assertIsNone(job); self.assertIn('class_not_permitted', why)
            self.no_effects(self.root, backend)

    def test_inputs_missing_and_absent_samplesheet(self):
        stage = prepare(self.root, row(), fastq=True)
        (self.root / 'w1-01.fq.gz').unlink()
        with patch.object(ex, '_submit_once') as backend:
            job, why = ex.submit(self.root, stage / 'submit.sh', ex.LOCAL)
            self.assertIsNone(job); self.assertIn('input_missing', why)
            self.no_effects(self.root, backend)
        other = self.root / 'other'; other.mkdir()
        stage = prepare(other, row())
        with patch.object(ex, '_submit_once', return_value=('42', None)):
            self.assertEqual(ex.submit(other, stage / 'submit.sh', ex.LOCAL), ('42', None))

    def test_finalize_route_lock_and_legacy_migration(self):
        base = {k: row()[k] for k in register.DATASET_BASE_FIELDS}
        values = register.dataset_values(self.root, base, 'local:fixture')
        register.write_dataset_record(self.root, values)
        path = self.root / '00_data/dataset.tsv'; old = path.read_bytes(), path.stat().st_mtime_ns
        register.write_dataset_record(self.root, values)
        self.assertEqual(old, (path.read_bytes(), path.stat().st_mtime_ns))
        for permitted, expiry in ((None, None), ('local:fixture', '2099-01-01')):
            with self.assertRaisesRegex(ValueError, 'dataset_classification_locked'):
                register.dataset_values(self.root, base, permitted, expiry)
        path.unlink(); write_row(self.root, base); old = path.read_bytes().splitlines()
        register.write_dataset_record(self.root, register.dataset_values(self.root, base))
        new = path.read_bytes().splitlines()
        self.assertTrue(all(b.startswith(a+b'\t') for a,b in zip(old,new)))
        self.assertEqual(path.stat().st_mode & 0o777, 0o444)
        path.unlink()
        private = dict(base, data_class='deidentified_under_agreement')
        with self.assertRaisesRegex(ValueError, 'dataset_expired'):
            register.dataset_values(self.root, private)
        with self.assertRaisesRegex(ValueError, 'class_not_permitted'):
            register.dataset_values(self.root, dict(base, data_class='identifiable'))
        Path(ex.HOMELAB_MARKER).touch()
        with self.assertRaisesRegex(ValueError, 'storage_venue_not_permitted'):
            register.dataset_values(self.root, private, expiry='2099-01-01')


class LocalFastqExemptionTests(PolicyFixture):
    def test_every_class_purpose_and_malformed_row(self):
        candidates = [row(c, p) for c in GRID for p in PURPOSES]
        candidates += [row('Public'), row(purpose='fixture '), row('public '), row(purpose='Fixture'),
                       row('unknown'), row(purpose='unknown')]
        for field in ('data_class', 'purpose'):
            missing = row(); del missing[field]; candidates.append(missing)
        for number, candidate in enumerate(candidates):
            with self.subTest(candidate=candidate):
                root = self.root / str(number); root.mkdir()
                stage = prepare(root, candidate, fastq=True)
                with patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                    job, why = ex.submit(root, stage / 'submit.sh', ex.LOCAL)
                    allowed = candidate.get('data_class') == 'public' and candidate.get('purpose') == 'fixture'
                    self.assertEqual(job == '42', allowed, why)
                    if not allowed:
                        self.assertIn('FASTQ rule', why); self.no_effects(root, backend)


class ExecutedDescriptorTests(PolicyFixture):
    def test_explicit_local_overrides_missing_descriptor(self):
        stage = prepare(self.root, row('deidentified_under_agreement', 'internal'))
        manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
        self.assertEqual(manifest['venue'], 'slurm')
        with patch.object(ex, '_local_submit') as backend:
            job, why = ex.submit(self.root, stage / 'submit.sh', descriptor=ex.LOCAL)
            self.assertIsNone(job); self.assertIn('venue_not_permitted', why); self.assertIn('venue local', why)
            self.no_effects(self.root, backend)
        commands = self.root / 'bin'; commands.mkdir()
        stub = commands / 'sbatch'; stub.write_text('#!' + os.path.join(os.sep, 'bin', 'bash') + '\necho Submitted batch job 42\n'); stub.chmod(0o755)
        with patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), ('42', None))

    def test_prepare_and_executed_venues_both_recorded(self):
        for descriptor in (ex.LOCAL, ex.SLURM):
            root = self.root / descriptor['name']; root.mkdir()
            stage = prepare(root, row())
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                self.assertEqual(ex.submit(root, stage / 'submit.sh', descriptor), ('42', None))
            self.assertEqual(ex.stage_record(root, stage)['venue'], descriptor['name'])
            self.assertEqual(json.loads((stage / 'reproducibility/manifest.json').read_text())['venue'], 'slurm')


class SubmissionOrderingTests(PolicyFixture):
    def analysis(self, candidate):
        write_row(self.root, candidate)
        adir = self.root / '03_custom_analysis/01_fixture'; adir.mkdir(parents=True)
        (adir / 'PLAN.md').write_text('Runs: login-node (user-requested)\n')
        script = adir / 'script.sh'; script.write_text('#!' + os.path.join(os.sep, 'bin', 'bash') + '\nexit 0\n')
        return adir, script

    def test_login_node_grades_slurm_and_records_local_executor(self):
        adir, script = self.analysis(row('public', 'internal'))
        with patch.object(ex, '_analysis_approval', return_value=(True, None)), \
                patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
            self.assertEqual(ex.submit(self.root, script, ex.SLURM), ('42', None))
            self.assertEqual(backend.call_args[0][2]['name'], 'local')
        entry = ex._analysis_entries(adir)[0]
        self.assertEqual((entry['executor'], entry['venue']), ('local', 'slurm'))

    def test_analysis_refusal_before_launcher_and_backend(self):
        adir, script = self.analysis(row('identifiable'))
        with patch.object(ex, '_analysis_approval', return_value=(True, None)), patch.object(ex, '_submit_once') as backend:
            job, why = ex.submit(self.root, script, ex.SLURM)
            self.assertIsNone(job); self.assertIn('class_not_permitted', why)
            self.no_effects(self.root, backend)

    def test_analysis_memory_declarations(self):
        adir, script = self.analysis(row())
        original = script.read_text()
        for declarations, reason in (
                ('#SBATCH --mem=8G\n', None),
                ('#SBATCH --mem=16G\n', 'memory rule: above 8 GiB'),
                ('#SBATCH --mem=2G\n#SBATCH --mem=4G\n', 'resource_unparseable')):
            with self.subTest(declarations=declarations):
                script.write_text(original.splitlines(True)[0] + declarations + 'exit 0\n')
                with patch.object(ex, '_analysis_approval', return_value=(True, None)), \
                        patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                    job, why = ex.submit(self.root, script, ex.LOCAL)
                    if reason is None:
                        self.assertEqual((job, why), ('42', None))
                        backend.assert_called_once()
                        entry = ex._analysis_entries(adir)[0]
                        self.assertEqual((entry['executor'], entry['venue']), ('local', 'local'))
                        (adir / ex.ANALYSIS_SUBMISSIONS).unlink()
                        Path(entry['launcher']).unlink()
                    else:
                        self.assertIsNone(job)
                        self.assertIn(reason, why)
                        self.no_effects(self.root, backend)

    def test_existing_analysis_refusals_first(self):
        adir, script = self.analysis(row('identifiable'))
        with patch.object(ex, '_analysis_approval', return_value=(False, 'not approved')):
            self.assertIn('R-073', ex.submit(self.root, script)[1])
        with patch.object(ex, '_analysis_approval', return_value=(True, None)):
            for job, state, expected in ((None, None, 'R-077'), ('42', None, 'R-077'), ('42', 'RUNNING', 'R-076')):
                (adir / ex.ANALYSIS_SUBMISSIONS).write_text(json.dumps(dict(script=str(script), job_id=job, executor='slurm'))+'\n')
                with patch.object(ex, '_scheduler_status', return_value=(state, None)), patch.object(ex, '_submit_once') as backend:
                    self.assertIn(expected, ex.submit(self.root, script)[1]); backend.assert_not_called()

    def test_existing_stage02_refusals_first(self):
        stage = prepare(self.root, row('identifiable'))
        config = self.root / '_config/rnaseq_bulk.yaml'; original = config.read_text()
        config.write_text(original+'changed: yes\n')
        self.assertIn('config_sha256', ex.submit(self.root, stage / 'submit.sh')[1])
        config.write_text(original)
        (stage / 'STATUS').write_text('COMPLETE fixture\n')
        self.assertIn('R-152', ex.submit(self.root, stage / 'submit.sh')[1])
        (stage / 'STATUS').unlink()
        key = ex.prepared_key(self.root, stage); directory = ex._records(self.root); directory.mkdir(exist_ok=True)
        (directory / (key+'.json')).write_text(json.dumps(dict(state='SUBMITTED')))
        self.assertIn('R-076', ex.submit(self.root, stage / 'submit.sh')[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
