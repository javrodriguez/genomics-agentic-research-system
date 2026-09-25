"""Stage-03 execution evidence: launcher ownership, all jobs, and guarded writes."""
import argparse
import contextlib
import io
import json
import os
import shlex
import tempfile
import time
import unittest
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from support import GARS, run, write_fixture_dataset
import guard_hook
from test_approval_forgery import PLAN
import executorlib as ex
import stage03_analysis as analysis


class Stage03ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='stage03-execution-')
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'gars'; self.workspace.mkdir()
        (self.workspace / '_references').symlink_to(GARS / '_references', target_is_directory=True)
        self.root = self.workspace / 'projects/p'
        write_fixture_dataset(self.root)
        self.adir = self.root / '03_custom_analysis/01_fixture'
        (self.adir / 'scripts').mkdir(parents=True)
        (self.adir / 'results').mkdir()
        (self.adir / 'results/table.tsv').write_text('fixture\n')
        (self.adir / 'PLAN.md').write_text(PLAN.replace('Status: APPROVED 2026-09-21', 'Status: DRAFT'))
        self.args = argparse.Namespace(project=str(self.root), analysis='01_fixture', model='fixture', date=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analysis.cmd_approve(self.args, self.workspace), 0)
        self.script = self.adir / 'scripts/x.sh'; self.script.write_text('set -euo pipefail\nexit 0\n')
        self.marker = self.adir / 'run/.gars_run_complete'
        self.record = self.adir / ex.ANALYSIS_SUBMISSIONS
        self.addCleanup(patch.stopall)
        patch.object(analysis.ws, 'workspace_root', return_value=self.workspace).start()

    def submit(self, script=None, descriptor=None):
        return ex.submit(self.root, script or self.script, descriptor or ex.LOCAL)

    def finish(self, script=None):
        job, why = self.submit(script)
        self.assertIsNotNone(job, why)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            state = ex._scheduler_status(self.root, job, ex.LOCAL)[0]
            if ex._scheduler_terminal(state):
                return job, state
            time.sleep(.02)
        self.fail('local fixture did not finish')

    def verify(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = analysis.cmd_verify(self.args, self.workspace)
        return code, json.loads(output.getvalue())

    def test_nested_script_approval_and_launcher_local_evidence(self):
        job, state = self.finish()
        self.assertEqual(state, 'COMPLETED')
        entries = ex._analysis_entries(self.adir); self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry['script'], str(self.script))
        self.assertEqual(entry['script_sha256'], ex._sha256(self.script))
        launcher = Path(entry['launcher'])
        self.assertEqual(launcher.parent, self.adir / 'run')
        self.assertEqual(entry['launcher_sha256'], ex._sha256(launcher))
        self.assertEqual(entry['job_id'], job)
        self.assertEqual(entry['executor'], 'local')
        self.assertIsInstance(entry['submitted_at'], (int, float))
        self.assertTrue(launcher.with_name(launcher.name + '.local.exit').is_file())
        self.assertTrue(self.marker.is_file())
        self.assertEqual(self.verify()[0], 0)

    def test_approval_precedes_launcher_and_backend(self):
        (self.adir / 'PLAN.md').write_text(PLAN + '\nchanged\n')
        with patch.object(ex, '_local_submit') as backend:
            job, why = self.submit()
            self.assertIsNone(job); self.assertIn('R-073', why); backend.assert_not_called()
        self.assertFalse((self.adir / 'run').exists())
        self.assertFalse(self.record.exists())

    def test_launcher_clears_marker_and_removes_script_forgery_on_failure(self):
        (self.adir / 'run').mkdir()
        self.marker.write_text('stale\n')
        self.script.write_text('set -euo pipefail\n[ ! -e run/.gars_run_complete ]\n'
                               'echo forged > run/.gars_run_complete\nexit 7\n')
        self.assertEqual(self.finish()[1], 'FAILED:EXIT_7')
        self.assertFalse(self.marker.exists(), 'launcher retained a failed script marker')
        self.assertEqual(self.verify()[0], 2)

    def test_slurm_directives_and_launcher_are_handed_to_backend(self):
        directives = b'#SBATCH --cpus-per-task=3\r\n#SBATCH --mem=2G\n'
        self.script.write_bytes(b'#!/bin/bash\n' + directives + b'set -euo pipefail\nexit 0\n')
        with patch.object(ex.subprocess, 'run') as backend:
            backend.return_value.returncode = 0
            backend.return_value.stdout = b'Submitted batch job 42\n'
            backend.return_value.stderr = b''
            self.assertEqual(self.submit(descriptor=ex.SLURM), ('42', None))
            launcher = Path(backend.call_args[0][0][-1])
            self.assertNotEqual(launcher, self.script)
            self.assertEqual(launcher.parent, self.adir / 'run')
            self.assertTrue(launcher.read_bytes().startswith(b'#!/bin/bash\n' + directives))

    def test_resubmit_polls_latest_job_under_lock_and_keeps_history(self):
        self.finish()
        original = self.record.read_bytes()
        for state, rule in [('RUNNING', 'R-076'), ('PENDING', 'R-076'), (None, 'R-077')]:
            with self.subTest(state=state), patch.object(ex, '_scheduler_status', return_value=(state, 'fixture')) as poll, \
                    patch.object(ex, '_submit_once') as backend:
                try:
                    job, why = self.submit(descriptor=ex.SLURM)
                except Exception as exc:
                    self.fail('resubmit must return a readable refusal: %s' % exc)
                self.assertIsNone(job); self.assertIn(rule, why)
                backend.assert_not_called()
                self.assertEqual(poll.call_args[0][2], ex.LOCAL)
                self.assertEqual(self.record.read_bytes(), original)
        for state in ('COMPLETED', 'FAILED:EXIT_7', 'CANCELLED'):
            before = self.record.read_bytes()
            with patch.object(ex, '_scheduler_status', return_value=(state, None)), \
                    patch.object(ex, '_submit_once', return_value=('99', None)):
                self.assertEqual(self.submit(), ('99', None))
            self.assertTrue(self.record.read_bytes().startswith(before))
        self.assertEqual(len(ex._analysis_entries(self.adir)), 4)
        unresolved = ex._analysis_entries(self.adir)[-1]; unresolved['job_id'] = None
        with self.record.open('a') as record:
            record.write(json.dumps(unresolved) + '\n')
        with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)) as poll, \
                patch.object(ex, '_submit_once', return_value=('100', None)) as backend:
            job, why = self.submit()
            self.assertIsNone(job); self.assertIn('R-077', why)
            poll.assert_not_called(); backend.assert_not_called()

    def test_definite_rejection_allows_resubmit_and_verify(self):
        commands = self.root / 'bin'; commands.mkdir()
        sbatch = commands / 'sbatch'
        sbatch.write_text('#!/bin/bash\necho "temporary scheduler rejection" >&2\nexit 1\n')
        sbatch.chmod(0o755)
        # Exercise the real SubmissionFailure classification, before and after history exists.
        for attempt in range(2):
            before = self.record.read_bytes() if self.record.exists() else b''
            with patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}):
                job, why = self.submit(descriptor=ex.SLURM)
            self.assertIsNone(job)
            self.assertIsInstance(why, ex.SubmissionFailure)
            self.assertIn('exited 1', why)
            after = self.record.read_bytes() if self.record.exists() else b''
            self.assertEqual(after, before, 'definite rejection changed submission history')
            self.assertEqual(self.finish()[1], 'COMPLETED')
            self.assertEqual(self.verify()[0], 0)
        self.assertEqual(len(ex._analysis_entries(self.adir)), 2)

    def test_ambiguous_rejection_still_blocks_resubmit_and_verify(self):
        with patch.object(ex.subprocess, 'run') as backend:
            backend.return_value.returncode = 0
            backend.return_value.stdout = b'connection lost after acceptance\n'
            backend.return_value.stderr = b''
            job, why = self.submit(descriptor=ex.SLURM)
        self.assertIsNone(job)
        self.assertNotIsInstance(why, ex.SubmissionFailure)
        entries = ex._analysis_entries(self.adir)
        self.assertEqual(len(entries), 1)
        self.assertIsNone(entries[0]['job_id'])
        original = self.record.read_bytes()
        with patch.object(ex, '_submit_once', return_value=('99', None)) as backend:
            job, why = self.submit()
            self.assertIsNone(job); self.assertIn('R-077', why)
            backend.assert_not_called()
        self.assertEqual(self.record.read_bytes(), original)
        second = self.adir / 'scripts/y.sh'; second.write_text('exit 0\n')
        self.assertEqual(self.finish(second)[1], 'COMPLETED')
        code, result = self.verify()
        self.assertEqual(code, 2)
        self.assertIn('submission has no job id', result['error'])

    def test_verify_refuses_reused_missing_or_invalid_local_pid_record(self):
        job, _ = self.finish()
        path = ex._local_jobs_dir(self.root) / (job + '.json')
        original = path.read_bytes()
        local = json.loads(original)
        other = self.root / 'other.sh'; other.write_text('exit 0\n')
        for fault in ('reused', 'missing', 'invalid', 'non-object', 'no-script'):
            with self.subTest(fault=fault):
                altered = dict(local)
                if fault == 'reused':
                    altered['script'] = str(other)
                elif fault == 'no-script':
                    del altered['script']
                path.write_text(json.dumps(altered))
                if fault == 'missing':
                    path.unlink()
                elif fault == 'invalid':
                    path.write_text('{')
                elif fault == 'non-object':
                    path.write_text('[]')
                with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)) as poll:
                    code, result = self.verify()
                    self.assertEqual(code, 2)
                    self.assertIn('marker is not execution evidence', result['error'])
                    self.assertIn('local PID record differs from submission launcher', result['error'])
                    poll.assert_not_called()
                self.assertFalse((self.adir / 'STATUS').exists())
                path.write_bytes(original)
        self.assertEqual(self.verify()[0], 0)

    def reused_pid_status(self, exit_code, expected, written):
        from test_lifecycle_executor import prepared
        import wrapperlib as wl
        job, _ = self.finish()
        stage, _, _ = prepared(self.root)
        # Deterministically model the later local submit overwriting the PID's record.
        def reused(root, script):
            exit_file = stage / 'submit.sh.local.exit'
            exit_file.write_text(str(exit_code))
            (ex._local_jobs_dir(root) / (job + '.json')).write_text(json.dumps({
                'script': str(script), 'exit_file': str(exit_file), 'started_at': time.time()}))
            return job
        with patch.object(ex, '_local_submit', side_effect=reused):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh', ex.LOCAL), (job, None))
        (stage / 'run').mkdir(exist_ok=True)
        (stage / 'run/.gars_run_complete').write_text('fixture\n')
        # With no matching stage-02 backend, stale analysis metadata must still refuse.
        self.assertIsNone(ex._analysis_job_descriptor(self.root, job, ex.SLURM))
        self.assertEqual(ex.status(self.root, job, ex.LOCAL)[0], expected)
        self.assertEqual(wl.read_status(stage), written)
        self.assertEqual(ex._job_record(self.root, job)[1]['state'], expected)
        code, result = self.verify()
        self.assertEqual(code, 2)
        self.assertIn('local PID record differs from submission launcher', result['error'])

    def test_reused_pid_status_updates_stage02_success(self):
        self.reused_pid_status(0, 'COMPLETED', 'VALIDATING')

    def test_reused_pid_status_updates_stage02_failure(self):
        self.reused_pid_status(7, 'FAILED:EXIT_7', 'FAILED:EXIT_7')

    def scheduler_stubs(self, job):
        commands = self.root / 'bin'; commands.mkdir()
        calls = self.root / 'scheduler-calls'
        answer = self.root / 'scheduler-answer'; answer.write_text('RUNNING|0:0\n')
        for name, body in (
                ('sbatch', 'echo "Submitted batch job %s"\n' % job),
                ('sacct', 'echo "$*" >> %s\ncase "$*" in\n'
                 '  *State,ExitCode*) cat %s ;;\n'
                 '  *) echo 2026-09-23T00:00:00 ;;\nesac\n' %
                 (shlex.quote(str(calls)), shlex.quote(str(answer))))):
            command = commands / name
            command.write_text('#!/bin/bash\n' + body); command.chmod(0o755)
        patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}).start()
        return calls, answer

    def test_stage02_slurm_status_wins_over_analysis_local_id(self):
        from test_lifecycle_executor import prepared
        import wrapperlib as wl
        job, _ = self.finish()
        stage, _, _ = prepared(self.root)
        calls, answer = self.scheduler_stubs(job)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ex.main(['submit', '--workspace', str(self.root),
                                      str(stage / 'submit.sh')]), 0)
        submitted = json.loads(output.getvalue())
        # A local caller can still address the analysis without updating stage 02.
        self.assertEqual(ex.status(self.root, job, ex.LOCAL), ('COMPLETED', None))
        self.assertEqual(wl.read_status(stage), 'SUBMITTED')
        self.assertFalse(calls.exists())
        for descriptor in (ex.SLURM, None):
            self.assertEqual(ex.status(self.root, job, descriptor), ('RUNNING', None))
            self.assertEqual(wl.read_status(stage), 'RUNNING')
            self.assertEqual(ex._job_record(self.root, job)[1]['state'], 'RUNNING')
        (stage / 'run').mkdir(exist_ok=True)
        (stage / 'run/.gars_run_complete').write_text('fixture\n')
        answer.write_text('COMPLETED|0:0\n')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ex.main(['status', '--workspace', str(self.root), job]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['state'], 'COMPLETED')
        self.assertEqual(result['executor'], 'slurm')
        self.assertEqual(submitted['executor'], 'slurm')
        self.assertEqual(wl.read_status(stage), 'VALIDATING')
        self.assertEqual(ex._job_record(self.root, job)[1]['state'], 'COMPLETED')
        self.assertEqual(sum('State,ExitCode' in call for call in calls.read_text().splitlines()), 3)
        self.assertEqual(self.verify()[0], 0)

    def test_stage02_local_status_wins_over_analysis_slurm_id(self):
        from test_lifecycle_executor import prepared
        import wrapperlib as wl
        job = '4242'
        calls, _ = self.scheduler_stubs(job)
        self.assertEqual(self.submit(descriptor=ex.SLURM), (job, None))
        stage, _, _ = prepared(self.root)
        (self.root / '_config/executor.yaml').write_text('name: local\n')
        def local_record(root, script):
            jobs = ex._local_jobs_dir(root); jobs.mkdir(exist_ok=True)
            exit_file = stage / 'submit.sh.local.exit'; exit_file.write_text('7\n')
            (jobs / (job + '.json')).write_text(json.dumps({
                'script': str(script), 'exit_file': str(exit_file), 'started_at': time.time()}))
            return job
        output = io.StringIO()
        with patch.object(ex, '_local_submit', side_effect=local_record), contextlib.redirect_stdout(output):
            self.assertEqual(ex.main(['submit', '--workspace', str(self.root),
                                      str(stage / 'submit.sh')]), 0)
        submitted = json.loads(output.getvalue())
        self.assertEqual(ex.status(self.root, job, ex.SLURM), ('RUNNING', None))
        self.assertEqual(wl.read_status(stage), 'SUBMITTED')
        before = calls.read_bytes()
        self.assertEqual(ex.status(self.root, job, ex.LOCAL), ('FAILED:EXIT_7', None))
        self.assertEqual(wl.read_status(stage), 'FAILED:EXIT_7')
        self.assertEqual(ex._job_record(self.root, job)[1]['state'], 'FAILED:EXIT_7')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(ex.main(['status', '--workspace', str(self.root), job]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['state'], 'FAILED:EXIT_7')
        self.assertEqual(result['executor'], 'local')
        self.assertEqual(submitted['executor'], 'local')
        self.assertEqual(calls.read_bytes(), before, 'local status queried Slurm')

    def test_concurrent_same_script_is_serialized(self):
        barrier = threading.Barrier(2)
        def approved(adir):
            barrier.wait(timeout=5)
            return True, None
        def launch(*args):
            time.sleep(.1)
            return '42', None
        with patch.object(ex, '_analysis_approval', side_effect=approved), \
                patch.object(ex, '_submit_once', side_effect=launch) as backend, \
                patch.object(ex, '_scheduler_status', return_value=('RUNNING', None)), \
                ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.submit) for _ in range(2)]
            answers = [job.result(timeout=10) for job in jobs]
        self.assertEqual(sum(job is not None for job, _ in answers), 1)
        self.assertEqual(backend.call_count, 1)
        self.assertEqual(len(ex._analysis_entries(self.adir)), 1)

    def test_marker_without_record_is_not_execution_evidence(self):
        self.marker.parent.mkdir(); self.marker.write_text('forged\n')
        code, result = self.verify()
        self.assertEqual(code, 2)
        self.assertIn('marker is not execution evidence', result['error'])
        self.assertIn('submitted before this fix', result['error'])
        self.assertFalse((self.adir / 'STATUS').exists())

    def test_verify_binds_paths_hashes_and_scheduler_for_every_latest_script(self):
        job, _ = self.finish()
        second = self.adir / 'scripts/y.sh'; second.write_text('exit 0\n')
        second_job, _ = self.finish(second)
        original = self.record.read_bytes()
        entries = ex._analysis_entries(self.adir)
        outside = self.root / 'outside.sh'; outside.write_bytes(self.script.read_bytes())
        for kind in ('script', 'launcher'):
            for fault in ('path', 'hash'):
                with self.subTest(kind=kind, fault=fault):
                    altered = [dict(e) for e in entries]
                    altered[0][kind if fault == 'path' else kind + '_sha256'] = str(outside) if fault == 'path' else '0'*64
                    self.record.write_text(''.join(json.dumps(e) + '\n' for e in altered))
                    code, result = self.verify()
                    self.assertEqual(code, 2)
                    self.assertIn('marker is not execution evidence', result['error'])
        altered = [dict(e) for e in entries]; altered[0]['job_id'] = None
        self.record.write_text(''.join(json.dumps(e) + '\n' for e in altered))
        with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
            code, result = self.verify()
            self.assertEqual(code, 2)
            self.assertIn('submission has no job id', result['error'])
        self.record.write_bytes(original)
        for state in ('RUNNING', 'FAILED:EXIT_7', 'CANCELLED', None):
            with self.subTest(state=state), patch.object(ex, '_scheduler_status',
                    side_effect=lambda root, jid, descriptor: (state if jid == job else 'COMPLETED', None)):
                self.assertEqual(self.verify()[0], 2)
        # A superseded failure does not defeat the latest completed entry of that script.
        old = dict(entries[0]); old['job_id'] = 'old-failed'
        self.record.write_text(json.dumps(old) + '\n' + original.decode())
        with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)) as poll:
            self.assertEqual(self.verify()[0], 0)
            self.assertEqual({c[0][1] for c in poll.call_args_list}, {job, second_job})
            self.assertTrue(all(c[0][2] == ex.LOCAL for c in poll.call_args_list))

    def test_login_node_uses_local_executor_and_status(self):
        # Recreate the approved fixture plan with its explicitly requested venue.
        plan = self.adir / 'PLAN.md'
        approval = analysis.approval_record_path(plan, self.workspace); approval.unlink()
        plan.write_text(PLAN.replace('Status: APPROVED 2026-09-21', 'Status: DRAFT').replace('Runs: batch', 'Runs: login-node (user-requested)'))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(analysis.cmd_approve(self.args, self.workspace), 0)
        def local_record(root, launcher, job):
            jobs = ex._local_jobs_dir(root); jobs.mkdir(exist_ok=True)
            (jobs / (job + '.json')).write_text(json.dumps({'script': str(launcher)}))
            return job
        with patch.object(ex, '_local_submit',
                          side_effect=lambda root, launcher: local_record(root, launcher, '123')) as backend:
            self.assertEqual(self.submit(descriptor=ex.SLURM), ('123', None))
            backend.assert_called_once()
        # The public CLI also reports the backend the approved plan actually selected.
        # An existing Slurm stage-02 record must not relabel this known local script.
        from test_lifecycle_executor import prepared
        stage, _, _ = prepared(self.root)
        with patch.object(ex, '_submit_once', return_value=('124', None)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh', ex.SLURM), ('124', None))
        other = self.adir / 'scripts/cli.sh'; other.write_text('exit 0\n')
        output = io.StringIO()
        with patch.object(ex, '_local_submit',
                          side_effect=lambda root, launcher: local_record(root, launcher, '124')), contextlib.redirect_stdout(output):
            self.assertEqual(ex.main(['submit', '--workspace', str(self.root), str(other)]), 0)
        self.assertEqual(json.loads(output.getvalue())['executor'], 'local')
        with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)) as poll:
            self.assertEqual(ex.status(self.root, '123', ex.SLURM)[0], 'COMPLETED')
            self.assertEqual(poll.call_args[0][2], ex.LOCAL)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(ex.main(['status', '--workspace', str(self.root), '123']), 0)
            self.assertEqual(json.loads(output.getvalue())['executor'], 'local')

    def test_run_and_submission_record_are_guarded(self):
        targets = ['run/.gars_run_complete', 'run/launch.sh', 'run/launch.sh.local.exit',
                   'run/launch.sh.local.log', 'run/nested/arbitrary', ex.ANALYSIS_SUBMISSIONS]
        settings = json.loads((GARS / '.claude/settings.json').read_text())['permissions']['deny']
        for glob in ('projects/*/03_custom_analysis/*/run/*',
                     'projects/*/03_custom_analysis/*/run/**/*',
                     'projects/*/03_custom_analysis/*/' + ex.ANALYSIS_SUBMISSIONS):
            self.assertIn(glob, guard_hook.READ_ONLY)
            for tool in ('Write', 'Edit'):
                self.assertIn(tool + '(' + glob + ')', settings)
        for target in targets:
            path = 'projects/p/03_custom_analysis/01_fixture/' + target
            for tool in ('Write', 'Edit'):
                result = run(['python3', GARS / '_system/guard_hook.py'], cwd=GARS,
                             env={'CLAUDE_PROJECT_DIR': str(GARS)}, stdin=json.dumps({
                                 'tool_name': tool, 'cwd': str(GARS), 'tool_input': {'file_path': path}}))
                self.assertEqual(result.returncode, 2, path)
            for command in ('echo forged > ' + path, 'cp source ' + path, 'tee ' + path,
                            'python3 -c "open(\'%s\', \'w\')"' % path,
                            'bash projects/p/03_custom_analysis/01_fixture/scripts/x.sh'):
                result = run(['python3', GARS / '_system/guard_hook.py'], cwd=GARS,
                             env={'CLAUDE_PROJECT_DIR': str(GARS)}, stdin=json.dumps({
                                 'tool_name': 'Bash', 'cwd': str(GARS), 'tool_input': {'command': command}}))
                self.assertEqual(result.returncode, 2, command)


if __name__ == '__main__':
    unittest.main(verbosity=2)
