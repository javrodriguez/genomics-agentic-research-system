"""S00-class: registration asks no internal, pilot or commercial question (FIXES.md item 1; 0321).

Built as glitch-b5 ruled the design (lanes/gars-t74/S00-CLASS-DESIGN.md, run 11 ruling 7):
1c, `purpose` keeps today's spellings and a new registration writes only `fixture` or `internal`,
shown to people as test and analysis; `pilot_internal`, `pilot_external` and `commercial` are
legacy, read and enforced exactly as before in the rows that carry them, never written anew.

The guard rows need frozen-file hunks that are patch files in lanes/gars-t74/, applied by
glitch-b5 at landing; each such test says which one in its docstring.
"""
import csv
import gzip
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import GARS
from tools import policy
import venue_policy

LEGACY = ('pilot_internal', 'pilot_external', 'commercial')


def fastq_gz(path):
    with gzip.open(str(path), 'wt') as fh:
        fh.write('@r\nACGT\n+\nIIII\n')


class Workspace(unittest.TestCase):
    """A disposable workspace copied from the real one, with one linked rnaseq_bulk project."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='s00-class-'))
        self.addCleanup(self.cleanup)
        self.ws = self.tmp / 'gars'
        self.ws.mkdir()
        for d in ('_system', '_references', '_templates'):
            shutil.copytree(str(GARS / d), str(self.ws / d),
                            ignore=shutil.ignore_patterns('__pycache__'))
        (self.ws / 'projects').mkdir()
        self.project = self.ws / 'projects/p'
        self.dataset = self.project / '00_data/dataset.tsv'

    def cleanup(self):
        for root, _, files in os.walk(str(self.tmp)):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def reg(self, *args):
        done = subprocess.run([sys.executable, str(self.ws / '_system/stage00_register.py')]
                              + list(args), cwd=str(self.ws), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        try:
            return done.returncode, json.loads(done.stdout)
        except ValueError:
            return done.returncode, {'stderr': done.stderr}

    def source(self, name='seq'):
        folder = self.tmp / name
        folder.mkdir()
        for s in ('A1_S1', 'A2_S2'):
            for r in ('R1', 'R2'):
                fastq_gz(folder / ('%s_L001_%s_001.fastq.gz' % (s, r)))
        return folder

    def linked(self, *folders):
        """create, then link each folder's files into the one assay's raw/."""
        code, result = self.reg('create', '--title', 'p', '--assays', 'rnaseq_bulk')
        self.assertEqual(code, 0, result)
        raw = self.project / '00_data/rnaseq_bulk/raw'
        for folder in folders:
            for f in sorted(folder.iterdir()):
                (raw / f.name).symlink_to(f)

    def finalize(self, *extra):
        return self.reg('finalize', '--project', 'projects/p', *extra)

    def legacy_row(self, purpose):
        """The row a person registered before 0321, with a legacy purpose, through the writer."""
        sys.path.insert(0, str(self.ws / '_system'))
        try:
            import stage00_register as s0
            base = {'data_class': 'public', 'purpose': purpose, 'agreement_ref': 'none',
                    'input_data_location': json.dumps(sorted(
                        str(p.resolve()) for p in (self.project / '00_data').glob('*/raw/*')),
                        separators=(',', ':'))}
            s0.write_dataset_record(self.project, s0.dataset_values(self.project, base))
        finally:
            sys.path.remove(str(self.ws / '_system'))
        return self.dataset.read_bytes()


class PurposeTests(Workspace):
    """1c: the purposes a new registration writes, and the legacy rows kept as they are."""

    def test_a_new_registration_refuses_each_legacy_purpose(self):
        self.linked(self.source())
        for purpose in LEGACY:
            with self.subTest(purpose=purpose):
                code, result = self.finalize('--data-class', 'public', '--purpose', purpose,
                                             '--agreement-ref', 'none')
                self.assertEqual(code, 2, result)
                self.assertTrue(any(f.startswith('purpose_legacy:') for f in result['failures']),
                                result)
                self.assertIn('fixture', ' '.join(result['failures']))
                self.assertFalse(self.dataset.exists())
                self.assertFalse((self.project / '00_data/rnaseq_bulk/files.csv').exists())

    def test_a_new_registration_writes_fixture_or_internal(self):
        for purpose in venue_policy.REGISTRABLE_PURPOSES:
            with self.subTest(purpose=purpose):
                self.tearDown_project()
                self.linked(self.source('seq-' + purpose))
                code, result = self.finalize('--data-class', 'public', '--purpose', purpose,
                                             '--agreement-ref', 'none')
                self.assertEqual(code, 0, result)
                with self.dataset.open(newline='') as fh:
                    self.assertEqual(next(csv.DictReader(fh, delimiter='\t'))['purpose'], purpose)

    def tearDown_project(self):
        if self.project.exists():
            for root, _, files in os.walk(str(self.project)):
                for f in files:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
            shutil.rmtree(str(self.project))

    def test_the_registrable_purposes_are_fixture_and_internal(self):
        self.assertEqual(venue_policy.REGISTRABLE_PURPOSES, ('fixture', 'internal'))
        self.assertEqual(venue_policy.LEGACY_PURPOSES, LEGACY)
        self.assertEqual(set(venue_policy.REGISTRABLE_PURPOSES + venue_policy.LEGACY_PURPOSES),
                         set(venue_policy.PURPOSES))

    def test_a_person_re_runs_a_legacy_row_byte_for_byte(self):
        """A person's finalize is not registry-bound: their re-run of a legacy row still runs."""
        for purpose in LEGACY:
            with self.subTest(purpose=purpose):
                self.tearDown_project()
                self.linked(self.source('seq-' + purpose))
                before = self.legacy_row(purpose)
                code, result = self.finalize('--data-class', 'public', '--purpose', purpose,
                                             '--agreement-ref', 'none')
                self.assertEqual(code, 0, result)
                self.assertEqual(self.dataset.read_bytes(), before)

    def test_a_legacy_row_still_refuses_a_new_purpose(self):
        """The classification lock is unchanged: a legacy row is not rewritten to a new value."""
        self.linked(self.source())
        before = self.legacy_row('pilot_internal')
        code, result = self.finalize('--data-class', 'public', '--purpose', 'internal',
                                     '--agreement-ref', 'none')
        self.assertEqual(code, 2, result)
        self.assertIn('dataset_classification_locked: existing dataset row differs',
                      result['failures'])
        self.assertEqual(self.dataset.read_bytes(), before)

    def test_finalize_names_the_data_line(self):
        self.linked(self.source())
        code, result = self.finalize('--data-class', 'public', '--purpose', 'fixture',
                                     '--agreement-ref', 'none')
        self.assertEqual(code, 0, result)
        self.assertEqual(result['data'], 'Data: public, test')

    def test_one_helper_shows_the_purpose_as_people_read_it(self):
        line = venue_policy.data_line
        self.assertEqual(line('public', 'fixture'), 'Data: public, test')
        self.assertEqual(line('public', 'internal'), 'Data: public, analysis')
        self.assertEqual(line('deidentified_under_agreement', 'internal'),
                         'Data: restricted (deidentified_under_agreement), analysis')
        self.assertEqual(line('public', 'pilot_internal'), 'Data: public, legacy pilot_internal')

    def test_the_agent_cannot_register_a_legacy_purpose(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S00-class-R1-registry.patch (hunk R1).

        Under R1 the agent's finalize takes only fixture or internal, so an agent's re-run of a
        legacy row is refused too: that re-run is the person's own (run 11 ruling 6)."""
        argv = ['python3', '_system/stage00_register.py', 'finalize', '--project', 'projects/p',
                '--data-class', 'public', '--agreement-ref', 'none', '--purpose']
        for purpose in venue_policy.REGISTRABLE_PURPOSES:
            tool, args = policy.parse_argv(argv + [purpose], root=GARS)
            policy.validate_args(tool, args, root=GARS)
            self.assertEqual(args['purpose'], purpose)
        for purpose in LEGACY:
            with self.subTest(purpose=purpose):
                tool, args = policy.parse_argv(argv + [purpose], root=GARS)
                with self.assertRaises(policy.Refusal) as caught:
                    policy.validate_args(tool, args, root=GARS)
                self.assertEqual(caught.exception.field, 'args.purpose')


if __name__ == '__main__':
    unittest.main()
