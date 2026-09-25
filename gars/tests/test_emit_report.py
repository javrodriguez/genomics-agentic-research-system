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


def doi_separator_forms():
    """The same 392 generated malformed forms exercise both identifier paths."""
    references = []
    separators = ('', ' ', '  ', '-', ':', '=', '_')
    enclosures = (('', ''), ('{', '}'), ('[', ']'), ('(', ')'))
    for left in separators:
        for opening, closing in enclosures:
            for right in separators:
                for token in ('10/abcfake', '10.123/fake'):
                    references.append('doi' + left + opening + right + token + closing)
    return references


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
        references = ['doi = {10/abcfake}', 'doi=10/abcfake', 'DOI-10/abcfake']
        references.extend(doi_separator_forms())
        # Neither adjacency nor order is required by the general rule.
        references.extend(('Title mentions DOI; pages 10. No identifier supplied',
                           'Pages 10. Journal of Doi Studies',
                           '10/abcfake precedes the DOI token',
                           'x_doi=10/abcfake', 'ref_doi=10/abcfake',
                           'x_doi:10/abcfake', 'ref_doi_10/abcfake'))
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
        # valid recorded DOI still resolves, but cannot hide the remaining
        # marker and page token under item 8's residual-text rule.
        # The lane's 0130 and 0131 decisions change the with-DOI half to emit.
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
            with self.subTest(residual_prose=prose):
                self.out.unlink()
                self.assertEqual(self.emit(recorded), (0, ''))
                self.assertTrue(self.out.is_file())
                self.assertEqual(requests, [
                    'https://api.crossref.org/works/' + quote(generator.REAL_DOI, safe='')])

        # E1 F2: a real DOI cannot conceal a second, unparseable identifier.
        for reference in ('doi:' + generator.REAL_DOI + '; doi = {10/abcfake}',
                          'DOI-10/abcfake; registered DOI: ' + generator.REAL_DOI):
            with self.subTest(mixed_reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                self.refuse('citation_unverifiable')

        # E1 F1: a year ending in 10 is not a numeric DOI token, even when
        # an author or title supplies the marker word. No lookup is needed.
        for reference in ('Doi, T. (2010). Synthetic biology methods.',
                          'Smith, J. (2010). Doi in synthetic biology.',
                          'Doi, T. 2010. Synthetic biology methods.',
                          'Smith, J. 2010. Doi in synthetic biology.',
                          'Doi T. 2010/2011. Synthetic methods.'):
            with self.subTest(year_reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                with patch.object(emitter.evidence_check.resolve_citation, 'resolve') as lookup:
                    self.assertEqual(self.emit(), (0, ''))
                    lookup.assert_not_called()

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
                          '[doi:' + generator.REAL_DOI + ';]',
                          '{doi:' + generator.REAL_DOI + '}',
                          'doi = {' + generator.REAL_DOI + '},',
                          '{doi:' + generator.REAL_DOI + ';}'):
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                self.assertEqual(self.emit(), (0, ''))

        # Brackets inside a suffix are meaningful; discard only unmatched closers.
        for identifier in ('10.1000.10/synthetic(part)', '10.1000.10/synthetic[part]',
                           '10.1000.10/synthetic{part}'):
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

    def test_doi_clean_reference_corpus(self):
        styles = (
            ('PubMed/NLM', 'Smith J. Synthetic methods. Nature. 2011;8(5):321-326.'),
            ('Vancouver', 'Smith J. Synthetic methods. Nature. 2011;8:321-6.'),
            ('APA 7', 'Smith, J. (2011). Synthetic methods. Nature, 8(5), 321-326.'),
            ('BibTeX', '@article{smith2011, author = {Smith, J.}, title = {Synthetic methods},'),
            ('Harvard', "Smith, J. (2011) 'Synthetic methods', Nature, 8, pp. 321-326. Accessed 3 March 2020."))
        forms = ('doi:{}', 'doi: {}', 'DOI {}', 'https://doi.org/{}',
                 'http://dx.doi.org/{}', 'doi = {{{}}},',
                 'url = {{https://doi.org/{}}},', '{}')
        stray_numbers = ('Epub 2011 Apr 10.', 'vol. 10.', 'pages 10.1-10.9',
                         'accessed 10/03/2020')
        for style, citation in styles:
            for form in forms:
                for stray in stray_numbers:
                    for before in (False, True):
                        for prose in ('', 'Doi T. Author contribution.', 'Title: Doi studies.'):
                            identifier = form.format(generator.REAL_DOI)
                            parts = (stray, identifier) if before else (identifier, stray)
                            reference = ' '.join((citation, prose) + parts)
                            with self.subTest(style=style, reference=reference):
                                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                                self.save()
                                requests = []
                                def recorded(url):
                                    requests.append(url)
                                    return replay(url)
                                self.assertEqual(self.emit(recorded), (0, ''))
                                self.assertTrue(self.out.is_file())
                                self.assertEqual(requests, [
                                    'https://api.crossref.org/works/' + quote(generator.REAL_DOI, safe='')])

        # C1 F1: Unicode words stop both walks; numeric boundaries stay ASCII.
        references = [
            '\u738b. \u65b9\u6cd5. DOI:' + generator.REAL_DOI + '. \u8bbf\u95ee\u4e8e 10/03/2020.',
            'DOI: ' + generator.REAL_DOI + ' (\u0434\u0430\u0442\u0430 \u043e\u0431\u0440\u0430\u0449\u0435\u043d\u0438\u044f: 10/03/2020).',
            'doi:' + generator.REAL_DOI + ' \u95b2\u89a7\u65e5 10/03/2020',
            'doi: ' + generator.REAL_DOI + ' \u03c3\u03b5\u03bb. 10.1-10.9']
        # Move B1's three guards here under the lane's C1 acceptance ruling.
        malformed = 'doi: ' + chr(233) + '10/abcfake'
        references.extend((malformed + '; doi:' + generator.REAL_DOI,
                           'doi:' + generator.REAL_DOI + '; ' + malformed,
                           'doi:' + generator.REAL_DOI + '; ' + chr(233) + ' 10/abcfake'))
        for reference in references:
            with self.subTest(unicode_word=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                requests = []
                def recorded(url):
                    requests.append(url)
                    return replay(url)
                self.assertEqual(self.emit(recorded), (0, ''))
                self.assertTrue(self.out.is_file())
                self.assertEqual(requests, [
                    'https://api.crossref.org/works/' + quote(generator.REAL_DOI, safe='')])

        # Internal markers never existed in the base's residual reference.
        identifier = '10.1000/synthetic_doi:10/abcfake'
        for reference in (identifier, identifier + '; 10/fake', 'doi:' + identifier,
                          'doi:' + identifier + '; pages 10.',
                          'doi:' + generator.REAL_DOI + '; ' + identifier):
            with self.subTest(internal_marker=reference):
                requests = []
                def resolved(url):
                    requests.append(url)
                    return 200, b'{"status":"ok","message":{}}'
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                self.assertEqual(self.emit(resolved), (0, ''))
                expected = [identifier]
                if generator.REAL_DOI in reference:
                    expected.insert(0, generator.REAL_DOI)
                self.assertEqual(requests, [
                    'https://api.crossref.org/works/' + quote(value, safe='') for value in expected])

        # Ruling 0134: a bound suffix number belongs to its parsed identifier.
        identifier = '10.1000.10/synthetic-doi-10.5'
        reference = 'doi:doi' + identifier
        requests = []
        def resolved(url):
            requests.append(url)
            return 200, b'{"status":"ok","message":{}}'
        self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
        self.save()
        with self.subTest(bound_inside_identifier=reference):
            self.assertEqual(self.emit(resolved), (0, ''))
            self.assertTrue(self.out.is_file())
            self.assertEqual(requests, [
                'https://api.crossref.org/works/' + quote(identifier, safe='')])

        # Consuming that span must still chain to a malformed trailing number.
        self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference + ' 10/fake'
        self.save()
        if self.out.exists():
            self.out.unlink()
        requests[:] = []
        self.refuse('citation_unverifiable', transport=resolved)
        self.assertEqual(requests, [
            'https://api.crossref.org/works/' + quote(identifier, safe='')] * 2)

    def test_doi_fabricated_beside_verified(self):
        forms = doi_separator_forms()
        self.assertEqual(len(forms), 392)
        references = []
        for malformed in forms:
            for before in (False, True):
                verified = 'doi:' + generator.REAL_DOI
                parts = (malformed, verified) if before else (verified, malformed)
                references.append('; '.join(parts))
        references.extend(('doi:' + generator.REAL_DOI + '; 10/abcfake',
                           'doi:' + generator.REAL_DOI + ', 10.123/fake',
                           'doi:' + generator.REAL_DOI + '; ' + generator.REAL_DOI + '; 10/abcfake'))
        for reference in references:
            with self.subTest(reference=reference):
                self.snapshot['claims'][0]['evidence'][1]['source']['reference'] = reference
                self.save()
                if self.out.exists():
                    self.out.unlink()
                requests = []
                def recorded(url):
                    requests.append(url)
                    return replay(url)
                self.refuse('citation_unverifiable', transport=recorded)
                self.assertEqual(requests, [
                    'https://api.crossref.org/works/' + quote(generator.REAL_DOI, safe='')]
                    * (2 * reference.count(generator.REAL_DOI)))

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
