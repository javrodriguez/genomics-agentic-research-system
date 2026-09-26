"""Row 13 step B (decisions 0140 D1, 0141): the pilot log's writer and its launch-bound actor.

Drives `_system/pilot_log.py` in-process with a patched clock (the only source of minutes), by
its CLI with and without the launch token, through the real dispatcher of a fixture workspace,
and the real `_system/guard_hook.py` with json.dumps payloads.
"""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, run  # noqa: E402
import pilot_fixture as fx  # noqa: E402
import pilot_log  # noqa: E402

WRITER = GARS / '_system/pilot_log.py'
T0 = 1789300000.0            # 2026-09-13T11:46:40Z
STATE = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory(prefix='pilot-log-')
    STATE['tmp'] = tmp
    STATE['top'] = Path(os.path.realpath(tmp.name))
    STATE['ws'] = fx.build(STATE['top'] / 'ws')


def tearDownModule():
    STATE['tmp'].cleanup()


class Clock(object):
    def __init__(self, start=T0):
        self.value = start

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def call(*argv, **kwargs):
    """(exit code, stdout) of pilot_log.main in-process, under an optional patched clock."""
    out = io.StringIO()
    clock = kwargs.get('clock')
    with contextlib.redirect_stdout(out):
        if clock is None:
            code = pilot_log.main([str(a) for a in argv])
        else:
            with patch.object(pilot_log, 'now', clock):
                code = pilot_log.main([str(a) for a in argv])
    return code, out.getvalue()


def span_of(text):
    return re.search(r'span ([0-9a-f]{16})', text).group(1)


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(dir=str(STATE['top'])))
        self.log = self.dir / 'projects/p/pilot/pilot1_log.csv'
        self.clock = Clock()

    def begin(self, stage='02_02_de', action='check', reason='other', agent=False, log=None):
        args = ['begin', '--log', log or self.log, '--stage', stage, '--action', action,
                '--reason', reason] + (['--launched-by-dispatcher'] if agent else [])
        code, out = call(*args, clock=self.clock)
        self.assertEqual(code, 0, out)
        return span_of(out)

    def end(self, span, agent=False, verb='end'):
        return call(verb, '--log', self.log, span,
                    *(['--launched-by-dispatcher'] if agent else []), clock=self.clock)

    def rows(self):
        return self.log.read_text().splitlines()[2:]

    def refusal(self, result, code):
        self.assertEqual(result, (2, 'refused: %s\n' % code))

    def test_every_verb_and_minutes_from_the_clock(self):
        print('red-on-fault: minutes from the clock', flush=True)
        span = self.begin()
        self.clock.advance(90.4)
        code, out = self.end(span)
        self.assertEqual((code, out), (0, 'end: span %s; minutes 1.51\n' % span))
        span = self.begin(stage='rerun', action='review_output', reason='rerun')
        self.clock.advance(59.7)
        code, out = self.end(span, verb='abort')
        self.assertEqual((code, out), (0, 'abort: span %s\n' % span))
        span = self.begin(stage='rerun', action='review_output', reason='rerun')
        self.clock.advance(30)
        self.assertEqual(self.end(span)[0], 0)
        self.assertEqual(self.rows(), ['2026-09-13T11:46:40Z,02_02_de,human,check,other,1.51',
                                       '2026-09-13T11:49:10Z,rerun,human,review_output,rerun,'
                                       '0.50'])
        header = self.log.read_text().splitlines()
        self.assertRegex(header[0], r'^# gars-pilot-log v1 nonce=[0-9a-f]{32}$')
        self.assertEqual(header[1], 'ts,stage,actor,action,reason_code,minutes')
        self.assertEqual(call('check', '--log', self.log),
                         (0, 'rows: 2; human: 2; agent: 0; tool: 0; open spans: 0; nonce: ok\n'))
        # Half-up once, at two decimals, from the clock's decimal readings: 0.3 s is 0.005 min.
        self.clock.value = T0 + 1000
        span = self.begin()
        self.clock.advance(0.3)
        self.assertEqual(self.end(span)[1], 'end: span %s; minutes 0.01\n' % span)

    def test_no_minutes_argument_exists(self):
        for verb in ('begin', 'end'):
            with self.subTest(verb=verb):
                code, out = call(verb, '--log', self.log, '--minutes', '5')
                self.assertEqual((code, out), (2, 'refused: usage\n'))

    def test_actor_is_the_launch_token(self):
        print('red-on-fault: actor from the token', flush=True)
        human = self.begin()
        agent = self.begin(agent=True)
        side = json.loads(Path(str(self.log) + '.open.json').read_text())
        self.assertEqual(side['spans'][human]['actor'], 'human')
        self.assertEqual(side['spans'][agent]['actor'], 'agent')
        # No input names the actor: an --actor option does not exist, with or without the token.
        for token in ([], ['--launched-by-dispatcher']):
            code, out = call('begin', '--log', self.log, '--stage', '02_02_de', '--action',
                             'check', '--reason', 'other', '--actor', 'human', *token)
            self.assertEqual((code, out), (2, 'refused: usage\n'))
        # By the CLI too.
        for token, actor in (([], 'human'), (['--launched-by-dispatcher'], 'agent')):
            result = run([sys.executable, WRITER, 'begin', '--log', self.log, '--stage',
                          '02_02_de', '--action', 'check', '--reason', 'other'] + token)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertIn('actor ' + actor, result.stdout.decode())

    def test_end_and_abort_across_actors_refused(self):
        print('red-on-fault: actor-matched end', flush=True)
        human = self.begin()
        agent = self.begin(agent=True)
        for verb in ('end', 'abort'):
            with self.subTest(verb=verb, span='human by agent'):
                self.refusal(self.end(human, agent=True, verb=verb), 'actor_mismatch')
            with self.subTest(verb=verb, span='agent by human'):
                self.refusal(self.end(agent, agent=False, verb=verb), 'actor_mismatch')
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.end(human)[0], 0)
        self.assertEqual(self.end(agent, agent=True)[0], 0)
        self.assertEqual([r.split(',')[2] for r in self.rows()], ['human', 'agent'])

    def test_status_by_operation_grid(self):
        """Each span status (open, closed, aborted) x each operation (begin, end, abort, check)."""
        print('red-on-fault: status grid', flush=True)
        expected = {
            ('open', 'begin'): 0, ('open', 'end'): 0, ('open', 'abort'): 0,
            ('open', 'check'): 1,
            ('closed', 'begin'): 0, ('closed', 'end'): 'span_closed',
            ('closed', 'abort'): 'span_closed', ('closed', 'check'): 0,
            ('aborted', 'begin'): 0, ('aborted', 'end'): 'span_aborted',
            ('aborted', 'abort'): 'span_aborted', ('aborted', 'check'): 0,
        }
        for (status, operation), outcome in sorted(expected.items()):
            with self.subTest(status=status, operation=operation):
                self.setUp()
                for stage in ('rerun', '02_02_de'):
                    other = self.begin(stage=stage, action='rerun', reason='rerun')
                    self.assertEqual(self.end(other)[0], 0)
                span = self.begin()
                if status == 'closed':
                    self.assertEqual(self.end(span)[0], 0)
                if status == 'aborted':
                    self.assertEqual(self.end(span, verb='abort')[0], 0)
                if operation == 'begin':
                    result = (0, None)
                    self.begin()
                elif operation == 'check':
                    result = call('check', '--log', self.log)
                else:
                    result = self.end(span, verb=operation)
                if isinstance(outcome, str):
                    self.refusal(result, outcome)
                else:
                    self.assertEqual(result[0], outcome, result)
        self.refusal(self.end('f' * 16), 'span_unknown')
        self.refusal(self.end('X'), 'span_malformed')

    def test_check_names_what_fails(self):
        span = self.begin()
        code, out = call('check', '--log', self.log)
        self.assertEqual((code, out), (1, 'rows: 0; human: 0; agent: 0; tool: 0; open spans: 1; '
                                          'nonce: ok\ncheck failed: open spans; no rows: '
                                          '02_02_de; no rows: rerun\n'))
        self.end(span)
        self.assertEqual(call('check', '--log', self.log)[0], 1)   # no rerun row yet

    def test_refusals(self):
        print('red-on-fault: nonce and shape refusals', flush=True)
        span = self.begin()
        self.clock.advance(60)
        self.end(span)
        good = self.log.read_bytes()
        side_path = Path(str(self.log) + '.open.json')
        side_good = side_path.read_bytes()
        lines = good.decode().splitlines()
        variants = {
            'extra column': (lines[:2] + [lines[2] + ',a sample name'], 'log_malformed line 3'),
            'out-of-vocabulary stage': (lines[:2] + [lines[2].replace('02_02_de', '02_03_x')],
                                        'log_malformed line 3'),
            'out-of-vocabulary actor': (lines[:2] + [lines[2].replace('human', 'owner')],
                                        'log_malformed line 3'),
            'typed minutes': (lines[:2] + [lines[2].replace('1.00', '1')],
                              'log_malformed line 3'),
            'nonce missing': (['# gars-pilot-log v1'] + lines[1:], 'nonce_missing'),
            'nonce unequal': (['# gars-pilot-log v1 nonce=' + 'a' * 32] + lines[1:],
                              'nonce_mismatch'),
            'header changed': (lines[:1] + ['ts,stage,actor,action,reason_code,minutes,note']
                               + lines[2:], 'log_malformed line 2'),
        }
        for name, (text, code) in variants.items():
            with self.subTest(variant=name):
                self.log.write_text('\n'.join(text) + '\n')
                for verb in ('check', 'begin'):
                    if verb == 'check':
                        self.refusal(call('check', '--log', self.log), code)
                    else:
                        self.refusal(call('begin', '--log', self.log, '--stage', '02_02_de',
                                          '--action', 'check', '--reason', 'other'), code)
                self.log.write_bytes(good)
        side = json.loads(side_good.decode())
        side['nonce'] = 'b' * 32
        side_path.write_text(json.dumps(side))
        self.refusal(call('check', '--log', self.log), 'nonce_mismatch')
        del side['nonce']
        side_path.write_text(json.dumps(side))
        self.refusal(call('check', '--log', self.log), 'sidecar_malformed')
        side_path.write_bytes(side_good)
        self.assertEqual(call('check', '--log', self.log)[0], 1)
        # Out-of-vocabulary values are refused before anything is written.
        for key, value in (('--stage', '03_x'), ('--action', 'typing'), ('--reason', 'cost')):
            args = dict([('--stage', '02_02_de'), ('--action', 'check'), ('--reason', 'other')])
            args[key] = value
            with self.subTest(key=key):
                result = call('begin', '--log', self.log, *[w for kv in args.items() for w in kv])
                self.assertEqual(result[0], 2)
                self.assertNotIn(value, result[1])
        self.assertEqual(self.log.read_bytes(), good)

    def test_pre_created_by_hand_refused(self):
        print('red-on-fault: pre-created log', flush=True)
        self.log.parent.mkdir(parents=True)
        self.log.write_text('# gars-pilot-log v1 nonce=%s\nts,stage,actor,action,reason_code,'
                            'minutes\n' % ('c' * 32))
        self.refusal(call('begin', '--log', self.log, '--stage', '02_02_de', '--action', 'check',
                          '--reason', 'other'), 'sidecar_missing')
        self.refusal(call('check', '--log', self.log), 'sidecar_missing')
        self.log.unlink()
        side = Path(str(self.log) + '.open.json')
        side.write_text(json.dumps({'format': 'gars-pilot-log v1', 'nonce': 'c' * 32,
                                    'spans': {}, 'imported': []}))
        self.refusal(call('begin', '--log', self.log, '--stage', '02_02_de', '--action', 'check',
                          '--reason', 'other'), 'log_missing')
        self.assertFalse(self.log.exists())

    def test_cold_start_twin(self):
        """The first-ever log (no pilot/ folder) beside an append to an existing log."""
        print('red-on-fault: cold start', flush=True)
        self.assertFalse(self.log.parent.exists())
        self.refusal(call('check', '--log', self.log), 'log_missing')
        self.assertFalse(self.log.parent.exists())
        first = self.begin()
        self.assertTrue(self.log.is_file())
        nonce = self.log.read_text().splitlines()[0]
        self.clock.advance(120)
        self.end(first)
        second = self.begin(stage='rerun', action='rerun', reason='rerun')
        self.clock.advance(60)
        self.end(second)
        text = self.log.read_text().splitlines()
        self.assertEqual(text[0], nonce)
        self.assertEqual([r.split(',')[-1] for r in text[2:]], ['2.00', '1.00'])
        self.assertEqual(call('check', '--log', self.log)[0], 0)

    def test_import_tool(self):
        print('red-on-fault: import-tool', flush=True)
        project = self.dir / 'projects/p'
        stage = project / 'x/rnaseq_bulk/02_rnaseq-de'
        (stage / 'reproducibility').mkdir(parents=True)
        (project / '_config').mkdir()
        key = 'ab' * 32
        manifest = stage / 'reproducibility/manifest.json'
        manifest.write_text(json.dumps({'wrapper': 'rnaseq-de', 'idempotency_key': key,
                                        'resources': {'Elapsed': '01:02:03', 'MaxRSS': '1K',
                                                      'AllocCPUS': '1'}}))
        (project / '.gars_submissions').mkdir()
        (project / '.gars_submissions' / (key + '.json')).write_text(json.dumps(
            {'executor': 'slurm', 'job_id': '100', 'submitted_at': T0,
             'started_at': T0 + 150}))
        self.begin()
        self.refusal(call('import-tool', '--log', self.log, '--manifest', manifest,
                          '--launched-by-dispatcher'), 'human_only')
        code, out = call('import-tool', '--log', self.log, '--manifest', manifest)
        self.assertEqual((code, out), (0, 'import-tool: rows 2; wait_queue 2.50; compute '
                                          '62.05\n'))
        self.assertEqual(self.rows(), ['2026-09-13T11:46:40Z,02_02_de,tool,wait_queue,other,2.50',
                                       '2026-09-13T11:49:10Z,02_02_de,tool,compute,other,62.05'])
        self.refusal(call('import-tool', '--log', self.log, '--manifest', manifest),
                     'already_imported')
        self.assertEqual(len(self.rows()), 2)

    def test_vocabulary_drift(self):
        vocab = json.loads((REPO / 'docs/pilot/pilot_log_vocabulary.json').read_text())
        self.assertEqual(pilot_log.COLUMNS, vocab['columns'])
        for key in ('stage', 'actor', 'action', 'reason_code'):
            self.assertEqual(pilot_log.VOCABULARY[key], vocab[key])
        self.assertEqual(pilot_log.HEADER.pattern.replace('(', '').replace(')', ''),
                         vocab['header_comment_regex'])
        self.assertEqual(pilot_log.TS.pattern, vocab['ts_regex'])
        self.assertEqual(pilot_log.MINUTES.pattern, vocab['minutes_regex'])
        registry = json.loads((GARS / '_system/tools/registry.json').read_text())['tools']
        entries = [t for t in registry if t['name'].startswith('pilot_log.')]
        self.assertEqual(sorted(t['name'] for t in entries),
                         ['pilot_log.abort', 'pilot_log.begin', 'pilot_log.check',
                          'pilot_log.end'])
        for tool in entries:
            with self.subTest(tool=tool['name']):
                self.assertEqual(tool['argv'][3:], ['--launched-by-dispatcher'])
                text = json.dumps([tool['input_schema'], tool['cli']])
                self.assertNotIn('launched', text)
                self.assertFalse(tool['input_schema']['additionalProperties'])
                self.assertEqual(tool['roles'], {'human': 'allow', 'producer': 'allow',
                                                 'reviewer': 'refuse'})
            if tool['name'] == 'pilot_log.begin':
                props = tool['input_schema']['properties']
                self.assertEqual(props['stage']['enum'], vocab['stage'])
                self.assertEqual(props['action']['enum'], vocab['action'])
                self.assertEqual(props['reason']['enum'], vocab['reason_code'])

    def test_python36_syntax(self):
        if sys.version_info < (3, 8):
            self.skipTest('ast feature_version needs Python 3.8')
        import ast
        for path in (WRITER, GARS / '_system/tools/closed_output.py'):
            ast.parse(path.read_text(), feature_version=(3, 6))


class DispatcherAndGuardTests(unittest.TestCase):
    def test_through_the_dispatcher_the_actor_is_agent(self):
        print('red-on-fault: dispatcher actor', flush=True)
        ws = STATE['ws']
        log = 'projects/open1/pilot/pilot1_log.csv'
        begin = {'log': log, 'stage': '02_02_de', 'action': 'submit', 'reason': 'other'}
        code, record, raw = fx.tool_call(ws, 'pilot_log.begin', begin)
        self.assertEqual(code, 0, raw)
        self.assertIn('actor agent', record['stdout'])
        agent = span_of(record['stdout'])
        human = run([sys.executable, ws / '_system/pilot_log.py', 'begin', '--log', log,
                     '--stage', '02_02_de', '--action', 'review_output', '--reason',
                     'approval'], cwd=ws)
        self.assertIn(b'actor human', human.stdout)
        human = span_of(human.stdout.decode())
        for verb in ('end', 'abort'):
            code, record, raw = fx.tool_call(ws, 'pilot_log.' + verb, {'log': log, 'span': human})
            self.assertEqual((code, record['stdout']), (2, 'refused: actor_mismatch\n'))
        # The JSON can neither supply nor remove the token.
        for extra in ({'launched-by-dispatcher': True}, {'actor': 'human'},
                      {'minutes': '5.00'}):
            code, record, raw = fx.tool_call(ws, 'pilot_log.begin', dict(begin, **extra))
            self.assertEqual((code, record['type']), (2, 'tool_refusal'), raw)
        code, record, raw = fx.tool_call(ws, 'pilot_log.end', {'log': log, 'span': agent})
        self.assertEqual(code, 0, raw)
        rows = (ws / log).read_text().splitlines()[2:]
        self.assertEqual([r.split(',')[2:4] for r in rows], [['agent', 'submit']])
        # A log path outside projects/<p>/pilot/ is refused by the schema.
        for path in ('pilot1_log.csv', 'projects/open1/pilot1_log.csv',
                     'projects/../pilot/pilot1_log.csv', str(ws / log)):
            code, record, raw = fx.tool_call(ws, 'pilot_log.check', {'log': path})
            self.assertEqual((code, record['type']), (2, 'tool_refusal'), path)

    def test_guard_refuses_writes_and_the_direct_spelling(self):
        print('red-on-fault: machine-owned pilot folder', flush=True)
        ws = STATE['ws']
        refusals = []
        for project in ('open1', 'pilot'):
            target = 'projects/%s/pilot/pilot1_log.csv' % project
            for tool in ('Write', 'Edit', 'MultiEdit'):
                refusals.append((tool, {'file_path': target, 'content': 'x', 'old_string': 'a',
                                        'new_string': 'b'}))
                refusals.append((tool, {'file_path': target + '.open.json', 'content': '{}'}))
            refusals.append(('NotebookEdit', {'notebook_path': target, 'new_source': 'x'}))
            for command in ('echo x > %s', 'echo x >> %s', 'tee %s', 'tee -a %s',
                            'cp /dev/null %s'):
                refusals.append(('Bash', {'command': command % target}))
            refusals.append(('Bash', {'command': 'python3 _system/pilot_log.py begin '
                                                 '--launched-by-dispatcher --log %s --stage '
                                                 '02_02_de --action check --reason other'
                                                 % target}))
            refusals.append(('Bash', {'command': 'python3 _system/pilot_log.py check --log %s'
                                                 % target}))
        for tool, data in refusals:
            with self.subTest(tool=tool, data=data):
                result = fx.hook_call(ws, tool, data)
                self.assertEqual(result.returncode, 2, result.stderr)
        # The READ_ONLY line refuses Write on a public project's pilot folder by itself.
        result = fx.hook_call(ws, 'Write', {'file_path': 'projects/open1/pilot/x.csv',
                                            'content': 'x'})
        self.assertIn(b'part of the GARS template', result.stderr)
        # Addition 3 names itself on the one direct spelling that parses.
        result = fx.hook_call(ws, 'Bash', {'command': 'python3 _system/pilot_log.py begin '
                                                      '--launched-by-dispatcher --log projects/'
                                                      'open1/pilot/pilot1_log.csv --stage '
                                                      '02_02_de --action check --reason other'})
        self.assertIn(b"pilot log's writer", result.stderr)
        # The dispatcher spelling stays open, on a public and a closed project.
        for project in ('open1', 'pilot'):
            data = {'command': fx.dispatch('pilot_log.check', {
                'log': 'projects/%s/pilot/pilot1_log.csv' % project})}
            self.assertEqual(fx.hook_call(ws, 'Bash', data).returncode, 0)
        print('EXIT pilot log (fixture): launch-bound actor', flush=True)

    def test_writer_is_outside_the_guard_and_settings_agree(self):
        import guard_hook
        self.assertIn('projects/*/pilot/*', guard_hook.READ_ONLY)
        settings = json.loads((GARS / '.claude/settings.json').read_text())
        deny = settings['permissions']['deny']
        for tool in ('Edit', 'Write'):
            self.assertIn('%s(projects/*/pilot/*)' % tool, deny)


if __name__ == '__main__':
    unittest.main(verbosity=2)
