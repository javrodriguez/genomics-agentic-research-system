"""R64-1-1 in the genome registry: the launch pad's yeast reference (decision 0246).

The two peak assays' genome menus must list it with the facts that travel with the genome (the
mitochondrial contig name and the MACS gsize) and a cache key per pinned pipeline, and the
second, ID-keyed hash table must be parsed separately from the identity table.
The menus are read from the repository's own registry through configure.py's real CLI, with no
bytecode written; the one synthetic registry lives in a temporary folder.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GARS = REPO / 'gars'
CONFIGURE = GARS / '_system' / 'configure.py'
REGISTRY = GARS / '_references' / 'genomes.md'
sys.path.insert(0, str(GARS / '_system'))
import configure  # noqa: E402
import workspace  # noqa: E402

PAD_REFS = '/home/ubuntu/genomics-agentic-research-system/install/refs/R64-1-1'
# The mito contig is the pinned FASTA's own header (`>MT`); the gsize is the effective size at
# read length 50 that nf-core/atacseq 2.1.2 gives R64-1-1, the registry's stated convention, and
# not the FASTA's whole length, 12157105 (decision 0246 records the commands and the ruling).
MITO = 'MT'
GSIZE = '11624332'
EXPECTED = {
    'id': 'R64-1-1',
    'species': 'Saccharomyces cerevisiae',
    'build': 'R64-1-1',
    'source': 'nf-core/test-datasets atacseq branch, pinned by sha256',
    'fasta': PAD_REFS + '/genome.fa',
    'gtf': PAD_REFS + '/genes.gtf',
    'cache_root': PAD_REFS + '/derived',
    'mito_name': MITO,
    'macs_gsize': GSIZE,
    'annotation_release': 'test-datasets atacseq branch, fetched 2026-09-30',
    'fasta_sha256': 'c0b7305c230b550c3d8ccc692df52338afc7a297b43d965868c285b98aa64ae1',
    'gtf_sha256': '3a1e64b8f290127562612b47d6014bc6e4c130399da3e06ad062b268fd6d08fb',
}
# Each peak assay's pin, spelled out here as well as read from workspace.PIPELINES, so a pin
# change shows up in this test and not only in the cache path it moves.
PINS = {'atacseq_bulk': 'nf-core-atacseq-2.1.2', 'chipseq_bulk': 'nf-core-chipseq-2.1.0'}


def menu(assay, *extra):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-B', str(CONFIGURE), 'genomes', '--assay', assay]
                            + list(extra), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            universal_newlines=True, env=env, cwd=str(GARS), timeout=60)
    return result.returncode, json.loads(result.stdout), result.stderr


class R64RegistryTests(unittest.TestCase):
    def test_peak_menus_list_r64_with_its_facts_and_cache_key(self):
        derived = {}
        for assay, pin in sorted(PINS.items()):
            with self.subTest(assay=assay):
                self.assertEqual(workspace.PIPELINES[assay], pin)
                code, res, err = menu(assay)
                self.assertEqual(code, 0, err)
                self.assertTrue(res['ok'])
                hits = [g for g in res['genomes'] if g['id'] == 'R64-1-1']
                self.assertEqual(len(hits), 1, [g['id'] for g in res['genomes']])
                entry = hits[0]
                for key, value in sorted(EXPECTED.items()):
                    self.assertEqual(entry.get(key), value, key)
                # The cache key is the registry's root plus this assay's pinned pipeline.
                self.assertEqual(entry['derived_dir'], os.path.join(PAD_REFS + '/derived', pin))
                self.assertEqual(entry['cached_indices'], os.path.isdir(entry['derived_dir']))
                derived[assay] = entry['derived_dir']
                code, res, err = menu(assay, '--select', 'R64-1-1')
                self.assertEqual(code, 0, err)
                self.assertEqual(res['genome_id'], 'R64-1-1')
                self.assertEqual(res['selected']['mito_name'], MITO)
                self.assertEqual(res['selected']['macs_gsize'], GSIZE)
        # ATAC and ChIP pin different pipelines, so neither reuses the other's index.
        self.assertEqual(len(set(derived.values())), 2, derived)

    def test_menu_numbers_keep_grch38_first(self):
        code, res, err = menu('atacseq_bulk')
        self.assertEqual(code, 0, err)
        self.assertEqual([(g['n'], g['id']) for g in res['genomes']],
                         [('01', 'GRCh38'), ('02', 'R64-1-1')])

    def test_hash_table_is_parsed_separately(self):
        rows, err = configure.read_genomes(GARS)
        self.assertIsNone(err)
        self.assertEqual([r['id'] for r in rows], ['GRCh38', 'R64-1-1'])
        for row in rows:
            with self.subTest(row=row['id']):
                for column in ('fasta', 'gtf'):
                    self.assertTrue(row[column].startswith('/'), row[column])
                self.assertIn('fasta_sha256', row)
        # Each table's own lines, counted from the file: one identity row per hash row.
        lines = REGISTRY.read_text(encoding='utf-8').splitlines()
        identity = lines.index('| ID | Species | Build | Source | FASTA | GTF | Derived cache root '
                               '| Mito contig | MACS gsize |')
        hashes = lines.index('| ID | Annotation release | fasta_sha256 | gtf_sha256 |')

        def body(start):
            out = []
            for line in lines[start + 2:]:
                if not line.startswith('|'):
                    break
                out.append(line.strip('|').split('|')[0].strip())
            return out
        self.assertEqual(body(identity), ['GRCh38', 'R64-1-1'])
        self.assertEqual(body(hashes), ['GRCh38', 'R64-1-1'])
        # A hash-table row with no identity row is never read as a genome.
        with tempfile.TemporaryDirectory(prefix='gars-r64-registry-') as temp:
            (Path(temp) / '_references').mkdir()
            planted = '| HASH-ONLY | planted | %s | %s |' % ('a' * 64, 'b' * 64)
            text = REGISTRY.read_text(encoding='utf-8').rstrip('\n') + '\n' + planted + '\n'
            (Path(temp) / '_references' / 'genomes.md').write_text(text, encoding='utf-8')
            planted_rows, err = configure.read_genomes(temp)
            self.assertIsNone(err)
            self.assertEqual([r['id'] for r in planted_rows], ['GRCh38', 'R64-1-1'])
            self.assertEqual(planted_rows, rows)


if __name__ == '__main__':
    unittest.main(verbosity=2)
