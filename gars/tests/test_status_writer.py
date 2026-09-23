"""R-150/R-151: one atomic, closed lifecycle writer; code owns STATUS."""
import ast
import json
import io
import tokenize
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from support import GARS, run, module
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


def unowned_status_mentions(path):
    """Plain substring sweep: only comments and actual writer calls may name STATUS."""
    tokens = list(tokenize.generate_tokens(io.StringIO(path.read_text()).readline))
    allowed = set()
    for i in range(len(tokens) - 3):
        if [t.string for t in tokens[i:i+4]] != ['wl', '.', 'write_status', '(']:
            continue
        depth = 1
        for j in range(i + 4, len(tokens)):
            token = tokens[j]
            if token.type == tokenize.OP:
                depth += token.string == '('
                depth -= token.string == ')'
            allowed.add(j)
            if depth == 0:
                break
    return [token.start[0] for i, token in enumerate(tokens)
            if 'STATUS' in token.string and token.type != tokenize.COMMENT and i not in allowed]



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
                    if (p / 'STATUS').exists():
                        (p / 'STATUS').unlink()
                    wl.write_status(p, state)
                    wl.write_status(p, 'CANCELLED')
                    self.assertEqual((p / 'STATUS').read_text().split()[0], 'CANCELLED')
                    (p / 'STATUS').unlink()
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
        self.assertGreaterEqual(len(wrappers), 10)
        for p in wrappers:
            self.assertFalse(inline_status_writes(p), p)
            self.assertFalse(unowned_status_mentions(p), p)
            self.assertIn('wl.write_status(substage, "COMPLETE")', p.read_text())
        self.assertFalse(inline_status_writes(GARS / '_system/executorlib.py'))
        print('every wrapper uses the writer')

    def test_stage03_and_generated_wrapper_use_writer(self):
        stage03 = GARS / '_system/stage03_analysis.py'
        self.assertFalse(inline_status_writes(stage03))
        self.assertIn('wl.write_status(adir, "COMPLETE")', stage03.read_text())
        author = module(GARS / '_system/authoring/create_bioinformatics_skill.py', 'row12_author')
        spec = {'assay_id': 'demo_assay', 'assay_label': 'Demo assay',
                'wrapper_name': 'demo-wrapper', 'substage': '01_demo-wrapper',
                'pipeline': 'nf-core/demo', 'pipeline_version': '1.0.0',
                'samplesheet_header': ['sample', 'fastq_1', 'fastq_2'],
                'required_config_keys': ['reference.fasta'],
                'artifacts': [{'type': 'counts_gene', 'path': 'run/counts.tsv', 'content_gate': True}]}
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp) / 'wrapper.py'
            generated.write_text(author.module_source(spec))
            self.assertFalse(inline_status_writes(generated))
            self.assertFalse(unowned_status_mentions(generated))
            self.assertIn('wl.write_status(substage, "COMPLETE")', generated.read_text())
            self.assertIn('wl.collect_failure(substage, result, EXIT_FAILURE)', generated.read_text())

    def test_sweep_detects_alias_and_direct_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'wrapper.py'
            for source in ['(stage / "STATUS").write_text("COMPLETE")',
                           '(stage / "STATUS").open("w")',
                           'target = stage / "STATUS"\nopen(target, "w")',
                           'with ws.atomic_open(stage / "STATUS") as fh:\n    fh.write("COMPLETE")']:
                p.write_text(source)
                self.assertTrue(inline_status_writes(p))

    def test_substring_sweep_detects_review_evasions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wrapper.py'
            for source in ('open(str(substage) + "/STATUS", "w")',
                           'shutil.copyfile(source, str(substage / "STATUS"))',
                           'pathlib.Path("%s/STATUS" % substage).write_text("COMPLETE")',
                           'wl.write_status(stage, "COMPLETE"); open("STATUS", "w")'):
                path.write_text(source)
                self.assertTrue(unowned_status_mentions(path), source)
            path.write_text('# STATUS is code-owned\nwl.write_status(stage, "COMPLETE")\n')
            self.assertFalse(unowned_status_mentions(path))

    def test_terminal_transitions_are_refused(self):
        for terminal in ('COMPLETE', 'CANCELLED', 'FAILED:TIMEOUT', 'REJECTED'):
            with self.subTest(terminal=terminal), tempfile.TemporaryDirectory() as tmp:
                stage = Path(tmp); (stage / 'run').mkdir()
                (stage / 'run/.gars_run_complete').write_text('done\n')
                (stage / 'OUTPUTS.tsv').write_text('# type\trole\tpath\n')
                wl.write_status(stage, terminal)
                before = (stage / 'STATUS').read_bytes()
                for state in ('RUNNING', 'SUBMITTED', 'STALE', 'COMPLETE', 'CANCELLED'):
                    if state == terminal:
                        continue
                    with self.assertRaises(wl.StatusRefusal):
                        wl.write_status(stage, state)
                    self.assertEqual((stage / 'STATUS').read_bytes(), before)
                wl.write_status(stage, terminal)
                self.assertEqual((stage / 'STATUS').read_bytes(), before)

    def test_machine_evidence_and_case_variants_refused(self):
        targets = [
            '.gars_submissions/key.json', '.gars_submissions',
            '.gars_local_jobs/42.json',
            '02_bioinformatics/assay/stage/run/.gars_run_complete',
            '02_bioinformatics/assay/stage/submit.sh.local.exit',
            '02_bioinformatics/assay/stage/reproducibility/manifest.json',
            '02_bioinformatics/assay/stage/submit.sh',
            '02_bioinformatics/assay/stage/params.yaml',
            '02_bioinformatics/assay/stage/status',
            '00_data/assay/FILES.CSV',
            '03_custom_analysis/01_test/plan.MD.approved',
        ]
        for tool in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
            for target in targets:
                with self.subTest(tool=tool, target=target):
                    result = run(['python3', GARS / '_system/guard_hook.py'], cwd=GARS,
                                 env={'CLAUDE_PROJECT_DIR': str(GARS)}, stdin=json.dumps({
                                     'tool_name': tool, 'cwd': str(GARS), 'tool_input': {
                                         'file_path': 'projects/fixture/' + target}}))
                    self.assertEqual(result.returncode, 2, result.stderr)

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
