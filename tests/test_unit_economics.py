"""Row 13 step A: the unit-economics sheet (decision 0140, D3; R-193, R-190, R-153, §11.3, §16.4).

Fixture values are synthetic (hourly value 1) and are never evidence. Every check drives the
real CLI; the module prints its reserved line only when regeneration is byte-identical.
"""
import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))
import unit_economics as ue  # noqa: E402 -- red at the parent: the script does not exist there
import pilot_emulation as emulation  # noqa: E402

FIXTURES = REPO / 'tests/fixtures/pilot'
SCRIPT = REPO / 'scripts/unit_economics.py'
FIXTURE_IDS = ('SAMPLEFIX', 'GENEFIX', 'synthetic fixture value', 'synthetic fixture project',
               'fixture-session', 'toolu_fixture')

D1 = {
    'columns': ['ts', 'stage', 'actor', 'action', 'reason_code', 'minutes'],
    'stage': ['00_register', '01_samplesheets', '02_01_counts', '02_02_de', 'rerun', 'report',
              'other'],
    'actor': ['human', 'agent', 'tool'],
    'action': ['read_contract', 'resolve_inputs', 'check', 'prepare', 'submit', 'poll_status',
               'collect', 'summarize', 'fill_config', 'approve_plan', 'fix_input', 'rerun',
               'review_output', 'verify_result', 'interpret', 'draft_claims', 'write_report',
               'wait_queue', 'compute', 'setup', 'break', 'other'],
    'reason_code': ['approval', 'fix', 'rerun', 'data', 'interpretation', 'other'],
}


class UnitEconomicsTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix='row13-ue-')
        self.root = Path(self._temp.name)
        self.inputs = {}
        for role, name in (('log', 'pilot1_log.csv'), ('baseline', 'pilot1_baseline.csv'),
                           ('bench', 'backend_bench.csv'), ('inputs', 'owner_inputs.json'),
                           ('quantities', 'bring_home.txt')):
            target = self.root / name
            shutil.copyfile(str(FIXTURES / name), str(target))
            self.inputs[role] = target

    def tearDown(self):
        self._temp.cleanup()

    def run_sheet(self, out='out', env=None, **override):
        paths = dict(self.inputs, **override)
        command = [sys.executable, str(SCRIPT)]
        for role in ('log', 'baseline', 'bench', 'inputs', 'quantities'):
            command += ['--' + role, str(paths[role])]
        command += ['--out', str(self.root / out)]
        full_env = dict(os.environ, **(env or {}))
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                universal_newlines=True, env=full_env)
        return result

    def sheet_lines(self, **override):
        result = self.run_sheet(**override)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.splitlines()

    def variant(self, name, text):
        path = self.root / ('variant-' + name)
        path.write_text(text)
        return path

    def assert_refused(self, reason, **override):
        out = 'refused-' + reason
        result = self.run_sheet(out=out, **override)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(result.stderr, 'refused: %s\n' % reason)  # a code, never a traceback
        self.assertFalse((self.root / out).exists(), 'a refused sheet wrote output')
        self.assertEqual(result.stdout, '')

    # -- regeneration -------------------------------------------------------------------------

    def test_regenerated_byte_identical(self):
        # Two pinned hash seeds proven to iterate the fixture's two stages in opposite orders,
        # so an ordering taken from a set differs between the runs on every run (review M1).
        orders = [subprocess.run(
            [sys.executable, '-c', "print(list({'02_02_de', 'rerun'} | {'02_02_de'}))"],
            stdout=subprocess.PIPE, universal_newlines=True,
            env=dict(os.environ, PYTHONHASHSEED=seed)).stdout for seed in ('0', '1')]
        self.assertNotEqual(orders[0], orders[1], 'the pinned seeds no longer disagree')
        first = self.run_sheet(out='a', env={'PYTHONHASHSEED': '0'})
        second = self.run_sheet(out='b', env={'PYTHONHASHSEED': '1'})
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(first.stdout, second.stdout)
        for name in ('unit_economics.csv', 'unit_economics.md'):
            self.assertEqual((self.root / 'a' / name).read_bytes(),
                             (self.root / 'b' / name).read_bytes())
        for role, path in self.inputs.items():
            self.assertIn('input %s sha256: %s' % (role, ue.sha256(path)), first.stdout)
        csv_text = (self.root / 'a/unit_economics.csv').read_text()
        self.assertTrue(csv_text.startswith('section,item,value\n'))
        self.assertIn('cost,total,"$0.50 + unmetered compute (local, slurm) + unmeasured compute '
                      '(homelab) + unmetered agent + unpriced liability"', csv_text)
        # Stage lines follow the vocabulary's order, whatever the hash seed.
        for out in (first.stdout, second.stdout):
            self.assertLess(out.index('hours by stage 02_02_de'), out.index('hours by stage rerun'))
            self.assertLess(out.index('time saved 02_02_de'), out.index('time saved rerun'))
        print('EXIT unit economics (fixture): regenerated byte-identical')

    def test_row_and_input_order_do_not_change_the_sheet(self):
        base = self.sheet_lines()
        log = self.inputs['log'].read_text().splitlines()
        shuffled_log = self.variant('log.csv', '\n'.join(log[:2] + log[2:][::-1]) + '\n')
        bench = self.inputs['bench'].read_text().splitlines()
        # Header names, not positions: reverse the columns and the rows.
        rows = [line.split(',')[::-1] for line in bench]
        reordered = self.variant('bench.csv', '\n'.join(
            [','.join(rows[0])] + [','.join(r) for r in rows[1:][::-1]]) + '\n')
        other = self.sheet_lines(log=shuffled_log, bench=reordered)
        strip = lambda lines: [l for l in lines if not l.startswith('input ')]
        self.assertEqual(strip(base), strip(other))

    # -- the formula --------------------------------------------------------------------------

    def test_fixture_sheet(self):
        lines = self.sheet_lines()
        for expected in (
                'log graded: 12 of 12 rows',
                'quantities graded: 5 of 9 lines',
                'quantity samples_in_design: 6',
                'quantity cpu_hours homelab: unmeasured',
                'hours by stage 02_02_de: 0.20 h (12.00 min) x hourly = $0.20',
                'hours by stage rerun: 0.10 h (6.00 min) x hourly = $0.10',
                'verification hours: 0.20 h (12.00 min) x hourly = $0.20',
                'compute local: unmetered (owned_hardware); cpu_hours 0.2',
                'compute homelab: unmeasured (no bench row); cpu_hours unmeasured',
                'compute slurm: unmetered (institutional_allocation); cpu_hours 1.75',
                'agent cost: unmetered (subscription); quantity 7.25 min',
                'liability cost: unpriced',
                'cost total: $0.50 + unmetered compute (local, slurm) + unmeasured compute (homelab) + unmetered agent + unpriced liability',
                'cost unmetered share: compute local, slurm; agent 7.25 min; liability unpriced',
                'cost per sample: $0.50/6 = $0.08',
                'margin: uncomputable: no price (R-193)',
                'time saved 02_02_de: baseline 2.50 h - human 0.35 h = 2.15 h',
                'time saved rerun: unmeasured (no baseline row); human 0.15 h',
                # ruling L3: the total covers baselined stages only; the rest is its own line
                'time saved total: baseline 2.50 h - human 0.35 h = 2.15 h',
                'human hours without a baseline: 0.15 (rerun)',
                'interventions total: 6',
                'row coverage human: 6/12',
                'ratio verification share of human minutes: 12.00/30.00'):
            self.assertIn(expected, lines)

    def test_verification_partition(self):
        # Each human minute lands in exactly one of stage hours or verification hours.
        def totals(lines):
            stage = sum(float(re.search(r'\(([0-9.]+) min\)', l).group(1))
                        for l in lines if l.startswith('hours by stage '))
            verify = float(re.search(r'\(([0-9.]+) min\)',
                                     [l for l in lines if l.startswith('verification ')][0])
                           .group(1))
            return stage, verify
        lines = self.sheet_lines()
        stage, verify = totals(lines)
        self.assertEqual((stage, verify), (18.0, 12.0))
        self.assertAlmostEqual(stage + verify, 30.0)
        # Relabel one non-verification human row as verification: it moves, it is not copied.
        text = self.inputs['log'].read_text().replace(
            '02_02_de,human,fix_input,fix,5.00', '02_02_de,human,verify_result,fix,5.00')
        moved = self.sheet_lines(log=self.variant('log.csv', text))
        self.assertEqual(totals(moved), (13.0, 17.0))
        self.assertIn('cost total: $0.50 + unmetered compute (local, slurm) + unmeasured compute (homelab) + unmetered agent + unpriced liability', moved)
        print('red-on-fault guard: verification partition 12.00 + 18.00 = 30.00 human minutes')

    def test_margin_uncomputable_and_no_price_anywhere(self):
        lines = self.sheet_lines()
        self.assertIn('margin: uncomputable: no price (R-193)', lines)
        self.assertEqual([l for l in lines if l.startswith('margin')],
                         ['margin: uncomputable: no price (R-193)'])
        self.assertFalse([l for l in lines if re.search(r'\bprice\b', l) and 'no price' not in l])
        self.assertFalse([l for l in lines if 'margin' in l and '$' in l])

    def test_zero_over_zero_is_uncomputable(self):
        log = self.inputs['log'].read_text().splitlines()[:2]
        empty = self.variant('log.csv', '\n'.join(log) + '\n')
        quantities = self.variant('q.txt', 'quantity samples_in_design 0\n')
        lines = self.sheet_lines(log=empty, quantities=quantities)
        self.assertIn('log graded: 0 of 0 rows', lines)
        self.assertIn('cost per sample: uncomputable ($0.00/0)', lines)
        self.assertIn('row coverage human: uncomputable (0/0)', lines)
        self.assertIn('ratio verification share of human minutes: uncomputable (0.00/0.00)', lines)
        self.assertIn('cross-check M4: unmeasured', lines)

    def test_missing_quantities_are_never_zero(self):
        lines = self.sheet_lines(quantities=self.variant('q.txt', 'nothing here\n'))
        self.assertIn('quantities graded: 0 of 1 lines', lines)
        self.assertIn('quantity samples_in_design: unmeasured', lines)
        self.assertIn('cost per sample: uncomputable (samples_in_design unmeasured)', lines)
        self.assertIn('compute slurm: unmetered (institutional_allocation); cpu_hours unmeasured',
                      lines)
        self.assertIn('cross-check M4: unmeasured', lines)
        self.assertFalse([l for l in lines if 'DISCREPANCY' in l])

    def test_no_slurm_row_is_unmeasured(self):
        bench = [l for l in self.inputs['bench'].read_text().splitlines()
                 if not l.startswith('slurm,')]
        lines = self.sheet_lines(bench=self.variant('bench.csv', '\n'.join(bench) + '\n'))
        self.assertIn('compute slurm: unmeasured (no bench row); cpu_hours 1.75', lines)
        # The cost line names the unmeasured backends; it never calls them unmetered (review m3).
        self.assertIn('cost total: $0.50 + unmetered compute (local) + unmeasured compute '
                      '(homelab, slurm) + unmetered agent + unpriced liability', lines)
        lines = self.sheet_lines(bench=self.variant('header.csv', bench[0] + '\n'))
        self.assertIn('cost total: $0.50 + unmeasured compute (local, homelab, slurm) + '
                      'unmetered agent + unpriced liability', lines)
        self.assertIn('cost unmetered share: compute none measured; agent 7.25 min; '
                      'liability unpriced', lines)

    def test_cross_check_flags_and_never_corrects(self):
        with_session = self.sheet_lines()
        self.assertIn('cross-check M4: human turns in 02_02 session: 6; inside a human span: 4; '
                      'outside any span: 2 (1.50 min)', with_session)
        self.assertIn('DISCREPANCY: 2 human turns outside any logged span', with_session)
        text = ''.join(l for l in self.inputs['quantities'].read_text().splitlines(True)
                       if not l.startswith('human turns:'))
        without = self.sheet_lines(quantities=self.variant('q.txt', text))
        self.assertIn('cross-check M4: unmeasured', without)
        keep = lambda lines: [l for l in lines if not l.startswith(('input ', 'quantities ',
                                                                    'cross-check', 'DISCREPANCY'))]
        self.assertEqual(keep(with_session), keep(without))
        print('red-on-fault guard: 2 outside turns flagged; every minute unchanged')

    def test_cross_check_counts_from_session_turns(self):
        # The quantities line is exactly what session_turns prints for the fixture transcript,
        # which counts tool_result and isMeta user records as non-human.
        result = subprocess.run(
            [sys.executable, str(REPO / 'scripts/session_turns.py'), '--transcript',
             str(FIXTURES / 'session.jsonl'), '--log', str(FIXTURES / 'pilot1_log.csv'),
             '--stage', '02_02_de'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(result.stdout.strip(), self.inputs['quantities'].read_text().splitlines())

    # -- refusals -----------------------------------------------------------------------------

    def test_refusals(self):
        log = self.inputs['log'].read_text()
        seventh = log.replace('reason_code,minutes', 'reason_code,minutes,cost_usd').replace(
            ',5.00\n', ',5.00,40\n')
        self.assert_refused('log_columns', log=self.variant('log7.csv', seventh))
        self.assert_refused('log_header_nonce',
                            log=self.variant('nononce.csv', log.split('\n', 1)[1]))
        self.assert_refused('log_actor line 3', log=self.variant(
            'actor.csv', log.replace('02_02_de,human,fill_config', '02_02_de,owner,fill_config')))
        self.assert_refused('log_minutes line 3', log=self.variant(
            'minutes.csv', log.replace(',data,5.00', ',data,5')))
        inputs = json.loads(self.inputs['inputs'].read_text())
        for reason, change in (('inputs_unknown_key', {'cost_usd': 40}),
                               ('liability_typed', {'liability': 5000}),
                               ('liability_not_unpriced', {'liability': 'capped'}),
                               ('price_not_null', {'price_usd': 900}),
                               ('inputs_hourly_value', {'hourly_value_usd': True})):
            self.assert_refused(reason, inputs=self.variant(
                reason + '.json', json.dumps(dict(inputs, **change))))
        missing = dict(inputs)
        del missing['price_usd']
        self.assert_refused('inputs_missing_key',
                            inputs=self.variant('missing.json', json.dumps(missing)))
        bench = self.inputs['bench'].read_text()
        for reason, old, new in (
                ('bench_hand_typed_cost line 3', 'unmetered,institutional', '4.20,institutional'),
                ('bench_cost_basis line 3', 'institutional_allocation', 'cloud_invoice'),
                ('bench_status line 2', 'local,COMPLETED', 'local,FAILED'),
                ('bench_number line 3', 'slurm,COMPLETED,6,6300', 'slurm,COMPLETED,6,-1')):
            self.assert_refused(reason, bench=self.variant('bench.csv', bench.replace(old, new)))
        self.assert_refused('bench_missing_column', bench=self.variant(
            'nobasis.csv', bench.replace('cost_basis', 'basis')))
        quantities = self.inputs['quantities'].read_text()
        self.assert_refused('quantity_conflict samples_in_design', quantities=self.variant(
            'q.txt', quantities + 'quantity samples_in_design 7\n'))
        # Input that crashes a parser is a named refusal with no traceback and no path.
        nul = log.replace(',data,5.00', ',data,5.00\x00')
        self.assert_refused('log_malformed line 3', log=self.variant('nul.csv', nul))
        self.assert_refused('bench_malformed', bench=self.variant(
            'nul-bench.csv', bench.replace('local,', 'lo\x00cal,')))
        self.assert_refused('bench_malformed', bench=self.variant(
            'long-bench.csv', bench.replace('local,', 'l' + 'o' * 200000 + 'cal,')))
        self.assert_refused('inputs_not_json',
                            inputs=self.variant('deep.json', '[' * 100000))
        # A number past the decimal context cannot be printed to the cent: a fixed code (r1).
        self.assert_refused('value_out_of_range', inputs=self.variant(
            'huge.json', json.dumps(dict(inputs, hourly_value_usd=1)).replace(
                '"hourly_value_usd": 1', '"hourly_value_usd": 1e30')))
        self.assert_refused('value_out_of_range', log=self.variant(
            'huge.csv', log.replace(',data,5.00', ',data,99999999999999999999999999999.00')))
        # An exponent past the context's Emax raises decimal.Overflow, not InvalidOperation (m1).
        for exponent in ('1e999999', '1E+999999999'):
            self.assert_refused('value_out_of_range', inputs=self.variant(
                'overflow.json', json.dumps(dict(inputs, hourly_value_usd=1)).replace(
                    '"hourly_value_usd": 1', '"hourly_value_usd": ' + exponent)))
        print('red-on-fault: seventh column, unknown key, typed liability, non-null price, '
              'hand-typed bench cost -> each REFUSED with its reason')

    def test_quantity_lines_canonical_or_refused(self):
        # Ruling L4: a `quantity ` line off the fixed shapes is refused, never ignored.
        quantities = self.inputs['quantities'].read_text()
        for line in ('quantity samples_in_design 7 ', 'quantity  samples_in_design 8',
                     'quantity cpu_hours Slurm 9.00', 'quantity samples_in_design -3',
                     'quantity cpu_hours cloud 3.00', 'quantity samples_in_design',
                     'quantity wall_hours slurm 1',
                     # the keyword in any case, after leading whitespace, is a quantity line (n2)
                     'Quantity samples_in_design 7', ' quantity samples_in_design 7',
                     'quantity\tsamples_in_design 7', 'QUANTITY samples_in_design 7', 'quantity'):
            self.assert_refused('quantity_malformed', quantities=self.variant(
                'bad-q.txt', quantities + line + '\n'))
        # A repeat is compared by canonical value and printed canonically, so line order and
        # spelling never change the sheet.
        spelled = ['quantity samples_in_design 006', 'quantity cpu_hours slurm 1.750',
                   'quantity cpu_hours slurm 01.75', 'quantity cpu_hours local 0.2']
        sheets = []
        for name, lines in (('fwd', spelled), ('rev', spelled[::-1])):
            out = self.sheet_lines(quantities=self.variant(
                name + '.txt', quantities + '\n'.join(lines) + '\n'))
            sheets.append([l for l in out if not l.startswith(('input ', 'quantities '))])
        self.assertEqual(sheets[0], sheets[1])
        for expected in ('quantity samples_in_design: 6', 'quantity cpu_hours slurm: 1.75',
                         'compute local: unmetered (owned_hardware); cpu_hours 0.2'):
            self.assertIn(expected, sheets[0])
        self.assert_refused('quantity_conflict cpu_hours slurm', quantities=self.variant(
            'conflict.txt', quantities + 'quantity cpu_hours slurm 1.76\n'))
        # A word that merely starts with the keyword is another line shape: counted, ignored.
        ignored = self.sheet_lines(quantities=self.variant(
            'word.txt', quantities + 'quantity_notes: none\n'))
        self.assertIn('quantities graded: 5 of 10 lines', ignored)
        self.assertEqual(ue.canonical_decimal('0.20'), '0.2')
        self.assertEqual(ue.canonical_decimal('100'), '100')
        self.assertEqual(ue.canonical_decimal('000.000'), '0')
        # Step B, D-vi n2: a line starting `human turns:` off the session_turns shape is refused,
        # never counted and ignored.
        session = [l for l in quantities.splitlines() if l.startswith('human turns:')][0]
        for line in (session.replace('; outside window: 0', ''),
                     session.replace('1.50', '1.5'), session + ' ', 'human turns: 6',
                     session.replace('graded 14 of 14 records', 'graded 14 of 15 records x')):
            self.assert_refused('quantity_malformed', quantities=self.variant(
                'bad-session.txt', quantities + line + '\n'))
        print('red-on-fault guard: malformed quantity lines refused; repeats compared canonically')

    def test_refusal_codes_do_not_depend_on_the_interpreter(self):
        # The lane's 3.13 host refused a NUL log row as `log_minutes` where 3.8 said
        # `log_malformed`: csv reads NUL as data from 3.11. Each case must give the same exit code,
        # stdout and stderr with the interpreter emulated on both sides of every split.
        log = self.inputs['log'].read_text()
        bench = self.inputs['bench'].read_text()
        baseline = self.inputs['baseline'].read_text()
        quantities = self.inputs['quantities'].read_text()
        many = '9' * 5000
        session = [l for l in quantities.splitlines() if l.startswith('human turns: ')][0]
        cases = (
            ('refused: log_malformed line 3\n',
             {'log': self.variant('nul.csv', log.replace(',data,5.00', ',data,5.00\x00'))}),
            ('refused: bench_malformed\n',
             {'bench': self.variant('nul-b.csv', bench.replace('local,', 'lo\x00cal,'))}),
            ('refused: baseline_malformed\n', {'baseline': self.variant(
                'nul-base.csv', baseline.replace('estimate', 'esti\x00mate'))}),
            ('', {'quantities': self.variant('long.txt', quantities.replace(
                'quantity samples_in_design 6', 'quantity samples_in_design ' + many))}),
            ('', {'quantities': self.variant('long-s.txt', quantities.replace(
                session, session.replace('human turns: 6; inside spans: 4',
                                         'human turns: %s; inside spans: %s'
                                         % (many, '9' * 4999 + '7'))))}),
            ('refused: quantity_session_inconsistent\n', {'quantities': self.variant(
                'long-x.txt', quantities.replace(session, session.replace(
                    'human turns: 6', 'human turns: ' + many)))}),
        )
        results = []
        for number, (stderr, override) in enumerate(cases):
            paths = dict(self.inputs, **override)
            seen = []
            for side in ('old', 'new'):
                argv = []
                for role in ('log', 'baseline', 'bench', 'inputs', 'quantities'):
                    argv += ['--' + role, str(paths[role])]
                argv += ['--out', str(self.root / ('emulated-%d-%s' % (number, side)))]
                with emulation.emulating(side, [ue]):
                    seen.append(emulation.outcome(ue.main, argv))
            self.assertEqual(seen[0], seen[1], 'case %d differs between interpreters' % number)
            self.assertEqual((seen[0][0], seen[0][2]), (2 if stderr else 0, stderr))
            results.append(seen[0])
        self.assertTrue('quantity samples_in_design: ' + many in results[3][1].splitlines(),
                        'the long count is not printed from its digits')
        self.assertIn('DISCREPANCY: 2 human turns outside any logged span',
                      results[4][1].splitlines())
        # A non-ASCII owner string (never printed) reads the same under a C locale as under UTF-8.
        inputs = json.loads(self.inputs['inputs'].read_text())
        accented = self.root / 'accented.json'
        accented.write_bytes(json.dumps(dict(inputs, hourly_value_source='synthetic f\u00e9e'),
                                        ensure_ascii=False).encode('utf-8'))
        runs = [self.run_sheet(out='locale-' + name, env=env, inputs=accented) for name, env in (
            ('c', {'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0'}),
            ('utf8', {'PYTHONUTF8': '1'}))]
        self.assertEqual([r.returncode for r in runs], [0, 0], runs[0].stderr + runs[1].stderr)
        self.assertEqual(runs[0].stdout, runs[1].stdout)
        print('red-on-fault guard: every refusal code is the same on both sides of each '
              'Python-version split')

    def test_templates_are_not_inputs(self):
        # The committed templates cannot be used as filled files: they carry placeholders.
        self.assert_refused('log_header_nonce', log=REPO / 'docs/pilot/pilot1_log.template.csv')
        self.assert_refused('inputs_hourly_value',
                            inputs=REPO / 'docs/pilot/owner_inputs.template.json')
        template = json.loads((REPO / 'docs/pilot/owner_inputs.template.json').read_text())
        self.assertEqual(sorted(template), sorted(ue.INPUT_KEYS))
        self.assertEqual((template['liability'], template['price_usd']), ('unpriced', None))
        baseline = (REPO / 'docs/pilot/pilot1_baseline.template.csv').read_text()
        self.assertEqual(baseline, 'stage,action,hours,basis\n')

    # -- invariants ---------------------------------------------------------------------------

    def test_output_invariants(self):
        result = self.run_sheet()
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = [result.stdout, (self.root / 'out/unit_economics.csv').read_text(),
                   (self.root / 'out/unit_economics.md').read_text()]
        for text in outputs:
            for forbidden in FIXTURE_IDS + (str(self.root), str(REPO)):
                self.assertNotIn(forbidden, text)
            self.assertIsNone(re.search(r'(^|[\s(])/[A-Za-z]', text, re.M), 'a path was printed')
        self.assertEqual(outputs[0].count('\n'),
                         outputs[1].count('\n') - 1)  # the csv adds its header row

    def test_vocabulary_is_d1(self):
        vocab = json.loads((REPO / 'docs/pilot/pilot_log_vocabulary.json').read_text())
        for key, value in D1.items():
            self.assertEqual(vocab[key], value)
        self.assertEqual(vocab['header_comment'], '# gars-pilot-log v1 nonce=<32 hex>')
        self.assertEqual(vocab['verification_actions'], ['review_output', 'verify_result'])
        self.assertEqual(vocab['baseline_basis'], ['measured_prior', 'estimate'])
        fixture = self.inputs['log'].read_text().splitlines()
        self.assertTrue(re.match(vocab['header_comment_regex'], fixture[0]))
        rows = ue.read_log(self.inputs['log'])
        for column in ('actor', 'reason_code'):
            self.assertEqual(sorted({r[column] for r in rows}), sorted(D1[column]))
        self.assertEqual(sorted({r['stage'] for r in rows}), ['02_02_de', 'rerun'])

    def test_readme_defines_the_interfaces(self):
        readme = (REPO / 'docs/pilot/README.md').read_text()
        for shape in ('quantity samples_in_design <non-negative integer>',
                      'quantity cpu_hours <backend> <non-negative decimal>',
                      'human turns: <t>; inside spans: <i>; outside spans: <o>; outside minutes: '
                      '<m>; session wall minutes: <w>; agent active minutes: <a>; outside window: '
                      '<k>; graded <n> of <n> records'):
            self.assertIn(shape, readme)
        examples = re.findall(r'^    (quantity .+|human turns: .+)$', readme, re.M)
        self.assertEqual(len(examples), 3)
        path = self.variant('readme-q.txt', '\n'.join(examples) + '\n')
        found, graded, total = ue.read_quantities(path)
        self.assertEqual((graded, total), (3, 3))
        self.assertEqual(sorted(found), ['cpu_hours slurm', 'samples_in_design', 'session'])

    def test_python36_syntax(self):
        if sys.version_info < (3, 8):
            self.skipTest('ast feature_version needs Python 3.8')
        for name in ('unit_economics.py', 'rerun_diff.py', 'session_turns.py'):
            ast.parse((REPO / 'scripts' / name).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main(verbosity=2)
