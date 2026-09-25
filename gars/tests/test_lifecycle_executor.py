"""Repo-side R-076/R-077 evidence. Stub scheduler is not the Slurm acceptance."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, write_fixture_dataset
import executorlib as ex
import wrapperlib as wl


def prepared(root):
    write_fixture_dataset(root)
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

    def test_edited_key_cannot_resubmit_identical_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('42', None))
                manifest_path = stage / 'reproducibility/manifest.json'
                manifest = json.loads(manifest_path.read_text())
                old = manifest['idempotency_key']; fake = 'f' * 64
                manifest['idempotency_key'] = fake
                manifest_path.write_text(json.dumps(manifest))
                script = stage / 'submit.sh'
                script.write_text(script.read_text().replace(old, fake))
                job, why = ex.submit(root, script)
                self.assertIsNone(job, 'edited key reached scheduler')
                self.assertIn('idempotency_key_missing_or_changed', why)
                self.assertEqual(backend.call_count, 1)

    def test_input_edits_are_rehashed_before_submit(self):
        for target in ('params.yaml', 'sheet.csv', '_config/rnaseq_bulk.yaml'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                path = stage / target if target == 'params.yaml' else root / target
                path.write_text(path.read_text() + '# changed\n')
                with patch.object(ex, '_submit_once', return_value=('99', None)) as backend:
                    job, why = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job)
                self.assertTrue('changed' in why, why)
                backend.assert_not_called()

    def test_definite_refusal_does_not_burn_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            commands = root / 'bin'; commands.mkdir()
            effect = root / 'effects'; sbatch = commands / 'sbatch'
            sbatch.write_text('#!/bin/bash\necho "Socket timed out" >&2\nexit 1\n')
            sbatch.chmod(0o755)
            with patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}):
                job, why = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job)
                self.assertIn('exited 1', why)
                sbatch.write_text('#!/bin/bash\necho submitted >> "' + str(effect) +
                                  '"\necho "Submitted batch job 42"\n')
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('42', None))
            self.assertEqual(effect.read_text().splitlines(), ['submitted'])

    def test_ambiguous_response_retains_reservation(self):
        for code, output in ((0, b'connection lost after acceptance\n'),
                             (-15, b''), (1, b'Submitted batch job 42\n')):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                with patch.object(ex.subprocess, 'run') as backend:
                    backend.return_value.returncode = code
                    backend.return_value.stdout = output
                    backend.return_value.stderr = b''
                    self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                    job, why = ex.submit(root, stage / 'submit.sh')
                    self.assertIsNone(job)
                    self.assertIn('duplicate_submission', why)
                    self.assertEqual(backend.call_count, 1)

    def test_missing_backend_releases_reservation(self):
        for descriptor in (ex.LOCAL, ex.SLURM):
            with self.subTest(backend=descriptor['name']), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                with patch.object(ex.subprocess, 'run', side_effect=FileNotFoundError('missing backend')):
                    job, why = ex.submit(root, stage / 'submit.sh', descriptor=descriptor)
                self.assertIsNone(job)
                self.assertIn('cannot run', why)
                self.assertFalse(list(ex._records(root).glob('*.json')))
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    self.assertEqual(ex.submit(root, stage / 'submit.sh', descriptor=descriptor), ('42', None))

    def test_corrected_failed_or_cancelled_stage_submits_once(self):
        for terminal in ('FAILED:TIMEOUT', 'CANCELLED'):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                commands = root / 'bin'; commands.mkdir()
                effect = root / 'effects'; sbatch = commands / 'sbatch'
                sbatch.write_text('#!/bin/bash\necho submitted >> "' + str(effect) +
                                  '"\necho "Submitted batch job 42"\n')
                sbatch.chmod(0o755)
                with patch.dict(os.environ, {'PATH': str(commands) + os.pathsep + os.environ['PATH']}):
                    self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('42', None))
                    old_key = ex.prepared_key(root, stage)
                    with patch.object(ex, '_scheduler_status', return_value=(terminal, None)):
                        self.assertEqual(ex.status(root, '42'), (terminal, None))
                    self.assertIn('retry_refused', ex.submit(root, stage / 'submit.sh')[1])
                    cfg.write_text('aligner: hisat2\n')
                    wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'true')
                    wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                             {'samplesheet': sheet, 'config': cfg}, [])
                    new_key = ex.prepared_key(root, stage)
                    self.assertNotEqual(old_key, new_key)
                    sbatch.write_text(sbatch.read_text().replace('job 42', 'job 43'))
                    self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('43', None),
                                     'corrected inputs must submit')
                    self.assertEqual((stage / 'STATUS').read_text().split()[:2], ['SUBMITTED', '43'])
                    record = ex.stage_record(root, stage)
                    self.assertEqual(record['supersedes_key'], old_key)
                    self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                    # A late poll of the superseded job must not terminate the new run.
                    with patch.object(ex, '_scheduler_status', return_value=(terminal, None)):
                        ex.status(root, '42')
                    self.assertEqual((stage / 'STATUS').read_text().split()[:2], ['SUBMITTED', '43'])
                self.assertEqual(effect.read_text().splitlines(), ['submitted', 'submitted'])

    def test_reprepare_keeps_tracking_and_blocks_overlapping_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', side_effect=[('42', None), ('43', None)]) as backend:
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('42', None))
                cfg.write_text('aligner: hisat2\n')
                wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'true')
                wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                         {'samplesheet': sheet, 'config': cfg}, [])
                # Refuse overlap even before the first status poll after re-prepare.
                job, why = ex.submit(root, stage / 'submit.sh')
                self.assertIsNone(job, 're-prepare launched an overlapping job')
                self.assertIn('stage_job_unresolved', why)
                for answer in (('RUNNING', None), (None, 'unreachable')):
                    with patch.object(ex, '_scheduler_status', return_value=answer):
                        self.assertEqual(ex.status(root, '42'), answer)
                    if answer[0]:
                        self.assertEqual((stage / 'STATUS').read_text().split()[:2], ['RUNNING', '42'])
                    self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                    self.assertEqual(backend.call_count, 1)
                with patch.object(ex, '_scheduler_status', return_value=('FAILED:TIMEOUT', None)):
                    self.assertEqual(ex.status(root, '42'), ('FAILED:TIMEOUT', None))
                self.assertEqual(wl.read_status(stage), 'FAILED:TIMEOUT')
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('43', None))
                self.assertEqual(backend.call_count, 2)

    def test_status_after_reprepare_validates_record_identity(self):
        for field, value in (('idempotency_key', 'f' * 64), ('script', 'other.sh')):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    ex.submit(root, stage / 'submit.sh')
                path = ex._records(root) / (ex.prepared_key(root, stage) + '.json')
                record = json.loads(path.read_text())
                record[field] = str(stage / value) if field == 'script' else value
                path.write_text(json.dumps(record))
                before = (stage / 'STATUS').read_bytes()
                with patch.object(ex, '_scheduler_status', return_value=('RUNNING', None)):
                    state, why = ex.status(root, '42')
                self.assertIsNone(state)
                self.assertIn('invalid submission record', why)
                self.assertEqual((stage / 'STATUS').read_bytes(), before)


    def test_corrective_submission_refusal_and_ambiguity_preserve_failure(self):
        for detail in (ex.SubmissionFailure('definite refusal'), 'ambiguous response'):
            with self.subTest(detail=detail), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    ex.submit(root, stage / 'submit.sh')
                with patch.object(ex, '_scheduler_status', return_value=('FAILED:TIMEOUT', None)):
                    ex.status(root, '42')
                before = (stage / 'STATUS').read_bytes()
                cfg.write_text('aligner: hisat2\n')
                wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'true')
                wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                         {'samplesheet': sheet, 'config': cfg}, [])
                with patch.object(ex, '_submit_once', return_value=(None, detail)):
                    self.assertEqual(ex.submit(root, stage / 'submit.sh'), (None, detail))
                self.assertEqual((stage / 'STATUS').read_bytes(), before)
                with patch.object(ex, '_submit_once', return_value=('43', None)) as backend:
                    job, why = ex.submit(root, stage / 'submit.sh')
                    if isinstance(detail, ex.SubmissionFailure):
                        self.assertEqual((job, why), ('43', None))
                        backend.assert_called_once()
                    else:
                        self.assertIsNone(job)
                        self.assertIn('duplicate_submission', why)
                        backend.assert_not_called()

    def test_terminal_writer_requires_corrective_record_evidence(self):
        for fault in ('missing_key', 'same_key', 'different_key', 'missing_supersedes', 'wrong_stage', 'old_reason', 'no_job', 'new_state'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    ex.submit(root, stage / 'submit.sh')
                old_key = ex.prepared_key(root, stage)
                with patch.object(ex, '_scheduler_status', return_value=('FAILED:TIMEOUT', None)):
                    ex.status(root, '42')
                before = (stage / 'STATUS').read_bytes()
                cfg.write_text('aligner: hisat2\n')
                wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', 'true')
                wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                         {'samplesheet': sheet, 'config': cfg}, [])
                new_key = ex.prepared_key(root, stage)
                record = {'idempotency_key': new_key, 'script': str(stage / 'submit.sh'),
                          'state': 'SUBMITTED', 'job_id': '43', 'executor': 'slurm',
                          'supersedes_key': old_key}
                supplied = new_key
                if fault == 'missing_key':
                    supplied = None
                elif fault == 'same_key':
                    supplied = old_key
                elif fault == 'different_key':
                    supplied = 'f' * 64
                elif fault == 'missing_supersedes':
                    del record['supersedes_key']
                elif fault == 'no_job':
                    record['job_id'] = None
                elif fault == 'new_state':
                    record['state'] = 'RUNNING'
                else:
                    old_path = ex._records(root) / (old_key + '.json')
                    old = json.loads(old_path.read_text())
                    if fault == 'old_reason':
                        old['state'] = 'FAILED:EXIT_1'
                    else:
                        old['script'] = str(root / '02_bioinformatics/rnaseq_bulk/02_other/submit.sh')
                    old_path.write_text(json.dumps(old))
                ex._save_record(ex._records(root) / (new_key + '.json'), record)
                with self.assertRaises(wl.StatusRefusal):
                    wl.write_status(stage, 'SUBMITTED', submission_key=supplied)
                self.assertEqual((stage / 'STATUS').read_bytes(), before)


    def test_terminal_without_record_refuses_before_backend(self):
        for terminal in ('FAILED:EXIT_1', 'CANCELLED', 'COMPLETE'):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); stage, sheet, cfg = prepared(root)
                (stage / 'STATUS').write_text(terminal + '\n')
                with patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                    job, why = ex.submit(root, stage / 'submit.sh')
                    self.assertIsNone(job)
                    self.assertIn('no matching', why)
                    backend.assert_not_called()

    def test_superseded_terminal_retained_after_empty_poll(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, sheet, cfg = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)):
                ex.submit(root, stage / 'submit.sh')
            old_key = ex.prepared_key(root, stage)
            with patch.object(ex, '_scheduler_status', return_value=('FAILED:TIMEOUT', None)):
                ex.status(root, '42')
            cfg.write_text('aligner: hisat2\n')
            wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                     {'samplesheet': sheet, 'config': cfg}, [])
            with patch.object(ex, '_submit_once', return_value=('43', None)):
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('43', None))
            before = (stage / 'STATUS').read_bytes()
            with patch.object(ex, '_scheduler_status', return_value=(None, 'empty poll')):
                ex.status(root, '42')
            old = json.loads((ex._records(root) / (old_key + '.json')).read_text())
            self.assertEqual(old['state'], 'FAILED:TIMEOUT')
            self.assertEqual((stage / 'STATUS').read_bytes(), before)

    def test_writer_refusal_retains_launched_job_and_reports_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); stage, _, _ = prepared(root)
            with patch.object(ex, '_submit_once', return_value=('42', None)), \
                    patch.object(wl, 'write_status', side_effect=wl.StatusRefusal('injected divergence')):
                job, why = ex.submit(root, stage / 'submit.sh')
            self.assertEqual(job, '42')
            self.assertIn('writer refused', why)
            path, record = ex._job_record(root, job)
            self.assertEqual(record['status_error'], 'injected divergence')
            with patch.object(ex, '_submit_once') as backend:
                self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                backend.assert_not_called()

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
