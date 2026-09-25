"""R-164 class 5: every collect gate and count check, on both sides of its boundary (0087).

Collect is driven through each wrapper's cmd_collect with the lifecycle writers stubbed
(they have their own suites); the observation is the exit code and the named failures.
"""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module
import integrity
import wrapperlib as wl

WRAPPERS = GARS / '_system/wrappers'


def wrapper(directory):
    source = WRAPPERS / directory / (directory.replace('-', '_') + '.py')
    return module(source, 'r164_bounds_' + directory.replace('-', '_'))


class CollectHarness(unittest.TestCase):
    directory = None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-bounds-')
        self.project = Path(self._tmp.name).resolve() / 'project'
        self.mod = wrapper(self.directory)
        self.stage = self.project / '02_bioinformatics' / self.mod.ASSAY / self.mod.SUBSTAGE
        (self.stage / 'run').mkdir(parents=True)
        (self.stage / 'run/.gars_run_complete').write_text('done\n')
        (self.project / '01_samplesheets').mkdir()
        (self.project / '_config').mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative, data):
        path = self.stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def sheet(self, text):
        (self.project / '01_samplesheets' / ('%s_samplesheet.csv' % self.mod.ASSAY)).write_text(text)

    def collect(self):
        """-> (exit code, failure details)."""
        failed = []

        def collect_failure(stage, result, code=1, model='unknown'):
            failed.extend(f['detail'] for f in result['failures'])
            return code

        args = argparse.Namespace(project=str(self.project), model='none', h5ad_from=None,
                                  counts_from=None)
        with patch.object(wl, 'require_collect_config'), \
                patch.object(wl, 'collect_failure', collect_failure), \
                patch.object(wl, 'complete_manifest'), patch.object(wl, 'write_status'), \
                patch.object(wl, 'harvest_cache', return_value='none'), \
                contextlib.redirect_stdout(io.StringIO()):
            code = self.mod.cmd_collect(args)
        return code, failed

    def assertNamed(self, failures, text):
        self.assertTrue(any(text in f for f in failures), failures)


class SpatialClusterCountBoundaryTests(CollectHarness):
    directory = 'spatial-cluster-count'

    def setUp(self):
        super().setUp()
        self.sheet('sample,spaceranger_dir\ns1,a\ns2,b\n')
        self.write('run/report.md', b'# report\n')

    def gate(self, samples, rows):
        self.write('run/summary.json', json.dumps(
            {'obs_column': 'clusters', 'samples': samples}).encode())
        table = 'sample\tcluster\tn_spots\n' + ''.join('%s\t%s\t%s\n' % r for r in rows)
        self.write('run/clusters.tsv', table.encode())
        return self.collect()

    def test_spot_count_boundary(self):
        other = {'s2': {'n_obs': 5, 'n_clusters': 2}}
        other_rows = [('s2', '0', 2), ('s2', '1', 3)]
        for n_obs, refused in ((1, False), (0, True), (-1, True)):
            with self.subTest(n_obs=n_obs):
                samples = dict(other, s1={'n_obs': n_obs, 'n_clusters': 1})
                code, failures = self.gate(samples, [('s1', '0', n_obs)] + other_rows)
                self.assertEqual(code != 0, refused, failures)
                self.assertEqual(any('sample s1 has no spots' in f for f in failures), refused)

    def test_cluster_count_boundary(self):
        other = {'s2': {'n_obs': 5, 'n_clusters': 1}}
        for n_clusters, rows, refused in ((1, [('s1', '0', 4)], False), (0, [], True),
                                          (-1, [], True)):
            with self.subTest(n_clusters=n_clusters):
                samples = dict(other, s1={'n_obs': 4, 'n_clusters': n_clusters})
                code, failures = self.gate(samples, rows + [('s2', '0', 5)])
                self.assertEqual(code != 0, refused, failures)
                self.assertEqual(any('sample s1 has no clusters' in f for f in failures), refused)

    def test_counts_must_be_integers(self):
        for value in (None, True, 1.0, '3'):
            with self.subTest(value=value):
                entry = {'n_clusters': 1} if value is None else {'n_obs': value, 'n_clusters': 1}
                code, failures = self.gate({'s1': entry, 's2': {'n_obs': 1, 'n_clusters': 1}},
                                           [('s1', '0', 1), ('s2', '0', 1)])
                self.assertEqual(code, 1)
                self.assertNamed(failures, 'sample s1: n_obs in summary.json is not an integer')

    def test_sample_set_missing_and_extra(self):
        one = {'n_obs': 1, 'n_clusters': 1}
        code, failures = self.gate({'s1': one}, [('s1', '0', 1)])
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'samplesheet sample(s) with no count in summary.json: s2')
        code, failures = self.gate({'s1': one, 's2': one, 's3': one},
                                   [('s1', '0', 1), ('s2', '0', 1), ('s3', '0', 1)])
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'the samplesheet does not list: s3')

    def test_table_must_agree_with_summary(self):
        samples = {'s1': {'n_obs': 3, 'n_clusters': 2}, 's2': {'n_obs': 1, 'n_clusters': 1}}
        code, failures = self.gate(samples, [('s1', '0', 1), ('s1', '1', 2), ('s2', '0', 1)])
        self.assertEqual((code, failures), (0, []))
        code, failures = self.gate(samples, [('s1', '0', 1), ('s1', '1', 1), ('s2', '0', 1)])
        self.assertNamed(failures, 'clusters.tsv spots for s1 sum to 2 but summary.json says n_obs 3')
        code, failures = self.gate(samples, [('s1', '0', 3), ('s2', '0', 1)])
        self.assertNamed(failures, 'clusters.tsv has 1 row(s) for s1 but summary.json says 2')

    def test_resolve_inputs_byte_boundary(self):
        results = self.project / 'results'
        for sample, size in (('s1', 1), ('s2', 0)):
            path = results / sample / 'data' / ('%s.h5ad' % sample)
            path.parent.mkdir(parents=True)
            path.write_bytes(b'x' * size)
        fails = []
        pairs = self.mod.resolve_inputs(str(results), ['s1', 's2'], fails)
        self.assertEqual([s for s, _ in pairs], ['s1'])
        self.assertEqual(len(fails), 1)
        self.assertIn('s2 (expected', fails[0]['detail'])
        single = self.project / 'one.h5ad'
        for size, samples, accepted in ((1, ['s1'], True), (0, ['s1'], False),
                                        (1, ['s1', 's2'], False)):
            with self.subTest(size=size, samples=samples):
                single.write_bytes(b'x' * size)
                fails = []
                pairs = self.mod.resolve_inputs(str(single), samples, fails)
                self.assertEqual(pairs == [('s1', single)], accepted, fails)
                self.assertEqual(bool(fails), not accepted)


class SpatialviCollectBoundaryTests(CollectHarness):
    directory = 'nfcore-spatialvi-wrapper'

    def setUp(self):
        super().setUp()
        self.sheet('sample,spaceranger_dir\ns1,a\ns2,b\n')
        (self.project / '_config/spatialvi.yaml').write_text('qc:\n  min_counts: 10\n')
        self.write('run/results/multiqc/multiqc_report.html', b'<html/>')
        for s in ('s1', 's2'):
            self.write('run/results/%s/data/%s.h5ad' % (s, s), b'h')
            self.write('run/results/%s/reports/report-%s.html' % (s, s), b'r')

    def test_all_present_passes(self):
        self.assertEqual(self.collect(), (0, []))

    def test_processed_object_byte_boundary_and_raw_never_substitutes(self):
        self.write('run/results/s1/data/s1-raw.h5ad', b'raw')
        self.write('run/results/s1/data/s1.h5ad', b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'no processed <sample>.h5ad under')
        self.assertNamed(failures, 's1 HAS a -raw.h5ad')
        (self.stage / 'run/results/s1/data/s1.h5ad').unlink()
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 's1 HAS a -raw.h5ad')

    def test_report_and_multiqc_byte_boundary(self):
        self.write('run/results/s2/reports/report-s2.html', b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'no per-sample report under')
        self.write('run/results/s2/reports/report-s2.html', b'r')
        self.write('run/results/multiqc/multiqc_report.html', b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'multiqc_report.html')


class ScrnaseqCollectBoundaryTests(CollectHarness):
    directory = 'nfcore-scrnaseq-wrapper'

    def setUp(self):
        super().setUp()
        self.sheet('sample,fastq_1,fastq_2\ns1,a,b\ns2,c,d\n')
        (self.project / '_config/scrnaseq.yaml').write_text('aligner: star\n')
        self.write('run/results/multiqc/multiqc_report.html', b'<html/>')
        for aligner in ('star', 'simpleaf'):
            base = 'run/results/%s/mtx_conversions/' % aligner
            self.write(base + 'combined_filtered_matrix.h5ad', b'c')
            for s in ('s1', 's2'):
                self.write(base + '%s/%s_matrix.h5ad' % (s, s), b'm')

    def test_combined_matrix_byte_boundary(self):
        self.assertEqual(self.collect(), (0, []))
        self.write('run/results/star/mtx_conversions/combined_filtered_matrix.h5ad', b'')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'combined_filtered_matrix.h5ad is zero bytes')

    def test_the_selected_aligners_matrices_are_the_ones_gated(self):
        (self.stage / 'run/results/star/mtx_conversions/s2/s2_matrix.h5ad').unlink()
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'for sample(s): s2')
        (self.project / '_config/scrnaseq.yaml').write_text('aligner: simpleaf\n')
        self.assertEqual(self.collect(), (0, []))
        (self.stage / 'run/results/simpleaf/mtx_conversions/combined_filtered_matrix.h5ad').unlink()
        self.write('run/results/simpleaf/mtx_conversions/combined_raw_matrix.h5ad', b'raw')
        code, failures = self.collect()
        self.assertEqual(code, 1)
        self.assertNamed(failures, 'the raw matrix is never substituted')


class RnaseqDeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-bounds-')
        self.root = Path(self._tmp.name).resolve()
        self.de = wrapper('rnaseq-de')

    def tearDown(self):
        self._tmp.cleanup()

    def level_failures(self, design_rows):
        project = self.root / 'project'
        (project / '_config').mkdir(parents=True, exist_ok=True)
        (project / '_config/rnaseq_bulk.yaml').write_text(
            'de:\n  formula: ~condition\n  contrast: condition,treated,control\n')
        design = project / 'design.csv'
        design.write_text('sample_id,condition\n' +
                          ''.join('%s,%s\n' % r for r in design_rows))
        counts = project / 'counts.tsv'
        counts.write_text('gene_id\t' + '\t'.join(s for s, _ in design_rows) + '\n')
        fails = self.de.run_checks(project, counts, design)[0]
        return [f['detail'] for f in fails if 'contrast level' in f['detail']]

    def test_contrast_level_needs_two_samples(self):
        self.assertEqual(self.level_failures(
            [('a', 'treated'), ('b', 'treated'), ('c', 'control'), ('d', 'control')]), [])
        failures = self.level_failures([('a', 'treated'), ('c', 'control'), ('d', 'control')])
        self.assertEqual(len(failures), 1)
        self.assertIn("'treated' has 1 sample(s)", failures[0])
        failures = self.level_failures([('a', 'treated'), ('b', 'treated'), ('c', 'control')])
        self.assertEqual(len(failures), 1)
        self.assertIn("'control' has 1 sample(s)", failures[0])
        failures = self.level_failures([('a', 'treated'), ('b', 'treated'), ('c', 'other')])
        self.assertIn("'control' has 0 sample(s)", failures[0])

    def table(self, rows, header='gene,pvalue,padj'):
        path = self.root / 'de.csv'
        path.write_text(header + '\n' + ''.join('g%d,%s,%s\n' % (i, p, q)
                                                for i, (p, q) in enumerate(rows)))
        return [f['detail'] for f in self.de.check_table(path)]

    def test_bh_tolerance_on_both_sides(self):
        p = [0.01, 0.02, 0.03, 0.04]
        bh = 0.04
        self.assertEqual(self.table([(x, bh) for x in p]), [])
        inside = bh * (1 + 0.5e-4)
        outside = bh * (1 + 2e-4)
        self.assertEqual(self.table([(x, bh) for x in p[:-1]] + [(p[-1], inside)]), [])
        self.assertEqual(self.table([(x, bh) for x in p[:-1]] + [(p[-1], outside)]),
                         ['padj differs from BH'])

    def test_probability_order_and_range(self):
        self.assertEqual(self.table([(1.0, 1.0)]), [])
        self.assertEqual(self.table([(0.0, 0.0)]), [])
        self.assertEqual(self.table([(0.5, 0.4999)]), ['padj below pvalue or invalid probabilities'])
        self.assertEqual(self.table([(0.5, 1.0001)]), ['padj below pvalue or invalid probabilities'])
        self.assertEqual(self.table([(-0.0001, 0.1)]), ['padj below pvalue or invalid probabilities'])

    def test_uncorrected_and_untested_tables(self):
        self.assertEqual(self.table([(0.2, 0.2)]), [])
        self.assertEqual(self.table([(0.2, 0.2), (0.3, 0.3)]), ['raw p-values without correction'])
        self.assertEqual(self.table([(1, 1), (1, 1)]), [])
        self.assertEqual(self.table([('NA', 'NA')]), ['no tested rows'])
        self.assertEqual(self.table([('NA', 0.1)]), ['padj present without pvalue'])
        self.assertEqual(self.table([], header='gene,pvalue'),
                         ['missing or ambiguous probability columns'])


class ScalarBoundaryTests(unittest.TestCase):
    def test_commit_pin_length_boundaries(self):
        for version, expected in (('abcdef1', True), ('abcdef', False), ('a' * 40, True),
                                  ('a' * 41, False), ('ABCDEF1', True), ('abcdefg', False),
                                  ('2.1.2', False), ('4.2.0', False)):
            with self.subTest(version=version):
                self.assertEqual(wl.is_commit_pin(version), expected)

    def test_login_node_threshold(self):
        limit = integrity.LOGIN_NODE_BYTES
        self.assertFalse(integrity.needs_scheduling(limit - 1))
        self.assertFalse(integrity.needs_scheduling(limit))
        self.assertTrue(integrity.needs_scheduling(limit + 1))
        per_minute = integrity.THROUGHPUT_BYTES_PER_S * 60
        self.assertEqual(integrity.estimate_minutes(0), 1)
        self.assertEqual(integrity.estimate_minutes(per_minute * 7), 7)

    def test_run_dir_populated_boundary(self):
        with tempfile.TemporaryDirectory(prefix='gars-bounds-') as tmp:
            stage = Path(tmp)
            def fails(refresh=False):
                found = []
                wl.check_run_dir(stage, found, resume_refresh=refresh)
                return found
            self.assertEqual(fails(), [])
            (stage / 'run').mkdir()
            self.assertEqual(fails(), [])
            (stage / 'run/partial').write_text('x')
            self.assertEqual(len(fails()), 1)
            self.assertEqual(len(fails(refresh=True)), 1)
            (stage / 'STATUS').write_text('FAILED 2026-01-01T00:00:00Z\n')
            self.assertEqual(len(fails(refresh=True)), 1)
            (stage / 'run/.nextflow').mkdir()
            self.assertEqual(fails(refresh=True), [])
            self.assertEqual(len(fails()), 1)
            (stage / 'run/.gars_run_complete').write_text('done\n')
            self.assertEqual(fails(), [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
