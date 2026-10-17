"""Gates a contract closes on one fixed word, re-asked on any other reply (FIXES.md, lane gars-t74).

GARS has no user-prompt hook, so no script sees what the user typed: a fixed word is held by the
contract's template naming exactly that word and its Process step re-asking on anything else.
"""
import re
import unittest
from support import GARS

STAGE00 = '00_initialize_project/CONTEXT.md'
STAGE01 = '01_prepare_samplesheets/CONTEXT.md'
ROUTER = '02_bioinformatics/CONTEXT.md'


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
    """Every Process step whose command block runs `command`, in order."""
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


def exit_rows(text, code):
    """The rows of the Definitions table under "The script's exit codes" for one code."""
    found = re.search(r"\*\*The script's exit codes\.\*\*.*?\n((?:\|[^\n]*\n)+)",
                      section(text, 'Definitions'), re.S)
    rows = [[cell.strip() for cell in line.strip().strip('|').split('|')]
            for line in (found.group(1).splitlines() if found else [])]
    return [row for row in rows if row and row[0] == str(code)]


class Stage01ExitTableTests(unittest.TestCase):
    def test_stage01_check_exit0_row_names_the_step_order_and_the_writer(self):
        rows = exit_rows(read(STAGE01), 0)
        self.assertTrue(rows, "no exit-0 row in stage 01's exit-code table")
        check = [row for row in rows if '--check' in ' '.join(row)]
        self.assertEqual(len(check), 1, 'the exit-0 table needs one row for the --check run: %r'
                         % rows)
        row = ' '.join(check[0])
        self.assertNotRegex(row, r'\bT[24]\b',
                            'a check-only exit 0 must not route to T2 or T4: %r' % row)
        self.assertRegex(row, r'steps? 6.*7.*8', 'the row must name steps 6, 7 and 8 in order')
        self.assertRegex(row, r'writer[^|]*(complete|finish)',
                         'the row must say the writer, not the check, completes the stage')


class Stage01GateWordTests(unittest.TestCase):
    """T7 and T5 close on `exclude` and `overwrite`; the writer refuses a switch with no
    matching check record (S01-yes), and step 10 sends that refusal back to the check."""

    def closing_words(self, text, name):
        block = template(text, name)
        self.assertTrue(block, '%s template not found' % name)
        last = [l.strip() for l in block.splitlines() if l.strip()][-1]
        return re.findall(r'`([^`]+)`', last)

    def test_stage01_gates_name_one_word_each(self):
        text = read(STAGE01)
        found = steps(text)
        for name, word, number in (('T7', 'exclude', '6'), ('T5', 'overwrite', '7')):
            with self.subTest(template=name):
                self.assertEqual(self.closing_words(text, name), [word, 'cancel'])
                body = found[number]
                self.assertIn('`%s`' % word, body)
                self.assertRegex(body, r'[Aa]ny other reply[^.]*%s again' % name,
                                 'step %s must re-send %s on any other reply' % (number, name))

    def test_stage01_refused_switch_returns_to_the_check(self):
        body = steps(read(STAGE01))['10']
        self.assertRegex(body, r'step 3', 'a refused switch must go back to the check (step 3)')
        self.assertIn('--check', body)



class RouterProtocolMenuTests(unittest.TestCase):
    """For a protocol assay (scrnaseq) the router offers the chemistry menu beside the genome
    and shows the chosen chemistry in T9 (R-protocol); `apply` refuses without `--protocol`."""

    def test_router_offers_and_confirms_the_chemistry(self):
        text = read(ROUTER)
        body = steps(text)['3a']
        self.assertIn('configure.py protocols --aligner', body,
                      'step 3a must run the chemistry menu for a protocol assay')
        self.assertIn('--protocol <n>', body, "step 3a's apply must pass the chosen chemistry")
        self.assertIn('--aligner', body.split('configure.py apply', 1)[-1],
                      "step 3a's apply must pass the config's aligner, not apply's default")
        render = text.split('**T9 — ', 1)[0].split('**T8 — ', 1)[-1]
        self.assertIn('`protocols`', render, 'T8 must say how the chemistry menu is rendered')
        self.assertRegex(template(text, 'T9'), r'protocol',
                         'T9 must show the chosen chemistry')
        closed = template(text, 'T10')
        self.assertIn('configure.py protocols', closed)
        self.assertIn('--protocol <n>', closed)


class RouterWriteGateTests(unittest.TestCase):
    """T9 closes on the reply `write`; step 3a writes only on it and re-sends T9 on any other
    reply, and `apply` writes only bytes equal to a recorded dry run (R-confirm)."""

    def test_router_config_gate_names_one_word(self):
        text = read(ROUTER)
        block = template(text, 'T9')
        self.assertTrue(block, 'T9 template not found')
        last = [l.strip() for l in block.splitlines() if l.strip()][-1]
        self.assertEqual(re.findall(r'`([^`]+)`', last), ['write'],
                         'T9 must close on the one fixed word `write`: %r' % last)
        body = steps(text)['3a']
        self.assertIn('`write`', body, 'step 3a must write only on the reply `write`')
        self.assertRegex(body, r'[Aa]ny other reply[^.]*T9 again',
                         'step 3a must re-send T9 on any other reply')
        closed = template(text, 'T10')
        self.assertIn('--dry-run', closed, "T10's terminal steps must run the dry run first")


if __name__ == '__main__':
    unittest.main()
