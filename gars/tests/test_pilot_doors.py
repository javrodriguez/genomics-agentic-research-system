"""Row 13 step B (decision 0141): the pilot's doors open to the dispatcher spelling only.

Drives the real `_system/guard_hook.py` with json.dumps payloads, and the real
`_system/tool_call.py` of a fixture workspace (pilot_fixture.py), over a public project `open1`,
a closed project `pilot` and a fresh project from `create`. Ruling D-i names the eleven doors;
D-ii admits a door only through the dispatcher, D-vii (b) refuses a door's direct spelling whatever it
names while a closed project exists, and D-vii (a) keeps 0107's session-cwd rule for doors; D5 refuses a door call naming a path outside the
workspace or outside its closed project; D-iv keeps a declared-public folder registrable.
Step B review round 1 (F-1, F-2): an agent's Write inside a closed project is refused like the
Edit family, and the DE doors read their design and counts only at the fixed layout.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO  # noqa: E402
import pilot_fixture as fx  # noqa: E402
import guard_hook  # noqa: E402
from tools import closed_output as co  # noqa: E402

REGISTRY = json.loads((GARS / '_system/tools/registry.json').read_text())['tools']
BY_NAME = dict((t['name'], t) for t in REGISTRY)
STATE = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory(prefix='pilot-doors-')
    STATE['tmp'] = tmp
    STATE['top'] = Path(os.path.realpath(tmp.name))
    STATE['ws'] = fx.build(STATE['top'])
    STATE['open_ws'] = fx.build(STATE['top'] / 'no-closed', closed=False)


def tearDownModule():
    STATE['tmp'].cleanup()


class DoorTests(unittest.TestCase):
    def allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))

    def refused(self, result, *words):
        err = result.stderr.decode('utf-8', 'replace')
        self.assertEqual(result.returncode, 2, err)
        self.assertIn('Blocked:', err)
        for word in words:
            self.assertIn(word, err)
        for marker in fx.MARKERS:
            self.assertNotIn(marker, err)
        return err

    def test_doors_are_the_eleven_of_ruling_d_i(self):
        print('red-on-fault: doors widened', flush=True)
        self.assertEqual(guard_hook.CLOSED_PROJECT_DOORS, fx.DOORS)
        for name in fx.DOORS:
            self.assertIn(name, BY_NAME)
        for name in ('executor.cancel', 'stage01_samplesheet', 'configure.apply',
                     'configure.contrasts', 'stage03_analysis.create', 'fs.read'):
            self.assertNotIn(name, guard_hook.CLOSED_PROJECT_DOORS)

    def test_dispatcher_spelling_allowed_on_closed(self):
        print('red-on-fault: door dispatcher spelling', flush=True)
        ws = STATE['ws']
        for name in fx.DOORS:
            with self.subTest(door=name):
                self.allowed(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(
                    name, fx.door_args(name))}))
        print('EXIT pilot doors (fixture): dispatcher allowed on closed', flush=True)

    def test_direct_spelling_refused_on_closed(self):
        print('red-on-fault: door direct spelling', flush=True)
        ws = STATE['ws']
        for name in fx.DOORS:
            tool = BY_NAME[name]
            args = fx.door_args(name)
            with self.subTest(door=name, spelling='bare'):
                self.refused(fx.hook_call(ws, 'Bash', {'command': fx.bare(tool, args)}))
            if name.startswith('pilot_log.'):
                # The token spelled by hand. `begin` parses and addition 3 refuses it; the other
                # verbs are refused earlier, by the transport's parse: a four-token registry
                # prefix matches the first pilot_log entry only (policy.parse_argv, unchanged).
                command = fx.bare(tool, args).replace(
                    tool['argv'][2], tool['argv'][2] + ' --launched-by-dispatcher', 1)
                words = ('0141', "pilot log's writer") if name == 'pilot_log.begin' \
                    else ('R-092',)
                with self.subTest(door=name, spelling='bare with token'):
                    self.refused(fx.hook_call(ws, 'Bash', {'command': command}), *words)
            else:
                with self.subTest(door=name, spelling='bare'):
                    # addition 1's own refusal, which precedes D-vii (b)'s path-free one
                    self.refused(fx.hook_call(ws, 'Bash', {'command': fx.bare(tool, args)}),
                                 '0107', '0141', 'tool_call.py ' + name,
                                 'this call names project pilot')

    def test_direct_spelling_from_inside_the_closed_project(self):
        ws = STATE['ws']
        tool = BY_NAME['resolve_artifact']
        command = fx.bare(tool, {'project': '.', 'assay': fx.ASSAY, 'list': True}).replace(
            '_system/', '../../_system/', 1)
        self.refused(fx.hook_call(ws, 'Bash', {'command': command}, 'projects/pilot'), '0107')

    def test_direct_spelling_refused_while_any_project_is_closed(self):
        """Ruling D-vii (b): fail-closed, a door's direct spelling is refused whatever it names
        while a closed project exists, and the same call is allowed when none does."""
        print('red-on-fault: door direct spelling fail-closed', flush=True)
        ws, open_ws = STATE['ws'], STATE['open_ws']
        for name in fx.DOORS:
            if name.startswith('pilot_log.'):
                continue    # refused in every agent session (addition 3), closed or not
            command = fx.bare(BY_NAME[name], fx.door_args(name, 'projects/open1'))
            with self.subTest(door=name, workspace='closed project exists'):
                self.refused(fx.hook_call(ws, 'Bash', {'command': command}), '0141',
                             'tool_call.py ' + name)
            with self.subTest(door=name, workspace='no closed project'):
                self.allowed(fx.hook_call(open_ws, 'Bash', {'command': command}))
        # A door with no path at all: every door's schema requires a project, so the transport
        # refuses the path-free spelling (R-094) before the guard's closed-project rules.
        command = 'python3 _system/executorlib.py status 100 --workspace .'
        for root in (ws, open_ws):
            with self.subTest(command=command, root=str(root)):
                self.refused(fx.hook_call(root, 'Bash', {'command': command}), 'R-094')

    def test_dispatcher_from_inside_the_closed_project_refused(self):
        """Ruling D-vii (a): 0107's session-cwd rule holds for a door's dispatcher spelling."""
        print('red-on-fault: door dispatcher from inside', flush=True)
        ws = STATE['ws']
        cwd = 'projects/pilot'
        for name in fx.DOORS:
            # the public project by absolute path; the log's schema takes the workspace form
            args = fx.door_args(name, 'projects/open1' if name.startswith('pilot_log.')
                                else str(ws / 'projects/open1'))
            with self.subTest(door=name):
                self.refused(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(name, args, cwd)},
                                          cwd), '0107', "session's working directory")

    def test_non_doors_refused_on_closed_in_both_spellings(self):
        print('red-on-fault: non-doors stay closed', flush=True)
        ws = STATE['ws']
        checked = 0
        for tool in REGISTRY:
            if tool['name'] in fx.DOORS or not fx.takes_place(tool):
                continue
            args = fx.place_args(tool, 'projects/pilot')
            for spelling in ('dispatch', 'bare'):
                command = fx.dispatch(tool['name'], args) if spelling == 'dispatch' \
                    else fx.bare(tool, args)
                with self.subTest(tool=tool['name'], spelling=spelling):
                    self.refused(fx.hook_call(ws, 'Bash', {'command': command}))
                    checked += 1
        self.assertGreater(checked, 60)

    def test_dispatcher_refuses_outside_paths(self):
        """A door call the guard admits is refused by the real dispatcher before running."""
        print('red-on-fault: outside paths', flush=True)
        ws, top = STATE['ws'], STATE['top']
        external = str(top / 'external' / 'notes.txt')
        cases = [
            ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check'), counts=external),
             'path_outside_workspace'),
            ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check', 'projects/open1'),
                                     counts=external), 'path_outside_workspace'),
            ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check'),
                                     design='projects/open1/' + fx.DESIGN),
             'path_outside_closed_project'),
            ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check'),
                                     design='_references/VERSION'),
             'path_outside_closed_project'),
            ('executor.submit', dict(fx.door_args('executor.submit'),
                                     script='projects/fresh/submit.sh'),
             'path_outside_closed_project'),
        ]
        for name, args, code in cases:
            with self.subTest(door=name, code=code, args=args):
                self.allowed(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(name, args)}))
                exit_code, record, raw = fx.tool_call(ws, name, args)
                self.assertEqual(exit_code, 2, raw)
                self.assertEqual(record['type'], 'tool_refusal')
                self.assertTrue(record['message'].startswith(code + ':'), record)
                self.assertNotIn(str(top), raw)
                for marker in fx.MARKERS:
                    self.assertNotIn(marker, raw)

    def test_declared_source_is_not_outside(self):
        """D-iv: a folder a human declared public still registers; an undeclared one does not."""
        print('red-on-fault: declared source exemption', flush=True)
        ws, top = STATE['ws'], STATE['top']
        declared, undeclared = str(top / 'declared'), str(top / 'external')
        inspect = {'assay': fx.ASSAY, 'source': declared}
        self.allowed(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(
            'stage00_register.inspect', inspect)}))
        exit_code, record, raw = fx.tool_call(ws, 'stage00_register.inspect', inspect)
        self.assertEqual(exit_code, 0, raw)
        self.assertEqual(json.loads(record['stdout'])['sample_ids'], ['D1', 'D2'])  # unfiltered
        link = {'project': 'projects/fresh', 'assay': fx.ASSAY, 'source': declared}
        self.allowed(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(
            'stage00_register.link', link)}))
        exit_code, record, raw = fx.tool_call(ws, 'stage00_register.link', link)
        self.assertEqual(exit_code, 0, raw)
        self.assertTrue(any(p.name.startswith('D1_S1') for p in
                            (ws / 'projects/fresh/00_data' / fx.ASSAY / 'raw').iterdir()))
        # The same folder named by a door beside the closed project it names is public data,
        # neither outside the workspace nor outside the project; the DE door then refuses it as
        # not its fixed-layout counts (review round 1 F-1), never as an outside path.
        args = dict(fx.door_args('rnaseq_de.check'), counts=declared)
        exit_code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', args)
        self.assertEqual(exit_code, 2, raw)
        self.assertTrue(record['message'].startswith('path_not_fixed_layout:'), raw)
        for name, args in (('stage00_register.inspect', {'assay': fx.ASSAY,
                                                         'source': undeclared}),
                           ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check',
                                                                 'projects/open1'),
                                                    counts=undeclared))):
            with self.subTest(name=name):
                exit_code, record, raw = fx.tool_call(ws, name, args)
                self.assertEqual(exit_code, 2, raw)
                self.assertTrue(record['message'].startswith('path_outside_workspace:'), raw)
                self.assertNotIn(fx.EXTERNAL_MARKER, raw)

    def test_bare_outside_workspace_refused_by_addition_2(self):
        ws, top = STATE['ws'], STATE['top']
        tool = BY_NAME['rnaseq_de.check']
        args = dict(fx.door_args('rnaseq_de.check', 'projects/open1'),
                    counts=str(top / 'external/notes.txt'))
        self.refused(fx.hook_call(ws, 'Bash', {'command': fx.bare(tool, args)}),
                     'path_outside_workspace', '0141')
        exit_code, record, raw = fx.tool_call(ws, 'rnaseq_de.check',
                                              fx.door_args('rnaseq_de.check', 'projects/open1'))
        self.assertNotEqual(record.get('type'), 'tool_refusal', raw)
        self.assertIn(fx.DESIGN_MARKER, raw)    # a public project's output is not filtered



BASE_COMMIT = 'e589ce8'     # the row's base under gars/ (equal to ca925a1 there)


class ClosedWriteTests(unittest.TestCase):
    """F-2 / F-1: an agent's Write inside a closed project is refused, judged like the Edit
    family; Bash write routes into it stay refused; with no closed project nothing changes."""

    def allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))

    def refused(self, result, *words):
        err = result.stderr.decode('utf-8', 'replace')
        self.assertEqual(result.returncode, 2, err)
        for word in words:
            self.assertIn(word, err)
        return err

    def test_agent_write_inside_closed_project_refused(self):
        print('red-on-fault: closed write', flush=True)
        ws = STATE['ws']
        cases = [
            ({'file_path': 'projects/pilot/probe/a.csv'}, ''),
            ({'file_path': str(ws / 'projects/pilot/probe/b.csv')}, ''),
            ({'file_path': '../pilot/probe/c.csv'}, 'projects/open1'),
            ({'file_path': 'Projects/PILOT/probe/d.csv'}, ''),
            ({'file_path': 'projects/open1/../pilot/probe/e.csv'}, ''),
            ({'file_path': 'projects/pilot/HISTORY.md'}, ''),
            ({'file_path': 'projects/pilot/_config/rnaseq_bulk.yaml'}, ''),
            ({'file_path': 'projects/pilot/' + fx.DE_STAGE + '/scripts/run_de.py'}, ''),
            ({'file_path': 'projects/fresh/probe.csv'}, ''),
        ]
        for data, cwd in cases:
            data = dict(data, content='sample_id,condition\n' + fx.COUNTS_MARKER + ',A\n')
            with self.subTest(data=data['file_path'], cwd=cwd):
                self.refused(fx.hook_call(ws, 'Write', data, cwd), '0107', '0141',
                             'never writes inside a closed project')
        # Path boundaries: a sibling that only shares the prefix, and a public project beside
        # the closed one, are not inside it.
        for path in ('projects/pilot-2/a.csv', 'projects/open1/notes/a.csv'):
            with self.subTest(path=path):
                self.allowed(fx.hook_call(ws, 'Write', {'file_path': path, 'content': 'x'}))
        # The Edit family keeps 0107's own refusal, unchanged.
        err = self.refused(fx.hook_call(ws, 'Edit', {
            'file_path': 'projects/pilot/HISTORY.md', 'old_string': 'a', 'new_string': 'b'}),
            '0107')
        self.assertNotIn('never writes inside a closed project', err)

    def test_generated_script_written_after_prepare_refused(self):
        """F-2: after the prepare door writes scripts/run_de.py, no agent route replaces it."""
        print('red-on-fault: generated script', flush=True)
        ws = fx.build(STATE['top'] / 'prepared')
        counts = ws / 'projects/pilot' / fx.COUNTS
        # The human's matrix, with every design sample, so prepare succeeds.
        counts.write_text(counts.read_text().replace(fx.COUNTS_MARKER, fx.DESIGN_MARKER))
        self.allowed(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(
            'rnaseq_de.prepare', fx.door_args('rnaseq_de.prepare'))}))
        exit_code, record, raw = fx.tool_call(ws, 'rnaseq_de.prepare',
                                              fx.door_args('rnaseq_de.prepare'))
        self.assertEqual(exit_code, 0, raw)
        self.assertIn('scripts/run_de.py', json.loads(record['stdout'])['wrote'])
        relative = 'projects/pilot/' + fx.DE_STAGE + '/scripts/run_de.py'
        script = ws / relative
        before = script.read_bytes()
        calls = [('Write', {'file_path': relative, 'content': 'print(1)\n'}),
                 ('Write', {'file_path': str(script), 'content': 'print(1)\n'}),
                 ('Edit', {'file_path': relative, 'old_string': 'import', 'new_string': 'x'}),
                 ('MultiEdit', {'file_path': relative,
                                'edits': [{'old_string': 'import', 'new_string': 'x'}]})]
        calls += [('Bash', {'command': command % relative}) for command in (
            'echo x > %s', 'echo x >> %s', 'tee %s', 'tee -a %s', 'cp _references/VERSION %s',
            'mv projects/open1/HISTORY.md %s', 'sed -i s/import/x/ %s', "sed -i '' s/a/b/ %s")]
        for tool, data in calls:
            with self.subTest(tool=tool, data=data):
                self.refused(fx.hook_call(ws, tool, data))
        self.assertEqual(script.read_bytes(), before)

    def test_bash_writes_inside_closed_project_refused(self):
        ws = STATE['ws']
        for target in ('projects/pilot/probe.csv', 'projects/pilot/' + fx.DESIGN,
                       'projects/pilot/_config/rnaseq_bulk.yaml'):
            for command in ('echo x > %s', 'echo x >> %s', 'printf x 1> %s', 'tee %s',
                            'tee -a %s', 'cp _references/VERSION %s',
                            'mv projects/open1/HISTORY.md %s', 'sed -i s/a/b/ %s'):
                with self.subTest(command=command % target):
                    self.refused(fx.hook_call(ws, 'Bash', {'command': command % target}))

    def test_write_without_closed_project_unchanged(self):
        """R-042: with no closed project, Write and Edit are judged exactly as BASE's guard
        judges them (exit code and message)."""
        print('red-on-fault: R-042 write identity', flush=True)
        ws = STATE['open_ws']
        base = STATE['top'] / 'base-guard'
        base.mkdir()
        archive = subprocess.run(['git', 'archive', BASE_COMMIT, 'gars/_system'],
                                 cwd=str(REPO), stdout=subprocess.PIPE, check=True).stdout
        subprocess.run(['tar', '-x', '-C', str(base)], input=archive, check=True)
        hook = base / 'gars/_system/guard_hook.py'
        cases = [('Write', {'file_path': 'projects/open1/probe/a.csv', 'content': 'x'}, ''),
                 ('Write', {'file_path': str(ws / 'projects/open1/HISTORY.md'), 'content': 'x'},
                  ''),
                 ('Write', {'file_path': 'probe/a.csv', 'content': 'x'}, 'projects/open1'),
                 ('Write', {'file_path': 'projects/new/a.csv', 'content': 'x'}, ''),
                 ('Edit', {'file_path': 'projects/open1/HISTORY.md', 'old_string': 'a',
                           'new_string': 'b'}, ''),
                 ('Write', {'file_path': '_system/x.py', 'content': 'x'}, ''),
                 ('Write', {'file_path': 'projects/open1/00_data/dataset.tsv', 'content': 'x'},
                  '')]
        allowed = 0
        for tool, data, cwd in cases:
            with self.subTest(tool=tool, data=data, cwd=cwd):
                ours = fx.hook_call(ws, tool, data, cwd)
                theirs = fx.hook_call(ws, tool, data, cwd, hook=hook)
                self.assertEqual((ours.returncode, ours.stderr), (theirs.returncode,
                                                                  theirs.stderr))
                allowed += ours.returncode == 0
        self.assertEqual(allowed, 5)


class FixedLayoutTests(unittest.TestCase):
    """F-1, defence in depth: while a project is closed, rnaseq_de.check and .prepare take their
    design and counts only at the fixed-layout, machine-owned paths; a probe file anywhere else
    (placed by a human, or by any process outside the agent's guarded tools) is refused before
    the wrapper runs, so no exit code or ok bit answers a guess about the project's samples."""

    @classmethod
    def setUpClass(cls):
        cls.ws = fx.build(STATE['top'] / 'probe')
        project = cls.ws / 'projects/pilot'
        probe = project / 'probe'
        probe.mkdir()
        # The reviewer's oracle: a design naming a guessed sample, right and wrong.
        for name, guess in (('right', fx.COUNTS_MARKER), ('wrong', 'S9')):
            (probe / (name + '.csv')).write_text(
                'sample_id,condition\n%s,A\nS2,A\nS3,B\nS4,B\n' % guess)
        (probe / 'counts.tsv').write_text('gene_id\tgene_name\t%s\tS2\tS3\tS4\n'
                                          'G1\tg1\t1\t2\t3\t4\n' % fx.DESIGN_MARKER)
        (probe / 'design-link.csv').symlink_to(project / fx.DESIGN)
        de_counts = project / fx.DE_STAGE / fx.COUNTS[len(fx.COUNTS_STAGE) + 1:]
        de_counts.parent.mkdir(parents=True)
        shutil.copyfile(str(project / fx.COUNTS), str(de_counts))
        cls.de_counts = str(de_counts.relative_to(cls.ws))
        (cls.ws / 'projects/open1/probe.csv').write_text(
            'sample_id,condition\n%s,A\nS2,A\nS3,B\nS4,B\n' % fx.COUNTS_MARKER)

    def test_probe_inputs_refused(self):
        print('red-on-fault: fixed layout', flush=True)
        ws = self.ws
        refusals = []
        for name in ('rnaseq_de.check', 'rnaseq_de.prepare'):
            base = fx.door_args(name)
            for args in (dict(base, design='projects/pilot/probe/right.csv'),
                         dict(base, design='projects/pilot/probe/wrong.csv'),
                         dict(base, counts='projects/pilot/probe/counts.tsv'),
                         dict(base, counts=self.de_counts),
                         dict(base, design='projects/pilot/01_samplesheets/other_design.csv'),
                         dict(base, design='projects/pilot/probe/../probe/right.csv')):
                with self.subTest(door=name, args=args):
                    self.assertEqual(fx.hook_call(ws, 'Bash', {'command': fx.dispatch(
                        name, args)}).returncode, 0)
                    exit_code, record, raw = fx.tool_call(ws, name, args)
                    self.assertEqual(exit_code, 2, raw)
                    self.assertEqual(record['type'], 'tool_refusal')
                    self.assertTrue(record['message'].startswith('path_not_fixed_layout:'),
                                    raw)
                    self.assertNotIn('stdout', record)
                    self.assertNotIn('"ok"', raw)
                    for marker in fx.MARKERS:
                        self.assertNotIn(marker, raw)
                    refusals.append((name, raw))
        # A right guess and a wrong one read the same, byte for byte: no oracle.
        for name in ('rnaseq_de.check', 'rnaseq_de.prepare'):
            self.assertEqual(len(set(raw for n, raw in refusals if n == name)), 1)

    def test_fixed_layout_accepted(self):
        ws = self.ws
        project = str(ws / 'projects/pilot')
        for args in (fx.door_args('rnaseq_de.check'),
                     dict(fx.door_args('rnaseq_de.check'), design=project + '/' + fx.DESIGN,
                          counts=project + '/' + fx.COUNTS),
                     dict(fx.door_args('rnaseq_de.check'),
                          design='projects/pilot/probe/design-link.csv')):
            with self.subTest(args=args):
                exit_code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', args)
                self.assertNotEqual(record.get('type'), 'tool_refusal', raw)
                self.assertEqual(json.loads(record['stdout'])['failures'],
                                 [{'check': 'counts', 'detail': co.WITHHELD}])

    def test_public_project_unchanged(self):
        """R-042: a public project's door reads any path, unfiltered, as before."""
        args = dict(fx.door_args('rnaseq_de.check', 'projects/open1'),
                    design='projects/open1/probe.csv')
        exit_code, record, raw = fx.tool_call(self.ws, 'rnaseq_de.check', args)
        self.assertEqual(exit_code, 0, raw)
        self.assertEqual(json.loads(record['stdout'])['ok'], True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
