"""G-model: the model a history entry or a run record names comes from the harness, never the agent.

Claude Code's SessionStart hook input carries the active model id as an optional `model` key
(the public hooks reference; no other hook event carries it). `_system/session_state.sh` passes
that input to the recorder, which writes the id, or `unknown` when the key is absent or off the
guard's MODEL_ID shape, to the workspace's `.gars_session_model`; every history writer reads that
file. `--model` stays accepted so the pinned registry still validates: `none` alone is honoured
(a scripted run, no model-mediated step), and any other value is ignored with a note on stderr
(glitch-b5's rulings Q1-Q3 of Sat 17 Oct 2026, lanes/gars-t74/RULINGS.md).

Every writer here is passed a flag value different from the one the session file records, so a
writer that still reads the flag is told apart from one that reads the harness.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, module, run  # noqa: E402
import guard_hook  # noqa: E402

LEGACY = module(REPO / 'tests/run_tests.py', 'history_model_helpers')
GROUPS = module(GARS / 'tests/test_manifest_groups.py', 'history_model_groups')
FLAG = 'claude-fake-9'
SESSION = 'claude-session-3'
SESSION_FILE = '.gars_session_model'
PLAN = """# Analysis plan: pca-of-samples

Status: DRAFT

## Goal
PCA of the count matrix to check sample clustering.

## Inputs
| Artifact type | Resolved from | Path |
|---|---|---|
| counts_gene | 01_nfcore-rnaseq-wrapper | results/counts.tsv |

## Method
1. Load the matrix; log-transform; PCA via scikit-learn (gars-bio).

## Outputs
| File | Type | Description |
|---|---|---|
| results/pca.csv | table | PC coordinates per sample |
| results/pca.png | figure | scatter of PC1 vs PC2 |

## Execution
Runs: login-node (user-requested)
Seconds; kilobytes.
"""


def start_session(ws, payload):
    """The harness's SessionStart: the real hook, its input JSON on stdin."""
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return run(['bash', ws / '_system/session_state.sh'], cwd=ws, stdin=text)


def claude_start(model=None):
    payload = {'session_id': 'fixture', 'transcript_path': '/dev/null', 'cwd': '.',
               'hook_event_name': 'SessionStart', 'source': 'startup'}
    if model is not None:
        payload['model'] = model
    return payload


def recorded(ws):
    return (Path(ws) / SESSION_FILE).read_text().strip()


def model_lines(text):
    return re.findall(r'^Model: (.*)$', text, re.M)


class RecorderTests(unittest.TestCase):
    """The SessionStart recorder: what the harness reported, or unknown, never a stale value."""

    def setUp(self):
        self.fixture = type('RecorderFixture', (LEGACY.WorkspaceFixture,), {})
        self.fixture.setUpClass()
        self.addCleanup(self.fixture.tearDownClass)
        self.ws = self.fixture.ws

    def test_session_start_records_the_reported_model(self):
        start_session(self.ws, claude_start(SESSION))
        self.assertEqual(recorded(self.ws), SESSION)

    def test_a_start_without_the_field_records_unknown_not_the_earlier_model(self):
        # After /clear or a recovered conversation the field can be omitted (hooks reference).
        start_session(self.ws, claude_start(SESSION))
        start_session(self.ws, claude_start())
        self.assertEqual(recorded(self.ws), 'unknown')

    def test_an_off_shape_or_unreadable_value_records_unknown(self):
        for payload in (claude_start('claude opus; rm -rf x'), claude_start(['claude-x']),
                        '[1, 2]', 'not json'):
            with self.subTest(payload=payload):
                start_session(self.ws, claude_start(SESSION))
                start_session(self.ws, payload)
                self.assertEqual(recorded(self.ws), 'unknown')

    def test_the_render_is_unchanged_by_the_recorder(self):
        with_model = start_session(self.ws, claude_start(SESSION))
        without = start_session(self.ws, '')
        self.assertEqual(with_model.returncode, without.returncode)
        self.assertEqual(with_model.stdout, without.stdout)

    def test_codex_session_start_passes_its_input_through(self):
        result = run([sys.executable, self.ws / '_system/codex_hook.py', 'session-start'],
                     cwd=self.ws, stdin=json.dumps(dict(claude_start('gpt-5.1-codex'),
                                                        turn_id='t1')))
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(recorded(self.ws), 'gpt-5.1-codex')

    def test_the_reader_has_the_guards_model_shape(self):
        import workspace
        self.assertEqual(workspace.MODEL_ID.pattern, guard_hook.MODEL_ID.pattern)
        (self.ws / SESSION_FILE).unlink()  # the suite's fixture records one; start without
        self.assertEqual(workspace.session_model(self.ws), 'unknown')
        (self.ws / SESSION_FILE).write_text('two words\n')
        self.assertEqual(workspace.session_model(self.ws), 'unknown')


class StageWritersTests(unittest.TestCase):
    """Stage 00 finalize, stage 01 and stage 03 verify, on the suite's own workspace chain."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = type('HistoryModelFixture', (LEGACY.WorkspaceFixture,), {})
        cls.fixture.setUpClass()
        f, cls.t = cls.fixture, cls.fixture('test_00_assay_menu_and_selection')
        cls.ws, cls.project = f.ws, f.project
        cls.t.test_01_create_seeds_config()
        code, _, raw = LEGACY.run(f.reg, ['link', '--project', 'projects/tall-test', '--assay',
                                          'rnaseq_bulk', '--source', str(f.src)], f.ws)
        assert code == 0, raw
        start_session(cls.ws, claude_start(SESSION))
        cls.finalize = LEGACY.run(f.reg, ['finalize', '--data-class', 'public', '--purpose',
                                          'fixture', '--project', 'projects/tall-test',
                                          '--model', FLAG], f.ws)
        cls.t.test_04_finalize_preserves_filled_design()
        cls.t.test_05_samplesheet_check_then_write()
        cls.t.test_11_resolver_prefers_native_and_gates_on_status()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDownClass()

    def stage01(self, *extra):
        code, _, raw = LEGACY.run(self.fixture.sheet, ['--project', 'projects/tall-test',
                                                       '--check'], self.ws)
        self.assertEqual(code, 0, raw)
        result = run([sys.executable, self.fixture.sheet, '--project', 'projects/tall-test',
                      '--force'] + list(extra), cwd=self.ws)
        self.assertEqual(result.returncode, 0, result.stdout.decode() + result.stderr.decode())
        return json.loads(result.stdout.decode()), result.stderr.decode()

    def test_stage00_finalize_names_the_session_model(self):
        code, res, raw = self.finalize
        self.assertEqual(code, 0, raw)
        self.assertEqual(res['model'], SESSION)
        history = (self.project / 'HISTORY.md').read_text()
        self.assertEqual(model_lines(history), [SESSION])
        self.assertNotIn(FLAG, history + raw)

    def test_stage01_names_the_session_model_and_notes_the_ignored_flag(self):
        res, err = self.stage01('--model', FLAG)
        self.assertEqual(model_lines(res['history_entry']), [SESSION])
        self.assertNotIn(FLAG, json.dumps(res))
        self.assertIn('--model', err)
        self.assertIn('ignored', err)

    def test_stage01_without_the_flag_says_nothing_on_stderr(self):
        res, err = self.stage01()
        self.assertEqual(model_lines(res['history_entry']), [SESSION])
        self.assertNotIn('--model', err)

    def test_none_alone_is_honoured(self):
        # A scripted replay (scripts/repro_exemplar_run.py) claims less, never more (ruling Q2).
        res, err = self.stage01('--model', 'none')
        self.assertEqual(model_lines(res['history_entry']), ['none'])
        self.assertNotIn('ignored', err)

    def test_stage03_verify_names_the_session_model(self):
        s3 = self.ws / '_system/stage03_analysis.py'
        code, res, raw = LEGACY.run(s3, ['create', '--project', 'projects/tall-test',
                                         '--slug', 'PCA of Samples'], self.ws)
        self.assertEqual(code, 0, raw)
        adir = self.project / '03_custom_analysis' / res['analysis']
        (adir / 'PLAN.md').write_text(PLAN)
        code, res, raw = LEGACY.run(s3, ['approve', '--project', 'projects/tall-test',
                                         '--analysis', adir.name], self.ws)
        self.assertEqual(code, 0, raw)
        script = adir / 'scripts/x.sh'
        script.write_text('set -euo pipefail\nexit 0\n')
        ex = self.ws / '_system/executorlib.py'
        code, submitted, raw = LEGACY.run(ex, ['submit', '--workspace', 'projects/tall-test',
                                               str(script)], self.ws)
        self.assertEqual(code, 0, raw)
        for _ in range(100):
            code, polled, raw = LEGACY.run(ex, ['status', '--workspace', 'projects/tall-test',
                                                submitted['job_id']], self.ws)
            if polled.get('state') == 'COMPLETED':
                break
            time.sleep(.02)
        self.assertEqual(polled.get('state'), 'COMPLETED', raw)
        (adir / 'results/pca.csv').write_text('sample,PC1,PC2\nTUMOR1,1,2\n')
        (adir / 'results/pca.png').write_bytes(b'\x89PNG fake')
        code, res, raw = LEGACY.run(s3, ['verify', '--project', 'projects/tall-test',
                                         '--analysis', adir.name, '--model', FLAG], self.ws)
        self.assertEqual(code, 0, raw)
        self.assertEqual(res['model'], SESSION)
        self.assertEqual(model_lines(res['history_entry']), [SESSION])
        self.assertNotIn(FLAG, raw)


class WrapperCollectTests(unittest.TestCase):
    """One wrapper collect (rnaseq-de): its history entry and the run record it completes."""

    def setUp(self):
        self.g = GROUPS.ManifestGroupsTests('test_model_sentinels_and_known_prefix')
        self.g.setUp()
        self.addCleanup(self.g.doCleanups)
        self.g.prepare(); self.g.fake_run(); self.g.submit()

    def collect(self, *extra):
        g = self.g
        result = run([sys.executable, g.fixture.de, 'collect', '--project', g.project] +
                     list(extra), cwd=g.ws, env=g.env)
        manifest = json.loads(g.manifest_path.read_text())
        return result, manifest

    def test_collect_names_the_session_model_in_history_and_manifest(self):
        start_session(self.g.ws, claude_start(SESSION))
        result, manifest = self.collect('--model', FLAG)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        res = json.loads(result.stdout.decode())
        self.assertEqual(model_lines(res['history_entry']), [SESSION])
        self.assertEqual(manifest['agent_model'], SESSION)
        self.assertEqual([s['model_id'] for s in manifest['model_steps']], [SESSION])
        self.assertNotIn(FLAG, result.stdout.decode() + json.dumps(manifest))
        self.assertIn('ignored', result.stderr.decode())

    def test_a_failed_collect_names_the_session_model_in_the_manifest(self):
        start_session(self.g.ws, claude_start(SESSION))
        os.unlink(str(self.g.stage / 'run/report.md'))
        result, manifest = self.collect('--model', FLAG)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(manifest['predicate_facts']['status'], 'FAILED')
        self.assertEqual(manifest['agent_model'], SESSION)
        self.assertNotIn(FLAG, json.dumps(manifest))

    def test_no_session_file_is_unknown(self):
        path = self.g.ws / SESSION_FILE
        if path.exists():
            path.unlink()
        result, manifest = self.collect('--model', FLAG)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(manifest['agent_model'], 'unknown')
        self.assertEqual(model_lines(json.loads(result.stdout.decode())['history_entry']),
                         ['unknown'])



class AuthoringTests(unittest.TestCase):
    """The authoring road: a wrapper the skill scaffolds, and conform's verdict on one, read the
    harness's model too (glitch-b5's ruling 1 on REVIEW-9eb28d9, lanes/gars-t74/RULINGS.md)."""

    TOOL = GARS / '_system/authoring/create_bioinformatics_skill.py'
    SOURCE = GARS / '_system/wrappers/nfcore-atacseq-wrapper'
    SPEC = {'assay_id': 'demo_assay', 'assay_label': 'Demo assay',
            'wrapper_name': 'demo-wrapper', 'substage': '01_demo-wrapper',
            'pipeline': 'nf-core/demo', 'pipeline_version': '1.0.0',
            'samplesheet_header': ['sample', 'fastq_1', 'fastq_2'],
            'required_config_keys': ['reference.fasta'],
            'artifacts': [{'type': 'counts_gene', 'path': 'run/counts.tsv',
                           'content_gate': True}]}

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.author = module(self.TOOL, 'history_model_author')

    def conform_mutant(self, old, new):
        dest = self.tmp / self.SOURCE.name
        if dest.exists():
            shutil.rmtree(str(dest))
        shutil.copytree(str(self.SOURCE), str(dest))
        target = dest / 'nfcore_atacseq_wrapper.py'
        src = target.read_text(encoding='utf-8')
        self.assertIn(old, src)
        target.write_text(src.replace(old, new), encoding='utf-8')
        result = run([sys.executable, self.TOOL, 'conform', dest])
        return result.returncode, json.loads(result.stdout.decode())

    def test_conform_refuses_a_collect_that_reads_the_flag(self):
        """The reviewer's reproduction: the checklist's reading, with conform green at 9eb28d9."""
        code, payload = self.conform_mutant('ws.history_model(WORKSPACE, args.model)',
                                            'args.model or "unknown"')
        self.assertEqual(code, 1, payload)
        self.assertIn('provenance', [f['check'] for f in payload['failures']])

    def test_conform_refuses_the_flag_on_an_entry_or_manifest_line(self):
        for old, new in (('"Model: %s" % model,', '"Model: %s" % args.model,'),
                         ('wl.complete_manifest(substage, model, "COMPLETE")',
                          'wl.complete_manifest(substage, args.model, "COMPLETE")'),
                         ('wl.collect_failure(substage, result, EXIT_FAILURE, model)',
                          'wl.collect_failure(substage, result, EXIT_FAILURE, args.model)')):
            with self.subTest(line=new):
                code, payload = self.conform_mutant(old, new)
                self.assertEqual(code, 1, payload)
                self.assertIn('provenance', [f['check'] for f in payload['failures']])

    def test_every_shipped_wrapper_still_conforms(self):
        result = run([sys.executable, self.TOOL, 'conform', GARS / '_system/wrappers'])
        self.assertEqual(result.returncode, 0, result.stdout.decode())

    def test_the_scaffold_reads_the_session_model_on_both_paths(self):
        """NIT 2 folded: the generated failure path names the same session model."""
        source = self.author.module_source(self.SPEC)
        read = source.index('model = ws.history_model(WORKSPACE, args.model)')
        failed = source.index('wl.collect_failure(substage, result, EXIT_FAILURE, model)')
        self.assertLess(read, failed)
        collect = source.split('def cmd_collect', 1)[1].split('def main', 1)[0]
        self.assertEqual(collect.count('args.model'), 1, 'collect reads the flag elsewhere')

    def test_the_scaffolded_skill_md_never_passes_the_flag(self):
        text = self.author.skill_md_source(self.SPEC)
        collect = [line for line in text.splitlines() if ' collect ' in line]
        self.assertEqual(len(collect), 1, collect)
        self.assertNotIn('--model', collect[0])


class ContractWordingTests(unittest.TestCase):
    """The contracts and gars/CLAUDE.md never ask an agent to name its own model (ruling Q2)."""

    def test_no_contract_passes_model_and_each_writer_step_says_never(self):
        readers = sorted(GARS.rglob('CONTEXT.md')) + [GARS / 'CLAUDE.md',
                                                      GARS / '_references/contract_standard.md']
        for path in readers:
            if 'projects' in path.relative_to(GARS).parts:
                continue
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=str(path.relative_to(GARS))):
                asked = [w for w in ('--model "', '"model":') if w in text]
                asked += re.findall(r'model id (?:that )?you are running as', text)
                self.assertEqual(asked, [], 'asks the agent for its own model')
                if re.search(r'\b(finalize|verify|collect)\b.*--project', text) or \
                        path.name == 'CLAUDE.md':
                    self.assertTrue(re.search(r'(?i)(never pass|pass no) `--model`', text),
                                    'never says not to pass --model')


if __name__ == '__main__':
    unittest.main()
