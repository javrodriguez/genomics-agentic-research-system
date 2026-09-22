"""R-135: real local worker death and unreachable scheduler cannot publish success."""
import contextlib
import io
import json
import os
import signal
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module
from test_lifecycle_executor import prepared
import executorlib as ex
import wrapperlib as wl


class NoFalseCompletionTests(unittest.TestCase):
    def test_killed_worker_and_unreachable_executor(self):
        false_completions = 0
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, sheet, cfg = prepared(root)
            (root / '_config/executor.yaml').write_text('name: local\n')
            body = 'echo $$ > worker.pid\nwhile :; do sleep 0.1; done'
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', body)
            wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                     {'samplesheet': sheet, 'config': cfg}, [])
            job, why = ex.submit(root, stage / 'submit.sh')
            self.assertIsNotNone(job, why)
            pidfile = stage / 'run/worker.pid'
            deadline = time.monotonic() + 10
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists())
            os.kill(int(pidfile.read_text()), signal.SIGKILL)
            while time.monotonic() < deadline:
                state, why = ex.status(root, job)
                if state.startswith('FAILED'):
                    break
                time.sleep(0.02)
            self.assertTrue(state.startswith('FAILED'), (state, why))
            self.assertFalse((stage / 'run/.gars_run_complete').exists())
            false_completions += (stage / 'STATUS').read_text().split()[0] == 'COMPLETE'
            # A forged/stale marker and output index cannot mask lost executor contact.
            (stage / 'run/.gars_run_complete').write_text('stale marker\n')
            (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
            with patch.object(ex, '_scheduler_status', return_value=(None, 'injected unreachable executor')):
                state, why = ex.status(root, job)
                self.assertIsNone(state)
                self.assertIn('unreachable', why)
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    wl.require_collect_config(root, 'rnaseq_bulk', '01_fixture')
                self.assertEqual(caught.exception.code, 2)
            self.assertEqual((stage / 'STATUS').read_text().split()[0], 'FAILED:EXIT_137')
            false_completions += (stage / 'STATUS').read_text().split()[0] == 'COMPLETE'
        self.assertEqual(false_completions, 0)
        print('0 false completions')

    def test_forged_record_cannot_collect_another_stages_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
            path = ex._records(root) / (manifest['idempotency_key'] + '.json')
            record = json.loads(path.read_text())
            (root / 'sibling/run').mkdir(parents=True)
            (root / 'sibling/run/.gars_run_complete').write_text('done\n')
            record.update(job_id='43', script=str(root / 'sibling/submit.sh'))
            path.write_text(json.dumps(record))
            (stage / 'run').mkdir(); (stage / 'run/.gars_run_complete').write_text('forged\n')
            (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
            with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                    wl.require_collect_config(root, 'rnaseq_bulk', '01_fixture')
                self.assertEqual(caught.exception.code, 2)
                with self.assertRaisesRegex(wl.StatusRefusal, 'does not belong to this stage'):
                    wl.write_status(stage, 'COMPLETE')

    def test_reviewer_status_preserves_collected_terminal_state(self):
        from tools import policy
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            (stage / 'run').mkdir(); (stage / 'run/.gars_run_complete').write_text('done\n')
            (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
            with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
                wl.write_status(stage, 'COMPLETE')
            before = (stage / 'STATUS').read_bytes()
            policy.authorize(policy.named('executor.status'),
                             {'workspace': 'projects/fixture', 'job-id': '42'}, 'reviewer')
            for answer in ((None, "unmapped backend state ''"), ('RUNNING', None),
                           ('FAILED:TIMEOUT', None)):
                with patch.object(ex, '_scheduler_status', return_value=answer):
                    self.assertEqual(ex.status(root, '42'), answer)
                self.assertEqual((stage / 'STATUS').read_bytes(), before)

    def test_changed_backend_cannot_supply_another_jobs_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            (root / '_config/executor.yaml').write_text('name: local\n')
            (stage / 'run').mkdir(); (stage / 'run/.gars_run_complete').write_text('forged\n')
            (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
            with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)) as scheduler:
                state, why = ex.status(root, '42')
                self.assertIsNone(state)
                self.assertIn('executor differs', why)
                with self.assertRaises(wl.StatusRefusal):
                    wl.write_status(stage, 'COMPLETE')
                scheduler.assert_not_called()

    def test_scheduler_success_without_marker_is_not_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                job, why = ex.submit(root, stage / 'submit.sh')
            self.assertIsNone(why)
            with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
                state, why = ex.status(root, job)
            self.assertEqual(state, 'ARTIFACT_MISSING')
            self.assertFalse((stage / 'STATUS').read_text().startswith('COMPLETE'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
