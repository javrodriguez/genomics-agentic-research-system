"""The S2b probe's file-by-file comparison, on two small result trees (the `run` verb needs the pad)."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
PROBE = REPO / 'scripts' / 'repro_s2b_probe.py'


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class ProbeCompareTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='s2b-probe-')
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def compare(self, out='cmp'):
        return subprocess.run([sys.executable, str(PROBE), 'compare', '--a', str(self.root / 'a'), '--b',
                               str(self.root / 'b'), '--out', str(self.root / out)], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)

    def test_every_difference_is_listed_with_its_offset_and_copied(self):
        for side in ('a', 'b'):
            write(self.root / side / 'bwa/x.narrowPeak', b'I\t10\t20\n')
            write(self.root / side / 'multiqc/report.html', b'<html>' + side.encode() + b'</html>')
        write(self.root / 'a' / 'only-a.txt', b'x')
        proc = self.compare()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.decode(), '3 files compared, 1 equal, 2 differ (html 1, text 1)\n')
        differs = (self.root / 'cmp/differs.tsv').read_text().splitlines()
        self.assertIn('multiqc/report.html\thtml\t14\t14\t6', differs)
        self.assertIn('only-a.txt\ttext\t1\t-\tonly one side', differs)
        self.assertEqual((self.root / 'cmp/differing/b/multiqc/report.html').read_bytes(), b'<html>b</html>')
        self.assertFalse((self.root / 'cmp/differing/a/bwa/x.narrowPeak').exists())

    def test_scan_counts_each_name_per_file(self):
        spec = importlib.util.spec_from_file_location('probe', str(PROBE))
        probe = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(probe)
        write(self.root / 'r/results/multiqc/report.html', b'<p>/home/ubuntu/run1 by ubuntu</p>')
        write(self.root / 'r/results/x.bed.gz', b'\x1f\x8b')
        write(self.root / 'r/work/ab/cd/.command.log', b'ubuntu')
        rows = probe.scan(self.root / 'r', ['ubuntu', '/home/ubuntu/run1', 's3://'], self.root / 'names.tsv')
        self.assertEqual([(r, c) for r, c, _ in rows], [('results/multiqc/report.html', [2, 1, 0]),
                                                      ('results/x.bed.gz', [0, 0, 0])])

    def test_a_used_out_folder_is_refused(self):
        write(self.root / 'a' / 'x', b'1')
        write(self.root / 'b' / 'x', b'1')
        write(self.root / 'cmp' / 'old', b'1')
        proc = self.compare()
        self.assertEqual(proc.returncode, 2)

    def test_run_refuses_without_its_tools(self):
        proc = subprocess.run([sys.executable, str(PROBE), 'run', '--sources', 'x', '--pipeline-commit', 'a' * 40,
                               '--nextflow', '26.04.6', '--out', str(self.root / 'out')], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, env={'PATH': '/nonexistent'})
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b'is not on PATH', proc.stderr)


if __name__ == '__main__':
    unittest.main()
