"""Regeneration, tamper and release-age controls; fixture values are never evidence."""
import datetime
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
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

    def test_terminal_restore_correction_same_timestamp(self):
        with tempfile.TemporaryDirectory(prefix='row11-terminal-') as temp:
            root = Path(temp)
            for name in (release.SPEC, 'scripts/release_check.py'):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(REPO / name), str(root / name))
            path = root / release.RESTORE
            path.parent.mkdir(parents=True)
            path.write_text('2026-09-22T12:00:00Z, 2.000000, 3.000000, PASS\n'
                            '2026-09-22T12:00:00Z, 2.000000, 3.100000, FAIL\n'
                            '2026-09-21T12:00:00Z, 1.000000, 2.000000, PASS\n')
            command = [sys.executable, str(root / 'scripts/release_check.py')]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            output = (root / release.OUTPUT).read_text()
            self.assertIn('RPO 2.000000 h; RTO 3.100000 min; FAIL; venue/canary unmeasured', output)
            self.assertNotIn('3.000000 min; PASS', output)
            value, when, meets = release.restore_measurement(root)
            self.assertEqual(when, datetime.date(2026, 9, 22))
            self.assertFalse(meets)
            result = subprocess.run(command + ['--check'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(command + ['--tag'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 1)
            self.assertIn(b'restore drill: unmeasured', result.stdout)
            self.assertIn(b'restore drill: threshold not established', result.stdout)
            print('red-on-fault: same-timestamp terminal FAIL retained by release CLI')

    def test_repository_table_regenerated(self):
        rows = release.clauses(REPO)
        self.assertEqual(len(rows), 13)
        self.assertEqual((REPO / release.OUTPUT).read_text(),
                         release.render(rows, release.measurements(REPO, rows)))
        print('DoD cells regenerated: 13/13')

    DECISIONS = 'docs/decisions'  # literal, so the tests also run against the parent reader
    # Row 5's committed evidence shape (docs/ops/restore-log.md), byte-copied.
    RESULT_TABLE = ('| Date | RPO_h | RTO_min | Result |\n'
                    '|---|---|---|---|\n'
                    '| 2026-09-22T16:55:13Z | 13.167400 | 0.284136 | PASS |\n')
    PROVENANCE = '| Date | Venue | Source | Target | Data | Seal | Record |\n|---|---|---|---|---|---|---|\n'
    QUALIFYING = ('2026-09-22T16:55:13Z; RPO 13.167400 h; RTO 0.284136 min; PASS; Node 1 from the '
                  'scheduled off-machine copy; target recovery-db; synthetic data; seal '
                  'independent_context (0054); public seal pending (external_human_seal)')

    def restore_root(self, temp, log, records=()):
        root = Path(temp)
        path = root / release.RESTORE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(log.encode('utf-8'))
        (root / self.DECISIONS).mkdir(parents=True, exist_ok=True)
        for name, text in records:
            (root / self.DECISIONS / name).write_text(text)
        return root

    def test_restore_table_rows_read(self):
        with tempfile.TemporaryDirectory(prefix='rc-table-') as temp:
            root = self.restore_root(temp, '# Restore evidence\n\n' + self.RESULT_TABLE)
            value, when, meets = release.restore_measurement(root)
        self.assertEqual(value, '2026-09-22T16:55:13Z; RPO 13.167400 h; RTO 0.284136 min; PASS; '
                                'venue/canary unmeasured')
        self.assertEqual(when, datetime.date(2026, 9, 22))
        self.assertFalse(meets)
        print('red-on-fault: a result-table row skipped -> cell reads unmeasured')

    def test_repository_restore_cell(self):
        self.assertEqual(release.restore_measurement(REPO),
                         (self.QUALIFYING, datetime.date(2026, 9, 22), True))
        with tempfile.TemporaryDirectory(prefix='rc-repo-') as temp:
            root = Path(temp)
            shutil.copytree(str(REPO / self.DECISIONS), str(root / self.DECISIONS))
            (root / release.RESTORE).parent.mkdir(parents=True)
            log = (REPO / release.RESTORE).read_text()
            self.assertEqual(log.count('| 13.167400 |'), 1)
            (root / release.RESTORE).write_text(log.replace('| 13.167400 |', '| 24.000001 |'))
            value, when, meets = release.restore_measurement(root)
        self.assertNotEqual(value, self.QUALIFYING.replace('13.167400', '24.000001'))
        self.assertIn('not qualifying', value)
        self.assertFalse(meets)
        print('red-on-fault: repository drill RPO 24.000001 -> not qualifying')

    def test_restore_table_strict(self):
        head = '| Date | RPO_h | RTO_min | Result |\n|---|---|---|---|\n'
        faults = [
            ('five cells', head + '| 2026-09-22T16:55:13Z | 1 | 1 | PASS | x |\n'),
            ('NaN', head + '| 2026-09-22T16:55:13Z | NaN | 1 | PASS |\n'),
            ('bad stamp', head + '| 2026-09-22 16:55:13 | 1 | 1 | PASS |\n'),
            ('outside a block', '# log\n\n| 2026-09-22T16:55:13Z | 1 | 1 | PASS |\n'),
        ]
        for label, log in faults:
            with self.subTest(label), tempfile.TemporaryDirectory(prefix='rc-strict-') as temp:
                root = self.restore_root(temp, log)
                with self.assertRaises(ValueError):
                    release.restore_measurement(root)
                print('red-on-fault: %s restore table row -> ValueError' % label)
        with tempfile.TemporaryDirectory(prefix='rc-strict-') as temp:
            root = self.restore_root(temp, '# log\n\n' + head + '\nprose\n')
            self.assertEqual(release.restore_measurement(root), ('unmeasured', None, False))
        print('red-on-fault: header-only restore table -> unmeasured')

    def test_restore_mixed_shapes(self):
        head = '| Date | RPO_h | RTO_min | Result |\n|---|---|---|---|\n'
        latest = ('2026-09-20T00:00:00Z, 1.000000, 1.000000, PASS\n' + head +
                  '| 2026-09-21T00:00:00Z | 2.000000 | 2.000000 | PASS |\n\n'
                  '2026-09-19T00:00:00Z, 3.000000, 3.000000, PASS\n')
        table_last = ('2026-09-21T00:00:00Z, 2.000000, 2.000000, PASS\n\n' + head +
                      '| 2026-09-21T00:00:00Z | 2.000000 | 2.500000 | FAIL |\n')
        csv_last = (head + '| 2026-09-21T00:00:00Z | 2.000000 | 2.000000 | PASS |\n\n'
                    '2026-09-21T00:00:00Z, 2.000000, 2.500000, FAIL\n')
        with tempfile.TemporaryDirectory(prefix='rc-mixed-') as temp:
            value = release.restore_measurement(self.restore_root(temp, latest))[0]
            self.assertTrue(value.startswith('2026-09-21T00:00:00Z; RPO 2.000000 h; RTO 2.000000 min; PASS'))
            print('red-on-fault: latest stamp across CSV and table -> the table row')
            for label, log in (('table', table_last), ('CSV', csv_last)):
                value = release.restore_measurement(self.restore_root(temp, log))[0]
                self.assertIn('RTO 2.500000 min; FAIL', value)
                print('red-on-fault: terminal %s FAIL at a tied stamp -> FAIL wins' % label)

    def test_restore_crlf(self):
        log = ('# Restore evidence\n\n' + self.RESULT_TABLE + '\n2026-09-21T00:00:00Z, 1, 1, PASS\n\n' +
               self.PROVENANCE +
               '| 2026-09-22T16:55:13Z | node1 | scheduled-offmachine | recovery-db | synthetic '
               '| independent_context | 0054 |\n')
        record = ('0054-fixture.md', '---\nstatus: standing\ntouches:\n  - docs/ops/restore-log.md\n---\n'
                  '`2026-09-22T16:55:13Z, 13.167400, 0.284136, PASS`; independent_context\n')
        with tempfile.TemporaryDirectory(prefix='rc-crlf-') as temp:
            lf = release.restore_measurement(self.restore_root(temp, log, [record]))
        with tempfile.TemporaryDirectory(prefix='rc-crlf-') as temp:
            crlf = release.restore_measurement(self.restore_root(temp, log.replace('\n', '\r\n'),
                                                                 [record]))
        self.assertEqual(lf, (self.QUALIFYING, datetime.date(2026, 9, 22), True))
        self.assertEqual(crlf, lf)
        print('red-on-fault: CRLF restore log -> parsed as the LF one')

    def test_restore_qualification_grid(self):
        stamp = '2026-09-20T10:00:00Z'
        # result rows (status, RPO, RTO) at the stamp; provenance rows (stamp, venue, source,
        # target, data, seal, record); record file (number, status, touches the log,
        # body has the CSV evidence line, body has the seal token); expected
        # (meets, text contains, text lacks) or ValueError.
        grid = [
            ('0054-like record', [('PASS', '13.17', '0.28')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (True, 'seal independent_context', None)),
            ('inclusive bounds, external seal', [('PASS', '24', '60')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'external_human_seal', '0054')],
             ('0054', 'standing', True, True, True), (True, 'seal external_human_seal', 'public seal pending')),
            ('RPO 24.000001', [('PASS', '24.000001', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (False, 'not qualifying', None)),
            ('RTO 60.000001', [('PASS', '1', '60.000001')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (False, 'not qualifying', None)),
            ('no provenance row', [('PASS', '1', '1')], [],
             None, (False, 'venue/canary unmeasured', None)),
            ('seal none', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'none', '0054')],
             ('0054', 'standing', True, True, True), (False, 'not qualifying', None)),
            ('venue laptop', [('PASS', '1', '1')],
             [(stamp, 'laptop', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), ValueError),
            ('record 9999 absent', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '9999')],
             ('0054', 'standing', True, True, True), (False, 'not qualifying', None)),
            ('record superseded', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'superseded', True, True, True), (False, 'not qualifying', None)),
            ('record touches lack the log', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', False, True, True), (False, 'not qualifying', None)),
            ('record body lacks the CSV line', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, False, True), (False, 'not qualifying', None)),
            ('record body lacks the seal', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, False), (False, 'not qualifying', None)),
            ('real data', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'real', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (True, 'real data', None)),
            ('data mock', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'mock', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), ValueError),
            ('FAIL', [('FAIL', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (False, 'FAIL', None)),
            ('PASS then FAIL, same stamp', [('PASS', '1', '1'), ('FAIL', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), (False, 'FAIL', None)),
            ('provenance for an absent stamp', [('PASS', '1', '1')],
             [('2026-09-19T10:00:00Z', 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), ValueError),
            ('two provenance rows, one stamp', [('PASS', '1', '1')],
             [(stamp, 'node1', 'scheduled-offmachine', 'recovery-db', 'synthetic', 'independent_context', '0054'),
              (stamp, 'node1', 'scheduled-offmachine', 'primary', 'synthetic', 'independent_context', '0054')],
             ('0054', 'standing', True, True, True), ValueError),
        ]
        for label, results, provenance, record, expected in grid:
            log = '# log\n\n| Date | RPO_h | RTO_min | Result |\n|---|---|---|---|\n'
            log += ''.join('| %s | %s | %s | %s |\n' % (stamp, rpo, rto, status)
                           for status, rpo, rto in results)
            log += '\n' + self.PROVENANCE + ''.join('| %s |\n' % ' | '.join(row) for row in provenance)
            records = []
            if record is not None:
                number, status, touches, evidence, seal = record
                status_row, rpo, rto = results[-1]
                text = '---\ndate: 2026-09-20\nstatus: %s\nkind: decision\ntouches:\n' % status
                text += '  - docs/ops/%s\n---\n# Fixture drill\n\n' % ('restore-log.md' if touches else 'HARDWARE.md')
                if evidence:
                    text += '- **Drill:** `%s, %s, %s, %s`.\n' % (stamp, rpo, rto, status_row)
                if seal:
                    text += 'The seal class is `%s`.\n' % provenance[0][5]
                records.append((number + '-fixture.md', text))
            with self.subTest(label), tempfile.TemporaryDirectory(prefix='rc-grid-') as temp:
                root = self.restore_root(temp, log, records)
                if expected is ValueError:
                    with self.assertRaises(ValueError):
                        release.restore_measurement(root)
                    print('red-on-fault: %s -> ValueError' % label)
                    continue
                meets, contains, lacks = expected
                value, when, got = release.restore_measurement(root)
                self.assertEqual((got, contains in value, lacks is not None and lacks in value),
                                 (meets, True, False), value)
                print('red-on-fault: %s -> meets %s, %r' % (label, meets, contains))

    def test_restore_qualified_tag_path(self):
        values = {'restore drill': release.restore_measurement(REPO)}
        self.assertEqual(values['restore drill'][1], datetime.date(2026, 9, 22))
        self.assertEqual(release.release_failures(values, datetime.date(2026, 9, 27)), [])
        self.assertEqual(release.release_failures(values, datetime.date(2026, 10, 7)),
                         ['restore drill: older than 14 days'])
        print('red-on-fault: qualified drill 15 days old -> older than 14 days at tag')

    def test_restore_qualified_cli(self):
        with tempfile.TemporaryDirectory(prefix='rc-cli-') as temp:
            root = Path(temp)
            for name in (release.SPEC, 'scripts/release_check.py', release.RESTORE):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(str(REPO / name), str(root / name))
            shutil.copytree(str(REPO / self.DECISIONS), str(root / self.DECISIONS))
            command = [sys.executable, str(root / 'scripts/release_check.py')]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 0, result.stderr)
            before = (root / release.OUTPUT).read_bytes()
            self.assertIn(('| %s |' % self.QUALIFYING).encode('utf-8'), before)
            result = subprocess.run(command + ['--check'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            self.assertEqual((result.returncode, result.stdout),
                             (0, b'DoD cells verified: 13/13 byte-stable\n'), result.stderr)
            self.assertEqual(before, (root / release.OUTPUT).read_bytes())
            result = subprocess.run(command + ['--tag'], stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn(b'restore drill: unmeasured', result.stdout)
            self.assertNotIn(b'restore drill: threshold not established', result.stdout)
            self.assertIn(b'design-defect catch rate: unmeasured', result.stdout)
        print('red-on-fault: qualified drill through the CLI -> check byte-stable, tag still REFUSED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
