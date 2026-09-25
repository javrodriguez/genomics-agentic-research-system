"""R-060: classification is explicit, immutable on re-finalize, and machine-owned."""
import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from support import GARS, REPO, module, run

legacy = module(REPO/'tests/run_tests.py','dataset_fixture_helpers')


class DataClassRequiredTests(unittest.TestCase):
    def setUp(self):
        self.fixture=type('DatasetFixture',(legacy.WorkspaceFixture,),{})
        self.fixture.setUpClass()
        self.addCleanup(self.fixture.tearDownClass)
        f=self.fixture
        for args in (['create','--title','tall-test','--assays','rnaseq_bulk'],
                     ['link','--project',f.project,'--assay','rnaseq_bulk','--source',f.src]):
            result=run([sys.executable,f.reg]+args,cwd=f.ws)
            self.assertEqual(result.returncode,0,result.stdout.decode()+result.stderr.decode())
        self.dataset=f.project/'00_data/dataset.tsv'

    def finalize(self,flags):
        f=self.fixture
        return run([sys.executable,f.reg,'finalize','--project',f.project]+flags,cwd=f.ws)

    def test_missing_or_unknown_data_class_refused(self):
        for flags in ([],['--data-class','unknown'],['--data-class','TODO']):
            result=self.finalize(flags+['--purpose','fixture'])
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'data_class_required',result.stdout)
            self.assertFalse(self.dataset.exists())

    def test_purpose_and_agreement_ref_required(self):
        for flags,reason in (([],b'purpose_required'),(['--purpose','unknown'],b'purpose_required'),
                             (['--purpose','fixture','--agreement-ref','unknown'],b'agreement_ref_required')):
            result=self.finalize(['--data-class','public']+flags)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(reason,result.stdout)
            self.assertFalse(self.dataset.exists())

    def test_valid_class_writes_read_only_and_refinalize_is_immutable(self):
        flags=['--data-class','public','--purpose','fixture']
        result=self.finalize(flags)
        self.assertEqual(result.returncode,0,result.stdout.decode())
        self.assertEqual(stat.S_IMODE(self.dataset.stat().st_mode),0o444)
        before=(self.dataset.read_bytes(),self.dataset.stat().st_mtime_ns)
        self.assertEqual(self.finalize(flags).returncode,0)
        self.assertEqual(before,(self.dataset.read_bytes(),self.dataset.stat().st_mtime_ns))
        for changed in (['--data-class','identifiable','--purpose','fixture'],
                        flags+['--agreement-ref','agreement-2'],['--data-class','public','--purpose','internal']):
            result=self.finalize(changed)
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'dataset_classification_locked',result.stdout)
            self.assertEqual(before,(self.dataset.read_bytes(),self.dataset.stat().st_mtime_ns))

    def test_guard_dataset_entry_and_sibling_control(self):
        target='projects/tall-test/00_data/dataset.tsv'
        calls=[('Write',{'file_path':target}),('Edit',{'file_path':target})]
        calls += [('Bash',{'command':command}) for command in
                  ('rm '+target,'mv '+target+' projects/tall-test/00_data/moved.tsv',
                   'mv source '+target,'echo x > '+target,'tee '+target)]
        for tool,data in calls:
            with self.subTest(tool=tool,data=data):
                result=run([sys.executable,GARS/'_system/guard_hook.py'],cwd=GARS,
                           stdin=json.dumps({'tool_name':tool,'tool_input':data,'cwd':str(GARS)}),
                           env={'CLAUDE_PROJECT_DIR':str(GARS)})
                self.assertEqual(result.returncode,2,result.stderr.decode())
        result=run([sys.executable,GARS/'_system/guard_hook.py'],cwd=GARS,
                   stdin=json.dumps({'tool_name':'Write','tool_input':{'file_path':'projects/tall-test/00_data/notes.txt'},'cwd':str(GARS)}),
                   env={'CLAUDE_PROJECT_DIR':str(GARS)})
        self.assertEqual(result.returncode,0,result.stderr.decode())
        settings=json.loads((GARS/'.claude/settings.json').read_text())['permissions']['deny']
        for tool in ('Edit','Write'):
            self.assertEqual(settings.count(tool+'(projects/*/00_data/dataset.tsv)'),1)


if __name__=='__main__':
    unittest.main(verbosity=2)
