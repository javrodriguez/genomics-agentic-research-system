"""Independent science contracts; no model, network or measurement evidence."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/bio-faults'))
import bio_common as bio
import bio_oracle as oracle


def finding(**changes):
    value = dict(id='f1', severity='MINOR', file='3-results/de_results.csv',
                 line_start=10, line_end=12, summary='Concrete mismatch',
                 evidence='The named rows contradict the specified analysis.')
    value['class'] = 'batch-confounded-contrast'
    value.update(changes)
    return value


def answer():
    return {'class': 'batch-confounded-contrast', 'min_severity': 'MINOR',
            'match_any': [dict(file='3-results/de_results.csv', line_start=10,
                               line_end=12, mode='file_lines')]}


class ContractTests(unittest.TestCase):
    def test_classes_closed(self):
        names = ('swapped-condition-labels wrong-reference-in-params '
                 'replicate-dropped-after-approval pseudoreplicated-de fabricated-citation '
                 'causal-language-on-correlational-da batch-confounded-contrast '
                 'p-value-edited-in-report missing-n2-limitation '
                 'contradictory-literature-omitted').split()
        self.assertEqual(set(bio.CLASSES), set(names))
        spec = (REPO / 'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md').read_text()
        phrases = ('swapped condition labels', 'wrong reference in params',
                   'replicate dropped after approval', 'pseudoreplicated DE',
                   'fabricated citation', 'causal language on correlational DA',
                   'batch-confounded contrast passing rank', 'p-value edited in the report',
                   'missing n = 2 limitation', 'contradictory literature omitted')
        section = spec.split('## 10. ', 1)[1].split('\n## 11.', 1)[0]
        for phrase in phrases:
            self.assertIn(phrase, section)
        for definition in bio.CLASSES.values():
            self.assertTrue(definition.endswith('.'))
            self.assertEqual(definition.count('.'), 1)

    def test_same_objects(self):
        for name in ('blindness', 'parse_stream', 'stream_facts', 'safe_review',
                     'launch_identity', 'clean_environment', 'next_attempt',
                     'host_digest', 'LIMIT', 'session_output_store', 'audit_words',
                     'strings', 'stream_items', 'input_fields', 'shell_words',
                     'placed_command', 'CommandPlacement', 'ShellWord'):
            self.assertIs(getattr(bio, name), getattr(bio.rf_run_reviews, name), name)
        for local, module, name in (
                ('validate', bio.rf_review_record, 'validate'),
                ('row9_invalid_reasons', bio.rf_review_record, 'invalid_reasons'),
                ('row9_caught', bio.rf_oracle, 'caught'),
                ('false_alarm', bio.rf_oracle, 'false_alarm'),
                ('SEVERITY', bio.rf_oracle, 'SEVERITY'),
                ('masked_copy', bio.rf_score, 'masked_copy'),
                ('ratio', bio.rf_score, 'ratio'),
                ('format_ratio', bio.rf_score, 'format_ratio')):
            self.assertIs(getattr(bio, local), getattr(module, name), local)
        self.assertIs(oracle.row9_caught, bio.rf_oracle.caught)
        self.assertIs(oracle.false_alarm, bio.rf_oracle.false_alarm)

    def test_audit_stub_stream_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            kit = Path(folder)
            outside = os.path.join(os.sep, 'outside', 'data')
            events = [dict(type='tool_use', name='Read', input={'file_path': name})
                      for name in ('project/3-results/de_results.csv', outside)]
            raw = '\n'.join(json.dumps(event) for event in events)
            science = bio.blindness(bio.parse_stream(raw), kit, 'session-a')
            code = bio.rf_run_reviews.blindness(bio.rf_run_reviews.parse_stream(raw), kit, 'session-a')
            self.assertEqual(science, code)
            self.assertEqual(science['hits'], 1)

    def test_one_process_both_import_orders(self):
        # Exactly the bare imports used by test_review_faults_core, in each order.
        source = '''
import sys
from pathlib import Path
root = Path(sys.argv[1])
sys.path.insert(0, str(root / 'evals/review-faults'))
sys.path.insert(0, str(root / 'evals/bio-faults'))
before = list(sys.path)
if sys.argv[2] == 'science':
    import bio_common, bio_oracle, bio_generate_base, bio_build_cases, bio_gates, bio_review_record, bio_run_reviews, bio_score
    import common, oracle, score
else:
    import common, oracle, score
    import bio_common, bio_oracle, bio_generate_base, bio_build_cases, bio_gates, bio_review_record, bio_run_reviews, bio_score
assert sys.path == before
assert len(common.CLASSES) == 10 and 'off-by-one' in common.CLASSES
assert len(bio_common.CLASSES) == 10 and 'pseudoreplicated-de' in bio_common.CLASSES
assert common.PROMPT_PATH == 'gars/_references/prompts/review_faults_code.md'
assert bio_common.PROMPT_PATH == 'gars/_references/prompts/review_faults_science.md'
assert common is bio_common.rf_common
assert oracle is bio_common.rf_oracle
assert score is bio_common.rf_score
for name in ('common', 'oracle', 'score', 'review_record', 'run_reviews', 'build_cases'):
    if name in sys.modules:
        assert Path(sys.modules[name].__file__).parent == root / 'evals/review-faults'
assert not any((root / 'evals/bio-faults' / (name + '.py')).exists()
               for name in ('common', 'oracle', 'score', 'review_record', 'run_reviews', 'build_cases'))
'''
        for order in ('science', 'code'):
            proc = subprocess.run([sys.executable, '-B', '-c', source, str(REPO), order],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def test_schema_drift(self):
        code = copy.deepcopy(bio.rf_review_record.SCHEMA)
        science = bio.read_json(bio.HERE / 'schema/review_record.schema.json')
        findings = science['properties']['review']['properties']['findings']['items']
        self.assertEqual(findings['properties']['class']['enum'], list(bio.CLASSES) + ['other'])
        findings['properties']['class']['enum'] = code['properties']['review']['properties']['findings']['items']['properties']['class']['enum']
        env = science['properties']['envelope']
        self.assertEqual(env['properties'].pop('safeguard_refusal'), {'type': 'boolean'})
        self.assertEqual(env['properties'].pop('retry_binding_sha256'),
                         {'type': 'string', 'pattern': '^[0-9a-f]{64}$'})
        phases = env['properties'].pop('phases')
        self.assertEqual((phases['minItems'], phases['maxItems']), (2, 2))
        self.assertEqual([p['properties']['name']['enum'] for p in phases['prefixItems']], [['A'], ['B']])
        self.assertIn('notes_sha256', phases['prefixItems'][0]['required'])
        self.assertNotIn('notes_sha256', phases['prefixItems'][1]['properties'])
        self.assertEqual(env['properties'].pop('narrative_withheld_until_phase_b'), {'type': 'boolean'})
        env['required'].remove('phases')
        env['required'].remove('narrative_withheld_until_phase_b')
        science_path = env['properties']['reviewer']['properties']['prompt_path']
        self.assertEqual(science_path['enum'], [bio.PROMPT_PATH])
        science_path['enum'] = [bio.rf_common.PROMPT_PATH]
        self.assertEqual(science, code)

    def test_prompt_schema_pin(self):
        # R1 authorizes precisely the science path in the science schema.
        schema = bio.read_json(bio.HERE / 'schema/review_record.schema.json')
        field = schema['properties']['envelope']['properties']['reviewer']['properties']['prompt_path']
        self.assertEqual(bio.validate(bio.rf_common.PROMPT_PATH, field), ['record: outside vocabulary'])
        self.assertEqual(bio.validate(bio.PROMPT_PATH, field), [])

    def test_manifest_tokens_require_explicit_exemptions(self):
        # Both required public fields are wholly added bytes, with no base exemption.
        manifest = json.dumps({'harness_commit': 'a' * 40, 'prompt_path': bio.PROMPT_PATH})
        self.assertIn('harness', manifest)
        self.assertIn('fault', manifest)

    def test_prompt_contract(self):
        text = (REPO / bio.PROMPT_PATH).read_text()
        for phrase in ('never change directory', 'foreground', 'No network', './tmp',
                       'Do not modify anything under project/', 'notes.json', 'review.json',
                       '## Phase 1', '## Phase 2'):
            self.assertIn(phrase, text)
        for name, definition in bio.CLASSES.items():
            self.assertIn('**%s**: %s' % (name, definition), text)
        for word in ('plant', 'harness', 'catch rate', 'evaluation', 'measurement'):
            self.assertNotIn(word, text.lower())


class OracleTests(unittest.TestCase):
    def test_any_of_grid(self):
        expected = answer()
        expected['match_any'].insert(0, dict(file='1-design/samples.csv', line_start=2, line_end=3, mode='file_lines'))
        for cls in (expected['class'], 'other'):
            for file in ('3-results/de_results.csv', '3-results/elsewhere.csv'):
                for line in (6, 7, 10, 15, 16):
                    for severity in bio.SEVERITY:
                        item = finding(file=file, line_start=line, line_end=line, severity=severity, **{'class': cls})
                        wanted = (cls == expected['class'] and file == '3-results/de_results.csv'
                                  and 7 <= line <= 15 and bio.SEVERITY[severity] >= bio.SEVERITY['MINOR'])
                        self.assertEqual(oracle.caught({'findings': [item]}, expected), wanted, item)
        expected['min_severity'] = 'MAJOR'
        self.assertFalse(oracle.caught({'findings': [finding()]}, expected))
        expected['match_any'][1]['mode'] = 'file'
        self.assertTrue(oracle.caught({'findings': [finding(severity='MAJOR', line_start=999, line_end=999)]}, expected))
        self.assertTrue(oracle.caught({'findings': [finding(file='1-design/samples.csv', severity='MAJOR', line_start=2, line_end=2)]}, expected))

    def test_pre_normalisation_drift(self):
        expected = answer()
        for prefix in ('', './', 'project/', './project/'):
            for line in range(5, 18):
                for severity in bio.SEVERITY:
                    plain = finding(line_start=line, line_end=line, severity=severity)
                    review = {'findings': [dict(plain, file=prefix + plain['file'])]}
                    original = copy.deepcopy(review)
                    code = bio.rf_oracle.caught({'findings': [plain]}, dict(expected, match=expected['match_any'][0]))
                    self.assertEqual(oracle.caught(review, expected), code)
                    self.assertEqual(review, original)

    def test_repo_never_matches(self):
        for prefix in ('repo/', './repo/', 'project/repo/', './project/repo/',
                       '././repo/', 'project/./repo/', './project/./repo/', '././'):
            self.assertFalse(oracle.caught({'findings': [finding(file=prefix + finding()['file'])]}, answer()))
        review = {'findings': [finding(file='repo/' + finding()['file']), finding()]}
        self.assertTrue(oracle.caught(review, answer()))

    def test_false_alarms_and_ratios_are_shared(self):
        self.assertFalse(oracle.false_alarm({'findings': [finding(severity='NOTE')]}))
        self.assertTrue(oracle.false_alarm({'findings': [finding()]}))
        self.assertFalse(oracle.false_alarm({'findings': [finding()]}, 'other'))
        self.assertEqual(bio.format_ratio(bio.ratio(0, 0)), '0/0 uncomputable')


if __name__ == '__main__':
    unittest.main(verbosity=2)
