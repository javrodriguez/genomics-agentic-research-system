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
import shutil
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
# Names the `<name>\t<label>` list cannot carry (review round 2 F-1): never written verbatim.
UNPRINTABLE = ('tab\tname', 'nl\nx', 'nl\nopen1', 'trail\n')
UNPRINTABLE_HEAD = '## (unprintable project name) — closed (unclassified)'
UNPRINTABLE_ROW = '| (unprintable project name) | closed (unclassified) | — | — | — | — | — |'
# A public-classed copy of open1 whose name the list cannot carry (review round 3 N-1).
PUBLIC_UNPRINTABLE = 'pub\tname'


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


def table(index):
    """The index's project rows, in order."""
    lines = index.split('\n')
    start = lines.index('|---|---|---|---|---|---|---|') + 1
    return [line for line in lines[start:] if line]


def closed_row(name, label):
    return '| %s | closed (%s) | — | — | — | — | — |' % (name, label)


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

    def test_b_project_is_named_and_judged_by_its_entry(self):
        # (F-3) a symlinked entry of projects/: --project prints the full render's line for it.
        ws = fx.build(STATE['top'] / 'symlinked')
        outside = STATE['top'] / 'symlinked' / 'outside_closed'
        shutil.copytree(str(ws / 'projects/pilot'), str(outside), symlinks=True)
        (ws / 'projects/linked').symlink_to(outside)
        expected = (['## linked — closed (deidentified_under_agreement)']
                    + statuses(ws / 'projects/linked'))
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        self.assertEqual(sections(render)['linked'], expected)
        for entry in ('projects/linked', str(ws / 'projects/linked'), 'projects/linked/'):
            one = hook_text(ws, ['python3', '_system/project_state.py', '--project', entry])
            self.assertEqual(sections(one), {'linked': expected}, entry)

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
        subprocess.run(['bash', str(ws / '_system/build_projects_index.sh'), str(ws)],
                       stdout=subprocess.PIPE, check=True)
        open1 = rows((ws / 'projects/_index.md').read_text())['open1']
        open1_render = sections(hook_text(ws, ['python3', '_system/project_state.py']))['open1']
        # (F-1) closed projects whose names the list format cannot carry, one of them spelled to
        # rewrite open1's row if it were split at its newline.
        for name in UNPRINTABLE:
            shutil.copytree(str(ws / 'projects/pilot'), str(ws / 'projects' / name),
                            symlinks=True)
        # (N-1) a public-classed unprintable name beside the closed ones: the label lookup
        # must not index a name the guard did not report.
        shutil.copytree(str(ws / 'projects/open1'), str(ws / 'projects' / PUBLIC_UNPRINTABLE),
                        symlinks=True)
        guard = dict((name, label) for name, label, _ in guard_hook.closed_projects(str(ws)))
        self.assertEqual(guard, dict(CLOSED, sealed='unclassified',
                                     **dict((n, CLOSED['pilot']) for n in UNPRINTABLE)))
        printable = dict((n, l) for n, l in guard.items() if n not in UNPRINTABLE)
        listed = hook_text(ws, ['python3', '_system/project_state.py', '--closed-list'])
        self.assertEqual([line.count('\t') for line in listed.splitlines()],
                         [1] * len(printable))
        self.assertEqual(dict(line.split('\t') for line in listed.splitlines()), printable)
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        closed_render = dict(re.match(r'^## (\S+) — closed \((\w+)\)$', line).groups()
                             for line in render.splitlines()
                             if ' — closed (' in line and line != UNPRINTABLE_HEAD)
        self.assertEqual(closed_render, printable)
        # An unprintable project is its heading alone; nothing of its name reaches the render.
        blocks = render.rstrip('\n').split('\n\n')
        self.assertEqual(blocks.count(UNPRINTABLE_HEAD), len(UNPRINTABLE) + 1)
        self.assertEqual(render.count('## (unprintable'), len(UNPRINTABLE) + 1)
        self.assertEqual(sections(render)['open1'], open1_render)
        self.assertEqual(set(sections(render)) - {'(unprintable'},
                         {'open1', 'fresh', 'pilot', 'sealed'})
        one = hook_text(ws, ['python3', '_system/project_state.py',
                             '--project', str(ws / 'projects' / PUBLIC_UNPRINTABLE)])
        self.assertEqual(one.split('\n\n', 1)[1], UNPRINTABLE_HEAD + '\n')
        self.assertNotIn('\t', render)
        for line in render.splitlines():
            self.assertFalse(line in ('x', 'name', 'open1') or line.startswith(('x ', 'open1 ')),
                             line)
        subprocess.run(['bash', str(ws / '_system/build_projects_index.sh'), str(ws)],
                       stdout=subprocess.PIPE, check=True)
        index = table((ws / 'projects/_index.md').read_text())
        self.assertEqual(sorted(index), sorted(
            [open1] + [closed_row(n, l) for n, l in printable.items()]
            + [UNPRINTABLE_ROW] * (len(UNPRINTABLE) + 1)))
        self.assertIn('## open1 — template', render)

    def test_g_a_guard_that_cannot_judge_closes_everything(self):
        # (F-2) the workspace's guard raises in closed_projects: render, --project and index.
        ws = fx.build(STATE['top'] / 'raises')
        with (ws / '_system/guard_hook.py').open('a') as fh:
            fh.write('\n\ndef closed_projects(root):\n'
                     '    raise OSError("fixture: the guard cannot judge")\n')
        names = ('fresh', 'open1', 'pilot')
        expected = dict((n, ['## %s — closed (unclassified)' % n]
                         + statuses(ws / 'projects' / n)) for n in names)
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        self.assertEqual(sections(render), expected)
        for name in names:
            one = hook_text(ws, ['python3', '_system/project_state.py',
                                 '--project', 'projects/' + name])
            self.assertEqual(sections(one), {name: expected[name]})
        subprocess.run(['bash', str(ws / '_system/build_projects_index.sh'), str(ws)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual(table((ws / 'projects/_index.md').read_text()),
                         [closed_row(n, 'unclassified') for n in names])

    def test_h_a_failing_closed_list_closes_every_row(self):
        # (F-2) --closed-list exits non-zero after a partial answer: no row trusts it.
        ws = fx.build(STATE['top'] / 'listfails')
        (ws / '_system/project_state.py').write_text(
            'import sys\nprint("fresh\\tunclassified")\nsys.exit(1)\n')
        subprocess.run(['bash', str(ws / '_system/build_projects_index.sh'), str(ws)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        self.assertEqual(table((ws / 'projects/_index.md').read_text()),
                         [closed_row(n, 'unclassified') for n in ('fresh', 'open1', 'pilot')])

    def test_i_closed_status_prints_only_a_writer_value(self):
        # (F-5) a closed STATUS line prints only when it is a value wrapperlib's writer produces.
        ws = fx.build(STATE['top'] / 'status')
        pilot = ws / 'projects/pilot'
        written = {
            fx.COUNTS_STAGE: 'FAILED:EXIT_1 4242 2026-09-26T06:00:00Z',
            fx.DE_STAGE: '%s,A' % fx.DESIGN_MARKER,
            '02_bioinformatics/rnaseq_bulk/03_reason_on_complete': 'COMPLETE:TIMEOUT',
            '02_bioinformatics/rnaseq_bulk/04_alias': 'COMPLETED',
            '02_bioinformatics/rnaseq_bulk/05_trailing': 'COMPLETE 2026-09-26T06:00:00Z extra',
            '02_bioinformatics/rnaseq_bulk/06_writer': 'COMPLETE 2026-09-26T06:00:00Z',
            # (N-4) the writer adds a job id only after SUBMITTED or RUNNING, then a timestamp.
            '02_bioinformatics/rnaseq_bulk/07_job_on_complete':
                'COMPLETE 4242 2026-09-26T06:00:00Z',
            '02_bioinformatics/rnaseq_bulk/08_running': 'RUNNING 4242 2026-09-26T06:00:00Z',
            '02_bioinformatics/rnaseq_bulk/09_job_no_stamp': 'SUBMITTED 4242',
            '02_bioinformatics/rnaseq_bulk/10_failed_stamp': 'FAILED:EXIT_1 2026-09-26T06:00:00Z',
        }
        for rel, line in written.items():
            (pilot / rel).mkdir(parents=True, exist_ok=True)
            (pilot / rel / 'STATUS').write_text(line + '\n')
        render = hook_text(ws, ['python3', '_system/project_state.py'])
        self.assertEqual(sections(render)['pilot'], [
            '## pilot — closed (deidentified_under_agreement)',
            '- 01_nfcore-rnaseq-wrapper: unrecognized',
            '- 02_rnaseq-de: unrecognized',
            '- 03_reason_on_complete: unrecognized',
            '- 04_alias: unrecognized',
            '- 05_trailing: unrecognized',
            '- 06_writer: COMPLETE 2026-09-26T06:00:00Z',
            '- 07_job_on_complete: unrecognized',
            '- 08_running: RUNNING 4242 2026-09-26T06:00:00Z',
            '- 09_job_no_stamp: unrecognized',
            '- 10_failed_stamp: FAILED:EXIT_1 2026-09-26T06:00:00Z'])
        self.assertNotIn(fx.DESIGN_MARKER, '\n'.join(sections(render)['pilot']))

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
