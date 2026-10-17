"""Stage 01-03 steps that read a file the guard refuses on a non-public project name a door or
what to tell the user (0107 item 11, 0141 item 12; change record 0291)."""
import re
import unittest
from support import GARS
import guard_hook

STAGES = ('01_prepare_samplesheets/CONTEXT.md', '02_bioinformatics/CONTEXT.md',
          '03_custom_analysis/CONTEXT.md')
SUBSTAGES = tuple(sorted(str(p.relative_to(GARS)) for p in
                         GARS.glob('02_bioinformatics/*/*/CONTEXT.md')))
# In-project files the guard refuses to Read on a non-public project (all but its dataset row and
# STATUS files), and resolve_artifact, which reads OUTPUTS.tsv and STATUS on the agent's behalf.
REFUSED = re.compile(r'_config/|samples\.csv|files\.csv|01_samplesheets/|_samplesheet\.csv|'
                     r'_design\.csv|OUTPUTS\.tsv|HISTORY\.md|PLAN\.md|resolve_artifact')
# 0107 item 11's list, held fixed so the detector above cannot quietly stop seeing it: stage 01's
# design, samplesheet and config, stage 02's config and OUTPUTS routing, stage 03's inputs and
# plan, and every HISTORY.md append; and, by ruling 2 of round 2, the steps that carry the stop
# or the door: each wrapper sub-stage's step 2, stage 03's step 2, the DE sub-stage's 4 to 8.
DE = '02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md'
NAMED = dict({'01_prepare_samplesheets/CONTEXT.md': ('2', '3', '13'),
              '02_bioinformatics/CONTEXT.md': ('3', '3a', '9'),
              '03_custom_analysis/CONTEXT.md': ('1', '2', '3', '5', '10')},
             **{path: ('2', '9') for path in SUBSTAGES if path != DE})
NAMED[DE] = ('4', '5', '6', '7', '8', '9')
# A spelling may wrap at either space, as steps 5 to 7 of the DE sub-stage do.
DOOR = re.compile(r'tool_call\.py\s+(%s)\s' % '|'.join(
    re.escape(door) for door in guard_hook.CLOSED_PROJECT_DOORS))


def section(text, name):
    found = re.search(r'^## %s\n(.*?)(?=^## )' % re.escape(name), text, re.M | re.S)
    return found.group(1) if found else ''


def steps(text):
    found = {}
    for part in re.split(r'^(?=\d+[a-z]?\. )', section(text, 'Process'), flags=re.M):
        number = re.match(r'(\d+[a-z]?)\. ', part)
        if number:
            found[number.group(1)] = part
    return found


def nonpublic_templates(text):
    return re.findall(r'^\*\*(T\d+) — Non-public project\*\*$', section(text, 'Response Format'),
                      re.M)


def silent_steps(read):
    """(steps checked, steps that name neither a door nor the Non-public template), each
    contract's text from read(path)."""
    silent, seen = [], 0
    for path in STAGES + SUBSTAGES:
        text = read(path)
        found, templates = steps(text), nonpublic_templates(text)
        assert len(templates) <= 1, path
        assert set(NAMED[path]) <= set(found), (path, sorted(found))
        for number, step in sorted(found.items()):
            if number not in NAMED[path] and not REFUSED.search(step):
                continue
            seen += 1
            if DOOR.search(step):
                continue
            if templates and re.search(r'\b%s\b' % templates[0], step):
                continue
            silent.append('%s step %s' % (path, number))
    return seen, silent


def contract(path):
    return (GARS / path).read_text()


def mutant(edits):
    """A reader that applies {path: (old, new)} edits in memory; each old must occur."""
    def read(path):
        text = contract(path)
        for old, new in edits.get(path, ()):
            assert old in text, (path, old)
            text = text.replace(old, new)
        return text
    return read


NFCORE = tuple(path for path in SUBSTAGES if '/01_nfcore-' in path)
STAGE03 = '03_custom_analysis/CONTEXT.md'
# The review's in-memory mutants (REVIEW-d699112 finding 2, ruling 2): each removes or
# misspells a stop or door step the detector must see.
MUTANTS = {
    'nf-core step 2 stop deleted': {
        path: (('   On a non-public project, reply T7 and stop here (Definitions).\n', ''),)
        for path in NFCORE},
    'executor.status misspelled in 02_rnaseq-de step 7': {
        DE: (("tool_call.py executor.status\n   '{\"workspace\"",
              "tool_call.py executor.statu\n   '{\"workspace\""),)},
    'stage 03 step 2 stop deleted': {
        STAGE03: (('\n   On a non-public project `create` is not a door: reply T7 and stop.', ''),)},
}


class ClosedProjectContractTests(unittest.TestCase):
    def test_every_refused_read_names_a_door_or_the_users_message(self):
        self.assertEqual(len(SUBSTAGES), 10)
        seen, silent = silent_steps(contract)
        print('refused-read steps: %d checked, %d silent' % (seen, len(silent)), flush=True)
        self.assertEqual(silent, [])

    def test_the_reviews_mutants_turn_the_detector_red(self):
        self.assertEqual(len(NFCORE), 7)
        for name, edits in sorted(MUTANTS.items()):
            with self.subTest(mutant=name):
                self.assertNotEqual(silent_steps(mutant(edits))[1], [], name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
