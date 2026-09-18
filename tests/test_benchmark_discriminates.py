"""Row 2: stdlib unittest, imported by run_tests.py (which does not discover files)."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'evals'))
import bench


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gars-bench-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def command(self, module):
        if not hasattr(self, 'suite_root'):
            return [sys.executable, str(REPO / 'evals' / (module + '.py'))]
        # Exercise the production CLI with a pinned, scratch-only five-task suite.
        bootstrap = ('import sys; from pathlib import Path; sys.path.insert(0, sys.argv.pop(1)); '
                     'import bench; bench.REPO=Path(sys.argv.pop(1)); import ' + module +
                     '; sys.exit(' + module + '.main())')
        return [sys.executable, '-c', bootstrap, str(REPO / 'evals'), str(self.suite_root)]

    def cli(self, *args):
        env = dict(os.environ)
        env.pop('GARS_BENCH_HOLDOUT_DIR', None)
        return subprocess.run(self.command('bench') + list(args),
                              cwd=str(REPO), env=env, stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True)

    def test_task_schema_and_input_hashes(self):
        tasks = bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False)
        self.assertEqual(len(tasks), 5)
        for task in tasks.values():
            self.assertIn(task['scorer'], ('exact', 'regex', 'pytest'))

    def bad_task(self, field, value):
        path = next((REPO / 'benchmarks/tasks').glob('*.yaml'))
        task = json.loads(path.read_text())
        if field == 'sha256':
            task['inputs'][0]['sha256'] = value
        else:
            task[field] = value
        folder = self.root / 'tasks'
        folder.mkdir()
        (folder / path.name).write_text(json.dumps(task))
        return self.cli('validate', '--tasks', str(folder))

    def test_wrong_sha_is_red(self):
        result = self.bad_task('sha256', '0' * 64)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('input sha256 mismatch', result.stdout)

    def test_model_scorer_is_red(self):
        result = self.bad_task('scorer', 'claude-opus')
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('scorer', result.stdout)

    def test_holdout_in_tuned_directory_is_red(self):
        result = self.bad_task('holdout', True)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('holdout', result.stdout)

    def test_generator_reproduces_fixtures(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('fixture_generator',
                                                     REPO / 'benchmarks/fixtures/generate.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.generate(self.root)
        for path in self.root.glob('*.csv'):
            self.assertEqual(path.read_bytes(), (REPO / 'benchmarks/fixtures' / path.name).read_bytes())

    def test_refusal_scorers_discriminate(self):
        tasks = bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False)
        for task_id, task in tasks.items():
            if task['scorer'] != 'exact':
                continue
            out = self.root / task_id
            out.mkdir()
            expected = task['expected_outputs']['response.json']['json_equals']
            (out / 'response.json').write_text(json.dumps(expected))
            self.assertTrue(bench.score_task(task, out)['passed'])
            wrong = dict(expected, execution_started=True)
            (out / 'response.json').write_text(json.dumps(wrong))
            self.assertFalse(bench.score_task(task, out)['passed'])
            wrong = dict(expected, flag='irrelevant')
            (out / 'response.json').write_text(json.dumps(wrong))
            self.assertFalse(bench.score_task(task, out)['passed'])

    def test_missing_outputs_fail_not_skip(self):
        for task in bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False).values():
            self.assertFalse(bench.score_task(task, self.root)['passed'])

    def test_json_boolean_numeric_substitutions_are_red(self):
        task = bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False)['batch-confounded']
        expected = task['expected_outputs']['response.json']['json_equals']
        for number in (0, 0.0, 1, 1.0):
            (self.root / 'response.json').write_text(json.dumps(dict(expected, execution_started=number)))
            self.assertFalse(bench.score_task(task, self.root)['passed'], repr(number))

    def test_nfcore_artifact_contracts_accept_and_reject_content(self):
        tasks = bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False)
        for task_id in ('bulk-rnaseq', 'bulk-atacseq'):
            task = tasks[task_id]
            output = self.root / task_id
            registry_name = next(k for k in task['expected_outputs'] if k.endswith('OUTPUTS.tsv'))
            contract = task['expected_outputs'][registry_name]['artifact_registry']
            registry = output / registry_name
            registry.parent.mkdir(parents=True)
            (registry.parent / 'STATUS').write_text('COMPLETE\n')
            sheet = output / contract['samplesheet']
            sheet.parent.mkdir(parents=True)
            roster = self.root / (task_id + '-expected.csv')
            roster.write_text('sample,replicate,fastq_1\ncontrol,1,control.fastq\ntreated,1,treated.fastq\n')
            sheet.write_bytes(roster.read_bytes())
            contract['expected_samplesheet'] = roster.name
            task['inputs'] = [{'path': roster.name, 'sha256': bench.file_sha(roster)}]
            for sample in ('control', 'treated'):
                raw = self.root / (sample + '.fastq')
                raw.write_text('synthetic interface input only')
                task['inputs'].append({'path': raw.name, 'sha256': bench.file_sha(raw)})
            tokens = ['control', 'treated'] if task_id == 'bulk-rnaseq' else ['control_REP1', 'treated_REP1']
            rows = []
            count_paths = []
            for typ, rule in contract['types'].items():
                path = registry.parent / 'artifacts' / typ
                path.parent.mkdir(parents=True, exist_ok=True)
                if rule == 'directory':
                    path.mkdir()
                    (path / 'synthetic-test-only').write_text('artifact contract test')
                elif rule == 'counts':
                    path.write_text('gene_id\t' + '\t'.join(tokens) + '\ngene_a\t1\t2\n')
                    count_paths.append(path)
                elif rule == 'bed':
                    path.write_text('chrSynthetic\t1\t10\n')
                else:
                    path.write_text('synthetic artifact test')
                rows.append(typ + '\tnative\tartifacts/' + typ)
            registry.write_text('# type\trole\tpath\n' + '\n'.join(rows) + '\n')
            self.assertTrue(bench.score_task(task, output, self.root)['passed'])
            original = count_paths[0].read_text()
            count_paths[0].write_text(original.replace(tokens[0], 'lost_sample'))
            self.assertFalse(bench.score_task(task, output, self.root)['passed'])
            count_paths[0].write_text(original.replace('1\t2', '-1\t2'))
            self.assertFalse(bench.score_task(task, output, self.root)['passed'])
            count_paths[0].write_text(original)
            originals = {path: path.read_bytes() for path in count_paths}
            for path in count_paths:
                path.write_text('gene_id\t' + tokens[0] + '\ngene_a\t1\n')
            # Coupled loss used to pass: remove the treated sample everywhere.
            sheet.write_text('sample,replicate\ncontrol,1\n')
            self.assertFalse(bench.score_task(task, output, self.root)['passed'])
            sheet.write_bytes(roster.read_bytes())
            for path, data in originals.items():
                path.write_bytes(data)
            self.assertTrue(bench.score_task(task, output, self.root)['passed'])
            with self.assertRaisesRegex(ValueError, 'unresolved required references'):
                bench.reference_readiness({task_id: task}, self.root)
            for path in count_paths:
                ref = self.root / (task_id + '-' + path.name + '.tsv')
                ref.write_bytes(path.read_bytes())
                task['inputs'].append({'path': ref.name, 'sha256': bench.file_sha(ref)})
                contract['reference_counts'][path.name] = ref.name
            bench.reference_readiness({task_id: task}, self.root)
            self.assertTrue(bench.score_task(task, output, self.root)['passed'])
            count_paths[0].write_text(original.replace('1\t2', '1\t3'))
            self.assertFalse(bench.score_task(task, output, self.root)['passed'])
            count_paths[0].write_text(original)
            registry.write_text('')
            self.assertFalse(bench.score_task(task, output, self.root)['passed'])

    def test_zero_denominator(self):
        self.assertEqual(bench.ratio_text(0, 0), '0/0 = uncomputable')


class BenchmarkRecordTests(unittest.TestCase):
    setUp = BenchmarkTests.setUp
    cli = BenchmarkTests.cli
    command = BenchmarkTests.command

    def record(self, run_id, passed=5, configuration='intact'):
        from unittest.mock import patch
        if not hasattr(self, 'suite_root'):
            self.suite_root = self.root / 'suite'
            tasks = self.suite_root / 'benchmarks/tasks'
            tasks.mkdir(parents=True)
            source = json.loads((REPO / 'benchmarks/tasks/batch-confounded.yaml').read_text())
            data = self.suite_root / 'synthetic-input.txt'
            data.write_text('synthetic arithmetic controls only')
            source['inputs'] = [{'path': data.name, 'sha256': bench.file_sha(data)}]
            source['expected_outputs'] = {'response.json': {'json_equals': {'passed': True}}}
            for i in range(5):
                (tasks / (str(i) + '.yaml')).write_text(json.dumps(source))
            self.outputs_root = self.root / 'archive'
            repo_patch = patch.object(bench, 'REPO', self.suite_root)
            repo_patch.start()
            self.addCleanup(repo_patch.stop)
            env_patch = patch.dict(os.environ, {'GARS_BENCH_OUTPUTS_DIR': str(self.outputs_root)})
            env_patch.start()
            self.addCleanup(env_patch.stop)
        outputs = self.outputs_root / run_id
        outputs.mkdir(parents=True, exist_ok=True)
        for i in range(5):
            folder = outputs / 'tuned_on' / str(i)
            folder.mkdir(parents=True, exist_ok=True)
            (folder / 'response.json').write_text(json.dumps({'passed': i < passed}))
        metadata = dict(run_id=run_id, git_sha='a' * 40, model='test-model',
                        prompt_sha256='b' * 64, configuration=configuration,
                        resource=dict(wall_time_seconds='unknown', tokens='unknown', cost_usd='unknown'))
        return bench.make_record(outputs, metadata)

    def save(self, record):
        path = self.root / (record['run_id'] + '.json')
        path.write_text(json.dumps(record))
        return str(path)

    def test_delta_cross_model_and_prompt_are_red(self):
        intact = [self.record('intact-' + str(i)) for i in range(1, 4)]
        paths = [self.save(r) for r in intact]
        for field, value in [('model', 'another-model'), ('prompt_sha256', 'd' * 64)]:
            after = self.record('degraded-1', 2, 'degraded')
            after[field] = value
            result = self.cli('delta', paths[0], self.save(after), '--intact', *paths)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('different ' + field, result.stdout)

    def test_two_run_noise_floor_is_red(self):
        paths = [self.save(self.record('intact-' + str(i))) for i in (1, 2)]
        result = subprocess.run(self.command('noise_floor') + paths,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                universal_newlines=True, cwd=str(REPO))
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('uncomputable', result.stdout)
        self.assertIn('found 2', result.stdout)
        paths.append(self.save(self.record('intact-3')))
        report = self.root / 'noise-floor.txt'
        result = subprocess.run(self.command('noise_floor') + paths +
                                ['--output', str(report)], stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, universal_newlines=True, cwd=str(REPO))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('tuned_on noise floor: 0/1 = 0.000000', report.read_text())
        self.assertIn('intact-3 [', report.read_text())

    def test_range_mean_and_strict_discrimination(self):
        from fractions import Fraction
        intact = [self.record('intact-' + str(i), score)
                  for i, score in enumerate((5, 4, 5), 1)]
        floor, mean = bench.noise_floor(intact)
        self.assertEqual(floor, Fraction(1, 5))
        self.assertEqual(mean, Fraction(14, 15))
        self.assertTrue(bench.discriminates(intact, self.record('degraded-1', 3, 'degraded')))
        self.assertFalse(bench.discriminates(intact, self.record('degraded-1', 4, 'degraded')))
        self.assertEqual(bench.compare(intact[0], intact[1], intact)['interpretation'], 'no change')
        # Equality is not discrimination, including the zero-noise case.
        flat = [self.record('intact-' + str(i), 4) for i in (1, 2, 3)]
        self.assertFalse(bench.discriminates(flat, self.record('degraded-1', 4, 'degraded')))

    def test_duplicate_repeats_and_suite_drift_refused(self):
        one = self.record('one')
        with self.assertRaisesRegex(ValueError, 'distinct repeats'):
            bench.noise_floor([one, one, one])
        different = self.record('two')
        different['scores']['tuned_on']['suite_sha256'] = 'd' * 64
        with self.assertRaisesRegex(ValueError, 'recomputed'):
            bench.compare(one, different, [one] * 3)

    def test_record_score_tampering_refused(self):
        record = self.record('one')
        record['scores']['tuned_on']['numerator'] = 0
        with self.assertRaisesRegex(ValueError, 'score does not match tasks'):
            bench.validate_record(record)

    def test_coherent_forgery_and_missing_artifacts_are_red(self):
        from unittest.mock import patch
        outputs = self.root / 'archive/intact-1'
        outputs.mkdir(parents=True)
        metadata = dict(run_id='intact-1', git_sha='a' * 40, model='test-model',
                        prompt_sha256='b' * 64, configuration='intact',
                        resource=dict(wall_time_seconds='unknown', tokens='unknown', cost_usd='unknown'))
        with patch.dict(os.environ, {'GARS_BENCH_OUTPUTS_DIR': str(outputs.parent)}):
            record = bench.make_record(outputs, metadata)
            forged = copy.deepcopy(record)
            score = forged['scores']['tuned_on']
            for verdict in score['tasks'].values():
                verdict.update(passed=True, reason='all artifact assertions passed')
            score['numerator'] = score['denominator']
            with self.assertRaisesRegex(ValueError, 'recomputed'):
                bench.validate_record(forged)
            bench.validate_record(record)
            outputs.rmdir()
            with self.assertRaisesRegex(ValueError, 'outputs directory is missing'):
                bench.validate_record(record)

    def test_strict_row_exit_rejects_missing_cohort(self):
        with self.assertRaisesRegex(ValueError, 'missing owner run record'):
            bench.row_exit([])
        result = self.cli('row-exit', '--runs', str(self.root / 'absent'))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn('missing owner run record', result.stdout)

    def test_strict_row_exit_requires_holdout_and_discrimination(self):
        from unittest.mock import patch
        intact = [self.record('intact-' + str(i)) for i in (1, 2, 3)]
        degraded = self.record('degraded-1', 0, 'degraded')
        with self.assertRaisesRegex(ValueError, 'held_out: unmeasured'):
            bench.row_exit(intact + [degraded])
        sealed = self.root / 'sealed'
        (sealed / 'tasks').mkdir(parents=True)
        source = copy.deepcopy(bench.load_tasks(self.suite_root / 'benchmarks/tasks', self.suite_root, False)['0'])
        source['holdout'] = True
        data = sealed / 'input.txt'
        data.write_text('synthetic seal interface only; no agent evidence')
        source['inputs'] = [{'path': data.name, 'sha256': bench.file_sha(data)}]
        (sealed / 'tasks/control.yaml').write_text(json.dumps(source))
        seal = dict(seal_type='independent_context', producer_access_denied=True,
                    suite_sha256=bench.digest({'control': source}))
        (sealed / 'seal.json').write_text(json.dumps(seal))
        with patch.dict(os.environ, {'GARS_BENCH_HOLDOUT_DIR': str(sealed)}):
            records = []
            for old in intact + [degraded]:
                output = self.outputs_root / old['run_id']
                folder = output / 'held_out/control'
                folder.mkdir(parents=True)
                (folder / 'response.json').write_text(json.dumps({'passed': old['configuration'] == 'intact'}))
                metadata = {k: old[k] for k in ('run_id', 'git_sha', 'model', 'prompt_sha256', 'configuration', 'resource')}
                records.append(bench.make_record(output, metadata))
            self.assertTrue(bench.row_exit(records))
            # A measured held-out partition must discriminate, too.
            output = self.outputs_root / 'degraded-1'
            (output / 'held_out/control/response.json').write_text(json.dumps({'passed': True}))
            records[-1] = bench.make_record(output, metadata)
            with self.assertRaisesRegex(ValueError, 'held_out: degraded must score below'):
                bench.row_exit(records)

    def test_strict_reference_readiness_rejects_placeholders(self):
        tasks = bench.load_tasks(REPO / 'benchmarks/tasks', REPO, False)
        with self.assertRaisesRegex(ValueError, 'unresolved required references'):
            bench.reference_readiness(tasks, REPO)

    def test_changed_artifact_hash_is_red(self):
        record = self.record('one')
        artifact = self.outputs_root / 'one/tuned_on/0/response.json'
        artifact.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'manifest/hash mismatch'):
            bench.validate_record(record)

    def test_cli_records_missing_outputs_and_resources(self):
        metadata = {k: v for k, v in self.record('owner-run').items()
                    if k in ('run_id', 'git_sha', 'model', 'prompt_sha256', 'configuration', 'resource')}
        outputs = self.outputs_root / 'empty-run'
        outputs.mkdir()
        metadata['run_id'] = 'empty-run'
        meta = self.root / 'metadata.json'
        meta.write_text(json.dumps(metadata))
        runs = self.root / 'runs'
        result = self.cli('score', '--outputs', str(outputs), '--metadata', str(meta), '--runs', str(runs))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn('tuned_on: 0/5', result.stdout)
        self.assertIn('held_out: unmeasured', result.stdout)
        paths = list(runs.glob('*.json'))
        self.assertEqual(len(paths), 1)
        record = bench.read_record(paths[0])
        self.assertEqual(record['resource'], metadata['resource'])
        self.assertEqual(paths[0].name, '%s-%s-%s.json' %
                         (record['run_sha256'], record['model'], record['prompt_sha256']))
        repeated = self.cli('score', '--outputs', str(outputs), '--metadata', str(meta), '--runs', str(runs))
        self.assertNotEqual(repeated.returncode, 0)
        self.assertIn('duplicate run_id', repeated.stdout)

    def test_external_holdout_is_separate_and_seal_is_checked(self):
        tasks = self.root / 'sealed/tasks'
        tasks.mkdir(parents=True)
        source = REPO / 'benchmarks/tasks/batch-confounded.yaml'
        task = json.loads(source.read_text())
        task['holdout'] = True
        # Synthetic interface test only. This is not a held-out measurement or seal.
        (self.root / 'sealed/input.txt').write_text('interface test')
        task['inputs'] = [{'path': 'input.txt', 'sha256': bench.file_sha(self.root / 'sealed/input.txt')}]
        (tasks / 'interface.yaml').write_text(json.dumps(task))
        loaded = bench.load_tasks(tasks, self.root / 'sealed', True)
        seal = {'seal_type': 'independent_context', 'producer_access_denied': True,
                'suite_sha256': bench.digest(loaded)}
        (tasks.parent / 'seal.json').write_text(json.dumps(seal))
        metadata = {k: v for k, v in self.record('interface').items()
                    if k in ('run_id', 'git_sha', 'model', 'prompt_sha256', 'configuration', 'resource')}
        outputs = self.outputs_root / 'interface'
        from unittest.mock import patch
        with patch.dict(os.environ, {'GARS_BENCH_HOLDOUT_DIR': str(tasks.parent)}):
            record = bench.make_record(outputs, metadata)
            self.assertEqual(record['scores']['tuned_on']['denominator'], 5)
            self.assertEqual(record['scores']['held_out']['denominator'], 1)
            self.assertEqual(record['scores']['held_out']['numerator'], 0)
            bench.validate_record(record)
            bad_record = copy.deepcopy(record)
            bad_record['scores']['held_out'].pop('seal')
            with self.assertRaisesRegex(ValueError, 'invalid held-out record seal'):
                bench.validate_record(bad_record)
            seal['suite_sha256'] = '0' * 64
            (tasks.parent / 'seal.json').write_text(json.dumps(seal))
            with self.assertRaisesRegex(ValueError, 'invalid seal'):
                bench.make_record(outputs, metadata)

    def test_benchmark_discriminates(self):
        # Read owner records only. Never manufacture agent evidence to pass this exit.
        paths = sorted((REPO / 'evals/runs').glob('*.json'))
        records = [bench.read_record(p) for p in paths]
        ids = [r['run_id'] for r in records]
        self.assertEqual(len(ids), len(set(ids)), 'duplicate owner run ids')
        required = ('intact-1', 'intact-2', 'intact-3', 'degraded-1')
        missing = [name for name in required if name not in ids]
        if missing:
            self.skipTest('missing owner run record(s): ' + ', '.join(missing))
        chosen = {r['run_id']: r for r in records}
        intact = [chosen[name] for name in required[:3]]
        degraded = chosen['degraded-1']
        # Repository development can skip absent runs. Once present, the same
        # strict gate as the CLI must pass, including held-out and reference evidence.
        self.assertTrue(bench.row_exit(records))


if __name__ == '__main__':
    unittest.main(verbosity=2)
