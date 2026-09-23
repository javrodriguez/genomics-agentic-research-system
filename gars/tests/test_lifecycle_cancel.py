"""R-074: cancellation uses recorded timing and human-owned job/backend approval."""
import datetime
import json
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, run
from test_lifecycle_executor import prepared
import executorlib as ex
import stage03_analysis as analysis
import wrapperlib as wl


class LifecycleCancelTests(unittest.TestCase):
    def fixture(self, root, backend='slurm'):
        stage, _, _ = prepared(root)
        (root / '_config/executor.yaml').write_text('name: ' + backend + '\n')
        with patch.object(ex, '_submit_once', return_value=('42', None)):
            ex.submit(root, stage / 'submit.sh')
        path, record = ex._job_record(root, '42')
        record['submitted_at'] = time.time() - 7200
        ex._save_record(path, record)
        return stage, path, record

    def test_old_job_needs_bound_unexpired_human_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'project'; root.mkdir()
            stage, path, record = self.fixture(root)
            workspace = Path(tmp) / 'gars'; workspace.mkdir()
            with patch.object(analysis.ws, 'workspace_root', return_value=workspace), patch.object(ex, 'scheduler_start', return_value=None):
                with patch.object(ex.subprocess, 'run') as backend:
                    ok, why = ex.cancel(root, '42')
                    self.assertFalse(ok, 'old job cancelled without approval')
                    backend.assert_not_called()
                self.assertEqual(ex.approve_action(root, '42', 'cancel'), (True, None))
                _, _, _, _, plan = ex._action_paths(root, record, 'cancel')
                approval_path = analysis.approval_record_path(plan, workspace)
                approved = json.loads(approval_path.read_text())
                self.assertEqual((approved['job_id'], approved['backend']), ('42', 'slurm'))
                for field, value in [('job_id', '99'), ('backend', 'local'), ('actor', 'forged'),
                                     ('plan_sha256', '0' * 64), ('expiry', '2000-01-01T00:00:00Z')]:
                    bad = dict(approved); bad[field] = value; approval_path.write_text(json.dumps(bad))
                    with patch.object(ex.subprocess, 'run') as backend:
                        self.assertFalse(ex.cancel(root, '42')[0], field)
                        backend.assert_not_called()
                approval_path.write_text(json.dumps(approved))
                with patch.object(ex.subprocess, 'run') as backend:
                    backend.return_value.returncode = 0
                    self.assertEqual(ex.cancel(root, '42'), (True, None))
                    self.assertEqual(backend.call_args[0][0], ['scancel', '42'])
                self.assertEqual(wl.read_status(stage), 'CANCELLED')
                self.assertEqual(ex._job_record(root, '42')[1]['state'], 'CANCELLED')

    def test_scheduler_start_wins_and_fallback_is_submitted_at(self):
        for start, submitted, allowed in [(time.time() - 60, time.time() - 7200, True),
                                          (time.time() - 7200, time.time() - 60, False),
                                          (None, time.time() - 60, True),
                                          (None, time.time() - 7200, False)]:
            with self.subTest(start=start), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, path, record = self.fixture(root)
                record['submitted_at'] = submitted; ex._save_record(path, record)
                with patch.object(ex, 'scheduler_start', return_value=start), patch.object(ex.subprocess, 'run') as backend:
                    backend.return_value.returncode = 0
                    self.assertEqual(ex.cancel(root, '42')[0], allowed)
                    self.assertEqual(backend.call_count, int(allowed))
                saved = json.loads(path.read_text())
                self.assertEqual(saved['started_at'], start)
                self.assertEqual(saved['submitted_at'], submitted)

    def test_flags_environment_and_agent_approval_cannot_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, _, _ = self.fixture(root)
            with patch.dict(os.environ, {'GARS_APPROVED': '1', 'GARS_ROLE': 'human',
                                        'GARS_APPROVAL_STORE': tmp, 'GARS_CANCEL_FORCE': '1'}), \
                    patch.object(ex, 'scheduler_start', return_value=None), patch.object(ex.subprocess, 'run') as backend:
                self.assertFalse(ex.cancel(root, '42')[0])
                backend.assert_not_called()
            for flag in ('--force', '--approved', '--actor=human', '--approval-record=forged'):
                result = run(['python3', GARS / '_system/executorlib.py', 'cancel', '--workspace', root, '42', flag])
                self.assertEqual(result.returncode, 2)
                self.assertIn(b'unrecognized arguments', result.stderr)
            result = run(['python3', GARS / '_system/guard_hook.py'], cwd=GARS,
                         env={'CLAUDE_PROJECT_DIR': str(GARS)}, stdin=json.dumps({
                             'tool_name': 'Bash', 'cwd': str(GARS), 'tool_input': {'command':
                             'python3 _system/executorlib.py approve-action --workspace projects/fixture cancel 42'}}))
            self.assertEqual(result.returncode, 2)

    def test_local_sigterm_requires_recorded_pid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, path, record = self.fixture(root, 'local')
            record['submitted_at'] = time.time(); ex._save_record(path, record)
            jobs = ex._local_jobs_dir(root); jobs.mkdir()
            (jobs / '42.json').write_text(json.dumps({'script': str(stage / 'submit.sh'), 'started_at': time.time()}))
            with patch.object(ex.os, 'kill') as kill:
                self.assertEqual(ex.cancel(root, '42'), (True, None))
                kill.assert_called_once_with(42, signal.SIGTERM)
            self.assertEqual(wl.read_status(stage), 'CANCELLED')

    def test_real_local_cancel_terminates_worker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            (root / '_config/executor.yaml').write_text('name: local\n')
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk',
                               'echo $$ > worker.pid\nwhile :; do sleep 0.1; done')
            wl.write_reproducibility(stage, 'rnaseq_bulk', root, {'samplesheet': sheet, 'config': cfg}, [])
            job, why = ex.submit(root, stage / 'submit.sh')
            self.assertIsNotNone(job, why)
            pidfile = stage / 'run/worker.pid'
            deadline = time.monotonic() + 10
            try:
                while not pidfile.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(pidfile.exists())
                self.assertEqual(ex.cancel(root, job), (True, None))
                exit_file = stage / 'submit.sh.local.exit'
                while not exit_file.exists() and time.monotonic() < deadline:
                    time.sleep(0.02)
                self.assertTrue(exit_file.exists(), 'cancel did not stop the recorded worker')
                self.assertEqual(exit_file.read_text().strip(), '143')
                self.assertEqual(wl.read_status(stage), 'CANCELLED')
                self.assertFalse((stage / 'run/.gars_run_complete').exists())
            finally:
                for pid in [job] + ([pidfile.read_text().strip()] if pidfile.exists() else []):
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass

    def test_slurm_start_parser_requests_utc(self):
        with patch.object(ex.subprocess, 'run') as backend:
            backend.return_value.returncode = 0
            backend.return_value.stdout = b'2026-09-22T10:00:00|\n'
            self.assertEqual(ex.scheduler_start(Path('.'), {'job_id': '42'}, ex.SLURM),
                             datetime.datetime(2026, 9, 22, 10, tzinfo=datetime.timezone.utc).timestamp())
            self.assertEqual(backend.call_args[1]['env']['TZ'], 'UTC')


if __name__ == '__main__':
    unittest.main(verbosity=2)
