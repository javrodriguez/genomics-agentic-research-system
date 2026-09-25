"""R-164 class 2: an interrupted write keeps the previous artifact and leaves no temp (0087).

Faults are injected at each step of each writer through the os functions it calls; the
observation is the directory afterwards: the previous complete bytes, and no sibling.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import run
import workspace as ws
import wrapperlib as wl


class Boom(Exception):
    pass


def refuse(*args, **kwargs):
    raise OSError('injected fault')


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
