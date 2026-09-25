"""Disposable faults for each decision-0128 session-placement edge, with an unfaulted control."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Label, source bytes, replacement, named acceptance test(s).
FAULTS = [
    ('carrying dropped',
     'start = previous[1]', 'start = None', ['test_honest_carrying']),
    ('blocked edge dropped',
     "        if self.blocked:\n            self.state['folder'] = self.state['kit']",
     '        if False:\n            pass', ['test_blocked_call_edge']),
    ('background edge dropped',
     'if carried and not background:', 'if carried:',
     ['test_background_edge']),
    ('missing-result edge dropped',
     'carries.get(previous[0])', 'carries.get(previous[0], True)', ['test_missing_result_edge']),
    ('result before its call accepted',
     'if use_id in seen:', 'if True:', ['test_missing_result_edge']),
    ('error-result edge dropped',
     "item.get('is_error', False) is not False or", 'False or', ['test_error_result_edge']),
    ('reset notice in result ignored',
     'any(CWD_RESET in text for text in strings(item))', 'False', ['test_reset_notice_edge']),
    ('reset notice in tool_use_result ignored',
     'notice = isinstance(event, dict) and any(', 'notice = False and any(', ['test_reset_notice_edge']),
    ('conditional end carried',
     "if not placed.state['conditional']:", 'if True:',
     ['test_conditional_and_subshell_edges']),
    ('sub-agent chains merged',
     "chain = event.get('parent_tool_use_id') if isinstance(event, dict) else None", 'chain = None',
     ['test_subagent_chains']),
    ('carrying extended to non-Bash tools',
     "else [(text, kit)]", 'else [(text, start or kit)]', ['test_other_tools_stay_at_root']),
    # Round B, rulings 1 and 2.
    # Round C rewrote the dot scan; this entry now restores 0125's scan on it.
    ('old dot scan restored',
     "            if word == '.' and index in command_words:\n",
     "            if word == '.' and (index in command_words or any(\n"
     "                    earlier in ('builtin', 'command', '!', 'time', 'env', 'exec', 'coproc', 'nohup') or\n"
     "                    '=' in earlier for earlier in\n"
     "                    words[1 + max([-1] + [i for i in range(index) if words[i].operator]):index])):\n",
     ['test_dot_operand_ruling', 'test_honest_session_data']),
    # Round C, review 1's F1.
    ('walk-back-to-the-operator dot scan restored',
     "                separator = bool(re.sub(redirection_syntax, '', word))\n"
     "                redirection = re.search('(?:%s)$' % redirection_syntax, word) is not None\n",
     "                separator, redirection = True, False\n",
     ['test_dot_after_redirection']),
    ('ambiguous counted as a hit',
     'ambiguous += 1', 'hits += 1', ['test_honest_session_data']),
    ('ambiguous counted as clean when optimistic is also outside',
     'if pessimistic and optimistic:', 'if False:', ['test_ambiguous_both_ways_outside']),
    ('optimistic placement applied after an error result',
     'optimistic = hopeful if carries.get(use_id) and not background else cautious', 'optimistic = hopeful',
     ['test_ambiguous_within_call']),
    ('optimistic-only outside counted clean',
     'elif optimistic:', 'elif False:', ['test_optimistic_only_outside']),
    ('optimistic carrying dropped',
     'hopeful_start = previous[2]', 'hopeful_start = None', ['test_honest_session_data']),
    ('conditional cd never assumed to run',
     "accepted and not state['optimistic'] and", 'accepted and', ['test_honest_session_data']),
]


class SessionFaultTests(unittest.TestCase):
    def test_session_faults_are_red(self):
        for label, old, new, names in FAULTS:
            with self.subTest(fault=label), tempfile.TemporaryDirectory(prefix='session-fault-') as temp:
                root = Path(temp).resolve()
                target = root / 'evals/review-faults'
                target.parent.mkdir(parents=True)
                shutil.copytree(str(REPO / 'evals/review-faults'), str(target),
                                ignore=shutil.ignore_patterns('__pycache__', 'runs'))
                (root / 'tests/data').mkdir(parents=True)
                for name in ('review_faults_session_calls.jsonl', 'review_faults_session_calls_README.md'):
                    shutil.copyfile(str(REPO / 'tests/data' / name), str(root / 'tests/data' / name))
                test = root / 'tests/test_review_faults_session.py'
                shutil.copyfile(str(REPO / 'tests/test_review_faults_session.py'), str(test))
                source = target / 'run_reviews.py'
                original = source.read_text()
                self.assertEqual(original.count(old), 1, label)
                def execute():
                    result = subprocess.run([sys.executable, str(test)] +
                                            ['SessionPlacementTests.' + name for name in names],
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            timeout=60)
                    return result.returncode, result.stdout.decode('utf-8', 'replace')
                status, output = execute()
                self.assertEqual(status, 0, output)
                source.write_text(original.replace(old, new, 1))
                # Avoid timestamp/size-dependent reuse after an equal-length mutation.
                shutil.rmtree(str(target / '__pycache__'), ignore_errors=True)
                status, output = execute()
                self.assertNotEqual(status, 0, output)
                self.assertIn('FAILED (', output)
                self.assertIn('AssertionError', output)
                self.assertNotIn('ERROR:', output)
                for name in names:
                    self.assertIn('FAIL: ' + name, output)
                print('session fault red: %s -> %s' % (label, ', '.join(names)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
