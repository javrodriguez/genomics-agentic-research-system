"""R-073/R-075/R-096: config binding and execution rendering boundaries."""
import hashlib
import importlib.util
import argparse
import contextlib
import io
import time
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

    def test_all_ten_direct_collect_gates(self):
        wrappers=list((GARS/'_system/wrappers').glob('*/*.py'))
        checked=0
        for source in wrappers:
            if 'def cmd_collect(args):' not in source.read_text(): continue
            spec=importlib.util.spec_from_file_location(source.stem, str(source))
            module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
            with self.subTest(wrapper=source.stem), tempfile.TemporaryDirectory(prefix='direct-collect-') as tmp:
                project=Path(tmp); (project/'_config').mkdir()
                cfg=project/'_config'/(module.ASSAY+'.yaml'); cfg.write_text('value: original\n')
                substage=project/'02_bioinformatics'/module.ASSAY/module.SUBSTAGE
                substage.mkdir(parents=True)
                (substage/'submit.sh').write_text('#!/bin/bash\nexit 0\n')
                wl.write_reproducibility(substage,module.ASSAY,project,{'config':cfg},[])
                with patch.object(ex, '_submit_once', return_value=('42', None)):
                    self.assertEqual(ex.submit(project, substage/'submit.sh'), ('42', None))
                (substage/'run').mkdir(); (substage/'run/.gars_run_complete').write_text('done\n')
                with patch.object(ex, '_scheduler_status', return_value=('COMPLETED', None)):
                    wl.require_collect_config(project,module.ASSAY,module.SUBSTAGE)
                before = (substage/'STATUS').read_bytes()
                cfg.write_text('value: edited\n')
                output=io.StringIO()
                with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as exit:
                    module.cmd_collect(argparse.Namespace(project=str(project),model='fixture'))
                self.assertEqual(exit.exception.code,2)
                self.assertIn('config_sha256 changed after prepare',output.getvalue())
                self.assertEqual((substage/'STATUS').read_bytes(), before)
                self.assertFalse((substage/'OUTPUTS.tsv').exists())
                checked+=1
        self.assertEqual(checked,10)

    def test_prepared_local_failure_refuses_unclassified_retry(self):
        # R-076/R-077/R-152: a recorded failure cannot be blindly resubmitted.
        from test_lifecycle_executor import prepared
        with tempfile.TemporaryDirectory(prefix='prepared-resume-') as tmp:
            root = Path(tmp)
            stage, sheet, cfg = prepared(root)
            (root / '_config/executor.yaml').write_text('name: local\n')
            body = 'mkdir -p .nextflow; echo first >> effects; exit 17'
            wl.write_submit_sh(stage, root, {}, 'fixture', 'rnaseq_bulk', body)
            wl.write_reproducibility(stage, 'rnaseq_bulk', root,
                                     {'config': cfg, 'samplesheet': sheet}, [])
            job, error = ex.submit(root, stage / 'submit.sh')
            self.assertIsNone(error)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                state, detail = ex.status(root, job)
                if state.startswith('FAILED'):
                    break
                time.sleep(0.02)
            self.assertEqual(state, 'FAILED:EXIT_17', detail)
            again, why = ex.submit(root, stage / 'submit.sh')
            self.assertIsNone(again)
            self.assertIn('R-152', why)
            self.assertEqual((stage / 'run/effects').read_text(), 'first\n')
            self.assertFalse((stage / 'run/.gars_run_complete').exists())

    def test_prepared_content_regressions(self):
        # Reuse the original content assertions with a fixture manifest produced by the
        # real helper. Existing test fixtures stay unchanged; production gates are not mocked.
        source=GARS.parent/'tests/run_tests.py'
        spec=importlib.util.spec_from_file_location('row4_content_fixtures',str(source))
        legacy=importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
        from tools import policy
        collect_tools={Path(t['argv'][1]).stem:t for t in policy.registry() if t['name'].endswith('.collect')}
        real_run=legacy.run
        def prepared_run(script,args,cwd,**kwargs):
            if args and args[0]=='collect' and Path(script).stem in collect_tools:
                tool=collect_tools[Path(script).stem]
                project=Path(cwd)/args[args.index('--project')+1]
                substage=project/'02_bioinformatics'/tool['assay']/tool['substage']
                manifest=substage/'reproducibility/manifest.json'
                if not manifest.exists():
                    substage.mkdir(parents=True,exist_ok=True)
                    cfg=project/'_config'/(tool['assay']+'.yaml')
                    (substage/'submit.sh').write_text('#!/bin/bash\nexit 0\n')
                    wl.write_reproducibility(substage,tool['assay'],project,{'config':cfg},[])
                # Each inherited content case is an independent completed-run fixture.
                # It does not model lifecycle recovery by editing completed outputs.
                if (substage/'STATUS').exists():
                    (substage/'STATUS').unlink()
                for record_path in ex._records(project).glob('*.json'):
                    if json.loads(record_path.read_text()).get('script') == str(substage/'submit.sh'):
                        record_path.unlink()
                legacy.completed_fixture_submission(project, substage)
            return real_run(script,args,cwd,**kwargs)
        cases = {'AtacseqWrapperTests': ['test_04_collect_gates'], 'RnaseqGarsWrapperTests': ['test_02_collect_gates_on_content'], 'ScrnaseqWrapperTests': ['test_05_collect_gates_on_every_sample', 'test_06_the_raw_matrix_is_never_substituted_for_the_filtered_one', 'test_07_empty_combined_matrix_is_refused'], 'SpatialviTests': ['test_04_collect_gates_per_sample_and_never_takes_the_raw_h5ad', 'test_05_a_missing_report_is_refused'], 'ScrnaQcClusterTests': ['test_02_collect_accepts_a_well_formed_run', 'test_03_an_anonymous_gene_is_refused', 'test_04_a_renamed_identifier_column_is_refused', 'test_05_a_sample_with_no_cells_is_refused_and_named', 'test_06_the_nfcore_sample_suffix_is_matched_not_reported_lost', 'test_07_a_label_matching_no_sample_is_refused', 'test_08_zero_cells_or_zero_clusters_are_refused', 'test_09_collect_refuses_before_the_run_finished'], 'SpatialClusterCountTests': ['test_05_collect_refuses_before_the_run_finished', 'test_06_collect_refuses_a_sample_set_that_differs_from_the_samplesheet', 'test_07_collect_refuses_a_table_that_disagrees_with_the_summary', 'test_08_collect_accepts_a_good_run_and_registers_only_table_and_report']}
        # ATAC's class fixture is populated by its earlier stage-00/01 and config tests.
        cases['AtacseqWrapperTests'] = sorted(n for n in dir(legacy.AtacseqWrapperTests)
            if n.startswith('test_00') or n.startswith('test_02_')) + cases['AtacseqWrapperTests']
        suite=unittest.TestSuite(getattr(legacy,cls)(name) for cls,names in cases.items() for name in names)
        output=io.StringIO()
        with patch.object(legacy,'run',side_effect=prepared_run), contextlib.redirect_stdout(output):
            result=unittest.TextTestRunner(stream=output).run(suite)
        self.assertTrue(result.wasSuccessful(),output.getvalue())
        self.assertFalse(result.skipped,output.getvalue())

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
