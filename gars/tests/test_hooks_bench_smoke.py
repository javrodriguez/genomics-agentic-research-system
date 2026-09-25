"""Row 14 Bench smoke gate: hook and audit in disposable repositories; never arm the source clone."""
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import unittest
from support import REPO, module, run
from secret_support import checked, fixture, scratch

SMOKE = module(REPO / 'evals/smoke/smoke.py', 'gars_smoke_under_hook_test')
FIXTURE_ENV = {'GIT_AUTHOR_NAME': 'Fixture', 'GIT_COMMITTER_NAME': 'Fixture',
               'GIT_AUTHOR_EMAIL': 'fixture', 'GIT_COMMITTER_EMAIL': 'fixture'}
RESOURCE = {'wall_time_seconds': 'unknown', 'tokens': 'unknown', 'cost_usd': 'unknown'}


def seed(root):
    """Copy the pinned evaluator and the three smoke tasks with their inputs; stage them."""
    names = ['evals/bench.py', 'evals/smoke/smoke.py', SMOKE.RESPONSE_MD]
    for task_id in SMOKE.TASK_IDS:
        name = 'benchmarks/tasks/%s.yaml' % task_id
        names.append(name)
        names.extend(item['path'] for item in json.loads((REPO / name).read_text())['inputs'])
    for name in sorted(set(names)):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())
    checked(['git', 'add', '--'] + sorted(set(names)), root)


def commit(root, message, *parents):
    tree = checked(['git', 'write-tree'], root)
    argv = ['git', 'commit-tree', tree]
    for parent in parents:
        argv += ['-p', parent]
    return checked(argv, root, message, FIXTURE_ENV)


def trailers(run_id, bench=None, review=None, session='producer'):
    return 'system change\n\nReview: %s\nBench: %s\nSession: %s\n' % (
        review or 'docs/reviews/records/%s.md' % run_id,
        bench or 'evals/runs/smoke/%s.json' % run_id, session)


def smoke_evidence(root, bound, parent, run_id, previous=None, floor='self', wrong=(),
                   model='fixture-model'):
    """Genuine-shaped synthetic evidence for `bound`: {path: bytes}; nothing is written."""
    tree = SMOKE.dir_reader(root)
    labels = ['run-1', 'run-2', 'run-3'] if floor == 'self' else ['run-1']
    outputs = {}
    for label in labels:
        outputs[label] = {}
        for task_id in SMOKE.TASK_IDS:
            task = json.loads((root / ('benchmarks/tasks/%s.yaml' % task_id)).read_text())
            answer = dict(task['expected_outputs']['response.json']['json_equals'])
            if task_id in wrong:
                answer['flag'] = 'none'
            outputs[label][task_id] = json.dumps(answer, sort_keys=True).encode('utf-8')
    transcripts = {label: {task: '7' * 64 for task in SMOKE.TASK_IDS} for label in labels}
    path, files = SMOKE.build_evidence(tree, outputs, run_id, bound, parent, model, transcripts,
                                       {label: RESOURCE for label in labels}, previous, floor,
                                       SMOKE.dir_reader(root))
    return path, files


def write_evidence(root, files, run_id=None, session='reviewer'):
    """Write evidence (overwriting) and a review stub, and stage them."""
    names = sorted(files)
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if run_id:
        stub = 'docs/reviews/records/%s.md' % run_id
        (root / 'docs/reviews/records').mkdir(parents=True, exist_ok=True)
        (root / stub).write_text('session: %s\nreviewed: fixture\nverdict: fixture\n' % session)
        names.append(stub)
    checked(['git', 'add', '--'] + names, root)


class BenchSmokeHookTests(unittest.TestCase):
    def setUp(self):
        self.root, self.hooks, first = fixture(self)
        shutil.copyfile(str(REPO / 'gars/_system/hooks/audit_trailers.py'),
                        str(self.hooks / 'audit_trailers.py'))
        seed(self.root)
        self.base = commit(self.root, 'seed evaluator and smoke tasks\n', first)
        self.push = runpy.run_path(str(self.hooks / 'pre-push'))
        self.count = 0

    def change(self, label=None):
        self.count += 1
        subject = self.root / 'gars/_system/subject.py'
        subject.write_text('print(%r)\n' % (label or 'change %d' % self.count))
        checked(['git', 'add', '--', 'gars/_system/subject.py'], self.root)

    def activate(self):
        record = self.root / self.push['ACTIVATION_RECORD']
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text('row activation fixture\n')
        checked(['git', 'add', '--', self.push['ACTIVATION_RECORD']], self.root)

    def landing(self, parent, run_id, previous=None, floor='self', side=None, wrong=()):
        """Ceremony: M with trailers (first parent `parent`), then E carrying M's evidence."""
        parents = [parent] + ([side] if side else [])
        merge = commit(self.root, trailers(run_id), *parents)
        path, files = smoke_evidence(self.root, merge, parent, run_id, previous, floor, wrong)
        write_evidence(self.root, files, run_id)
        return merge, commit(self.root, 'records for %s\n' % run_id, merge), path

    def first_landing(self):
        self.activate()
        self.change()
        return self.landing(self.base, 'smoke-20260925-first')

    def payload(self, local, remote=None):
        return ('refs/heads/fixture %s refs/heads/fixture %s\n'
                % (local, remote or self.base)).encode()

    def gate(self, local, remote=None):
        return self.push['trailer_gate'](self.root, self.payload(local, remote))

    def audit(self, rev=None):
        argv = [sys.executable, self.hooks / 'audit_trailers.py']
        return run(argv + (['--rev', rev] if rev else []), self.root)

    def test_ceremony_and_first_parent_side_branch(self):
        merge1, records1, path1 = self.first_landing()
        self.change('side branch')
        side = commit(self.root, 'side-branch system change without trailers\n', records1)
        merge2, records2, path2 = self.landing(records1, 'smoke-20260926-second', path1, path1,
                                               side=side)
        self.assertEqual(self.push['pushed_commits'](self.root, self.payload(records2)),
                         [merge1, records1, merge2, records2])
        self.assertTrue(self.gate(records2))
        result = self.audit(records2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(b'trailers audit: 2/2 _system first-parent commits', result.stdout)
        # The same kind of commit on the first-parent line carries no evidence of its own.
        self.change('side branch, straight onto the line')
        straight = commit(self.root, 'system change without trailers\n', records2)
        self.assertFalse(self.gate(straight))
        result = self.audit(straight)
        self.assertEqual(result.returncode, 1)
        self.assertIn(('REFUSED %s (missing Review, Bench or Session trailer)' % straight).encode(),
                      result.stdout)
        print('red-on-fault: side-branch commit accepted through its merge; on the first-parent line REFUSED')

    def test_activation_only_on_first_parent_line(self):
        self.activate()
        side = commit(self.root, 'activation record on a side branch\n', self.base)
        checked(['git', 'rm', '-q', '--cached', '--', self.push['ACTIVATION_RECORD']], self.root)
        plain = commit(self.root, 'main without the record\n', self.base)
        self.assertIsNone(self.push['activation_of'](self.root, plain))
        self.activate()
        merge = commit(self.root, 'merge the record\n', plain, side)
        self.assertEqual(self.push['activation_of'](self.root, merge), merge)
        self.assertEqual(self.push['pushed_commits'](self.root, self.payload(merge)), [merge])

    def test_deletion_and_readdition_cannot_move_activation(self):
        merge1, records1, path1 = self.first_landing()
        checked(['git', 'rm', '-q', '--cached', '--', self.push['ACTIVATION_RECORD']], self.root)
        deletion = commit(self.root, 'remove activation record\n', records1)
        self.activate()
        readded = commit(self.root, 're-add activation record\n', deletion)
        # A branch ref at the tip, so a `log --all` spelling without the tip still sees this
        # history (round-2 review NOTE; lane ruling L3): commit-tree alone points no ref at it.
        checked(['git', 'update-ref', 'refs/heads/fixture-tip', readded], self.root)
        self.assertEqual(self.push['activation_of'](self.root, readded), merge1)
        self.assertEqual(self.push['pushed_commits'](self.root, self.payload(readded, '0' * 40)),
                         [merge1, records1, deletion, readded])
        self.assertTrue(self.gate(readded, '0' * 40))
        # A deletion push sends no commits; a new ref includes every commit since activation.
        self.assertEqual(self.push['pushed_commits'](self.root, self.payload('0' * 40, readded)), [])
        self.assertEqual(self.audit(readded).returncode, 0)
        print('red-on-fault: deleting and re-adding 0120 leaves activation at the first landing')

    def test_shallow_repository_refused(self):
        merge1, records1, path1 = self.first_landing()
        (self.root / '.git/shallow').write_text(merge1 + '\n')
        with self.assertRaisesRegex(ValueError, 'shallow'):
            self.push['pushed_commits'](self.root, self.payload(records1))
        result = self.audit()
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'REFUSED (shallow history', result.stdout)

    def test_trusted_evaluator_mismatch_and_absence(self):
        merge1, records1, path1 = self.first_landing()
        reader = self.push['committed_reader'](self.root, merge1, records1)
        self.push['validate_evidence'](self.root, merge1, reader, None)
        for name in ('evals/smoke/smoke.py', 'evals/bench.py'):
            target = self.root / name
            original = target.read_bytes()
            try:
                target.write_bytes(original + b'\n# a harmless-looking edit\n')
                with self.assertRaisesRegex(ValueError, 'untrusted evaluator: ' + name):
                    self.push['validate_evidence'](self.root, merge1, reader, None)
                target.unlink()
                with self.assertRaisesRegex(ValueError, 'untrusted evaluator: ' + name):
                    self.push['validate_evidence'](self.root, merge1, reader, None)
            finally:
                target.write_bytes(original)
        self.push['validate_evidence'](self.root, merge1, reader, None)
        print('red-on-fault: evaluator bytes differ from or are absent at TRUSTED_EVALUATOR -> REFUSED')

    def test_evidence_same_commit_non_descendant_and_bench_location(self):
        self.activate()
        self.change()
        run_id = 'smoke-20260925-inline'
        merge = commit(self.root, trailers(run_id), self.base)
        path, files = smoke_evidence(self.root, merge, self.base, run_id)
        write_evidence(self.root, files, run_id)
        # Evidence inside the commit it is bound to is a self-reference.
        inline = commit(self.root, trailers(run_id), self.base)
        self.assertFalse(self.gate(inline))
        result = self.audit(inline)
        self.assertEqual(result.returncode, 1)
        self.assertIn(b'later committed evidence snapshot required', result.stdout)
        sibling = commit(self.root, 'evidence on a sibling\n', self.base)
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            self.push['committed_reader'](self.root, merge, sibling)
        later = commit(self.root, 'records\n', merge)
        reader = self.push['committed_reader'](self.root, merge, later)
        self.push['validate_evidence'](self.root, merge, reader, None)
        for bench in ('evals/runs/run.json', 'n/a'):
            other = commit(self.root, trailers(run_id, bench=bench), self.base)
            snapshot = commit(self.root, 'records\n', other)
            with self.assertRaisesRegex(ValueError, 'evals/runs/smoke/'):
                self.push['validate_evidence'](
                    self.root, other, self.push['committed_reader'](self.root, other, snapshot), None)
        print('red-on-fault: same-commit, sibling, non-smoke and n/a Bench evidence -> REFUSED')

    def test_audit_zero_rule(self):
        self.activate()
        activation = commit(self.root, 'activation touching no _system path\n', self.base)
        result = self.audit(activation)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(b'trailers audit: 0/0 _system first-parent commits since activation', result.stdout)
        self.assertIn(b'FAIL activation exists and 0 commits were checked', result.stdout)
        print('red-on-fault: activation with zero checked commits -> audit FAILS')

    def test_audit_not_applicable_and_given_commit(self):
        result = self.audit(self.base)
        self.assertEqual(result.returncode, 0)
        self.assertIn(('not applicable — not activated at %s' % self.base[:7]).encode(), result.stdout)
        merge1, records1, path1 = self.first_landing()
        result = self.audit(merge1)
        self.assertEqual(result.returncode, 1)
        self.assertIn(('REFUSED %s (later committed evidence snapshot required' % merge1).encode(),
                      result.stdout)

    def test_audit_previous_chain(self):
        merge1, records1, path1 = self.first_landing()
        self.change()
        merge2, records2, path2 = self.landing(records1, 'smoke-20260926-second', path1, path1)
        result = self.audit(records2)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(('verified %s (Bench previous: none)' % merge1).encode(), result.stdout)
        self.assertIn(('verified %s (Bench previous: %s)' % (merge2, path1)).encode(), result.stdout)
        # A third landing that skips its predecessor is refused by the chain.
        self.change()
        merge3, records3, path3 = self.landing(records2, 'smoke-20260927-third', path1, path1)
        result = self.audit(records3)
        self.assertEqual(result.returncode, 1)
        self.assertIn(('REFUSED %s (Bench smoke record refused: PREVIOUS_MISMATCH previous' % merge3).encode(),
                      result.stdout)
        print('red-on-fault: record naming a skipped predecessor -> audit REFUSED')

    def test_build_branch_is_red_by_construction(self):
        self.activate()
        self.change()
        build = commit(self.root, 'row 14 round 1\n', self.base)
        result = self.audit(build)
        self.assertEqual(result.returncode, 1)
        self.assertIn(('REFUSED %s (missing Review, Bench or Session trailer)' % build).encode(),
                      result.stdout)
        result = self.audit(self.base)
        self.assertEqual(result.returncode, 0)
        self.assertIn(('not applicable — not activated at %s' % self.base[:7]).encode(), result.stdout)
        print('build branch: audit REFUSES its round-1 commit; its base reads not applicable')

    def test_previous_bench_below_pushed_range(self):
        merge1, records1, path1 = self.first_landing()
        self.change()
        merge2, records2, path2 = self.landing(records1, 'smoke-20260926-second', path1, path1)
        self.assertEqual(self.push['pushed_commits'](self.root, self.payload(records2, records1)),
                         [merge2, records2])
        self.assertEqual(self.push['previous_bench'](self.root, merge2), path1)
        self.assertTrue(self.gate(records2, records1))
        result = self.audit(records2)
        self.assertIn(('verified %s (Bench previous: %s)' % (merge2, path1)).encode(), result.stdout)

    def test_dir_and_git_readers_agree(self):
        merge1, records1, path1 = self.first_landing()
        for tamper in (False, True):
            if tamper:
                name = SMOKE.outputs_prefix('smoke-20260925-first', 'run-2') + 'pseudoreplicates/response.json'
                (self.root / name).write_bytes(b'{"answer": "proceed"}\n')
                checked(['git', 'add', '--', name], self.root)
                records1 = commit(self.root, 'tampered records\n', records1)
            git_verdict = SMOKE.evaluate(
                self.push['committed_reader'](self.root, merge1, records1)(path1),
                self.push['committed_reader'](self.root, merge1, records1),
                self.push['tree_reader'](self.root, merge1), merge1, self.base, None,
                record_path=path1)
            folder = scratch(self) / ('snapshot-%d' % tamper)
            folder.mkdir()
            checked(['git', 'worktree', 'add', '-q', '--detach', str(folder / 'evidence'), records1],
                    self.root)
            checked(['git', 'worktree', 'add', '-q', '--detach', str(folder / 'tree'), merge1],
                    self.root)
            dir_verdict = SMOKE.evaluate(
                (folder / 'evidence' / path1).read_bytes(), SMOKE.dir_reader(folder / 'evidence'),
                SMOKE.dir_reader(folder / 'tree'), merge1, self.base, None, record_path=path1)
            self.assertEqual(git_verdict, dir_verdict)
            self.assertEqual(git_verdict['ok'], not tamper)
        self.assertEqual(sorted(set(f['code'] for f in git_verdict['findings'])),
                         ['COUNT_MISMATCH', 'FLOOR_MISMATCH', 'OUTPUT_HASH_MISMATCH', 'REGRADE_MISMATCH'])
        print('contract drift: git-mode and dir-mode verdicts identical, clean and tampered')


HOOK = 'gars/_system/hooks/pre-push'
AUDIT = 'gars/_system/hooks/audit_trailers.py'
FAULTS = [
    ('first-parent rule replaced by all-parents', HOOK,
     "git_bytes(root, 'rev-list', '--first-parent',\n                                        *revision)",
     "git_bytes(root, 'rev-list',\n                                        *revision)",
     'BenchSmokeHookTests.test_ceremony_and_first_parent_side_branch'),
    ('activation searched over --all', HOOK,
     '    chain = first_parent_chain(root, tip)\n    query =',
     "    found = git_bytes(root, 'log', '--exclude=refs/replace/*', '--all', '--full-history',\n"
     "                      '--format=%H', '--diff-filter=A', '--no-renames', tip, '--',\n"
     "                      ACTIVATION_RECORD).decode('ascii').split()\n"
     "    if len(found) != 1:\n"
     "        raise ValueError('ambiguous trailer activation history')\n"
     "    return found[0]\n"
     '    chain = first_parent_chain(root, tip)\n    query =',
     'BenchSmokeHookTests.test_deletion_and_readdition_cannot_move_activation'),
    ('activation searched over --all, no tip, latest add', HOOK,
     '    chain = first_parent_chain(root, tip)\n    query =',
     "    found = git_bytes(root, 'log', '--all', '--format=%H', '--diff-filter=A', '--',\n"
     "                      ACTIVATION_RECORD).decode('ascii').split()\n"
     "    return found[0] if found else None\n"
     '    chain = first_parent_chain(root, tip)\n    query =',
     'BenchSmokeHookTests.test_deletion_and_readdition_cannot_move_activation'),
    ('TRUSTED_EVALUATOR check removed', HOOK,
     '        if (path.is_symlink() or not path.is_file() or\n'
     '                hashlib.sha256(path.read_bytes()).hexdigest() != expected):',
     '        if False:',
     'BenchSmokeHookTests.test_trusted_evaluator_mismatch_and_absence'),
    ("audit's zero rule removed", AUDIT,
     '    if not checked:\n', '    if False:\n',
     'BenchSmokeHookTests.test_audit_zero_rule'),
]
COPIED = ['gars/tests/test_hooks_bench_smoke.py', 'gars/tests/support.py',
          'gars/tests/secret_support.py', 'gars/.gitleaks.toml', 'tests/run_tests.py',
          'gars/_system/hooks/pre-push', 'gars/_system/hooks/pre-commit',
          'gars/_system/hooks/install.py', AUDIT, 'evals/bench.py', 'evals/smoke/smoke.py',
          SMOKE.RESPONSE_MD]


class BenchSmokeHookFaultTests(unittest.TestCase):
    def test_hook_guards_go_red(self):
        copy = scratch(self) / 'source'
        names = list(COPIED)
        for task_id in SMOKE.TASK_IDS:
            name = 'benchmarks/tasks/%s.yaml' % task_id
            names.append(name)
            names.extend(item['path'] for item in json.loads((REPO / name).read_text())['inputs'])
        for name in sorted(set(names)):
            target = copy / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(REPO / name), str(target))
        for label, name, old, new, test in FAULTS:
            with self.subTest(fault=label):
                target = copy / name
                original = target.read_bytes()
                text = original.decode('utf-8')
                self.assertEqual(text.count(old), 1, label)
                argv = [sys.executable, copy / 'gars/tests/test_hooks_bench_smoke.py', test]
                try:
                    target.write_text(text.replace(old, new))
                    red = run(argv, copy)
                finally:
                    target.write_bytes(original)
                self.assertNotEqual(red.returncode, 0, label)
                self.assertRegex(red.stderr, rb'FAILED \((failures|errors)=')
                green = run(argv, copy)
                self.assertEqual(green.returncode, 0, green.stderr[-2000:])
                print('red-on-fault: %s -> %s red, then green after restore' % (label, test))


if __name__ == '__main__':
    unittest.main(verbosity=2)
