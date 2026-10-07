"""The reproduction package (decisions 0281, 0283): harvest, render, verify and compare.

Each test builds a small world on disk with GARS's own record writers (wrapperlib's params.yaml
writer, output index, software evidence and input key), so harvest re-checks a record shaped like a
real stage 02 run: a clean GARS clone, a pipeline checkout at the recorded commit, a samplesheet
naming FASTQs by absolute path, and a submit.sh whose -work-dir is an S3 bucket holding a fake
account id. Harvest and render run as the command line a person would run.
"""
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import GARS, REPO, module, run

import wrapperlib as wl

CLAIMS = GARS / '_system/claims'
TOOL = CLAIMS / 'package_run.py'
FIXTURES = GARS / 'tests/fixtures/package'
renderer = module(CLAIMS / 'render_methods.py', 'package_test_render_methods')
comparer = module(CLAIMS / 'package/compare.py', 'package_test_compare')

ACCOUNT = '123456789012'
BUCKET = 'gars-demo-runs-' + ACCOUNT
TEST_DATASETS = 'cd022b097372b078a68d8afadb172ad7342fd91f'
LANE = 'f' * 40
ACTOR = 'fixture-approver-q7x'
STAGE_REL = '02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper'
STAGE = 'atacseq_bulk.01_nfcore-atacseq-wrapper'
LABELS = ('recorded at run', 'computed at harvest', 'supplied at packaging from ', 'computed at packaging from ',
          'not recorded by the run', 'withheld')   # the six defined labels (the exemplar review's round 1, m1)
GIT_ENV = {'GIT_AUTHOR_NAME': 'fixture', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
           'GIT_COMMITTER_NAME': 'fixture', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
           'GIT_AUTHOR_DATE': '2026-10-05T12:00:00Z', 'GIT_COMMITTER_DATE': '2026-10-05T12:00:00Z'}
READS = (('atac-a-r1', 'SRR1822153'), ('atac-b-r1', 'SRR1822157'))


def git(repo, *args):
    env = dict(os.environ, **GIT_ENV)
    return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false',
                           '-C', str(repo)] + list(args), env=env, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.decode().strip()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        data = data.encode('utf-8')
    path.write_bytes(data)
    return path


def nextflow_pin():
    text = (GARS / '_references/gars-nxf.conda.txt').read_text(encoding='utf-8')
    return re.findall(r'/nextflow-([0-9][0-9.]*)-', text)[0]


class World(object):
    """One GARS clone with one yeast ATAC project whose stage 02 ran and was collected."""

    def __init__(self, root, sparse=False, index_param=False, private_image=False, stage03=False,
                 nextflow=None, data_class='public'):
        self.root = root
        self.clone = root / 'clone'
        (self.clone / 'gars').mkdir(parents=True)
        for name in ('_system', '_references'):
            shutil.copytree(str(GARS / name), str(self.clone / 'gars' / name),
                            ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copyfile(str(REPO / 'CITATION.cff'), str(self.clone / 'CITATION.cff'))
        shutil.copyfile(str(REPO / '.gitignore'), str(self.clone / '.gitignore'))   # the repository's own (h1 H10)
        git(self.clone, 'init', '-q')
        git(self.clone, 'add', '-A')
        git(self.clone, 'commit', '-q', '-m', 'fixture clone')
        self.commit = git(self.clone, 'rev-parse', 'HEAD')
        self.lane = None
        checkout = root / 'pipelines' / 'atacseq-2.1.2'
        write(checkout / 'main.nf', 'workflow {}\n')
        git(checkout, 'init', '-q')
        git(checkout, 'add', '-A')
        git(checkout, 'commit', '-q', '-m', 'pipeline')
        self.checkout = checkout
        self.pipeline_commit = git(checkout, 'rev-parse', 'HEAD')
        self.project = self.clone / 'gars' / 'projects' / 'yeast'
        self.stage = self.project / STAGE_REL
        reads = READS[:1] if sparse else READS
        self.fastqs = {}
        for sample, accession in reads:
            for end in ('1', '2'):
                name = '%s_S1_L001_R%s_001.fastq.gz' % (sample, end)
                self.fastqs[name] = (accession + '_' + end + '.fastq.gz',
                                     write(root / 'fixtures' / name, '@%s/%s\nACGT\n+\nIIII\n' % (sample, end)))
        self.refs = {'genome.fa': write(root / 'refs' / 'genome.fa', '>I\nACGTACGT\n>MT\nACGT\n'),
                     'genes.gtf': write(root / 'refs' / 'genes.gtf', 'I\tfixture\tgene\t1\t8\t.\t+\t.\tgene_id "Y1";\n')}
        config = self.project / '_config' / 'atacseq_bulk.yaml'
        write(config, 'reference.fasta: %s\nreference.gtf: %s\nreference.mito_name: MT\npeaks.type: narrow\n'
                      'compute.cpus: 4\n' % (self.refs['genome.fa'], self.refs['genes.gtf']))
        template = (GARS / '_templates/config/nextflow.awsbatch.config').read_text(encoding='utf-8')
        executor_config = write(self.project / '_config' / 'nextflow.awsbatch.config',
                                template.replace('{{queue}}', 'gars-pad-queue').replace('{{goal}}', 'repro-fixture')
                                .replace('{{region}}', 'us-east-1'))
        descriptor = write(self.project / '_config' / 'executor.yaml',
                           'name: local\nwork_dir: s3://%s/work\n' % BUCKET)
        write(self.project / '00_data' / 'dataset.tsv', 'purpose\tdata_class\nfixture\t%s\n' % data_class)
        write(self.project / 'HISTORY.md', '# History\n')
        sheet = self.project / '01_samplesheets' / 'atacseq_bulk_samplesheet.csv'
        lines = ['sample,fastq_1,fastq_2,replicate']
        for sample, _ in reads:
            lines.append('%s,%s,%s,1' % (sample.rsplit('-', 1)[0], self.fastqs['%s_S1_L001_R1_001.fastq.gz' % sample][1],
                                         self.fastqs['%s_S1_L001_R2_001.fastq.gz' % sample][1]))
        write(sheet, '\n'.join(lines) + '\n')
        design = write(self.project / '01_samplesheets' / 'atacseq_bulk_design_check.json', '{"ok": true}\n')
        self.stage.mkdir(parents=True)
        params = [('input', str(sheet)), ('outdir', str(self.stage / 'run' / 'results')),
                  ('fasta', str(self.refs['genome.fa'])), ('gtf', str(self.refs['genes.gtf'])),
                  ('mito_name', 'MT'), ('aligner', 'bwa'), ('macs_gsize', '11624332'), ('narrow_peak', 'true')]
        params.append(('bwa_index', str(root / 'derived' / 'bwa')) if index_param else ('save_reference', 'true'))
        wl.write_params_yaml(self.stage, 'atacseq_bulk', params)
        results = self.stage / 'run' / 'results'
        ml = results / 'bwa' / 'merged_library'
        write(ml / 'atac-a.mLb.clN.sorted.bam', b'BAM\x01' + bytes(range(64)))
        write(ml / 'macs2' / 'narrow_peak' / 'atac-a.mLb.clN_peaks.narrowPeak', 'I\t10\t20\tpeak1\t50\t.\n')
        write(ml / 'macs2' / 'narrow_peak' / 'consensus' / 'consensus_peaks.mLb.clN.saf',
              'GeneID\tChr\tStart\tEnd\tStrand\npeak1\tI\t10\t20\t+\n')
        counts = write(ml / 'macs2' / 'narrow_peak' / 'consensus' / 'consensus_peaks.mLb.clN.featureCounts.txt',
                       '# Program:featureCounts v2.0.1; Command:"featureCounts" "-a" "/tmp/nxf.3f9a2c/x.saf"\n'
                       'Geneid\tChr\tStart\tEnd\tStrand\tLength\tatac-a\npeak1\tI\t10\t20\t+\t11\t5\n')
        write(results / 'multiqc' / 'narrow_peak' / 'multiqc_report.html', '<html>report</html>\n')
        write(results / 'pipeline_info' / 'software_versions.yml',
              'BWA_MEM:\n  bwa: 0.7.17-r1188\nWorkflow:\n  Nextflow: %s\n  nf-core/atacseq: v2.1.2\n'
              % (nextflow or nextflow_pin()))
        image = ('123456789012.dkr.ecr.us-east-1.amazonaws.com/bwa:0.7.17' if private_image
                 else 'quay.io/biocontainers/bwa:0.7.17--hed695b0_7')
        write(self.stage / 'run' / 'pipeline_info' / 'gars_trace.txt',
              'task_id\tprocess\tcontainer\tstart\tcomplete\n'
              '1\tNFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BWA_MEM\t%s\t2026-10-09 10:00:00.000\t2026-10-09 10:01:00.000\n'
              '2\tNFCORE_ATACSEQ:ATACSEQ:MULTIQC\tquay.io/biocontainers/multiqc:1.13--pyhdfd78af_0\t'
              '2026-10-09 10:02:00.000\t2026-10-09 10:03:00.000\n' % image)
        rows = [('peaks', 'run/results/bwa/merged_library/macs2/narrow_peak')]
        if not sparse:
            rows += [('counts_peaks', str(counts.relative_to(self.stage))),
                     ('bam_genome', 'run/results/bwa/merged_library'),
                     ('qc_multiqc', 'run/results/multiqc/narrow_peak/multiqc_report.html')]
        write(self.stage / 'OUTPUTS.tsv', '# type\trole\tpath\n' + ''.join('%s\tnative\t%s\n' % r for r in rows))
        outputs = wl.complete_output_index(self.stage)
        write(self.stage / 'STATUS', 'COMPLETE\n')
        self.nextflow_log = True
        submit = write(self.stage / 'submit.sh',
                       '#!/bin/bash\nset -euo pipefail\nWS="%s"\nsource "$WS/_system/gars-env.sh"\n'
                       'export NXF_SYNTAX_PARSER=v1\ncd "%s"\nnextflow run "%s" \\\n    -c "%s" \\\n'
                       '    -params-file "%s/params.yaml" \\\n    -work-dir "s3://%s/work/yeast-atacseq_bulk" \\\n'
                       '    $RESUME\n' % (self.clone / 'gars', self.stage, checkout, executor_config, self.stage, BUCKET))
        # Nextflow's own log names the launch line (h3-5); a real launch line was checked by the early probe.
        write(self.stage / 'run' / '.nextflow.log',
              'Oct-09 10:00:00.000 [main] DEBUG nextflow.cli.Launcher - $> nextflow run %s -c %s -params-file %s/params.yaml '
              '-work-dir s3://%s/work/yeast-atacseq_bulk\n' % (checkout, executor_config, self.stage, BUCKET))
        commands = write(self.stage / 'reproducibility' / 'commands.sh',
                         '# The exact submission this sub-stage makes:\nbash %s\n' % submit)
        inputs = {'samplesheet': str(sheet), 'config': str(config)}
        manifest = {
            'agent_model': 'none', 'agreement_ref': 'none', 'approvals': [],
            'artifact_destination': 'gars/projects/yeast/%s/run' % STAGE_REL, 'backend': 'local',
            'checkout': str(checkout), 'command': {'path': 'reproducibility/commands.sh', 'sha256': sha(commands.read_bytes())},
            'config_sha256': sha(config.read_bytes()),
            'containers': wl.trace_evidence(self.stage)[0],
            'data_class': data_class,
            'design_check': {'path': '01_samplesheets/atacseq_bulk_design_check.json', 'sha256': sha(design.read_bytes())},
            'execution': {'complete': '2026-10-09 10:03:00.000', 'start': '2026-10-09 10:00:00.000'},
            'execution_config': [
                {'path': 'gars/projects/yeast/_config/executor.yaml', 'role': 'executor_descriptor',
                 'sha256': sha(descriptor.read_bytes())},
                {'path': 'gars/projects/yeast/_config/nextflow.awsbatch.config', 'role': 'nextflow_config',
                 'sha256': sha(executor_config.read_bytes())}],
            'execution_config_resolved': {'backend': 'local', 'nextflow_config': 'nextflow.awsbatch.config',
                                          'nextflow_profile': ''},
            'expiry': 'none', 'failure_class': None, 'gars_commit': self.commit,
            'input_data_location': dict(inputs, dataset=str(root / 'fixtures')), 'inputs': inputs,
            'key_formula': 'stage01-v1', 'model_steps': [], 'outputs': outputs, 'params': dict(params),
            'permitted_backends': 'local:fixture', 'pipeline_commit': self.pipeline_commit,
            'predicate_facts': {'approval_gated': False, 'backend': 'local', 'design_record': True,
                                'model_step': False, 'reference_named': True, 'status': 'COMPLETE',
                                'wrapper_kind': 'nextflow'},
            'purpose': 'fixture', 'random_seeds': 'no-rng-in-code-path',
            'reference': {'annotation_release': 'R64-1-1.fixture', 'build': 'R64-1-1', 'comparison': 'matched',
                          'fasta_sha256': sha(self.refs['genome.fa'].read_bytes()),
                          'gtf_sha256': sha(self.refs['genes.gtf'].read_bytes()), 'id': 'R64-1-1',
                          'observed': {'fasta_sha256': sha(self.refs['genome.fa'].read_bytes()),
                                       'gtf_sha256': sha(self.refs['genes.gtf'].read_bytes())}},
            'resources': {'applicability': 'not applicable'},
            'samplesheet_sha256': sha(sheet.read_bytes()),
            'software_versions': wl.software_evidence(self.stage, 'nextflow'),
            'template_version': 'v0.10.0', 'threads': 4, 'venue': 'local',
            'workflow_name': 'nfcore-atacseq-wrapper', 'workflow_version': '2.1.2', 'wrapper': 'atacseq_bulk'}
        manifest['idempotency_key'] = wl.input_key(self.stage, manifest)
        with submit.open('a') as handle:   # as wrapperlib.write_reproducibility leaves it
            handle.write('# idempotency_key=' + manifest['idempotency_key'] + '\n')
        self.manifest_path = write(self.stage / 'reproducibility' / 'manifest.json',
                                   json.dumps(manifest, indent=2, sort_keys=True))
        if stage03:
            self.add_analysis()
        self.sources = write(root / 'lane-sources.tsv', self.lane_sources())
        self.tolerances = write(root / 'package-tolerances.json', json.dumps({'entries': []}, indent=2) + '\n')
        bin_dir = root / 'bin'
        self.gitleaks_log = root / 'gitleaks.log'
        write(bin_dir / 'gitleaks', '#!/bin/sh\necho "$@" >> "%s"\nexit "${FAKE_GITLEAKS_EXIT:-0}"\n' % self.gitleaks_log)
        os.chmod(str(bin_dir / 'gitleaks'), 0o755)
        self.env = {'PATH': '%s:%s' % (bin_dir, os.environ.get('PATH', ''))}

    def add_analysis(self):
        adir = self.project / '03_custom_analysis' / '01_followup'
        plan = write(adir / 'PLAN.md', '# Plan\n\nCount peaks per sample.\n')
        script = write(adir / 'analysis.sh', 'echo peaks\n')
        self.submit_analysis(adir, script, '4242', 1791550800.0)   # 2026-10-09T13:00Z
        store = self.clone / '.gars-approvals'
        store.mkdir(mode=0o700)
        identity = str(plan.resolve())
        write(store / (sha(identity.encode('utf-8')) + '.json'), json.dumps({
            'actor': ACTOR, 'expiry': '2026-10-10T12:00:00Z', 'plan_path': identity,
            'plan_sha256': sha(plan.read_bytes()), 'timestamp': '2026-10-09T12:00:00Z'}, sort_keys=True))
        self.plan = plan

    def submit_analysis(self, adir, script, job, at, append=False):
        """As executorlib's local submit leaves it (review h3-1): GARS's own launcher, which removes the
        marker first and writes it only on exit 0, run for real; the local job record naming that
        launcher with its exit file; and the submission entry."""
        import executorlib
        (adir / 'run').mkdir(exist_ok=True)   # GARS's submit makes it before it writes the launcher
        launcher = executorlib._analysis_launcher(adir, script, {'name': 'local'})
        code = subprocess.run(['bash', str(launcher)], stdout=subprocess.DEVNULL).returncode
        jobs = self.project / executorlib.LOCAL_JOBS_DIR
        exit_file = write(jobs / ('%s.exit' % job), '%d\n' % code)
        write(jobs / ('%s.json' % job), json.dumps({'script': str(launcher), 'exit_file': str(exit_file)}))
        entry = json.dumps({'script': str(script), 'script_sha256': sha(script.read_bytes()),
                            'launcher': str(launcher), 'launcher_sha256': sha(launcher.read_bytes()),
                            'job_id': job, 'executor': 'local', 'submitted_at': at}) + '\n'
        record = adir / '.gars_submissions.jsonl'
        write(record, (record.read_text() if append and record.exists() else '') + entry)
        return launcher, code

    def lane_sources(self):
        lines = ['kind\tname\turl\tsha256\tsource']
        for name, (original, path) in sorted(self.fastqs.items()):
            lines.append('input\t%s\thttps://raw.githubusercontent.com/nf-core/test-datasets/%s/testdata/%s\t%s\t'
                         'nf-core/test-datasets@%s:testdata/%s'
                         % (name, TEST_DATASETS, original, sha(path.read_bytes()), TEST_DATASETS, original))
        for name, path in sorted(self.refs.items()):
            lines.append('reference\t%s\thttps://raw.githubusercontent.com/nf-core/test-datasets/%s/reference/%s\t%s\t'
                         'nf-core/test-datasets@%s:reference/%s'
                         % (name, TEST_DATASETS, name, sha(path.read_bytes()), TEST_DATASETS, name))
        return '\n'.join(lines) + '\n'

    def harvest(self, out='harvest', extra=()):
        return run([sys.executable, TOOL, 'harvest', '--gars', self.clone, '--project', self.project,
                    '--lane-commit', self.lane or self.commit, '--out', self.root / out] + list(extra),
                   env=self.env)

    def render(self, harvest='harvest', out='package', env=None):
        return run([sys.executable, TOOL, 'render', '--harvest', self.root / harvest, '--gars-repo', self.clone,
                    '--sources', self.sources, '--tolerances', self.tolerances, '--out', self.root / out],
                   env=dict(self.env, **(env or {})))

    def rerun_copy(self, out='rerun'):
        """A re-run folder holding exactly the recorded outputs, where rerun.sh would write them."""
        target = self.root / out / 'results' / STAGE
        shutil.copytree(str(self.stage / 'run' / 'results'), str(target))
        return self.root / out


def package_files(folder):
    return dict((p.relative_to(folder).as_posix(), p.read_bytes()) for p in sorted(folder.rglob('*')) if p.is_file())


class PackageCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='package-run-')
        self.root = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def world(self, **options):
        return World(self.root / ('w%d' % len(list(self.root.iterdir()))), **options)

    def built(self, **options):
        w = self.world(**options)
        h = w.harvest()
        self.assertEqual(h.returncode, 0, h.stderr.decode())
        r = w.render()
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return w, w.root / 'package'

    def refused(self, proc, words):
        self.assertEqual(proc.returncode, 1, proc.stdout.decode() + proc.stderr.decode())
        if isinstance(words, tuple):   # any one of several named refusals
            self.assertTrue(any(w in proc.stderr.decode() for w in words), proc.stderr.decode())
        else:
            self.assertIn(words, proc.stderr.decode())


class HarvestAndRender(PackageCase):
    def test_render_twice_is_byte_identical_and_verifies(self):
        w, package = self.built()
        again = w.render(out='package-2')
        self.assertEqual(again.returncode, 0, again.stderr.decode())
        self.assertEqual(package_files(package), package_files(w.root / 'package-2'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertIn(b'package verified', proc.stdout)
        self.assertIn(b'note: no landing README', proc.stdout)
        logged = w.gitleaks_log.read_text(encoding='utf-8')
        self.assertIn('gars/.gitleaks.toml', logged)
        self.assertIn('dir ', logged)

    def test_group_4_alone_may_be_absent_and_any_other_group_refuses(self):
        w = self.world()
        report = __import__('manifest_check').grade(json.loads(w.manifest_path.read_text()))
        absent = [g['number'] for g in report['groups'] if g['applicable'] and not g['present']
                  and g['class'] != 'optional']
        self.assertEqual(absent, [4])
        self.assertEqual(w.harvest().returncode, 0)
        manifest = json.loads(w.manifest_path.read_text())
        manifest['threads'] = None
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        self.refused(w.harvest(out='h2'), 'grades incomplete')

    def test_every_harvest_refusal(self):
        cases = {
            'a flipped output byte': ('bytes disagree', lambda w: write(
                w.stage / 'run/results/multiqc/narrow_peak/multiqc_report.html', '<html>other</html>\n')),
            'a changed samplesheet': ('input key differs', lambda w: write(
                w.project / '01_samplesheets/atacseq_bulk_samplesheet.csv',
                (w.project / '01_samplesheets/atacseq_bulk_samplesheet.csv').read_text() + '\n')),
            'recorded params edited': ('params.yaml does not hold the recorded params', self.edit_params),
            'a patched pipeline checkout': ('patched at run', lambda w: write(w.checkout / 'main.nf', 'workflow { patched }\n')),
            'a dirty GARS clone': ('not clean', lambda w: write(w.clone / 'stray.txt', 'x\n')),
        }
        for name, (words, damage) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world()
                damage(w)
                self.refused(w.harvest(), words)
                self.assertFalse((w.root / 'harvest').exists())

    def test_review_h2_harvest_refusals(self):
        """Each case is one finding of the harvest-only review r2, reproduced as the reviewer did."""
        cases = {
            'M2 a relative link that climbs out': ('a link to a path outside it', {}, self.relative_link_out),
            'M3 a versions file changed': ('not the versions files on disk', {}, lambda w: write(
                w.stage / 'run/results/pipeline_info/software_versions.yml',
                (w.stage / 'run/results/pipeline_info/software_versions.yml').read_text() + '# edited\n')),
            'M3 the recorded images edited': ('not the ones the trace names', {}, self.edit_images),
            'M3 the executor descriptor changed': ('executor_descriptor is not the file', {}, lambda w: write(
                w.project / '_config/executor.yaml', 'name: local\n')),
            'M3 the reference changed': ('reference fasta is not the file', {}, lambda w: write(
                w.refs['genome.fa'], '>I\nTTTT\n')),
            'm4 the dataset is now controlled': ('not public', {}, lambda w: write(
                w.project / '00_data/dataset.tsv', 'purpose\tdata_class\nfixture\tcontrolled\n')),
            'm5 a failed stage': ('not COMPLETE', {}, lambda w: write(w.stage / 'STATUS', 'FAILED\n')),
            'm5 a manifest recording FAILED': ('recorded as FAILED', {}, self.record_failed),
            'a manifest naming a non-public data class': ('data_class is', {}, self.manifest_controlled),
            'm6 a stage 03 that never finished': ('did not finish', {'stage03': True}, lambda w: (
                w.project / '03_custom_analysis/01_followup/run/.gars_run_complete').unlink()),
            'm6 a stage 03 submission with an error': ('records an error', {'stage03': True}, self.submission_error),
            'm7 an ignored file in the pipeline': ('patched at run', {}, self.ignored_in_pipeline),
            'm8 the clone moved after the run': ('the clone is at', {}, lambda w: git(
                w.clone, 'commit', '--allow-empty', '-q', '-m', 'moved')),
        }
        for name, (words, options, damage) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world(**options)
                damage(w)
                self.refused(w.harvest(), words)
                self.assertFalse((w.root / 'harvest').exists())

    def test_a_real_shaped_stage_03_launcher_ships_masked(self):
        w, package = self.built(stage03=True)
        [launcher] = list((package / 'code/custom.01_followup/scripts/run').glob('launch-*.sh'))
        text = launcher.read_text()
        self.assertIn('Masked copy', text)
        self.assertIn('cd <WORKSPACE>/gars/projects/yeast/03_custom_analysis/01_followup', text)
        self.assertIn('custom.01_followup/run/%s: shipped masked' % launcher.name, (package / 'PROVENANCE.md').read_text())

    def test_params_ship_typed_as_the_runs_yaml_read_them(self):
        w, package = self.built()
        params = json.loads((package / ('params/%s.params.json' % STAGE)).read_text())
        self.assertIs(params['narrow_peak'], True)
        self.assertIs(params['save_reference'], True)
        self.assertEqual(params['macs_gsize'], 11624332)
        self.assertEqual(params['aligner'], 'bwa')

    @staticmethod
    def manifest_controlled(w):
        """The dataset record says public, the run's manifest does not: the manifest's own check refuses."""
        manifest = json.loads(w.manifest_path.read_text())
        manifest['data_class'] = 'controlled'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    @staticmethod
    def record_failed(w):
        manifest = json.loads(w.manifest_path.read_text())
        manifest['predicate_facts']['status'] = 'FAILED'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    def test_a_masked_launchers_submit_hash_never_prints(self):
        w = self.world(stage03=True)
        [path] = list((w.project / '03_custom_analysis/01_followup/run').glob('launch-*.sh'))
        launcher = sha(path.read_bytes())
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': ['run/results/multiqc/narrow_peak/multiqc_report.html'], 'mode': 'presence',
            'origin': 'pass-1', 'cause': 'the report embeds its run time', 'evidence': 'launcher ' + launcher}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'the sha256 of a file holding a masked value')

    @staticmethod
    def relative_link_out(w):
        peaks = w.stage / 'run/results/bwa/merged_library/macs2/narrow_peak'
        os.symlink('../' * 23 + 'opt/private-lab/refs/genome.fa', str(peaks / 'genome.fa'))
        manifest = json.loads(w.manifest_path.read_text())
        manifest['outputs'] = wl.complete_output_index(w.stage)
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    @staticmethod
    def edit_images(w):
        manifest = json.loads(w.manifest_path.read_text())
        manifest['containers'][0]['image'] = 'quay.io/biocontainers/bwa:9.9.9--edited'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    @staticmethod
    def submission_error(w):
        path = w.project / '03_custom_analysis/01_followup/.gars_submissions.jsonl'
        entry = json.loads(path.read_text())
        entry['job_id'], entry['error'] = None, 'local submission unresolved'
        write(path, json.dumps(entry) + '\n')

    @staticmethod
    def ignored_in_pipeline(w):
        write(w.checkout / 'bin' / 'samtools', '#!/bin/sh\n')
        write(w.checkout / '.git' / 'info' / 'exclude', 'bin/samtools\n')

    def test_review_h3_harvest_refusals(self):
        """Each case is one finding of the harvest-only review r3, reproduced as the reviewer did."""
        cases = {
            'h3-1 a first script that failed': ('FAILED', {'stage03': True}, self.first_script_failed),
            'h3-1 a resubmission that never started': ('R-135', {'stage03': True}, self.resubmitted_never_started),
            'h3-3 a samplesheet path that is gone': ('not a regular file at harvest', {}, self.sheet_path_gone),
            'h3-4 a script naming a private data path': ('an absolute path', {'stage03': True}, self.private_data_path),
            'h3-5 a launch line that differs': ("logged launch line is not", {}, lambda w: write(
                w.stage / 'run/.nextflow.log', (w.stage / 'run/.nextflow.log').read_text().replace(
                    '-work-dir', '--skip_trimming true -work-dir'))),
            # git's own status catches the edit when it lands in the index's second (a racy entry); either
            # refusal is the edit caught (the landing review: intermittent under load)
            'h3-6 an edit hidden by stat settings': (('differ from HEAD by content', 'gars/_system/wrapperlib.py)'), {},
                                                      self.stat_only_edit),
            'h3-6 an unexpected ignored file': ('git status: !!', {}, lambda w: write(
                w.clone / 'gars/_system/claims/notes.pyc', b'x')),
        }
        for name, (words, options, damage) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world(**options)
                damage(w)
                proc = w.harvest()
                if proc.returncode == 0:
                    proc = w.render()
                self.refused(proc, words)
                self.assertFalse((w.root / 'package').exists())

    def test_h3_2_an_in_tree_output_link_harvests_and_copies_to_the_right_place(self):
        w = self.world()
        peaks = w.stage / 'run/results/bwa/merged_library/macs2/narrow_peak'
        os.symlink('atac-a.mLb.clN_peaks.narrowPeak', str(peaks / 'latest.narrowPeak'))
        manifest = json.loads(w.manifest_path.read_text())
        manifest['outputs'] = wl.complete_output_index(w.stage)
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        proc = w.harvest()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue((w.root / 'harvest/project' / STAGE_REL / 'run/results/multiqc/narrow_peak/multiqc_report.html').is_file())
        self.assertEqual(w.render().returncode, 0)

    def test_h3_8_users_come_from_the_records_and_a_tool_image_is_not_a_user(self):
        tool = module(TOOL, 'package_run_users')
        # the stock login is never armed (the coordinating session's ruling (a)); a real name always is
        self.assertEqual(tool.record_users(['/home/ubuntu/x', '"/Users/jdoe/y"', '/home/conda/z']), ['jdoe'])
        self.assertFalse(tool.user_named('container nf-core/ubuntu:20.04', 'ubuntu'))
        self.assertTrue(tool.user_named('ran as ubuntu on the box', 'ubuntu'))
        self.assertTrue(tool.user_named('/home/ubuntu/run', 'ubuntu'))
        w, package = self.built()
        record = json.loads((w.root / 'harvest/HARVEST.json').read_text())
        self.assertNotIn(__import__('getpass').getuser(), record['secrets']['users'] if '/Users/' not in str(w.root)
                         and '/home/' not in str(w.root) else [])

    def test_h3_8_a_user_name_the_records_carry_never_ships(self):
        """The run's records name a home folder (not a shipped field); a lane note naming that user as a
        word must refuse the render."""
        w = self.world()
        manifest = json.loads(w.manifest_path.read_text())
        manifest['input_data_location']['dataset'] = '/home/fixture-q9/seqrun/atacseq'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': ['run/results/multiqc/narrow_peak/multiqc_report.html'], 'mode': 'presence',
            'origin': 'pass-1', 'cause': 'the report embeds its run time', 'evidence': 'read by fixture-q9'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.assertIn('fixture-q9', json.loads((w.root / 'harvest/HARVEST.json').read_text())['secrets']['users'])
        self.refused(w.render(), "a user name the run's records carry")

    def first_script_failed(self, w):
        adir = w.plan.parent
        qc = write(adir / 'qc.sh', 'exit 1\n')
        w.submit_analysis(adir, qc, '5001', 1791550900.0, append=True)
        plot = write(adir / 'plot.sh', 'echo plot\n')
        w.submit_analysis(adir, plot, '5002', 1791551000.0, append=True)

    def resubmitted_never_started(self, w):
        adir = w.plan.parent
        script = adir / 'analysis.sh'
        write(script, 'echo v2 -- never ran\n')
        import executorlib
        launcher = executorlib._analysis_launcher(adir, script, {'name': 'local'})
        record = adir / '.gars_submissions.jsonl'
        write(record, record.read_text() + json.dumps({
            'script': str(script), 'script_sha256': sha(script.read_bytes()), 'launcher': str(launcher),
            'launcher_sha256': sha(launcher.read_bytes()), 'job_id': '6002', 'executor': 'local',
            'submitted_at': 1791551000.0}) + '\n')

    @staticmethod
    def sheet_path_gone(w):
        name, (original, path) = sorted(w.fastqs.items())[0]
        path.unlink()

    def private_data_path(self, w):
        adir = w.plan.parent
        write(adir / 'analysis.sh', 'echo reads /data/lab-private/fixtures/counts.tsv\n')
        w.submit_analysis(adir, adir / 'analysis.sh', '7001', 1791551100.0, append=True)

    @staticmethod
    def stat_only_edit(w):
        git(w.clone, 'config', 'core.trustctime', 'false')
        git(w.clone, 'config', 'core.checkStat', 'minimal')
        lib = w.clone / 'gars/_system/wrapperlib.py'
        older = lib.stat().st_mtime_ns - 100 * 10 ** 9
        os.utime(str(lib), ns=(older, older))
        git(w.clone, 'update-index', '--refresh')
        info = lib.stat()
        old = "raise ValueError('output_hash: OUTPUTS.tsv, manifest and artifact bytes disagree')"
        new = "pass; ValueError('output_hash: OUTPUTS.tsv, manifest and artifact bytes disagree')"
        lib.write_text(lib.read_text().replace(old, new + ' ' * (len(old) - len(new))))
        os.utime(str(lib), ns=(info.st_atime_ns, info.st_mtime_ns))
        git(w.clone, 'status', '--porcelain')   # a lax status between edit and harvest, as a shell prompt runs

    def test_review_h1_harvest_refusals(self):
        """Each case is one finding of the harvest-only review r1, reproduced as the reviewer did."""
        cases = {
            'H1 commands.sh edited': ('commands.sh is not the file the run recorded', {}, lambda w: write(
                w.stage / 'reproducibility/commands.sh',
                (w.stage / 'reproducibility/commands.sh').read_text() + 'echo NOT-WHAT-RAN\n')),
            'H1 submit.sh edited': ('exactly the recorded input-key line', {}, self.edit_submit),
            'H2 a linked folder': ('linked folder', {}, self.link_a_folder),
            'H3 re-approved after the run': ('not in force when', {'stage03': True}, self.reapprove),
            'H4 an output link to an absolute path': ('a link to a path outside it', {}, self.absolute_link),
            'H5 the samplesheet shifted into the config': ('samplesheet_sha256 differs', {}, self.shift_row),
            'H6 a skip-worktree edit in GARS': ('skip-worktree', {}, self.skip_worktree),
            'H6 an untracked file in the pipeline': ('patched at run', {}, lambda w: write(
                w.checkout / 'bin' / 'samtools', '#!/bin/sh\n')),
            'H7 scripts/ under stage01-v1': ('bound by no input key', {}, lambda w: write(
                w.stage / 'scripts' / 'helper.py', 'print(1)\n')),
            'H8 a controlled stage 03 project': ('not public', {'stage03': True}, self.controlled_dataset),
        }
        for name, (words, options, damage) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world(**options)
                damage(w)
                self.refused(w.harvest(), words)
                self.assertFalse((w.root / 'harvest').exists())

    def test_a_replay_linked_config_is_harvested_by_its_bytes(self):
        w = self.world()
        config = w.project / '_config' / 'nextflow.awsbatch.config'
        elsewhere = write(w.root / 'replayed' / 'nextflow.awsbatch.config', config.read_bytes())
        config.unlink()
        os.symlink(str(elsewhere), str(config))
        self.assertEqual(w.harvest().returncode, 0)
        record = json.loads((w.root / 'harvest/HARVEST.json').read_text())
        self.assertEqual([l['path'] for l in record['links']], ['_config/nextflow.awsbatch.config'])
        self.assertEqual(w.render().returncode, 0)

    def test_h9_a_lane_commit_that_did_not_run_is_refused_at_render(self):
        w = self.world()
        w.lane = 'e' * 40
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'is not in the GARS repository')
        w.lane = w.commit
        git(w.clone, 'checkout', '-q', '-b', 'other-lane')   # a lane commit off to the side; HEAD comes back
        write(w.clone / 'gars/_system/claims/package_run.py', '# another file\n')
        git(w.clone, 'commit', '-q', '-am', 'another package_run')
        w.lane = git(w.clone, 'rev-parse', 'HEAD')
        git(w.clone, 'checkout', '-q', w.commit)
        self.assertEqual(w.harvest(out='h2').returncode, 0)
        self.refused(w.render(harvest='h2'), 'is not the file at the lane commit')

    @staticmethod
    def edit_submit(w):
        path = w.stage / 'submit.sh'
        write(path, path.read_text().replace('    $RESUME', '    --skip_trimming true $RESUME'))
        lines = [l for l in path.read_text().splitlines() if not l.startswith('# idempotency_key=')]
        write(path, '\n'.join(lines) + '\n')

    @staticmethod
    def link_a_folder(w):
        target = write(w.root / 'elsewhere' / 'x.csv', 'x\n').parent
        os.symlink(str(target), str(w.project / '01_samplesheets' / 'linked'))

    @staticmethod
    def reapprove(w):
        write(w.plan, '# Plan\n\nAnother plan.\n')
        store = w.clone / '.gars-approvals'
        for old in store.iterdir():
            old.unlink()
        identity = str(w.plan.resolve())
        write(store / (sha(identity.encode('utf-8')) + '.json'), json.dumps({
            'actor': ACTOR, 'expiry': '2026-10-13T12:00:00Z', 'plan_path': identity,
            'plan_sha256': sha(w.plan.read_bytes()), 'timestamp': '2026-10-12T12:00:00Z'}, sort_keys=True))

    @staticmethod
    def absolute_link(w):
        peaks = w.stage / 'run/results/bwa/merged_library/macs2/narrow_peak'
        os.symlink('/opt/private-lab/refs/genome.fa', str(peaks / 'genome.fa'))
        manifest = json.loads(w.manifest_path.read_text())
        rows = [{k: r[k] for k in ('type', 'role', 'path')} for r in __import__('resolve_artifact').read_outputs(
            w.stage / 'OUTPUTS.tsv')[0]]
        write(w.stage / 'OUTPUTS.tsv', '# type\trole\tpath\n' + ''.join('%s\t%s\t%s\n' % (r['type'], r['role'], r['path'])
                                                                       for r in rows))
        manifest['outputs'] = wl.complete_output_index(w.stage)
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    @staticmethod
    def shift_row(w):
        sheet = w.project / '01_samplesheets/atacseq_bulk_samplesheet.csv'
        config = w.project / '_config/atacseq_bulk.yaml'
        lines = sheet.read_text().splitlines(True)
        write(sheet, ''.join(lines[:-1]))
        write(config, lines[-1] + config.read_text())

    @staticmethod
    def skip_worktree(w):
        path = w.clone / 'gars/_system/wrapperlib.py'
        write(path, path.read_text() + '\n# edited\n')
        git(w.clone, 'update-index', '--skip-worktree', 'gars/_system/wrapperlib.py')

    @staticmethod
    def controlled_dataset(w):
        write(w.project / '00_data' / 'dataset.tsv', 'purpose\tdata_class\nfixture\tcontrolled\n')
        manifest = json.loads(w.manifest_path.read_text())
        manifest['data_class'] = 'public'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        shutil.rmtree(str(w.project / '02_bioinformatics'))

    @staticmethod
    def edit_params(w):
        manifest = json.loads(w.manifest_path.read_text())
        manifest['params']['macs_gsize'] = '12157105'
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))

    def test_a_private_data_class_is_refused(self):
        self.refused(self.world(data_class='controlled').harvest(), 'not public')

    def test_every_render_refusal(self):
        cases = {
            'an index parameter': ('an index that is not in the package', {'index_param': True}, None),
            'a private registry image': ('a stranger cannot pull', {'private_image': True}, None),
            'a Nextflow version off the lock': ('gars-nxf lock', {'nextflow': '23.10.1'}, None),
            'a branch URL': ('not pinned to a commit', {}, lambda w: write(w.sources, w.sources.read_text().replace(
                '/%s/testdata' % TEST_DATASETS, '/atacseq/testdata', 1))),
            'an input checksum off its pin': ('differs from the pinned source', {}, lambda w: write(
                w.sources, re.sub(r'\t[0-9a-f]{64}\t', '\t' + 'a' * 64 + '\t', w.sources.read_text(), count=1))),
            'a tolerance entry with no cause': ('lacks a declared mode', {}, lambda w: write(w.tolerances, json.dumps(
                {'entries': [{'stage': STAGE, 'members': ['x'], 'mode': 'presence', 'origin': 'pass-1',
                              'evidence': 'e'}]}))),
            'a tolerance entry for no member': ('names a member the run did not record', {}, lambda w: write(
                w.tolerances, json.dumps({'entries': [{'stage': STAGE, 'members': ['run/results/none'],
                                                       'mode': 'presence', 'origin': 'pass-1', 'cause': 'c',
                                                       'evidence': 'e'}]}))),
            'a harvest with a path its map misses': ('survived masking', {}, self.drop_workspace_prefix),
            'a manifest edited after harvest': ('another GARS commit', {}, self.edit_harvested_commit),
            'an output holding the bucket': ('its recorded sha256 would confirm', {}, self.bucket_in_output),
            'lane text quoting a masked file\'s sha256': ('the sha256 of a file holding a masked value', {},
                                                          self.oracle_in_evidence),
        }
        for name, (words, options, damage) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world(**options)
                h = w.harvest()
                self.assertEqual(h.returncode, 0, h.stderr.decode())
                if damage:
                    damage(w)
                self.refused(w.render(), words)
                self.assertFalse((w.root / 'package').exists())

    @staticmethod
    def drop_workspace_prefix(w):
        path = w.root / 'harvest' / 'HARVEST.json'
        record = json.loads(path.read_text())
        record['prefixes'] = []
        path.write_text(json.dumps(record))

    @staticmethod
    def oracle_in_evidence(w):
        """A tolerance entry's evidence is copied into the package; one quoting the sha256 of the
        unmasked samplesheet would let a reader confirm a guessed path."""
        digest = sha((w.project / '01_samplesheets/atacseq_bulk_samplesheet.csv').read_bytes())
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': ['run/results/multiqc/narrow_peak/multiqc_report.html'], 'mode': 'presence',
            'origin': 'pass-1', 'cause': 'the report embeds its run time', 'evidence': 'samplesheet ' + digest}]}))

    @staticmethod
    def bucket_in_output(w):
        """As if MultiQC had printed the S3 work folder: the harvested copy holds the bucket."""
        write(w.root / 'harvest/project' / STAGE_REL / 'run/results/multiqc/narrow_peak/multiqc_report.html',
              '<html>s3://%s/work</html>\n' % BUCKET)

    @staticmethod
    def edit_harvested_commit(w):
        path = w.root / 'harvest' / 'project' / STAGE_REL / 'reproducibility' / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['gars_commit'] = 'e' * 40
        path.write_text(json.dumps(manifest))

    def test_a_gitleaks_finding_refuses_and_writes_nothing(self):
        w = self.world()
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(env={'FAKE_GITLEAKS_EXIT': '1'}), 'gitleaks found a finding')
        self.assertFalse((w.root / 'package').exists())
        self.assertEqual([p.name for p in w.root.iterdir() if p.name.startswith('.package-')], [])


class Privacy(PackageCase):
    def test_no_path_bucket_uri_or_account_id_survives(self):
        w, package = self.built()
        self.assertFalse((package / 'code' / STAGE / 'submit.sh').exists())   # unbound by any record (h2 M1)
        # The masker itself, on the harvested submit.sh, which holds the S3 work folder and its account id.
        tool = module(TOOL, 'package_run_masker')
        record = json.loads((w.root / 'harvest/HARVEST.json').read_text())
        self.assertIn(BUCKET, record['secrets']['buckets'])
        self.assertIn(ACCOUNT, record['secrets']['accounts'])
        masked = tool.Masker(record).mask((w.root / 'harvest/project' / STAGE_REL / 'submit.sh').read_text())
        self.assertIn('s3://<BUCKET>/work/yeast-atacseq_bulk', masked)
        self.assertIn('<WORKSPACE>', masked)
        self.assertNotIn(ACCOUNT, masked)
        self.assertNotIn(str(w.root), masked)
        for rel, data in package_files(package).items():
            text = data.decode('utf-8', 'replace')
            for value in (ACCOUNT, BUCKET, str(w.root), '/Users/'):
                self.assertNotIn(value, text, rel)
            self.assertIsNone(re.search(r'/home/(?!conda/)', text), rel)   # conda's build prefix, in the pip lock
            self.assertIsNone(re.search(r'(?i)s3://(?!<BUCKET>)', text), rel)
            self.assertIsNone(re.search(r'(?<![0-9A-Fa-f])[0-9]{12}(?![0-9A-Fa-f])', text), rel)

    def test_no_sha256_of_a_file_holding_a_masked_value_is_printed(self):
        w, package = self.built()
        holders = [w.stage / 'submit.sh', w.stage / 'reproducibility/commands.sh', w.manifest_path,
                   w.project / '01_samplesheets/atacseq_bulk_samplesheet.csv', w.project / '_config/atacseq_bulk.yaml',
                   w.project / '_config/executor.yaml']
        digests = [sha(p.read_bytes()) for p in holders]
        digests.append(json.loads(w.manifest_path.read_text())['idempotency_key'])
        for rel, data in package_files(package).items():
            for digest in digests:
                self.assertNotIn(digest, data.decode('utf-8', 'replace'), rel)
        record = json.loads((package / 'records' / (STAGE + '.manifest.json')).read_text())
        withheld = [item['field'] for item in record['withheld_fields']]
        reasons = dict((item['field'], item['reason']) for item in record['withheld_fields'])
        for field in ('command.sha256', 'config_sha256', 'samplesheet_sha256', 'idempotency_key'):
            self.assertEqual(reasons[field], 'it hashes a file holding values the package masks', field)
        # the design check holds no masked value: its reason must say so, never claim an oracle
        self.assertEqual(reasons['design_check.sha256'], 'the file it hashes is not in this package')

    def test_the_approver_is_never_named(self):
        w, package = self.built(stage03=True)
        for rel, data in package_files(package).items():
            self.assertNotIn(ACTOR, data.decode('utf-8', 'replace'), rel)
        approval = list(csv.DictReader(io.StringIO((package / 'params/approval.tsv').read_text()), delimiter='\t'))
        self.assertEqual(approval[0]['plan_sha256'], sha(w.plan.read_bytes()))
        self.assertEqual((package / ('params/custom.01_followup.PLAN.md')).read_bytes(), w.plan.read_bytes())

    def test_a_plan_changed_after_approval_is_refused(self):
        w = self.world(stage03=True)
        self.assertEqual(w.harvest().returncode, 0)
        write(w.root / 'harvest/project/03_custom_analysis/01_followup/PLAN.md', '# Plan\n\nAnother plan.\n')
        self.refused(w.render(), 'R-073')
        write(w.plan, '# Plan\n\nAnother plan.\n')
        self.refused(w.harvest(out='h2'), 'R-073')


class Labels(PackageCase):
    def test_every_cell_carries_one_of_the_defined_labels(self):
        w, package = self.built()
        seen = 0
        for path in sorted(package.rglob('*.tsv')) + [package / 'code/GARS.txt']:
            rows = list(csv.DictReader(io.StringIO(path.read_text()), delimiter='\t'))
            if path.name == 'lane-sources.tsv':
                continue
            label_columns = [c for c in rows[0] if c == 'source' or c.endswith('_source')] if rows else []
            value_columns = [c for c in rows[0] if c + '_source' in rows[0]] if rows else []
            self.assertTrue(label_columns, path.name)
            for row in rows:
                for column in label_columns:
                    seen += 1
                    self.assertTrue(row[column].startswith(LABELS), (path.name, column, row[column]))
                for column in value_columns:
                    self.assertNotEqual(row[column], '', (path.name, column))
        self.assertGreater(seen, 40)

    def test_inputs_are_pinned_to_a_commit_and_labelled(self):
        w, package = self.built()
        rows = list(csv.DictReader(io.StringIO((package / 'inputs/inputs.tsv').read_text()), delimiter='\t'))
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertRegex(row['url'], r'^https://raw\.githubusercontent\.com/nf-core/test-datasets/[0-9a-f]{40}/')
            self.assertTrue(row['sha256_source'].startswith('computed at harvest'))
            self.assertTrue(row['url_source'].startswith('supplied at packaging from nf-core/test-datasets@'))
        sheet = (package / ('inputs/%s.samplesheet.csv' % STAGE)).read_text()
        self.assertIn('<INPUTS>/atac-a-r1_S1_L001_R1_001.fastq.gz', sheet)

    def test_not_recorded_reads_plainly_with_its_provenance_line(self):
        w, package = self.built()
        rows = list(csv.DictReader(io.StringIO((package / 'env/containers.tsv').read_text()), delimiter='\t'))
        self.assertEqual(sorted(r['digest'] for r in rows), ['not recorded', 'not recorded'])
        provenance = (package / 'PROVENANCE.md').read_text()
        self.assertIn('- %s: container digest of process NFCORE_ATACSEQ:ATACSEQ:FASTQ_ALIGN_BWA:BWA_MEM: not recorded '
                      'by the run.' % STAGE, provenance)
        self.assertIn('G1:', provenance)
        self.assertIn('digests', (package / 'README.md').read_text())

    def test_methods_is_the_renderers_own_output(self):
        w, package = self.built()
        expected = renderer.render([str(w.root / 'harvest/project' / STAGE_REL / 'reproducibility/manifest.json')])
        self.assertEqual((package / 'METHODS.md').read_text(), expected)

    def test_a_table_holding_a_path_is_left_out_and_named(self):
        w, package = self.built()
        small = sorted(p.relative_to(package / 'outputs/small').as_posix() for p in (package / 'outputs/small').rglob('*')
                       if p.is_file())
        self.assertIn(STAGE + '/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.saf', small)
        self.assertNotIn(STAGE + '/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.featureCounts.txt',
                         small)
        self.assertIn('consensus_peaks.mLb.clN.featureCounts.txt`: it holds a path', (package / 'PROVENANCE.md').read_text())


class Compare(PackageCase):
    def counts(self, package, rerun):
        return comparer.compare(str(package), str(rerun))['counts']

    def test_nested_outputs_are_compared_member_by_member_and_counted_once(self):
        w, package = self.built()
        rows = list(csv.DictReader(io.StringIO((package / 'outputs/outputs.tsv').read_text()), delimiter='\t'))
        distinct = set((r['stage'], comparer.member_path(r)) for r in rows)
        self.assertLess(len(distinct), len(rows))   # the peaks folder sits inside merged_library
        counts = self.counts(package, w.rerun_copy())
        self.assertEqual(counts, {'N': 4, 'n': len(distinct), 'M': 4, 'K': 0, 'P': 0, 'F': 0})

    def test_verify_exit_codes(self):
        w, package = self.built()
        rerun = w.rerun_copy()
        proc = run([sys.executable, package / 'verify.py', '--against', rerun])
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertIn(b'of 4 outputs (5 files), 4 matched exactly, 0 within the stated tolerance, 0 present but '
                      b'not byte-comparable, 0 differ (causes in PROVENANCE.md)', proc.stdout)
        bam = rerun / 'results' / STAGE / 'bwa/merged_library/atac-a.mLb.clN.sorted.bam'
        bam.write_bytes(b'BAM\x02')
        proc = run([sys.executable, package / 'verify.py', '--against', rerun])
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b'of 4 outputs (5 files), 3 matched exactly, 0 within the stated tolerance, 0 present but '
                      b'not byte-comparable, 1 differ', proc.stdout)   # the bam is a member of bam_genome only

    def test_presence_is_never_a_match(self):
        w = self.world()
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': ['run/results/multiqc/narrow_peak/multiqc_report.html'], 'mode': 'presence',
            'origin': 'S2b-preregistered', 'cause': 'the report embeds its run time', 'evidence': 'two probe runs'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        rerun = w.rerun_copy()
        write(rerun / 'results' / STAGE / 'multiqc/narrow_peak/multiqc_report.html', '<html>later</html>\n')
        counts = self.counts(package, rerun)
        self.assertEqual((counts['N'], counts['M'], counts['K'], counts['P'], counts['F']), (4, 3, 0, 1, 0))
        proc = run([sys.executable, package / 'verify.py', '--against', rerun])
        self.assertEqual(proc.returncode, 3, proc.stdout.decode())
        write(rerun / 'results' / STAGE / 'multiqc/narrow_peak/multiqc_report.html', '')
        self.assertEqual(self.counts(package, rerun)['F'], 1)

    def test_an_extra_file_in_a_recorded_folder_differs(self):
        w, package = self.built()
        rerun = w.rerun_copy()
        write(rerun / 'results' / STAGE / 'bwa/merged_library/macs2/narrow_peak/extra.bed', 'x\n')
        counts = self.counts(package, rerun)
        self.assertEqual(counts['F'], 2)   # narrow_peak and merged_library both hold it


class Verify(PackageCase):
    def damaged(self, damage):
        w, package = self.built()
        damage(w, package)
        return run([sys.executable, package / 'verify.py'])

    def test_verify_fails_with_a_named_line(self):
        cases = {
            'a flipped byte': ('does not match its SHA256SUMS line', lambda w, p: write(
                p / 'README.md', (p / 'README.md').read_text() + ' ')),
            'a missing file': ('is missing', lambda w, p: (p / 'REPRODUCE.md').unlink()),
            'an added file': ('not in SHA256SUMS', lambda w, p: write(p / 'extra.txt', 'x\n')),
            'a landing README for another digest': ('another package digest', lambda w, p: write(
                p.parent / 'README.md', 'package sha256 `%s`\n' % ('0' * 64))),
        }
        for name, (words, damage) in sorted(cases.items()):
            with self.subTest(name):
                proc = self.damaged(damage)
                self.assertEqual(proc.returncode, 1, proc.stdout.decode())
                self.assertIn(words, proc.stdout.decode())

    def test_a_changed_cross_link_fails_even_with_resummed_files(self):
        def edit(rel, old, new, count=1):
            def apply(w, package):
                path = package / rel
                text = path.read_text()
                self.assertIn(old, text)
                write(path, text.replace(old, new, count))
            return apply
        small = 'outputs/small/%s/bwa/merged_library/macs2/narrow_peak/consensus/consensus_peaks.mLb.clN.saf' % STAGE
        cases = {
            'the GARS commit': ('gars_commit differs', lambda w, p: edit(
                'code/GARS.txt', 'gars_commit\t' + w.commit, 'gars_commit\t' + 'a' * 40)(w, p)),
            'the pipeline commit': ('does not carry the pipeline commit',
                                    lambda w, p: edit('code/pipelines.tsv', w.pipeline_commit, 'a' * 40)(w, p)),
            'the release': ('does not carry the pipeline commit', edit('code/pipelines.tsv', '\t2.1.2\t', '\t2.1.3\t')),
            'the executor config': ('not the executor config', edit('env/run-executor.config', 'maxRetries    = 3',
                                                                    'maxRetries    = 4')),
            'an output hash': ('does not list exactly the members', lambda w, p: edit(
                'outputs/outputs.tsv', sha((w.stage / 'run/results/multiqc/narrow_peak/multiqc_report.html').read_bytes()),
                'b' * 64)(w, p)),
            'a small table': ('is not a recorded member', edit(small, 'peak1', 'peak2')),
            'the Methods citation': ('METHODS.md does not cite', lambda w, p: edit(
                'METHODS.md', w.commit, 'c' * 40, -1)(w, p)),
        }
        for name, (words, damage) in sorted(cases.items()):
            with self.subTest(name):
                w, package = self.built()
                damage(w, package)
                sums = ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                               for p in sorted(package.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS')
                write(package / 'SHA256SUMS', sums)
                proc = run([sys.executable, package / 'verify.py'])
                self.assertEqual(proc.returncode, 1, proc.stdout.decode())
                self.assertIn(words, proc.stdout.decode())

    def test_a_landing_readme_for_this_package_passes(self):
        w, package = self.built()
        digest = sha((package / 'SHA256SUMS').read_bytes())
        write(package.parent / 'README.md', 'package sha256 `%s`\n' % digest)
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertIn('the landing README names this package', proc.stdout.decode())


class Rerun(PackageCase):
    """rerun.sh with stand-ins for docker, java, curl and nextflow on PATH: the stand-ins log every call,
    so a test can show what ran and, after a refusal, that no pipeline started."""

    def setUp(self):
        super(Rerun, self).setUp()
        self.w, self.package = self.built()
        self.downloads = self.root / 'downloads'
        for name, (original, path) in self.w.fastqs.items():
            write(self.downloads / original, path.read_bytes())
        for name, path in self.w.refs.items():
            write(self.downloads / name, path.read_bytes())
        self.bin = self.root / 'fakebin'
        self.nf_log = self.root / 'nextflow.log'
        fakes = {
            'docker': '#!/bin/sh\n[ "$1" = info ] && echo "${FAKE_NCPU:-4} ${FAKE_MEM:-16500000000}"\n',
            'java': '#!/bin/sh\nexit 0\n',
            'curl': '#!/bin/sh\nwhile [ "$#" -gt 1 ]; do [ "$1" = -o ] && dest="$2"; shift; done\n'
                    'cp "%s/$(basename "$1")" "$dest"\n' % self.downloads,
            'nextflow': '#!/bin/sh\necho "NXF_VER=$NXF_VER NXF_SYNTAX_PARSER=${NXF_SYNTAX_PARSER:-} $*" >> "%s"\n'
                        % self.nf_log,
        }
        for name, text in fakes.items():
            write(self.bin / name, text)
            os.chmod(str(self.bin / name), 0o755)

    def rerun(self, out='out', **env):
        settings = {'PATH': '%s:/usr/bin:/bin' % self.bin}
        settings.update(env)
        return run(['bash', self.package / 'rerun.sh', '--out', self.root / out], env=settings)

    def test_a_rerun_runs_each_pipeline_pinned_by_commit(self):
        proc = self.rerun()
        self.assertEqual(proc.returncode, 0, proc.stdout.decode() + proc.stderr.decode())
        out = self.root / 'out'
        logged = self.nf_log.read_text()
        self.assertIn('NXF_VER=%s NXF_SYNTAX_PARSER=v1 run nf-core/atacseq -r %s -params-file %s/params/%s.params.json '
                      '-c %s/env/rerun.config -profile docker -work-dir %s/work/%s'
                      % (nextflow_pin(), self.w.pipeline_commit, out, STAGE, self.package, out, STAGE), logged)
        params = json.loads((out / 'params' / (STAGE + '.params.json')).read_text())
        self.assertEqual(params['outdir'], '%s/results/%s' % (out, STAGE))
        self.assertEqual(params['fasta'], '%s/refs/genome.fa' % out)
        self.assertIn('%s/inputs/atac-a-r1_S1_L001_R1_001.fastq.gz' % out,
                      (out / 'inputs' / (STAGE + '.samplesheet.csv')).read_text())

    def test_a_checksum_mismatch_refuses_before_any_pipeline(self):
        original = sorted(self.w.fastqs.values())[0][0]
        write(self.downloads / original, b'other bytes\n')
        proc = self.rerun()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode() + proc.stderr.decode())
        self.assertIn('computed at harvest', proc.stderr.decode())
        self.assertIn('no pipeline was started', proc.stderr.decode())
        self.assertFalse(self.nf_log.exists())

    def test_a_small_machine_or_a_used_folder_is_refused(self):
        for env, words in (({'FAKE_NCPU': '2'}, 'Docker has 2 CPUs'),
                           ({'FAKE_MEM': '8000000000'}, 'about 16 GB')):
            with self.subTest(words):
                proc = self.rerun(out='small-' + words.split()[-1], **env)
                self.assertEqual(proc.returncode, 2, proc.stderr.decode())
                self.assertIn(words, proc.stderr.decode())
        write(self.root / 'used' / 'x', 'x')
        proc = self.rerun(out='used')
        self.assertEqual(proc.returncode, 2)
        self.assertIn('is not empty', proc.stderr.decode())
        self.assertFalse(self.nf_log.exists())


NARROW = 'run/results/bwa/merged_library/macs2/narrow_peak'
COUNTS = NARROW + '/consensus/consensus_peaks.mLb.clN.featureCounts.txt'
PCA = NARROW + '/consensus/deseq2/consensus_peaks.mLb.clN.pca.vals.txt'
METRICS = NARROW + '/qc/atac-a_REP1.mLb.mkD.sorted.MarkDuplicates.metrics.txt'
REPORT = 'run/results/multiqc/narrow_peak/multiqc_report.html'


def add_members(w, files):
    """Write files into the stage's results and rebuild the recorded outputs, as collect would."""
    for rel, text in files.items():
        write(w.stage / rel, text)
    manifest = json.loads(w.manifest_path.read_text())
    manifest['outputs'] = wl.complete_output_index(w.stage)
    w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


S2B_FILES = {
    PCA: '"PC1"\t"PC2"\n"atac-a"\t-9.56516077694756\t4.78390491930369\n"atac-b"\t6.32531222161207\t2.3983488406228\n',
    METRICS: '## htsjdk\n# Started on: Mon Oct 05 21:27:08 GMT 2026\nLIBRARY\tREADS\nlib-a\t100\nlib-b\t200\n',
}


def s2b_entries(**override):
    entries = [
        dict(stage=STAGE, mode='column_matched_table', members=[COUNTS], origin='S2b-preregistered',
             cause='sample columns in completion order', evidence='S2b'),
        dict(stage=STAGE, mode='sign_aligned_numeric', members=[PCA], origin='S2b-preregistered',
             cause='arbitrary component sign', evidence='S2b'),
        dict(stage=STAGE, mode='sorted_table', drop_lines=['^# Started on: '], members=[METRICS],
             origin='S2b-preregistered', cause='start time line', evidence='S2b'),
        dict(stage=STAGE, mode='presence', members=[REPORT], origin='S2b-preregistered',
             cause='embeds its generation time', evidence='S2b'),
    ]
    for entry in entries:
        entry.update(override.get(entry['mode'], {}))
    return entries


class EarlyProbeModes(PackageCase):
    """The four modes the early probe measured (decision 0283), each on the kinds it is declared for only."""

    def world_with(self, entries, findings=None):
        w = self.world()
        add_members(w, S2B_FILES)
        body = {'entries': entries}
        if findings is not None:
            body['findings'] = findings
        write(w.tolerances, json.dumps(body))
        return w

    def rerun_like_s2b(self, w):
        rerun = w.rerun_copy()
        top = rerun / 'results' / STAGE
        counts = top / COUNTS[len('run/results/'):]
        rows = [l.split('\t') for l in counts.read_text().splitlines()]
        swapped = []
        for r in rows:   # move the last column first: the same table, columns in another order
            swapped.append('\t'.join(r if r[0].startswith('#') else [r[-1]] + r[:-1]))
        write(counts, '\n'.join(swapped) + '\n')
        write(top / PCA[len('run/results/'):],
              '"PC1"\t"PC2"\n"atac-b"\t6.32531222161208\t-2.3983488406228\n"atac-a"\t-9.56516077694755\t-4.78390491930369\n')
        write(top / METRICS[len('run/results/'):],
              '## htsjdk\n# Started on: Mon Oct 05 22:00:22 GMT 2026\nLIBRARY\tREADS\nlib-b\t200\nlib-a\t100\n')
        write(top / REPORT[len('run/results/'):], '<html>generated later</html>\n')
        return rerun

    def test_each_mode_matches_what_s2b_measured(self):
        w = self.world_with(s2b_entries())
        self.assertEqual(w.harvest().returncode, 0)
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        rerun = self.rerun_like_s2b(w)
        result = comparer.compare(str(w.root / 'package'), str(rerun))
        bad = [m for m in result['members'] if m['result'] not in ('match', 'present') and
               not m['result'].startswith(('within', 'match after '))]   # a normalised match names its mode
        self.assertEqual(bad, [])
        self.assertEqual({k: result['counts'][k] for k in 'NMKPF'}, {'N': 4, 'M': 0, 'K': 3, 'P': 1, 'F': 0})
        run_verify = run([sys.executable, w.root / 'package' / 'verify.py', '--against', rerun])
        self.assertEqual(run_verify.returncode, 3, run_verify.stdout.decode())

    def errata_world(self, member=None):
        w = self.world_with(s2b_entries())
        entry = s2b_entries()[0]
        errata = w.root / 'errata.json'
        write(errata, json.dumps({'corrections': [{'stage': entry['stage'], 'members': [member or entry['members'][0]],
                                                    'correction': 'a narrower cause', 'evidence': 'the record'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        return w, errata

    def render_with(self, w, errata, out='package'):
        return run([sys.executable, TOOL, 'render', '--harvest', w.root / 'harvest', '--gars-repo', w.clone,
                    '--sources', w.sources, '--tolerances', w.tolerances, '--errata', errata,
                    '--out', w.root / out], env=w.env)

    def test_errata_ship_hashed_print_under_corrections_and_change_no_count(self):
        w, errata = self.errata_world()
        plain = w.render(out='plain')
        self.assertEqual(plain.returncode, 0, plain.stderr.decode())
        proc = self.render_with(w, errata)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        package = w.root / 'package'
        self.assertEqual((package / 'outputs/package-errata.json').read_bytes(), errata.read_bytes())
        self.assertIn('outputs/package-errata.json', (package / 'SHA256SUMS').read_text())
        self.assertIn('## Corrections', (package / 'PROVENANCE.md').read_text())
        self.assertIn('a narrower cause', (package / 'PROVENANCE.md').read_text())
        self.assertEqual((package / 'outputs/outputs.tsv').read_bytes(),
                         (w.root / 'plain/outputs/outputs.tsv').read_bytes())   # no mode or member changes
        verified = run([sys.executable, package / 'verify.py'])
        self.assertEqual(verified.returncode, 0, verified.stdout.decode())
        rerun = self.rerun_like_s2b(w)
        a = comparer.compare(str(package), str(rerun))['counts']
        b = comparer.compare(str(w.root / 'plain'), str(rerun))['counts']
        self.assertEqual(a, b)   # the result line is unchanged

    def test_a_correction_naming_an_unknown_member_refuses(self):
        w, errata = self.errata_world(member='run/results/not/a/member.txt')
        self.refused(self.render_with(w, errata), 'which no finding or entry names')

    def test_verify_refuses_a_tampered_errata_file(self):
        w, errata = self.errata_world()
        self.assertEqual(self.render_with(w, errata).returncode, 0)
        package = w.root / 'package'
        target = package / 'outputs/package-errata.json'
        target.write_text(target.read_text().replace('a narrower cause', 'a stronger cause'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())   # SHA256SUMS
        body = json.loads(target.read_text())
        body['corrections'][0]['members'] = ['run/results/not/a/member.txt']
        target.write_text(json.dumps(body))
        write(package / 'SHA256SUMS', ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                                              for p in sorted(package.rglob('*'))
                                              if p.is_file() and p.name != 'SHA256SUMS'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())   # the cross-link, with sums re-summed
        self.assertIn('no finding or entry names', proc.stdout.decode())

    def test_rerun_note_counts_normalised_and_sign_aligned_matches_as_compare_does(self):
        """The landing README's line equals compare.py's own line for the same pass (the exemplar review's round 1: rerun-note
        had counted `match after <mode>` and sign-aligned members as differing, and had no test)."""
        w = self.world_with(s2b_entries())
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        rerun = self.rerun_like_s2b(w)
        artifacts = []
        for n in ('2', '3'):
            folder = w.root / ('pass' + n)
            proc = run([sys.executable, package / 'verify.py', '--against', rerun, '--table-out', folder])
            self.assertEqual(proc.returncode, 3, proc.stdout.decode())
            write(folder / 'package-sha256.txt', sha((package / 'SHA256SUMS').read_bytes()) + '\n')
            write(folder / 'machine.txt', '4-CPU 16 GB pad m5.xlarge\n2026-10-07\n')
            artifacts += ['--artifact', folder]
        expected = comparer.line(comparer.compare(str(package), str(rerun))['counts'])
        repo = w.root / 'repo'   # the landing's own shape: <repo>/reproduction/<name>/package
        placed = repo / 'reproduction' / 'yeast-atac' / 'package'
        shutil.copytree(str(package), str(placed))
        note = placed.parent / 'README.md'
        argv = [sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow', 'reproduction-yeast-atac.yml',
                '--out', note] + artifacts
        refused = run(argv)
        self.refused(refused, 'no workflow reproduction-yeast-atac.yml in this repository')   # the exemplar review's round 2, M7
        write(repo / '.github' / 'workflows' / 'reproduction-yeast-atac.yml', 'name: x\n')
        proc = run(argv)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(expected, note.read_text())
        self.assertIn('0 differ', expected)
        self.assertNotIn('fresh', note.read_text())   # nothing in the artifact records freshness
        self.assertIn('Re-run twice, each on its own 4-CPU 16 GB pad m5.xlarge', note.read_text())
        self.assertIn('no independent re-run', note.read_text())
        self.assertIn('Compared exactly', note.read_text())   # the landing review, M3: mode counts, named so
        # the landing review's round 2, m2: a pass whose outputs table is not its own members' rollup, or
        # whose members carry another mode than the package's, is refused, never printed
        doctored = w.root / 'pass3-doctored'
        shutil.copytree(str(w.root / 'pass3'), str(doctored))
        table_text = (doctored / 'outputs.tsv').read_text()
        lines_ = table_text.splitlines(True)
        cells = lines_[1].rstrip('\n').split('\t')
        cells[3] = str(int(cells[3]) + 1)
        lines_[1] = '\t'.join(cells) + '\n'
        (doctored / 'outputs.tsv').write_text(''.join(lines_))
        refused_table = run([sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow',
                             'reproduction-yeast-atac.yml', '--out', note, '--artifact', w.root / 'pass2',
                             '--artifact', doctored])
        self.refused(refused_table, 'is not the rollup of its own member table')
        (doctored / 'outputs.tsv').write_text(table_text)
        member_lines = (doctored / 'members.tsv').read_text().splitlines(True)
        head = member_lines[0].rstrip('\n').split('\t')
        first = member_lines[1].rstrip('\n').split('\t')
        first[head.index('mode')] = 'presence' if first[head.index('mode')] != 'presence' else 'exact'
        member_lines[1] = '\t'.join(first) + '\n'
        (doctored / 'members.tsv').write_text(''.join(member_lines))
        refused_mode = run([sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow',
                            'reproduction-yeast-atac.yml', '--out', note, '--artifact', doctored])
        self.refused(refused_mode, 'names another mode')
        # the check of that fold, MINOR 1: the extra counts appear only in outputs.tsv, so an output edited there
        # alone (its extra count and its verdict together) is refused when the edit moves a count, by the line
        # verify.py wrote beside the tables; an unreadable extra count is refused, never a traceback
        (doctored / 'members.tsv').write_text((w.root / 'pass3' / 'members.tsv').read_text())
        out_lines = table_text.splitlines(True)
        out_head = out_lines[0].rstrip('\n').split('\t')
        cells = out_lines[1].rstrip('\n').split('\t')
        self.assertNotEqual(cells[out_head.index('result')], 'F')
        cells[out_head.index('extra')] = '1'
        cells[out_head.index('result')] = 'F'
        (doctored / 'outputs.tsv').write_text(''.join([out_lines[0], '\t'.join(cells) + '\n'] + out_lines[2:]))
        refused_extra = run([sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow',
                             'reproduction-yeast-atac.yml', '--out', note, '--artifact', doctored])
        self.refused(refused_extra, 'do not give the result line verify.py wrote (result.txt)')
        cells[out_head.index('extra')] = 'x'
        (doctored / 'outputs.tsv').write_text(''.join([out_lines[0], '\t'.join(cells) + '\n'] + out_lines[2:]))
        refused_unreadable = run([sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow',
                                  'reproduction-yeast-atac.yml', '--out', note, '--artifact', w.root / 'pass2',
                                  '--artifact', doctored])
        self.refused(refused_unreadable, 'pass artifact 2 has an unreadable outputs table')
        (doctored / 'outputs.tsv').write_text(table_text)
        self.assertEqual(run([sys.executable, TOOL, 'rerun-note', '--package', placed, '--workflow',
                              'reproduction-yeast-atac.yml', '--out', note, '--artifact', doctored]).returncode, 0)
        agreed = list(csv.DictReader(io.StringIO((placed.parent / 'agreed-members.tsv').read_text()), delimiter='\t'))
        table = list(csv.DictReader(io.StringIO((w.root / 'pass2' / 'members.tsv').read_text()), delimiter='\t'))
        self.assertEqual(sorted((r['stage'], r['path'], r['mode'], r['result']) for r in agreed),
                         sorted((r['stage'], r['path'], r['mode'], r['result']) for r in table))   # M2

    def test_a_difference_beyond_the_mode_still_differs(self):
        cases = {
            'a count changed': (COUNTS, lambda t: t.replace('5\tpeak1', '6\tpeak1')),
            'a PCA value moved by 1e-6': (PCA, lambda t: t.replace('6.32531222161208', '6.32531322161208')),
            'a non-date line changed': (METRICS, lambda t: t.replace('lib-a\t100', 'lib-a\t101')),
            'a second line dropped as if a date': (METRICS, lambda t: t.replace('## htsjdk', '## other')),
        }
        for name, (member, edit) in sorted(cases.items()):
            with self.subTest(name):
                w = self.world_with(s2b_entries())
                self.assertEqual(w.harvest().returncode, 0)
                self.assertEqual(w.render().returncode, 0)
                rerun = self.rerun_like_s2b(w)
                path = rerun / 'results' / STAGE / member[len('run/results/'):]
                before = path.read_text()
                self.assertNotEqual(edit(before), before, 'the edit must change the file')
                write(path, edit(before))
                self.assertGreaterEqual(comparer.compare(str(w.root / 'package'), str(rerun))['counts']['F'], 1)

    def test_a_mode_never_applies_to_a_kind_it_is_not_declared_for(self):
        narrow = NARROW + '/atac-a.mLb.clN_peaks.narrowPeak'
        cases = {
            'sign_aligned_numeric on a narrowPeak': {'sign_aligned_numeric': {'members': [narrow]}},
            'column_matched_table on a narrowPeak': {'column_matched_table': {'members': [narrow]}},
            'presence on a result table': {'presence': {'members': [narrow]}},
        }
        for name, override in sorted(cases.items()):
            with self.subTest(name):
                entries = s2b_entries(**override)
                w = self.world_with(entries)
                self.assertEqual(w.harvest().returncode, 0)
                self.refused(w.render(), 'is not a kind the')
        # and at compare: a re-run file of another kind under a declared mode fails, never matches
        w = self.world_with(s2b_entries())
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        rerun = self.rerun_like_s2b(w)
        write(rerun / 'results' / STAGE / PCA[len('run/results/'):], b'\x1f\x8b\x08binary')
        member = [m for m in comparer.compare(str(w.root / 'package'), str(rerun))['members'] if m['path'] == PCA][0]
        self.assertEqual(member['result'], 'not a kind sign_aligned_numeric is declared for')

    def test_drop_lines_are_explicit_anchored_and_only_for_sorted_table(self):
        for name, override, words in (
                ('unanchored', {'sorted_table': {'drop_lines': ['Started on']}}, 'anchored'),
                ('missing', {'sorted_table': {'drop_lines': None}}, 'every sorted_table entry lists it'),
                ('on presence', {'presence': {'drop_lines': ['^x']}}, 'drop_lines belongs to a sorted_table')):
            with self.subTest(name):
                entries = s2b_entries(**override)
                for e in entries:
                    if e.get('drop_lines', 0) is None:
                        del e['drop_lines']
                w = self.world_with(entries)
                self.assertEqual(w.harvest().returncode, 0)
                self.refused(w.render(), words)

    def test_findings_are_stated_plainly_and_bound_to_recorded_members(self):
        homer = NARROW + '/atac-a.mLb.clN_peaks.narrowPeak'
        finding = dict(stage=STAGE, members=[homer], counted='differ', evidence='S2b',
                       finding="nf-core/atacseq 2.1.2's HOMER annotation picks between tied genes")
        w = self.world_with(s2b_entries(), [finding])
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        provenance = (w.root / 'package/PROVENANCE.md').read_text()
        self.assertIn("## Findings", provenance)
        self.assertIn("HOMER annotation picks between tied genes", provenance)
        for name, bad, words in (('unrecorded', dict(finding, members=[NARROW + '/none.txt']), 'finding names a member'),
                                 ('also an entry', dict(finding, members=[COUNTS]), 'both a finding'),
                                 ('not counted', dict(finding, counted='match'), 'counted: differ')):
            with self.subTest(name):
                w = self.world_with(s2b_entries(), [bad])
                self.assertEqual(w.harvest().returncode, 0)
                self.refused(w.render(), words)


class StockLogins(PackageCase):
    """The coordinating session's ruling (a), 5 Oct 2026: the launch pad's stock login is not a private name; any other is."""

    def world_naming(self, user):
        w = self.world()
        manifest = json.loads(w.manifest_path.read_text())
        manifest['input_data_location']['dataset'] = '/home/%s/seqrun/atacseq' % user
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        add_members(w, {REPORT: '<html>launched in /home/%s/gars-launchpad/run by %s</html>\n' % (user, user)})
        return w

    def test_a_stock_login_in_a_multiqc_report_ships(self):
        w = self.world_naming('ubuntu')
        self.assertEqual(w.harvest().returncode, 0)
        # the stock login arms nothing; only the test folder's own home user may appear (CI's TMPDIR sits
        # under /home/runner/; the landing review, M1)
        own = module(TOOL, 'package_run_stock_own').record_users([str(w.root)])
        self.assertNotIn('ubuntu', own)
        self.assertEqual(json.loads((w.root / 'harvest/HARVEST.json').read_text())['secrets']['users'], own)
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn('`ubuntu`, the stock login', (w.root / 'package/PROVENANCE.md').read_text())

    def test_any_other_user_in_a_multiqc_report_is_refused(self):
        w = self.world_naming('jdoe-q7')
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'its recorded sha256 would confirm')

    def presence_report(self, text, presence=True):
        """The exemplar run, 6 Oct 2026: on the AWS Batch road MultiQC prints the S3 work folder, so the recorded
        report holds the runs bucket and the account id inside its name."""
        w = self.world()
        add_members(w, {REPORT: text})
        if presence:
            write(w.tolerances, json.dumps({'entries': [{
                'stage': STAGE, 'members': [REPORT], 'mode': 'presence', 'origin': 'S2b-preregistered',
                'cause': 'the report embeds its run time', 'evidence': 'S2b'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        return w

    def test_a_bucket_in_a_presence_report_ships_with_its_hash_withheld(self):
        w = self.presence_report('<html>work dir s3://%s/work/launchpad/repro-s3</html>\n' % BUCKET)
        digest = sha((w.stage / REPORT).read_bytes())
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        package = w.root / 'package'
        rows = [r for r in csv.DictReader(io.StringIO((package / 'outputs/outputs.tsv').read_text()), delimiter='\t')
                if r['output_path'] == REPORT]
        self.assertEqual([(r['recorded_sha256'], r['mode']) for r in rows], [('withheld', 'presence')])
        self.assertIn('withheld', rows[0]['recorded_sha256_source'])
        for path in package.rglob('*'):
            if path.is_file():
                self.assertNotIn(digest.encode(), path.read_bytes(), path)
                self.assertNotIn(BUCKET.encode(), path.read_bytes(), path)
        [record] = list((package / 'records').glob('*.manifest.json'))
        outputs = json.loads(record.read_text())['outputs']
        self.assertEqual([o['sha256'] for o in outputs if o['path'] == REPORT], ['withheld'])
        self.assertIn(REPORT, (package / 'PROVENANCE.md').read_text())
        verified = run([sys.executable, package / 'verify.py'])
        self.assertEqual(verified.returncode, 0, verified.stdout.decode())

    def test_a_bucket_in_an_exact_member_still_refuses(self):
        w = self.presence_report('<html>work dir s3://%s/work</html>\n' % BUCKET, presence=False)
        self.refused(w.render(), 'its recorded sha256 would confirm')

    def test_a_user_name_in_a_presence_report_still_refuses(self):
        w = self.world_naming('jdoe-q7')
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': [REPORT], 'mode': 'presence', 'origin': 'S2b-preregistered',
            'cause': 'the report embeds its run time', 'evidence': 'S2b'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'its recorded sha256 would confirm')

    def test_verify_refuses_a_withheld_hash_off_a_presence_row(self):
        w = self.presence_report('<html>work dir s3://%s/work</html>\n' % BUCKET)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        table = package / 'outputs/outputs.tsv'
        lines = table.read_text().splitlines(True)
        lines = [l.replace('\tpresence\t', '\texact\t') if l.split('\t')[2] == REPORT else l for l in lines]
        table.write_text(''.join(lines))
        sums = ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                       for p in sorted(package.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS')
        write(package / 'SHA256SUMS', sums)
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn('withheld', proc.stdout.decode())

    SUMMARY = 'run/results/bwa/merged_library/macs2/narrow_peak/qc/macs2_peak.mLb.clN.summary.txt'

    def test_a_decimal_with_twelve_fraction_digits_is_not_an_id(self):
        """The exemplar run, 6 Oct 2026: MACS2's peak summary printed a mean of 408.955439056357, whose twelve
        fraction digits the bounded sweep read as an account-shaped id."""
        w = self.world()
        add_members(w, {self.SUMMARY: 'Min.\tMean\tmeasure\n192\t408.955439056357\tlength\n'})
        self.assertEqual(w.harvest().returncode, 0)
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(list((w.root / 'package/outputs/small').rglob('macs2_peak.mLb.clN.summary.txt')))

    def test_a_bare_twelve_digit_run_in_a_table_still_refuses(self):
        w = self.world()
        add_members(w, {self.SUMMARY: 'owner\tmeasure\n987654321098\tlength\n'})
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'a 12-digit id')

    def test_a_presence_report_holding_a_user_name_beside_the_bucket_still_refuses(self):
        """The coordinating session's condition (a), 6 Oct 2026: only a file whose sole sensitive content is the runs
        bucket or the account id has its sha256 withheld; a second kind of value beside it refuses."""
        w = self.world_naming('jdoe-q7')
        add_members(w, {REPORT: '<html>work dir s3://%s/work, launched in /home/jdoe-q7/run</html>\n' % BUCKET})
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': [REPORT], 'mode': 'presence', 'origin': 'S2b-preregistered',
            'cause': 'the report embeds its run time', 'evidence': 'S2b'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'a user name')

    def test_a_presence_report_holding_a_user_name_beside_the_account_id_still_refuses(self):
        w = self.world_naming('jdoe-q7')
        add_members(w, {REPORT: '<html>account %s, launched in /home/jdoe-q7/run</html>\n' % ACCOUNT})
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': [REPORT], 'mode': 'presence', 'origin': 'S2b-preregistered',
            'cause': 'the report embeds its run time', 'evidence': 'S2b'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'a user name')

    def test_the_twelve_digit_sweep_catches_every_id_form_and_spares_only_a_fraction(self):
        """The coordinating session's condition (b), 6 Oct 2026: an account-shaped run is caught bare, inside an ARN,
        after a colon or a slash, at a line's start or end; only digits.digits fractions are exempt.
        A synthetic id, never a real one."""
        id_like = module(TOOL, 'package_run_bounded').id_like
        fake = '210987654321'
        caught = [fake, 'owner %s here' % fake, 'arn:aws:iam::%s:role/batch' % fake,
                  'arn:aws:s3:::bucket-%s' % fake, 'key:%s' % fake, 'path/%s/work' % fake,
                  '%s\tlength' % fake, 'value\t%s' % fake, 'line\n%s\nnext' % fake,
                  'bucket-%s' % fake, '"%s"' % fake, 'v%s' % fake, '%s.5' % fake, '-%s' % fake,
                  'bucket.%s' % fake, '.%s' % fake, 'host.%s.internal' % fake, 'a:.%s' % fake,
                  'us-east-1.%s' % fake, 'v1.2.%s' % fake, 'run1.%s' % fake, 'gars-runs-v1.%s' % fake,
                  's3://gars.v2.%s/work' % fake, '192.168.1.%s' % fake, 'x86_64.%s' % fake,
                  'sample_2.%s.bam' % fake, '1.2.%s' % fake, '408.%s.5' % fake]
        caught += ['1.5E+%s' % fake, '-3.0e-%s' % fake]   # review round 2, m3: an exponent is not a fraction
        for text in caught:
            self.assertEqual(id_like(text), fake, text)
        spared = ['408.%s' % fake, 'mean 0.%s\n' % fake, '\t7.%s\t' % fake, '-3.%se-05' % fake,
                  '"Mean": 408.%s,' % fake]
        for text in spared:
            self.assertIsNone(id_like(text), text)

    def presence_entry(self, w, member):
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': [member], 'mode': 'presence', 'origin': 'S2b-preregistered',
            'cause': 'a plot embeds its creation time', 'evidence': 'S2b'}]}))

    def test_every_presence_sha256_is_withheld_even_when_nothing_is_seen_in_it(self):
        """Review MAJOR 2 (6 Oct 2026): a byte search cannot see a bucket inside a compressed member,
        so no presence member's sha256 is published, whatever the search finds."""
        import gzip
        w = self.world()
        member = 'run/results/bwa/merged_library/deeptools/plotprofile/atac-a.computeMatrix.vals.mat.tab'
        blob = gzip.compress(('{"work": "s3://%s/work"}' % BUCKET).encode(), mtime=0)
        self.assertNotIn(BUCKET.encode(), blob)   # non-vacuous: the raw bytes hide the bucket
        clean = NARROW + '/qc/atac-b.mLb.clN.plots.pdf'
        clean_body = b'%PDF-1.4\nnothing sensitive at all\n'   # a presence member nothing is seen in
        add_members(w, {member: blob, clean: clean_body})
        write(w.tolerances, json.dumps({'entries': [{
            'stage': STAGE, 'members': [member, clean], 'mode': 'presence', 'origin': 'S2b-preregistered',
            'cause': 'a plot embeds its creation time', 'evidence': 'S2b'}]}))
        self.assertEqual(w.harvest().returncode, 0)
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        package = w.root / 'package'
        for digest in (sha(blob), sha(clean_body)):
            for path in package.rglob('*'):
                if path.is_file():
                    self.assertNotIn(digest.encode(), path.read_bytes(), path)
        rows = [r for r in csv.DictReader(io.StringIO((package / 'outputs/outputs.tsv').read_text()), delimiter='\t')
                if r['mode'] == 'presence']
        self.assertTrue(rows)
        self.assertEqual(set(r['recorded_sha256'] for r in rows), {'withheld'})
        self.assertFalse([p for p in (package / 'outputs').rglob('*computeMatrix.vals.mat.tab')])   # a table suffix, never shipped
        self.assertEqual(run([sys.executable, package / 'verify.py']).returncode, 0)

    def test_a_presence_table_never_ships_in_small(self):
        """A presence member with a table suffix is never copied into outputs/small/: its bytes would carry
        the hash the package withholds, and verify cross-checks small/ against recorded sha256."""
        w = self.world()
        import gzip
        member = NARROW + '/qc/atac-a.mLb.clN.summary.txt'   # gzip bytes under a table suffix
        add_members(w, {member: gzip.compress(b'measure\tvalue\nlength\t192\n', mtime=0)})
        self.presence_entry(w, member)
        self.assertEqual(w.harvest().returncode, 0)
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        package = w.root / 'package'
        self.assertFalse([p for p in (package / 'outputs/small').rglob('atac-a.mLb.clN.summary.txt')])
        self.assertEqual(run([sys.executable, package / 'verify.py']).returncode, 0)

    def test_a_withheld_member_withholds_its_directory_tree_hash(self):
        """Review MAJOR 1 (6 Oct 2026): a directory output's tree hash is a public function of its
        member list, so a withheld member must take its directory's tree hash with it."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        add_members(w, {member: '%%PDF-1.4\nwork dir s3://%s/work\n' % BUCKET})
        self.presence_entry(w, member)
        self.assertEqual(w.harvest().returncode, 0)
        recorded = json.loads(w.manifest_path.read_text())['outputs']
        trees = [o['sha256'].split(':', 1)[1] for o in recorded
                 if o.get('members') and any(o['path'] + '/' + m['path'] == member for m in o['members'])]
        self.assertTrue(trees)   # non-vacuous: the member sits in at least one directory output
        proc = w.render()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        package = w.root / 'package'
        for path in package.rglob('*'):
            if path.is_file():
                for tree in trees:
                    self.assertNotIn(tree.encode(), path.read_bytes(), path)
        [record] = list((package / 'records').glob('*.manifest.json'))
        shipped = json.loads(record.read_text())['outputs']
        self.assertTrue([o for o in shipped if o.get('members') and o['sha256'] == 'withheld'])

    def test_a_withheld_digest_repeated_in_another_field_refuses(self):
        """Review MINOR 2 (6 Oct 2026): the withheld digest is in the sweep's oracle set, so the same
        digest printed through any other allowlisted field refuses the render."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        body = '%%PDF-1.4\nwork dir s3://%s/work\n' % BUCKET
        add_members(w, {member: body})
        self.presence_entry(w, member)
        manifest = json.loads(w.manifest_path.read_text())
        manifest['predicate_facts']['echo'] = sha(body.encode())   # kept beside the run's own facts
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'the sha256 of a file holding a masked value')

    def echo_world(self, echo_of):
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        add_members(w, {member: '%PDF-1.4\nnothing sensitive here\n'})
        self.presence_entry(w, member)
        manifest = json.loads(w.manifest_path.read_text())
        manifest['predicate_facts']['echo'] = echo_of(manifest, member)
        w.manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        self.assertEqual(w.harvest().returncode, 0)
        return w

    def test_a_clean_presence_digest_repeated_in_another_field_refuses(self):
        w = self.echo_world(lambda m, member: sha(b'%PDF-1.4\nnothing sensitive here\n'))
        self.refused(w.render(), 'the sha256 of a file holding a masked value')

    def test_a_withheld_tree_hash_repeated_in_another_field_refuses(self):
        def tree(m, member):
            return [o['sha256'] for o in m['outputs']
                    if o.get('members') and any(o['path'] + '/' + x['path'] == member for x in o['members'])][0]
        w = self.echo_world(tree)
        self.refused(w.render(), 'the sha256 of a file holding a masked value')

    def test_an_unread_large_exact_member_refuses(self):
        """Review round 2, MAJOR (6 Oct 2026): a member over 5 MB harvested without --copy-large was never
        read for the bucket or the account id, so its sha256 is never printed: render refuses."""
        w = self.world()
        add_members(w, {REPORT: '<html>work dir s3://%s/work</html>\n' % BUCKET + 'x' * (6 * 1000 * 1000)})
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'was not harvested')

    def test_an_unread_large_presence_member_refuses_too(self):
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        add_members(w, {member: '%PDF-1.4\n' + 'x' * (6 * 1000 * 1000)})
        self.presence_entry(w, member)
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'was not harvested')   # its presence form needs its bytes, so unread refuses too

    def test_a_bucket_inside_a_gzip_exact_member_refuses(self):
        """Review round 2, m1: an exact-mode gzip member is read in its decompressed stream too."""
        import gzip
        w = self.world()
        member = 'run/results/bwa/merged_library/deeptools/atac-a.computeMatrix.mat.gz'
        blob = gzip.compress(('work s3://%s/work\n' % BUCKET).encode(), mtime=0)
        self.assertNotIn(BUCKET.encode(), blob)
        add_members(w, {member: blob})
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'its recorded sha256 would confirm')

    def test_the_dashed_account_form_is_swept(self):
        """Review round 2, m6: the console's dddd-dddd-dddd form of the armed account id refuses."""
        w = self.world()
        add_members(w, {NARROW + '/qc/note.mLb.clN.summary.txt':
                        'account %s-%s-%s\n' % (ACCOUNT[:4], ACCOUNT[4:8], ACCOUNT[8:])})
        self.assertEqual(w.harvest().returncode, 0)
        self.refused(w.render(), 'an account id')

    def test_verify_refuses_a_printed_presence_hash_and_a_kept_tree_hash(self):
        """Review round 2, m4: verify enforces both directions of the withheld rule."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        body = '%PDF-1.4\nplain\n'
        add_members(w, {member: body})
        self.presence_entry(w, member)
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        recorded = json.loads(w.manifest_path.read_text())['outputs']

        def resum():
            write(package / 'SHA256SUMS', ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                                                  for p in sorted(package.rglob('*'))
                                                  if p.is_file() and p.name != 'SHA256SUMS'))
        table = package / 'outputs/outputs.tsv'
        original = table.read_text()
        table.write_text(original.replace('withheld', sha(body.encode()), 1))
        resum()
        self.assertEqual(run([sys.executable, package / 'verify.py']).returncode, 1)
        table.write_text(original)
        [record] = list((package / 'records').glob('*.manifest.json'))
        shipped = json.loads(record.read_text())
        tree = dict((o['path'], o['sha256']) for o in recorded if o.get('members'))
        for o in shipped['outputs']:
            if o.get('members') and o['sha256'] == 'withheld':
                o['sha256'] = tree[o['path']]
        record.write_text(json.dumps(shipped, indent=2, sort_keys=True) + '\n')
        resum()
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())

    def test_verify_refuses_a_consistent_printed_presence_hash(self):
        """R5 alone: outputs.tsv and the records both print the presence member's sha256."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.plots.pdf'
        body = '%PDF-1.4\nplain\n'
        add_members(w, {member: body})
        self.presence_entry(w, member)
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        digest = sha(body.encode())
        table = package / 'outputs/outputs.tsv'
        table.write_text('\n'.join(l.replace('\twithheld\t', '\t%s\t' % digest) if member.split('/')[-1] in l else l
                                    for l in table.read_text().split('\n')))
        [record] = list((package / 'records').glob('*.manifest.json'))
        shipped = json.loads(record.read_text())
        for o in shipped['outputs']:
            for m in o.get('members') or []:
                if (o['path'] + '/' + m['path']) == member:
                    m['sha256'] = digest
        record.write_text(json.dumps(shipped, indent=2, sort_keys=True) + '\n')
        write(package / 'SHA256SUMS', ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                                              for p in sorted(package.rglob('*'))
                                              if p.is_file() and p.name != 'SHA256SUMS'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn('must read withheld', proc.stdout.decode())

    def test_verify_checks_every_row_of_a_member_listed_twice(self):
        """R7 alone: an exact member two nested outputs share is listed twice; an edit to the first row fails."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.frip.txt'
        add_members(w, {member: 'frip\t0.42\n'})
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        table = package / 'outputs/outputs.tsv'
        lines = table.read_text().split('\n')
        hits = [i for i, l in enumerate(lines) if l.split('\t')[3:4] and l.split('\t')[2] + '/' + l.split('\t')[3] == member]
        self.assertEqual(len(hits), 2)   # non-vacuous: the member is listed under two directory outputs
        cells = lines[hits[0]].split('\t')
        cells[4] = '0' * 64
        lines[hits[0]] = '\t'.join(cells)
        table.write_text('\n'.join(lines))
        write(package / 'SHA256SUMS', ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                                              for p in sorted(package.rglob('*'))
                                              if p.is_file() and p.name != 'SHA256SUMS'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())

    def test_a_history_naming_a_bare_bucket_keeps_its_hash_out_of_methods(self):
        """Review round 2, m2, pinned on a stage-03 world (the coordinating session's ruling, 6 Oct 2026): a bucket armed
        with no account id in its name, written bare in HISTORY.md, marks that file as holding a masked
        value, so the sha256 METHODS.md would print for it never leaves in the package."""
        global BUCKET
        saved = BUCKET
        BUCKET = 'gars-demo-runs-east'
        try:
            w = self.world(stage03=True)
            history = w.project / 'HISTORY.md'
            history.write_bytes(b'# History\n\nRun outputs were kept in bucket ' + BUCKET.encode() + b'.\n')
            h = w.harvest()
            self.assertEqual(h.returncode, 0, h.stderr.decode())
            secrets = json.loads((w.root / 'harvest/HARVEST.json').read_text())['secrets']
            self.assertIn(BUCKET, secrets['buckets'])   # non-vacuous: the bare bucket is armed
            self.assertFalse([a for a in secrets['accounts'] if a in BUCKET])   # and no account sits inside it
            digest = sha(history.read_bytes())
            proc = w.render()
            if proc.returncode == 0:
                for path in (w.root / 'package').rglob('*'):
                    if path.is_file():
                        self.assertNotIn(digest.encode(), path.read_bytes(), path)
            else:
                self.assertIn('the sha256 of a file holding a masked value', proc.stderr.decode())
        finally:
            BUCKET = saved

    def test_the_stock_list_is_exactly_the_ruled_one(self):
        tool = module(TOOL, 'package_run_stock')
        self.assertEqual(sorted(tool.STOCK_LOGINS), ['root', 'ubuntu'])
        self.assertEqual(tool.record_users(['/home/ubuntu/x', '/home/ec2-user/y', '/Users/root/z']), ['ec2-user'])


class ExemplarReviewRound1(PackageCase):
    """The exemplar review's round 1 fixes (6 Oct 2026)."""

    def test_render_names_the_commit_whose_package_run_rendered_it(self):
        w = self.world()
        self.assertEqual(w.harvest().returncode, 0)
        commit = w.lane or w.commit
        proc = run([sys.executable, TOOL, 'render', '--harvest', w.root / 'harvest', '--gars-repo', w.clone,
                    '--render-commit', commit, '--sources', w.sources, '--tolerances', w.tolerances,
                    '--out', w.root / 'package'], env=w.env)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        gars = dict((r['field'], r) for r in csv.DictReader(
            io.StringIO((w.root / 'package/code/GARS.txt').read_text()), delimiter='\t'))
        self.assertEqual(gars['render_commit']['value'], commit)
        self.assertEqual(gars['render_package_run_sha256']['value'], sha(TOOL.read_bytes()))

    def test_a_render_commit_holding_another_package_run_refuses(self):
        w = self.world()
        self.assertEqual(w.harvest().returncode, 0)
        proc = run([sys.executable, TOOL, 'render', '--harvest', w.root / 'harvest', '--gars-repo', w.clone,
                    '--render-commit', '0' * 40, '--sources', w.sources, '--tolerances', w.tolerances,
                    '--out', w.root / 'package'], env=w.env)
        self.refused(proc, 'is not in the GARS repository')
        # a commit that exists but holds another package_run.py: on a side branch of the clone
        base = git(w.clone, 'rev-parse', 'HEAD')
        git(w.clone, 'checkout', '-q', '-b', 'other')
        target = w.clone / 'gars/_system/claims/package_run.py'
        write(target, TOOL.read_bytes() + b'# another file\n')
        git(w.clone, 'add', '-f', 'gars/_system/claims/package_run.py')
        git(w.clone, 'commit', '-qm', 'another package_run.py')
        other = git(w.clone, 'rev-parse', 'HEAD')
        git(w.clone, 'checkout', '-q', base)
        proc = run([sys.executable, TOOL, 'render', '--harvest', w.root / 'harvest', '--gars-repo', w.clone,
                    '--render-commit', other, '--sources', w.sources, '--tolerances', w.tolerances,
                    '--out', w.root / 'package2'], env=w.env)
        self.refused(proc, 'is not the file at the render commit it names')

    def test_an_unlabelled_source_cell_refuses(self):
        tool = module(TOOL, 'package_run_labels')
        with self.assertRaises(tool.Refusal):
            tool.tsv(('value', 'value_source'), [{'value': 'x', 'value_source': 'from somewhere'}])
        self.assertTrue(tool.tsv(('value', 'value_source'), [{'value': 'x', 'value_source': 'withheld: x'}]))

    def test_verify_checks_the_mode_of_every_row_of_a_member_listed_twice(self):
        """The exemplar review's round 1, m3: a mode edit on the first of two rows of a nested member fails offline."""
        w = self.world()
        member = NARROW + '/qc/atac-a.mLb.clN.frip.txt'
        add_members(w, {member: 'frip\t0.42\n'})
        self.assertEqual(w.harvest().returncode, 0)
        self.assertEqual(w.render().returncode, 0)
        package = w.root / 'package'
        table = package / 'outputs/outputs.tsv'
        lines = table.read_text().split('\n')
        hits = [i for i, l in enumerate(lines) if len(l.split('\t')) > 3 and
                l.split('\t')[2] + '/' + l.split('\t')[3] == member]
        self.assertEqual(len(hits), 2)   # non-vacuous: listed under two directory outputs
        cells = lines[hits[0]].split('\t')
        cells[6] = 'sorted_table'
        lines[hits[0]] = '\t'.join(cells)
        table.write_text('\n'.join(lines))
        write(package / 'SHA256SUMS', ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                                              for p in sorted(package.rglob('*'))
                                              if p.is_file() and p.name != 'SHA256SUMS'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())

    def test_a_normalised_match_is_reported_apart_from_a_byte_identical_one(self):
        """The exemplar review's round 1, M2: compare's member result names the mode a normalised match needed."""
        tool = module(CLAIMS / 'package' / 'compare.py', 'compare_normalised')
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'x.tsv'
            path.write_bytes(b'b\ta\n1\t2\n')
            form = tool.sorted_table_form(path.read_bytes(), [])
            row = {'member_path': 'x.tsv', 'normalised': 'sha256:' + sha(form), 'entry': {'drop_lines': []}}
            ok, result, _ = tool.MODES['sorted_table'](str(path), row)
            self.assertTrue(ok, result)
            self.assertEqual(result, 'match after sorted_table')


class ExemplarReviewRound2(PackageCase):
    """The exemplar review's round 2: its two check-loosening MINORs (6 Oct 2026), fixed under the stop rule."""

    PCA = ('#id: pca\n#plot_type: scatter\n"sample"\t"PC1: 58% variance"\t"PC2: 24% variance"\n'
           '"atac-b_REP1"\t-7.23271284930167\t0.170213954159205\n"atac-a_REP1"\t3.9928642939662\t-7.35246771408569\n')

    def test_sign_aligned_refuses_a_nan_and_an_injected_row(self):
        tool = module(CLAIMS / 'package' / 'compare.py', 'compare_numeric')
        recorded = tool.numeric_values(self.PCA.encode())
        self.assertEqual(sorted(recorded), ['atac-a_REP1', 'atac-b_REP1'])   # the real shape still reads
        nan = self.PCA.replace('-7.23271284930167', 'NaN')
        with self.assertRaises(ValueError):
            tool.numeric_values(nan.encode())
        injected = self.PCA + 'INJECTED\tnot-a-number\tgarbage\n'
        with self.assertRaises(ValueError):
            tool.numeric_values(injected.encode())
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'consensus_peaks.mLb.clN.pca.vals.txt'
            path.write_bytes(nan.encode())
            row = {'member_path': path.name, 'normalised': json.dumps(recorded), 'entry': {}}
            ok, result, _ = tool.MODES['sign_aligned_numeric'](str(path), row)
            self.assertFalse(ok, result)

    def test_verify_refuses_a_linked_folder(self):
        w, package = self.built()
        import tempfile
        outside = Path(tempfile.mkdtemp(dir=str(w.root)))
        write(outside / 'x.txt', 'x\n')
        os.symlink(str(outside), str(package / 'outputs' / 'linked'))
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn('is a link', proc.stdout.decode())


class Goldens(PackageCase):
    """A complete and a sparse package, normalised for the values a fixture world cannot hold still:
    its GARS commit, the pipeline commit and package_run.py's own sha256. SHA256SUMS is derived and
    left out. PACKAGE_GOLDENS_WRITE=1 rewrites them, to be read in review like any other diff."""

    def normalised(self, w, package):
        record = json.loads((w.root / 'harvest' / 'HARVEST.json').read_text())
        swaps = ((w.commit, '<GARS_COMMIT>'), (w.pipeline_commit, '<PIPELINE_COMMIT>'),
                 (record['package_run']['sha256'], '<PACKAGE_RUN_SHA256>'), (self.root.name, '<TEST_ROOT>'))
        files = {}
        for rel, data in package_files(package).items():
            if rel == 'SHA256SUMS':
                continue
            text = data.decode('utf-8')
            for old, new in swaps:
                text = text.replace(old, new)
            files[rel] = text
        return files

    def check(self, name, **options):
        w, package = self.built(**options)
        files = self.normalised(w, package)
        golden = FIXTURES / name
        if os.environ.get('PACKAGE_GOLDENS_WRITE') == '1':
            shutil.rmtree(str(golden), ignore_errors=True)
            for rel, text in files.items():
                write(golden / rel, text)
        expected = dict((p.relative_to(golden).as_posix(), p.read_text(encoding='utf-8'))
                        for p in sorted(golden.rglob('*')) if p.is_file())
        self.assertEqual(sorted(files), sorted(expected))
        for rel in sorted(files):
            self.assertEqual(files[rel], expected[rel], rel)

    def test_complete_package(self):
        self.check('complete')

    def test_sparse_package(self):
        self.check('sparse', sparse=True)

    def test_no_golden_file_is_ignored_by_git(self):
        names = [p.relative_to(REPO).as_posix() for p in sorted(FIXTURES.rglob('*')) if p.is_file()]
        proc = subprocess.run(['git', '-C', str(REPO), 'check-ignore', '--no-index'] + names,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.stdout.decode(), '', 'git would leave these golden files out')


if __name__ == '__main__':
    unittest.main()
