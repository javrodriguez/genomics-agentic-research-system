"""R-073/R-075/R-096: config binding and execution rendering boundaries."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from support import GARS
import executorlib as ex
import wrapperlib as wl
from tools.execution import config_holds


class ExecutionPolicyTests(unittest.TestCase):
    def test_config_edit_after_prepare(self):
        with tempfile.TemporaryDirectory(prefix='config-hash-') as tmp:
            project=Path(tmp); (project/'_config').mkdir()
            cfg=project/'_config/rnaseq_bulk.yaml'; cfg.write_text('aligner: star\n')
            stage=project/'02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper'
            stage.mkdir(parents=True)
            (stage/'submit.sh').write_text('exit 0\n')
            wl.write_reproducibility(stage,'rnaseq_bulk',project,{'config':cfg},[])
            self.assertIsNone(config_holds(project,stage,'rnaseq_bulk'))
            cfg.write_text('aligner: changed\n')
            self.assertIsNotNone(config_holds(project,stage,'rnaseq_bulk'))
            self.assertIn('changed after prepare',config_holds(project,stage,'rnaseq_bulk'))
            with patch.object(ex,'_local_submit') as submit:
                job,why=ex.submit(project,stage/'submit.sh',descriptor=ex.LOCAL)
                self.assertIsNone(job); self.assertIn('config_sha256',why)
                submit.assert_not_called()

    def test_header_refuses_unquoted_value(self):
        cfg={'compute.partition':'cpu','compute.time':'01:00:00','compute.cpus':'1','compute.mem':'1G'}
        self.assertTrue(ex.header_lines(None,cfg,'p','assay','stage',descriptor=ex.SLURM))
        for key in cfg:
            with self.subTest(key=key):
                bad=dict(cfg);bad[key]='value;echo injected'
                with self.assertRaisesRegex(ValueError,'R-075'):
                    ex.header_lines(None,bad,'p','assay','stage',descriptor=ex.SLURM)

    def test_shell_values_charset_and_quote(self):
        for value in ('/scratch/plain','s3://bucket/work','cpu_long','00:01:00'):
            with patch('tools.execution.shlex.quote', wraps=__import__('shlex').quote) as quote:
                self.assertEqual(wl.shell_value(value,'field'),value)
                quote.assert_called_once_with(value)
        for value in ('has spaces','$(echo x)','x\ny','x;echo','x"y'):
            with self.assertRaises(ValueError): wl.shell_value(value,'field')

    def test_descriptor_cannot_execute_or_export_all(self):
        for key,value in [('submit_argv',['sh','-c','{script}']),
                          ('status_argv',['env']),('directives',['echo injected']),
                          ('directives',['#SBATCH --export=ALL']),
                          ('nextflow_profile','apptainer;echo')]:
            descriptor=dict(ex.SLURM);descriptor[key]=value
            self.assertTrue(ex.validate(descriptor),key)
        argv=ex.submit_argv(ex.SLURM,'submit.sh')
        self.assertTrue(any(a.startswith('--export=PATH,') for a in argv))
        self.assertNotIn('--export=ALL',argv)
        with patch.dict('os.environ', {'SYNTHETIC_SECRET':'canary'}):
            self.assertNotIn('SYNTHETIC_SECRET',ex.execution_env())


if __name__ == '__main__':
    unittest.main(verbosity=2)
