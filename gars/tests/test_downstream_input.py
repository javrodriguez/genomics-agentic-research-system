"""D-input and D-supplier: a downstream analysis finds its own input, and names its supplier, with
GARS's resolver (FIXES.md items D-input and D-supplier).

scrna-qc-cluster and spatial-cluster-count resolve their `h5ad` input themselves, by artifact type
from the OUTPUTS.tsv of the completed sub-stages before them (`_system/resolve_artifact.py`), so
no session has to carry a path over; an explicit `--h5ad` other than the one the resolver found is
refused (exit 2) and nothing is written. At collect, the history entry's "supplied by" line names
the sub-stage the resolver finds, never the agent's `--h5ad-from` / `--counts-from` words, and
`unknown` when it finds none.

Every case reuses the suite's real wrapper fixtures (test_manifest_groups) and adds only the
completed upstream sub-stage the resolver reads.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, module, run  # noqa: E402

GROUPS = module(GARS / 'tests/test_manifest_groups.py', 'downstream_input_groups')
MADE_UP = 'made-up-stage'


def complete(stage, outputs, files):
    """A completed sub-stage as the resolver reads it: STATUS COMPLETE and its OUTPUTS.tsv."""
    for rel in files:
        path = stage / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('fixture %s\n' % rel)
    with (stage / 'OUTPUTS.tsv').open('w') as fh:
        fh.write('# type\trole\tpath\n')
        for typ, rel in outputs:
            fh.write('%s\tnative\t%s\n' % (typ, rel))
    (stage / 'STATUS').write_text('COMPLETE 2026-10-17T00:00:00\n')


class DownstreamCase(object):
    KEY = None
    UPSTREAM = None
    OUTPUT = None
    FILES = ()
    WRONG = None

    def setUp(self):
        self.g = GROUPS.ManifestGroupsTests('test_model_sentinels_and_known_prefix')
        self.g.setUp()
        self.addCleanup(self.g.doCleanups)
        self.g.pipeline_fixtures()
        self.g.configure_wrapper(self.KEY, 'local', self.g.project)
        self.upstream = self.g.project / '02_bioinformatics' / self.g.assay / self.UPSTREAM
        complete(self.upstream, [('h5ad', self.OUTPUT)], self.FILES)
        self.resolved = str((self.upstream / self.OUTPUT).resolve())

    def wrapper(self, verb, *extra):
        result = run(self.g.wrapper_argv(verb, list(extra)), cwd=self.g.ws, env=self.g.env)
        return result.returncode, result.stdout.decode(), result.stderr.decode()

    def manifest(self):
        return json.loads(self.g.manifest_path.read_text())

    def test_prepare_without_a_path_uses_the_resolvers_artifact(self):
        code, out, err = self.wrapper('prepare')
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.manifest()['params']['h5ad'], self.resolved)

    def test_prepare_refuses_another_h5ad_from_the_same_run(self):
        """The plan's red case: a second, wrong object from the same run, as the agent's path."""
        self.assertEqual(self.wrapper('prepare', '--h5ad', self.resolved)[0], 0)
        before = self.g.manifest_path.read_bytes()
        code, out, err = self.wrapper('prepare', '--h5ad', self.upstream / self.WRONG)
        self.assertEqual(code, 2, out + err)
        self.assertIn(self.resolved, out, 'the refusal names the resolved input')
        self.assertEqual(self.g.manifest_path.read_bytes(), before, 'nothing written')

    def test_check_names_another_path_as_not_resolved(self):
        code, out, err = self.wrapper('check', '--h5ad', self.upstream / self.WRONG)
        self.assertEqual(code, 1, out + err)
        self.assertIn('input_not_resolved', [f['check'] for f in json.loads(out)['failures']])

    def test_the_resolvers_own_path_is_accepted(self):
        code, out, err = self.wrapper('prepare', '--h5ad', self.resolved)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(self.manifest()['params']['h5ad'], self.resolved)

    def test_collect_names_the_resolvers_supplier_never_the_flag(self):
        self.assertEqual(self.wrapper('prepare', '--h5ad', self.resolved)[0], 0)
        self.g.fake_wrapper_run()
        self.g.submit()
        code, out, err = self.wrapper('collect', '--h5ad-from', MADE_UP)
        self.assertEqual(code, 0, out + err)
        entry = json.loads(out)['history_entry']
        self.assertIn('Matrix supplied by: %s' % self.UPSTREAM, entry)
        self.assertNotIn(MADE_UP, out)
        self.assertIn('ignored', err)

    def test_an_explicit_path_with_nothing_resolved_names_no_supplier(self):
        """0305's residual (REVIEW-85a1b4a finding 2): nothing resolved at prepare, an explicit
        path used, an upstream completed before collect; the run did not read its artifact."""
        status = self.upstream / 'STATUS'
        kept = status.read_text()
        status.unlink()
        self.assertEqual(self.wrapper('prepare', '--h5ad', self.upstream / self.WRONG)[0], 0)
        status.write_text(kept)
        self.g.fake_wrapper_run()
        self.g.submit()
        code, out, err = self.wrapper('collect')
        self.assertEqual(code, 0, out + err)
        self.assertIn('Matrix supplied by: unknown', json.loads(out)['history_entry'])


class ScrnaQcClusterInputTests(DownstreamCase, unittest.TestCase):
    KEY = 'scrna-qc-cluster'
    UPSTREAM = '01_nfcore-scrnaseq-wrapper'
    OUTPUT = 'run/results/simpleaf/mtx_conversions/combined_filtered_matrix.h5ad'
    WRONG = 'run/results/simpleaf/mtx_conversions/S1/matrix.h5ad'
    FILES = (OUTPUT, WRONG)


class SpatialClusterCountInputTests(DownstreamCase, unittest.TestCase):
    KEY = 'spatial-cluster-count'
    UPSTREAM = '01_nfcore-spatialvi-wrapper'
    OUTPUT = 'run/results'
    WRONG = 'run/results-old'
    FILES = tuple('%s/S%d/data/S%d.h5ad' % (d, n, n) for d in (OUTPUT, WRONG) for n in range(1, 5))


class RnaseqDeSupplierTests(unittest.TestCase):
    """D-supplier for rnaseq-de: "Counts supplied by" names the resolver's producer only when
    prepare read that producer's artifact, and prepare refuses other counts once the resolver
    finds one (REVIEW-85a1b4a finding 2)."""

    REL = 'run/results/star_salmon/salmon.merged.gene_counts_length_scaled.tsv'

    def setUp(self):
        self.g = GROUPS.ManifestGroupsTests('test_model_sentinels_and_known_prefix')
        self.g.setUp()
        self.addCleanup(self.g.doCleanups)
        self.producer = self.g.project / '02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper'

    def run_through(self):
        self.g.prepare(); self.g.fake_run(); self.g.submit()

    def complete_producer(self, sha256=None):
        complete(self.producer, [('counts_gene', self.REL)], [self.REL])
        artifact = self.producer / self.REL
        artifact.write_bytes(Path(self.g.fixture.counts_native).read_bytes())
        if sha256:
            (self.producer / 'OUTPUTS.tsv').write_text(
                '# type\trole\tpath\tsha256\tartifact_class\n'
                'counts_gene\tnative\t%s\t%s\tdurable\n' % (self.REL, sha256))
        return artifact

    def prepare(self, counts):
        g = self.g
        (g.project / '_config/executor.yaml').write_text('name: local\n')
        result = run([sys.executable, g.fixture.de, 'prepare', '--project', g.project,
                      '--counts', counts, '--design',
                      g.project / '01_samplesheets/rnaseq_bulk_design.csv'], cwd=g.ws, env=g.env)
        return result.returncode, result.stdout.decode() + result.stderr.decode()

    def collect(self):
        g = self.g
        result = run([sys.executable, g.fixture.de, 'collect', '--project', g.project,
                      '--counts-from', MADE_UP], cwd=g.ws, env=g.env)
        self.assertEqual(result.returncode, 0, result.stdout.decode() + result.stderr.decode())
        return json.loads(result.stdout.decode())['history_entry'], result.stdout.decode()

    def test_the_resolvers_producer_never_the_flag(self):
        """The reviewer's reproduction: prepare read counts outside the project, and a producer
        completed afterwards did not supply them (glitch-b5's ruling 2 on REVIEW-85a1b4a)."""
        self.run_through()
        self.complete_producer()
        entry, out = self.collect()
        self.assertIn('Counts supplied by: unknown', entry)
        self.assertNotIn(MADE_UP, out)

    def test_no_producer_is_unknown_never_the_flag(self):
        self.run_through()
        entry, out = self.collect()
        self.assertIn('Counts supplied by: unknown', entry)
        self.assertNotIn(MADE_UP, out)

    def test_prepare_refuses_counts_other_than_the_resolvers(self):
        self.complete_producer()
        code, out = self.prepare(self.g.fixture.counts_native)
        self.assertEqual(code, 2, out)
        self.assertIn(str((self.producer / self.REL).resolve()), out)
        self.assertFalse((self.g.stage / 'reproducibility/manifest.json').exists(), 'nothing written')
        self.assertFalse((self.g.stage / 'submit.sh').exists(), 'nothing written')

    def test_the_producer_is_named_when_prepare_read_its_artifact(self):
        artifact = self.complete_producer()
        code, out = self.prepare(artifact)
        self.assertEqual(code, 0, out)
        self.g.fake_run(); self.g.submit()
        entry, out = self.collect()
        self.assertIn('Counts supplied by: 01_nfcore-rnaseq-wrapper', entry)
        self.assertNotIn(MADE_UP, out)

    def test_a_producer_whose_recorded_sha256_differs_is_not_named(self):
        artifact = self.complete_producer(sha256='0' * 64)
        code, out = self.prepare(artifact)
        self.assertEqual(code, 0, out)
        self.g.fake_run(); self.g.submit()
        entry, out = self.collect()
        self.assertIn('Counts supplied by: unknown', entry)

if __name__ == '__main__':
    unittest.main()
