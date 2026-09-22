"""Repo-side R-076/R-077 evidence. Stub scheduler is not the Slurm acceptance."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS
import executorlib as ex
import wrapperlib as wl


def prepared(root):
    (root / '_config').mkdir()
    (root / '_system').mkdir()
    (root / '_system/gars-env.sh').write_text(':\n')
    cfg = root / '_config/rnaseq_bulk.yaml'
    cfg.write_text('aligner: star\n')
    sheet = root / 'sheet.csv'
    sheet.write_text('sample,fastq_1,fastq_2,strandedness\n')
    stage = root / '02_bioinformatics/rnaseq_bulk/01_fixture'
    stage.mkdir(parents=True)
    wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', str(sheet))])
    wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'true')
    wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                             {'samplesheet': sheet, 'config': cfg}, [])
    return stage, sheet, cfg


class LifecycleExecutorTests(unittest.TestCase):
    def test_key_is_exact_concatenated_bytes_and_in_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage, sheet, cfg = prepared(Path(tmp))
            key = hashlib.sha256((stage / 'params.yaml').read_bytes() +
                                  sheet.read_bytes() + cfg.read_bytes()).hexdigest()
            manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
            self.assertEqual(manifest['idempotency_key'], key)
            self.assertIn('# idempotency_key=' + key, (stage / 'submit.sh').read_text())

    def test_duplicate_never_reaches_stub_scheduler(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage, sheet, cfg = prepared(root)
            commands = root / 'bin'; commands.mkdir()
            effect = root / 'effects'
            sbatch = commands / 'sbatch'
            sbatch.write_text('#!/bin/bash\necho submitted >> "' + str(effect) +
                              '"\necho "Submitted batch job 123"\n')
            sbatch.chmod(0o755)
            with patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}):
                job, why = ex.submit(root, stage / 'submit.sh')
                self.assertEqual(job, '123', why)
                self.assertEqual((stage / 'STATUS').read_text().split()[:2], ['SUBMITTED', '123'])
                for state in ('SUBMITTED', 'RUNNING', 'COMPLETE'):
                    with patch.object(ex, 'recorded_state', return_value=state):
                        again, why = ex.submit(root, stage / 'submit.sh')
                    self.assertIsNone(again)
                    self.assertIn('duplicate_submission', why)
            self.assertEqual(effect.read_text().splitlines(), ['submitted'])
            print('duplicate side effects 0')

    def test_scheduler_reasons_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            for raw, expected in [('TIMEOUT', 'FAILED:TIMEOUT'),
                                  ('OUT_OF_MEMORY', 'FAILED:OUT_OF_MEMORY'),
                                  ('NODE_FAIL', 'FAILED:NODE_FAIL'),
                                  ('CANCELLED by 1234', 'CANCELLED'),
                                  ('FAILED|17:0', 'FAILED:EXIT_17')]:
                with self.subTest(raw=raw), patch.object(ex.subprocess, 'run') as run:
                    run.return_value.returncode = 0
                    run.return_value.stdout = (raw + '\n').encode()
                    state, why = ex.status(Path(tmp), '123')
                    self.assertEqual(state, expected, why)


if __name__ == '__main__':
    unittest.main(verbosity=2)
