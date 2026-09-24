"""Disposable faults for each decision-0125 proof, with an unfaulted control."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Label, source bytes, replacement, named acceptance test(s).
FAULTS = [
    ('placement never moves',
     "destination = target if accepted else state['kit']", "destination = state['kit']",
     ['test_honest_cd_data']),
    ('top-level condition dropped',
     'not self.blocked and top_level and plain and target is not None',
     'not self.blocked and plain and target is not None', ['test_top_level_required']),
    ('resolvability condition dropped',
     "if not argument or argument == '-' or any(",
     "if False and (not argument or argument == '-') or False and any(", ['test_variable_target_reset']),
    ('symlink containment dropped',
     'lexical and within(joined, kit)', 'lexical', ['test_symlink_target_reset']),
    ('all containment dropped',
     'if not (lexical and within(joined, kit)):', 'if False:', ['test_outside_targets_reset']),
    ('placement carried between calls',
     "    state = {'kit': kit, 'folder': kit, 'conditional': False}",
     "    state = getattr(placed_command, 'saved', None)\n"
     "    if state is None or state['kit'] != kit:\n"
     "        state = {'kit': kit, 'folder': kit, 'conditional': False}\n"
     "    placed_command.saved = state", ['test_calls_start_at_root']),
    ('conditional-chain limit dropped',
     "if state['conditional'] and depth == 0 and word.operator", 'if False and word.operator',
     ['test_conditional_chain_limit']),
    ('whole-call conditions dropped',
     "self.blocked = bool(forbidden or broken or parens != 0 or backquote or self.state.get('blocked'))", 'self.blocked = False',
     ['test_whole_call_conditions']),
    ('placement from flattened audit stream',
     '    placement = CommandPlacement(text, words) if isinstance(text, ShellWord) and text.state else None',
     "    if isinstance(text, ShellWord) and text.state:\n"
     "        words = [ShellWord(str(word)) for word, scan_root in audit_words(str(text))]\n"
     '    placement = CommandPlacement(text, words) if isinstance(text, ShellWord) and text.state else None',
     ['test_nested_program_not_flattened']),
    ('deduplication by token alone',
     'tokens = list(dict.fromkeys(decoded))',
     'tokens = list({pair[0]: pair for pair in reversed(decoded)}.values())',
     ['test_deduplicate_by_token_and_folder']),
    ('CDPATH retained',
     "k in ('CDPATH', 'BASH_ENV', 'ENV')", "k in ('BASH_ENV', 'ENV')",
     ['test_environment_startup_variables_removed']),
]


class CdFaultTests(unittest.TestCase):
    def test_placement_faults_are_red(self):
        for label, old, new, names in FAULTS:
            with self.subTest(fault=label), tempfile.TemporaryDirectory(prefix='cd-fault-') as temp:
                root = Path(temp).resolve()
                target = root / 'evals/review-faults'
                target.parent.mkdir(parents=True)
                shutil.copytree(str(REPO / 'evals/review-faults'), str(target),
                                ignore=shutil.ignore_patterns('__pycache__', 'runs'))
                (root / 'tests/data').mkdir(parents=True)
                for name in ('review_faults_cd_calls.jsonl', 'review_faults_cd_calls_README.md'):
                    shutil.copyfile(str(REPO / 'tests/data' / name), str(root / 'tests/data' / name))
                test = root / 'tests/test_review_faults_cd.py'
                shutil.copyfile(str(REPO / 'tests/test_review_faults_cd.py'), str(test))
                source = target / 'run_reviews.py'
                original = source.read_text()
                self.assertIn(old, original, label)
                def execute():
                    result = subprocess.run([sys.executable, str(test)] +
                                            ['CdPlacementTests.' + name for name in names],
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
                if label == 'placement never moves':
                    for call in ('P1-34', 'P1-40', 'P1-47', 'P1-52', 'P1-63'):
                        self.assertIn("call='%s'" % call, output)
                if label == 'top-level condition dropped':
                    for spelling in ('subshell', 'pipeline-left', 'or-left', 'nested-shell'):
                        self.assertIn("spelling='%s'" % spelling, output)
                print('cd fault red: %s -> %s' % (label, ', '.join(names)))
                for line in output.splitlines():
                    if line.startswith('FAIL:'):
                        print('cd witness: ' + line)


if __name__ == '__main__':
    unittest.main(verbosity=2)
