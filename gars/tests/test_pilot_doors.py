"""Row 13 step B (decision 0141): the pilot's doors open to the dispatcher spelling only.

Drives the real `_system/guard_hook.py` with json.dumps payloads, and the real
`_system/tool_call.py` of a fixture workspace (pilot_fixture.py), over a public project `open1`,
a closed project `pilot` and a fresh project from `create`. Ruling D-i names the eleven doors;
D-ii admits a door only through the dispatcher, D-vii (b) refuses a door's direct spelling whatever it
names while a closed project exists, and D-vii (a) keeps 0107's session-cwd rule for doors; D5 refuses a door call naming a path outside the
workspace or outside its closed project; D-iv keeps a declared-public folder registrable.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS  # noqa: E402
import pilot_fixture as fx  # noqa: E402
import guard_hook  # noqa: E402

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
        # neither outside the workspace nor outside the project.
        args = dict(fx.door_args('rnaseq_de.check'), counts=declared)
        exit_code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', args)
        self.assertNotEqual(record.get('type'), 'tool_refusal', raw)
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
