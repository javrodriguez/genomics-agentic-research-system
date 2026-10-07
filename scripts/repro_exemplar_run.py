#!/usr/bin/env python3
"""The reproduction package's exemplar run: GARS stages 00-02 on the yeast ATAC fixture with no model,
then harvest, render and verify, all on the machine that ran it, before teardown (decision 0281).

  python3 scripts/repro_exemplar_run.py --gars <public GARS clone> --expect-commit <40-hex>
      --fixtures <folder holding the 8 yeast ATAC FASTQs> --gen-executor <gen_executor_config.sh>
      --package-run <package_run.py> --lane-commit <40-hex> --gars-repo <git repo holding both commits>
      --sources <lane-sources.tsv> --tolerances <package-tolerances.json>
      --private-out <empty folder> --public-out <empty folder> --harvest-copy <empty folder>
      [--title yeast-atac] [--poll-seconds 60] [--max-wait-minutes 180]

Private and public material never share a folder (review h3-8): --private-out gets run.log and the
harvest, which hold the run's unmasked records; --public-out gets only the rendered package. The
harvest is copied to --harvest-copy (the operator's sync folder) the moment it exists, before render,
so a stop at any later step still leaves it to be carried off the machine (review h3-7).

Each step is the documented helper call the stage contracts name (stage00_register.py, stage01_samplesheet.py,
configure.py, the ATAC wrapper's check, prepare and collect, executorlib.py submit and status), with the answers
fixed for this fixture before its first run (4 October 2026); the model a navigation would run is `none`, and the run records it.
It never retries a failed step, never edits a record by hand, and stops at the first non-zero exit with the
step named. The machine's own lifetime (up, down) is the operator's, never this script's.
Every step and its exit code go to <out>/run.log; exit 0 when the package verified, 1 at the first failure,
2 when a precondition refuses before any stage runs, 3 usage. Standard library only, Python 3.6 or later.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ASSAY = 'atacseq_bulk'
SUBSTAGE = '02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper'
WRAPPER = '_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py'
# The fixture's design, fixed before its first run (4 October 2026): two conditions, two replicates each.
DESIGN = ('sample_id,condition,group,replicate\n'
          'atac-a-r1,a,atac-a,1\natac-a-r2,a,atac-a,2\natac-b-r1,b,atac-b,1\natac-b-r2,b,atac-b,2\n')
SAMPLES = ('atac-a-r1', 'atac-a-r2', 'atac-b-r1', 'atac-b-r2')
STAGE01_LINES = (('unit_of_replication', 'sample'), ('reference_release', 'R64-1-1'))
GENOME, PEAKS = 'R64-1-1', 'narrow'
MEMORY = ('  mem: 64G\n', '  mem: 8G\n')   # the local venue's memory rule, as the fixture's first run set it
TERMINAL = ('COMPLETED', 'FAILED', 'CANCELLED', 'ARTIFACT_MISSING')
# package_run.py's CLONE_IGNORED_OK, checked here before stage 00 so a clone harvest would refuse is
# refused before the paid run, not after it (a test holds the two equal).
CLONE_IGNORED_OK = ('gars/projects/', 'gars/data_sources.tsv', '.gars-approvals/')


class Stop(Exception):
    def __init__(self, message, code=1):
        Exception.__init__(self, message)
        self.code = code


class Run(object):
    def __init__(self, args):
        self.args = args
        self.private = Path(args.private_out).resolve()
        self.public = Path(args.public_out).resolve()
        self.harvest_copy = Path(args.harvest_copy).resolve()
        self.gars = Path(args.gars).resolve() / 'gars'
        self.project_rel = 'projects/' + args.title
        self.project = self.gars / self.project_rel
        self.log = None

    def note(self, text):
        line = '%s %s' % (datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), text)
        print(line, flush=True)
        with self.log.open('a', encoding='utf-8') as handle:
            handle.write(line + '\n')

    def call(self, step, argv, cwd=None, want_json=False):
        """One helper call; its exit code and output are logged, and anything but 0 stops the run."""
        self.note('step %s: %s' % (step, ' '.join(str(a) for a in argv)))
        proc = subprocess.run([str(a) for a in argv], cwd=str(cwd or self.gars), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT)
        text = proc.stdout.decode('utf-8', 'replace')
        with self.log.open('a', encoding='utf-8') as handle:
            handle.write(text if text.endswith('\n') or not text else text + '\n')
        self.note('step %s: exit %d' % (step, proc.returncode))
        if proc.returncode != 0:
            raise Stop('step %s exited %d; see %s' % (step, proc.returncode, self.log))
        if want_json:
            # executorlib prints one object indented over several lines (the exemplar run, 6 Oct); a helper that
            # prints notes first ends with its object, so the last line opening a parseable object wins.
            lines = text.strip().splitlines()
            for start in range(len(lines) - 1, -1, -1):
                if not lines[start].startswith('{'):
                    continue
                try:
                    value = json.loads('\n'.join(lines[start:]))
                except ValueError:
                    continue
                if isinstance(value, dict):
                    return value
            raise Stop('step %s printed no JSON object' % step)
        return text

    def git(self, *args):
        proc = subprocess.run(['git', '-C', str(self.gars.parent)] + list(args), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        return proc.stdout.decode('utf-8', 'replace').strip()

    def preconditions(self):
        args = self.args
        if not re.match(r'[0-9a-f]{40}\Z', args.expect_commit) or not re.match(r'[0-9a-f]{40}\Z', args.lane_commit):
            raise Stop('--expect-commit and --lane-commit are full 40-hex commits', 3)
        folders = (self.private, self.public, self.harvest_copy)
        if len(set(folders)) != 3 or any(a in b.parents for a in folders for b in folders):
            raise Stop('the private, public and copy folders must be three separate folders', 3)
        for folder in folders:
            if folder.exists() and any(folder.iterdir()):
                raise Stop('%s is not empty' % folder, 2)
        for folder in folders:
            folder.mkdir(parents=True, exist_ok=True)
        self.log = self.private / 'run.log'
        head = self.git('rev-parse', 'HEAD')
        if head != args.expect_commit:
            raise Stop('the GARS clone is at %s, not %s' % (head[:12], args.expect_commit[:12]), 2)
        for line in self.git('status', '--porcelain', '--untracked-files=all', '--ignored').splitlines():
            path = line[3:].strip('"')
            if line[:2] == '!!' and (path.startswith(CLONE_IGNORED_OK) or '__pycache__/' in '/' + path):
                continue
            raise Stop('the GARS clone is not clean (%s), and harvest would refuse it after the run' % line, 2)
        if self.project.exists():
            raise Stop('%s already exists; the exemplar starts from no project' % self.project_rel, 2)
        sources = self.gars / 'data_sources.tsv'
        fixtures = str(Path(args.fixtures).resolve())
        if not sources.is_file() or not any(line.split('\t')[:2] == [fixtures, 'public'] for line in
                                             sources.read_text(encoding='utf-8').splitlines()):
            raise Stop('gars/data_sources.tsv does not declare %s public (the operator writes it)' % fixtures, 2)
        found = sorted(p.name for p in Path(fixtures).iterdir() if p.name.endswith('.fastq.gz'))
        wanted = sorted('%s_S1_L001_R%s_001.fastq.gz' % (s, e) for s in SAMPLES for e in ('1', '2'))
        if found != wanted:
            raise Stop('the fixtures folder holds %d FASTQs, not the 8 the design names' % len(found), 2)
        for path in (args.gen_executor, args.package_run, args.sources, args.tolerances):
            if not Path(path).is_file():
                raise Stop('%s is missing' % path, 2)
        self.note('preconditions: GARS %s clean; fixtures 8 of 8; data_sources declares them public' % head)

    def edit_once(self, path, old, new, step):
        text = path.read_text(encoding='utf-8')
        if text.count(old) != 1:
            raise Stop('step %s: %s holds %r %d times, not once' % (step, path.name, old.strip(), text.count(old)))
        path.write_text(text.replace(old, new), encoding='utf-8')
        self.note('step %s: %s: %r -> %r' % (step, path.name, old.strip(), new.strip()))

    def stage00(self):
        py = sys.executable
        self.call('00.create', [py, '_system/stage00_register.py', 'create', '--title', self.args.title,
                                '--assays', ASSAY])
        self.call('00.link', [py, '_system/stage00_register.py', 'link', '--project', self.project_rel,
                              '--assay', ASSAY, '--source', Path(self.args.fixtures).resolve()])
        self.call('00.finalize', [py, '_system/stage00_register.py', 'finalize', '--project', self.project_rel,
                                  '--data-class', 'public', '--purpose', 'fixture', '--agreement-ref', 'none',
                                  '--model', 'none'])
        # finalize seeds samples.csv (the header and the sample ids, design columns empty) and keeps it
        # thereafter; the design is written after it, as the fixture's first run did.
        design = self.project / '00_data' / ASSAY / 'samples.csv'
        seeded = design.read_text(encoding='utf-8').splitlines() if design.is_file() else []
        if not seeded or seeded[0] != DESIGN.splitlines()[0] or sorted(l.split(',')[0] for l in seeded[1:]) != list(SAMPLES):
            raise Stop('step 00.design: the seeded samples.csv is not the header and the four samples of the design')
        design.write_text(DESIGN, encoding='utf-8')
        self.note('step 00.design: samples.csv written (the design\'s four rows)')

    def stage01(self):
        config = self.project / '_config' / (ASSAY + '.yaml')
        text = config.read_text(encoding='utf-8')
        for key, value in STAGE01_LINES:
            line = [l for l in text.splitlines(True) if l.startswith(key + ': <REQUIRED')]
            if len(line) != 1:
                raise Stop('step 01.config: %s is not one <REQUIRED> line' % key)
            self.edit_once(config, line[0], '%s: %s\n' % (key, value), '01.config')
            text = config.read_text(encoding='utf-8')
        py = sys.executable
        self.call('01.check', [py, '_system/stage01_samplesheet.py', '--project', self.project_rel, '--check'])
        self.call('01.write', [py, '_system/stage01_samplesheet.py', '--project', self.project_rel, '--model', 'none'])

    def stage02(self):
        py = sys.executable
        self.call('02.executor', ['bash', self.args.gen_executor, self.project, '--head', 'local', '--force'])
        if not re.search(r'(?m)^name: local$', (self.project / '_config' / 'executor.yaml').read_text(encoding='utf-8')):
            raise Stop('step 02.executor: executor.yaml does not name the local head')
        dry = self.call('02.configure-dry', [py, '_system/configure.py', 'apply', '--project', self.project_rel,
                                             '--assay', ASSAY, '--genome', GENOME, '--peaks-type', PEAKS, '--dry-run'])
        if GENOME not in dry or PEAKS not in dry:
            raise Stop('step 02.configure-dry: the dry run does not show %s and %s' % (GENOME, PEAKS))
        self.call('02.configure', [py, '_system/configure.py', 'apply', '--project', self.project_rel,
                                   '--assay', ASSAY, '--genome', GENOME, '--peaks-type', PEAKS])
        config = self.project / '_config' / (ASSAY + '.yaml')
        self.edit_once(config, MEMORY[0], MEMORY[1], '02.memory')
        derived = re.search(r'(?m)^\s*derived_dir:\s*(\S+)', config.read_text(encoding='utf-8'))
        if derived and Path(derived.group(1)).is_dir() and any(Path(derived.group(1)).iterdir()):
            raise Stop('step 02.cache: the derived cache %s is populated; the exemplar needs it empty, so the '
                       'run records save_reference' % derived.group(1))
        self.call('02.check', [py, WRAPPER, 'check', '--project', self.project_rel])
        self.call('02.prepare', [py, WRAPPER, 'prepare', '--project', self.project_rel])
        params = (self.project / SUBSTAGE / 'params.yaml').read_text(encoding='utf-8')
        if not re.search(r'(?m)^save_reference: true$', params) or re.search(r'(?m)^bwa_index:', params):
            raise Stop('step 02.prepare: params.yaml does not record save_reference (the package refuses an index)')
        submitted = self.call('02.submit', [py, '_system/executorlib.py', 'submit', '--workspace', self.project,
                                            self.project / SUBSTAGE / 'submit.sh'], want_json=True)
        job = submitted.get('job_id')
        if not job:
            raise Stop('step 02.submit: no job id (%s)' % submitted.get('error'))
        self.wait(job)
        self.call('02.collect', [py, WRAPPER, 'collect', '--project', self.project_rel, '--model', 'none'])

    def wait(self, job):
        py = sys.executable
        deadline = time.time() + 60 * self.args.max_wait_minutes
        while True:
            state = self.call('02.status', [py, '_system/executorlib.py', 'status', '--workspace', self.project, job],
                              want_json=True)
            word = str(state.get('state') or state.get('status') or '')
            if word.split(':')[0] in TERMINAL:
                if word != 'COMPLETED':
                    raise Stop('step 02.status: job %s ended %s' % (job, word))
                return
            if time.time() >= deadline:
                raise Stop('step 02.status: job %s still %s after %d minutes; the operator decides' %
                           (job, word, self.args.max_wait_minutes))
            time.sleep(self.args.poll_seconds)

    def package(self):
        py, args = sys.executable, self.args
        harvest, package = self.private / 'harvest', self.public / 'package'
        self.call('pkg.harvest', [py, args.package_run, 'harvest', '--gars', self.gars.parent, '--project', self.project,
                                  '--lane-commit', args.lane_commit, '--out', harvest, '--copy-large'])
        shutil.copytree(str(harvest), str(self.harvest_copy / 'harvest'), symlinks=True)
        self.note('step pkg.harvest-copy: the harvest copied to %s before render' % self.harvest_copy)
        self.call('pkg.render', [py, args.package_run, 'render', '--harvest', harvest, '--gars-repo', args.gars_repo,
                                 '--sources', args.sources, '--tolerances', args.tolerances, '--out', package])
        self.call('pkg.verify', [py, package / 'verify.py'], cwd=self.public)
        self.note('done: package %s verified on this machine; copy the harvest off before down' % package)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('--gars', '--expect-commit', '--fixtures', '--gen-executor', '--package-run', '--lane-commit',
                 '--gars-repo', '--sources', '--tolerances', '--private-out', '--public-out', '--harvest-copy'):
        parser.add_argument(name, required=True)
    parser.add_argument('--title', default='yeast-atac')
    parser.add_argument('--poll-seconds', type=int, default=60)
    parser.add_argument('--max-wait-minutes', type=int, default=180)
    args = parser.parse_args(argv)
    if not re.match(r'[a-z0-9][a-z0-9-]{0,40}\Z', args.title):
        parser.error('--title is a plain project folder name')
    run = Run(args)
    try:
        run.preconditions()
        run.stage00()
        run.stage01()
        run.stage02()
        run.package()
    except Stop as exc:
        if run.log is not None:
            run.note('STOP: %s' % exc)
        else:
            print('STOP: %s' % exc, file=sys.stderr)
        return exc.code
    return 0


if __name__ == '__main__':
    sys.exit(main())
