"""Follow-up 0151: the session-start render and the projects index name a closed project only.

Runs the real SessionStart hook (`_system/session_state.sh`) of a fixture workspace
(pilot_fixture.py): a public project `open1`, a closed deidentified project `pilot` with planted
sample-name and CODE markers, and a fresh project from `create` (no dataset row: unclassified).
A closed project renders as `## <name> — closed (<label>)` and one `- <sub-stage>: <STATUS>` line
per stage 02 sub-stage; its index row names its class and nothing else. `open1`'s render and
row stay byte-identical to BASE_COMMIT's code on the same workspace (R-042). The render, the
index and `guard_hook.closed_projects` agree on the closed set, including a project whose
dataset row cannot be read.
"""
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO, run  # noqa: E402
import pilot_fixture as fx  # noqa: E402
import guard_hook  # noqa: E402

BASE_COMMIT = '1a009a4'
HISTORY_MARKER = 'MARKER0151historyS4'
CLOSED = {'pilot': 'deidentified_under_agreement', 'fresh': 'unclassified'}
HEAD = re.compile(r'^## (\S+) ')
STATE = {}


def setUpModule():
    tmp = tempfile.TemporaryDirectory(prefix='session-state-closed-')
    STATE['tmp'] = tmp
    STATE['top'] = Path(os.path.realpath(tmp.name))
    ws = fx.build(STATE['top'])
    STATE['ws'] = ws
    # (e): a HISTORY entry whose header carries a marker, on the closed project.
    history = ws / 'projects/pilot/HISTORY.md'
    history.chmod(0o644)
    with history.open('a') as fh:
        fh.write('\n## 2026-09-26 — %s — planted\nbody\n' % HISTORY_MARKER)
    # What the closed projects' detail was, per BASE_COMMIT's render: none of it may appear.
    STATE['old'] = old_workspace(ws)
    STATE['old_render'] = hook_text(STATE['old'], ['python3', '_system/project_state.py'])
    STATE['old_one'] = hook_text(STATE['old'], ['python3', '_system/project_state.py',
                                                '--project', str(ws / 'projects/open1')])
    subprocess.run(['bash', str(STATE['old'] / '_system/build_projects_index.sh'), str(ws)],
                   stdout=subprocess.PIPE, check=True)
    STATE['old_index'] = (ws / 'projects/_index.md').read_text()
    result = run(['bash', ws / '_system/session_state.sh'], cwd=ws)
    STATE['hook'] = result
    STATE['render'] = result.stdout.decode('utf-8')
    STATE['index'] = (ws / 'projects/_index.md').read_text()


def tearDownModule():
    for root, dirs, files in os.walk(str(STATE['top'])):
        for name in dirs + files:
            try:
                os.chmod(os.path.join(root, name), stat.S_IRWXU)
            except OSError:
                pass
    STATE['tmp'].cleanup()


def old_workspace(ws):
    """BASE_COMMIT's project_state.py and build_projects_index.sh, run on `ws`'s projects."""
    old = STATE['top'] / 'base' / 'gars'
    (old / '_system').mkdir(parents=True)
    for rel in ('_system/workspace.py', '_references/VERSION'):
        (old / rel).parent.mkdir(parents=True, exist_ok=True)
        (old / rel).write_bytes((ws / rel).read_bytes())
    for rel in ('gars/_system/project_state.py', 'gars/_system/build_projects_index.sh'):
        shown = subprocess.run(['git', 'show', '%s:%s' % (BASE_COMMIT, rel)], cwd=str(REPO),
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert shown.returncode == 0, shown.stderr
        (old / rel[len('gars/'):]).write_bytes(shown.stdout)
    (old / 'projects').symlink_to(ws / 'projects')
    return old


def hook_text(cwd, argv):
    result = run(argv, cwd=cwd)
    assert result.returncode == 0, result.stderr
    return result.stdout.decode('utf-8')


def sections(render):
    """{project name: [its lines]} from a render."""
    found, name = {}, None
    for line in render.splitlines():
        match = HEAD.match(line)
        if match:
            name = match.group(1)
            found[name] = []
        if name and line:
            found[name].append(line)
    return found


def rows(index):
    return dict((line.split(' | ')[0][2:], line) for line in index.splitlines()
                if line.startswith('| ') and not line.startswith('| Project'))


def statuses(project):
    lines = []
    for sub in sorted((project / '02_bioinformatics').glob('*/*')):
        status = sub / 'STATUS'
        lines.append('- %s: %s' % (sub.name, status.read_text().splitlines()[0].strip()
                                   if status.is_file() else 'NOT_STARTED'))
    return lines


class SessionStateClosedTests(unittest.TestCase):
    def test_a_closed_detail_never_reaches_the_session(self):
        self.assertEqual(STATE['hook'].returncode, 0, STATE['hook'].stderr)
        old = sections(STATE['old_render'])
        leaked = []
        for name in CLOSED:
            history = (STATE['ws'] / 'projects' / name / 'HISTORY.md').read_text()
            planted = [line[3:].strip() for line in history.splitlines()
                       if line.startswith('## ')]
            detail = list(fx.MARKERS) + [HISTORY_MARKER] + planted
            for line in old[name][1:]:
                sample = re.search(r'\(\d+ samples\)', line)
                if sample:
                    detail.append(sample.group(0))
                if 'config decisions still unmade: ' in line:
                    detail += line.split(': ', 1)[1].split(', ')
                if ' · artifacts: ' in line:
                    detail += [' · artifacts: ' + line.split(' · artifacts: ', 1)[1]]
            detail.append('created ')
            new = '\n'.join(sections(STATE['render'])[name])
            for text in detail:
                if text in new:
                    leaked.append((name, 'render', text))
            row = rows(STATE['index'])[name]
            for text in detail + ['filled', 'missing', 'rnaseq_bulk', 'COMPLETE']:
                if text in row:
                    leaked.append((name, 'index', text))
        # The fixture plants the markers in the public open1 too; everything else is checked.
        public = set(sections(STATE['render'])['open1'] + [rows(STATE['index'])['open1']])
        for marker in fx.MARKERS + (HISTORY_MARKER,):
            for where, text in (('render', STATE['render']), ('index', STATE['index'])):
                if any(marker in line for line in text.splitlines() if line not in public):
                    leaked.append(('any', where, marker))
        self.assertEqual(leaked, [])

    def test_b_closed_lines_are_the_rule_shape(self):
        render = sections(STATE['render'])
        index = rows(STATE['index'])
        for name, label in CLOSED.items():
            project = STATE['ws'] / 'projects' / name
            expected = ['## %s — closed (%s)' % (name, label)] + statuses(project)
            self.assertEqual(render[name], expected)
            self.assertEqual(index[name], '| %s | closed (%s) | — | — | — | — | — |'
                             % (name, label))
            one = hook_text(STATE['ws'], ['python3', '_system/project_state.py',
                                          '--project', 'projects/' + name])
            self.assertEqual(sections(one)[name], expected)
        self.assertEqual(render['pilot'][1:], ['- 01_nfcore-rnaseq-wrapper: COMPLETE',
                                               '- 02_rnaseq-de: COMPLETE'])

    def test_c_public_render_and_row_are_byte_identical(self):
        self.assertEqual(sections(STATE['render'])['open1'],
                         sections(STATE['old_render'])['open1'])
        self.assertEqual(rows(STATE['index'])['open1'], rows(STATE['old_index'])['open1'])
        one = hook_text(STATE['ws'], ['python3', '_system/project_state.py',
                                      '--project', str(STATE['ws'] / 'projects/open1')])
        self.assertEqual(one, STATE['old_one'])

    def test_c_no_closed_project_changes_nothing(self):
        ws = fx.build(STATE['top'] / 'open-only', closed=False)
        old = STATE['top'] / 'open-only' / 'base.sh'
        old.write_bytes((STATE['old'] / '_system/build_projects_index.sh').read_bytes())
        index = []
        for script in (old, ws / '_system/build_projects_index.sh'):
            subprocess.run(['bash', str(script), str(ws)], stdout=subprocess.PIPE, check=True)
            index.append([line for line in (ws / 'projects/_index.md').read_text().splitlines()
                          if not line.startswith('Last built: ')])
        self.assertEqual(index[0], index[1])
        new = hook_text(ws, ['python3', '_system/project_state.py'])
        base = STATE['top'] / 'open-only' / 'base' / 'gars'
        (base / '_system').mkdir(parents=True)
        for rel in ('_system/project_state.py', '_system/workspace.py', '_references/VERSION'):
            source = STATE['old'] / rel
            (base / rel).parent.mkdir(parents=True, exist_ok=True)
            (base / rel).write_bytes(source.read_bytes())
        (base / 'projects').symlink_to(ws / 'projects')
        self.assertEqual(new, hook_text(base, ['python3', '_system/project_state.py']))

    def test_f_closed_status_read_only_as_its_own_file(self):
        ws = fx.build(STATE['top'] / 'linked')
        sub = ws / 'projects/pilot' / fx.DE_STAGE
        (sub / 'STATUS').unlink()
        (sub / 'STATUS').symlink_to(ws / 'projects/pilot/00_data' / fx.ASSAY / 'samples.csv')
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        self.assertEqual(sections(render)['pilot'],
                         ['## pilot — closed (deidentified_under_agreement)'])
        self.assertNotIn('sample_id', render)

    def test_d_render_index_and_guard_agree_on_the_closed_set(self):
        ws = fx.build(STATE['top'] / 'drift')
        fx.register(ws, 'create', '--title', 'sealed', '--assays', fx.ASSAY)
        fx.register(ws, 'link', '--project', 'projects/sealed', '--assay', fx.ASSAY,
                    '--source', STATE['top'] / 'drift' / 'pubseq')
        fx.register(ws, 'finalize', '--project', 'projects/sealed', '--data-class', 'public',
                    '--purpose', 'fixture')
        row = ws / 'projects/sealed/00_data/dataset.tsv'
        row.chmod(0)
        if os.access(str(row), os.R_OK):
            self.skipTest('running as a user who reads a mode-0 file')
        guard = dict((name, label) for name, label, _ in guard_hook.closed_projects(str(ws)))
        self.assertEqual(guard, dict(CLOSED, sealed='unclassified'))
        listed = hook_text(ws, ['python3', '_system/project_state.py', '--closed-list'])
        self.assertEqual(dict(line.split('\t') for line in listed.splitlines()), guard)
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        closed_render = dict(re.match(r'^## (\S+) — closed \((\w+)\)$', line).groups()
                             for line in render.splitlines() if ' — closed (' in line)
        subprocess.run(['bash', str(ws / '_system/build_projects_index.sh'), str(ws)],
                       stdout=subprocess.PIPE, check=True)
        closed_index = dict(re.match(r'^\| (\S+) \| closed \((\w+)\) \|', line).groups()
                            for line in (ws / 'projects/_index.md').read_text().splitlines()
                            if '| closed (' in line)
        self.assertEqual(closed_render, guard)
        self.assertEqual(closed_index, guard)
        self.assertIn('## open1 — template', render)

    def test_e_planted_history_header_never_appears(self):
        self.assertIn(HISTORY_MARKER, STATE['old_render'])  # the plant is live at BASE_COMMIT
        self.assertNotIn(HISTORY_MARKER, STATE['render'])
        self.assertNotIn(HISTORY_MARKER, STATE['index'])


if __name__ == '__main__':
    result = unittest.main(verbosity=2, exit=False).result
    sys.stderr.flush()
    if result.wasSuccessful():
        print('EXIT session state (fixture): closed projects name and status only', flush=True)
    sys.exit(not result.wasSuccessful())
