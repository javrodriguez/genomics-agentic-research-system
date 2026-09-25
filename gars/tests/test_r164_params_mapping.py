"""R-164 class 3: every params builder maps each config field to its own parameter (0087).

Fixture values are pairwise distinct, so a swapped, dropped or duplicated field is visible
in the emitted list, the manifest or the generated script.
"""
import argparse
import ast
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module
import executorlib as ex

WRAPPERS = GARS / '_system/wrappers'


def wrapper(directory):
    source = WRAPPERS / directory / (directory.replace('-', '_') + '.py')
    return module(source, 'r164_params_' + directory.replace('-', '_'))


def constants(script, *names):
    """Literal values assigned at top level of a GENERATED script (an output artifact)."""
    found = {}
    for line in script.splitlines():
        match = re.match(r'^([A-Z0-9_, ]+?)\s*=\s*(.+?)\s*(#.*)?$', line)
        if match and match.group(1).strip() in names:
            found[match.group(1).strip()] = ast.literal_eval(match.group(2))
    return found


class NfcoreBuildParamsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-params-')
        self.root = Path(self._tmp.name).resolve()
        self.paths = {'samplesheet': self.root / 'sheet.csv',
                      'substage': self.root / 'stage'}
        self.sheet = str(self.root / 'sheet.csv')
        self.outdir = str(self.root / 'stage/run/results')

    def tearDown(self):
        self._tmp.cleanup()

    def p(self, name):
        return str(self.root / name)

    def index(self, relative, name='x'):
        path = self.root / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / name).write_text(relative)
        return str(path)

    def test_rnaseq_indices_are_not_exchanged(self):
        rnaseq = wrapper('nfcore-rnaseq-wrapper')
        cfg = {'reference.fasta': self.p('g.fa'), 'reference.gtf': self.p('g.gtf'),
               'aligner': 'star_salmon', 'reference.derived_dir': self.p('derived')}
        head = [('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('g.fa')),
                ('gtf', self.p('g.gtf')), ('aligner', 'star_salmon')]
        self.assertEqual(rnaseq.build_params(cfg, self.paths), head + [('save_reference', 'true')])
        star = self.index('derived/index/star', 'SA')
        salmon = self.index('derived/index/salmon', 'pos.bin')
        (self.root / 'derived/genome.transcripts.fa').write_text('>t\n')
        self.assertEqual(rnaseq.build_params(cfg, self.paths), head + [
            ('star_index', star), ('salmon_index', salmon),
            ('transcript_fasta', self.p('derived/genome.transcripts.fa'))])
        other = dict(cfg, aligner='hisat2')
        self.assertEqual(rnaseq.build_params(other, self.paths),
                         head[:-1] + [('aligner', 'hisat2'), ('save_reference', 'true')])
        bare = {k: v for k, v in cfg.items() if k != 'reference.derived_dir'}
        self.assertEqual(rnaseq.build_params(bare, self.paths), head)

    def test_atacseq_every_field(self):
        atac = wrapper('nfcore-atacseq-wrapper')
        cfg = {'reference.fasta': self.p('a.fa'), 'reference.gtf': self.p('a.gtf'),
               'reference.mito_name': 'chrMito', 'aligner': 'bowtie2',
               'peaks.type': 'broad', 'peaks.macs_gsize': '2.7e9'}
        head = [('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('a.fa')),
                ('gtf', self.p('a.gtf')), ('mito_name', 'chrMito'), ('aligner', 'bowtie2'),
                ('macs_gsize', '2.7e9')]
        self.assertEqual(atac.build_params(cfg, self.paths), head)
        index = self.index('derived/bowtie2')
        full = dict(cfg, **{'peaks.type': 'narrow', 'reference.blacklist': self.p('bl.bed'),
                            'reference.derived_dir': self.p('derived'),
                            'pipeline.skip_preseq': 'true'})
        self.assertEqual(atac.build_params(full, self.paths), head + [
            ('narrow_peak', 'true'), ('blacklist', self.p('bl.bed')),
            ('bowtie2_index', index), ('skip_preseq', 'true')])

    def test_chipseq_every_field(self):
        chip = wrapper('nfcore-chipseq-wrapper')
        cfg = {'reference.fasta': self.p('c.fa'), 'reference.gtf': self.p('c.gtf'),
               'aligner': 'chromap', 'peaks.type': 'broad', 'peaks.macs_gsize': '1.87e9'}
        head = [('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('c.fa')),
                ('gtf', self.p('c.gtf')), ('aligner', 'chromap'), ('macs_gsize', '1.87e9')]
        self.assertEqual(chip.build_params(cfg, self.paths), head)
        full = dict(cfg, **{'peaks.type': 'narrow', 'reference.blacklist': self.p('cb.bed'),
                            'reference.derived_dir': self.p('derived')})
        self.assertEqual(chip.build_params(full, self.paths), head + [
            ('narrow_peak', 'true'), ('blacklist', self.p('cb.bed')),
            ('save_reference', 'true')])

    def test_cutandrun_every_field(self):
        cut = wrapper('nfcore-cutandrun-wrapper')
        cfg = {'reference.fasta': self.p('r.fa'), 'reference.gtf': self.p('r.gtf'),
               'reference.mito_name': 'MT', 'spikein.fasta': self.p('ecoli.fa'),
               'spikein.bowtie2': self.p('ecoli-bt2'), 'peaks.peakcaller': 'macs2',
               'peaks.normalisation': 'CPM'}
        head = [('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('r.fa')),
                ('gtf', self.p('r.gtf')), ('mito_name', 'MT'),
                ('spikein_fasta', self.p('ecoli.fa')), ('spikein_bowtie2', self.p('ecoli-bt2')),
                ('peakcaller', 'macs2'), ('normalisation_mode', 'CPM')]
        self.assertEqual(cut.build_params(cfg, self.paths), head + [('use_control', 'true')])
        full = dict(cfg, **{'peaks.use_control': 'false', 'reference.blacklist': self.p('x.bed'),
                            'qc.gene_heatmaps': 'off'})
        self.assertEqual(cut.build_params(full, self.paths), head + [
            ('use_control', 'false'), ('blacklist', self.p('x.bed')), ('skip_heatmaps', 'true')])

    def test_methylseq_every_field(self):
        meth = wrapper('nfcore-methylseq-wrapper')
        cfg = {'reference.fasta': self.p('m.fa'), 'aligner': 'bwameth'}
        self.assertEqual(meth.build_params(cfg, self.paths), [
            ('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('m.fa')),
            ('aligner', 'bwameth')])
        self.assertEqual(meth.build_params({'reference.fasta': self.p('m.fa')}, self.paths)[-1],
                         ('aligner', 'bismark'))

    def test_scrnaseq_every_field(self):
        sc = wrapper('nfcore-scrnaseq-wrapper')
        cfg = {'reference.fasta': self.p('s.fa'), 'reference.gtf': self.p('s.gtf'),
               'aligner': 'kallisto', 'protocol': '10XV3',
               'reference.derived_dir': self.p('derived'),
               'pipeline.skip_cellbender': 'true', 'pipeline.skip_qcatch': 'TRUE'}
        index = self.index('derived/kallisto')
        self.assertEqual(sc.build_params(cfg, self.paths), [
            ('input', self.sheet), ('outdir', self.outdir), ('fasta', self.p('s.fa')),
            ('gtf', self.p('s.gtf')), ('aligner', 'kallisto'), ('protocol', '10XV3'),
            ('igenomes_ignore', 'true'), ('kallisto_index', index),
            ('skip_cellbender', 'true'), ('skip_qcatch', 'true')])

    def test_spatialvi_every_field(self):
        spv = wrapper('nfcore-spatialvi-wrapper')
        cfg = {'hd_bin_size': '16', 'qc.min_counts': '101', 'qc.min_genes': '202',
               'qc.min_spots': '303', 'qc.mito_threshold': '4.5', 'cluster_resolution': '0.7'}
        self.assertEqual(spv.build_params(cfg, self.paths), [
            ('input', self.sheet), ('outdir', self.outdir), ('hd_bin_size', '16'),
            ('qc_min_counts', '101'), ('qc_min_genes', '202'), ('qc_min_spots', '303'),
            ('qc_mito_threshold', '4.5'), ('cluster_resolution', '0.7')])


class DownstreamPrepareTests(unittest.TestCase):
    """cmd_prepare with run_checks as the fixture: the manifest and script it writes."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-params-')
        self.root = Path(self._tmp.name).resolve()
        (self.root / '_config').mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def prepare(self, directory, cfg, args, paths):
        mod = wrapper(directory)
        config = self.root / '_config' / (mod.ASSAY + '.yaml')
        config.write_text('fixture: declared\n')
        stage = self.root / '02_bioinformatics' / mod.ASSAY / mod.SUBSTAGE
        paths = dict(paths, substage=stage, config=config)
        with patch.object(mod, 'run_checks', return_value=([], cfg, paths)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(mod.cmd_prepare(argparse.Namespace(project=str(self.root), **args)), 0)
        manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
        return stage, manifest

    def test_rnaseq_de_formula_contrast_and_inputs(self):
        counts = self.root / 'counts.tsv'
        counts.write_text('gene_id\tA\n')
        design = self.root / '01_samplesheets/rnaseq_bulk_design.csv'
        design.parent.mkdir()
        design.write_text('sample_id,condition\nA,x\n')
        cfg = {'de.formula': '~ batch + condition', 'de.contrast': 'condition,treated,control'}
        stage, manifest = self.prepare('rnaseq-de', cfg,
                                       {'counts': str(counts), 'design': str(design)}, {})
        self.assertEqual(manifest['params'], {'formula': '~ batch + condition',
                                              'contrast': 'condition,treated,control',
                                              'counts': str(counts), 'design': str(design)})
        script = (stage / 'scripts/run_de.py').read_text()
        adapted = stage / 'adapted'
        self.assertEqual(constants(script, 'COUNTS', 'DESIGN', 'IDMAP', 'OUT', 'FORMULA',
                                   'FACTOR, NUMERATOR, DENOMINATOR'), {
            'COUNTS': str(adapted / 'counts_gene.tsv'), 'DESIGN': str(design),
            'IDMAP': str(adapted / 'gene_id_to_name.tsv'), 'OUT': str(stage / 'run'),
            'FORMULA': '~ batch + condition',
            'FACTOR, NUMERATOR, DENOMINATOR': ('condition', 'treated', 'control')})
        submit = (stage / 'submit.sh').read_text()
        self.assertIn('--counts "%s"' % counts, submit)
        self.assertIn('--out "%s"' % adapted, submit)

    def test_scrna_qc_cluster_thresholds(self):
        h5ad = self.root / 'combined.h5ad'
        h5ad.write_bytes(b'h5')
        sheet = self.root / 'sheet.csv'
        sheet.write_text('sample\ns1\n')
        cfg = {'qc.min_genes': '211', 'qc.min_cells': '3', 'qc.max_mito_pct': '17.5',
               'n_hvg': '1999', 'cluster_resolution': '0.35', 'qc.mito_prefix': 'mt-'}
        stage, manifest = self.prepare('scrna-qc-cluster', cfg, {'h5ad': str(h5ad)},
                                       {'samplesheet': sheet})
        self.assertEqual(manifest['params'], {'h5ad': str(h5ad), 'min_genes': '211',
                                              'min_cells': '3', 'max_mito_pct': '17.5',
                                              'n_hvg': '1999', 'cluster_resolution': '0.35'})
        script = (stage / 'scripts/run_scrna.py').read_text()
        self.assertEqual(constants(script, 'IN_H5AD', 'OUT', 'MIN_GENES', 'MIN_CELLS',
                                   'MAX_MITO_PCT', 'N_HVG', 'RESOLUTION', 'MITO_PREFIX'), {
            'IN_H5AD': str(h5ad), 'OUT': str(stage / 'run'), 'MIN_GENES': 211, 'MIN_CELLS': 3,
            'MAX_MITO_PCT': 17.5, 'N_HVG': 1999, 'RESOLUTION': 0.35, 'MITO_PREFIX': 'mt-'})

    def test_spatial_cluster_count_inputs_per_sample(self):
        results = self.root / 'results'
        first, second = results / 's1.h5ad', results / 's2.h5ad'
        results.mkdir()
        first.write_bytes(b'one')
        second.write_bytes(b'two')
        sheet = self.root / 'sheet.csv'
        sheet.write_text('sample,spaceranger_dir\ns1,a\ns2,b\n')
        stage, manifest = self.prepare('spatial-cluster-count', {}, {'h5ad': str(results)},
                                       {'samplesheet': sheet,
                                        'inputs': [('s1', first), ('s2', second)]})
        self.assertEqual(manifest['params'], {'h5ad': str(results), 'obs_column': 'clusters',
                                              'samples': 's1,s2'})
        self.assertEqual(manifest['inputs']['h5ad_s1'], str(first))
        self.assertEqual(manifest['inputs']['h5ad_s2'], str(second))
        script = (stage / 'scripts/count_clusters.py').read_text()
        self.assertEqual(constants(script, 'INPUTS', 'OUT', 'OBS_COLUMN'), {
            'INPUTS': [('s1', str(first)), ('s2', str(second))], 'OUT': str(stage / 'run'),
            'OBS_COLUMN': 'clusters'})


class DirectiveMappingTests(unittest.TestCase):
    def test_slurm_directives_carry_each_compute_field(self):
        with tempfile.TemporaryDirectory(prefix='gars-params-') as tmp:
            stage = Path(tmp).resolve() / 'stage'
            cfg = {'compute.partition': 'p-short', 'compute.time': '01:02:03',
                   'compute.cpus': '7', 'compute.mem': '11G'}
            lines = ex.header_lines(None, cfg, 'proj', 'assay1', stage, descriptor=dict(ex.SLURM))
            self.assertEqual(lines, [
                '#SBATCH --job-name=proj-assay1', '#SBATCH --partition=p-short',
                '#SBATCH --time=01:02:03', '#SBATCH --cpus-per-task=7', '#SBATCH --mem=11G',
                '#SBATCH --output=%s/logs/slurm-%%j.out' % stage,
                '#SBATCH --error=%s/logs/slurm-%%j.err' % stage])


if __name__ == '__main__':
    unittest.main(verbosity=2)
