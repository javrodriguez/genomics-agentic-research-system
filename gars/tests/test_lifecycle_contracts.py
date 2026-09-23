"""Derive stage-02 writer vocabulary from code, including generated wrappers."""
import ast
import re
import unittest
from support import GARS
import executorlib as ex
import wrapperlib as wl


def strings(node):
    constant = getattr(ast, 'Constant', None)
    if constant is not None:
        return [n.value for n in ast.walk(node) if isinstance(n, constant) and isinstance(n.value, str)]
    return [n.s for n in ast.walk(node) if isinstance(n, ast.Str)]


def written_states():
    values = set()
    for path in (GARS / '_system').rglob('*.py'):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, 'attr', getattr(node.func, 'id', '')) == 'write_status':
                if len(node.args) > 1:
                    values.update(strings(node.args[1]))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == '_status_locked':
                values.update(v for v in strings(node) if v in wl.STATUS_STATES or v in ex.STATES or v.startswith('FAILED:'))
        # The authoring generator contains Python source in a template string.
        if path.parent.name == 'authoring':
            for template in strings(tree):
                values.update(re.findall(r'write_status\([^,\n]+,\s*["\']([A-Z_:]+)["\']', template))
    for descriptor in list(ex.BUILTINS.values()) + [ex.parse_descriptor(
            (GARS / '_templates/config/executor.yaml').read_text())]:
        values.update(descriptor['status_map'].values())
    # COMPLETE is the writer's established alias; PENDING is the executor's SUBMITTED.
    return {'FAILED:<reason>' if v == 'FAILED' or v.startswith('FAILED:') else
            ('SUBMITTED' if v == 'PENDING' else wl.STATUS_ALIASES.get(v, v)) for v in values}


class LifecycleContractTests(unittest.TestCase):
    def test_parent_status_paragraph_covers_derived_writer_states(self):
        derived = written_states()
        required = {'SUBMITTED', 'RUNNING', 'VALIDATING', 'ARTIFACT_MISSING', 'STALE',
                    'COMPLETE', 'FAILED:<reason>', 'CANCELLED'}
        self.assertTrue(derived)
        self.assertTrue(required <= derived, derived)
        text = (GARS / '02_bioinformatics/CONTEXT.md').read_text()
        paragraph = text.split('**STATUS file.**', 1)[1].split('\n\n', 1)[0]
        for state in sorted(derived):
            self.assertIn('`' + state + ' ', paragraph, 'contract omits derived state ' + state)

    def test_contract_routes_and_executor_ownership(self):
        parent = (GARS / '02_bioinformatics/CONTEXT.md').read_text()
        for start, end in [('5.', '6.'), ('6.', '7.'), ('7.', '8.'), ('8.', '9.'), ('9.', '10.'),
                           ('**T2', '**T3'), ('**T3', '**T4')]:
            section = parent.split(start, 1)[1].split(end, 1)[0]
            for state in ('VALIDATING', 'ARTIFACT_MISSING', 'STALE'):
                self.assertIn(state, section)
        child = (GARS / '03_custom_analysis/CONTEXT.md').read_text()
        step7 = child.split('7. Execute', 1)[1].split('8.', 1)[0]
        for phrase in ('every script', 'set -euo pipefail', 'local backend', 'Never write `run/`', 'executor launcher'):
            self.assertIn(phrase, ' '.join(step7.split()))
        self.assertNotIn('STATUS records the failure', child)
        self.assertNotIn('or `FAILED <iso8601>`', child)
        self.assertIn('verify alone writes STATUS', child)


if __name__ == '__main__':
    unittest.main(verbosity=2)
