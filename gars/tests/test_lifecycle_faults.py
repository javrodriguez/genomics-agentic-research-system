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
                for directory in ('_system', 'tests', '.claude'):
                    shutil.copytree(str(GARS / directory), str(root / directory),
                                    ignore=shutil.ignore_patterns('__pycache__'))
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
