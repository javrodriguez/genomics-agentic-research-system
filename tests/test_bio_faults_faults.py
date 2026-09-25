"""Fault controls for the implemented contracts, each in a disposable copy."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

REPO = Path(__file__).resolve().parents[1]
# Row 9 list shape: label, file, old bytes, replacement, module, named test.
FAULTS = [
    ('any-of ignores class', 'evals/review-faults/oracle.py',
     "if finding['class'] != expected['class']:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('any-of ignores file', 'evals/review-faults/oracle.py',
     "if normalize_file(finding['file']) != target['file']:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('line tolerance widened', 'evals/review-faults/oracle.py',
     "target['line_end'] + 3", "target['line_end'] + 4",
     'core', 'OracleTests.test_any_of_grid'),
    ('severity ignored', 'evals/review-faults/oracle.py',
     "if SEVERITY[finding['severity']] < SEVERITY[expected.get('min_severity', 'MINOR')]:", 'if False:',
     'core', 'OracleTests.test_any_of_grid'),
    ('repo drop removed', 'evals/bio-faults/bio_oracle.py',
     "if name.startswith('repo/'):", 'if False:',
     'core', 'OracleTests.test_repo_never_matches'),
    ('science name reimplemented', 'evals/bio-faults/bio_common.py',
     'ratio = rf_score.ratio', "ratio = lambda n, d: {'n': n, 'd': d}",
     'core', 'ContractTests.test_same_objects'),
    ('science module renamed to bare name', 'evals/bio-faults/bio_oracle.py',
     None, 'evals/bio-faults/oracle.py',
     'core', 'ContractTests.test_one_process_both_import_orders'),
    ('narrative delivered in phase A', 'evals/bio-faults/bio_run_reviews.py',
     '        session = str(uuid.uuid4())',
     "        shutil.copytree(str(source / '4-report'), str(kit / 'project/4-report'))\n        session = str(uuid.uuid4())",
     'pipeline', 'LaunchTests.test_two_phase_only_no_overwrite'),
    ('phase B blindness ignored', 'evals/bio-faults/bio_run_reviews.py',
     '            audit = blindness(events, kit, own_session)',
     "            audit = blindness(events, kit, own_session) if name == 'A' else dict(calls=0, hits=0, ambiguous=0)",
     'pipeline', 'LaunchTests.test_each_phase_hit'),
    ('envelope from stub text', 'evals/bio-faults/bio_run_reviews.py',
     '        write_json(output, record)',
     "        record['envelope'] = review.get('envelope', record['envelope'])\n        write_json(output, record)",
     'pipeline', 'LaunchTests.test_stub_cannot_supply_envelope'),
    ('producer uid removed', 'evals/review-faults/run_reviews.py',
     '    if uid == producer.pw_uid:', '    if False:',
     'pipeline', 'LaunchTests.test_producer_uid_and_root'),
    ('answer file allowed', 'evals/bio-faults/bio_build_cases.py',
     "                if path.is_symlink() or path.name in ('expected.json', 'plant.diff', 'key', 'key.json'):",
     "                if path.name == 'expected.json':\n                    path.unlink()\n                    continue\n                if path.is_symlink() or path.name in ('plant.diff', 'key', 'key.json'):",
     'pipeline', 'BuildTests.test_answer_file_refused'),
    ('unsalted neutral id', 'evals/bio-faults/bio_build_cases.py',
     "sha256((salt + cid).encode('ascii'))[:12]", "sha256(cid.encode('ascii'))[:12]",
     'pipeline', 'BuildTests.test_determinism_stats_neutral'),
    ('fixed mtime dropped', 'evals/bio-faults/bio_build_cases.py',
     '        os.utime(str(path), (FIXED_TIME, FIXED_TIME))', '        pass',
     'pipeline', 'BuildTests.test_determinism_stats_neutral'),
    ('gate refusal ignored', 'evals/bio-faults/bio_build_cases.py',
     '    if refused:', '    if False:',
     'pipeline', 'BuildTests.test_refusals_and_quiet'),
    ('first run always true', 'evals/bio-faults/bio_score.py',
     '    first = previous is None', '    first = True',
     'pipeline', 'ScoreTests.test_score_invalid_denominators_first_repeat'),
    ('partial set printed met', 'evals/bio-faults/bio_score.py',
     '≤ 1/5: NOT met (partial set:', '≤ 1/5: met (partial set:',
     'pipeline', 'ScoreTests.test_score_invalid_denominators_first_repeat'),
    ('mask literal unmasked', 'evals/bio-faults/bio_score.py',
     "    result = masked_copy(result, key['run_salt'], list(mapping), literals)",
     "    result = masked_copy(result, key['run_salt'], list(mapping), [])",
     'pipeline', 'PublicationTests.test_sealed_denominator_and_masked_score'),
    ('stage03 gate omitted', 'evals/bio-faults/bio_gates.py',
     "        results['stage03_verify'] = check(lambda: verify_data(base))", "        results['stage03_verify'] = True",
     'pipeline', 'BuildTests.test_each_gate_refuses'),
    ('group rep gate omitted', 'evals/bio-faults/bio_gates.py',
     "        results['group_rep_presence'] = check(lambda: group_rep_presence(base, root))",
     "        results['group_rep_presence'] = True",
     'pipeline', 'BuildTests.test_each_gate_refuses'),
    ('invalid plant counted caught', 'evals/bio-faults/bio_score.py',
     "        valid = [item for item in history[-1:] if not item['invalid_reasons']]",
     "        valid = history[-1:] if mapping[neutral]['kind'] == 'plant' else [item for item in history[-1:] if not item['invalid_reasons']]",
     'pipeline', 'ScoreTests.test_score_invalid_denominators_first_repeat'),
    ('phase B audited with A id', 'evals/bio-faults/bio_run_reviews.py',
     '            audit = blindness(events, kit, own_session)',
     '            audit = blindness(events, kit, session)',
     'pipeline', 'LaunchTests.test_phase_b_session_audit'),
    ('science path equality skipped', 'evals/bio-faults/bio_review_record.py',
     "    if not (env['reviewer']['prompt_path'] == manifest['prompt_path'] == PROMPT_PATH):",
     '    if False:',
     'pipeline', 'AdapterTests.test_science_path_equality'),
    ('code prompt accepted', 'evals/bio-faults/bio_review_record.py',
     '    errors = validate(record, SCHEMA)',
     "    if record['envelope']['reviewer']['prompt_path'] == rf_common.PROMPT_PATH:\n        return []\n    errors = validate(record, SCHEMA)",
     'pipeline', 'AdapterTests.test_code_path_invalid'),
    ('manifest substring exemption', 'evals/bio-faults/bio_build_cases.py',
     "target = 'commit' if key == 'harness_commit' else key",
     "target = 'commit' if 'harness_commit' in key else key",
     'pipeline', 'BuildTests.test_manifest_sweep_exact'),

]


class FaultTests(unittest.TestCase):
    def test_faults(self):
        for label, relative, old, new, module, name in FAULTS:
            with self.subTest(fault=label), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                for directory in ('evals/review-faults', 'evals/bio-faults', 'gars/_system', 'gars/_references'):
                    shutil.copytree(str(REPO / directory), str(root / directory),
                                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'runs'))
                for relative_file in ('tests/test_bio_faults_core.py', 'tests/test_bio_faults_pipeline.py',
                                      'scripts/release_check.py',
                                      'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md',
                                      'gars/_references/prompts/review_faults_science.md'):
                    target = root / relative_file
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(REPO / relative_file), str(target))
                script = root / ('tests/test_bio_faults_' + module + '.py')
                argv = [sys.executable, '-B', str(script), name]
                control = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
                self.assertEqual(control.returncode, 0, control.stdout.decode())
                path = root / relative
                if old is None:
                    path.rename(str(root / new))
                else:
                    source = path.read_text()
                    self.assertEqual(source.count(old), 1)
                    path.write_text(source.replace(old, new))
                failed = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=20)
                self.assertNotEqual(failed.returncode, 0, label)
                evidence = failed.stdout.decode()
                if old is None:
                    self.assertIn('ModuleNotFoundError', evidence)
                elif label == 'envelope from stub text':
                    self.assertIn('FAIL: ', evidence)
                else:
                    self.assertIn('FAIL: ' + name.split('.')[-1], evidence)
                    self.assertNotIn('ERROR:', evidence)
                print('science fault red: ' + label)


if __name__ == '__main__':
    unittest.main(verbosity=2)
