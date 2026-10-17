"""Gates a contract closes on one fixed word, re-asked on any other reply (FIXES.md, lane gars-t74).

GARS has no user-prompt hook, so no script sees what the user typed: a fixed word is held by the
contract's template naming exactly that word and its Process step re-asking on anything else.
"""
import re
import unittest
from support import GARS

STAGE00 = '00_initialize_project/CONTEXT.md'


def read(path):
    return (GARS / path).read_text()


def section(text, name):
    found = re.search(r'^## %s\n(.*?)(?=^## )' % re.escape(name), text, re.M | re.S)
    return found.group(1) if found else ''


def template(text, name):
    """The fenced block under a Response Format heading such as `**T4a — ...**`."""
    found = re.search(r'^\*\*%s — [^\n]*\*\*\n```\n(.*?)```' % re.escape(name),
                      section(text, 'Response Format'), re.M | re.S)
    return found.group(1) if found else ''


def steps(text):
    found = {}
    for part in re.split(r'^(?=\d+[a-z]?\. )', section(text, 'Process'), flags=re.M):
        number = re.match(r'(\d+[a-z]?)\. ', part)
        if number:
            found[number.group(1)] = ' '.join(part.split())
    return found


def step_running(text, command):
    """The one Process step whose command block runs `command`."""
    hits = [body for body in steps(text).values() if command in body]
    return hits


class Stage00LinkGateTests(unittest.TestCase):
    def test_stage00_link_gate_names_one_word(self):
        text = read(STAGE00)
        block = template(text, 'T4a')
        self.assertTrue(block, 'T4a template not found')
        last = [l.strip() for l in block.splitlines() if l.strip()][-1]
        self.assertEqual(re.findall(r'`([^`]+)`', last), ['link'],
                         'T4a must close on the one fixed word `link`: %r' % last)
        hits = step_running(text, 'stage00_register.py link ')
        self.assertEqual(len(hits), 1, 'expected one step running link')
        body = hits[0]
        self.assertIn('`link`', body, 'the link step must run only on the reply `link`')
        self.assertRegex(body, r'[Aa]ny other reply[^.]*T4a again',
                         'the link step must re-ask T4a on any other reply')


if __name__ == '__main__':
    unittest.main()
