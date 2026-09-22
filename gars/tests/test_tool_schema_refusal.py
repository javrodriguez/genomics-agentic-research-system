"""R-092: schema failures are typed, field-specific, and precede execution."""
import json
import sys
import unittest
from unittest.mock import patch
from support import GARS, run
from tools import policy
import tool_call


class ToolSchemaRefusalTests(unittest.TestCase):
    def test_out_of_vocabulary_field(self):
        with self.assertRaises(policy.Refusal) as ctx:
            policy.validate_args(policy.named('configure.genomes'), {'assay':'invented'})
        self.assertEqual(ctx.exception.field, 'args.assay')

    def test_unknown_field_before_execution(self):
        with patch('tool_call.subprocess.run') as execute:
            self.assertEqual(tool_call.main(['configure.genomes', '{"shell":"bad"}']), 2)
            execute.assert_not_called()

    def test_cli_error_names_field(self):
        p = run([sys.executable, GARS / '_system/tool_call.py', 'configure.genomes',
                 '{"assay":"invented"}'])
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stdout)['field'], 'args.assay')

    def test_required_type_and_unknown_option(self):
        tool = policy.named('stage03_analysis.create')
        for args in ({}, {'project':3, 'slug':'ok'}, {'project':'projects/p','slug':'ok','actor':'human'}):
            with self.subTest(args=args), self.assertRaises(policy.Refusal):
                policy.validate_args(tool, args)
        with self.assertRaises(policy.Refusal):
            policy.parse_argv(['python3','_system/stage00_register.py','assays','--unknown'])

    def test_registry_complete_metadata(self):
        expected = {'name','description','input_schema','output_schema','roles',
                    'timeout_seconds','side_effects','network_required','version'}
        tools = policy.registry()
        self.assertEqual(len({t['name'] for t in tools}), len(tools))
        for tool in tools:
            self.assertTrue(expected.issubset(tool), tool['name'])
        for path in (GARS / '_system/wrappers').glob('*/*.py'):
            for verb in ('check','prepare','collect'):
                self.assertIn(path.stem+'.'+verb, {t['name'] for t in tools})

    def test_real_readonly_positive_control(self):
        p=run([sys.executable,GARS/'_system/tool_call.py','stage00_register.assays','{}'])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)['exit_code'],0)

    def test_paths_cannot_redirect_helper_writes(self):
        for path in ('_system','projects/../_system','../outside'):
            with self.subTest(path=path), self.assertRaises(policy.Refusal):
                policy.validate_args(policy.named('stage03_analysis.create'), {'project':path,'slug':'x'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
