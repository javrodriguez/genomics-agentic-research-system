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


class DeclarationTests(Workspace):
    """2a: the person's own data_sources.tsv settles test or analysis, else T4c asks once."""

    def declare(self, *rows, header=('source', 'data_class', 'declared_by', 'use')):
        text = '\t'.join(header) + '\n' + ''.join('\t'.join(r) + '\n' for r in rows)
        (self.ws / 'data_sources.tsv').write_text(text)

    def purpose(self):
        with self.dataset.open(newline='') as fh:
            return next(csv.DictReader(fh, delimiter='\t'))['purpose']

    def unsettled(self, *extra):
        code, result = self.finalize('--data-class', 'public', '--agreement-ref', 'none', *extra)
        self.assertEqual(code, 2, result)
        self.assertEqual(result.get('template'), 'T4c', result)
        self.assertTrue(any(f.startswith('purpose_required:') for f in result['failures']), result)
        self.assertFalse(self.dataset.exists())
        self.assertFalse((self.project / '00_data/rnaseq_bulk/files.csv').exists())

    def test_a_declared_use_settles_the_purpose(self):
        for use, purpose in (('test', 'fixture'), ('analysis', 'internal')):
            with self.subTest(use=use):
                PurposeTests.tearDown_project(self)
                seq = self.source('seq-' + use)
                self.declare((str(seq), 'public', 'lane fixture', use))
                self.linked(seq)
                code, result = self.finalize('--data-class', 'public', '--agreement-ref', 'none')
                self.assertEqual(code, 0, result)
                self.assertEqual(self.purpose(), purpose)
                self.assertEqual(result['data'], 'Data: public, ' + use)

    def test_mixed_uses_are_unsettled(self):
        one, two = self.source('one'), self.source('two')
        for f in two.iterdir():
            f.rename(two / f.name.replace('A', 'B'))
        self.declare((str(one), 'public', 'lane', 'test'), (str(two), 'public', 'lane', 'analysis'))
        self.linked(one, two)
        self.unsettled()

    def test_an_empty_use_is_unsettled(self):
        seq = self.source()
        self.declare((str(seq), 'public', 'lane', ''))
        self.linked(seq)
        self.unsettled()

    def test_a_three_cell_declaration_is_unsettled(self):
        seq = self.source()
        self.declare((str(seq), 'public', 'lane'), header=('source', 'data_class', 'declared_by'))
        self.linked(seq)
        self.unsettled()

    def test_an_entry_outside_every_declared_source_is_unsettled(self):
        seq, other = self.source(), self.source('other')
        self.declare((str(other), 'public', 'lane', 'test'))
        self.linked(seq)
        self.unsettled()

    def test_a_use_outside_the_two_words_settles_nothing(self):
        seq = self.source()
        for word in ('Test', 'fixture', ' test', 'internal'):
            with self.subTest(word=word):
                self.declare((str(seq), 'public', 'lane', word))
                if not self.project.exists():
                    self.linked(seq)
                self.unsettled()

    def test_no_declaration_is_unsettled(self):
        self.linked(self.source())
        self.unsettled()

    def test_a_purpose_that_disagrees_with_the_declaration_is_refused(self):
        seq = self.source()
        self.declare((str(seq), 'public', 'lane', 'test'))
        self.linked(seq)
        code, result = self.finalize('--data-class', 'public', '--agreement-ref', 'none',
                                     '--purpose', 'internal')
        self.assertEqual(code, 2, result)
        self.assertTrue(any(f.startswith('purpose_disagrees:') for f in result['failures']),
                        result)
        self.assertFalse(self.dataset.exists())
        code, result = self.finalize('--data-class', 'public', '--agreement-ref', 'none',
                                     '--purpose', 'fixture')
        self.assertEqual(code, 0, result)
        self.assertEqual(self.purpose(), 'fixture')

    def test_the_reply_to_t4c_is_the_purpose(self):
        """Unsettled, the person's word goes in as --purpose: test is fixture, analysis internal."""
        self.linked(self.source())
        self.unsettled()
        code, result = self.finalize('--data-class', 'public', '--agreement-ref', 'none',
                                     '--purpose', 'internal')
        self.assertEqual(code, 0, result)
        self.assertEqual(self.purpose(), 'internal')

    def test_the_guard_reads_a_four_column_declaration(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S00-class-G1-guard.patch (hunk G1).

        A fourth column `use` is optional; its cell is test, analysis or empty, and a row of
        three cells stays valid. Anything else in it declares nothing."""
        import guard_hook
        root = self.ws
        seq, other = self.source(), self.source('other')
        cases = [
            (('source', 'data_class', 'declared_by', 'use'),
             [(str(seq), 'public', 'lane', 'test'), (str(other), 'public', 'lane', '')], True),
            (('source', 'data_class', 'declared_by', 'use'),
             [(str(seq), 'public', 'lane', 'analysis'), (str(other), 'public', 'lane')], True),
            (('source', 'data_class', 'declared_by'), [(str(seq), 'public', 'lane')], True),
            (('source', 'data_class', 'declared_by', 'use'), [(str(seq), 'public', 'lane', 'Test')],
             False),
            (('source', 'data_class', 'declared_by', 'use'),
             [(str(seq), 'public', 'lane', 'test', 'x')], False),
            (('source', 'data_class', 'declared_by', 'purpose'),
             [(str(seq), 'public', 'lane', 'test')], False),
            (('source', 'data_class', 'declared_by'), [(str(seq), 'public', 'lane', 'test')], False),
        ]
        for header, rows, valid in cases:
            with self.subTest(header=header, rows=rows):
                self.declare(*rows, header=header)
                sources, failed = guard_hook.declared_sources(str(root))
                if valid:
                    self.assertIsNone(failed)
                    self.assertIn(os.path.realpath(str(seq)), sources)
                else:
                    self.assertEqual(sources, ())
                    self.assertIsNotNone(failed)


class DeclarationContractTests(unittest.TestCase):
    """2a in the stage 00 contract: finalize carries no purpose; T4c asks once when unsettled."""

    def setUp(self):
        text = (GARS / '00_initialize_project/CONTEXT.md').read_text()
        self.process = text.split('## Process', 1)[1].split('## Response Format', 1)[0]
        self.formats = text.split('## Response Format', 1)[1].split('## OUTPUT', 1)[0]

    def test_t4c_names_the_two_words(self):
        self.assertIn('**T4c', self.formats)
        t4c = self.formats.split('**T4c', 1)[1].split('**T', 1)[0]
        self.assertIn('Reply `test` or `analysis`', t4c)
        for word in ('internal', 'pilot', 'commercial'):
            self.assertNotIn(word, t4c)

    def test_finalize_carries_no_purpose_until_t4c(self):
        lines = [' '.join(l.split()) for l in self.process.splitlines()
                 if 'stage00_register.py finalize' in l]
        self.assertTrue(lines)
        self.assertNotIn('--purpose <purpose>', ' '.join(lines))
        flat = ' '.join(self.process.split())
        self.assertIn('`template: T4c`', flat)
        self.assertIn('`test` → re-run it with `--purpose fixture`', flat)
        self.assertIn('`analysis` → with `--purpose internal`', flat)
        self.assertIn('any other reply → send T4c again', flat)


if __name__ == '__main__':
    unittest.main()
