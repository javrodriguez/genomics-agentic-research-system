"""Producer-visible semantic fault witnesses. These are not sealed evaluation scores."""
import contextlib
import copy
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS, run
from tools import policy, pins
import executorlib as ex
import test_execution_policy
import test_tool_schema_refusal
import test_policy_pins
import test_approval_forgery
import stage03_analysis as stage


class PolicyFaultTests(unittest.TestCase):
    def observed_red(self, case, label):
        output=io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            result=unittest.TextTestRunner(stream=output).run(unittest.TestSuite([case]))
        self.assertFalse(result.wasSuccessful(), 'survived: '+label)
        self.assertTrue(result.failures, 'must fail an assertion, not crash: '+output.getvalue())
        print('red-on-fault: '+label,flush=True)

    def guard_fault(self, old, new, command, label):
        with tempfile.TemporaryDirectory(prefix='guard-fault-') as tmp:
            root=Path(tmp)
            shutil.copytree(str(GARS/'_system'), str(root/'_system'),
                            ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            guard=root/'_system/guard_hook.py'; source=guard.read_text()
            self.assertIn(old,source); guard.write_text(source.replace(old,new,1))
            payload=json.dumps({'tool_name':'Bash','tool_input':{'command':command},'cwd':str(root)})
            result=run([sys.executable,guard],root,payload,{'CLAUDE_PROJECT_DIR':str(root)})
            class Witness(unittest.TestCase):
                def runTest(self): self.assertEqual(result.returncode,2,result.stderr)
            self.observed_red(Witness(),label)

    def test_separator_fault(self):
        self.guard_fault('tokens = simple_tokens(command)',
                         'tokens = simple_tokens(command.split(";")[0])',
                         'python3 _system/stage00_register.py assays; echo injected',
                         'guard allows separator')

    def test_unregistered_helper_fault(self):
        self.guard_fault('command = tool_input.get("command")',
                         'command = tool_input.get("command")\n    if command == "python3 _system/unregistered.py": return',
                         'python3 _system/unregistered.py','guard allows unregistered helper')

    def test_no_verify_equals_fault(self):
        self.guard_fault('command = tool_input.get("command")',
                         'command = tool_input.get("command")\n    if "--no-verify=" in command: return',
                         'git push --no-verify=true','guard allows --no-verify equals')

    def test_schema_vocabulary_fault(self):
        registry=copy.deepcopy(policy.registry())
        for tool in registry:
            if tool['name']=='configure.genomes':
                del tool['input_schema']['properties']['assay']['enum']
        with patch.object(policy,'registry',return_value=registry):
            self.observed_red(test_tool_schema_refusal.ToolSchemaRefusalTests('test_out_of_vocabulary_field'),
                              'schema accepts out-of-vocabulary field')

    def test_config_rehash_fault(self):
        with patch('test_execution_policy.config_holds',return_value=None):
            self.observed_red(test_execution_policy.ExecutionPolicyTests('test_config_edit_after_prepare'),
                              'config edit after prepare is accepted')

    def test_header_quoting_fault(self):
        with patch.object(ex,'shell_value',side_effect=lambda v,k: str(v)):
            self.observed_red(test_execution_policy.ExecutionPolicyTests('test_header_refuses_unquoted_value'),
                              'unquoted value reaches header_lines')

    def test_plan_binding_fault(self):
        with patch.object(stage,'approval_holds',return_value=(True,None)):
            self.observed_red(test_approval_forgery.ApprovalForgeryTests('test_plan_edited_after_approval'),
                              'plan edited after approval is accepted')

    def test_unreviewed_pin_fault(self):
        real=pins.check
        def faulty(root=pins.WORKSPACE):
            return [p for p in real(root) if ': unreviewed' not in p]
        with patch.object(pins,'check',side_effect=faulty):
            self.observed_red(test_policy_pins.PolicyPinsTests('test_unreviewed_altered_missing_and_rejected'),
                              'unreviewed pin is accepted')


if __name__ == '__main__':
    unittest.main(verbosity=2)
