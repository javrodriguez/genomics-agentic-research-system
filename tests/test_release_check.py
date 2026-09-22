"""Regeneration, tamper and release-age controls; fixture values are never evidence."""
import datetime
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('row11_release', str(REPO / 'scripts/release_check.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class ReleaseCheckTests(unittest.TestCase):
    def test_regeneration_and_hand_edit(self):
        with tempfile.TemporaryDirectory(prefix='row11-release-') as temp:
            root = Path(temp)
            (root / release.SPEC).parent.mkdir(parents=True)
            shutil.copyfile(str(REPO / release.SPEC), str(root / release.SPEC))
            saved = release.REPO
            release.REPO = root
            try:
                self.assertEqual(release.main([]), 0)
                before = (root / release.OUTPUT).read_bytes()
                self.assertEqual(release.main([]), 0)
                self.assertEqual(before, (root / release.OUTPUT).read_bytes())
                self.assertEqual(release.main(['--check']), 0)
                (root / release.OUTPUT).write_bytes(before.replace(b'| unmeasured |', b'| 100% |', 1))
                self.assertEqual(release.main(['--check']), 1)
                self.assertEqual(release.main(['--tag']), 1)
                print('red-on-fault: hand-typed DoD cell -> check and tag REFUSED')
                self.assertEqual(release.main([]), 0)
                self.assertEqual(before, (root / release.OUTPUT).read_bytes())
                self.assertEqual(release.main(['--tag']), 1)
            finally:
                release.REPO = saved

    def test_stale_release_row_and_threshold(self):
        today = datetime.date(2026, 9, 22)
        fresh = ('fixture result', today, True)
        rows = {'fixture': fresh}
        self.assertEqual(release.release_failures(rows, today), [])
        rows['fixture'] = ('fixture result', today - datetime.timedelta(days=14), True)
        self.assertEqual(release.release_failures(rows, today), [])
        rows['fixture'] = ('fixture result', today - datetime.timedelta(days=15), True)
        self.assertIn('fixture: older than 14 days', release.release_failures(rows, today))
        with tempfile.TemporaryDirectory(prefix='row11-stale-') as temp:
            root = Path(temp)
            output = root / release.OUTPUT
            output.parent.mkdir(parents=True)
            clauses = [('fixture', 'fixture test', 'fixture threshold')]
            output.write_text(release.render(clauses, rows))
            with mock.patch.object(release, 'REPO', root), \
                    mock.patch.object(release, 'clauses', return_value=clauses), \
                    mock.patch.object(release, 'measurements', return_value=rows):
                # Use a date guaranteed stale against the actual UTC clock, too.
                rows['fixture'] = ('fixture result', datetime.date(2000, 1, 1), True)
                self.assertEqual(release.main(['--tag']), 1)
        print('red-on-fault: stale release row -> release tag REFUSED')
        rows['fixture'] = ('fixture below threshold', today, False)
        self.assertTrue(release.release_failures(rows, today))
        rows['fixture'] = ('fixture result', today + datetime.timedelta(days=1), True)
        self.assertTrue(release.release_failures(rows, today))

    def test_existing_restore_output_format(self):
        with tempfile.TemporaryDirectory(prefix='row11-output-') as temp:
            root = Path(temp)
            path = root / release.RESTORE
            path.parent.mkdir(parents=True)
            path.write_text('# Existing output format\n2026-09-21T12:00:00Z, 2.000000, 3.000000, PASS\n')
            value, when, meets = release.restore_measurement(root)
            self.assertIn('RPO 2.000000 h; RTO 3.000000 min; PASS', value)
            self.assertEqual(when, datetime.date(2026, 9, 21))
            self.assertFalse(meets)  # This format cannot prove venue/canary provenance.
            path.write_text(path.read_text() + '2026-09-22T12:00:00Z, 25, 61, FAIL\n')
            self.assertIn('FAIL', release.restore_measurement(root)[0])
            path.write_text('2026-09-22T12:00:00Z, NaN, 1, PASS\n')
            with self.assertRaises(ValueError):
                release.restore_measurement(root)

    def test_repository_table_regenerated(self):
        rows = release.clauses(REPO)
        self.assertEqual(len(rows), 13)
        self.assertEqual((REPO / release.OUTPUT).read_text(),
                         release.render(rows, release.measurements(REPO, rows)))
        print('DoD cells regenerated: 13/13')


if __name__ == '__main__':
    unittest.main(verbosity=2)
