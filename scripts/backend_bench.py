#!/usr/bin/env python3
"""W1 integrity-and-hash instrument. Python 3.6.8, stdlib only; no measured rows ship."""
import argparse
import csv
import datetime
import fcntl
import functools
import hashlib
import json
import math
import os
import re
import resource
import shlex
import struct
import subprocess
import sys
import time
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'gars/_system'))
import executorlib as ex
import integrity
import stage00_register as register
import wrapperlib as wl

WORKLOAD = 'W1'
SAMPLES = 24
BLOB_BYTES = 8 * 1024 ** 2
STAGE = '02_bioinformatics/rnaseq_bulk/99_backend-bench'
CSV_PATH = REPO / 'benchmarks/backend_bench.csv'
EVIDENCE_DIR = REPO / 'benchmarks/backend_bench'
FIELDS = ['backend', 'venue', 'status', 'workload_id', 'workload_sha256', 'samples',
          'wall_s', 'cpu_s', 'max_rss_mb', 'queue_wait_s', 'python_version', 'gars_commit',
          'measured_at', 'cost_usd_per_sample', 'cost_basis']
CSV_FIELDS = FIELDS + ['evidence_sha256', 'supersedes']


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def blob(number):
    """SHAKE seed expansion and explicit stored DEFLATE blocks avoid zlib-version drift."""
    raw = hashlib.shake_256(('GARS-W1-seed-801:%02d' % number).encode('ascii')).digest(BLOB_BYTES)
    parts = [b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff']
    for offset in range(0, len(raw), 65535):
        block = raw[offset:offset+65535]
        final = offset + len(block) == len(raw)
        parts.append(struct.pack('<BHH', int(final), len(block), 65535-len(block)) + block)
    parts.append(struct.pack('<II', zlib.crc32(raw) & 0xffffffff, len(raw)))
    return b''.join(parts)


def workload(out=None):
    digest = hashlib.sha256()
    for number in range(1, SAMPLES+1):
        name = 'w1-%02d.bin.gz' % number
        content = blob(number)
        digest.update((name + '\t' + hashlib.sha256(content).hexdigest() + '\n').encode('ascii'))
        if out is not None:
            (Path(out) / name).write_bytes(content)
    return digest.hexdigest()


@functools.lru_cache(maxsize=1)
def expected_workload_sha256():
    return workload()


def rss_mb(value, platform):
    require(platform == 'darwin' or platform.startswith('linux'), 'unsupported ru_maxrss platform')
    return value / float(1024 ** 2) if platform == 'darwin' else value / 1024.0


def worker(out):
    root = Path(out)
    stage = root / STAGE
    paths = [(str(n), root / 'workload' / ('w1-%02d.bin.gz' % n)) for n in range(1, SAMPLES+1)]
    start = time.monotonic()
    before = resource.getrusage(resource.RUSAGE_SELF)
    problems = integrity.check_many(paths, 'full')
    digest = hashlib.sha256()
    for _, path in paths:
        digest.update((path.name + '\t' + wl.sha256(path) + '\n').encode('ascii'))
    after = resource.getrusage(resource.RUSAGE_SELF)
    timing = {'wall_s': time.monotonic()-start,
              'cpu_s': after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
              'max_rss_mb': rss_mb(after.ru_maxrss, sys.platform),
              'python_version': '.'.join(str(x) for x in sys.version_info[:3]),
              'workload_sha256': digest.hexdigest(), 'ok': not problems}
    (stage / 'run/result.json').write_text(json.dumps(timing, sort_keys=True)+'\n')
    if problems:
        raise ValueError('integrity_failed')
    (stage / 'run/.gars_run_complete').write_text('W1 completed\n')


def run(venue, out):
    root = Path(out).resolve()
    require(not root.exists(), 'output_already_exists')
    descriptor = ex.SLURM if venue == 'slurm' else ex.LOCAL
    require(ex.venue_of(descriptor) == venue, 'venue_host_mismatch')
    root.mkdir(parents=True)
    (root / 'workload').mkdir()
    digest = workload(root / 'workload')
    (root / '_config').mkdir()
    (root / '_config/executor.yaml').write_text('name: '+descriptor['name']+'\n')
    config = root / '_config/rnaseq_bulk.yaml'
    config.write_text('strandedness: auto\naligner: star_salmon\ncompute:\n'
                      '  partition: fixture\n  time: "00:30:00"\n  cpus: 4\n  mem: 2G\n')
    base = dict(data_class='public', purpose='fixture', agreement_ref='none',
                input_data_location=json.dumps([str(root / 'workload')], separators=(',', ':')))
    register.write_dataset_record(root, register.dataset_values(root, base))
    stage = root / STAGE
    for directory in ('run', 'logs'):
        (stage / directory).mkdir(parents=True, exist_ok=True)
    header = ex.header_lines(root, wl.read_config(config), 'backend-bench', 'rnaseq_bulk', stage)
    program = 'import runpy,sys; runpy.run_path(sys.argv[1])["worker"](sys.argv[2])'
    body = ' '.join(shlex.quote(value) for value in (sys.executable, '-c', program, str(Path(__file__).resolve()), str(root)))
    (stage / 'submit.sh').write_text('#!' + os.path.join(os.sep, 'bin', 'bash') + '\n'+'\n'.join(header)+'\nset -euo pipefail\n'+body+'\n')
    inputs = {'config': config}
    inputs.update({'blob_%02d' % n: root / 'workload' / ('w1-%02d.bin.gz' % n) for n in range(1,SAMPLES+1)})
    wl.write_reproducibility(stage, 'rnaseq_bulk', REPO, inputs, [])
    job, why = ex.submit(root, stage / 'submit.sh')
    require(job is not None and why is None, 'submit_refused: '+str(why))
    submitted = dict(venue=venue, job_id=job, workload_sha256=digest)
    (root / 'submitted.json').write_text(json.dumps(submitted, sort_keys=True)+'\n')
    return submitted


def duration(value):
    match = re.fullmatch(r'(?:(\d+)-)?(\d+):(\d{2}):(\d{2}(?:\.\d+)?)', value)
    if match:
        day, hour, minute, second = match.groups()
        return int(day or 0)*86400 + int(hour)*3600 + int(minute)*60 + float(second)
    match = re.fullmatch(r'(\d+):(\d{2}(?:\.\d+)?)', value)
    require(match is not None, 'accounting_duration_invalid')
    return int(match.group(1))*60 + float(match.group(2))


def slurm_timings(job):
    env = dict(os.environ, TZ='UTC')
    args = ['sacct', '-j', job, '--format=Submit,Start,End,Elapsed,TotalCPU,MaxRSS,State', '-P', '-n']
    result = subprocess.run(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'accounting_unavailable')
    rows = [line.split('|')[:7] for line in result.stdout.decode().splitlines() if line.strip()]
    require(bool(rows) and all(len(row)==7 for row in rows), 'accounting_invalid')
    main = rows[0]
    # Query the batch step explicitly; row ordering alone cannot identify it.
    args[2] = job+'.batch'
    result = subprocess.run(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'batch_accounting_unavailable')
    batch = [line.split('|')[:7] for line in result.stdout.decode().splitlines() if line.strip()]
    require(len(batch)==1 and len(batch[0])==7, 'batch_accounting_invalid')
    rss = re.fullmatch(r'(\d+(?:\.\d+)?)([KMGT])', batch[0][5])
    require(rss is not None, 'batch_rss_invalid')
    instant = lambda value: datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
    wait = (instant(main[1])-instant(main[0])).total_seconds()
    require(wait >= 0 and instant(main[2]) >= instant(main[1]), 'accounting_time_invalid')
    return dict(wall_s=duration(main[3]), cpu_s=duration(main[4]),
                max_rss_mb=float(rss.group(1))*1024**('KMGT'.index(rss.group(2))-1), queue_wait_s=wait)


def validate_evidence(value, completed=False):
    require(isinstance(value, dict) and set(value)==set(FIELDS), 'evidence_schema')
    require(value['venue'] in ('local','homelab','slurm') and value['backend']==value['venue'], 'evidence_backend')
    require(value['status'] in ('COMPLETED','FAILED'), 'evidence_status')
    require(not completed or value['status']=='COMPLETED', 'evidence_not_completed')
    require(value['workload_id']==WORKLOAD and value['workload_sha256']==expected_workload_sha256(), 'workload_sha256_mismatch')
    require(type(value['samples']) is int and value['samples']==SAMPLES, 'evidence_samples')
    for field in ('wall_s','cpu_s','max_rss_mb','queue_wait_s'):
        number=value[field]
        require((number is None and value['status']=='FAILED') or
                (type(number) in (int,float) and math.isfinite(number) and number>=0), 'evidence_'+field)
    require(value['venue']=='slurm' or value['queue_wait_s']==0, 'evidence_queue_wait_s')
    require(value['cost_usd_per_sample']=='unmetered', 'evidence_cost')
    basis='institutional_allocation' if value['venue']=='slurm' else 'owned_hardware'
    require(value['cost_basis']==basis, 'evidence_cost_basis')
    require((value['python_version'] is None and value['status']=='FAILED') or
            (isinstance(value['python_version'],str) and re.fullmatch(r'\d+\.\d+\.\d+', value['python_version'])), 'evidence_python_version')
    require(isinstance(value['gars_commit'],str) and re.fullmatch(r'[0-9a-f]{40}',value['gars_commit']), 'evidence_commit')
    require(isinstance(value['measured_at'],str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z',value['measured_at']), 'evidence_timestamp')
    datetime.datetime.strptime(value['measured_at'], '%Y-%m-%dT%H:%M:%SZ')
    return value


def collect(out, timeout_s=300):
    require(math.isfinite(timeout_s) and timeout_s>=0, 'timeout_invalid')
    root=Path(out).resolve()
    submitted=json.loads((root / 'submitted.json').read_text())
    deadline=time.monotonic()+timeout_s
    while True:
        state, why=ex.status(root, submitted['job_id'])
        if state in ('COMPLETED','FAILED','CANCELLED','ARTIFACT_MISSING') or (state and state.startswith('FAILED:')):
            break
        require(time.monotonic()<deadline, 'collection_timeout')
        time.sleep(min(1, max(0, deadline-time.monotonic())))
    status='COMPLETED' if state=='COMPLETED' else 'FAILED'
    stage=root / STAGE
    result_path=stage / 'run/result.json'
    # A worker killed before its result write has no trustworthy resource measurement.
    require(result_path.is_file() or status=='FAILED', 'terminal_result_missing')
    timing=(json.loads(result_path.read_text()) if result_path.is_file() else
            dict(wall_s=None, cpu_s=None, max_rss_mb=None, python_version=None,
                 workload_sha256=submitted['workload_sha256'], ok=False))
    require(submitted['workload_sha256']==timing['workload_sha256']==expected_workload_sha256(), 'workload_sha256_mismatch')
    if not timing['ok']:
        status='FAILED'
    measured={key:timing[key] for key in ('wall_s','cpu_s','max_rss_mb')}
    measured['queue_wait_s']=0
    if submitted['venue']=='slurm':
        try:
            measured=slurm_timings(submitted['job_id'])
        except (ValueError, OSError):
            if status != 'FAILED':
                raise
            measured=dict(wall_s=None, cpu_s=None, max_rss_mb=None, queue_wait_s=None)
    value=dict(measured, backend=submitted['venue'], venue=submitted['venue'], status=status,
               workload_id=WORKLOAD, workload_sha256=submitted['workload_sha256'], samples=SAMPLES,
               python_version=timing['python_version'], gars_commit=wl.git_value(REPO,'rev-parse','HEAD'),
               measured_at=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
               cost_usd_per_sample='unmetered', cost_basis='institutional_allocation' if submitted['venue']=='slurm' else 'owned_hardware')
    validate_evidence(value)
    path=root / 'evidence.json'
    require(not path.exists(), 'evidence_already_exists')
    path.write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')
    return value


def csv_row(evidence, digest, supersedes=''):
    validate_evidence(evidence, completed=True)
    require(re.fullmatch(r'[0-9a-f]{64}',digest) is not None, 'evidence_sha_invalid')
    require(not supersedes or re.fullmatch(r'[0-9a-f]{64}',supersedes), 'supersedes_invalid')
    return {key:str(value) for key,value in dict(evidence,evidence_sha256=digest,supersedes=supersedes).items()}


def verify_rows(rows, evidence_dir):
    active={}
    seen=set()
    for row in rows:
        require(set(row)==set(CSV_FIELDS), 'csv_schema')
        digest=row['evidence_sha256']
        require(re.fullmatch(r'[0-9a-f]{64}',digest) is not None, 'evidence_sha_invalid')
        path=Path(evidence_dir) / (digest+'.json')
        require(path.is_file(), 'evidence_missing')
        content=path.read_bytes()
        require(hashlib.sha256(content).hexdigest()==digest, 'evidence_sha_mismatch')
        expected=csv_row(json.loads(content.decode('utf-8')),digest,row['supersedes'])
        require(row==expected, 'csv_evidence_mismatch')
        key=(row['backend'],row['workload_id'])
        require(row['supersedes']==active.get(key,''), 'supersession_mismatch')
        require(digest not in seen, 'duplicate_evidence')
        seen.add(digest);active[key]=digest
    return active


def append(evidence, supersede=None):
    content=Path(evidence).read_bytes()
    value=validate_evidence(json.loads(content.decode('utf-8')), completed=True)
    digest=hashlib.sha256(content).hexdigest()
    with CSV_PATH.open('r+', newline='') as handle:
        fcntl.flock(handle.fileno(),fcntl.LOCK_EX)
        reader=csv.DictReader(handle)
        require(reader.fieldnames==CSV_FIELDS, 'csv_schema')
        rows=list(reader)
        active=verify_rows(rows,EVIDENCE_DIR)
        previous=active.get((value['backend'],value['workload_id']))
        require((previous is None and supersede is None) or (previous is not None and supersede==previous), 'supersede_required')
        require(all(row['evidence_sha256']!=digest for row in rows), 'duplicate_evidence')
        row=csv_row(value,digest,supersede or '')
        EVIDENCE_DIR.mkdir(exist_ok=True)
        path=EVIDENCE_DIR / (digest+'.json')
        if path.exists():
            require(path.read_bytes()==content,'evidence_collision')
        else:
            with path.open('xb') as output:
                output.write(content);output.flush();os.fsync(output.fileno())
        handle.seek(0,os.SEEK_END)
        writer=csv.DictWriter(handle,fieldnames=CSV_FIELDS,lineterminator='\n')
        writer.writerow(row);handle.flush();os.fsync(handle.fileno())
    return row


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest='verb')
    launch=commands.add_parser('run');launch.add_argument('--venue',required=True,choices=('local','homelab','slurm'));launch.add_argument('--out',required=True)
    poll=commands.add_parser('collect');poll.add_argument('--out',required=True);poll.add_argument('--timeout-s',type=float,default=300)
    add=commands.add_parser('append');add.add_argument('--evidence',required=True);add.add_argument('--supersede')
    args=parser.parse_args(argv)
    try:
        if args.verb=='run': result=run(args.venue,args.out)
        elif args.verb=='collect': result=collect(args.out,args.timeout_s)
        elif args.verb=='append': result=append(args.evidence,args.supersede)
        else: parser.error('choose run, collect or append')
    except (ValueError,OSError,KeyError,TypeError) as exc:
        print('backend bench refused: '+str(exc),file=sys.stderr);return 2
    print(json.dumps(result,sort_keys=True));return 0


if __name__=='__main__':
    sys.exit(main())
