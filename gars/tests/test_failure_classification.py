"""Six injected failures, bounded retries and artifact-gate transitions (R-152)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS
from test_lifecycle_executor import prepared
import executorlib as ex
import wrapperlib as wl


class FailureClassificationTests(unittest.TestCase):
    def test_six_injected_failures(self):
        for state, expected in [('FAILED:EXIT_104', 'transient'),
                                ('FAILED:EXIT_137', 'transient'),
                                ('FAILED:TIMEOUT', 'infrastructure'),
                                ('FAILED:EXIT_127', 'tool'),
                                ('FAILED:EXIT_65', 'data_quality'),
                                ('FAILED:EXIT_1', 'workflow')]:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, _, _ = prepared(root)
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    ex.submit(root, stage / 'submit.sh')
                with patch.object(ex, '_scheduler_status', return_value=(state, None)):
                    ex.status(root, '42')
                record = ex.stage_record(root, stage)
                self.assertEqual(record['failure_class'], expected)
                self.assertEqual(Path(record['failure_artifact']).read_text(), expected + '\n')
                self.assertEqual(Path(record['failure_artifact']).with_suffix('.log').read_text(), state + '\n')
                self.assertEqual(wl.read_status(stage), state)
        for code in [104] + list(range(130, 146)):
            self.assertEqual(ex.classify('FAILED', code), 'transient')
        for reason in ('TIMEOUT', 'OUT_OF_MEMORY', 'NODE_FAIL'):
            self.assertEqual(ex.classify(reason, 137), 'infrastructure')
        self.assertEqual(ex.classify('FAILED', 126), 'tool')
        self.assertIsNone(ex.classify('COMPLETED', 0))
        print('six injected failures classified')

    def test_only_transient_retries_at_existing_max_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, _, _ = prepared(root)
            (root / '_config/nextflow.slurm.config').write_bytes(
                (GARS / '_templates/config/nextflow.slurm.config').read_bytes())
            work = stage / 'run/.nextflow'; work.mkdir(parents=True)
            (work / 'retained').write_text('cache')
            with patch.object(ex, '_submit_once', side_effect=[(str(i), None) for i in range(42, 47)]) as backend:
                for i in range(4):
                    job, why = ex.submit(root, stage / 'submit.sh')
                    self.assertEqual(job, str(42 + i), why)
                    self.assertEqual(wl.read_status(stage), 'SUBMITTED')
                    with patch.object(ex, '_scheduler_status', return_value=('FAILED:EXIT_104', None)):
                        ex.status(root, job)
                    self.assertEqual(wl.read_status(stage), 'FAILED:EXIT_104')
                job, why = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job, 'retry exceeded maxRetries')
                self.assertIn('maxRetries', why)
                self.assertEqual(backend.call_count, 4)
            self.assertEqual((work / 'retained').read_text(), 'cache')
            self.assertEqual(len(ex.stage_record(root, stage)['attempts']), 3)
            self.assertIn('RESUME="-resume"', (stage / 'submit.sh').read_text())
            record = ex.stage_record(root, stage)
            Path(record['failure_artifact']).write_text('workflow\n')
            self.assertIn('differs', ex.retry_refusal(root, stage, record, 0))

    def test_retry_after_correction_keeps_prior_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            (root / '_config/nextflow.slurm.config').write_text('maxRetries = 3\n')
            with patch.object(ex, '_submit_once', side_effect=[('42', None), ('43', None), ('44', None), ('45', None)]):
                ex.submit(root, stage / 'submit.sh')
                original = ex.prepared_key(root, stage)
                with patch.object(ex, '_scheduler_status', return_value=('FAILED:EXIT_104', None)):
                    ex.status(root, '42')
                cfg.write_text('aligner: hisat2\n')
                wl.write_reproducibility(stage, 'rnaseq_bulk', root, {'samplesheet': sheet, 'config': cfg}, [])
                for job in ('43', '44', '45'):
                    self.assertEqual(ex.submit(root, stage / 'submit.sh'), (job, None))
                    self.assertEqual(ex.stage_record(root, stage)['supersedes_key'], original)
                    with patch.object(ex, '_scheduler_status', return_value=('FAILED:EXIT_104', None)):
                        ex.status(root, job)
                    self.assertEqual(wl.read_status(stage), 'FAILED:EXIT_104')

            cfg.write_text('aligner: star\n')
            wl.write_reproducibility(stage, 'rnaseq_bulk', root, {'samplesheet': sheet, 'config': cfg}, [])
            with patch.object(ex, '_submit_once', return_value=('46', None)) as backend:
                job, why = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job)
                self.assertIn('superseded', why)
                backend.assert_not_called()

    def test_nontransient_and_destructive_retry_requirements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, _, _ = prepared(root)
            (root / '_config/nextflow.slurm.config').write_text('maxRetries = 3\n')
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            with patch.object(ex, '_scheduler_status', return_value=('FAILED:EXIT_104', None)):
                ex.status(root, '42')
            record = ex.stage_record(root, stage); record['destructive'] = True
            ex._save_record(ex._records(root) / (record['idempotency_key'] + '.json'), record)
            with patch.object(ex, '_submit_once') as backend:
                self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                backend.assert_not_called()
            import stage03_analysis as analysis
            workspace = root / 'workspace'; workspace.mkdir()
            with patch.object(analysis.ws, 'workspace_root', return_value=workspace):
                self.assertEqual(ex.approve_action(root, '42', 'cancel'), (True, None))
                self.assertIsNotNone(ex.retry_refusal(root, stage, record, 0))
                self.assertEqual(ex.approve_action(root, '42', 'retry'), (True, None))
                self.assertIsNone(ex.retry_refusal(root, stage, record, 0))
                with patch.object(ex, '_submit_once', return_value=('43', None)):
                    self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('43', None))
            for state in ('FAILED:EXIT_65', 'FAILED:EXIT_127', 'FAILED:TIMEOUT', 'FAILED:EXIT_1'):
                ex.record_failure(stage, record, state, state); record['state'] = state
                self.assertIn('only transient', ex.retry_refusal(root, stage, record, 0))

    def test_scheduler_success_then_collect_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            (stage / 'run').mkdir(); (stage / 'run/.gars_run_complete').write_text('done\n')
            with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
                self.assertEqual(ex.status(root, '42'), ('COMPLETED', None))
                self.assertEqual(wl.read_status(stage), 'VALIDATING')
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(wl.collect_failure(stage, {'failures': ['missing counts']}), 1)
                self.assertEqual(wl.read_status(stage), 'FAILED:EXIT_1')
                ex.status(root, '42')
                self.assertEqual(wl.read_status(stage), 'FAILED:EXIT_1')
            record = ex.stage_record(root, stage)
            self.assertEqual(record['scheduler_state'], 'COMPLETED')
            self.assertEqual(record['state'], 'FAILED:EXIT_1')
            cfg.write_text('aligner: hisat2\n')
            wl.write_reproducibility(stage, 'rnaseq_bulk', root, {'samplesheet': sheet, 'config': cfg}, [])
            with patch.object(ex, '_submit_once', return_value=('43', None)):
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('43', None))


if __name__ == '__main__':
    unittest.main(verbosity=2)
