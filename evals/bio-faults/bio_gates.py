"""Read-only case gates, driven on disposable mapped project copies."""
import contextlib
import csv
import datetime
import importlib.util
import io
import json
import shutil
import sys
import tempfile
from functools import partial
from unittest.mock import patch
from pathlib import Path
from types import SimpleNamespace
from bio_common import REPO, read_json, sha256
from bio_generate_base import write_json, LAYOUT

SYSTEM = REPO / 'gars/_system'


def load(relative, name):
    previous = list(sys.path)
    try:
        sys.path.insert(0, str(SYSTEM))
        spec = importlib.util.spec_from_file_location(name, str(SYSTEM / relative))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = previous


stage01 = load('stage01_samplesheet.py', '_bio_stage01')
stage03 = load('stage03_analysis.py', '_bio_stage03')
de = load('wrappers/rnaseq-de/rnaseq_de.py', '_bio_de')
rna = load('wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py', '_bio_rna')
atac = load('wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py', '_bio_atac')
renderer = load('claims/render_report.py', '_bio_renderer')
emitter = load('claims/emit_report.py', '_bio_emitter')
wl = de.wl
GATE_NAMES = ('stage01_design', 'catalogue_integrity', 'catalogue_probabilities',
              'group_rep_presence', 'count_matrix_header', 'de_identifiers',
              'stage03_verify', 'catalogue_evidence', 'render_report')


def put(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def captured(function, *args, **kwargs):
    output = io.StringIO()
    previous = list(sys.path)
    sys.path.insert(0, str(SYSTEM))
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        try:
            result = function(*args, **kwargs)
        except SystemExit as exc:
            result = exc.code
        finally:
            sys.path[:] = previous
    return result, output.getvalue()


def mapped_project(base, root, assay):
    data = root / '00_data' / assay
    data.mkdir(parents=True)
    shutil.copyfile(str(base / 'samples.csv'), str(data / 'samples.csv'))
    shutil.copytree(str(base / 'raw'), str(data / 'raw'))
    files = (base / 'files.csv').read_text().replace('2-data/raw/', '00_data/' + assay + '/raw/')
    put(data / 'files.csv', files)
    put(root / '_config' / (assay + '.yaml'), (base / 'config.yaml').read_text())
    return data


def wrapper_scaffold(base, root, assay, module):
    stage = root / '02_bioinformatics' / module.ASSAY / module.SUBSTAGE
    put(root / '_config' / (module.ASSAY + '.yaml'), (base / 'config.yaml').read_text())
    put(root / '01_samplesheets' / (module.ASSAY + '_design.csv'), (base / 'samples.csv').read_text())
    with (base / 'samples.csv').open() as handle:
        samples = list(csv.DictReader(handle))
    sheet = 'sample,fastq_1,fastq_2,replicate\n' + ''.join(
        '%s,x,,%s\n' % (s['group'] if module is atac else s['sample_id'], s['replicate']) for s in samples)
    put(root / '01_samplesheets' / (module.ASSAY + '_samplesheet.csv'), sheet)
    put(stage / 'run/.gars_run_complete', 'complete\n')
    (stage / 'reproducibility').mkdir(parents=True)
    manifest = {
        'wrapper': module.SUBSTAGE.split('_', 1)[-1],
        'config_sha256': sha256((root / '_config' / (module.ASSAY + '.yaml')).read_bytes()),
        'inputs': {'config': str((root / '_config' / (module.ASSAY + '.yaml')).resolve())},
        'key_formula': 'downstream-v1', 'params': {}}
    key = wl.input_key(stage, manifest)
    manifest['idempotency_key'] = key
    write_json(stage / 'reproducibility/manifest.json', manifest)
    put(stage / 'submit.sh', '# idempotency_key=' + key + '\n')
    put(root / '_config/executor.yaml', 'name: local\n')
    submissions = wl.ex._records(root)
    submissions.mkdir()
    write_json(submissions / (key + '.json'), {'idempotency_key': key,
        'script': str((stage / 'submit.sh').resolve()), 'state': 'COMPLETED',
        'executor': 'local', 'job_id': 'content-check'})
    jobs = wl.ex._local_jobs_dir(root)
    jobs.mkdir()
    put(stage / 'content.exit', '0\n')
    write_json(jobs / 'content-check.json', {'script': str((stage / 'submit.sh').resolve()),
        'exit_file': str((stage / 'content.exit').resolve())})
    if module is de:
        for name in ('de_results.csv', 'normalized_counts.csv'):
            put(stage / 'run/tables' / name, (base / name).read_text())
        for name in ('pca.png', 'volcano.png', 'ma_plot.png'):
            put(stage / 'run/figures' / name, 'content check only\n')
        put(stage / 'run/report.md', 'Analysis summary\n')
        for name in ('counts_gene.tsv', 'gene_id_to_name.tsv'):
            put(stage / 'adapted' / name, (base / 'counts.tsv').read_text())
    elif module is rna:
        for name in ('salmon.merged.gene_counts_length_scaled.tsv',
                     'salmon.merged.transcript_counts.tsv', 'salmon.merged.gene_tpm.tsv'):
            put(stage / 'run/results/star_salmon' / name, (base / 'counts.tsv').read_text())
        put(stage / 'run/results/star_salmon/aligned.sorted.bam', 'content check only\n')
        put(stage / 'run/results/multiqc/star_salmon/multiqc_report.html', 'QC\n')
    else:
        prefix = stage / 'run/results/bwa/merged_library'
        put(prefix / 'macs2/narrow_peak/regions.narrowPeak', 'chr1\t0\t100\n')
        put(prefix / 'macs2/narrow_peak/consensus/regions.bed', 'chr1\t0\t100\n')
        put(prefix / 'macs2/narrow_peak/consensus/regions.featureCounts.txt', (base / 'counts.tsv').read_text())
        put(prefix / 'bigwig/coverage.bigWig', 'content check only\n')
        put(prefix / 'aligned.sorted.bam', 'content check only\n')
        put(stage / 'run/results/multiqc/narrow_peak/multiqc_report.html', 'QC\n')
    return captured(module.cmd_collect, SimpleNamespace(project=root, model='none', counts_from=None))[0] == 0


def verify_data(base):
    """Drive real verify with historical approval and synthetic execution data.

    Only the disposable store's actor/path binding and clock are adapted. The
    supplied hash, timestamp and expiry are preserved. No approval command runs.
    Execution sidecars describe the content-check scaffold, never a real job.
    """
    record = read_json(base / 'approval.json')
    if record.get('actor') != 'human':
        return False
    instant = stage03.utc_instant(read_json(base / 'manifest.json')['params']['execution_finished_at'])
    with tempfile.TemporaryDirectory(prefix='bv-') as folder:
        root = Path(folder)
        workspace = root / 'w'
        project = workspace / 'projects/p'
        adir = project / '03_custom_analysis/01_analysis'
        shutil.copytree(str(base), str(adir))
        put(workspace / '_references/artifact_types.md', (REPO / 'gars/_references/artifact_types.md').read_text())
        store = stage03.approval_store(workspace)
        store.mkdir(mode=0o700)
        supplied = dict(record, actor=stage03.LAUNCH_ACTOR, plan_path=str((adir / 'PLAN.md').resolve()))
        approval = stage03.approval_record_path(adir / 'PLAN.md', workspace)
        write_json(approval, supplied)
        approval.chmod(0o600)
        put(adir / 'run/.gars_run_complete', 'complete\n')
        put(adir / 'scripts/content.sh', 'true\n')
        put(adir / 'run/content.sh', 'true\n')
        entry = {'executor': 'local', 'job_id': 'content-check'}
        for kind, relative in (('script', 'scripts/content.sh'), ('launcher', 'run/content.sh')):
            entry[kind] = str((adir / relative).resolve())
            entry[kind + '_sha256'] = sha256((adir / relative).read_bytes())
        put(adir / wl.ex.ANALYSIS_SUBMISSIONS, json.dumps(entry) + '\n')
        jobs = wl.ex._local_jobs_dir(project)
        jobs.mkdir()
        put(adir / 'content.exit', '0\n')
        write_json(jobs / 'content-check.json', {'script': entry['launcher'],
                   'exit_file': str((adir / 'content.exit').resolve())})
        class HistoricalClock(datetime.datetime):
            @classmethod
            def now(cls, tz=None):
                return instant if tz else instant.replace(tzinfo=None)
        clock_module = SimpleNamespace(datetime=HistoricalClock, timezone=datetime.timezone,
                                       timedelta=datetime.timedelta)
        with patch.object(stage03, 'datetime', clock_module):
            code, unused = captured(stage03.cmd_verify,
                SimpleNamespace(project=project, analysis='01_analysis', model='none'), workspace)
        return code == 0


def check(callback):
    """Malformed data is a named refusal, never an unrecorded gate exception."""
    try:
        return bool(callback())
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        return False


def group_rep_presence(base, root):
    with (base / 'samples.csv').open() as handle:
        samples = list(csv.DictReader(handle))
    sheet = root / 'sheet.csv'
    put(sheet, 'sample,x,y,replicate\n' + ''.join('%s,,,%s\n' % (s['group'], s['replicate']) for s in samples))
    tokens = wl.samplesheet_group_rep_tokens(sheet)
    header = (base / 'counts.tsv').read_text().splitlines()[0].split('\t')
    identifiers = (base / 'de_results.csv').read_text().splitlines()[0].split(',')
    normalized = (base / 'normalized_counts.csv').read_text().splitlines()[0].split(',')
    return all(t in header and t in identifiers and t in normalized for t in tokens)


def evidence_gate(base, root, assay):
    evidence = root / 'e'
    for source, destination in LAYOUT.items():
        target = evidence / destination.format(assay=assay)
        target.parent.mkdir(parents=True, exist_ok=True)
        if (base / source).is_dir():
            shutil.copytree(str(base / source), str(target))
        else:
            shutil.copyfile(str(base / source), str(target))
    code, unused = captured(emitter.main, ['--snapshot', str(base / 'snapshot.json'),
        '--manifest', str(base / 'manifest.json'), '--project', str(evidence), '--out', str(root / 'emitted.md')],
        transport=lambda unused: (_ for _ in ()).throw(ValueError('network unavailable')))
    return code == 0


def run_gates(base, assay):
    base = Path(base)
    results = {}
    with tempfile.TemporaryDirectory(prefix='bg-') as folder:
        root = Path(folder)
        project = root / 'p'
        try:
            mapped_project(base, project, assay)
        except (OSError, ValueError, KeyError, TypeError):
            pass  # The real stage check below names the absent/unreadable input.
        code, unused = captured(stage01.main, ['--project', str(project), '--check'])
        results['stage01_design'] = code == 0
        with patch.object(stage01.integrity, 'check_many',
                          partial(stage01.integrity.check_many, log=io.StringIO())):
            code, unused = captured(stage01.main, ['--project', str(project), '--check', '--verify-integrity', 'full'])
        results['catalogue_integrity'] = code == 0
        results['catalogue_probabilities'] = check(lambda: not de.check_table(base / 'de_results.csv'))
        results['group_rep_presence'] = check(lambda: group_rep_presence(base, root))
        results['count_matrix_header'] = check(lambda: wrapper_scaffold(base, root / 'w', assay, atac if assay == 'atacseq_bulk' else rna))
        results['de_identifiers'] = check(lambda: wrapper_scaffold(base, root / 'd', assay, de))
        results['stage03_verify'] = check(lambda: verify_data(base))
        results['catalogue_evidence'] = check(lambda: evidence_gate(base, root, assay))
        try:
            report = renderer.render(read_json(base / 'snapshot.json'), read_json(base / 'manifest.json'),
                                     (SYSTEM / 'claims/report_template.md').read_text())
            results['render_report'] = True
        except (OSError, ValueError, KeyError, TypeError, IndexError):
            report = None
            results['render_report'] = False
    return results, report
