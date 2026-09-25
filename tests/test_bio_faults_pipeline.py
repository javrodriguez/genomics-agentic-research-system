"""Science construction, validity, stub launch and scoring; stdlib, no models."""
import contextlib
import ast
import inspect
import copy
import csv
import datetime
import importlib.util
import io
import json
import os
import shutil
import math
import statistics
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/bio-faults'))
import bio_common as bio
import bio_build_cases as builder
import bio_generate_base as generator
import bio_gates as gates
import bio_review_record as validator
import bio_run_reviews as launcher
import bio_score as scorer
support = bio.load_row9('testing')
BASE_HASHES = {'atac-a': '52a704ff3e389c8614756f7d80de46dbaa3b90406284d2f6bf2a257143eae9fb', 'rna-a': '42418064a7d2ede5a797cbb6792e48989c7e79266c83f0a2c1aeedf39d579f4e', 'rna-b': '890c7988af399fdf168bd916ed00f134e2fe901a65060ba8466426b9566eb9f7'}


def temporary(test):
    resource = tempfile.TemporaryDirectory(prefix='t-')
    test.addCleanup(resource.cleanup)
    return Path(resource.name).resolve()


def record(neutral='a' * 12, prompt_sha='b' * 64):
    value = support.record(neutral, prompt_sha)
    env = value['envelope']
    env['reviewer']['prompt_path'] = bio.PROMPT_PATH
    env['phases'] = [dict(name=name, session_id=env['reviewer']['session_id'],
                         started_at=env['started_at'], finished_at=env['finished_at'],
                         exit_code=0, ended_on_usage_limit=False, blindness={'calls': 0, 'hits': 0})
                     for name in ('A', 'B')]
    env['phases'][0]['notes_sha256'] = 'a' * 64
    env['phases'][1]['session_matches_phase_a'] = True
    env['narrative_withheld_until_phase_b'] = True
    return value


def manifest():
    return dict(prompt_path=bio.PROMPT_PATH, prompt_sha256='b' * 64)


class AdapterTests(unittest.TestCase):
    def test_projection_and_drift(self):
        value, context = record(), manifest()
        original = copy.deepcopy((value, context))
        projected, adapted = validator.project_prompt_path(value, context)
        self.assertEqual((value, context), original)
        projected['envelope']['reviewer']['prompt_path'] = bio.PROMPT_PATH
        adapted['prompt_path'] = bio.PROMPT_PATH
        self.assertEqual((projected, adapted), original)
        self.assertEqual(validator.invalid_reasons(value, context), [])
        for fault in ('uid', 'root', 'blindness', 'limit', 'exit', 'sha', 'interval'):
            science = record()
            env = science['envelope']
            if fault == 'uid': env['reviewer']['uid'] = env['producer']['uid']
            if fault == 'root': env['reviewer']['uid'] = 0
            if fault == 'blindness':
                env['blindness']['hits'] = 1
                env['phases'][0]['blindness']['hits'] = 1
            if fault == 'limit': env['ended_on_usage_limit'] = True
            if fault == 'exit': env['exit_code'] = 1
            if fault == 'sha': env['reviewer']['prompt_sha256'] = 'c' * 64
            if fault == 'interval':
                science['review']['findings'] = [support.finding(line_start=3, line_end=1, **{'class': 'other'})]
            code, code_manifest = validator.project_prompt_path(science, context)
            del code['envelope']['phases']
            del code['envelope']['narrative_withheld_until_phase_b']
            self.assertEqual(bool(validator.invalid_reasons(science, context)),
                             bool(bio.row9_invalid_reasons(code, code_manifest)), fault)

    def test_science_path_equality(self):
        context = manifest()
        context['prompt_path'] = bio.rf_common.PROMPT_PATH
        self.assertTrue(validator.invalid_reasons(record(), context))

    def test_code_path_invalid(self):
        value = record()
        value['envelope']['reviewer']['prompt_path'] = bio.rf_common.PROMPT_PATH
        self.assertTrue(validator.invalid_reasons(value, manifest()))

    def test_phase_rules(self):
        for phase in (0, 1):
            for key in ('exit_code', 'ended_on_usage_limit', 'blindness'):
                value = record()
                if key == 'blindness': value['envelope']['phases'][phase][key]['hits'] = 1
                else: value['envelope']['phases'][phase][key] = True if key == 'ended_on_usage_limit' else 1
                self.assertTrue(validator.invalid_reasons(value, manifest()))
        for bad in ([], [record()['envelope']['phases'][0]], [None, None]):
            value = record(); value['envelope']['phases'] = bad
            self.assertTrue(validator.invalid_reasons(value, manifest()))
        value = record(); value['envelope']['narrative_withheld_until_phase_b'] = False
        self.assertTrue(validator.invalid_reasons(value, manifest()))


class BuildTests(unittest.TestCase):
    def test_bases_and_bh(self):
        root = temporary(self)
        for name, (assay, seed) in generator.BASES.items():
            base = generator.generate(root / name, name)
            self.assertTrue(all(gates.run_gates(base, assay)[0].values()))
            with (base / 'de_results.csv').open() as handle:
                rows = list(csv.DictReader(handle))
            ps = [float(row['pvalue']) for row in rows]
            for i, row in enumerate(rows):
                ranked = sorted(ps)
                rank = ranked.index(ps[i]) + 1
                expected = min([1.0] + [p * len(ps) / (j + 1) for j, p in enumerate(ranked) if j + 1 >= rank])
                self.assertAlmostEqual(float(row['padj']), expected)

    def test_student_reference_and_analysis(self):
        # Independent df=4 closed form: integrates (1+t*t/4)**(-5/2).
        for t in (0, 0.1, 1, 2.776, 8.61, 30):
            y = t / math.sqrt(t*t + 4)
            expected = 1 - 1.5*y + 0.5*y**3
            self.assertAlmostEqual(generator.student_p(t), expected, places=12)
            self.assertEqual(generator.student_p(t), generator.student_p(-t))
        self.assertAlmostEqual(generator.student_p(2.776), .05, delta=.0001)
        self.assertAlmostEqual(generator.student_p(8.61), .001, delta=.00001)
        self.assertAlmostEqual(generator.regularized_beta(.3, 1, 1), .3)
        root = temporary(self)
        for name, (assay, seed) in generator.BASES.items():
            base = generator.generate(root / name, name)
            counts, effects = generator.simulate(seed)
            self.assertGreaterEqual(len(counts), 200)
            self.assertEqual(len(effects), len(counts) // 10)
            self.assertTrue(all(1 <= abs(v) <= 3 for v in effects.values()))
            self.assertTrue(any(v < 0 for v in effects.values()))
            self.assertTrue(any(v > 0 for v in effects.values()))
            self.assertEqual(counts, generator.simulate(seed)[0])
            sizes = [sum(row[j] for row in counts) for j in range(6)]
            self.assertEqual(len(set(sizes)), 6)
            ratios = [[] for unused in range(6)]
            for row in counts:
                if min(row) > 0:
                    product = 1
                    for x in row: product *= x
                    gm = product ** (1.0 / 6.0)
                    for j in range(6): ratios[j].append(row[j] / gm)
            factors = [statistics.median(values) for values in ratios]
            with (base / 'de_results.csv').open() as handle:
                results = list(csv.DictReader(handle))
            up = down = 0
            for row, output in zip(counts, results):
                normalized = [x / f for x, f in zip(row, factors)]
                logs = [math.log2(x + 1) for x in normalized]
                means = [sum(logs[:3]) / 3, sum(logs[3:]) / 3]
                ss = sum((x - means[j // 3])**2 for j, x in enumerate(logs))
                t = (means[1] - means[0]) / math.sqrt((ss / 4) * (2.0 / 3))
                self.assertAlmostEqual(float(output['baseMean']), sum(normalized) / 6)
                self.assertAlmostEqual(float(output['stat']), t)
                self.assertAlmostEqual(float(output['log2FoldChange']), means[1] - means[0])
                y = abs(t) / math.sqrt(t*t + 4)
                self.assertAlmostEqual(float(output['pvalue']), 1 - 1.5*y + .5*y**3)
                if float(output['padj']) < .05:
                    up += int(t > 0); down += int(t < 0)
            self.assertGreater(up, 0); self.assertGreater(down, 0)
            claim = bio.read_json(base / 'snapshot.json')['claims'][0]['text']
            self.assertIn('%d of 240' % (up + down), claim)
            self.assertIn('%d higher and %d lower' % (up, down), claim)
            qc = (base / 'qc.md').read_text()
            self.assertIn('n = 3 per group', qc)
            if assay == 'rnaseq_bulk':
                self.assertIn('strandedness', qc); self.assertNotIn('FRiP', qc)
            else:
                self.assertIn('FRiP', qc); self.assertNotIn('strandedness', (base / 'config.yaml').read_text() + qc)

    def test_count_inputs_consistent(self):
        root = temporary(self)
        builder.build(root / 'built')
        for project in (root / 'built/cases').glob('*/project'):
            self.assertFalse((project / '2-data/raw').exists())
            self.assertFalse(list(project.rglob('*.fastq')))
            with (project / '2-data/counts.tsv').open() as handle:
                matrix = list(csv.reader(handle, delimiter='\t'))
            with (project / '2-data/files.csv').open() as handle:
                files = list(csv.DictReader(handle))
            self.assertEqual([r['sample_id'] for r in files], matrix[0][1:])
            for j, entry in enumerate(files, 1):
                column = project / entry['count_file']
                self.assertEqual(entry['count_sha256'], bio.sha256(column.read_bytes()))
                with column.open() as handle:
                    rows = list(csv.reader(handle, delimiter='\t'))
                self.assertEqual(rows, [['gene', 'count']] + [[r[0], r[j]] for r in matrix[1:]])
                self.assertEqual(int(entry['read_count']), sum(int(r[j]) for r in matrix[1:]))
            plan = (project / '1-design/PLAN.md').read_text()
            self.assertIn('Analysis starts from the supplied count matrix', plan)
            self.assertIn('read_count is the sum over supplied features', plan)
            qc = (project / '3-results/qc.md').read_text()
            self.assertIn('are unavailable from counts', qc)
            self.assertNotIn('mapping rate 0.96', qc)
            report = (project / '4-report/report.md').read_text().replace(chr(92), '')
            self.assertIn('Upstream read-level QC unavailable; conclusions concern supplied counts only.', report)
            self.assertIn('DEGRADE', report)
        # Integrity still rejects a mismatching checksum, total, column or absent input.
        for mutation in ('checksum', 'total', 'column', 'missing'):
            base = generator.generate(root / mutation, 'rna-a')
            if mutation in ('checksum', 'total'):
                with (base / 'files.csv').open() as handle:
                    rows = list(csv.reader(handle))
                rows[1][3 if mutation == 'checksum' else 1] = '0'
                generator.table(base / 'files.csv', rows[0], rows[1:])
            else:
                library = base / 'libraries/A_REP1.tsv'
                if mutation == 'missing': library.unlink()
                else:
                    library.write_text(library.read_text().replace('g1', 'renamed', 1))
                    with (base / 'files.csv').open() as handle:
                        rows = list(csv.reader(handle))
                    rows[1][3] = bio.sha256(library.read_bytes())
                    generator.table(base / 'files.csv', rows[0], rows[1:])
            self.assertFalse(gates.run_gates(base, 'rnaseq_bulk')[0]['catalogue_integrity'], mutation)

    def test_base_fingerprints(self):
        hashes = BASE_HASHES
        root = temporary(self)
        for name, expected in sorted(hashes.items()):
            base = generator.generate(root / name, name)
            entries = sorted((p.relative_to(base).as_posix(), bio.sha256(p.read_bytes()))
                             for p in base.rglob('*') if p.is_file())
            payload = json.dumps(entries, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
            self.assertEqual(bio.sha256(payload), expected, name)
            for path in base.rglob('*'):
                if path.is_file(): self.assertNotIn(b'\r', path.read_bytes())
        # Built-in sum has different float semantics before/after Python 3.12.
        tree = ast.parse(inspect.getsource(generator.analyse))
        self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                             and n.func.id == 'sum' for n in ast.walk(tree)))

    def test_atac_peak_coordinates(self):
        root = temporary(self)
        base = generator.generate(root / 'base', 'atac-a')
        with (base / 'counts.tsv').open() as handle:
            rows = list(csv.reader(handle, delimiter='\t'))[1:]
        previous, widths, gaps = {}, set(), set()
        for row in rows:
            chrom, interval = row[0].split(':')
            start, end = [int(value) for value in interval.split('-')]
            self.assertGreaterEqual(end - start, 150)
            self.assertLessEqual(end - start, 900)
            widths.add(end - start)
            if chrom in previous:
                gap = start - previous[chrom]
                self.assertGreaterEqual(gap, 500)
                gaps.add(gap)
            previous[chrom] = end
        self.assertGreater(len(previous), 1)
        self.assertGreater(len(widths), 20)
        self.assertGreater(len(gaps), 20)

    def test_base_identity_not_visible(self):
        root = temporary(self)
        builder.build(root / 'built')
        for path in (root / 'built/cases').rglob('*'):
            if path.is_file():
                content = path.read_bytes()
                for name, (assay, seed) in generator.BASES.items():
                    self.assertNotIn(name.encode(), content)
                    self.assertNotIn(str(seed).encode(), content)
                for text in (b'"seed"', b'illustrative', b'not the source'):
                    self.assertNotIn(text, content)

    def test_build_from_outside_repository(self):
        root = temporary(self)
        commit = subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD']).decode().strip()
        # Launch from a scratch cwd without changing this test process's cwd.
        code = 'import sys; sys.path.insert(0, sys.argv[1]); import bio_build_cases as b; b.build(sys.argv[2])'
        out = root / 'built'
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(bio.HERE), str(out)],
                              cwd=str(root), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(bio.read_json(out / 'manifest.json')['harness_commit'], commit)

    def test_group_rep_collector_drift(self):
        root = temporary(self)
        for change in ('none', 'missing'):
            base = generator.generate(root / change, 'atac-a')
            if change == 'missing':
                p = base / 'counts.tsv'
                p.write_text(p.read_text().replace('A_REP1', 'removed'))
            adapter_root = root / ('adapter-' + change); adapter_root.mkdir()
            adapter = gates.group_rep_presence(base, adapter_root)
            actual = gates.wrapper_scaffold(base, root / ('real-' + change), 'atacseq_bulk', gates.atac)
            self.assertEqual(adapter, actual, change)
            self.assertEqual(actual, change == 'none')

    def test_each_gate_refuses(self):
        mutations = [
            ('stage01_design', 'samples.csv', 'A_REP1,A,A,1', 'A_REP2,A,A,1'),
            ('catalogue_integrity', 'libraries/A_REP1.tsv', 'gene', 'changed'),
            ('catalogue_probabilities', 'de_results.csv', 'padj', 'raw_p'),
            ('group_rep_presence', 'normalized_counts.csv', 'A_REP1', 'removed'),
            ('count_matrix_header', 'counts.tsv', 'A_REP1', 'removed'),
            ('de_identifiers', 'de_results.csv', 'gene,', 'anonymous,'),
            ('stage03_verify', 'PLAN.md', '## Goal', '## Altered goal'),
            ('catalogue_evidence', 'snapshot.json', '3-results/de_results.csv', '3-results/missing.csv'),
            ('render_report', 'snapshot.json', 'OBSERVATION', 'invalid-type')]
        root = temporary(self)
        for name, file, old, new in mutations:
            base = generator.generate(root / name, 'rna-a')
            path = base / file
            self.assertIn(old, path.read_text())
            path.write_text(path.read_text().replace(old, new))
            results, unused = gates.run_gates(base, 'rnaseq_bulk')
            self.assertFalse(results[name], name)
        base = generator.generate(root / 'imbalance', 'rna-a')
        path = base / 'samples.csv'
        lines = path.read_text().splitlines()
        lines[0] += ',age'
        for i in range(1, 7): lines[i] += ',' + str(20 + i if i <= 3 else 60 + i)
        path.write_text('\n'.join(lines) + '\n')
        results, unused = gates.run_gates(base, 'rnaseq_bulk')
        self.assertFalse(results['stage01_design'], 'covariate_imbalance')


    def test_stage03_verify_drift(self):
        root = temporary(self)
        for change in ('none', 'plan', 'missing', 'empty'):
            base = generator.generate(root / change, 'rna-a')
            if change == 'plan': (base / 'PLAN.md').write_text((base / 'PLAN.md').read_text() + '\nchanged\n')
            if change == 'missing': (base / 'de_results.csv').unlink()
            if change == 'empty': (base / 'de_results.csv').write_text('')
            project = root / ('p-' + change)
            adir = project / '03_custom_analysis/01_analysis'
            shutil.copytree(str(base), str(adir))
            (adir / 'run').mkdir(); (adir / 'run/.gars_run_complete').write_text('complete\n')
            expected = bio.read_json(base / 'approval.json')['plan_sha256']
            def holds(plan, unused, workspace):
                ok = bio.sha256(plan.read_bytes()) == expected
                return ok, None if ok else 'changed'
            # Deployment store/scheduler supplied as data; content function stays real.
            with patch.object(gates.stage03, 'approval_holds', side_effect=holds), \
                    patch.object(gates.wl.ex, 'analysis_execution_evidence', return_value=None):
                code, unused = gates.captured(gates.stage03.cmd_verify,
                    SimpleNamespace(project=project, analysis='01_analysis', model='none'), REPO / 'gars')
            self.assertEqual(gates.verify_data(base), code == 0, change)
        base = generator.generate(root / 'expired', 'rna-a')
        approval = base / 'approval.json'
        value = bio.read_json(approval); value['expiry'] = '2026-09-25T01:00:30Z'
        approval.write_text(json.dumps(value))
        self.assertFalse(gates.verify_data(base))

    def test_determinism_stats_neutral(self):
        root = temporary(self)
        outputs = [root / name for name in ('one', 'two')]
        for out in outputs:
            builder.build(out, salt='a' * 32)
        def tree(out):
            return [(p.relative_to(out).as_posix(), p.read_bytes() if p.is_file() else None,
                     stat.S_IMODE(p.stat().st_mode), p.stat().st_mtime_ns) for p in sorted(out.rglob('*'))]
        self.assertEqual(tree(outputs[0]), tree(outputs[1]))
        manifest = bio.read_json(outputs[0] / 'manifest.json')
        key = bio.read_json(outputs[0] / 'private/key.json')
        for neutral, entry in key['cases'].items():
            self.assertEqual(neutral, bio.sha256(('a' * 32 + entry['id']).encode())[:12])
            for path in (outputs[0] / 'cases' / neutral).rglob('*'):
                self.assertEqual(path.stat().st_mtime, builder.FIXED_TIME)
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o755 if path.is_dir() else 0o644)
        self.assertNotIn('run_salt', manifest)
        self.assertEqual(len(key['cases']), 4)

    def test_manifest_sweep_exact(self):
        value = {'harness_commit': 'a' * 40, 'prompt_path': bio.PROMPT_PATH}
        self.assertEqual(builder.sweep(json.dumps(value).encode(), [], True), [])
        self.assertTrue(builder.sweep(json.dumps(value).encode(), []))
        for key, item in [('harness_commit_extra', 'a'), ('other', bio.PROMPT_PATH),
                          ('prompt_path', bio.PROMPT_PATH + '.extra'), ('commit', 'fault'),
                          ('harness_commit', 'plant')]:
            changed = dict(value); changed[key] = item
            self.assertTrue(builder.sweep(json.dumps(changed).encode(), [], True), (key, item))
        for word in list(bio.CLASSES) + list(builder.WORDS) + ['P01']:
            self.assertTrue(builder.sweep(('prefix' + word + 'suffix').encode(), ['P01']))

    def test_refusals_and_quiet(self):
        root = temporary(self)
        out = root / 'exists'; out.mkdir()
        with self.assertRaises(ValueError): builder.build(out)
        worktree = root / 'worktree'; worktree.mkdir()
        subprocess.check_call(['git', 'init', '--quiet', str(worktree)])
        with self.assertRaises(ValueError): builder.build(worktree / 'prohibited-output')
        with patch.object(builder, 'sha256', return_value='a' * 64):
            with self.assertRaises(ValueError): builder.build(root / 'collision')
        original = generator.generate
        def bad_base(destination, name, seed):
            base = original(destination, name, seed)
            p = base / 'samples.csv'; p.write_text(p.read_text().replace('A_REP1,A,A,1', 'A_REP2,A,A,1'))
            return base
        log = root / 'log.json'
        output = io.StringIO()
        with patch.object(builder, 'generate', side_effect=bad_base), contextlib.redirect_stdout(output):
            with self.assertRaises(ValueError): builder.build(root / 'bad', log=log, quiet_ids=True)
        self.assertEqual(output.getvalue(), '')
        entries = bio.read_json(root / 'bad/private/key.json')['cases']
        self.assertTrue(all(not v['gates']['stage01_design'] for v in entries.values()))
        self.assertTrue(log.exists())
        self.assertFalse((root / 'bad/manifest.json').exists())
        def absent_output(destination, name, seed):
            base = original(destination, name, seed)
            (base / 'de_results.csv').unlink()
            return base
        with patch.object(builder, 'generate', side_effect=absent_output):
            with self.assertRaises(ValueError): builder.build(root / 'absent', quiet_ids=True)
        entries = bio.read_json(root / 'absent/private/key.json')['cases']
        self.assertTrue(all(not v['gates']['stage03_verify'] for v in entries.values()))

    def test_answer_file_refused(self):
        root = temporary(self)
        original = generator.generate
        def bad_base(destination, name, seed):
            base = original(destination, name, seed)
            (base / 'expected.json').write_text('{}')
            return base
        with patch.object(builder, 'generate', side_effect=bad_base):
            with self.assertRaises(ValueError): builder.build(root / 'bad')

    def test_bad_patch_and_sealed_id(self):
        root = temporary(self)
        source = root / 'sources'; shutil.copytree(str(bio.HERE / 'fixtures'), str(source))
        (source / 'P01/plant.diff').write_text('not a diff\n')
        with self.assertRaises(ValueError): builder.build(root / 'bad', [source])
        (source / 'P01').rename(str(source / 'P03'))
        expected = bio.read_json(source / 'P03/expected.json'); expected['id'] = 'P03'
        (source / 'P03/expected.json').write_text(json.dumps(expected))
        with patch.object(bio, 'HERE', root):
            source.rename(str(root / 'fixtures'))
            with self.assertRaises(ValueError): bio.load_cases([root / 'fixtures'])


class LaunchTests(unittest.TestCase):
    def setup_launch(self, mode='normal'):
        root = temporary(self)
        built = root / 'input'; m, unused = builder.build(built)
        settings = root / 'settings.json'; settings.write_text('{}\n')
        args = SimpleNamespace(cases=str(built / 'cases'), manifest=str(built / 'manifest.json'),
            prompt=str(REPO / bio.PROMPT_PATH), kits_root=str(root / 'k'), records=str(root / 'r'),
            model='stub-model', producer_account='synthetic-producer', login_entry=1, only=None, settings=str(settings))
        binary = root / 'bin'; binary.mkdir()
        source = '#!' + sys.executable + '\n' + '''import json, sys
from pathlib import Path
if '--version' in sys.argv:
    print('stub-1'); sys.exit(0)
b = '--resume' in sys.argv
assert Path('project/4-report').exists() == b
session = sys.argv[-1]
mode = MODE
if b and mode == 'different': session = 'different-session'
print(json.dumps(dict(type='system', subtype='init', model='stub-model', session_id=session)))
if (b and mode == 'hit-b') or (not b and mode == 'hit-a'):
    print(json.dumps(dict(type='tool_use', name='Read', input={'file_path': '../outside'})))
if b and mode == 'different':
    print(json.dumps(dict(type='tool_use', name='Read', input={'file_path': 'review.json'})))
if b and mode == 'limit': print("Claude usage limit reached.")
value = {'verdict': 'APPROVE', 'findings': []} if b else {'findings': []}
if b and mode == 'envelope': value['envelope'] = {'exit_code': 0, 'ended_on_usage_limit': False}
Path('review.json' if b else 'notes.json').write_text(json.dumps(value))
if not b and mode == 'made-report': Path('project/4-report').mkdir()
'''.replace('MODE', repr(mode))
        (binary / 'claude').write_text(source); (binary / 'claude').chmod(0o755)
        # The executable is a runtime stub. It neither invokes nor emulates a model.
        identities = record()['envelope']
        self.enter_patch = patch.object(launcher, 'launch_identity', return_value=(identities['reviewer'], identities['producer']))
        self.enter_patch.start(); self.addCleanup(self.enter_patch.stop)
        env = dict(os.environ); env.pop('ANTHROPIC_API_KEY', None); env['PATH'] = str(binary) + os.pathsep + env.get('PATH', '')
        context = patch.dict(os.environ, env, clear=True); context.start(); self.addCleanup(context.stop)
        return root, args, m

    def test_two_phase_only_no_overwrite(self):
        root, args, m = self.setup_launch()
        args.only = m['cases'][0]
        self.assertEqual(launcher.run(args), 0)
        records = list((root / 'r').glob('*.record.json'))
        self.assertEqual(len(records), 1)
        value = bio.read_json(records[0]); self.assertEqual(validator.invalid_reasons(value, m), [])
        env = value['envelope']; self.assertTrue(env['narrative_withheld_until_phase_b'])
        self.assertEqual(len(env['phases']), 2)
        self.assertEqual(env['phases'][0]['session_id'], env['phases'][1]['session_id'])
        self.assertEqual((root / 'k' / args.only / '.claude/settings.json').read_bytes(), Path(args.settings).read_bytes())
        with self.assertRaises(ValueError): launcher.run(args)

    def test_phase_b_session_audit(self):
        root, args, m = self.setup_launch('different'); args.only = m['cases'][0]
        with patch.object(launcher, 'blindness', wraps=bio.blindness) as audit:
            launcher.run(args)
        self.assertEqual(audit.call_args_list[1][0][2], 'different-session')
        value = bio.read_json(next((root / 'r').glob('*.record.json')))
        self.assertEqual(value['envelope']['phases'][1]['session_id'], 'different-session')
        self.assertFalse(value['envelope']['phases'][1]['session_matches_phase_a'])
        self.assertEqual(validator.invalid_reasons(value, m), [])

    def test_phase_a_created_report_recorded(self):
        root, args, m = self.setup_launch('made-report')
        self.assertEqual(launcher.run(args), 0)
        records = list((root / 'r').glob('*.record.json'))
        self.assertEqual(len(records), len(m['cases']))
        for path in records:
            value = bio.read_json(path)
            self.assertTrue(validator.invalid_reasons(value, m))
            self.assertIn('phase A created project/4-report', value['review']['invalid_notes'])
            self.assertEqual(value['envelope']['phases'][1]['exit_code'], 1)

    def test_each_phase_hit(self):
        for mode in ('hit-a', 'hit-b'):
            root, args, m = self.setup_launch(mode); args.only = m['cases'][0]
            launcher.run(args)
            value = bio.read_json(next((root / 'r').glob('*.record.json')))
            self.assertTrue(validator.invalid_reasons(value, m), mode)
            self.assertGreater(value['envelope']['phases'][0 if mode == 'hit-a' else 1]['blindness']['hits'], 0)

    def test_usage_limit(self):
        root, args, m = self.setup_launch('limit')
        output = io.StringIO()
        with contextlib.redirect_stdout(output): self.assertEqual(launcher.run(args), 0)
        self.assertEqual(len(list((root / 'r').glob('*.record.json'))), 1)
        self.assertIn('remaining: ' + ','.join(m['cases'][1:]), output.getvalue())

    def test_stub_cannot_supply_envelope(self):
        root, args, m = self.setup_launch('envelope'); args.only = m['cases'][0]
        launcher.run(args)
        value = bio.read_json(next((root / 'r').glob('*.record.json')))
        self.assertIn('phases', value['envelope'])
        self.assertTrue(validator.invalid_reasons(value, m))

    def test_producer_uid_and_root(self):
        uid = os.getuid() or 1
        with patch.object(bio.rf_run_reviews.os, 'getuid', return_value=uid), \
                patch.object(bio.rf_run_reviews.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=uid, pw_name='synthetic-producer')):
            with self.assertRaises(ValueError): bio.launch_identity('synthetic-producer')
        with patch.object(bio.rf_run_reviews.os, 'getuid', return_value=0):
            with self.assertRaises(ValueError): bio.launch_identity('synthetic-producer')

    def test_launcher_audit_identity(self):
        self.assertIs(launcher.blindness, bio.rf_run_reviews.blindness)
        self.assertIs(launcher.safe_review, bio.rf_run_reviews.safe_review)
        events = [{'type': 'tool_use', 'name': 'Read', 'input': {'file_path': '../outside'}}]
        root = temporary(self)
        self.assertEqual(launcher.blindness(events, root, 's'), bio.rf_run_reviews.blindness(events, root, 's'))


class ScoreTests(unittest.TestCase):
    def setup_score(self):
        root = temporary(self)
        m, key = builder.build(root / 'built')
        records = root / 'records'; records.mkdir()
        runs = root / 'runs'; runs.mkdir()
        answers = bio.load_cases([bio.HERE / 'fixtures'])
        for neutral, entry in key['cases'].items():
            value = record(neutral, m['prompt_sha256'])
            if entry['kind'] == 'plant':
                target = answers[entry['id']]['expected']['match_any'][0]
                value['review']['findings'] = [support.finding(file=target['file'], line_start=target['line_start'],
                    line_end=target['line_end'], **{'class': entry['class']})]
            bio.write_json(records / (neutral + '.record.json'), value)
        return root, records, m, key, runs

    def test_score_invalid_denominators_first_repeat(self):
        root, records, m, key, runs = self.setup_score()
        for neutral, entry in key['cases'].items():
            if entry['id'] in ('P01', 'C01'):
                path = records / (neutral + '.record.json'); v = bio.read_json(path)
                v['envelope']['exit_code'] = 1; path.write_text(json.dumps(v))
        result = scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs, '20000101T000000Z')
        self.assertEqual(result['overall']['caught'], {'n': 1, 'd': 2})
        self.assertEqual(result['overall']['invalid'], {'n': 2, 'd': 4})
        self.assertEqual(result['invalid_clean'], 1)
        self.assertEqual(result['per_class']['batch-confounded-contrast']['caught'], {'n': 0, 'd': 1})
        self.assertTrue(result['first_run_at_sha'])
        output = io.StringIO()
        with contextlib.redirect_stdout(output): scorer.print_score(result)
        self.assertIn('0/2 (1 invalid, not clean)', output.getvalue())
        self.assertIn('uncomputable', output.getvalue())
        self.assertIn('NOT met (partial set: 2 plants of 10 classes, 2 clean of 5)', output.getvalue())
        bio.write_json(runs / 'first.json', result)
        second = scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs, '20000102T000000Z')
        self.assertFalse(second['first_run_at_sha'])
        self.assertEqual(second['first_run_values'], result['overall'])
        second['repeat'] = scorer.compare(second, result)
        self.assertEqual(second['repeat']['caught'], dict(both=1, one=0, neither=1))
        with contextlib.redirect_stdout(output): scorer.print_score(second)
        self.assertIn('repeatability observation (not a metric)', output.getvalue())

    def test_resume_id_differs_count(self):
        root, records, m, key, runs = self.setup_score()
        path = next(records.glob('*.record.json'))
        value = bio.read_json(path)
        value['envelope']['phases'][1]['session_id'] = 'different-session'
        value['envelope']['phases'][1]['session_matches_phase_a'] = False
        self.assertEqual(validator.invalid_reasons(value, m), [])
        path.write_text(json.dumps(value))
        result = scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs)
        self.assertEqual(result['resume_id_differs'], {'n': 1, 'd': 4})
        self.assertEqual(result['overall']['invalid']['n'], 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output): scorer.print_score(result)
        self.assertIn('resume id differs: 1/4', output.getvalue())
        paths = sorted(records.glob('*.record.json'))
        other = next(p for p in paths if p != path)
        value = bio.read_json(other)
        # Mirror the launcher's code-stamped shape when B never ran.
        phase = value['envelope']['phases'][1]
        phase.update(session_id='not-started', exit_code=1, session_matches_phase_a=False)
        other.write_text(json.dumps(value))
        result = scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs)
        self.assertEqual(result['resume_id_differs'], {'n': 1, 'd': 3})
        self.assertEqual(result['overall']['invalid']['n'], 1)
        output = io.StringIO()
        with contextlib.redirect_stdout(output): scorer.print_score(result)
        self.assertIn('resume id differs: 1/3', output.getvalue())
        phase['session_id'] = 'missing-init'
        other.write_text(json.dumps(value))
        self.assertEqual(scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs)
                         ['resume_id_differs'], {'n': 1, 'd': 3})
        for p in paths:
            value = bio.read_json(p)
            value['envelope']['phases'][1]['session_id'] = 'not-started'
            p.write_text(json.dumps(value))
        result = scorer.score(records, key, m, [bio.HERE / 'fixtures'], runs)
        self.assertEqual(result['resume_id_differs'], {'n': 0, 'd': 0})
        output = io.StringIO()
        with contextlib.redirect_stdout(output): scorer.print_score(result)
        self.assertIn('resume id differs: 0/0 uncomputable', output.getvalue())

    def test_tampered_answer_and_key(self):
        root, records, m, key, runs = self.setup_score()
        sources = root / 'sources'; shutil.copytree(str(bio.HERE / 'fixtures'), str(sources))
        p = sources / 'P01/expected.json'; p.write_text(p.read_text() + '\n')
        with self.assertRaises(ValueError): scorer.score(records, key, m, [sources], runs)
        altered = copy.deepcopy(key); next(iter(altered['cases'].values()))['kind'] = 'wrong'
        with self.assertRaises(ValueError): scorer.score(records, altered, m, [bio.HERE / 'fixtures'], runs)

    def test_published_mask(self):
        root, records, m, key, runs = self.setup_score()
        neutral = next(iter(key['cases']))
        value = record(neutral, m['prompt_sha256'])
        value['review']['findings'] = [support.finding(summary='sentinel-text', evidence=str(root / neutral / 'report.md'), **{'class': 'other'})]
        masked = bio.masked_copy(value, key['run_salt'], list(key['cases']), ['sentinel-text'])
        text = json.dumps(masked)
        for literal in ('sentinel-text', 'os_user', str(root), str(value['envelope']['reviewer']['uid']), value['envelope']['host_digest']):
            self.assertNotIn(literal, text)
        self.assertIn('uid', masked['envelope']['reviewer'])
        self.assertIn('host_digest', masked['envelope'])
        self.assertIs(scorer.masked_copy, bio.rf_score.masked_copy)
        self.assertEqual(scorer.masked_copy(value, key['run_salt'], list(key['cases']), ['sentinel-text']), masked)


class PublicationTests(unittest.TestCase):
    def test_sealed_denominator_and_masked_score(self):
        root = temporary(self)
        sources = root / 'sources'
        shutil.copytree(str(bio.HERE / 'fixtures'), str(sources))
        for cid in ('P03', 'P04', 'P05'):
            shutil.copytree(str(sources / 'P01'), str(sources / cid))
            p = sources / cid / 'expected.json'
            value = bio.read_json(p); value['id'] = cid
            value['seal_type'] = 'independent_context' if cid != 'P05' else 'unsealed'
            p.write_text(json.dumps(value))
        p = sources / 'P01/expected.json'; value = bio.read_json(p)
        value['mask_literals'] = ['sentinel-text']; p.write_text(json.dumps(value))
        m, key = builder.build(root / 'built', [sources])
        records = root / 'records'; records.mkdir()
        for neutral, entry in key['cases'].items():
            value = record(neutral, m['prompt_sha256'])
            value['review']['findings'] = [support.finding(summary='sentinel-text', **{'class': 'other'})]
            bio.write_json(records / (neutral + '.record.json'), value)
        result = scorer.score(records, key, m, [sources], root / 'runs')
        self.assertNotIn('sentinel-text', json.dumps(result))
        self.assertEqual(result['sealed'], {'n': 2, 'd': 5, 'types': ['independent_context']})
        output = io.StringIO()
        with contextlib.redirect_stdout(output): scorer.print_score(result)
        self.assertIn('sealed 2/5 (independent_context)', output.getvalue())
        self.assertEqual(result['overall']['caught']['d'], 5)
        bad = copy.deepcopy(result); bad['model_id'] = 'different-model'
        with self.assertRaises(ValueError): scorer.compare(result, bad)
        bad = copy.deepcopy(result); bad['prompt_sha256'] = 'e' * 64
        with self.assertRaises(ValueError): scorer.compare(result, bad)

    def test_release_reader_code_pin_and_science(self):
        spec = importlib.util.spec_from_file_location('_bio_release', str(REPO / 'scripts/release_check.py'))
        release = importlib.util.module_from_spec(spec); spec.loader.exec_module(release)
        root = temporary(self)
        self.assertEqual(release.reviewer_measurement(root), ('unmeasured', None, False))
        code_dir = root / 'evals/review-faults/runs'; code_dir.mkdir(parents=True)
        code = {'created_at': '20000101T000000Z', 'overall': {'caught': {'n': 7, 'd': 10},
            'false_alarms': {'n': 1, 'd': 5}}, 'sealed_slots': {cls: ['independent_context']
            for cls in ('race', 'hardcoded-secret', 'weakened-criterion')}, 'first_run_at_sha': True}
        bio.write_json(code_dir / 'code.json', code)
        pinned = ('unmeasured (public: needs external_human_seal); development, code: 7/10 catch, '
                  '1/5 false alarms, seals independent_context, first-run-at-sha true '
                  '(evals/review-faults/runs/code.json); science: unmeasured')
        self.assertEqual(release.reviewer_measurement(root)[0], pinned)
        science_dir = root / 'evals/bio-faults/runs'; science_dir.mkdir(parents=True)
        science = {'created_at': '20000102T000000Z', 'overall': {'caught': {'n': 1, 'd': 5},
            'false_alarms': {'n': 1, 'd': 3}, 'invalid': {'n': 2, 'd': 8}},
            'sealed': {'n': 2, 'd': 5, 'types': ['independent_context']},
            'first_run_at_sha': False, 'first_run_values': {'caught': {'n': 0, 'd': 5}}}
        bio.write_json(science_dir / 'science.json', science)
        text, unused, met = release.reviewer_measurement(root)
        self.assertFalse(met)
        self.assertTrue(text.startswith(pinned.replace('science: unmeasured', '')))
        self.assertIn('science: development (sealed 2/5 independent_context, partial set 5 plants + 3 clean of 10 + 5)', text)
        self.assertIn('1/5 catch, 1/3 false alarms, invalid 2/8, first-run-at-sha false', text)
        self.assertIn('first-run values:', text)
        (code_dir / 'code.json').unlink()
        self.assertTrue(release.reviewer_measurement(root)[0].startswith('code: unmeasured; science: development'))


class AdditionalTests(unittest.TestCase):
    def test_added_case_bytes_swept(self):
        root = temporary(self)
        original = generator.generate
        for word in ('harness_commit', bio.PROMPT_PATH, 'P03'):
            def changed(destination, name, seed):
                base = original(destination, name, seed)
                p = base / 'qc.md'; p.write_text(p.read_text() + word)
                return base
            with patch.object(builder, 'generate', side_effect=changed):
                with self.assertRaises(ValueError): builder.build(root / ('out' + str(len(list(root.iterdir())))))

    def test_launcher_refusals(self):
        helper = LaunchTests()
        self.addCleanup(helper.doCleanups)
        root, args, m = helper.setup_launch()
        args.only = m['cases'][0]
        for field, bad in (('model', ''), ('settings', ''), ('only', 'outside')):
            changed = copy.copy(args); setattr(changed, field, bad)
            with self.assertRaises(ValueError): launcher.run(changed)
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'synthetic'}):
            with self.assertRaises(ValueError): launcher.run(args)
        m['prompt_sha256'] = 'a' * 64
        Path(args.manifest).write_text(json.dumps(m))
        with self.assertRaises(ValueError): launcher.run(args)

    def test_schema_projection_does_not_hide_hash(self):
        v = record(); m = manifest(); m['prompt_sha256'] = 'e' * 64
        self.assertIn('prompt mismatch', validator.invalid_reasons(v, m))



if __name__ == '__main__':
    unittest.main(verbosity=2)
