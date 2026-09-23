"""R-082/R-141: real CLI rendering, refusal, three-input and spec-drift gates."""
import ast
import builtins
import copy
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from support import REPO, GARS, module, run

CLAIMS = GARS / '_system/claims'
FIXTURE = GARS / 'tests/fixtures/claims'
# Import must fail at the parent naming the absent production path.
renderer = module(CLAIMS / 'render_report.py', 'row07_renderer')
# Independent oracle: removing a production verb must turn the test red.
VERBS = (
    'show shows showed shown showing', 'demonstrate demonstrates demonstrated demonstrating',
    'prove proves proved proven proving', 'confirm confirms confirmed confirming',
    'establish establishes established establishing', 'reveal reveals revealed revealing',
    'observe observes observed observing', 'detect detects detected detecting',
    'measure measures measured measuring', 'find finds found finding',
    'identify identifies identified identifying', 'verify verifies verified verifying',
    'validate validates validated validating', 'determine determines determined determining',
    'record records recorded recording', 'document documents documented documenting',
    'quantify quantifies quantified quantifying', 'indicate indicates indicated indicating',
    'exhibit exhibits exhibited exhibiting', 'display displays displayed displaying',
)


class RenderReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='gars-report-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.code = self.root / 'claims'
        self.fixture = self.root / 'fixture'
        shutil.copytree(str(CLAIMS), str(self.code))
        shutil.copytree(str(FIXTURE), str(self.fixture))
        self.snapshot = json.loads((self.fixture / 'snapshot.json').read_text())
        self.out = self.root / 'report.md'

    def command(self):
        return [sys.executable, self.code / 'render_report.py', '--snapshot',
                self.fixture / 'snapshot.json', '--manifest', self.fixture / 'manifest.json',
                '--out', self.out]

    def invoke(self):
        (self.fixture / 'snapshot.json').write_text(json.dumps(self.snapshot))
        return run(self.command())

    def refuse(self, reason):
        for existing in (False, True):
            if existing:
                self.out.write_bytes(b'previous report\n')
            p = self.invoke()
            self.assertNotEqual(p.returncode, 0, p.stdout)
            self.assertIn(reason, p.stderr.decode())
            if existing:
                self.assertEqual(self.out.read_bytes(), b'previous report\n')
            else:
                self.assertFalse(self.out.exists())
        self.out.unlink()

    def test_fixture_every_section_golden_and_deterministic(self):
        self.assertEqual(self.invoke().returncode, 0)
        golden = (FIXTURE / 'report.md').read_bytes()
        self.assertEqual(self.out.read_bytes(), golden)
        self.assertEqual(self.invoke().returncode, 0)
        self.assertEqual(self.out.read_bytes(), golden)
        headings = re.findall(r'^## (.+)$', golden.decode(), re.M)
        self.assertEqual(headings, [s[0] for s in renderer.SECTIONS])
        self.assertIn(b'REFERENCE RELEASE MISMATCH', golden)
        lines = golden.decode().splitlines()
        for i, line in enumerate(lines):
            if 'DEGRADE' in line and line.startswith('|'):
                self.assertIn('Limitation:', lines[i + 1])
                self.assertIn('Synthetic cohort only', lines[i + 1])
        print('template renders fixture: 8/8 sections', flush=True)

    def test_missing_section_refused(self):
        template = self.code / 'report_template.md'
        original = template.read_text()
        for heading, _ in renderer.SECTIONS:
            with self.subTest(section=heading):
                template.write_text(original.replace('## ' + heading + '\n', ''))
                self.refuse(heading)
        template.write_text(original)

    def test_missing_section_source_refused(self):
        template = self.code / 'report_template.md'
        original = template.read_text()
        for heading, key in renderer.SECTIONS:
            with self.subTest(section=heading):
                for replacement in ('', '{{' + key + '}}', '{' + key + ':.0}'):
                    template.write_text(original.replace('{' + key + '}', replacement))
                    self.refuse(heading)
        template.write_text(original)

    def test_hypothesis_all_verbs_and_inflections(self):
        hypothesis = next(c for c in self.snapshot['claims'] if c['type'] == 'HYPOTHESIS')
        for forms in VERBS:
            for verb in forms.split():
                with self.subTest(verb=verb):
                    hypothesis['text'] = 'This ' + verb.upper() + ' a result.'
                    self.refuse('HYPOTHESIS observation verb')
        hypothesis['text'] = 'A showingly unconfirmed possibility.'
        self.assertEqual(self.invoke().returncode, 0)

    def test_degrade_requires_limitation(self):
        claim = next(c for c in self.snapshot['claims']
                     if c['process_risk'].get('qc_disposition') == 'DEGRADE')
        for value in (None, '', '   ', '\u200b', '\u00ad', '\u034f', '\u2800', '\u3164', '\u115f', [], {}):
            with self.subTest(value=value):
                claim['process_risk']['limitation'] = value
                self.refuse('DEGRADE requires limitation')

    def test_unicode_verbs_and_invalid_snapshot_types(self):
        hypothesis = next(c for c in self.snapshot['claims'] if c['type'] == 'HYPOTHESIS')
        original = copy.deepcopy(self.snapshot)
        for text in ('This sh\u200bows a result.', 'This sh\u00adows a result.', 'This ＳＨＯＷＳ a result.',
                     'This sh\u034fows a result.', 'This sh\ufe0fows a result.', 'This sh\u3164ows a result.'):
            hypothesis['text'] = text
            self.refuse('HYPOTHESIS observation verb')
        for separator in ('\n', '\t', '\r', '\v', '\f', '\x85', '\u3164', '\u200b'):
            hypothesis['text'] = 'This' + separator + 'shows a result.'
            self.refuse('HYPOTHESIS observation verb')
        hypothesis['type'] = 'Hypothesis'
        self.refuse('invalid claim type')
        for value in ('Degrade', 'degrade', 'DEGRADE ', ['DEGRADE']):
            self.snapshot = copy.deepcopy(original)
            self.snapshot['claims'][1]['process_risk'] = {'qc_disposition': value}
            self.refuse('invalid QC disposition')
        for cid in ('<img src=x>', '1\n# Injected', True, {}, 2 ** 63):
            self.snapshot = copy.deepcopy(original)
            self.snapshot['claims'][0]['id'] = cid
            self.refuse('invalid claim id')
        for group, value in (('process_risk', {'QC_disposition': 'DEGRADE'}),
                             ('bio_support', {'replication': {'confidence': 1}}),
                             ('process_risk', {'data_quality': [{'score': 1}]})):
            self.snapshot = copy.deepcopy(original)
            self.snapshot['claims'][0][group] = value
            self.refuse('invalid ' + group + ' keys')
        for value in ([], 1, 'text'):
            self.snapshot = value
            self.refuse('snapshot and manifest must be JSON objects')

    def test_unknown_sources(self):
        self.snapshot = {'run': {}, 'claims': []}
        self.assertEqual(self.invoke().returncode, 0)
        report = self.out.read_text()
        self.assertEqual(renderer.display(' \t\n', 'run registration'), 'UNKNOWN (owned by run registration)')
        for owner in ('run registration', 'row 6: data_class, venue, purpose',
                      'row 6', '§14 QC dispositions', 'claims snapshot',
                      'row 11: docs/ledger.csv has no per-run cost source'):
            self.assertIn('UNKNOWN (owned by %s)' % owner, report)

    def test_absent_limitations_and_malformed_manifest(self):
        for claim in self.snapshot['claims']:
            claim['process_risk'] = {}
        self.assertEqual(self.invoke().returncode, 0)
        section = self.out.read_text().split('## limitations adjacent to the affected claims\n', 1)[1]
        self.assertTrue(section.lstrip().startswith('UNKNOWN (owned by claims snapshot)'))
        self.out.unlink()
        (self.fixture / 'manifest.json').write_text('[]')
        self.refuse('snapshot and manifest must be JSON objects')

    def test_manifest_binding_and_text_cannot_add_sections(self):
        for digest in (0, False, 'bad'):
            self.snapshot['run']['manifest_sha256'] = digest
            self.refuse('invalid manifest sha256')
        self.snapshot['run']['manifest_sha256'] = '0' * 64
        self.refuse('manifest sha256 mismatch')
        del self.snapshot['run']['manifest_sha256']
        self.snapshot['run']['question'] = '\n## invented\n<script>x</script>|extra|'
        self.assertEqual(self.invoke().returncode, 0)
        self.assertNotIn('\n## invented', self.out.read_text())
        self.assertNotIn('<script>', self.out.read_text())
        self.assertEqual(renderer.display("cohort's", 'claims snapshot'), "cohort's")
        self.assertEqual(renderer.display('~~not~~ $x$', 'claims snapshot'), r'\~\~not\~\~ \$x\$')

    def test_three_inputs_invariant_sweep(self):
        sentinel = 'ROW7_FORBIDDEN_PROSE_SENTINEL'
        allowed = {self.fixture / 'snapshot.json', self.fixture / 'manifest.json',
                   self.code / 'report_template.md'}
        allowed = {p.resolve() for p in allowed}
        # Every other file is planted; code gets a comment so it remains executable.
        for folder in (self.code, self.fixture):
            (folder / 'agent_prose.md').write_text('untrusted prose')
            for path in folder.rglob('*'):
                if path.is_file() and path.resolve() not in allowed:
                    with path.open('ab') as fh:
                        fh.write(('\n# ' + sentinel + '\n').encode())
        real_open, real_io_open, real_os_open = builtins.open, io.open, os.open
        reads = []
        def guarded(opener):
            def opening(path, mode='r', *args, **kwargs):
                if isinstance(path, (str, bytes, Path)) and ('r' in mode or '+' in mode):
                    p = Path(path).resolve()
                    self.assertIn(p, allowed, 'renderer opening a fourth file: ' + str(p))
                    reads.append(p)
                return opener(path, mode, *args, **kwargs)
            return opening
        def guarded_os_open(path, flags, *args, **kwargs):
            if not flags & os.O_WRONLY and not flags & os.O_CREAT:
                p = Path(path).resolve()
                self.assertIn(p, allowed, 'renderer opening a fourth file: ' + str(p))
                reads.append(p)
            return real_os_open(path, flags, *args, **kwargs)
        with mock.patch('builtins.open', guarded(real_open)), mock.patch('io.open', guarded(real_io_open)), \
                mock.patch('os.open', guarded_os_open):
            subject = module(self.code / 'render_report.py', 'row07_isolation')
            self.assertEqual(subject.main([str(a) for a in self.command()[2:]]), 0)
        self.assertEqual(set(reads), allowed)
        self.assertNotIn(sentinel, self.out.read_text())
        self.assertEqual(self.out.read_bytes(), (FIXTURE / 'report.md').read_bytes())

    def test_spec_template_section_order(self):
        spec = (REPO / 'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md').read_text()
        section = spec.split('### 7.8 ', 1)[1].split('\n### ', 1)[0]
        listed = section.split('mandatory sections in verification order: ', 1)[1].split('. A report', 1)[0]
        expected = listed.split('; ')
        headings = re.findall(r'^## (.+)$', (CLAIMS / 'report_template.md').read_text(), re.M)
        self.assertEqual(headings, expected)

    def test_python36_parseable(self):
        source = (CLAIMS / 'render_report.py').read_text()
        if sys.version_info >= (3, 8):
            ast.parse(source, feature_version=(3, 6))
        else:
            ast.parse(source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
