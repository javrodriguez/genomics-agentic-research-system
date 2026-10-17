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
# plan, and every HISTORY.md append.
NAMED = dict({'01_prepare_samplesheets/CONTEXT.md': ('2', '3', '13'),
              '02_bioinformatics/CONTEXT.md': ('3', '3a', '9'),
              '03_custom_analysis/CONTEXT.md': ('1', '3', '5', '10')},
             **{path: ('9',) for path in SUBSTAGES})
DOOR = re.compile(r'tool_call\.py (%s) ' % '|'.join(
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


class ClosedProjectContractTests(unittest.TestCase):
    def test_every_refused_read_names_a_door_or_the_users_message(self):
        silent, seen = [], 0
        self.assertEqual(len(SUBSTAGES), 10)
        for path in STAGES + SUBSTAGES:
            text = (GARS / path).read_text()
            found, templates = steps(text), nonpublic_templates(text)
            self.assertLessEqual(len(templates), 1, path)
            self.assertTrue(set(NAMED[path]) <= set(found), (path, sorted(found)))
            for number, step in sorted(found.items()):
                if number not in NAMED[path] and not REFUSED.search(step):
                    continue
                seen += 1
                if DOOR.search(step):
                    continue
                if templates and re.search(r'\b%s\b' % templates[0], step):
                    continue
                silent.append('%s step %s' % (path, number))
        print('refused-read steps: %d checked, %d silent' % (seen, len(silent)), flush=True)
        self.assertEqual(silent, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
