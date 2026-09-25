"""Decision 0129 faults: each an in-memory patch of run_reviews.py, with an unfaulted control."""
import sys
import types
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'evals/review-faults'))
sys.path.insert(0, str(REPO / 'tests'))
import test_review_faults_heredoc as heredoc

SOURCE = REPO / 'evals/review-faults/run_reviews.py'
END = ("                    if not placed.state['conditional']:\n"
       "                        end = placed.state['folder']\n"
       "                    hopeful_end = hopeful.state['folder']\n")
# Label, source bytes, replacement, named acceptance test(s).
FAULTS = [
    ('data-only carry dropped',
     "        if self.data_only:\n            self.state['folder'] = carried",
     '        if False:\n            pass',
     ['test_honest_heredoc_sessions', 'test_honest_data_only_carry']),
    ('refused cd in a data-only block keeps the carried placement',
     "destination = target if accepted else state['kit']",
     "destination = target if accepted else (state['folder'] if self.data_only else state['kit'])",
     ['test_refused_cd_in_call', 'test_refused_cd_next_call', 'test_cd_word_in_data_only_call']),
    ('carry applied to every blocked call',
     'self.data_only = self.blocked and not moving', 'self.data_only = self.blocked',
     ['test_shell_moving_in_call']),
    ('shell-moving block end carried to the next call',
     END,
     "                    if not placed.state['conditional']:\n"
     "                        end = start if placed.state.get('moving') else placed.state['folder']\n"
     "                    hopeful_end = hopeful_start if hopeful.state.get('moving') else hopeful.state['folder']\n",
     ['test_shell_moving_next_call']),
    ('data-only block end not carried to the next call',
     END,
     "                    if not placed.state['conditional']:\n"
     "                        end = None if placed.state.get('blocked') else placed.state['folder']\n"
     "                    hopeful_end = None if hopeful.state.get('blocked') else hopeful.state['folder']\n",
     ['test_honest_data_only_carry']),
    ('error edge skipped after a data-only block',
     "item.get('is_error', False) is not False or", 'False or',
     ['test_error_edge_after_data_only']),
]
# Subtests each fault must turn red, beside its named tests.
WITNESSES = {
    'data-only carry dropped': ["session='C01'", "session='C02'"],
    'carry applied to every blocked call': ["block='eval'", "block='pushd'", "block='heredoc-and-eval'"],
    'shell-moving block end carried to the next call': ["block='eval'", "block='pushd'",
                                                        "block='heredoc-and-eval'"],
}


def patched(old, new):
    """run_reviews.py compiled from memory, with one replacement applied."""
    module = types.ModuleType('run_reviews_fault')
    module.__file__ = str(SOURCE)
    code = compile(SOURCE.read_text().replace(old, new, 1), str(SOURCE), 'exec')
    exec(code, module.__dict__)
    return module


def outcome(module, names):
    """Run the named tests with the accessor pointed at the given module."""
    case = type('FaultedHeredocTests', (heredoc.HeredocPlacementTests,), {'harness': module})
    result = unittest.TestResult()
    unittest.TestSuite([case(name) for name in names]).run(result)
    failed = set()
    for test, trace in result.failures:
        failed.add(getattr(test, 'test_case', test)._testMethodName)
        failed.add(test.id())
    return result, failed


class HeredocFaultTests(unittest.TestCase):
    def test_heredoc_faults_are_red(self):
        source = SOURCE.read_text()
        for label, old, new, names in FAULTS:
            with self.subTest(fault=label):
                self.assertEqual(source.count(old), 1, label)
                control, failed = outcome(patched(old, old), names)
                self.assertTrue(control.wasSuccessful(), (control.failures, control.errors))
                faulted, failed = outcome(patched(old, new), names)
                self.assertEqual(faulted.errors, [], label)
                self.assertFalse(faulted.wasSuccessful(), label)
                self.assertEqual(set(names) - failed, set(), label)
                for witness in WITNESSES.get(label, []):
                    self.assertTrue(any(witness in name for name in failed), (label, witness))
                print('heredoc fault red: %s -> %s' % (label, ', '.join(names)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
