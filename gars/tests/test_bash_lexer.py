"""Quoted Bash operator literals, with direct JSON hook calls and a shell oracle."""
import ast
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import GARS, run
from tools import policy

OPERATOR_MESSAGE = 'only one simple command; no shell operators or expansion'
VOCABULARY_MESSAGE = 'value is outside the declared vocabulary'
OPERATORS = ('|', '||', '&&', '&', ';', '>', '>>', '>|', '<', '<<', '<<<', '<(x)', '2>&1')
REPORTED = (
    ('grep -n "sanitiz\\|add_argument" _system/stage00_register.py', 0, None),
    ('grep -nE "sanitiz|add_argument" _system/stage00_register.py', 2, VOCABULARY_MESSAGE),
    ('grep -n "add_argument" _system/stage00_register.py', 0, None),
    ('rg -n "sanitiz|add_argument" _system/stage00_register.py', 0, None),
    ("rg -n 'sanitiz|add_argument' _system/stage00_register.py", 0, None),
)
BOUNDARIES = (
    (r"grep 'a\' ; ls '", 2, OPERATOR_MESSAGE),
    (r'grep "a\\" ; ls', 2, OPERATOR_MESSAGE),
    ('grep "a" ; echo "b|c"', 2, OPERATOR_MESSAGE),
    ('''grep "a'" ; ls''', 2, OPERATOR_MESSAGE),
    (r'grep "a\" ; ls "', 0, None),
    ('grep "a|b', 2, 'could not read command quoting'),
    (r'grep -n a\|b f', 2, OPERATOR_MESSAGE),
)
COMMENTS = (
    ('grep -r x # README.md', 2, OPERATOR_MESSAGE),
    ('ls # x', 2, OPERATOR_MESSAGE),
    ('cat CONTEXT.md # x', 2, OPERATOR_MESSAGE),
    ("ls #'|'", 2, OPERATOR_MESSAGE),
    ('grep -n x #f', 2, OPERATOR_MESSAGE),
    ('grep -n "#" CONTEXT.md', 0, None),
    ("grep -n '#x' CONTEXT.md", 0, None),
    (r'grep -n \#x CONTEXT.md', 0, None),
    ('grep -n a#b CONTEXT.md', 0, None),
    ('# comment', 2, OPERATOR_MESSAGE),
    ('ls\t# x', 2, OPERATOR_MESSAGE),
    ('grep -n "a"#b CONTEXT.md', 0, None),
    ("grep -n ''#x CONTEXT.md", 0, None),
    ('grep -n " "#x CONTEXT.md', 0, None),
    (r'grep -n a\ #x CONTEXT.md', 0, None),
    (r"ls \#'|'", 0, None),
)
BRACES_TILDES = (
    ('ls {..,"|"}', 2, OPERATOR_MESSAGE),
    ('cat {/etc/hosts,"|"}', 2, OPERATOR_MESSAGE),
    ('ls ~/"|"', 2, OPERATOR_MESSAGE),
    ('cat {../projects/closed/00_data/rnaseq_bulk/raw/s.txt,x}', 2, OPERATOR_MESSAGE),
    ('ls ~', 2, OPERATOR_MESSAGE),
    ('cat ~/x', 2, OPERATOR_MESSAGE),
    ('ls x=~/y', 2, OPERATOR_MESSAGE),
    ('ls ~+', 2, OPERATOR_MESSAGE),
    ('ls a~', 2, OPERATOR_MESSAGE),
    ('ls {a,b}', 2, OPERATOR_MESSAGE),
    ('grep -n a{2} f', 2, OPERATOR_MESSAGE),
    ('ls x:~/y', 2, OPERATOR_MESSAGE),
    ('ls "a"~', 2, OPERATOR_MESSAGE),
    ('ls "a"{b,c}', 2, OPERATOR_MESSAGE),
    ('python3 _system/stage00_register.py create --title a~ --assays rnaseq_bulk',
     2, OPERATOR_MESSAGE),
    ('python3 _system/stage00_register.py create --title a{b,c} --assays rnaseq_bulk',
     2, OPERATOR_MESSAGE),
    ('grep -n "{" CONTEXT.md', 0, None),
    ("grep -n '{' CONTEXT.md", 0, None),
    ("grep -n '~' CONTEXT.md", 0, None),
    ('grep -n "~" CONTEXT.md', 0, None),
    ('grep -n "a{2}" CONTEXT.md', 0, None),
    (r'grep -n \{ CONTEXT.md', 0, None),
    (r'grep -n \~ CONTEXT.md', 0, None),
    (r'grep -n a\{b,c} CONTEXT.md', 2, OPERATOR_MESSAGE),
    ('grep -n a} CONTEXT.md', 2, OPERATOR_MESSAGE),
    ('ls x }', 2, OPERATOR_MESSAGE),
    ('grep -n "a}" CONTEXT.md', 0, None),
    ("grep -n '}' CONTEXT.md", 0, None),
    ('grep -n "}" CONTEXT.md', 0, None),
    (r'grep -n a\} CONTEXT.md', 0, None),
    (r'grep -n a\{b,c\} CONTEXT.md', 0, None),
    ('grep -n "a{b,c}" CONTEXT.md', 0, None),
)
# Guard-only payloads: never put executable zsh qualifiers or =(...) in a shell corpus.
PARENTHESIS_REFUSALS = (
    ("ls *(e:'touch a;touch b':)", 2, OPERATOR_MESSAGE),
    ("cat =(eval 'touch e;touch g')", 2, OPERATOR_MESSAGE),
    ("ls _system/*(e:'touch a|sh':)", 2, OPERATOR_MESSAGE),
    ('ls =(touch e)', 2, OPERATOR_MESSAGE),
    ("ls *(e:'touch a':)", 2, OPERATOR_MESSAGE),
    ('ls a(b', 2, OPERATOR_MESSAGE),
    ('ls a)b', 2, OPERATOR_MESSAGE),
)
CLOSED_QUALIFIER = "ls _system/*(e:'cat projects/closed/00_data/rnaseq_bulk/raw/s.txt':)"
PARENTHESIS_LITERALS = (
    ('grep -n "(a|b)" CONTEXT.md', 0, None),
    ("grep -n '(x)' CONTEXT.md", 0, None),
    (r'grep -n \(x\) CONTEXT.md', 0, None),
)
UNMATCHED_OPEN_BRACES = (
    ('ls a{b', 2, OPERATOR_MESSAGE),
    ('grep -n x{ CONTEXT.md', 2, OPERATOR_MESSAGE),
    ('grep -n "x{" CONTEXT.md', 0, None),
)


def operator_rows():
    for operator in OPERATORS:
        for quote in ('', '"', "'"):
            value = quote + 'a' + operator + 'b' + quote
            yield ('grep -n ' + value + ' _system/stage00_register.py',
                   0 if quote else 2, None if quote else OPERATOR_MESSAGE)
            yield ('python3 _system/stage00_register.py create --title ' + value +
                   ' --assays rnaseq_bulk', 2, OPERATOR_MESSAGE)


def expansion_rows():
    for expansion in ('$(echo x)', '${HOME}', '$VAR', '`echo x`', '\n', '\r', '\\\n'):
        for quote in ('', '"', "'"):
            yield ('grep ' + quote + 'a' + expansion + 'b' + quote,
                   2, OPERATOR_MESSAGE)
    yield ("grep $'a|b'", 2, OPERATOR_MESSAGE)


def strict_rows():
    yield ('python3 _system/stage00_register.py create --title "a|b" --assays rnaseq_bulk',
           2, OPERATOR_MESSAGE)
    yield ("python3 _system/tool_call.py fs.search " +
           shlex.quote(json.dumps({'pattern': 'a|b', 'paths': ['_system/stage00_register.py']})),
           2, OPERATOR_MESSAGE)


def lexical_rows():
    """Finite scan corpus shared by the guard tests and the real-shell differential."""
    rows = list(REPORTED) + list(BOUNDARIES) + list(COMMENTS) + list(operator_rows())
    rows += list(BRACES_TILDES)
    rows += list(PARENTHESIS_LITERALS) + list(UNMATCHED_OPEN_BRACES)
    rows += list(expansion_rows()) + list(strict_rows())
    # Adjacent quote regions, empty words, escaped quote/space, and a literal backslash.
    rows += [(command, 0, None) for command in (
        'grep a"|"b f', "grep a'|'b f", 'grep "" f', "grep '' f",
        r'grep a\ b f', r'grep "a\\b|c" f', r'grep "a\qb|c" f',
        "grep 'a\\|b' f", 'grep "a\'|b" f', r'grep a\"b f',
    )]
    # Every filesystem executable comes from the registry, including future additions.
    for tool in policy.registry():
        if tool.get('filesystem'):
            rows.append((tool['argv'][0] + ' "a|b"', 0, None))
    return rows


def static_regressions():
    """Harvest the fixture-free denied Bash rows from their source ASTs.

    Context-dependent refusals are collected during the original modules' runs;
    transplanting those commands into GARS would discard cwd, symlinks and data_class.
    """
    rows = []
    folder = Path(__file__).resolve().parent
    for filename in ('test_policy_attacks.py', 'test_guard_hook.py', 'test_policy_faults.py'):
        tree = ast.parse((folder / filename).read_text())
        before = len(rows)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'ATTACKS'
                                                     for t in node.targets):
                for command, _ in ast.literal_eval(node.value).values():
                    rows.append((filename, command))
            if not isinstance(node, ast.ClassDef):
                continue
            for method in node.body:
                if not isinstance(method, ast.FunctionDef):
                    continue
                if node.name == 'ExtraSpellingsTests' and method.name.startswith('test_') \
                        and method.name != 'test_positive_controls':
                    for call in ast.walk(method):
                        if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                                and call.func.attr == 'denied' and isinstance(call.args[0], ast.Constant):
                            rows.append((filename, ast.literal_eval(call.args[0])))
                        if isinstance(call, ast.For) and isinstance(call.iter, ast.Tuple):
                            for command in ast.literal_eval(call.iter):
                                rows.append((filename, command))
                if method.name == 'test_denied_shapes':
                    loop = next(n for n in ast.walk(method) if isinstance(n, ast.For))
                    for transport, data in ast.literal_eval(loop.iter):
                        if transport == 'Bash':
                            rows.append((filename, data['command']))
                if method.name == 'test_bypass_switch_as_shipped':
                    loop = next(n for n in ast.walk(method) if isinstance(n, ast.For))
                    rows.extend((filename, c) for c in ast.literal_eval(loop.iter))
                for call in ast.walk(method):
                    if isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) \
                            and call.func.attr == 'guard_fault':
                        rows.append((filename, ast.literal_eval(call.args[2])))
        if len(rows) == before:
            raise AssertionError('empty regression source: ' + filename)
    return rows


def guard(command, root=GARS):
    payload = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                          'tool_input': {'command': command}, 'cwd': str(root)})
    return run([sys.executable, root / '_system/guard_hook.py'], root, payload,
               {'CLAUDE_PROJECT_DIR': str(root)})


def differential_rows(shell, cwd, zsh=False):
    """Only scan-accepted corpus rows reach the shell; replace the executable with printf."""
    for command, _, _ in lexical_rows():
        try:
            tokens = policy.simple_tokens(command)
        except policy.Refusal:
            continue
        # zsh's =cmd expansion is out of scope, including future corpus additions.
        if zsh and any(word.startswith('=') for word in tokens[1:]):
            continue
        rest = command.split(None, 1)[1] if len(command.split(None, 1)) == 2 else ''
        options = ['-f'] if zsh else ['--noprofile', '--norc']
        result = subprocess.run([shell] + options + ['-c', 'printf "<%s>" ' + rest],
                                cwd=str(cwd), env={'PATH': str(Path(shell).parent), 'LC_ALL': 'C'},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
        expected = ''.join('<%s>' % word for word in shlex.split(command, posix=True)[1:]).encode()
        yield command, tokens[1:], result, expected


class BashLexerTests(unittest.TestCase):
    def check_rows(self, rows, root=GARS):
        for command, expected, message in rows:
            with self.subTest(command=command):
                result = guard(command, root)
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertNotIn(b'the guard failed while checking', result.stderr)
                if message:
                    self.assertIn(message.encode(), result.stderr)
                    self.assertIn(b'R-092', result.stderr)
                if message == VOCABULARY_MESSAGE:
                    self.assertNotIn(OPERATOR_MESSAGE.encode(), result.stderr)

    def test_reported_commands(self):
        self.check_rows(REPORTED)

    def test_operator_pairs(self):
        self.check_rows(operator_rows())

    def test_expansions_and_line_breaks(self):
        self.check_rows(expansion_rows())

    def test_quote_boundaries(self):
        self.check_rows(BOUNDARIES)

    def test_word_start_comments_and_literal_hashes(self):
        self.check_rows(COMMENTS)
        with tempfile.TemporaryDirectory(prefix='lexer-comments-') as tmp:
            root = Path(tmp)
            shutil.copytree(str(GARS / '_system'), str(root / '_system'),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            data = root / 'projects/closed/00_data'
            data.mkdir(parents=True)
            (data / 'dataset.tsv').write_text(
                'data_class\tpurpose\tagreement_ref\tinput_data_location\n'
                'deidentified_under_agreement\tfixture\tnone\t[]\n')
            self.check_rows(COMMENTS, root)

    def test_brace_and_tilde_expansions_and_literals(self):
        self.check_rows(BRACES_TILDES)
        with tempfile.TemporaryDirectory(prefix='lexer-brace-tilde-') as tmp:
            root = Path(tmp)
            shutil.copytree(str(GARS / '_system'), str(root / '_system'),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            raw = root / 'projects/closed/00_data/rnaseq_bulk/raw'
            raw.mkdir(parents=True)
            (raw / 's.txt').write_text('synthetic closed fixture\n')
            (root / 'projects/closed/00_data/dataset.tsv').write_text(
                'data_class\tpurpose\tagreement_ref\tinput_data_location\n'
                'deidentified_under_agreement\tfixture\tnone\t[]\n')
            pub = root / 'pub'
            pub.mkdir()
            for command, expected, message in BRACES_TILDES:
                if expected != 2:
                    continue  # Existing closed-project literal-path rules remain unchanged.
                with self.subTest(command=command, cwd='pub', closed=True):
                    payload = json.dumps({'hook_event_name': 'PreToolUse', 'tool_name': 'Bash',
                                          'tool_input': {'command': command}, 'cwd': str(pub)})
                    result = run([sys.executable, root / '_system/guard_hook.py'], root,
                                 payload, {'CLAUDE_PROJECT_DIR': str(root)})
                    self.assertEqual(result.returncode, expected, result.stderr)
                    self.assertIn(message.encode(), result.stderr)
                    self.assertIn(b'R-092', result.stderr)
                    self.assertNotIn(b'the guard failed while checking', result.stderr)

    def test_escaped_closing_braces_match_quoted_spellings(self):
        for escaped, quoted in ((r'a\}', '"a}"'), (r'a\{b,c\}', '"a{b,c}"')):
            with self.subTest(escaped=escaped, quoted=quoted):
                literal = guard('grep -n ' + escaped + ' CONTEXT.md')
                reference = guard('grep -n ' + quoted + ' CONTEXT.md')
                self.assertEqual(reference.returncode, 0, reference.stderr)
                self.assertEqual(literal.returncode, reference.returncode, literal.stderr)
                self.assertEqual(literal.stderr, reference.stderr)

    def test_unquoted_parentheses_refused(self):
        with tempfile.TemporaryDirectory(prefix='lexer-parentheses-') as tmp:
            root = Path(tmp)
            shutil.copytree(str(GARS / '_system'), str(root / '_system'),
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            self.check_rows(PARENTHESIS_REFUSALS, root)
            raw = root / 'projects/closed/00_data/rnaseq_bulk/raw'
            raw.mkdir(parents=True)
            (raw / 's.txt').write_text('synthetic closed fixture\n')
            (root / 'projects/closed/00_data/dataset.tsv').write_text(
                'data_class\tpurpose\tagreement_ref\tinput_data_location\n'
                'deidentified_under_agreement\tfixture\tnone\t[]\n')
            self.check_rows([(CLOSED_QUALIFIER, 2, OPERATOR_MESSAGE)], root)

    def test_parenthesis_literals(self):
        self.check_rows(PARENTHESIS_LITERALS)

    def test_unmatched_opening_brace_witnesses(self):
        self.check_rows(UNMATCHED_OPEN_BRACES)

    def test_helpers_and_dispatcher_stay_strict(self):
        self.check_rows(strict_rows())

    def test_filesystem_executables_from_registry(self):
        rows = []
        for tool in policy.registry():
            if tool.get('filesystem'):
                for quote in ('"', "'"):
                    rows.append((tool['argv'][0] + ' ' + quote + 'a|b' + quote, 0, None))
        self.assertTrue(rows)
        self.check_rows(rows)

    def test_harvested_static_regressions(self):
        rows = static_regressions()
        print('static Bash regressions: %d' % len(rows), flush=True)
        for source, command in rows:
            with self.subTest(source=source, command=command):
                self.check_rows([(command, 2, None)])

    def test_schema_refusals_on_bash_transport(self):
        # test_tool_schema_refusal exercises the typed/native path, with no Bash calls.
        # Carry those exact invalid argument shapes through the Bash dispatcher as well.
        for name, args in (
                ('configure.genomes', {'assay': 'invented'}),
                ('configure.genomes', {'shell': 'bad'}),
                ('stage03_analysis.create', {}),
                ('stage03_analysis.create', {'project': 3, 'slug': 'ok'}),
                ('stage03_analysis.create', {'project': 'projects/p', 'slug': 'ok', 'actor': 'human'})):
            self.check_rows([('python3 _system/tool_call.py ' + name + ' ' +
                              shlex.quote(json.dumps(args)), 2, None)])
        self.check_rows([('python3 _system/stage00_register.py assays --unknown', 2, None)])
        for path in ('_system', 'projects/../_system', '../outside'):
            command = 'python3 _system/tool_call.py stage03_analysis.create ' + shlex.quote(
                json.dumps({'project': path, 'slug': 'x'}))
            self.check_rows([(command, 2, None)])

    @unittest.skipUnless(shutil.which('bash'), 'bash is absent')
    def test_real_shell_differential(self):
        self.check_shell_differential(shutil.which('bash'))

    @unittest.skipUnless(shutil.which('zsh'), 'zsh is absent')
    def test_zsh_differential_excluding_equals_command_expansion(self):
        self.check_shell_differential(shutil.which('zsh'), zsh=True)

    def check_shell_differential(self, shell, zsh=False):
        count = 0
        with tempfile.TemporaryDirectory(prefix='lexer-differential-') as tmp:
            for command, argv, result, expected in differential_rows(shell, tmp, zsh):
                count += 1
                with self.subTest(command=command, argv=argv):
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, expected)
        self.assertGreater(count, 0)
        print('%s differential: %d accepted rows' % (Path(shell).name, count), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
