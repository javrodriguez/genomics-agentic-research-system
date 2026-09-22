"""R-150/R-151: one atomic, closed lifecycle writer; code owns STATUS."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from support import GARS, run
import wrapperlib as wl


def inline_status_writes(path):
    """Sweep path expressions (including aliases) that reach a write operation."""
    tree = ast.parse(path.read_text())
    aliases = set()
    def literal(node):
        constant = getattr(ast, 'Constant', None)
        if constant is not None:
            return node.value if isinstance(node, constant) and isinstance(node.value, str) else None
        return node.s if isinstance(node, ast.Str) else None
    def names_status(node):
        return any(literal(n) == 'STATUS' or
                   (isinstance(n, ast.Name) and n.id in aliases) for n in ast.walk(node))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and names_status(node.value):
            aliases.update(n.id for t in node.targets for n in ast.walk(t)
                           if isinstance(n, ast.Name))
    bad = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and names_status(node):
            name = getattr(node.func, 'attr', getattr(node.func, 'id', ''))
            if name in ('atomic_open', 'write_text', 'write_bytes', 'rename', 'replace'):
                bad.append(node.lineno)
            elif name == 'open':
                modes = node.args + [k.value for k in node.keywords if k.arg == 'mode']
                if any(literal(n) and literal(n) != 'STATUS' and
                       any(c in literal(n) for c in 'wax+') for n in modes):
                    bad.append(node.lineno)
    return bad


class StatusWriterTests(unittest.TestCase):
    def test_closed_enum_and_atomic_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            wl.write_status(p, 'RUNNING')
            before = (p / 'STATUS').read_bytes()
            for state, reason in [('MAGIC', None), ('FAILED', 'invented'),
                                  ('RUNNING', 'TIMEOUT'), ('FAILED:EXIT_-1', None)]:
                with self.subTest(state=state, reason=reason):
                    with self.assertRaises(wl.StatusRefusal) as caught:
                        wl.write_status(p, state, reason)
                    self.assertEqual(caught.exception.record()['rule'], 'R-151')
                    self.assertEqual(before, (p / 'STATUS').read_bytes())
            with mock.patch.object(wl.os, 'replace', side_effect=OSError('injected disk error')):
                with self.assertRaises(OSError):
                    wl.write_status(p, 'CANCELLED')
            self.assertEqual(before, (p / 'STATUS').read_bytes())

    def test_all_nonterminal_states_have_cancel_and_failure_edges(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for state in wl.STATUS_STATES:
                if state in wl.TERMINAL_STATES:
                    continue
                with self.subTest(state=state):
                    wl.write_status(p, state)
                    wl.write_status(p, 'CANCELLED')
                    self.assertEqual((p / 'STATUS').read_text().split()[0], 'CANCELLED')
                    wl.write_status(p, state)
                    wl.write_status(p, 'FAILED', 'TIMEOUT')
                    self.assertEqual((p / 'STATUS').read_text().split()[0], 'FAILED:TIMEOUT')

    def test_complete_requires_marker_and_collected_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            for state in ('COMPLETE', 'COMPLETED'):
                with self.assertRaises(wl.StatusRefusal):
                    wl.write_status(p, state)
            (p / 'run').mkdir()
            (p / 'run/.gars_run_complete').write_text('done\n')
            with self.assertRaises(wl.StatusRefusal):
                wl.write_status(p, 'COMPLETE')
            (p / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
            wl.write_status(p, 'COMPLETED')
            self.assertEqual((p / 'STATUS').read_text().split()[0], 'COMPLETE')

    def test_every_wrapper_uses_writer(self):
        wrappers = sorted((GARS / '_system/wrappers').glob('*/*.py'))
        self.assertEqual(len(wrappers), 10)
        for p in wrappers:
            self.assertFalse(inline_status_writes(p), p)
            self.assertIn('wl.write_status(substage, "COMPLETE")', p.read_text())
        self.assertFalse(inline_status_writes(GARS / '_system/executorlib.py'))
        print('every wrapper uses the writer')

    def test_sweep_detects_alias_and_direct_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'wrapper.py'
            for source in ['(stage / "STATUS").write_text("COMPLETE")',
                           '(stage / "STATUS").open("w")',
                           'target = stage / "STATUS"\nopen(target, "w")',
                           'with ws.atomic_open(stage / "STATUS") as fh:\n    fh.write("COMPLETE")']:
                p.write_text(source)
                self.assertTrue(inline_status_writes(p))

    def test_agent_status_write_refused(self):
        for tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
            result = run(['python3', GARS / '_system/guard_hook.py'], cwd=GARS,
                         env={'CLAUDE_PROJECT_DIR': str(GARS)}, stdin=json.dumps({
                             'tool_name': tool, 'cwd': str(GARS), 'tool_input': {
                                 'file_path': 'projects/fixture/02_bioinformatics/assay/stage/STATUS'}}))
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn(b'executorlib.py status', result.stderr)
            self.assertIn(b'R-151', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
