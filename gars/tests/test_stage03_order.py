"""S03-order: the plan orders its scripts and GARS runs them in that order (FIXES.md item S03-order).

A plan's `## Scripts` section lists its scripts in run order. `approve` refuses a list that does
not name exactly the files under `scripts/`, and writes `scripts/run_all.sh`, which runs them in
that order as one job and stops at the first failure; it is bound with the other scripts.
`executorlib submit` then refuses any other script of that analysis, and `verify` refuses a
declared output older than the run that should have produced it, so a stale copy left by an
earlier attempt never passes as this run's result. A plan without a Scripts section keeps the
earlier behaviour.

The runner is one job, so it carries one set of Slurm directives, written by `approve` from the
listed scripts' leading `#SBATCH` lines (the fold of REVIEW-85a1b4a, finding 1): `--time` is the
sum of the scripts' times, memory and `--cpus-per-task` the largest, and every other directive
must agree; a disagreement or a value approve cannot parse is refused with nothing written. The
launcher and the venue policy then read the runner's directives, as they read a single script's.
"""
import argparse
import contextlib
import io
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from support import GARS, write_fixture_dataset
import executorlib as ex
import stage03_analysis as analysis

PLAN = '''# Analysis plan
Status: DRAFT
## Goal
Two steps, the second reading the first's output.
## Scripts
1. scripts/01_first.sh
2. scripts/02_second.sh
## Outputs
| File | Type | Description |
|---|---|---|
| results/a.tsv | table | step one |
| results/b.tsv | table | step two, read from step one |
## Execution
Runs: batch
'''
FIRST = 'set -euo pipefail\nprintf "x\\t1\\n" > results/a.tsv\n'
SECOND = 'set -euo pipefail\ncut -f2 results/a.tsv > results/b.tsv\n'


class ScriptOrderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='stage03-order-')
        self.addCleanup(self.tmp.cleanup)
        self.workspace = Path(self.tmp.name) / 'gars'
        self.workspace.mkdir()
        (self.workspace / '_references').symlink_to(GARS / '_references', target_is_directory=True)
        self.root = self.workspace / 'projects/p'
        write_fixture_dataset(self.root)
        self.adir = self.root / '03_custom_analysis/01_fixture'
        (self.adir / 'scripts').mkdir(parents=True)
        (self.adir / 'results').mkdir()
        self.plan = self.adir / 'PLAN.md'
        self.plan.write_text(PLAN)
        self.first = self.adir / 'scripts/01_first.sh'
        self.second = self.adir / 'scripts/02_second.sh'
        self.first.write_text(FIRST)
        self.second.write_text(SECOND)
        self.runner = self.adir / 'scripts/run_all.sh'
        self.args = argparse.Namespace(project=str(self.root), analysis='01_fixture',
                                       model='fixture', date=None)
        self.addCleanup(patch.stopall)
        patch.object(analysis.ws, 'workspace_root', return_value=self.workspace).start()

    def approve(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = analysis.cmd_approve(self.args, self.workspace)
        return code, json.loads(out.getvalue())

    def finish(self, script):
        job, why = ex.submit(self.root, script, ex.LOCAL)
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

    def test_approve_writes_the_runner_in_plan_order_and_binds_it(self):
        code, result = self.approve()
        self.assertEqual(code, 0, result)
        self.assertEqual(result['runner'], 'scripts/run_all.sh')
        lines = [l for l in self.runner.read_text().splitlines() if l.startswith('bash ')]
        self.assertEqual(lines, ['bash scripts/01_first.sh', 'bash scripts/02_second.sh'])
        record = json.loads(analysis.approval_record_path(self.plan, self.workspace).read_text())
        self.assertEqual(record['scripts']['scripts/run_all.sh'], ex._sha256(self.runner))

    def test_a_list_that_does_not_name_exactly_the_scripts_is_refused(self):
        (self.adir / 'scripts/03_extra.sh').write_text('exit 0\n')
        code, result = self.approve()
        self.assertEqual(code, 2, result)
        self.assertTrue(any('03_extra.sh' in b for b in result['blocked']), result['blocked'])
        self.assertFalse(self.runner.exists())

    def test_the_runner_runs_in_order_and_verifies(self):
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.finish(self.runner), 'COMPLETED')
        self.assertEqual((self.adir / 'results/b.tsv').read_text(), '1\n')
        self.assertEqual(self.verify()[0], 0)

    def test_the_runner_stops_at_the_first_failure(self):
        self.first.write_text('exit 3\n')
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.finish(self.runner), 'FAILED:EXIT_3')
        self.assertFalse((self.adir / 'results/b.tsv').exists(), 'step two ran after a failure')

    def test_one_script_of_an_ordered_plan_is_refused(self):
        self.assertEqual(self.approve()[0], 0)
        with patch.object(ex, '_local_submit') as backend:
            job, why = ex.submit(self.root, self.second, ex.LOCAL)
            backend.assert_not_called()
        self.assertIsNone(job)
        self.assertIn('scripts/run_all.sh', why)

    def test_a_stale_output_from_an_earlier_attempt_is_refused(self):
        """The plan's red case: step one writes nothing new, step two reads a planted old copy."""
        self.first.write_text('exit 0\n')
        stale = self.adir / 'results/a.tsv'
        stale.write_text('x\t9\n')
        old = time.time() - 86400
        os.utime(str(stale), (old, old))
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.finish(self.runner), 'COMPLETED')
        code, result = self.verify()
        self.assertEqual(code, 2, result)
        self.assertIn('results/a.tsv', result['error'])

    def test_a_plan_without_a_scripts_section_keeps_single_submissions(self):
        self.plan.write_text(PLAN.replace('## Scripts\n1. scripts/01_first.sh\n'
                                          '2. scripts/02_second.sh\n', ''))
        self.assertEqual(self.approve()[0], 0)
        self.assertFalse(self.runner.exists())
        self.assertEqual(self.finish(self.first), 'COMPLETED')


class RunnerDirectiveTests(unittest.TestCase):
    """The runner's #SBATCH lines are the listed scripts' (the fold of REVIEW-85a1b4a, finding 1)."""

    setUp = ScriptOrderTests.setUp
    approve = ScriptOrderTests.approve

    def directives(self):
        return [l for l in self.runner.read_text().splitlines() if l.startswith('#SBATCH')]

    def refused_with_nothing_written(self):
        code, result = self.approve()
        self.assertEqual(code, 2, result)
        self.assertFalse(self.runner.exists())
        self.assertIn('Status: DRAFT', self.plan.read_text())
        self.assertFalse(analysis.approval_record_path(self.plan, self.workspace).exists())
        return ' '.join(result['blocked'])

    def test_the_slurm_launcher_carries_the_scripts_directives(self):
        """The reviewer's reproduction: the launcher's header was `#!/bin/bash` and nothing else."""
        self.first.write_text('#SBATCH --mem=64G\n#SBATCH --time=12:00:00\n' + FIRST)
        self.assertEqual(self.approve()[0], 0)
        with patch.object(ex, '_submit_once', return_value=('J', None)) as backend:
            job, why = ex.submit(self.root, self.runner, ex.SLURM)
        self.assertEqual((job, why), ('J', None))
        header = Path(backend.call_args[0][1]).read_text().split('cd ', 1)[0]
        self.assertIn('#SBATCH --mem=64G\n', header)
        self.assertIn('#SBATCH --time=12:00:00\n', header)

    def test_the_local_venue_refuses_the_runner_as_it_refuses_the_script(self):
        alone = self.root / '03_custom_analysis/02_alone'
        (alone / 'scripts').mkdir(parents=True)
        (alone / 'results').mkdir()
        (alone / 'PLAN.md').write_text(PLAN.replace('## Scripts\n1. scripts/01_first.sh\n'
                                                    '2. scripts/02_second.sh\n', ''))
        script = alone / 'scripts/01_first.sh'
        script.write_text('#SBATCH --mem=64G\n' + FIRST)
        self.first.write_text('#SBATCH --mem=64G\n' + FIRST)
        refusals = []
        for name, submitted in (('02_alone', script), ('01_fixture', self.runner)):
            self.args.analysis = name
            self.assertEqual(self.approve()[0], 0)
            with patch.object(ex, '_local_submit') as backend:
                job, why = ex.submit(self.root, submitted, ex.LOCAL)
                backend.assert_not_called()
            self.assertIsNone(job)
            refusals.append(why)
        self.assertIn('venue_not_permitted: venue local memory rule: above 8 GiB', refusals[0])
        self.assertEqual(refusals[1], refusals[0])

    def test_the_scripts_times_add_up(self):
        self.first.write_text('#SBATCH --time=12:00:00\n' + FIRST)
        self.second.write_text('#SBATCH --time=12:00:00\n' + SECOND)
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.directives(), ['#SBATCH --time=24:00:00'])

    def test_the_largest_memory_and_cpus_win(self):
        self.first.write_text('#SBATCH --mem=16G\n#SBATCH --cpus-per-task=2\n' + FIRST)
        self.second.write_text('#SBATCH --mem=4096M\n#SBATCH --cpus-per-task=8\n' + SECOND)
        self.assertEqual(self.approve()[0], 0)
        self.assertEqual(self.directives(), ['#SBATCH --mem=16G', '#SBATCH --cpus-per-task=8'])

    def test_a_disagreement_is_refused_naming_the_scripts_and_the_directive(self):
        self.first.write_text('#SBATCH --partition=short\n' + FIRST)
        self.second.write_text('#SBATCH --partition=long\n' + SECOND)
        blocked = self.refused_with_nothing_written()
        for word in ('--partition', 'scripts/01_first.sh', 'scripts/02_second.sh'):
            self.assertIn(word, blocked)

    def test_a_time_on_some_scripts_only_is_refused(self):
        self.first.write_text('#SBATCH --time=12:00:00\n' + FIRST)
        blocked = self.refused_with_nothing_written()
        for word in ('--time', 'scripts/02_second.sh'):
            self.assertIn(word, blocked)

    def test_a_value_approve_cannot_parse_is_refused(self):
        self.first.write_text('#SBATCH --mem=lots\n' + FIRST)
        blocked = self.refused_with_nothing_written()
        for word in ('--mem', 'scripts/01_first.sh'):
            self.assertIn(word, blocked)


if __name__ == '__main__':
    unittest.main()
