"""Decision 0129: a Bash call blocked only by retained data keeps its carried placement."""
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


class HeredocPlacementTests(unittest.TestCase):
    # The module under test. The fault list swaps in an in-memory patched copy.
    harness = run_reviews

    def setUp(self):
        self.root = temporary(self)
        self.kit = self.root / 'k'
        for relative in ('repo', 'tmp', os.path.join('repo', 'tmp', 'prev')):
            (self.kit / relative).mkdir(parents=True)
        self.parent = chr(46) * 2
        self.near = os.path.join(self.parent, 'tmp')
        self.read = 'export TMPDIR=%s' % self.near
        self.outside = os.path.join(self.parent, 'x')
        self.climb = os.path.join(self.parent, self.parent, 'x')
        self.count = 0

    def heredoc(self, command):
        return "%s <<'EOF'\nbody line\nEOF" % command

    def use(self, command):
        self.count += 1
        use_id = 'toolu_%03d' % self.count
        return use_id, {'type': 'assistant', 'parent_tool_use_id': None, 'message': {
            'content': [{'type': 'tool_use', 'id': use_id, 'name': 'Bash', 'input': {'command': command}}]}}

    def result(self, use_id, error=False):
        return {'type': 'user', 'parent_tool_use_id': None, 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': use_id, 'content': '', 'is_error': error}]}}

    def call(self, command, error=False):
        use_id, event = self.use(command)
        return [event, self.result(use_id, error)]

    def score(self, events):
        return self.harness.blindness(events, self.kit)

    def both(self, events):
        result = self.score(events)
        return result['hits'], result['ambiguous']

    def status(self, command):
        """Accessor for the preflight's verdict on one call, independent of its start."""
        placed = self.harness.placed_command(command, self.kit.resolve())
        list(self.harness.audit_words(placed))
        if not placed.state.get('blocked'):
            return 'unblocked'
        return 'blocked' if placed.state.get('moving') else 'data-only'

    def in_call(self, command):
        """After a first call into repo whose result arrived, the call's own hits."""
        return self.score(self.call('cd repo') + self.call(command))['hits']

    def next_call(self, first, read, error=False):
        """The next call's own hit: adding it raises the stream's hits by at least 1."""
        lead = self.call('cd repo') + self.call(first, error)
        before = self.score(lead)['hits']
        after = self.score(lead + self.call(read))['hits']
        self.assertGreaterEqual(after, before + 1, first)

    def rows(self):
        return [json.loads(line) for line in
                (REPO / 'tests/data/review_faults_heredoc_calls.jsonl').read_text().splitlines()]

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
                ('review_faults_heredoc_calls.jsonl', 'd77ad25273262e3ca1396153d8e3df284061548770e46d9e1e048e485a35d180'),
                ('review_faults_heredoc_calls_README.md', '98a4f14e4f11ade1303864b2decb1e7c49db745cd7978a6fc979d716d064f187')):
            self.assertEqual(hashlib.sha256((REPO / 'tests/data' / name).read_bytes()).hexdigest(), digest)

    def test_honest_heredoc_sessions(self):
        rows = self.rows()
        self.assertEqual(len(rows), 17)
        expected = {'C01': (7, 0, 0), 'C02': (10, 0, 2)}
        self.assertEqual(sorted(set(row['session'] for row in rows)), sorted(expected))
        for session, (count, hits, ambiguous) in sorted(expected.items()):
            own = sorted((row for row in rows if row['session'] == session), key=lambda row: row['order'])
            self.assertEqual([row['order'] for row in own], list(range(1, count + 1)))
            events = []
            for row in own:
                self.assertEqual((row['tool'], row['expect'], row['rule']), ('Bash', 'honest', None))
                use_id = 'toolu_' + row['id']
                fields = self.substitute(row['fields'])
                events.append({'type': 'assistant', 'parent_tool_use_id': None, 'message': {'content': [
                    {'type': 'tool_use', 'id': use_id, 'name': row['tool'], 'input': fields}]}})
                events.append(self.result(use_id, row['result_is_error']))
                # Each session's last call is blocked only by its heredoc.
                verdict = 'data-only' if row['order'] == count else 'unblocked'
                self.assertEqual(self.status(fields['command']), verdict, row['id'])
            result = self.score(events)
            print('heredoc-call corpus %s graded-against-seen: %d/%d' % (session, result['calls'], len(own)))
            print('heredoc-call corpus %s hits: %d, ambiguous: %d' % (session, result['hits'], result['ambiguous']))
            with self.subTest(session=session):
                self.assertEqual(result['calls'], len(own))
                self.assertEqual((result['hits'], result['ambiguous']), (hits, ambiguous))

    def test_honest_data_only_carry(self):
        write = self.heredoc('cat > %s' % os.path.join(self.near, 'review.json'))
        self.assertEqual(self.status(write), 'data-only')
        self.assertEqual(self.both(self.call('cd repo') + self.call(write) + self.call(self.read)), (0, 0))
        self.assertEqual(self.both(self.call('cd repo') + self.call(self.heredoc('cat')) + self.call(self.read)), (0, 0))

    def test_block_causes(self):
        eval_cd = 'eval "cd %s"' % self.parent
        causes = [('heredoc', self.heredoc('cat'), 'data-only'),
                  ('here-string', 'cat <<< text', 'data-only'),
                  ('kept-comment', 'true # note $(date)', 'data-only'),
                  ('nested-heredoc', "bash -c %s" % "'cat <<EOF\nbody\nEOF\n'", 'data-only'),
                  ('eval', eval_cd, 'blocked'),
                  ('pushd', 'pushd %s' % self.parent, 'blocked'),
                  ('heredoc-and-eval', self.heredoc('%s; cat' % eval_cd), 'blocked'),
                  ('heredoc-and-unset', self.heredoc('unset X; cat'), 'blocked'),
                  ('heredoc-and-nested-eval', self.heredoc("bash -c 'eval true'; cat"), 'blocked'),
                  ('heredoc-and-raw-control', self.heredoc('cat' + chr(13)), 'blocked'),
                  ('plain', 'cat x', 'unblocked')]
        # The calls the outside-direction tests below use, by the same verdict.
        causes += [('refused-cd', self.heredoc('cd %s; cat %s' % (self.parent, self.outside)), 'data-only'),
                   ('climb', self.heredoc('cat %s' % self.climb), 'data-only'),
                   ('comment-climb', 'cat %s # note $(date)' % self.climb, 'data-only'),
                   ('eval-read', '%s; cat %s' % (eval_cd, self.outside), 'blocked'),
                   ('pushd-read', 'pushd %s; cat %s' % (self.parent, self.outside), 'blocked')]
        for label, command, verdict in causes:
            with self.subTest(cause=label):
                self.assertEqual(self.status(command), verdict)

    def test_refused_cd_in_call(self):
        # Escape (1): the shell went up one level before the read.
        command = self.heredoc('cd %s; cat %s' % (self.parent, self.outside))
        self.assertGreaterEqual(self.in_call(command), 1)

    def test_cd_word_in_data_only_call(self):
        # A cd word in kept heredoc text is refused too: its operand is judged
        # from the carried folder, and the words after it at the kit root.
        kit = self.kit.resolve()
        kept = ': $(true); cat <<EOF\ncd tmp\nEOF\ncat %s' % self.near
        self.assertEqual(self.status(kept), 'data-only')
        placed = self.harness.placed_command(kept, kit, kit / 'repo')
        folders = [(str(word), word.folder) for word, scan_root in self.harness.audit_words(placed)]
        self.assertIn(('tmp', kit / 'repo'), folders)
        self.assertIn((self.near, kit), folders)
        self.assertEqual(placed.state['folder'], kit)

    def test_refused_cd_next_call(self):
        self.next_call(self.heredoc('cd %s; cat' % self.parent), 'cat %s' % self.outside)

    def test_shell_moving_in_call(self):
        # Escape (2): these blocks can move the shell where the audit cannot see.
        eval_cd = 'eval "cd %s"' % self.parent
        for label, command in (('eval', '%s; cat %s' % (eval_cd, self.outside)),
                               ('pushd', 'pushd %s; cat %s' % (self.parent, self.outside)),
                               ('heredoc-and-eval', self.heredoc('%s; cat %s' % (eval_cd, self.outside)))):
            with self.subTest(block=label):
                self.assertGreaterEqual(self.in_call(command), 1)

    def test_shell_moving_next_call(self):
        eval_cd = 'eval "cd %s"' % self.parent
        for label, command in (('eval', eval_cd), ('pushd', 'pushd %s' % self.parent),
                               ('heredoc-and-eval', self.heredoc('%s; cat' % eval_cd))):
            with self.subTest(block=label):
                self.next_call(command, 'cat %s' % self.outside)

    def test_data_only_climb(self):
        command = self.heredoc('cat %s' % self.climb)
        self.assertGreaterEqual(self.in_call(command), 1)
        self.next_call(self.heredoc('cat'), 'cat %s' % self.climb)

    def test_comment_climb(self):
        command = 'cat %s # note $(date)' % self.climb
        self.assertGreaterEqual(self.in_call(command), 1)
        self.next_call('true # note $(date)', 'cat %s' % self.climb)

    def test_error_edge_after_data_only(self):
        # test_honest_data_only_carry scores the same pair clean without the error.
        self.next_call(self.heredoc('cat'), self.read, error=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
