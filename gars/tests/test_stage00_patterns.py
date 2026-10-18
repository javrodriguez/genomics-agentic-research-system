"""One sample-name pattern per assay (FIXES.md item S00-onepattern).

`link` takes the `--sample-id-pattern` its assay's `inspect` used, refuses one that does not read
the folder before any link exists, and records it beside `raw/` as the machine-owned
`00_data/<assay>/sample_id_pattern.txt` (empty for the bcl2fastq convention). `finalize` derives
each assay's names with that assay's own record, so one assay's pattern is never applied to
another; a `--sample-id-pattern` given to finalize that disagrees with an assay's record is
refused with nothing written, and an assay linked before this change (no record) keeps the
flag's old meaning (0314).
"""
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

PATTERN = r'^(?P<sample>atac-[A-Z0-9]+)\.r(?P<read>[12])\.fq\.gz$'


def fastq_gz(path):
    with gzip.open(str(path), 'wt') as fh:
        fh.write('@r\nACGT\n+\nIIII\n')


class PatternTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='stage00-patterns-'))
        self.addCleanup(self.cleanup)
        self.ws = self.tmp / 'gars'
        self.ws.mkdir()
        for d in ('_system', '_references', '_templates'):
            shutil.copytree(str(GARS / d), str(self.ws / d),
                            ignore=shutil.ignore_patterns('__pycache__'))
        (self.ws / 'projects').mkdir()
        self.rna = self.tmp / 'rna'
        self.atac = self.tmp / 'atac'
        self.rna.mkdir()
        self.atac.mkdir()
        for s in ('A1_S1', 'A2_S2'):
            for r in ('R1', 'R2'):
                fastq_gz(self.rna / ('%s_L001_%s_001.fastq.gz' % (s, r)))
        for s in ('atac-X1', 'atac-X2'):
            for r in ('1', '2'):
                fastq_gz(self.atac / ('%s.r%s.fq.gz' % (s, r)))
        self.project = self.ws / 'projects/p'

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

    def create(self, *assays):
        code, result = self.reg('create', '--title', 'p', '--assays', *assays)
        self.assertEqual(code, 0, result)

    def link(self, assay, source, *extra):
        return self.reg('link', '--project', 'projects/p', '--assay', assay,
                        '--source', str(source), *extra)

    def finalize(self, *extra):
        return self.reg('finalize', '--project', 'projects/p', '--data-class', 'public',
                        '--purpose', 'fixture', *extra)

    def ids(self, assay):
        text = (self.project / '00_data' / assay / 'samples.csv').read_text()
        return [l.split(',')[0] for l in text.splitlines()[1:]]

    def two_assays(self):
        self.create('rnaseq_bulk', 'atacseq_bulk')
        code, result = self.link('rnaseq_bulk', self.rna)
        self.assertEqual(code, 0, result)
        code, result = self.link('atacseq_bulk', self.atac, '--sample-id-pattern', PATTERN)
        self.assertEqual(code, 0, result)

    def test_each_assay_keeps_the_pattern_its_own_inspection_used(self):
        self.two_assays()
        code, result = self.finalize()
        self.assertEqual(code, 0, result)
        self.assertEqual(self.ids('rnaseq_bulk'), ['A1', 'A2'])
        self.assertEqual(self.ids('atacseq_bulk'), ['atac-X1', 'atac-X2'])

    def test_link_records_the_pattern_machine_owned(self):
        self.two_assays()
        atac = self.project / '00_data/atacseq_bulk/sample_id_pattern.txt'
        rna = self.project / '00_data/rnaseq_bulk/sample_id_pattern.txt'
        self.assertEqual(atac.read_text(), PATTERN + '\n')
        self.assertEqual(rna.read_text(), '')
        self.assertEqual(stat.S_IMODE(atac.stat().st_mode), 0o444)

    def test_finalize_refuses_a_pattern_that_disagrees_with_a_record(self):
        self.two_assays()
        code, result = self.finalize('--sample-id-pattern', PATTERN)
        self.assertEqual(code, 2, result)
        failure = ' '.join(result['failures'])
        self.assertIn('rnaseq_bulk', failure)
        self.assertIn('the bcl2fastq convention', failure)
        self.assertFalse((self.project / '00_data/rnaseq_bulk/files.csv').exists())
        self.assertFalse((self.project / '00_data/atacseq_bulk/files.csv').exists())

    def test_link_refuses_a_pattern_that_does_not_read_the_folder(self):
        self.create('rnaseq_bulk')
        code, result = self.link('rnaseq_bulk', self.rna, '--sample-id-pattern', PATTERN)
        self.assertEqual(code, 2, result)
        self.assertIn('unmatched_examples', result)
        self.assertEqual(list((self.project / '00_data/rnaseq_bulk/raw').iterdir()), [])
        self.assertFalse((self.project / '00_data/rnaseq_bulk/sample_id_pattern.txt').exists())

    def test_an_assay_linked_before_the_record_keeps_the_flag(self):
        self.create('atacseq_bulk')
        raw = self.project / '00_data/atacseq_bulk/raw'
        for name in sorted(os.listdir(str(self.atac))):     # links as an earlier link made them
            os.symlink(str(self.atac / name), str(raw / name))
        code, result = self.finalize('--sample-id-pattern', PATTERN)
        self.assertEqual(code, 0, result)
        self.assertEqual(self.ids('atacseq_bulk'), ['atac-X1', 'atac-X2'])

    def test_a_one_assay_convention_project_writes_the_same_tables(self):
        self.create('rnaseq_bulk')
        code, result = self.link('rnaseq_bulk', self.rna)
        self.assertEqual(code, 0, result)
        code, result = self.finalize()
        self.assertEqual(code, 0, result)
        raw = '00_data/rnaseq_bulk/raw'
        self.assertEqual(
            (self.project / '00_data/rnaseq_bulk/files.csv').read_text(),
            '# generated by stage 00 — do not edit\nsample_id,lane,fastq_1,fastq_2\n'
            'A1,L001,%s/A1_S1_L001_R1_001.fastq.gz,%s/A1_S1_L001_R2_001.fastq.gz\n'
            'A2,L001,%s/A2_S2_L001_R1_001.fastq.gz,%s/A2_S2_L001_R2_001.fastq.gz\n'
            % ((raw,) * 4))
        self.assertEqual((self.project / '00_data/rnaseq_bulk/samples.csv').read_text(),
                         'sample_id,condition,group,replicate\nA1,,,\nA2,,,\n')

    def test_the_guard_admits_link_with_a_pattern(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S00-onepattern-registry.patch."""
        tool, args = policy.parse_argv(
            ['python3', '_system/stage00_register.py', 'link', '--project', 'projects/p',
             '--assay', 'atacseq_bulk', '--source', '/data/atac',
             '--sample-id-pattern', PATTERN], root=GARS)
        self.assertEqual(tool['name'], 'stage00_register.link')
        self.assertEqual(args['sample-id-pattern'], PATTERN)


class ContractTests(unittest.TestCase):
    def test_link_carries_the_pattern_and_finalize_does_not(self):
        text = (GARS / '00_initialize_project/CONTEXT.md').read_text()
        process = text.split('## Process', 1)[1].split('## Response Format', 1)[0]
        link = [l for l in process.splitlines() if 'stage00_register.py link' in l]
        self.assertEqual(len(link), 1, link)
        self.assertIn("--sample-id-pattern", ' '.join(process.split('12. ', 1)[1]
                                                       .split('13. ', 1)[0].split()))
        step15 = ' '.join(process.split('15. ', 1)[1].split('16. ', 1)[0].split())
        self.assertNotIn('Add the same `--sample-id-pattern`', step15)
        self.assertIn('sample_id_pattern.txt', step15)


if __name__ == '__main__':
    unittest.main()
