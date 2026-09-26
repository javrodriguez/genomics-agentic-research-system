"""Row 13 step A: the session cross-check (decision 0140, D4b and rulings L1, L2, L6; 0150).

The transcript is synthetic: human turns, tool_result user records, isMeta records and
assistant records, with two human turns outside every logged span. Every check drives the
real CLI; the output is numbers only.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
sys.path.insert(0, str(REPO / 'tests'))
import session_turns as st  # noqa: E402 -- red at the parent: the script does not exist there
import pilot_emulation as emulation  # noqa: E402

FIXTURES = REPO / 'tests/fixtures/pilot'
SCRIPT = REPO / 'scripts/session_turns.py'
EXPECTED = ('human turns: 6; inside spans: 4; outside spans: 2; outside minutes: 1.50; '
            'session wall minutes: 47.00; agent active minutes: 45.50; outside window: 0; '
            'graded 14 of 14 records')
LINE = re.compile(r'^human turns: \d+; inside spans: \d+; outside spans: \d+; outside minutes: '
                  r'\d+\.\d\d; session wall minutes: \d+\.\d\d; agent active minutes: \d+\.\d\d; '
                  r'outside window: \d+; graded (\d+) of (\d+) records\n$')
# The sanitized inventory of 40 real local transcripts (ruling 0150; type names, counts and key
# names only): the real-type fixture must carry every record type it lists.
INVENTORY = json.loads((FIXTURES / 'transcript_type_inventory.json').read_text(encoding='utf-8'))
LOG_HEAD = ('# gars-pilot-log v1 nonce=0123456789abcdef0123456789abcdef\n'
            'ts,stage,actor,action,reason_code,minutes\n')


def user(ts, content, meta=None):
    record = {'type': 'user', 'timestamp': ts, 'message': {'role': 'user', 'content': content}}
    if meta is not None:
        record['isMeta'] = meta
    return record


def harness(ts, key):
    """A user record Claude Code writes itself (ruling L2), with real bookkeeping keys."""
    record = user(ts, 'This session is being continued from a previous conversation.')
    record.update({key: True, 'uuid': 'fixture-uuid', 'parentUuid': None, 'cwd': 'fixture-cwd',
                   'userType': 'external', 'version': '0.0.0', 'gitBranch': 'fixture'})
    return record


def assistant(ts, sidechain=None):
    record = {'type': 'assistant', 'timestamp': ts,
              'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'ok'}]}}
    if sidechain is not None:
        record['isSidechain'] = sidechain
    return record


class SessionTurnsTests(unittest.TestCase):
    def setUp(self):
        self._temp = tempfile.TemporaryDirectory(prefix='row13-st-')
        self.root = Path(self._temp.name)

    def tearDown(self):
        self._temp.cleanup()

    def run_turns(self, transcript=None, log=None, stage='02_02_de', env=None):
        return subprocess.run(
            [sys.executable, str(SCRIPT), '--transcript',
             str(transcript or FIXTURES / 'session.jsonl'), '--log',
             str(log or FIXTURES / 'pilot1_log.csv'), '--stage', stage],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
            env=dict(os.environ, **(env or {})))

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

    def test_harness_records_are_graded_not_human(self):
        # Ruling L2: isCompactSummary and isSidechain user records are non-human; graded, never a
        # human turn, never the predecessor of an outside turn. The fixture's outside turn at
        # 10:12:30 has its predecessor at 10:10:30; harness records at 10:12:00 and 10:12:15
        # would shorten its interval if they counted.
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        extra = [json.dumps(harness('2026-01-15T10:12:00Z', 'isCompactSummary')),
                 json.dumps(harness('2026-01-15T10:12:15Z', 'isSidechain'))]
        self.assertEqual([st.classify(json.loads(l)) for l in extra], ['harness', 'harness'])
        result = self.run_turns(self.write('h.jsonl', lines[:8] + extra + lines[8:]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED.replace('graded 14 of 14', 'graded 16 of 16')
                         + '\n')
        # Ruling L6, narrowed by L7: a user or assistant record carrying isSidechain is subagent
        # traffic. A subagent's reply at 10:12:20 would otherwise start the 10:12:30 outside
        # turn's interval (0.17 min, not 1.50), and one at 09:59:30 would stretch the agent-active
        # span to 46.50.
        sidechain = [json.dumps(assistant('2026-01-15T10:12:20Z', sidechain=True)),
                     json.dumps(assistant('2026-01-15T09:59:30Z', sidechain=True)),
                     json.dumps(dict(user('2026-01-15T10:12:25Z', 'subagent prompt'),
                                     isSidechain=True))]
        self.assertEqual([st.classify(json.loads(l)) for l in sidechain], ['harness'] * 3)
        self.assertEqual(st.classify(assistant('2026-01-15T10:12:20Z', sidechain=False)),
                         'assistant')
        self.assertIsNone(st.classify(assistant('2026-01-15T10:12:20Z', sidechain='yes')))
        result = self.run_turns(self.write('s.jsonl', lines[:8] + sidechain + lines[8:]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED.replace('graded 14 of 14', 'graded 17 of 17')
                         + '\n')
        # Review round 3, m2: a record carrying isSidechain OR isMeta is never a predecessor and
        # never a human turn, whichever flag is read first; one carrying both is no different.
        both = user('2026-01-15T10:12:20Z', 'subagent hook output', meta=True)
        both['isSidechain'] = True
        flagged = [json.dumps(both), json.dumps(user('2026-01-15T10:12:22Z', 'hook', meta=True)),
                   json.dumps(dict(assistant('2026-01-15T10:12:24Z'), isMeta=True))]
        self.assertNotIn('human', [st.classify(json.loads(l)) for l in flagged])
        result = self.run_turns(self.write('m.jsonl', lines[:8] + flagged + lines[8:]))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, EXPECTED.replace('graded 14 of 14', 'graded 17 of 17')
                         + '\n')
        # An unknown bookkeeping key on a human turn leaves it a human turn.
        extra_key = json.loads(lines[0])
        extra_key.update({'uuid': 'u', 'cwd': 'c', 'isSidechain': False, 'somethingNew': 1})
        self.assertEqual(st.classify(extra_key), 'human')
        # The flags must be booleans, like isMeta.
        for key in ('isCompactSummary', 'isSidechain'):
            bad = harness('2026-01-15T10:12:00Z', key)
            bad[key] = 'yes'
            self.assertIsNone(st.classify(bad))
        print('red-on-fault guard: isCompactSummary and isSidechain records graded, never human, '
              'never a predecessor, never agent activity')

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
                              '9.50; outside window: 0; graded 6 of 6 records\n')
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
        for bad in (user('2026-01-15 10:01:00', 'no T, no zone'),
                    user('2026-01-15T10:01:00', 'no zone'),
                    user('2026-02-30T10:01:00Z', 'no such day'),
                    user('2026-01-15T24:01:00Z', 'no such hour'),
                    {'type': 'user', 'message': {'role': 'user', 'content': 'no timestamp'}},
                    user('2026-01-15T10:01:00Z', 'meta not a bool', meta='yes'),
                    user('2026-01-15T10:01:00Z', []),
                    mixed, 'not json', '', '[1, 2]',
                    # a parser crash is unclassifiable, never a traceback naming a host path
                    '[' * 100000):
            self.assert_unclassifiable([good, bad, good], 2)
        # Ruling 0150 (R1, superseding L7 (a) for a non-empty string type): a `summary` record
        # was unclassifiable here; it is now a harness record, graded and never timed.
        self.assertEqual(self.line([good, {'type': 'summary', 'timestamp': '2026-01-15T10:01:00Z'},
                                    good], []),
                         'human turns: 0; inside spans: 0; outside spans: 0; outside minutes: '
                         '0.00; session wall minutes: 0.00; agent active minutes: 0.00; outside '
                         'window: 0; graded 3 of 3 records\n')
        nul_log = self.root / 'nul.csv'
        nul_log.write_text(LOG_HEAD + '2026-01-15T10:00:00Z,02_02_de,human,check,other,5.00\x00\n')
        result = self.run_turns(log=nul_log)
        self.assertEqual((result.returncode, result.stderr), (2, 'refused: log_malformed line 3\n'))
        print('red-on-fault guard: every unclassifiable record exits 2; none skipped')

    def test_unknown_type_exits_2_whatever_its_flags(self):
        # Ruling L7 (a), review round 3 m3: the type is checked first, and no flag makes a missing
        # or null type classifiable. Ruling 0150 (R1) supersedes L7 (a) for a non-empty string
        # type other than `user` or `assistant`: it is a harness record, graded, and its flags
        # and timestamp are not examined. The `banana` record is the reviewer's, which moved
        # session wall minutes to 2103853.33 at 7c202a4; it now moves no number but `graded`.
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        for flag in ('isSidechain', 'isMeta', 'isCompactSummary'):
            for record in ('{"type":null,"%s":true,"timestamp":"2026-01-15T10:12:20Z"}' % flag,
                           '{"%s":true,"timestamp":"2026-01-15T10:12:20Z"}' % flag):
                result = self.run_turns(self.write('u.jsonl', lines + [record]))
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (2, '', 'refused: unclassifiable record line 15\n'), record)
            for record in ('{"type":"banana","%s":true,"timestamp":"2030-01-15T10:12:20Z"}' % flag,
                           '{"type":"system","%s":true,"timestamp":"2026-01-15T10:12:20Z"}' % flag):
                result = self.run_turns(self.write('u.jsonl', lines + [record]))
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (0, EXPECTED.replace('graded 14 of 14', 'graded 15 of 15')
                                  + '\n', ''), record)
        print('red-on-fault guard: a missing or null record type exits 2 whatever its flags; an '
              'unknown one is a harness record whatever its flags')

    def test_real_record_types_graded_as_harness(self):
        # Ruling 0150, test (a): a transcript carrying one or more records of every type the
        # sanitized inventory of 40 real sessions lists, each with only the keys the inventory
        # found on that type, interleaved with the step A fixture. Stripped of every type but
        # `user` and `assistant` it is the step A fixture byte for byte, and it yields the same
        # number for every field of the line; each `graded` count is its own file's record count.
        real = (FIXTURES / 'session_real_types.jsonl').read_text()
        types = [json.loads(l)['type'] for l in real.splitlines()]
        self.assertEqual(sorted(set(types)), sorted(INVENTORY['types']))
        self.assertEqual(len(INVENTORY['types']), 15)
        stripped = ''.join(l + '\n' for l in real.splitlines()
                           if json.loads(l)['type'] in ('user', 'assistant'))
        self.assertEqual(stripped, (FIXTURES / 'session.jsonl').read_text())
        runs = [self.run_turns(FIXTURES / 'session_real_types.jsonl'),
                self.run_turns(self.write('stripped.jsonl', stripped.splitlines()))]
        self.assertEqual([(r.returncode, r.stderr) for r in runs], [(0, '')] * 2)
        fields = [dict(re.findall(r'(?:^|; )([a-z ]+): ([0-9.]+)', r.stdout)) for r in runs]
        self.assertEqual(sorted(fields[0]), ['agent active minutes', 'human turns',
                                             'inside spans', 'outside minutes', 'outside spans',
                                             'outside window', 'session wall minutes'])
        for name in sorted(fields[0]):
            self.assertEqual(fields[0][name], fields[1][name], name)
        graded = [LINE.match(r.stdout).groups() for r in runs]
        self.assertEqual(graded, [(str(len(types)),) * 2,
                                  (str(types.count('user') + types.count('assistant')),) * 2])
        self.assertEqual(runs[0].stdout,
                         EXPECTED.replace('graded 14 of 14', 'graded 34 of 34') + '\n')
        print('red-on-fault guard: every real record type is graded; none moves a number')

    def test_harness_type_never_timed(self):
        # Ruling 0150, test (b): a record of a non-message type is never a human turn, never the
        # predecessor of an outside turn, never agent activity and never part of the window,
        # whatever its timestamp (far future, before the window, unparseable or absent), flags or
        # content. The fixture's outside turn at 10:12:30 has its predecessor at 10:10:30.
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        records = [
            {'type': 'system', 'timestamp': '2026-01-15T10:12:20Z', 'isSidechain': False,
             'isMeta': False, 'message': {'role': 'user', 'content': 'looks like a human turn'}},
            {'type': 'attachment', 'timestamp': '2026-01-15T10:12:25Z',
             'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': 'ok'}]}},
            {'type': 'queue-operation', 'timestamp': '2030-01-15T10:12:20Z'},
            {'type': 'queue-operation', 'timestamp': '2026-01-15T09:00:00Z'},
            {'type': 'file-history-delta', 'timestamp': 'not a time'},
            {'type': 'mode', 'timestamp': 20260115, 'isMeta': 'yes', 'isSidechain': None},
            {'type': 'ai-title', 'message': 'not an object'},
        ]
        # Review round 1, F2: the type comparison is exact. A record whose type differs from
        # `user` or `assistant` only in case or by a space is a harness record, whatever it holds.
        for kind in ('User', 'USER', 'user ', 'Assistant'):
            records.append({'type': kind, 'timestamp': '2026-01-15T10:12:20Z',
                            'message': {'role': 'user', 'content': 'is GENEFIX0003 filtered?'}})
        for where in (0, 8, 9, len(lines)):
            for record in records:
                result = self.run_turns(self.write(
                    'b.jsonl', lines[:where] + [json.dumps(record)] + lines[where:]))
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (0, EXPECTED.replace('graded 14 of 14', 'graded 15 of 15')
                                  + '\n', ''), (where, record))
        # Every one of them at once, just before the outside turn.
        result = self.run_turns(self.write(
            'all.jsonl', lines[:8] + [json.dumps(r) for r in records] + lines[8:]))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, EXPECTED.replace('graded 14 of 14', 'graded 25 of 25') + '\n', ''))
        # Alone, they make no window: nothing inside, nothing outside, no minute.
        self.assertEqual(self.line(records, []),
                         'human turns: 0; inside spans: 0; outside spans: 0; outside minutes: '
                         '0.00; session wall minutes: 0.00; agent active minutes: 0.00; outside '
                         'window: 0; graded 11 of 11 records\n')
        self.assertEqual([st.classify(r) for r in records], ['harness_type'] * len(records))
        print('red-on-fault guard: a harness-type record is never a turn, a predecessor, agent '
              'activity or part of the window')

    def test_records_split_on_newline_only(self):
        # Review round 1, F1 (the lane's ruling): records are the file's "\n"-separated lines, a
        # trailing "\r" stripped. JSON allows U+2028, U+2029 and U+0085 raw inside a string;
        # str.splitlines() would cut a record there. A harness record carrying one is graded in
        # full; a user record carrying one classifies as it would without it.
        real = (FIXTURES / 'session_real_types.jsonl').read_text(encoding='utf-8').splitlines()
        lines = (FIXTURES / 'session.jsonl').read_text(encoding='utf-8').splitlines()
        for char in (' ', ' ', '\u0085'):
            carried = []
            for line in real:
                record = json.loads(line)
                if record['type'] == 'ai-title':
                    record['aiTitle'] = 'a title%sover two lines' % char
                elif record['type'] == 'last-prompt':
                    record['lastPrompt'] = 'a prompt%sover two lines' % char
                carried.append(json.dumps(record, ensure_ascii=False)
                               if record['type'] in ('ai-title', 'last-prompt') else line)
            text = ''.join(l + '\n' for l in carried)
            self.assertEqual(text.count(char), len([l for l in real if json.loads(l)['type']
                                                    in ('ai-title', 'last-prompt')]))
            self.assertGreaterEqual(text.count(char), 2)
            path = self.root / 'sep.jsonl'
            path.write_bytes(text.encode('utf-8'))
            result = self.run_turns(path)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0, EXPECTED.replace('graded 14 of 14', 'graded 34 of 34') + '\n',
                              ''), repr(char))
            # The same character in a human turn and in a tool result changes no class.
            touched = list(lines)
            for index, old in ((6, 'approved'), (2, 'rows for SAMPLEFIX_A7')):
                record = json.loads(touched[index])
                touched[index] = json.dumps(record, ensure_ascii=False).replace(
                    old, old[:4] + char + old[4:])
                self.assertIn(char, touched[index])
                self.assertEqual(st.classify(json.loads(touched[index])),
                                 st.classify(record))
            path.write_bytes(''.join(l + '\n' for l in touched).encode('utf-8'))
            result = self.run_turns(path)
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0, EXPECTED + '\n', ''), repr(char))
        # "\r\n" line ends: the trailing "\r" is stripped.
        path = self.root / 'crlf.jsonl'
        path.write_bytes(''.join(l + '\r\n' for l in real).encode('utf-8'))
        result = self.run_turns(path)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, EXPECTED.replace('graded 14 of 14', 'graded 34 of 34') + '\n', ''))
        print('red-on-fault guard: a record is one "\\n"-separated line, whatever its strings hold')

    def test_queued_prompt_is_a_human_turn(self):
        # Review round 1, F3 (the lane's ruling): a prompt the human types while the agent works is
        # an `attachment` record whose `attachment` is a `queued_command`. With `humanTurn` true,
        # or `commandMode` "prompt" and `isMeta` not true, it is a human turn timed by the
        # record's own (outer) timestamp; every other attachment stays harness. The three
        # combinations are the inventory's; only the last is a human turn.
        def queued(ts, inner):
            body = {'type': 'queued_command', 'prompt': 'typed while the agent works',
                    'source_uuid': 'fixture-uuid-q', 'timestamp': '2026-01-15T10:03:30Z'}
            body.update(inner)
            return {'type': 'attachment', 'timestamp': ts, 'isSidechain': False,
                    'parentUuid': 'fixture-uuid-p', 'uuid': 'fixture-uuid-a', 'attachment': body}
        self.assertEqual(sorted(INVENTORY['queued_command']['by_commandMode_isMeta_humanTurn']),
                         ['prompt|isMeta=False|humanTurn=True',
                          'prompt|isMeta=True|humanTurn=False',
                          'task-notification|isMeta=False|humanTurn=False'])
        notification = {'commandMode': 'task-notification'}
        meta_prompt = {'commandMode': 'prompt', 'isMeta': True, 'origin': {'kind': 'fixture'}}
        typed = {'commandMode': 'prompt', 'humanTurn': True, 'origin': {'kind': 'fixture'}}
        self.assertEqual([st.classify(queued('2026-01-15T10:25:00Z', c))
                          for c in (notification, meta_prompt, typed)],
                         ['harness_type', 'harness_type', 'human'])
        # `commandMode` "prompt" without `isMeta` is a human turn too; any other attachment is not.
        self.assertEqual(st.classify(queued('2026-01-15T10:25:00Z', {'commandMode': 'prompt'})),
                         'human')
        for other in ({'type': 'attachment', 'timestamp': '2026-01-15T10:25:00Z',
                       'attachment': {'type': 'edited_text_file', 'commandMode': 'prompt',
                                      'humanTurn': True}},
                      {'type': 'attachment', 'attachment': 'queued_command', 'humanTurn': True},
                      {'type': 'attachment', 'humanTurn': True, 'commandMode': 'prompt'},
                      queued('2026-01-15T10:25:00Z', {'commandMode': 'prompt', 'isMeta': True,
                                                      'humanTurn': 'yes'}),
                      queued('not a time', notification)):
            self.assertEqual(st.classify(other), 'harness_type', other)
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        # Spans 10:00-10:05, 10:09-10:11, 10:30-10:35, 10:40-10:49. A queued prompt at 10:03:30
        # is inside a span. One at 10:25:00 is outside every span (its inner timestamp says
        # 10:03:30; the outer one counts): a third outside turn, whose interval runs from the
        # 10:21:00 agent record, 4.00 minutes, so outside minutes 1.50 + 4.00.
        inside = json.dumps(queued('2026-01-15T10:03:30Z', typed))
        outside = json.dumps(queued('2026-01-15T10:25:00Z', typed))
        result = self.run_turns(self.write('q.jsonl', lines[:6] + [inside] + lines[6:10]
                                           + [outside] + lines[10:]))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, 'human turns: 8; inside spans: 5; outside spans: 3; outside minutes: '
                             '5.50; session wall minutes: 47.00; agent active minutes: 45.50; '
                             'outside window: 0; graded 16 of 16 records\n', ''))
        # The other two combinations, at the same places, move no number but `graded`.
        for combo in (notification, meta_prompt):
            records = [json.dumps(queued(ts, combo))
                       for ts in ('2026-01-15T10:03:30Z', '2026-01-15T10:25:00Z')]
            result = self.run_turns(self.write('n.jsonl', lines[:6] + records[:1] + lines[6:10]
                                               + records[1:] + lines[10:]))
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (0, EXPECTED.replace('graded 14 of 14', 'graded 16 of 16') + '\n',
                              ''), combo)
        # Like a user human turn it is main-thread: first in the file at 09:58:00 it opens the
        # window (48.00 wall minutes) and is the 09:59:00 turn's predecessor (09:58-09:59, outside
        # every span: 1.00 more outside minute); it has no predecessor itself.
        early = json.dumps(queued('2026-01-15T09:58:00Z', typed))
        result = self.run_turns(self.write('e.jsonl', [early] + lines))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, 'human turns: 7; inside spans: 4; outside spans: 3; outside minutes: '
                             '2.50; session wall minutes: 48.00; agent active minutes: 45.50; '
                             'outside window: 0; graded 15 of 15 records\n', ''))
        # Like a user human turn it needs a timestamp.
        for ts in ('not a time', None):
            bad = queued(ts, typed)
            if ts is None:
                del bad['timestamp']
            self.assertIsNone(st.classify(bad))
            result = self.run_turns(self.write('t.jsonl', lines[:3] + [json.dumps(bad)]
                                               + lines[3:]))
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (2, '', 'refused: unclassifiable record line 4\n'))
        print('red-on-fault guard: a queued prompt the human typed is a human turn; the outside '
              'one is flagged')

    def test_duplicate_type_key_exits_2(self):
        # Review round 1, F5: json.loads keeps the last of a repeated key, so a record naming two
        # types could hide a human turn. A repeated `type` key, in the record or in any object
        # inside it, is refused with its own code.
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        human = lines[8]
        self.assertTrue(human.endswith(', "type": "user"}'))
        for bad in (human[:-1] + ', "type": "system"}',
                    '{"type": "system", ' + human[1:],
                    human.replace('"role": "user"', '"role": "user", "type": "a", "type": "b"'),
                    '{"type": "attachment", "attachment": {"type": "queued_command", '
                    '"type": "date", "commandMode": "prompt", "humanTurn": true}, '
                    '"timestamp": "2026-01-15T10:25:00Z"}'):
            result = self.run_turns(self.write('d.jsonl', lines[:8] + [bad] + lines[9:]))
            self.assertEqual((result.returncode, result.stdout, result.stderr),
                             (2, '', 'refused: duplicate_type_key line 9\n'), bad)
        # Another repeated key is not this refusal: the record classifies as before.
        twice = human[:-1] + ', "sessionId": "fixture-session"}'
        result = self.run_turns(self.write('d.jsonl', lines[:8] + [twice] + lines[9:]))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, EXPECTED + '\n', ''))
        print('red-on-fault guard: a record repeating its type key exits 2')

    def test_missing_or_non_string_type_exits_2(self):
        # Ruling 0150, test (c): only a non-empty string type can be a harness record.
        good = assistant('2026-01-15T10:00:00Z')
        ts = '2026-01-15T10:01:00Z'
        for bad in ({'timestamp': ts}, {'type': None, 'timestamp': ts},
                    {'type': '', 'timestamp': ts}, {'type': 1, 'timestamp': ts},
                    {'type': True, 'timestamp': ts}, {'type': ['system'], 'timestamp': ts},
                    {'type': {'name': 'system'}, 'timestamp': ts},
                    '"system"', '["system"]', '1', 'null', 'not json', ''):
            self.assert_unclassifiable([good, bad, good], 2)
        print('red-on-fault guard: a missing, null, empty or non-string type exits 2')

    def test_session_window_ruling_l7(self):
        # Ruling L7 (b): the window runs from the first to the last main-thread record in file
        # order; a record outside it is graded and counted as `outside window`, and moves no
        # minute. The reviewer's far-future record, as a known type, leaves every number as is.
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        far = '{"type":"assistant","isSidechain":true,"timestamp":"2030-01-15T10:12:20Z"}'
        result = self.run_turns(self.write('far.jsonl', lines + [far]))
        self.assertEqual((result.returncode, result.stderr), (0, ''))
        self.assertEqual(result.stdout, EXPECTED.replace('outside window: 0', 'outside window: 1')
                         .replace('graded 14 of 14', 'graded 15 of 15') + '\n')
        # Flagged records before the start and after the end: outside, whatever their kind.
        early = json.dumps(user('2026-01-15T09:00:00Z', 'hook', meta=True))
        late = json.dumps(dict(user('2026-01-15T12:00:00Z', 'summary'), isCompactSummary=True))
        result = self.run_turns(self.write('edges.jsonl', [early] + lines + [late]))
        self.assertEqual(result.stdout, EXPECTED.replace('outside window: 0', 'outside window: 2')
                         .replace('graded 14 of 14', 'graded 16 of 16') + '\n')
        # A main-thread record between the first and the last in file order but earlier in time
        # than the first is outside the window too: never a predecessor, never wall time.
        records = [assistant('2026-01-15T10:00:00Z'), assistant('2026-01-15T09:30:00Z'),
                   user('2026-01-15T10:03:00Z', 'outside')]
        self.assertEqual(self.line(records, []),
                         'human turns: 1; inside spans: 0; outside spans: 1; outside minutes: '
                         '3.00; session wall minutes: 3.00; agent active minutes: 0.00; outside '
                         'window: 1; graded 3 of 3 records\n')
        # A start later than the end is refused.
        inverted = [assistant('2026-01-15T10:05:00Z'), user('2026-01-15T10:00:00Z', 'first')]
        result = self.run_turns(self.write('inv.jsonl', inverted))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (2, '', 'refused: session_window_inverted\n'))
        print('red-on-fault guard: a record outside the session window moves no minute')

    def test_human_turn_outside_the_window_gets_no_attention_interval(self):
        # Step B, D-vi n1 (the lane's reading of L7, confirmed): a human turn whose timestamp lies
        # outside the session window counts as a turn and as an outside span, and adds no minute.
        # Its twin inside the window gets its interval from the latest earlier record.
        outside = [assistant('2026-01-15T10:00:00Z'), user('2026-01-15T09:30:00Z', 'early'),
                   assistant('2026-01-15T10:05:00Z')]
        self.assertEqual(self.line(outside, []),
                         'human turns: 1; inside spans: 0; outside spans: 1; outside minutes: '
                         '0.00; session wall minutes: 5.00; agent active minutes: 5.00; outside '
                         'window: 1; graded 3 of 3 records\n')
        inside = [assistant('2026-01-15T10:00:00Z'), user('2026-01-15T10:03:00Z', 'late'),
                  assistant('2026-01-15T10:05:00Z')]
        self.assertEqual(self.line(inside, []),
                         'human turns: 1; inside spans: 0; outside spans: 1; outside minutes: '
                         '3.00; session wall minutes: 5.00; agent active minutes: 5.00; outside '
                         'window: 0; graded 3 of 3 records\n')

    def test_refusal_codes_do_not_depend_on_the_interpreter(self):
        # The lane's 3.13 host refused a NUL log row as `log_minutes` where 3.8 said
        # `log_malformed`: csv reads NUL as data from 3.11. A long integer in an extra key must
        # not be unclassifiable on one Python and graded on another.
        nul_log = self.root / 'nul.csv'
        nul_log.write_text(LOG_HEAD + '2026-01-15T10:00:00Z,02_02_de,human,check,other,5.00\x00\n')
        long_key = assistant('2026-01-15T10:47:00Z')
        long_key['requestId'] = '@LONG@'
        lines = (FIXTURES / 'session.jsonl').read_text().splitlines()
        transcript = self.root / 'long.jsonl'
        transcript.write_text('\n'.join(lines + [json.dumps(long_key).replace(
            '"@LONG@"', '9' * 5000)]) + '\n')
        fixture_log = str(FIXTURES / 'pilot1_log.csv')
        for argv, expected in (
                (['--transcript', str(FIXTURES / 'session.jsonl'), '--log', str(nul_log)],
                 (2, '', 'refused: log_malformed line 3\n')),
                (['--transcript', str(transcript), '--log', fixture_log],
                 (0, EXPECTED.replace('47.00', '48.00').replace('45.50', '46.50')
                  .replace('graded 14 of 14', 'graded 15 of 15') + '\n', ''))):
            seen = []
            for side in ('old', 'new'):
                with emulation.emulating(side, [st, st.ue]):
                    seen.append(emulation.outcome(st.main, argv + ['--stage', '02_02_de']))
            self.assertEqual(seen, [expected, expected])
        # A non-ASCII transcript record (never printed) reads the same under a C locale as under
        # UTF-8 (review round 3, n3).
        accented = self.root / 'accented.jsonl'
        accented.write_bytes(('\n'.join(lines).replace('Config filled.', 'Config rempli, caf\u00e9.')
                              + '\n').encode('utf-8'))
        self.assertIn(b'\xc3\xa9', accented.read_bytes())
        runs = [self.run_turns(accented, env=env) for env in (
            {'LC_ALL': 'C', 'LANG': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0'},
            {'PYTHONUTF8': '1'})]
        self.assertEqual([(r.returncode, r.stdout, r.stderr) for r in runs],
                         [(0, EXPECTED + '\n', '')] * 2)
        print('red-on-fault guard: every refusal code is the same on both sides of each '
              'Python-version split')

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
