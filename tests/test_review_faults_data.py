"""Decision 0127: tr operands are data; runtime-built paths, no shell execution."""
import os
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
import run_reviews
from testing import temporary


class DataOperandTests(unittest.TestCase):
    def setUp(self):
        self.root = temporary(self)
        self.kit = self.root / 'k'
        (self.kit / 'repo').mkdir(parents=True)
        (self.kit / 'tmp').mkdir()
        self.sep = os.sep
        parent = chr(46) * 2
        # Outside the kit by each spelling of rule (i); none is a source literal.
        self.outside = [('absolute', os.path.join(os.sep, 'outside', 'file')),
                        ('tilde', chr(126) + os.sep + 'file'),
                        ('home', '$' + 'HOME' + os.sep + 'file'),
                        ('parent', os.path.join(parent, parent, 'file'))]

    def hits(self, command):
        event = {'type': 'tool_use', 'name': 'Bash', 'input': {'command': command}}
        return run_reviews.blindness([event], self.kit)['hits']

    def honest(self, commands):
        for label, command in commands:
            with self.subTest(honest=label):
                self.assertEqual(self.hits(command), 0, command)

    def bad(self, commands):
        for label, command in commands:
            with self.subTest(outside=label):
                self.assertGreaterEqual(self.hits(command), 1, command)

    def test_honest_tr_operands(self):
        s = self.sep
        commands = [
            # The deployment's call, as run inside its loop.
            ('real call', "for c in 'a b' 'c%sd'; do n=$(echo $c | tr '%s ' '__'); echo \"$n\"; done"
             % (s, s)),
            ('real call alone', "n=$(echo $c | tr '%s ' '__')" % s),
            ('plain', 'tr %s _' % s),
            ('delete', 'tr -d %s' % s),
            ('squeeze', "tr -s '%s' ' '" % s),
            ('end of options', "tr -- '%s' '_'" % s),
            ('long option', 'tr --delete %s' % s),
            ('option after operands', 'tr %s _ -s' % s),
            ('lone dash operand', 'tr - %s' % s),
            ('doubled separator set', 'tr %s _' % (s * 2)),
            ('in-kit redirections', 'tr %s _ < repo%sinput.txt > tmp%sout.txt' % (s, s, s)),
            ('pipeline', 'cat repo%sinput.txt | tr %s _ | sort' % (s, s)),
            ('prefix', 'env -- timeout 5 command -- tr -d %s' % s),
            ('full path tr', '%s -d %s' % (os.path.join(os.sep, 'usr', 'bin', 'tr'), s)),
            ('nested shell', "bash -c 'tr %s _ < repo%sinput.txt'" % (s, s)),
            ('sed y program', "sed 'y%s\\%s%s_%s' repo%sinput.txt" % (s, s, s, s, s)),
            ('sed y expression', "sed -e 'y%s\\%s%s_%s' repo%sinput.txt" % (s, s, s, s, s)),
        ]
        self.honest(commands)

    def test_redirections_stay_scanned(self):
        commands = []
        for label, path in self.outside:
            commands += [('from ' + label, 'tr %s _ < %s' % (os.sep, path)),
                         ('to ' + label, 'tr a b > %s' % path),
                         ('append ' + label, 'tr -d a >> %s' % path),
                         ('descriptor ' + label, 'tr a b 0< %s' % path),
                         ('after end of options ' + label, 'tr -- a b < %s' % path),
                         ('prefixed ' + label, 'env -- tr a b < %s' % path),
                         ('real loop ' + label,
                          "for c in x; do n=$(tr '%s ' '__' < %s); done" % (os.sep, path)),
                         ('then xargs ' + label, 'tr %s _ < %s | xargs cat' % (os.sep, path))]
        self.bad(commands)

    def test_outside_direction(self):
        commands = []
        for label, path in self.outside:
            commands += [('then cat ' + label, 'tr %s _ ; cat %s' % (os.sep, path)),
                         ('and cat ' + label, 'tr %s _ && cat %s' % (os.sep, path)),
                         ('piped cat ' + label, 'tr %s _ | cat %s' % (os.sep, path)),
                         ('substitution ' + label, 'tr a $(cat %s)' % path),
                         ('sed y input ' + label, "sed 'y%sa%sb%s' %s" % (os.sep, os.sep, os.sep, path))]
        commands += [('then list root', 'tr %s _ ; ls %s' % (os.sep, os.sep)),
                     ('xargs operand', 'tr %s _ | xargs cat %s' % (os.sep, self.outside[0][1]))]
        self.bad(commands)

    def test_word_pieces_stay_whole(self):
        # Item 22(d) outside tr: a separator inside a longer word of another
        # command is not a separator-only word. The corpus's one witness for
        # this rule was a tr set, which decision 0127 makes data.
        s = self.sep
        self.honest([
            ('git message', "git commit -m 'split a %s b'" % s),
            ('quoted in-kit name', "cat 'repo%snotes %s draft.txt'" % (s, s)),
            ('spaced option value', "git log --grep='a %s b'" % s)])

    def test_xargs_residual_named(self):
        # Item 20(c): a path assembled at run time from data and read through
        # xargs never appears as a token; the sandbox must refuse that read.
        command = 'printf %%s _outside_file | tr _ %s | xargs cat' % os.sep
        self.assertEqual(self.hits(command), 0, command)


if __name__ == '__main__':
    unittest.main(verbosity=2)
