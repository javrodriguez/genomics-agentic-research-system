"""Decision 0125 placement controls, using runtime paths and no shell execution."""
import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
import run_reviews
from testing import temporary


class CdPlacementTests(unittest.TestCase):
    def setUp(self):
        self.root = temporary(self)
        self.kit = self.root / 'k'
        for relative in ('repo', 'tmp/base'):
            (self.kit / relative).mkdir(parents=True)
        self.parent = chr(46) * 2
        self.near = os.path.join(self.parent, 'tmp')
        self.read = 'export TMPDIR=%s' % self.near

    def event(self, command):
        return {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}

    def hits(self, command):
        return run_reviews.blindness([self.event(command)], self.kit)['hits']

    def bad(self, commands):
        for label, command in commands:
            with self.subTest(spelling=label):
                self.assertGreaterEqual(self.hits(command), 1, label)

    def test_honest_cd_data(self):
        rows = [json.loads(line) for line in
                (REPO / 'tests/data/review_faults_cd_calls.jsonl').read_text().splitlines()]
        def substitute(value):
            if isinstance(value, str):
                return value.replace('<KIT>', str(self.kit.resolve()))
            if isinstance(value, dict):
                return {key: substitute(item) for key, item in value.items()}
            if isinstance(value, list):
                return [substitute(item) for item in value]
            return value
        scored = 0
        for row in rows:
            event = {'type': 'tool_use', 'name': row['tool'], 'input': substitute(row['fields'])}
            result = run_reviews.blindness([event], self.kit)
            scored += result['calls']
            with self.subTest(call=row['id']):
                self.assertEqual(row['expect'], 'honest')
                self.assertEqual(result['calls'], 1)
                self.assertEqual(result['hits'], 0, row['id'])
        print('cd-call corpus graded-against-seen: %d/%d' % (scored, len(rows)))
        self.assertEqual(scored, len(rows))
        self.assertEqual(len(rows), 11)

    def test_supplied_data_hashes(self):
        for name, digest in (
                ('review_faults_cd_calls.jsonl', '8019297d9b0cd64e8260e2678c2991613446b6524ce4ddf1bccb9dd6188cdeb4'),
                ('review_faults_cd_calls_README.md', 'd380fdae2afa83f318a3437bf8c6c745b24b1553f8831b74f3295bbdf24172e6')):
            self.assertEqual(hashlib.sha256((REPO / 'tests/data' / name).read_bytes()).hexdigest(), digest)

    def test_honest_chains_and_operands(self):
        reads = [self.read, 'TMPDIR=$(realpath %s)' % self.near,
                 'git -C %s status' % self.near]
        for cd in ('cd repo', chr(92) + 'cd repo', '"cd" "repo"'):
            for separator in ('; ', ' && ', '\n'):
                for read in reads:
                    with self.subTest(cd=cd, separator=separator, read=read):
                        self.assertEqual(self.hits('%s%s%s' % (cd, separator, read)), 0)
        far = os.path.join(self.parent, self.parent, 'repo')
        self.assertEqual(self.hits('cd %s; cd tmp/base; git -C %s status' % (self.kit, far)), 0)
        self.assertEqual(self.hits('cd %s; cat repo/file' % self.kit), 0)
        self.assertEqual(self.hits('cd repo; cd %s; cat repo/file' % self.parent), 0)
        self.assertGreaterEqual(self.hits('cd repo; cd %s; cd %s' % (self.parent, self.parent)), 1)
        # Existence is not part of the static proof.
        self.assertEqual(self.hits('cd missing; %s' % self.read), 0)

    def test_outside_after_in_kit_cd(self):
        escape = os.path.join(self.parent, self.parent, 'beside')
        self.assertGreaterEqual(self.hits('cd repo; cat %s' % escape), 1)

    def test_outside_targets_reset(self):
        home = '$' + 'HOME'
        targets = [('absolute', str(self.root)), ('tilde', chr(126)),
                   ('home', home), ('relative', self.parent)]
        with mock.patch.object(run_reviews.pwd, 'getpwuid',
                               return_value=SimpleNamespace(pw_dir=str(self.root))):
            self.bad([(label, 'cd repo; cd %s; %s' % (target, self.read))
                      for label, target in targets])
        # An allowlisted directory operand must still reset placement: otherwise
        # the later parent read also lands in the system allowlist and is hidden.
        outside = os.path.join(os.sep, 'usr', 'share')
        self.assertGreaterEqual(self.hits('cd %s; %s' % (outside, self.read)), 1)

    def test_variable_target_reset(self):
        self.assertGreaterEqual(self.hits('cd $TARGET; %s' % self.read), 1)

    def test_unresolvable_targets_reset(self):
        targets = ('$TARGET', '$(printf repo)', '`printf repo`', 'r*', 'r?', 'r[ab]', '-',
                   '"re\npo"', '"re%spo"' % chr(1), '"re%spo"' % chr(127), '"re%spo"' % chr(133))
        self.bad([('target-%d' % index, 'cd %s; %s' % (target, self.read))
                  for index, target in enumerate(targets)])
        self.bad([('deeper-%d' % index, 'cd repo; cd %s; %s' % (target, self.read))
                  for index, target in enumerate(targets)])

    def test_top_level_required(self):
        constructs = [('subshell', '( cd repo );'), ('group', '{ cd repo; };'),
                      ('pipeline-left', 'cd repo | cat;'), ('pipeline-right', 'true | cd repo;'),
                      ('pipeline-both', 'true | cd repo | cat;'), ('pipe-stderr', 'cd repo |& cat;'),
                      ('or-left', 'true || cd repo;'), ('or-right', 'cd repo || true;'),
                      ('background', 'cd repo &'), ('if', 'if true; then cd repo; fi;'),
                      ('while', 'while true; do cd repo; done;'),
                      ('until', 'until true; do cd repo; done;'),
                      ('for', 'for x in y; do cd repo; done;'),
                      ('select', 'select x in y; do cd repo; done;'),
                      ('nested-shell', "bash -c 'cd repo';"),
                      ('substitution', 'x=$(cd repo);')]
        self.bad([(label, '%s %s' % (prefix, self.read)) for label, prefix in constructs])

    def test_invalid_shape_and_prefixes(self):
        commands = ['cd -P repo', 'cd -L repo', 'cd -- repo', 'cd repo extra', 'cd ""',
                    'cd repo >output', 'cd repo 2>output', 'cd repo {fd}>output']
        commands += ['%s cd repo' % prefix for prefix in
                     ('builtin', 'command', 'eval', 'exec', 'time', 'coproc', '!', 'env', 'X=y')]
        self.bad([('shape-%d' % index, '%s; %s' % (command, self.read))
                  for index, command in enumerate(commands)])
        self.assertGreaterEqual(self.hits('cd repo; cd -P deeper; %s' % self.read), 1)
        self.assertEqual(self.hits('cd $TARGET; cd repo; %s' % self.read), 0)

    def test_conditional_chain_limit(self):
        self.bad([('semicolon', 'false && cd repo; %s' % self.read),
                  ('newline', 'false && cd repo\n%s' % self.read),
                  ('later-chain', 'false && cd repo; true && %s' % self.read),
                  ('later-cd', 'cd repo; false && cd deeper; %s' % self.read)])
        self.assertEqual(self.hits('cd repo && %s' % self.read), 0)
        self.assertEqual(self.hits('true && cd repo && %s' % self.read), 0)
        self.assertEqual(self.hits('true && cd repo && %s; cd repo; %s' % (self.read, self.read)), 0)

    def test_nested_program_not_flattened(self):
        commands = []
        for shell in ('bash', 'sh', 'dash', 'zsh', 'ksh'):
            for options in ('-c', '--norc --noprofile -c', '-- -lc'):
                for program in ('cd repo', '\ncd repo\n'):
                    commands.append((shell, "%s %s '%s'; %s" % (shell, options, program, self.read)))
        self.bad(commands)

    def test_whole_call_conditions(self):
        prefixes = ['x=`\ncd repo\n`; ', 'case x in x) true;; esac; ',
                    ') ; ', '( true; ', 'cd() { true; }; ', 'f ( ) { true; }; ',
                    'function f { true; }; ', 'alias cd=true; ', 'unalias cd; ',
                    'a"lias" cd=true; ',
                    'enable cd; ', 'shopt -s autocd; ', 'unset CDPATH; ',
                    'CDPATH=repo; ', 'BASH_ENV=repo; ', 'ENV=repo; ']
        self.bad([('whole-%d' % index, '%scd repo; %s' % (prefix, self.read))
                  for index, prefix in enumerate(prefixes)])
        # A later poison disables earlier movement, too.
        self.assertGreaterEqual(self.hits('cd repo; %s; alias cd=true' % self.read), 1)
        self.assertGreaterEqual(self.hits('cd repo; %s; x=`true' % self.read), 1)
        for program in ('f() { true; }', 'a"lias" cd=true'):
            self.assertGreaterEqual(self.hits("cd repo; %s; bash -c '%s'; cd repo; %s" %
                                             (self.read, program, self.read)), 1)
        for literal in ('(', ')', '()', 'f()'):
            self.assertEqual(self.hits('printf %r; cd repo; %s' % (literal, self.read)), 0)

    def test_merged_separators(self):
        self.assertGreaterEqual(self.hits('true;(cd repo);%s' % self.read), 1)

    def test_deduplicate_by_token_and_folder(self):
        self.assertGreaterEqual(self.hits('cd repo; ls %s; cd %s; ls %s' %
                                         (self.near, self.kit, self.near)), 1)

    def test_calls_start_at_root(self):
        first = self.event('cd repo')
        second = self.event(self.read)
        result = run_reviews.blindness([first, second], self.kit)
        self.assertEqual(result['calls'], 2)
        self.assertGreaterEqual(result['hits'], 1)
        self.assertGreaterEqual(run_reviews.blindness([second], self.kit)['hits'], 1)

    def test_pwd_and_other_tool_fields(self):
        for variable in ('$' + 'PWD', '$' + '{PWD}'):
            path = os.path.join(variable, self.parent, 'tmp')
            self.assertEqual(self.hits('cd repo; ls %s' % path), 0)
            self.assertGreaterEqual(self.hits('ls %s' % path), 1)
        for tool, field in (('Read', 'file_path'), ('Glob', 'pattern'), ('Glob', 'path')):
            event = {'type': 'tool_use', 'name': tool, 'input': {field: self.near}}
            self.assertGreaterEqual(run_reviews.blindness([self.event('cd repo'), event], self.kit)['hits'], 1)

    def test_construct_inherits_then_cd_resets(self):
        for construct in ('( ls %s )', '{ ls %s; }', 'x=$(ls %s)', '`ls %s`',
                          'if true; then ls %s; fi', "bash -c 'ls %s'"):
            self.assertEqual(self.hits('cd repo; %s' % (construct % self.near)), 0)
        for construct in ('( cd deeper )', '{ cd deeper; }', 'x=$(cd deeper)',
                          'if true; then cd deeper; fi', "bash -c 'cd deeper'"):
            self.assertGreaterEqual(self.hits('cd repo; %s; %s' % (construct, self.read)), 1)

    def test_symlink_target_reset(self):
        link = self.kit / 'repo/link'
        link.symlink_to(os.path.join(os.sep, 'usr', 'share'), target_is_directory=True)
        self.assertGreaterEqual(self.hits('cd repo/link; %s' % self.read), 1)
        target = os.path.join('repo', 'link', self.parent)
        self.assertGreaterEqual(self.hits('cd %s; %s' % (target, self.read)), 1)
        outside = self.root / 'return'
        outside.symlink_to(self.kit / 'repo', target_is_directory=True)
        self.assertGreaterEqual(self.hits('cd %s; %s' % (outside, self.read)), 1)
        (self.kit / 'local').symlink_to(self.kit / 'repo', target_is_directory=True)
        self.assertEqual(self.hits('cd local; %s' % self.read), 0)

    def test_existing_spellings_after_cd(self):
        outside = str(self.root / 'file')
        home = '$' + 'HOME'
        far = os.path.join(self.parent, self.parent, 'file')
        tokens = [outside, os.path.join(chr(126), 'file'), os.path.join(home, 'file'),
                  os.path.join('$' + '{HOME}', 'file'), far,
                  os.path.join('$' + 'PWD', far), os.path.join('$' + '{PWD}', far)]
        commands = ['cat %s' % token for token in tokens]
        commands += ['git -C%s status' % outside, 'git --git-dir=%s status' % outside,
                     'dd if=%s' % outside, "bash -c 'cat %s'" % outside,
                     'ls %s' % os.sep, 'cd', 'cd --', 'cd {fd}>output',
                     'cat <<END\ncontent\nEND\ncat %s' % outside,
                     'ls # $(true); cat %s' % outside]
        for index, command in enumerate(commands):
            with self.subTest(spelling=index):
                self.assertGreaterEqual(self.hits('cd repo; %s' % command), 1)

    def test_environment_startup_variables_removed(self):
        values = {'CDPATH': 'repo', 'BASH_ENV': 'startup', 'ENV': 'startup', 'KEEP': 'yes'}
        with mock.patch.object(run_reviews.os, 'environ', values):
            cleaned = run_reviews.clean_environment(self.kit)
        for key in ('CDPATH', 'BASH_ENV', 'ENV'):
            self.assertNotIn(key, cleaned)
        self.assertEqual(cleaned['KEEP'], 'yes')
        for key in ('TMPDIR', 'TEMP', 'TMP'):
            self.assertEqual(cleaned[key], str(self.kit / 'tmp'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
