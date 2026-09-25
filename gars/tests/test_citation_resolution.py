"""DOI replay contract; only this test module reads GARS_NETWORK_TESTS."""
import ast
import contextlib
import hashlib
import io
import inspect
import json
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import module, REPO

resolver = module(REPO / 'gars/_system/resolve_citation.py', 'citation_test_resolver')
RECORDS = json.loads((REPO / 'gars/tests/fixtures/citations/responses.json').read_text())


def replay(url):
    matches = [r for r in RECORDS['responses'] if r['request_url'] == url]
    if len(matches) != 1:
        raise ValueError('unrecorded request')
    record = matches[0]
    body = record['body'].encode('utf-8')
    if hashlib.sha256(body).hexdigest() != record['body_sha256']:
        raise ValueError('recorded body digest mismatch')
    return record['status'], body


class CitationResolutionTests(unittest.TestCase):
    def call(self, ref, transport=replay):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = resolver.main([ref], transport=transport)
        return code, output.getvalue().strip()

    def test_marker_pattern_constant(self):
        source = inspect.getsource(resolver.mentions_doi)
        lines = [line.strip() for line in source.splitlines()
                 if line.strip().startswith('pattern = ')]
        self.assertEqual(len(lines), 1)
        self.assertEqual(ast.literal_eval(lines[0].split(' = ', 1)[1]),
                         resolver.MARKER_PATTERN)

    def test_ten_recorded_dois(self):
        self.assertEqual(len(RECORDS['real']), 5)
        self.assertEqual(len(RECORDS['fabricated']), 5)
        for ref in RECORDS['real']:
            self.assertEqual(self.call(ref), (0, 'resolved'))
        for ref in RECORDS['fabricated']:
            self.assertEqual(self.call(ref), (1, 'citation_unresolved'))

    def test_prefixes_and_datacite_fallback(self):
        ref = RECORDS['real'][-1]
        for prefix in ('', 'doi:', 'https://doi.org/', 'https://dx.doi.org/'):
            for suffix in ('', '.', ',', ';'):
                self.assertEqual(self.call(prefix + ref + suffix), (0, 'resolved'))

    def test_transient_refuses(self):
        def broken(url):
            raise OSError('network down')
        self.assertEqual(self.call(RECORDS['real'][0], broken), (1, 'citation_unverifiable'))
        for status in (429, 500, 502, 503, 599):
            def failed(url):
                return status, b'{}'
            self.assertEqual(self.call(RECORDS['real'][0], failed), (1, 'citation_unverifiable'))
        def handle_failed(url):
            return (404, b'{}') if 'crossref' in url else (503, b'{}')
        self.assertEqual(self.call(RECORDS['real'][0], handle_failed), (1, 'citation_unverifiable'))

    @unittest.skipUnless(os.environ.get('GARS_NETWORK_TESTS') == '1', 'live DOI resolution unmeasured')
    def test_ten_live_dois(self):
        for ref in RECORDS['real']:
            self.assertEqual(self.call(ref, resolver.live_transport), (0, 'resolved'))
        for ref in RECORDS['fabricated']:
            self.assertEqual(self.call(ref, resolver.live_transport), (1, 'citation_unresolved'))

    def test_no_replay_switch(self):
        whitelist = json.loads((REPO / 'gars/tests/fixtures/citations/interface.json').read_text())
        for relative, expected in whitelist.items():
            path = REPO / relative
            loaded = module(path, 'whitelist_' + path.stem)
            self.assertEqual([action.option_strings for action in loaded.parser()._actions],
                             expected['options'])
            tree = ast.parse(path.read_text())
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend('import ' + alias.name + (' as ' + alias.asname if alias.asname else '')
                                   for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.extend('from ' + (node.module or '') + ' import ' + alias.name +
                                   (' as ' + alias.asname if alias.asname else '') for alias in node.names)
            self.assertEqual(sorted(imports), expected['imports'])
            # No environment access, including an added access through an existing import.
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, ('environ', 'getenv'))
                if isinstance(node, ast.Name):
                    self.assertNotIn(node.id, ('__import__', 'eval', 'exec'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
