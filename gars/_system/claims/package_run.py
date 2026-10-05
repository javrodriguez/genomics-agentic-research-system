#!/usr/bin/env python3
"""Build a GARS reproduction package from a run's own records (decisions 0281, 0283).

  harvest     on the machine that ran the analysis, before teardown:
              python3 package_run.py harvest --gars <GARS clone> --project <project folder>
                  --lane-commit <commit of this file's checkout> --out <private harvest folder>
              Re-checks every recorded hash against the bytes on disk with GARS's own checks,
              copies the records, the stage trees (output members up to 5 MB) and the inputs'
              checksums into a private folder. The harvest is never published.
  render      anywhere, pure: no network, no model, byte-identical on re-run:
              python3 package_run.py render --harvest <dir> --gars-repo <GARS git clone>
                  --sources <lane-sources.tsv> --tolerances <package-tolerances.json> --out <package>
              Reads only the harvest, named files at the recorded GARS commit (git show) and the
              two lane files; every value carries one of three labels.
  rerun-note  writes the landing README beside a package, from a verifying pass's artifact:
              python3 package_run.py rerun-note --package <dir> --artifact <dir> [--artifact <dir>]
                  --workflow <workflow file name> --out <README.md>

Every refusal exits 1 with the reason on stderr and writes nothing; 2 is a usage error.
Standard library only, Python 3.6 or later.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
TEMPLATES = HERE / 'package'
STATIC = ('verify.py', 'compare.py', 'rerun.sh')
HARVEST_FORMAT = 'gars-harvest/1'

RUN = 'recorded at run'
HARVEST = 'computed at harvest'
PACKAGING = 'supplied at packaging from '
LABELS = (RUN, HARVEST, PACKAGING.strip())
NOT_RECORDED = 'not recorded'

SMALL_LIMIT = 5 * 1024 * 1024
TABLE_SUFFIXES = ('.tsv', '.txt', '.csv', '.bed', '.narrowPeak', '.broadPeak', '.gappedPeak', '.saf')
RESULTS_PREFIX = 'run/results/'
STAGE_COPY = ('submit.sh', 'params.yaml', 'OUTPUTS.tsv')
STAGE_TREES = ('reproducibility', 'scripts', 'run/pipeline_info', 'run/results/pipeline_info')
PROJECT_COPY = ('_config', '01_samplesheets', '00_data/dataset.tsv', 'HISTORY.md')
REFERENCE_PARAMS = {'fasta': 'fasta_sha256', 'gtf': 'gtf_sha256'}
PUBLIC_REGISTRIES = ('quay.io', 'docker.io', 'registry-1.docker.io', 'ghcr.io', 'public.ecr.aws',
                     'community.wave.seqera.io', 'depot.galaxyproject.org')
ORIGINS = ('S2b-preregistered', 'pass-1')
COMPARISON_MODES = ('exact', 'presence')
PROCESS_NAME = re.compile(r'[A-Za-z0-9_:]+\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
STORAGE_URI = re.compile(r'(?i)(?<![A-Za-z0-9+.-])(s3[an]?|gs|gcs|az|abfss?|wasbs?)://([^/\s\'"<>]+)')
ARN_ACCOUNT = re.compile(r'arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:([0-9]{12}):')
BOUNDED_12 = re.compile(r'(?<![0-9A-Fa-f])[0-9]{12}(?![0-9A-Fa-f])')
UNMASKED_URI = re.compile(r'(?i)(?<![A-Za-z0-9+.-])(?:s3[an]?|gs|gcs|az|abfss?|wasbs?)://(?!<BUCKET>)')
PLACEHOLDERS = ('<WORKSPACE>', '<HOME>', '<SCRATCH>')
# A home folder in any file. The one exception is conda's own build prefix, which GARS's public pip
# lock names in a comment (gars/_references/gars-bio.lock.txt: `file:///home/conda/...`).
HOME_PATH = re.compile(r'/Users/|/home/(?!conda/)')
INPUTS_TOKEN = '<INPUTS>/'
# An absolute path left in a masked file: anything but the system folders a script names.
SURVIVOR = re.compile(r'(?<![A-Za-z0-9_.<>:/$-])/(?!bin/|usr/|dev/|etc/|opt/nf-tools/)[A-Za-z0-9_.-]+/')
RERUN_TOKEN = '<RERUN>'


class Refusal(Exception):
    """Something the package will not state, ship or guess around."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def dump_json(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n'


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo, *args):
    # Status reads the bytes, never trusted stat data or a filesystem monitor (review h2 m7).
    proc = subprocess.run(['git', '--no-replace-objects', '-c', 'core.trustctime=true', '-c', 'core.checkStat=default',
                           '-c', 'core.fsmonitor=false', '-C', str(repo)] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise Refusal('git %s failed in %s' % (args[0], repo))
    return proc.stdout


def tsv(columns, rows):
    out = io.StringIO()
    out.write('\t'.join(columns) + '\n')
    for row in rows:
        cells = [str(row[c]) for c in columns]
        for c in cells:
            if '\t' in c or '\n' in c or '\r' in c:
                raise Refusal('a table cell holds a tab or a line break')
        out.write('\t'.join(cells) + '\n')
    return out.getvalue()


def read_tsv(path):
    with io.open(str(path), encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


def run_label(field):
    return '%s: manifest field %s' % (RUN, field)


def packaging_label(repo, commit, path):
    return '%s%s@%s:%s' % (PACKAGING, repo, commit, path)


# =================================================================================================
# harvest: on the run's machine, before teardown
# =================================================================================================

def gars_modules(gars):
    system = Path(gars) / 'gars' / '_system'
    for folder in (system, system / 'claims'):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    import wrapperlib
    import manifest_check
    import render_methods
    return wrapperlib, manifest_check, render_methods


def copy_file(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(source), str(target))


def copy_tree(source, target, links=None):
    """Regular files under `source`. With `links` (a list), a linked FILE is copied by its target's
    bytes and noted there, as a replay links _config/ and 01_samplesheets/ (0251); without it a link
    is refused, never skipped in silence (review h1 H2). A linked folder is always refused."""
    if source.is_symlink():
        raise Refusal('%s is a link; harvest copies real folders only' % source.name)
    if not source.is_dir():
        return
    for folder, dirs, files in os.walk(str(source), followlinks=False):
        for d in dirs:
            if os.path.islink(os.path.join(folder, d)):
                raise Refusal('%s holds a linked folder (%s)' % (source.name, d))
        dirs.sort()
        for name in sorted(files):
            path = Path(folder) / name
            rel = path.relative_to(source)
            if path.is_symlink():
                if links is None or not path.is_file():
                    raise Refusal('%s holds a link (%s) harvest will not follow' % (source.name, rel.as_posix()))
                links.append((source.name + '/' + rel.as_posix(), os.readlink(str(path))))
            if path.is_file():
                copy_file(path, target / rel)


def params_yaml_values(path):
    """params.yaml as wrapperlib.write_params_yaml writes it: comments, then `key: value` lines,
    a value holding a space written as JSON. Read back, never re-derived (planner-A M2)."""
    values = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition(': ')
        if not sep or key in values:
            raise Refusal('params.yaml line is not one key and one value: %r' % line[:60])
        values[key] = json.loads(value) if value.startswith('"') else value
    return values


def grade_complete(manifest_check, manifest, role):
    """Complete, with exactly one tested exception: group 4 (container digests) absent (G1)."""
    try:
        report = manifest_check.grade(manifest)
    except (ValueError, KeyError, TypeError) as exc:
        raise Refusal('%s cannot be graded: %s' % (role, exc))
    missing = [g['number'] for g in report['groups']
               if g['applicable'] and not g['present'] and g['class'] != 'optional']
    if [n for n in missing if n != 4]:
        raise Refusal('%s grades incomplete: required groups %s absent' % (role, missing))
    return 4 in missing


def checkout_unpatched(manifest, role):
    checkout = manifest.get('checkout')
    if not isinstance(checkout, str) or not checkout:
        raise Refusal('%s records no pipeline checkout' % role)
    head = git(checkout, 'rev-parse', 'HEAD').decode('ascii').strip()
    if head != manifest.get('pipeline_commit'):
        raise Refusal('%s: the pipeline checkout is not at the recorded commit' % role)
    if git(checkout, 'status', '--porcelain', '--untracked-files=all', '--ignored').strip() or hidden_edits(checkout):
        raise Refusal('%s: the pipeline checkout was patched at run; -r <commit> would not be the '
                      'code that ran' % role)


# Ignored paths a GARS clone holds by design while a run is harvested: the projects, the human-written
# data_sources.tsv, the human-owned approval store, and the bytecode Python writes when GARS's own
# modules are imported. Anything else ignored is a file git status would not show (review h3-6).
CLONE_IGNORED_OK = ('gars/projects/', 'gars/data_sources.tsv', '.gars-approvals/')


def clean_clone(repo):
    """The clone is HEAD, read by content: no change, untracked or unexpected ignored file in git status;
    no hidden-edit flag; and a fresh index built from HEAD, refreshed by hashing every file, reports no
    difference, so no stat setting or cached index entry can hide an edit (review h3-6)."""
    porcelain = git(repo, 'status', '--porcelain', '--untracked-files=all', '--ignored').decode('utf-8')
    for line in porcelain.splitlines():
        code, path = line[:2], line[3:].strip('"')
        if code == '!!' and (path.startswith(CLONE_IGNORED_OK) or '__pycache__/' in '/' + path):
            continue
        raise Refusal('the GARS clone is not clean (git status: %s %s)' % (code, path))
    if hidden_edits(repo):
        raise Refusal('the GARS clone is not clean (a file is flagged skip-worktree or assume-unchanged)')
    handle, index = tempfile.mkstemp(prefix='.harvest-index-')
    os.close(handle)
    os.unlink(index)
    env = dict(os.environ, GIT_INDEX_FILE=index)
    base = ['git', '--no-replace-objects', '-c', 'core.trustctime=true', '-c', 'core.checkStat=default',
            '-c', 'core.fsmonitor=false', '-C', str(repo)]
    try:
        for args in (['read-tree', 'HEAD'], ['update-index', '-q', '--refresh'], ['diff-files', '--quiet']):
            proc = subprocess.run(base + args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                raise Refusal('the GARS clone is not clean (its files differ from HEAD by content)')
    finally:
        if os.path.exists(index):
            os.unlink(index)


def hidden_edits(repo):
    """Files git status cannot see changed: skip-worktree (S) or assume-unchanged (a lowercase tag)."""
    for line in git(repo, 'ls-files', '-v').decode('utf-8', 'replace').splitlines():
        if line[:1] == 'S' or line[:1].islower():
            return True
    return False


KEY_LINE = re.compile(r'^# idempotency_key=([0-9a-f]+)$', re.M)
YAML_SCALAR = re.compile(r'(true|false|-?[0-9]+|-?[0-9]+\.[0-9]+)\Z')


def yaml_scalar(text):
    if text in ('true', 'false'):
        return text == 'true'
    return float(text) if '.' in text else int(text)


def check_commands(stage, manifest, role):
    """The run's command files are shipped as the code that ran, so each is bound first (review h1
    H1): commands.sh by its recorded sha256, submit.sh by the one input-key line prepare writes and
    the executor checks at submit (executorlib.prepared_key)."""
    command = manifest.get('command') or {}
    path = stage / 'reproducibility' / 'commands.sh'
    if not path.is_file() or sha256_file(path) != command.get('sha256'):
        raise Refusal('%s: reproducibility/commands.sh is not the file the run recorded (sha256 differs)' % role)
    submit = stage / 'submit.sh'
    if not submit.is_file() or submit.is_symlink():
        raise Refusal('%s: submit.sh is missing' % role)
    keys = KEY_LINE.findall(submit.read_text(encoding='utf-8'))
    if keys != [manifest.get('idempotency_key')]:
        raise Refusal('%s: submit.sh does not carry exactly the recorded input-key line' % role)


LAUNCH = re.compile(r'DEBUG nextflow\.cli\.Launcher - \$> (.+)$', re.M)


def submit_launch(text):
    """The `nextflow run` line prepare wrote into submit.sh, as tokens, without the resume slot."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('nextflow run '):
            joined = line
            while joined.endswith('\\') and i + 1 < len(lines):
                i += 1
                joined = joined[:-1] + ' ' + lines[i]
            return [t for t in shlex.split(joined) if t != '$RESUME']
    return None


def check_launch(stage, role):
    """No run record binds submit.sh's bytes, so what Nextflow itself logged as its launch line is
    compared with the line prepare wrote (review h3-5); a run resumed once logs `-resume` last."""
    log = stage / 'run' / '.nextflow.log'
    if not log.is_file():
        raise Refusal('%s: run/.nextflow.log is absent; the launch line cannot be checked' % role)
    match = LAUNCH.search(log.read_text(encoding='utf-8', errors='replace'))
    expected = submit_launch((stage / 'submit.sh').read_text(encoding='utf-8'))
    if not match or expected is None:
        raise Refusal('%s: no launch line in run/.nextflow.log or submit.sh' % role)
    launched = shlex.split(match.group(1))
    if launched[-1:] == ['-resume']:
        launched = launched[:-1]
    if launched != expected:
        raise Refusal('%s: Nextflow\'s logged launch line is not the one prepare wrote in submit.sh' % role)


def check_project_inputs(project, target, manifest, role):
    """The harvested copies render ships, re-hashed against the run's record (review h1 H2, H5): the
    samplesheet and the assay config by their recorded sha256, the executor config by its
    execution_config entry. The input key alone does not frame the samplesheet from the config."""
    inputs = manifest.get('inputs') or {}
    for label, folder in (('samplesheet', '01_samplesheets'), ('config', '_config')):
        if label not in inputs:
            continue
        copy = target / folder / Path(inputs[label]).name
        if not copy.is_file() or sha256_file(copy) != manifest.get(label + '_sha256'):
            raise Refusal('%s: the project\'s %s is not the one the run recorded (%s_sha256 differs)'
                          % (role, label, label))
    for entry in manifest.get('execution_config') or []:
        if entry.get('role') == 'nextflow_config':
            copy = target / '_config' / Path(entry['path']).name
            if not copy.is_file() or sha256_file(copy) != entry.get('sha256'):
                raise Refusal('%s: the project\'s executor config is not the one the run recorded' % role)


def check_status(wl, stage, manifest, role):
    """Only a run that completed is packaged (review h2 m5)."""
    facts = manifest.get('predicate_facts') or {}
    if facts.get('status') != 'COMPLETE' or manifest.get('failure_class') is not None:
        raise Refusal('%s: the run is recorded as %s, not COMPLETE' % (role, facts.get('status')))
    if (stage / 'STATUS').exists() and wl.read_status(stage) != 'COMPLETE':
        raise Refusal('%s: the stage STATUS is not COMPLETE' % role)


def check_evidence(wl, gars, project, stage, manifest, role):
    """The fields render prints are re-derived from the files with GARS's own collect functions, so
    every recorded hash among them is re-checked too (review h2 M3): the container per process from
    the trace, the software versions files and their sha256, the design check, the executor config
    and descriptor, and the reference files the run hashed."""
    kind = (manifest.get('predicate_facts') or {}).get('wrapper_kind')
    try:
        containers = wl.trace_evidence(stage)[0]
        versions = wl.software_evidence(stage, kind)
    except (OSError, ValueError, KeyError) as exc:
        raise Refusal('%s: the trace or versions files cannot be read (%s)' % (role, type(exc).__name__))
    if containers != manifest.get('containers'):
        raise Refusal('%s: the recorded containers are not the ones the trace names' % role)
    if versions != manifest.get('software_versions'):
        raise Refusal('%s: the recorded software versions are not the versions files on disk' % role)
    design = manifest.get('design_check')
    if isinstance(design, dict):
        path = project / str(design.get('path'))
        if not path.is_file() or sha256_file(path) != design.get('sha256'):
            raise Refusal('%s: the design check is not the file the run recorded' % role)
    for entry in manifest.get('execution_config') or []:
        path = Path(gars) / str(entry.get('path'))
        if not path.is_file() or sha256_file(path) != entry.get('sha256'):
            raise Refusal('%s: the %s is not the file the run recorded' % (role, entry.get('role')))
    observed = (manifest.get('reference') or {}).get('observed') or {}
    for param, field in (('fasta', 'fasta_sha256'), ('gtf', 'gtf_sha256')):
        value = (manifest.get('params') or {}).get(param)
        if field in observed and value:
            if not Path(value).is_file() or sha256_file(value) != observed[field]:
                raise Refusal('%s: the reference %s is not the file the run hashed' % (role, param))


def samplesheet_inputs(sheet, stage_id):
    """Every samplesheet cell naming an existing file: its name and its sha256, computed here."""
    rows = list(csv.reader(io.StringIO(sheet.read_text(encoding='utf-8'))))
    found = []
    for r, row in enumerate(rows[1:], 1):
        for c, value in enumerate(row):
            if c >= len(rows[0]):
                raise Refusal('samplesheet row %d is longer than its header' % r)
            if value.startswith('/') and (not Path(value).is_file() or Path(value).is_symlink() and
                                          not Path(value).resolve().is_file()):
                raise Refusal('samplesheet row %d names %s, which is not a regular file at harvest (h3-3)'
                              % (r, Path(value).name))
            if value.startswith('/'):
                found.append({'stage': stage_id, 'row': r, 'column': rows[0][c], 'file': Path(value).name,
                              'path': value, 'sha256': sha256_file(value), 'size': Path(value).stat().st_size})
    return found


def scan_secrets(texts):
    buckets, accounts = set(), set()
    for text in texts:
        for match in STORAGE_URI.finditer(text):
            buckets.add(match.group(2))
            accounts.update(re.findall(r'(?<![0-9])[0-9]{12}(?![0-9])', match.group(2)))
        accounts.update(ARN_ACCOUNT.findall(text))
    return sorted(buckets), sorted(accounts)


def user_named(text, user):
    """True when `text` names `user` as a word, not as a container image's repository (registry/name:tag),
    which is a public tool name such as nf-core/ubuntu:20.04."""
    for match in re.finditer(r'(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-])' % re.escape(user), text):
        before, after = text[match.start() - 1:match.start()], text[match.end():match.end() + 1]
        if before == '/' and after == ':':
            continue
        return True
    return False


def record_users(texts):
    """The user names the run's own records carry in home paths (h3-8): read from what was harvested,
    never from the account harvest itself runs as."""
    found = set()
    for text in texts:
        found.update(re.findall(r'/(?:home|Users)/([A-Za-z0-9_][A-Za-z0-9_.-]*)', text))
    found.discard('conda')
    return sorted(found)


def stage_id_of(rel):
    return rel.replace('/', '.').replace('02_bioinformatics.', '').replace('03_custom_analysis.', 'custom.')


def harvest(args):
    gars, project = Path(args.gars).resolve(), Path(args.project).resolve()
    out = Path(args.out)
    if not COMMIT.match(args.lane_commit or ''):
        raise Refusal('--lane-commit must be a full 40-hex commit')
    if out.exists() and any(out.iterdir()):
        raise Refusal('the harvest folder is not empty')
    gars_commit = git(gars, 'rev-parse', 'HEAD').decode('ascii').strip()
    clean_clone(gars)
    wl, manifest_check, render_methods = gars_modules(gars)   # imported only once the clone is vetted
    dataset = wl.dataset_record(project)
    if dataset.get('data_class') != 'public':   # every harvest, not only a stage 03 one (review h2 m4)
        raise Refusal('the project\'s dataset record names data_class %r, not public' % dataset.get('data_class'))
    stages, members, inputs, texts = [], [], [], []
    temp = Path(tempfile.mkdtemp(prefix='.harvest-', dir=str(out.parent if out.parent.is_dir() else '.')))
    try:
        target = temp / 'project'
        links = []
        for rel in PROJECT_COPY:
            source = project / rel
            if source.is_dir():
                copy_tree(source, target / rel, links)
            elif source.is_file():
                if source.is_symlink():
                    links.append((rel, os.readlink(str(source))))
                copy_file(source, target / rel)
        for manifest_path in sorted(project.glob('02_bioinformatics/*/*/reproducibility/manifest.json')):
            stage = manifest_path.parent.parent
            rel = stage.relative_to(project).as_posix()
            role = 'the manifest of ' + rel
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            if manifest.get('data_class') != 'public':
                raise Refusal('%s: data_class is %r, not public' % (role, manifest.get('data_class')))
            if manifest.get('gars_commit') != gars_commit:   # while the box can still be checked out (h2 m8)
                raise Refusal('%s: the run recorded GARS commit %s, but the clone is at %s'
                              % (role, str(manifest.get('gars_commit'))[:12], gars_commit[:12]))
            check_status(wl, stage, manifest, role)
            g4 = grade_complete(manifest_check, manifest, role)
            try:
                wl.verify_output_manifest(stage)
            except (OSError, ValueError, KeyError) as exc:
                raise Refusal('%s: %s' % (role, exc))
            try:
                key = wl.input_key(stage, manifest)
            except (OSError, ValueError, KeyError) as exc:
                raise Refusal('%s: the input key cannot be recomputed (%s)' % (role, type(exc).__name__))
            if key != manifest.get('idempotency_key'):
                raise Refusal('%s: the inputs or parameters changed since prepare (input key differs)' % role)
            if (stage / 'params.yaml').is_file() and params_yaml_values(stage / 'params.yaml') != manifest.get('params'):
                raise Refusal('%s: params.yaml does not hold the recorded params' % role)
            checkout_unpatched(manifest, role)
            check_commands(stage, manifest, role)
            check_launch(stage, role)
            check_project_inputs(project, target, manifest, role)
            check_evidence(wl, gars, project, stage, manifest, role)
            for name in STAGE_COPY:
                if (stage / name).is_file():
                    copy_file(stage / name, target / rel / name)
            for tree in STAGE_TREES:
                if tree == 'scripts' and os.path.lexists(str(stage / 'scripts')) and \
                        manifest.get('key_formula') != 'downstream-v2':
                    if (stage / 'scripts').is_dir() and not (stage / 'scripts').is_symlink() and \
                            not os.listdir(str(stage / 'scripts')):
                        continue
                    raise Refusal('%s: scripts/ is bound by no input key under %s; it cannot ship as the '
                                  'code that ran' % (role, manifest.get('key_formula')))
                copy_tree(stage / tree, target / rel / tree)
            for output in manifest.get('outputs') or []:
                top = os.path.normpath(str(stage / output['path']))
                for link in output.get('symlinks') or []:
                    link_target = str(link.get('target'))   # never `target`, the harvest folder (h3-2)
                    where = os.path.normpath(os.path.join(os.path.dirname(os.path.join(top, link['path'])),
                                                          link_target))
                    if os.path.isabs(link_target) or not where.startswith(top + os.sep):
                        raise Refusal('%s: output %s holds a link to a path outside it, which the record would '
                                      'publish' % (role, output['path']))
                listed = ([('.', output['sha256'])] if output.get('members') is None else
                          [(m['path'], m['sha256']) for m in output['members']])
                for member, digest in listed:
                    path = stage / output['path'] if member == '.' else stage / output['path'] / member
                    size = path.stat().st_size
                    copied = size <= SMALL_LIMIT or args.copy_large
                    if copied:
                        copy_file(path, target / rel / (output['path'] if member == '.' else
                                                        output['path'] + '/' + member))
                    members.append({'stage': rel, 'output_path': output['path'], 'member': member,
                                    'sha256': digest, 'size': size, 'copied': copied})
            sheet = (manifest.get('inputs') or {}).get('samplesheet')
            if sheet:
                inputs += samplesheet_inputs(Path(sheet), rel)
            stages.append({'kind': '02', 'rel': rel, 'group4_absent': g4})
        actors = set()
        for plan in sorted(project.glob('03_custom_analysis/*/PLAN.md')):
            stage, actor = harvest_analysis(plan, project, gars, target, render_methods)
            stages.append(stage)
            if isinstance(actor, str) and actor.strip():
                actors.add(actor)
        if not stages:
            raise Refusal('the project holds no stage 02 manifest and no stage 03 plan')
        for path in sorted(temp.rglob('*')):
            if path.is_file():
                texts.append(path.read_bytes().decode('utf-8', 'replace'))
        buckets, accounts = scan_secrets(texts)
        prefixes = []
        for spelled, placeholder in ((args.gars, '<WORKSPACE>'), (os.path.expanduser('~'), '<HOME>'),
                                     (tempfile.gettempdir(), '<SCRATCH>'), ('/tmp', '<SCRATCH>')):
            for form in sorted(set((os.path.abspath(spelled), str(Path(spelled).resolve())))):
                if form not in [p['prefix'] for p in prefixes]:
                    prefixes.append({'prefix': form, 'placeholder': placeholder})
        record = {
            'format': HARVEST_FORMAT, 'project': project.name, 'gars_commit': gars_commit,
            'gars_clean': True, 'package_run': {'commit': args.lane_commit,
                                                'sha256': sha256_file(Path(__file__).resolve())},
            'links': [{'path': p, 'target_masked_at_render': True} for p, _ in sorted(links)],
            'stages': stages, 'members': members, 'inputs': inputs, 'prefixes': prefixes,
            'secrets': {'buckets': buckets, 'accounts': accounts, 'actors': sorted(actors),
                        'users': record_users(texts)}}
        (temp / 'HARVEST.json').write_text(dump_json(record), encoding='utf-8')
        if out.exists():
            out.rmdir()
        os.replace(str(temp), str(out))
        temp = None
    finally:
        if temp is not None:
            shutil.rmtree(str(temp), ignore_errors=True)
    print('harvest: %d stages, %d output members (%d copied), %d input files -> %s'
          % (len(stages), len(members), sum(1 for m in members if m['copied']), len(inputs), out))
    return 0


def utc_epoch(text):
    import datetime
    stamp = datetime.datetime.strptime(str(text), '%Y-%m-%dT%H:%M:%SZ')
    return (stamp - datetime.datetime(1970, 1, 1)).total_seconds()


def harvest_analysis(plan, project, gars, target, render_methods):
    """Stage 03: the approved plan bound to its approval record, and every submitted script and
    launcher re-checked against the sha256 bound at submit (R-073, R-135), read-only, no poll."""
    import executorlib
    import stage03_analysis
    adir = plan.parent
    rel = adir.relative_to(project).as_posix()
    record_path = stage03_analysis.approval_record_path(plan, Path(gars) / 'gars')
    try:
        approval = json.loads(record_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        raise Refusal('%s: no readable approval record in the approval store' % rel)
    try:
        render_methods.check_approval(approval, plan.read_bytes())
    except render_methods.Refusal as exc:
        raise Refusal('%s: %s (R-073)' % (rel, exc))
    try:
        approved_at = utc_epoch(approval.get('timestamp'))
        expires_at = utc_epoch(approval.get('expiry'))
        entries = executorlib._analysis_entries(adir)
        if not entries:
            raise Refusal('%s: no submission record' % rel)
        scripts = []
        for entry in executorlib._analysis_latest(entries).values():
            if not entry.get('job_id') or entry.get('error'):
                raise Refusal('%s: the latest submission of %s has no job, or records an error'
                              % (rel, Path(str(entry.get('script'))).name))
            submitted = entry.get('submitted_at')
            # The approval must have been in force when the script ran, not only now (review h1 H3).
            if type(submitted) not in (int, float) or not approved_at <= submitted < expires_at:
                raise Refusal('%s: the approval record in the store was not in force when %s was submitted'
                              % (rel, Path(str(entry.get('script'))).name))
            for kind in ('script', 'launcher'):
                path = Path(entry[kind]).resolve()
                path.relative_to(adir.resolve())
                if executorlib._sha256(path) != entry[kind + '_sha256']:
                    raise Refusal('%s: %s sha256 changed since submit' % (rel, kind))
                scripts.append(path.relative_to(adir.resolve()).as_posix())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Refusal('%s: the submission record cannot be checked (%s)' % (rel, type(exc).__name__))
    if not (adir / 'run' / '.gars_run_complete').is_file():   # the launcher writes it on exit 0 only
        raise Refusal('%s: run/.gars_run_complete is absent; the analysis did not finish' % rel)
    # GARS's own reading of a stage 03 run (R-135): every script's latest job, its bytes and its
    # finished state. One message from it is a refusal (review h3-1).
    problem = executorlib.analysis_execution_evidence(project, adir)
    if problem:
        raise Refusal('%s: %s' % (rel, problem))
    for name in sorted(set(scripts)) + ['PLAN.md', 'OUTPUTS.tsv', executorlib.ANALYSIS_SUBMISSIONS]:
        if (adir / name).is_file():
            copy_file(adir / name, target / rel / name)
    copy_file(record_path, target.parent / 'approvals' / (stage_id_of(rel) + '.json'))
    return {'kind': '03', 'rel': rel, 'scripts': sorted(set(scripts))}, approval.get('actor')


# =================================================================================================
# render: pure, from the harvest
# =================================================================================================

class Masker(object):
    """One mask map per package: absolute path prefixes to placeholders, storage URIs to
    <BUCKET>/<key>, account ids to <account>. The map lists placeholders and span counts only."""

    def __init__(self, record):
        self.prefixes = sorted(((p['prefix'], p['placeholder']) for p in record['prefixes']),
                               key=lambda item: -len(item[0]))
        self.buckets = list(record['secrets']['buckets'])
        self.accounts = list(record['secrets']['accounts'])
        self.counts = {}

    def count(self, name, n):
        if n:
            self.counts[name] = self.counts.get(name, 0) + n

    def mask(self, text):
        text, n = STORAGE_URI.subn(lambda m: m.group(1) + '://<BUCKET>', text)
        self.count('<BUCKET>', n)
        for account in self.accounts:
            self.count('<account>', text.count(account))
            text = text.replace(account, '<account>')
        for prefix, placeholder in self.prefixes:
            self.count(placeholder, text.count(prefix))
            text = text.replace(prefix, placeholder)
        return text

    def holds(self, text):
        """True when `text` holds a value this map masks."""
        return text != Masker.mask(self._quiet(), text)

    def _quiet(self):
        clone = Masker.__new__(Masker)
        clone.prefixes, clone.buckets, clone.accounts, clone.counts = self.prefixes, self.buckets, self.accounts, {}
        return clone


class Package(object):
    def __init__(self):
        self.files = {}

    def add(self, rel, data):
        if rel in self.files:
            raise Refusal('two package files would share the path %s' % rel)
        if isinstance(data, str):
            data = data.encode('utf-8')
        self.files[rel] = data


def tables_sources(rows, columns):
    for row in rows:
        for column in columns:
            if column == 'source' or column.endswith('_source'):
                if not any(str(row[column]).startswith(label) for label in LABELS):
                    raise Refusal('a %s cell carries no label' % column)


class Render(object):
    def __init__(self, args):
        self.harvest = Path(args.harvest)
        self.repo = Path(args.gars_repo)
        try:
            self.record = json.loads((self.harvest / 'HARVEST.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            raise Refusal('the harvest has no readable HARVEST.json')
        if self.record.get('format') != HARVEST_FORMAT:
            raise Refusal('the harvest format is not %s' % HARVEST_FORMAT)
        self.commit = self.record['gars_commit']
        if not COMMIT.match(self.commit):
            raise Refusal('the harvest names no full GARS commit')
        self.masker = Masker(self.record)
        self.sources = self.read_sources(Path(args.sources))
        self.tolerance_bytes, self.tolerances = self.read_tolerances(Path(args.tolerances))
        self.pkg = Package()
        self.not_recorded, self.withheld, self.left_out, self.unread = [], [], [], []
        self.masked_scripts = []
        self.oracle = set()
        self.project = self.harvest / 'project'
        self.stages = []
        for stage in self.record['stages']:
            if stage['kind'] == '02':
                path = self.project / stage['rel'] / 'reproducibility' / 'manifest.json'
                try:
                    manifest = json.loads(path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    raise Refusal('the harvest lacks the manifest of %s' % stage['rel'])
                if manifest.get('gars_commit') != self.commit:
                    raise Refusal('the manifest of %s names another GARS commit than the harvest' % stage['rel'])
                if manifest.get('data_class') != 'public':
                    raise Refusal('the manifest of %s: data_class is not public' % stage['rel'])
                self.stages.append(dict(stage, id=stage_id_of(stage['rel']), manifest=manifest,
                                        manifest_path=path))
            else:
                self.stages.append(dict(stage, id=stage_id_of(stage['rel'])))

    # ---- the three inputs render reads besides the harvest ------------------------------------

    def show(self, path):
        return git(self.repo, 'show', '%s:%s' % (self.commit, path))

    def read_sources(self, path):
        try:
            rows = read_tsv(path)
        except (OSError, UnicodeError, csv.Error):
            raise Refusal('cannot read the lane sources file')
        for row in rows:
            if set(row) != {'kind', 'name', 'url', 'sha256', 'source'} or row['kind'] not in ('input', 'reference'):
                raise Refusal('a lane sources row is not kind/name/url/sha256/source')
            pinned = re.match(r'https://raw\.githubusercontent\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/([0-9a-f]{40})/', row['url'])
            if not pinned or not DIGEST.match(row['sha256']) or not re.match(
                    r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}:\S+\Z', row['source']):
                raise Refusal('lane source %s is not pinned to a commit with a sha256' % row['name'])
        self.sources_bytes = path.read_bytes()
        return rows

    def read_tolerances(self, path):
        try:
            data = path.read_bytes()
            value = json.loads(data.decode('utf-8'))
        except (OSError, UnicodeError, ValueError):
            raise Refusal('cannot read the package tolerances file')
        entries = value.get('entries') if isinstance(value, dict) else None
        if not isinstance(entries, list):
            raise Refusal('the package tolerances file has no entries list')
        for entry in entries:
            if not isinstance(entry, dict) or entry.get('mode') not in COMPARISON_MODES or \
                    entry.get('mode') == 'exact' or entry.get('origin') not in ORIGINS or \
                    not entry.get('cause') or not entry.get('evidence') or \
                    not isinstance(entry.get('members'), list) or not entry['members']:
                raise Refusal('a tolerance entry lacks a declared mode, members, a cause, evidence or an origin')
        return data, entries

    # ---- the package files --------------------------------------------------------------------

    def run(self, out):
        stages02 = [s for s in self.stages if s['kind'] == '02']
        self.code(stages02)
        self.env(stages02)
        self.inputs(stages02)
        self.params(stages02)
        self.outputs(stages02)
        self.records(stages02)
        self.analyses([s for s in self.stages if s['kind'] == '03'])
        self.methods()
        for name in STATIC:
            self.pkg.add(name, (TEMPLATES / name).read_bytes())
        self.pages(stages02)
        self.sweep()
        sums = ''.join('%s  %s\n' % (sha256_bytes(self.pkg.files[rel]), rel) for rel in sorted(self.pkg.files))
        self.pkg.add('SHA256SUMS', sums)
        self.write(out)
        return sha256_bytes(sums.encode('utf-8'))

    def gars_values(self, stages02):
        values = sorted(set(s['manifest'].get('template_version') for s in stages02))
        if len(values) > 1:
            raise Refusal('the stages record different template versions')
        return values[0] if values else NOT_RECORDED

    def code(self, stages02):
        citation = self.show('CITATION.cff').decode('utf-8')
        match = re.search(r'^repository-code: "([^"]+)"$', citation, re.M)
        if not match:
            raise Refusal('CITATION.cff at the GARS commit names no repository-code')
        self.repository = match.group(1)
        rows = [
            {'field': 'repository', 'value': self.repository,
             'source': packaging_label('genomics-agentic-research-system', self.commit, 'CITATION.cff')},
            {'field': 'gars_commit', 'value': self.commit, 'source': run_label('gars_commit')},
            {'field': 'template_version', 'value': self.gars_values(stages02), 'source': run_label('template_version')},
            {'field': 'package_run_commit', 'value': self.record['package_run']['commit'],
             'source': HARVEST + ': named at harvest; the sha256 below equals that commit\'s package_run.py'},
            {'field': 'package_run_sha256', 'value': self.record['package_run']['sha256'],
             'source': HARVEST + ': sha256 of that package_run.py'},
            {'field': 'gars_clone_status', 'value': 'clean (git status --porcelain: 0 lines)',
             'source': HARVEST + ': git status of the GARS clone that ran'},
        ]
        lane = self.record['package_run']
        try:
            ran = sha256_bytes(git(self.repo, 'show', '%s:gars/_system/claims/package_run.py' % lane['commit']))
        except Refusal:
            raise Refusal('the lane commit harvest named (%s) is not in the GARS repository' % lane['commit'][:12])
        if ran != lane['sha256']:
            raise Refusal('the package_run.py that ran harvest is not the file at the lane commit it named')
        self.pkg.add('code/GARS.txt', tsv(('field', 'value', 'source'), rows))
        workspace = self.show('gars/_system/workspace.py').decode('utf-8')
        legacy = re.search(r'^NEXTFLOW_LEGACY_PARSER = \{([^}]*)\}', workspace, re.M)
        if not legacy:
            raise Refusal('workspace.py at the GARS commit names no NEXTFLOW_LEGACY_PARSER')
        legacy = set(re.findall(r'"([^"]+)"', legacy.group(1)))
        pin = re.findall(r'/nextflow-([0-9][0-9.]*)-', self.show('gars/_references/gars-nxf.conda.txt').decode('utf-8'))
        prows = []
        for s in stages02:
            m = s['manifest']
            versions = {}
            for i, entry in enumerate(m.get('software_versions') or []):
                for key, value in (entry.get('versions') or {}).items():
                    versions[key] = (value, 'software_versions[%d].versions.%s' % (i, key))
            workflows = sorted(k for k in versions if k.startswith('Workflow/nf-core/'))
            if len(workflows) != 1:
                raise Refusal('%s records %d nf-core workflow names, not one' % (s['rel'], len(workflows)))
            nextflow = versions.get('Workflow/Nextflow')
            if nextflow is None:
                raise Refusal('%s records no Nextflow version' % s['rel'])
            if pin != [str(nextflow[0]).lstrip('v')]:
                raise Refusal('%s: the recorded Nextflow %s is not the gars-nxf lock\'s %s'
                              % (s['rel'], nextflow[0], ','.join(pin) or 'none'))
            parser = 'v1' if m.get('wrapper') in legacy else 'none'
            prows.append({
                'stage': s['id'], 'workflow': m['workflow_name'], 'workflow_source': run_label('workflow_name'),
                'pipeline': workflows[0][len('Workflow/'):], 'pipeline_source': run_label(versions[workflows[0]][1] + ' (key)'),
                'release': m['workflow_version'], 'release_source': run_label('workflow_version'),
                'pipeline_commit': m['pipeline_commit'], 'pipeline_commit_source': run_label('pipeline_commit'),
                'nextflow': str(nextflow[0]).lstrip('v'), 'nextflow_source': run_label(nextflow[1]),
                'nxf_syntax_parser': parser,
                'nxf_syntax_parser_source': packaging_label('genomics-agentic-research-system', self.commit,
                                                            'gars/_system/workspace.py') + ' (NEXTFLOW_LEGACY_PARSER)'})
            if not COMMIT.match(str(m.get('pipeline_commit'))):
                raise Refusal('%s records no full pipeline commit' % s['rel'])
            # commands.sh is the run's bound submission record (its sha256 is recorded). submit.sh is
            # not shipped: no run record binds its bytes, only its input-key line (review h2 M1).
            path = self.project / s['rel'] / 'reproducibility' / 'commands.sh'
            text = path.read_text(encoding='utf-8')
            self.mark_oracle(text)
            note = ('# Masked copy written by package_run.py render: absolute paths, buckets and account ids '
                    'are replaced (PROVENANCE.md).\n# The sha256 the run recorded is of the unmasked file and '
                    'is not checkable from this package.\n')
            self.pkg.add('code/%s/commands.sh' % s['id'], note + self.masked(text, 'commands.sh'))
            scripts = self.project / s['rel'] / 'scripts'
            for path in sorted(scripts.rglob('*')) if scripts.is_dir() else []:
                if path.is_file():
                    text = path.read_text(encoding='utf-8')
                    if self.masker.holds(text):
                        raise Refusal('the generated script %s holds a masked value' % path.name)
                    self.pkg.add('code/%s/scripts/%s' % (s['id'], path.relative_to(scripts).as_posix()), text)
        self.pkg.add('code/pipelines.tsv', tsv(('stage', 'workflow', 'workflow_source', 'pipeline',
                                                'pipeline_source', 'release', 'release_source', 'pipeline_commit',
                                                'pipeline_commit_source', 'nextflow', 'nextflow_source',
                                                'nxf_syntax_parser', 'nxf_syntax_parser_source'), prows))
        self.pipelines = prows

    def masked(self, text, role):
        """A masked copy, refused if any absolute path other than a system folder survives."""
        text = self.masker.mask(text)
        if SURVIVOR.search(text):
            raise Refusal('an absolute path survived masking in %s' % role)
        return text

    def mark_oracle(self, text):
        if self.masker.holds(text):
            self.oracle.add(sha256_bytes(text.encode('utf-8')))

    def env(self, stages02):
        configs, containers = set(), []
        for s in stages02:
            m = s['manifest']
            entries = [e for e in m.get('execution_config') or [] if e.get('role') == 'nextflow_config']
            if len(entries) != 1:
                raise Refusal('%s records no single executor config' % s['rel'])
            name = Path(entries[0]['path']).name
            path = self.project / '_config' / name
            if not path.is_file() or sha256_file(path) != entries[0]['sha256']:
                raise Refusal('%s: the harvested executor config is not the one the run recorded' % s['rel'])
            configs.add(path.read_bytes())
            seen = set()
            for i, c in enumerate(m.get('containers') or []):
                key = (c.get('process'), c.get('image'))
                if key in seen:
                    continue
                seen.add(key)
                if not PROCESS_NAME.match(str(c.get('process'))):
                    raise Refusal('%s: a recorded process name is not a plain process name' % s['rel'])
                image = str(c.get('image'))
                registry = image.split('/', 1)[0] if '/' in image and ('.' in image.split('/', 1)[0]) else 'docker.io'
                if registry not in PUBLIC_REGISTRIES:
                    raise Refusal('%s: process %s ran an image from a registry a stranger cannot pull'
                                  % (s['rel'], c['process']))
                digest = c.get('digest')
                containers.append({
                    'stage': s['id'], 'process': c['process'], 'image': image,
                    'image_source': run_label('containers[%d].image' % i),
                    'digest': digest if digest else NOT_RECORDED,
                    'digest_source': run_label('containers[%d].digest' % i) + ('' if digest else ' (absent)')})
                if not digest:
                    self.note_not_recorded('%s: container digest of process %s' % (s['id'], c['process']))
        if len(configs) != 1:
            raise Refusal('the stages ran with different executor configs; one env/run-executor.config cannot hold them')
        config = configs.pop()
        if self.masker.holds(config.decode('utf-8')):
            raise Refusal('the executor config holds a path, bucket or account id; it ships byte-exact')
        self.pkg.add('env/run-executor.config', config)
        limits = re.search(r'^\s*resourceLimits\s*=\s*\[([^\]]*)\]', config.decode('utf-8'), re.M)
        if not limits:
            raise Refusal('the executor config records no resourceLimits clamp')
        containers.sort(key=lambda r: (r['stage'], r['process'], r['image']))
        self.pkg.add('env/containers.tsv', tsv(('stage', 'process', 'image', 'image_source', 'digest',
                                                'digest_source'), containers))
        lines = ['// Generated by package_run.py render. Every line names its source.',
                 '// The re-run machine class (4 CPUs, 16 GB, every process local, in Docker) is this',
                 '// package\'s own setting (decision 0281), not a run record.',
                 'executor {', "    name   = 'local'", '    cpus   = 4', '    memory = 14.GB', '}', '',
                 'process {',
                 '    // recorded at run: resourceLimits of env/run-executor.config, the run\'s own clamp',
                 '    resourceLimits = [%s]' % limits.group(1).strip()]
        named = {}
        for c in containers:
            if named.setdefault(c['process'], c['image']) != c['image']:
                raise Refusal('process %s ran two different images' % c['process'])
        for process in sorted(named):
            lines.append("    // recorded at run: the image the trace names for this process (tag; digest %s)"
                         % ('recorded' if any(c['digest'] != NOT_RECORDED for c in containers
                                              if c['process'] == process) else 'not recorded'))
            lines.append("    withName: '%s' { container = '%s' }" % (process, named[process]))
        lines.append('}')
        self.pkg.add('env/rerun.config', '\n'.join(lines) + '\n')
        pins = self.show('gars/_references/gars-bio.lock.txt').decode('utf-8')
        self.pkg.add('env/gars-bio.pins.txt',
                     '# %s: gars/_references/gars-bio.lock.txt at the GARS commit.\n'
                     '# A pip pin list with no hashes, not the run\'s recorded environment (PROVENANCE.md).\n'
                     % packaging_label('genomics-agentic-research-system', self.commit, 'gars/_references/gars-bio.lock.txt')
                     + pins)

    def note_not_recorded(self, text):
        if text not in self.not_recorded:
            self.not_recorded.append(text)

    def source_row(self, kind, name):
        rows = [r for r in self.sources if r['kind'] == kind and r['name'] == name]
        if len(rows) != 1:
            raise Refusal('the lane sources name %s %s %d times, not once' % (kind, name, len(rows)))
        return rows[0]

    def inputs(self, stages02):
        rows, by_file = [], {}
        for item in self.record['inputs']:
            known = by_file.setdefault(item['file'], item['sha256'])
            if known != item['sha256']:
                raise Refusal('two input files named %s differ' % item['file'])
        for name, digest in sorted(by_file.items()):
            source = self.source_row('input', name)
            if source['sha256'] != digest:
                raise Refusal('input %s: the harvest sha256 differs from the pinned source\'s' % name)
            rows.append({'file': name, 'url': source['url'],
                         'url_source': PACKAGING + source['source'],
                         'sha256': digest, 'sha256_source': HARVEST + ': hashed on the run\'s machine from the file the samplesheet named'})
        self.note_not_recorded('every stage: the input files\' checksums and URLs (G5)')
        self.pkg.add('inputs/inputs.tsv', tsv(('file', 'url', 'url_source', 'sha256', 'sha256_source'), rows))
        self.pkg.add('inputs/lane-sources.tsv', self.sources_bytes)
        refs = []
        for s in stages02:
            m = s['manifest']
            sheet_path = Path((m.get('inputs') or {}).get('samplesheet', ''))
            harvested = self.project / '01_samplesheets' / sheet_path.name
            if not harvested.is_file():
                raise Refusal('%s: the harvest lacks the samplesheet' % s['rel'])
            text = harvested.read_text(encoding='utf-8')
            self.mark_oracle(text)
            out = []
            for r, row in enumerate(csv.reader(io.StringIO(text))):
                cells = []
                for value in row:
                    if r and value.startswith('/'):
                        if Path(value).name not in by_file:
                            raise Refusal('%s: a samplesheet path names a file the harvest did not hash' % s['rel'])
                        value = INPUTS_TOKEN + Path(value).name
                    cells.append(value)
                out.append(','.join(cells))
            self.pkg.add('inputs/%s.samplesheet.csv' % s['id'], '\n'.join(out) + '\n')
            reference = m.get('reference') or {}
            for param, field in sorted(REFERENCE_PARAMS.items()):
                value = (m.get('params') or {}).get(param)
                if not value:
                    continue
                name = Path(value).name
                source = self.source_row('reference', name)
                if reference.get(field) != source['sha256']:
                    raise Refusal('%s: reference %s recorded sha256 differs from the pinned source\'s' % (s['rel'], name))
                refs.append({'stage': s['id'], 'param': param, 'file': name, 'url': source['url'],
                             'url_source': PACKAGING + source['source'],
                             'sha256': reference[field], 'sha256_source': run_label('reference.' + field),
                             'build': reference.get('build') or NOT_RECORDED, 'build_source': run_label('reference.build'),
                             'annotation_release': reference.get('annotation_release') or NOT_RECORDED,
                             'annotation_release_source': run_label('reference.annotation_release')})
        self.pkg.add('inputs/reference.tsv', tsv(('stage', 'param', 'file', 'url', 'url_source', 'sha256',
                                                  'sha256_source', 'build', 'build_source', 'annotation_release',
                                                  'annotation_release_source'), refs))

    def params(self, stages02):
        rows, seeds = [], []
        for s in stages02:
            m = s['manifest']
            params, shipped = m.get('params') or {}, {}
            sheet = (m.get('inputs') or {}).get('samplesheet')
            for key in sorted(params):
                value = params[key]
                label = run_label('params.' + key)
                if key.endswith('_index'):
                    raise Refusal('%s: the recorded parameter %s points at an index that is not in the package; '
                                  'the run must record save_reference instead' % (s['rel'], key))
                if isinstance(value, str) and (value.startswith('/') or STORAGE_URI.search(value)):
                    if value == sheet:
                        value = '%s/inputs/%s.samplesheet.csv' % (RERUN_TOKEN, s['id'])
                    elif key == 'outdir':
                        value = '%s/results/%s' % (RERUN_TOKEN, s['id'])
                    elif key in REFERENCE_PARAMS:
                        value = '%s/refs/%s' % (RERUN_TOKEN, Path(value).name)
                    else:
                        raise Refusal('%s: parameter %s holds a path the package cannot ship' % (s['rel'], key))
                    label += ', the path replaced by the re-run\'s own folder'
                if isinstance(value, str) and YAML_SCALAR.match(value):
                    # params.yaml wrote it bare, so Nextflow's YAML reader saw a boolean or a number.
                    value = yaml_scalar(value)
                    label += ', typed as the run\'s params.yaml was read'
                shipped[key] = value
                rows.append({'stage': s['id'], 'key': key, 'value': json.dumps(value), 'value_source': label})
            self.pkg.add('params/%s.params.json' % s['id'], dump_json(shipped))
            recorded = m.get('random_seeds')
            if isinstance(recorded, str):
                seeds.append({'stage': s['id'], 'call': 'every call', 'seed': recorded,
                              'seed_source': run_label('random_seeds')})
            elif isinstance(recorded, list):
                for i, item in enumerate(recorded):
                    seed = item.get('seed')
                    seeds.append({'stage': s['id'], 'call': item.get('call', NOT_RECORDED),
                                  'seed': seed if seed is not None else 'seed not supported (%s)'
                                  % item.get('determinism', NOT_RECORDED),
                                  'seed_source': run_label('random_seeds[%d]' % i)})
            else:
                seeds.append({'stage': s['id'], 'call': 'every call', 'seed': NOT_RECORDED,
                              'seed_source': run_label('random_seeds') + ' (absent)'})
                self.note_not_recorded('%s: random seeds' % s['id'])
        self.pkg.add('params/params.tsv', tsv(('stage', 'key', 'value', 'value_source'), rows))
        self.pkg.add('params/seeds.tsv', tsv(('stage', 'call', 'seed', 'seed_source'), seeds))

    def outputs(self, stages02):
        rows = []
        declared = {}
        for entry in self.tolerances:
            for member in entry['members']:
                declared[(entry.get('stage'), member)] = entry['mode']
        copied = dict(((m['stage'], m['output_path'], m['member']), m) for m in self.record['members'])
        for s in stages02:
            for output in s['manifest'].get('outputs') or []:
                if not output['path'].startswith(RESULTS_PREFIX):
                    raise Refusal('%s: output %s is not under %s' % (s['rel'], output['path'], RESULTS_PREFIX))
                listed = ([('.', output['sha256'])] if output.get('members') is None else
                          [(m['path'], m['sha256']) for m in output['members']])
                for member, digest in listed:
                    full = output['path'] if member == '.' else output['path'] + '/' + member
                    mode = declared.pop((s['id'], full), 'exact')
                    rows.append({'stage': s['id'], 'output_type': output['type'], 'output_path': output['path'],
                                 'member': member, 'recorded_sha256': digest,
                                 'recorded_sha256_source': run_label('outputs' if member == '.' else 'outputs[].members'),
                                 'mode': mode,
                                 'mode_source': PACKAGING + 'outputs/package-tolerances.json' if mode != 'exact'
                                 else PACKAGING + 'the default comparison mode (decision 0283)'})
                    harvested = copied.get((s['rel'], output['path'], member))
                    self.oracle_member(s, full, harvested)
                    self.small(s, full, digest, harvested)
        if declared:
            raise Refusal('a tolerance entry names a member the run did not record')
        self.pkg.add('outputs/outputs.tsv', tsv(('stage', 'output_type', 'output_path', 'member', 'recorded_sha256',
                                                 'recorded_sha256_source', 'mode', 'mode_source'), rows))
        self.pkg.add('outputs/package-tolerances.json', self.tolerance_bytes)

    def sensitive(self):
        record = self.record['secrets']
        return ([('a run bucket name', b) for b in record['buckets']] +
                [('an account id', a) for a in record['accounts']] +
                [('the approver the run recorded', a) for a in record.get('actors', [])] +
                [('a user name the run\'s records carry', u) for u in record.get('users', [])])

    def oracle_member(self, s, full, harvested):
        """A recorded output's sha256 is printed for comparison, so an output holding a bucket, account
        id, approver or user name would make that hash an oracle: refused. A member too large to
        harvest was not read, and PROVENANCE says so."""
        rel = '%s/%s' % (s['id'], full)
        if harvested is None or not harvested['copied']:
            if rel not in self.unread:
                self.unread.append(rel)
            return
        data = (self.project / s['rel'] / full).read_bytes()
        text = data.decode('utf-8', 'replace')
        for what, value in self.sensitive():
            hit = user_named(text, value) if what.startswith('a user name') else value.encode('utf-8') in data
            if value and hit:
                raise Refusal('output member %s holds %s; its recorded sha256 would confirm that value offline'
                              % (rel, what))

    def small(self, s, full, digest, harvested):
        if not full.endswith(TABLE_SUFFIXES) or 'pipeline_info/' in full:
            return
        rel = '%s/%s' % (s['id'], full[len(RESULTS_PREFIX):])
        if 'outputs/small/' + rel in self.pkg.files or rel in [r for r, _ in self.left_out]:
            return   # a member two nested outputs share is placed, or named, once
        if harvested is None or not harvested['copied']:
            self.left_out.append((rel, 'larger than 5 MB'))
            return
        data = (self.project / s['rel'] / full).read_bytes()
        if sha256_bytes(data) != digest:
            raise Refusal('%s: a harvested result table differs from its recorded sha256' % s['rel'])
        if len(data) > SMALL_LIMIT:
            self.left_out.append((rel, 'larger than 5 MB'))
            return
        text = data.decode('utf-8', 'replace')
        if self.masker.holds(text) or HOME_PATH.search(text):
            self.left_out.append((rel, 'it holds a path, which a byte-exact table cannot mask'))
            return
        self.pkg.add('outputs/small/' + rel, data)

    ALLOWED = ('agent_model', 'backend', 'containers', 'data_class', 'execution', 'execution_config',
               'failure_class', 'gars_commit', 'model_steps', 'outputs', 'pipeline_commit', 'predicate_facts',
               'purpose', 'random_seeds', 'reference', 'software_versions', 'template_version', 'threads',
               'venue', 'workflow_name', 'workflow_version', 'wrapper')
    HASH_FIELDS = (('command.sha256', 'reproducibility/commands.sh'), ('config_sha256', None),
                   ('samplesheet_sha256', None), ('idempotency_key', None), ('design_check.sha256', None))

    def records(self, stages02):
        for s in stages02:
            m = s['manifest']
            self.mark_oracle(s['manifest_path'].read_text(encoding='utf-8'))
            kept = dict((k, m[k]) for k in self.ALLOWED if k in m)
            kept['containers'] = [dict((k, c[k]) for k in ('process', 'image', 'digest') if k in c)
                                  for c in m.get('containers') or []]
            kept['execution_config'] = [dict((k, e[k]) for k in ('role', 'path', 'sha256') if k in e)
                                        for e in m.get('execution_config') or [] if e.get('role') == 'nextflow_config']
            for step in kept.get('model_steps') or []:
                step.pop('input_context', None)
            withheld = [{'field': f, 'reason': self.hash_reason(s, m, f)}
                        for f, _ in self.HASH_FIELDS if self.present(m, f)]
            withheld.append({'field': 'execution_config[executor_descriptor]', 'reason': 'executor descriptor values '
                             'beyond the backend name never ship'})
            if any(st.get('input_context') for st in m.get('model_steps') or []):
                withheld.append({'field': 'model_steps[].input_context', 'reason': 'it hashes the project history'})
            kept['stage'] = s['id']
            kept['withheld_fields'] = withheld
            self.withheld += [(s['id'], w['field'], w['reason']) for w in withheld]
            text = dump_json(kept)
            if self.masker.holds(text):
                raise Refusal('%s: an allowlisted record field holds a path, bucket or account id' % s['rel'])
            self.pkg.add('records/%s.manifest.json' % s['id'], text)

    def hash_reason(self, s, m, field):
        """Why a recorded hash is cited by name only: the file it hashes holds a masked value (then
        it is an oracle, and the sweep is armed with it), or that file is not in this package."""
        stage = self.project / s['rel']
        files = {'command.sha256': [stage / 'reproducibility' / 'commands.sh'],
                 'config_sha256': [self.project / '_config' / Path(m['inputs'].get('config', '')).name],
                 'samplesheet_sha256': [self.project / '01_samplesheets' / Path(m['inputs'].get('samplesheet', '')).name],
                 'design_check.sha256': [self.project / str((m.get('design_check') or {}).get('path', ''))]}
        files['idempotency_key'] = files['config_sha256'] + files['samplesheet_sha256'] + [stage / 'params.yaml']
        holds = False
        for path in files[field]:
            if not path.is_file():
                return 'the file it hashes was not harvested'
            holds = holds or self.masker.holds(path.read_text(encoding='utf-8', errors='replace'))
        value = m[field.split('.')[0]]['sha256'] if '.' in field else m[field]
        if holds:
            self.oracle.add(value)
            return 'it hashes a file holding values the package masks'
        return 'the file it hashes is not in this package'

    @staticmethod
    def present(m, dotted):
        node = m
        for part in dotted.split('.'):
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
        return node not in (None, '')

    def analyses(self, stages03):
        rows = []
        for s in stages03:
            adir = self.project / s['rel']
            plan = (adir / 'PLAN.md').read_bytes()
            approval = json.loads((self.harvest / 'approvals' / (s['id'] + '.json')).read_text(encoding='utf-8'))
            if approval.get('plan_sha256') != sha256_bytes(plan):
                raise Refusal('%s: PLAN.md is not the plan its approval record binds (R-073)' % s['rel'])
            self.pkg.add('params/%s.PLAN.md' % s['id'], plan)
            rows.append({'stage': s['id'], 'plan_sha256': approval['plan_sha256'],
                         'plan_sha256_source': '%s: the approval record\'s plan_sha256 (its actor and plan path are never printed)' % RUN,
                         'approved_at': approval.get('timestamp') or NOT_RECORDED,
                         'approved_at_source': '%s: the approval record\'s timestamp' % RUN})
            for name in s.get('scripts', []):
                text = (adir / name).read_text(encoding='utf-8')
                if self.masker.holds(text):
                    # A real launcher cds into the analysis folder by absolute path: shipped masked,
                    # and its submit-time sha256 (an oracle then) is never printed (review h2 n10).
                    self.mark_oracle(text)
                    self.masked_scripts.append('%s/%s' % (s['id'], name))
                    text = ('# Masked copy written by package_run.py render (PROVENANCE.md); the sha256 bound '
                            'at submit is of the unmasked file.\n' + self.masked(text, name))
                self.pkg.add('code/%s/scripts/%s' % (s['id'], name), text)
            self.note_not_recorded('%s: output sha256 and the analysis environment (G2)' % s['id'])
        if rows:
            self.pkg.add('params/approval.tsv', tsv(('stage', 'plan_sha256', 'plan_sha256_source', 'approved_at',
                                                     'approved_at_source'), rows))

    def methods(self):
        renderer = load_module(HERE / 'render_methods.py', 'package_run_render_methods')
        manifests = [str(s['manifest_path']) for s in self.stages if s['kind'] == '02']
        plans = [s for s in self.stages if s['kind'] == '03']
        plan = approval = history = None
        if len(plans) > 1:
            raise Refusal('the Methods renderer takes one approved plan; this harvest holds %d' % len(plans))
        if plans:
            plan = str(self.project / plans[0]['rel'] / 'PLAN.md')
            approval = str(self.harvest / 'approvals' / (plans[0]['id'] + '.json'))
            if (self.project / 'HISTORY.md').is_file():
                history = str(self.project / 'HISTORY.md')
        try:
            text = renderer.render(manifests, plan, approval, history)
        except renderer.Refusal as exc:
            raise Refusal('the Methods renderer refused: %s' % exc)
        for path in [p for p in (plan, approval, history) if p]:
            self.mark_oracle(Path(path).read_text(encoding='utf-8'))
        self.pkg.add('METHODS.md', text)

    # ---- the human pages ----------------------------------------------------------------------

    def pages(self, stages02):
        first = self.pipelines[0] if self.pipelines else None
        what = ('A GARS run of %s %s (pipeline commit `%s`) at GARS commit `%s`.'
                % (first['pipeline'], first['release'], first['pipeline_commit'], self.commit)) if first else \
            'A GARS custom analysis at GARS commit `%s`.' % self.commit
        g1 = any('container digest' in n for n in self.not_recorded)
        readme = ['# Reproduction package', '', what, '',
                  'Re-run: `bash rerun.sh --out <empty folder>`', '',
                  'Verify: `python3 verify.py` (this package), then `python3 verify.py --against <that folder>` '
                  '(the re-run\'s outputs).', '']
        if g1:
            readme += ['Container images are pinned by tag; the run did not record their digests (PROVENANCE.md).', '']
        self.pkg.add('README.md', '\n'.join(readme))
        reproduce = [
            '# Reproduce', '',
            '## Prerequisites', '',
            '- Docker, with at least 4 CPUs and about 16 GB of memory available to it.',
            '- Java, curl, python3 and the Nextflow launcher (`nextflow`) on PATH; rerun.sh pins the Nextflow '
            'version the run recorded (code/pipelines.tsv).',
            '- About 10 GB of free disk.', '',
            '## Re-run', '', '`bash rerun.sh --out <empty folder>`', '',
            'It downloads every input and reference file from the URL the package names, and refuses before '
            'any pipeline starts if a checksum differs, saying which file and where its checksum came from.', '',
            '## Verify', '', '`python3 verify.py --against <that folder>`', '',
            'Each recorded output is compared member by member and lands in one count: M matched exactly, '
            'K within the stated tolerance, P present but not byte-comparable, F differ.',
            'The exit code is 0 when every output matched (M + K = N), 2 when any output differs, and 3 when '
            'none differs but some are presence-only.', '',
            '## On a mismatch', '',
            'Read the member table verify.py prints and the comparison entries in PROVENANCE.md; a member '
            'that differs with no entry is a finding about this package, not a failure of your machine.', '']
        if any(s['kind'] == '03' for s in self.stages):
            reproduce += ['A stage 03 analysis is packaged in full (params/, code/), but its re-run is not '
                          'automated in this version.', '']
        self.pkg.add('REPRODUCE.md', '\n'.join(reproduce))
        self.pkg.add('PROVENANCE.md', self.provenance())

    def provenance(self):
        lines = ['# Provenance', '', '## Labels', '',
                 'Every value in this package\'s tables carries one of three labels:',
                 '- `recorded at run`: a field of a run record, named; only these are the run\'s attestation.',
                 '- `computed at harvest`: hashed on the run\'s machine from the unmasked file, after the run and '
                 'before teardown.',
                 '- `supplied at packaging from <repository>@<commit>:<path>`: read from a named file at a pinned commit.',
                 '', '## Masked values', '',
                 'Absolute paths, storage buckets and account ids are replaced; the originals are not in this package.',
                 '', '| Placeholder | Spans replaced |', '|---|---|']
        for name in sorted(self.masker.counts):
            lines.append('| `%s` | %d |' % (name, self.masker.counts[name]))
        lines += ['', '## Hash oracle', '',
                  'A sha256 of a run record holding a masked value would let anyone confirm a guessed user name, '
                  'path or bucket, so this package prints no such hash; the fields below are cited by name only '
                  'and are not checkable from the package.',
                  'Output sha256 values are printed, since the comparison needs them; render refuses an output '
                  'holding a bucket, account id, approver or user name, and a result table holding a path is '
                  'named under "Result tables not shipped".',
                  'submit.sh is not shipped: no run record binds its bytes. code/<stage>/commands.sh, the recorded '
                  'submission line, is.',
                  'Limit: GARS records no sha256 of submit.sh. On the run\'s machine, harvest compared the launch line '
                  'Nextflow itself logged (run/.nextflow.log) with the nextflow run line in submit.sh and refused on '
                  'any difference; the rest of submit.sh (its environment lines) is bound by nothing.', '']
        for rel in self.masked_scripts:
            lines.append('- %s: shipped masked; its sha256 bound at submit is of the unmasked file, not printed.' % rel)
        for stage, field, reason in self.withheld:
            lines.append('- %s: `%s`, not printed: %s.' % (stage, field, reason))
        for rel in sorted(self.unread):
            lines.append('- %s: larger than 5 MB and not harvested, so not read for masked values; its recorded '
                         'sha256 is printed for comparison.' % rel)
        lines += ['', '## Not recorded', '']
        for text in self.not_recorded:
            lines.append('- %s: not recorded by the run.' % text)
        lines.append('- every stage: the timezone of the trace timestamps.')
        lines += ['', '## Gaps', '']
        if any('container digest' in n for n in self.not_recorded):
            lines.append('- G1: container images are pinned by the tag the trace recorded; no digest was recorded '
                         'at run, and none is resolved here.')
        lines.append('- G4: the run\'s records hold absolute paths; the package masks them (above).')
        lines.append('- G5: no run record holds an input URL or an input FASTQ checksum; inputs/inputs.tsv labels '
                     'each value it carries.')
        if any(s['kind'] == '03' for s in self.stages):
            lines.append('- G2: a stage 03 analysis records no output sha256 and no environment.')
        lines += ['', '## Comparison modes and tolerance entries', '',
                  'Every member is compared `exact` unless an entry below declares another mode with a cause read '
                  'from its bytes (decision 0283).', '']
        for origin in ORIGINS:
            lines.append('- entries of origin `%s`: %d' % (origin, sum(1 for e in self.tolerances if e['origin'] == origin)))
        for entry in self.tolerances:
            lines.append('- %s, %d members, mode `%s`, origin `%s`: %s (evidence: %s).'
                         % (entry.get('stage'), len(entry['members']), entry['mode'], entry['origin'],
                            entry['cause'], entry['evidence']))
        lines += ['', '## Result tables not shipped', '']
        for rel, reason in sorted(self.left_out):
            lines.append('- `%s`: %s.' % (rel, reason))
        if not self.left_out:
            lines.append('- none.')
        lines += ['', '## Environment', '',
                  '- env/gars-bio.pins.txt is the pip pin list at the GARS commit, with no hashes; it is not the '
                  'run\'s recorded environment.',
                  '- env/rerun.config pins each process to the image tag the run recorded, on 4 CPUs and the run\'s '
                  'own resource clamp; the original ran on AWS Batch, so a re-run here is cross-platform.',
                  '', '## Sources', '',
                  '- code/, env/containers.tsv, params/, outputs/outputs.tsv, records/: the run\'s manifests, as harvested.',
                  '- inputs/inputs.tsv: checksums computed at harvest; URLs from inputs/lane-sources.tsv.',
                  '- inputs/reference.tsv: checksums recorded at run; URLs from inputs/lane-sources.tsv.',
                  '- METHODS.md: the GARS Methods renderer, run over the same records.',
                  '- code/GARS.txt: the harvest record (the package_run.py checkout and the clone status).', '']
        return '\n'.join(lines)

    # ---- the checks before anything is written ------------------------------------------------

    def sweep(self):
        literal = [('a run bucket name', b) for b in self.masker.buckets] + \
                  [('an account id', a) for a in self.masker.accounts] + \
                  [('the approver the run recorded', a) for a in self.record['secrets'].get('actors', [])] + \
                  [('an original path prefix', p) for p, _ in self.masker.prefixes]
        for rel in sorted(self.pkg.files):
            text = self.pkg.files[rel].decode('utf-8', 'replace')
            hits = []
            if HOME_PATH.search(text):
                hits.append('a home path')
            if UNMASKED_URI.search(text):
                hits.append('an unmasked storage URI')
            for what, value in literal:
                if value and value in text:
                    hits.append(what)
            for user in self.record['secrets'].get('users', []):
                if user_named(text, user):
                    hits.append('a user name the run\'s records carry')
            if BOUNDED_12.search(text):
                hits.append('a 12-digit id')
            if SURVIVOR.search(text):   # every shipped text, not only the masked files (h3-4)
                hits.append('an absolute path (%s)' % SURVIVOR.search(text).group(0))
            for digest in self.oracle:
                if digest in text:
                    hits.append('the sha256 of a file holding a masked value')
            if hits:
                raise Refusal('the masking sweep found %s in %s' % (hits[0], rel))

    def write(self, out):
        out = Path(out)
        if out.exists():
            raise Refusal('the package folder already exists')
        temp = Path(tempfile.mkdtemp(prefix='.package-', dir=str(out.parent)))
        try:
            for rel in sorted(self.pkg.files):
                path = temp / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(self.pkg.files[rel])
                os.chmod(str(path), 0o755 if rel == 'rerun.sh' else 0o644)
            gitleaks(temp)
            os.chmod(str(temp), 0o755)
            os.replace(str(temp), str(out))
            temp = None
        finally:
            if temp is not None:
                shutil.rmtree(str(temp), ignore_errors=True)


def gitleaks(folder):
    """The repository's own gitleaks rules, directory mode, over the package folder only."""
    binary = shutil.which('gitleaks')
    if binary is None:
        raise Refusal('gitleaks is not on PATH; the package is not written unscanned')
    config = HERE.parents[1] / '.gitleaks.toml'
    proc = subprocess.run([binary, 'dir', str(folder), '--config', str(config), '--no-banner', '--redact',
                           '--exit-code', '1'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise Refusal('gitleaks found a finding in the package (exit %d)' % proc.returncode)


def render(args):
    digest = Render(args).run(args.out)
    print('render: package sha256 %s -> %s' % (digest, args.out))
    print('For the paper: "Code, pinned environments, input checksums and output checksums for this analysis '
          'are in the reproduction package %s (sha256 %s)."' % (Path(args.out).name, digest))
    return 0


# =================================================================================================
# rerun-note: the landing README, from the verifying pass's artifact
# =================================================================================================

OK_RESULTS = ('match', 'present')
MACHINE = re.compile(r'[A-Za-z0-9 .,/()+-]{1,80}\Z')
DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}\Z')


def read_artifact(folder, package_digest):
    folder = Path(folder)
    try:
        digest = (folder / 'package-sha256.txt').read_text(encoding='utf-8').strip()
        machine, date = (folder / 'machine.txt').read_text(encoding='utf-8').splitlines()[:2]
        members = read_tsv(folder / 'members.tsv')
        outputs = read_tsv(folder / 'outputs.tsv')
    except (OSError, ValueError, UnicodeError, csv.Error):
        raise Refusal('the pass artifact %s is incomplete' % folder.name)
    if digest != package_digest:
        raise Refusal('the pass artifact verified another package (sha256 %s)' % digest[:12])
    if not MACHINE.match(machine) or not DATE.match(date):
        raise Refusal('the pass artifact\'s machine class or date is malformed')
    return {'machine': machine, 'date': date, 'members': members, 'outputs': outputs}


def rerun_note(args):
    package = Path(args.package)
    compare = load_module(package / 'compare.py', 'package_compare')
    package_digest = sha256_file(package / 'SHA256SUMS')
    if not re.match(r'[a-z0-9-]+\.yml\Z', args.workflow):
        raise Refusal('--workflow is a workflow file name such as reproduction-yeast-atac.yml')
    passes = [read_artifact(a, package_digest) for a in args.artifact]
    if len(passes) > 2:
        raise Refusal('at most two claim passes')
    rows = compare.package_rows(str(package))
    results = [dict(((m['stage'], m['path']), m) for m in p['members']) for p in passes]
    keys = set((r['stage'], compare.member_path(r)) for r in rows)
    for result in results:
        if set(result) != keys:
            raise Refusal('a pass artifact does not list exactly the package\'s members')
    members, unstable = {}, []
    for key in sorted(keys):
        seen = [(r[key]['mode'], r[key]['result']) for r in results]
        stable = len(set(seen)) == 1
        if not stable:
            unstable.append(key)
        row = next(r for r in rows if (r['stage'], compare.member_path(r)) == key)
        members[key] = {'row': row, 'ok': stable and seen[0][1] in OK_RESULTS,
                        'result': seen[0][1] if stable else 'unstable', 'rerun_sha256': ''}
    extra = {}
    for p in passes:
        for o in p['outputs']:
            if int(o['extra']):
                extra[(o['stage'], o['output_path'])] = ['extra']
    result = compare.rollup(rows, members, extra)
    record = json.loads(sorted(package.glob('records/*.manifest.json'))[0].read_text(encoding='utf-8'))
    repository = [r for r in read_tsv(package / 'code' / 'GARS.txt') if r['field'] == 'repository'][0]['value']
    pipes = read_tsv(package / 'code' / 'pipelines.tsv')
    counts = result['counts']
    machine = ' and '.join(sorted(set(p['machine'] for p in passes)))
    dates = ' and '.join(sorted(set(p['date'] for p in passes)))
    runs = '%s/actions/workflows/%s' % (repository, args.workflow)
    badge = 'https://img.shields.io/badge/re--run-%d%%20exact%%2C%%20%d%%20tolerance%%2C%%20%d%%20presence%%2C%%20%d%%20differ-informational' % (
        counts['M'], counts['K'], counts['P'], counts['F'])
    lines = ['# %s, re-run from its reproduction package' % record.get('workflow_name', 'A GARS run'), '',
             '[![re-run counts](%s)](%s)' % (badge, runs), '',
             'What was analysed: %s.' % '; '.join('%s %s (pipeline commit `%s`)' % (p['pipeline'], p['release'],
                                                                                    p['pipeline_commit']) for p in pipes),
             '', 'Re-run: `bash package/rerun.sh --out <empty folder>`', '',
             'Verify: `python3 package/verify.py --against <that folder>`', '',
             'Re-run on a fresh %s, %s, from this package and the public sources it pins by checksum '
             '(package sha256 `%s`): %s.' % (machine, dates, package_digest, compare.line(counts)), '',
             'The re-run was a pre-landing pass in a private environment (not viewable); the public workflow\'s '
             'runs ([%s](%s)) must show the same table.' % (args.workflow, runs), '']
    if unstable:
        lines += ['%d members differed between the two passes on the same machine type; each counts as differing, '
                  'with the cause "unstable between re-runs on the same machine type".' % len(unstable), '']
    for p in passes:
        lines += ['| Stage | Output | Path | Members | Exact | Presence | Other | Failed | Extra | Result |',
                  '|---|---|---|---|---|---|---|---|---|---|']
        for o in p['outputs']:
            lines.append('| %s | %s | `%s` | %s | %s | %s | %s | %s | %s | %s |' % tuple(
                o[c] for c in ('stage', 'output_type', 'output_path', 'members', 'exact', 'presence', 'other',
                               'failed', 'extra', 'result')))
        lines.append('')
        if not unstable:
            break
    lines += ['Every caveat, label and "not recorded" is in [package/PROVENANCE.md](package/PROVENANCE.md).', '']
    text = '\n'.join(lines)
    if HOME_PATH.search(text):
        raise Refusal('the landing README would hold a home path')
    out = Path(args.out)
    if out.resolve().parent != package.resolve().parent:
        raise Refusal('the landing README goes beside the package folder')
    out.write_text(text, encoding='utf-8')
    print('rerun-note: %s (%s)' % (out, compare.line(counts)))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='verb')
    p = sub.add_parser('harvest')
    p.add_argument('--gars', required=True)
    p.add_argument('--project', required=True)
    p.add_argument('--lane-commit', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--copy-large', action='store_true')
    p = sub.add_parser('render')
    p.add_argument('--harvest', required=True)
    p.add_argument('--gars-repo', required=True)
    p.add_argument('--sources', required=True)
    p.add_argument('--tolerances', required=True)
    p.add_argument('--out', required=True)
    p = sub.add_parser('rerun-note')
    p.add_argument('--package', required=True)
    p.add_argument('--artifact', action='append', required=True)
    p.add_argument('--workflow', required=True)
    p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    if args.verb is None:
        parser.print_usage(sys.stderr)
        return 2
    try:
        return {'harvest': harvest, 'render': render, 'rerun-note': rerun_note}[args.verb](args)
    except Refusal as exc:
        print('package_run refused: %s' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
