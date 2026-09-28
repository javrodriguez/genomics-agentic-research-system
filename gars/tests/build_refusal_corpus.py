"""Harvest public main 868a1b2's direct guard calls and replay their decisions without running tools.

Payloads retain json.dumps formatting with explicit portable path placeholders.
Snapshots and shared file text are plain JSON; replay binds placeholders at runtime.
Gzip fixture inputs are stored as readable decompressed text and rebuilt on replay.
"""
import gzip
from collections import defaultdict, deque
import getpass
import contextlib
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import re

from support import GARS, REPO
from tools import policy
import guard_hook

SOURCES = ('test_policy_attacks', 'test_guard_hook', 'test_policy_faults',
           'test_nonpublic_read_block', 'test_pilot_doors', 'test_tool_schema_refusal',
           'test_bash_lexer', 'test_fs_vocabulary')
FIXTURE = Path(__file__).parent / 'fixtures/refusal_decisions.jsonl'
KEYS = ('exit', 'type', 'field', 'rule')


def decision(code, text):
    record = {}
    if text.startswith('Blocked: {'):
        try:
            record = json.JSONDecoder().raw_decode(text[len('Blocked: '):])[0]
        except ValueError:
            pass
    return dict(zip(KEYS, (code, record.get('type'), record.get('field'), record.get('rule'))))


def judge(payload, root):
    output = io.StringIO()
    with patch.dict(os.environ, {'CLAUDE_PROJECT_DIR': str(root)}), \
            patch.object(sys, 'stdin', io.StringIO(payload)), contextlib.redirect_stderr(output):
        try:
            guard_hook.main()
        except SystemExit as exc:
            code = exc.code
    return decision(code, output.getvalue()), output.getvalue()


def dispatch_judge(payload, root):
    """Dispatcher refusal path only: parse and authorize; never argv_for or execution."""
    try:
        value = json.loads(payload)
    except ValueError:
        return None, ''
    if not isinstance(value, dict) or value.get('tool_name') != 'Bash':
        return None, ''
    try:
        tokens = policy.simple_tokens(value['tool_input'].get('command'))
        tool, args = policy.parse_argv(tokens, root, value.get('cwd') or root)
        policy.authorize(tool, args, 'producer', root, value.get('cwd') or root)
    except policy.Refusal as exc:
        text = 'Blocked: ' + json.dumps(exc.record(), sort_keys=True)
        return decision(2, text), text
    return decision(0, ''), ''


def snapshot(root):
    root = Path(root).resolve()
    scratch = Path(os.environ['TMPDIR']).resolve()
    if root == GARS.resolve():
        return {'root': str(root), 'top': str(root), 'repo': True, 'entries': []}
    relative = root.relative_to(scratch)
    top = scratch / relative.parts[0]
    entries = []
    def visit(folder):
        for p in sorted(folder.iterdir()):
            rel = str(p.relative_to(top))
            if p.name in ('__pycache__', '.git') or p.suffix == '.pyc':
                continue
            # Round 6 proved these captured pilot outputs do not affect guard decisions.
            # Exclude the files themselves so cache hashes never enter the public fixture.
            pilot_output = 'prepared/gars/projects/pilot/02_bioinformatics/rnaseq_bulk/02_rnaseq-de/'
            if rel in (pilot_output + 'submit.sh', pilot_output + 'reproducibility/manifest.json'):
                continue
            if p.is_symlink():
                entries.append([rel, 'link', os.readlink(str(p))])
            elif p.is_dir():
                entries.append([rel, 'dir', ''])
                # System code is never fixture state; preserve its path names separately.
                if p.name not in ('_system', '_templates', '_references', '.claude'):
                    visit(p)
            elif p.is_file():
                if '_system' in p.relative_to(top).parts:
                    entries.append([rel, 'file', ''])
                else:
                    raw = p.read_bytes()
                    kind = 'file'
                    if raw.startswith(bytes((31, 139))):
                        raw, kind = gzip.decompress(raw), 'gzip'
                    entries.append([rel, kind, raw.decode('utf-8', errors='surrogateescape')])
    visit(top)
    return {'root': str(root), 'top': str(top), 'repo': False, 'entries': entries}


def relocate(text, bindings):
    for before, after in sorted(bindings, key=lambda pair: -len(pair[0])):
        text = text.replace(before, after)
    return text


def portable(state, payload):
    """Replace machine roots before hashing or serializing any captured content."""
    root, top = state['root'], state['top']
    bindings = [(root, '<GARS_ROOT>'), (top, '<SCRATCH_ROOT>'),
                (str(GARS.resolve()), '<SOURCE_GARS>'), (str(REPO.resolve()), '<REPO_ROOT>'),
                (str(Path(os.environ['TMPDIR']).resolve()), '<JOB_SCRATCH>'),
                (str(Path.home().resolve()), '<HOME_ROOT>'),
                (getpass.getuser(), '<USER_NAME>')]
    # The first binding wins where the captured workspace is also a source root.
    unique = {}
    for before, after in bindings:
        unique.setdefault(before, after)
    def text(value):
        value = relocate(value, list(unique.items())).replace(chr(126), '<TILDE>')
        # Any remaining rooted fixture path uses the filesystem-root token.
        return re.sub(r'(?<![A-Za-z0-9_.<>/-])/', '<SYSTEM_ROOT>/', value)
    result = {'repo': state['repo'], 'root_relative': str(Path(root).relative_to(top)),
              'entries': [[text(name), kind, text(value)] for name, kind, value in state['entries']]}
    return result, text(payload)


def replay_bindings(state, destination):
    top = destination / 'tree'
    root = GARS if state['repo'] else top / state['root_relative']
    bindings = [('<GARS_ROOT>', str(root)), ('<SCRATCH_ROOT>', str(top)),
                ('<SOURCE_GARS>', str(GARS)), ('<REPO_ROOT>', str(REPO)),
                ('<JOB_SCRATCH>', str(Path(tempfile.gettempdir()).resolve())),
                ('<HOME_ROOT>', str(Path.home().resolve())), ('<USER_NAME>', getpass.getuser()),
                ('<SYSTEM_ROOT>', os.sep.rstrip(os.sep)), ('<TILDE>', chr(126))]
    return str(root), bindings


def materialize(state, destination):
    root, bindings = replay_bindings(state, destination)
    top = destination / 'tree'
    if not state['repo']:
        top.mkdir()
        for relative, kind, value in state['entries']:
            p = top / relocate(relative, bindings)
            p.parent.mkdir(parents=True, exist_ok=True)
            if kind == 'dir':
                p.mkdir(exist_ok=True)
            elif kind == 'link':
                p.symlink_to(relocate(value, bindings))
            else:
                raw = relocate(value, bindings).encode('utf-8', errors='surrogateescape')
                if kind == 'gzip':
                    with p.open('wb') as stream, gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as zipped:
                        zipped.write(raw)
                else:
                    p.write_bytes(raw)
    return str(root), bindings


def rows():
    contexts, texts = {}, {}
    with FIXTURE.open() as stream:
        for line in stream:
            row = json.loads(line)
            texts.update(row.get('file_texts', {}))
            if 'snapshot' in row:
                state = dict(row['snapshot'])
                state['entries'] = [[name, kind, texts[value] if kind in ('file', 'gzip') else value]
                                    for name, kind, value in state['entries']]
                contexts[row['context']] = state
            yield row, contexts[row['context']]


def replay():
    """Reuse adjacent identical snapshots, binding portable payload templates to scratch paths."""
    previous = None
    temporary = None
    try:
        for row, state in rows():
            if row['context'] != previous:
                if temporary is not None:
                    temporary.cleanup()
                temporary = tempfile.TemporaryDirectory(prefix='refusal-replay-')
                root, bindings = materialize(state, Path(temporary.name).resolve())
                previous = row['context']
            payload = relocate(row['payload'], bindings)
            actual, text = judge(payload, root)
            dispatched, rendered = dispatch_judge(payload, root)
            yield row, actual, text, dispatched, rendered
    finally:
        if temporary is not None:
            temporary.cleanup()


def pin():
    counts = {}
    allowed = refused = 0
    for row, actual, text, dispatched, rendered in replay():
        assert actual == {key: row[key] for key in KEYS}, (row['name'], actual, text)
        assert dispatched == row['dispatcher'], (row['name'], dispatched, rendered)
        counts[row['source']] = counts.get(row['source'], 0) + 1
        allowed += actual['exit'] == 0
        refused += actual['exit'] == 2
    for source in SOURCES + ('registry', 'reported'):
        assert counts.get(source, 0), source
        print('corpus %s: %d rows' % (source, counts[source]), flush=True)
    print('decision pin: %d refused, %d allowed; OK' % (refused, allowed), flush=True)


def build():
    # Generate only from the pinned public system tree, with the current capture code.
    diff = subprocess.check_output(['git', '-C', str(REPO), 'diff', '868a1b2019e8b5824c8aa0874dd292c53691160c', '--', 'gars/_system'])
    assert not diff, 'generate only against the unchanged 868a1b2 system'
    # Retain row identities when a source inserts new calls between existing ones.
    prior_names = defaultdict(deque)
    reserved_names = set()
    if FIXTURE.exists():
        for line in FIXTURE.read_text().splitlines():
            row = json.loads(line)
            prior_names[(row['source'], row['payload'])].append(row['name'])
            reserved_names.add(row['name'])
    real_run = subprocess.run
    real_validate = policy.validate_args
    seen = set()
    file_texts = set()
    output = []
    source = [None]
    active = [False]
    def capture(payload, root, name):
        if active[0]:
            return
        active[0] = True
        try:
            state = snapshot(root)
            state, template = portable(state, payload)
            previous = prior_names[(source[0], template)]
            if previous:
                name = previous.popleft()
            elif name in reserved_names:
                name = '%s-added-%d' % (source[0], len(output))
            new_texts = {}
            for entry in state['entries']:
                if entry[1] in ('file', 'gzip'):
                    value = entry[2]
                    key = hashlib.sha256(value.encode('utf-8', errors='surrogateescape')).hexdigest()
                    if key not in file_texts:
                        new_texts[key] = value
                        file_texts.add(key)
                    entry[2] = key
            digest = hashlib.sha256(json.dumps(state, sort_keys=True).encode()).hexdigest()
            expected, rendered = judge(payload, root)
            dispatched, _ = dispatch_judge(payload, root)
            row = dict(expected, payload=template, source=source[0], name=name,
                       context=digest, dispatcher=dispatched)
            if digest not in seen:
                row['snapshot'] = state
                seen.add(digest)
            if new_texts:
                row['file_texts'] = new_texts
            output.append(row)
            return expected, rendered
        finally:
            active[0] = False
    def intercepted(argv, *args, **kwargs):
        words = [str(w) for w in argv] if isinstance(argv, (list, tuple)) else []
        if len(words) > 1 and words[1].endswith('guard_hook.py') and 'input' in kwargs:
            raw = kwargs['input']
            raw = raw.decode() if isinstance(raw, bytes) else raw
            root = kwargs.get('env', os.environ).get('CLAUDE_PROJECT_DIR', str(GARS))
            captured = capture(raw, root, '%s-%d' % (source[0], len(output)))
            hook = Path(words[1])
            if hook.read_bytes() == (GARS / '_system/guard_hook.py').read_bytes():
                expected, rendered = captured
                return subprocess.CompletedProcess(argv, expected['exit'], b'', rendered.encode())
        return real_run(argv, *args, **kwargs)
    def validated(tool, args, root=policy.WORKSPACE, cwd=None):
        if source[0] == 'test_tool_schema_refusal' and not active[0]:
            command = 'python3 _system/tool_call.py ' + tool['name'] + ' ' + shlex.quote(json.dumps(args))
            capture(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command},
                                'cwd': str(cwd or root)}), root, 'schema-%d' % len(output))
        return real_validate(tool, args, root, cwd)
    with patch.object(subprocess, 'run', intercepted), patch.object(policy, 'validate_args', validated):
        for name in SOURCES:
            source[0] = name
            module = importlib.import_module(name)
            result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
            assert result.wasSuccessful(), 'baseline harvest tests failed: ' + name
    source[0] = 'registry'
    def bash(command, name):
        capture(json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command},
                            'cwd': str(GARS)}), GARS, name)
    for tool in policy.registry():
        prefix = ' '.join(shlex.quote(s) for s in tool['argv'])
        bash(prefix, tool['name'] + '-bare')
        if tool.get('filesystem'):
            for flag in tool['input_schema']['properties']['flags']['items']['enum'] + ['--undeclared']:
                suffix = ' 256' if tool['name'] == 'fs.checksum' and flag == '-a' else ''
                suffix += ' x' if 'pattern' in tool['input_schema']['properties'] else ''
                bash(prefix + ' ' + flag + suffix + ' CONTEXT.md', tool['name'] + '-' + flag)
        else:
            for key, cli in tool['cli'].items():
                if cli['flag']:
                    bash(prefix + ' ' + cli['flag'], tool['name'] + '-' + key)
            bash(prefix + ' --undeclared', tool['name'] + '-undeclared')
            for key in tool['input_schema'].get('required', []):
                bash('python3 _system/tool_call.py ' + tool['name'] + " '{}'", tool['name'] + '-missing-' + key)
    source[0] = 'reported'
    outside = os.path.join(str(Path(os.environ['TMPDIR']).resolve()), 'background-output.txt')
    capture(json.dumps({'tool_name': 'Read', 'tool_input': {'file_path': outside},
                        'cwd': str(GARS)}), GARS, 'background-native')
    bash('cat ' + shlex.quote(outside), 'background-cat')
    bash('grep -n a CONTEXT.md | head', 'operator')
    bash('ls -R', 'vocabulary')
    bash('python3 _system/unregistered.py', 'unregistered')
    capture(json.dumps({'tool_name': 'Write', 'tool_input': {'file_path': 'projects/p/STATUS'},
                        'cwd': str(GARS)}), GARS, 'status')
    for char in ('$', '`', '\n', '#', '{', chr(126), '('):
        bash('grep ' + char + ' CONTEXT.md', 'lexer-' + str(ord(char)))
    # Append coverage without renaming or reordering any previously pinned row.
    source[0] = 'registry'
    for tool in policy.registry():
        if tool.get('filesystem'):
            prefix = ' '.join(shlex.quote(word) for word in tool['argv'])
            pattern = ' x' if 'pattern' in tool['input_schema']['properties'] else ''
            bash(prefix + pattern + ' _system _references', tool['name'] + '-two-paths')
            if tool['argv'][0] == 'find':
                bash(prefix + ' _system -name CONTEXT.md', tool['name'] + '-expression')
    for tool in policy.registry():
        predicates = tool.get('predicates', {})
        for predicate, pattern in sorted(predicates.items()):
            good = next(value for value in ('1', 'f', 'x') if re.fullmatch(pattern, value))
            bad = next(value for value in ('-delete', 'a/b', '-1', 'l')
                       if not re.fullmatch(pattern, value))
            for label, value in (('valid', good), ('invalid', bad)):
                bash(tool['argv'][0] + ' . ' + predicate + ' ' + shlex.quote(value),
                     tool['name'] + '-predicate-' + predicate + '-' + label)
        if predicates:
            bash(tool['argv'][0] + ' . --undeclared x', tool['name'] + '-predicate-undeclared')
    source[0] = 'reported'
    bash("python3 _system/tool_call.py fs.nosuch '{}'", 'unknown-typed-tool')
    bash('grep -n hooks.gitleaks false.txt', 'read-gitleaks-false')
    FIXTURE.parent.mkdir(exist_ok=True)
    with FIXTURE.open('w') as stream:
        for row in output:
            line = json.dumps(row, sort_keys=True)
            stream.write(line + '\n')
    print('harvested %d payloads in %d contexts' % (len(output), len(seen)), flush=True)


if __name__ == '__main__':
    if '--check' in sys.argv:
        pin()
    else:
        build()
