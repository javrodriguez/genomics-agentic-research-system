"""Row 13 step B (decision 0141, D6): bring_home carries only keep-listed lines off the cluster.

The ruling's test: a failing fixture wrapper whose error text is the real `rnaseq_de`
count-matrix message, carrying a planted sample-ID marker, is replayed by the real
`scripts/rerun_check.py` on test_rerun_check's stub scheduler. The marker is in the raw console
and in `comparison.json`, and absent from `bring_home`'s output.
"""
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, run  # noqa: E402
import test_rerun_check as trc  # noqa: E402
from tools import closed_output as co  # noqa: E402

BRING_HOME = REPO / 'scripts/bring_home.py'
MARKER = 'MARKER0141bringS4'
FIXTURES = REPO / 'tests/fixtures/pilot'
# Injected into the disposable copy of the rerun fixture wrapper, committed there before the
# original run: a replay's prepare runs the real rnaseq_de check on a design whose sample the
# count matrix lacks, prints the wrapper's own JSON and fails with its exit code.
FAILING = '''
    if args.verb == 'prepare' and project.name.startswith('run-'):
        import subprocess
        scratch = project / 'de-check'
        (scratch / 'p').mkdir(parents=True)
        (scratch / 'design.csv').write_text('sample_id,condition\\n%s,a\\n' % MARKER)
        (scratch / 'counts.tsv').write_text('gene\\tS1\\n')
        de = WORKSPACE / '_system/wrappers/rnaseq-de/rnaseq_de.py'
        check = subprocess.run([sys.executable, str(de), 'check', '--project', str(scratch / 'p'),
                                '--counts', str(scratch / 'counts.tsv'), '--design',
                                str(scratch / 'design.csv')], stdout=subprocess.PIPE)
        sys.stdout.write(check.stdout.decode())
        raise SystemExit(check.returncode or 1)
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bring_home(out, **inputs):
    argv = [sys.executable, BRING_HOME, '--out', out]
    for key, value in inputs.items():
        argv += ['--' + key.replace('_', '-'), value]
    return run(argv)


class BringHomeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp))

    def failing_rerun(self):
        case = trc.RerunCheckTests('test_instrument_self_test')
        original = case.commit

        def commit():
            source = case.wrapper.read_text()
            anchor = "    project = args.project\n"
            self.assertEqual(source.count(anchor), 1)
            case.wrapper.write_text(source.replace(anchor, anchor + FAILING).replace(
                "SUBSTAGE = '01_rerun-fixture'\n",
                "SUBSTAGE = '01_rerun-fixture'\nMARKER = %r\n" % MARKER))
            trc.checked(['git', '-C', case.repo, 'add', 'gars'])
            original()
        case.commit = commit
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    def test_failing_wrapper_detail_stays_on_the_cluster(self):
        print('red-on-fault: reason tail', flush=True)
        case = self.failing_rerun()
        console_text = case.cli(expected=1, runs=1)
        console = self.tmp / 'console.txt'
        console.write_text(console_text)
        comparison = case.out / 'comparison.json'
        record = json.loads(comparison.read_text())
        # The real count-matrix message, marker included, is in both raw files.
        detail = 'count matrix lacks column(s) for design sample(s): ' + MARKER
        self.assertIn(detail, console_text)
        self.assertIn(detail, record['runs'][0]['reason'])
        self.assertTrue(record['runs'][0]['reason'].startswith('wrapper prepare failed: '))
        out = self.tmp / 'bring_home.txt'
        result = bring_home(out, rerun_console=console, comparison=comparison)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text()
        self.assertNotIn(MARKER, text)
        self.assertNotIn('count matrix', text)
        self.assertNotIn(str(case.repo), text)
        self.assertIn('== rerun-console sha256=%s ==' % sha(console), text)
        self.assertIn('== comparison sha256=%s ==' % sha(comparison), text)
        self.assertIn('run 1 match=no reason=wrapper prepare failed\n', text)
        self.assertIn('run 1 job=none match=no reason=wrapper prepare failed\n', text)
        self.assertIn('reproduction: 0/1\n', text)
        last = text.splitlines()[-1]
        self.assertRegex(last, r'^bring-home: 2 sections; withheld lines: [0-9]+$')
        self.assertGreater(int(last.rsplit(' ', 1)[1]), 5)
        self.assertEqual(result.stdout.decode().strip(), last)
        print('EXIT bring home (fixture): detail withheld', flush=True)

    def test_passing_rerun_is_carried_by_kind(self):
        case = trc.RerunCheckTests('test_instrument_self_test')
        case.setUp()
        self.addCleanup(case.doCleanups)
        console = self.tmp / 'console.txt'
        console.write_text(case.cli(runs=2))
        comparison = case.out / 'comparison.json'
        out = self.tmp / 'bring_home.txt'
        self.assertEqual(bring_home(out, rerun_console=console,
                                    comparison=comparison).returncode, 0)
        text = out.read_text()
        self.assertIn('reproduction: 2/2', text)
        self.assertEqual(text.count('graded 2 of 2 outputs'), 2)
        self.assertIn('artifact other byte_stable match=yes sha256_equal=1', text)
        self.assertIn('artifact other numeric_tolerance match=yes max_absolute_error=', text)
        self.assertNotIn('run/stable.txt', text)
        self.assertNotIn(str(case.repo), text)
        self.assertRegex(text, r'run 1 job=[0-9]+ match=yes reason=none')

    def test_reason_prefixes_bound_to_rerun_check(self):
        import ast
        tree = ast.parse((REPO / 'scripts/rerun_check.py').read_text())

        def literal(node):
            if isinstance(node, ast.BinOp):
                return literal(node.left)
            if isinstance(node, getattr(ast, 'Constant', ())) and isinstance(
                    getattr(node, 'value', None), str):
                return node.value
            return node.s if hasattr(ast, 'Str') and isinstance(node, ast.Str) else None
        found = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args:
                name = getattr(node.func, 'id', getattr(node.func, 'attr', None))
                if name == 'require' and len(node.args) >= 2:
                    found.add(literal(node.args[1]))
                if name == 'ValueError':
                    found.add(literal(node.args[0]))
        found.discard(None)
        self.assertGreater(len(found), 40)
        for text in sorted(found):
            head = text.split(':', 1)[0].strip()
            with self.subTest(reason=text):
                self.assertTrue(any(v == head or v.startswith(head + ' ')
                                    for v in co.RERUN_REASONS), head)
        self.assertEqual(co.reason_prefix('wrapper prepare failed: ' + MARKER),
                         'wrapper prepare failed')
        self.assertIsNone(co.reason_prefix("[Errno 2] No such file: '/x/%s'" % MARKER))
        self.assertIsNone(co.reason_prefix(MARKER))

    def test_manifest_check_error_lines_withheld(self):
        print('red-on-fault: manifest ERROR line', flush=True)
        broken = self.tmp / ('%s_manifest.json' % MARKER)
        broken.write_text('{not json')
        schema = json.loads((GARS / '_references/manifest_schema.json').read_text())
        check = run([sys.executable, GARS / '_system/manifest_check.py', broken,
                     FIXTURES / 'comparison.template.json'])
        console = self.tmp / 'manifest_check.txt'
        console.write_bytes(check.stdout + ('%s x required applicable=yes present=yes\n'
                                            % MARKER).encode())
        self.assertIn(MARKER.encode(), console.read_bytes())
        self.assertIn(b'ERROR ', console.read_bytes())
        out = self.tmp / 'bring_home.txt'
        self.assertEqual(bring_home(out, manifest_check=console).returncode, 0)
        text = out.read_text()
        self.assertNotIn(MARKER, text)
        self.assertEqual(text.count('ERROR withheld'), 2)
        self.assertIn('manifests read: 2; manifests graded: 0', text)
        self.assertIn('== manifest-check sha256=%s ==' % sha(console), text)
        self.assertTrue(schema['groups'])

    def test_fixed_format_sections(self):
        rerun_diff = run([sys.executable, REPO / 'scripts/rerun_diff.py', '--comparison',
                          self.comparison_fixture()])
        self.assertEqual(rerun_diff.returncode, 0, rerun_diff.stderr)
        diff = self.tmp / 'diff.txt'
        diff.write_bytes(rerun_diff.stdout + ('gene %s\n' % MARKER).encode())
        turns = self.tmp / 'turns.txt'
        session = run([sys.executable, REPO / 'scripts/session_turns.py', '--transcript',
                       FIXTURES / 'session.jsonl', '--log', FIXTURES / 'pilot1_log.csv',
                       '--stage', '02_02_de'])
        self.assertEqual(session.returncode, 0, session.stderr)
        turns.write_bytes(session.stdout + ('note %s\n' % MARKER).encode())
        summary = self.tmp / 'summary.json'
        summary.write_text(json.dumps({
            'ok': True, 'command': 'summary', 'assay': 'rnaseq_bulk', 'status': 'COMPLETE',
            'failures': [], 'gate': [], 'genes_tested': 5, 'padj_lt_0.05': {'up': 2, 'down': 1},
            'padj_lt_0.1': 3, 'na_padj': 1, 'samples_in_design': 6, 'top_gene': MARKER}))
        bench = self.tmp / 'evidence.json'
        bench.write_text(json.dumps({
            'backend': 'slurm', 'venue': 'slurm', 'status': 'COMPLETED', 'workload_id': 'W1',
            'workload_sha256': 'a' * 64, 'samples': 24, 'wall_s': 100.0, 'cpu_s': 6300.0,
            'max_rss_mb': 10.5, 'queue_wait_s': 3.0, 'python_version': '3.6.8',
            'gars_commit': 'b' * 40, 'measured_at': '2026-09-25T00:00:00Z',
            'cost_usd_per_sample': 'unmetered', 'cost_basis': 'institutional_allocation',
            'hostname': MARKER}))
        log, check = self.tmp / 'pilot1_log.csv', self.tmp / 'check.txt'
        shutil.copyfile(str(FIXTURES / 'pilot1_log.csv'), str(log))
        check.write_text('rows: 12; human: 5; agent: 4; tool: 3; open spans: 0; nonce: ok\n')
        out = self.tmp / 'bring_home.txt'
        result = bring_home(out, rerun_diff=diff, session_turns=turns, summary=summary,
                            bench_evidence=bench, pilot_log=log, pilot_check=check)
        self.assertEqual(result.returncode, 0, result.stderr)
        text = out.read_text()
        self.assertNotIn(MARKER, text)
        for line in rerun_diff.stdout.decode().splitlines() + [session.stdout.decode().strip()]:
            self.assertIn(line + '\n', text)
        for line in ('summary genes_tested 5', 'summary padj_lt_0.05 up 2 down 1',
                     'summary gate none', 'quantity samples_in_design 6',
                     'quantity cpu_hours slurm 1.75', 'bench cost_usd_per_sample unmetered',
                     'rows: 12; human: 5; agent: 4; tool: 3; open spans: 0; nonce: ok'):
            self.assertIn(line + '\n', text)
        for line in log.read_text().splitlines():
            self.assertIn(line + '\n', text)
        self.assertTrue(text.endswith('bring-home: 6 sections; withheld lines: 4\n'), text)
        # The sheet reads the quantities this file carries (step A's interface).
        sys.path.insert(0, str(REPO / 'scripts'))
        import unit_economics
        found, graded, total = unit_economics.read_quantities(out)
        self.assertEqual(found['samples_in_design'], '6')
        self.assertEqual(found['cpu_hours slurm'], '1.75')
        self.assertIn('session', found)

    def comparison_fixture(self):
        """Step A's comparison template, laid out under scratch the way test_rerun_diff does."""
        table = 'run/tables/de_results.csv'
        stage = self.tmp / 'project/02_bioinformatics/rnaseq_bulk/02_rnaseq-de'
        (stage / 'run/tables').mkdir(parents=True)
        shutil.copyfile(str(FIXTURES / 'de_original.csv'), str(stage / table))
        out = self.tmp / 'out'
        for n in (1, 2):
            target = out / ('run-%d' % n) / '02_bioinformatics/rnaseq_bulk/02_rnaseq-de' / table
            target.parent.mkdir(parents=True)
            shutil.copyfile(str(FIXTURES / ('de_run%d.csv' % n)), str(target))
        template = (FIXTURES / 'comparison.template.json').read_text()
        (out / 'comparison.json').write_text(template.replace('@ORIGINAL_STAGE@', str(stage))
                                             .replace('@WRAPPERS_ROOT@', str(self.tmp / 'w')))
        return out / 'comparison.json'

    def test_refusals(self):
        out = self.tmp / 'bring_home.txt'
        result = bring_home(out, summary=self.tmp / 'absent.json')
        self.assertEqual((result.returncode, result.stderr), (2, b'refused: input_missing '
                                                                 b'summary\n'))
        self.assertFalse(out.exists())
        log = self.tmp / 'pilot1_log.csv'
        log.write_text((FIXTURES / 'pilot1_log.csv').read_text().replace(',human,', ',%s,'
                                                                            % MARKER, 1))
        result = bring_home(out, pilot_log=log)
        self.assertEqual((result.returncode, result.stderr), (2, b'refused: pilot_log_value\n'))
        check = self.tmp / 'check.txt'
        check.write_text('rows: 1; %s\n' % MARKER)
        result = bring_home(out, pilot_check=check)
        self.assertEqual((result.returncode, result.stderr), (2, b'refused: pilot_check_value\n'))
        self.assertFalse(out.exists())

    def test_contract_drift_with_the_dispatcher(self):
        """bring_home and the dispatcher apply the same keep-list to the same payload."""
        payload = json.dumps({
            'ok': False, 'command': 'summary', 'assay': 'rnaseq_bulk', 'status': 'FAILED',
            'failures': [{'check': 'de_results', 'detail': MARKER}], 'gate': ['de_results'],
            'genes_tested': 7, 'padj_lt_0.05': {'up': 1, 'down': MARKER}, 'padj_lt_0.1': 2,
            'na_padj': 0, 'samples_in_design': None, 'extra': MARKER})
        dispatched = json.loads(co.filter_output('rnaseq_de.summary', payload, '', 1)[0])
        self.assertNotIn(MARKER, json.dumps(dispatched))
        path = self.tmp / 'summary.json'
        path.write_text(payload)
        out = self.tmp / 'bring_home.txt'
        self.assertEqual(bring_home(out, summary=path).returncode, 0)
        text = out.read_text()
        self.assertNotIn(MARKER, text)
        kept = dict(line.split(' ', 2)[1:] for line in text.splitlines()
                    if line.startswith('summary ') and not line.startswith('summary padj_lt_0.05'))
        for key in ('status', 'genes_tested', 'padj_lt_0.1', 'na_padj'):
            self.assertEqual(kept[key], str(dispatched[key]))
        self.assertEqual(kept['gate'], ','.join(dispatched['gate']))
        self.assertEqual(dispatched['padj_lt_0.05'], {'up': 1, 'down': co.WITHHELD})
        self.assertNotIn('summary padj_lt_0.05', text)
        self.assertNotIn('quantity samples_in_design', text)
        withheld = len([v for v in dispatched.values() if v == co.WITHHELD])
        self.assertTrue(text.endswith('withheld lines: %d\n' % withheld))
        for line in ('rows: 3; human: 1; agent: 1; tool: 1; open spans: 0; nonce: ok',
                     'check failed: open spans'):
            self.assertEqual(co.pilot_lines(line)[0], [line])

    def test_bench_binding_to_8b_real_header(self):
        """Step A's sheet reads row 8B's real bench header by name; bring_home carries 8B's
        evidence allowlist, no more."""
        sys.path.insert(0, str(REPO / 'scripts'))
        import backend_bench
        import unit_economics
        header = (REPO / 'benchmarks/backend_bench.csv').read_text().splitlines()[0]
        self.assertEqual(header, 'backend,venue,status,workload_id,workload_sha256,samples,'
                                 'wall_s,cpu_s,max_rss_mb,queue_wait_s,python_version,'
                                 'gars_commit,measured_at,cost_usd_per_sample,cost_basis,'
                                 'evidence_sha256,supersedes')
        # The expectation is re-derived from the file by header name, not pinned: row 8B
        # appends real rows (the lane's ruling, 0141's fourth addendum).
        def derived(path):
            with open(str(path), newline='') as handle:
                expected = {}
                for bench_row in csv.DictReader(handle):
                    if bench_row['status'] == 'COMPLETED':
                        expected.setdefault(bench_row['backend'], set()).add(
                            bench_row['cost_basis'])
                return expected
        real = derived(REPO / 'benchmarks/backend_bench.csv')
        self.assertEqual(unit_economics.read_bench(REPO / 'benchmarks/backend_bench.csv'), real)
        appended = self.tmp / 'backend_bench_appended.csv'
        shutil.copyfile(str(REPO / 'benchmarks/backend_bench.csv'), str(appended))
        # a (backend, cost_basis) pair the real file does not yet carry, so the row must show
        backend, basis = next((b, c) for b in unit_economics.BACKENDS
                              for c in unit_economics.UNMETERED_BASES
                              if c not in real.get(b, set()))
        if not appended.read_text().endswith('\n'):
            with open(str(appended), 'a') as handle:
                handle.write('\n')
        with open(str(appended), 'a', newline='') as handle:
            csv.writer(handle, lineterminator='\n').writerow(
                [backend, backend, 'COMPLETED', 'W1', 'd' * 64, '24', '120.5', '7000.25',
                 '18.5', '0', '3.8.2', 'e' * 40, '2026-09-26T00:00:00Z', 'unmetered', basis,
                 'f' * 64, ''])
        self.assertNotEqual(derived(appended), real)
        self.assertEqual(unit_economics.read_bench(appended), derived(appended))
        evidence = {'backend': 'slurm', 'venue': 'slurm', 'status': 'COMPLETED',
                    'workload_id': 'W1', 'workload_sha256': 'a' * 64, 'samples': 24,
                    'wall_s': 100.0, 'cpu_s': 6300.0, 'max_rss_mb': 10.5,
                    'queue_wait_s': 3.0, 'python_version': '3.6.8', 'gars_commit': 'b' * 40,
                    'measured_at': '2026-09-25T00:00:00Z', 'cost_usd_per_sample': 'unmetered',
                    'cost_basis': 'institutional_allocation'}
        with unittest.mock.patch.object(backend_bench, 'validate_evidence',
                                        side_effect=lambda value, completed=False: value):
            row = backend_bench.csv_row(evidence, 'c' * 64)
        copy = self.tmp / 'backend_bench.csv'
        copy.write_text(header + '\n' + ','.join(row[k] for k in header.split(',')) + '\n')
        self.assertEqual(unit_economics.read_bench(copy), {'slurm': {'institutional_allocation'}})
        import bring_home as bh
        self.assertEqual(list(bh.BENCH_FIELDS), backend_bench.FIELDS)

    def test_python36_syntax(self):
        if sys.version_info < (3, 8):
            self.skipTest('ast feature_version needs Python 3.8')
        import ast
        ast.parse(BRING_HOME.read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main(verbosity=2)
