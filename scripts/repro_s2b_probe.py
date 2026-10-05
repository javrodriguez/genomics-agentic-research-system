#!/usr/bin/env python3
"""S2b, the early probe of the reproduction package (decision 0283): plain nf-core/atacseq at the pinned
commit, run twice on the yeast fixture with GARS's own parameters and the recorded resource clamp, on one
fresh 4 vCPU / 16 GB machine, then compared file by file. It measures re-run against re-run, so any
difference it finds needs a cause read from the bytes before it may become a comparison entry.

  python3 scripts/repro_s2b_probe.py run --sources <lane-sources.tsv> --pipeline-commit <40-hex>
      --nextflow <version> --out <empty folder> [--runs 2]
  python3 scripts/repro_s2b_probe.py compare --a <results A> --b <results B> --out <folder>

`run` needs docker, java, curl and nextflow; `compare` needs nothing but Python. `compare` writes
members.tsv (every file: path, size and sha256 on each side, equal or not), differs.tsv (only the
differing ones, with the first differing byte offset and the file kind), summary.txt, and copies every
differing file of at most 5 MB from both sides under differing/a and differing/b, for reading the cause.
Exit 0 done, 1 a failure, 2 refused, 3 usage. Standard library only, Python 3.6 or later.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

SMALL = 5 * 1024 * 1024
# GARS's own ATAC parameters for this fixture (the atacseq wrapper's build_params with the R64-1-1 row and
# an empty derived cache), so the probe meets the same code paths the exemplar will.
PARAMS = {'mito_name': 'MT', 'aligner': 'bwa', 'macs_gsize': 11624332, 'narrow_peak': True,
          'save_reference': True}
CLAMP = ("executor {\n    name   = 'local'\n    cpus   = 4\n    memory = 14.GB\n}\n"
         "process {\n    resourceLimits = [ cpus: 4, memory: 14.GB, time: 8.h ]\n}\n")
DESIGN = (('atac-a', 1, 'atac-a-r1'), ('atac-a', 2, 'atac-a-r2'), ('atac-b', 1, 'atac-b-r1'),
          ('atac-b', 2, 'atac-b-r2'))


def sha256(path):
    digest = hashlib.sha256()
    with open(str(path), 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def files(top):
    top = Path(top)
    found = {}
    for folder, dirs, names in os.walk(str(top), followlinks=False):
        dirs.sort()
        for name in names:
            path = Path(folder) / name
            if path.is_symlink():
                found[path.relative_to(top).as_posix()] = ('link', os.readlink(str(path)))
            elif path.is_file():
                found[path.relative_to(top).as_posix()] = (path.stat().st_size, sha256(path))
    return found


def first_difference(a, b):
    with open(str(a), 'rb') as left, open(str(b), 'rb') as right:
        offset = 0
        while True:
            x, y = left.read(1 << 16), right.read(1 << 16)
            if x != y:
                for i in range(min(len(x), len(y))):
                    if x[i] != y[i]:
                        return offset + i
                return offset + min(len(x), len(y))
            if not x:
                return -1
            offset += len(x)


def kind(path):
    name = path.lower()
    for suffix, label in (('.bam', 'bam'), ('.bai', 'bam index'), ('.gz', 'gzip'), ('.html', 'html'),
                          ('.bigwig', 'bigwig'), ('.bw', 'bigwig'), ('.narrowpeak', 'peaks'), ('.bed', 'bed'),
                          ('.txt', 'text'), ('.tsv', 'table'), ('.pdf', 'pdf'), ('.png', 'png'), ('.json', 'json'),
                          ('.yml', 'yaml'), ('.log', 'log')):
        if name.endswith(suffix):
            return label
    return 'other'


def compare(args):
    a, b, out = Path(args.a), Path(args.b), Path(args.out)
    if out.exists() and any(out.iterdir()):
        print('refused: %s is not empty' % out, file=sys.stderr)
        return 2
    left, right = files(a), files(b)
    rows, differs = [], []
    for rel in sorted(set(left) | set(right)):
        l, r = left.get(rel), right.get(rel)
        equal = l == r
        rows.append({'path': rel, 'size_a': l[0] if l else '-', 'sha256_a': l[1] if l else 'absent',
                     'size_b': r[0] if r else '-', 'sha256_b': r[1] if r else 'absent', 'equal': 'yes' if equal else 'no'})
        if not equal:
            offset = first_difference(a / rel, b / rel) if l and r and l[0] != 'link' and r[0] != 'link' else -2
            differs.append({'path': rel, 'kind': kind(rel), 'size_a': rows[-1]['size_a'], 'size_b': rows[-1]['size_b'],
                            'first_difference_at': offset if offset >= 0 else ('only one side' if offset == -2 else '-')})
            for side, top, item in (('a', a, l), ('b', b, r)):
                if item and item[0] != 'link' and item[0] <= SMALL:
                    target = out / 'differing' / side / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(str(top / rel), str(target))
    out.mkdir(parents=True, exist_ok=True)
    for name, columns, data in (('members.tsv', ('path', 'size_a', 'sha256_a', 'size_b', 'sha256_b', 'equal'), rows),
                                ('differs.tsv', ('path', 'kind', 'size_a', 'size_b', 'first_difference_at'), differs)):
        with io.open(str(out / name), 'w', encoding='utf-8', newline='\n') as handle:
            handle.write('\t'.join(columns) + '\n')
            for row in data:
                handle.write('\t'.join(str(row[c]) for c in columns) + '\n')
    by_kind = {}
    for row in differs:
        by_kind[row['kind']] = by_kind.get(row['kind'], 0) + 1
    summary = '%d files compared, %d equal, %d differ (%s)\n' % (
        len(rows), len(rows) - len(differs), len(differs),
        ', '.join('%s %d' % item for item in sorted(by_kind.items())) or 'none')
    (out / 'summary.txt').write_text(summary, encoding='utf-8')
    print(summary, end='')
    return 0


def run(args):
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        print('refused: %s is not empty' % out, file=sys.stderr)
        return 2
    for tool in ('docker', 'java', 'curl', 'nextflow'):
        if shutil.which(tool) is None:
            print('refused: %s is not on PATH' % tool, file=sys.stderr)
            return 2
    out.mkdir(parents=True, exist_ok=True)
    sources = list(csv.DictReader(io.open(args.sources, encoding='utf-8'), delimiter='\t'))
    folders = {'input': out / 'inputs', 'reference': out / 'refs'}
    for row in sources:
        dest = folders[row['kind']] / row['name']
        dest.parent.mkdir(parents=True, exist_ok=True)
        if subprocess.call(['curl', '-fsSL', '--retry', '3', '-o', str(dest), row['url']]) != 0:
            print('failed: could not download %s' % row['name'], file=sys.stderr)
            return 1
        if sha256(dest) != row['sha256']:
            print('refused: %s does not match its pinned sha256; no pipeline started' % row['name'], file=sys.stderr)
            return 2
    sheet = out / 'samplesheet.csv'
    lines = ['sample,fastq_1,fastq_2,replicate']
    for group, rep, sample in DESIGN:
        lines.append('%s,%s,%s,%d' % (group, out / 'inputs' / ('%s_S1_L001_R1_001.fastq.gz' % sample),
                                      out / 'inputs' / ('%s_S1_L001_R2_001.fastq.gz' % sample), rep))
    sheet.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (out / 'clamp.config').write_text(CLAMP, encoding='utf-8')
    record = {'pipeline_commit': args.pipeline_commit, 'nextflow': args.nextflow, 'runs': []}
    for n in range(1, args.runs + 1):
        label = 'run%d' % n
        params = dict(PARAMS, input=str(sheet), outdir=str(out / label / 'results'),
                      fasta=str(out / 'refs' / 'genome.fa'), gtf=str(out / 'refs' / 'genes.gtf'))
        (out / label).mkdir()
        (out / label / 'params.json').write_text(json.dumps(params, indent=2, sort_keys=True), encoding='utf-8')
        env = dict(os.environ, NXF_VER=args.nextflow, NXF_SYNTAX_PARSER='v1')
        start = time.time()
        with open(str(out / label / 'nextflow.log'), 'wb') as log:
            code = subprocess.call(['nextflow', 'run', 'nf-core/atacseq', '-r', args.pipeline_commit, '-profile', 'docker',
                                    '-params-file', str(out / label / 'params.json'), '-c', str(out / 'clamp.config'),
                                    '-work-dir', str(out / label / 'work')], cwd=str(out / label), env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        wall = time.time() - start
        disk = subprocess.run(['du', '-sb', str(out)], stdout=subprocess.PIPE).stdout.decode().split()[0]
        record['runs'].append({'label': label, 'exit': code, 'wall_seconds': round(wall, 1), 'disk_bytes_after': int(disk)})
        (out / 'probe.json').write_text(json.dumps(record, indent=2, sort_keys=True), encoding='utf-8')
        print('%s: exit %d, %.0f s, %s bytes on disk after' % (label, code, wall, disk), flush=True)
        if code != 0:
            return 1
    code = compare(argparse.Namespace(a=str(out / 'run1' / 'results'), b=str(out / 'run2' / 'results'),
                                      out=str(out / 'compare')))
    # The S2b acceptance item of review h3-7: where a real run's outputs (MultiQC's report, the trace, the
    # tables) name the box's user, the launch folder or a bucket, before render meets them in the paid S3.
    import getpass
    scan(out / 'run1', [getpass.getuser(), str(out / 'run1'), 's3://'], out / 'compare' / 'names.tsv')
    return code


def scan(top, needles, dest):
    """Per file under `top`, how many times each needle occurs (plain bytes; a .gz member is not opened,
    and is listed so)."""
    rows = []
    for folder, dirs, names in os.walk(str(top), followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != 'work')
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink() or not path.is_file():
                continue
            data = path.read_bytes()
            counts = [data.count(n.encode('utf-8')) for n in needles]
            if any(counts) or name.endswith('.gz'):
                rows.append((path.relative_to(top).as_posix(), counts, name.endswith('.gz')))
    rows.sort(key=lambda row: row[0])   # by path, never by walk order
    with io.open(str(dest), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('path\t' + '\t'.join('count:%s' % n for n in needles) + '\tcompressed\n')
        for rel, counts, gz in rows:
            handle.write('%s\t%s\t%s\n' % (rel, '\t'.join(str(c) for c in counts), 'yes, not opened' if gz else 'no'))
    print('names: %d files name the user, the launch folder or a bucket (%s)' % (
        sum(1 for _, c, _ in rows if any(c)), dest))
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='verb')
    p = sub.add_parser('run')
    p.add_argument('--sources', required=True)
    p.add_argument('--pipeline-commit', required=True)
    p.add_argument('--nextflow', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--runs', type=int, default=2)
    p = sub.add_parser('compare')
    p.add_argument('--a', required=True)
    p.add_argument('--b', required=True)
    p.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    if args.verb is None:
        parser.print_usage(sys.stderr)
        return 3
    return {'run': run, 'compare': compare}[args.verb](args)


if __name__ == '__main__':
    sys.exit(main())
