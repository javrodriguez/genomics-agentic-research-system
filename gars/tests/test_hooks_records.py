"""Row 11 hook faults in disposable repositories; never arm the source clone."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import unittest
from support import run
from secret_support import checked, fixture, snapshot, standin


def decisions_fixture(root):
    folder = root / 'docs/decisions'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / '0001-legacy.md').write_text('---\ndate: 2026-09-21\nstatus: standing\n---\nLegacy.\n')
    checked(['git', 'add', '--', 'docs/decisions'], root)


class RecordHookTests(unittest.TestCase):
    def setUp(self):
        self.root, self.hooks, self.base = fixture(self)
        decisions_fixture(self.root)
        checked(['git', 'add', '--', 'gars/_system'], self.root)
        self.env = standin(self.root)
        self.push = runpy.run_path(str(self.hooks / 'pre-push'))

    def commit(self, message, parent=None):
        tree = checked(['git', 'write-tree'], self.root)
        env = {'GIT_AUTHOR_NAME': 'Fixture', 'GIT_COMMITTER_NAME': 'Fixture',
               'GIT_AUTHOR_EMAIL': 'fixture', 'GIT_COMMITTER_EMAIL': 'fixture'}
        return checked(['git', 'commit-tree', tree, '-p', parent or self.base],
                       self.root, message, env)

    def test_precommit_staged_links_and_independent_vetoes(self):
        code = self.root / 'candidate.py'
        for word in ('decision', 'decisions'):
            code.write_text('# ' + word + ' ' + '9999\n')
            checked(['git', 'add', '--', 'candidate.py'], self.root)
            code.write_text('# harmless working copy\n')
            result = run([sys.executable, self.hooks / 'pre-commit'], self.root, env=self.env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'gitleaks: passed', result.stdout)
            self.assertIn(b'citations: 0/1 resolve', result.stdout)
            print('red-on-fault: pre-commit dangling %s -> REFUSED' % word)
        code.write_text('# (2024)\n')
        checked(['git', 'add', '--', 'candidate.py'], self.root)
        result = run([sys.executable, self.hooks / 'pre-commit'], self.root, env=self.env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'citations: 0/0 resolve', result.stdout)
        result = run([sys.executable, self.hooks / 'pre-commit'], self.root,
                     env=standin(self.root, 'error'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'citations: 0/0 resolve', result.stdout)

    def test_precommit_unreadable_decisions_folder(self):
        folder = self.root / 'docs/decisions'
        folder.chmod(0)
        try:
            result = run([sys.executable, self.hooks / 'pre-commit'], self.root, env=self.env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(b'unreadable decisions folder', result.stderr)
            self.assertIn(b'gitleaks: passed', result.stdout)
            print('red-on-fault: unreadable decisions folder -> pre-commit REFUSED')
        finally:
            folder.chmod(0o755)

    def test_trailers_missing_duplicate_and_not_final(self):
        for message in ('system change\n',
                        'Review: r\nBench: b\nSession: s\n\nordinary body\n',
                        'system change\n\nReview: r\nBench: b\nSession: s\nSession: t\n'):
            commit = self.commit(message)
            with self.assertRaises(ValueError):
                self.push['required_trailers'](self.root, commit)
        print('red-on-fault: _system commit with no trailers -> REFUSED')

    def test_equal_and_differing_review_session(self):
        for record in ('session: producer\n', 'session: a\nsession: b\n', 'no session\n'):
            with self.assertRaises(ValueError):
                self.push['review_session'](record, 'producer')
        self.assertEqual(self.push['review_session']('session: reviewer\n', 'producer'), 'reviewer')
        print('red-on-fault: Review session equals Session -> REFUSED; differing id passes')

    def test_bench_binding_and_na(self):
        message = 'system change\n\nReview: review.md\nBench: evals/runs/run.json\nSession: producer\n'
        commit = self.commit(message)
        records = {'review.md': 'session: reviewer\n',
                   'evals/runs/run.json': json.dumps({'git_sha': commit})}
        self.push['validate_evidence'](self.root, commit, records.__getitem__)
        records['evals/runs/run.json'] = json.dumps({'git_sha': self.base})
        with self.assertRaises(ValueError):
            self.push['validate_evidence'](self.root, commit, records.__getitem__)
        commit = self.commit(message.replace('evals/runs/run.json', 'n/a'))
        with self.assertRaises(ValueError):
            self.push['validate_evidence'](self.root, commit, records.__getitem__)



    def test_activation_range_history_deletion_and_each_commit(self):
        record = self.root / self.push['ACTIVATION_RECORD']
        record.write_text('row activation fixture\n')
        checked(['git', 'add', '--', self.push['ACTIVATION_RECORD']], self.root)
        activation = self.commit('activation without trailers\n')
        subject = self.root / 'gars/_system/subject.py'
        subject.write_text('print(2)\n')
        checked(['git', 'add', '--', 'gars/_system/subject.py'], self.root)
        message = 'system change\n\nReview: review.md\nBench: evals/runs/run.json\nSession: producer\n'
        tip = self.commit(message, activation)
        evidence = {'review.md': 'session: reviewer\n',
                    'evals/runs/run.json': json.dumps({'git_sha': tip})}
        def payload(local, remote):
            return ('refs/heads/test %s refs/heads/test %s\n' % (local, remote)).encode()
        self.assertEqual(self.push['pushed_commits'](self.root, payload(tip, activation)), [tip])
        self.assertTrue(self.push['trailer_gate'](self.root, payload(tip, activation), evidence.__getitem__))
        # Looking only at the tip would miss the activation commit's missing trailers.
        self.assertFalse(self.push['trailer_gate'](self.root, payload(tip, self.base), evidence.__getitem__))
        print('red-on-fault: earlier outgoing _system commit missing trailers -> range REFUSED')
        record.unlink()
        checked(['git', 'add', '--', self.push['ACTIVATION_RECORD']], self.root)
        deletion = self.commit('remove activation record\n', tip)
        self.assertIn(activation, self.push['pushed_commits'](self.root, payload(deletion, self.base)))
        self.assertFalse(self.push['trailer_gate'](self.root, payload(deletion, self.base), evidence.__getitem__))
        # Deleting a remote ref sends no commits; a new ref includes every nonexempt ancestor.
        self.assertEqual(self.push['pushed_commits'](self.root, payload('0' * 40, tip)), [])
        self.assertIn(activation, self.push['pushed_commits'](self.root, payload(tip, '0' * 40)))
        for invalid in (b'bad\n', payload('f' * 40, self.base)):
            self.assertFalse(self.push['trailer_gate'](self.root, invalid, evidence.__getitem__))

    def activate(self, review='review.md', bench='evals/runs/run.json'):
        record = self.root / self.push['ACTIVATION_RECORD']
        record.write_text('row activation fixture\n')
        checked(['git', 'add', '--', self.push['ACTIVATION_RECORD']], self.root)
        return self.commit('system change\n\nReview: %s\nBench: %s\nSession: producer\n' %
                           (review, bench))

    def evidence(self, commit, session='reviewer', sha=None):
        (self.root / 'review.md').write_text('session: ' + session + '\n')
        folder = self.root / 'evals/runs'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'run.json').write_text(json.dumps({'git_sha': sha or commit}))
        checked(['git', 'add', '--', 'review.md', 'evals/runs/run.json'], self.root)
        return self.commit('record evidence\n', commit)

    def invoke_push(self, tip, remote=None, env=None):
        payload = 'refs/heads/fixture %s refs/heads/fixture %s\n' % (tip, remote or self.base)
        return run([sys.executable, self.hooks / 'pre-push', 'fixture-remote', 'fixture-target'],
                   self.root, payload, env or self.env)

    def test_production_requires_later_committed_snapshot(self):
        commit = self.activate()
        result = self.invoke_push(commit)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'self-reference refused', result.stderr)
        self.assertIn(b'gitleaks: passed', result.stdout)
        self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
        # Write and stage matching evidence, but keep the outgoing tip at code.
        tip = self.evidence(commit)
        result = self.invoke_push(commit)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'later committed evidence snapshot required', result.stderr)
        # Only the later outgoing commit makes this code commit pushable.
        result = self.invoke_push(tip)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'trailers: 1 _system commits checked', result.stdout)
        # HEAD still names the old base; neither worktree nor index can change acceptance.
        self.assertEqual(checked(['git', 'rev-parse', 'HEAD'], self.root), self.base)
        self.evidence(commit, session='producer', sha=self.base)
        result = self.invoke_push(tip)
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / 'review.md').unlink()
        (self.root / 'evals/runs/run.json').unlink()
        result = self.invoke_push(tip)
        self.assertEqual(result.returncode, 0, result.stderr)
        print('red-on-fault: code tip and uncommitted evidence -> REFUSED; later committed snapshot passes')

    def test_production_bad_committed_evidence_ignores_worktree_repairs(self):
        commit = self.activate()
        for session, sha, reason in (
                ('producer', commit, b'review session equals'),
                ('reviewer', self.base, b'Bench git_sha does not match')):
            tip = self.evidence(commit, session=session, sha=sha)
            self.evidence(commit)  # Good index/working bytes cannot repair the outgoing object.
            result = self.invoke_push(tip)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(reason, result.stderr)
            self.assertIn(b'gitleaks: passed', result.stdout)
            self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
        print('red-on-fault: equal committed session and wrong committed Bench hash -> pre-push REFUSED')

    def test_production_missing_evidence_and_missing_trailers(self):
        commit = self.activate()
        tip = self.commit('later snapshot without evidence\n', commit)
        self.evidence(commit)
        result = self.invoke_push(tip)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'evidence file absent', result.stderr)
        missing = self.commit('system change without trailers\n')
        later = self.commit('later snapshot\n', missing)
        result = self.invoke_push(later)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'missing Review, Bench or Session trailer', result.stderr)
        self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
        print('red-on-fault: committed evidence absent and system trailers absent -> pre-push REFUSED')

    def test_committed_reader_refuses_self_ancestors_paths_and_symlinks(self):
        commit = self.activate()
        tip = self.evidence(commit)
        for snapshot in (commit, self.base):
            with self.assertRaises((ValueError, subprocess.CalledProcessError)):
                self.push['committed_reader'](self.root, commit, snapshot)
        reader = self.push['committed_reader'](self.root, commit, tip)
        for name in ('../review.md', '/review.md', './review.md', 'evals//runs/run.json',
                     'HEAD:review.md', 'review.md/child', 'absent', 'evals/runs'):
            with self.assertRaises(ValueError):
                reader(name)
        (self.root / 'review.md').unlink()
        (self.root / 'review.md').symlink_to('docs/decisions/0001-legacy.md')
        checked(['git', 'add', '--', 'review.md'], self.root)
        linked = self.commit('symlink evidence\n', commit)
        result = self.invoke_push(linked)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'evidence must be a regular committed file', result.stderr)
        print('red-on-fault: self-reference, earlier snapshot, invalid path and symlink evidence -> REFUSED')

    def test_production_every_ref_and_independent_gate_vetoes(self):
        commit = self.activate()
        tip = self.evidence(commit)
        payload = ('refs/heads/good %s refs/heads/good %s\n'
                   'refs/heads/code %s refs/heads/code %s\n') % (tip, self.base, commit, self.base)
        result = run([sys.executable, self.hooks / 'pre-push'], self.root, payload, self.env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'self-reference refused', result.stderr)
        result = self.invoke_push(tip, env=standin(self.root, 'error'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'trailers: 1 _system commits checked', result.stdout)
        self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
        previous = self.hooks / 'pre-push.gars-previous'
        previous.write_text('#!' + sys.executable + '\nimport sys\nfrom pathlib import Path\n'
                            'Path("previous-input").write_bytes(sys.stdin.buffer.read())\n'
                            'sys.exit(19)\n')
        previous.chmod(0o755)
        result = self.invoke_push(tip)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'trailers: 1 _system commits checked', result.stdout)
        self.assertIn(b'collected 1 tests from gars/tests', result.stdout)
        self.assertIn(tip, (self.root / 'previous-input').read_text())
        previous.unlink()
        test = self.root / 'gars/tests/test_gate_gars_sample.py'
        test.write_text(test.read_text().replace('assertTrue(True)', 'assertTrue(False)'))
        result = self.invoke_push(tip)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'trailers: 1 _system commits checked', result.stdout)
        self.assertIn(b'FAIL: test_positive', result.stderr)
        print('red-on-fault: every outgoing ref and previous/scanner/suite vetoes retained')


if __name__ == '__main__':
    unittest.main(verbosity=2)
