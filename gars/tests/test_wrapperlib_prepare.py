"""R-164: the shared prepare writers emit identical bytes on repeated inputs."""
import tempfile
import time
import unittest
from pathlib import Path
from support import bytes_in
import wrapperlib as wl
import workspace


class WrapperlibPrepareTests(unittest.TestCase):
    def test_prepare_twice_identical_bytes(self):
        with tempfile.TemporaryDirectory(prefix='gars-prepare-') as tmp:
            root = Path(tmp)
            source = root / 'input.csv'
            source.write_text('sample,value\nA,1\n')
            for assay in sorted(workspace.PIPELINES):
                with self.subTest(assay=assay):
                    stage = root / assay
                    stage.mkdir()
                    cfg = {'compute.partition': 'test', 'compute.time': '00:01:00',
                           'compute.cpus': '1', 'compute.mem': '1G'}
                    def prepare():
                        wl.write_params_yaml(stage, assay, [('input', str(source)), ('n', 1)])
                        wl.write_submit_sh(stage, root, cfg, 'fixture', assay, 'true')
                        wl.write_reproducibility(stage, assay, root,
                                                 {'samplesheet': source}, [('n', 1)])
                    prepare()
                    before = bytes_in(stage)
                    self.assertEqual(set(before), {'params.yaml', 'submit.sh',
                                     'reproducibility/manifest.json',
                                     'reproducibility/commands.sh'})
                    time.sleep(1.05)  # also catches timestamps serialized at second precision
                    prepare()
                    self.assertEqual(before, bytes_in(stage))


if __name__ == '__main__':
    unittest.main(verbosity=2)
