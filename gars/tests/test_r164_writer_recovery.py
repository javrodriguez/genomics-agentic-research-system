"""R-164 class 2 by principle: every recorded-state writer survives a fault at each step (0111).

One table row per public entry point that writes a recorded state or artifact file. Each row
is driven through its public interface once cleanly, then again with ONE fault injected for
ONE destination file: refusing the open-for-write, failing a write part-way, refusing the
fsync, refusing the rename into place, and (where a row names them) a helper or copy step.
The postcondition is the same for every row: the fault surfaces, the destination keeps its
prior bytes exactly (or stays absent on a first write), and no file appears anywhere in the
fixture tree. A writer added later is covered by one more row.

Faults are matched by destination, not by writer, so a writer that bypasses the atomic helper
(plain `open`, `write_text`) is still caught: its partial write lands on the destination.
"""
import argparse
import builtins
import contextlib
import errno
import io
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module, write_fixture_dataset
from test_lifecycle_executor import prepared
import configure
import executorlib as ex
import stage03_analysis as s03
import wrapperlib as wl
import test_r164_boundaries as bounds
import test_r164_collect_gates as gates
import test_r164_failure_recovery as recovery
import test_r164_params_mapping as mapping

WRAPPERS = GARS / '_system/wrappers'
RAISED = object()
STEPS = ('open', 'write', 'fsync', 'replace', 'first-write')
_modules = {}


def wrapper(directory):
    if directory not in _modules:
        source = WRAPPERS / directory / (directory.replace('-', '_') + '.py')
        _modules[directory] = module(source, 'r164_writer_' + directory.replace('-', '_'))
    return _modules[directory]


class Faulty(object):
    """A write handle whose first write lands half its data, then fails."""

    def __init__(self, handle, injector):
        self._handle, self._injector = handle, injector

    def write(self, data):
        self._handle.write(data[:len(data) // 2])
        self._handle.flush()
        self._injector.fired = True
        raise OSError(errno.ENOSPC, 'injected fault at write')

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def __getattr__(self, name):
        return getattr(self._handle, name)

    def __iter__(self):
        return iter(self._handle)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._handle.close()
        return False


class Injector(object):
    """One fault, at one step, for one destination file and its temporary siblings."""

    def __init__(self, target, step):
        self.target, self.step = Path(target), step
        self.parent = os.path.realpath(str(self.target.parent))
        self.fired = False
        self.fds = set()

    def same_folder(self, path):
        path = os.fspath(path)
        if isinstance(path, bytes):
            path = path.decode()
        return os.path.realpath(os.path.dirname(os.path.abspath(path))) == self.parent, \
            os.path.basename(path)

    def ours(self, path):
        """The destination itself or a temporary written for it (`name.tmp`, `.stem-XXXX`)."""
        if isinstance(path, int):
            return False
        here, name = self.same_folder(path)
        target = self.target.name
        return here and (name == target or name.startswith(target + '.') or
                         name.startswith('.' + target.split('.')[0] + '-'))

    def fire(self, where):
        self.fired = True
        raise OSError(errno.EIO, 'injected fault at %s of %s' % (where, self.target.name))

    def track(self, handle):
        self.fds.add(handle.fileno())
        return Faulty(handle, self) if self.step == 'write' else handle

    def patches(self):
        real_open, real_io_open = builtins.open, io.open
        real_fdopen, real_mkstemp = os.fdopen, tempfile.mkstemp
        real_fsync, real_replace, real_rename = os.fsync, os.replace, os.rename

        def opener(real):
            def open_(file, mode='r', *args, **kwargs):
                if any(c in mode for c in 'wax+') and self.ours(file):
                    if self.step == 'open':
                        self.fire('open')
                    return self.track(real(file, mode, *args, **kwargs))
                return real(file, mode, *args, **kwargs)
            return open_

        def mkstemp(*args, **kwargs):
            fd, path = real_mkstemp(*args, **kwargs)
            if self.ours(path):
                if self.step == 'open':
                    os.close(fd)
                    os.unlink(path)
                    self.fire('open')
                self.fds.add(fd)
            return fd, path

        def fdopen(fd, *args, **kwargs):
            handle = real_fdopen(fd, *args, **kwargs)
            if fd in self.fds and self.step == 'write':
                return Faulty(handle, self)
            return handle

        def fsync(fd):
            if self.step == 'fsync' and fd in self.fds:
                self.fire('fsync')
            return real_fsync(fd)

        def mover(real):
            def move(source, destination, *args, **kwargs):
                here, name = self.same_folder(destination)
                if self.step == 'replace' and here and name == self.target.name:
                    self.fire('replace')
                return real(source, destination, *args, **kwargs)
            return move

        return [patch.object(builtins, 'open', opener(real_open)),
                patch.object(io, 'open', opener(real_io_open)),
                patch.object(tempfile, 'mkstemp', mkstemp),
                patch.object(os, 'fdopen', fdopen), patch.object(os, 'fsync', fsync),
                patch.object(os, 'replace', mover(real_replace)),
                patch.object(os, 'rename', mover(real_rename))]


def raising(injector, label):
    def fault(*args, **kwargs):
        injector.fire(label)
    return fault


class Writer(object):
    """A table row: `setup(test, tmp) -> (tree, call)`; `call()` drives the entry point."""

    def __init__(self, name, setup, destinations, success=None, prime=True,
                 steps=STEPS, extra=None, reads=(), creates=()):
        self.name, self.setup, self.destinations = name, setup, destinations
        self.success, self.prime, self.steps = success, prime, steps
        self.extra = extra or {}      # destination -> [(label, factory(injector) -> patch)]
        self.reads = reads            # destinations the writer reads first: no first-write
        self.creates = creates        # completed artifacts a first run writes before the fault


def files(tree):
    return sorted(str(p.relative_to(tree)) for p in tree.rglob('*')
                  if p.is_file() or p.is_symlink())


def pinned(call):
    """`call` with the pipeline checkout's `git rev-parse` answered in-process: the commit
    value is not what these rows observe, and a subprocess per fault run costs seconds."""
    real = wl.subprocess.run

    def run(argv, *args, **kwargs):
        if list(argv[:1]) == ['git'] and 'rev-parse' in argv:
            return wl.subprocess.CompletedProcess(argv, 0, b'f' * 40 + b'\n', b'')
        return real(argv, *args, **kwargs)

    def pinned_call():
        with patch.object(wl.subprocess, 'run', run):
            return call()
    return pinned_call


def invoke(call):
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            return call()
        except Exception:
            return RAISED


# -- fixtures: each returns (tree, call) ------------------------------------------------------

def stage_in(tmp):
    stage = tmp / 'stage'
    stage.mkdir()
    return stage


def params_yaml(test, tmp):
    stage = stage_in(tmp)
    return tmp, lambda: wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', 'a.csv'), ('n', 2)])


def submit_sh(test, tmp):
    (tmp / '_system').mkdir()
    (tmp / '_system/gars-env.sh').write_text(':\n')
    (tmp / '_config').mkdir()
    (tmp / '_config/executor.yaml').write_text('name: local\n')
    stage = stage_in(tmp)
    return tmp, lambda: wl.write_submit_sh(stage, tmp, {}, 'fixture', 'rnaseq_bulk', 'true')


def reproducibility(test, tmp):
    stage, sheet, cfg = prepared(tmp)
    return tmp, pinned(lambda: wl.write_reproducibility(stage, 'rnaseq_bulk', tmp,
                                                        {'samplesheet': sheet, 'config': cfg}, []))


def output_index(test, tmp):
    stage = stage_in(tmp)
    (stage / 'counts.tsv').write_text('gene\tA\ng1\t1\n')
    (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\ncounts_gene\tnative\tcounts.tsv\n')
    return tmp, lambda: wl.complete_output_index(stage)


def status(test, tmp):
    stage = stage_in(tmp)
    return tmp, lambda: wl.write_status(stage, 'CREATED')


def manifest(test, tmp):
    stage = prepared(tmp)[0]
    (tmp / '_config/executor.yaml').write_text('name: local\n')
    with patch.object(ex, '_submit_once', return_value=('42', None)):
        test.assertEqual(ex.submit(tmp, stage / 'submit.sh')[0], '42')
    return tmp, lambda: wl.complete_manifest(stage, 'none', 'COMPLETE')


def harvest(test, tmp):
    built = tmp / 'built'
    (built / 'part').mkdir(parents=True)
    (built / 'part/data.bin').write_bytes(b'index\n')
    cache = tmp / 'cache'
    test.assertEqual(wl.harvest_cache(str(cache), 'bwa', built, ['first']), 'populated')

    def call():
        # The second aligner's index is published beside the first; PROVENANCE is shared.
        shutil.rmtree(str(cache / 'bowtie2'), ignore_errors=True)
        return wl.harvest_cache(str(cache), 'bowtie2', built, ['pipeline: fixture', 'second'])
    return tmp, call


def submission_record(test, tmp):
    records = tmp / '.gars_submissions'
    records.mkdir()
    return tmp, lambda: ex._save_record(records / ('a' * 64 + '.json'),
                                        {'job_id': '1', 'state': 'PENDING'})


def failure_record(test, tmp):
    stage = stage_in(tmp)
    return tmp, lambda: ex.record_failure(stage, {'job_id': '7'}, 'FAILED:EXIT_1', 'detail')


def dataset_record(test, tmp):
    (tmp / '00_data/rnaseq_bulk/raw').mkdir(parents=True)
    return tmp, lambda: write_fixture_dataset(tmp)


def check(directory):
    def setup(test, tmp):
        mod = wrapper(directory)
        project = tmp / 'project'
        project.mkdir()
        stage = project / '02_bioinformatics' / mod.ASSAY / mod.SUBSTAGE
        args = argparse.Namespace(project=str(project), counts=None, design=None, h5ad=None)

        def call():
            with patch.object(mod, 'run_checks',
                              return_value=([], {}, {'substage': stage, 'inputs': []})):
                return mod.cmd_check(args)
        return tmp, call
    return setup


def nfcore_prepare(directory):
    def setup(test, tmp):
        mod = wrapper(directory)
        project = tmp / 'project'
        (project / '_config').mkdir(parents=True)
        (project / '_config/executor.yaml').write_text('name: local\n')
        (project / '01_samplesheets').mkdir()
        paths = mod.paths_for(project)
        paths['samplesheet'].write_text('sample,fastq_1\nS1,a\n')
        paths['config'].write_text('fixture: declared\n')
        paths['checkout'] = tmp / 'pipeline'
        paths['checkout'].mkdir()
        cfg = {'compute.work_dir': str(tmp / 'work')}
        params = [('input', str(paths['samplesheet'])), ('outdir', str(tmp / 'out'))]
        args = argparse.Namespace(project=str(project))

        def call():
            with patch.object(mod, 'run_checks', return_value=([], cfg, dict(paths))), \
                    patch.object(mod, 'build_params', return_value=params):
                return mod.cmd_prepare(args)
        return tmp, pinned(call)
    return setup


def downstream_prepare(directory):
    def setup(test, tmp):
        mod = wrapper(directory)
        (tmp / '_config').mkdir()
        (tmp / '01_samplesheets').mkdir()
        config = tmp / '_config' / (mod.ASSAY + '.yaml')
        config.write_text('fixture: declared\n')
        stage = tmp / '02_bioinformatics' / mod.ASSAY / mod.SUBSTAGE
        sheet = tmp / '01_samplesheets/sheet.csv'
        sheet.write_text('sample,spaceranger_dir\ns1,a\n')
        paths = {'substage': stage, 'config': config, 'samplesheet': sheet}
        if directory == 'rnaseq-de':
            counts, design = tmp / 'counts.tsv', tmp / '01_samplesheets/rnaseq_bulk_design.csv'
            counts.write_text('gene_id\tA\n')
            design.write_text('sample_id,condition\nA,x\n')
            cfg = {'de.formula': '~ condition', 'de.contrast': 'condition,b,a'}
            args = {'counts': str(counts), 'design': str(design)}
        elif directory == 'scrna-qc-cluster':
            h5ad = tmp / 'combined.h5ad'
            h5ad.write_bytes(b'h5')
            cfg = {'qc.min_genes': '1', 'qc.min_cells': '2', 'qc.max_mito_pct': '3',
                   'n_hvg': '4', 'cluster_resolution': '0.5'}
            args = {'h5ad': str(h5ad)}
        else:
            h5ad = tmp / 's1.h5ad'
            h5ad.write_bytes(b'one')
            cfg, args = {}, {'h5ad': str(tmp)}
            paths['inputs'] = [('s1', h5ad)]
        namespace = argparse.Namespace(project=str(tmp), **args)

        def call():
            with patch.object(mod, 'run_checks', return_value=([], cfg, dict(paths))):
                return mod.cmd_prepare(namespace)
        return tmp, pinned(call)
    return setup


def collect(case_class, complete=None):
    def setup(test, tmp):
        case = case_class('setUp')
        case.setUp()
        test.addCleanup(case.tearDown)
        if complete:
            complete(case)
        return case.project.parent, lambda: case.collect()[0]
    return setup


def spatial_counts(case):
    case.gate({'s1': {'n_obs': 3, 'n_clusters': 1}, 's2': {'n_obs': 5, 'n_clusters': 2}},
              [('s1', '0', 3), ('s2', '0', 2), ('s2', '1', 3)])


def configure_apply(test, tmp):
    case = mapping.ConfigureApplyMappingTests('setUp')
    case.setUp()
    test.addCleanup(case.tearDown)
    (case.project / '_config/scrnaseq.yaml').write_text(
        'reference:\n  fasta: <REQUIRED>\n  gtf: <REQUIRED>\nprotocol: <REQUIRED>\n'
        'aligner: simpleaf\n')
    argv = ['--workspace', str(case.root), 'apply', '--project', str(case.project),
            '--assay', 'scrnaseq', '--genome', 'G1', '--protocol', '10XV3', '--aligner', 'star']
    return case.root, lambda: configure.main(argv)


def adapt_counts(test, tmp):
    adapter = module(GARS / '_system/adapt_counts.py', 'r164_writer_adapt_counts')
    counts = tmp / 'native.tsv'
    counts.write_text('gene_id\tgene_name\tA\tB\ng1\tn1\t1.0\t2\n')
    return tmp, lambda: adapter.main(['--counts', str(counts), '--out', str(tmp / 'adapted')])


def analysis_plan(test, tmp):
    (tmp / 'project').mkdir()
    return tmp, lambda: s03.main(['create', '--project', str(tmp / 'project'),
                                  '--slug', 'fixture'])


def stage01(test, tmp):
    case = recovery.CallSiteRecoveryTests('setUp')
    case.setUp()
    test.addCleanup(case.tearDown)
    data = case.stage01_project()
    return case.root, lambda: case.stage01(data, 'reverse', 'B')


def finalize(first_run):
    def setup(test, tmp):
        case = recovery.CallSiteRecoveryTests('setUp')
        case.setUp()
        test.addCleanup(case.tearDown)
        (case.root / '_config').mkdir()
        (case.root / 'CONTEXT.md').write_text('# {{project_title}}\n')
        (case.root / 'HISTORY.md').write_text('v {{template_version}}\n')
        case.link('K1')
        case.link('K2')
        if not first_run:
            test.assertEqual(case.finalize(), 0)
        return case.root, case.finalize
    return setup


def hooks(test, tmp):
    installer = module(GARS / '_system/hooks/install.py', 'r164_writer_hooks_install')
    folder = tmp / 'hooks'
    folder.mkdir()
    (folder / 'pre-push').write_text('#!/bin/sh\necho the user\'s own hook\n')
    (folder / 'pre-push').chmod(0o755)
    return tmp, lambda: installer.install_hook(folder, 'pre-push')


def half_copy(injector):
    def copyfile(source, destination, *args, **kwargs):
        with open(str(destination), 'wb') as fh:
            fh.write(Path(source).read_bytes()[:10])
        injector.fire('copy')
    return patch.object(shutil, 'copyfile', copyfile)


def helper(target, name):
    return lambda injector: patch.object(target, name, raising(injector, name))


PREPARED = ['stage/params.yaml', 'stage/submit.sh', 'stage/reproducibility/manifest.json',
            'stage/reproducibility/commands.sh']
NFCORE = ('nfcore-atacseq-wrapper', 'nfcore-chipseq-wrapper', 'nfcore-cutandrun-wrapper',
          'nfcore-methylseq-wrapper', 'nfcore-rnaseq-wrapper', 'nfcore-scrnaseq-wrapper',
          'nfcore-spatialvi-wrapper')
CHECK_WRITERS = NFCORE + ('scrna-qc-cluster', 'spatial-cluster-count')
SCRIPTS = {'rnaseq-de': 'run_de.py', 'scrna-qc-cluster': 'run_scrna.py',
           'spatial-cluster-count': 'count_clusters.py'}
COLLECTS = [('nfcore-atacseq-wrapper', gates.AtacseqCollectGateTests, gates.AtacseqCollectGateTests.complete),
            ('nfcore-chipseq-wrapper', gates.ChipseqCollectGateTests, gates.ChipseqCollectGateTests.complete),
            ('nfcore-cutandrun-wrapper', gates.CutandrunCollectGateTests, gates.CutandrunCollectGateTests.complete),
            ('nfcore-methylseq-wrapper', gates.MethylseqCollectGateTests, gates.MethylseqCollectGateTests.complete),
            ('nfcore-rnaseq-wrapper', gates.RnaseqCollectGateTests, gates.RnaseqCollectGateTests.complete),
            ('nfcore-scrnaseq-wrapper', bounds.ScrnaseqCollectBoundaryTests, None),
            ('nfcore-spatialvi-wrapper', bounds.SpatialviCollectBoundaryTests, None),
            ('rnaseq-de', gates.RnaseqDeCollectGateTests, gates.RnaseqDeCollectGateTests.complete),
            ('scrna-qc-cluster', gates.ScrnaQcClusterCollectGateTests,
             gates.ScrnaQcClusterCollectGateTests.complete),
            ('spatial-cluster-count', bounds.SpatialClusterCountBoundaryTests, spatial_counts)]


def stage_of(directory, root='project'):
    mod = wrapper(directory)
    return '%s/02_bioinformatics/%s/%s' % (root, mod.ASSAY, mod.SUBSTAGE)


def rows():
    table = [
        Writer('wrapperlib.write_params_yaml', params_yaml, ['stage/params.yaml']),
        Writer('wrapperlib.write_submit_sh', submit_sh, ['stage/submit.sh']),
        Writer('wrapperlib.write_reproducibility', reproducibility,
               [p.replace('stage/', '02_bioinformatics/rnaseq_bulk/01_fixture/')
                for p in PREPARED[1:]],
               extra={'02_bioinformatics/rnaseq_bulk/01_fixture/reproducibility/manifest.json':
                      [('helper:prepare_manifest_facts',
                        helper(wl, 'prepare_manifest_facts'))]},
               reads=['02_bioinformatics/rnaseq_bulk/01_fixture/submit.sh']),
        Writer('wrapperlib.complete_output_index', output_index, ['stage/OUTPUTS.tsv'],
               success=RAISED, reads=['stage/OUTPUTS.tsv']),
        Writer('wrapperlib.write_status', status, ['stage/STATUS'], success='CREATED'),
        Writer('wrapperlib.complete_manifest', manifest,
               ['02_bioinformatics/rnaseq_bulk/01_fixture/reproducibility/manifest.json'],
               success=RAISED,
               reads=['02_bioinformatics/rnaseq_bulk/01_fixture/reproducibility/manifest.json']),
        Writer('wrapperlib.harvest_cache', harvest, ['cache/PROVENANCE'], success='populated'),
        Writer('executorlib._save_record', submission_record,
               ['.gars_submissions/' + 'a' * 64 + '.json']),
        Writer('executorlib.record_failure', failure_record,
               ['stage/logs/failure-7.log', 'stage/logs/failure-7.class']),
        Writer('stage00_register.write_dataset_record', dataset_record, ['00_data/dataset.tsv'],
               prime=False, steps=('open', 'write', 'fsync', 'replace')),
        Writer('stage00_register finalize (re-run)', finalize(False),
               ['00_data/rnaseq_bulk/files.csv', 'CONTEXT.md', 'HISTORY.md'], success=0,
               reads=['CONTEXT.md', 'HISTORY.md']),
        Writer('stage00_register finalize (first run)', finalize(True),
               ['00_data/rnaseq_bulk/samples.csv'], success=0, prime=False,
               steps=('open', 'write', 'fsync', 'replace'),
               creates=['00_data/rnaseq_bulk/files.csv']),
        Writer('stage01_samplesheet main', stage01,
               ['01_samplesheets/rnaseq_bulk_samplesheet.csv',
                '01_samplesheets/rnaseq_bulk_design.csv',
                '01_samplesheets/rnaseq_bulk_design_check.json'], success=0),
        Writer('stage03_analysis create', analysis_plan,
               ['project/%s/01_fixture/PLAN.md' % s03.stage_root(Path('project')).name],
               success=0, prime=False, steps=('open', 'write', 'fsync', 'replace')),
        Writer('configure.py apply', configure_apply, ['project/_config/scrnaseq.yaml'],
               success=0, reads=['project/_config/scrnaseq.yaml']),
        Writer('adapt_counts.py main', adapt_counts,
               ['adapted/counts_gene.tsv', 'adapted/gene_id_to_name.tsv'], success=0),
        Writer('hooks/install.py install_hook', hooks, ['hooks/pre-push'], prime=False,
               steps=('open',),
               extra={'hooks/pre-push': [('copy', half_copy),
                                         ('chmod', helper(Path, 'chmod'))]}),
    ]
    for directory in CHECK_WRITERS:
        table.append(Writer('%s check' % directory, check(directory),
                            [stage_of(directory) + '/preflight/check_result.json'], success=0))
    for directory in NFCORE:
        stage = stage_of(directory)
        table.append(Writer('%s prepare' % directory, nfcore_prepare(directory),
                            [p.replace('stage', stage, 1) for p in PREPARED], success=0,
                            extra={stage + '/reproducibility/manifest.json': [
                                ('helper:write_reproducibility',
                                 helper(wl, 'write_reproducibility'))]}))
    for directory, script in sorted(SCRIPTS.items()):
        stage = stage_of(directory, root='.').lstrip('./')
        table.append(Writer('%s prepare' % directory, downstream_prepare(directory),
                            ['%s/scripts/%s' % (stage, script)] +
                            [p.replace('stage', stage, 1) for p in PREPARED[1:]], success=0))
    for directory, case_class, complete in COLLECTS:
        table.append(Writer('%s collect' % directory, collect(case_class, complete),
                            [stage_of(directory) + '/OUTPUTS.tsv'], success=0))
    return table


WRITERS = rows()


class WriterRecoveryTests(unittest.TestCase):
    """Generated below: one test per row, one subtest per destination and step."""

    def fixture(self, writer):
        tmp = Path(tempfile.mkdtemp(prefix='gars-writer-')).resolve()
        self.addCleanup(shutil.rmtree, str(tmp), True)
        tree, call = writer.setup(self, tmp)
        if writer.prime:
            outcome = invoke(call)
            self.assertIsNot(outcome, RAISED, 'the clean run must succeed')
            if writer.success is not RAISED:
                self.assertEqual(outcome, writer.success)
        return tree, call

    def run_fault(self, writer, tree, call, destination, step, fault=None):
        target = tree / destination
        kept = None
        if step == 'first-write':
            kept = (target.read_bytes(), target.stat().st_mode)
            target.unlink()
        before = target.read_bytes() if target.exists() else None
        listing = [f for f in files(tree) if f not in writer.creates]
        injector = Injector(target, 'write' if step == 'first-write' else step)
        with contextlib.ExitStack() as stack:
            for active in (injector.patches() if fault is None else [fault(injector)]):
                stack.enter_context(active)
            outcome = invoke(call)
        self.assertTrue(injector.fired, 'the fault was never reached')
        self.assertTrue(outcome is RAISED or outcome != writer.success,
                        'the fault did not surface: %r' % (outcome,))
        self.assertEqual(target.read_bytes() if target.exists() else None, before)
        self.assertEqual([f for f in files(tree) if f not in writer.creates], listing)
        if kept is not None:
            target.write_bytes(kept[0])
            target.chmod(kept[1])

    def check_writer(self, writer):
        """A primed row shares one fixture: a correctly handled fault leaves it as it was.
        An unprimed row (a first write, or a destination that moves) gets one per run."""
        shared = self.fixture(writer) if writer.prime else None
        runs = [(d, s, None) for d in writer.destinations for s in writer.steps
                if s != 'first-write' or (writer.prime and d not in writer.reads)]
        runs = ([r for r in runs if r[1] != 'first-write'] +
                [(d, label, fault) for d in writer.destinations
                 for label, fault in writer.extra.get(d, ())] +
                [r for r in runs if r[1] == 'first-write'])
        for destination, step, fault in runs:
            with self.subTest(file=destination, step=step):
                tree, call = shared or self.fixture(writer)
                self.run_fault(writer, tree, call, destination, step, fault)

    def test_the_table_names_every_wrapper(self):
        on_disk = sorted(p.name for p in WRAPPERS.iterdir() if (p / 'SKILL.md').is_file())
        for verb, expected in (('prepare', on_disk), ('collect', on_disk),
                               ('check', [d for d in on_disk if d != 'rnaseq-de'])):
            with self.subTest(verb=verb):
                named = sorted(w.name.rsplit(' ', 1)[0] for w in WRITERS
                               if w.name.endswith(' ' + verb) and w.name.split(' ')[0] in on_disk)
                self.assertEqual(named, expected)


def _slug(name):
    return ''.join(c if c.isalnum() else '_' for c in name.lower()).strip('_')


for _writer in WRITERS:
    setattr(WriterRecoveryTests, 'test_' + _slug(_writer.name),
            (lambda w: lambda self: self.check_writer(w))(_writer))


if __name__ == '__main__':
    unittest.main(verbosity=2)
