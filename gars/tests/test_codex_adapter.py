"""Codex adapter: one guard behind two envelopes (decision 0266), red first.

Groups 1-12 are the plan's Task 2.1 (gars-codex-portability.md); each test class is one group.
Every test builds its own temp workspace (`<tmp>/repo/.git` plus `<tmp>/repo/gars/...`), copying
`_system`, `_references`, `_templates`, `.claude`, `.codex` and the root files the guard reads;
no test writes into this repository's tree, and no test reads or writes the real home: the cases
that spell `~` set HOME to a temp folder, in-process and in every subprocess.

The adapter (`_system/codex_hook.py`) and `guard_hook.decide` are reached lazily, inside each
test, so while either is missing each group fails or errors on its own and this module still
imports. Names this module relies on beyond the plan's interface contract:
- `codex_hook.run(payload, root)`, `codex_hook.main()` (argv[1] is the mode), `codex_hook.GARS_ROOT`
- `codex_hook.PASS_TOOLS`: the iterable of Codex tool names allowed without a judgment
- `codex_hook.decide` (the name `from guard_hook import decide` binds), patched in group 7
- `guard_hook.decide(payload, root=None)`

The fail-closed sweep (group 7) is an invariant over every case in this module: each adapter
verdict, in-process or through a subprocess, is checked to exit only 0 or 2, and 2 with text.
Runs on stock python 3.6.8, stdlib only.
"""
import contextlib
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import unittest
from pathlib import Path
from unittest.mock import patch

from support import GARS, REPO
import build_refusal_corpus as corpus  # the replay helpers: rows, materialize, relocate, judge
import guard_hook

SYSTEM = GARS / '_system'
ADAPTER_SOURCE = SYSTEM / 'codex_hook.py'
LOGIN_SHELL = os.environ.get('SHELL', '/bin/sh')
PUBLIC_ROW = ('data_class\tpurpose\tagreement_ref\tinput_data_location\n'
              'public\tfixture\tnone\t[]\n')
CLOSED_ROW = ('data_class\tpurpose\tagreement_ref\tinput_data_location\n'
              'deidentified_under_agreement\tfixture\tnone\t[]\n')
ENVELOPE_KEYS = {'session_id', 'turn_id', 'transcript_path', 'cwd', 'hook_event_name', 'model',
                 'permission_mode', 'tool_name', 'tool_input', 'tool_use_id'}
PROTECTED_FIRST = 'Blocked: _system/x.py is protected template or machine-owned state'


# --- group 1: the envelope ------------------------------------------------------------------

def codex_payload(tool_name, tool_input, cwd):
    """A PreToolUse stdin object as Codex 0.154 sends it (hooks.md; events_pre_tool_use.rs)."""
    return {'session_id': '0199a000-0000-7000-8000-000000000001', 'turn_id': 'turn-1',
            'transcript_path': None, 'cwd': str(cwd), 'hook_event_name': 'PreToolUse',
            'model': 'gpt-5-codex', 'permission_mode': 'default', 'tool_name': tool_name,
            'tool_input': tool_input, 'tool_use_id': 'call-0001'}


def rewrite(cwd, command):
    """The workdir pin (group 12): allowed shell commands run in the folder they were judged in."""
    return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'allow',
                                   'updatedInput': {'command': 'cd -- ' + shlex.quote(str(cwd))
                                                    + ' && ' + command}}}


# --- apply_patch fixtures (the grammar of ap_parser.rs / ap_streaming.rs) --------------------

def add(path, lines=('hello',)):
    return ['*** Add File: ' + path] + ['+' + line for line in lines]


def update(path, old=('a',), new=('b',), move=None):
    return (['*** Update File: ' + path] + (['*** Move to: ' + move] if move else []) + ['@@']
            + ['-' + line for line in old] + ['+' + line for line in new])


def delete(path):
    return ['*** Delete File: ' + path]


def patch_text(*entries, **kw):
    lines = ['*** Begin Patch'] + [line for entry in entries for line in entry] + ['*** End Patch']
    return '\n'.join(lines) + kw.get('tail', '\n')


def apply_patch(text, cwd):
    return codex_payload('apply_patch', {'command': text}, cwd)


# --- verdicts and the fail-closed invariant (group 7) -----------------------------------------

class Verdict(object):
    def __init__(self, code, err, out, result, escaped):
        self.code, self.err, self.out, self.result, self.escaped = code, err, out, result, escaped

    @property
    def first(self):
        return self.err.split('\n', 1)[0]

    def __repr__(self):
        return 'Verdict(exit=%r, first=%r, result=%r, escaped=%r)' % (
            self.code, self.first, self.result, self.escaped)


def capture(call):
    err, out = io.StringIO(), io.StringIO()
    code, result, escaped = 0, None, None
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(out):
        try:
            result = call()
        except SystemExit as exc:
            code = exc.code
        except BaseException as exc:  # noqa: B902 -- KeyboardInterrupt too: it would fail open
            escaped = exc
    return Verdict(code, err.getvalue(), out.getvalue(), result, escaped)


def fail_closed(verdict, where):
    """Group 7's invariant, applied to every adapter verdict in this module."""
    if verdict.escaped is not None:
        raise AssertionError('%s let %s escape; Codex runs the call when a hook crashes (fail-open)'
                             % (where, type(verdict.escaped).__name__))
    if verdict.code not in (0, 2):
        raise AssertionError('%s exited %r; Codex treats every exit but 2 as allow' % (where, verdict.code))
    if verdict.code == 2 and not verdict.err.strip():
        raise AssertionError('%s exited 2 with empty stderr; Codex lets that call run' % where)
    if verdict.code == 2 and '"allow"' in verdict.out:
        raise AssertionError('%s refused but printed an allow on stdout: %r' % (where, verdict.out))
    if verdict.code == 0 and verdict.result is not None and not isinstance(verdict.result, dict):
        raise AssertionError('%s returned %r; run() returns None or the rewrite dict' % (where, verdict.result))
    return verdict


def environment(home=None, project_dir=None):
    env = {k: v for k, v in os.environ.items() if k != 'CLAUDE_PROJECT_DIR'}
    if home is not None:
        env['HOME'] = str(home)
    if project_dir is not None:
        env['CLAUDE_PROJECT_DIR'] = str(project_dir)
    return env


def adapter():
    """The adapter, imported lazily so a missing one is this test's error, not the module's."""
    import codex_hook
    return codex_hook


def codex_run(payload, root, home=None):
    """codex_hook.run in-process, with CLAUDE_PROJECT_DIR unset (Codex has no project variable)."""
    hook = adapter()
    with patch.dict(os.environ, environment(home), clear=True):
        verdict = capture(lambda: hook.run(payload, str(root)))
    if verdict.code is None or (verdict.escaped is None and verdict.code not in (0, 2)):
        raise AssertionError('run() exited %r; it denies (exit 2) or returns' % verdict.code)
    return fail_closed(verdict, 'codex_hook.run')


def codex_main(stdin_bytes, mode='pre-tool-use', home=None):
    """codex_hook.main in-process; stdin is a real text stream over bytes (it has .buffer)."""
    hook = adapter()
    stream = io.TextIOWrapper(io.BytesIO(stdin_bytes), encoding='utf-8')
    with patch.dict(os.environ, environment(home), clear=True), \
            patch.object(sys, 'argv', ['codex_hook.py', mode]), patch.object(sys, 'stdin', stream):
        verdict = capture(hook.main)
    if verdict.code is None:
        verdict.code = 0
    return fail_closed(verdict, 'codex_hook.main')


def decide(tool, tool_input, cwd, root, home=None):
    """guard_hook.decide on a Claude-shaped payload: the verdict an adapter entry must equal."""
    judge = guard_hook.decide
    payload = {'tool_name': tool, 'tool_input': tool_input, 'cwd': str(cwd)}
    with patch.dict(os.environ, environment(home), clear=True):
        verdict = capture(lambda: judge(payload, str(root)))
    if verdict.escaped is not None:
        raise verdict.escaped
    return verdict


def claude_main(tool, tool_input, cwd, root, home=None):
    """Claude's envelope: guard_hook.main with CLAUDE_PROJECT_DIR set, as the corpus judge does."""
    payload = json.dumps({'tool_name': tool, 'tool_input': tool_input, 'cwd': str(cwd)})
    with patch.dict(os.environ, environment(home, project_dir=root), clear=True), \
            patch.object(sys, 'stdin', io.StringIO(payload)):
        verdict = capture(guard_hook.main)
    if verdict.escaped is not None:
        raise verdict.escaped
    return verdict


def run_process(argv, cwd, stdin_bytes, home, where):
    """A subprocess with CLAUDE_PROJECT_DIR unset and HOME at a temp folder."""
    env = environment(home)
    for name in ('ZDOTDIR', 'BASH_ENV', 'ENV'):
        env.pop(name, None)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    result = subprocess.run([str(a) for a in argv], cwd=str(cwd), env=env, input=stdin_bytes,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    verdict = Verdict(result.returncode, result.stderr.decode('utf-8', 'replace'),
                      result.stdout.decode('utf-8', 'replace'), None, None)
    return fail_closed(verdict, where)


def through_shell(shell, command, cwd, stdin_bytes, home):
    """A hooks.json command as Codex runs it ($SHELL -lc, engine_command_runner.rs:433) or via sh -c."""
    argv = ['/bin/sh', '-c', command] if shell == 'sh' else [LOGIN_SHELL, '-lc', command]
    return run_process(argv, cwd, stdin_bytes, home, '%s hooks.json command' % shell)


def as_bytes(payload):
    return json.dumps(payload).encode('utf-8')


# --- temp workspaces --------------------------------------------------------------------------

class Workspace(object):
    """<tmp>/repo/.git + <tmp>/repo/gars/... with project p public and, if `closed`, c closed."""

    def __init__(self, closed=True):
        self._tmp = tempfile.TemporaryDirectory(prefix='codex-adapter-')
        self.tmp = Path(os.path.realpath(self._tmp.name))
        self.repo = self.tmp / 'repo'
        self.gars = self.repo / 'gars'
        # Codex's own project root: a .git file, or a .git folder holding HEAD
        # (config/src/loader/mod.rs find_project_root, rust-v0.154.0).
        (self.repo / '.git').mkdir(parents=True)
        (self.repo / '.git/HEAD').write_text('ref: refs/heads/main\n')
        self.gars.mkdir()
        for name in ('_system', '_references', '_templates', '.claude', '.codex'):
            if (GARS / name).is_dir():
                shutil.copytree(str(GARS / name), str(self.gars / name), symlinks=True,
                                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        for name in ('AGENTS.md', 'CLAUDE.md', 'CONTEXT.md'):
            shutil.copy2(str(GARS / name), str(self.gars / name))
        self.home = self.tmp / 'home'
        self.home.mkdir()
        self.outside = self.tmp / 'outside'
        self.outside.mkdir()
        self.project('p', PUBLIC_ROW)
        (self.gars / 'projects/p/notes.md').write_text('a\n')
        if closed:
            self.project('c', CLOSED_ROW)
            (self.gars / 'projects/c/notes.md').write_text('a\n')

    def project(self, name, row):
        data = self.gars / 'projects' / name / '00_data'
        data.mkdir(parents=True)
        (data / 'dataset.tsv').write_text(row)
        return self.gars / 'projects' / name

    @property
    def adapter(self):
        return self.gars / '_system/codex_hook.py'

    def hooks(self):
        data = json.loads((self.gars / '.codex/hooks.json').read_text())
        return {event: [h['command'] for group in groups for h in group['hooks']]
                for event, groups in data['hooks'].items()}

    def cleanup(self):
        self._tmp.cleanup()


class WorkspaceCase(unittest.TestCase):
    CLOSED = True

    @classmethod
    def setUpClass(cls):
        cls.ws = Workspace(closed=cls.CLOSED)

    @classmethod
    def tearDownClass(cls):
        cls.ws.cleanup()

    def same(self, codex, claude, expect=None, label=''):
        """Same exit and a byte-equal first stderr line; optionally the exit the grid expects."""
        self.assertEqual((codex.code, codex.first), (claude.code, claude.first), label)
        if expect is not None:
            self.assertEqual(codex.code, expect, '%s %r' % (label, codex))
        if codex.code == 2:
            self.assertIn('Next:', codex.err)


# --- group 1 ----------------------------------------------------------------------------------

class Group01EnvelopeTests(WorkspaceCase):
    def test_envelope_fields_and_acceptance(self):
        payload = codex_payload('Bash', {'command': 'ls'}, self.ws.gars)
        self.assertEqual(set(payload), ENVELOPE_KEYS)
        expected = rewrite(self.ws.gars, 'ls')
        verdict = codex_run(payload, self.ws.gars)
        self.assertEqual((verdict.code, verdict.result), (0, expected), verdict)
        # A sub-agent's call carries agent_id and agent_type; it is judged the same way.
        child = dict(payload, agent_id='agent-1', agent_type='worker')
        self.assertEqual(codex_run(child, self.ws.gars).result, expected)


# --- group 2 ----------------------------------------------------------------------------------

GRADED = ('Bash', 'Write', 'Edit', 'malformed')
NOT_CODEX = ('Read', 'Grep', 'Glob', 'MultiEdit', 'NotebookEdit')


def classify(text):
    """(class, parsed payload). Malformed: unparseable, non-dict, a non-dict tool_input, or no
    string tool name. Write and Edit rows whose path an apply_patch header cannot carry
    (not a non-empty string, a control character, or surrounding whitespace that Codex trims)
    are counted as `inexpressible`, never dropped."""
    try:
        value = json.loads(text)
    except ValueError:
        return 'malformed', None
    if (not isinstance(value, dict) or not isinstance(value.get('tool_input') or {}, dict)
            or not isinstance(value.get('tool_name'), str) or not value.get('tool_name')):
        return 'malformed', value
    tool = value['tool_name']
    if tool in ('Write', 'Edit'):
        path = value['tool_input'].get('file_path')
        if (not isinstance(path, str) or not path or path != path.strip()
                or any(unicodedata.category(ch)[0] == 'C' for ch in path)):
            return 'inexpressible', value
    return tool, value


def content_lines(text):
    lines = (text or '').split('\n')
    if len(lines) > 1 and lines[-1] == '':
        lines.pop()
    return lines


def malformed_stdin(text, value):
    """A Codex envelope with the same defect as the Claude row."""
    if not isinstance(value, dict):
        return text.encode('utf-8')
    envelope = codex_payload('', {}, '')
    for key in ('tool_name', 'tool_input', 'cwd'):
        del envelope[key]
    envelope.update(value)
    return as_bytes(envelope)


class Group02ParityReplayTests(unittest.TestCase):
    def test_corpus_parity(self):
        hook = adapter()  # before the loop: a missing adapter is one error, not 2606
        self.assertTrue(callable(hook.run))
        started = time.time()
        counts, tallies, seen, graded_seen = {}, {}, 0, 0
        previous, temporary, root, bindings = None, None, None, None
        try:
            for row, state in corpus.rows():
                if row['context'] != previous:
                    if temporary is not None:
                        temporary.cleanup()
                    temporary = tempfile.TemporaryDirectory(prefix='codex-parity-')
                    root, bindings = corpus.materialize(state, Path(temporary.name).resolve())
                    previous = row['context']
                text = corpus.relocate(row['payload'], bindings)
                cls, value = classify(text)
                counts[cls] = counts.get(cls, 0) + 1
                seen += 1
                if cls not in GRADED:
                    continue
                graded_seen += 1
                with self.subTest(row=row['name'], cls=cls):
                    expected, claude_text = corpus.judge(text, root)
                    # The replay itself must still reproduce the pinned decision.
                    self.assertEqual(expected, {key: row[key] for key in corpus.KEYS})
                    claude_first = claude_text.split('\n', 1)[0]
                    if cls == 'malformed':
                        codex = codex_main(malformed_stdin(text, value))
                        # Exit and first line bound to Claude's live verdict (review r1, R1-2/F3).
                        self.assertEqual((codex.code, codex.first), (expected['exit'], claude_first),
                                         'Claude %r' % claude_text)
                        self.assertEqual(codex.code, 2, codex)
                        self.assertIn('Next:', codex.err)
                        tallies[cls, codex.code] = tallies.get((cls, codex.code), 0) + 1
                        continue
                    cwd = value.get('cwd')
                    data = value['tool_input']
                    if cls == 'Bash':
                        payload = codex_payload('Bash', dict(data), cwd)
                    elif cls == 'Write':
                        payload = apply_patch(patch_text(add(data['file_path'], content_lines(
                            data.get('content')))), cwd)
                    else:
                        payload = apply_patch(patch_text(update(
                            data['file_path'], content_lines(data.get('old_string')),
                            content_lines(data.get('new_string')))), cwd)
                    codex = codex_run(payload, root)
                    self.assertEqual((codex.code, codex.first), (expected['exit'], claude_first),
                                     'Claude %r' % claude_text)
                    if cls == 'Bash' and expected['exit'] == 0:
                        self.assertEqual(codex.result, rewrite(cwd, data['command']))
                    tallies[cls, codex.code] = tallies.get((cls, codex.code), 0) + 1
        finally:
            if temporary is not None:
                temporary.cleanup()
        others = sorted(set(counts) - set(GRADED) - set(NOT_CODEX) - {'inexpressible'})
        graded = sum(counts.get(c, 0) for c in GRADED)
        line = 'graded %d / seen %d: %s; not Codex tools: %s' % (
            graded, seen, ', '.join('%s %d' % (c, counts.get(c, 0)) for c in GRADED),
            ', '.join('%s %d' % (c, counts.get(c, 0)) for c in NOT_CODEX + tuple(others)))
        if counts.get('inexpressible'):
            line += '; inexpressible %d' % counts['inexpressible']
        sys.stderr.write('\n' + line + '\n')
        sys.stderr.write('parity tallies (class, exit): %s; %.1f s\n' % (
            ', '.join('%s/%d %d' % (c, e, n) for (c, e), n in sorted(tallies.items())),
            time.time() - started))
        with open(str(corpus.FIXTURE)) as stream:
            total = sum(1 for _ in stream)
        self.assertEqual(seen, total)
        self.assertEqual(sum(counts.values()), seen)
        self.assertEqual(graded_seen, graded)
        self.assertEqual(sum(tallies.values()), graded, 'every graded row reached a verdict')
        self.assertEqual(graded, counts.get('Bash', 0) + counts.get('Write', 0) + counts.get('Edit', 0)
                         + counts.get('malformed', 0))
        self.assertEqual(counts.get('inexpressible', 0), 0,
                         'a Write/Edit row an apply_patch header cannot carry: grade it explicitly')
        for cls in GRADED:
            self.assertTrue(counts.get(cls), 'class %s is empty: the replay is vacuous' % cls)
        for cls in ('Bash', 'Write', 'Edit'):
            for code in (0, 2):
                self.assertTrue(tallies.get((cls, code)), 'no %s row exited %d' % (cls, code))
        self.assertRegex(line, r'^graded \d+ / seen \d+: Bash \d+, Write \d+, Edit \d+, malformed \d+; '
                               r'not Codex tools: Read \d+, Grep \d+, Glob \d+, MultiEdit \d+, '
                               r'NotebookEdit \d+')


# --- group 3 ----------------------------------------------------------------------------------

FREE = 'projects/p/notes.md'
PROTECTED = ('_system/x.py', 'CONTEXT.md', 'projects/p/STATUS')
CLOSED = 'projects/c/notes.md'


class Group03ApplyPatchGrammarTests(WorkspaceCase):
    def targets(self):
        outside = str(self.ws.outside / 'x.txt')
        return ([('free', FREE)] + [('protected', p) for p in PROTECTED] + [('closed', CLOSED)]
                + [('outside', outside), ('outside', '../../x.txt')])

    def codex(self, text, cwd=None):
        return codex_run(apply_patch(text, cwd or self.ws.gars), self.ws.gars)

    def decide(self, tool, data, cwd=None):
        return decide(tool, data, cwd or self.ws.gars, self.ws.gars)

    def test_entry_kind_grid(self):
        for kind, path in self.targets():
            expect = 0 if kind == 'free' else 2
            with self.subTest(entry='Add', target=path):
                self.same(self.codex(patch_text(add(path, ['hello']))),
                          self.decide('Write', {'file_path': path, 'content': 'hello\n'}), expect)
            with self.subTest(entry='Update', target=path):
                self.same(self.codex(patch_text(update(path, ['old'], ['new']))),
                          self.decide('Edit', {'file_path': path, 'old_string': 'old',
                                               'new_string': 'new'}), expect)
            with self.subTest(entry='Delete', target=path):
                # Judged as an empty Write: on a free path that is the guard's Write verdict, allow.
                self.same(self.codex(patch_text(delete(path))),
                          self.decide('Write', {'file_path': path, 'content': ''}), expect)

    def test_claude_cannot_delete_either(self):
        # Under Claude a delete is `rm`, which is unregistered and refused (R-092).
        for path in (FREE, PROTECTED[0]):
            with self.subTest(target=path):
                self.assertEqual(self.decide('Bash', {'command': 'rm ' + path}).code, 2)

    def test_move_matrix(self):
        outside = str(self.ws.outside / 'x.txt')
        pairs = [(FREE, 'projects/p/moved.md'), (FREE, PROTECTED[0]), (FREE, 'projects/p/STATUS'),
                 (PROTECTED[0], 'projects/p/moved.md'), (CLOSED, 'projects/p/moved.md'),
                 (FREE, CLOSED), (FREE, outside), (outside, 'projects/p/moved.md'),
                 (PROTECTED[0], CLOSED)]
        for src, dst in pairs:
            with self.subTest(source=src, destination=dst):
                codex = self.codex(patch_text(update(src, move=dst)))
                source = self.decide('Edit', {'file_path': src, 'old_string': 'a', 'new_string': 'b'})
                target = self.decide('Write', {'file_path': dst, 'content': 'b\n'})
                if source.code == 0 and target.code == 0:
                    self.assertEqual((codex.code, codex.err), (0, ''), codex)
                    self.assertEqual((src, dst), (FREE, 'projects/p/moved.md'))
                    continue
                self.assertEqual(codex.code, 2, codex)
                refused = [v.first for v in (source, target) if v.code == 2]
                self.assertIn(codex.first, refused)

    def test_link_at_a_protected_place_is_not_deleted_or_moved(self):
        # Delete File and a Move's source act on the link itself, while the guard judges the file
        # it points to (review r1, R1-4): a link at a machine-owned place pointing at a free file.
        run = self.ws.gars / 'projects/p/02_bioinformatics/r/run'
        run.mkdir(parents=True, exist_ok=True)
        link = run / 'out.txt'
        if not os.path.lexists(str(link)):
            os.symlink('../../../notes.md', str(link))
        rel = 'projects/p/02_bioinformatics/r/run/out.txt'
        for label, entry in (('Delete', delete(rel)), ('Move source', update(rel, move='projects/p/m.md')),
                             ('Delete, absolute', delete(str(self.ws.gars / rel)))):
            with self.subTest(entry=label):
                verdict = self.codex(patch_text(entry))
                self.assertEqual(verdict.code, 2, verdict)
                self.assertIn('Next:', verdict.err)
        # Writing through the link judges its target, as Claude's Write does.
        self.same(self.codex(patch_text(update(rel, ['a'], ['b']))),
                  self.decide('Edit', {'file_path': rel, 'old_string': 'a', 'new_string': 'b'}), 0)

    def test_two_entries_only_the_second_protected(self):
        cases = [(add(FREE), add(PROTECTED[0]), ('Write', PROTECTED[0])),
                 (update(FREE), delete('projects/p/STATUS'), ('Write', 'projects/p/STATUS')),
                 (add('projects/p/new.md'), update(PROTECTED[1]), ('Edit', PROTECTED[1])),
                 (delete(FREE), add(CLOSED), ('Write', CLOSED))]
        for first, second, (tool, path) in cases:
            with self.subTest(first=first[0], second=second[0]):
                self.same(self.codex(patch_text(first, second)),
                          self.decide(tool, {'file_path': path, 'content': 'x',
                                             'old_string': 'a', 'new_string': 'b'}), 2)

    def test_unjudgeable_patches_refused(self):
        free = patch_text(add(FREE, ['x']))
        cases = [
            ('environment id', '*** Begin Patch\n*** Environment ID: remote-1\n' + '\n'.join(add(FREE)) + '\n*** End Patch\n'),
            ('empty', ''),
            ('blank', '  \n\n'),
            ('no entries', '*** Begin Patch\n*** End Patch\n'),
            ('no begin', '\n'.join(add(FREE)) + '\n*** End Patch\n'),
            ('no end', '*** Begin Patch\n' + '\n'.join(add(FREE)) + '\n'),
            ('unknown header', '*** Begin Patch\n*** Copy File: ' + FREE + '\n+x\n*** End Patch\n'),
            ('unknown header after add', '*** Begin Patch\n' + '\n'.join(add(FREE)) + '\n*** Rename File: x\n*** End Patch\n'),
            ('crlf', free.replace('\n', '\r\n')),
            ('cr', free.replace('\n', '\r')),
            ('cr in content', patch_text(add(FREE, ['a\rb']))),
            ('u2028 in content', patch_text(add(FREE, ['a b']))),
        ]
        for sep in (' ', ' ', '\x85', '\x0b', '\x0c', '\x1c', '\x1d', '\x1e'):
            cases.append(('separator %r after header' % sep,
                          '*** Begin Patch\n*** Add File: ' + FREE + sep + '+x\n*** End Patch\n'))
        for ch in ('\x00', '\x01', '\x1b', '\x7f', '\t'):
            cases.append(('control %r in path' % ch, patch_text(add('projects/p/no' + ch + 'tes.md'))))
            cases.append(('control %r in move' % ch, patch_text(update(FREE, move='projects/p/mo' + ch + 'ved.md'))))
        for path in ('file://' + str(self.ws.gars / FREE), 'file:' + FREE, 'http://example.org/x',
                     'https:' + FREE):
            cases.append(('scheme ' + path.split(':')[0], patch_text(add(path))))
        cases.append(('absolute outside the root', patch_text(add(str(self.ws.outside / 'x.txt')))))
        for label, text in cases:
            with self.subTest(case=label):
                verdict = self.codex(text)
                self.assertEqual(verdict.code, 2, verdict)
                self.assertIn('Next:', verdict.err)

    def test_header_trimming_as_codex(self):
        protected, free = PROTECTED[0], FREE
        write = lambda p: self.decide('Write', {'file_path': p, 'content': 'x\n'})
        edit = lambda p: self.decide('Edit', {'file_path': p, 'old_string': 'a', 'new_string': 'b'})
        cases = [
            # Start, Add and Delete modes trim the whole line (ap_streaming.rs process_line).
            ('indented first header, protected', '*** Begin Patch\n   *** Add File: ' + protected + '   \n+x\n*** End Patch\n', write(protected), 2),
            ('indented first header, free', '*** Begin Patch\n\t*** Add File: ' + free + ' \n+x\n*** End Patch\n', write(free), 0),
            ('indented header after Add', patch_text(add(free), ['  *** Add File: ' + protected + '  ', '+y']), write(protected), 2),
            ('indented header after Delete', patch_text(delete(free), ['\t*** Add File: ' + protected, '+y']), write(protected), 2),
            ('indented markers', '  *** Begin Patch  \n*** Add File: ' + free + '\n+x\n   *** End Patch   \n', write(free), 0),
            # Update mode trims only the end of a line (`update_line = line.trim_end()`).
            ('trailing blanks on a header after Update', patch_text(update(free), ['*** Add File: ' + protected + '   ', '+y']), write(protected), 2),
            ('trailing blanks on Move to', patch_text(['*** Update File: ' + free, '*** Move to: ' + protected + '  ', '@@', '-a', '+b']), write(protected), 2),
            # ... so an indented header inside an Update is a context line, not a new entry.
            ('indented header inside Update is context', patch_text(update(free) + ['  *** Add File: ' + protected]), edit(free), 0),
            # The marker's single space is all that is cut: the rest of the path is kept.
            ('second blank after the marker is part of the path', patch_text(['*** Add File:  ' + protected, '+x']), write(' ' + protected), None),
            ('leading blank lines and a trailing newline', '\n\n' + patch_text(add(free)) + '\n', write(free), 0),
        ]
        for label, text, claude, expect in cases:
            with self.subTest(case=label):
                self.same(self.codex(text), claude, expect, label)

    def test_freeform_wrappers(self):
        for wrapper in ('<<EOF', "<<'EOF'", '<<"EOF"'):
            for tail in ('EOF', 'EOF\n'):
                for path, expect in ((PROTECTED[0], 2), (FREE, 0)):
                    with self.subTest(wrapper=wrapper, tail=tail, target=path):
                        text = wrapper + '\n' + patch_text(add(path)) + tail
                        self.same(self.codex(text),
                                  self.decide('Write', {'file_path': path, 'content': 'hello\n'}), expect)

    def test_relative_paths_resolve_against_cwd(self):
        system = self.ws.gars / '_system'
        project = self.ws.gars / 'projects/p'
        for cwd, path, expect in ((system, 'x.py', 2), (project, '../../_system/x.py', 2),
                                  (project, 'notes2.md', 0), (self.ws.gars, 'x.py', 0),
                                  (project, '../c/notes.md', 2)):
            with self.subTest(cwd=str(cwd), target=path):
                self.same(self.codex(patch_text(add(path)), cwd),
                          self.decide('Write', {'file_path': path, 'content': 'hello\n'}, cwd), expect)

    def test_edge_paths(self):
        link = self.ws.gars / 'projects/p/sys'
        if not os.path.lexists(str(link)):
            os.symlink('../../_system', str(link))
        for path, expect in (('projects/p/my notes.md', 0), ('../../x.txt', 2), ('projects/../../x.txt', 2),
                             ('projects/p/sys/x.py', 2), (str(self.ws.gars / FREE), 0),
                             (str(self.ws.gars / PROTECTED[0]), 2)):
            for tool, entry in (('Write', add(path)), ('Edit', update(path))):
                with self.subTest(target=path, entry=entry[0].split(':')[0]):
                    self.same(self.codex(patch_text(entry)),
                              self.decide(tool, {'file_path': path, 'content': 'hello\n',
                                                 'old_string': 'a', 'new_string': 'b'}), expect)


# --- group 4 ----------------------------------------------------------------------------------

class Group04ShellHeredocTests(WorkspaceCase):
    def test_apply_patch_in_shell_refused(self):
        body = patch_text(add(FREE, ['x']), tail='')
        commands = ["apply_patch <<'EOF'\n" + body + '\nEOF', 'applypatch <<EOF\n' + body + '\nEOF',
                    'apply_patch <<"EOF"\n' + body + '\nEOF', "apply_patch '*** Begin Patch'",
                    'bash -lc "apply_patch < change.patch"', 'cat change.patch | applypatch',
                    'apply_patch', 'applypatch']
        for command in commands:
            with self.subTest(command=command):
                claude = decide('Bash', {'command': command}, self.ws.gars, self.ws.gars)
                self.assertEqual(claude.code, 2, claude)
                codex = codex_run(codex_payload('Bash', {'command': command}, self.ws.gars), self.ws.gars)
                self.assertEqual(codex.code, 2, codex)
                self.assertIsNone(codex.result)
                # Decision 0175: exactly one Next, and it names the apply_patch tool.
                self.assertEqual(codex.err.count('Next:'), 1, codex.err)
                self.assertIn('apply_patch', codex.err.split('Next:', 1)[1], codex.err)


# --- group 5 ----------------------------------------------------------------------------------

class Group05RootBindingTests(WorkspaceCase):
    def test_cold_start_from_nested_cwd(self):
        command = self.ws.hooks()['PreToolUse'][0]
        target = str(self.ws.gars / '_system/x.py')
        claude = decide('Write', {'file_path': target, 'content': 'hello\n'}, self.ws.gars, self.ws.gars)
        self.assertTrue(claude.first.startswith(PROTECTED_FIRST), claude)
        for cwd in (self.ws.gars / 'projects/p/00_data', self.ws.gars):
            for shell in ('sh', 'login'):
                with self.subTest(cwd=str(cwd), shell=shell):
                    stdin = as_bytes(apply_patch(patch_text(add(target)), cwd))
                    result = through_shell(shell, command, cwd, stdin, self.ws.home)
                    self.assertEqual(result.code, 2, result)
                    self.assertEqual(result.first, claude.first)


# --- group 6 ----------------------------------------------------------------------------------

class Group06ToolCoverageTests(WorkspaceCase):
    def test_unjudgeable_tools_refused(self):
        for name, data in (('mcp__x__y', {'q': 1}), ('frobnicate', {}), ('web_search', {'query': 'x'}),
                           ('mcp__filesystem__write_file', {'path': FREE, 'content': 'x'})):
            with self.subTest(tool=name):
                verdict = codex_run(codex_payload(name, data, self.ws.gars), self.ws.gars)
                self.assertEqual(verdict.code, 2, verdict)
                self.assertEqual(verdict.err.count('Next:'), 1, verdict.err)

    def test_pass_tools_allowed(self):
        names = list(adapter().PASS_TOOLS)
        self.assertIn('update_plan', names)
        never = {'Bash', 'apply_patch', 'view_image', 'web_search', 'exec_command', 'shell',
                 'local_shell', 'shell_command', 'unified_exec', 'Write', 'Edit', 'Read'}
        for name in names:
            with self.subTest(tool=name):
                self.assertIsInstance(name, str)
                self.assertNotIn(name, never)
                self.assertFalse(name.startswith('mcp__'))
                # The empty-payload edge case: nothing to judge, still allowed.
                verdict = codex_run(codex_payload(name, {}, self.ws.gars), self.ws.gars)
                self.assertEqual(verdict.code, 0, verdict)

    def test_view_image_on_another_filesystem_refused(self):
        # Like a patch's Environment ID: the target filesystem is unknown, so it cannot be judged.
        payload = codex_payload('view_image', {'path': 'projects/p/plot.png', 'environment_id': 'remote-1'},
                                self.ws.gars)
        verdict = codex_run(payload, self.ws.gars)
        self.assertEqual(verdict.code, 2, verdict)
        self.assertIn('Next:', verdict.err)

    def test_view_image_is_a_read(self):
        for path, expect in (('projects/c/plot.png', 2), ('projects/p/plot.png', 0),
                             (str(self.ws.outside / 'plot.png'), 2), ('_system/x.png', 0)):
            with self.subTest(target=path):
                codex = codex_run(codex_payload('view_image', {'path': path}, self.ws.gars), self.ws.gars)
                claude = decide('Read', {'file_path': path}, self.ws.gars, self.ws.gars)
                self.same(codex, claude, expect)


# --- group 7 ----------------------------------------------------------------------------------

class Group07FailClosedTests(WorkspaceCase):
    def bad_inputs(self):
        good = codex_payload('Bash', {'command': 'ls'}, self.ws.gars)
        def without(key):
            value = dict(good)
            del value[key]
            return as_bytes(value)
        return [('empty', b''), ('invalid json', b'not json {'), ('non-utf-8', b'\xff\xfe{"a": 1}'),
                ('non-utf-8 inside a string', b'{"tool_name": "Bash", "x": "\xff"}'),
                ('list', b'[]'), ('null', b'null'),
                ('non-dict tool_input', as_bytes(dict(good, tool_input='ls'))),
                ('list tool_input', as_bytes(dict(good, tool_input=['ls']))),
                ('missing tool_name', without('tool_name')), ('non-str tool_name', as_bytes(dict(good, tool_name=5))),
                ('missing cwd', without('cwd')), ('non-str cwd', as_bytes(dict(good, cwd=5))),
                # Codex always sends an absolute cwd; any other cannot be judged (R-098).
                ('empty cwd', as_bytes(dict(good, cwd=''))), ('relative cwd', as_bytes(dict(good, cwd='projects/p'))),
                ('non-str command', as_bytes(dict(good, tool_input={'command': ['ls']}))),
                ('non-str patch', as_bytes(apply_patch(5, self.ws.gars)))]

    def test_bad_stdin_subprocess(self):
        for label, data in self.bad_inputs():
            with self.subTest(stdin=label):
                result = run_process([sys.executable, self.ws.adapter, 'pre-tool-use'], self.ws.gars,
                                     data, self.ws.home, 'adapter subprocess')
                self.assertEqual(result.code, 2, result)
                self.assertIn('Next:', result.err)

    def test_bad_stdin_in_process(self):
        for label, data in self.bad_inputs():
            with self.subTest(stdin=label):
                verdict = codex_main(data, home=self.ws.home)
                self.assertEqual(verdict.code, 2, verdict)

    def test_guard_import_failure_refuses(self):
        # The import of guard_hook sits inside the adapter's fail-closed net (review r1, R1-3/F2).
        for label, broken in (('guard_hook raises', 'raise RuntimeError("broken guard")\n'),
                              ('guard_hook syntax error', 'def (\n')):
            with tempfile.TemporaryDirectory(prefix='codex-import-') as tmp:
                system = Path(tmp) / '_system'
                system.mkdir()
                shutil.copy2(str(self.ws.adapter), str(system / 'codex_hook.py'))
                (system / 'guard_hook.py').write_text(broken)
                for mode in ('pre-tool-use', 'session-start'):
                    with self.subTest(case=label, mode=mode):
                        result = run_process([sys.executable, system / 'codex_hook.py', mode], self.ws.gars,
                                             as_bytes(codex_payload('Bash', {'command': 'ls'}, self.ws.gars)),
                                             self.ws.home, 'adapter with a broken guard')
                        if mode == 'pre-tool-use':
                            self.assertEqual(result.code, 2, result)
                            self.assertIn('Next:', result.err)
                        else:
                            self.assertEqual(result.code, 0, result)
                            stop = json.loads(result.out)
                            self.assertIs(stop['continue'], False)
                            self.assertIn('Next:', stop['stopReason'])

    def test_injected_crash_in_decide(self):
        hook = adapter()
        stdin = as_bytes(codex_payload('Bash', {'command': 'ls'}, GARS))
        for exc in (RuntimeError('injected'), KeyboardInterrupt(), MemoryError(), RecursionError()):
            def boom(*args, **kwargs):
                raise exc
            with self.subTest(exception=type(exc).__name__):
                with patch.object(guard_hook, 'decide', boom), \
                        patch.object(hook, 'decide', boom, create=True):
                    verdict = codex_main(stdin, home=self.ws.home)
                self.assertEqual(verdict.code, 2, verdict)
                self.assertIn('Next:', verdict.err)


# --- group 8 ----------------------------------------------------------------------------------

class Group08SessionStartPinsTests(unittest.TestCase):
    def session_start(self, ws, cwd=None):
        return run_process([sys.executable, ws.adapter, 'session-start'], cwd or ws.gars, b'',
                           ws.home, 'adapter session-start')

    def pins(self, ws):
        return run_process([sys.executable, ws.gars / '_system/tools/pins.py'], ws.gars, b'',
                           ws.home, 'pins.py')

    def assert_stops(self, ws):
        pins = self.pins(ws)
        self.assertEqual(pins.code, 2, 'pins.py passed: %r' % pins)
        result = self.session_start(ws)
        self.assertEqual(result.code, 0, result)
        expected = json.dumps({'continue': False, 'stopReason': pins.err.strip()})
        self.assertIn(result.out, (expected, expected + '\n'))

    def test_pins_pass_stdout_passes_through(self):
        ws = Workspace()
        self.addCleanup(ws.cleanup)
        self.assertFalse((ws.gars / 'projects/_index.md').exists())  # the cold-start twin
        result = self.session_start(ws)
        self.assertEqual(result.code, 0, result)
        direct = run_process(['bash', ws.gars / '_system/session_state.sh'], ws.gars, b'',
                             ws.home, 'session_state.sh')
        self.assertEqual(direct.code, 0, direct)
        self.assertEqual(result.out, direct.out)
        self.assertIn('R-099: workspace pins reviewed and intact', result.out)
        self.assertNotIn('"continue"', result.out)

    def test_pins_failures_stop_first_turn(self):
        def changed_config(ws):
            with (ws.gars / '.codex/config.toml').open('a') as stream:
                stream.write('\n# changed\n')
        def nested_codex(ws):
            (ws.gars / 'projects/p/.codex').mkdir()
            (ws.gars / 'projects/p/.codex/config.toml').write_text('[features]\nhooks = false\n')
        def unpinned_skill(ws):
            (ws.gars / 'projects/p/SKILL.md').write_text('---\nname: x\n---\n')
        for label, plant in (('unpinned SKILL.md', unpinned_skill),
                             ('changed .codex/config.toml', changed_config),
                             ('extra file in a nested .codex', nested_codex)):
            with self.subTest(failure=label):
                ws = Workspace()
                self.addCleanup(ws.cleanup)
                plant(ws)
                self.assert_stops(ws)

    def test_skill_md_under_codex_and_agents_found(self):
        from support import module
        for folder in ('.codex/skills/x', '.agents/skills/x'):
            with self.subTest(folder=folder):
                ws = Workspace()
                self.addCleanup(ws.cleanup)
                (ws.gars / folder).mkdir(parents=True)
                skill = ws.gars / folder / 'SKILL.md'
                skill.write_text('---\nname: x\n---\n')
                pins = module(ws.gars / '_system/tools/pins.py', 'pins_' + folder.split('/')[0][1:])
                self.assertIn(skill, [Path(p) for p in pins.inventory(ws.gars)])
                self.assert_stops(ws)


# --- group 9 ----------------------------------------------------------------------------------

def keys_in(value):
    if isinstance(value, dict):
        return set(value) | set(k for v in value.values() for k in keys_in(v))
    if isinstance(value, list):
        return set(k for v in value for k in keys_in(v))
    return set()


class Group09WiringTests(WorkspaceCase):
    CLOSED = False

    def test_hooks_json_shape(self):
        data = json.loads((GARS / '.codex/hooks.json').read_text())
        self.assertEqual(set(data['hooks']), {'PreToolUse', 'SessionStart'})
        for event, groups in data['hooks'].items():
            with self.subTest(event=event):
                self.assertTrue(groups)
                for group in groups:
                    self.assertEqual(group.get('matcher'), '.*')
                    self.assertTrue(group['hooks'])
                    for handler in group['hooks']:
                        self.assertEqual(handler.get('type'), 'command')
                        self.assertIsInstance(handler.get('command'), str)
        keys = keys_in(data)
        self.assertNotIn('async', keys)
        self.assertNotIn('timeout', keys)

    def test_commands_match_run_under_both_shells(self):
        hooks = self.ws.hooks()
        gars = self.ws.gars
        payloads = [('protected apply_patch', apply_patch(patch_text(add('_system/x.py')), gars)),
                    ('free apply_patch', apply_patch(patch_text(add(FREE)), gars)),
                    ('allowed Bash', codex_payload('Bash', {'command': 'ls'}, gars)),
                    ('refused Bash', codex_payload('Bash', {'command': 'pip install x'}, gars)),
                    ('unknown tool', codex_payload('mcp__x__y', {}, gars))]
        for label, payload in payloads:
            expected = codex_run(payload, gars)
            for command in hooks['PreToolUse']:
                for shell in ('sh', 'login'):
                    with self.subTest(payload=label, shell=shell):
                        result = through_shell(shell, command, gars, as_bytes(payload), self.ws.home)
                        self.assertEqual(result.code, expected.code, result)
                        if result.code == 2:
                            self.assertEqual(result.first, expected.first)
                        elif expected.result is not None:
                            line = [l for l in result.out.split('\n') if l.strip()][-1]
                            self.assertEqual(json.loads(line), expected.result)
                            if shell == 'sh':
                                self.assertIn(result.out, (json.dumps(expected.result),
                                                           json.dumps(expected.result) + '\n'))
        direct = run_process([sys.executable, self.ws.adapter, 'session-start'], gars, b'',
                             self.ws.home, 'adapter session-start')
        for command in hooks['SessionStart']:
            for shell in ('sh', 'login'):
                with self.subTest(event='SessionStart', shell=shell):
                    result = through_shell(shell, command, gars, as_bytes(dict(
                        codex_payload('', {}, gars), hook_event_name='SessionStart',
                        source='startup')), self.ws.home)
                    self.assertEqual(result.code, 0, result)
                    self.assertTrue(result.out.endswith(direct.out), result.out)
                    self.assertIn('R-099: workspace pins reviewed and intact', result.out)

    def test_no_git_root(self):
        hooks = self.ws.hooks()
        lost = self.ws.tmp / 'nogit/sub'
        lost.mkdir(parents=True)
        payload = as_bytes(codex_payload('Bash', {'command': 'ls'}, lost))
        for shell in ('sh', 'login'):
            for command in hooks['PreToolUse']:
                with self.subTest(event='PreToolUse', shell=shell):
                    result = through_shell(shell, command, lost, payload, self.ws.home)
                    self.assertEqual(result.code, 2, result)
                    self.assertIn('Next:', result.err)
            for command in hooks['SessionStart']:
                with self.subTest(event='SessionStart', shell=shell):
                    result = through_shell(shell, command, lost, b'{}', self.ws.home)
                    self.assertEqual((result.code, result.out), (0, ''), result)

    def test_decoy_adapter_never_reached(self):
        ws = Workspace(closed=False)
        self.addCleanup(ws.cleanup)
        hooks = ws.hooks()
        open1 = ws.project('open1', PUBLIC_ROW)
        (open1 / '_system').mkdir()
        (open1 / '_system/codex_hook.py').write_text('import sys\nsys.exit(0)\n')
        (open1 / '.codex').mkdir()
        (open1 / '.codex/hooks.json').write_text(json.dumps({'hooks': {'PreToolUse': [{
            'matcher': '.*', 'hooks': [{'type': 'command',
                                        'command': 'python3 _system/codex_hook.py pre-tool-use'}]}]}}))
        # An empty planted .git folder (no HEAD) is not a project root for Codex, nor for the launcher.
        (ws.gars / 'projects/p/.git').mkdir()
        target = str(ws.gars / '_system/x.py')
        for cwd in (open1, open1 / '_system', ws.gars / 'projects/p'):
            for shell in ('sh', 'login'):
                with self.subTest(cwd=str(cwd), shell=shell):
                    stdin = as_bytes(apply_patch(patch_text(add(target)), cwd))
                    result = through_shell(shell, hooks['PreToolUse'][0], cwd, stdin, ws.home)
                    self.assertEqual(result.code, 2, result)
                    self.assertTrue(result.first.startswith(PROTECTED_FIRST), result)

    def test_config_toml_disables_web_search(self):
        text = (GARS / '.codex/config.toml').read_text()
        lines = [l.split('#', 1)[0].strip() for l in text.split('\n')]
        lines = [l for l in lines if l]
        self.assertIn('web_search = "disabled"', [re.sub(r'\s*=\s*', ' = ', l) for l in lines])
        # A top-level key: it must come before any [table] header, or it is a nested key.
        first_table = next((i for i, l in enumerate(lines) if l.startswith('[')), len(lines))
        index = [re.sub(r'\s*=\s*', ' = ', l) for l in lines].index('web_search = "disabled"')
        self.assertLess(index, first_table)


# --- group 10 ---------------------------------------------------------------------------------

class Group10NoReplicaTests(unittest.TestCase):
    def test_adapter_defines_no_guard_logic(self):
        source = ADAPTER_SOURCE.read_text()
        for label, pattern in (('READ_ONLY', r'^\s*READ_ONLY\s*='), ('PROTECTED_PREFIXES', r'^\s*PROTECTED_PREFIXES\s*='),
                               ('check_bash', r'\bdef\s+check_bash\b|^\s*check_bash\s*='),
                               ('check_write_tool', r'\bdef\s+check_write_tool\b'),
                               ('fnmatch', r'^\s*(import|from)\s+fnmatch\b|\bfnmatch\s*\.')):
            with self.subTest(replica=label):
                self.assertIsNone(re.search(pattern, source, re.M), label)
        self.assertRegex(source, r'\bdecide\s*\(')
        # The unreadable-call text is the guard's own, byte for byte (review r1, R1-2/F3).
        self.assertEqual(adapter().UNREADABLE, guard_hook.UNREADABLE)
        self.assertRegex(source, re.compile(r'^\s*from guard_hook import (\([^)]*|[^\n(]*)\bdecide\b', re.M),
                         'decide comes from the guard')


# --- group 11 ---------------------------------------------------------------------------------

CODEX_READ = ('.codex/hooks.json', '.codex/config.toml', 'projects/p/.codex/config.toml',
              'AGENTS.override.md', 'projects/p/AGENTS.override.md', '../.codex/config.toml',
              '../AGENTS.override.md', 'projects/p/.git/HEAD', 'projects/p/.git',
              # Codex loads repo skills from .agents/skills/ (review r1, F1).
              '.agents/skills/x/SKILL.md', '.agents/skills/x/agents/openai.yaml',
              'projects/p/.agents/skills/x/SKILL.md', '../.agents/skills/x/SKILL.md')


class Group11ProtectionTests(WorkspaceCase):
    CLOSED = False  # no closed project, so only the protection itself can refuse

    def spellings(self):
        for rel in CODEX_READ:
            yield rel
            yield os.path.normpath(str(self.ws.gars / rel))

    def test_codex_read_files_refused_both_envelopes(self):
        gars = self.ws.gars
        for path in self.spellings():
            write = claude_main('Write', {'file_path': path, 'content': 'x\n'}, gars, gars)
            edit = claude_main('Edit', {'file_path': path, 'old_string': 'a', 'new_string': 'b'}, gars, gars)
            for label, verdict in (('Claude Write', write), ('Claude Edit', edit)):
                with self.subTest(target=path, envelope=label):
                    self.assertEqual(verdict.code, 2, verdict)
                    self.assertIn('Next:', verdict.err)
            for label, entry, claude in (('Codex Add', add(path, ['x']), write),
                                         ('Codex Update', update(path), edit),
                                         ('Codex Delete', delete(path), None),
                                         ('Codex Move to', update(FREE, move=path), None)):
                with self.subTest(target=path, envelope=label):
                    verdict = codex_run(apply_patch(patch_text(entry), gars), gars)
                    self.assertEqual(verdict.code, 2, verdict)
                    if claude is not None:
                        self.assertEqual(verdict.first, claude.first)

    def test_tilde_write_refused_both_envelopes(self):
        path = '~/.codex/config.toml'
        for closed in (False, True):
            ws = self.ws if not closed else Workspace(closed=True)
            if closed:
                self.addCleanup(ws.cleanup)
            for label, call in (
                    ('Claude Write', lambda: claude_main('Write', {'file_path': path, 'content': 'x\n'},
                                                         ws.gars, ws.gars, ws.home)),
                    ('Claude Edit', lambda: claude_main('Edit', {'file_path': path, 'old_string': 'a',
                                                                 'new_string': 'b'}, ws.gars, ws.gars, ws.home)),
                    ('Codex Add', lambda: codex_run(apply_patch(patch_text(add(path)), ws.gars),
                                                    ws.gars, ws.home)),
                    ('Codex Update', lambda: codex_run(apply_patch(patch_text(update(path)), ws.gars),
                                                       ws.gars, ws.home))):
                with self.subTest(envelope=label, closed_project=closed):
                    verdict = call()
                    self.assertEqual(verdict.code, 2, verdict)
                    self.assertIn('inside the workspace root', verdict.first)
            self.assertFalse((ws.home / '.codex').exists())

    def test_tilde_read_refused_both_envelopes(self):
        gars, home = self.ws.gars, self.ws.home
        for label, call in (
                ('Claude Read', lambda: claude_main('Read', {'file_path': '~/x.txt'}, gars, gars, home)),
                ('Claude Grep', lambda: claude_main('Grep', {'pattern': 'x', 'path': '~/'}, gars, gars, home)),
                ('Claude Glob', lambda: claude_main('Glob', {'pattern': '*', 'path': '~'}, gars, gars, home)),
                ('Codex view_image', lambda: codex_run(codex_payload('view_image', {'path': '~/x.txt'}, gars),
                                                       gars, home))):
            with self.subTest(envelope=label):
                verdict = call()
                self.assertEqual(verdict.code, 2, verdict)
                self.assertIn('outside the workspace', verdict.first)


# --- group 12 ---------------------------------------------------------------------------------

class Group12WorkdirPinTests(WorkspaceCase):
    def test_allowed_bash_rewritten(self):
        spaced = self.ws.gars / 'projects/p/my dir'
        spaced.mkdir(exist_ok=True)
        for cwd, command in ((self.ws.gars, 'ls'), (spaced, 'ls'), (self.ws.gars, 'cat CONTEXT.md'),
                             (self.ws.gars / 'projects/p', 'ls 00_data')):
            with self.subTest(cwd=str(cwd), command=command):
                self.assertEqual(decide('Bash', {'command': command}, cwd, self.ws.gars).code, 0)
                verdict = codex_run(codex_payload('Bash', {'command': command}, cwd), self.ws.gars)
                self.assertEqual((verdict.code, verdict.result), (0, rewrite(cwd, command)), verdict)
        # Through main, stdout is exactly the rewrite JSON.
        payload = codex_payload('Bash', {'command': 'ls'}, spaced)
        result = run_process([sys.executable, self.ws.adapter, 'pre-tool-use'], spaced,
                             as_bytes(payload), self.ws.home, 'adapter subprocess')
        exact = json.dumps(rewrite(spaced, 'ls'))
        self.assertEqual(result.code, 0, result)
        self.assertIn(result.out, (exact, exact + '\n'))
        self.assertIn("cd -- '", exact)  # the space forces shlex quoting

    def test_own_prefix_not_wrapped_twice(self):
        gars = self.ws.gars
        prefix = 'cd -- ' + shlex.quote(str(gars)) + ' && '
        verdict = codex_run(codex_payload('Bash', {'command': prefix + 'ls'}, gars), gars)
        self.assertEqual((verdict.code, verdict.result), (0, rewrite(gars, 'ls')), verdict)
        for remainder in ('pip install x', prefix + 'ls', 'ls projects/c'):
            with self.subTest(remainder=remainder):
                codex = codex_run(codex_payload('Bash', {'command': prefix + remainder}, gars), gars)
                self.same(codex, decide('Bash', {'command': remainder}, gars, gars), 2)

    def test_other_prefix_judged_as_written(self):
        gars = self.ws.gars
        for command in ('cd -- ' + shlex.quote(str(gars / '_system')) + ' && ls',
                        'cd -- ' + shlex.quote(str(gars / 'projects/c')) + ' && ls',
                        'cd -- ' + shlex.quote(str(gars) + '/') + ' && ls',
                        'cd ' + shlex.quote(str(gars)) + ' && ls',
                        'cd "' + str(gars) + '" && ls',
                        'cd -- ' + shlex.quote(str(gars)) + ' ; ls'):
            with self.subTest(command=command):
                codex = codex_run(codex_payload('Bash', {'command': command}, gars), gars)
                self.same(codex, decide('Bash', {'command': command}, gars, gars), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
