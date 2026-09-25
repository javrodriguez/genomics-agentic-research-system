"""Row 13 step A: the session cross-check (decision 0140, D4b and ruling L1).

The transcript is synthetic: human turns, tool_result user records, isMeta records and
assistant records, with two human turns outside every logged span. Every check drives the
real CLI; the output is numbers only.
"""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import session_turns as st  # noqa: E402 -- red at the parent: the script does not exist there

FIXTURES = REPO / 'tests/fixtures/pilot'
SCRIPT = REPO / 'scripts/session_turns.py'
EXPECTED = ('human turns: 6; inside spans: 4; outside spans: 2; outside minutes: 1.50; '
            'session wall minutes: 47.00; agent active minutes: 45.50; graded 14 of 14 records')
LINE = re.compile(r'^human turns: \d+; inside spans: \d+; outside spans: \d+; outside minutes: '
                  r'\d+\.\d\d; session wall minutes: \d+\.\d\d; agent active minutes: \d+\.\d\d; '
                  r'graded (\d+) of (\d+) records\n$')
LOG_HEAD = ('# gars-pilot-log v1 nonce=0123456789abcdef0123456789abcdef\n'
            'ts,stage,actor,action,reason_code,minutes\n')


def user(ts, content, meta=None):
    record = {'type': 'user', 'timestamp': ts, 'message': {'role': 'user', 'content': content}}
    if meta is not None:
        record['isMeta'] = meta
    return record


def assistant(ts):
    return {'type': 'assistant', 'timestamp': ts,
            'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'ok'}]}}


class SessionTurnsTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix='row13-st-')
        self.root = Path(self._temp.name)

    def tearDown(self):
        self._temp.cleanup()

    def run_turns(self, transcript=None, log=None, stage='02_02_de'):
        return subprocess.run(
            [sys.executable, str(SCRIPT), '--transcript',
             str(transcript or FIXTURES / 'session.jsonl'), '--log',
             str(log or FIXTURES / 'pilot1_log.csv'), '--stage', stage],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def write(self, name, records):
        path = self.root / name
        path.write_text(''.join(json.dumps(r) + '\n' if not isinstance(r, str) else r + '\n'
                                for r in records))
        return path

    def log(self, rows):
        path = self.root / 'log.csv'
        path.write_text(LOG_HEAD + ''.join(r + '\n' for r in rows))
        return path

    def line(self, records, rows):
        result = self.run_turns(self.write('t.jsonl', records), self.log(rows))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def assert_unclassifiable(self, records, line_no):
        result = self.run_turns(self.write('bad.jsonl', records))
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertEqual(result.stderr, 'refused: unclassifiable record line %d\n' % line_no)
        self.assertEqual(result.stdout, '')

    def test_fixture_counts_only(self):
        result = self.run_turns()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED + '\n')
        match = LINE.match(result.stdout)
        self.assertEqual(match.group(1), match.group(2))
        transcript = (FIXTURES / 'session.jsonl').read_text()
        for word in ('SAMPLEFIX', 'GENEFIX', 'fixture-session', 'toolu_fixture', 'approved',
                     'command-name', str(REPO)):
            self.assertIn(word, transcript + str(REPO))
            self.assertNotIn(word, result.stdout + result.stderr)
        # The line is exactly the one the bring-home fixture carries for the sheet.
        self.assertIn(EXPECTED, (FIXTURES / 'bring_home.txt').read_text().splitlines())
        print('EXIT session turns (fixture): counts only')

    def test_tool_result_and_meta_are_not_human(self):
        records = [json.loads(l) for l in (FIXTURES / 'session.jsonl').read_text().splitlines()]
        kinds = [st.classify(r) for r in records]
        self.assertEqual(kinds.count('human'), 6)
        self.assertEqual(kinds.count('tool_result'), 2)
        self.assertEqual(kinds.count('meta'), 1)
        self.assertEqual(kinds.count('assistant'), 5)
        only_machine = [user('2026-01-15T10:00:00Z', [{'type': 'tool_result', 'content': 'x'}]),
                        user('2026-01-15T10:01:00Z', 'hook output', meta=True),
                        assistant('2026-01-15T10:02:00Z')]
        out = self.line(only_machine, [])
        self.assertTrue(out.startswith('human turns: 0; inside spans: 0; outside spans: 0; '
                                       'outside minutes: 0.00; session wall minutes: 2.00;'))
        print('red-on-fault guard: tool_result and isMeta user records counted non-human')

    def test_outside_minutes_ruling_l1(self):
        span = '2026-01-15T10:10:00Z,02_02_de,human,check,other,5.00'  # 10:10-10:15
        other_stage = '2026-01-15T10:00:00Z,rerun,human,check,other,30.00'
        records = [
            user('2026-01-15T10:00:00Z', 'first turn, no earlier record: empty interval'),
            assistant('2026-01-15T10:08:00Z'),
            # the latest record strictly earlier IN TIME is the 10:12 turn below (file order is
            # not time order): 10:12 -> 10:17, clipped to the span, leaves 10:15-10:17 = 2 min
            user('2026-01-15T10:17:00Z', 'outside'),
            assistant('2026-01-15T10:17:30Z'),
            # inside the span: contributes nothing
            user('2026-01-15T10:12:00+00:00', [{'type': 'text', 'text': 'inside'}]),
            # latest record strictly earlier in time is 10:17:30 -> 10:19:30 = 2 minutes
            user('2026-01-15T11:19:30+01:00', 'outside, offset timestamp'),
        ]
        out = self.line(records, [span, other_stage])
        self.assertEqual(out, 'human turns: 4; inside spans: 1; outside spans: 3; outside '
                              'minutes: 4.00; session wall minutes: 19.50; agent active minutes: '
                              '9.50; graded 6 of 6 records\n')
        # Overlapping attention intervals are counted once: two turns at one instant share one.
        overlap = [assistant('2026-01-15T10:00:00Z'), user('2026-01-15T10:03:00Z', 'a'),
                   user('2026-01-15T10:03:00Z', 'b')]
        self.assertIn('outside minutes: 3.00;', self.line(overlap, []))
        # Rounded half-up once, at the end: 30.3 s + 30.3 s = 60.6 s = 1.01 min.
        halves = [assistant('2026-01-15T10:00:00Z'), user('2026-01-15T10:00:30.300Z', 'a'),
                  assistant('2026-01-15T10:01:00Z'), user('2026-01-15T10:01:30.300Z', 'b')]
        self.assertIn('outside minutes: 1.01;', self.line(halves, []))
        # The stage's spans only: under `rerun` its 30-minute span holds every turn.
        result = self.run_turns(self.write('t.jsonl', records), self.log([span, other_stage]),
                                stage='rerun')
        self.assertIn('inside spans: 4; outside spans: 0; outside minutes: 0.00;', result.stdout)

    def test_unclassifiable_records_exit_2(self):
        good = assistant('2026-01-15T10:00:00Z')
        mixed = user('2026-01-15T10:01:00Z', [{'type': 'tool_result', 'content': 'x'},
                                              {'type': 'text', 'text': 'y'}])
        for bad in ({'type': 'summary', 'timestamp': '2026-01-15T10:01:00Z'},
                    user('2026-01-15 10:01:00', 'no T, no zone'),
                    user('2026-01-15T10:01:00', 'no zone'),
                    user('2026-02-30T10:01:00Z', 'no such day'),
                    user('2026-01-15T24:01:00Z', 'no such hour'),
                    {'type': 'user', 'message': {'role': 'user', 'content': 'no timestamp'}},
                    user('2026-01-15T10:01:00Z', 'meta not a bool', meta='yes'),
                    user('2026-01-15T10:01:00Z', []),
                    mixed, 'not json', '', '[1, 2]'):
            self.assert_unclassifiable([good, bad, good], 2)
        print('red-on-fault guard: every unclassifiable record exits 2; none skipped')

    def test_log_is_validated(self):
        bad_log = self.root / 'bad.csv'
        bad_log.write_text('ts,stage,actor,action,reason_code,minutes\n')
        result = self.run_turns(log=bad_log)
        self.assertEqual((result.returncode, result.stderr), (2, 'refused: log_header_nonce\n'))
        result = self.run_turns(stage='02_03_nothing')
        self.assertEqual((result.returncode, result.stderr), (2, 'refused: stage\n'))

    def test_timestamps(self):
        self.assertEqual(st.micros('1970-01-01T00:00:01Z'), 1000000)
        self.assertEqual(st.micros('1970-01-01T01:00:01+01:00'), 1000000)
        self.assertEqual(st.micros('1970-01-01T00:00:01.5-0000'), 1500000)
        self.assertEqual(st.micros('2024-02-29T00:00:00Z') - st.micros('2024-02-28T00:00:00Z'),
                         86400 * 1000000)
        for bad in ('2023-02-29T00:00:00Z', '2026-01-15T10:00:00+25:00', 20260115, None):
            self.assertIsNone(st.micros(bad))


if __name__ == '__main__':
    unittest.main(verbosity=2)
