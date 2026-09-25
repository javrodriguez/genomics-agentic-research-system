"""Visible step-B fault controls in isolated trees, not sealed measurements."""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from support import GARS, REPO, run


class VenueFaultTests(unittest.TestCase):
    def test_policy_faults_are_red(self):
        stage02="        refusal = _venue_refusal(config_root, descriptor, '02', stage, script)\n        if refusal:\n            return None, refusal\n"
        stage03="            refusal = _venue_refusal(root, executed, '03', adir, script)\n            if refusal:\n                return None, refusal\n"
        faults = [
            ('stage02 skips policy', 'executorlib.py', stage02, '', 'ExecutedDescriptorTests'),
            ('stage03 skips policy', 'executorlib.py', stage03, '', 'SubmissionOrderingTests.test_analysis_refusal_before_launcher_and_backend'),
            ('FASTQ exemption widened', 'venue_policy.py', "fixture = data_class == 'public' and row.get('purpose') == 'fixture'", 'fixture = True', 'LocalFastqExemptionTests'),
            ('class case insensitive', 'venue_policy.py', "fixture = data_class == 'public'", "fixture = str(data_class).lower() == 'public'", 'LocalFastqExemptionTests'),
            ('purpose case insensitive', 'venue_policy.py', "row.get('purpose') == 'fixture'", "str(row.get('purpose')).lower() == 'fixture'", 'LocalFastqExemptionTests'),
            ('FASTQ reason suppressed', 'venue_policy.py', 'if fastq_inputs and not fixture:', 'if fastq_inputs and not fixture and not failures:', 'LocalFastqExemptionTests'),
            ('absent memory refused', 'venue_policy.py', 'if mem_bytes is None and not fixture:', 'if mem_bytes is None:', 'VenuePolicyTests.test_memory_boundary_absence_and_unparseable'),
            ('unparseable memory allowed', 'executorlib.py', 'failures.append(policy.fail("resource_unparseable", \'declared memory is not K/M/G/T\'))', 'pass', 'VenuePolicyTests.test_memory_boundary_absence_and_unparseable'),
            ('8.5 GiB accepted', 'venue_policy.py', 'mem_bytes > 8 * 1024 ** 3', 'mem_bytes > 9 * 1024 ** 3', 'VenuePolicyTests.test_memory_boundary_absence_and_unparseable'),
            ('homelab without marker', 'executorlib.py', "return 'homelab' if Path(HOMELAB_MARKER).exists() else 'local'", "return 'homelab'", 'VenuePolicyTests.test_marker_is_constant_not_environment'),
            ('grade load instead of executed descriptor', 'executorlib.py', "_venue_refusal(config_root, descriptor, '02', stage, script)", "_venue_refusal(config_root, load(config_root), '02', stage, script)", 'ExecutedDescriptorTests'),
            ('grade prepare-time group 11', 'executorlib.py', 'policy.check(row, venue_of(executed),', "policy.check(row, manifest['venue'] if stage_kind == '02' else venue_of(executed),", 'ExecutedDescriptorTests'),
            ('analysis submission venue missing', 'executorlib.py', "'venue': venue_of(executed),", "'missing_venue': venue_of(executed),", 'SubmissionOrderingTests.test_login_node_grades_slurm_and_records_local_executor'),
            ('submission venue missing', 'executorlib.py', "'venue': venue_of(descriptor),", "'missing_venue': venue_of(descriptor),", 'ExecutedDescriptorTests.test_prepare_and_executed_venues_both_recorded'),
            ('widen permitted backends', 'venue_policy.py', 'if not permissions(value).issubset(permissions(default)):', 'if False:', 'VenuePolicyTests.test_expiry_unclassified_narrowing_and_widening'),
            ('missing expiry accepted', 'venue_policy.py', "or data_class == 'deidentified_under_agreement':", ':', 'VenuePolicyTests.test_expiry_unclassified_narrowing_and_widening'),
            ('marker environment override', 'executorlib.py', "Path(HOMELAB_MARKER).exists()", "(os.environ.get('GARS_HOMELAB') == '1' or Path(HOMELAB_MARKER).exists())", 'VenuePolicyTests.test_marker_is_constant_not_environment'),
            ('identifiable accepted', 'venue_policy.py', "    failures = []", "    if dataset_row and dataset_row.get('data_class') == 'identifiable':\n        return []\n    failures = []", 'VenuePolicyTests.test_full_grid'),
            ('login-node graded after swap', 'executorlib.py', "_venue_refusal(root, executed, '03', adir, script)", "_venue_refusal(root, descriptor, '03', adir, script)", 'SubmissionOrderingTests.test_login_node_grades_slurm_and_records_local_executor'),
            ('test-mode bypass', 'venue_policy.py', '    failures = []', "    if __import__('os').environ.get('GARS_TEST_MODE'):\n        return []\n    failures = []", 'VenuePolicyTests.test_environment_cannot_bypass_submit'),
        ]
        for label, source, old, new, case in faults:
            self.fault(label, source, [(old,new)], case)
        self.fault('policy after reservation', 'executorlib.py', [(stage02,''),
                   ('        _save_record(path, record)\n        job, detail = _submit_once',
                    '        _save_record(path, record)\n'+stage02+'        job, detail = _submit_once')], 'ExecutedDescriptorTests')
        self.fault('policy after analysis launcher', 'executorlib.py', [(stage03,''),
                   ('            launcher = _analysis_launcher(adir, script, descriptor)\n',
                    '            launcher = _analysis_launcher(adir, script, descriptor)\n'+stage03)],
                   'SubmissionOrderingTests.test_analysis_refusal_before_launcher_and_backend')
        self.fault('policy before config refusal', 'executorlib.py', [(stage02,''),
                   ("    # Keep row 4's preflight refusal intact.",
                    stage02.replace('        ', '    ')+"    # Keep row 4's preflight refusal intact.")],
                   'SubmissionOrderingTests.test_existing_stage02_refusals_first')
        self.fault('policy before approval refusal', 'executorlib.py', [(stage03,''),
                   ('    holds, why = _analysis_approval(adir)',
                    stage03.replace('executed','descriptor').replace('            ','    ')+'    holds, why = _analysis_approval(adir)')],
                   'SubmissionOrderingTests.test_existing_analysis_refusals_first')

    def test_bench_and_route_faults_are_red(self):
        faults = [
            ('CSV row without evidence', 'scripts/backend_bench.py', '    active={}\n    seen=set()', '    return {}\n    active={}\n    seen=set()', 'test_append_regeneration_supersession_and_tampering'),
            ('host name in evidence', 'scripts/backend_bench.py', "isinstance(value, dict) and set(value)==set(FIELDS)", "isinstance(value, dict)", 'test_append_regeneration_supersession_and_tampering'),
            ('hand-edited wall_s', 'scripts/backend_bench.py', "require(row==expected, 'csv_evidence_mismatch')", 'pass', 'test_append_regeneration_supersession_and_tampering'),
            ('evidence before terminal', 'scripts/backend_bench.py', "if state in ('COMPLETED','FAILED','CANCELLED','ARTIFACT_MISSING')", "if state in ('PENDING','COMPLETED','FAILED','CANCELLED','ARTIFACT_MISSING')", 'test_collection_waits_for_terminal_and_failure_never_appends'),
            ('FAILED evidence appended', 'scripts/backend_bench.py', "require(not completed or value['status']=='COMPLETED', 'evidence_not_completed')", 'pass', 'test_collection_waits_for_terminal_and_failure_never_appends'),
            ('route table drift', 'gars/_references/data_policy.tsv', '\tany\tyes\t', '\tchanged\tyes\t', None),
        ]
        for label, source, old, new, case in faults:
            with self.subTest(fault=label), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                for folder in ('_system','_references','tests'):
                    shutil.copytree(str(GARS / folder),str(root / 'gars' / folder),ignore=shutil.ignore_patterns('__pycache__'))
                for name in ('scripts/backend_bench.py','tests/test_backend_bench.py','benchmarks/backend_bench.csv',
                             'docs/decisions/0100-row-8-data-handling.md'):
                    dest=root / name;dest.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copyfile(str(REPO / name),str(dest))
                target=root / source;text=target.read_text();self.assertIn(old,text);text=text.replace(old,new,1)
                if target.suffix=='.py': compile(text,str(target),'exec')
                target.write_text(text)
                argv=([sys.executable,root / 'tests/test_backend_bench.py','BackendBenchTests.'+case] if case else
                      [sys.executable,root / 'gars/tests/test_data_route.py'])
                result=run(argv,cwd=root)
                output=result.stdout.decode()+result.stderr.decode()
                self.assertNotEqual(result.returncode,0,output)
                self.assertIn('FAIL',output)
                print('fault red: '+label)


    def fault(self, label, source, replacements, case):
        with self.subTest(fault=label), tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ('_system','_references','tests'):
                shutil.copytree(str(GARS / folder),str(root / 'gars' / folder),ignore=shutil.ignore_patterns('__pycache__'))
            target = root / 'gars/_system' / source
            text = target.read_text()
            for old,new in replacements:
                self.assertIn(old,text,label);text=text.replace(old,new,1)
            # A syntax error is not a behavioral kill.
            compile(text,str(target),'exec')
            target.write_text(text)
            result=run([sys.executable,root / 'gars/tests/test_venue_policy.py',case],cwd=root)
            output=result.stdout.decode()+result.stderr.decode()
            self.assertNotEqual(result.returncode,0,output)
            self.assertTrue('FAIL' in output or 'ERROR' in output, output)
            self.assertNotIn('ImportError',output)
            print('fault red: '+label)


if __name__=='__main__':
    unittest.main(verbosity=2)
