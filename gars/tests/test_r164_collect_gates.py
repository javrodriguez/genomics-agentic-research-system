"""R-164 class 5: the remaining collect gates, each artifact at zero and one byte (0087, round 2).

Each wrapper's cmd_collect runs over a complete fixture of its published layout, then over
the same fixture with one gated artifact emptied, shrunk to one byte, removed, or missing one
sample; the observation is the exit code and the named failure. The lifecycle writers are
stubbed by the shared harness (they have their own suites).
"""
import json
import unittest
from test_r164_boundaries import CollectHarness


class GateCases(object):
    """Mixin: `byte_gated` artifacts refuse at zero bytes and pass at one; `required` refuse
    when absent. Subclasses build the complete layout in `complete()`."""
    byte_gated = ()
    required = ()

    def setUp(self):
        super().setUp()
        self.complete()

    def test_complete_layout_passes(self):
        self.assertEqual(self.collect(), (0, []))

    def test_each_byte_gate_at_zero_and_one_byte(self):
        for relative, named in self.byte_gated:
            with self.subTest(artifact=relative):
                original = (self.stage / relative).read_bytes()
                self.write(relative, b'')
                code, failures = self.collect()
                self.assertEqual(code, 1, relative)
                self.assertNamed(failures, named)
                self.write(relative, b'x')
                self.assertEqual(self.collect(), (0, []))
                self.write(relative, original)

    def test_each_required_artifact_absent(self):
        for relative, named in self.required:
            with self.subTest(artifact=relative):
                path = self.stage / relative
                original = path.read_bytes()
                path.unlink()
                code, failures = self.collect()
                self.assertEqual(code, 1, relative)
                self.assertNamed(failures, named)
                self.write(relative, original)
        self.assertEqual(self.collect(), (0, []))


class RnaseqCollectGateTests(GateCases, CollectHarness):
    directory = 'nfcore-rnaseq-wrapper'
    counts = 'run/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv'
    byte_gated = (('run/results/multiqc/star_salmon/multiqc_report.html', 'missing or empty'),)
    required = (('run/results/star_salmon/salmon.merged.transcript_counts.tsv', 'missing'),
                ('run/results/star_salmon/salmon.merged.gene_tpm.tsv', 'missing'),
                ('run/results/star_salmon/S1.sorted.bam', 'no *.sorted.bam under'),
                (counts, 'missing or empty'))

    def complete(self):
        self.sheet('sample,fastq_1,fastq_2,strandedness\nS1,a,b,auto\nS2,c,d,auto\n')
        (self.project / '_config/rnaseq_bulk.yaml').write_text('aligner: star_salmon\n')
        self.write(self.counts, b'gene_id\tgene_name\tS1\tS2\ng\tn\t1\t2\n')
        for name in ('salmon.merged.transcript_counts.tsv', 'salmon.merged.gene_tpm.tsv',
                     'S1.sorted.bam'):
            self.write('run/results/star_salmon/' + name, b'x')
        self.write('run/results/multiqc/star_salmon/multiqc_report.html', b'<html/>')

    def test_counts_matrix_byte_boundary_and_sample_columns(self):
        self.write(self.counts, b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'missing or empty')
        self.write(self.counts, b'\n')
        code, failures = self.collect()
        self.assertNamed(failures, 'lacks column(s) for sample(s): S1, S2')
        self.write(self.counts, b'gene_id\tgene_name\tS1\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'lacks column(s) for sample(s): S2')

    def test_the_configured_aligners_directory_is_gated(self):
        (self.project / '_config/rnaseq_bulk.yaml').write_text('aligner: star_rsem\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'star_rsem')


class AtacseqCollectGateTests(GateCases, CollectHarness):
    directory = 'nfcore-atacseq-wrapper'
    base = 'run/results/bwa/merged_library/'
    consensus = base + 'macs2/narrow_peak/consensus/'
    byte_gated = (('run/results/multiqc/narrow_peak/multiqc_report.html', 'missing or empty'),)
    required = ((base + 'macs2/narrow_peak/G1_REP1.narrowPeak', 'no *.narrowPeak under'),
                (consensus + 'consensus_peaks.bed', 'no consensus *.bed under'),
                (consensus + 'consensus_peaks.featureCounts.txt', 'no *.featureCounts.txt'),
                (base + 'bigwig/G1_REP1.bigWig', 'no *.bigWig under'),
                (base + 'G1_REP1.sorted.bam', 'no merged-library *.sorted.bam'))

    def complete(self):
        self.sheet('sample,fastq_1,fastq_2,replicate\nG1,a,b,1\nG1,c,d,2\nG2,e,f,1\n')
        (self.project / '_config/atacseq_bulk.yaml').write_text(
            'aligner: bwa\npeaks:\n  type: narrow\n')
        for relative, _ in self.required:
            self.write(relative, b'x')
        self.write(self.consensus + 'consensus_peaks.featureCounts.txt',
                   b'# program\nGeneid\tChr\tG1_REP1.bam\tG1_REP2.bam\tG2_REP1.bam\n')
        self.write('run/results/multiqc/narrow_peak/multiqc_report.html', b'<html/>')

    def test_a_lost_replicate_is_named(self):
        self.write(self.consensus + 'consensus_peaks.featureCounts.txt',
                   b'# program\nGeneid\tChr\tG1_REP1.bam\tG2_REP1.bam\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'lacks column(s) for: G1_REP2')

    def test_the_configured_peak_type_is_gated(self):
        (self.project / '_config/atacseq_bulk.yaml').write_text(
            'aligner: bwa\npeaks:\n  type: broad\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'no *.broadPeak under')


class ChipseqCollectGateTests(GateCases, CollectHarness):
    directory = 'nfcore-chipseq-wrapper'
    base = 'run/results/bwa/merged_library/'
    consensus = base + 'macs3/narrow_peak/consensus/H3K4me3/'
    byte_gated = (('run/results/multiqc/narrow_peak/multiqc_report.html', 'missing or empty'),)
    required = ((base + 'macs3/narrow_peak/IP_REP1.narrowPeak', 'no *.narrowPeak under'),
                (consensus + 'H3K4me3.consensus_peaks.bed', 'no consensus */*.bed'),
                (consensus + 'H3K4me3.featureCounts.txt', 'no */*.featureCounts.txt'),
                (base + 'bigwig/IP_REP1.bigWig', 'no *.bigWig under'),
                (base + 'IP_REP1.sorted.bam', 'no merged-library *.sorted.bam'))

    def complete(self):
        self.sheet('sample,fastq_1,fastq_2,replicate,antibody,control,control_replicate\n'
                   'IP,a,b,1,H3K4me3,IN,1\nIP,c,d,2,H3K4me3,IN,1\nIN,e,f,1,,,\n')
        (self.project / '_config/chipseq_bulk.yaml').write_text(
            'aligner: bwa\npeaks:\n  type: narrow\n')
        for relative, _ in self.required:
            self.write(relative, b'x')
        self.write(self.consensus + 'H3K4me3.featureCounts.txt',
                   b'# program\nGeneid\tChr\tIP_REP1.bam\tIP_REP2.bam\n')
        self.write('run/results/multiqc/narrow_peak/multiqc_report.html', b'<html/>')

    def test_a_lost_ip_replicate_is_named_and_input_is_not_required(self):
        self.write(self.consensus + 'H3K4me3.featureCounts.txt',
                   b'# program\nGeneid\tChr\tIP_REP1.bam\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'carries IP sample(s): IP_REP2')
        self.assertFalse(any('IN_REP1' in f for f in failures), failures)


class CutandrunCollectGateTests(GateCases, CollectHarness):
    directory = 'nfcore-cutandrun-wrapper'
    peaks = 'run/results/03_peak_calling/'
    byte_gated = (('run/results/04_reporting/multiqc/multiqc_report.html', 'missing or empty'),)
    required = (('run/results/02_alignment/bowtie2/target/markdup/T_R1.bam', 'no *.bam under'),
                (peaks + '03_bed_to_bigwig/T_R1.bigWig', 'no *.bigWig under'),
                (peaks + '04_called_peaks/seacr/T_R1.seacr.peaks.stringent.bed',
                 'no called-peak *.bed'),
                (peaks + '05_consensus_peaks/T.consensus.peaks.bed', 'no consensus *.bed'))

    def complete(self):
        self.sheet('group,replicate,fastq_1,fastq_2,control\nT,1,a,b,IGG\nIGG,1,c,d,\n')
        (self.project / '_config/cutandrun.yaml').write_text('peakcaller: seacr\n')
        for relative, _ in self.required:
            self.write(relative, b'x')
        self.write('run/results/04_reporting/multiqc/multiqc_report.html', b'<html/>')

    def test_a_target_group_without_peaks_is_named(self):
        self.sheet('group,replicate,fastq_1,fastq_2,control\nT,1,a,b,IGG\nU,1,e,f,IGG\n'
                   'IGG,1,c,d,\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'no called-peak file for target group(s): U')


class MethylseqCollectGateTests(GateCases, CollectHarness):
    directory = 'nfcore-methylseq-wrapper'
    base = 'run/results/bismark/'
    byte_gated = (('run/results/multiqc/multiqc_report.html', 'missing or empty'),)
    required = ((base + 'methylation_calls/S1.txt.gz', 'nothing under'),
                (base + 'bedGraph/S1.bedGraph.gz', 'nothing under'))

    def complete(self):
        self.sheet('sample,fastq_1,fastq_2\nS1,a,b\nS2,c,d\n')
        (self.project / '_config/methylseq.yaml').write_text('aligner: bismark\n')
        for relative, _ in self.required:
            self.write(relative, b'x')
        for s in ('S1', 'S2'):
            self.write(self.base + 'methylation_coverage/%s.bismark.cov.gz' % s, b'x')
        self.write('run/results/multiqc/multiqc_report.html', b'<html/>')

    def test_a_sample_without_coverage_is_named(self):
        (self.stage / self.base / 'methylation_coverage/S2.bismark.cov.gz').unlink()
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'no coverage file for sample(s): S2')
        (self.stage / self.base / 'methylation_coverage/S1.bismark.cov.gz').unlink()
        code, failures = self.collect()
        self.assertNamed(failures, 'no *.cov.gz under')


class RnaseqDeCollectGateTests(GateCases, CollectHarness):
    directory = 'rnaseq-de'
    table = 'run/tables/de_results.csv'
    byte_gated = tuple(('run/figures/%s' % f, 'missing or empty') for f in
                       ('pca.png', 'volcano.png', 'ma_plot.png')) + (
        ('run/report.md', 'missing or empty'),
        ('adapted/counts_gene.tsv', 'missing or empty adapted/counts_gene.tsv'),
        ('adapted/gene_id_to_name.tsv', 'missing or empty adapted/gene_id_to_name.tsv'))
    required = (('run/tables/normalized_counts.csv', 'missing'),)

    def complete(self):
        (self.project / '01_samplesheets/rnaseq_bulk_design.csv').write_text(
            'sample_id,condition\nS1,a\nS2,b\n')
        self.write(self.table, b'gene,pvalue,padj\ng1,0.5,0.5\n')
        self.write('run/tables/normalized_counts.csv', b'gene,S1,S2\ng1,1,2\n')
        for relative, _ in self.byte_gated:
            self.write(relative, b'x')

    def test_results_table_byte_boundary_and_identifier_column(self):
        self.write(self.table, b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'missing or empty')
        self.write(self.table, b'x')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, "first column is 'x', not 'gene'")
        self.write(self.table, b'gene,pvalue,padj\n,0.5,0.5\n')
        code, failures = self.collect()
        self.assertNamed(failures, 'empty gene identifier(s) present')

    def test_normalized_counts_must_carry_every_design_sample(self):
        self.write('run/tables/normalized_counts.csv', b'gene,S1\ng1,1\n')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'normalized_counts.csv lacks sample(s): S2')


class ScrnaQcClusterCollectGateTests(GateCases, CollectHarness):
    directory = 'scrna-qc-cluster'
    byte_gated = (('run/data/processed.h5ad', 'missing or empty'),
                  ('run/figures/umap_clusters.png', 'missing or empty'),
                  ('run/figures/violin_qc.png', 'missing or empty'),
                  ('run/report.md', 'missing or empty'),
                  ('run/tables/cluster_markers.csv', 'missing or empty'))
    required = (('run/summary.json', 'missing'),)

    def complete(self):
        self.sheet('sample,fastq_1,fastq_2\nS1,a,b\nS2,c,d\n')
        self.summary(n_cells_out=5, n_clusters=2, cells_after_qc={'S1_filtered': 3, 'S2': 2})
        for relative, _ in self.byte_gated:
            self.write(relative, b'x')
        self.write('run/tables/cluster_markers.csv', b'gene,cluster\ng1,0\n')

    def summary(self, **fields):
        self.write('run/summary.json', json.dumps(fields).encode())

    def test_each_byte_gate_at_zero_and_one_byte(self):
        # The markers table is content-checked at one byte, so it is gated separately below.
        self.byte_gated = self.byte_gated[:-1]
        super().test_each_byte_gate_at_zero_and_one_byte()

    def test_markers_table_identifier_column(self):
        for data, named in ((b'', 'missing or empty'), (b'x', "first column is 'x', not 'gene'"),
                            (b'gene,cluster\n,0\n', 'empty gene identifier(s)')):
            with self.subTest(data=data):
                self.write('run/tables/cluster_markers.csv', data)
                code, failures = self.collect()
                self.assertEqual(code, 1)
                self.assertNamed(failures, named)

    def test_cell_and_cluster_totals_at_one_zero_and_minus_one(self):
        after = {'S1': 3, 'S2': 2}
        for field, named in (('n_cells_out', 'no cells survived QC'),
                             ('n_clusters', 'no clusters were found')):
            for value, refused in ((1, False), (0, True), (-1, True)):
                with self.subTest(field=field, value=value):
                    fields = {'n_cells_out': 5, 'n_clusters': 2, 'cells_after_qc': after}
                    fields[field] = value
                    self.summary(**fields)
                    code, failures = self.collect()
                    self.assertEqual(code != 0, refused, failures)
                    self.assertEqual(any(named in f for f in failures), refused)

    def test_per_sample_cells_missing_zero_and_extra(self):
        cases = [({'S1': 1, 'S2': 1}, None), ({'S1_filtered': 1, 'S2_raw': 1}, None),
                 ({'all': 5}, None),
                 ({'S1': 1, 'S2': 0}, 'sample(s) with no cells after QC: S2'),
                 ({'S1': 1, 'S2': -1}, 'sample(s) with no cells after QC: S2'),
                 ({'S1': 1}, 'sample(s) with no cells after QC: S2'),
                 ({'S1': 1, 'S2': 1, 'S3': 1}, 'match no samplesheet sample: S3')]
        for after, named in cases:
            with self.subTest(after=after):
                self.summary(n_cells_out=5, n_clusters=2, cells_after_qc=after)
                code, failures = self.collect()
                if named is None:
                    self.assertEqual((code, failures), (0, []))
                else:
                    self.assertEqual(code, 1)
                    self.assertNamed(failures, named)


if __name__ == '__main__':
    unittest.main(verbosity=2)
