#!/usr/bin/env python3
"""Row 5 engine. Python >=3.6, stdlib only; configuration and rationale in 0044."""
import csv
import datetime as dt
import hashlib
import io
import ipaddress
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess as sp
import sys
import time

REPO = Path(__file__).resolve().parents[2]
STAMP = '%Y-%m-%dT%H:%M:%SZ'
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_]*\Z')
HOST = re.compile(r'[A-Za-z0-9][A-Za-z0-9.:-]*\Z')
ARCHIVE = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)-(\d{8}T\d{6}Z)\.dump\.(gpg|age)\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')
SOURCE = ('PGHOST', 'PGPORT', 'PGUSER', 'PGDATABASE', 'PGPASSFILE')
COMMON = SOURCE + ('BACKUP_LOCAL_DIR', 'BACKUP_WORK_DIR', 'BACKUP_OFFMACHINE_DEST', 'ENC_KEY_FILE')
TARGET = ('DRILL_TARGET_PGHOST', 'DRILL_TARGET_PGPORT', 'DRILL_TARGET_PGUSER', 'DRILL_TARGET_PGDATABASE')
EXPOSURE = ('EXPOSURE_PUBLIC_HOST', 'EXPOSURE_TAILNET_HOST', 'EXPOSURE_PORTS',
            'EXPOSURE_CONTROL_HOST', 'EXPOSURE_CONTROL_PORT', 'EXPOSURE_LOG')


class Fail(Exception):
    pass


def require(keys):
    for key in keys:
        if not os.environ.get(key):
            raise Fail('missing_' + key)


def utc():
    return dt.datetime.now(dt.timezone.utc)


def epoch(value):
    try:
        return dt.datetime.strptime(value, STAMP).replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        raise Fail('invalid_timestamp')


def run(argv, data=None, timeout=60):
    try:
        p = sp.run([str(x) for x in argv], input=data, stdout=sp.PIPE,
                   stderr=sp.DEVNULL, timeout=timeout)
    except (OSError, sp.TimeoutExpired):
        raise Fail('command_failed')
    if p.returncode:
        raise Fail('command_failed')
    return p.stdout


def safe_path(value):
    if not re.fullmatch(r'/[A-Za-z0-9_./ -]+', value):
        raise Fail('invalid_path')
    p = Path(value)
    if '..' in p.parts or any(part.is_symlink() for part in [p] + list(p.parents)):
        raise Fail('unsafe_path')
    return p.resolve()


def external_path(value):
    p = safe_path(value)
    # Check ancestors, including non-existent leaf paths, without asking git to read config.
    if any((part / '.git').exists() for part in [p] + list(p.parents)):
        raise Fail('local_dir_in_repo')
    return p


def inside(path, root):
    return path != root and root in path.parents


def ident(value):
    if not NAME.fullmatch(value):
        raise Fail('invalid_identifier')
    return '"' + value + '"'


def table_ident(value):
    parts = value.split('.')
    if len(parts) != 2:
        raise Fail('invalid_identifier')
    return '.'.join(ident(x) for x in parts)


def port(value):
    if not value.isdigit() or not 1 <= int(value) <= 65535:
        raise Fail('invalid_port')
    return int(value)


def host(value):
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not HOST.fullmatch(value):
        raise Fail('invalid_host')
    return value


class Config:
    def __init__(self, drill=False):
        require(COMMON + (TARGET + ('DRILL_CANARY_FILE', 'RESTORE_LOG') if drill else ()))
        self.e = dict(os.environ)
        self.local = external_path(self.e['BACKUP_LOCAL_DIR'])
        self.work = safe_path(self.e['BACKUP_WORK_DIR'])
        if not inside(self.work, self.local):
            raise Fail('work_dir_outside_local')
        self.key = external_path(self.e['ENC_KEY_FILE'])
        self.passfile = external_path(self.e['PGPASSFILE'])
        self.mode = self.e.get('PG_CLIENT_MODE', 'container')
        if self.mode not in ('container', 'host'):
            raise Fail('invalid_client_mode')
        self.compose = []
        if self.mode == 'container':
            require(('COMPOSE_PROJECT', 'PG_PASSWORD_FILE', 'PG_DATA_DIR'))
            if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', self.e['COMPOSE_PROJECT']):
                raise Fail('invalid_project')
            engine = self.e.get('CONTAINER_ENGINE', 'docker')
            if engine not in ('docker', 'podman'):
                raise Fail('invalid_engine')
            external_path(self.e['PG_PASSWORD_FILE'])
            if not external_path(self.e['PG_DATA_DIR']).is_dir():
                raise Fail('invalid_data_dir')
            self.compose = [engine, 'compose', '-f', str(REPO / 'infra/compose/postgres.compose.yml'),
                            '-p', self.e['COMPOSE_PROJECT'], 'exec', '-T', 'db']
        self.tool = self.e.get('ENC_TOOL', 'auto')
        if self.tool == 'auto':
            self.tool = next((x for x in ('gpg', 'age') if shutil.which(x)), '')
        if self.tool not in ('gpg', 'age') or not shutil.which(self.tool):
            raise Fail('encryption_unavailable')
        self.identity = external_path(self.e.get('ENC_IDENTITY_FILE', str(self.key)))
        if self.tool == 'age':
            require(('ENC_IDENTITY_FILE',))
        for p in (self.key, self.identity, self.passfile):
            if not p.is_file():
                raise Fail('key_or_passfile_missing')
        self.src = self.endpoint('')
        self.dst = self.endpoint('DRILL_TARGET_') if drill else None
        self.off = Destination(self.e['BACKUP_OFFMACHINE_DEST'])
        self.second = Destination(self.e['BACKUP_SECOND_DEST']) if self.e.get('BACKUP_SECOND_DEST') else None
        roots = [str(self.local), self.off.value] + ([self.second.value] if self.second else [])
        if len(roots) != len(set(roots)):
            raise Fail('destinations_not_distinct')
        try:
            self.retention = int(self.e.get('RETENTION_COUNT', '14'))
            if self.retention < 1:
                raise ValueError()
        except ValueError:
            raise Fail('invalid_retention')
        if drill:
            self.canary = external_path(self.e['DRILL_CANARY_FILE'])
            if not self.canary.is_file():
                raise Fail('canary_missing')
            self.log = safe_path(self.e['RESTORE_LOG'])

    def endpoint(self, prefix):
        return (host(self.e[prefix + 'PGHOST']), port(self.e[prefix + 'PGPORT']),
                self.e[prefix + 'PGUSER'], self.e[prefix + 'PGDATABASE'])

    def client(self, tool, endpoint, args):
        h, p, u, d = endpoint
        ident(u)
        ident(d)
        argv = [tool, '-h', h, '-p', str(p), '-U', u]
        argv += (['-d', d] if tool != 'pg_dump' else ['--dbname', d])
        argv += list(args)
        if self.compose:
            # Static shell text only. Password is read in the container, never argv/output.
            return self.compose + ['sh', '-c',
                'export PGPASSWORD="$(cat /run/secrets/pg_password)"; '
                'export PGCONNECT_TIMEOUT=5; exec "$@"', 'row05'] + argv
        return argv

    def sql(self, endpoint, query):
        return run(self.client('psql', endpoint, ['-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1',
                                                  '-c', query])).decode().strip()

    def crypt(self, decrypt=False, tool=None):
        tool = tool or self.tool
        if not shutil.which(tool):
            raise Fail('encryption_unavailable')
        if tool == 'gpg':
            # No gpg agent, config, trustdb or keyring; no socket in a system temp directory.
            return ['gpg', '--no-options', '--no-default-keyring', '--no-random-seed-file', '--homedir', str(self.work), '--batch', '--yes',
                    '--no-symkey-cache', '--s2k-count', '65011712', '--pinentry-mode', 'loopback', '--no-autostart',
                    '--passphrase-file', str(self.key), '--output', '-',
                    '--decrypt' if decrypt else '--symmetric']
        return ['age', '-d', '-i', str(self.identity)] if decrypt else ['age', '-R', str(self.key)]


def stream(commands, output=None, reason='restore_failed'):
    """Connect pipes without a plaintext file; check EVERY producer, including on SIGTERM."""
    procs = []
    try:
        previous = None
        for i, argv in enumerate(commands):
            last = i == len(commands) - 1
            p = sp.Popen([str(x) for x in argv], stdin=previous,
                         stdout=output if last and output is not None else sp.PIPE,
                         stderr=sp.DEVNULL)
            procs.append(p)
            if previous is not None:
                previous.close()
            previous = p.stdout
        data = procs[-1].communicate(timeout=3600)[0]
        codes = [p.wait(timeout=30) for p in procs]
        if any(codes):
            raise Fail(reason)
        return data or b''
    except (OSError, sp.TimeoutExpired):
        raise Fail(reason)
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=5)
            except sp.TimeoutExpired:
                p.kill()
                p.wait()


class Destination:
    def __init__(self, value):
        self.remote = None
        if not value.startswith('/'):
            match = re.fullmatch(r'([A-Za-z0-9_][A-Za-z0-9_.-]*@[A-Za-z0-9][A-Za-z0-9.-]*):(/[A-Za-z0-9_./ -]+)', value)
            if not match:
                raise Fail('invalid_destination')
            self.remote, value = match.groups()
            if '..' in Path(value).parts:
                raise Fail('unsafe_path')
            self.root = Path(value)
        else:
            self.root = external_path(value)
        if str(self.root) == '/':
            raise Fail('unsafe_path')
        self.value = (self.remote + ':' if self.remote else '') + str(self.root)

    def ssh(self, args):
        return ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', self.remote,
                ' '.join(shlex.quote(str(x)) for x in args)]

    def path(self, name):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name):
            raise Fail('invalid_archive_name')
        p = self.root / name
        if not self.remote and (p.is_symlink() or not inside(p.resolve(), self.root)):
            raise Fail('unsafe_path')
        return p

    def list(self):
        if self.remote:
            # Remote Python provides portable timestamps and checks every path component.
            code = "import os,json,pathlib,sys;p=pathlib.Path(sys.argv[1]);assert not any(x.is_symlink() for x in [p]+list(p.parents));print(json.dumps([(x.name,x.stat().st_mtime) for x in p.iterdir() if x.is_file() and not x.is_symlink()]))"
            import json
            return json.loads(run(self.ssh(['python3', '-c', code, str(self.root)])))
        if not self.root.exists():
            return []
        return [(p.name, p.stat().st_mtime) for p in self.root.iterdir()
                if p.is_file() and not p.is_symlink()]

    def reader(self, name):
        p = self.path(name)
        if self.remote:
            code = "import pathlib,sys,shutil;p=pathlib.Path(sys.argv[1]);assert not any(x.is_symlink() for x in [p]+list(p.parents));shutil.copyfileobj(p.open('rb'),sys.stdout.buffer)"
            return self.ssh(['python3', '-c', code, str(p)])
        return ['cat', str(p)]

    def read(self, name):
        return run(self.reader(name))

    def sha(self, name):
        # Stream even very large destination archives back, do not buffer them in memory.
        p = sp.Popen(self.reader(name), stdout=sp.PIPE, stderr=sp.DEVNULL)
        try:
            h = hashlib.sha256()
            for chunk in iter(lambda: p.stdout.read(1024 * 1024), b''):
                h.update(chunk)
            if p.wait():
                raise Fail('destination_read_failed')
            return h.hexdigest()
        finally:
            p.stdout.close()
            if p.poll() is None:
                p.kill()
                p.wait()

    def mkdir(self):
        if self.remote:
            # Refuse symlink roots before rsync; remote host is a trusted backup destination.
            code = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);assert not any(x.is_symlink() for x in [p]+list(p.parents));p.mkdir(parents=True,exist_ok=True)"
            run(self.ssh(['python3', '-c', code, str(self.root)]))
        else:
            self.root.mkdir(parents=True, exist_ok=True)

    def copy(self, path):
        target = (self.remote + ':' + shlex.quote(str(self.root) + '/') if self.remote
                  else str(self.root) + '/')
        self.path(path.name)
        run(['rsync', '-a', '--checksum', '--', str(path), target])

    def remove(self, name):
        p = self.path(name)
        if not ARCHIVE.fullmatch(name[:-7] if name.endswith('.sha256') else name):
            raise Fail('unsafe_prune')
        if self.remote:
            code = "import pathlib,sys;p=pathlib.Path(sys.argv[1]);assert not any(x.is_symlink() for x in [p]+list(p.parents));p.unlink() if p.exists() else None"
            run(self.ssh(['python3', '-c', code, str(p)]))
        elif p.exists():
            p.unlink()

    def prune(self, db, count):
        files = sorted(n for n, _ in self.list() if ARCHIVE.fullmatch(n)
                       and ARCHIVE.fullmatch(n).group(1) == db)
        for name in files[:-count]:
            self.remove(name)
            self.remove(name + '.sha256')


def manifest(destination):
    if 'manifest.tsv' not in dict(destination.list()):
        return {}
    rows = csv.reader(io.StringIO(destination.read('manifest.tsv').decode()), delimiter='\t')
    result = {}
    for row in rows:
        if len(row) != 5 or not ARCHIVE.fullmatch(row[0]) or not DIGEST.fullmatch(row[1]):
            raise Fail('invalid_manifest')
        if row[0] in result:
            raise Fail('manifest_ambiguous')
        epoch(row[2])
        result[row[0]] = row
    return result


def candidate(destination, source, start):
    records = manifest(destination)
    files = dict(destination.list())
    eligible = []
    for name, mtime in files.items():
        match = ARCHIVE.fullmatch(name)
        if not match or mtime >= start:
            continue
        if name not in records:
            print('result=IGNORED reason=unregistered_backup')
            continue
        row = records[name]
        if row[3:] != [source[0], source[3]]:
            continue
        when = epoch(row[2])
        if when >= start:
            continue
        # Archive mtime is normalized to dump start; the sidecar retains its
        # completion time so a dump completed during this drill is ineligible.
        if files.get(name + '.sha256', 0) >= start:
            continue
        named = dt.datetime.strptime(match.group(2), '%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc).timestamp()
        if max(abs(named - when), abs(mtime - when)) > 300:
            raise Fail('timestamp_drift')
        try:
            sidecar = destination.read(name + '.sha256').decode().strip()
            digest = destination.sha(name)
        except (Fail, UnicodeError):
            raise Fail('unregistered_backup')
        if sidecar != row[1] or digest != row[1]:
            raise Fail('unregistered_backup')
        eligible.append((when, name, row[1]))
    if not eligible:
        raise Fail('no_scheduled_backup')
    return max(eligible)


def parse_canary(path):
    try:
        with path.open(newline='') as f:
            rows = list(csv.reader(line for line in f if line.strip() and not line.startswith('#')))
        if not rows or len(rows[0]) != 4 or rows[0][0] != 'canary' or not rows[0][3]:
            raise Fail('canary_missing')
        canary = rows[0][1:]
        table_ident(canary[0])
        ident(canary[1])
        counts = {}
        for row in rows[1:]:
            if len(row) != 3 or not row[1].isdigit() or not re.fullmatch(r'[0-9a-f]{32}', row[2]):
                raise Fail('invalid_canary')
            table_ident(row[0])
            if row[0] in counts or row[0] == 'public.gars_drill_target':
                raise Fail('invalid_canary')
            counts[row[0]] = (int(row[1]), row[2])
        if canary[0] not in counts:
            raise Fail('canary_missing')
        return canary, counts
    except (OSError, UnicodeError, csv.Error):
        raise Fail('canary_missing')


def checksum_table(config, endpoint, table):
    """Shared read-only checksum contract for independent canary writer and drill."""
    quoted = table_ident(table)
    keys = config.sql(endpoint,
        "SELECT string_agg(quote_ident(a.attname), ',' ORDER BY k.ordinality) "
        "FROM pg_index i CROSS JOIN LATERAL unnest(i.indkey) WITH ORDINALITY k(attnum,ordinality) "
        "JOIN pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.attnum "
        "WHERE i.indisprimary AND i.indrelid='" + quoted + "'::regclass")
    if not keys:
        raise Fail('missing_primary_key')
    # keys are database-quoted identifiers; never caller-provided SQL.
    answer = config.sql(endpoint, "SELECT count(*)::text || ',' || "
        "md5(COALESCE(string_agg(row_to_json(t)::text, E'\\n' ORDER BY " + keys + "),'')) FROM " + quoted + ' t')
    count, digest = answer.split(',')
    return int(count), digest


def identity(config, endpoint):
    value = config.sql(endpoint, "SELECT COALESCE(inet_server_addr()::text,'') || '|' || "
                       "COALESCE(inet_server_port()::text,'') || '|' || current_database()")
    parts = value.split('|')
    if len(parts) != 3 or not all(parts):
        raise Fail('identity_unresolved')
    return tuple(parts)


def guards(config):
    source, target = identity(config, config.src), identity(config, config.dst)
    if source == target:
        raise Fail('target_is_primary')
    # Different IPv4/IPv6 or interface addresses can still address the SAME cluster.
    source_cluster = config.sql(config.src, 'SELECT system_identifier FROM pg_control_system()')
    target_cluster = config.sql(config.dst, 'SELECT system_identifier FROM pg_control_system()')
    if not source_cluster.isdigit() or not target_cluster.isdigit():
        raise Fail('identity_unresolved')
    if source_cluster == target_cluster and source[2] == target[2]:
        raise Fail('target_is_primary')
    if config.sql(config.dst, "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n "
                  "ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname='gars_drill_target' "
                  "AND c.relkind='r')") != 't':
        raise Fail('target_not_marked')


def backup(config):
    config.local.mkdir(parents=True, exist_ok=True)
    config.work.mkdir(mode=0o700, parents=True, exist_ok=True)
    lock = config.work / 'backup.lock'
    try:
        lock.mkdir()
    except FileExistsError:
        raise Fail('backup_locked')
    path = None
    complete = False
    try:
        now = utc()
        name = '%s-%s.dump.%s' % (config.src[3], now.strftime('%Y%m%dT%H%M%SZ'), config.tool)
        proposed = config.local / name
        if proposed.exists() or name in manifest(Destination(str(config.local))):
            raise Fail('backup_exists')
        with proposed.open('xb') as out:
            path = proposed  # cleanup only files this process actually created
            stream([config.client('pg_dump', config.src, ['--format=custom']), config.crypt()],
                   out, 'dump_interrupted')
        dest = Destination(str(config.local))
        stream([dest.reader(name), config.crypt(True), restore_list(config)], reason='archive_unreadable')
        # RPO measures dump start, irrespective of how long encryption takes.
        # rsync -a preserves this time at each destination. The sidecar below
        # keeps its real completion time for the drill-start exclusion guard.
        os.utime(str(path), (now.timestamp(), now.timestamp()))
        digest = dest.sha(name)
        dest.path(name + '.sha256').write_text(digest + '\n')
        with dest.path('manifest.tsv').open('a', newline='') as f:
            csv.writer(f, delimiter='\t', lineterminator='\n').writerow(
                [name, digest, now.strftime(STAMP), config.src[0], config.src[3]])
        complete = True
        for target, label in ((config.off, 'offmachine'), (config.second, 'second')):
            if target is None:
                print('second=not-configured (awaiting the data-handling decision, §18 row 8 / R-136)')
                continue
            target.mkdir()
            for item in (path, config.local / (name + '.sha256'), config.local / 'manifest.tsv'):
                target.copy(item)
            if target.sha(name) != digest or target.read(name + '.sha256').decode().strip() != digest:
                raise Fail(label + '_verification_failed')
            extras(config, target)
            target.prune(config.src[3], config.retention)
        dest.prune(config.src[3], config.retention)
        print('pg_backup: date=%s file=%s sha256=%s archive_readable=ok offmachine_verified=ok second_verified=%s enc=%s result=PASS' %
              (utc().strftime(STAMP), name, digest, 'ok' if config.second else 'not-configured', config.tool))
    finally:
        if path is not None and not complete and path.exists():
            path.unlink()
            side = path.with_name(path.name + '.sha256')
            if side.exists():
                side.unlink()
        for extra in getattr(config, 'extra_cleanup', []):
            if extra.exists():
                extra.unlink()
        lock.rmdir()


def extras(config, destination):
    paths = config.e.get('EXTRA_PATHS', '').splitlines()
    if not paths:
        return
    checked = [external_path(value) for value in paths]
    if any(not p.exists() for p in checked):
        raise Fail('invalid_extra_path')
    target = Destination(destination.value + '/extras')
    target.mkdir()
    # One encrypted snapshot is copied to both locations, never a plaintext temp file.
    if not hasattr(config, 'extra_bundle'):
        name = 'extras-' + utc().strftime('%Y%m%dT%H%M%SZ') + '.tar.' + config.tool
        path = config.work / name
        side = path.with_name(name + '.sha256')
        if path.exists() or side.exists():
            raise Fail('extras_exists')
        config.extra_cleanup = []
        with path.open('xb') as out:
            config.extra_cleanup.append(path)
            stream([['tar', '-cf', '-', '--'] + [str(p) for p in checked], config.crypt()],
                   out, 'extras_interrupted')
        digest = Destination(str(config.work)).sha(name)
        with side.open('x') as f:
            config.extra_cleanup.append(side)
            f.write(digest + '\n')
        config.extra_bundle = (path, side, digest)
    path, side, digest = config.extra_bundle
    target.copy(path)
    target.copy(side)
    if target.sha(path.name) != digest or target.read(side.name).decode().strip() != digest:
        raise Fail('extras_verification_failed')


def restore_list(config):
    return config.compose + ['pg_restore', '-l'] if config.compose else ['pg_restore', '-l']


def restore_result(config, start, mono, rpo, failures, log=None):
    rto = (time.monotonic() - mono) / 60
    if rto > 60:
        failures.append('rto_exceeded')
    for reason in failures:
        print('result=FAIL reason=' + reason)
    line = '%s, %.6f, %.6f, %s' % (start.strftime(STAMP), rpo, rto, 'FAIL' if failures else 'PASS')
    if log is None:
        with config.log.open('a') as f:
            f.write(line + '\n')
    else:
        log.write(line + '\n')
        log.flush()
    print(line)
    return 1 if failures else 0


def drill(config, destroy=False):
    start, mono = utc(), time.monotonic()
    canary, expected = parse_canary(config.canary)
    when, name, digest = candidate(config.off, config.src, start.timestamp())
    rpo = (start.timestamp() - when) / 3600
    guards(config)
    commands = [config.off.reader(name), config.crypt(True, ARCHIVE.fullmatch(name).group(3))]
    # gpg --no-options + --no-autostart is read-only even if work does not exist.
    stream(commands + [restore_list(config)], reason='restore_failed')
    if not destroy:
        if rpo > 24:
            raise Fail('backup_too_old')
        print('result=DRY_RUN action=drop_create_restore_verify rpo_h=%.6f writes=none' % rpo)
        return 0
    failures = ['backup_too_old'] if rpo > 24 else []
    # Open and retain the append handle before any destructive SQL. Dry-run
    # never reaches this point and remains write-free.
    try:
        log = safe_path(str(config.log)).open('a')
    except OSError:
        raise Fail('restore_log_unwritable')
    with log:
        return destructive_restore(config, commands, name, digest, canary, expected,
                                   start, mono, rpo, failures, log)


def destructive_restore(config, commands, name, digest, canary, expected,
                        start, mono, rpo, failures, log):
    # Repeat both guards immediately before destruction; neither has an override.
    guards(config)
    try:
        admin = config.dst[:3] + ('postgres',)
        if config.dst[3] == 'postgres':
            raise Fail('invalid_target_database')
        config.sql(admin, 'DROP DATABASE ' + ident(config.dst[3]))
        config.sql(admin, 'CREATE DATABASE ' + ident(config.dst[3]) + ' OWNER ' + ident(config.dst[2]))
        stream(commands + [config.client('pg_restore', config.dst,
                                        ['--exit-on-error', '--no-owner', '--no-privileges'])])
        # Re-read after restore to detect destination changes during consumption.
        if config.off.sha(name) != digest:
            raise Fail('unregistered_backup')
        tables = config.sql(config.dst, "SELECT n.nspname || '.' || c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind IN ('r','p') "
            "AND NOT c.relispartition AND n.nspname NOT IN ('pg_catalog','information_schema') "
            "AND n.nspname NOT LIKE 'pg_toast%' AND NOT "
            "(n.nspname='public' AND c.relname='gars_drill_target') ORDER BY 1").splitlines()
        actual = {t: checksum_table(config, config.dst, t) for t in tables}
        if not actual or not sum(v[0] for v in actual.values()):
            raise Fail('empty_database')
        if set(actual) != set(expected):
            raise Fail('count_mismatch')
        if any(actual[t][0] != expected[t][0] for t in actual):
            raise Fail('count_mismatch')
        if any(actual[t][1] != expected[t][1] for t in actual):
            raise Fail('checksum_mismatch')
        # Hex encoding makes arbitrary sealed values safe SQL literals without quoting ambiguity.
        encoded = canary[2].encode().hex()
        query = 'SELECT EXISTS (SELECT 1 FROM ' + table_ident(canary[0]) + ' WHERE ' + ident(canary[1])
        query += "::text = convert_from(decode('" + encoded + "','hex'),'UTF8'))"
        if config.sql(config.dst, query) != 't':
            raise Fail('canary_missing')
    except Fail as exc:
        failures.append(str(exc) if str(exc) != 'command_failed' else 'restore_failed')
    except KeyboardInterrupt:
        failures.append('restore_interrupted')
    except (OSError, ValueError, UnicodeError):
        failures.append('restore_failed')
    return restore_result(config, start, mono, rpo, failures, log=log)


def connect(hostname, number):
    try:
        with socket.create_connection((hostname, number), timeout=3):
            return 'open'
    except (ConnectionRefusedError, socket.timeout):
        return 'closed'
    except OSError:
        return 'unknown'


def exposure():
    require(EXPOSURE)
    e = os.environ
    public, control, tailnet = [host(e[k]) for k in
        ('EXPOSURE_PUBLIC_HOST', 'EXPOSURE_CONTROL_HOST', 'EXPOSURE_TAILNET_HOST')]
    log = safe_path(e['EXPOSURE_LOG'])
    ports = [port(v) for v in e['EXPOSURE_PORTS'].split()]
    if not ports:
        raise Fail('missing_EXPOSURE_PORTS')
    cp = port(e['EXPOSURE_CONTROL_PORT'])
    try:
        ips = [{a[4][0] for a in socket.getaddrinfo(h, None)} for h in (public, control, tailnet)]
    except OSError:
        raise Fail('host_unresolved')
    if ips[1] & (ips[0] | ips[2]):
        raise Fail('control_not_third_host')
    try:
        argv = shlex.split(e.get('SOURCE_IP_CMD', 'curl -s https://ifconfig.me'))
        if not argv:
            raise Fail('source_ip_missing')
        source = run(argv, timeout=10).decode().strip()
        ipaddress.ip_address(source)
    except (ValueError, UnicodeError, Fail):
        raise Fail('source_ip_missing')
    control_state = connect(control, cp)
    observations = [(p, connect(public, p)) for p in ports]
    opened = [str(p) for p, state in observations if state == 'open']
    on_tailnet = False
    if shutil.which('tailscale'):
        try:
            run(['tailscale', 'status'], timeout=5)
            on_tailnet = True
        except Fail:
            pass
    result = 'FAIL' if opened else 'PASS'
    if on_tailnet:
        print('note: this host is ON the tailnet; the outside claim needs a host that is not')
    if on_tailnet or control_state != 'open' or any(s == 'unknown' for _, s in observations):
        result = 'INCONCLUSIVE'
    line = '%s, %s, %s, %s, %s' % (utc().strftime(STAMP), source, control_state,
                                     '|'.join(opened) or '0', result)
    with log.open('a') as f:
        f.write(line + '\n')
    print(line)
    return 0 if result == 'PASS' else 1


def main():
    os.umask(0o077)
    # Libpq must not consume connection services/options/passwords from the caller.
    for key in list(os.environ):
        if key.startswith('PG') and key not in set(SOURCE + ('PG_CLIENT_MODE', 'PG_PASSWORD_FILE',
                                                           'PG_BIND_ADDR', 'PG_PORT', 'PG_RESTART', 'PG_DATA_DIR')):
            del os.environ[key]
    os.environ['PGCONNECT_TIMEOUT'] = '5'
    try:
        mode = sys.argv[1]
        args = sys.argv[2:]
        if mode == 'exposure' and not args:
            return exposure()
        if mode == 'backup' and not args:
            def interrupted(*_):
                raise Fail('dump_interrupted')
            for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                signal.signal(signum, interrupted)
            backup(Config())
            return 0
        if mode == 'drill' and args in ([], ['--dry-run'], ['--destroy']):
            def restore_interrupted(*_):
                raise Fail('restore_interrupted')
            for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                signal.signal(signum, restore_interrupted)
            return drill(Config(True), args == ['--destroy'])
        raise Fail('invalid_arguments')
    except (Fail, OSError, ValueError, UnicodeError, KeyboardInterrupt) as exc:
        reason = str(exc) if isinstance(exc, Fail) else 'operation_failed'
        print('result=FAIL reason=' + reason)
        return 1


if __name__ == '__main__':
    sys.exit(main())
