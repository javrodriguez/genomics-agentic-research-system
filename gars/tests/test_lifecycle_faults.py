"""Visible row-12 fault witnesses in disposable source copies; no sealed score."""
import shutil
import tempfile
import unittest
from pathlib import Path
from support import GARS, run


class LifecycleFaultTests(unittest.TestCase):
    def test_implemented_faults_are_red(self):
        faults = [
            ('wrapper writes STATUS inline',
             '_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py',
             'wl.write_status(substage, "COMPLETE")',
             '(substage / "STATUS").write_text("COMPLETE")',
             'test_status_writer.py', 'StatusWriterTests.test_every_wrapper_uses_writer', 'AssertionError'),
            ('writer accepts an out-of-enum value', '_system/wrapperlib.py',
             'if state not in STATUS_STATES:', 'if False:',
             'test_status_writer.py', 'StatusWriterTests.test_closed_enum_and_atomic_refusal',
             'StatusRefusal not raised'),
            ('TIMEOUT folds into FAILED', '_system/executorlib.py',
             '"TIMEOUT": "FAILED:TIMEOUT"', '"TIMEOUT": "FAILED"',
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_scheduler_reasons_survive',
             "'FAILED' != 'FAILED:TIMEOUT'"),
            ('duplicate submission reaches scheduler', '_system/executorlib.py',
             'if path.exists():\n            record = json.loads',
             'if path.exists():\n            return _submit_once(config_root, script, descriptor)\n            record = json.loads',
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_duplicate_never_reaches_stub_scheduler',
             "'123' is not None"),
            ('corrected terminal stage stays wedged', '_system/wrapperlib.py',
             "if not corrective:", "if True:",
             'test_lifecycle_executor.py',
             'LifecycleExecutorTests.test_corrected_failed_or_cancelled_stage_submits_once',
             'terminal_state: cannot change'),
            ('status binds to re-prepared inputs', '_system/executorlib.py',
             '            stage = _validate_record(config_root, path, record)',
             "            stage = _validate_record(config_root, path, record)\n"
             "            if stage_record(config_root, stage) != record:\n"
             "                raise ValueError('record differs from current preparation')",
             'test_lifecycle_executor.py',
             'LifecycleExecutorTests.test_reprepare_keeps_tracking_and_blocks_overlapping_job',
             'prepared key has no submission record'),
            ('new key overlaps unresolved stage job', '_system/executorlib.py',
             'if any(not _scheduler_terminal(recorded_state(old)) for old in history):',
             'if False:',
             'test_lifecycle_executor.py',
             'LifecycleExecutorTests.test_reprepare_keeps_tracking_and_blocks_overlapping_job',
             're-prepare launched an overlapping job'),
            ('forged record bypasses script identity', '_system/executorlib.py',
             "record.get('script') != str(stage / 'submit.sh')", 'False',
             'test_no_false_completion.py',
             'NoFalseCompletionTests.test_forged_record_cannot_collect_another_stages_job',
             'StatusRefusal not raised'),
            ('agent session writes STATUS', '_system/guard_hook.py',
             '    "projects/*/STATUS",', '    "projects/*/OTHER_STATUS",',
             'test_status_writer.py', 'StatusWriterTests.test_agent_status_write_refused', '0 != 2'),
            ('killed worker reported COMPLETE', '_system/executorlib.py',
             '    return state, detail\n\n\n# --- CLI',
             '    if record and state and state.startswith("FAILED"):\n'
             '        (Path(record["script"]).parent / "STATUS").write_text("COMPLETE\\n")\n'
             '        state = "COMPLETE"\n'
             '    return state, detail\n\n\n# --- CLI',
             'test_no_false_completion.py',
             'NoFalseCompletionTests.test_killed_worker_and_unreachable_executor',
             "'COMPLETE'"),
        ]
        faults.extend([
            ('P9 terminal without record reaches backend', '_system/executorlib.py',
             "if terminal and not (prior and previous == recorded_state(prior) and",
             "if False and not (prior and previous == recorded_state(prior) and",
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_terminal_without_record_refuses_before_backend',
             'AssertionError'),
            ('old terminal reason ignored', '_system/wrapperlib.py',
             "and old['state'] == previous", "and True",
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_terminal_writer_requires_corrective_record_evidence',
             'StatusRefusal not raised'),
            ('new record without job accepted', '_system/wrapperlib.py',
             "record['state'] == 'SUBMITTED' and bool(record.get('job_id')) and", "True and",
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_terminal_writer_requires_corrective_record_evidence',
             'StatusRefusal not raised'),
            ('empty poll overwrites terminal record', '_system/executorlib.py',
             'if not _scheduler_terminal(recorded_state(record)):', 'if True:',
             'test_lifecycle_executor.py', 'LifecycleExecutorTests.test_superseded_terminal_retained_after_empty_poll',
             "'STALE' != 'FAILED:TIMEOUT'"),
            ('retry exceeds maxRetries', '_system/executorlib.py',
             "retries >= int(values[0])", "False",
             'test_failure_classification.py', 'FailureClassificationTests.test_only_transient_retries_at_existing_max_retries',
             'retry exceeded maxRetries'),
            ('old job cancelled without approval', '_system/executorlib.py',
             "if not isinstance(since, (int, float)) or not 0 <= time.time() - since <= 3600:", "if False:",
             'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_old_job_needs_bound_unexpired_human_record',
             'Expected'),
            ('success skips VALIDATING', '_system/executorlib.py',
             "'VALIDATING' if state == 'COMPLETED'", "'RUNNING' if state == 'COMPLETED'",
             'test_failure_classification.py', 'FailureClassificationTests.test_scheduler_success_then_collect_failure',
             "'RUNNING' != 'VALIDATING'"),
        ])
        faults.extend([
            ('M8 cancel ignores recorded backend', '_system/executorlib.py', "if not record or record.get('executor') != descriptor['name']:", 'if not record:', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_backend_and_terminal_stage_refuse_before_any_backend', 'AssertionError'),
            ('M9 cancel ignores terminal STATUS', '_system/executorlib.py', "if previous and previous.split(':', 1)[0] in wl.TERMINAL_STATES:", 'if False:', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_backend_and_terminal_stage_refuse_before_any_backend', 'AssertionError'),
            ('M11 downstream accepts another assay config', '_system/executorlib.py', "raise ValueError('config input differs from stage assay')", 'pass', 'test_downstream_keys.py', 'DownstreamKeyTests.test_rnaseq_de_submit', 'AssertionError'),
            ('cancel poll removed', '_system/executorlib.py', 'observed = _scheduler_status(root, job_id, descriptor)', "observed = ('RUNNING', None)", 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_finished_unpolled_job_is_recorded_without_signal', 'AssertionError'),
            ('unknown scheduler cancel refusal removed', '_system/executorlib.py', 'if observed[0] is None:', 'if False:', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_unknown_scheduler_leaves_all_evidence_unchanged', 'AssertionError'),
            ('cancel polls twice', '_system/executorlib.py', 'descriptor, observed=observed)', 'descriptor)', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_finished_unpolled_job_is_recorded_without_signal', 'AssertionError'),
            ('scheduler CANCELLED loses terminal success reply', '_system/executorlib.py', "return saved == 'CANCELLED',", 'return False,', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_finished_unpolled_job_is_recorded_without_signal', 'AssertionError'),
            ('CANCELLED retry loses readable refusal', '_system/executorlib.py', "if record['state'] == 'CANCELLED':", 'if False:', 'test_lifecycle_cancel.py', 'LifecycleCancelTests.test_cancelled_same_key_has_readable_retry_refusal', 'AssertionError'),
            ('launcher writes marker on any exit', '_system/executorlib.py', 'if [ "$code" -eq 0 ]; then', 'if true; then', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_launcher_clears_marker_and_removes_script_forgery_on_failure', 'AssertionError'),
            ('launcher keeps stale marker before script', '_system/executorlib.py', "'rm -f -- %s || exit 1\\n'", "': %s\\n'", 'test_stage03_execution.py', 'Stage03ExecutionTests.test_launcher_clears_marker_and_removes_script_forgery_on_failure', 'AssertionError'),
            ('launcher loses Slurm resource directives', '_system/executorlib.py', "b''.join(directives) if descriptor['name'] == 'slurm' else b''", "b''", 'test_stage03_execution.py', 'Stage03ExecutionTests.test_slurm_directives_and_launcher_are_handed_to_backend', 'AssertionError'),
            ('stage03 checks approval beside nested script', '_system/executorlib.py', 'stage = Path(config_root).resolve().joinpath(*parts[:2])', 'stage = Path(script).resolve().parent', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_nested_script_approval_and_launcher_local_evidence', 'AssertionError'),
            ('stage03 creates launcher before approval refusal', '_system/executorlib.py', 'holds, why = _analysis_approval(adir)', 'holds, why = True, None', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_approval_precedes_launcher_and_backend', 'AssertionError'),
            ('stage03 running resubmit refusal removed', '_system/executorlib.py', 'if not _scheduler_terminal(state):', 'if False:', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_resubmit_polls_latest_job_under_lock_and_keeps_history', 'AssertionError'),
            ('stage03 unknown resubmit refusal removed', '_system/executorlib.py', "if state is None:\n                    return None, 'R-077:", "if False:\n                    return None, 'R-077:", 'test_stage03_execution.py', 'Stage03ExecutionTests.test_resubmit_polls_latest_job_under_lock_and_keeps_history', 'AssertionError'),
            ('stage03 submission history overwritten', '_system/executorlib.py', "(adir / ANALYSIS_SUBMISSIONS).open('a')", "(adir / ANALYSIS_SUBMISSIONS).open('w')", 'test_stage03_execution.py', 'Stage03ExecutionTests.test_resubmit_polls_latest_job_under_lock_and_keeps_history', 'AssertionError'),
            ('login-node bypasses local route', '_system/executorlib.py', 'return LOCAL\n    return descriptor', 'return descriptor\n    return descriptor', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_login_node_uses_local_executor_and_status', 'AssertionError'),
            ('verify record and scheduler binding removed', '_system/stage03_analysis.py', 'problem = ex.analysis_execution_evidence(project, adir)', 'problem = None', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_marker_without_record_is_not_execution_evidence', 'AssertionError'),
            ('verify accepts absent submission record', '_system/executorlib.py', 'if not entries:\n            raise ValueError', 'if False:\n            raise ValueError', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_marker_without_record_is_not_execution_evidence', 'AssertionError'),
            ('verify accepts paths outside analysis', '_system/executorlib.py', '                path.relative_to(adir)', '                pass', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script', 'AssertionError'),
            ('verify ignores changed hashes', '_system/executorlib.py', "if _sha256(path) != entry[kind + '_sha256']:", 'if False:', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script', 'AssertionError'),
            ('verify ignores failed or unknown scheduler', '_system/executorlib.py', "if state != 'COMPLETED':", 'if False:', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script', 'AssertionError'),
            ('verify checks only the last script', '_system/executorlib.py', 'for entry in _analysis_latest(entries).values():', 'for entry in list(_analysis_latest(entries).values())[-1:]:', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script', 'AssertionError'),
            ('stage03 guard removed: projects/*/03_custom_analysis/*/run/*', '_system/guard_hook.py', '    "projects/*/03_custom_analysis/*/run/*",', '', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 guard removed: projects/*/03_custom_analysis/*/.gars_submissions.jsonl', '_system/guard_hook.py', '    "projects/*/03_custom_analysis/*/.gars_submissions.jsonl",', '', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Edit projects/*/03_custom_analysis/*/run/*', '.claude/settings.json', 'Edit(projects/*/03_custom_analysis/*/run/*)', 'Edit(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Write projects/*/03_custom_analysis/*/run/*', '.claude/settings.json', 'Write(projects/*/03_custom_analysis/*/run/*)', 'Write(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Edit projects/*/03_custom_analysis/*/run/**/*', '.claude/settings.json', 'Edit(projects/*/03_custom_analysis/*/run/**/*)', 'Edit(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Write projects/*/03_custom_analysis/*/run/**/*', '.claude/settings.json', 'Write(projects/*/03_custom_analysis/*/run/**/*)', 'Write(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Edit projects/*/03_custom_analysis/*/.gars_submissions.jsonl', '.claude/settings.json', 'Edit(projects/*/03_custom_analysis/*/.gars_submissions.jsonl)', 'Edit(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('stage03 settings deny removed: Write projects/*/03_custom_analysis/*/.gars_submissions.jsonl', '.claude/settings.json', 'Write(projects/*/03_custom_analysis/*/.gars_submissions.jsonl)', 'Write(unused)', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_run_and_submission_record_are_guarded', 'AssertionError'),
            ('parent contract loses a writer state', '02_bioinformatics/CONTEXT.md', '`VALIDATING <iso8601>`, ', '', 'test_lifecycle_contracts.py', 'LifecycleContractTests.test_parent_status_paragraph_covers_derived_writer_states', 'AssertionError'),
            ('parent contract loses collect route', '02_bioinformatics/CONTEXT.md', 'VALIDATING, ARTIFACT_MISSING and STALE continue', 'VALIDATING and STALE continue', 'test_lifecycle_contracts.py', 'LifecycleContractTests.test_contract_routes_and_executor_ownership', 'AssertionError'),
            ('stage03 contract loses failure discipline', '03_custom_analysis/CONTEXT.md', 'set -euo pipefail', 'set -x', 'test_lifecycle_contracts.py', 'LifecycleContractTests.test_contract_routes_and_executor_ownership', 'AssertionError'),
            ('stage03 contract falsely records FAILED', '03_custom_analysis/CONTEXT.md', 'The scheduler log and `executorlib.py status` record the failure; verify alone writes STATUS.', 'STATUS records the failure.', 'test_lifecycle_contracts.py', 'LifecycleContractTests.test_contract_routes_and_executor_ownership', 'AssertionError'),
        ])
        faults.extend([
            ('stage03 nested run guard removed',
             '_system/guard_hook.py',
             '    "projects/*/03_custom_analysis/*/run/**/*",',
             '',
             'test_stage03_execution.py',
             'Stage03ExecutionTests.test_run_and_submission_record_are_guarded',
             'AssertionError'),
            ('stage03 submission lock removed',
             '_system/executorlib.py',
             "with (run / '.submission.lock').open('a') as lock:\n"
             '        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)',
             "with (run / '.submission.lock').open('a') as lock:\n        pass",
             'test_stage03_execution.py',
             'Stage03ExecutionTests.test_concurrent_same_script_is_serialized',
             'AssertionError'),
        ])
        faults.extend([
            ('stage03 unresolved submission allowed',
             '_system/executorlib.py',
             "if not previous.get('job_id'):",
             'if False:',
             'test_stage03_execution.py',
             'Stage03ExecutionTests.test_resubmit_polls_latest_job_under_lock_and_keeps_history',
             'AssertionError'),
            ('verify accepts missing job identity',
             '_system/executorlib.py',
             "if not entry.get('job_id'):",
             'if False:',
             'test_stage03_execution.py',
             'Stage03ExecutionTests.test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script',
             'AssertionError'),
        ])
        faults.append(('login-node CLI reports wrong executor', '_system/executorlib.py', 'result["executor"] = recorded["name"]', 'result["executor"] = descriptor["name"]', 'test_stage03_execution.py', 'Stage03ExecutionTests.test_login_node_uses_local_executor_and_status', 'AssertionError'))
        for label, expression in [
                ('computed STATUS path', 'open(str(substage) + "/STATUS", "w")'),
                ('copied STATUS path', 'shutil.copyfile(source, str(substage / "STATUS"))'),
                ('formatted STATUS path', 'pathlib.Path("%s/STATUS" % substage).write_text("COMPLETE")')]:
            faults.append((label,
                           '_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py',
                           'wl.write_status(substage, "COMPLETE")', expression,
                           'test_status_writer.py', 'StatusWriterTests.test_every_wrapper_uses_writer',
                           'AssertionError'))
        for label, relative, old, new, test, case, witness in faults:
            with self.subTest(fault=label), tempfile.TemporaryDirectory(prefix='row12-fault-') as tmp:
                root = Path(tmp) / 'gars'
                root.mkdir()
                for directory in ('_system', 'tests', '.claude', '_templates', '_references'):
                    shutil.copytree(str(GARS / directory), str(root / directory),
                                    ignore=shutil.ignore_patterns('__pycache__'))
                for contract in ('02_bioinformatics/CONTEXT.md', '03_custom_analysis/CONTEXT.md'):
                    (root / contract).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(GARS / contract), str(root / contract))
                target = root / relative
                original = target.read_text()
                self.assertIn(old, original)
                target.write_text(original.replace(old, new, 1))
                result = run(['python3', root / 'tests' / test, case], cwd=Path(tmp))
                output = result.stdout.decode() + result.stderr.decode()
                self.assertNotEqual(result.returncode, 0, output)
                self.assertIn(witness, output)
                print('fault red: ' + label)


if __name__ == '__main__':
    unittest.main(verbosity=2)
