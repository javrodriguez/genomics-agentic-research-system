"""Row 6: real wrapper verbs and executor records, synthetic execution evidence only."""
import ast
import copy
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import GARS, REPO, module, run
if not (GARS / "_system/manifest_check.py").is_file():
    raise ImportError("missing gars/_system/manifest_check.py (Row 6 instrument)")
import manifest_check as mc

LEGACY = module(REPO / 'tests/run_tests.py', 'manifest_fixture_helpers')
MODEL = 'claude-opus-5-5'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(argv, cwd=REPO, env=None):
    result = run(argv, cwd=cwd, env=env)
    if result.returncode:
        raise AssertionError(result.stdout.decode() + result.stderr.decode())
    return result.stdout.decode().strip()


class ManifestGroupsTests(unittest.TestCase):
    def setUp(self):
        # Reuse the suite's native-counts and design fixture, never a production checkout.
        self.fixture = type('ManifestRNAFixture', (LEGACY.RnaseqGarsWrapperTests,), {})
        self.fixture.setUpClass()
        self.addCleanup(self.fixture.tearDownClass)
        f = self.fixture
        self.ws, self.project, self.stage = f.ws, f.project, f.de_substage
        # Optional venue fixture patches the constant in both interpreter copies.
        if hasattr(self, 'marker_present'):
            import executorlib as ex
            marker = f.tmp / 'operator-marker'
            if self.marker_present:
                marker.touch()
            marker_patch = patch.object(ex, 'HOMELAB_MARKER', str(marker))
            marker_patch.start(); self.addCleanup(marker_patch.stop)
            copied = self.ws / '_system/executorlib.py'
            copied.write_text(copied.read_text() +
                "\nHOMELAB_MARKER = str(Path(__file__).resolve().parents[2] / 'operator-marker')\n")
        config = self.project / '_config/rnaseq_bulk.yaml'
        config.write_text(config.read_text().replace('mem: 32G', 'mem: 2G'))
        for directory in ('00_initialize_project', '02_bioinformatics'):
            shutil.copytree(str(GARS / directory), str(f.ws / directory))
        for name in ('HISTORY.md', 'CONTEXT.md'):
            shutil.copyfile(str(f.ws / '_templates/project' / name), str(f.project / name))
        raw = f.project / '00_data/rnaseq_bulk/raw'
        raw.mkdir(parents=True)
        for sample in range(1,5):
            for read in (1,2):
                name = 'S%d_S%d_L001_R%d_001.fastq.gz' % (sample,sample,read)
                source = f.tmp / name
                shutil.copyfile(str(f.tmp / 'reads.fastq.gz'), str(source))
                (raw / name).symlink_to(source)
        checked([sys.executable,f.ws / '_system/stage00_register.py','finalize','--project',f.project,
                 '--data-class','public','--purpose','fixture','--model',MODEL], cwd=f.ws)
        registry = f.ws / '_references/genomes.md'
        registry.write_text('| ID | Species | Build | Source | FASTA | GTF |\n|---|---|---|---|---|---|\n'
            '| FIXTURE | synthetic | fixture-build | fixture | %s | %s |\n\n'
            '| ID | Annotation release | fasta_sha256 | gtf_sha256 |\n|---|---|---|---|\n'
            '| FIXTURE | fixture-release | %s | %s |\n' %
            (f.refs / 'genome.fa.gz', f.refs / 'genome.gtf.gz',
             sha(f.refs / 'genome.fa.gz'), sha(f.refs / 'genome.gtf.gz')))
        self.repo = f.tmp
        (self.repo / '.gitignore').write_text('__pycache__/\n')
        checked(['git','init','-q',self.repo])
        checked(['git','-C',self.repo,'add','gars'])
        checked(['git','-C',self.repo,'-c','user.name=fixture','-c','user.email=fixture@example.invalid',
                 'commit','-qm','synthetic GARS checkout'])
        self.env = {'PYTHONDONTWRITEBYTECODE':'1'}
        (self.project / '01_samplesheets/rnaseq_bulk_design_check.json').write_text('{"fixture":true}\n')

    def prepare(self, backend='local'):
        (self.project / '_config/executor.yaml').write_text('name: %s\n' % backend)
        f = self.fixture
        checked([sys.executable,f.de,'prepare','--project',self.project,
                 '--counts',f.counts_native,'--design',self.project / '01_samplesheets/rnaseq_bulk_design.csv'],
                cwd=self.ws,env=self.env)
        self.manifest_path = self.stage / 'reproducibility/manifest.json'
        self.prepared = json.loads(self.manifest_path.read_text())
        return self.prepared

    def fake_run(self):
        # Same artifacts as RnaseqGarsWrapperTests.test_04_de_prepare_and_collect.
        # One tested gene, so BH(pvalue) == pvalue: padj must equal it or collect's
        # BH gate (row 8 step A, rule 8) refuses the table as uncorrected_pvalues.
        files = {'run/tables/de_results.csv':'gene,baseMean,log2FoldChange,pvalue,padj\ng1,1,2,0.1,0.1\n',
                 'run/tables/normalized_counts.csv':'gene,S1,S2,S3,S4\ng1,1,2,3,4\n',
                 'run/report.md':'# fixture report\n',
                 'adapted/counts_gene.tsv':'gene\tS1\ng\t1\n',
                 'adapted/gene_id_to_name.tsv':'gene_id\tgene_name\ng\tG\n',
                 'run/versions.json':json.dumps({'python':'3.9.0','pandas':'fixture-1'}),
                 'run/.gars_run_complete':'fixture\n'}
        files.update({'run/figures/'+name:'fixture png' for name in ('pca.png','volcano.png','ma_plot.png')})
        for name,contents in files.items():
            path = self.stage / name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(contents)

    def submit(self):
        # Mirror completed_fixture_submission: real submit, synthetic job completion.
        code = '''import json,sys,time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,sys.argv[1])
import executorlib as ex
root,stage=Path(sys.argv[2]),Path(sys.argv[3])
with patch.object(ex,'_submit_once',return_value=('4242',None)):
    job,error=ex.submit(root,stage/'submit.sh')
assert job=='4242',error
jobs=ex._local_jobs_dir(root);jobs.mkdir(exist_ok=True)
exit_file=stage/'fixture.exit';exit_file.write_text('0\\n')
(jobs/'4242.json').write_text(json.dumps({'script':str(stage/'submit.sh'),'exit_file':str(exit_file),'started_at':time.time()-1}))
'''
        checked([sys.executable,'-c',code,self.ws / '_system',self.project,self.stage],cwd=self.ws,env=self.env)

    def collect(self, model=MODEL, expected=0):
        result = run([sys.executable,self.fixture.de,'collect','--project',self.project,'--model',model],
                     cwd=self.ws,env=self.env)
        self.assertEqual(result.returncode,expected,result.stdout.decode()+result.stderr.decode())
        manifest = json.loads(self.manifest_path.read_text())
        for key,value in self.prepared.items():
            self.assertEqual(manifest[key],value,'prepare key changed: '+key)
        self.assertEqual(manifest['predicate_facts']['status'],(self.stage / 'STATUS').read_text().split()[0])
        return manifest

    def test_rnaseq_de_cold_start_and_idempotent_collect(self):
        self.prepare(); self.fake_run(); self.submit()
        manifest = self.collect()
        report = checked([sys.executable,self.ws / '_system/manifest_check.py',self.manifest_path],cwd=self.ws)
        self.assertTrue(mc.grade(manifest)['ok'],report)
        print(report)
        grade = mc.grade(manifest)
        before = self.manifest_path.read_bytes()
        self.collect()
        self.assertEqual(before,self.manifest_path.read_bytes())
        self.assertEqual(self.prepared['random_seeds'][0]['seed'],0)
        tree = ast.parse((self.stage / 'scripts/run_de.py').read_text())
        calls = [n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='PCA']
        self.assertEqual(len(calls),1)
        self.assertTrue(any(k.arg=='random_state' and isinstance(k.value,ast.Name) and k.value.id=='RANDOM_SEED' for k in calls[0].keywords))
        self.assertIn('RANDOM_SEED = 0',(self.stage / 'scripts/run_de.py').read_text())

    def test_design_check_missing_cannot_shrink_denominator(self):
        check = self.project / '01_samplesheets/rnaseq_bulk_design_check.json'
        check.unlink()
        self.prepare(); self.fake_run(); self.submit()
        manifest = self.collect()
        grade = mc.grade(manifest)
        self.assertTrue(manifest['predicate_facts']['design_record'])
        self.assertTrue(grade['groups'][13]['applicable'])
        self.assertFalse(grade['groups'][13]['present'])
        self.assertFalse(grade['ok'])
        check.write_text('{"fixture":true}\n')
        complete = self.collect()
        self.assertTrue(mc.grade(complete)['ok'])
        self.assertEqual(mc.grade(complete)['applicable'], grade['applicable'])
        check.unlink()
        self.assertFalse(mc.grade(self.collect())['ok'])

    def test_failure_collect_preserves_prepare_facts(self):
        self.prepare(); self.fake_run(); self.submit()
        (self.stage / 'run/tables/de_results.csv').write_text('gene,padj\n,0.2\n')
        manifest = self.collect(expected=1)
        self.assertEqual(manifest['failure_class'],'workflow')
        self.assertEqual(manifest['predicate_facts']['status'],'FAILED')

    def pipeline_fixtures(self):
        import workspace
        root = self.fixture.tmp / 'pipelines'
        root.mkdir()
        self.spatial_pin = None
        for assay,key in workspace.PIPELINES.items():
            path = root / key.replace('nf-core-','')
            path.mkdir()
            (path / 'main.nf').write_text('// synthetic checkout; never executed\n')
            (path / 'assets').mkdir()
            (path / 'assets/protocols.json').write_text(json.dumps({'simpleaf':{'10XV3':{}}}))
            checked(['git','init','-q',path])
            checked(['git','-C',path,'add','main.nf','assets/protocols.json'])
            checked(['git','-C',path,'-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-qm','synthetic pipeline'])
            if assay == 'spatialvi':
                self.spatial_pin = checked(['git','-C',path,'rev-parse','HEAD'])[:7]
                path.rename(root / ('spatialvi-'+self.spatial_pin))
            else:
                checked(['git','-C',path,'tag',key.rsplit('-',1)[-1]])
        print('SYNTHETIC PINS '+json.dumps(dict(workspace.PIPELINES, spatialvi='nf-core-spatialvi-'+self.spatial_pin),sort_keys=True))
        self.env['GARS_PIPELINES'] = str(root)
        self.env['PATH'] = str(GARS / 'tests/fixtures/manifest') + os.pathsep + os.environ['PATH']
        stubs = self.fixture.tmp / 'imports'
        stubs.mkdir()
        for name in ('scanpy','anndata','leidenalg','sklearn','matplotlib','pandas','numpy'):
            (stubs / (name+'.py')).write_text('# import-name fixture; analysis is not executed\n')
        self.env.update(GARS_PY=sys.executable,PYTHONPATH=str(stubs))

    def wrapper_argv(self, verb, extra=()):
        launcher = ('import sys,runpy;sys.path.insert(0,sys.argv.pop(1));import workspace;'
                    'workspace.PIPELINES["spatialvi"]="nf-core-spatialvi-"+sys.argv.pop(1);'
                    'sys.argv=sys.argv[1:];runpy.run_path(sys.argv[0],run_name="__main__")')
        return [sys.executable,'-c',launcher,self.ws / '_system',self.spatial_pin,
                self.wrapper,verb,'--project',self.project]+list(extra)

    def configure_wrapper(self, key, backend, base):
        info = mc.load_schema()['wrappers'][key]
        assay,name = info['assay'],info['name']
        self.project = self.ws / 'projects' / (name+'-'+backend)
        shutil.copytree(str(base),str(self.project),symlinks=True)
        self.stage = self.project / '02_bioinformatics' / assay / info['substage']
        self.wrapper = self.ws / '_system/wrappers' / name / (name.replace('-','_')+'.py')
        self.fixture.de = self.wrapper
        self.assay,self.name,self.info = assay,name,info
        (self.project / '_config/executor.yaml').write_text('name: %s\n' % backend)
        shutil.copyfile(str(self.ws / '_templates/config/nextflow.slurm.config'),str(self.project / '_config/nextflow.slurm.config'))
        fasta,gtf = self.fixture.refs / 'genome.fa.gz',self.fixture.refs / 'genome.gtf.gz'
        values = {'unit_of_replication':'sample','reference_release':'fixture-release','reference.fasta':str(fasta),'reference.gtf':str(gtf),
                  'reference.mito_name':'MT','peaks.type':'narrow','peaks.macs_gsize':'12345',
                  'de.formula':'"~ condition"','de.contrast':'"condition,MT,WT"',
                  'compute.partition':'fixture','compute.time':'"1:00:00"','compute.cpus':'4',
                  'compute.mem':'4G','compute.work_dir':str(self.fixture.tmp / 'work'),
                  'protocol':'10XV3','spikein.fasta':str(fasta),'spikein.bowtie2':str(self.fixture.refs / 'bt2')}
        (self.fixture.refs / 'bt2').mkdir(exist_ok=True)
        (self.fixture.refs / 'bt2/genome.1.bt2').write_text('fixture')
        template = (self.ws / '_templates/config' / (assay+'.yaml')).read_text()
        lines,section = [],''
        for line in template.splitlines():
            if line.strip() and not line.lstrip().startswith('#') and ':' in line:
                field,value = line.strip().split(':',1)
                if not line.startswith(' '):
                    section = field if not value.strip() else ''
                full = section+'.'+field if line.startswith(' ') else field
                if full in values:
                    line = ('  ' if line.startswith(' ') else '') + field+': '+values[full]
            lines.append(line)
        (self.project / '_config' / (assay+'.yaml')).write_text('\n'.join(lines)+'\n')
        design = self.project / '01_samplesheets' / (assay+'_design.csv')
        if not design.exists():
            shutil.copyfile(str(base / '01_samplesheets/rnaseq_bulk_design.csv'),str(design))
        (self.project / '01_samplesheets' / (assay+'_design_check.json')).write_text('{"fixture":true}\n')
        fq = str(self.fixture.tmp / 'reads.fastq.gz')
        headings = {'rnaseq_bulk':'sample,fastq_1,fastq_2,strandedness',
                    'atacseq_bulk':'sample,fastq_1,fastq_2,replicate',
                    'chipseq_bulk':'sample,fastq_1,fastq_2,replicate,antibody,control,control_replicate',
                    'cutandrun':'group,replicate,fastq_1,fastq_2,control',
                    'methylseq':'sample,fastq_1,fastq_2','scrnaseq':'sample,fastq_1,fastq_2',
                    'spatialvi':'sample,spaceranger_dir'}
        rows = [headings[assay]]
        for n in range(1,5):
            sample = 'S%d' % n
            if assay=='spatialvi':
                raw = self.fixture.tmp / ('spatial-'+sample)
                raw.mkdir(exist_ok=True); (raw / 'filtered_feature_bc_matrix.h5').write_text('fixture')
                rows.append(sample+','+str(raw))
            elif assay=='cutandrun': rows.append('%s,1,%s,%s,%s' % (sample,fq,fq,'S4' if n<4 else ''))
            else:
                row = '%s,%s,%s' % (sample,fq,fq)
                if assay=='rnaseq_bulk': row+=',auto'
                if assay in ('atacseq_bulk','chipseq_bulk'): row+=',1'
                if assay=='chipseq_bulk': row+=',H3K27ac,S4,1' if n<4 else ',,,'
                rows.append(row)
        (self.project / '01_samplesheets' / (assay+'_samplesheet.csv')).write_text('\n'.join(rows)+'\n')
        extra=[]
        if name=='rnaseq-de': extra=['--counts',self.fixture.counts_native,'--design',design]
        elif name in ('scrna-qc-cluster','spatial-cluster-count'):
            h5ad = self.project / 'input.h5ad'; h5ad.write_text('fixture matrix')
            if name=='spatial-cluster-count':
                h5ad = self.project / 'input-matrices'; h5ad.mkdir()
                for n in range(1,5):
                    path=h5ad / ('S%d/data/S%d.h5ad' % (n,n));path.parent.mkdir(parents=True);path.write_text('fixture')
            extra=['--h5ad',h5ad]
        self.prepare_extra = extra
        checked(self.wrapper_argv('prepare',extra),cwd=self.ws,env=self.env)
        self.manifest_path=self.stage / 'reproducibility/manifest.json'
        self.prepared=json.loads(self.manifest_path.read_text())
        if info['kind']=='local':
            scripts=list((self.stage/'scripts').glob('*.py'))
            self.assertEqual(len(scripts),1)
            script=scripts[0].read_text();tree=ast.parse(script)
            self.assertIn('versions.json',script)
            recorded=self.prepared['random_seeds']
            if isinstance(recorded,list):
                self.assertIn('RANDOM_SEED = 0',script)
                calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
                for fact in recorded:
                    name=fact['call'].rsplit('.',1)[-1]
                    def qualified(node):
                        if isinstance(node,ast.Name): return node.id
                        if isinstance(node,ast.Attribute): return qualified(node.value)+'.'+node.attr
                        return ''
                    expected=fact['call'].replace('scanpy.','sc.')
                    matching=[n for n in calls if qualified(n.func)==expected or
                              (not expected.startswith('sc.') and qualified(n.func).rsplit('.',1)[-1]==name)]
                    self.assertTrue(matching,fact)
                    if 'seed' in fact:
                        self.assertEqual(fact['seed'],0)
                        for call in matching:
                            self.assertTrue(any(k.arg=='random_state' and isinstance(k.value,ast.Name) and
                                                k.value.id=='RANDOM_SEED' for k in call.keywords),fact)

    def fake_wrapper_run(self):
        if self.name=='rnaseq-de':
            self.fake_run(); return
        files={'run/.gars_run_complete':'fixture\n'}
        if self.assay in ('atacseq_bulk','chipseq_bulk'):
            macs='macs2' if self.assay=='atacseq_bulk' else 'macs3'
            ml='run/results/bwa/merged_library/'
            peaks=ml+macs+'/narrow_peak/'
            consensus=peaks+'consensus/'+('H3K27ac/' if self.assay=='chipseq_bulk' else '')
            files.update({peaks+'S1.narrowPeak':'chr1\t1\t2\n',consensus+'peaks.bed':'chr1\t1\t2\n',
                consensus+'counts.featureCounts.txt':'Geneid\tS1_REP1\tS2_REP1\tS3_REP1\tS4_REP1\ng1\t1\t2\t3\t4\n',
                ml+'bigwig/S1.bigWig':'fixture',ml+'S1.sorted.bam':'fixture',
                'run/results/multiqc/narrow_peak/multiqc_report.html':'<html>fixture</html>'})
        elif self.assay=='rnaseq_bulk':
            base='run/results/star_salmon/'
            files.update({base+'salmon.merged.gene_counts_length_scaled.tsv':self.fixture.counts_native.read_text(),
                base+'salmon.merged.transcript_counts.tsv':'tx\n',base+'salmon.merged.gene_tpm.tsv':'tpm\n',
                base+'S1.markdup.sorted.bam':'fixture','run/results/multiqc/star_salmon/multiqc_report.html':'<html>fixture</html>'})
        elif self.assay=='cutandrun':
            for rel in ('02_alignment/bowtie2/target/markdup/S1.bam','03_peak_calling/03_bed_to_bigwig/S1.bigWig',
                        '03_peak_calling/04_called_peaks/S1-S2-S3.bed','03_peak_calling/05_consensus_peaks/peaks.bed',
                        '04_reporting/multiqc/multiqc_report.html'): files['run/results/'+rel]='fixture'
        elif self.assay=='methylseq':
            for rel in ['bismark/methylation_coverage/S%d.cov.gz'%n for n in range(1,5)]+[
                    'bismark/methylation_calls/calls.txt','bismark/bedGraph/S1.bedGraph','multiqc/multiqc_report.html']:
                files['run/results/'+rel]='fixture'
        elif self.name=='nfcore-scrnaseq-wrapper':
            for n in range(1,5): files['run/results/simpleaf/mtx_conversions/S%d/matrix.h5ad'%n]='fixture'
            files['run/results/simpleaf/mtx_conversions/combined_filtered_matrix.h5ad']='fixture'
            files['run/results/multiqc/multiqc_report.html']='<html>fixture</html>'
        elif self.name=='nfcore-spatialvi-wrapper':
            files['run/results/multiqc/multiqc_report.html']='<html>fixture</html>'
            for n in range(1,5):
                files['run/results/S%d/data/S%d.h5ad'%(n,n)]='fixture'
                files['run/results/S%d/reports/report-S%d.html'%(n,n)]='<html>fixture</html>'
        elif self.name=='scrna-qc-cluster':
            files.update({'run/tables/cluster_markers.csv':'gene,cluster,pvals_adj\nG1,0,0.01\n',
                'run/summary.json':json.dumps({'n_cells_out':40,'n_clusters':2,'cells_after_qc':{'S%d_filtered'%n:10 for n in range(1,5)}}),
                'run/data/processed.h5ad':'fixture','run/figures/umap_clusters.png':'fixture',
                'run/figures/violin_qc.png':'fixture','run/report.md':'# fixture'})
        elif self.name=='spatial-cluster-count':
            files.update({'run/summary.json':json.dumps({'obs_column':'clusters','samples':{'S%d'%n:{'n_obs':10,'n_clusters':1} for n in range(1,5)}}),
                'run/clusters.tsv':'sample\tcluster\tn_spots\n'+''.join('S%d\t0\t10\n'%n for n in range(1,5)),
                'run/report.md':'# fixture'})
        for rel,contents in files.items():
            p=self.stage / rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(contents)
        if self.info['kind']=='nextflow':
            evidence=self.stage / 'run/pipeline_info'; evidence.mkdir(parents=True,exist_ok=True)
            fixture=GARS / 'tests/fixtures/manifest'
            # Whole-run positive fixtures use both immutable forms; mutable is a negative below.
            (evidence/'gars_trace.txt').write_text('\n'.join((fixture/'trace.txt').read_text().splitlines()[:3])+'\n')
            shutil.copyfile(str(fixture/'fixture.sif'),str(evidence/'fixture.sif'))
            versions=self.stage/'run/results/pipeline_info';versions.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(str(fixture/'software_versions.yml'),str(versions/'software_versions.yml'))
        else:
            (self.stage/'run/versions.json').write_text(json.dumps({'python':'3.9.0','fixture-package':'1.0'}))

    def test_all_ten_wrappers_both_backends(self):
        self.pipeline_fixtures()
        base=self.project
        schema=mc.load_schema()
        self.assertEqual(len(schema['wrappers']),10)
        for key,info in sorted(schema['wrappers'].items()):
            for backend in ('local','slurm'):
                with self.subTest(wrapper=info['name'],backend=backend):
                    self.configure_wrapper(key,backend,base)
                    self.fake_wrapper_run();self.submit()
                    result=run(self.wrapper_argv('collect',['--model',MODEL]),cwd=self.ws,env=self.env)
                    self.assertEqual(result.returncode,0,result.stdout.decode()+result.stderr.decode())
                    manifest=json.loads(self.manifest_path.read_text())
                    self.assertEqual({k:manifest[k] for k in self.prepared},self.prepared)
                    self.assertEqual(manifest['predicate_facts']['status'],(self.stage/'STATUS').read_text().split()[0])
                    report=checked([sys.executable,self.ws/'_system/manifest_check.py',self.manifest_path],cwd=self.ws)
                    grade=mc.grade(manifest);self.assertTrue(grade['ok'],report)
                    self.assertGreater(grade['applicable'],0)
                    print(report)
                    print('EXIT manifest completeness %s %s: %d/%d'%(info['name'],backend,grade['present'],grade['applicable']))
                    before=self.manifest_path.read_bytes()
                    checked(self.wrapper_argv('collect',['--model',MODEL]),cwd=self.ws,env=self.env)
                    self.assertEqual(before,self.manifest_path.read_bytes())
                    self.assert_outputs(manifest)
                    if key == 'scrna-qc-cluster':
                        self.assertIn('samplesheet', manifest['inputs'])
                    for label, source in manifest['inputs'].items():
                        self.assertEqual(manifest[label + '_sha256'], sha(source))
                        self.assertEqual(manifest['input_data_location'][label], source)
                        broken = copy.deepcopy(manifest)
                        del broken[label + '_sha256']
                        self.assertFalse(mc.grade(broken)['groups'][0]['present'], label)

    def test_all_ten_failure_collects_both_backends(self):
        self.pipeline_fixtures()
        base = self.project
        wrappers = mc.load_schema()['wrappers']
        self.assertEqual(len(wrappers), 10)
        for key, info in sorted(wrappers.items()):
            for backend in ('local', 'slurm'):
                with self.subTest(wrapper=info['name'], backend=backend):
                    self.configure_wrapper(key, backend, base)
                    self.fake_wrapper_run(); self.submit()
                    # Keep the completion marker and scheduler evidence, but remove
                    # required scientific output so the real artifact gate fails.
                    target = ('run/results' if info['kind'] == 'nextflow' else
                              'run/clusters.tsv' if key == 'spatial-cluster-count' else
                              'run/tables')
                    missing = self.stage / target
                    if missing.is_dir():
                        shutil.rmtree(str(missing))
                    else:
                        missing.unlink()
                    result = run(self.wrapper_argv('collect', ['--model', MODEL]),
                                 cwd=self.ws, env=self.env)
                    self.assertEqual(result.returncode, 1,
                                     result.stdout.decode() + result.stderr.decode())
                    self.assertTrue(json.loads(result.stdout.decode())['failures'])
                    manifest = json.loads(self.manifest_path.read_text())
                    self.assertEqual({k: manifest[k] for k in self.prepared}, self.prepared)
                    self.assertEqual((self.stage / 'STATUS').read_text().split()[0], 'FAILED')
                    self.assertIn('predicate_facts', manifest, 'failure completion omitted')
                    self.assertIn('failure_class', manifest, 'group 15 omitted')
                    self.assertEqual(manifest['predicate_facts']['status'], 'FAILED')
                    self.assertEqual(manifest['failure_class'], 'workflow')
                    group = mc.grade(manifest)['groups'][14]
                    self.assertEqual(group['number'], 15)
                    self.assertTrue(group['applicable'])
                    self.assertTrue(group['present'])
                    print('FAILED COLLECT %s %s: group 15 present; prepare keys unchanged' %
                          (info['name'], backend))

    def assert_outputs(self, manifest):
        rows=[line.split('\t') for line in (self.stage/'OUTPUTS.tsv').read_text().splitlines() if line and not line.startswith('#')]
        self.assertEqual(len(rows),len(manifest['outputs']))
        for row,evidence in zip(rows,manifest['outputs']):
            self.assertEqual(len(row),5)
            self.assertEqual(row[3],evidence['sha256'])
            path=self.stage/row[2]
            if path.is_file(): self.assertEqual(row[3],sha(path))
            else:
                listing=''
                for item in evidence['members']:
                    self.assertEqual(item['sha256'],sha(path/item['path']))
                    listing+=item['path']+'\t'+item['sha256']+'\n'
                self.assertEqual(row[3],'sha256-tree:'+hashlib.sha256(listing.encode()).hexdigest())

    def complete_rna(self, model=MODEL):
        self.prepare();self.fake_run();self.submit()
        return self.collect(model=model)

    def check_manifest(self, manifest):
        path=self.fixture.tmp/'candidate.json';path.write_text(json.dumps(manifest))
        result=run([sys.executable,self.ws/'_system/manifest_check.py',path,'--json'],cwd=self.ws)
        return result.returncode,json.loads(result.stdout.decode())

    def test_schema_matches_lane_table_and_spec(self):
        import re
        schema=mc.load_schema()
        conditional={4:('wrapper_kind','nextflow'),6:('reference_named',True),10:('backend','slurm'),
                     12:('approval_gated',True),14:('design_record',True),15:('status','FAILED'),16:('model_step',True)}
        expected=[(n,'required_if_applicable' if n in conditional else 'required',
                   {'fact':conditional[n][0],'equals':conditional[n][1]} if n in conditional else None)
                  for n in range(1,19)]
        self.assertEqual([(g['number'],g['class'],g['predicate']) for g in schema['groups']],expected)
        spec=(REPO/'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md').read_text()
        paragraph=next(line for line in spec.splitlines() if line.startswith('1. inputs and their sha256'))
        names=re.split(r';\s*\d+\.\s*',paragraph[3:])
        names[-1]=names[-1].split('. A finding')[0].rstrip('.')
        self.assertEqual([g['name'] for g in schema['groups']],names)

    def test_group_removal_sweep(self):
        manifest=self.complete_rna()
        all_groups=copy.deepcopy(manifest)
        all_groups['predicate_facts'].update(wrapper_kind='nextflow',backend='slurm',approval_gated=True,design_record=True,status='FAILED')
        all_groups.update(containers=[{'process':'FIXTURE','image':'fixture@sha256:'+'a'*64,'digest':'sha256:'+'a'*64}],
            resources={'Elapsed':'00:01:00','MaxRSS':'2048K','AllocCPUS':'4'},approvals=[{'id':'fixture-approval','sha256':'a'*64}],
            design_check={'path':'design.json','sha256':'b'*64},failure_class='workflow',backend='slurm',venue='slurm')
        # R9: this synthetic all-groups case changes local -> Nextflow, so its
        # positive control must also supply Nextflow's required execution file.
        all_groups['execution_config'].append({'role':'nextflow_config',
            'path':'fixture/nextflow.config', 'sha256':'c'*64})
        for complete in (manifest,all_groups):
            self.assertEqual(self.check_manifest(complete)[0],0)
            for group in mc.grade(complete)['groups']:
                candidate=copy.deepcopy(complete)
                for field in group['fields']: candidate.pop(field,None)
                code,report=self.check_manifest(candidate)
                expected=group['applicable'] and group['class'] in ('required','required_if_applicable')
                self.assertEqual(code!=0,expected,'group %d'%group['number'])
                self.assertEqual(report['manifests'][0]['groups'][group['number']-1]['applicable'],group['applicable'],'a predicate read its own group')

    def test_predicates_and_missing_facts_fail_closed(self):
        manifest=self.complete_rna();schema=mc.load_schema()
        for key,values in schema['predicate_facts'].items():
            for value in values:
                candidate=copy.deepcopy(manifest);candidate['predicate_facts'][key]=value
                for g in mc.grade(candidate)['groups']:
                    if g['predicate'] and g['predicate']['fact']==key:
                        self.assertEqual(g['applicable'],value==g['predicate']['equals'])
            for bad in ('REMOVE','invalid',None):
                candidate=copy.deepcopy(manifest)
                if bad=='REMOVE': candidate['predicate_facts'].pop(key)
                else: candidate['predicate_facts'][key]=bad
                code,report=self.check_manifest(candidate)
                self.assertNotEqual(code,0);self.assertIn('error',report['manifests'][0])
        candidate=copy.deepcopy(manifest);candidate['predicate_facts']['backend']='slurm'
        self.assertFalse(mc.grade(candidate)['groups'][10]['present'], 'prepare backend differs from executor record')
        candidate=copy.deepcopy(manifest);candidate.pop('predicate_facts')
        self.assertNotEqual(self.check_manifest(candidate)[0],0)
        schema['groups'][3]['predicate']={'group':'containers','equals':True}
        with self.assertRaises(ValueError): mc.grade(manifest,schema)

    def test_backend_venue_pairs(self):
        manifest = self.complete_rna()
        allowed = {('local', 'local'), ('local', 'homelab'), ('slurm', 'slurm')}
        for backend in ('local', 'slurm', 'homelab', 'unknown', None):
            for venue in ('local', 'homelab', 'slurm', 'Local', 'homelab ', None):
                with self.subTest(backend=backend, venue=venue):
                    candidate = copy.deepcopy(manifest)
                    candidate.update(backend=backend, venue=venue)
                    candidate['predicate_facts']['backend'] = backend
                    self.assertEqual(mc.group_present(11, candidate, mc.load_schema()),
                                     (backend, venue) in allowed)
        for venue in ('local', 'homelab'):
            candidate = copy.deepcopy(manifest)
            candidate.update(backend='local', venue=venue)
            candidate['predicate_facts']['backend'] = 'slurm'
            self.assertFalse(mc.group_present(11, candidate, mc.load_schema()))

    def test_model_sentinels_and_known_prefix(self):
        self.prepare();self.fake_run();self.submit()
        for model,applicable,present in (('unknown',True,False),('none',False,False),(MODEL,True,True)):
            manifest=self.collect(model=model)
            group=mc.grade(manifest)['groups'][15]
            self.assertEqual((group['applicable'],group['present']),(applicable,present))
            self.assertEqual(manifest['agent_model'],model)
            self.assertEqual(mc.grade(manifest)['ok'],model!='unknown')
        for field in ('model_id','model_version','provider','prompt_id'):
            candidate=copy.deepcopy(manifest);candidate['model_steps'][0][field]='unknown'
            self.assertNotEqual(self.check_manifest(candidate)[0],0)
        candidate=copy.deepcopy(manifest);candidate['workflow_name']='no-rng-in-code-path'
        self.assertNotEqual(self.check_manifest(candidate)[0],0)

    def test_agreement_ref_is_required_prepare_evidence(self):
        original = self.prepare()
        self.assertEqual(original['agreement_ref'], 'none')
        self.fake_run(); self.submit()
        complete = self.collect()
        self.assertTrue(mc.grade(complete)['groups'][10]['present'])
        self.assertIn('agreement_ref', mc.load_schema()['groups'][10]['fields'])
        for value in (None, '', 'unknown', 'TODO', 'null'):
            candidate = copy.deepcopy(complete)
            candidate['agreement_ref'] = value
            self.assertFalse(mc.grade(candidate)['groups'][10]['present'])
        candidate = copy.deepcopy(complete)
        del candidate['agreement_ref']
        self.assertFalse(mc.grade(candidate)['groups'][10]['present'])
        # A legacy dataset row must not acquire an invented agreement at prepare.
        dataset = self.project / '00_data/dataset.tsv'
        rows = list(csv.DictReader(dataset.read_text().splitlines(), delimiter='\t'))
        rows[0].pop('agreement_ref')
        dataset.chmod(0o644)
        with dataset.open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter='\t')
            writer.writeheader(); writer.writerows(rows)
        self.assertIsNone(self.prepare()['agreement_ref'])

    def test_collect_evidence_guard_refuses_session_writes(self):
        self.pipeline_fixtures(); self.configure_wrapper('scrnaseq', 'local', self.project)
        self.fake_wrapper_run(); self.submit()
        trace = self.stage / 'run/pipeline_info/gars_trace.txt'
        lines = (GARS / 'tests/fixtures/manifest/trace.txt').read_text().splitlines()
        trace.write_text(lines[0] + '\n' + lines[3] + '\n')
        checked(self.wrapper_argv('collect', ['--model', MODEL]), cwd=self.ws, env=self.env)
        manifest = json.loads(self.manifest_path.read_text())
        self.assertFalse(mc.grade(manifest)['groups'][3]['present'])
        self.assertNotEqual(self.check_manifest(manifest)[0], 0)
        before = trace.read_bytes()
        for suffix in ('run/pipeline_info/gars_trace.txt', 'run/versions.json'):
            target = str((self.stage / suffix).relative_to(self.ws))
            calls = [('Write', {'file_path': target, 'content': 'forged'}),
                     ('Edit', {'file_path': target, 'old_string': 'tag', 'new_string': 'digest'})]
            calls += [('Bash', {'command': command}) for command in (
                'echo forged > ' + target, 'tee ' + target, 'cp source ' + target,
                'mv source ' + target, 'mv ' + target + ' moved', 'rm ' + target)]
            for tool, data in calls:
                with self.subTest(target=suffix, tool=tool, data=data):
                    result = run([sys.executable, self.ws / '_system/guard_hook.py'], cwd=self.ws,
                        stdin=json.dumps(dict(tool_name=tool, tool_input=data, cwd=str(self.ws))),
                        env={'CLAUDE_PROJECT_DIR': str(self.ws)})
                    self.assertEqual(result.returncode, 2, result.stderr.decode())
        sibling = str((self.stage / 'notes.txt').relative_to(self.ws))
        result = run([sys.executable, self.ws / '_system/guard_hook.py'], cwd=self.ws,
            stdin=json.dumps(dict(tool_name='Write', tool_input={'file_path': sibling}, cwd=str(self.ws))),
            env={'CLAUDE_PROJECT_DIR': str(self.ws)})
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        self.assertEqual(trace.read_bytes(), before)

    def test_mutable_tag_and_immutable_trace_evidence(self):
        self.pipeline_fixtures();self.configure_wrapper('scrnaseq','local',self.project)
        self.fake_wrapper_run();self.submit()
        trace=self.stage/'run/pipeline_info/gars_trace.txt'
        lines=(GARS/'tests/fixtures/manifest/trace.txt').read_text().splitlines()
        for index,present in ((1,True),(2,True),(3,False)):
            trace.write_text(lines[0]+'\n'+lines[index]+'\n')
            checked(self.wrapper_argv('collect',['--model',MODEL]),cwd=self.ws,env=self.env)
            manifest=json.loads(self.manifest_path.read_text())
            self.assertEqual(mc.grade(manifest)['groups'][3]['present'],present)
            self.assertEqual(self.check_manifest(manifest)[0]==0,present)

    def test_unparseable_manifest_is_never_skipped(self):
        manifest=self.complete_rna()
        bad=self.fixture.tmp/'broken.json';bad.write_text('{broken')
        result=run([sys.executable,self.ws/'_system/manifest_check.py',self.manifest_path,bad,'--json'],cwd=self.ws)
        self.assertNotEqual(result.returncode,0)
        report=json.loads(result.stdout.decode())
        self.assertEqual((report['manifests_read'],report['manifests_graded']),(2,1))
        self.assertEqual(len(report['manifests']),2);self.assertIn('error',report['manifests'][1])
        empty=mc.load_schema();empty['groups']=[];grade=mc.grade(manifest,empty)
        self.assertEqual((grade['present'],grade['applicable'],grade['ok']),(0,0,False))

    def test_reference_hash_mismatch_refused_and_unknown_is_incomplete(self):
        self.prepare();source=self.fixture.refs/'genome.fa.gz';source.write_bytes(source.read_bytes()+b'drift')
        result=run([sys.executable,self.fixture.de,'prepare','--project',self.project,'--counts',self.fixture.counts_native,
                    '--design',self.project/'01_samplesheets/rnaseq_bulk_design.csv'],cwd=self.ws)
        self.assertNotEqual(result.returncode,0);self.assertIn(b'reference_hash_mismatch',result.stdout)
        registry=self.ws/'_references/genomes.md'
        import re
        registry.write_text(re.sub(r'\b[0-9a-f]{64}\b','UNKNOWN',registry.read_text()))
        self.prepare();self.fake_run();self.submit();manifest=self.collect()
        self.assertEqual(manifest['reference']['reason'],'reference_hash_unknown')
        self.assertFalse(mc.grade(manifest)['groups'][5]['present'])

    def test_output_hash_invariant_and_complete_gate(self):
        manifest=self.complete_rna();self.assert_outputs(manifest)
        index=self.stage/'OUTPUTS.tsv';original=index.read_text();first=manifest['outputs'][0]['sha256']
        index.write_text(original.replace(first,'0'*64,1))
        code='import sys;sys.path.insert(0,sys.argv[1]);import wrapperlib;from pathlib import Path;wrapperlib.write_status(Path(sys.argv[2]),"COMPLETE")'
        result=run([sys.executable,'-c',code,self.ws/'_system',self.stage],cwd=self.ws)
        self.assertNotEqual(result.returncode,0)
        index.write_text(original);(self.stage/manifest['outputs'][0]['path']).write_text('modified output')
        result=run([sys.executable,'-c',code,self.ws/'_system',self.stage],cwd=self.ws)
        self.assertNotEqual(result.returncode,0)

    def test_commit_pin_mismatch_still_refused(self):
        self.pipeline_fixtures()
        code='import sys;sys.path.insert(0,sys.argv[1]);import workspace,wrapperlib;workspace.PIPELINES["spatialvi"]="nf-core-spatialvi-"+sys.argv[2];f=[];wrapperlib.check_pipeline("spatialvi",f);assert not f,f'
        checked([sys.executable,'-c',code,self.ws/'_system',self.spatial_pin],cwd=self.ws,env=self.env)
        path=Path(self.env['GARS_PIPELINES'])/('spatialvi-'+self.spatial_pin)
        wrong='0'*7 if self.spatial_pin!='0'*7 else 'f'*7
        path.rename(path.parent/('spatialvi-'+wrong))
        result=run([sys.executable,'-c',code,self.ws/'_system',wrong],cwd=self.ws,env=self.env)
        self.assertNotEqual(result.returncode,0);self.assertIn(b'expected '+wrong.encode(),result.stderr)

    def test_tree_hash_lists_symlinks_without_following(self):
        import wrapperlib as wl
        directory=self.fixture.tmp/'tree';directory.mkdir()
        (directory/'b.txt').write_text('b');(directory/'a.txt').write_text('a')
        (directory/'link.txt').symlink_to(directory/'a.txt')
        (directory/'cycle').symlink_to(directory,target_is_directory=True)
        evidence=wl.output_evidence(self.fixture.tmp,{'type':'table','role':'native','path':'tree'})
        self.assertEqual([r['path'] for r in evidence['members']],['a.txt','b.txt'])
        self.assertEqual([r['path'] for r in evidence['symlinks']],['cycle','link.txt'])
        listing=''.join(r['path']+'\t'+r['sha256']+'\n' for r in evidence['members'])
        self.assertEqual(evidence['sha256'],'sha256-tree:'+hashlib.sha256(listing.encode()).hexdigest())
        (directory/'b.txt').write_text('changed')
        self.assertNotEqual(evidence['sha256'],wl.output_evidence(self.fixture.tmp,{'type':'table','role':'native','path':'tree'})['sha256'])

    def test_trace_template_grammar_and_manual_migration(self):
        import wrapperlib as wl
        template=(GARS/'_templates/config/nextflow.slurm.config').read_text()
        path=self.fixture.tmp/'executor.config'
        for text,valid in ((template,True),(template.split('\ntrace {')[0],False),
                           (template.replace('task_id,hash,process','task_id,process'),False)):
            path.write_text(text);fails=[];wl.check_groovy(path,fails)
            self.assertEqual(not fails,valid)
            if not valid: self.assertIn('unregistered Groovy grammar',str(fails))


if __name__ == '__main__':
    unittest.main(verbosity=2)
