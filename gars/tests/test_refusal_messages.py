"""Text-only guard lane: immutable decisions and actionable refusal messages."""
import ast
import base64
import binascii
import contextlib
import getpass
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import zlib
import unittest
from unittest.mock import patch

from support import GARS
import build_refusal_corpus as corpus
from tools import policy
import tool_call

# No generic fs.read CONTEXT.md alternative is needed by this lane's refusal sites.
GENUINE_CONTEXT_READS = set()
OLD_ALTERNATIVE = 'python3 _system/tool_call.py fs.read ' + "'{\"paths\":[\"CONTEXT.md\"]}'"


def strings(node):
    return [n.s for n in ast.walk(node) if isinstance(n, ast.Str)]


def has_next(node, assignments, functions, seen=None):
    """Follow message constants and renderers, including the structured refusal relay."""
    seen = set() if seen is None else seen
    if any('Next: ' in value and value.split('Next: ', 1)[1].strip() for value in strings(node)):
        return True
    if isinstance(node, ast.BinOp) and 'Next: ' in strings(node):
        calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
        if any(isinstance(n.func, ast.Name) and n.func.id in functions and
               any(value.strip() for value in strings(functions[n.func.id])) for n in calls):
            return True
    for item in ast.walk(node):
        if isinstance(item, ast.Name) and item.id not in seen:
            targets = assignments.get(item.id, [])
            if targets and any(has_next(t, assignments, functions, seen | {item.id}) for t in targets):
                return True
        if isinstance(item, ast.Call):
            if isinstance(item.func, ast.Name) and item.func.id in functions and item.func.id not in seen:
                returns = [n.value for n in ast.walk(functions[item.func.id])
                           if isinstance(n, ast.Return) and n.value is not None
                           and not (isinstance(n.value, ast.NameConstant) and n.value.value is None)]
                if returns and all(has_next(r, assignments, functions, seen | {item.func.id}) for r in returns):
                    return True
            if isinstance(item.func, ast.Attribute) and item.func.attr == 'record':
                # JSON relay: the site's Refusal alternative is checked independently below.
                return True
    return False


class RefusalMessagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results = list(corpus.replay())

    def test_01_decision_pin(self):
        counts = {}
        allowed = refused = 0
        for row, actual, text, dispatched, rendered in self.results:
            self.assertEqual(actual, {key: row[key] for key in corpus.KEYS}, row['name'])
            self.assertEqual(dispatched, row['dispatcher'], row['name'])
            counts[row['source']] = counts.get(row['source'], 0) + 1
            allowed += actual['exit'] == 0
            refused += actual['exit'] == 2
        for source in corpus.SOURCES + ('registry', 'reported'):
            self.assertGreater(counts.get(source, 0), 0)
            print('corpus %s: %d rows' % (source, counts[source]), flush=True)
        print('decision pin: %d refused, %d allowed; OK' % (refused, allowed), flush=True)

    def test_02_static_next_steps(self):
        for relative in ('guard_hook.py', 'tools/policy.py', 'tool_call.py'):
            tree = ast.parse((GARS / '_system' / relative).read_text())
            assignments = {}
            functions = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
            for n in ast.walk(tree):
                if isinstance(n, ast.Assign):
                    for target in n.targets:
                        if isinstance(target, ast.Name):
                            assignments.setdefault(target.id, []).append(n.value)
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name):
                    continue
                with self.subTest(file=relative, line=n.lineno):
                    if n.func.id == 'Refusal':
                        alternatives = [k.value for k in n.keywords if k.arg == 'alternative']
                        self.assertEqual(len(alternatives), 1, 'site needs alternative=')
                        self.assertTrue(has_next(alternatives[0], assignments, functions),
                                        'alternative needs a nonempty Next: action')
                    elif n.func.id == 'deny':
                        self.assertTrue(has_next(n.args[0], assignments, functions),
                                        'deny needs a nonempty Next: action')

    def check_next(self, decision, text):
        self.assertEqual(text.count('Next: '), 1, text)
        self.assertTrue(text.split('Next: ', 1)[1].strip(), text)
        if (decision['rule'], decision['field']) not in GENUINE_CONTEXT_READS:
            self.assertNotIn(OLD_ALTERNATIVE, text)
        # Detect the legacy suffix even if a site's new action appears before it.
        self.assertNotIn('Use typed call: ' + OLD_ALTERNATIVE, text)
        self.assertNotIn('Rule R-092/R-094/R-098', text)

    def test_03_dynamic_next_steps(self):
        for row, actual, text, dispatched, rendered in self.results:
            with self.subTest(row=row['name']):
                if actual['exit'] == 2:
                    self.check_next(actual, text)
                if dispatched and dispatched['exit'] == 2:
                    self.check_next(dispatched, rendered)

    def test_04_approval_store_is_not_a_generic_path(self):
        for row, actual, text, dispatched, rendered in self.results:
            with self.subTest(row=row['name']):
                if '.gars-approvals' not in row['payload'] and 'PLAN.md.approved' not in row['payload']:
                    self.assertNotIn('approval store', text + rendered)

    def test_05_record_rule_is_cited(self):
        for row, actual, text, dispatched, rendered in self.results:
            for result, output in ((actual, text), (dispatched, rendered)):
                if result and result['type'] == 'tool_refusal':
                    with self.subTest(row=row['name'], rule=result['rule']):
                        record = json.JSONDecoder().raw_decode(output[len('Blocked: '):])[0]
                        self.assertEqual(set(record), {'type', 'field', 'rule', 'message', 'source', 'alternative'})
                        self.assertIn(record['rule'], record['message'])
                        cited = set(re.findall(r'R-[0-9]{3}', record['message']))
                        self.assertTrue(cited == {record['rule']} or
                                        'R-073 (recorded as R-094)' in record['message'])

    def test_06_reported_rows(self):
        named = {row['name']: (actual, text) for row, actual, text, _, _ in self.results
                 if row['source'] == 'reported'}
        for name in ('background-native', 'background-cat'):
            result, text = named[name]
            self.assertEqual(result['exit'], 2)
            self.assertIn('is outside the workspace (', text)
            self.assertIn('a session reads only inside it', text)
            self.assertIn("command's background output", text)
            self.assertIn('run that command in the foreground', text)
            self.assertIn('decision 0160', text)
        result, text = named['background-cat']
        self.assertEqual(result['field'], 'args.paths')
        self.assertEqual(result['rule'], 'R-094')
        self.assertIn('R-073 (recorded as R-094)', text)
        result, text = named['operator']
        self.assertEqual(result['exit'], 2)
        self.assertEqual(result['field'], 'command')
        self.assertIn('one command per call: run each step as its own call', text)
        result, text = named['vocabulary']
        self.assertEqual(result['exit'], 2)
        self.assertEqual(result['field'], 'args.flags[0]')
        for flag in ('-a', '-l', '-la', '-al'):
            self.assertIn(flag, text)
        result, text = named['status']
        self.assertEqual(result['exit'], 2)
        self.assertEqual(text.count('Use typed call'), 1)
        self.assertEqual(text.count('Next: '), 1)

    def test_09_review_reported_rows(self):
        named = {row['name']: (actual, text) for row, actual, text, _, _ in self.results
                 if row['source'] == 'reported'}
        for name, phrase in (
                ('unknown-typed-tool', 'the tool name is not registered'),
                ('read-gitleaks-false', 'this command contains hooks.gitleaks and false')):
            with self.subTest(row=name):
                self.assertIn(name, named)
                result, text = named[name]
                self.assertEqual(result['exit'], 2)
                self.assertIn(phrase, text)
                self.assertEqual(text.count('Next: '), 1)

    def test_07_registry_drives_advice(self):
        tool = policy.named('fs.list')
        with self.assertRaises(policy.Refusal) as ctx:
            policy.validate(['invented'], {'type': 'array', 'items': {'type': 'string', 'enum': ['fixture-flag']}})
        self.assertIn('fixture-flag', str(ctx.exception))
        amended = dict(tool, name='fs.fixture', argv=['fixture-command'])
        with patch.object(policy, 'registry', return_value=[amended]):
            with self.assertRaises(policy.Refusal) as ctx:
                policy.parse_argv(['not-registered'])
        text = json.dumps(ctx.exception.record())
        self.assertIn('fixture-command', text)
        self.assertIn("or a typed call, python3 _system/tool_call.py <tool> '<json>', "
                      "for a tool named in _system/tools/registry.json", text)
        self.assertNotIn('fs.fixture', text)
        self.assertEqual(ctx.exception.field, 'command')
        self.assertEqual(ctx.exception.rule, 'R-092')

    def test_08_execution_wrapper(self):
        output = io.StringIO()
        with patch.object(tool_call.subprocess, 'run', side_effect=OSError('fixture')), \
                contextlib.redirect_stdout(output):
            self.assertEqual(tool_call.main(['stage00_register.assays', '{}']), 2)
        record = json.loads(output.getvalue())
        self.assertEqual((record['type'], record['field'], record['rule']),
                         ('tool_refusal', 'execution', 'R-092'))
        self.check_next(dict(rule=record['rule'], field=record['field']), output.getvalue())
        self.assertIn('R-092', record['message'])


class ReplayBindingsTests(unittest.TestCase):
    def test_without_temp_environment(self):
        # Resolve the active scratch cache before removing environment overrides.
        scratch = Path(tempfile.gettempdir()).resolve()
        original = dict(os.environ)
        absent = {key: value for key, value in original.items()
                  if key not in ('TMPDIR', 'TEMP', 'TMP')}
        with patch.dict(os.environ, absent, clear=True):
            for key in ('TMPDIR', 'TEMP', 'TMP'):
                self.assertNotIn(key, os.environ)
            for repository in (False, True):
                with self.subTest(repository=repository):
                    state = {'repo': repository, 'root_relative': 'workspace'}
                    destination = scratch / 'bindings-without-environment'
                    root, bindings = corpus.replay_bindings(state, destination)
                    self.assertEqual(dict(bindings)['<JOB_SCRATCH>'], str(scratch))
                    expected = GARS if repository else destination / 'tree/workspace'
                    self.assertEqual(root, str(expected))
                    payload = json.dumps({'cwd': '<GARS_ROOT>', 'tool_name': 'Read',
                                          'tool_input': {'file_path': '<JOB_SCRATCH>/output'}})
                    bound = json.loads(corpus.relocate(payload, bindings))
                    self.assertEqual(bound['cwd'], str(expected))
                    self.assertEqual(bound['tool_input']['file_path'], str(scratch / 'output'))
        self.assertEqual(dict(os.environ), original)


class ReviewMessageTests(unittest.TestCase):
    def bash(self, command):
        payload = json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command},
                              'cwd': str(GARS)})
        return corpus.judge(payload, GARS)

    def test_unknown_typed_tool(self):
        for argument in ("'{}'", "'{'"):
            with self.subTest(argument=argument):
                result, text = self.bash('python3 _system/tool_call.py fs.nosuch ' + argument)
                self.assertEqual(result, dict(exit=2, type='tool_refusal', field='args', rule='R-092'))
                self.assertIn('the tool name is not registered', text)
                self.assertIn('Next: ', text)
                self.assertIn("python3 _system/tool_call.py <tool> '<json>'", text)
                self.assertIn('_system/tools/registry.json', text)
                self.assertNotIn('could not read JSON arguments', text)
        result, text = self.bash("python3 _system/tool_call.py fs.read '{'")
        self.assertEqual(result, dict(exit=2, type='tool_refusal', field='args', rule='R-092'))
        self.assertIn('could not read JSON arguments', text)

    def test_read_containing_no_verify(self):
        result, text = self.bash('grep -n --no-verify CONTEXT.md')
        self.assertEqual(result, dict(exit=2, type=None, field=None, rule=None))
        self.assertIn('this command contains --no-verify, which can disable', text)
        self.assertIn('(R-096, spec', text)
        self.assertIn('Next: commit and push normally; the secret scan runs by itself.', text)

    def test_read_containing_gitleaks_false(self):
        result, text = self.bash('grep -n hooks.gitleaks false.txt')
        self.assertEqual(result, dict(exit=2, type=None, field=None, rule=None))
        self.assertIn('this command contains hooks.gitleaks and false, a combination that can disable', text)
        self.assertIn('(R-096, spec', text)
        self.assertIn('Next: commit and push normally; the secret scan runs by itself.', text)


class FixturePrivacyTests(unittest.TestCase):
    def test_fixture_is_readable_and_portable(self):
        raw = corpus.FIXTURE.read_text()
        escapes = re.findall(r'\\u([0-9a-fA-F]{4})', raw)
        self.assertFalse(any(32 <= int(value, 16) <= 126 for value in escapes),
                         'printable ASCII must be stored literally')
        self.assertIsNone(re.search(r'[A-Za-z0-9+/]{81,}={0,2}', raw),
                          'fixture must not contain encoded blobs')
        forbidden = (str(Path.home().resolve()), str(GARS.parent.resolve()),
                     str(Path(tempfile.gettempdir()).resolve()), getpass.getuser())
        def check(value):
            if isinstance(value, str):
                self.assertFalse(any(part in value for part in forbidden),
                                 'fixture contains a machine-specific path')
            elif isinstance(value, dict):
                for key, item in value.items():
                    check(key)
                    check(item)
            elif isinstance(value, list):
                for item in value:
                    check(item)
        malformed = {'test_guard_hook-36', 'test_guard_hook-37'}
        nonobjects = {'test_guard_hook-38': list, 'test_guard_hook-39': type(None)}
        count = 0
        for row, state in corpus.rows():
            check(row)
            if 'snapshot' in row:
                self.assertIsInstance(row['snapshot'], dict)
            payload = row['payload']
            # Substitution changes path values, never the hook payload's keys.
            _, bindings = corpus.replay_bindings(
                state, Path(tempfile.gettempdir()).resolve() / 'privacy-substitution')
            substituted = corpus.relocate(payload, bindings)
            if row['name'] in malformed:
                with self.assertRaises(ValueError):
                    json.loads(substituted)
                continue
            before, after = json.loads(payload), json.loads(substituted)
            if row['name'] in nonobjects:
                self.assertIsInstance(after, nonobjects[row['name']])
                continue
            self.assertIsInstance(after, dict)
            self.assertEqual(set(before), set(after), row['name'])
            count += 1
        self.assertEqual(count, 2175)


    def test_whole_fixture_recursive_privacy(self):
        started = time.monotonic()
        owner_digests = (
            (9, 'bac473d0af940b322f6fe80865c652959a89a034118c549e938749a5e8419845'),
            (8, 'ccacea157c077347b0df2cd1b2b86c56b6ed026bc151a5720ae0fb8a1194a5f5'),
            (12, '721b8463858b809171679895bd5bae7a6f247ded1e4235dbbe801b0ad97c9d85'),
            (24, '2f3b96061b6ba87e9a1b8a40c6ebda451861e17e17f92b9b7a9cda55a039b932'),
        )
        targets = [(length, bytes.fromhex(digest)) for length, digest in owner_digests]
        runtime = tuple(value.lower() for value in
                        (str(Path.home()), str(GARS.parent.resolve()), getpass.getuser()) if value)
        slash = re.escape(chr(47))
        homes = re.compile(slash + '(?:users|home)' + slash + '([a-z0-9._-]+)')
        text_cache, folded_cache = {}, {}
        counts = {'strings': 0, 'decoded_blobs': 0, 'zlib_blobs': 0}
        sha256 = hashlib.sha256

        def walk(value):
            found = set()
            if isinstance(value, str):
                found.update(scan(value))
            elif isinstance(value, dict):
                for key, item in value.items():
                    found.update(scan(key))
                    found.update(walk(item))
            elif isinstance(value, list):
                for item in value:
                    found.update(walk(item))
            return found

        def scan(text):
            if text in text_cache:
                return text_cache[text]
            found = set()
            text_cache[text] = found
            counts['strings'] += 1
            folded = text.lower()
            if folded not in folded_cache:
                direct = set()
                if any(value in folded for value in runtime):
                    direct.add('runtime identity')
                if any(match.group(1) != 'ubuntu' for match in homes.finditer(folded)):
                    direct.add('home prefix')
                if folded:
                    encoded = folded.encode('utf-8', errors='replace')
                    ascii_text = len(encoded) == len(folded)
                    for length, expected in targets:
                        for offset in range(len(folded) - length + 1):
                            window = (encoded[offset:offset + length] if ascii_text else
                                      folded[offset:offset + length].encode('utf-8', errors='replace'))
                            if sha256(window).digest() == expected:
                                direct.add('owner digest')
                folded_cache[folded] = direct
            found.update(folded_cache[folded])
            try:
                parsed = json.loads(text)
            except ValueError:
                pass
            else:
                found.update(walk(parsed))
            if len(text) >= 16:
                try:
                    decoded = base64.b64decode(text, validate=True)
                except (ValueError, binascii.Error):
                    pass
                else:
                    counts['decoded_blobs'] += 1
                    found.update(scan(decoded.decode('utf-8', errors='replace')))
                    try:
                        inflated = zlib.decompress(decoded)
                    except zlib.error:
                        pass
                    else:
                        counts['zlib_blobs'] += 1
                        found.update(scan(inflated.decode('utf-8', errors='replace')))
            return found

        raw = corpus.FIXTURE.read_bytes().decode('utf-8', errors='replace')
        failures = {}
        for number, line in enumerate(raw.splitlines(), 1):
            row = json.loads(line)
            found = walk(row)
            if found:
                failures[row.get('name', 'row-%d' % number)] = sorted(found)
        raw_found = scan(raw)
        if raw_found:
            failures['raw fixture'] = sorted(raw_found)
        print('privacy scan: strings=%d decoded_blobs=%d zlib_blobs=%d elapsed=%.3fs' %
              (counts['strings'], counts['decoded_blobs'], counts['zlib_blobs'],
               time.monotonic() - started), flush=True)
        self.assertGreater(counts['strings'], 0)
        self.assertFalse(failures, 'private fixture content by row: ' + json.dumps(failures, sort_keys=True))


if __name__ == '__main__':
    unittest.main(verbosity=2)
