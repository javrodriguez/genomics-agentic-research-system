"""R-091 instrument self-test, never the owner's real Slurm re-run result."""
import ast
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO, GARS, module, run
import wrapperlib as wl
import executorlib as ex

INSTRUMENT = REPO / 'scripts/rerun_check.py'
if not INSTRUMENT.is_file():
    raise ImportError('missing scripts/rerun_check.py (instrument self-test)')
import manifest_check as mc
rc = module(INSTRUMENT, 'rerun_instrument')


def checked(argv, **kwargs):
    result = run(argv, **kwargs)
    if result.returncode:
        raise AssertionError(result.stdout.decode() + result.stderr.decode())
    return result.stdout.decode()


class RerunCheckTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.ws = self.repo / 'gars'
        self.ws.mkdir(parents=True)
        for folder in ('_system', '_references'):
            shutil.copytree(str(GARS / folder), str(self.ws / folder))
        (self.repo / 'scripts').mkdir()
        shutil.copyfile(str(INSTRUMENT), str(self.repo / 'scripts/rerun_check.py'))
        self.wrappers = self.ws / 'test-wrappers'
        shutil.copytree(str(GARS / 'tests/fixtures/rerun-fixture'), str(self.wrappers / 'rerun-fixture'))
        # The fixture computes WORKSPACE with the same depth as real wrappers.
        self.wrapper = self.wrappers / 'rerun-fixture/rerun_fixture.py'
        # Place at the actual depth; override root still separates it from real inventory.
        self.wrappers = self.ws / '_system/test-wrappers'
        shutil.move(str(self.ws / 'test-wrappers'), str(self.wrappers))
        self.wrapper = self.wrappers / 'rerun-fixture/rerun_fixture.py'
        (self.repo / '.rerun-self-test').write_text('suite only\n')
        (self.ws / '_system/gars-env.sh').write_text(':\n')
        checked(['git', 'init', '-q', self.repo])
        checked(['git', '-C', self.repo, 'add', 'gars', 'scripts', '.rerun-self-test'])
        self.commit()
        self.project = self.ws / 'projects/original'
        (self.project / '_config').mkdir(parents=True)
        (self.project / '_config/executor.yaml').write_text('name: local\n')
        (self.project / '_config/rerun-fixture.yaml').write_text('compute:\n  cpus: 1\n')
        (self.project / '01_samplesheets').mkdir()
        (self.project / '01_samplesheets/rerun-fixture_samplesheet.csv').write_text('sample\nfixture\n')
        (self.project / '00_data').mkdir()
        (self.project / '00_data/dataset.tsv').write_text(
            'purpose\tdata_class\tinput_data_location\nfixture\tpublic\tsynthetic\n')
        (self.project / 'HISTORY.md').write_text('# fixture\n')
        checked([sys.executable, self.wrapper, 'prepare', '--project', self.project])
        self.stage = self.project / '02_bioinformatics/rerun-fixture/01_rerun-fixture'
        self.path = self.stage / 'reproducibility/manifest.json'
        self.prepared = json.loads(self.path.read_text())
        job, why = ex.submit(self.project, self.stage / 'submit.sh')
        self.assertIsNotNone(job, why)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            state, why = ex.status(self.project, job)
            if state == 'COMPLETED':
                break
            self.assertIn(state, ('PENDING', 'RUNNING', 'SUBMITTED'), why)
            time.sleep(0.02)
        self.assertEqual(state, 'COMPLETED')
        checked([sys.executable, self.wrapper, 'collect', '--project', self.project, '--model', 'none'])
        self.manifest = json.loads(self.path.read_text())
        self.assertTrue(mc.grade(self.manifest)['ok'])
        self.out = self.repo / 'replays'

    def commit(self):
        checked(['git', '-C', self.repo, '-c', 'user.name=fixture', '-c',
                 'user.email=fixture@example.invalid', 'commit', '-qm', 'instrument fixture'])

    def cli(self, expected=0, env=None, runs=2):
        result = run([sys.executable, self.repo / 'scripts/rerun_check.py', self.path,
                      '--runs', str(runs), '--out', self.out, '--wrappers-root', self.wrappers], env=env)
        text = result.stdout.decode() + result.stderr.decode()
        self.assertEqual(result.returncode, expected, text)
        return text

    def save(self, manifest):
        self.path.write_text(json.dumps(manifest))

    def refusal(self, reason, env=None):
        text = self.cli(expected=2, env=env)
        self.assertIn(reason, text)
        self.assertFalse(self.out.exists(), 'refusal ran something')

    def test_instrument_self_test(self):
        text = self.cli()
        self.assertEqual(json.loads((self.stage / 'run/seed.json').read_text())['seed'],
                         self.prepared['random_seeds'][0]['seed'])
        self.assertFalse(self.prepared['no-rng-in-code-path'])
        self.assertEqual(self.prepared['seed_source'], 'os.urandom(16)')
        self.assertIn('reproduction: 2/2', text)
        result = json.loads((self.out / 'comparison.json').read_text())
        self.assertEqual(len(result['runs']), 2)
        self.assertEqual(text.count('graded 2 of 2 outputs'), 2)
        for run_result in result['runs']:
            self.assertTrue(run_result['job'])
            replay_stage = self.out / ('run-%d' % run_result['run']) / '02_bioinformatics/rerun-fixture/01_rerun-fixture'
            replay_manifest = json.loads((replay_stage / 'reproducibility/manifest.json').read_text())
            self.assertEqual(json.loads((replay_stage / 'run/seed.json').read_text())['seed'],
                             replay_manifest['random_seeds'][0]['seed'])
            artifacts = run_result['artifacts']
            self.assertEqual({r['path'] for r in artifacts}, {r['path'] for r in self.manifest['outputs']})
            for row in artifacts:
                self.assertIn(row['path'] + ' ' + row['mode'], text)
                self.assertTrue(row['match'])
                if row['mode'] == 'byte_stable':
                    self.assertEqual(row['original_sha256'], row['replay_sha256'])
                else:
                    self.assertNotEqual(row['original_sha256'], row['replay_sha256'])
                    print('MEASURE instrument self-test run %d: max_absolute_error=%s; bytes differ' %
                          (run_result['run'], row['value']))
        print('reproduction: 2/2')
        print('EXIT instrument self-test (fixture, local): reproduction 2/2')

    def test_byte_change_one_of_two(self):
        # Plant only after worker execution, before real collect hashes the artifact.
        source = self.wrapper.read_text().replace("wl.require_collect_config(project, ASSAY, SUBSTAGE)",
            "wl.require_collect_config(project, ASSAY, SUBSTAGE)\n"
            "        if project.name == 'run-2':\n"
            "            (stage / 'run/stable.txt').write_text('id\\tvalue\\nb\\t2\\na\\t1\\n')")
        self.wrapper.write_text(source)
        text = self.cli(expected=1)
        self.assertIn('reproduction: 1/2', text)
        self.assertIn('run/stable.txt byte_stable match=no', text)

    def test_unlisted_defaults_to_exact_bytes(self):
        rule = rc.rule_for([], 'anything', dict(type='table', path='run/stable.txt'))
        self.assertEqual(rule['mode'], 'byte_stable')
        other = self.repo / 'other'
        (other / 'run').mkdir(parents=True)
        (other / 'run/stable.txt').write_text('id\tvalue\nb\t2\na\t1\n')
        result = rc.compare_artifact(self.stage, other, self.manifest['outputs'][0], rule)
        self.assertFalse(result['match'])
        # If an execution changes the original after preflight, it cannot move
        # the comparison baseline away from the manifest's recorded hash.
        (self.stage / 'run/stable.txt').write_bytes((other / 'run/stable.txt').read_bytes())
        with self.assertRaisesRegex(ValueError, 'original output drifted'):
            rc.compare_artifact(self.stage, other, self.manifest['outputs'][0], rule)

    def test_numeric_threshold_and_canonicalization(self):
        left, right = self.repo / 'left', self.repo / 'right'
        left.mkdir(); right.mkdir()
        (left / 'table.tsv').write_text('# original metadata\nid\tx\ty\na\t1\t2\nb\t3\t4\n')
        row = dict(type='fixture_numeric', role='native', path='table.tsv')
        rule = dict(mode='numeric_tolerance', metric='max_absolute_error', threshold=0.000001)
        for value, expected in (('1.000000999', True), ('1.000001001', False)):
            (right / 'table.tsv').write_text('# other metadata\ny\tx\tid\n4.0\t3.0\tb\n2\t'+value+'\ta\n')
            result = rc.compare_artifact(left, right, row, rule)
            self.assertEqual(result['match'], expected)
            self.assertNotEqual(result['original_sha256'], result['replay_sha256'])
        (right / 'table.tsv').write_text('id\tx\ty\na\tNaN\t2\n')
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            rc.compare_artifact(left, right, row, rule)

    def test_all_refusals_and_contract_agreement(self):
        base = copy.deepcopy(self.manifest)
        changes = [ ('pipeline_commit', 'f' * 40, 'pipeline_commit differs from HEAD'),
                    ('gars_commit', 'f' * 40, 'gars_commit differs from HEAD') ]
        for key, value, reason in changes:
            manifest = copy.deepcopy(base); manifest[key] = value; self.save(manifest)
            self.refusal(reason)
        manifest = copy.deepcopy(base); del manifest['execution_config']; self.save(manifest)
        self.assertFalse(mc.grade(manifest)['groups'][2]['present'])
        self.refusal('no execution config recorded')
        for group in mc.load_schema()['groups']:
            if not mc.applicable(group, base['predicate_facts']):
                continue
            manifest = copy.deepcopy(base)
            for field in group['fields']:
                manifest.pop(field, None)
            self.assertFalse(mc.grade(manifest)['ok'], group['number'])
            self.save(manifest)
            self.refusal('no execution config recorded' if group['number'] == 3 else 'incomplete manifest')
        self.save(base)
        source = Path(base['inputs']['samplesheet'])
        old = source.read_bytes(); source.write_bytes(old + b'changed\n')
        self.refusal('input hash changed'); source.write_bytes(old)
        (self.stage / 'STATUS').write_text('FAILED\n')
        self.refusal('run status is not COMPLETE')

    def test_execution_config_immutable_and_drift_refused(self):
        self.assertEqual(self.prepared['execution_config'], self.manifest['execution_config'])
        self.assertEqual(self.prepared['execution_config_resolved'], self.manifest['execution_config_resolved'])
        self.assertEqual(self.prepared['idempotency_key'], wl.input_key(self.stage, self.manifest))
        descriptor = self.project / '_config/executor.yaml'
        descriptor.write_text('name: local\n# drift\n')
        self.refusal('execution config drifted:')

    def test_slurm_unavailable(self):
        manifest = copy.deepcopy(self.manifest)
        manifest.update(backend='slurm', venue='slurm', resources=dict(Elapsed='1', MaxRSS='1K', AllocCPUS='1'))
        manifest['predicate_facts']['backend'] = 'slurm'
        manifest['execution_config_resolved']['backend'] = 'slurm'
        self.save(manifest)
        bin_dir = self.repo / 'git-only-bin'
        bin_dir.mkdir()
        (bin_dir / 'git').symlink_to(shutil.which('git'))
        self.refusal('second backend unavailable', env={'PATH': str(bin_dir)})

    def test_tolerance_refusals(self):
        tolerance = self.ws / '_references/tolerances.yaml'
        original = json.loads(tolerance.read_text())
        for key, value, reason in [('cause', '', 'missing cause'), ('evidence', '', 'missing evidence'),
                                  ('mode', 'unknown', 'unknown mode'), ('metric', '', 'missing metric'),
                                  ('threshold', None, 'missing threshold')]:
            changed = copy.deepcopy(original); changed['entries'][0][key] = value
            tolerance.write_text(json.dumps(changed))
            self.refusal(reason)
        tolerance.write_text(json.dumps(original) + '\n')
        self.refusal('tolerances are not pre-committed')

    def test_execution_config_shapes(self):
        for value in ([], None, [{'role':'executor_descriptor', 'path':'x','sha256':'bad'}],
                      [{'role':'unknown','path':'x','sha256':'a'*64}],
                      [{'role':'executor_descriptor','path':'/absolute','sha256':'a'*64}]):
            manifest = copy.deepcopy(self.manifest); manifest['execution_config'] = value
            self.assertFalse(mc.grade(manifest)['groups'][2]['present'])
        manifest = copy.deepcopy(self.manifest)
        manifest['predicate_facts']['wrapper_kind'] = 'nextflow'
        self.assertFalse(mc.grade(manifest)['groups'][2]['present'])

    def test_python36_grammar(self):
        for path in (INSTRUMENT, GARS / 'tests/fixtures/rerun-fixture/rerun_fixture.py',
                     GARS / '_system/wrapperlib.py', GARS / '_system/manifest_check.py'):
            ast.parse(path.read_text(), feature_version=(3, 6))


class RealWrapperReplayTests(unittest.TestCase):
    def test_scrna_samplesheet_replay_and_drift(self):
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
            case.configure_wrapper('scrna-qc-cluster', 'local', case.project)
        case.fake_wrapper_run(); case.submit()
        checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
        original = json.loads(case.manifest_path.read_text())
        original_stage = case.stage
        sheet = case.project / '01_samplesheets/scrnaseq_samplesheet.csv'
        self.assertIn('samplesheet', original['inputs'])
        self.assertEqual(original['inputs']['samplesheet'], str(sheet.resolve()))
        self.assertEqual(original['samplesheet_sha256'], wl.sha256(sheet))
        self.assertEqual(original['input_data_location']['samplesheet'], str(sheet.resolve()))
        self.assertEqual(original['samplesheet_sha256'], case.prepared['samplesheet_sha256'])
        out = case.repo / 'scrna-replay'
        submissions = []

        def synthetic_execution(config_root, script, descriptor=None):
            # Replace only the biological worker/scheduler: real prepare, submit's
            # key/record checks, local status, collect and comparison still run.
            stage = Path(script).parent
            project = stage.parents[2]
            case.stage = stage
            try:
                case.fake_wrapper_run()
            finally:
                case.stage = original_stage
            job = str(5000 + len(submissions))
            submissions.append(job)
            jobs = ex._local_jobs_dir(project); jobs.mkdir(exist_ok=True)
            exit_file = stage / 'fixture.exit'; exit_file.write_text('0\n')
            (jobs / (job + '.json')).write_text(json.dumps(dict(
                script=str(script), exit_file=str(exit_file), started_at=time.time()-1)))
            return job, None

        with patch.object(rc, 'REPO', case.repo), patch.dict(os.environ, case.env):
            rc.validate_manifest(original, original_stage)
            legacy = copy.deepcopy(original)
            del legacy['inputs']['samplesheet']
            with self.assertRaisesRegex(ValueError, 'manifest lacks required samplesheet input'):
                rc.validate_manifest(legacy, original_stage)
            saved = sheet.read_bytes()
            sheet.write_bytes(saved + b'changed\n')
            try:
                with self.assertRaisesRegex(ValueError, 'input hash changed: samplesheet'):
                    rc.reproduce(case.manifest_path, 2, out, case.ws / '_system/wrappers')
                self.assertFalse(out.exists())
                with self.assertRaisesRegex(ValueError, 'prepared key differs from input bytes'):
                    ex.prepared_key(case.project, case.stage)
            finally:
                sheet.write_bytes(saved)
            with patch.object(rc.ex, '_submit_once', side_effect=synthetic_execution):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    result = rc.reproduce(case.manifest_path, 2, out, case.ws / '_system/wrappers')
            self.assertEqual(result, 0, output.getvalue())
            self.assertEqual(len(submissions), 2)
            comparisons = json.loads((out / 'comparison.json').read_text())
            self.assertEqual(len(comparisons['runs']), 2)
            self.assertIn('reproduction: 2/2', output.getvalue())
            for number in (1, 2):
                project = out / ('run-%d' % number)
                replay_sheet = project / '01_samplesheets/scrnaseq_samplesheet.csv'
                self.assertTrue(replay_sheet.is_symlink())
                self.assertEqual(replay_sheet.resolve(), sheet.resolve())
                stage = project / '02_bioinformatics' / case.assay / case.info['substage']
                replay = json.loads((stage / 'reproducibility/manifest.json').read_text())
                self.assertEqual(replay['idempotency_key'], original['idempotency_key'])
                self.assertEqual(replay['samplesheet_sha256'], original['samplesheet_sha256'])
                self.assertTrue(mc.grade(replay)['ok'])
                self.assertTrue(all(row['match'] for row in comparisons['runs'][number-1]['artifacts']))
        print('SCRNA replay fixture: 2/2; real prepare/submit/status/collect, synthetic worker')

    def test_all_real_wrapper_repreparations_and_execution_evidence(self):
        # Real prepare, synthetic checkouts/import probes; no bio execution is claimed.
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
        base = case.project
        for backend in ('local', 'slurm'):
            for key in sorted(mc.load_schema()['wrappers']):
                with self.subTest(wrapper=key, backend=backend):
                    case.configure_wrapper(key, backend, base)
                    before = json.loads(case.manifest_path.read_text())
                    current_source = case.wrapper.read_bytes()
                    relative = case.wrapper.relative_to(case.repo).as_posix()
                    baseline_source = run(['git', 'show', '9def5b3:' + relative]).stdout
                    self.assertTrue(baseline_source)
                    try:
                        case.wrapper.write_bytes(baseline_source)
                        checked(case.wrapper_argv('prepare', rc.prepare_arguments(before)), cwd=case.ws, env=case.env)
                        baseline = json.loads(case.manifest_path.read_text())
                        # No new legacy-submit refusal is authorized by R10.
                        self.assertEqual(ex.prepared_key(case.project, case.stage), baseline['idempotency_key'])
                    finally:
                        case.wrapper.write_bytes(current_source)
                    checked(case.wrapper_argv('prepare', rc.prepare_arguments(before)), cwd=case.ws, env=case.env)
                    restored = json.loads(case.manifest_path.read_text())
                    self.assertEqual(before, restored)
                    if key == 'scrna-qc-cluster':
                        self.assertEqual(set(before['inputs']), {'config', 'h5ad', 'samplesheet'})
                        self.assertNotEqual(before['idempotency_key'], baseline['idempotency_key'])
                        dropped = copy.deepcopy(before)
                        del dropped['inputs']['samplesheet']
                        self.assertEqual(wl.input_key(case.stage, dropped), baseline['idempotency_key'])
                    else:
                        self.assertEqual(before['idempotency_key'], baseline['idempotency_key'])
                    self.assertEqual(ex.prepared_key(case.project, case.stage), before['idempotency_key'])
                    print('BASE KEY %s %s: %s' % (key, backend,
                          'samplesheet changes key' if key == 'scrna-qc-cluster' else 'unchanged from 9def5b3'))
                    command = wl.sha256(case.stage / 'reproducibility/commands.sh')
                    extras = rc.prepare_arguments(before)
                    checked(case.wrapper_argv('prepare', extras), cwd=case.ws, env=case.env)
                    after = json.loads(case.manifest_path.read_text())
                    for field in ('params', 'config_sha256', 'idempotency_key', 'execution_config', 'execution_config_resolved'):
                        self.assertEqual(before[field], after[field], field)
                    self.assertEqual(command, wl.sha256(case.stage / 'reproducibility/commands.sh'))
                    # R9 never enters either existing key formula.
                    self.assertEqual(before['idempotency_key'], wl.input_key(case.stage, before))
                    replay_project = case.repo / 'fresh-replays' / (key + '-' + backend)
                    with patch.object(rc, 'REPO', case.repo):
                        rc.bind_project(before, replay_project, case.info)
                    argv = case.wrapper_argv('prepare', extras)
                    argv[argv.index('--project') + 1] = replay_project
                    checked(argv, cwd=case.ws, env=case.env)
                    replay_stage = replay_project / '02_bioinformatics' / case.assay / case.info['substage']
                    replay_manifest = json.loads((replay_stage / 'reproducibility/manifest.json').read_text())
                    rc.validate_preparation(before, replay_manifest, case.stage, replay_stage)
                    case.fake_wrapper_run(); case.submit()
                    checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
                    completed = json.loads(case.manifest_path.read_text())
                    self.assertEqual(json.dumps(before['execution_config'], sort_keys=True),
                                     json.dumps(completed['execution_config'], sort_keys=True))
                    self.assertTrue(mc.grade(completed)['ok'])
                    if key == 'rnaseq_bulk' and backend == 'slurm':
                        groovy = case.project / '_config/nextflow.slurm.config'
                        groovy.write_text(groovy.read_text().replace("executor = 'slurm'", "executor = 'local'"))
                        with patch.object(rc, 'REPO', case.repo):
                            with self.assertRaisesRegex(ValueError, 'execution config drifted'):
                                rc.validate_manifest(completed, case.stage)
                    print('REPREPARE %s %s: params config_sha256 commands.sh idempotency_key equal; collect preserves execution_config' % (key, backend))


if __name__ == '__main__':
    unittest.main(verbosity=2)
