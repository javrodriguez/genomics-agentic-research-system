"""Each downstream wrapper prepares and submits with its own declared-input key."""
import argparse
import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS
import executorlib as ex
import wrapperlib as wl


class DownstreamKeyTests(unittest.TestCase):
    def check_wrapper(self, name):
        source = GARS / '_system/wrappers' / name / (name.replace('-', '_') + '.py')
        spec = importlib.util.spec_from_file_location(name.replace('-', '_'), str(source))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '_config').mkdir()
            cfg_path = root / '_config' / (module.ASSAY + '.yaml'); cfg_path.write_text('fixture: declared\n')
            stage = root / '02_bioinformatics' / module.ASSAY / module.SUBSTAGE
            sheet = root / 'sheet.csv'; sheet.write_text('sample\ns1\n')
            data = root / 'data'; data.write_text('declared input\n')
            design = (root / '01_samplesheets/rnaseq_bulk_design.csv'
                      if name == 'rnaseq-de' else root / 'design')
            design.parent.mkdir(exist_ok=True)
            design.write_text('sample,condition\ns1,A\n')
            paths = {'substage': stage, 'config': cfg_path, 'samplesheet': sheet, 'inputs': [('s1', data)]}
            cfg = {'de.formula': '~condition', 'de.contrast': 'condition,A,B',
                   'qc.min_genes': '1', 'qc.min_cells': '1', 'qc.max_mito_pct': '20',
                   'n_hvg': '2000', 'cluster_resolution': '1'}
            args = argparse.Namespace(project=str(root), counts=str(data), design=str(design), h5ad=str(data))
            with patch.object(module, 'run_checks', return_value=([], cfg, paths)), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.cmd_prepare(args), 0)
            key = ex.prepared_key(root, stage)
            manifest = json.loads((stage / 'reproducibility/manifest.json').read_text())
            self.assertEqual(manifest['key_formula'], 'downstream-v1')
            self.assertFalse((stage / 'params.yaml').exists())
            # Insertion order is irrelevant, and unrelated stage-01 rewrites do not participate.
            reversed_manifest = dict(manifest); reversed_manifest['inputs'] = dict(reversed(list(manifest['inputs'].items())))
            self.assertEqual(wl.input_key(stage, reversed_manifest), key)
            (root / 'other_stage01.csv').write_text('changed stage01 serialization\n')
            self.assertEqual(ex.prepared_key(root, stage), key)
            # A coherent key for another assay's config must still refuse before submit.
            other = root / '_config/other_assay.yaml'; other.write_bytes(cfg_path.read_bytes())
            wrong = dict(manifest); wrong['inputs'] = dict(manifest['inputs'], config=str(other))
            wrong['idempotency_key'] = wl.input_key(stage, wrong)
            manifest_path = stage / 'reproducibility/manifest.json'
            script = stage / 'submit.sh'; original_script = script.read_text()
            manifest_path.write_text(json.dumps(wrong))
            script.write_text(original_script.replace(key, wrong['idempotency_key']))
            with patch.object(ex, '_submit_once', return_value=('99', None)) as backend:
                self.assertIsNone(ex.submit(root, script)[0])
                backend.assert_not_called()
            manifest_path.write_text(json.dumps(manifest)); script.write_text(original_script)
            with patch.object(ex, '_submit_once', return_value=('42', None)) as backend:
                self.assertEqual(ex.submit(root, stage / 'submit.sh'), ('42', None))
                self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                self.assertEqual(backend.call_count, 1)
            data.write_text('changed declared input\n')
            with patch.object(ex, '_submit_once', return_value=('99', None)) as backend:
                self.assertIsNone(ex.submit(root, stage / 'submit.sh')[0])
                backend.assert_not_called()

    def test_rnaseq_de_submit(self):
        self.check_wrapper('rnaseq-de')

    def test_scrna_qc_cluster_submit(self):
        self.check_wrapper('scrna-qc-cluster')

    def test_spatial_cluster_count_submit(self):
        self.check_wrapper('spatial-cluster-count')


if __name__ == '__main__':
    unittest.main(verbosity=2)
