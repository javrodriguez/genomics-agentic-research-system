"""S03-scripts: a stage 03 analysis's scripts are approved with its plan (FIXES.md item S03-scripts).

`approve` records the sha256 of every file under the analysis's `scripts/` in the approval record,
beside the plan's; `executorlib submit` refuses a stage 03 script that is not in that record or
changed since, before any launcher or backend; `verify` refuses when a submitted script is not the
approved one. So a script written or edited after the user approved the plan never runs as an
approved analysis.
"""
import argparse
import contextlib
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from support import GARS, write_fixture_dataset
from test_approval_forgery import PLAN
import executorlib as ex
import stage03_analysis as analysis

SCRIPT = 'set -euo pipefail\nexit 0\n'


class ScriptApprovalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='stage03-scripts-')
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'gars'
        self.workspace.mkdir()
        (self.workspace / '_references').symlink_to(GARS / '_references', target_is_directory=True)
        self.root = self.workspace / 'projects/p'
        write_fixture_dataset(self.root)
        self.adir = self.root / '03_custom_analysis/01_fixture'
        (self.adir / 'scripts').mkdir(parents=True)
        (self.adir / 'results').mkdir()
        (self.adir / 'results/table.tsv').write_text('fixture\n')
        (self.adir / 'PLAN.md').write_text(PLAN.replace('Status: APPROVED 2026-09-21', 'Status: DRAFT'))
        self.script = self.adir / 'scripts/x.sh'
        self.script.write_text(SCRIPT)
        self.args = argparse.Namespace(project=str(self.root), analysis='01_fixture',
                                       model='fixture', date=None)
        self.addCleanup(patch.stopall)
        patch.object(analysis.ws, 'workspace_root', return_value=self.workspace).start()

    def approve(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = analysis.cmd_approve(self.args, self.workspace)
        return code, json.loads(out.getvalue())

    def record(self):
        path = analysis.approval_record_path(self.adir / 'PLAN.md', self.workspace)
        return json.loads(path.read_text())

    def submit(self, script=None):
        return ex.submit(self.root, script or self.script, ex.LOCAL)

    def finish(self, script=None):
        job, why = self.submit(script)
        self.assertIsNotNone(job, why)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            state = ex._scheduler_status(self.root, job, ex.LOCAL)[0]
            if ex._scheduler_terminal(state):
                return state
            time.sleep(.02)
        self.fail('local fixture did not finish')

    def verify(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = analysis.cmd_verify(self.args, self.workspace)
        return code, json.loads(out.getvalue())

    def test_approve_records_every_script_with_the_plan(self):
        (self.adir / 'scripts/lib').mkdir()
        (self.adir / 'scripts/lib/helper.py').write_text('print(1)\n')
        code, result = self.approve()
        self.assertEqual(code, 0, result)
        self.assertEqual(self.record()['scripts'],
                         {'scripts/lib/helper.py': ex._sha256(self.adir / 'scripts/lib/helper.py'),
                          'scripts/x.sh': ex._sha256(self.script)})
        self.assertEqual(result['scripts'], ['scripts/lib/helper.py', 'scripts/x.sh'])

    def test_a_script_edited_after_approval_is_refused_before_it_runs(self):
        self.assertEqual(self.approve()[0], 0)
        self.script.write_text(SCRIPT.replace('exit 0', 'echo edited\nexit 0'))
        with patch.object(ex, '_local_submit') as backend:
            job, why = self.submit()
            backend.assert_not_called()
        self.assertIsNone(job)
        self.assertIn('scripts/x.sh', why)
        self.assertIn('changed since the plan was approved', why)
        self.assertFalse((self.adir / ex.ANALYSIS_SUBMISSIONS).exists())

    def test_a_script_written_after_approval_is_refused_before_it_runs(self):
        self.assertEqual(self.approve()[0], 0)
        late = self.adir / 'scripts/late.sh'
        late.write_text(SCRIPT)
        with patch.object(ex, '_local_submit') as backend:
            job, why = self.submit(late)
            backend.assert_not_called()
        self.assertIsNone(job)
        self.assertIn('was not approved with the plan', why)

    def test_verify_refuses_a_run_of_a_script_changed_after_approval(self):
        self.assertEqual(self.approve()[0], 0)
        self.script.write_text(SCRIPT.replace('exit 0', 'echo edited\nexit 0'))
        # The run happened anyway (a submission made outside the gate): verify still refuses.
        with patch.object(ex, '_analysis_script_refusal', return_value=None, create=True):
            self.assertEqual(self.finish(), 'COMPLETED')
        code, result = self.verify()
        self.assertEqual(code, 2, result)
        self.assertIn('scripts/x.sh', result['error'])

    def test_the_approved_script_runs_and_verifies(self):
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.finish(), 'COMPLETED')
        code, result = self.verify()
        self.assertEqual(code, 0, result)


if __name__ == '__main__':
    unittest.main()
