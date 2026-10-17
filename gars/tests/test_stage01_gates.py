"""Stage 01's two human gates bind to the check the user saw (FIXES.md item S01-yes).

`--confirm-exclusions` clears T7 and `--force` clears T5. Each is honoured only against the record
the read-only `--check` wrote: the same excluded samples, the same existing files byte for byte.
A switch with no matching record is refused (exit 2), so an agent cannot clear a gate the user
never saw, nor one whose subject changed after they saw it.
"""
import contextlib
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

import support  # noqa: F401  -- puts gars/_system on the path, honours TMPDIR
import guard_hook
import stage01_samplesheet as s01

SAMPLES = ('K1', 'K2', 'K3', 'K4', 'K5', 'K6')
WRITTEN = ['rnaseq_bulk_design.csv', 'rnaseq_bulk_design_check.json',
           'rnaseq_bulk_samplesheet.csv']


class Stage01GateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-s01-gates-')
        self.root = Path(self._tmp.name)
        self.data = self.root / '00_data/rnaseq_bulk'
        (self.data / 'raw').mkdir(parents=True)
        (self.root / '_config').mkdir()
        (self.root / '_config/rnaseq_bulk.yaml').write_text(
            'strandedness: reverse\nunit_of_replication: sample\n'
            'reference_release: synthetic-v1\n')
        with (self.data / 'files.csv').open('w', newline='') as fh:
            writer = csv.writer(fh)
            writer.writerow(['sample_id', 'lane', 'fastq_1', 'fastq_2'])
            for sample in SAMPLES:
                raw = self.data / 'raw' / ('%s_R1.fastq' % sample)
                raw.write_text('@synthetic\nACGT\n+\nIIII\n')
                writer.writerow([sample, '1', str(raw.relative_to(self.root)), ''])
        self.design(SAMPLES)

    def tearDown(self):
        self._tmp.cleanup()

    def design(self, samples, swapped=False):
        """samples.csv with a row for each of `samples`; any other linked sample is excluded.
        `swapped` gives every sample the other condition: a different design, the same ids."""
        rows = [['sample_id', 'condition', 'group', 'replicate']]
        for i, sample in enumerate(samples):
            arm = 'A' if (i % 2 == 0) != swapped else 'B'
            rows.append([sample, arm, 'G' + arm, str(i // 2 + 1)])
        with (self.data / 'samples.csv').open('w', newline='') as fh:
            csv.writer(fh).writerows(rows)

    def stage01(self, *flags):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = s01.main(['--project', str(self.root)] + list(flags))
        return code, json.loads(out.getvalue())

    def sheets(self):
        return sorted(p.name for p in (self.root / '01_samplesheets').iterdir())

    def record(self):
        """The one check record a clean --check left, wherever the stage keeps it."""
        found = [p for p in self.root.rglob(s01.CHECK_RECORD)]
        self.assertEqual(len(found), 1, found)
        return found[0]

    def written_once(self):
        code, res = self.stage01()
        self.assertEqual(code, 0, res)

    def assertRefused(self, code, res, word):
        self.assertEqual(code, s01.EXIT_NEEDS_CONFIRM, res)
        self.assertFalse(res['ok'])
        self.assertTrue(any(word in why for why in res.get('blocked', [])), res)
        self.assertEqual(res['wrote'], [])

    # -- the overwrite gate (T5, --force) ------------------------------------------------------

    def test_force_with_no_prior_check_is_refused(self):
        self.written_once()
        before = {n: (self.root / '01_samplesheets' / n).read_bytes() for n in WRITTEN}
        code, res = self.stage01('--force')
        self.assertRefused(code, res, '--check')
        self.assertEqual({n: (self.root / '01_samplesheets' / n).read_bytes() for n in WRITTEN},
                         before, 'a refused overwrite must leave every file as it was')

    def test_force_after_the_files_changed_since_the_check_is_refused(self):
        self.written_once()
        code, res = self.stage01('--check')
        self.assertEqual(code, 0, res)
        sheet = self.root / '01_samplesheets' / 'rnaseq_bulk_samplesheet.csv'
        sheet.write_text(sheet.read_text() + '# edited after the check\n')
        code, res = self.stage01('--force')
        self.assertRefused(code, res, 'rnaseq_bulk_samplesheet.csv')

    def test_force_after_a_matching_check_writes(self):
        self.written_once()
        code, res = self.stage01('--check')
        self.assertEqual((code, sorted(res['existing_outputs'])), (0, WRITTEN), res)
        code, res = self.stage01('--force')
        self.assertEqual(code, 0, res)

    def test_force_after_an_identical_forced_rewrite_and_a_design_change_is_refused(self):
        # A forced rewrite reproduces the bytes the check hashed; the condition swap after it
        # was never shown in a T5, so the check the user saw must not clear it (review finding 1).
        self.written_once()
        self.assertEqual(self.stage01('--check')[0], 0)
        code, res = self.stage01('--force')
        self.assertEqual(code, 0, res)
        self.design(SAMPLES, swapped=True)
        code, res = self.stage01('--force')
        self.assertRefused(code, res, '--check')

    # -- the exclusions gate (T7, --confirm-exclusions) ----------------------------------------

    def test_confirm_exclusions_with_no_prior_check_is_refused(self):
        self.design(SAMPLES[:4])
        code, res = self.stage01('--confirm-exclusions')
        self.assertRefused(code, res, '--check')

    def test_confirm_exclusions_after_the_design_changed_is_refused(self):
        self.design(SAMPLES[:5])
        code, res = self.stage01('--check')
        self.assertEqual((code, res['exclusions_pending']), (0, True), res)
        self.design(SAMPLES[:4])        # one more sample dropped after the user saw T7
        code, res = self.stage01('--confirm-exclusions')
        self.assertRefused(code, res, 'K5')

    def test_confirm_exclusions_after_a_matching_check_writes(self):
        self.design(SAMPLES[:4])
        code, res = self.stage01('--check')
        self.assertEqual((code, res['exclusions_pending']), (0, True), res)
        code, res = self.stage01('--confirm-exclusions')
        self.assertEqual(code, 0, res)

    def test_both_switches_after_an_identical_rewrite_and_a_design_change_are_refused(self):
        # Review finding 1, second case: the same excluded ids throughout, conditions swapped.
        self.design(SAMPLES[:4])
        self.assertEqual(self.stage01('--check')[0], 0)
        self.assertEqual(self.stage01('--confirm-exclusions')[0], 0)
        self.assertEqual(self.stage01('--check')[0], 0)
        code, res = self.stage01('--confirm-exclusions', '--force')
        self.assertEqual(code, 0, res)
        self.design(SAMPLES[:4], swapped=True)
        code, res = self.stage01('--confirm-exclusions', '--force')
        self.assertRefused(code, res, '--check')

    # -- the record ------------------------------------------------------------------------------

    def test_the_guard_refuses_a_write_to_the_check_record(self):
        # Review finding 2: the record lives where the guard already refuses the agent's Write.
        self.written_once()
        self.assertEqual(self.stage01('--check')[0], 0)
        rel = Path('projects/demo') / self.record().relative_to(self.root)
        with self.assertRaises(SystemExit) as refused, \
                contextlib.redirect_stderr(io.StringIO()):
            guard_hook.check_write_tool({'file_path': str(rel)}, str(support.GARS),
                                        str(support.GARS))
        self.assertEqual(refused.exception.code, 2, rel)

    def test_a_record_of_the_wrong_shape_is_refused_not_a_traceback(self):
        # Review NIT 2: a hand-made record is refused with exit 2, never exit 1 (read as T3).
        self.written_once()
        self.assertEqual(self.stage01('--check')[0], 0)
        record = self.record()
        for body, flags in ((({'existing': 'x', 'exclusions': {}}), ('--force',)),
                            (({'existing': {}, 'exclusions': ['K5']}), ('--force',)),
                            (({'existing': {'a': 1}, 'exclusions': {}}), ('--force',))):
            with self.subTest(body=body):
                record.write_text(json.dumps(body))
                code, res = self.stage01(*flags)
                self.assertRefused(code, res, '--check')
        self.design(SAMPLES[:4])
        record.write_text(json.dumps({'existing': {}, 'exclusions': ['K5']}))
        code, res = self.stage01('--confirm-exclusions', '--force')
        self.assertRefused(code, res, '--check')

    # -- what stays as it was --------------------------------------------------------------------

    def test_a_switch_that_clears_no_gate_needs_no_record(self):
        code, res = self.stage01('--confirm-exclusions', '--force')
        self.assertEqual(code, 0, res)

    def test_check_then_write_leaves_only_the_three_artifacts(self):
        # The three artifacts and, by glitch-b5's ruling of 17 Oct (review question 2), the
        # stage's own check record beside them; the artifacts' bytes are the unchanged writer's.
        self.design(SAMPLES[:4])
        self.assertEqual(self.stage01('--check')[0], 0)
        self.assertEqual(self.stage01('--confirm-exclusions')[0], 0)
        self.assertEqual(self.sheets(), sorted(WRITTEN + [s01.CHECK_RECORD]))
        written = {n: (self.root / '01_samplesheets' / n).read_bytes() for n in WRITTEN}
        res = s01.validate_assay(self.root, 'rnaseq_bulk')
        for name in WRITTEN:
            (self.root / '01_samplesheets' / name).unlink()
        s01.write_assay(self.root, 'rnaseq_bulk', res)
        self.assertEqual({n: (self.root / '01_samplesheets' / n).read_bytes() for n in WRITTEN},
                         written, 'the gates must not change what the writer writes')


if __name__ == '__main__':
    unittest.main()
