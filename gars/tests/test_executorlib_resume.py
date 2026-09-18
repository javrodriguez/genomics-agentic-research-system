"""R-164: run the shipped generated guard through the local executor seam."""
import tempfile
import time
import unittest
from pathlib import Path
from support import bytes_in
import executorlib as ex
import wrapperlib as wl


class ExecutorlibResumeTests(unittest.TestCase):
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
                self.assertIsNone(error)
                self.assertTrue(job)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    state, detail = ex.status(root, job)
                    if state in ('COMPLETED', 'FAILED'):
                        self.assertEqual(state, expected, detail)
                        return
                    time.sleep(0.02)
                self.fail('local job did not finish')
            execute('FAILED')
            run = stage / 'run'
            self.assertFalse((run / '.gars_run_complete').exists())
            self.assertEqual((run / 'effects').read_text(), 'first\n')
            execute('COMPLETED')
            self.assertEqual((run / 'effects').read_text(), 'first\nsecond\n')
            self.assertTrue((run / '.gars_run_complete').is_file())
            completed = bytes_in(run)
            execute('COMPLETED')
            self.assertEqual(bytes_in(run), completed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
