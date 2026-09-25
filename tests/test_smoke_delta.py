"""Row 14 smoke delta: schema, evaluator, arithmetic against bench, CLI and red-on-fault plants.

Stdlib unittest, no model and no network; collected by tests/run_tests.py.
"""
import copy
from fractions import Fraction
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

if os.environ.get('TMPDIR'):
    tempfile.tempdir = os.environ['TMPDIR']

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'tests'))
sys.path.insert(0, str(REPO / 'evals'))
import bench  # noqa: E402
import test_evaluator_planted_lie as oracle  # noqa: E402

SMOKE = oracle.SMOKE
FIXTURES = oracle.FIXTURES
TREE = SMOKE.dir_reader(FIXTURES / 'tree')
C01 = FIXTURES / 'clean/C01'
FLOOR = 'evals/runs/smoke/smoke-20260925-fixture-floor.json'
FIRST = 'evals/runs/smoke/smoke-20260926-fixture-one.json'
SECOND = 'evals/runs/smoke/smoke-20260927-fixture-two.json'


def expected(folder):
    return json.loads((folder / 'expected.json').read_text())


def scratch_copy(case, source, name='evidence'):
    temp = tempfile.TemporaryDirectory(prefix='gars-smoke-test-')
    case.addCleanup(temp.cleanup)
    target = Path(temp.name) / name
    shutil.copytree(str(source), str(target))
    return target


def check(evidence, record_bytes=None, path=SECOND, commit=None, parent=None,
          previous=FIRST, tree=TREE):
    exp = expected(C01)
    data = record_bytes if record_bytes is not None else (Path(evidence) / path).read_bytes()
    return SMOKE.evaluate(data, SMOKE.dir_reader(evidence), tree, commit or exp['bound_commit'],
                          parent or exp['bound_parent'], previous, record_path=path)


def codes(verdict):
    return sorted(set(finding['code'] for finding in verdict['findings']))


def edited(change, path=SECOND):
    record = json.loads((C01 / 'evidence' / path).read_text())
    change(record)
    return json.dumps(record).encode('utf-8')


class SchemaTests(unittest.TestCase):
    def test_valid_records_have_no_schema_problems(self):
        for path in (FLOOR, FIRST, SECOND):
            record = json.loads((C01 / 'evidence' / path).read_text())
            self.assertEqual(SMOKE.schema_problems(record), [], path)

    def test_invalid_records_are_schema_findings_only(self):
        def run_edit(change):
            return lambda r: change(r['runs'][0])
        variants = {
            'unknown field': lambda r: r.update(extra=1),
            'missing field': lambda r: r.pop('delta'),
            'run_id shape': lambda r: r.update(run_id='smoke-bad'),
            'no runs': lambda r: r.update(runs=[]),
            'two runs': lambda r: r.update(runs=r['runs'] * 2),
            'negative numerator': run_edit(lambda run: run.update(numerator=-1)),
            'boolean numerator': run_edit(lambda run: run.update(numerator=True)),
            'zero-denominator floor': lambda r: r['floor'].update(value='1/0'),
            'delta text': lambda r: r.update(delta='fifty'),
            'interpretation': lambda r: r.update(interpretation='better'),
            'output manifest': run_edit(lambda run: run['outputs'].pop('batch-confounded/response.json')),
            'resource rule': run_edit(lambda run: run['resource'].update(tokens=1.5)),
            'transcript hash': run_edit(lambda run: run['transcript_sha256'].update(
                {'batch-confounded': 'not-hex'})),
            'task order': lambda r: r['suite'].update(task_ids=list(reversed(SMOKE.TASK_IDS))),
            'run label': run_edit(lambda run: run.update(run_label='run-2')),
            'schema name': lambda r: r.update(schema='gars-smoke/2'),
        }
        raw = {'not JSON': b'{"schema": ', 'JSON array': b'[]',
               'duplicate key': b'{"schema": "gars-smoke/1", "schema": "gars-smoke/1"}',
               'not UTF-8': b'\xff\xfe'}
        cases = [(name, edited(change)) for name, change in variants.items()] + list(raw.items())
        for name, data in cases:
            with self.subTest(variant=name):
                verdict = check(C01 / 'evidence', data)
                self.assertFalse(verdict['ok'])
                self.assertEqual(codes(verdict), ['SCHEMA'])
                self.assertEqual(verdict['graded']['records_read'], 0)
        print('schema: %d invalid variants -> SCHEMA only; the valid chain has no schema problem'
              % len(cases))


class EvaluatorTests(unittest.TestCase):
    """One plant per finding code other than SCHEMA and UNREADABLE, each beside its clean twin."""

    def plant(self, code):
        folder = next(folder for folder in sorted((FIXTURES / 'lies').iterdir())
                      if expected(folder)['lie_class'] == code)
        outcome, lie_class, verdict = oracle.grade(folder, oracle.fixture_tree_reader,
                                                   (oracle.DEVELOPMENT_SEAL,))
        self.assertEqual((outcome, lie_class), ('caught', code), verdict)
        twin = oracle.grade(C01, oracle.fixture_tree_reader, (oracle.DEVELOPMENT_SEAL,))
        self.assertEqual(twin[0], 'passed', twin[2])
        print('plant %s: caught; clean twin passed' % code)

    def test_clean_controls_and_cold_start_twin(self):
        self.assertTrue(check(C01 / 'evidence')['ok'])
        cold = FIXTURES / 'clean/C02/evidence'
        exp = expected(FIXTURES / 'clean/C02')
        first = SMOKE.evaluate((cold / FLOOR).read_bytes(), SMOKE.dir_reader(cold), TREE,
                               exp['bound_commit'], exp['bound_parent'], None, record_path=FLOOR)
        self.assertTrue(first['ok'], first)
        self.assertEqual(first['graded'], {'records_read': 1, 'records_named': 1,
                                           'tasks_regraded': 9, 'outputs_hashed': 9})
        again = SMOKE.evaluate((cold / FLOOR).read_bytes(), SMOKE.dir_reader(cold), TREE,
                               exp['bound_commit'], exp['bound_parent'], SECOND, record_path=FLOOR)
        self.assertEqual(codes(again), ['PREVIOUS_MISMATCH'])
        # A second record beside it may not claim to be first.
        second = edited(lambda r: r.update(previous=None, delta=SMOKE.NO_PREVIOUS,
                                           interpretation='uncomputable'), FIRST)
        original = json.loads((C01 / 'evidence' / FIRST).read_text())
        verdict = check(C01 / 'evidence', second, FIRST, original['git_sha'],
                        original['parent_sha'], None)
        self.assertEqual(codes(verdict), ['FLOOR_MISMATCH'])
        print('cold start: first record with previous null passes; a second record may not claim it')

    def test_several_findings_at_once(self):
        data = edited(lambda r: (r.update(git_sha='1' * 40, delta='-1/3'),
                                 r['runs'][0].update(numerator=3)))
        verdict = check(C01 / 'evidence', data)
        self.assertEqual(codes(verdict), ['BINDING_MISMATCH', 'COUNT_MISMATCH', 'DELTA_MISMATCH'])
        self.assertGreaterEqual(len(verdict['findings']), 3)

    def test_graded_against_seen(self):
        self.assertEqual(check(C01 / 'evidence')['graded'],
                         {'records_read': 3, 'records_named': 3, 'tasks_regraded': 15,
                          'outputs_hashed': 15})
        evidence = scratch_copy(self, C01 / 'evidence')
        (evidence / FIRST).unlink()
        verdict = check(evidence)
        self.assertFalse(verdict['ok'])
        self.assertIn('UNREADABLE', codes(verdict))
        self.assertEqual((verdict['graded']['records_read'], verdict['graded']['records_named']), (2, 3))

    def test_unreadable_readers(self):
        evidence = C01 / 'evidence'
        plain = SMOKE.dir_reader(evidence)
        verdict = SMOKE.evaluate((evidence / SECOND).read_bytes(), lambda name: plain(name), TREE,
                                 expected(C01)['bound_commit'], expected(C01)['bound_parent'],
                                 FIRST, record_path=SECOND)
        self.assertEqual(codes(verdict), ['UNREADABLE'])

        def no_tree(name):
            raise OSError('no tree')
        verdict = check(evidence, tree=no_tree)
        self.assertIn('UNREADABLE', codes(verdict))
        self.assertEqual(verdict['graded']['tasks_regraded'], 0)

    def test_extra_and_missing_outputs(self):
        evidence = scratch_copy(self, C01 / 'evidence')
        folder = evidence / SMOKE.outputs_prefix('smoke-20260927-fixture-two', 'run-1')
        (folder / 'notes.txt').write_text('not a retained output\n')
        verdict = check(evidence)
        self.assertEqual(codes(verdict), ['OUTPUT_HASH_MISMATCH'])
        self.assertIn('extra file', verdict['findings'][0]['detail'])
        (folder / 'notes.txt').unlink()
        (folder / 'single-replicate/response.json').unlink()
        verdict = check(evidence)
        self.assertIn('OUTPUT_HASH_MISMATCH', codes(verdict))
        self.assertIn('retained output missing', ' '.join(f['detail'] for f in verdict['findings']))

    def test_score_task_is_the_scorer(self):
        sentinel = {'passed': True, 'reason': 'sentinel scorer'}
        with mock.patch.object(SMOKE.bench, 'score_task', return_value=sentinel) as scorer:
            verdict = check(C01 / 'evidence')
        self.assertTrue(scorer.called)
        self.assertIn('REGRADE_MISMATCH', codes(verdict))
        self.assertTrue(check(C01 / 'evidence')['ok'])
        print('contract drift: patching bench.score_task changes the verdict')


for _code in oracle.LIE_CLASSES:
    setattr(EvaluatorTests, 'test_plant_' + _code,
            (lambda code: lambda self: self.plant(code))(_code))


def bench_record(run_id, numerator):
    """A bench-shaped record carrying one smoke value, for bench's own arithmetic."""
    tasks = {task: {'passed': index < numerator, 'reason': 'arithmetic control'}
             for index, task in enumerate(SMOKE.TASK_IDS)}
    return {'run_id': run_id, 'run_sha256': bench.digest([run_id]), 'git_sha': 'a' * 40,
            'model': 'fixture-model', 'prompt_sha256': 'b' * 64, 'configuration': 'intact',
            'scores': {'tuned_on': {'state': 'measured', 'numerator': numerator,
                                    'denominator': len(tasks), 'tasks': tasks,
                                    'suite_sha256': 'c' * 64}}}


class ArithmeticTests(unittest.TestCase):
    """Coupling: row 2's pending change touches compatible(), validate_record() and the record
    schema; its landing must re-run this test and, if red, amend bench_record above."""

    def test_floor_delta_and_interpretation_match_bench(self):
        checked = 0
        with mock.patch.object(bench, 'validate_record', side_effect=lambda record: record):
            for floor in itertools.product(range(4), repeat=3):
                intact = [bench_record('intact-%d' % index, value) for index, value in enumerate(floor)]
                values = [Fraction(value, 3) for value in floor]
                noise, unused_mean = bench.noise_floor(intact)
                self.assertEqual(SMOKE.floor_range(values), noise)
                for before, after in itertools.product(range(4), repeat=2):
                    result = bench.compare(bench_record('before', before), bench_record('after', after),
                                           intact)
                    delta = Fraction(after - before, 3)
                    self.assertEqual(result['delta'], delta)
                    self.assertEqual(SMOKE.interpret(delta, SMOKE.floor_range(values)),
                                     result['interpretation'])
                    self.assertTrue(SMOKE.SIGNED.match(SMOKE.fraction_text(delta)))
                    checked += 1
        print('arithmetic: %d floor/delta cases agree with bench.noise_floor and bench.compare' % checked)


class CohortTests(unittest.TestCase):
    def test_smoke_record_not_collected_by_cohort_glob(self):
        temp = tempfile.TemporaryDirectory(prefix='gars-smoke-cohort-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / 'repo'
        names = ['tests/test_benchmark_discriminates.py', 'evals/bench.py']
        for path in sorted((REPO / 'benchmarks/tasks').glob('*.yaml')):
            names.append(path.relative_to(REPO).as_posix())
            names.extend(item['path'] for item in json.loads(path.read_text())['inputs'])
        for name in sorted(set(names)):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(REPO / name), str(root / name))
        placed = root / SECOND
        placed.parent.mkdir(parents=True)
        shutil.copyfile(str(C01 / 'evidence' / SECOND), str(placed))
        with self.assertRaisesRegex(ValueError, 'unsupported record schema'):
            bench.read_record(placed)
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env.pop('GARS_BENCH_HOLDOUT_DIR', None)
        result = subprocess.run([sys.executable, 'tests/test_benchmark_discriminates.py',
                                 'BenchmarkRecordTests.test_benchmark_discriminates'], cwd=str(root),
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        self.assertIn(b'skipped', result.stderr)
        print('cohort: a smoke record under evals/runs/smoke/ is not collected; bench refuses it by schema')


class CliTests(unittest.TestCase):
    def smoke(self, *args):
        return subprocess.run([sys.executable, str(REPO / 'evals/smoke/smoke.py')] + list(args),
                              cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), timeout=300)

    def test_bundle_check_and_score(self):
        record = json.loads((C01 / 'evidence' / SECOND).read_text())
        result = self.smoke('bundle', '--tree', str(FIXTURES / 'tree'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(('prompt_sha256: ' + record['prompt_sha256']).encode(), result.stdout)
        self.assertIn(('suite_sha256: ' + record['suite']['suite_sha256']).encode(), result.stdout)

        root = scratch_copy(self, C01 / 'evidence', 'repo')
        exp = expected(C01)
        base = ['check', '--evidence', str(root), '--tree', str(FIXTURES / 'tree'),
                '--bound-commit', exp['bound_commit'], '--bound-parent', exp['bound_parent']]
        self.assertEqual(self.smoke(*base + ['--record', str(root / SECOND),
                                             '--expect-previous', FIRST]).returncode, 0)
        result = self.smoke(*base + ['--record', str(root / SECOND), '--expect-previous', FLOOR])
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'PREVIOUS_MISMATCH', result.stdout)
        self.assertIn(b'graded 3 of 3 records seen', result.stderr)
        missing = list(base)
        missing[missing.index('--evidence') + 1] = str(root / 'absent')
        self.assertEqual(self.smoke(*missing + ['--record', str(root / SECOND), '--first']).returncode, 2)

        outputs = root.parent / 'outputs'
        for task in SMOKE.TASK_IDS:
            folder = outputs / 'run-1' / task
            folder.mkdir(parents=True)
            answer = json.loads((FIXTURES / 'tree/benchmarks/tasks' / (task + '.yaml')).read_text())
            (folder / 'response.json').write_text(json.dumps(
                answer['expected_outputs']['response.json']['json_equals']))
        (root.parent / 'transcripts.json').write_text(json.dumps(
            {'run-1': {task: 'e' * 64 for task in SMOKE.TASK_IDS}}))
        (root.parent / 'resource.json').write_text(json.dumps(
            {'run-1': {'wall_time_seconds': 12, 'tokens': 'unknown', 'cost_usd': 'unknown'}}))

        def score(run_id, model, previous):
            return self.smoke('score', '--tree', str(FIXTURES / 'tree'), '--outputs', str(outputs),
                              '--run-id', run_id, '--git-sha', 'd' * 40, '--parent-sha',
                              exp['bound_commit'], '--model', model, '--transcripts',
                              str(root.parent / 'transcripts.json'), '--resource',
                              str(root.parent / 'resource.json'), '--previous', previous,
                              '--floor', FLOOR, '--out-root', str(root))
        result = score('smoke-20260928-cli', 'fixture-model', SECOND)
        self.assertEqual(result.returncode, 0, result.stderr)
        written = json.loads((root / 'evals/runs/smoke/smoke-20260928-cli.json').read_text())
        self.assertEqual((written['delta'], written['interpretation']), ('2/3', 'increase'))
        again = score('smoke-20260928-cli', 'fixture-model', SECOND)
        self.assertEqual(again.returncode, 2)
        self.assertIn(b'refusing to overwrite', again.stderr)
        refused = score('smoke-20260929-cli-model', 'another-model', 'evals/runs/smoke/smoke-20260928-cli.json')
        self.assertEqual(refused.returncode, 1)
        self.assertIn(b'MODEL_MISMATCH', refused.stdout)
        self.assertTrue((root / 'evals/runs/smoke/smoke-20260929-cli-model.json').is_file())
        print('cli: bundle re-derives the prompt; check exits 0/1/2; score refuses overwrite and '
              'refuses (deleting nothing) what the evaluator refuses')


SMOKE_PY = 'evals/smoke/smoke.py'
COHORT = 'tests/test_benchmark_discriminates.py'
FAULTS = [
    ('regrade skipped', SMOKE_PY, [('            if regrade:\n', '            if False:\n')],
     'EvaluatorTests.test_plant_REGRADE_MISMATCH'),
    ('counts trusted', SMOKE_PY,
     [("if run['numerator'] != recorded:", 'if False:'),
      ("if passes is not None and run['numerator'] != passes:", 'if False:')],
     'EvaluatorTests.test_plant_COUNT_MISMATCH'),
    ('output hashes trusted', SMOKE_PY, [('if sha256(data) != expected_hash:', 'if False:')],
     'EvaluatorTests.test_plant_OUTPUT_HASH_MISMATCH'),
    ('floor trusted', SMOKE_PY,
     [("if floor_value is not None and record['floor']['value'] != fraction_text(floor_value):",
       'if False:')], 'EvaluatorTests.test_plant_FLOOR_MISMATCH'),
    ('delta trusted', SMOKE_PY,
     [("if expected_delta is not None and record['delta'] != expected_delta:", 'if False:')],
     'EvaluatorTests.test_plant_DELTA_MISMATCH'),
    ('interpretation trusted', SMOKE_PY,
     [("if expected_interpretation is not None and record['interpretation'] != expected_interpretation:",
       'if False:')], 'EvaluatorTests.test_plant_INTERPRETATION_MISMATCH'),
    ('previous not checked', SMOKE_PY, [("if record['previous'] != expect_previous:", 'if False:')],
     'EvaluatorTests.test_plant_PREVIOUS_MISMATCH'),
    ('model/prompt/suite equality dropped', SMOKE_PY,
     [('if identity(floor)[field] != own[field]:', 'if False:'),
      ('changed = [field for field in COMPARED if identity(previous)[field] != own[field]]',
       'changed = []')], 'EvaluatorTests.test_plant_MODEL_MISMATCH'),
    ('git_sha binding dropped', SMOKE_PY, [("if record['git_sha'] != bound_commit:", 'if False:')],
     'EvaluatorTests.test_plant_BINDING_MISMATCH'),
    ('smoke glob made recursive in the cohort test', COHORT,
     [("paths = sorted((REPO / 'evals/runs').glob('*.json'))",
       "paths = sorted((REPO / 'evals/runs').rglob('*.json'))")],
     'CohortTests.test_smoke_record_not_collected_by_cohort_glob'),
]


class FaultTests(unittest.TestCase):
    """Every evaluator guard planted in a disposable copy with byte backups (row 12's pattern)."""

    def test_evaluator_guards_go_red(self):
        temp = tempfile.TemporaryDirectory(prefix='gars-smoke-faults-')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / 'source'
        names = ['tests/test_smoke_delta.py', 'tests/test_evaluator_planted_lie.py', COHORT,
                 'evals/bench.py', SMOKE_PY]
        names.extend(p.relative_to(REPO).as_posix() for p in (REPO / 'evals/smoke/fixtures').rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts)
        for path in sorted((REPO / 'benchmarks/tasks').glob('*.yaml')):
            names.append(path.relative_to(REPO).as_posix())
            names.extend(item['path'] for item in json.loads(path.read_text())['inputs'])
        for name in sorted(set(names)):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(str(REPO / name), str(root / name))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        for label, name, edits, test in FAULTS:
            with self.subTest(fault=label):
                target = root / name
                original = target.read_bytes()
                text = original.decode('utf-8')
                for old, new in edits:
                    self.assertEqual(text.count(old), 1, label + ': ' + old)
                    text = text.replace(old, new)
                argv = [sys.executable, 'tests/test_smoke_delta.py', test]
                try:
                    target.write_text(text)
                    red = subprocess.run(argv, cwd=str(root), env=env, stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE, timeout=300)
                finally:
                    target.write_bytes(original)
                self.assertNotEqual(red.returncode, 0, label)
                self.assertRegex(red.stderr, rb'FAILED \((failures|errors)=')
                green = subprocess.run(argv, cwd=str(root), env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, timeout=300)
                self.assertEqual(green.returncode, 0, green.stderr[-2000:])
                print('red-on-fault: %s -> %s red, then green after restore' % (label, test))


if __name__ == '__main__':
    unittest.main(verbosity=2)
