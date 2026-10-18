"""Stage 01-03 steps that read a file the guard refuses on a non-public project name a door or
what to tell the user (0107 item 11, 0141 item 12; change record 0291); a step that spells a
door directly, or a step its Definitions lists as taking the dispatcher spelling, also gives
that spelling under the workspace-wide condition (change record 0323)."""
import json
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


def templates(text):
    """{template id: its fenced block} from the Response Format section."""
    return dict(re.findall(r'^\*\*(T\d+) — [^*]+\*\*\n```\n(.*?)```',
                           section(text, 'Response Format'), re.M | re.S))


def last_in_assay():
    """The sub-stage contracts that come last in their assay's row of the assay map."""
    last = {}
    for line in (GARS / '_references/assay_stage_skill_map.md').read_text().splitlines():
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        if len(cells) > 3 and cells[2] == '02_bioinformatics':
            last[cells[1]] = '02_bioinformatics/%s/%s/CONTEXT.md' % (cells[1], cells[3])
    return set(last.values())


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

STAGE02 = '02_bioinformatics/CONTEXT.md'
LOWER = 'configure.py lower --project projects/<title> --assay <Assay ID>'


def memory_step_problems(read):
    """T57 (0293): stage 02 fits compute.mem to the venue in its own step 3b, with its own
    confirmation T12 that names only that line, and on a non-public project its own question
    T13 naming only `lower` (REVIEW-4d631ae finding 4); the preflight names the remedy."""
    problems = []
    text = read(STAGE02)
    found, blocks = steps(text), templates(text)
    step = found.get('3b', '')
    public, _, closed = step.partition('On a non-public project')
    if not step:
        return ['no step 3b']
    if LOWER + ' --dry-run' not in public:
        problems.append('3b does not dry-run lower first')
    if not re.search(r'Reply T12 and \*\*wait', public):
        problems.append('3b does not wait on T12')
    if 'history_entry' not in public or 'HISTORY.md' not in public:
        problems.append('3b does not append the history_entry')
    if not re.search(r'lowered: null[^.]*step 4', public):
        problems.append('3b does not pass a null lowering to step 4')
    if 'needs_venue' not in public:
        problems.append('3b does not stop on needs_venue')
    t12 = blocks.get('T12', '')
    if 'compute.mem' not in t12:
        problems.append('T12 does not name compute.mem')
    for word in ('reference:', 'fasta', 'contrast:', 'formula:', 'peaks', 'apply'):
        if word in t12:
            problems.append('T12 renders a decision line: %s' % word)
    t13 = blocks.get('T13', '')
    if not closed or 'Reply T13 and wait' not in closed:
        problems.append('3b does not ask T13 on a non-public project')
    if not t13.strip().endswith('?') or LOWER not in t13 or 'apply' in t13:
        problems.append('T13 is not one question naming only lower')
    if LOWER in blocks.get('T11', '') or re.search(r'\bT11\b', closed):
        problems.append('T13 is merged into T11')
    if not re.search(r'[Yy]es[^.]*step 4', closed) or not re.search(r'[Nn]o[^.]*T10', closed):
        problems.append('3b non-public branch does not route yes to step 4 and no to T10')
    if LOWER not in blocks.get('T10', ''):
        problems.append('T10 does not name lower for step 3b')
    closed3a = found.get('3a', '')[found.get('3a', '').find('On a non-public project'):]
    if not re.search(r'[Yy]es[^.]*step 3b', closed3a):
        problems.append('3a non-public yes skips step 3b')
    preflight = text[text.find('**Venue preflight'):text.find('**Non-public project')]
    for word in ('configure.py lower', 'venue_too_small', 'never by a hand edit'):
        if word not in preflight:
            problems.append('preflight does not name %s' % word)
    if 'venue_too_small' not in read(STAGE03):
        problems.append('stage 03 vocabulary does not name venue_too_small')
    return problems


MEMORY_MUTANTS = {
    'T12 wait dropped': {STAGE02: (('Reply T12 and **wait**', 'Reply T12'),)},
    'decision line in T12': {STAGE02: (('  compute.mem: <from>  ->  <to>\n',
                                        '  compute.mem: <from>  ->  <to>\n  reference: <genome id>\n'),)},
    'T13 names apply': {STAGE02: (('Have you run python3 _system/' + LOWER,
                                   'Have you run python3 _system/configure.py apply and python3 _system/' + LOWER),)},
    'T13 merged back into T11': {STAGE02: (('Reply T13 and wait', 'Reply T11 and wait'),)},
    'lower without a dry run first': {STAGE02: ((LOWER + ' --dry-run\n', LOWER + '\n'),)},
}


# 0323: every contract with a Process section, the stage map's and the templates' included.
CONTRACTS = tuple(sorted(str(p.relative_to(GARS)) for p in GARS.glob('**/CONTEXT.md')
                         if p.relative_to(GARS).parts[0] != 'projects'))
REGISTRY = json.loads((GARS / '_system/tools/registry.json').read_text())['tools']
DOORS = {tool['name']: tool for tool in REGISTRY
         if tool['name'] in guard_hook.CLOSED_PROJECT_DOORS}
# The house phrase of 0141's ruling D-vii b: the direct spelling is refused for every project.
WORKSPACE_WIDE = re.compile(r'while any (non-public project )?exists in the workspace', re.I)


def direct(tool):
    """A door's direct spelling: its script's basename and verb, either wrapped; a verbless
    script counts only when an option follows it, so a mention of the file is not a call."""
    script = re.escape(tool['argv'][1].rsplit('/', 1)[-1])
    if len(tool['argv']) > 2:
        return re.compile(r'%s\s+%s\b' % (script, re.escape(tool['argv'][2])))
    return re.compile(r'%s\s+--' % script)


def dispatcher_problem(step, name):
    """'' when the step spells tool_call.py <name> with a JSON literal whose keys the door's
    input schema admits and which holds every required key, under the workspace-wide
    condition; else what is wrong."""
    schema = DOORS[name]['input_schema']
    calls = re.findall(r"tool_call\.py\s+%s\s+'(\{.*?\})'" % re.escape(name), step, re.S)
    if not calls:
        return 'no dispatcher spelling'
    for literal in calls:
        try:
            keys = set(json.loads(literal.replace(', ...]', ']')))
        except ValueError:
            return 'JSON literal does not parse'
        if not keys <= set(schema['properties']):
            return 'keys outside the schema: %s' % sorted(keys - set(schema['properties']))
        if not set(schema.get('required', ())) <= keys:
            return 'required keys missing: %s' % sorted(set(schema['required']) - keys)
    if not WORKSPACE_WIDE.search(' '.join(step.split())):
        return 'condition not workspace-wide'
    return ''


def door_steps(read):
    """(the step-door pairs that spell a door directly, those whose step lacks a valid
    dispatcher spelling, with the reason), each contract's text from read(path)."""
    checked, without = [], []
    for path in CONTRACTS:
        for number, step in sorted(steps(read(path)).items()):
            for name, tool in sorted(DOORS.items()):
                if not direct(tool).search(step):
                    continue
                checked.append('%s step %s %s' % (path, number, name))
                problem = dispatcher_problem(step, name)
                if problem:
                    without.append('%s step %s %s: %s' % (path, number, name, problem))
    return checked, without


def listed_door_steps(read):
    """(the step-door pairs of the steps a contract's Definitions lists as taking the dispatcher
    spelling, "use that spelling at steps N to M", where the step names the door only through
    tool_call.py and describes the direct call in prose; those whose step lacks the
    workspace-wide condition, or names no door at all), each contract's text from read(path)."""
    checked, without = [], []
    for path in CONTRACTS:
        text = read(path)
        listed = re.search(r'use that spelling at steps (\d+) to (\d+)',
                           ' '.join(section(text, 'Definitions').split()))
        if not listed:
            continue
        found = steps(text)
        for number in range(int(listed.group(1)), int(listed.group(2)) + 1):
            step = found.get(str(number), '')
            names = sorted(set(DOOR.findall(step)))
            if not names:
                without.append('%s step %d: names no door' % (path, number))
            for name in names:
                if direct(DOORS[name]).search(step):
                    continue
                checked.append('%s step %d %s' % (path, number, name))
                if not WORKSPACE_WIDE.search(' '.join(step.split())):
                    without.append('%s step %d %s: condition not workspace-wide'
                                   % (path, number, name))
    return checked, without


WRAPPERS = tuple(path for path in SUBSTAGES if '/01_nfcore-' in path)
CLUSTER = ('02_bioinformatics/scrnaseq/02_scrna-qc-cluster/CONTEXT.md',
           '02_bioinformatics/spatialvi/02_spatial-cluster-count/CONTEXT.md')
SIX_STATUS = ('02_bioinformatics/scrnaseq/01_nfcore-scrnaseq-wrapper/CONTEXT.md',
              '02_bioinformatics/spatialvi/01_nfcore-spatialvi-wrapper/CONTEXT.md')
# The pairs PLAN.md's sweep found on f047180c, held fixed so the detector cannot quietly stop
# seeing them: 27 unpaired, and the DE sub-stage's steps 6 and 7 and the three resolve_artifact
# steps, paired already.
DOOR_STEPS = sorted(
    ['02_bioinformatics/CONTEXT.md step 9 resolve_artifact', '%s step 3 resolve_artifact' % DE,
     '%s step 1 resolve_artifact' % STAGE03]
    + ['%s step 5 executor.submit' % path for path in WRAPPERS + CLUSTER]
    + ['%s step 7 executor.status' % path for path in WRAPPERS]
    + ['%s step 6 executor.status' % path for path in SIX_STATUS]
    + ['%s step %s executor.status' % (path, n) for path in CLUSTER for n in '678']
    + ['%s step 6 executor.submit' % DE, '%s step 7 executor.status' % DE,
       '%s step 8 executor.status' % DE,
       '%s step 7 executor.submit' % STAGE03, '%s step 8 executor.status' % STAGE03])
# The prose door steps of the one contract that lists its door steps (the DE sub-stage's
# Definitions, steps 3 to 8), held fixed so the listed-step check cannot quietly stop seeing them.
LISTED_DOOR_STEPS = ['%s step 4 rnaseq_de.check' % DE, '%s step 5 rnaseq_de.prepare' % DE,
                     '%s step 8 rnaseq_de.collect' % DE]
STATUS_LINE = ("   While any non-public project exists in the workspace, the direct status call is\n"
               "   refused (decision 0141): `python3 _system/tool_call.py executor.status\n"
               "   '{\"workspace\": \"<project dir>\", \"job-id\": \"<job_id>\"}'`; its state is in the\n"
               "   JSON of its `stdout`.\n")
# Each removes, misspells or breaks one dispatcher spelling the detector must see.
DOOR_MUTANTS = {
    'scrna-qc-cluster status dispatcher lines deleted': {CLUSTER[0]: ((STATUS_LINE, ''),)},
    'executor.submit misspelled in 02_rnaseq-de step 6': {
        DE: (('tool_call.py executor.submit\n', 'tool_call.py executor.submits\n'),)},
    'job_id for job-id in stage 03 step 8': {
        STAGE03: (('"job-id": "<job_id>"', '"job_id": "<job_id>"'),)},
    'script dropped from an nf-core submit': {WRAPPERS[0]: (
        ('"workspace": "<project dir>", "script": "<sub-stage dir>/submit.sh"',
         '"workspace": "<project dir>"'),)},
}

# Each puts one listed prose door step back under the non-public-only condition.
LISTED_MUTANTS = {
    'collect under the non-public-only condition in 02_rnaseq-de step 8': {DE: ((
        '   On a non-public project, or while any exists in the workspace: `python3 _system/tool_call.py\n'
        '   rnaseq_de.collect',
        '   On a non-public project: `python3 _system/tool_call.py\n   rnaseq_de.collect'),)},
}


class ClosedProjectContractTests(unittest.TestCase):
    def test_stage02_fits_memory_in_its_own_step_and_confirmation(self):
        self.assertEqual(memory_step_problems(contract), [])
        for name, edits in sorted(MEMORY_MUTANTS.items()):
            with self.subTest(mutant=name):
                self.assertNotEqual(memory_step_problems(mutant(edits)), [], name)

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

    def test_stage02_passes_3a_on_a_nonpublic_project_once_the_config_is_done(self):
        # Walk stage 02's Process as the agent on a non-public project, who cannot Read
        # _config/<Assay ID>.yaml (ruling 1 of round 2): step 3a's non-public branch must ask
        # the user (a template ending in a question), go on to step 4 on yes and reply T10 on
        # no; T10 must promise no routing; a sub-stage's T7 promises routing only after the
        # config is confirmed, and the last sub-stage of an assay none to a next sub-stage.
        text = contract('02_bioinformatics/CONTEXT.md')
        found, blocks = steps(text), templates(text)
        branch = found['3a'][found['3a'].find('On a non-public project'):]
        self.assertIn('On a non-public project', found['3a'])
        asked = [name for name in re.findall(r'\b(T\d+)\b', branch)
                 if blocks.get(name, '').strip().endswith('?')]
        self.assertEqual(len(asked), 1, branch)
        self.assertIn('_config/<Assay ID>.yaml', blocks[asked[0]])
        self.assertRegex(branch, r'[Yy]es[^.]*step 4')
        self.assertRegex(branch, r'[Nn]o[^.]*T10')
        self.assertNotIn('route', blocks['T10'])
        self.assertIn('done', blocks['T10'])
        for path in SUBSTAGES:
            block = templates(contract(path)).get(nonpublic_templates(contract(path))[0], '')
            with self.subTest(path=path):
                if 'stage 02' in block:
                    self.assertIn('config', block)
                if path in last_in_assay():
                    self.assertNotIn('next sub-stage', block)


    def test_every_door_step_names_its_dispatcher_spelling(self):
        checked, without = door_steps(contract)
        print('door steps: %d checked, %d without the dispatcher spelling'
              % (len(checked), len(without)), flush=True)
        self.assertEqual(without, [])
        self.assertEqual(checked, DOOR_STEPS)

    def test_the_door_step_mutants_turn_the_detector_red(self):
        for name, edits in sorted(DOOR_MUTANTS.items()):
            with self.subTest(mutant=name):
                self.assertNotEqual(door_steps(mutant(edits))[1], [], name)


    def test_every_listed_door_step_gives_the_workspace_wide_condition(self):
        checked, without = listed_door_steps(contract)
        print('listed door steps: %d checked, %d without the workspace-wide condition'
              % (len(checked), len(without)), flush=True)
        self.assertEqual(without, [])
        self.assertEqual(checked, LISTED_DOOR_STEPS)
        for name, edits in sorted(LISTED_MUTANTS.items()):
            with self.subTest(mutant=name):
                self.assertNotEqual(listed_door_steps(mutant(edits))[1], [], name)

if __name__ == '__main__':
    unittest.main(verbosity=2)
