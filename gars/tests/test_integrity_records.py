"""Whole FASTQ records in full mode, with quick/skip behavior retained."""
import gzip
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import module, REPO
integrity = module(REPO / 'gars/_system/integrity.py', 'record_integrity')


class IntegrityRecordTests(unittest.TestCase):
    def test_records_plain_and_gzip(self):
        whole = b'@synthetic\nACGT\n+\nIIII\n'
        bad = [b'@synthetic\nACGT\n+\n', b'@synthetic\nACGT\nwrong\nIIII\n',
               b'@synthetic\nACGT\n+\nIII\n', whole[:-1], b'synthetic\nACGT\n+\nIIII\n']
        with tempfile.TemporaryDirectory(prefix='integrity-records-') as folder:
            for suffix in ('.fastq', '.fq', '.fastq.gz', '.fq.gz'):
                path = Path(folder) / ('reads' + suffix)
                for content in [whole, whole * 2] + bad:
                    path.write_bytes(gzip.compress(content) if suffix.endswith('.gz') else content)
                    problem = integrity.check_one(path, 'full')
                    if content in bad:
                        self.assertEqual(problem, 'truncated record 1')
                    else:
                        self.assertIsNone(problem)
                    self.assertIsNone(integrity.check_one(path, 'quick'))
                    self.assertIsNone(integrity.check_one(path, 'skip'))

    def test_stage01_plain_truncation_and_default(self):
        generator = module(REPO / 'benchmarks/defects/generate.py', 'integrity_generator')
        import json
        import subprocess
        with tempfile.TemporaryDirectory(prefix='integrity-stage-') as folder:
            root = Path(folder)
            data = generator.project(root)
            sorted((data / 'raw').iterdir())[0].write_bytes(b'@synthetic\nACGT\n+\n')
            argv = [sys.executable, str(REPO / 'gars/_system/stage01_samplesheet.py'),
                    '--project', str(root), '--check']
            default = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(default.returncode, 0)
            full = subprocess.run(argv + ['--verify-integrity', 'full'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertEqual(full.returncode, 1)
            result = json.loads(full.stdout.decode())
            self.assertTrue(any(f['check'] == 'integrity'
                                for a in result['assays'].values() for f in a['failures']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
