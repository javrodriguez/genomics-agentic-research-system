"""T57 (0293): `compute.mem` is seeded from the venue's own table and only ever lowered by code.

Stage 00 `create` fills each assay template's `{{mem}}` slot from `venue_policy.SEEDED_MEM` for
the venue the workspace's descriptor template names; on a Slurm (or homelab) workspace that is
today's value byte for byte. `configure.py lower` re-seeds one project's `compute.mem` when the
venue has a code memory ceiling and the request is above it: it writes only that line, takes no
value and no decision, and offers nothing when the venue would refuse the run anyway. The
ceiling itself stays `venue_policy.check`'s, compared at submit, unchanged.
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, write_fixture_dataset
import configure
import executorlib as ex
import guard_hook
import stage00_register as s00
import venue_policy as vp
import wrapperlib as wl

ASSAYS = ('atacseq_bulk', 'chipseq_bulk', 'cutandrun', 'methylseq', 'rnaseq_bulk', 'scrnaseq',
          'spatialvi')
# Each template's `compute.mem` at base (a97fa9cd), and the sha256 of the template there: the
# slot filled with that value must give back these bytes, so a Slurm workspace seeds today's file.
BASE_MEM = {'atacseq_bulk': '64G', 'chipseq_bulk': '64G', 'cutandrun': '64G', 'methylseq': '96G',
            'rnaseq_bulk': '64G', 'scrnaseq': '96G', 'spatialvi': '32G'}
BASE_SHA256 = {
    'atacseq_bulk': '29d06905393509b79abd0afe24ea9a076dee5112a582d1118bdb52e2c63428c5',
    'chipseq_bulk': '588acbce90efeedf7625c712aee84a3f79c3ff0b744180140c4fde8b0fda4ae6',
    'cutandrun': '360ea68fbcf67069afcef5a1c138193e7f290a804c957742237c35b591e78b72',
    'methylseq': 'e0979283e7f9675eb122e7a05a3d6ae6cad76953887315a527255017310e1128',
    'rnaseq_bulk': '7d266590e38b40f8a6eafcce99255def8a21303c65daa6e6a2ebc2d3ed17ca5d',
    'scrnaseq': '24cdb806b4642a1f7cfda77135bf721cf1f7ee31da163dcabbb339c7690d8451',
    'spatialvi': '0b0e8d7c1f7107fbab55ecbb7d50e221822afe4a9d804d4483511401ff2dc84c',
}


def quiet(main, argv):
    """A helper's exit code and its JSON, run in-process so the homelab marker stays patched."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, json.loads(out.getvalue())


def name_line(project, name):
    path = project / '_config/executor.yaml'
    text = path.read_text(encoding='utf-8')
    lines = [l for l in text.splitlines(True) if l.startswith('name:')]
    assert len(lines) == 1, lines
    path.write_text(text.replace(lines[0], 'name: %s\n' % name), encoding='utf-8')


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Absent unless a case plants it, so a host carrying the real marker cannot turn the
        # local cases into homelab no-ops.
        self.marker = self.root / 'operator-marker'
        marker = patch.object(ex, 'HOMELAB_MARKER', str(self.marker))
        marker.start(); self.addCleanup(marker.stop)

    def workspace(self, venue_name=None):
        ws = self.root / ('ws-%s' % (venue_name or 'shipped')) / 'gars'
        (ws / 'projects').mkdir(parents=True)
        for name in ('_references', '_templates'):
            shutil.copytree(str(GARS / name), str(ws / name))
        if venue_name is not None:
            descriptor = ws / '_templates/config/executor.yaml'
            text = descriptor.read_text(encoding='utf-8')
            descriptor.write_text(text.replace('\nname: slurm\n', '\nname: %s\n' % venue_name),
                                  encoding='utf-8')
            self.assertIn('\nname: %s\n' % venue_name, descriptor.read_text(encoding='utf-8'))
        return ws

    def create(self, ws, title='seeded', assays=ASSAYS):
        code, out = quiet(s00.main, ['--workspace', str(ws), 'create', '--title', title,
                                     '--assays'] + list(assays))
        self.assertEqual(code, 0, out)
        return ws / 'projects' / out['sanitized_title']

    def lower(self, project, assay, *extra):
        return quiet(configure.main, ['lower', '--project', str(project), '--assay', assay]
                     + list(extra))


class SeedTests(Workspace):
    def test_every_local_seed_is_within_the_ceiling(self):
        self.assertEqual(vp.MEM_CEILING, {'local': 8 * 1024 ** 3})
        self.assertEqual(vp.memory_bytes(vp.ACCEPTED_MEM['local']), vp.MEM_CEILING['local'])
        # check() refuses exactly above the table's ceiling, so the two cannot drift apart.
        fixture = {'data_class': 'public', 'purpose': 'fixture', 'expiry': 'none'}
        self.assertEqual(vp.check(fixture, 'local', 'fixture', vp.MEM_CEILING['local'], []), [])
        self.assertIn('memory rule', str(vp.check(fixture, 'local', 'fixture', vp.MEM_CEILING['local'] + 1, [])))
        for venue in vp.VENUES:
            for aid in ASSAYS:
                with self.subTest(venue=venue, assay=aid):
                    self.assertIsNotNone(vp.seeded_mem(venue, aid))
        for aid in ASSAYS:
            self.assertLessEqual(vp.memory_bytes(vp.seeded_mem('local', aid)), vp.MEM_CEILING['local'])
            for venue in ('slurm', 'homelab'):
                self.assertEqual(vp.seeded_mem(venue, aid), BASE_MEM[aid])

    def test_a_local_workspace_seeds_memory_within_the_local_ceiling(self):
        ws = self.workspace('local')
        project = self.create(ws)
        write_fixture_dataset(project)
        row = wl.dataset_record(project)
        for aid in ASSAYS:
            with self.subTest(assay=aid):
                memory = wl.read_config(project / '_config' / (aid + '.yaml'))['compute.mem']
                self.assertLessEqual(vp.memory_bytes(memory), vp.MEM_CEILING['local'])
                self.assertEqual(vp.check(row, 'local', 'fixture', vp.memory_bytes(memory), []), [])
        # No new seeded file: the guard's stamp is unchanged.
        actual = {str(p.relative_to(project)).replace(os.sep, '/') for p in project.rglob('*')}
        expected = set()
        for entry in guard_hook.CREATE_STAMP:
            expected.update([entry.replace('{assay}', a) for a in ASSAYS] if '{assay}' in entry
                            else [entry])
        self.assertEqual(actual - {'00_data/dataset.tsv'}, expected)

    def test_a_slurm_workspace_seeds_todays_bytes(self):
        for aid in ASSAYS:
            text = (GARS / '_templates/config' / (aid + '.yaml')).read_text(encoding='utf-8')
            restored = text.replace('{{mem}}', BASE_MEM[aid])
            self.assertEqual(hashlib.sha256(restored.encode('utf-8')).hexdigest(), BASE_SHA256[aid], aid)
        ws = self.workspace()
        project = self.create(ws, 'Slurm Bytes')
        scratch = os.environ.get('GARS_SCRATCH', '/gpfs/scratch/%s/gars-work' % os.environ.get('USER', 'USER'))
        for aid in ASSAYS:
            with self.subTest(assay=aid):
                text = (GARS / '_templates/config' / (aid + '.yaml')).read_text(encoding='utf-8')
                expected = (text.replace('{{mem}}', BASE_MEM[aid])
                            .replace('{{project_title}}', 'Slurm_Bytes')
                            .replace('{{work_dir}}', '%s/%s' % (scratch, 'Slurm_Bytes')))
                self.assertEqual((project / '_config' / (aid + '.yaml')).read_text(encoding='utf-8'),
                                 expected)


class LowerTests(Workspace):
    def local_project(self, title='lowered', assays=ASSAYS):
        project = self.create(self.workspace(), title, assays)
        write_fixture_dataset(project)
        name_line(project, 'local')
        self.assertEqual(ex.venue_of(ex.load(project)), 'local')
        return project

    def test_lower_serves_every_assay_and_never_raises(self):
        project = self.local_project()
        for aid in ASSAYS:
            with self.subTest(assay=aid):
                cfg = project / '_config' / (aid + '.yaml')
                before = cfg.read_bytes()
                code, out = self.lower(project, aid, '--dry-run')
                self.assertEqual(code, 0, out)
                self.assertEqual(out['lowered'], {'from': BASE_MEM[aid], 'to': '8G', 'venue': 'local',
                                                  'accepts_up_to': '8G'})
                self.assertEqual(cfg.read_bytes(), before)
                code, out = self.lower(project, aid)
                self.assertEqual(code, 0, out)
                self.assertEqual(wl.read_config(cfg)['compute.mem'], '8G')
                self.assertEqual(out['wrote'], '_config/%s.yaml' % aid)
                self.assertIn('compute.mem lowered', out['history_entry'])
                self.assertIn('compute.mem %s -> 8G' % BASE_MEM[aid], out['history_entry'])
                # Every other byte is kept: putting the old line back gives the pre-run file.
                self.assertEqual(cfg.read_bytes().replace(b'\n  mem: 8G\n',
                                                          ('\n  mem: %s\n' % BASE_MEM[aid]).encode()),
                                 before)
                code, out = self.lower(project, aid)
                self.assertEqual((code, out['lowered']), (0, None))

    def test_lower_leaves_other_venues_and_small_requests(self):
        project = self.local_project('others', ('rnaseq_bulk',))
        cfg = project / '_config/rnaseq_bulk.yaml'
        text = cfg.read_text(encoding='utf-8')
        cfg.write_text(text.replace('\n  mem: 64G\n', '\n  mem: 4G\n'), encoding='utf-8')
        before = cfg.read_bytes()
        self.assertEqual(self.lower(project, 'rnaseq_bulk'), (0, {
            'assay': 'rnaseq_bulk', 'command': 'lower', 'lowered': None, 'ok': True,
            'venue': 'local'}))
        cfg.write_text(text.replace('\n  mem: 64G\n', '\n  mem: 128G\n'), encoding='utf-8')
        name_line(project, 'slurm')
        before = cfg.read_bytes()
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual((code, out['lowered'], out['venue']), (0, None, 'slurm'))
        self.assertEqual(cfg.read_bytes(), before)
        name_line(project, 'local')
        self.marker.touch()
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual((code, out['lowered'], out['venue']), (0, None, 'homelab'))
        self.assertEqual(cfg.read_bytes(), before)

    def test_lower_refuses_without_writing(self):
        project = self.local_project('refusals', ('rnaseq_bulk', 'methylseq'))
        cfg = project / '_config/rnaseq_bulk.yaml'
        original = cfg.read_text(encoding='utf-8')
        descriptor = project / '_config/executor.yaml'
        held = descriptor.read_bytes()
        cases = (
            ('two mem lines', lambda: cfg.write_text(original + 'other:\n  mem: 2G\n', encoding='utf-8'), 1),
            ('a second mem line outside compute', lambda: cfg.write_text(
                original.replace('\naligner:', '\nlimits:\n  mem: 2G\naligner:'), encoding='utf-8'), 1),
            ('descriptor not text', lambda: descriptor.write_bytes(b'name: local\n\xff\xfe\n'), 1),
            ('config absent', lambda: cfg.unlink(), 3),
        )
        for label, plant, expected in cases:
            with self.subTest(case=label):
                cfg.write_text(original, encoding='utf-8')
                descriptor.write_bytes(held)
                plant()
                before = cfg.read_bytes() if cfg.exists() else None
                code, out = self.lower(project, 'rnaseq_bulk')
                self.assertEqual(code, expected, out)
                self.assertFalse(out['ok'])
                self.assertIn('error', out)
                self.assertEqual(cfg.read_bytes() if cfg.exists() else None, before)
                self.assertEqual(sorted(p.name for p in cfg.parent.iterdir() if p.name.endswith('.tmp')), [])
        code, out = self.lower(project, 'not_an_assay')
        self.assertEqual(code, 3, out)
        # A descriptor that is not a file is read as the submit reads it (Slurm): a no-op.
        cfg.write_text(original, encoding='utf-8')
        descriptor.unlink(); descriptor.mkdir()
        before = cfg.read_bytes()
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual((code, out['lowered'], out['venue']), (0, None, ex.venue_of(ex.load(project))))
        self.assertEqual(cfg.read_bytes(), before)
        descriptor.rmdir(); descriptor.write_bytes(held)
        # A `mem:` line that is not compute.mem is not the request the submit compares: with no
        # compute.mem there is nothing to lower, and that other line is never touched.
        cfg.write_text(original.replace('\n  mem: 64G\n', '\n').replace(
            '\naligner:', '\nlimits:\n  mem: 64G\naligner:'), encoding='utf-8')
        before = cfg.read_bytes()
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual((code, out['lowered']), (0, None), out)
        self.assertEqual(cfg.read_bytes(), before)

    def test_lower_takes_no_decision_argument(self):
        project = self.local_project('science', ('rnaseq_bulk',))
        cfg = project / '_config/rnaseq_bulk.yaml'
        text = cfg.read_text(encoding='utf-8')
        formula = [l for l in text.splitlines(True) if l.startswith('  formula:')][0]
        cfg.write_text(text.replace(formula, '  formula: "~ batch + condition"\n'), encoding='utf-8')
        for flag in ('--genome', '--formula', '--contrast', '--mem', '--venue', '--value'):
            with self.subTest(flag=flag), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    configure.main(['lower', '--project', str(project), '--assay', 'rnaseq_bulk',
                                    flag, 'x'])
                self.assertEqual(raised.exception.code, 2)
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual(code, 0, out)
        after = cfg.read_text(encoding='utf-8')
        self.assertIn('\n  formula: "~ batch + condition"\n', after)
        self.assertIn('  contrast: <REQUIRED', after)

    def test_lower_offers_nothing_a_venue_refuses_anyway(self):
        """REVIEW-4d631ae finding 2: on local a non-fixture run is refused whatever its memory,
        so lowering would be futile; `lower` says the dataset needs another venue instead."""
        project = self.create(self.workspace(), 'analysis', ('rnaseq_bulk',))
        write_fixture_dataset(project, purpose='internal')
        name_line(project, 'local')
        cfg = project / '_config/rnaseq_bulk.yaml'
        before = cfg.read_bytes()
        for extra in (('--dry-run',), ()):
            with self.subTest(extra=extra):
                code, out = self.lower(project, 'rnaseq_bulk', *extra)
                self.assertEqual(code, 1, out)
                self.assertIsNone(out['lowered'])
                self.assertIn('venue local purpose rule: fixture only', out['needs_venue'])
                self.assertEqual(cfg.read_bytes(), before)
        (project / '00_data/dataset.tsv').chmod(0o644)
        (project / '00_data/dataset.tsv').unlink()
        code, out = self.lower(project, 'rnaseq_bulk')
        self.assertEqual(code, 1, out)
        self.assertIn('dataset_unclassified', out['needs_venue'])
        self.assertEqual(cfg.read_bytes(), before)

    def test_lower_keeps_line_endings_comment_and_mode(self):
        project = self.local_project('bytes', ('spatialvi',))
        cfg = project / '_config/spatialvi.yaml'
        text = cfg.read_text(encoding='utf-8')
        planted = text.replace('\n  mem: 32G\n', '\n  mem: 32G   # sized for the cluster\n').replace('\n', '\r\n')
        cfg.write_bytes(planted.encode('utf-8'))
        cfg.chmod(0o640)
        code, out = self.lower(project, 'spatialvi')
        self.assertEqual(code, 0, out)
        self.assertEqual(cfg.read_bytes(), planted.replace('  mem: 32G   #', '  mem: 8G   #').encode('utf-8'))
        self.assertEqual(stat.S_IMODE(cfg.stat().st_mode), 0o640)
        self.assertEqual(wl.read_config(cfg)['compute.mem'], '8G')

    def test_a_refused_replace_leaves_the_config(self):
        """Stands in for `lower`'s row in test_r164_writer_recovery (0293)."""
        project = self.local_project('fault', ('cutandrun',))
        cfg = project / '_config/cutandrun.yaml'
        before = cfg.read_bytes()
        with patch('os.replace', side_effect=OSError(28, 'no space left on device')):
            with self.assertRaises(OSError):
                self.lower(project, 'cutandrun')
        self.assertEqual(cfg.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in cfg.parent.iterdir()),
                         sorted(['.gitkeep', 'cutandrun.yaml', 'executor.yaml', 'nextflow.slurm.config']))

    def test_apply_is_unchanged_by_t57(self):
        """`apply` gains no lowering: T9's "Nothing else in the file changes" stays true."""
        project = self.local_project('applied', ('cutandrun',))
        cfg = project / '_config/cutandrun.yaml'
        argv = ['--workspace', str(project.parents[1]), 'apply',
                '--project', str(project), '--assay', 'cutandrun', '--genome', 'R64-1-1']
        with patch.object(configure.os, 'access', return_value=True):
            # R-confirm (0302): every apply writes only what a dry run showed.
            code, out = quiet(configure.main, argv + ['--dry-run'])
            self.assertEqual(code, 0, out)
            code, out = quiet(configure.main, argv)
        self.assertEqual(code, 0, out)
        self.assertEqual(wl.read_config(cfg)['compute.mem'], '64G')
        self.assertFalse([key for key in out if 'lower' in key or 'mem' in key], out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
