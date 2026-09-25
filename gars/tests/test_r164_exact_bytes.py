"""R-164 class 1: every input checksum is the digest of the exact bytes (0087).

The oracle is hashlib over the bytes the fixture wrote; no source file is read.
"""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from support import GARS, module
import executorlib as ex
import wrapperlib as wl
from tools.execution import config_holds

MIB = 1 << 20


def digest(data):
    return hashlib.sha256(data).hexdigest()


def payloads():
    """Pairwise-distinct byte strings that a lossy reader would confuse."""
    near = b'x' * (MIB - 1)
    return [
        ('empty', b''),
        ('newline', b'\n'),
        ('no-newline', b'value'),
        ('trailing-newline', b'value\n'),
        ('trailing-space', b'value '),
        ('trailing-mixed', b'value \t\r\n'),
        ('crlf', b'value\r\n'),
        ('binary', bytes(range(256)) + b'\x00\xff\x00'),
        ('chunk-minus-one', near),
        ('chunk-exact', near + b' '),
        ('chunk-plus-one', near + b' x'),
        ('space-at-chunk-end', near + b' ' + b'tail'),
        ('chunk-plus-one-trailing', near + b'xy '),
    ]


class ExactBytesTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='gars-bytes-')
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def test_sha256_is_the_digest_of_the_exact_bytes(self):
        seen = {}
        for label, data in payloads():
            with self.subTest(payload=label):
                path = self.write(label, data)
                self.assertEqual(wl.sha256(path), digest(data))
                seen[label] = wl.sha256(path)
        self.assertEqual(len(set(seen.values())), len(seen))

    def test_reproducibility_records_exact_input_digests(self):
        stage = self.root / 'stage'
        stage.mkdir()
        sheet = self.write('sheet.csv', b'sample,fastq_1\nA,a.fq \n')
        config = self.write('cfg.yaml', b'aligner: star\n\n')
        wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', str(sheet))])
        wl.write_submit_sh(stage, self.root, {}, 'fixture', 'rnaseq_bulk', 'true')
        wl.write_reproducibility(stage, 'rnaseq_bulk', self.root,
                                 {'samplesheet': sheet, 'config': config}, [('n', 1)])
        manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
        self.assertEqual(manifest['samplesheet_sha256'], digest(sheet.read_bytes()))
        self.assertEqual(manifest['config_sha256'], digest(config.read_bytes()))
        self.assertEqual(manifest['key_formula'], 'stage01-v1')
        expected = digest((stage / 'params.yaml').read_bytes() + sheet.read_bytes() +
                          config.read_bytes())
        self.assertEqual(manifest['idempotency_key'], expected)
        self.assertIn('# idempotency_key=' + expected + '\n',
                      (stage / 'submit.sh').read_text())

    def test_stage01_key_is_the_ordered_concatenation(self):
        stage = self.root / 'stage'
        stage.mkdir()
        (stage / 'params.yaml').write_bytes(b'input: s\n')
        near = b'p' * (MIB - 1)
        cases = [(b'a,b\n', b'k: v\n'), (b'a,b\n ', b'k: v\n'), (b'a,b', b'k: v\n'),
                 (near + b' ', b'k: v'), (near + b'  ', b'k: v'), (b'', b'')]
        keys = set()
        for sheet_bytes, config_bytes in cases:
            with self.subTest(sheet=sheet_bytes[-3:], config=config_bytes):
                sheet = self.write('sheet.csv', sheet_bytes)
                config = self.write('cfg.yaml', config_bytes)
                manifest = {'key_formula': 'stage01-v1',
                            'inputs': {'samplesheet': str(sheet), 'config': str(config)}}
                key = wl.input_key(stage, manifest)
                self.assertEqual(key, digest(b'input: s\n' + sheet_bytes + config_bytes))
                keys.add(key)
        self.assertEqual(len(keys), len(cases))

    def test_downstream_key_separates_every_byte_difference(self):
        stage = self.root / 'stage'
        stage.mkdir()
        keys = {}
        for label, data in payloads():
            path = self.write('inputs/' + label, data)
            manifest = {'key_formula': 'downstream-v1', 'params': {'n': 1},
                        'inputs': {'counts': str(path)}}
            keys[label] = wl.input_key(stage, manifest)
            with self.subTest(payload=label):
                copy = self.write('copies/' + label, data)
                same = dict(manifest, inputs={'counts': str(copy)})
                self.assertEqual(wl.input_key(stage, same), keys[label])
        self.assertEqual(len(set(keys.values())), len(keys))

    def test_output_evidence_file_and_tree_digests(self):
        stage = self.root / 'stage'
        members = {'b.txt': b'1\n', 'sub/c.bin': b'\x00 ', 'sub/d.txt': b'd \n'}
        for name, data in members.items():
            self.write('stage/run/tree/' + name, data)
        single = self.write('stage/run/one.txt', b'x \n')
        row = wl.output_evidence(stage, {'type': 't', 'role': 'native', 'path': 'run/one.txt'})
        self.assertEqual(row['sha256'], digest(single.read_bytes()))
        tree = wl.output_evidence(stage, {'type': 't', 'role': 'native', 'path': 'run/tree'})
        listed = [{'path': k, 'sha256': digest(v)} for k, v in sorted(members.items())]
        self.assertEqual(tree['members'], listed)
        listing = ''.join(r['path'] + '\t' + r['sha256'] + '\n' for r in listed)
        self.assertEqual(tree['sha256'], 'sha256-tree:' + digest(listing.encode('utf-8')))
        self.write('stage/run/tree/sub/d.txt', b'd\n')
        changed = wl.output_evidence(stage, {'type': 't', 'role': 'native', 'path': 'run/tree'})
        self.assertNotEqual(changed['sha256'], tree['sha256'])

    def test_reference_digest_follows_the_bytes(self):
        path = self.write('ref.fa', b'>chr1\nACGT \n')
        os.utime(str(path), ns=(1000000000, 1000000000))
        self.assertEqual(wl.reference_sha256(path), digest(b'>chr1\nACGT \n'))
        path.write_bytes(b'>chr1\nACGTT\n')
        os.utime(str(path), ns=(2000000000, 2000000000))
        self.assertEqual(wl.reference_sha256(path), digest(b'>chr1\nACGTT\n'))

    def test_config_rehash_refuses_whitespace_only_edits(self):
        project = self.root / 'project'
        stage = project / 'stage'
        (stage / 'reproducibility').mkdir(parents=True)
        (project / '_config').mkdir()
        original = b'aligner: star\n'
        config = project / '_config/rnaseq_bulk.yaml'
        config.write_bytes(original)
        (stage / 'reproducibility/manifest.json').write_text(
            json.dumps({'config_sha256': digest(original)}))
        self.assertIsNone(config_holds(project, stage, 'rnaseq_bulk'))
        for edited in (b'aligner: star\n\n', b'aligner: star \n', b'aligner: star'):
            with self.subTest(edited=edited):
                config.write_bytes(edited)
                self.assertIn('config_sha256 changed', config_holds(project, stage, 'rnaseq_bulk'))

    def test_claim_evidence_digest_is_exact(self):
        check = module(GARS / '_system/claims/evidence_check.py', 'r164_evidence_check')
        project = self.root / 'project'
        for label, data in payloads():
            with self.subTest(payload=label):
                self.write('project/e.bin', data)
                artifact = {'path': 'e.bin', 'sha256': digest(data)}
                self.assertIsNone(check.artifact_problem(artifact, project))
                artifact = {'path': 'e.bin', 'sha256': digest(data + b' ')}
                self.assertEqual(check.artifact_problem(artifact, project),
                                 'evidence_hash_mismatch')

    def test_executor_script_digest_is_exact(self):
        seen = set()
        for label, data in payloads():
            with self.subTest(payload=label):
                path = self.write('scripts/' + label, data)
                self.assertEqual(ex._sha256(path), digest(data))
                seen.add(ex._sha256(path))
        self.assertEqual(len(seen), len(payloads()))

    def legacy_stage(self, config_bytes, sheet_bytes):
        root = self.root / 'legacy'
        stage = root / '02_bioinformatics/rnaseq_bulk/01_fixture'
        (stage / 'reproducibility').mkdir(parents=True, exist_ok=True)
        (root / '_config').mkdir(exist_ok=True)
        (root / '_config/rnaseq_bulk.yaml').write_bytes(config_bytes)
        sheet = root / 'sheet.csv'
        sheet.write_bytes(sheet_bytes)
        wl.write_params_yaml(stage, 'rnaseq_bulk', [('input', str(sheet.resolve()))])
        return root, stage

    def claim(self, stage, key):
        (stage / 'reproducibility/manifest.json').write_text(json.dumps({'idempotency_key': key}))
        (stage / 'submit.sh').write_text('#!/bin/bash\n# idempotency_key=%s\ntrue\n' % key)

    def test_legacy_prepared_key_is_the_exact_concatenation(self):
        near = b'c' * (MIB - 1)
        cases = [(b'aligner: star\n', b'a,b\n'), (b'aligner: star \n', b'a,b\n'),
                 (b'aligner: star\n\n', b'a,b \n'), (near + b' ', b''), (b'', b'')]
        keys = set()
        for config_bytes, sheet_bytes in cases:
            with self.subTest(config=config_bytes[-4:], sheet=sheet_bytes):
                root, stage = self.legacy_stage(config_bytes, sheet_bytes)
                params = (stage / 'params.yaml').read_bytes()
                exact = digest(params + sheet_bytes + config_bytes)
                self.claim(stage, exact)
                self.assertEqual(ex.prepared_key(root, stage), exact)
                keys.add(exact)
                lossy = digest(params.rstrip() + sheet_bytes.rstrip() + config_bytes.rstrip())
                if lossy != exact:
                    self.claim(stage, lossy)
                    with self.assertRaises(ValueError):
                        ex.prepared_key(root, stage)
        self.assertEqual(len(keys), len(cases))


if __name__ == '__main__':
    unittest.main(verbosity=2)
