"""The yeast ATAC exemplar's committed files agree with each other (decisions 0281, 0283).

The landing README's result line and table, and the agreed member outcomes the public workflow
compares a re-run against, are both rendered by `package_run.py rerun-note` from the same two
pass artifacts. These tests bind them on every push: rolling agreed-members.tsv up through the
package's own compare.py must give the README's line and every row of its table, the agreed members
must be exactly the package's, in the package's modes, and the package must verify offline.
Standard library only; no network.
"""
import csv
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
EXEMPLAR = REPO / 'reproduction' / 'yeast-atac'
PACKAGE = EXEMPLAR / 'package'
OK_RESULTS = ('match', 'present')


def load_compare():
    spec = importlib.util.spec_from_file_location('exemplar_compare', str(PACKAGE / 'compare.py'))
    module = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(module)
    return module


def result_ok(result):
    """A result compare.py counts as matching (as package_run.py's result_ok)."""
    return result in OK_RESULTS or result.startswith(('match after ', 'within '))


def agreed_members():
    text = (EXEMPLAR / 'agreed-members.tsv').read_text(encoding='utf-8')
    return {(r['stage'], r['path']): r for r in csv.DictReader(io.StringIO(text), delimiter='\t')}


def readme_rows():
    """The landing README's table rows, as the tuple compare.py's OUTPUT_COLUMNS would print."""
    rows = []
    for line in (EXEMPLAR / 'README.md').read_text(encoding='utf-8').splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if line.startswith('| ') and len(cells) == 10 and cells[3].isdigit():
            cells[2] = cells[2].strip('`')
            rows.append(tuple(cells))
    return rows


class YeastAtacExemplar(unittest.TestCase):
    def test_agreed_members_are_the_packages_in_its_modes(self):
        compare = load_compare()
        rows = compare.package_rows(str(PACKAGE))
        modes = {}
        for row in rows:
            modes.setdefault((row['stage'], compare.member_path(row)), row['mode'])
        agreed = agreed_members()
        self.assertEqual(sorted(agreed), sorted(modes))
        for key, row in agreed.items():
            self.assertEqual(row['mode'], modes[key], key)

    def test_the_readme_line_and_table_are_the_agreed_members_rolled_up(self):
        compare = load_compare()
        rows = compare.package_rows(str(PACKAGE))
        row_of = {}
        for row in rows:
            row_of.setdefault((row['stage'], compare.member_path(row)), row)
        members = {key: {'row': row_of[key], 'ok': result_ok(a['result']), 'result': a['result'],
                         'rerun_sha256': ''} for key, a in agreed_members().items()}
        result = compare.rollup(rows, members, {})
        readme = (EXEMPLAR / 'README.md').read_text(encoding='utf-8')
        self.assertIn(compare.line(result['counts']), readme)
        rolled = [tuple(str(o[c]) for c in compare.OUTPUT_COLUMNS) for o in result['outputs']]
        self.assertEqual(readme_rows(), rolled)

    def test_the_package_verifies_offline(self):
        proc = subprocess.run([sys.executable, str(PACKAGE / 'verify.py')], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, env={'PYTHONDONTWRITEBYTECODE': '1', 'PATH': '/usr/bin:/bin'})
        self.assertEqual(proc.returncode, 0, proc.stdout.decode('utf-8', 'replace'))
        self.assertIn('package verified', proc.stdout.decode('utf-8', 'replace'))


if __name__ == '__main__':
    unittest.main()
