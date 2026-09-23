"""R-073 acceptance: real verification, protected store, expiry and plan identity."""
import argparse
import contextlib
import hashlib
import datetime
import os
from unittest.mock import patch
import io
import json
import tempfile
import unittest
from pathlib import Path
from support import GARS
import stage03_analysis as stage
import executorlib as ex
from test_policy_attacks import guard

PLAN = '''# Analysis plan
Status: APPROVED 2026-09-21
## Goal
Synthetic policy test.
## Outputs
| File | Type | Description |
|---|---|---|
| results/table.tsv | table | synthetic |
## Execution
Runs: batch
'''


class ApprovalForgeryTests(unittest.TestCase):
    forgery = None

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='approval-policy-')
        self.workspace=Path(self.tmp.name)/'workspace'
        self.workspace.mkdir()
        (self.workspace/'_references').symlink_to(GARS/'_references', target_is_directory=True)
        self.project=self.workspace/'projects/p'
        self.adir=self.project/'03_custom_analysis/01_policy'
        (self.adir/'results').mkdir(parents=True)
        (self.adir/'results/table.tsv').write_text('a\tb\n1\t2\n')
        (self.adir/'PLAN.md').write_text(PLAN)
        (self.adir/'run').mkdir()
        (self.adir/'run/.gars_run_complete').write_text('synthetic successful execution\n')
        self.args=argparse.Namespace(project=str(self.project),analysis='01_policy',model='fixture',date=None)
        script = self.adir / 'script.sh'; script.write_text('exit 0\n')
        launcher = self.adir / 'run/launcher.sh'; launcher.write_text('exit 0\n')
        (self.adir / ex.ANALYSIS_SUBMISSIONS).write_text(json.dumps({
            'script': str(script), 'script_sha256': ex._sha256(script),
            'launcher': str(launcher), 'launcher_sha256': ex._sha256(launcher),
            'job_id': 'fixture', 'executor': 'local', 'submitted_at': 1}) + '\n')
        jobs = ex._local_jobs_dir(self.project); jobs.mkdir()
        exit_file = self.adir / 'run/launcher.sh.local.exit'; exit_file.write_text('0')
        (jobs / 'fixture.json').write_text(json.dumps({'exit_file': str(exit_file)}))

    def tearDown(self): self.tmp.cleanup()

    def handwritten_record(self, expiry='2099-01-01T00:00:00Z'):
        record={'actor':'human','timestamp':'2026-09-21T00:00:00Z','expiry':expiry,
                'plan_sha256':hashlib.sha256((self.adir/'PLAN.md').read_bytes()).hexdigest(),
                'tool':'stage03_analysis.py approve','template_version':'fixture'}
        (self.adir/'PLAN.md.approved').write_text(json.dumps(record))

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return stage.cmd_verify(self.args,self.workspace)

    def test_forged_status_line(self):
        self.assertEqual(self.verify(),2)

    def test_handwritten_record_after_hook_bypass(self):
        # Simulates an unguarded filesystem writer, not the protected Write tool.
        self.handwritten_record()
        code=self.verify()
        type(self).forgery=int(code==0)
        self.assertEqual(code,2,'workspace sidecar must never authenticate')

    def approve(self):
        (self.adir/'PLAN.md').write_text(PLAN.replace('Status: APPROVED 2026-09-21','Status: DRAFT'))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(stage.cmd_approve(self.args,self.workspace),0)
        return stage.approval_record_path(self.adir/'PLAN.md',self.workspace)

    def test_verify_requires_execution_marker(self):
        self.approve()
        (self.adir/'run/.gars_run_complete').unlink()
        self.assertEqual(self.verify(), 2)
        self.assertFalse((self.adir/'STATUS').exists())
        (self.adir/'run/.gars_run_complete').write_text('synthetic successful execution\n')
        self.assertEqual(self.verify(), 0)
        self.assertEqual((self.adir/'STATUS').read_text().split()[0], 'COMPLETE')

    def test_expired_approval(self):
        path=self.approve()
        self.assertEqual(self.verify(),0)
        record=json.loads(path.read_text())
        record.update(timestamp='2000-01-01T00:00:00Z',expiry='2000-01-02T00:00:00Z')
        path.write_text(json.dumps(record))
        self.assertEqual(self.verify(),2)
        self.assertIn('expired',stage.approval_holds(self.adir/'PLAN.md',path,self.workspace)[1])

    def test_plan_edited_after_approval(self):
        self.approve()
        with (self.adir/'PLAN.md').open('a') as fh: fh.write('\nEdited after approval.\n')
        self.assertEqual(self.verify(),2)

    def test_record_copied_from_another_plan(self):
        path=self.approve()
        original=self.adir/'PLAN.md'
        other=self.adir/'other/PLAN.md'; other.parent.mkdir(); other.write_bytes(original.read_bytes())
        copied=stage.approval_record_path(other,self.workspace)
        copied.write_bytes(path.read_bytes()); copied.chmod(0o600)
        self.assertFalse(stage.approval_holds(other,copied,self.workspace)[0])
        self.assertFalse(stage.approval_holds(original,self.adir/'PLAN.md.approved',self.workspace)[0])

    def test_actor_is_process_identity_and_lifetime_is_utc(self):
        with patch.dict(os.environ,{'USER':'forged','LOGNAME':'forged','GARS_ACTOR':'forged'}):
            path=self.approve()
        record=json.loads(path.read_text())
        self.assertEqual(record['actor'],stage.pwd.getpwuid(os.getuid()).pw_name)
        self.assertEqual(stage.utc_instant(record['expiry'])-stage.utc_instant(record['timestamp']),
                         datetime.timedelta(hours=24))
        self.assertFalse((self.adir/'PLAN.md.approved').exists())
        self.assertEqual(self.verify(),0)

    def test_store_permissions_symlink_and_malformed_expiry_refuse(self):
        path=self.approve(); record=json.loads(path.read_text())
        path.chmod(0o644); self.assertEqual(self.verify(),2); path.chmod(0o600)
        for expiry in ('', '2099-01-01', '2099-01-01T00:00:00+05:00', None):
            record['expiry']=expiry; path.write_text(json.dumps(record))
            self.assertEqual(self.verify(),2)
        path.unlink(); path.symlink_to(self.adir/'PLAN.md')
        self.assertEqual(self.verify(),2)

    def test_cli_cannot_supply_actor_or_relocate_store(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit:
            stage.main(['approve','--project',str(self.project),'--analysis','01_policy','--actor','human'])
        self.assertEqual(exit.exception.code,2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(stage.main(['--workspace',str(self.workspace),'verify',
                                        '--project',str(self.project),'--analysis','01_policy']),2)

    def test_submit_uses_same_store_and_expiry_gate(self):
        import executorlib as ex
        path=self.approve()
        script=self.adir/'submit.sh'; script.write_text('exit 0\n')
        with patch.object(stage.ws,'workspace_root',return_value=self.workspace), \
                patch.object(ex,'_local_submit',return_value='123') as launch:
            self.assertEqual(ex.submit(self.project,script,descriptor=ex.LOCAL),('123',None))
            launch.assert_called_once()
            record=json.loads(path.read_text())
            record.update(timestamp='2000-01-01T00:00:00Z',expiry='2000-01-02T00:00:00Z')
            path.write_text(json.dumps(record)); launch.reset_mock()
            job,why=ex.submit(self.project,script,descriptor=ex.LOCAL)
            self.assertIsNone(job); self.assertIn('expired',why); launch.assert_not_called()

    def test_agent_approve_is_refused(self):
        p=guard('python3 _system/stage03_analysis.py approve --project projects/p --analysis 01_policy')
        self.assertEqual(p.returncode,2)
        self.assertIn(b'R-093',p.stderr)

    def test_verify_rechecks_all_plan_gates(self):
        for old,new in (('| table |','| invented |'),('Runs: batch','Runs: whatever'),
                        ('results/table.tsv','results/../../escape'),
                        ('Synthetic policy test.','<FILL: goal>')):
            with self.subTest(new=new):
                (self.adir/'PLAN.md').write_text(PLAN.replace(old,new))
                path=stage.approval_record_path(self.adir/'PLAN.md',self.workspace)
                stage.check_store(self.workspace,create=True)
                now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
                path.write_text(json.dumps({'actor':stage.LAUNCH_ACTOR,
                    'timestamp':now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'expiry':(now+stage.APPROVAL_LIFETIME).strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'plan_path':str((self.adir/'PLAN.md').resolve()),
                    'plan_sha256':hashlib.sha256((self.adir/'PLAN.md').read_bytes()).hexdigest()}))
                path.chmod(0o600)
                self.assertEqual(self.verify(),2)

    @classmethod
    def tearDownClass(cls):
        if cls.forgery is not None:
            print('forgeable approvals: %d/1' % cls.forgery,flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
