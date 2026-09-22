"""R-094: every write spelling, repo paths, and resolved outside targets refuse."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from support import GARS, run
import guard_hook

PATHS = ('../.gars-approvals/record.json','_system/guard_hook.py','.claude/settings.json','_references/ceilings.yaml',
         '_references/prompts/reviewer.md','_templates/project/CONTEXT.md',
         '../.githooks/pre-commit','../.github/workflows/ci.yml',
         '../docs/decisions/0042-a-call-the-guard-cannot-judge-is-refused.md',
         'projects/p/03_custom_analysis/01_x/PLAN.md.approved',
         '../tests/fixtures/sealed/item.json','../evals/review-faults/fixtures/item.json',
         'tests/fixtures/injection/manifest.json')
SPELLINGS = ('echo x > {p}','echo x >| {p}','echo x >> {p}','tee {p}',
             'tee -a {p}','sed -i x {p}','cp source {p}','mv source {p}',
             'dd if=source of={p}','ln -sf source {p}','truncate -s 0 {p}',
             'install source {p}','chmod 666 {p}','rm {p}','touch {p}')


class ProtectedPathsTests(unittest.TestCase):
    def call(self, tool, data, root=GARS):
        return run([sys.executable,GARS/'_system/guard_hook.py'],GARS,
                   json.dumps({'tool_name':tool,'tool_input':data,'cwd':str(root)}),
                   {'CLAUDE_PROJECT_DIR':str(root)})

    def test_every_target_every_write_spelling(self):
        for target in PATHS:
            for tool in guard_hook.WRITE_TOOLS:
                with self.subTest(target=target,tool=tool):
                    self.assertEqual(self.call(tool,{'file_path':target}).returncode,2)
            for spelling in SPELLINGS:
                with self.subTest(target=target,spelling=spelling):
                    self.assertEqual(self.call('Bash',{'command':spelling.format(p=target)}).returncode,2)

    def test_resolved_symlink_escape(self):
        with tempfile.TemporaryDirectory(prefix='protected-path-') as tmp:
            root=Path(tmp)/'workspace'; root.mkdir()
            outside=Path(tmp)/'outside'; outside.mkdir()
            (root/'link').symlink_to(outside, target_is_directory=True)
            result=self.call('Write',{'file_path':'link/record'},root)
            self.assertEqual(result.returncode,2)
            self.assertIn(b'outside the workspace',result.stderr)
            self.assertIn(b'Row 15',result.stderr)

    def test_settings_equal_guard_patterns(self):
        settings=json.loads((GARS/'.claude/settings.json').read_text())
        actual={s for s in settings['permissions']['deny'] if s.startswith(('Edit(','Write('))}
        expected={tool+'('+p.replace('repo:','../')+')' for p in guard_hook.READ_ONLY for tool in ('Edit','Write')}
        self.assertEqual(actual,expected)

    def test_approval_store_read_and_symlink_refuse(self):
        with tempfile.TemporaryDirectory(prefix='store-guard-') as tmp:
            root=Path(tmp)/'workspace'; root.mkdir()
            store=Path(tmp)/'.gars-approvals'; store.mkdir(mode=0o700)
            (store/'record.json').write_text('{}')
            (root/'link').symlink_to(store,target_is_directory=True)
            for path in ('../.gars-approvals/record.json','link/record.json'):
                for tool,data in (('Read',{'file_path':path}),('Write',{'file_path':path}),
                                  ('Bash',{'command':'cat '+path})):
                    with self.subTest(path=path,tool=tool):
                        self.assertEqual(self.call(tool,data,root).returncode,2)

    def test_normal_project_edit_positive_control(self):
        self.assertEqual(self.call('Edit',{'file_path':'projects/p/PLAN.md'}).returncode,0)
        for tool in ('Read','Glob','Grep'):
            self.assertEqual(self.call(tool,{'path':'.','pattern':'PLAN'}).returncode,0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
