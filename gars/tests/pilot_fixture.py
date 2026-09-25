"""Fixture workspaces for row 13 step B's tests (decision 0141); not a test module.

A workspace holds a copy of `_system/`, `_references/` and `_templates/` (so the real dispatcher
runs against it), a public project `open1` and a closed project `pilot` registered with the real
stage 00 helper (0107's fixture shape), a fresh project from `create`, an external folder and a
folder a human declared public, both outside the workspace. Sample-name markers are planted in
the closed project's design, its counts header, its DE table and its OUTPUTS index, and in the
external folder; a lowercase CODE-shaped marker in the design, the counts header and the OUTPUTS
type and role.
"""
import gzip
import hashlib
import json
import shlex
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, run  # noqa: E402

ASSAY = 'rnaseq_bulk'
DESIGN_MARKER = 'MARKER0141designS9'
COUNTS_MARKER = 'MARKER0141countsS8'
GENE_MARKER = 'MARKER0141geneX7'
EXTERNAL_MARKER = 'MARKER0141externalS6'
# A valid CODE (closed_output.CODE, lowercase snake_case), so a field judged by that rule alone
# would let it through (review round 1 F-4): planted as a design column, a counts column and an
# OUTPUTS type and role.
CODE_MARKER = 'zzmarker0141_code'
MARKERS = (DESIGN_MARKER, COUNTS_MARKER, GENE_MARKER, EXTERNAL_MARKER, CODE_MARKER)
COUNTS_STAGE = '02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper'
DE_STAGE = '02_bioinformatics/rnaseq_bulk/02_rnaseq-de'
COUNTS = COUNTS_STAGE + '/run/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv'
DESIGN = '01_samplesheets/rnaseq_bulk_design.csv'
LOG = 'pilot/pilot1_log.csv'
DOORS = ('resolve_artifact', 'rnaseq_de.check', 'rnaseq_de.prepare', 'rnaseq_de.collect',
         'rnaseq_de.summary', 'executor.submit', 'executor.status', 'pilot_log.begin',
         'pilot_log.end', 'pilot_log.abort', 'pilot_log.check')
CONFIG = """strandedness: auto
aligner: star_salmon
compute:
  partition: cpu_short
  time: "01:00:00"
  cpus: 1
  mem: 1G
  work_dir: /scratch/fixture
de:
  formula:  "~ condition"
  contrast: "condition,B,A"
"""


def fastqs(folder, names):
    folder.mkdir(parents=True, exist_ok=True)
    for name in names:
        for read in ('R1', 'R2'):
            with gzip.open(str(folder / ('%s_L001_%s_001.fastq.gz' % (name, read))), 'wt') as fh:
                fh.write('@r0\nACGT\n+\nIIII\n')


def register(ws, *args):
    result = run([sys.executable, ws / '_system/stage00_register.py', '--workspace', ws] +
                 [str(a) for a in args], cwd=ws)
    if result.returncode:
        raise AssertionError('stage00 %s: %s %s' % (args, result.stdout, result.stderr))
    return result


def plant(project):
    """What a project at stage 02 holds: a design, a counts matrix whose header lacks one design
    sample, a completed DE run, a prepared DE manifest bound to the config, and STATUS files."""
    samples = project / '00_data' / ASSAY / 'samples.csv'
    samples.chmod(0o644)
    samples.write_text('sample_id,condition\n%s,A\nS2,A\nS3,B\nS4,B\n' % DESIGN_MARKER)
    (project / '01_samplesheets').mkdir(exist_ok=True)
    (project / DESIGN).write_text('sample_id,condition,%s\n%s,A,x\nS2,A,x\nS3,B,y\nS4,B,y\n'
                                  % (CODE_MARKER, DESIGN_MARKER))
    (project / '_config' / (ASSAY + '.yaml')).write_text(CONFIG)
    counts = project / COUNTS
    counts.parent.mkdir(parents=True)
    counts.write_text('gene_id\tgene_name\t%s\tS2\tS3\tS4\t%s\nG1\tg1\t1\t2\t3\t4\t5\n'
                      % (COUNTS_MARKER, CODE_MARKER))
    stage = project / COUNTS_STAGE
    (stage / 'OUTPUTS.tsv').write_text(
        '# type\trole\tpath\ncounts_gene\tnative\t%s\ntable\tnative\trun/%s.tsv\n'
        '%s\tnative\trun/results/code.tsv\ntable\t%s\trun/results/role.tsv\n'
        % (COUNTS[len(COUNTS_STAGE) + 1:], GENE_MARKER, CODE_MARKER, CODE_MARKER))
    (stage / 'STATUS').write_text('COMPLETE\n')
    de = project / DE_STAGE
    (de / 'run/tables').mkdir(parents=True)
    (de / 'run/tables/de_results.csv').write_text(
        'gene,baseMean,log2FoldChange,pvalue,padj\n'
        '%s,10,2.5,0.001,0.004\nG2,10,-1.5,0.01,0.02\nG3,10,0.5,0.03,0.04\n'
        'G4,10,0.1,0.5,0.5\nG5,10,NA,NA,NA\n' % GENE_MARKER)
    (de / 'STATUS').write_text('COMPLETE\n')
    (de / 'reproducibility').mkdir()
    config_sha = hashlib.sha256((project / '_config' / (ASSAY + '.yaml')).read_bytes()).hexdigest()
    (de / 'reproducibility/manifest.json').write_text(json.dumps({'config_sha256': config_sha}))


def build(top, closed=True, declare=True):
    """A fixture workspace under `top`; returns its root (`top/gars`)."""
    top = Path(top)
    ws = top / 'gars'
    ws.mkdir(parents=True)
    ignore = shutil.ignore_patterns('__pycache__')
    for folder in ('_system', '_references', '_templates'):
        shutil.copytree(str(GARS / folder), str(ws / folder), ignore=ignore)
    for folder in ('.claude', 'projects'):
        (ws / folder).mkdir()
    (top / '.gars-approvals').mkdir()
    fastqs(top / 'pubseq', ['P1_S1', 'P2_S2'])
    fastqs(top / 'seqrun', ['S2_S2', 'S3_S3'])
    fastqs(top / 'external', [EXTERNAL_MARKER + '_S5'])
    (top / 'external' / 'notes.txt').write_text(EXTERNAL_MARKER + '\n')
    fastqs(top / 'declared', ['D1_S1', 'D2_S2'])
    projects = ws / 'projects'
    register(ws, 'create', '--title', 'open1', '--assays', ASSAY)
    register(ws, 'link', '--project', 'projects/open1', '--assay', ASSAY,
             '--source', top / 'pubseq')
    register(ws, 'finalize', '--project', 'projects/open1', '--data-class', 'public',
             '--purpose', 'fixture')
    plant(projects / 'open1')
    if closed:
        register(ws, 'create', '--title', 'pilot', '--assays', ASSAY)
        register(ws, 'link', '--project', 'projects/pilot', '--assay', ASSAY,
                 '--source', top / 'seqrun')
        register(ws, 'finalize', '--project', 'projects/pilot', '--data-class',
                 'deidentified_under_agreement', '--purpose', 'fixture', '--expiry',
                 '2099-12-31')
        plant(projects / 'pilot')
        register(ws, 'create', '--title', 'fresh', '--assays', ASSAY)
    if declare:
        (ws / 'data_sources.tsv').write_text(
            'source\tdata_class\tdeclared_by\n%s\tpublic\tlane fixture\n' % (top / 'declared'))
    return ws


def hook_call(root, tool, data, cwd='', hook=None):
    here = Path(root) / cwd if cwd else Path(root)
    return run([sys.executable, hook or GARS / '_system/guard_hook.py'], root,
               json.dumps({'tool_name': tool, 'tool_input': data, 'cwd': str(here)}),
               {'CLAUDE_PROJECT_DIR': str(root)})


def dispatch(name, args, cwd=''):
    up = '../' * len([p for p in cwd.split('/') if p]) if cwd else ''
    return 'python3 %s_system/tool_call.py %s %s' % (up, name, shlex.quote(json.dumps(args)))


def bare(tool, args):
    """The direct spelling of a registered helper, as a human would type it."""
    if tool.get('filesystem'):
        words = [tool['argv'][0]] + args.get('flags', [])
        if 'pattern' in args:
            words.append(args['pattern'])
        return ' '.join(shlex.quote(w) for w in words + args['paths'])
    words = ['python3', tool['argv'][1]] + [a for a in tool['argv'][2:]
                                           if a != '--launched-by-dispatcher']
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


def tool_call(ws, name, args, cwd=None):
    """The real dispatcher of the fixture workspace; (exit code, parsed JSON, raw stdout)."""
    result = run([sys.executable, ws / '_system/tool_call.py', name, json.dumps(args)],
                 cwd=cwd or ws)
    text = result.stdout.decode('utf-8', 'replace')
    return result.returncode, json.loads(text), text + result.stderr.decode('utf-8', 'replace')


def door_args(name, project='projects/pilot'):
    """Valid arguments for each door on `project` (the dispatcher runs at the workspace root)."""
    return {
        'resolve_artifact': {'project': project, 'assay': ASSAY,
                             'consumes': ['counts_gene', 'design']},
        'rnaseq_de.check': {'project': project, 'counts': project + '/' + COUNTS,
                            'design': project + '/' + DESIGN},
        'rnaseq_de.prepare': {'project': project, 'counts': project + '/' + COUNTS,
                              'design': project + '/' + DESIGN},
        'rnaseq_de.collect': {'project': project, 'model': 'claude-opus-5-5',
                              'counts-from': '01_nfcore-rnaseq-wrapper'},
        'rnaseq_de.summary': {'project': project},
        'executor.submit': {'workspace': project, 'script': project + '/' + DE_STAGE +
                            '/submit.sh'},
        'executor.status': {'workspace': project, 'job-id': '100'},
        'pilot_log.begin': {'log': project + '/' + LOG, 'stage': '02_02_de',
                            'action': 'check', 'reason': 'other'},
        'pilot_log.end': {'log': project + '/' + LOG, 'span': '0123456789abcdef'},
        'pilot_log.abort': {'log': project + '/' + LOG, 'span': '0123456789abcdef'},
        'pilot_log.check': {'log': project + '/' + LOG},
    }[name]


def place_args(tool, project):
    """Minimal valid arguments naming `project` wherever the tool takes a project or path."""
    if tool['name'] in DOORS:
        return door_args(tool['name'], project)
    schema = tool['input_schema']
    props = schema.get('properties', {})
    keys = list(schema.get('required', []))
    for optional in ('project', 'pattern'):
        if optional in props and optional not in keys:
            keys.append(optional)
    values = {'project': project, 'workspace': project, 'paths': [project + '/' + DESIGN],
              'source': project + '/00_data/rnaseq_bulk/raw', 'counts': project + '/' + COUNTS,
              'design': project + '/' + DESIGN, 'script': project + '/s.sh', 'pattern': 'S',
              'h5ad': project + '/x.h5ad', 'assay': ASSAY, 'assays': [ASSAY], 'title': 'T',
              'slug': '01_x', 'analysis': '01_x', 'job-id': '42', 'genome': 'GRCh38'}
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
    return any(k in props for k in ('project', 'workspace', 'paths', 'source', 'log'))
