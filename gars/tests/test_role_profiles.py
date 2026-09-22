"""R-093 role decisions; OS separation remains a deployment prerequisite."""
import os
import unittest
from unittest.mock import patch
from support import GARS
from tools import policy


class RoleProfileTests(unittest.TestCase):
    def test_attack_route_decision_differs(self):
        # Workflow-parameter attack route: producer may enter prepare's validating
        # preflight; reviewer cannot prepare at all. Neither may execute the injected value.
        tool=policy.named('nfcore_atacseq_wrapper.prepare')
        self.assertEqual(policy.decide(tool,'producer'),'allow')
        self.assertEqual(policy.decide(tool,'reviewer'),'refuse')

    def test_approval_is_human_only(self):
        tool=policy.named('stage03_analysis.approve')
        self.assertEqual(policy.decide(tool,'human'),'allow')
        for role in ('producer','reviewer','invented'):
            self.assertEqual(policy.decide(tool,role),'refuse')

    def test_cancel_needs_approval(self):
        self.assertEqual(policy.decide(policy.named('executor.cancel'),'producer'),'needs-approval')

    def test_cancel_declared_refusal_names_row_12(self):
        for role in ('producer','reviewer','human'):
            with self.subTest(role=role), self.assertRaisesRegex(policy.Refusal,'row 12'):
                policy.authorize(policy.named('executor.cancel'),
                                 {'workspace':'projects/p','job-id':'123'},role)

    def test_role_not_environment_or_argument(self):
        with patch.dict(os.environ, {'GARS_ROLE':'human','GARS_ACTOR':'human'}):
            self.assertEqual(policy.launch_role(),'producer')
        with self.assertRaises(policy.Refusal):
            policy.validate_args(policy.named('stage03_analysis.approve'),
                                 {'project':'projects/p','analysis':'01_x','actor':'human'})

    def test_reviewer_only_read_and_status(self):
        for tool in policy.registry():
            if tool['side_effects'] and tool['name'] != 'executor.status':
                self.assertEqual(policy.decide(tool,'reviewer'),'refuse',tool['name'])
        self.assertEqual(policy.decide(policy.named('executor.status'),'reviewer'),'allow')


if __name__ == '__main__':
    unittest.main(verbosity=2)
