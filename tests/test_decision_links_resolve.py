"""R-001 and the owner's rulings 7A/8A; uses the production pre-commit checker."""
import contextlib
import io
from pathlib import Path
import runpy
import re
from unittest import mock
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
CHECK = runpy.run_path(str(REPO / 'gars/_system/hooks/pre-commit'))


class DecisionLinksTests(unittest.TestCase):
    def test_repository_citations_resolve(self):
        self.assertTrue(CHECK['decision_links'](REPO))

    def test_forms_fields_and_staged_tree(self):
        with tempfile.TemporaryDirectory(prefix='row11-links-') as temp:
            root = Path(temp)
            def git(*args):
                return subprocess.check_output(['git'] + list(args), cwd=str(root),
                                               stderr=subprocess.PIPE)
            git('init', '-q')
            folder = root / 'docs/decisions'
            folder.mkdir(parents=True)
            legacy = folder / '0001-legacy.md'
            legacy.write_text('---\ndate: 2026-09-21\nstatus: standing\n---\nLegacy.\n')
            code = root / 'sample.py'
            code.write_text('# DECISIONS 0001 and (2024)\n')
            git('add', '--', 'docs', 'sample.py')
            self.assertTrue(CHECK['decision_links'](root, staged=True))
            print('positive control: legacy frontmatter and bare (2024) accepted; count=1')
            with mock.patch.dict(CHECK['decision_links'].__globals__, RECORD_DATE='2000-01-01',
                                 LEGACY_THROUGH='0000'):
                with self.assertRaises(AssertionError):
                    self.assertTrue(CHECK['decision_links'](root, staged=True))
            print('red-on-fault: legacy treated as new -> legacy acceptance assertion FAILED')
            for word in ('decision', 'decisions'):
                code.write_text('# ' + word + ' ' + '9999\n')
                git('add', '--', 'sample.py')
                code.write_text('# clean unstaged copy\n')
                self.assertFalse(CHECK['decision_links'](root, staged=True))
                print('red-on-fault: dangling %s -> staged check REFUSED' % word)
            code.write_text('# (2024)\n')
            git('add', '--', 'sample.py')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertTrue(CHECK['decision_links'](root, staged=True))
            self.assertIn('citations: 0/0 resolve', output.getvalue())
            with mock.patch.dict(CHECK['decision_links'].__globals__,
                                 CITATION=re.compile(r'\((\d{4})\)')):
                with self.assertRaises(AssertionError):
                    self.assertTrue(CHECK['decision_links'](root, staged=True))
            print('red-on-fault: bare year counted -> citation acceptance assertion FAILED')
            new = folder / '0066-new.md'
            body = '---\ndate: 2026-09-22\nstatus: standing\n---\n'
            body += ''.join('## %s\nRequired content.\n' % s for s in
                            ('Context', 'Decision', 'Status', 'Date'))
            new.write_text(body)
            git('add', '--', 'docs')
            self.assertFalse(CHECK['decision_links'](root, staged=True))
            print('red-on-fault: new record missing Test -> REFUSED')
            new.write_text(body + '## Test\nRun the acceptance.\n')
            git('add', '--', 'docs')
            self.assertTrue(CHECK['decision_links'](root, staged=True))
            legacy.unlink()
            git('add', '--', 'docs')
            code.write_text('# decision ' + '0001\n')
            git('add', '--', 'sample.py')
            self.assertFalse(CHECK['decision_links'](root, staged=True))

    def test_bad_frontmatter_and_empty_sections_refuse(self):
        for content in ('no metadata', '---\ndate: bad\nstatus: standing\n---\n',
                        '---\ndate: 2026-09-22\nstatus: standing\n---\n## Test\n'):
            with self.assertRaises(ValueError):
                CHECK['record_fields'](content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
