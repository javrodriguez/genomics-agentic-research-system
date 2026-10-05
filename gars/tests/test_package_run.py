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
LABELS = ('recorded at run', 'computed at harvest', 'supplied at packaging from ')
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
        write(self.clone / '.gitignore', 'gars/projects/*/\n__pycache__/\n.gars-approvals/\n')
        git(self.clone, 'init', '-q')
        git(self.clone, 'add', '-A')
        git(self.clone, 'commit', '-q', '-m', 'fixture clone')
        self.commit = git(self.clone, 'rev-parse', 'HEAD')
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
        submit = write(self.stage / 'submit.sh',
                       '#!/bin/bash\nset -euo pipefail\nWS="%s"\nsource "$WS/_system/gars-env.sh"\n'
                       'export NXF_SYNTAX_PARSER=v1\ncd "%s"\nnextflow run "%s" \\\n    -c "%s" \\\n'
                       '    -params-file "%s/params.yaml" \\\n    -work-dir "s3://%s/work/yeast-atacseq_bulk" \\\n'
                       '    $RESUME\n' % (self.clone / 'gars', self.stage, checkout, executor_config, self.stage, BUCKET))
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
        script = write(adir / 'analysis.py', 'print("peaks")\n')
        launcher = write(adir / 'launch.sh', '#!/bin/sh\npython3 analysis.py\n')
        write(adir / '.gars_submissions.jsonl', json.dumps({
            'script': str(script), 'script_sha256': sha(script.read_bytes()),
            'launcher': str(launcher), 'launcher_sha256': sha(launcher.read_bytes()),
            'job_id': '4242', 'executor': 'local'}) + '\n')
        store = self.clone / '.gars-approvals'
        store.mkdir(mode=0o700)
        identity = str(plan.resolve())
        write(store / (sha(identity.encode('utf-8')) + '.json'), json.dumps({
            'actor': ACTOR, 'expiry': '2026-10-10T12:00:00Z', 'plan_path': identity,
            'plan_sha256': sha(plan.read_bytes()), 'timestamp': '2026-10-09T12:00:00Z'}, sort_keys=True))
        self.plan = plan

    def lane_sources(self):
        lines = ['kind\tname\turl\tsha256\tsource']
        for name, (original, path) in sorted(self.fastqs.items()):
            lines.append('input\t%s\thttps://raw.githubusercontent.com/nf-core/test-datasets/%s/atacseq/testdata/%s\t%s\t'
                         'nf-core/test-datasets@%s:atacseq/testdata/%s'
                         % (name, TEST_DATASETS, original, sha(path.read_bytes()), TEST_DATASETS, original))
        for name, path in sorted(self.refs.items()):
            lines.append('reference\t%s\thttps://raw.githubusercontent.com/nf-core/test-datasets/%s/atacseq/reference/%s\t%s\t'
                         'nf-core/test-datasets@%s:atacseq/reference/%s'
                         % (name, TEST_DATASETS, name, sha(path.read_bytes()), TEST_DATASETS, name))
        return '\n'.join(lines) + '\n'

    def harvest(self, out='harvest', extra=()):
        return run([sys.executable, TOOL, 'harvest', '--gars', self.clone, '--project', self.project,
                    '--lane-commit', LANE, '--out', self.root / out] + list(extra), env=self.env)

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
                '/%s/atacseq/testdata' % TEST_DATASETS, '/atacseq/atacseq/testdata', 1))),
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
        submit = (package / 'code' / STAGE / 'submit.sh').read_text()
        self.assertIn('s3://<BUCKET>/work/yeast-atacseq_bulk', submit)
        self.assertIn('<WORKSPACE>', submit)
        for rel, data in package_files(package).items():
            text = data.decode('utf-8', 'replace')
            for value in (ACCOUNT, BUCKET, str(w.root), '/Users/'):
                self.assertNotIn(value, text, rel)
            self.assertIsNone(re.search(r'/home/(?!conda/)', text), rel)   # conda's build prefix, in the pip lock
            self.assertIsNone(re.search(r'(?i)s3://(?!<BUCKET>)', text), rel)
            self.assertIsNone(re.search(r'(?<![0-9A-Fa-f])[0-9]{12}(?![0-9A-Fa-f])', text), rel)
        provenance = (package / 'PROVENANCE.md').read_text()
        self.assertRegex(provenance, r'\| `<BUCKET>` \| [1-9][0-9]* \|')

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
    def test_every_cell_carries_one_of_three_labels(self):
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
        w, package = self.built()
        path = package / 'code/pipelines.tsv'
        write(path, path.read_text().replace(w.pipeline_commit, 'a' * 40))
        sums = ''.join('%s  %s\n' % (sha(p.read_bytes()), p.relative_to(package).as_posix())
                       for p in sorted(package.rglob('*')) if p.is_file() and p.name != 'SHA256SUMS')
        write(package / 'SHA256SUMS', sums)
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 1)
        self.assertIn('does not carry the pipeline commit', proc.stdout.decode())

    def test_a_landing_readme_for_this_package_passes(self):
        w, package = self.built()
        digest = sha((package / 'SHA256SUMS').read_bytes())
        write(package.parent / 'README.md', 'package sha256 `%s`\n' % digest)
        proc = run([sys.executable, package / 'verify.py'])
        self.assertEqual(proc.returncode, 0, proc.stdout.decode())
        self.assertIn('the landing README names this package', proc.stdout.decode())


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
