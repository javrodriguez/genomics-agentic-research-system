"""Preflight refusal preserves output; a single export feeds check and render."""
import contextlib
import copy
import io
import json
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import module, REPO
from test_citation_resolution import replay
emitter = module(REPO / 'gars/_system/claims/emit_report.py', 'report_emit_test')
generator = module(REPO / 'benchmarks/defects/generate.py', 'report_generator')


class EmitReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='emit-report-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.snapshot = generator.claims(self.root)
        self.out = self.root / 'out.md'

    def argv(self):
        return ['--snapshot', str(self.root / 'snapshot.json'), '--manifest', str(self.root / 'manifest.json'),
                '--project', str(self.root / 'project'), '--out', str(self.out)]

    def save(self):
        generator.write_json(self.root / 'snapshot.json', self.snapshot)

    def emit(self, transport=replay):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = emitter.main(self.argv(), transport=transport)
        return code, output.getvalue()

    def refuse(self, code):
        for exists in (False, True):
            if exists:
                self.out.write_bytes(b'previous report\n')
            rc, output = self.emit()
            self.assertNotEqual(rc, 0)
            self.assertIn(code, output)
            if exists:
                self.assertEqual(self.out.read_bytes(), b'previous report\n')
            else:
                self.assertFalse(self.out.exists())

    def test_missing_path(self):
        self.snapshot['claims'][0]['evidence'][0]['artifact']['path'] = 'invented.csv'
        self.save()
        self.refuse('evidence_missing')

    def test_changed_hash(self):
        (self.root / 'project/evidence.tsv').write_text('changed\n')
        self.refuse('evidence_hash_mismatch')

    def test_fabricated_doi(self):
        self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = generator.FAKE_DOI
        self.save()
        self.refuse('citation_unresolved')

    def test_doi_reference_forms(self):
        for reference in ('http://doi.org/' + generator.FAKE_DOI,
                          'https://www.doi.org/' + generator.FAKE_DOI,
                          'doi.org/' + generator.FAKE_DOI,
                          'DOI ' + generator.FAKE_DOI,
                          'Smith J. (2020) Nature. doi:' + generator.FAKE_DOI):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                self.refuse('citation_unresolved')
        for reference in ('doi:invalid', 'https://doi.org/invalid', 'DOI missing'):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                self.refuse('citation_unverifiable')

    def test_malformed_evidence(self):
        artifact, source = copy.deepcopy(self.snapshot['claims'][0]['evidence'])
        cases = [dict(artifact, artifact=None, path='results/fabricated_output.tsv'),
                 dict(artifact, artifact={}), dict(source, source={}),
                 dict(artifact, source=source['source'], source_id=1),
                 dict(artifact, artifact_id=2), dict(artifact, artifact_id=None),
                 dict(source, source_id=2), dict(source, source_id=None),
                 dict(source, artifact_id=1), dict(artifact, source_id=1),
                 dict(source, source={'id': 1, 'reference': None}),
                 dict(artifact, artifact={'id': 1, 'path': 'evidence.tsv'}),
                 dict(source, source={'id': 1, 'reference': ''})]
        for evidence in cases:
            with self.subTest(evidence=evidence):
                self.snapshot['claims'][0]['evidence'] = [evidence]
                self.save()
                if self.out.exists():
                    self.out.unlink()
                self.refuse('evidence_missing')

    def test_path_containment(self):
        artifact = self.snapshot['claims'][0]['evidence'][0]['artifact']
        inside = self.root / 'project/evidence.tsv'
        outside = self.root / 'outside.tsv'
        outside.write_bytes(inside.read_bytes())
        link = self.root / 'project/link.tsv'
        link.symlink_to(outside)
        for path in (str(inside.resolve()), os.path.join(os.pardir, 'outside.tsv'), 'link.tsv'):
            artifact['path'] = path
            self.save()
            self.out.unlink() if self.out.exists() else None
            self.refuse('evidence_missing')

    def test_clean_bytes_and_snapshot_shape(self):
        self.assertEqual(self.emit()[0], 0)
        baseline = self.root / 'baseline.md'
        result = subprocess.run([sys.executable, str(REPO / 'gars/_system/claims/render_report.py'),
                                 '--snapshot', str(self.root / 'snapshot.json'),
                                 '--manifest', str(self.root / 'manifest.json'), '--out', str(baseline)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.out.read_bytes(), baseline.read_bytes())

    def test_preflight_before_renderer(self):
        with patch.object(emitter.evidence_check, 'main', return_value=1), patch.object(emitter.subprocess, 'run') as run:
            self.assertEqual(self.emit()[0], 1)
            run.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_database_export_once_same_snapshot(self):
        argv = self.argv()
        argv[:2] = ['--from-db', '1']
        checked, rendered = [], []
        real_check = emitter.evidence_check.main
        real_run = subprocess.run
        def check(args, transport=None):
            checked.append(Path(args[args.index('--snapshot') + 1]))
            return real_check(args, transport=transport)
        def render(args, **kwargs):
            self.assertNotIn('--from-db', args)
            rendered.append(Path(args[args.index('--snapshot') + 1]))
            self.assertEqual(json.loads(rendered[-1].read_text()), self.snapshot)
            return real_run(args, **kwargs)
        with patch.object(emitter.render_report, 'database_snapshot', return_value=self.snapshot) as export, \
                patch.object(emitter.evidence_check, 'main', side_effect=check), \
                patch.object(emitter.subprocess, 'run', side_effect=render):
            self.assertEqual(emitter.main(argv, transport=replay), 0)
        export.assert_called_once_with('1')
        self.assertEqual(checked, rendered)
        self.assertEqual(checked[0].parent, self.out.parent)
        self.assertFalse(checked[0].exists())
        self.assertTrue(self.out.exists())

    def test_network_failure_refuses(self):
        def failed(url):
            raise OSError('offline')
        rc, output = self.emit(failed)
        self.assertEqual(rc, 1)
        self.assertIn('citation_unverifiable', output)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
