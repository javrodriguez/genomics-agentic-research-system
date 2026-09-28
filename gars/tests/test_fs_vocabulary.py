"""grep -E/-F/-w/-l/-c and find's declared predicates, through the guard and the dispatcher."""
import json
import re
import shlex
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from support import GARS, run
from tools import policy
import test_bash_lexer

OUTSIDE = '<outside>'
EXPRESSION, PATHS, FLAGS, COMMAND = 'args.expression', 'args.paths', 'args.flags', 'command'
GLOB_MESSAGE = "quote find's pattern"
OPERATOR_MESSAGE = 'only one simple command; no shell operators or expansion'

NEWLY_ALLOWED = (
    'grep -E "a|b" CONTEXT.md', 'grep -n -E "a|b" CONTEXT.md', 'grep -F a.b CONTEXT.md',
    'grep -w x CONTEXT.md', 'grep -l x CONTEXT.md', 'grep -c x CONTEXT.md',
    'grep -r -l x _system',
    'find _system -maxdepth 1', 'find . -maxdepth 2 -type d',
    'find _system -mindepth 1 -maxdepth 1 -type f', 'find _system -name "*.py"',
    "find _system -iname '*.PY' -type f", 'find _system -maxdepth 1 -name tools',
    "find . -name '*'", r'find . -name \*.py',
)
UNCHANGED_ALLOWED = ('find .', 'find _system', 'grep -n x CONTEXT.md', 'grep -r x _system',
                     'ls -la', 'cat CONTEXT.md')
# (command, field prefix of the refusal, rule); each class names why the row is refused.
REFUSED = {
    'program': (
        ('find . -exec cat {} +', COMMAND, 'R-092'),  # the unquoted brace refuses first
        ('find . -exec cat "{}" ";"', EXPRESSION, 'R-092'),
        ('find . -exec ls', EXPRESSION, 'R-092'),
        ('find . -execdir ls', EXPRESSION, 'R-092'),
        ('find . -ok ls', EXPRESSION, 'R-092'),
        ('find . -okdir ls', EXPRESSION, 'R-092'),
    ),
    'write': (
        ('find . -delete', EXPRESSION, 'R-092'),
        ('find . -delete x', EXPRESSION, 'R-092'),
        ('find . -name x -delete', EXPRESSION, 'R-092'),
        ('find . -name x -o -delete', EXPRESSION, 'R-092'),
        ('find . -fprint out.txt', EXPRESSION, 'R-092'),
        ('find . -fprint0 out.txt', EXPRESSION, 'R-092'),
        ('find . -fprintf out.txt %p', EXPRESSION, 'R-092'),
        ('find . -fls out.txt', EXPRESSION, 'R-092'),
    ),
    'file_operand': (
        ('find . -newer CONTEXT.md', EXPRESSION, 'R-092'),
        ('find . -anewer CONTEXT.md', EXPRESSION, 'R-092'),
        ('find . -cnewer CONTEXT.md', EXPRESSION, 'R-092'),
        ('find . -newermt 2020-01-01', EXPRESSION, 'R-092'),
        ('find . -samefile CONTEXT.md', EXPRESSION, 'R-092'),
    ),
    'outside': (
        ('find ' + OUTSIDE + ' -maxdepth 1', PATHS, 'R-094'),
        ('find .. -maxdepth 1', PATHS, 'R-094'),
        ('find . ' + OUTSIDE + ' -maxdepth 1', PATHS, 'R-094'),
    ),
    'flag': (
        ('find -L . -name x', FLAGS, 'R-092'),
        ('find -maxdepth 1', FLAGS, 'R-092'),
    ),
    'value': (
        ('find . -maxdepth x', EXPRESSION, 'R-092'),
        ('find . -maxdepth -1', EXPRESSION, 'R-092'),
        ('find . -maxdepth', EXPRESSION, 'R-092'),
        ('find . -maxdepth 1000', EXPRESSION, 'R-092'),
        ('find . -mindepth 01', EXPRESSION, 'R-092'),
        ('find . -type l', EXPRESSION, 'R-092'),
        ('find . -type fd', EXPRESSION, 'R-092'),
        ('find . -name', EXPRESSION, 'R-092'),
        ('find . -name a/b', EXPRESSION, 'R-092'),
        ('find . -name -delete', EXPRESSION, 'R-092'),
    ),
    'not_in_table': (
        ('find . -o -name x', EXPRESSION, 'R-092'),
        ('find . -not -name x', EXPRESSION, 'R-092'),
        ('find . "!" -name x', PATHS, 'R-092'),  # a second path breaks the one-path rule
        ('find . -print', EXPRESSION, 'R-092'),
        ('find . -print0', EXPRESSION, 'R-092'),
        ('find . -ls', EXPRESSION, 'R-092'),
        ('find . -printf %p', EXPRESSION, 'R-092'),
        ('find . -follow', EXPRESSION, 'R-092'),
        ('find . -regex x', EXPRESSION, 'R-092'),
        ('find . -path x', EXPRESSION, 'R-092'),
    ),
    'glob': tuple((c, COMMAND, 'R-092') for c in (
        'find . -name *', 'find . -name *.py', 'find . -name a*', 'find *', 'find ..?',
        'find . -name [ab]')),
    'grep': (
        ('grep -f ' + OUTSIDE + ' CONTEXT.md', FLAGS, 'R-092'),
        ('grep -e a CONTEXT.md', FLAGS, 'R-092'),
        ('grep -A 3 a CONTEXT.md', FLAGS, 'R-092'),
        ('grep --include=x a .', FLAGS, 'R-092'),
        ('grep -En a CONTEXT.md', FLAGS, 'R-092'),
        ('grep -E a ' + OUTSIDE, PATHS, 'R-094'),
    ),
}
# Predicates that run a program, write, read an unjudged file operand, or combine expressions.
FORBIDDEN = ('-exec', '-execdir', '-ok', '-okdir', '-delete', '-fprint', '-fprint0', '-fprintf',
             '-fls', '-newer', '-anewer', '-cnewer', '-newermt', '-samefile', '-o', '-or', '-a',
             '-and', '-not', '-print', '-print0', '-printf', '-ls', '-follow', '-regex', '-path')
VALID_POOL = ('1', '0', 'f', 'd', 'x', 'tools', '*.py')
INVALID_POOL = ('-delete', 'a/b', '-1', 'l', '1000')
CLOSED_ROW = ('data_class\tpurpose\tagreement_ref\tinput_data_location\n'
              'deidentified_under_agreement\tfixture\tnone\t[]\n')


def workspace(tmp, closed=False):
    root = Path(tmp)
    shutil.copytree(str(GARS / '_system'), str(root / '_system'),
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (root / 'CONTEXT.md').write_text('a\nb\nx\n')
    if closed:
        data = root / 'projects/closed/00_data'
        data.mkdir(parents=True)
        (data / 'dataset.tsv').write_text(CLOSED_ROW)
        (data / 'rnaseq_bulk/raw').mkdir(parents=True)
        (data / 'rnaseq_bulk/raw/s.txt').write_text('synthetic closed fixture\n')
    return root


def guard(command, root):
    payload = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                          'tool_input': {'command': command}, 'cwd': str(root)})
    return run([sys.executable, root / '_system/guard_hook.py'], root, payload,
               {'CLAUDE_PROJECT_DIR': str(root)})


def record(result):
    text = result.stderr.decode()
    if not text.startswith('Blocked: {'):
        return {}
    return json.JSONDecoder().raw_decode(text[len('Blocked: '):])[0]


def find_tool():
    return policy.named('fs.find')


class FsVocabularyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='fs-vocabulary-')
        cls.root = workspace(Path(cls.tmp.name) / 'ws')
        cls.outside = str(cls.root.parent)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def spell(self, command):
        return command.replace(OUTSIDE, shlex.quote(self.outside))

    def allowed(self, commands):
        for command in commands:
            with self.subTest(command=command):
                result = guard(self.spell(command), self.root)
                self.assertEqual(result.returncode, 0, result.stderr)

    def refused(self, rows):
        for command, field, rule in rows:
            with self.subTest(command=command):
                result = guard(self.spell(command), self.root)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertNotIn(b'the guard failed while checking', result.stderr)
                found = record(result)
                self.assertTrue(found.get('field', '').startswith(field), result.stderr)
                self.assertEqual(found.get('rule'), rule, result.stderr)
                if field == EXPRESSION:
                    for name in find_tool()['predicates']:
                        self.assertIn(name, found['message'])

    def test_newly_allowed(self):
        self.allowed(NEWLY_ALLOWED)

    def test_unchanged_allowed(self):
        self.allowed(UNCHANGED_ALLOWED)

    def test_program_refused(self):
        self.refused(REFUSED['program'])

    def test_write_refused(self):
        self.refused(REFUSED['write'])

    def test_unjudged_file_operand_refused(self):
        self.refused(REFUSED['file_operand'])

    def test_outside_refused(self):
        self.refused(REFUSED['outside'])

    def test_flag_refused(self):
        self.refused(REFUSED['flag'])

    def test_value_refused(self):
        self.refused(REFUSED['value'])

    def test_not_in_table_refused(self):
        self.refused(REFUSED['not_in_table'])

    def test_glob_rule(self):
        self.refused(REFUSED['glob'])
        for command, _, _ in REFUSED['glob']:
            with self.subTest(command=command):
                self.assertIn(GLOB_MESSAGE.encode(), guard(command, self.root).stderr)

    def test_grep_still_refused(self):
        self.refused(REFUSED['grep'])

    def test_forbidden_predicates_never_declared(self):
        predicates = find_tool()['predicates']
        for name in FORBIDDEN:
            with self.subTest(predicate=name):
                self.assertNotIn(name, predicates)
        self.refused([('find . %s x' % name, EXPRESSION, 'R-092') for name in FORBIDDEN])

    def test_every_declared_predicate_checks_its_value(self):
        predicates = find_tool()['predicates']
        self.assertTrue(predicates)
        for name, pattern in sorted(predicates.items()):
            with self.subTest(predicate=name):
                good = next((v for v in VALID_POOL if re.fullmatch(pattern, v)), None)
                bad = next((v for v in INVALID_POOL if not re.fullmatch(pattern, v)), None)
                self.assertIsNotNone(good, 'no valid sample value for ' + name)
                self.assertIsNotNone(bad, 'no invalid sample value for ' + name)
                self.allowed(['find . %s %s' % (name, shlex.quote(good))])
                self.refused([('find . %s %s' % (name, shlex.quote(bad)), EXPRESSION, 'R-092'),
                              ('find . ' + name, EXPRESSION, 'R-092')])

    def test_closed_project_refused_as_without_predicates(self):
        with tempfile.TemporaryDirectory(prefix='fs-vocabulary-closed-') as tmp:
            root = workspace(tmp, closed=True)
            # dataset.tsv is the closed project's one readable file (0107), so its grep -E
            # row matches grep's outcome, allowed; the raw file shows the refusal itself.
            for command, reference, exit_code in (
                    ('find projects/closed -maxdepth 1', 'find projects/closed', 2),
                    ('find projects -maxdepth 1 -name x', 'find projects', 2),
                    ('grep -E x projects/closed/00_data/dataset.tsv',
                     'grep x projects/closed/00_data/dataset.tsv', 0),
                    ('grep -E x projects/closed/00_data/rnaseq_bulk/raw/s.txt',
                     'grep x projects/closed/00_data/rnaseq_bulk/raw/s.txt', 2)):
                with self.subTest(command=command):
                    result, expected = guard(command, root), guard(reference, root)
                    self.assertEqual(expected.returncode, exit_code, expected.stderr)
                    self.assertEqual(result.returncode, expected.returncode, result.stderr)
                    self.assertEqual(result.stderr, expected.stderr)

    def test_dispatcher_new_find_forms(self):
        forms = [c for c in NEWLY_ALLOWED if c.startswith('find ')]
        self.assertTrue(forms)
        for command in forms:
            with self.subTest(command=command):
                tokens = shlex.split(command)
                tool, args = policy.parse_argv(tokens, self.root, self.root)
                self.assertEqual(tool['name'], 'fs.find')
                policy.validate_args(tool, args, self.root, self.root)
                self.assertEqual(policy.argv_for(tool, args, self.root),
                                 tool['argv'] + tokens[1:])
                call = {k: v for k, v in args.items() if v}
                result = guard('python3 _system/tool_call.py fs.find ' +
                               shlex.quote(json.dumps(call)), self.root)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_dispatcher_refused_find_forms(self):
        reached = 0
        for rows in REFUSED.values():
            for command, _, _ in rows:
                if not command.startswith('find '):
                    continue
                command = self.spell(command)
                try:
                    tool, args = policy.parse_argv(policy.simple_tokens(command),
                                                   self.root, self.root)
                except policy.Refusal:
                    continue
                reached += 1
                call = {k: v for k, v in args.items() if v}
                with self.subTest(command=command, call=call):
                    with self.assertRaises(policy.Refusal):
                        policy.validate_args(tool, call, self.root, self.root)
                    result = guard('python3 _system/tool_call.py fs.find ' +
                                   shlex.quote(json.dumps(call)), self.root)
                    self.assertEqual(result.returncode, 2, result.stderr)
        self.assertGreater(reached, 30)

    def test_expression_refused_on_tools_without_predicates(self):
        for tool in policy.registry():
            if tool.get('filesystem') and 'predicates' not in tool:
                with self.subTest(tool=tool['name']):
                    with self.assertRaises(policy.Refusal):
                        policy.validate_args(tool, {'paths': ['.'],
                                                    'expression': ['-maxdepth', '1']},
                                             self.root, self.root)

    def test_dispatcher_positive_control(self):
        result = run([sys.executable, GARS / '_system/tool_call.py', 'fs.find',
                      json.dumps({'paths': ['_system'], 'expression': ['-maxdepth', '1']})], GARS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        listed = json.loads(result.stdout.decode())['stdout'].splitlines()
        self.assertIn('_system/tools', listed)
        self.assertNotIn('_system/tools/policy.py', listed)

    def test_harvested_grep_and_find_refusals(self):
        names = re.compile(r'(^|[\s;|&(])(grep|find)(\s|$)')
        lexer = [c for c, expected, _ in list(test_bash_lexer.lexical_rows()) +
                 list(test_bash_lexer.PARENTHESIS_REFUSALS) if expected == 2 and names.search(c)]
        attacks = [c for source, c in test_bash_lexer.static_regressions()
                   if source == 'test_policy_attacks.py' and names.search(c)]
        print('harvested grep/find refusals: test_bash_lexer %d, test_policy_attacks %d'
              % (len(lexer), len(attacks)), flush=True)
        self.assertGreater(len(lexer), 0)
        self.assertGreater(len(attacks), 0)
        for source, commands in (('test_bash_lexer', lexer), ('test_policy_attacks', attacks)):
            for command in commands:
                with self.subTest(source=source, command=command):
                    result = guard(command, GARS)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertNotIn(b'the guard failed while checking', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
