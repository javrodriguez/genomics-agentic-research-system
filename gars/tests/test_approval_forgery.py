"""R-073 acceptance: real verification, including the unresolved record-authenticity gap."""
import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from support import GARS
import stage03_analysis as stage
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
        self.project=Path(self.tmp.name)
        self.adir=self.project/'03_custom_analysis/01_policy'
        (self.adir/'results').mkdir(parents=True)
        (self.adir/'results/table.tsv').write_text('a\tb\n1\t2\n')
        (self.adir/'PLAN.md').write_text(PLAN)
        self.args=argparse.Namespace(project=str(self.project),analysis='01_policy',model='fixture')

    def tearDown(self): self.tmp.cleanup()

    def handwritten_record(self, expiry='2099-01-01T00:00:00Z'):
        record={'actor':'human','timestamp':'2026-09-21T00:00:00Z','expiry':expiry,
                'plan_sha256':hashlib.sha256((self.adir/'PLAN.md').read_bytes()).hexdigest(),
                'tool':'stage03_analysis.py approve','template_version':'fixture'}
        (self.adir/'PLAN.md.approved').write_text(json.dumps(record))

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return stage.cmd_verify(self.args,GARS)

    def test_forged_status_line(self):
        self.assertEqual(self.verify(),2)

    def test_handwritten_record_after_hook_bypass(self):
        # Simulates an unguarded filesystem writer, not the protected Write tool.
        self.handwritten_record()
        code=self.verify()
        type(self).forgery=int(code==0)
        self.assertEqual(code,2,'R-073 NOT met: approval authenticity awaits owner ruling 0053')

    def test_expired_approval(self):
        self.handwritten_record('2000-01-01T00:00:00Z')
        self.assertEqual(self.verify(),2,'R-073 NOT met: expiry policy awaits owner ruling 0053')

    def test_plan_edited_after_approval(self):
        self.handwritten_record()
        with (self.adir/'PLAN.md').open('a') as fh: fh.write('\nEdited after approval.\n')
        self.assertEqual(self.verify(),2)

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
                self.handwritten_record()
                self.assertEqual(self.verify(),2)

    @classmethod
    def tearDownClass(cls):
        if cls.forgery is not None:
            print('forgeable approvals: %d/1' % cls.forgery,flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
