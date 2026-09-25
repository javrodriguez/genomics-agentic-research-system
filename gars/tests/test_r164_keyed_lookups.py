"""R-164 class 4: every table keyed by aligner, assay, genome or backend returns its own row (0087).

Each fixture carries at least two keys whose content differs, and the test asserts the
chosen key's content, so reading another key's entry is visible.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module
import configure
import executorlib as ex
import workspace as ws
import wrapperlib as wl

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
