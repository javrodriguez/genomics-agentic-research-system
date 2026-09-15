"""R-164: enumerate every shipped wrapper and its stage contract."""
import json
import sys
import unittest
from support import GARS, REPO, module, run

lint = module(REPO / 'tests/check_contracts.py', 'row3_contract_lint')


def wrappers():
    return sorted(p for p in (GARS / '_system/wrappers').iterdir() if p.is_dir())


class WrapperContractTests(unittest.TestCase):
    def test_all_wrapper_contracts(self):
        found = wrappers()
        nfcore = [p for p in found if p.name.startswith('nfcore-')]
        print('wrapper contracts: %d/7 found/expected nf-core; %d total wrappers' %
              (len(nfcore), len(found)), flush=True)
        self.assertGreaterEqual(len(nfcore), 7)
        for wrapper in found:
            with self.subTest(wrapper=wrapper.name):
                scripts = list(wrapper.glob('*.py'))
                self.assertEqual(len(scripts), 1)
                implementation = module(scripts[0], 'contract_' + wrapper.name.replace('-', '_'))
                contract = (GARS / '02_bioinformatics' / implementation.ASSAY /
                            implementation.SUBSTAGE / 'CONTEXT.md')
                errors = []
                text = contract.read_text()
                lint.check_sections(contract.relative_to(GARS), text, errors)
                lint.check_wait_points(contract.relative_to(GARS), text, errors)
                self.assertEqual(errors, [])
                self.assertTrue((wrapper / 'SKILL.md').is_file())
                for verb in ('check', 'prepare', 'collect'):
                    extra = []
                    if wrapper.name == 'rnaseq-de' and verb in ('check', 'prepare'):
                        extra = ['--counts', 'absent-counts.csv', '--design', 'absent-design.csv']
                    result = run([sys.executable, scripts[0], verb, '--project',
                                  'projects/row3-nonexistent-project'] + extra)
                    self.assertEqual(result.returncode, 3, result.stderr)
                    payload = json.loads(result.stdout.decode())
                    self.assertFalse(payload['ok'])
                    self.assertEqual(payload['command'], verb)
                    self.assertIn('no such project', payload['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
