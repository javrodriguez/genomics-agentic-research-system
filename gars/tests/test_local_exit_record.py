"""0195: the local executor's exit record is never read half-written.

The local runner used to create its exit record with a shell redirection and fill it a
moment later, so a status poll between the two read an empty file and recorded a finished
job as a bare, permanent FAILED. These tests freeze the runner in that window with
`ulimit -f 0` (the open succeeds, the first byte kills the runner with SIGXFSZ) and check
the reader's handling of an empty record.
"""
import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS  # noqa: F401  (puts gars/_system on the path)
import executorlib as ex
import wrapperlib as wl

# Run the real LOCAL_RUNNER exactly as _local_submit does, under a zero file-size limit.
FROZEN = 'ulimit -f 0; exec bash -c "$1" gars-local "$2" "$3" "$4"'


def _gone(pid, seconds=10):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        time.sleep(0.01)            # a poll for the process to end, never a timing guess
    return False


class LocalExitRecordTests(unittest.TestCase):
    def frozen_run(self, directory, body):
        script = directory / 'submit.sh'
        script.write_text(body)
        exit_path = directory / 'submit.sh.local.exit'
        proc = subprocess.run(
            ['bash', '-c', FROZEN, 'x', ex.LOCAL_RUNNER, str(script),
             str(directory / 'submit.sh.local.log'), str(exit_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ex.execution_env())
        pid = int(proc.stdout.decode().strip())
        self.assertTrue(_gone(pid), 'the frozen runner %d did not end within 10 s' % pid)
        return exit_path

    def assertWholeOrAbsent(self, exit_path):
        # G1: when the exit record exists, it holds one full integer line.
        if exit_path.exists():
            text = exit_path.read_text()
            self.assertRegex(text, r'\A[0-9]+\n\Z',
                             'exit record published half-written: %r' % text)

    def test_torn_write_never_publishes_an_empty_record(self):
        # C1: the normal path, frozen between the record's creation and its content.
        with tempfile.TemporaryDirectory(prefix='exit-record-') as tmp:
            self.assertWholeOrAbsent(self.frozen_run(Path(tmp), 'exit 17\n'))

    def test_cancel_record_is_published_whole(self):
        # C5: the TERM trap's own write (exit 143), frozen the same way.
        with tempfile.TemporaryDirectory(prefix='exit-record-') as tmp:
            self.assertWholeOrAbsent(self.frozen_run(Path(tmp), 'kill -TERM $PPID; exec sleep 30\n'))

    def empty_record(self, root, job_id):
        jobs = ex._local_jobs_dir(root)
        jobs.mkdir(parents=True)
        exit_file = root / 'submit.sh.local.exit'
        exit_file.write_text('')
        (jobs / ('%s.json' % job_id)).write_text(json.dumps({'exit_file': str(exit_file)}))

    def test_empty_record_with_live_runner_reads_running(self):
        # C2: an empty record is not a verdict while the runner lives. (A partial digit
        # string cannot be told from a full code by any reader; the writer half covers it.)
        with tempfile.TemporaryDirectory(prefix='exit-record-') as tmp:
            job = str(os.getpid())
            self.empty_record(Path(tmp), job)
            self.assertEqual(ex._local_status(Path(tmp), job), 'RUNNING')

    def test_empty_record_with_dead_runner_reads_failed(self):
        # C3: ... and never "running forever": a gone runner that left no code is FAILED.
        with tempfile.TemporaryDirectory(prefix='exit-record-') as tmp:
            self.empty_record(Path(tmp), '42')
            with patch.object(ex.os, 'kill', side_effect=ProcessLookupError) as kill:
                self.assertEqual(ex._local_status(Path(tmp), '42'), 'FAILED')
                kill.assert_called_once_with(42, 0)

    def test_status_keeps_the_exit_code(self):
        # C4: end to end, polled with no pause, the stored verdict keeps the exit code.
        from test_lifecycle_executor import prepared
        with tempfile.TemporaryDirectory(prefix='exit-record-') as tmp:
            root = Path(tmp)
            stage, sheet, cfg = prepared(root)
            (root / '_config/executor.yaml').write_text('name: local\n')
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'exit 17')
            wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                     {'config': cfg, 'samplesheet': sheet}, [])
            job, error = ex.submit(root, stage / 'submit.sh')
            self.assertIsNone(error)
            deadline = time.monotonic() + 10
            state, detail = ex.status(root, job)
            while not state.startswith(('FAILED', 'COMPLETED')) and time.monotonic() < deadline:
                state, detail = ex.status(root, job)
            self.assertEqual(state, 'FAILED:EXIT_17', detail)
            _, record = ex._job_record(root, job)
            self.assertEqual(record['failure_class'], ex.classify('FAILED:EXIT_17', None))


if __name__ == '__main__':
    unittest.main()
