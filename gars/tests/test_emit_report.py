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
from urllib.parse import quote

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

    def refuse(self, code, transport=replay):
        for exists in (False, True):
            if exists:
                self.out.write_bytes(b'previous report\n')
            rc, output = self.emit(transport)
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
        for reference in ('doi:invalid', 'https://doi.org/invalid', 'DOI: missing',
                          'DOI 10/x', 'doi 10/abcfake', 'DOI 10.123/fake',
                          'Doi\t10/x', 'DOI\n10.123/fake'):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                self.refuse('citation_unverifiable')

        # Ruling 7: separator spelling cannot bypass an explicit DOI token.
        # Include concatenation and underscores as lexical separators too.
        separators = ('', ' ', '  ', '-', ':', '=', '_')
        enclosures = (('', ''), ('{', '}'), ('[', ']'), ('(', ')'))
        references = ['doi = {10/abcfake}', 'doi=10/abcfake', 'DOI-10/abcfake']
        for left in separators:
            for opening, closing in enclosures:
                for right in separators:
                    for token in ('10/abcfake', '10.123/fake'):
                        references.append('doi' + left + opening + right + token + closing)
        # Neither adjacency nor order is required by the general rule.
        references.extend(('Title mentions DOI; pages 10. No identifier supplied',
                           'Pages 10. Journal of Doi Studies',
                           '10/abcfake precedes the DOI token'))
        for reference in references:
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                # These contain no parseable DOI; refuse without a network lookup.
                with patch.object(emitter.evidence_check.resolve_citation, 'resolve') as lookup:
                    self.refuse('citation_unverifiable')
                    lookup.assert_not_called()

        # Ordinary title/journal prose plus a page number and no identifier is
        # intentionally unverifiable under ruling 7, even if bibliographically
        # legitimate: the general rule requires a parseable DOI. Adding the
        # valid recorded DOI must emit and actually resolve that identifier.
        for prose in ('Title mentions DOI; pages 10.', 'Journal of Doi Studies, p. 10.'):
            self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = prose
            self.save()
            if self.out.exists():
                self.out.unlink()
            self.refuse('citation_unverifiable')
            self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = (
                prose + ' Registered reference: ' + generator.REAL_DOI)
            self.save()
            requests = []
            def recorded(url):
                requests.append(url)
                return replay(url)
            self.assertEqual(self.emit(recorded), (0, ''))
            self.assertEqual(requests, [
                'https://api.crossref.org/works/' + quote(generator.REAL_DOI, safe='')])

        reference = '10.1000.10/gars-fabricated-subdivided'
        requests = []
        def not_found(url):
            requests.append(url)
            return (404, b'{}') if 'crossref' in url else (404, b'{"responseCode":100}')
        self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
        self.save()
        self.out.unlink()
        self.refuse('citation_unresolved', transport=not_found)
        self.assertEqual(requests, [
            'https://api.crossref.org/works/' + quote(reference, safe=''),
            'https://doi.org/api/handles/' + quote(reference, safe='')] * 2)

        for reference in ('(doi:' + generator.REAL_DOI + ')',
                          '[doi:' + generator.REAL_DOI + ']',
                          '(doi:' + generator.REAL_DOI + ').',
                          '[doi:' + generator.REAL_DOI + ';]'):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                self.assertEqual(self.emit(), (0, ''))

        # Brackets inside a suffix are meaningful; discard only unmatched closers.
        for identifier in ('10.1000.10/synthetic(part)', '10.1000.10/synthetic[part]'):
            for reference in (identifier, '(doi:' + identifier + ')'):
                with self.subTest(reference=reference):
                    requests = []
                    def resolved(url):
                        requests.append(url)
                        return 200, b'{"status":"ok","message":{}}'
                    self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                    self.save()
                    self.assertEqual(self.emit(resolved), (0, ''))
                    self.assertEqual(requests, [
                        'https://api.crossref.org/works/' + quote(identifier, safe='')])

        for reference in ('Doi T, Sato K (2019) J Synth Biol 3:1-9', 'DOI missing'):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                with patch.object(emitter.evidence_check.resolve_citation, 'resolve') as lookup:
                    self.assertEqual(self.emit(), (0, ''))
                    lookup.assert_not_called()

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
        for original, parent_key in ((artifact, 'artifact'), (source, 'source')):
            for key in ('id', 'kind', 'relation'):
                for value in ('results/fabricated_output.tsv', '', None, True, 1.5, [], {}):
                    cases.append(dict(original, **{key: value}))
            for key, value in (('id', '1'), ('kind', 'Computational'),
                               ('relation', 'Supports')):
                cases.append(dict(original, **{key: value}))
            cases.append(dict(original, path='results/fabricated_output.tsv'))
            extra_parent = copy.deepcopy(original)
            extra_parent[parent_key]['extra_path'] = 'results/fabricated_output.tsv'
            cases.append(extra_parent)
            for key in original:
                missing = copy.deepcopy(original)
                del missing[key]
                cases.append(missing)
            for key in original[parent_key]:
                missing = copy.deepcopy(original)
                del missing[parent_key][key]
                cases.append(missing)
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
        # Every BASE kind/relation remains legal for either evidence parent.
        for kind in ('computational', 'statistical', 'literature'):
            for relation in ('supports', 'contradicts', 'absent'):
                with self.subTest(kind=kind, relation=relation):
                    for evidence in self.snapshot['claims'][0]['evidence']:
                        evidence['kind'] = kind
                        evidence['relation'] = relation
                    self.save()
                    self.assertEqual(self.emit(), (0, ''))

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
