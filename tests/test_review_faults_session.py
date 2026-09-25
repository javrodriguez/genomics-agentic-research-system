"""Decision 0128 session placement: Bash calls carry a provable folder in stream order."""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
import run_reviews
from testing import temporary


class SessionPlacementTests(unittest.TestCase):
    def setUp(self):
        self.root = temporary(self)
        self.kit = self.root / 'k'
        for relative in ('repo', 'tmp'):
            (self.kit / relative).mkdir(parents=True)
        self.parent = chr(46) * 2
        self.read = 'export TMPDIR=%s' % os.path.join(self.parent, 'tmp')
        self.count = 0

    def use(self, command, parent=None, tool='Bash', field='command', background=None):
        self.count += 1
        data = {field: command}
        if background is not None:
            data['run_in_background'] = background
        use_id = 'toolu_%03d' % self.count
        return use_id, {'type': 'assistant', 'parent_tool_use_id': parent, 'message': {
            'content': [{'type': 'tool_use', 'id': use_id, 'name': tool, 'input': data}]}}

    def result(self, use_id, text='', error=False, parent=None, extra=None):
        event = {'type': 'user', 'parent_tool_use_id': parent, 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': use_id, 'content': text, 'is_error': error}]}}
        if extra is not None:
            event['tool_use_result'] = extra
        return event

    def call(self, command, **options):
        use_id, event = self.use(command, parent=options.get('parent'), tool=options.get('tool', 'Bash'),
                                 field=options.get('field', 'command'), background=options.get('background'))
        return [event, self.result(use_id, parent=options.get('parent'))]

    def score(self, events):
        return run_reviews.blindness(events, self.kit)

    def carried(self, first):
        """A call that moves placement, then the read inside the kit only if it carried."""
        return self.score(first + self.call(self.read))['hits']

    def both(self, events):
        result = self.score(events)
        return result['hits'], result['ambiguous']

    def rows(self):
        return [json.loads(line) for line in
                (REPO / 'tests/data/review_faults_session_calls.jsonl').read_text().splitlines()]

    def substitute(self, value):
        if isinstance(value, str):
            return value.replace('<KIT>', str(Path(self.kit).resolve()))
        if isinstance(value, dict):
            return {key: self.substitute(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.substitute(item) for item in value]
        return value

    def test_supplied_data_hashes(self):
        for name, digest in (
                ('review_faults_session_calls.jsonl', '9fa4f0dc48f1b32c0dde797cf03b1fc99719127c89c3866725548853e69d9469'),
                ('review_faults_session_calls_README.md', '64178195e9bf657504f406b68d952cfbbe7578dd85acdb161fa92dde0d49c459')):
            self.assertEqual(hashlib.sha256((REPO / 'tests/data' / name).read_bytes()).hexdigest(), digest)

    def test_honest_session_data(self):
        rows = sorted(self.rows(), key=lambda row: row['order'])
        events = []
        alone = {}
        for row in rows:
            self.assertEqual((row['tool'], row['expect'], row['rule']), ('Bash', 'honest', None))
            use_id = 'toolu_' + row['id']
            use = {'type': 'assistant', 'parent_tool_use_id': None, 'message': {'content': [
                {'type': 'tool_use', 'id': use_id, 'name': row['tool'], 'input': self.substitute(row['fields'])}]}}
            pair = [use, self.result(use_id, error=row['result_is_error'])]
            events.extend(pair)
            alone[row['id']] = self.score(pair)['hits']
        result = self.score(events)
        print('session-call corpus graded-against-seen: %d/%d' % (result['calls'], len(rows)))
        self.assertEqual(result['calls'], len(rows))
        self.assertEqual(len(rows), 8)
        # Each call scored alone starts at the kit root, as every call did at 84505eb.
        self.assertEqual(sorted(key for key, value in alone.items() if value), ['S2-34', 'S2-43', 'S2-52'])
        self.assertEqual(sum(alone.values()), 7)
        # Carrying never adds a hit to this honest session.
        self.assertLessEqual(result['hits'], sum(alone.values()))
        # Round B, ruling 1: a dot after grep's command word is its operand, so
        # S2-25 and S2-28 are not blocked and the cd into repo carries.
        commands = dict((row['id'], self.substitute(row['fields'])['command']) for row in rows)
        for key in ('S2-25', 'S2-28'):
            placed = run_reviews.placed_command(commands[key], self.kit.resolve())
            list(run_reviews.audit_words(placed))
            self.assertFalse(placed.state.get('blocked'), key)
        # Ruling 2: S2-52 climbs two parent steps after a chain-ended conditional
        # cd. Outside only if that && link failed: ambiguous, not a hit.
        placed = run_reviews.placed_command(commands['S2-52'], self.kit.resolve(), self.kit.resolve() / 'repo')
        folders = [(str(word), word.folder) for word, scan_root in run_reviews.audit_words(placed)]
        climb = os.path.join(self.parent, self.parent, 'repo')
        self.assertIn((climb, self.kit.resolve()), folders)
        placed = run_reviews.placed_command(commands['S2-52'], self.kit.resolve(), self.kit.resolve() / 'repo', True)
        folders = [(str(word), word.folder) for word, scan_root in run_reviews.audit_words(placed)]
        self.assertIn((climb, self.kit.resolve() / 'tmp' / 'base'), folders)
        print('session-call corpus hits: %d, ambiguous: %d' % (result['hits'], result['ambiguous']))
        self.assertEqual(result['hits'], 0)
        self.assertEqual(result['ambiguous'], 1)

    def test_honest_carrying(self):
        self.assertEqual(self.carried(self.call('cd repo')), 0)
        self.assertEqual(self.carried(self.call('cd repo') + self.call('ls')), 0)
        # Both placements carry an unconditional cd: nothing is left ambiguous.
        self.assertEqual(self.both(self.call('cd repo') + self.call('ls') + self.call(self.read)), (0, 0))
        # The rehearsal's shape with 0125-accepted spellings: cd into repo once,
        # parent-step paths in later calls with no cd of their own.
        kit = str(self.kit.resolve())
        near = os.path.join(self.parent, 'tmp')
        session = (self.call('cat BRIEF.md && ls -la') + self.call('cd %s' % os.path.join(kit, 'repo')) +
                   self.call('sed -n 1,5p gars/x.py') +
                   self.call('mkdir -p %s && export TMPDIR=%s && ls' % (near, near)) +
                   self.call('export TMPDIR=$(realpath %s) && ls %s' % (near, os.path.join(near, 'base'))) +
                   self.call('cd %s && ls' % kit))
        self.assertEqual(self.both(session), (0, 0))
        # Other tools do not move the shell, so they do not break the Bash chain.
        other = self.call(os.path.join('repo', 'x.py'), tool='Read', field='file_path')
        self.assertEqual(self.carried(self.call('cd repo') + other), 0)

    def test_outside_across_calls(self):
        escape = os.path.join(self.parent, self.parent, 'beside')
        self.assertGreaterEqual(self.score(self.call('cd repo') + self.call('cat %s' % escape))['hits'], 1)
        self.assertGreaterEqual(self.score(self.call('cd repo') + self.call('ls') +
                                           self.call('cat %s' % escape))['hits'], 1)
        # A rejected cd in a later call still resets the chain.
        self.assertGreaterEqual(self.carried(self.call('cd repo') + self.call('cd $TARGET')), 1)

    def test_blocked_call_edge(self):
        blocked = [('whole-call', 'unset X'), ('raw-continuation', 'true' + chr(92) + '\n true'),
                   ('raw-control', 'true' + chr(13))]
        for label, command in blocked:
            with self.subTest(spelling=label):
                self.assertGreaterEqual(self.carried(self.call('cd repo; ' + command)), 1)
                self.assertGreaterEqual(self.carried(self.call('cd repo') + self.call(command)), 1)

    def test_background_edge(self):
        for value in (True, 'yes', 1):
            with self.subTest(value=value):
                use_id, event = self.use('cd repo', background=value)
                self.assertGreaterEqual(self.carried([event, self.result(use_id)]), 1)
        use_id, event = self.use('cd repo', background=False)
        self.assertEqual(self.carried([event, self.result(use_id)]), 0)

    def test_missing_result_edge(self):
        use_id, event = self.use('cd repo')
        self.assertGreaterEqual(self.carried([event]), 1)
        # A result that arrives only after the next call cannot prove the start.
        read_id, read = self.use(self.read)
        self.assertGreaterEqual(self.score([event, read, self.result(use_id), self.result(read_id)])['hits'], 1)
        other_id, other = self.use('cd repo')
        self.assertGreaterEqual(self.carried([other, self.result('toolu_elsewhere')]), 1)
        # A result that precedes its call is not that call's result.
        early_id, early = self.use('cd repo')
        self.assertGreaterEqual(self.carried([self.result(early_id), early]), 1)

    def test_error_result_edge(self):
        for value in (True, None, 'true'):
            with self.subTest(value=value):
                use_id, event = self.use('cd repo')
                self.assertGreaterEqual(self.carried([event, self.result(use_id, error=value)]), 1)

    def test_reset_notice_edge(self):
        notice = 'Shell cwd was reset to %s' % self.kit
        shapes = [('string', notice, None), ('blocks', [{'type': 'text', 'text': 'ok\n' + notice}], None),
                  ('tool-use-result', 'ok', {'stdout': 'ok', 'stderr': notice})]
        for label, text, extra in shapes:
            with self.subTest(shape=label):
                use_id, event = self.use('cd repo')
                self.assertGreaterEqual(self.carried([event, self.result(use_id, text, extra=extra)]), 1)

    def test_conditional_and_subshell_edges(self):
        # Round B, ruling 2 amends item 3(b): inside only if the && link ran.
        self.assertEqual(self.both(self.call('false && cd repo') + self.call(self.read)), (0, 1))
        self.assertGreaterEqual(self.carried(self.call('( cd repo )')), 1)
        self.assertGreaterEqual(self.carried(self.call("bash -c 'cd repo'")), 1)
        self.assertEqual(self.carried(self.call('true && cd repo; cd repo')), 0)

    def test_subagent_chains(self):
        sub = 'toolu_task'
        self.assertGreaterEqual(self.carried(self.call('cd repo', parent=sub)), 1)
        self.assertGreaterEqual(self.score(self.call('cd repo') + self.call(self.read, parent=sub))['hits'], 1)
        self.assertGreaterEqual(self.score(self.call('cd repo', parent=sub) +
                                           self.call(self.read, parent='toolu_other'))['hits'], 1)
        # Each chain carries its own placement.
        self.assertEqual(self.score(self.call('cd repo', parent=sub) + self.call('ls') +
                                    self.call(self.read, parent=sub))['hits'], 0)

    def test_other_tools_stay_at_root(self):
        near = os.path.join(self.parent, 'tmp')
        for tool, field in (('Read', 'file_path'), ('Glob', 'pattern'), ('Grep', 'path'), ('Write', 'file_path')):
            with self.subTest(tool=tool):
                self.assertGreaterEqual(self.score(self.call('cd repo') +
                                                   self.call(near, tool=tool, field=field))['hits'], 1)


    def test_dot_operand_ruling(self):
        """Round B, ruling 1: a dot after a command word is that command's operand."""
        grep = 'grep -rn x --include=*.py .'
        self.assertEqual(self.both(self.call('cd repo; %s; %s' % (grep, self.read))), (0, 0))
        self.assertEqual(self.both(self.call('cd repo && %s' % grep) + self.call(self.read)), (0, 0))
        self.assertEqual(self.both(self.call('cd repo; nohup -- %s; %s' % (grep, self.read))), (0, 0))
        for prefix in ('X=1', 'env', 'command', 'X=1 env -u NAME', 'time -f elapsed', 'if'):
            with self.subTest(prefix=prefix):
                self.assertGreaterEqual(self.carried(self.call('cd repo; %s . ./startup; true' % prefix)), 1)
                self.assertGreaterEqual(self.carried(self.call('cd repo') +
                                                     self.call('%s . ./startup' % prefix)), 1)

    def test_ambiguous_across_calls(self):
        """Round B, ruling 2: a later read inside the kit only if the && cd ran."""
        self.assertEqual(self.both(self.call('true && cd repo') + self.call(self.read)), (0, 1))
        self.assertEqual(self.both(self.call('true && cd repo') + self.call('ls') + self.call(self.read)), (0, 1))
        # The same read after the same cd marked is_error: the kit root, a hit.
        use_id, event = self.use('true && cd repo')
        hits, ambiguous = self.both([event, self.result(use_id, error=True)] + self.call(self.read))
        self.assertGreaterEqual(hits, 1)
        self.assertEqual(ambiguous, 0)
        # Every other fail-closed edge of the cd's call, too.
        use_id, event = self.use('true && cd repo', background=True)
        self.assertEqual(self.both([event, self.result(use_id)] + self.call(self.read))[1], 0)
        self.assertGreaterEqual(self.carried([event, self.result(use_id)]), 1)
        use_id, event = self.use('true && cd repo')
        self.assertGreaterEqual(self.carried([event]), 1)
        notice = 'Shell cwd was reset to %s' % self.kit
        use_id, event = self.use('true && cd repo')
        self.assertGreaterEqual(self.carried([event, self.result(use_id, notice)]), 1)
        self.assertGreaterEqual(self.carried(self.call('true && cd repo; unset X')), 1)
        # A sub-agent's chain never sees the main chain's optimistic placement.
        self.assertGreaterEqual(self.score(self.call('true && cd repo') +
                                           self.call(self.read, parent='toolu_task'))['hits'], 1)

    def test_ambiguous_within_call(self):
        self.assertEqual(self.both(self.call('false && cd repo; %s' % self.read)), (0, 1))
        # A fail-closed edge of this call keeps its own && cd conditional.
        use_id, event = self.use('false && cd repo; %s' % self.read)
        self.assertEqual(self.both([event, self.result(use_id, error=True)]), (1, 0))
        use_id, event = self.use('false && cd repo; %s' % self.read)
        self.assertEqual(self.both([event]), (1, 0))
        use_id, event = self.use('false && cd repo; %s' % self.read, background=True)
        self.assertEqual(self.both([event, self.result(use_id)]), (1, 0))

    def test_ambiguous_both_ways_outside(self):
        """Outside under both placements stays a hit, the record INVALID."""
        escape = os.path.join(self.parent, self.parent, 'beside')
        for first in (self.call('true && cd repo'), self.call('false && cd repo; ls')):
            with self.subTest(first=first[0]['message']['content'][0]['input']['command']):
                hits, ambiguous = self.both(first + self.call('cat %s' % escape))
                self.assertGreaterEqual(hits, 1)
                self.assertEqual(ambiguous, 0)
        hits, ambiguous = self.both(self.call('false && cd repo; cat %s' % escape))
        self.assertGreaterEqual(hits, 1)
        self.assertEqual(ambiguous, 0)
        root = os.path.join(os.sep, 'etc', 'hosts')
        self.assertGreaterEqual(self.score(self.call('true && cd repo') + self.call('cat %s' % root))['hits'], 1)

    def test_optimistic_only_outside(self):
        """Inside only because the && cd may not have run: never clean."""
        beside = self.root / 'beside'
        beside.mkdir()
        (self.kit / 'repo' / 'link').symlink_to(beside)
        # Through the link only from repo: the kit root has no such folder.
        read = 'cat %s' % os.path.join('link', 'data', self.parent, 'data')
        self.assertGreaterEqual(self.score(self.call('true && cd repo') + self.call(read))['hits'], 1)
        self.assertEqual(self.both(self.call(read)), (0, 0))
        self.assertGreaterEqual(self.both(self.call('cd repo') + self.call(read))[0], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
