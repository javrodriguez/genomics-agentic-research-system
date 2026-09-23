"""R-164: run the shipped generated guard through the local executor seam."""
import tempfile
import time
import unittest
from pathlib import Path
from support import bytes_in, run
import executorlib as ex
import wrapperlib as wl


class ExecutorlibResumeTests(unittest.TestCase):
    def test_generated_resume_guard_preserves_work_and_completed_reentry(self):
        # Unit proof of the generated guard only; neither Slurm nor an allowed retry.
        with tempfile.TemporaryDirectory(prefix='gars-guard-') as tmp:
            root = Path(tmp)
            (root / '_system').mkdir()
            (root / '_system/gars-env.sh').write_text(':\n')
            (root / '_config').mkdir()
            (root / '_config/executor.yaml').write_text('name: local\n')
            stage = root / 'stage'; stage.mkdir()
            body = '''if [ "$RESUME" != "-resume" ]; then
    mkdir -p .nextflow work
    echo preserved > work/cache
    echo first >> effects
    exit 104
fi
test "$(cat work/cache)" = preserved
echo second >> effects'''
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', body)
            for expected in (104, 0, 0):
                result = run(['bash', stage / 'submit.sh'])
                self.assertEqual(result.returncode, expected, result.stderr)
            self.assertEqual((stage / 'run/effects').read_text(), 'first\nsecond\n')
            self.assertEqual((stage / 'run/work/cache').read_text(), 'preserved\n')

    def test_interrupted_resume_and_completed_reentry(self):
        with tempfile.TemporaryDirectory(prefix='gars-resume-') as tmp:
            root = Path(tmp)
            (root / '_system').mkdir()
            # Only the external environment is stubbed; the generated guard is unedited.
            (root / '_system/gars-env.sh').write_text(':\n')
            (root / '_config').mkdir()
            (root / '_config/executor.yaml').write_text('name: local\n')
            stage = root / 'stage'
            stage.mkdir()
            body = '''if [ "$RESUME" != "-resume" ]; then
    mkdir -p .nextflow
    echo first >> effects
    exit 17
fi
echo second >> effects'''
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', body)
            def execute(expected):
                job, error = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job)
                self.assertIn('R-073: submit requires a prepared stage or approved analysis', error)
            execute('FAILED')
            run = stage / 'run'
            self.assertFalse((run / '.gars_run_complete').exists())
            self.assertFalse((run / 'effects').exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
