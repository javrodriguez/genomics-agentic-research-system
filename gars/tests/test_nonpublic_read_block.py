"""0107: a guarded session never reads a non-public project; a human declares public data.

Drives the real hook (`_system/guard_hook.py`) with synthetic payloads, as
test_protected_paths.py does, over fixture workspace roots built with the real stage 00 helper:
R0 has no declaration, R1 declares one folder public (`decl/`) and leaves another (`undecl/`)
undeclared. Every refusal is checked for the invariants in `refused()`.
"""
import gzip
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, run
import guard_hook
import wrapperlib

HOOK = GARS / '_system/guard_hook.py'
REG = GARS / '_system/stage00_register.py'
BASE_COMMIT = '0754ec6'
MARKER = 'MARKER-0107-planted-sample-value'
ASSAY = 'rnaseq_bulk'
SUB = '02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper'
REGISTRY = json.loads((GARS / '_system/tools/registry.json').read_text())['tools']
STAGE00_OPENING = ('stage00_register.inspect', 'stage00_register.link')

P = 'projects/pilot'
SAMPLES = P + '/00_data/rnaseq_bulk/samples.csv'
STATUS = P + '/' + SUB + '/STATUS'
DATASET = P + '/00_data/dataset.tsv'

ROOTS = {}
TMP = None


def fastqs(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        for read in ('R1', 'R2'):
            with gzip.open(str(folder / ('%s_L001_%s_001.fastq.gz' % (name, read))), 'wt') as fh:
                fh.write('@r0\nACGT\n+\nIIII\n')


def register(ws, *args):
    result = run([sys.executable, REG, '--workspace', ws] + list(args), cwd=ws)
    if result.returncode:
        raise AssertionError('stage00 %s: %s %s' % (args, result.stdout, result.stderr))
    return result


def dataset_text(data_class):
    header = ['data_class', 'purpose', 'agreement_ref', 'input_data_location',
              'permitted_backends', 'provider_exposure', 'retention', 'expiry']
    return '\t'.join(header) + '\n' + '\t'.join([data_class, 'fixture', 'none', '[]', 'local',
                                                'none', 'none', 'none']) + '\n'


def plant(project):
    """What a project at stage 02 holds: a design with a planted value, files.csv, an emitted
    samplesheet, a sub-stage's OUTPUTS.tsv and its STATUS through the real writer."""
    data = project / '00_data' / ASSAY
    data.mkdir(parents=True, exist_ok=True)
    samples = data / 'samples.csv'
    if samples.exists():
        samples.chmod(0o644)
    samples.write_text('sample_id,condition,group,replicate\nS1,%s,a,1\n' % MARKER)
    if not (data / 'files.csv').exists():
        (data / 'files.csv').write_text('sample_id,lane,fastq_1,fastq_2\n')
    (project / '01_samplesheets').mkdir(exist_ok=True)
    (project / '01_samplesheets/x.csv').write_text('sample,fastq_1\nS1,x\n')
    stage = project / SUB
    stage.mkdir(parents=True, exist_ok=True)
    (stage / 'OUTPUTS.tsv').write_text('type\tpath\ncounts\tx\n')
    wrapperlib.write_status(stage, 'CREATED')


def build_root(name, declare=False, only_public=False):
    top = Path(TMP) / name
    ws = top / 'gars'
    ws.mkdir(parents=True)
    for d in ('_references', '_templates'):
        shutil.copytree(str(GARS / d), str(ws / d))
    for d in ('_system', '.claude', 'projects'):
        (ws / d).mkdir()
    (top / '.gars-approvals').mkdir()
    seq = top / 'seqrun'
    fastqs(seq, ['S1_S1', 'S2_S2'])
    fastqs(ws / 'decl', ['D1_S1', 'D2_S2'])
    fastqs(ws / 'undecl', ['U1_S1', 'U2_S2'])
    projects = ws / 'projects'

    def made(title, source=None, data_class=None, *flags):
        register(ws, 'create', '--title', title, '--assays', ASSAY)
        if source is not None:
            register(ws, 'link', '--project', 'projects/' + title, '--assay', ASSAY,
                     '--source', str(source))
        if data_class is not None:
            register(ws, 'finalize', '--project', 'projects/' + title, '--data-class',
                     data_class, '--purpose', 'fixture', *flags)
        return projects / title

    plant(made('open1', seq, 'public'))
    if only_public:
        return ws
    plant(made('pilot', seq, 'deidentified_under_agreement', '--expiry', '2027-12-31'))
    plant(made('pilot-2', seq, 'public'))
    made('fresh')
    legacy = made('legacy', ws / 'decl')
    plant(legacy)
    ident = made('ident', seq)
    (ident / '00_data/dataset.tsv').write_text(dataset_text('identifiable'))
    plant(ident)
    public_row = top / 'public_row.tsv'
    public_row.write_text(dataset_text('public'))
    bad = {'bad-Public': dataset_text('Public'), 'bad-space': dataset_text('public '),
           'bad-nocol': dataset_text('public').replace('data_class', 'class', 1),
           'bad-tworows': dataset_text('public') + dataset_text('identifiable').split('\n')[1] + '\n',
           'bad-empty': '', 'bad-crlf': dataset_text('public').replace('\n', '\r\n'),
           'bad-symlink': None}
    for title, text in bad.items():
        project = made(title, seq)
        row = project / '00_data/dataset.tsv'
        if text is None:
            row.symlink_to(public_row)
        else:
            row.write_text(text)
        plant(project)
    # Registration fixtures: create's stamp plus raw links only.
    made('ready', ws / 'decl')
    made('undeclraw', ws / 'undecl')
    stamped = made('stamped', ws / 'decl')
    (stamped / '00_data/dataset.tsv').write_text(dataset_text('deidentified_under_agreement'))
    dangling = made('dangling')
    (dangling / '00_data' / ASSAY / 'raw' / 'D9_S9_L001_R1_001.fastq.gz').symlink_to(
        top / 'missing.fastq.gz')
    # Links for the symlink, `..` and two-bases cases.
    open1 = projects / 'open1'
    (open1 / 'lnk-pilot').symlink_to(projects / 'pilot/00_data', target_is_directory=True)
    (projects / 'pilot/lnk-open').symlink_to(open1, target_is_directory=True)
    (open1 / 'nest/projects').mkdir(parents=True)
    (open1 / 'nest/projects/pilot').symlink_to(open1, target_is_directory=True)
    stage = projects / 'pilot' / SUB
    (stage / 'STATUS.bak').write_text('x\n')
    (stage / 'xSTATUS').write_text('x\n')
    decl = ws / 'decl'
    # Probe links sit one level down, so decl/ itself stays a clean source to link.
    (decl / 'links').mkdir()
    (decl / 'links/to-undecl').symlink_to(ws / 'undecl', target_is_directory=True)
    (decl / 'links/to-pilot').symlink_to(projects / 'pilot/00_data/rnaseq_bulk',
                                         target_is_directory=True)
    (projects / 'pilot/lnk-decl').symlink_to(decl, target_is_directory=True)
    outward = decl / 'outward'
    fastqs(outward, ['O1_S1'])
    (outward / 'O1_S1_L001_R2_001.fastq.gz').unlink()
    (outward / 'O1_S1_L001_R2_001.fastq.gz').symlink_to(ws / 'undecl/U1_S1_L001_R2_001.fastq.gz')
    fastqs(decl / 'withdangling', ['W1_S1'])
    (decl / 'withdangling/W2_S2_L001_R1_001.fastq.gz').symlink_to(top / 'missing.fastq.gz')
    (decl / 'sub').mkdir()
    if declare:
        (ws / 'data_sources.tsv').write_text(declaration(ws))
    return ws


def declaration(ws, *rows):
    rows = rows or ((str(ws / 'decl'), 'public', 'lane fixture'),)
    return 'source\tdata_class\tdeclared_by\n' + ''.join('\t'.join(r) + '\n' for r in rows)


def setUpModule():
    global TMP
    tmp = tempfile.TemporaryDirectory(prefix='nonpublic-read-block-')
    TMP = os.path.realpath(tmp.name)
    ROOTS['tmp'] = tmp
    ROOTS['R0'] = build_root('r0')
    ROOTS['R1'] = build_root('r1', declare=True)
    ROOTS['base'] = base_hook()


def tearDownModule():
    ROOTS['tmp'].cleanup()


def base_hook():
    """The hook as it stood at the base commit, beside the same policy and registry."""
    system = Path(TMP) / 'base/_system'
    shutil.copytree(str(GARS / '_system/tools'), str(system / 'tools'))
    source = subprocess.run(['git', 'show', BASE_COMMIT + ':gars/_system/guard_hook.py'],
                            cwd=str(REPO), stdout=subprocess.PIPE, check=True).stdout
    (system / 'guard_hook.py').write_bytes(source)
    return system / 'guard_hook.py'


def door_hook(name, doors, extra_tool=None):
    """A test-only copy of the hook whose CLOSED_PROJECT_DOORS names `doors`."""
    system = Path(TMP) / name / '_system'
    shutil.copytree(str(GARS / '_system/tools'), str(system / 'tools'))
    if extra_tool:
        registry = json.loads((system / 'tools/registry.json').read_text())
        registry['tools'].append(extra_tool)
        (system / 'tools/registry.json').write_text(json.dumps(registry))
    source = HOOK.read_text()
    line = 'CLOSED_PROJECT_DOORS = ()                   # empty in this lane (0107)'
    assert source.count(line) == 1
    (system / 'guard_hook.py').write_text(source.replace(
        line, 'CLOSED_PROJECT_DOORS = %r' % (tuple(doors),)))
    return system / 'guard_hook.py'


def call(root, tool, data, cwd='', hook=HOOK):
    here = Path(root) / cwd if cwd else Path(root)
    return run([sys.executable, hook], root,
               json.dumps({'tool_name': tool, 'tool_input': data, 'cwd': str(here)}),
               {'CLAUDE_PROJECT_DIR': str(root)})


def up(cwd):
    return '../' * len([p for p in cwd.split('/') if p]) if cwd else ''


def dispatch(name, args, cwd=''):
    return 'python3 %s_system/tool_call.py %s %s' % (up(cwd), name,
                                                     shlex.quote(json.dumps(args)))


def bare(tool, args, cwd=''):
    if tool.get('filesystem'):
        words = [tool['argv'][0]] + args.get('flags', [])
        if 'pattern' in args:
            words.append(args['pattern'])
        return ' '.join(shlex.quote(w) for w in words + args['paths'])
    words = ['python3', up(cwd) + tool['argv'][1]] + tool['argv'][2:]
    for key, spec in tool['cli'].items():
        if key not in args:
            continue
        value = args[key]
        if value is True:
            words.append(spec['flag'])
            continue
        if spec['flag']:
            words.append(spec['flag'])
        words += value if isinstance(value, list) else [str(value)]
    return ' '.join(shlex.quote(w) for w in words)


def sample_args(tool, project):
    """Minimal valid arguments naming `project` wherever the tool takes a project or path."""
    schema = tool['input_schema']
    props = schema.get('properties', {})
    keys = list(schema.get('required', []))
    for optional in ('project', 'pattern'):
        if optional in props and optional not in keys:
            keys.append(optional)
    values = {'project': project, 'workspace': project, 'paths': [project + '/CONTEXT.md'],
              'source': project + '/00_data/rnaseq_bulk/raw', 'counts': project + '/c.csv',
              'design': project + '/d.csv', 'script': project + '/s.sh', 'pattern': 'x',
              'assay': ASSAY, 'assays': [ASSAY], 'title': 'T', 'slug': '01_x',
              'analysis': '01_x', 'job-id': '42', 'genome': 'GRCh38'}
    args = {}
    for key in keys:
        spec = props[key]
        if key in values:
            args[key] = values[key]
        elif 'enum' in spec:
            args[key] = spec['enum'][0]
        elif spec.get('type') == 'array':
            args[key] = ['x']
        else:
            args[key] = 'x'
    return args


def takes_place(tool):
    props = tool['input_schema'].get('properties', {})
    return any(k in props for k in ('project', 'workspace', 'paths', 'source'))


class HookCase(unittest.TestCase):
    def refused(self, result, rule='0107', root=None):
        err = result.stderr.decode('utf-8', 'replace')
        self.assertEqual(result.returncode, 2, err)
        self.assertIn('Blocked:', err)
        self.assertIn(rule, err)
        self.assertNotIn(MARKER, err)
        path = Path(root or ROOTS['R1']) / 'data_sources.tsv'
        if path.exists():
            for line in path.read_text().splitlines():
                if line.strip():
                    self.assertNotIn(line, err)
        return err

    def allowed(self, result):
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8', 'replace'))

    def expect(self, result, expect, root):
        if expect == 'allow':
            self.allowed(result)
        elif expect == 'block':
            self.refused(result, '0107', root)
        else:                                   # refused at the base already (schema/transport)
            self.refused(result, 'R-092', root)


# family, tool, input (a Bash command or a tool_input), cwd, expectation. `block`: refused by
# the 0107 rule; `base`: refused before the rule runs (schema or transport), still a refusal.
READS = [
    ('read', 'Read', {'file_path': SAMPLES}, '', 'block'),
    ('read', 'Read', {'file_path': DATASET}, '', 'allow'),
    ('read', 'Read', {'file_path': STATUS}, '', 'allow'),
    ('read', 'Bash', 'cat ' + STATUS, '', 'allow'),
    ('read', 'Bash', dispatch('fs.read', {'paths': [STATUS]}), '', 'allow'),
    ('read', 'Bash', 'cat ' + DATASET, '', 'allow'),
    ('read', 'Read', {'file_path': STATUS + '.bak'}, '', 'block'),
    ('read', 'Read', {'file_path': P + '/' + SUB + '/xSTATUS'}, '', 'block'),
    ('read', 'Read', {'file_path': P + '/CONTEXT.md'}, '', 'block'),
    ('read', 'Read', {'file_path': 'projects/open1/00_data/rnaseq_bulk/samples.csv'}, '', 'allow'),
    ('read', 'Read', {'file_path': 'projects/pilot-2/00_data/rnaseq_bulk/samples.csv'}, '', 'allow'),
    ('read', 'Bash', 'cat projects/pilot-2/00_data/rnaseq_bulk/samples.csv', '', 'allow'),
    ('glob', 'Glob', {'path': P, 'pattern': '*'}, '', 'block'),
    ('glob', 'Glob', {'pattern': '**/*.csv'}, '', 'block'),
    ('glob', 'Glob', {'path': '_system', 'pattern': '../projects/pilot/**'}, '', 'block'),
    ('grep', 'Grep', {'path': SAMPLES, 'pattern': 'S1'}, '', 'block'),
    ('grep', 'Grep', {'path': P, 'pattern': 'S1'}, '', 'block'),
    ('grep', 'Grep', {'pattern': 'S1'}, '', 'block'),
    ('grep', 'Grep', {'path': 'projects', 'pattern': 'S1'}, '', 'block'),
    ('bash', 'Bash', 'cat ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'head ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'tail ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'wc ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'stat ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'shasum ' + SAMPLES, '', 'block'),
    ('bash', 'Bash', 'grep -r x ' + P, '', 'block'),
    ('bash', 'Bash', 'rg x .', '', 'block'),
    ('bash', 'Bash', 'find projects', '', 'block'),
    ('bash', 'Bash', 'ls -R .', '', 'base'),
    ('bash', 'Bash', 'ls --recursive .', '', 'base'),
    ('bash', 'Bash', 'ls projects/pilot/00_data', '', 'block'),
    ('bash', 'Bash', 'ls projects/pilot', '', 'block'),
    ('bash', 'Bash', 'grep -f %s x STATUS' % SAMPLES, '', 'base'),
    ('bash', 'Bash', 'wc --files0-from=' + SAMPLES, '', 'base'),
    ('bash', 'Bash', 'grep -rf%s x .' % SAMPLES, '', 'base'),
    ('option', 'Bash', 'python3 _system/stage00_register.py finalize --project projects/open1 '
     '--data-class public --purpose fixture --model -m' + SAMPLES, '', 'block'),
    ('option', 'Bash', 'python3 _system/stage00_register.py finalize --project projects/open1 '
     '--data-class public --purpose fixture --model=' + SAMPLES, '', 'block'),
    ('dispatch', 'Bash', dispatch('fs.read', {'paths': [SAMPLES]}), '', 'block'),
    ('dispatch', 'Bash', dispatch('fs.read', {'paths': [SAMPLES]}, 'projects/open1'),
     'projects/open1', 'block'),
    ('dotdot', 'Bash', 'cat ../pilot/00_data/rnaseq_bulk/samples.csv', 'projects/open1', 'block'),
    ('dotdot', 'Read', {'file_path': '../pilot/00_data/rnaseq_bulk/samples.csv'},
     'projects/open1', 'block'),
    ('symlink', 'Bash', 'cat projects/open1/lnk-pilot/rnaseq_bulk/samples.csv', '', 'block'),
    ('symlink', 'Read', {'file_path': 'projects/open1/lnk-pilot/rnaseq_bulk/samples.csv'}, '',
     'block'),
    ('symlink', 'Bash', 'cat projects/pilot/lnk-open/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/ident/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/fresh/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/legacy/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-Public/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-space/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-nocol/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-tworows/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-empty/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-crlf/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/bad-symlink/CONTEXT.md', '', 'block'),
    ('classes', 'Bash', 'cat projects/open1/CONTEXT.md', '', 'allow'),
]

EXPANSION = [
    ('glob', 'Bash', 'cat projects/pil*/00_data/rnaseq_bulk/samples.csv', '', 'block'),
    ('brace', 'Bash', 'cat projects/{pilot,open1}/CONTEXT.md', '', 'block'),
    ('bracket', 'Bash', 'cat projects/pilo[t]/CONTEXT.md', '', 'block'),
    ('qualifier', 'Bash', 'ls projects/*(/)', '', 'block'),
    ('tilde', 'Bash', 'cat ~/x', '', 'block'),
    ('tilde', 'Bash', 'ls ~', '', 'block'),
    ('tilde', 'Bash', dispatch('fs.read', {'paths': ['~/x']}), '', 'block'),
    ('pattern-slot', 'Bash', 'grep pil* CONTEXT.md', '', 'block'),
    ('raw', 'Bash', 'ls projects/pilot/00_data/rnaseq_bulk/raw/*', '', 'block'),
    ('cost', 'Bash', "grep 'a.*b' STATUS", '', 'block'),
    ('cost', 'Bash', "grep 'a.*b' STATUS", '_system', 'allow'),
    ('cost', 'Bash', dispatch('fs.search', {'pattern': 'a.*b', 'paths': ['STATUS']}), '',
     'block'),
    ('cost', 'Bash', dispatch('fs.search', {'pattern': 'a.*b', 'paths': ['STATUS']}, '_system'),
     '_system', 'allow'),
]

PRE = [
    ('pre', 'Bash', 'rg x STATUS --pre=bash', '', 'base'),
    ('pre', 'Bash', "rg --pre-glob '*' x STATUS", '', 'base'),
    ('pre', 'Bash', dispatch('fs.inspect', {'pattern': '--pre=bash', 'paths': ['STATUS']}), '',
     'pre'),
    ('pre', 'Bash', 'python3 _system/stage00_register.py assays --select --pre', '', 'pre'),
]


class GridTests(HookCase):
    def grid(self, rows, root_key='R0'):
        root = ROOTS[root_key]
        for family, tool, data, cwd, expect in rows:
            data = {'command': data} if isinstance(data, str) else data
            with self.subTest(family=family, tool=tool, data=data, cwd=cwd):
                result = call(root, tool, data, cwd)
                if expect == 'pre':
                    err = self.refused(result, '0107', root)
                    self.assertIn('--pre', err)
                    self.assertIn('R-092', err)
                else:
                    self.expect(result, expect, root)

    def test_reads(self):
        print('red-on-fault: reads', flush=True)
        self.grid(READS)

    def test_shell_expansion(self):
        print('red-on-fault: shell expansion', flush=True)
        self.grid(EXPANSION)

    def test_rg_pre(self):
        print('red-on-fault: rg --pre', flush=True)
        self.grid(PRE)

    def test_case_variant(self):
        print('red-on-fault: case variant', flush=True)
        root = ROOTS['R0']
        if not (root / 'projects/PILOT').exists():
            self.skipTest('case-sensitive filesystem: the case-variant probe needs a '
                          'case-insensitive one')
        for data in ({'file_path': 'projects/PILOT/00_data/rnaseq_bulk/samples.csv'},):
            self.refused(call(root, 'Read', data), root=root)
        self.refused(call(root, 'Bash', {'command': 'cat projects/Pilot/CONTEXT.md'}), root=root)


class EveryToolTests(HookCase):
    def test_every_registered_tool(self):
        print('red-on-fault: every registered tool', flush=True)
        root, base = ROOTS['R0'], ROOTS['base']
        checked = 0
        for tool in REGISTRY:
            if not takes_place(tool):
                continue
            for spelling in ('dispatch', 'bare'):
                def command(project, cwd=''):
                    args = sample_args(tool, project)
                    return dispatch(tool['name'], args, cwd) if spelling == 'dispatch' \
                        else bare(tool, args, cwd)
                reference = call(root, 'Bash', {'command': command('projects/open1')},
                                 hook=base)
                ours = call(root, 'Bash', {'command': command('projects/open1')})
                with self.subTest(tool=tool['name'], spelling=spelling, project='open1'):
                    if tool['name'] in STAGE00_OPENING:
                        self.refused(ours, root=root)
                    else:
                        self.assertEqual(ours.returncode, reference.returncode, ours.stderr)
                        if ours.returncode:
                            self.assertEqual(ours.stderr, reference.stderr)
                for project in ('projects/pilot', 'projects/fresh'):
                    with self.subTest(tool=tool['name'], spelling=spelling, project=project):
                        err = self.refused(call(root, 'Bash', {'command': command(project)}),
                                           'Blocked:', root)
                        if reference.returncode == 0 or tool['name'] in STAGE00_OPENING:
                            self.assertIn('0107', err)
                        checked += 1
        self.assertGreater(checked, 100)

    def test_path_free_calls_stay_open(self):
        print('red-on-fault: path-free calls', flush=True)
        root = ROOTS['R0']
        for command in ('python3 _system/stage00_register.py assays',
                        'python3 _system/configure.py genomes',
                        'python3 _system/stage00_register.py create --title T --assays ' + ASSAY,
                        dispatch('stage00_register.create', {'title': 'T', 'assays': [ASSAY]})):
            with self.subTest(command=command):
                self.allowed(call(root, 'Bash', {'command': command}))

    def test_cwd_inside_closed_project(self):
        print('red-on-fault: cwd inside a closed project', flush=True)
        root, base, cwd = ROOTS['R0'], ROOTS['base'], P
        target = str(root / 'projects/open1')
        for tool in REGISTRY:
            args = sample_args(tool, target)
            for command in (dispatch(tool['name'], args, cwd), bare(tool, args, cwd)):
                with self.subTest(tool=tool['name'], command=command):
                    reference = call(root, 'Bash', {'command': command}, cwd, base)
                    err = self.refused(call(root, 'Bash', {'command': command}, cwd),
                                       'Blocked:', root)
                    if reference.returncode == 0:
                        self.assertIn('0107', err)


def stage00(verb, *args):
    return 'python3 _system/stage00_register.py %s %s' % (
        verb, ' '.join(shlex.quote(str(a)) for a in args))


class Stage00Tests(HookCase):
    def bash(self, root, command, cwd=''):
        return call(root, 'Bash', {'command': command}, cwd)

    def test_without_declaration(self):
        print('red-on-fault: stage 00 without a declaration', flush=True)
        root = ROOTS['R0']
        for command in (
                stage00('inspect', '--assay', ASSAY, '--source', root / 'decl'),
                stage00('inspect', '--assay', ASSAY, '--source', root / 'undecl'),
                stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                        root / 'decl'),
                stage00('link', '--project', 'projects/open1', '--assay', ASSAY, '--source',
                        root / 'decl'),
                stage00('finalize', '--project', 'projects/ready', '--data-class', 'public',
                        '--purpose', 'fixture'),
                stage00('finalize', '--project', 'projects/fresh', '--data-class',
                        'deidentified_under_agreement', '--purpose', 'fixture'),
                dispatch('stage00_register.inspect', {'assay': ASSAY,
                                                      'source': str(root / 'decl')})):
            with self.subTest(command=command):
                self.refused(self.bash(root, command), root=root)

    def declared_allowed(self, root):
        decl = root / 'decl'
        return [stage00('inspect', '--assay', ASSAY, '--source', decl),
                stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source', decl),
                dispatch('stage00_register.link', {'project': 'projects/fresh', 'assay': ASSAY,
                                                   'source': str(decl)}),
                stage00('finalize', '--project', 'projects/ready', '--data-class', 'public',
                        '--purpose', 'fixture'),
                dispatch('stage00_register.finalize', {'project': 'projects/ready',
                                                       'data-class': 'public',
                                                       'purpose': 'fixture'})]

    def test_declared_registration(self):
        print('red-on-fault: declared registration', flush=True)
        root = ROOTS['R1']
        for command in self.declared_allowed(root):
            with self.subTest(command=command):
                self.allowed(self.bash(root, command))
        decl, undecl = root / 'decl', root / 'undecl'
        refused = [
            stage00('inspect', '--assay', ASSAY, '--source', undecl),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source', undecl),
            stage00('inspect', '--assay', ASSAY, '--source', decl / 'links/to-undecl'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    decl / 'links/to-undecl'),
            stage00('inspect', '--assay', ASSAY, '--source', decl / 'links/to-pilot'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    decl / 'links/to-pilot'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    decl / 'outward'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    decl / 'withdangling'),
            stage00('finalize', '--project', 'projects/dangling', '--data-class', 'public',
                    '--purpose', 'fixture'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source', decl,
                    '--force'),
            stage00('finalize', '--project', 'projects/ready', '--data-class',
                    'deidentified_under_agreement', '--purpose', 'fixture'),
            stage00('finalize', '--project', 'projects/ready', '--data-class', 'Public',
                    '--purpose', 'fixture'),
            stage00('finalize', '--project', 'projects/fresh', '--data-class', 'public',
                    '--purpose', 'fixture'),
            stage00('finalize', '--project', 'projects/undeclraw', '--data-class', 'public',
                    '--purpose', 'fixture'),
            stage00('finalize', '--project', 'projects/legacy', '--data-class', 'public',
                    '--purpose', 'fixture'),
            stage00('link', '--project', 'projects/legacy', '--assay', ASSAY, '--source', decl),
            stage00('finalize', '--project', 'projects/stamped', '--data-class', 'public',
                    '--purpose', 'fixture'),
            stage00('link', '--project', 'projects/stamped', '--assay', ASSAY, '--source', decl),
            stage00('inspect', '--assay', ASSAY, '--source', 'projects/pilot/00_data/rnaseq_bulk'),
            stage00('inspect', '--assay', ASSAY, '--source', 'projects/pilot/lnk-decl'),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    'projects/pilot/lnk-decl'),
            stage00('finalize', '--project', 'projects/ready', '--data-class', 'public',
                    '--purpose', 'fixture', '--model', 'projects/pilot/00_data/rnaseq_bulk'),
            stage00('link', '--project', 'projects/fres*', '--assay', ASSAY, '--source', decl),
            stage00('link', '--project', 'projects/fresh', '--assay', ASSAY, '--source',
                    str(decl) + '*'),
            stage00('inspect', '--assay', ASSAY, '--source', '~/decl'),
            dispatch('stage00_register.finalize', {'project': 'projects/ready',
                                                   'data-class': 'publi[c]',
                                                   'purpose': 'fixture'}),
            stage00('link', '--project', 'projects/open1', '--assay', ASSAY, '--source', decl),
        ]
        schema = ('--data-class Public', 'publi[c]')   # refused by the registry's enum first
        for command in refused:
            with self.subTest(command=command):
                rule = 'R-092' if any(s in command for s in schema) else '0107'
                self.refused(self.bash(root, command), rule, root)

    def test_invalid_declarations(self):
        print('red-on-fault: invalid declarations', flush=True)
        root = ROOTS['R1']
        path = root / 'data_sources.tsv'
        good = path.read_text()
        decl, ok = str(root / 'decl'), (str(root / 'decl'), 'public', 'lane fixture')
        valid_elsewhere = Path(TMP) / 'valid_declaration.tsv'
        valid_elsewhere.write_text(good)
        variants = {
            'symlinked file': None,
            'CRLF': good.replace('\n', '\r\n'),
            'CRLF row': good.split('\n')[0] + '\n' + good.split('\n')[1] + '\r\n',
            'wrong header': good.replace('declared_by', 'owner', 1),
            'duplicate source': declaration(root, ok, ok),
            'nested sources': declaration(root, ok, (decl + '/sub', 'public', 'x')),
            'relative source': declaration(root, ok, ('undecl', 'public', 'x')),
            'equal to the workspace root': declaration(root, ok, (str(root), 'public', 'x')),
            'contains the workspace root': declaration(root, ok, (str(root.parent), 'public', 'x')),
            'equal to projects/': declaration(root, ok, (str(root / 'projects'), 'public', 'x')),
            'a project': declaration(root, ok, (str(root / 'projects/open1'), 'public', 'x')),
            'inside a project': declaration(root, ok, (str(root / 'projects/open1/_config'),
                                                       'public', 'x')),
            '_system/': declaration(root, ok, (str(root / '_system'), 'public', 'x')),
            '_references/': declaration(root, ok, (str(root / '_references'), 'public', 'x')),
            '.gars-approvals/': declaration(root, ok, (str(root.parent / '.gars-approvals'),
                                                       'public', 'x')),
            'missing directory': declaration(root, ok, (str(root / 'absent'), 'public', 'x')),
            'non-public class': declaration(root, ok, (str(root / 'undecl'),
                                                       'deidentified_under_agreement', 'x')),
            'Public class': declaration(root, ok, (str(root / 'undecl'), 'Public', 'x')),
            'shell-glob source': declaration(root, ok, (str(root / 'undec?'), 'public', 'x')),
            'tilde source': declaration(root, ok, ('~/undecl', 'public', 'x')),
            'empty declared_by': declaration(root, ok, (str(root / 'undecl'), 'public', ' ')),
        }
        try:
            for name, text in variants.items():
                path.unlink()
                if text is None:
                    path.symlink_to(valid_elsewhere)
                else:
                    path.write_text(text)
                for command in self.declared_allowed(root):
                    with self.subTest(variant=name, command=command):
                        self.refused(self.bash(root, command), '0107', root)
                with self.subTest(variant=name, check='declared_sources'):
                    self.assertEqual(guard_hook.declared_sources(str(root))[0], ())
        finally:
            path.unlink()
            path.write_text(good)
        self.assertEqual(guard_hook.declared_sources(str(root)), ((decl,), None))

    def test_declaration_protected(self):
        print('red-on-fault: declaration protection', flush=True)
        root = ROOTS['R1']
        for tool in ('Write', 'Edit'):
            for target in ('data_sources.tsv', str(root / 'data_sources.tsv')):
                with self.subTest(tool=tool, target=target):
                    err = self.refused(call(root, tool, {'file_path': target}), root=root)
                    self.assertIn('only a human writes it', err)


class DoorTests(HookCase):
    def test_door_mechanism(self):
        print('red-on-fault: doors', flush=True)
        self.assertEqual(guard_hook.CLOSED_PROJECT_DOORS, ())
        root = ROOTS['R0']
        dummy = {'name': 'dummy.door', 'argv': ['python3', '_system/dummy_door.py'],
                 'roles': {'producer': 'allow'}, 'timeout_seconds': 5,
                 'input_schema': {'type': 'object', 'additionalProperties': False,
                                  'required': ['project'],
                                  'properties': {'project': {'type': 'string', 'minLength': 1}}},
                 'output_schema': {'type': 'object'},
                 'cli': {'project': {'flag': '--project', 'nargs': None}}}
        hook = door_hook('door', ['dummy.door'], dummy)
        self.allowed(call(root, 'Bash', {'command': dispatch('dummy.door', {'project': P})},
                          hook=hook))
        for command in (dispatch('fs.read', {'paths': [SAMPLES]}),
                        dispatch('configure.contrasts', {'project': P, 'assay': ASSAY}),
                        dispatch('stage01_samplesheet', {'project': P})):
            with self.subTest(command=command):
                self.refused(call(root, 'Bash', {'command': command}, hook=hook), root=root)


class Q8Tests(HookCase):
    def test_agent_never_supplies_public(self):
        print('red-on-fault: Q8', flush=True)
        root = ROOTS['R0']
        fresh = ['--project', 'projects/fresh', '--purpose', 'fixture']
        cases = [
            (stage00('finalize', *(fresh + ['--data-class', 'public'])), '', 'block'),
            (stage00('finalize', *(fresh + ['--data-class=public'])), '', 'block'),
            (dispatch('stage00_register.finalize', {'project': 'projects/fresh',
                                                    'data-class': 'public',
                                                    'purpose': 'fixture'}), '', 'block'),
            (stage00('finalize', *(fresh + ['--data-class', 'Public'])), '', 'base'),
            (stage00('finalize', *(fresh + ['--data-class', 'public '])), '', 'base'),
            ('python3 ../../_system/stage00_register.py finalize --project ../fresh '
             '--data-class public --purpose fixture', 'projects/open1', 'block'),
            ('python3 ../../../_system/stage00_register.py finalize --project projects/pilot '
             '--data-class public --purpose fixture', 'projects/open1/nest', 'block'),
            (stage00('finalize', '--project', 'projects/open1', '--data-class', 'public',
                     '--purpose', 'fixture'), '', 'allow'),
        ]
        for command, cwd, expect in cases:
            with self.subTest(command=command, cwd=cwd):
                self.expect(call(root, 'Bash', {'command': command}, cwd), expect, root)

    def test_q8_alone(self):
        """With finalize a door, only Q8 stands between the agent and class public."""
        print('red-on-fault: Q8 alone', flush=True)
        root = ROOTS['R0']
        hook = door_hook('door-finalize', ['stage00_register.finalize'])
        err = self.refused(call(root, 'Bash', {'command': stage00(
            'finalize', '--project', 'projects/fresh', '--data-class', 'public', '--purpose',
            'fixture')}, hook=hook), root=root)
        self.assertIn('§21 Q4', err)
        self.assertIn("classifying data is the owner's", err)
        self.assertIn('data_sources.tsv', err)
        self.allowed(call(root, 'Bash', {'command': stage00(
            'finalize', '--project', 'projects/fresh', '--data-class',
            'deidentified_under_agreement', '--purpose', 'fixture')}, hook=hook))


class ControlAndDriftTests(HookCase):
    def test_positive_control_moved(self):
        print('red-on-fault: positive control (M1)', flush=True)
        closed, open_root = ROOTS['R0'], build_root('all-public', only_public=True)
        for tool, data in (('Grep', {'pattern': 'S1'}), ('Glob', {'pattern': '**/*.csv'}),
                           ('Grep', {'path': '.', 'pattern': 'S1'})):
            with self.subTest(tool=tool, data=data):
                self.refused(call(closed, tool, data), root=closed)
                self.allowed(call(open_root, tool, data))

    def test_class_flip_bound_to_row_6(self):
        print('red-on-fault: class flip', flush=True)
        root = ROOTS['R0']
        for tool in ('Write', 'Edit'):
            err = self.refused(call(root, tool, {'file_path': DATASET}), 'R-092', root)
            self.assertIn('part of the GARS template', err)
        err = self.refused(call(root, 'Bash', {'command': 'tee ' + DATASET}), 'R-092', root)
        self.assertIn('unregistered helper', err)

    def test_edit_family_refused_in_closed_project(self):
        # Review round 1, F3: an edit echoes the file around it, so residual 10 is closed here.
        print('red-on-fault: edit family', flush=True)
        root = ROOTS['R0']
        cases = [
            ('Edit', {'file_path': P + '/HISTORY.md', 'old_string': 'a', 'new_string': 'b'}, ''),
            ('Edit', {'file_path': str(Path(root) / P / 'HISTORY.md'), 'old_string': 'a',
                      'new_string': 'b'}, ''),
            ('Edit', {'file_path': '../pilot/HISTORY.md', 'old_string': 'a',
                      'new_string': 'b'}, 'projects/open1'),
            ('Edit', {'file_path': 'projects/open1/lnk-pilot/rnaseq_bulk/samples.csv',
                      'old_string': 'a', 'new_string': 'b'}, ''),
            ('Edit', {'file_path': P + '/_config/rnaseq_bulk.yaml', 'old_string': 'a',
                      'new_string': 'b'}, ''),
            ('MultiEdit', {'file_path': P + '/HISTORY.md',
                           'edits': [{'old_string': 'a', 'new_string': 'b'}]}, ''),
            ('NotebookEdit', {'notebook_path': P + '/x.ipynb', 'new_source': 'b'}, ''),
            ('Edit', {'file_path': 'projects/fresh/HISTORY.md', 'old_string': 'a',
                      'new_string': 'b'}, ''),
        ]
        for tool, data, cwd in cases:
            with self.subTest(tool=tool, data=data, cwd=cwd):
                err = self.refused(call(root, tool, data, cwd), root=root)
                self.assertIn('is in project', err)
        self.allowed(call(root, 'Edit', {'file_path': 'projects/open1/HISTORY.md',
                                         'old_string': 'a', 'new_string': 'b'}))

    def test_contract_drift(self):
        print('red-on-fault: contract drift', flush=True)
        root = ROOTS['R1']
        steps = [['create', '--title', 'drift', '--assays', ASSAY],
                 ['link', '--project', 'projects/drift', '--assay', ASSAY, '--source',
                  str(root / 'decl')],
                 ['finalize', '--project', 'projects/drift', '--data-class', 'public',
                  '--purpose', 'fixture']]
        for step in steps:
            self.allowed(call(root, 'Bash', {'command': stage00(*step)}))
            register(root, *step)
        project = root / 'projects/drift'
        self.assertTrue(guard_hook.project_is_public(str(project)))
        self.allowed(call(root, 'Read', {'file_path': 'projects/drift/00_data/rnaseq_bulk/samples.csv'}))
        import stage00_register as reg
        header = (project / '00_data/dataset.tsv').read_text().split('\n')[0].split('\t')
        self.assertEqual(header, reg.DATASET_BASE_FIELDS + reg.DATASET_ROUTE_FIELDS)
        for data_class, flags in (('deidentified_under_agreement', ['--expiry', '2027-12-31']),):
            title = 'drift-' + data_class.split('_')[0]
            register(root, 'create', '--title', title, '--assays', ASSAY)
            register(root, 'link', '--project', 'projects/' + title, '--assay', ASSAY,
                     '--source', str(root.parent / 'seqrun'))
            register(root, 'finalize', '--project', 'projects/' + title, '--data-class',
                     data_class, '--purpose', 'fixture', *flags)
            self.assertFalse(guard_hook.project_is_public(str(root / 'projects' / title)))
            self.refused(call(root, 'Read', {'file_path': 'projects/%s/CONTEXT.md' % title}),
                         root=root)
        four = Path(TMP) / 'four-column'
        (four / '00_data').mkdir(parents=True)
        (four / '00_data/dataset.tsv').write_text(
            'data_class\tpurpose\tagreement_ref\tinput_data_location\npublic\tfixture\tnone\t[]\n')
        self.assertTrue(guard_hook.project_is_public(str(four)))

    def test_create_stamp(self):
        print('red-on-fault: create stamp drift', flush=True)
        ws = Path(TMP) / 'stamp/gars'
        (ws / 'projects').mkdir(parents=True)
        for d in ('_references', '_templates'):
            shutil.copytree(str(GARS / d), str(ws / d))
        assays = json.loads(register(ws, 'assays').stdout)['assays']
        ids = [a['assay_id'] for a in assays]
        register(ws, 'create', '--title', 'Stamp Title (x)', '--assays', *ids)
        project = ws / 'projects/Stamp_Title_x'
        actual = {str(p.relative_to(project)).replace(os.sep, '/') for p in project.rglob('*')}
        expected = set()
        for entry in guard_hook.CREATE_STAMP:
            expected.update([entry.replace('{assay}', a) for a in ids] if '{assay}' in entry
                            else [entry])
        self.assertEqual(actual, expected)
        self.assertTrue(guard_hook.registrable(str(project)))

    def test_cold_start_twin(self):
        print('red-on-fault: cold start', flush=True)
        ws = Path(TMP) / 'cold/gars'
        (ws / 'projects').mkdir(parents=True)
        for d in ('_references', '_templates'):
            shutil.copytree(str(GARS / d), str(ws / d))
        fastqs(ws.parent / 'seqrun', ['C1_S1'])
        register(ws, 'create', '--title', 'cold', '--assays', ASSAY)
        read = ('Read', {'file_path': 'projects/cold/CONTEXT.md'})
        self.refused(call(ws, *read), root=ws)
        register(ws, 'link', '--project', 'projects/cold', '--assay', ASSAY, '--source',
                 str(ws.parent / 'seqrun'))
        register(ws, 'finalize', '--project', 'projects/cold', '--data-class', 'public',
                 '--purpose', 'fixture')
        self.allowed(call(ws, *read))


if __name__ == '__main__':
    unittest.main(verbosity=2)
