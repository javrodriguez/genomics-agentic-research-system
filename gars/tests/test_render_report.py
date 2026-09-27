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

    def test_claim_requires_nonempty_evidence(self):
        claim = self.snapshot['claims'][0]
        for value in (None, [], {}, 'evidence', 1, False):
            with self.subTest(value=value):
                claim['evidence'] = value
                self.refuse('report refused: claim 1 has no evidence links')
        del claim['evidence']
        self.refuse('report refused: claim 1 has no evidence links')

    def test_hypothesis_all_rendered_text(self):
        original = copy.deepcopy(self.snapshot)
        paths = (
            ('text',), ('bio_support', 'literature'),
            ('bio_support', 'replication'), ('process_risk', 'limitation'),
            ('process_risk', 'data_quality'), ('reference_release',), ('workflow_version',),
            ('evidence', 0, 'source', 'reference'),
        )
        for path in paths:
            for text in ('This proves the association.', 'Smith 2020 demonstrated and confirmed it',
                         'This sh\u200bows a result.', 'This finding may reflect a mechanism.',
                         'This proves_it.', 'This __proves__ it.', 'Replication confirms2 it.'):
                with self.subTest(path=path, text=text):
                    self.snapshot = copy.deepcopy(original)
                    target = self.snapshot['claims'][2]
                    for key in path[:-1]:
                        target = target[key]
                    target[path[-1]] = text
                    self.refuse('HYPOTHESIS observation verb in claim 3')
        for nested in ({'note': ['This proves it.']}, {'demonstrated': 'possible'}):
            self.snapshot = copy.deepcopy(original)
            self.snapshot['claims'][2]['bio_support']['literature'] = nested
            self.refuse('HYPOTHESIS observation verb in claim 3')
        self.snapshot = original
        self.snapshot['claims'][2]['process_risk']['limitation'] = 'An association remains possible.'
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
                     'This sh\u034fows a result.', 'This sh\ufe0fows a result.', 'This sh\u3164ows a result.',
                     'This proves_it.', 'This __proves__ it.', 'Replication confirms2 it.'):
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
        (self.fixture / 'manifest.json').write_text('{}')
        self.assertEqual(self.invoke().returncode, 0)
        report = self.out.read_text()
        self.assertEqual(renderer.display(' \t\n', 'row 7: run registrar'), 'UNKNOWN (owned by row 7: run registrar)')
        for owner in ('row 7: run registrar', '§14 QC dispositions',
                      'row 7: claim writer', 'row 6: manifest producer'):
            self.assertIn('UNKNOWN (owned by %s)' % owner, report)
        for key in ('data_class', 'venue', 'purpose', 'reference', 'agent_model', 'command'):
            self.assertIn('not recorded (the manifest has no `%s`)' % key, report)
        self.assertIn('Not recorded: GARS does not meter per-run cost yet, and this manifest has no cost field.', report)

    def render_manifest(self, manifest):
        # Keep existing methods populated so any row-6 UNKNOWN is a new-field regression.
        manifest = dict({'pipeline_commit': 'fixture', 'params': {}}, **manifest)
        return renderer.render(self.snapshot, manifest, (CLAIMS / 'report_template.md').read_text())

    def test_manifest_values_rendered(self):
        manifest = {
            'data_class': 'public', 'venue': 'home_lab', 'purpose': 'fixture & review',
            'agreement_ref': 'agreement[1]',
            'reference': {'build': 'GRCh38', 'annotation_release': 'GENCODE 44',
                          'fasta_sha256': 'a' * 64, 'gtf_sha256': 'b' * 64, 'comparison': 'matched'},
            'command': {'path': 'reproducibility/commands.sh', 'sha256': 'c' * 64},
            'agent_model': 'claude-opus-5-5',
            'model_steps': [
                {'model_id': 'claude-opus-5-5', 'prompt_id': 'wrapper/CONTEXT.md',
                 'prompt_sha256': {'algorithm': 'git-sha1', 'value': 'd' * 40}, 'routing_rule_id': 'none'},
                {'model_id': 'model_two', 'prompt_id': 'prompt[2]',
                 'prompt_sha256': 'hash*2', 'routing_rule_id': 'route|2'}],
            'cost': 'N/A: fixture-only.',
            'resources': {'AllocCPUS': '8', 'Elapsed': '01:02:03', 'MaxRSS': '12G'},
        }
        report = self.render_manifest(manifest)
        for expected in (
                r'data_class: public; venue: home\_lab; purpose: fixture &amp; review; agreement_ref: agreement\[1\]',
                'Reference: build=GRCh38; annotation_release=GENCODE 44; fasta_sha256=' + 'a' * 64 + '; gtf_sha256=' + 'b' * 64,
                r'Model steps: claude\-opus\-5\-5 / wrapper/CONTEXT\.md / ' + 'd' * 40 + r' / none; model\_two / prompt\[2\] / hash\*2 / route\|2',
                r'Reproduce this analysis (`commands.sh`): reproducibility/commands\.sh (relative to the sub-stage folder), sha256 ' + 'c' * 64,
                r'N/A: fixture\-only\.',
                r'Resources consumed (scheduler accounting): \{"AllocCPUS": "8", "Elapsed": "01:02:03", "MaxRSS": "12G"\}'):
            self.assertIn(expected, report)
        self.assertNotIn('registry check:', report)
        self.assertIn('b' * 64 + '\n\nModel steps:', report)
        self.assertNotIn('owned by row 6', report)
        self.assertNotIn('owned by row 11', report)

    def test_no_model_mediated_step(self):
        report = self.render_manifest({'agent_model': 'none', 'model_steps': [{'model_id': 'ignored'}]})
        self.assertIn('Model steps: no model-mediated step (agent_model: none)', report)
        self.assertNotIn('ignored', report)

    def test_reference_registry_comparison(self):
        for comparison, reason in (('missing', 'FASTA hash missing'), ('mismatch', '<wrong>|hash'),
                                   (None, None), ('matched ', None), ([], [])):
            with self.subTest(comparison=comparison):
                report = self.render_manifest({'reference': {'comparison': comparison, 'reason': reason}})
                self.assertIn('Reference: build=not recorded; annotation_release=not recorded; '
                              'fasta_sha256=not recorded; gtf_sha256=not recorded', report)
                self.assertIn('registry check: ' + (renderer.display(comparison, 'manifest') if comparison else 'not recorded') +
                              ' (' + (renderer.display(reason, 'manifest') if reason else 'not recorded') + ')', report)

    def test_hostile_manifest_values_cannot_add_sections(self):
        hostile = '\n## invented\n<script>|row|`'
        report = self.render_manifest({
            'data_class': hostile, 'venue': hostile, 'purpose': hostile, 'agreement_ref': hostile,
            'reference': dict((key, hostile) for key in
                              ('build', 'annotation_release', 'fasta_sha256', 'gtf_sha256', 'comparison', 'reason')),
            'command': {'path': hostile, 'sha256': hostile}, 'agent_model': hostile,
            'model_steps': [dict((key, hostile) for key in
                                 ('model_id', 'prompt_id', 'prompt_sha256', 'routing_rule_id')), hostile],
            'cost': hostile, 'resources': {'Elapsed': hostile},
        })
        self.assertEqual(re.findall(r'^## (.+)$', report, re.M), [s[0] for s in renderer.SECTIONS])
        self.assertNotIn('<script>', report)
        self.assertNotIn('|row|', report)
        self.assertIn(r'data_class:  \#\# invented &lt;script&gt;\|row\|\`', report)
        self.assertIn(r'Reproduce this analysis (`commands.sh`):  \#\# invented &lt;script&gt;\|row\|\` (relative to the sub-stage folder)', report)

    def test_missing_and_empty_manifest_values(self):
        for empty in (None, [], '', ' \t\n', {}):
            with self.subTest(empty=empty):
                report = self.render_manifest(dict((key, empty) for key in
                    ('data_class', 'venue', 'purpose', 'agreement_ref', 'agent_model')))
                for key in ('data_class', 'venue', 'purpose', 'agent_model'):
                    self.assertIn('not recorded (the manifest has no `%s`)' % key, report)
                self.assertNotIn('agreement_ref:', report)
                report = self.render_manifest({
                    'reference': dict((key, empty) for key in
                                      ('build', 'annotation_release', 'fasta_sha256', 'gtf_sha256')),
                    'command': {'path': empty, 'sha256': empty}, 'agent_model': 'model_name',
                    'model_steps': [{'model_id': empty, 'prompt_id': empty,
                                     'prompt_sha256': {'value': empty}, 'routing_rule_id': empty}, empty],
                })
                self.assertIn('Model steps: not recorded / not recorded / not recorded / not recorded; ', report)
                self.assertIn('not recorded (relative to the sub-stage folder), sha256 not recorded', report)
                self.assertNotIn('UNKNOWN (owned by manifest)', report)
                self.assertNotIn('owned by row 6', report)
                self.assertNotIn('owned by row 11', report)
                report = self.render_manifest({'agent_model': 'model_name', 'model_steps': empty})
                self.assertIn(r'Model steps: agent_model: model\_name; not recorded (the manifest has no `model_steps`)', report)
        report = self.render_manifest({'reference': 'not an object', 'command': ['not an object'],
                                       'agent_model': 'model', 'model_steps': [{}]})
        self.assertIn('Reference: not recorded (the manifest has no `reference`)', report)
        self.assertIn('not recorded (the manifest has no `command`)', report)
        self.assertIn('Model steps: not recorded / not recorded / not recorded / not recorded', report)

    def test_cost_and_resources_absence(self):
        for cost in (None, '', ' \n', [], {}, 0, False):
            for resources in (None, [], 'local', {}, {'applicability': 'not applicable', 'Elapsed': 'ignored'}):
                with self.subTest(cost=cost, resources=resources):
                    report = self.render_manifest({'cost': cost, 'resources': resources})
                    self.assertIn('Not recorded: GARS does not meter per-run cost yet, and this manifest has no cost field.', report)
                    self.assertNotIn('Resources consumed', report)

    def test_absent_limitations_and_malformed_manifest(self):
        for claim in self.snapshot['claims']:
            claim['process_risk'] = {}
        self.assertEqual(self.invoke().returncode, 0)
        section = self.out.read_text().split('## limitations adjacent to the affected claims\n', 1)[1]
        self.assertTrue(section.lstrip().startswith('UNKNOWN (owned by row 7: claim writer)'))
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
        self.assertEqual(renderer.display("cohort's", 'row 7: claim writer'), "cohort's")
        self.assertEqual(renderer.display('~~not~~ $x$', 'row 7: claim writer'), r'\~\~not\~\~ \$x\$')

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
