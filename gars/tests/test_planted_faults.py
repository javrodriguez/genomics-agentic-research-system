"""Watch three acceptance cases go red on public, disposable faults."""
import shutil
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from support import GARS
import test_guard_hook
import test_wrapper_contract
import test_wrapperlib_prepare


class PlantedFaultTests(unittest.TestCase):
    def assert_red(self, case, name):
        result = unittest.TestResult()
        case.run(result)
        self.assertTrue(result.failures, result.errors)
        print('red-on-fault: %s -> %s' % (name, result.failures[0][0].id()), flush=True)

    def test_missing_wrapper_contract_section(self):
        with tempfile.TemporaryDirectory(prefix='gars-contract-fault-') as tmp:
            root = Path(tmp)
            shutil.copytree(str(GARS / '_system'), str(root / '_system'))
            shutil.copytree(str(GARS / '02_bioinformatics'), str(root / '02_bioinformatics'))
            path = next((root / '02_bioinformatics').glob('*/01_*/CONTEXT.md'))
            path.write_text(path.read_text().replace('## Scope Boundaries', '## Missing'))
            with mock.patch.object(test_wrapper_contract, 'GARS', root):
                self.assert_red(test_wrapper_contract.WrapperContractTests('test_all_wrapper_contracts'),
                                'missing wrapper contract section')

    def test_prepare_timestamp_changes_bytes(self):
        original = test_wrapperlib_prepare.wl.write_params_yaml
        def timestamp(stage, assay, params):
            original(stage, assay, params)
            with (stage / 'params.yaml').open('a') as output:
                output.write('# timestamp: %s\n' % time.time())
        with mock.patch.object(test_wrapperlib_prepare.wl, 'write_params_yaml', timestamp):
            self.assert_red(test_wrapperlib_prepare.WrapperlibPrepareTests(
                'test_prepare_twice_identical_bytes'), 'prepare writes timestamp')

    def test_guard_allows_denied_shape(self):
        with tempfile.TemporaryDirectory(prefix='gars-guard-fault-') as tmp:
            root = Path(tmp)
            (root / '_system').mkdir()
            source = (GARS / '_system/guard_hook.py').read_text()
            self.assertIn('    sys.exit(2)', source)
            (root / '_system/guard_hook.py').write_text(source.replace('    sys.exit(2)',
                                                                       '    sys.exit(0)'))
            with mock.patch.object(test_guard_hook, 'GARS', root):
                self.assert_red(test_guard_hook.GuardHookTests('test_denied_shapes'),
                                'guard allows denied shape')


if __name__ == '__main__':
    unittest.main(verbosity=2)
