"""The exemplar driver (scripts/repro_exemplar_run.py) on a stub GARS: every helper it calls is a stand-in
that logs its argv and leaves just enough state behind, so the order, the arguments, the `none` model and
every stop are shown without a pipeline, a cloud or a model. Its first real run was the exemplar's, on the launch pad."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
DRIVER = REPO / 'scripts' / 'repro_exemplar_run.py'
SAMPLES = ('atac-a-r1', 'atac-a-r2', 'atac-b-r1', 'atac-b-r2')
SUB = 'projects/yeast-atac/02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper'

# One stand-in for every helper; it logs `<name> <argv>` and acts by name.
STUB = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
name, args = os.path.basename(sys.argv[0]), sys.argv[1:]
log = os.environ['STUB_LOG']
with open(log, 'a') as fh:
    fh.write(json.dumps([name] + args) + '\n')
fail = os.environ.get('STUB_FAIL', '')
if fail and fail == name + ':' + (args[0] if args else ''):
    print('stub failure'); sys.exit(1)
gars = Path(os.environ['STUB_GARS'])
project = gars / 'projects' / 'yeast-atac'
sub = project / '02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper'
if name == 'stage00_register.py' and args[0] == 'create':
    (project / '_config').mkdir(parents=True)
    (project / '_config' / 'atacseq_bulk.yaml').write_text(
        'unit_of_replication: <REQUIRED: declare at stage 01>\nreference_release: <REQUIRED: declare at stage 01>\n'
        'compute:\n  mem: 64G\n  derived_dir: %s\n' % os.environ['STUB_DERIVED'])
if name == 'stage00_register.py' and args[0] == 'link':
    (project / '00_data/atacseq_bulk/raw').mkdir(parents=True)
# GARS seeds samples.csv at finalize, never at link (stage00_register.py:694-704 at 0f602ea0; the exemplar run, 6 Oct)
if name == 'stage00_register.py' and args[0] == 'finalize':
    (project / '00_data/atacseq_bulk/samples.csv').write_text(
        'sample_id,condition,group,replicate\n' + ''.join(s + ',,,\n' for s in os.environ['STUB_SAMPLES'].split()))
if name == 'configure.py':
    print('reference R64-1-1 narrow' + (' (dry run)' if '--dry-run' in args else ''))
if name == 'nfcore_atacseq_wrapper.py' and args[0] == 'prepare':
    sub.mkdir(parents=True, exist_ok=True)
    (sub / 'params.yaml').write_text('# generated\n' + os.environ.get('STUB_PARAMS', 'save_reference: true\n'))
    (sub / 'submit.sh').write_text('#!/bin/bash\n')
if name == 'executorlib.py' and args[0] == 'submit':
    # executorlib prints its object indented over several lines (the exemplar run, 6 Oct: job 4657)
    print(json.dumps({'command': 'submit', 'job_id': '4242', 'ok': True}, indent=2))
if name == 'executorlib.py' and args[0] == 'status':
    states = os.environ['STUB_STATES'].split()
    counter = Path(os.environ['STUB_LOG'] + '.status')
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    print(json.dumps({'command': 'status', 'job_id': args[-1], 'state': states[min(n, len(states) - 1)]}, indent=2))
if name == 'gen_executor_config.sh':
    (Path(args[0]) / '_config' / 'executor.yaml').write_text('name: local\n')
if name == 'package_run.py' and args[0] == 'harvest':
    out = Path(args[args.index('--out') + 1]); out.mkdir(parents=True)
    (out / 'HARVEST.json').write_text('{}')
if name == 'package_run.py' and args[0] == 'render':
    out = Path(args[args.index('--out') + 1]); out.mkdir(parents=True)
    (out / 'verify.py').write_text('import sys\nprint("package verified")\n')
'''


def git(repo, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME='f', GIT_AUTHOR_EMAIL='f@example.invalid', GIT_COMMITTER_NAME='f',
               GIT_COMMITTER_EMAIL='f@example.invalid')
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-C', str(repo)] + list(args), env=env,
                          check=True, stdout=subprocess.PIPE).stdout.decode().strip()


class Stub(object):
    def __init__(self, root, samples=SAMPLES):
        self.root = root
        self.clone = root / 'clone'
        gars = self.clone / 'gars'
        bodies = {'_system/stage00_register.py': STUB, '_system/stage01_samplesheet.py': STUB,
                  '_system/configure.py': STUB, '_system/executorlib.py': STUB,
                  '_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py': STUB}
        for rel, body in bodies.items():
            (gars / rel).parent.mkdir(parents=True, exist_ok=True)
            (gars / rel).write_text(body)
        (self.clone / '.gitignore').write_text('gars/projects/\ngars/data_sources.tsv\n')
        git(self.clone, 'init', '-q')
        git(self.clone, 'add', '-A')
        git(self.clone, 'commit', '-q', '-m', 'stub')
        self.commit = git(self.clone, 'rev-parse', 'HEAD')
        self.fixtures = root / 'fixtures'
        self.fixtures.mkdir()
        for s in samples:
            for e in ('1', '2'):
                (self.fixtures / ('%s_S1_L001_R%s_001.fastq.gz' % (s, e))).write_bytes(b'x')
        (gars / 'data_sources.tsv').write_text('source\tdata_class\tdeclared_by\n%s\tpublic\toperator\n' % self.fixtures)
        self.tools = root / 'tools'
        self.tools.mkdir()
        for name in ('gen_executor_config.sh', 'package_run.py'):
            (self.tools / name).write_text(STUB)
        (self.tools / 'gen_executor_config.sh').write_text('#!/bin/sh\nexec python3 "%s/gen.py" "$@"\n' % self.tools)
        (self.tools / 'gen.py').write_text(STUB.replace("os.path.basename(sys.argv[0])", "'gen_executor_config.sh'"))
        for name in ('lane-sources.tsv', 'package-tolerances.json'):
            (self.tools / name).write_text('x\n')
        self.derived = root / 'derived'
        self.derived.mkdir()
        self.log = root / 'calls.log'
        self.env = {'STUB_LOG': str(self.log), 'STUB_GARS': str(gars), 'STUB_DERIVED': str(self.derived),
                    'STUB_SAMPLES': ' '.join(SAMPLES), 'STUB_STATES': 'RUNNING COMPLETED'}

    def run(self, extra=(), **env):
        settings = dict(os.environ, **self.env)
        settings.update(env)
        argv = [sys.executable, str(DRIVER), '--gars', str(self.clone), '--expect-commit', self.commit,
                '--fixtures', str(self.fixtures), '--gen-executor', str(self.tools / 'gen_executor_config.sh'),
                '--package-run', str(self.tools / 'package_run.py'), '--lane-commit', 'a' * 40,
                '--gars-repo', str(self.clone), '--sources', str(self.tools / 'lane-sources.tsv'),
                '--tolerances', str(self.tools / 'package-tolerances.json'), '--private-out', str(self.root / 'out'),
                '--public-out', str(self.root / 'public'), '--harvest-copy', str(self.root / 'copy'),
                '--poll-seconds', '0'] + list(extra)
        return subprocess.run(argv, env=settings, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)

    def calls(self):
        return [json.loads(l) for l in self.log.read_text().splitlines()] if self.log.exists() else []

    def steps(self):
        return [(c[0], c[1] if len(c) > 1 else '') for c in self.calls()]


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='exemplar-driver-')
        self.stub = Stub(Path(self.temp.name).resolve())

    def tearDown(self):
        self.temp.cleanup()

    def test_the_whole_run_in_order_with_no_model(self):
        proc = self.stub.run()
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertEqual(self.stub.steps(), [
            ('stage00_register.py', 'create'), ('stage00_register.py', 'link'), ('stage00_register.py', 'finalize'),
            ('stage01_samplesheet.py', '--project'), ('stage01_samplesheet.py', '--project'),
            ('gen_executor_config.sh', str(self.stub.clone / 'gars/projects/yeast-atac')),
            ('configure.py', 'apply'), ('configure.py', 'apply'),
            ('nfcore_atacseq_wrapper.py', 'check'), ('nfcore_atacseq_wrapper.py', 'prepare'),
            ('executorlib.py', 'submit'), ('executorlib.py', 'status'), ('executorlib.py', 'status'),
            ('nfcore_atacseq_wrapper.py', 'collect'),
            ('package_run.py', 'harvest'), ('package_run.py', 'render')])
        calls = self.stub.calls()
        for call in calls:
            if '--model' in call:
                self.assertEqual(call[call.index('--model') + 1], 'none', call)
        self.assertIn('--copy-large', calls[-2])
        self.assertEqual(calls[2][calls[2].index('--data-class') + 1], 'public')
        self.assertIn('--dry-run', calls[6])
        config = (self.stub.clone / 'gars/projects/yeast-atac/_config/atacseq_bulk.yaml').read_text()
        self.assertIn('unit_of_replication: sample\n', config)
        self.assertIn('reference_release: R64-1-1\n', config)
        self.assertIn('  mem: 8G\n', config)
        design = (self.stub.clone / 'gars/projects/yeast-atac/00_data/atacseq_bulk/samples.csv').read_text()
        self.assertIn('atac-b-r2,b,atac-b,2\n', design)
        self.assertIn(b'package verified', proc.stdout)

    def test_preconditions_refuse_before_any_stage(self):
        cases = {
            'a wrong commit': (['--expect-commit', 'b' * 40], {}, None, 'not ' + 'b' * 12),
            'a dirty clone': ([], {}, lambda s: (s.clone / 'gars' / 'stray.txt').write_text('x'), 'not clean'),
            'no data_sources line': ([], {}, lambda s: (s.clone / 'gars/data_sources.tsv').write_text('source\n'),
                                     'does not declare'),
            'a missing fixture': ([], {}, lambda s: next(s.fixtures.iterdir()).unlink(), 'not the 8'),
            'a used out folder': ([], {}, lambda s: (s.root / 'out').mkdir() or (s.root / 'out' / 'x').write_text('x'),
                                  'is not empty'),
        }
        for name, (extra, env, damage, words) in sorted(cases.items()):
            with self.subTest(name):
                self.tearDown()
                self.setUp()
                if damage:
                    damage(self.stub)
                argv = list(extra)
                if argv[:1] == ['--expect-commit']:
                    proc = subprocess.run([sys.executable, str(DRIVER)] + self.full_args(argv),
                                          env=dict(os.environ, **self.stub.env), stdout=subprocess.PIPE,
                                          stderr=subprocess.STDOUT)
                else:
                    proc = self.stub.run()
                self.assertEqual(proc.returncode, 2, proc.stdout.decode())
                self.assertIn(words, proc.stdout.decode())
                self.assertEqual(self.stub.calls(), [])

    def full_args(self, override):
        s = self.stub
        args = {'--gars': str(s.clone), '--expect-commit': s.commit, '--fixtures': str(s.fixtures),
                '--gen-executor': str(s.tools / 'gen_executor_config.sh'), '--package-run': str(s.tools / 'package_run.py'),
                '--lane-commit': 'a' * 40, '--gars-repo': str(s.clone), '--sources': str(s.tools / 'lane-sources.tsv'),
                '--tolerances': str(s.tools / 'package-tolerances.json'), '--private-out': str(s.root / 'out'),
                '--public-out': str(s.root / 'public'), '--harvest-copy': str(s.root / 'copy')}
        args[override[0]] = override[1]
        return [x for pair in args.items() for x in pair] + ['--poll-seconds', '0']

    def test_a_failed_job_stops_before_collect(self):
        proc = self.stub.run(STUB_STATES='RUNNING FAILED:TIMEOUT')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('ended FAILED:TIMEOUT', proc.stdout.decode())
        self.assertNotIn(('nfcore_atacseq_wrapper.py', 'collect'), self.stub.steps())
        self.assertNotIn(('package_run.py', 'harvest'), self.stub.steps())

    def test_a_job_still_running_at_the_cap_is_the_operators_call(self):
        proc = self.stub.run(['--max-wait-minutes', '0'], STUB_STATES='RUNNING')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('the operator decides', proc.stdout.decode())
        self.assertNotIn(('nfcore_atacseq_wrapper.py', 'collect'), self.stub.steps())

    def test_a_populated_cache_or_an_index_parameter_stops_before_submit(self):
        (self.stub.derived / 'bwa').mkdir()
        proc = self.stub.run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn('is populated', proc.stdout.decode())
        self.assertNotIn(('nfcore_atacseq_wrapper.py', 'check'), self.stub.steps())
        self.tearDown()
        self.setUp()
        proc = self.stub.run(STUB_PARAMS='bwa_index: /x/bwa\n')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('does not record save_reference', proc.stdout.decode())
        self.assertNotIn(('executorlib.py', 'submit'), self.stub.steps())

    def test_any_failing_step_stops_the_run_where_it_failed(self):
        for failing in ('stage00_register.py:finalize', 'stage01_samplesheet.py:--project',
                        'nfcore_atacseq_wrapper.py:prepare', 'package_run.py:harvest'):
            with self.subTest(failing):
                self.tearDown()
                self.setUp()
                proc = self.stub.run(STUB_FAIL=failing)
                self.assertEqual(proc.returncode, 1, proc.stdout.decode())
                name, verb = failing.split(':')
                self.assertEqual(self.stub.steps()[-1], (name, verb))
                self.assertIn('STOP: step', (self.stub.root / 'out' / 'run.log').read_text())

    def test_the_harvest_is_copied_off_before_render_so_a_render_stop_keeps_it(self):
        proc = self.stub.run(STUB_FAIL='package_run.py:render')
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertTrue((self.stub.root / 'copy' / 'harvest' / 'HARVEST.json').is_file())
        self.assertTrue((self.stub.root / 'out' / 'harvest' / 'HARVEST.json').is_file())
        self.assertEqual(list((self.stub.root / 'public').iterdir()), [])   # nothing private in public

    def test_private_and_public_never_share_a_folder(self):
        proc = subprocess.run([sys.executable, str(DRIVER)] + self.full_args(['--public-out', str(self.stub.root / 'out')]),
                              env=dict(os.environ, **self.stub.env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(proc.returncode, 3)
        self.assertIn('three separate folders', proc.stdout.decode())
        proc = subprocess.run([sys.executable, str(DRIVER)] + self.full_args(['--public-out', str(self.stub.root / 'out/pub')]),
                              env=dict(os.environ, **self.stub.env), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.assertEqual(proc.returncode, 3)

    def test_the_driver_allows_exactly_the_ignored_paths_harvest_allows(self):
        import importlib.util, re as _re
        text = (REPO / 'gars/_system/claims/package_run.py').read_text()
        harvest_list = _re.search(r'^CLONE_IGNORED_OK = (\(.*?\))$', text, _re.M).group(1)
        driver_list = _re.search(r'^CLONE_IGNORED_OK = (\(.*?\))$', DRIVER.read_text(), _re.M).group(1)
        self.assertEqual(harvest_list, driver_list)

    def test_an_unexpected_ignored_file_in_the_clone_refuses_before_any_stage(self):
        (self.stub.clone / 'gars' / 'data_sources.tsv').write_text(
            (self.stub.clone / 'gars' / 'data_sources.tsv').read_text())
        (self.stub.clone / '.gitignore').write_text((self.stub.clone / '.gitignore').read_text() + 'notes.txt\n')
        git(self.stub.clone, 'commit', '-qam', 'ignore notes')
        self.stub.commit = git(self.stub.clone, 'rev-parse', 'HEAD')
        (self.stub.clone / 'notes.txt').write_text('x')
        proc = self.stub.run()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn('not clean', proc.stdout.decode())
        self.assertEqual(self.stub.calls(), [])

    def test_a_seeded_design_that_differs_stops(self):
        proc = self.stub.run(STUB_SAMPLES='atac-a-r1 atac-a-r2 atac-b-r1 other')
        self.assertEqual(proc.returncode, 1)
        self.assertIn('the seeded samples.csv', proc.stdout.decode())
        self.assertEqual(self.stub.steps()[-1], ('stage00_register.py', 'finalize'))


if __name__ == '__main__':
    unittest.main()
