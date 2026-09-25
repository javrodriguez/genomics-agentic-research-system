"""R-091 instrument self-test, never the owner's real Slurm re-run result."""
import ast
import contextlib
import copy
import stat
import io
import hashlib
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


def baseline_wrapper(path):
    root = GARS / 'tests/fixtures/replay-baseline'
    content = (root / path.name).read_bytes()
    expected = json.loads((root / 'sha256.json').read_text())[path.name]
    if hashlib.sha256(content).hexdigest() != expected:
        raise AssertionError('baseline wrapper fixture drifted: ' + path.name)
    return content


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
            shutil.copytree(str(GARS / folder), str(self.ws / folder), ignore=shutil.ignore_patterns('__pycache__'))
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
        copied_executor = self.ws / '_system/executorlib.py'
        copied_executor.write_text(copied_executor.read_text() +
            '\nHOMELAB_MARKER = str(Path(__file__).resolve().parents[1] / "fixture-marker")\n')
        marker = patch.object(ex, 'HOMELAB_MARKER', str(self.repo / 'fixture-marker'))
        marker.start(); self.addCleanup(marker.stop)
        commands = self.repo / 'bin'; commands.mkdir()
        scheduler = """import json, subprocess, sys
from pathlib import Path
base = Path(__file__).resolve().parent
if '--version' in sys.argv:
    print('fixture scheduler'); sys.exit(0)
if Path(__file__).name == 'sbatch':
    count = base / 'count'
    job = int(count.read_text()) + 1 if count.exists() else 100
    count.write_text(str(job))
    result = subprocess.run(['bash', sys.argv[-1]], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (base / str(job)).write_text(str(result.returncode))
    print('Submitted batch job ' + str(job))
else:
    fields = ' '.join(sys.argv)
    if 'Elapsed,MaxRSS,AllocCPUS' in fields:
        print('00:00:01|1024K|1|')
    elif '--format=Start' in fields:
        print('2026-09-25T00:00:00|')
    else:
        code = int((base / sys.argv[sys.argv.index('-j')+1]).read_text())
        print(('COMPLETED|0:0' if code == 0 else 'FAILED|%d:0' % code))
"""
        for name in ('sbatch', 'sacct'):
            command = commands / name
            command.write_text('#!' + sys.executable + '\n' + scheduler)
            command.chmod(0o755)
        environment = patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']})
        environment.start(); self.addCleanup(environment.stop)
        (self.repo / '.rerun-self-test').write_text('suite only\n')
        (self.repo / '.gitignore').write_text('__pycache__/\n*.pyc\n')
        (self.ws / '_system/gars-env.sh').write_text(':\n')
        checked(['git', 'init', '-q', self.repo])
        checked(['git', '-C', self.repo, 'add', 'gars', 'scripts', '.rerun-self-test', '.gitignore'])
        self.commit()
        self.project = self.ws / 'projects/original'
        (self.project / '_config').mkdir(parents=True)
        (self.project / '_config/executor.yaml').write_text('name: slurm\n')
        (self.project / '_config/rerun-fixture.yaml').write_text('compute:\n  cpus: 1\n')
        (self.project / '01_samplesheets').mkdir()
        (self.project / '01_samplesheets/rerun-fixture_samplesheet.csv').write_text('sample\nfixture\n')
        (self.project / '01_samplesheets/rerun-fixture_design_check.json').write_text('{"fixture":true}\n')
        raw = self.project / '00_data/rerun-fixture/raw'
        raw.mkdir(parents=True)
        source = self.repo / 'S1_S1_L001_R1_001.fastq'
        source.write_text('@fixture\nA\n+\nI\n')
        (raw / source.name).symlink_to(source)
        for name in ('CONTEXT.md', 'HISTORY.md'):
            (self.project / name).write_text('# fixture\n')
        checked([sys.executable, self.ws / '_system/stage00_register.py', 'finalize',
                 '--project', self.project, '--data-class', 'deidentified_under_agreement',
                 '--purpose', 'internal', '--agreement-ref', 'fixture-agreement-01',
                 '--expiry', '2099-01-01', '--model', 'none'])
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

    def test_missing_agreement_ref_refused(self):
        for missing in (True, False):
            manifest = copy.deepcopy(self.manifest)
            if missing:
                del manifest['agreement_ref']
            else:
                manifest['agreement_ref'] = None
            self.save(manifest)
            self.assertFalse(mc.grade(manifest)['groups'][10]['present'])
            self.refusal('no agreement_ref recorded')

    def test_no_direct_dataset_write(self):
        # Grep-style ownership tripwire: replay must only invoke finalize.
        self.assertNotIn('dataset.tsv', INSTRUMENT.read_text())

    def test_instrument_self_test(self):
        text = self.cli()
        self.assertEqual(json.loads((self.stage / 'run/seed.json').read_text())['seed'],
                         self.prepared['random_seeds'][0]['seed'])
        self.assertFalse(self.prepared['no-rng-in-code-path'])
        self.assertEqual(self.prepared['seed_source'], 'os.urandom(16)')
        self.assertIn('reproduction: 2/2', text)
        result = json.loads((self.out / 'comparison.json').read_text())
        self.assertEqual(len(result['runs']), 2)
        self.assertEqual(result['wrappers_root'], str(self.wrappers))
        self.assertEqual(result['wrapper_sha256'], wl.sha256(self.wrapper))
        for attempt in result['runs']:
            self.assertEqual(attempt['code']['wrapper_sha256'], wl.sha256(self.wrapper))
            self.assertEqual(attempt['code']['wrapperlib_sha256'], wl.sha256(self.ws / '_system/wrapperlib.py'))
        self.assertEqual(text.count('graded 2 of 2 outputs'), 2)
        for run_result in result['runs']:
            self.assertTrue(run_result['job'])
            replay_stage = self.out / ('run-%d' % run_result['run']) / '02_bioinformatics/rerun-fixture/01_rerun-fixture'
            replay_manifest = json.loads((replay_stage / 'reproducibility/manifest.json').read_text())
            dataset = replay_stage.parents[2] / '00_data/dataset.tsv'
            original_values = wl.dataset_record(self.project)
            replay_values = wl.dataset_record(replay_stage.parents[2])
            for field in ('data_class', 'purpose', 'agreement_ref'):
                self.assertEqual(replay_values[field].encode('utf-8'), original_values[field].encode('utf-8'))
                self.assertEqual(replay_manifest[field], original_values[field])
            self.assertEqual(stat.S_IMODE(dataset.stat().st_mode), 0o444)
            self.assertEqual(dataset.read_bytes(), (self.project / '00_data/dataset.tsv').read_bytes())
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
        print('EXIT instrument self-test (fixture, stub slurm): reproduction 2/2')

    def replay(self, expected=0):
        output = io.StringIO()
        with patch.object(rc, 'REPO', self.repo), patch.object(rc, 'TOLERANCES', self.ws / '_references/tolerances.yaml'):
            with contextlib.redirect_stdout(output):
                result = rc.reproduce(self.path, 2, self.out, self.wrappers)
        self.assertEqual(result, expected, output.getvalue())
        return output.getvalue()

    def test_byte_change_one_of_two(self):
        # Alter the output at the collect boundary; executed source stays committed.
        original = rc.run_wrapper
        def changed(wrapper, verb, project, manifest, env):
            if verb == 'collect' and project.name == 'run-2':
                stage = project / '02_bioinformatics/rerun-fixture/01_rerun-fixture'
                (stage / 'run/stable.txt').write_text('id\tvalue\nb\t2\na\t1\n')
            return original(wrapper, verb, project, manifest, env)
        with patch.object(rc, 'run_wrapper', side_effect=changed):
            text = self.replay(expected=1)
        self.assertIn('reproduction: 1/2', text)
        self.assertIn('run/stable.txt byte_stable match=no', text)

    def test_dirty_code_and_real_wrapper_override_refused(self):
        for path in (self.wrapper, self.ws / '_system/wrapperlib.py',
                     self.repo / 'scripts/rerun_check.py',
                     self.ws / '_references/manifest_schema.json',
                     self.ws / '_references/genomes.md'):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                # Keep JSON parseable so the refusal must come from code cleanliness.
                path.write_bytes(original + (b'\n' if path.suffix == '.json' else b'\n# uncommitted\n'))
                try:
                    self.refusal('GARS code has uncommitted changes')
                finally:
                    path.write_bytes(original)
        for relative in ('_system/untracked.py', '_references/untracked.md'):
            with self.subTest(untracked=relative):
                untracked = self.ws / relative
                untracked.write_text('# untracked\n')
                try:
                    self.refusal('GARS code has uncommitted changes')
                finally:
                    untracked.unlink()
        for name in mc.load_schema()['wrappers']:
            with self.subTest(wrapper=name):
                with self.assertRaisesRegex(ValueError, 'override is only allowed for rerun-fixture'):
                    rc.wrapper_info(dict(wrapper=name), self.wrappers)

    def test_failed_attempts_stay_in_denominator(self):
        original_status, original_wrapper = rc.ex.status, rc.run_wrapper
        for fault in ('FAILED:EXIT_1', 'collect', 'inventory', 'unavailable'):
            with self.subTest(fault=fault):
                self.out = self.repo / ('replay-' + fault.replace(':', '-'))
                def status(project, job):
                    state, why = original_status(project, job)
                    if project.name == 'run-2' and state in ('COMPLETED', 'VALIDATING', 'COMPLETE'):
                        if fault == 'FAILED:EXIT_1':
                            return fault, 'injected worker failure'
                        if fault == 'unavailable':
                            return None, 'injected accounting failure'
                    return state, why
                def wrapper(path, verb, project, manifest, env):
                    if verb == 'collect' and project.name == 'run-2' and fault == 'collect':
                        raise ValueError('wrapper collect failed: injected')
                    original_wrapper(path, verb, project, manifest, env)
                    if verb == 'collect' and project.name == 'run-2' and fault == 'inventory':
                        stage = project / '02_bioinformatics/rerun-fixture/01_rerun-fixture'
                        manifest_path = stage / 'reproducibility/manifest.json'
                        value = json.loads(manifest_path.read_text())
                        value['outputs'].reverse()
                        manifest_path.write_text(json.dumps(value))
                        index = stage / 'OUTPUTS.tsv'
                        lines = index.read_text().splitlines()
                        index.write_text('\n'.join([lines[0]] + list(reversed(lines[1:]))) + '\n')
                with patch.object(rc.ex, 'status', side_effect=status), patch.object(rc, 'run_wrapper', side_effect=wrapper):
                    text = self.replay(expected=1)
                self.assertIn('reproduction: 1/2', text)
                result = json.loads((self.out / 'comparison.json').read_text())
                self.assertEqual(result['requested'], 2)
                self.assertEqual(len(result['runs']), 2)
                self.assertEqual([r['match'] for r in result['runs']], [True, False])
                self.assertTrue(result['runs'][1]['job'])
                reason = {'FAILED:EXIT_1': 're-run failed: FAILED:EXIT_1',
                          'collect': 'wrapper collect failed', 'inventory': 'output inventory differs',
                          'unavailable': 'executor unavailable'}[fault]
                self.assertIn(reason, result['runs'][1]['reason'])

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
            self.refusal({3: 'no execution config recorded', 11: 'no agreement_ref recorded'}.get(
                group['number'], 'incomplete manifest'))
        self.save(base)
        source = Path(base['inputs']['samplesheet'])
        old = source.read_bytes(); source.write_bytes(old + b'changed\n')
        self.refusal('input hash changed'); source.write_bytes(old)
        design_check = self.project / self.manifest['design_check']['path']
        old = design_check.read_bytes()
        design_check.write_bytes(old + b'changed\n')
        self.refusal('design check changed or missing')
        design_check.write_bytes(old)
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
    def test_dirty_pipeline_refused(self):
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
            case.configure_wrapper('rnaseq_bulk', 'local', case.project)
        case.fake_wrapper_run(); case.submit()
        checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
        manifest = json.loads(case.manifest_path.read_text())
        pipeline = Path(manifest['checkout'])
        with patch.object(rc, 'REPO', case.repo), patch.dict(os.environ, case.env):
            rc.validate_manifest(manifest, case.stage)
            for filename in ('main.nf', 'untracked.nf'):
                path = pipeline / filename
                old = path.read_bytes() if path.exists() else None
                path.write_text('// dirty fixture\n')
                try:
                    with self.assertRaisesRegex(ValueError, 'pipeline code has uncommitted changes'):
                        rc.validate_manifest(manifest, case.stage)
                finally:
                    if old is None:
                        path.unlink()
                    else:
                        path.write_bytes(old)

    def test_rnaseq_design_prepare_identity(self):
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
            case.configure_wrapper('rnaseq-de', 'local', case.project)
        canonical = case.project / '01_samplesheets/rnaseq_bulk_design.csv'
        alternate = case.project / 'alternate-design.csv'
        alternate.write_bytes(canonical.read_bytes())
        alias = case.project / 'design-link.csv'
        alias.symlink_to(canonical)
        original_source = case.wrapper.read_bytes()
        baseline_source = baseline_wrapper(case.wrapper)
        self.assertTrue(baseline_source)

        def prepare(design):
            return run(case.wrapper_argv('prepare', ['--counts', case.fixture.counts_native,
                       '--design', design]), cwd=case.ws, env=case.env)

        def snapshot():
            return {str(path.relative_to(case.project)):
                    ('link', os.readlink(str(path))) if path.is_symlink() else
                    ('file', path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else
                    ('dir',) for path in case.project.rglob('*')}

        # Refusal cannot overwrite a prior preparation or create a new one.
        for populated in (True, False):
            if not populated:
                shutil.rmtree(str(case.stage))
            before = snapshot()
            result = prepare(alternate)
            self.assertEqual(result.returncode, 2, result.stdout.decode())
            answer = json.loads(result.stdout.decode())
            self.assertFalse(answer['ok'])
            self.assertEqual(answer['failures'], [dict(check='design_not_canonical',
                             detail='design is not the canonical project design')])
            self.assertEqual(snapshot(), before, 'refused prepare wrote project files')

        # Migration of an actual legacy, prepared-but-unsubmitted alternate design.
        try:
            case.wrapper.write_bytes(baseline_source)
            result = prepare(alternate)
            self.assertEqual(result.returncode, 0, result.stdout.decode())
            legacy = json.loads(case.manifest_path.read_text())
            self.assertEqual(legacy['inputs']['design'], str(alternate.resolve()))
        finally:
            case.wrapper.write_bytes(original_source)
        result = prepare(canonical)
        self.assertEqual(result.returncode, 0, result.stdout.decode())
        migrated = json.loads(case.manifest_path.read_text())
        self.assertEqual(migrated['inputs']['design'], str(canonical.resolve()))
        self.assertEqual(ex.prepared_key(case.project, case.stage), migrated['idempotency_key'])

        # Compare each spelling to the real parent implementation at identical paths.
        for design in (canonical, alias, Path(os.path.relpath(str(canonical), str(case.ws)))):
            with self.subTest(design=str(design)):
                try:
                    case.wrapper.write_bytes(baseline_source)
                    result = prepare(design)
                    self.assertEqual(result.returncode, 0, result.stdout.decode())
                    before = json.loads(case.manifest_path.read_text())
                    scripts = {name: (case.stage / name).read_bytes() for name in
                               ('submit.sh', 'scripts/run_de.py', 'reproducibility/commands.sh')}
                finally:
                    case.wrapper.write_bytes(original_source)
                result = prepare(design)
                self.assertEqual(result.returncode, 0, result.stdout.decode())
                after = json.loads(case.manifest_path.read_text())
                expected = copy.deepcopy(before)
                expected['params']['design'] = str(canonical.resolve())
                expected['idempotency_key'] = wl.input_key(case.stage, expected)
                self.assertEqual(after, expected)
                self.assertEqual(after['inputs']['design'], str(canonical.resolve()))
                self.assertEqual(ex.prepared_key(case.project, case.stage), after['idempotency_key'])
                self.assertEqual(after['idempotency_key'], migrated['idempotency_key'])
                if str(design) != str(canonical.resolve()):
                    self.assertNotEqual(after['idempotency_key'], before['idempotency_key'])
                for name, content in scripts.items():
                    self.assertEqual((case.stage / name).read_bytes(),
                                     content.replace(before['idempotency_key'].encode(),
                                                     after['idempotency_key'].encode()))

    def test_rnaseq_design_replay_and_legacy_refusal(self):
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
            case.configure_wrapper('rnaseq-de', 'local', case.project)
        original_stage = case.stage
        canonical = case.project / '01_samplesheets/rnaseq_bulk_design.csv'
        alternate = case.project / 'alternate-design.csv'
        alternate.write_bytes(canonical.read_bytes())
        # Produce a legacy COMPLETE manifest with the actual pre-R11 wrapper.
        source = case.wrapper.read_bytes()
        baseline = baseline_wrapper(case.wrapper)
        self.assertTrue(baseline)
        try:
            case.wrapper.write_bytes(baseline)
            checked(case.wrapper_argv('prepare', ['--counts', case.fixture.counts_native,
                    '--design', alternate]), cwd=case.ws, env=case.env)
        finally:
            case.wrapper.write_bytes(source)
        case.fake_wrapper_run(); case.submit()
        checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
        legacy = json.loads(case.manifest_path.read_text())
        self.assertTrue(mc.grade(legacy)['ok'])
        self.assertEqual(wl.read_status(case.stage), 'COMPLETE')
        self.assertEqual(legacy['inputs']['design'], str(alternate.resolve()))
        out = case.repo / 'rnaseq-replay'
        with patch.object(rc, 'REPO', case.repo), patch.dict(os.environ, case.env):
            with patch.object(rc.ex, 'submit') as submit:
                with self.assertRaisesRegex(ValueError, 'design is not the canonical project design'):
                    rc.reproduce(case.manifest_path, 2, out, case.ws / '_system/wrappers')
                submit.assert_not_called()
            self.assertFalse(out.exists())

        self.check_rnaseq_replay(relative=False)

    def test_relative_rnaseq_prepare_replays_two_of_two(self):
        self.check_rnaseq_replay(relative=True)

    def check_rnaseq_replay(self, relative):
        import test_manifest_groups as fixtures
        # A separate canonical original uses the new code; no terminal stage reset.
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
            case.configure_wrapper('rnaseq-de', 'local', case.project)
        out = case.repo / 'rnaseq-replay'
        original_stage = case.stage
        canonical = case.project / '01_samplesheets/rnaseq_bulk_design.csv'
        if relative:
            argv = case.wrapper_argv('prepare', ['--counts', case.fixture.counts_native,
                                               '--design', canonical])
            for flag in ('--project', '--counts', '--design'):
                index = argv.index(flag) + 1
                argv[index] = os.path.relpath(str(argv[index]), str(case.ws))
            checked(argv, cwd=case.ws, env=case.env)
        case.fake_wrapper_run(); case.submit()
        checked(case.wrapper_argv('collect', ['--model', 'none']), cwd=case.ws, env=case.env)
        original = json.loads(case.manifest_path.read_text())
        submissions = []

        def synthetic_execution(config_root, script, descriptor=None):
            stage = Path(script).parent
            project = stage.parents[2]
            case.stage = stage
            try:
                case.fake_wrapper_run()
            finally:
                case.stage = original_stage
            job = str(6000 + len(submissions))
            submissions.append(job)
            jobs = ex._local_jobs_dir(project); jobs.mkdir(exist_ok=True)
            exit_file = stage / 'fixture.exit'; exit_file.write_text('0\n')
            (jobs / (job + '.json')).write_text(json.dumps(dict(
                script=str(script), exit_file=str(exit_file), started_at=time.time()-1)))
            return job, None

        with patch.object(rc, 'REPO', case.repo), patch.dict(os.environ, case.env):
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
                design = project / '01_samplesheets/rnaseq_bulk_design.csv'
                self.assertTrue(design.is_symlink())
                self.assertEqual(design.resolve(), canonical.resolve())
                stage = project / '02_bioinformatics' / case.assay / case.info['substage']
                replay = json.loads((stage / 'reproducibility/manifest.json').read_text())
                self.assertEqual(replay['idempotency_key'], original['idempotency_key'])
                self.assertEqual(replay['design_sha256'], original['design_sha256'])
                self.assertTrue(mc.grade(replay)['ok'])
                rc.validate_manifest(replay, stage)
                self.assertTrue(all(row['match'] for row in comparisons['runs'][number-1]['artifacts']))
        print('RNASEQ %s replay fixture: reproduction: 2/2; two submissions; synthetic worker' %
              ('relative-path' if relative else 'design'))

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

    def test_all_wrapper_path_params_are_canonical(self):
        import test_manifest_groups as fixtures
        case = fixtures.ManifestGroupsTests('test_all_ten_wrappers_both_backends')
        self.addCleanup(case.doCleanups)
        with contextlib.redirect_stdout(io.StringIO()):
            case.setUp(); case.pipeline_fixtures()
        base = case.project
        wrappers = mc.load_schema()['wrappers']
        self.assertEqual(len(wrappers), 10)
        for key in sorted(wrappers):
            for backend in ('local', 'slurm'):
                with self.subTest(wrapper=key, backend=backend):
                    case.configure_wrapper(key, backend, base)
                    # Preserve config bytes/key inputs across both CLI spellings.
                    # Relative reference config exercises normalization at the writer.
                    config = case.project / '_config' / (case.assay + '.yaml')
                    refs = case.fixture.refs
                    for directory in ('bwa', 'simpleaf', 'index/star', 'index/salmon'):
                        index = refs / directory
                        index.mkdir(parents=True, exist_ok=True)
                        (index / 'genomeParameters.txt').write_text('fixture index')
                    (refs / 'genome.transcripts.fa').write_text('>fixture\nA\n')
                    (refs / 'blacklist.bed').write_text('chr1\t1\t2\n')
                    text = config.read_text().replace('reference:\n',
                        'reference:\n  derived_dir: %s\n  blacklist: %s\n' %
                        (refs, refs / 'blacklist.bed'))
                    config.write_text(text.replace(
                        str(refs), os.path.relpath(str(refs), str(case.ws))))
                    absolute = case.wrapper_argv('prepare', case.prepare_extra)
                    relative = list(absolute)
                    for flag in ('--project', '--counts', '--design', '--h5ad'):
                        if flag in relative:
                            index = relative.index(flag) + 1
                            relative[index] = os.path.relpath(str(relative[index]), str(case.ws))
                    checked(absolute, cwd=case.ws, env=case.env)
                    before = json.loads(case.manifest_path.read_text())
                    checked(relative, cwd=case.ws, env=case.env)
                    after = json.loads(case.manifest_path.read_text())
                    self.assertEqual(json.dumps(before['params']).encode(),
                                     json.dumps(after['params']).encode())
                    self.assertEqual(before['idempotency_key'], after['idempotency_key'])
                    self.assertEqual(ex.prepared_key(case.project, case.stage), after['idempotency_key'])
                    path_keys = {'input', 'outdir', 'counts', 'design', 'h5ad', 'fasta', 'gtf',
                                 'spikein_fasta', 'spikein_bowtie2', 'blacklist', 'bwa_index',
                                 'simpleaf_index', 'star_index', 'salmon_index', 'transcript_fasta'}
                    optional = {'atacseq_bulk': {'blacklist', 'bwa_index'},
                                'chipseq_bulk': {'blacklist', 'bwa_index'},
                                'cutandrun': {'blacklist'}, 'scrnaseq': {'simpleaf_index'},
                                'rnaseq_bulk': {'star_index', 'salmon_index', 'transcript_fasta'}}
                    self.assertTrue(optional.get(key, set()).issubset(after['params']))
                    paths = path_keys.intersection(after['params'])
                    self.assertTrue(paths)
                    for name in paths:
                        value = after['params'][name]
                        self.assertTrue(Path(value).is_absolute(), (name, value))
                        self.assertEqual(value, str(Path(value).resolve()))
                    print('PATH PARAMS %s %s: byte-identical params; same key' % (key, backend))

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
                    baseline_source = baseline_wrapper(case.wrapper)
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
