"""R-164 class 4: every table keyed by aligner, assay, genome or backend returns its own row (0087).

Each fixture carries at least two keys whose content differs, and the test asserts the
chosen key's content, so reading another key's entry is visible.
"""
import argparse
import contextlib
import csv
import gzip
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module
import configure
import executorlib as ex
import stage00_register as s00
import stage01_samplesheet as s01
import workspace as ws
import wrapperlib as wl
import test_r164_params_mapping as mapping
import test_stage03_execution as stage03

WRAPPERS = GARS / '_system/wrappers'

PROTOCOLS = {'simpleaf': {'10XV2': {}, '10XV3': {}},
             'star': {'10XV3': {}, 'dropseq': {}, 'smartseq': {}},
             'kallisto': {'10XV4': {}}}


def wrapper(directory):
    source = WRAPPERS / directory / (directory.replace('-', '_') + '.py')
    return module(source, 'r164_keyed_' + directory.replace('-', '_'))


class KeyedLookupTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-keyed-')
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def checkout(self, name):
        path = self.root / 'pipelines' / name
        (path / 'assets').mkdir(parents=True)
        (path / 'assets/protocols.json').write_text(json.dumps(PROTOCOLS))
        return path

    def test_scrnaseq_protocols_are_read_for_the_selected_aligner(self):
        sc = wrapper('nfcore-scrnaseq-wrapper')
        checkout = self.checkout('scrnaseq')
        for aligner, table in PROTOCOLS.items():
            with self.subTest(aligner=aligner):
                self.assertEqual(sc.supported_protocols(checkout, aligner), sorted(table))
        self.assertIsNone(sc.supported_protocols(checkout, 'cellranger'))
        self.assertIsNone(sc.supported_protocols(None, 'star'))
        self.assertIsNone(sc.supported_protocols(self.root / 'absent', 'star'))

    def test_scrnaseq_preflight_judges_protocol_against_its_own_aligner(self):
        sc = wrapper('nfcore-scrnaseq-wrapper')
        pin = ws.PIPELINES['scrnaseq'].replace('nf-core-', '')
        self.checkout(pin)
        project = self.root / 'project'
        (project / '_config').mkdir(parents=True)
        config = project / '_config/scrnaseq.yaml'
        cases = [('star', 'dropseq', False), ('star', '10XV2', True),
                 ('simpleaf', '10XV2', False), ('simpleaf', 'dropseq', True),
                 ('kallisto', '10XV4', False), ('kallisto', '10XV3', True)]
        with patch.dict(os.environ, {'GARS_PIPELINES': str(self.root / 'pipelines')}):
            for aligner, protocol, refused in cases:
                with self.subTest(aligner=aligner, protocol=protocol):
                    config.write_text('aligner: %s\nprotocol: %s\n' % (aligner, protocol))
                    fails = sc.run_checks(project)[0]
                    named = [f for f in fails if 'protocol %r' % protocol in f['detail']]
                    self.assertEqual(bool(named), refused, fails)
                    if refused:
                        self.assertIn('aligner %r' % aligner, named[0]['detail'])
                        self.assertIn('|'.join(sorted(PROTOCOLS[aligner])), named[0]['detail'])

    def test_index_parameter_is_the_selected_aligners(self):
        expected = {'nfcore-atacseq-wrapper': {'bwa': 'bwa_index', 'bowtie2': 'bowtie2_index',
                                               'chromap': 'chromap_index', 'star': 'star_index'},
                    'nfcore-chipseq-wrapper': {'bwa': 'bwa_index', 'bowtie2': 'bowtie2_index',
                                               'chromap': 'chromap_index', 'star': 'star_index'},
                    'nfcore-scrnaseq-wrapper': {'simpleaf': 'simpleaf_index',
                                                'star': 'star_index',
                                                'kallisto': 'kallisto_index'}}
        derived = self.root / 'derived'
        for aligner in ('bwa', 'bowtie2', 'chromap', 'star', 'simpleaf', 'kallisto'):
            (derived / aligner).mkdir(parents=True)
            (derived / aligner / ('%s.idx' % aligner)).write_text(aligner)
        paths = {'samplesheet': self.root / 's.csv', 'substage': self.root / 'stage'}
        cfg = {'reference.fasta': 'f.fa', 'reference.gtf': 'g.gtf', 'reference.mito_name': 'M',
               'peaks.type': 'broad', 'peaks.macs_gsize': '1', 'protocol': '10XV3',
               'reference.derived_dir': str(derived)}
        for directory, table in expected.items():
            mod = wrapper(directory)
            for aligner, param in table.items():
                with self.subTest(wrapper=directory, aligner=aligner):
                    params = mod.build_params(dict(cfg, aligner=aligner), paths)
                    indices = [p for p in params if p[0].endswith('_index')]
                    self.assertEqual(indices, [(param, str(derived / aligner))])

    def test_design_columns_and_input_kind_by_assay(self):
        base = ['sample_id', 'condition', 'group', 'replicate']
        self.assertEqual(ws.design_columns('chipseq_bulk'), base + ['antibody', 'control'])
        self.assertEqual(ws.design_columns('cutandrun'), base + ['control'])
        for assay in ('rnaseq_bulk', 'atacseq_bulk', 'methylseq', 'scrnaseq', 'spatialvi'):
            self.assertEqual(ws.design_columns(assay), base)
        self.assertEqual(ws.files_header('spatialvi'), ['sample_id', 'spaceranger_dir'])
        self.assertEqual(ws.files_header('rnaseq_bulk'), ['sample_id', 'lane', 'fastq_1', 'fastq_2'])

    def test_pipeline_checkout_by_assay(self):
        stems = {'rnaseq_bulk': 'rnaseq', 'atacseq_bulk': 'atacseq', 'chipseq_bulk': 'chipseq',
                 'cutandrun': 'cutandrun', 'methylseq': 'methylseq', 'scrnaseq': 'scrnaseq',
                 'spatialvi': 'spatialvi'}
        self.assertEqual(set(ws.PIPELINES), set(stems))
        seen = set()
        with patch.dict(os.environ, {'GARS_PIPELINES': str(self.root)}):
            for assay, stem in stems.items():
                with self.subTest(assay=assay):
                    checkout, version = wl.pipeline_checkout(assay)
                    self.assertEqual(checkout.parent, self.root)
                    self.assertEqual(checkout.name, '%s-%s' % (stem, version))
                    self.assertEqual(ws.PIPELINES[assay], 'nf-core-%s-%s' % (stem, version))
                    seen.add(checkout)
        self.assertEqual(len(seen), len(stems))

    def test_legacy_parser_export_follows_the_assay(self):
        legacy = {'atacseq_bulk', 'chipseq_bulk', 'cutandrun', 'methylseq'}
        for assay in sorted(ws.PIPELINES):
            with self.subTest(assay=assay):
                stage = self.root / assay
                stage.mkdir()
                wl.write_submit_sh(stage, self.root, {}, 'fixture', assay, 'true')
                script = (stage / 'submit.sh').read_text()
                self.assertEqual('export NXF_SYNTAX_PARSER=v1\n' in script, assay in legacy)

    def test_reference_evidence_uses_the_named_genome_row(self):
        files = {}
        for name, data in (('a.fa', b'>a\nAAAA\n'), ('a.gtf', b'a\tgtf\n'),
                           ('b.fa', b'>b\nCCCC\n'), ('b.gtf', b'b\tgtf\n')):
            files[name] = self.root / name
            files[name].write_bytes(data)
        rows = [{'id': 'genome-a', 'build': 'A1', 'annotation_release': 'ra',
                 'fasta': str(files['a.fa']), 'gtf': str(files['a.gtf']),
                 'fasta_sha256': wl.sha256(files['a.fa']), 'gtf_sha256': 'f' * 64},
                {'id': 'genome-b', 'build': 'B2', 'annotation_release': 'rb',
                 'fasta': str(files['b.fa']), 'gtf': str(files['b.gtf']),
                 'fasta_sha256': wl.sha256(files['b.fa']), 'gtf_sha256': wl.sha256(files['b.gtf'])}]
        with patch.object(configure, 'read_genomes', return_value=(rows, None)):
            evidence, mismatches = wl.reference_evidence(
                {'reference.fasta': str(files['b.fa']), 'reference.gtf': str(files['b.gtf'])})
            self.assertEqual(mismatches, [])
            self.assertEqual((evidence['id'], evidence['build'], evidence['annotation_release'],
                              evidence['comparison']), ('genome-b', 'B2', 'rb', 'matched'))
            self.assertEqual(evidence['observed'], {'fasta_sha256': wl.sha256(files['b.fa']),
                                                    'gtf_sha256': wl.sha256(files['b.gtf'])})
            evidence, mismatches = wl.reference_evidence(
                {'reference.fasta': str(files['a.fa']), 'reference.gtf': str(files['a.gtf'])})
            self.assertEqual((evidence['id'], mismatches), ('genome-a', ['gtf']))
            self.assertEqual(evidence['comparison'], 'mismatch')

    def test_executor_descriptor_by_backend(self):
        cfg = {'compute.partition': 'part9', 'compute.time': '02:00:00',
               'compute.cpus': '3', 'compute.mem': '5G'}
        slurm, local = self.root / 'slurm', self.root / 'local'
        for project in (slurm, local):
            (project / '_config').mkdir(parents=True)
        (local / '_config/executor.yaml').write_text('name: local\n')
        self.assertEqual(ex.load(slurm)['name'], 'slurm')
        self.assertEqual(ex.load(local)['name'], 'local')
        self.assertEqual(ex.nextflow_config_path(slurm), slurm / '_config/nextflow.slurm.config')
        self.assertIsNone(ex.nextflow_config_path(local))
        self.assertEqual(ex.nextflow_profile(slurm), 'apptainer')
        self.assertEqual(ex.nextflow_profile(local), '')
        slurm_lines = ex.header_lines(slurm, cfg, 'p', 'a', slurm / 'stage')
        local_lines = ex.header_lines(local, cfg, 'p', 'a', local / 'stage')
        self.assertIn('#SBATCH --partition=part9', slurm_lines)
        self.assertFalse(any(l.startswith('#SBATCH') for l in local_lines))
        self.assertIn('# compute.* stays in the record: partition=part9 time=02:00:00 '
                      'cpus=3 mem=5G', local_lines)


class Stage01FormatByAssayTests(unittest.TestCase):
    """The emitted samplesheet is the selected assay's own format, never another's."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-keyed-')
        self.project = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def fixture(self, assay, samples=None):
        samples = samples or [['sample_id', 'condition', 'group', 'replicate'],
                              ['K1', 'A', 'GA', '1'], ['K2', 'A', 'GA', '2'],
                              ['K3', 'B', 'GB', '1'], ['K4', 'B', 'GB', '2']]
        data = self.project / '00_data' / assay
        (data / 'raw').mkdir(parents=True)
        (self.project / '_config').mkdir(exist_ok=True)
        (self.project / '_config' / (assay + '.yaml')).write_text(
            'strandedness: reverse\nunit_of_replication: sample\nreference_release: synthetic-v1\n')
        with (data / 'samples.csv').open('w', newline='') as fh:
            csv.writer(fh).writerows(samples)
        with (data / 'files.csv').open('w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['sample_id', 'lane', 'fastq_1', 'fastq_2'])
            for sample in [row[0] for row in samples[1:]]:
                raw = data / 'raw' / ('%s_R1.fastq' % sample)
                raw.write_text('@synthetic\nACGT\n+\nIIII\n')
                writer.writerow([sample, '1', str(raw.relative_to(self.project)), ''])

    def emitted(self, assay, samples=None):
        self.fixture(assay, samples)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = s01.main(['--project', str(self.project)])
        self.assertEqual(code, 0, out.getvalue())
        sheet = self.project / '01_samplesheets' / ('%s_samplesheet.csv' % assay)
        rows = list(csv.reader(sheet.read_text().splitlines()))
        keep = [i for i, name in enumerate(rows[0]) if name not in ('fastq_1', 'fastq_2')]
        return rows[0], [[row[i] for i in keep] for row in rows[1:]]

    def test_rnaseq_sheet_carries_strandedness_and_sample_ids(self):
        header, rows = self.emitted('rnaseq_bulk')
        self.assertEqual(header, ['sample', 'fastq_1', 'fastq_2', 'strandedness'])
        self.assertEqual(rows, [['K1', 'reverse'], ['K2', 'reverse'], ['K3', 'reverse'],
                                ['K4', 'reverse']])

    def test_methylseq_sheet_has_no_rna_column(self):
        header, rows = self.emitted('methylseq')
        self.assertEqual(header, ['sample', 'fastq_1', 'fastq_2'])
        self.assertEqual(rows, [['K1'], ['K2'], ['K3'], ['K4']])

    def test_atacseq_sheet_names_the_group_and_replicate(self):
        header, rows = self.emitted('atacseq_bulk')
        self.assertEqual(header, ['sample', 'fastq_1', 'fastq_2', 'replicate'])
        self.assertEqual(rows, [['GA', '1'], ['GA', '2'], ['GB', '1'], ['GB', '2']])


    def test_chipseq_control_columns_are_the_controls_group_and_replicate(self):
        # Controls are crossed (IP rep 1 -> input rep 2), so a row's own replicate, its
        # control's replicate, its group and its control's group are all distinguishable.
        header, rows = self.emitted('chipseq_bulk', [
            ['sample_id', 'condition', 'group', 'replicate', 'antibody', 'control'],
            ['IP1', 'A', 'GIP', '1', 'H3K27ac', 'IN2'],
            ['IP2', 'A', 'GIP', '2', 'H3K27ac', 'IN1'],
            ['IN1', 'A', 'GIN', '1', '', ''],
            ['IN2', 'A', 'GIN', '2', '', '']])
        self.assertEqual(header, ['sample', 'fastq_1', 'fastq_2', 'replicate', 'antibody',
                                  'control', 'control_replicate'])
        self.assertEqual(rows, [['GIP', '1', 'H3K27ac', 'GIN', '2'],
                                ['GIP', '2', 'H3K27ac', 'GIN', '1'],
                                ['GIN', '1', '', '', ''],
                                ['GIN', '2', '', '', '']])

    def test_cutandrun_control_is_each_rows_own_igg_group(self):
        header, rows = self.emitted('cutandrun', [
            ['sample_id', 'condition', 'group', 'replicate', 'control'],
            ['T1', 'A', 'GT1', '1', 'IGA'],
            ['T2', 'A', 'GT2', '1', 'IGB'],
            ['G1', 'A', 'IGA', '1', ''],
            ['G2', 'A', 'IGB', '1', '']])
        self.assertEqual(header, ['group', 'replicate', 'fastq_1', 'fastq_2', 'control'])
        self.assertEqual(rows, [['GT1', '1', 'IGA'], ['GT2', '1', 'IGB'],
                                ['IGA', '1', ''], ['IGB', '1', '']])

class SchedulerStateMapTests(unittest.TestCase):
    """The backend's first token is looked up in the descriptor's own status_map."""

    def status(self, line, status_map=None):
        descriptor = dict(ex.BUILTINS['slurm'], status_argv=['/bin/echo', '{job_id}'])
        if status_map is not None:
            descriptor['status_map'] = status_map
        return ex._scheduler_status(None, line, descriptor)

    def test_each_token_reads_its_own_entry(self):
        table = {'QUEUED': 'PENDING', 'GOING': 'RUNNING', 'DONE': 'COMPLETED',
                 'KILLED': 'CANCELLED', 'BROKEN': 'FAILED:NODE_FAIL'}
        for token, state in table.items():
            with self.subTest(token=token):
                self.assertEqual(self.status(token + '|0:0', table), (state, None))
        state, why = self.status('UNKNOWN|0:0', table)
        self.assertIsNone(state)
        self.assertIn("unmapped backend state 'UNKNOWN'", why)

    def test_slurm_tokens_as_sacct_prints_them(self):
        for line, state in (('PENDING', 'PENDING'), ('RUNNING|0:0', 'RUNNING'),
                            ('COMPLETED+|0:0', 'COMPLETED'), ('CANCELLED by 1234|0:15', 'CANCELLED'),
                            ('OUT_OF_MEMORY|0:125', 'FAILED:OUT_OF_MEMORY'),
                            ('NODE_FAIL|1:0', 'FAILED:NODE_FAIL'), ('completed|0:0', 'COMPLETED')):
            with self.subTest(line=line):
                self.assertEqual(self.status(line), (state, None))

def quiet_json(call):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = call()
    return code, json.loads(out.getvalue())


class KeyedTablePrincipleTests(unittest.TestCase):
    """Class 4 by principle (0087, round 6): every table lookup keyed on a backend or an assay.

    Each lookup is driven through its public interface with a non-default key beside a
    default one whose content differs, and the chosen key's content is asserted. Backend:
    `slurm` (the default `load` falls back to) beside `local`. Assay: the default input kind
    (`fastq`) beside `spatialvi` (`sample_dir`), and an assay with extra design columns
    beside one without. The lookups already driven elsewhere in this module are named in the
    change report's round-6 inventory, not repeated here.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-keyed-table-')
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    # -- backend-keyed: executorlib.BUILTINS -------------------------------------------------

    def test_validate_reads_the_named_backends_own_entry(self):
        self.assertEqual(ex.validate(dict(ex.BUILTINS['slurm'])), [])
        self.assertEqual(ex.validate(dict(ex.BUILTINS['local'])), [])
        crossed = [('local', 'submit_argv', 'slurm'), ('slurm', 'status_argv', 'local'),
                   ('local', 'directives', 'slurm'), ('slurm', 'directives', 'local')]
        for name, key, other in crossed:
            with self.subTest(backend=name, key=key):
                descriptor = dict(ex.BUILTINS[name])
                descriptor[key] = ex.BUILTINS[other][key]
                problems = ex.validate(descriptor)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn('R-075', problems[0])

    def test_submit_and_resources_argv_are_the_backends_own(self):
        script = str(self.root / 'submit.sh')
        self.assertEqual(ex.submit_argv(dict(ex.BUILTINS['slurm']), script),
                         ['sbatch', '--export=' + ','.join(ex.EXPORT_NAMES), script])
        self.assertEqual(ex.submit_argv(dict(ex.BUILTINS['local']), script), [])
        self.assertEqual(ex.resources_argv(dict(ex.BUILTINS['slurm']), '42'),
                         ['sacct', '-j', '42', '--format=Elapsed,MaxRSS,AllocCPUS', '-P', '-n'])
        self.assertEqual(ex.resources_argv(dict(ex.BUILTINS['local']), '42'), [])

    def analysis(self):
        """A stage-03 analysis, built as test_stage03_execution builds it, holding one
        script submitted to each backend: `a.sh` as slurm job 42, `b.sh` as local job 43."""
        case = stage03.Stage03ExecutionTests('setUp')
        case.setUp()
        self.addCleanup(case.doCleanups)
        scripts = {}
        for name, backend, job in (('a.sh', 'slurm', '42'), ('b.sh', 'local', '43')):
            script = case.adir / 'scripts' / name
            script.write_text('set -euo pipefail\nexit 0\n')
            with patch.object(ex, '_submit_once', return_value=(job, None)):
                self.assertEqual(ex.submit(case.root, script, dict(ex.BUILTINS[backend])),
                                 (job, None))
            scripts[name] = script
        entries = {e['job_id']: e for e in ex._analysis_entries(case.adir)}
        self.assertEqual({j: e['executor'] for j, e in entries.items()},
                         {'42': 'slurm', '43': 'local'})
        # The local backend's own PID record, naming the launcher, as _local_submit leaves it.
        jobs = ex._local_jobs_dir(case.root)
        jobs.mkdir(parents=True, exist_ok=True)
        (jobs / '43.json').write_text(json.dumps({'script': entries['43']['launcher']}))
        return case, scripts

    def polled(self, calls, state='COMPLETED'):
        def status(root, job_id, descriptor):
            calls.append((str(job_id), descriptor['name'], descriptor['status_argv']))
            return state, None
        return patch.object(ex, '_scheduler_status', status)

    SLURM_POLL = ['sacct', '-j', '{job_id}', '--format=State,ExitCode', '--noheader', '--parsable2']

    def test_resubmission_polls_the_prior_jobs_own_backend(self):
        case, scripts = self.analysis()
        # Each script is resubmitted through the OTHER backend: the prior job is still polled
        # through the backend it was submitted to.
        for name, executed, job, backend, argv in (
                ('a.sh', 'local', '42', 'slurm', self.SLURM_POLL),
                ('b.sh', 'slurm', '43', 'local', [])):
            with self.subTest(script=name):
                calls = []
                with self.polled(calls), patch.object(ex, '_submit_once', return_value=('50', None)):
                    self.assertEqual(ex.submit(case.root, scripts[name],
                                               dict(ex.BUILTINS[executed])), ('50', None))
                self.assertEqual(calls, [(job, backend, argv)])

    def test_execution_evidence_polls_each_scripts_own_backend(self):
        case, _ = self.analysis()
        calls = []
        with self.polled(calls):
            self.assertIsNone(ex.analysis_execution_evidence(case.root, case.adir))
        self.assertEqual(sorted(calls), [('42', 'slurm', self.SLURM_POLL), ('43', 'local', [])])
        with self.polled([], state='FAILED:EXIT_1'):
            self.assertIn('recorded job', ex.analysis_execution_evidence(case.root, case.adir))

    def test_status_of_an_analysis_job_uses_its_recorded_backend(self):
        case, _ = self.analysis()
        for job, asked, backend, argv in (('42', 'local', 'slurm', self.SLURM_POLL),
                                          ('43', 'slurm', 'local', [])):
            with self.subTest(job=job):
                calls = []
                with self.polled(calls):
                    self.assertEqual(ex.status(case.root, job, dict(ex.BUILTINS[asked])),
                                     ('COMPLETED', None))
                self.assertEqual(calls, [(job, backend, argv)])

    # -- assay-keyed: workspace.PIPELINES, configure.ASSAY_DECISIONS -------------------------

    def test_check_records_the_wrappers_own_pipeline(self):
        pins = {}
        for directory in ('nfcore-atacseq-wrapper', 'nfcore-chipseq-wrapper',
                          'nfcore-cutandrun-wrapper', 'nfcore-methylseq-wrapper',
                          'nfcore-rnaseq-wrapper', 'nfcore-scrnaseq-wrapper',
                          'nfcore-spatialvi-wrapper'):
            with self.subTest(wrapper=directory):
                mod = wrapper(directory)
                project = self.root / directory
                project.mkdir()
                stage = project / '02_bioinformatics' / mod.ASSAY / mod.SUBSTAGE
                args = argparse.Namespace(project=str(project), counts=None, design=None,
                                          h5ad=None)
                with patch.object(mod, 'run_checks',
                                  return_value=([], {}, {'substage': stage, 'inputs': []})):
                    self.assertEqual(quiet_json(lambda: mod.cmd_check(args))[0], 0)
                record = json.loads((stage / 'preflight/check_result.json').read_text())
                self.assertEqual(record['pipeline'], ws.PIPELINES[mod.ASSAY])
                pins[mod.ASSAY] = record['pipeline']
        self.assertEqual(len(set(pins.values())), 7)

    def test_genome_menu_cache_is_the_assays_own_pipeline(self):
        case = mapping.ConfigureApplyMappingTests('setUp')
        case.setUp()
        self.addCleanup(case.tearDown)
        seen = set()
        for assay in ('rnaseq_bulk', 'atacseq_bulk', 'spatialvi'):
            with self.subTest(assay=assay):
                code, result = quiet_json(lambda: configure.main(
                    ['--workspace', str(case.root), 'genomes', '--assay', assay]))
                self.assertEqual(code, 0, result)
                derived = {g['id']: g['derived_dir'] for g in result['genomes']}
                self.assertEqual(derived, {
                    'G1': str(case.root / 'cache1' / ws.PIPELINES[assay]),
                    'G2': str(case.root / 'cache2' / ws.PIPELINES[assay])})
                seen.add(derived['G1'])
        self.assertEqual(len(seen), 3)
        code, result = quiet_json(lambda: configure.main(['--workspace', str(case.root), 'genomes']))
        self.assertEqual([g['derived_dir'] for g in result['genomes']], [None, None])

    def test_apply_completes_the_assays_own_decisions(self):
        case = mapping.ConfigureApplyMappingTests('setUp')
        case.setUp()
        self.addCleanup(case.tearDown)
        template = 'reference:\n  fasta: <REQUIRED>\n  gtf: <REQUIRED>\n'
        for assay in ('cutandrun', 'methylseq'):
            with self.subTest(assay=assay):
                text = case.apply(assay, template, '--genome', 'G2')
                self.assertEqual(sorted(text.splitlines()),
                                 sorted(['reference:'] + case.genome_lines('G2')))
        # An assay with no registered decisions is a usage refusal, never another's shape.
        (case.project / '_config/spatialvi.yaml').write_text(template)
        code, result = quiet_json(lambda: configure.main(
            ['--workspace', str(case.root), 'apply', '--project', str(case.project),
             '--assay', 'spatialvi', '--genome', 'G2']))
        self.assertEqual(code, configure.EXIT_USAGE, result)
        self.assertIn("assay 'spatialvi'", result['error'])
        self.assertEqual((case.project / '_config/spatialvi.yaml').read_text(), template)

    def test_assay_menu_entries_carry_their_own_assays_row(self):
        (self.root / '_references').mkdir()
        (self.root / '_references/assay_stage_skill_map.md').write_text(
            '| Assay | Assay ID | Source | Sub-stage | Skill |\n|---|---|---|---|---|\n'
            '| Bulk fixture | bulk_x | gars | 01_align | aligner-x |\n'
            '| Bulk fixture | bulk_x | gars | 02_count | counter-x |\n'
            '| Spatial fixture | spatial_y | gars | 01_spots | spotter-y |\n')
        code, result = quiet_json(lambda: s00.main(['--workspace', str(self.root), 'assays']))
        self.assertEqual(code, 0, result)
        self.assertEqual(result['assays'], [
            {'n': '01', 'assay': 'Bulk fixture', 'assay_id': 'bulk_x',
             'substages': [{'substage': '01_align', 'skill': 'aligner-x'},
                           {'substage': '02_count', 'skill': 'counter-x'}]},
            {'n': '02', 'assay': 'Spatial fixture', 'assay_id': 'spatial_y',
             'substages': [{'substage': '01_spots', 'skill': 'spotter-y'}]}])

    # -- input-kind-keyed: workspace.INPUT_KINDS through stage 00 and stage 01 ---------------

    def source(self):
        """One sample directory, one sample tarball and one FASTQ, side by side."""
        source = self.root / 'source'
        (source / 'S1/outs').mkdir(parents=True)
        (source / 'S1/outs/matrix.h5').write_bytes(b'S1')
        (source / 'S2.tar.gz').write_bytes(b'S2')
        (source / 'K1_S1_L001_R1_001.fastq.gz').write_bytes(gzip.compress(b'@r\nACGT\n+\nIIII\n'))
        return source

    def test_inspect_and_link_find_the_assays_own_kind_of_input(self):
        source = self.source()
        project = self.root / 'project'
        for assay, kind, raw in (('spatialvi', 'sample_dir', ['S1', 'S2.tar.gz']),
                                 ('rnaseq_bulk', 'fastq', ['K1_S1_L001_R1_001.fastq.gz'])):
            with self.subTest(assay=assay):
                code, result = quiet_json(lambda: s00.main(
                    ['inspect', '--assay', assay, '--source', str(source)]))
                self.assertEqual(code, 0, result)
                self.assertEqual((result['input_kind'], result['raw_file_count']),
                                 (kind, len(raw)))
                (project / '00_data' / assay / 'raw').mkdir(parents=True)
                code, result = quiet_json(lambda: s00.main(
                    ['link', '--project', str(project), '--assay', assay,
                     '--source', str(source)]))
                self.assertEqual(code, 0, result)
                self.assertEqual(sorted(p.name for p in
                                        (project / '00_data' / assay / 'raw').iterdir()), raw)

    def finalize_project(self, name):
        project = self.root / name
        (project / '_config').mkdir(parents=True)
        (project / 'CONTEXT.md').write_text('{{assay_table}}\n')
        (project / 'HISTORY.md').write_text('v {{template_version}}\n')
        source = self.root / name / 'source'
        for sample in ('S1', 'S2'):
            (source / sample).mkdir(parents=True)
            (source / sample / 'matrix.h5').write_bytes(sample.encode())
        for assay, samples in (('spatialvi', ('S1', 'S2')), ('rnaseq_bulk', ('K1',)),
                               ('chipseq_bulk', ('C1',))):
            raw = project / '00_data' / assay / 'raw'
            raw.mkdir(parents=True)
            for sample in samples:
                if assay == 'spatialvi':
                    os.symlink(str(source / sample), str(raw / sample))
                    continue
                for read in ('R1', 'R2'):
                    fastq = source / ('%s_S1_L001_%s_001.fastq.gz' % (sample, read))
                    fastq.write_bytes(gzip.compress(b'@r\nACGT\n+\nIIII\n'))
                    os.symlink(str(fastq), str(raw / fastq.name))
        return project

    def finalize(self, project):
        return quiet_json(lambda: s00.main(
            ['finalize', '--project', str(project), '--data-class', 'public',
             '--purpose', 'fixture', '--date', '2026-09-25']))

    def test_finalize_registers_and_gates_each_assay_by_its_own_kind(self):
        project = self.finalize_project('project')
        code, result = self.finalize(project)
        self.assertEqual(code, 0, result)
        data = project / '00_data'

        def rows(assay, name):
            return [l.split(',') for l in (data / assay / name).read_text().splitlines()
                    if not l.startswith('#')]
        self.assertEqual(rows('spatialvi', 'files.csv'),
                         [['sample_id', 'spaceranger_dir'],
                          ['S1', '00_data/spatialvi/raw/S1'], ['S2', '00_data/spatialvi/raw/S2']])
        self.assertEqual(rows('rnaseq_bulk', 'files.csv'),
                         [['sample_id', 'lane', 'fastq_1', 'fastq_2'],
                          ['K1', 'L001', '00_data/rnaseq_bulk/raw/K1_S1_L001_R1_001.fastq.gz',
                           '00_data/rnaseq_bulk/raw/K1_S1_L001_R2_001.fastq.gz']])
        self.assertEqual(rows('spatialvi', 'samples.csv')[0],
                         ['sample_id', 'condition', 'group', 'replicate'])
        self.assertEqual(rows('chipseq_bulk', 'samples.csv')[0],
                         ['sample_id', 'condition', 'group', 'replicate', 'antibody', 'control'])
        self.assertEqual({a: result['assays'][a]['layout'] for a in result['assays']},
                         {'spatialvi': 'sample-dir', 'rnaseq_bulk': 'paired-end',
                          'chipseq_bulk': 'paired-end'})
        names = s00.catalog_names(s00.read_assay_map(GARS)[0])
        table = (project / 'CONTEXT.md').read_text()
        for assay in ('spatialvi', 'rnaseq_bulk', 'chipseq_bulk'):
            self.assertIn('| %s | %s |' % (names[assay], assay), table)
        self.assertEqual(len({names[a] for a in ('spatialvi', 'rnaseq_bulk', 'chipseq_bulk')}), 3)
        # A spatial directory link that resolves to nothing is refused by the sample_dir gate.
        project = self.finalize_project('dangling')
        os.symlink(str(self.root / 'absent'), str(project / '00_data/spatialvi/raw/S3'))
        code, result = self.finalize(project)
        self.assertEqual(code, s00.EXIT_FAILURE, result)
        self.assertEqual(result['failures'], ['spatialvi: 00_data/spatialvi/raw/S3 does not resolve'])

    def test_stage01_emits_the_directory_column_for_a_directory_assay(self):
        project = self.root / 'project'
        data = project / '00_data/spatialvi'
        (data / 'raw/S1').mkdir(parents=True)
        (data / 'raw/S2').mkdir()
        (project / '_config').mkdir()
        (project / '_config/spatialvi.yaml').write_text('reference_release: synthetic-v1\n')
        (data / 'files.csv').write_text('# generated by stage 00\nsample_id,spaceranger_dir\n'
                                        'S1,00_data/spatialvi/raw/S1\nS2,00_data/spatialvi/raw/S2\n')
        (data / 'samples.csv').write_text('sample_id,condition,group,replicate\n'
                                          'S1,A,GA,1\nS2,B,GB,1\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = s01.main(['--project', str(project)])
        self.assertEqual(code, 0, out.getvalue())
        sheet = project / '01_samplesheets/spatialvi_samplesheet.csv'
        self.assertEqual([l.split(',') for l in sheet.read_text().splitlines()],
                         [['sample', 'spaceranger_dir'], ['S1', str(data / 'raw/S1')],
                          ['S2', str(data / 'raw/S2')]])


if __name__ == '__main__':
    unittest.main(verbosity=2)
