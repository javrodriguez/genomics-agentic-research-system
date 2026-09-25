"""Row 13 step B (decision 0141, D5 and ruling D-iii): what a typed call returns from a closed
project.

Every registered tool is run through the real dispatcher of a fixture workspace
(pilot_fixture.py: a public project `open1`, a closed project `pilot`, an external folder), with
sample-name markers planted in the closed project's design, counts header, DE table and OUTPUTS
index and in the external folder. On the closed route no marker reaches stdout or stderr; a
door's output keeps only its keep-list; a path outside the workspace or outside the closed
project is refused with its named code; with no non-public project in the workspace the
dispatcher's output is byte-identical to BASE's (R-042).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, run  # noqa: E402
import pilot_fixture as fx  # noqa: E402
import guard_hook  # noqa: E402
from tools import closed_output as co  # noqa: E402

BASE_COMMIT = 'e589ce8'
REGISTRY = json.loads((GARS / '_system/tools/registry.json').read_text())['tools']
BY_NAME = dict((t['name'], t) for t in REGISTRY)
STATE = {}
W = co.WITHHELD


def setUpModule():
    tmp = tempfile.TemporaryDirectory(prefix='closed-outputs-')
    STATE['tmp'] = tmp
    STATE['top'] = Path(os.path.realpath(tmp.name))
    STATE['ws'] = fx.build(STATE['top'] / 'main')


def tearDownModule():
    STATE['tmp'].cleanup()


def leaves(value):
    if isinstance(value, dict):
        return [x for v in value.values() for x in leaves(v)]
    if isinstance(value, list):
        return [x for v in value for x in leaves(v)]
    return [value]


class EveryToolTests(unittest.TestCase):
    def assert_no_marker(self, text, where):
        for marker in fx.MARKERS:
            self.assertNotIn(marker, text, where)

    def test_marker_absent_from_every_tool(self):
        print('red-on-fault: filter skipped for one tool', flush=True)
        ws = STATE['ws']
        dataset = (ws / 'projects/pilot/00_data/dataset.tsv').read_bytes()
        ordered = sorted(REGISTRY, key=lambda t: t['name'].startswith('stage00_register'))
        seen = 0
        for tool in ordered:
            args = fx.place_args(tool, 'projects/pilot')
            with self.subTest(tool=tool['name']):
                code, record, raw = fx.tool_call(ws, tool['name'], args)
                self.assert_no_marker(raw, tool['name'])
                if record.get('type') == 'tool_refusal':
                    continue
                seen += 1
                if not fx.takes_place(tool):
                    continue                      # path-free: nothing to filter
                stdout, stderr = record['stdout'], record['stderr']
                self.assertTrue(stderr == '' or stderr.startswith(W), stderr)
                if tool['name'].startswith('pilot_log.'):
                    kept, withheld = co.pilot_lines(stdout)
                    self.assertEqual(withheld, 0, stdout)
                    continue
                parsed = json.loads(stdout)
                if parsed == {'withheld': True, 'exit_code': code}:
                    continue
                keep = tool['closed_output']
                for key, value in parsed.items():
                    if key not in keep:
                        self.assertEqual(value, W, (tool['name'], key))
                for leaf in leaves(parsed):
                    if isinstance(leaf, str) and leaf != W:
                        self.assertNotIn(str(ws), leaf)
                        self.assertFalse('projects/' in leaf or 'raw' in leaf.split('/'),
                                         (tool['name'], leaf))
                        if '/' in leaf:
                            self.assertRegex(leaf, co.LAYOUT.pattern + '|' + '|'.join(
                                map(re.escape, co.FIXED_NAMES)))
                self.assertNotIn('"detail": "', stdout.replace('"detail": "' + W, ''))
        self.assertGreater(seen, 40)
        self.assertEqual((ws / 'projects/pilot/00_data/dataset.tsv').read_bytes(), dataset)
        print('EXIT closed outputs (fixture): marker absent from every tool', flush=True)

    def test_positive_control_markers_are_planted(self):
        """The same calls on the public project, unfiltered, do carry the markers."""
        ws = STATE['ws']
        for name, args, marker in (
                ('fs.read', {'paths': ['projects/open1/' + fx.DESIGN]}, fx.DESIGN_MARKER),
                ('rnaseq_de.check', fx.door_args('rnaseq_de.check', 'projects/open1'),
                 fx.DESIGN_MARKER),
                ('fs.read', {'paths': ['projects/open1/' + fx.COUNTS]}, fx.COUNTS_MARKER),
                ('resolve_artifact', {'project': 'projects/open1', 'assay': fx.ASSAY,
                                      'list': True}, fx.GENE_MARKER)):
            with self.subTest(name=name, marker=marker):
                code, record, raw = fx.tool_call(ws, name, args)
                self.assertIn(marker, record['stdout'])

    def test_count_matrix_failure_keeps_code_loses_detail(self):
        print('red-on-fault: failure detail kept', flush=True)
        ws = STATE['ws']
        wrapper = ws / '_system/wrappers/rnaseq-de/rnaseq_de.py'
        project = ws / 'projects/pilot'
        direct = run([sys.executable, wrapper, 'check', '--project', project, '--counts',
                      project / fx.COUNTS, '--design', project / fx.DESIGN])
        self.assertIn(b'count matrix lacks column(s) for design sample(s): ' +
                      fx.DESIGN_MARKER.encode(), direct.stdout)
        code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', fx.door_args('rnaseq_de.check'))
        self.assertEqual(code, 1, raw)
        parsed = json.loads(record['stdout'])
        self.assertIn({'check': 'counts', 'detail': W}, parsed['failures'])
        self.assertEqual(parsed['ok'], False)
        self.assertNotIn('count matrix', raw)
        self.assertNotIn(fx.DESIGN_MARKER, raw)

    def test_collect_never_returns_history_entry(self):
        payload = json.dumps({'ok': True, 'command': 'collect', 'assay': 'rnaseq_bulk',
                              'failures': [], 'outputs': [
                                  {'type': 'de_results', 'role': 'native',
                                   'path': 'run/tables/de_results.csv'}],
                              'template_version': '2.4.0', 'model': 'claude-opus-5-5',
                              'history_entry': 'Counts supplied by: ' + fx.DESIGN_MARKER})
        stdout, _ = co.filter_output('rnaseq_de.collect', payload, '', 0)
        parsed = json.loads(stdout)
        self.assertEqual(parsed['history_entry'], W)
        self.assertEqual(parsed['outputs'], [{'type': 'de_results', 'role': 'native',
                                              'path': W}])
        self.assertEqual((parsed['template_version'], parsed['model']),
                         ('2.4.0', 'claude-opus-5-5'))
        self.assertNotIn(fx.DESIGN_MARKER, stdout)

    def test_door_keep_lists(self):
        ws = STATE['ws']
        code, record, raw = fx.tool_call(ws, 'resolve_artifact',
                                         fx.door_args('resolve_artifact'))
        parsed = json.loads(record['stdout'])
        self.assertEqual(parsed['resolved']['counts_gene'],
                         {'substage': '01_nfcore-rnaseq-wrapper', 'resolved': fx.COUNTS})
        self.assertEqual(parsed['resolved']['design'],
                         {'substage': '01_prepare_samplesheets', 'resolved': fx.DESIGN})
        code, record, raw = fx.tool_call(ws, 'resolve_artifact', {
            'project': 'projects/pilot', 'assay': fx.ASSAY, 'list': True})
        self.assertEqual(json.loads(record['stdout'])['artifacts'], W)
        code, record, raw = fx.tool_call(ws, 'resolve_artifact', {
            'project': 'projects/pilot', 'assay': fx.ASSAY, 'type': 'nothing_here'})
        self.assertEqual(json.loads(record['stdout'])['missing'], {'nothing_here': W})
        code, record, raw = fx.tool_call(ws, 'rnaseq_de.summary', {'project': 'projects/pilot'})
        self.assertEqual(json.loads(record['stdout']), {
            'ok': True, 'command': 'summary', 'assay': 'rnaseq_bulk', 'status': 'COMPLETE',
            'failures': [], 'gate': [], 'genes_tested': 5, 'padj_lt_0.05': {'up': 2, 'down': 1},
            'padj_lt_0.1': 3, 'na_padj': 1, 'samples_in_design': 4})
        code, record, raw = fx.tool_call(ws, 'executor.status', fx.door_args('executor.status'))
        self.assertEqual(set(json.loads(record['stdout']).values()), {W})

    def test_filter_rules(self):
        print('red-on-fault: keep-list widened', flush=True)
        self.assertEqual(co.filter_output('rnaseq_de.check', 'not json ' + fx.DESIGN_MARKER,
                                          'a\nb\nc\n', 3),
                         ('{"exit_code": 3, "withheld": true}\n', W + '; stderr lines: 3\n'))
        self.assertEqual(co.filter_output('fs.read', '{"ok": true}', '', 0)[0],
                         json.dumps({'ok': W}, indent=2) + '\n')
        stdout, _ = co.filter_output('rnaseq_de.prepare', json.dumps({
            'ok': True, 'wrote': ['submit.sh', fx.DESIGN_MARKER + '.sh'],
            'failures': [{'check': 'design', 'detail': fx.DESIGN_MARKER},
                         {'check': fx.DESIGN_MARKER, 'detail': 'x'}],
            'submit': '/abs/projects/pilot/submit.sh'}), '', 0)
        self.assertEqual(json.loads(stdout), {
            'ok': True, 'wrote': ['submit.sh', W], 'submit': W,
            'failures': [{'check': 'design', 'detail': W}, {'check': W, 'detail': W}]})
        stdout, _ = co.filter_output('executor.status', json.dumps({
            'ok': True, 'job_id': '123', 'state': 'FAILED:' + fx.DESIGN_MARKER,
            'terminal': True, 'error': fx.DESIGN_MARKER}), '', 0)
        self.assertEqual(json.loads(stdout), {'ok': True, 'job_id': '123', 'state': 'FAILED',
                                              'terminal': True, 'error': W})
        stdout, _ = co.filter_output('resolve_artifact', json.dumps({
            'ok': True, 'resolved': {'counts_gene': {
                'substage': '01_x', 'resolved': '02_bioinformatics/rnaseq_bulk/01_x/run/' +
                fx.DESIGN_MARKER + '.tsv', 'path': 'x'}}}), '', 0)
        self.assertEqual(json.loads(stdout)['resolved'],
                         {'counts_gene': {'substage': '01_x', 'resolved': W}})
        kept, withheld = co.pilot_lines('begin: span 0123456789abcdef; actor agent\n'
                                        'refused: ' + fx.DESIGN_MARKER + '\nfree text\n')
        self.assertEqual((kept, withheld), (['begin: span 0123456789abcdef; actor agent'], 2))

    def test_registry_keep_lists(self):
        for tool in REGISTRY:
            with self.subTest(tool=tool['name']):
                keep = tool['closed_output']
                self.assertIsInstance(keep, list)
                if tool['name'].startswith('pilot_log.'):
                    self.assertEqual(keep, [co.LINES])
                else:
                    self.assertTrue(set(keep) <= set(co.RULES), keep)
                if tool['name'] in fx.DOORS:
                    self.assertTrue(keep)
                elif tool['name'] != 'executor.cancel':
                    self.assertEqual(keep, [])
        self.assertNotIn('history_entry', BY_NAME['rnaseq_de.collect']['closed_output'])
        self.assertEqual(BY_NAME['rnaseq_de.summary']['closed_output'], co.SUMMARY_KEYS)


class ClosedRuleTests(unittest.TestCase):
    def test_outside_paths_refused_with_named_codes(self):
        print('red-on-fault: outside-path refusal', flush=True)
        ws, top = STATE['ws'], STATE['top'] / 'main'
        cases = [
            ([str(top / 'external/notes.txt')], 'path_outside_workspace'),
            (['projects/open1', '../external'], 'path_outside_workspace'),
            (['projects/pilot', 'projects/open1/' + fx.DESIGN], 'path_outside_closed_project'),
            (['projects/pilot', '_system/tool_call.py'], 'path_outside_closed_project'),
            (['projects/pilot', 'projects/fresh'], 'path_outside_closed_project'),
            (['projects/pilot', 'projects'], 'path_outside_closed_project'),
            (['projects/pilot', '~/x'], 'path_outside_workspace'),
        ]
        for strings, code in cases:
            with self.subTest(strings=strings):
                with self.assertRaises(co.ClosedRefusal) as caught:
                    co.closed(strings, ws)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(co.closed(['projects/pilot', 'projects/pilot/' + fx.DESIGN,
                                    'rnaseq_bulk', 'counts_gene', 'claude-opus-5-5'], ws),
                         'pilot')
        self.assertIsNone(co.closed(['projects/open1/' + fx.DESIGN, 'rnaseq_bulk'], ws))
        self.assertEqual(co.closed([str(top / 'declared/D1_S1_L001_R1_001.fastq.gz'),
                                    'projects/pilot'], ws), 'pilot')

    def test_raw_link_target_is_the_closed_project(self):
        print('red-on-fault: raw link target', flush=True)
        ws, top = STATE['ws'], STATE['top'] / 'main'
        target = str(top / 'seqrun/S2_S2_L001_R1_001.fastq.gz')
        self.assertEqual(co.closed([target], ws), 'pilot')
        self.assertEqual(co.closed(['projects/pilot', target], ws), 'pilot')
        with self.assertRaises(co.ClosedRefusal) as caught:
            co.closed(['projects/open1', target], ws)
        self.assertEqual(caught.exception.code, 'path_outside_closed_project')
        args = dict(fx.door_args('rnaseq_de.check', 'projects/open1'), counts=target)
        code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', args)
        self.assertEqual(code, 2, raw)
        self.assertTrue(record['message'].startswith('path_outside_closed_project:'))
        args = dict(fx.door_args('rnaseq_de.check'), counts=target)
        code, record, raw = fx.tool_call(ws, 'rnaseq_de.check', args)
        self.assertNotEqual(record.get('type'), 'tool_refusal', raw)
        # The wrapper's traceback on a gzip file is withheld whole; its line count is kept.
        self.assertEqual(json.loads(record['stdout']), {'exit_code': code, 'withheld': True})
        self.assertRegex(record['stderr'], '^' + re.escape(W) + '; stderr lines: [0-9]+\n$')
        self.assertNotIn('seqrun', raw)

    def test_contract_drift_with_the_guards_reader(self):
        """closed_output.closed and the guard's 0107 reader judge the same projects alike."""
        ws = STATE['ws']
        guard = [name for name, _, _ in guard_hook.closed_projects(str(ws))]
        ours = [name for name, _, _ in co.closed_projects(ws)]
        self.assertEqual(ours, guard)
        self.assertEqual(sorted(guard), ['fresh', 'pilot'])
        for path in sorted((ws / 'projects').iterdir()):
            if not path.is_dir():
                continue
            with self.subTest(project=path.name):
                verdict = co.closed(['projects/' + path.name + '/CONTEXT.md'], ws)
                self.assertEqual(verdict is None, guard_hook.project_is_public(str(path)))
                self.assertEqual(verdict, None if verdict is None else path.name)
        self.assertIs(co.guard_hook.closed_hit, guard_hook.closed_hit)


class BaseIdentityTests(unittest.TestCase):
    """R-042: with no non-public project in the workspace, the dispatcher is BASE's, byte for
    byte."""

    def test_public_output_byte_identical_to_base(self):
        print('red-on-fault: R-042 identity', flush=True)
        ws = fx.build(STATE['top'] / 'public', closed=False, declare=False)
        archive = subprocess.run(['git', 'archive', BASE_COMMIT, 'gars/_system'],
                                 cwd=str(REPO), stdout=subprocess.PIPE, check=True).stdout
        base = STATE['top'] / 'base-tree'
        base.mkdir()
        subprocess.run(['tar', '-x', '-C', str(base)], input=archive, check=True)
        calls = [('resolve_artifact', fx.door_args('resolve_artifact', 'projects/open1')),
                 ('resolve_artifact', {'project': 'projects/open1', 'assay': fx.ASSAY,
                                       'list': True}),
                 ('rnaseq_de.check', fx.door_args('rnaseq_de.check', 'projects/open1')),
                 ('executor.status', fx.door_args('executor.status', 'projects/open1')),
                 ('fs.read', {'paths': ['projects/open1/' + fx.DESIGN]}),
                 ('stage00_register.assays', {}),
                 ('rnaseq_de.check', dict(fx.door_args('rnaseq_de.check', 'projects/open1'),
                                          counts=str(STATE['top'] / 'main/external/notes.txt')))]
        ours = [fx.tool_call(ws, name, args)[2] for name, args in calls]
        current = ws / '_system'
        shutil.move(str(current), str(STATE['top'] / 'current-system'))
        shutil.copytree(str(base / 'gars/_system'), str(current))
        try:
            theirs = [fx.tool_call(ws, name, args)[2] for name, args in calls]
        finally:
            shutil.rmtree(str(current))
            shutil.move(str(STATE['top'] / 'current-system'), str(current))
        for (name, _), mine, base_out in zip(calls, ours, theirs):
            with self.subTest(tool=name):
                self.assertEqual(mine, base_out)
        self.assertIn(fx.DESIGN_MARKER, ours[4])


if __name__ == '__main__':
    unittest.main(verbosity=2)
