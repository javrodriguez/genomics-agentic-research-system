"""R-164 class 2: an interrupted write keeps the previous artifact and leaves no temp (0087).

Faults are injected at each step of each writer through the os functions it calls; the
observation is the directory afterwards: the previous complete bytes, and no sibling.
"""
import contextlib
import csv
import gzip
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, module, run
from test_lifecycle_executor import prepared
import executorlib as ex
import stage00_register as s00
import stage01_samplesheet as s01
import workspace as ws
import wrapperlib as wl

CLAIMS_FIXTURE = GARS / 'tests/fixtures/claims'


class Boom(Exception):
    pass


def refuse(*args, **kwargs):
    raise OSError('injected fault')


def replace_refused_for(name):
    """os.replace that refuses only when the destination is `name`: one writer, one fault."""
    real = os.replace

    def replace(source, destination, *args, **kwargs):
        if Path(str(destination)).name == name:
            raise OSError('injected fault at %s' % name)
        return real(source, destination, *args, **kwargs)
    return patch.object(ws.os, 'replace', replace)


class Unprintable(object):
    def __str__(self):
        raise Boom('value cannot be rendered')


class FailureRecoveryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-recovery-')
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def names(self, directory=None):
        return sorted(p.name for p in (directory or self.root).iterdir())

    def test_atomic_open_keeps_previous_artifact_at_every_step(self):
        target = self.root / 'artifact.csv'
        steps = [('body', None), ('fsync', 'fsync'), ('replace', 'replace')]
        for label, function in steps:
            with self.subTest(step=label):
                target.write_bytes(b'previous,complete\n')
                with self.assertRaises((Boom, OSError)):
                    if function is None:
                        with ws.atomic_open(target) as fh:
                            fh.write('half')
                            raise Boom('interrupted')
                    else:
                        with patch.object(ws.os, function, refuse):
                            with ws.atomic_open(target) as fh:
                                fh.write('new,partial\n')
                self.assertEqual(target.read_bytes(), b'previous,complete\n')
                self.assertEqual(self.names(), ['artifact.csv'])

    def test_atomic_open_first_write_interrupted_leaves_nothing(self):
        target = self.root / 'fresh.csv'
        with self.assertRaises(Boom):
            with ws.atomic_open(target) as fh:
                fh.write('half')
                raise Boom('interrupted')
        self.assertEqual(self.names(), [])

    def test_atomic_open_success_replaces_and_applies_mode(self):
        target = self.root / 'owned.csv'
        target.write_bytes(b'old\n')
        with ws.atomic_open(target, mode=ws.MACHINE_OWNED_MODE) as fh:
            fh.write('new\n')
        self.assertEqual(target.read_bytes(), b'new\n')
        self.assertEqual(target.stat().st_mode & 0o777, 0o444)
        self.assertEqual(self.names(), ['owned.csv'])

    def test_params_yaml_interrupted_mid_write_keeps_previous(self):
        stage = self.root / 'stage'
        stage.mkdir()
        wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', 'first.csv'), ('n', 1)])
        before = (stage / 'params.yaml').read_bytes()
        with self.assertRaises(Boom):
            wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', 'second.csv'),
                                                        ('n', Unprintable())])
        self.assertEqual((stage / 'params.yaml').read_bytes(), before)
        self.assertEqual(self.names(stage), ['params.yaml'])

    def test_status_write_failure_keeps_previous_status(self):
        stage = self.root / 'stage'
        stage.mkdir()
        self.assertEqual(wl.write_status(stage, 'CREATED'), 'CREATED')
        before = (stage / 'STATUS').read_bytes()
        for function in ('fsync', 'replace'):
            with self.subTest(step=function):
                with patch.object(wl.os, function, refuse):
                    with self.assertRaises(OSError):
                        wl.write_status(stage, 'PLANNED')
                self.assertEqual((stage / 'STATUS').read_bytes(), before)
                self.assertEqual([n for n in self.names(stage) if n.startswith('.STATUS-')], [])
        self.assertEqual(wl.write_status(stage, 'PLANNED'), 'PLANNED')
        self.assertTrue((stage / 'STATUS').read_text().startswith('PLANNED '))

    def built(self, content=b'index\n'):
        built = self.root / 'built'
        (built / 'part').mkdir(parents=True, exist_ok=True)
        (built / 'part/data.bin').write_bytes(content)
        return built

    def test_harvest_publishes_whole_and_leaves_no_incoming(self):
        cache = self.root / 'cache'
        action = wl.harvest_cache(str(cache), 'star', self.built(),
                                  ['pipeline: fixture', 'fasta: f.fa'])
        self.assertEqual(action, 'populated')
        self.assertEqual((cache / 'star/part/data.bin').read_bytes(), b'index\n')
        self.assertEqual((cache / 'PROVENANCE').read_text(), 'pipeline: fixture\nfasta: f.fa\n')
        self.assertEqual(self.names(cache), ['PROVENANCE', 'star'])

    def test_harvest_lost_rename_leaves_no_partial_cache(self):
        cache = self.root / 'cache'
        with patch.object(wl.os, 'rename', refuse):
            action = wl.harvest_cache(str(cache), 'star', self.built(), ['p'])
        self.assertEqual(action, 'reused')
        self.assertEqual(self.names(cache), [])

    def test_harvest_never_overwrites_a_populated_cache(self):
        cache = self.root / 'cache'
        (cache / 'star').mkdir(parents=True)
        (cache / 'star/data.bin').write_bytes(b'winner\n')
        action = wl.harvest_cache(str(cache), 'star', self.built(b'loser\n'), ['p'],
                                  provenance_in_target=True)
        self.assertEqual(action, 'reused')
        self.assertEqual(self.names(cache / 'star'), ['data.bin'])
        self.assertEqual((cache / 'star/data.bin').read_bytes(), b'winner\n')
        self.assertEqual(wl.harvest_cache('', 'star', self.built(), ['p']), 'none')
        empty = self.root / 'empty'
        empty.mkdir()
        self.assertEqual(wl.harvest_cache(str(self.root / 'other'), 'star', empty, ['p']), 'none')
        self.assertFalse((self.root / 'other/star').exists())

    def test_generated_guard_resumes_and_never_repeats_completed_work(self):
        (self.root / '_system').mkdir()
        (self.root / '_system/gars-env.sh').write_text(':\n')
        (self.root / '_config').mkdir()
        (self.root / '_config/executor.yaml').write_text('name: local\n')
        stage = self.root / 'stage'
        stage.mkdir()
        wl.write_submit_sh(stage, self.root, {}, 'fixture', 'rnaseq_bulk',
                           'echo "body [$RESUME]" >> effects')
        script, effects = stage / 'submit.sh', stage / 'run/effects'
        self.assertEqual(run(['bash', script]).returncode, 0)
        self.assertEqual(effects.read_text(), 'body []\n')
        # Completed: the marker short-circuits, even with Nextflow state present.
        (stage / 'run/.nextflow').mkdir()
        self.assertEqual(run(['bash', script]).returncode, 0)
        self.assertEqual(effects.read_text(), 'body []\n')
        # Interrupted after Nextflow started: no marker, state present -> native resume.
        (stage / 'run/.gars_run_complete').unlink()
        self.assertEqual(run(['bash', script]).returncode, 0)
        self.assertEqual(effects.read_text(), 'body []\nbody [-resume]\n')
        self.assertTrue((stage / 'run/.gars_run_complete').is_file())


class CollectWriterRecoveryTests(unittest.TestCase):
    """The collect-side writers: the manifest, the submission record and the report."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-recovery-')
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def submitted(self):
        stage = prepared(self.root)[0]
        (self.root / '_config/executor.yaml').write_text('name: local\n')
        with patch.object(ex, '_submit_once', return_value=('42', None)):
            job, why = ex.submit(self.root, stage / 'submit.sh')
        self.assertEqual(job, '42', why)
        return stage

    def test_complete_manifest_interrupted_keeps_previous_manifest(self):
        stage = self.submitted()
        manifest = stage / 'reproducibility/manifest.json'
        before = manifest.read_bytes()
        listing = sorted(p.name for p in manifest.parent.iterdir())

        def half_then_fail(obj, fh, **kwargs):
            fh.write('{"half": ')
            raise OSError('injected fault')

        faults = [('dump', patch.object(wl.json, 'dump', half_then_fail)),
                  ('fsync', patch.object(wl.os, 'fsync', refuse)),
                  ('replace', patch.object(wl.os, 'replace', refuse))]
        for label, fault in faults:
            with self.subTest(step=label):
                with fault, self.assertRaises(OSError):
                    wl.complete_manifest(stage, 'none', 'COMPLETE')
                self.assertEqual(manifest.read_bytes(), before)
                self.assertEqual(sorted(p.name for p in manifest.parent.iterdir()), listing)
        written = wl.complete_manifest(stage, 'none', 'COMPLETE')
        self.assertEqual(json.loads(manifest.read_text()), written)
        self.assertEqual(written['predicate_facts']['status'], 'COMPLETE')
        self.assertEqual(sorted(p.name for p in manifest.parent.iterdir()), listing)

    def test_submission_record_interrupted_keeps_previous_record(self):
        records = self.root / '.gars_submissions'
        records.mkdir()
        path = records / ('a' * 64 + '.json')
        ex._save_record(path, {'job_id': '1', 'state': 'PENDING'})
        before = path.read_bytes()
        self.assertEqual(json.loads(before.decode()), {'job_id': '1', 'state': 'PENDING'})
        for label in ('unserialisable', 'fsync', 'replace'):
            with self.subTest(step=label):
                if label == 'unserialisable':
                    with self.assertRaises(TypeError):
                        ex._save_record(path, {'job_id': '1', 'state': object()})
                else:
                    with patch.object(ws.os, label, refuse), self.assertRaises(OSError):
                        ex._save_record(path, {'job_id': '1', 'state': 'COMPLETED'})
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(sorted(p.name for p in records.iterdir()), [path.name])

    def test_report_render_interrupted_keeps_previous_report(self):
        renderer = module(GARS / '_system/claims/render_report.py', 'r164_recovery_renderer')
        out = self.root / 'report.md'
        argv = ['--snapshot', str(CLAIMS_FIXTURE / 'snapshot.json'),
                '--manifest', str(CLAIMS_FIXTURE / 'manifest.json'), '--out', str(out)]
        real = renderer.tempfile.NamedTemporaryFile

        def failing_write(*args, **kwargs):
            handle = real(*args, **kwargs)
            handle.write(b'half')
            handle.write = refuse
            return handle

        out.write_bytes(b'previous report\n')
        faults = [('write', patch.object(renderer.tempfile, 'NamedTemporaryFile', failing_write)),
                  ('replace', patch.object(renderer.os, 'replace', refuse))]
        for label, fault in faults:
            with self.subTest(step=label):
                with fault, open(os.devnull, 'w') as sink, patch.object(renderer.sys, 'stderr', sink):
                    self.assertEqual(renderer.main(argv), 1)
                self.assertEqual(out.read_bytes(), b'previous report\n')
                self.assertEqual(self.names(), ['report.md'])
        self.assertEqual(renderer.main(argv), 0)
        self.assertEqual(out.read_bytes(), (CLAIMS_FIXTURE / 'report.md').read_bytes())
        self.assertEqual(self.names(), ['report.md'])

    def names(self):
        return sorted(p.name for p in self.root.iterdir())


class CallSiteRecoveryTests(unittest.TestCase):
    """The same postcondition at the writers' callers and on their recovery branches."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-recovery-')
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def listing(self, directory):
        return sorted(p.name for p in directory.iterdir())

    # -- executorlib.submit: a definite refusal rolls the record back ------------------------

    def test_refused_first_submission_leaves_no_record(self):
        stage = prepared(self.root)[0]
        (self.root / '_config/executor.yaml').write_text('name: local\n')
        refusal = ex.SubmissionFailure('definite refusal')
        with patch.object(ex, '_submit_once', return_value=(None, refusal)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), (None, refusal))
        records = ex._records(self.root)
        self.assertEqual([n for n in self.listing(records) if n != '.lock'], [])
        self.assertEqual(wl.read_status(stage), 'STALE')
        with patch.object(ex, '_submit_once', return_value=('43', None)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), ('43', None))
        self.assertEqual(ex.stage_record(self.root, stage)['job_id'], '43')

    def test_refused_retry_restores_the_failed_record(self):
        stage = prepared(self.root)[0]
        (self.root / '_config/executor.yaml').write_text('name: local\n')
        (self.root / '_config/nextflow.slurm.config').write_text('maxRetries = 3\n')
        with patch.object(ex, '_submit_once', return_value=('42', None)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), ('42', None))
        with patch.object(ex, '_scheduler_status', return_value=('FAILED:EXIT_104', None)):
            ex.status(self.root, '42')
        records = ex._records(self.root)
        names = self.listing(records)
        (path,) = [records / n for n in names if n.endswith('.json')]
        before, status = path.read_bytes(), (stage / 'STATUS').read_bytes()
        refusal = ex.SubmissionFailure('definite refusal')
        with patch.object(ex, '_submit_once', return_value=(None, refusal)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), (None, refusal))
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.listing(records), names)
        self.assertEqual((stage / 'STATUS').read_bytes(), status)
        with patch.object(ex, '_submit_once', return_value=('43', None)):
            self.assertEqual(ex.submit(self.root, stage / 'submit.sh'), ('43', None))
        record = ex.stage_record(self.root, stage)
        self.assertEqual(record['job_id'], '43')
        self.assertEqual([a['job_id'] for a in record['attempts']], ['42'])

    # -- claims/emit_report.py main: the exported snapshot never outlives the call ------------

    def test_emit_report_leaves_no_snapshot_on_any_exit(self):
        emitter = module(GARS / '_system/claims/emit_report.py', 'r164_recovery_emitter')
        out = self.root / 'report.md'
        out.write_bytes(b'previous report\n')
        argv = ['--from-db', 'fixture-db', '--manifest', str(self.root / 'manifest.json'),
                '--project', str(self.root), '--out', str(out)]
        seen = []

        def preflight(code):
            def check(args, transport=None):
                snapshot = Path(args[args.index('--snapshot') + 1])
                seen.append(json.loads(snapshot.read_text()))
                if isinstance(code, Exception):
                    raise code
                return code
            return check

        def renderer(code):
            return lambda *args, **kwargs: subprocess.CompletedProcess(args, code, b'', b'')

        cases = [('preflight refuses', {'k': 'v'}, preflight(3), renderer(0), 3),
                 ('preflight raises', {'k': 'v'}, preflight(OSError('down')), renderer(0), 1),
                 ('renderer fails', {'k': 'v'}, preflight(0), renderer(2), 2),
                 ('export fails', {'k': object()}, preflight(0), renderer(0), 1),
                 ('rendered', {'k': 'v'}, preflight(0), renderer(0), 0)]
        for label, payload, check, render, code in cases:
            with self.subTest(case=label):
                del seen[:]
                with patch.object(emitter.render_report, 'database_snapshot',
                                  return_value=payload), \
                        patch.object(emitter.evidence_check, 'main', check), \
                        patch.object(emitter.subprocess, 'run', render), \
                        open(os.devnull, 'w') as sink, patch.object(emitter.sys, 'stderr', sink):
                    self.assertEqual(emitter.main(argv), code)
                if label != 'export fails':
                    self.assertEqual(seen, [payload])
                self.assertEqual(self.listing(self.root), ['report.md'])
                self.assertEqual(out.read_bytes(), b'previous report\n')

    # -- stage 01: each file main() writes keeps its previous bytes ---------------------------

    def stage01_project(self):
        data = self.root / '00_data/rnaseq_bulk'
        (data / 'raw').mkdir(parents=True)
        (self.root / '_config').mkdir()
        with (data / 'files.csv').open('w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['sample_id', 'lane', 'fastq_1', 'fastq_2'])
            for sample in ('K1', 'K2', 'K3', 'K4'):
                raw = data / 'raw' / ('%s_R1.fastq' % sample)
                raw.write_text('@synthetic\nACGT\n+\nIIII\n')
                writer.writerow([sample, '1', str(raw.relative_to(self.root)), ''])
        return data

    def stage01(self, data, strandedness, second, force=True):
        (self.root / '_config/rnaseq_bulk.yaml').write_text(
            'strandedness: %s\nunit_of_replication: sample\n'
            'reference_release: synthetic-v1\n' % strandedness)
        with (data / 'samples.csv').open('w', newline='') as fh:
            csv.writer(fh).writerows([['sample_id', 'condition', 'group', 'replicate'],
                                      ['K1', 'A', 'GA', '1'], ['K2', 'A', 'GA', '2'],
                                      ['K3', second, 'GB', '1'], ['K4', second, 'GB', '2']])
        with contextlib.redirect_stdout(io.StringIO()):
            return s01.main(['--project', str(self.root)] + (['--force'] if force else []))

    def test_stage01_interrupted_keeps_each_previous_file(self):
        data = self.stage01_project()
        sheets = self.root / '01_samplesheets'
        self.assertEqual(self.stage01(data, 'reverse', 'B', force=False), 0)
        written = ['rnaseq_bulk_samplesheet.csv', 'rnaseq_bulk_design.csv',
                   'rnaseq_bulk_design_check.json']
        self.assertEqual(self.listing(sheets), sorted(written))
        before = {name: (sheets / name).read_bytes() for name in written}
        for name in written:
            with self.subTest(file=name):
                with replace_refused_for(name), self.assertRaises(OSError):
                    self.stage01(data, 'forward', 'C')
                self.assertEqual((sheets / name).read_bytes(), before[name])
                self.assertEqual(self.listing(sheets), sorted(written))
                for other in written:
                    (sheets / other).write_bytes(before[other])
        self.assertEqual(self.stage01(data, 'forward', 'C'), 0)
        for name in written[:2]:
            self.assertNotEqual((sheets / name).read_bytes(), before[name])

    # -- stage 00 finalize: files.csv, samples.csv and the stamped placeholders ---------------

    def finalize(self):
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            return s00.main(['finalize', '--project', str(self.root), '--data-class', 'public',
                             '--purpose', 'fixture', '--date', '2026-09-25'])

    def link(self, sample):
        source = self.root / 'source'
        source.mkdir(exist_ok=True)
        raw = self.root / '00_data/rnaseq_bulk/raw'
        raw.mkdir(parents=True, exist_ok=True)
        for read in ('R1', 'R2'):
            fastq = source / ('%s_S1_L001_%s_001.fastq.gz' % (sample, read))
            fastq.write_bytes(gzip.compress(b'@r\nACGT\n+\nIIII\n'))
            os.symlink(str(fastq), str(raw / fastq.name))

    def test_finalize_interrupted_keeps_each_previous_file(self):
        stamps = {'CONTEXT.md': '# {{project_title}}\n', 'HISTORY.md': 'v {{template_version}}\n'}
        (self.root / '_config').mkdir()
        for name, text in stamps.items():
            (self.root / name).write_text(text)
        self.link('K1')
        self.link('K2')
        data = self.root / '00_data/rnaseq_bulk'
        # First finalize, interrupted at samples.csv: no half-created user file is left.
        with replace_refused_for('samples.csv'), self.assertRaises(OSError):
            self.finalize()
        self.assertEqual(self.listing(data), ['files.csv', 'raw'])
        self.assertEqual(self.finalize(), 0)
        self.assertEqual(self.listing(data), ['files.csv', 'raw', 'samples.csv'])
        # A re-run regenerates files.csv from the same raw/ (the dataset record locks the
        # input list), so the previous bytes are also the expected ones; the fault must still
        # surface, and nothing may be left beside the file.
        files_before = (data / 'files.csv').read_bytes()
        for name, directory, before in [('files.csv', data, files_before)] + [
                (stamp, self.root, text.encode()) for stamp, text in sorted(stamps.items())]:
            with self.subTest(file=name):
                for stamp, text in stamps.items():
                    (self.root / stamp).write_text(text)
                listing = self.listing(directory)
                with replace_refused_for(name), self.assertRaises(OSError):
                    self.finalize()
                self.assertEqual((directory / name).read_bytes(), before)
                self.assertEqual(self.listing(directory), listing)
        self.assertEqual(self.finalize(), 0)
        self.assertEqual((data / 'files.csv').read_bytes(), files_before)
        self.assertEqual((self.root / 'CONTEXT.md').read_text(), '# %s\n' % self.root.name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
