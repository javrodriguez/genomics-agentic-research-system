"""Row 5 CLI tests, stdlib / Python 3.6.

Scheduled state x drill grid: absent -> no_scheduled_backup; registered fresh ->
restore; registered >24h -> backup_too_old; created after start -> ignored;
unregistered -> ignored; digest mismatch -> unregistered_backup; drift ->
timestamp_drift. No database may be inherited. Real PostgreSQL tests only use a
new compose project with scratch-backed volume; all gates have explicit skips.
"""
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / 'infra/backup'
spec = importlib.util.spec_from_file_location('row05', str(SCRIPTS / 'row05.py'))
row = importlib.util.module_from_spec(spec)
spec.loader.exec_module(row)
# The result grammar belongs to the tests, not imported from the implementation.
RESULT = re.compile(r'^(?:\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ, \d+\.\d{6}, \d+\.\d{6}, (?:PASS|FAIL)|'
                    r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ, [0-9a-fA-F:.]+, (?:open|closed|unknown), [0-9|]+, (?:PASS|FAIL|INCONCLUSIVE)|'
                    r'pg_backup: date=\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ file=[A-Za-z0-9_.-]+ sha256=[0-9a-f]{64} '
                    r'archive_readable=ok offmachine_verified=ok second_verified=(?:ok|not-configured) enc=(?:gpg|age) result=PASS|'
                    r'result=(?:FAIL|IGNORED) reason=[A-Za-z0-9_]+|'
                    r'result=DRY_RUN action=drop_create_restore_verify rpo_h=\d+\.\d{6} writes=none)$')
LOGS = [REPO / ('docs/ops/' + x + '-log.md') for x in ('restore', 'exposure')]


def scratch():
    value = os.environ.get('GARS_ROW5_SCRATCH')
    if not value:
        raise RuntimeError('GARS_ROW5_SCRATCH is required; no system-temp fallback')
    p = Path(value).resolve()
    if not p.is_dir() or p == REPO or REPO in p.parents:
        raise RuntimeError('GARS_ROW5_SCRATCH must be an existing directory outside the repository')
    return p


def scrubbed_env(values=None):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PG', 'DRILL_', 'BACKUP_', 'EXPOSURE_', 'ENC_', 'COMPOSE_'))
           and k not in ('RESTORE_LOG', 'SOURCE_IP_CMD', 'CONTAINER_ENGINE', 'EXTRA_PATHS', 'RETENTION_COUNT')
           and not k.endswith('_LOG')}
    env.update({k: str(scratch()) for k in ('TMPDIR', 'TEMP', 'TMP', 'GARS_ROW5_SCRATCH')})
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    if values:
        env.update({k: str(v) for k, v in values.items()})
    return env


def execute(script, env=None, args=()):
    proc = subprocess.run(['bash', str(SCRIPTS / script)] + list(args), env=scrubbed_env(env),
                          cwd=str(REPO), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          universal_newlines=True, timeout=90)
    for line in proc.stdout.splitlines():
        if line.startswith(('result=', 'pg_backup:')) or re.match(r'^\d{4}-', line):
            if not RESULT.fullmatch(line):
                raise AssertionError('unparseable result line: ' + line)
    return proc


def repository_bytes():
    # No reads outside repo/scratch. Include untracked implementation files, exclude git internals.
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in REPO.rglob('*') if p.is_file() and '.git' not in p.parts
            }


class Row05OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='row05-', dir=str(scratch())))
        self.before = repository_bytes()
        self.logs = [p.read_bytes() for p in LOGS]
        self.env = self.fixture()
        self.clean_context = mock.patch.dict(os.environ, scrubbed_env(self.env), clear=True)
        self.clean_context.start()
        self.addCleanup(self.clean_context.stop)

    def tearDown(self):
        self.assertEqual(repository_bytes(), self.before, 'a test changed repository bytes')
        for p, before in zip(LOGS, self.logs):
            self.assertEqual(p.read_bytes(), before)
            self.assertNotRegex(p.read_text(), r'(?m)^\| .*PASS')
        shutil.rmtree(str(self.tmp))

    def fixture(self):
        local = self.tmp / 'local'
        work = local / 'private'
        work.mkdir(parents=True)
        key = self.tmp / 'key'
        key.write_text('synthetic-test-passphrase\n')
        key.chmod(0o600)
        canary = self.tmp / 'canary.csv'
        canary.write_text('canary,public.items,value,sealed\npublic.items,1,' + '0' * 32 + '\n')
        return dict(PGHOST='127.0.0.1', PGPORT='5432', PGUSER='fixture', PGDATABASE='source',
                    PGPASSFILE=str(key), PG_CLIENT_MODE='host', ENC_TOOL='auto', ENC_KEY_FILE=str(key),
                    ENC_IDENTITY_FILE=str(key), BACKUP_LOCAL_DIR=str(local), BACKUP_WORK_DIR=str(work),
                    BACKUP_OFFMACHINE_DEST=str(self.tmp / 'off machine'),
                    BACKUP_SECOND_DEST=str(self.tmp / 'second'),
                    DRILL_TARGET_PGHOST='127.0.0.1', DRILL_TARGET_PGPORT='5432',
                    DRILL_TARGET_PGUSER='fixture', DRILL_TARGET_PGDATABASE='recovery',
                    DRILL_CANARY_FILE=str(canary), RESTORE_LOG=str(self.tmp / 'restore.log'))

    def refused(self, proc, reason):
        self.assertNotEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('reason=' + reason, proc.stdout)
        self.assertNotRegex(proc.stdout, r'\bPASS\b')
        self.assertNotIn('synthetic-test-passphrase', proc.stdout)

    def test_missing_variables_each_script(self):
        for script, required in [('pg_backup.sh', row.COMMON),
                                 ('restore_drill.sh', row.COMMON + row.TARGET + ('DRILL_CANARY_FILE', 'RESTORE_LOG')),
                                 ('test_exposure.sh', row.EXPOSURE)]:
            for key in required:
                with self.subTest(script=script, key=key):
                    env = dict(self.env)
                    env.update({k: 'placeholder' for k in row.EXPOSURE})
                    env.pop(key, None)
                    self.refused(execute(script, env), 'missing_' + key)
        for key in ('COMPOSE_PROJECT', 'PG_PASSWORD_FILE'):
            env = dict(self.env, PG_CLIENT_MODE='container', COMPOSE_PROJECT='fixture',
                       PG_PASSWORD_FILE=self.env['PGPASSFILE'])
            del env[key]
            self.refused(execute('pg_backup.sh', env), 'missing_' + key)

    def test_poison_environment_is_scrubbed(self):
        poison = dict(PGDATABASE='some_real_name', PGHOST='do-not-connect', PGOPTIONS='poison',
                      DRILL_TARGET_PGDATABASE='real', BACKUP_LOCAL_DIR='bad', RESTORE_LOG='bad',
                      EXPOSURE_LOG='bad', ENC_KEY_FILE='bad', SOURCE_IP_CMD='bad')
        with mock.patch.dict(os.environ, poison):
            clean = scrubbed_env()
            self.assertTrue(all(k not in clean for k in poison))
            self.refused(execute('restore_drill.sh'), 'missing_PGHOST')
            case = dict(self.env)
            del case['PGDATABASE']
            self.refused(execute('restore_drill.sh', case), 'missing_PGDATABASE')
            self.refused(execute('restore_drill.sh', case, ('--destroy', '--force')), 'invalid_arguments')

    def test_required_scratch_and_no_system_temp(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'GARS_ROW5_SCRATCH'):
                scrubbed_env()
        env = scrubbed_env()
        self.assertTrue(all(env[k] == str(scratch()) for k in ('TMPDIR', 'TMP', 'TEMP')))
        self.assertNotIn('TMPDIR', (SCRIPTS / 'row05.py').read_text())

    def test_no_encryption_tool_refuses(self):
        with mock.patch.dict(os.environ, scrubbed_env(self.env), clear=True), mock.patch.object(row.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(row.Fail, 'encryption_unavailable'):
                row.Config()

    def test_path_guards_and_injection(self):
        for change, reason in [({'BACKUP_LOCAL_DIR': REPO}, 'local_dir_in_repo'),
                               ({'BACKUP_WORK_DIR': self.tmp}, 'work_dir_outside_local'),
                               ({'PGHOST': 'a;bad'}, 'invalid_host'),
                               ({'BACKUP_OFFMACHINE_DEST': 'u@host:/a;bad'}, 'invalid_destination')]:
            env = dict(self.env, **change)
            self.refused(execute('pg_backup.sh', env), reason)
        link = self.tmp / 'link'
        link.symlink_to(self.tmp / 'local', target_is_directory=True)
        self.refused(execute('pg_backup.sh', dict(self.env, BACKUP_LOCAL_DIR=str(link))), 'unsafe_path')

    def register(self, age=10, content=b'encrypted fixture', db='source'):
        dest = row.Destination(self.env['BACKUP_OFFMACHINE_DEST'])
        dest.mkdir()
        when = row.utc() - dt.timedelta(seconds=age)
        name = db + '-' + when.strftime('%Y%m%dT%H%M%SZ') + '.dump.gpg'
        p = dest.root / name
        p.write_bytes(content)
        os.utime(str(p), (when.timestamp(), when.timestamp()))
        digest = hashlib.sha256(content).hexdigest()
        (dest.root / (name + '.sha256')).write_text(digest + '\n')
        (dest.root / 'manifest.tsv').write_text('\t'.join([name, digest, when.strftime(row.STAMP), '127.0.0.1', db]) + '\n')
        return dest, p, when

    def test_manifest_state_grid(self):
        dest = row.Destination(self.env['BACKUP_OFFMACHINE_DEST'])
        src = ('127.0.0.1', 5432, 'fixture', 'source')
        with self.assertRaisesRegex(row.Fail, 'no_scheduled_backup'):
            row.candidate(dest, src, time.time())
        dest, p, when = self.register()
        self.assertEqual(row.candidate(dest, src, time.time())[1], p.name)
        original = (dest.root / 'manifest.tsv').read_text()
        for fault, reason in [('corrupt', 'unregistered_backup'), ('sidecar', 'unregistered_backup'),
                              ('duplicate', 'manifest_ambiguous'), ('drift', 'timestamp_drift'),
                              ('future', 'no_scheduled_backup'), ('stray', 'no_scheduled_backup')]:
            with self.subTest(fault=fault):
                dest, p, when = self.register()
                if fault == 'corrupt':
                    p.write_bytes(b'corrupt')
                    os.utime(str(p), (when.timestamp(), when.timestamp()))
                elif fault == 'sidecar':
                    (dest.root / (p.name + '.sha256')).write_text('0' * 64)
                elif fault == 'duplicate':
                    (dest.root / 'manifest.tsv').write_text(original * 2)
                elif fault == 'stray':
                    (dest.root / 'manifest.tsv').unlink()
                else:
                    value = time.time() + 60 if fault == 'future' else time.time() - 600
                    os.utime(str(p), (value, value))
                with self.assertRaisesRegex(row.Fail, reason):
                    row.candidate(dest, src, time.time())
        dest, p, _ = self.register(age=25 * 3600)
        selected = row.candidate(dest, src, time.time())
        self.assertGreater((time.time() - selected[0]) / 3600, 24)

    def test_canary_example_crlf_and_duplicates(self):
        row.parse_canary(SCRIPTS / 'canary.example')
        path = Path(self.env['DRILL_CANARY_FILE'])
        path.write_bytes(path.read_bytes().replace(b'\n', b'\r\n'))
        self.assertEqual(row.parse_canary(path)[0][2], 'sealed')
        with path.open('a') as f:
            f.write('public.items,1,' + '0' * 32 + '\n')
        with self.assertRaisesRegex(row.Fail, 'invalid_canary'):
            row.parse_canary(path)

    def test_retention_cold_start_and_scope(self):
        dest = row.Destination(self.env['BACKUP_OFFMACHINE_DEST'])
        dest.mkdir()
        dest.prune('source', 14)
        for i in range(16):
            name = 'source-202609%02dT000000Z.dump.gpg' % (i + 1)
            (dest.root / name).write_text('cipher')
            (dest.root / (name + '.sha256')).write_text('hash')
        (dest.root / 'manifest.tsv').write_text('preserve history')
        (dest.root / 'other-20260901T000000Z.dump.gpg').write_text('other database')
        dest.prune('source', 14)
        self.assertEqual(len(list(dest.root.glob('source-*.dump.gpg'))), 14)
        self.assertFalse((dest.root / 'source-20260901T000000Z.dump.gpg').exists())
        self.assertEqual((dest.root / 'manifest.tsv').read_text(), 'preserve history')
        self.assertTrue((dest.root / 'other-20260901T000000Z.dump.gpg').exists())

    def stub(self, name, body):
        bindir = self.tmp / 'bin'
        bindir.mkdir(exist_ok=True)
        p = bindir / name
        p.write_text('#!/usr/bin/env python3\n' + body)
        p.chmod(0o700)
        self.env['PATH'] = str(bindir) + os.pathsep + os.environ['PATH']
        return p

    def test_stream_encryption_cold_backup_and_failed_dump(self):
        # Real gpg and rsync, stub archive producer/listing only; not database evidence.
        self.stub('pg_dump', "import sys\nsys.stdout.buffer.write(b'fixture archive')\n")
        self.stub('pg_restore', "import sys\nsys.stdin.buffer.read()\n")
        extra = self.tmp / 'vault fixture'
        extra.write_text('synthetic vault bytes')
        self.env['EXTRA_PATHS'] = str(extra)
        proc = execute('pg_backup.sh', self.env)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('archive_readable=ok offmachine_verified=ok second_verified=ok enc=gpg', proc.stdout)
        local = Path(self.env['BACKUP_LOCAL_DIR'])
        files = list(local.glob('*.dump.gpg'))
        self.assertEqual(len(files), 1)
        self.assertNotIn(b'fixture archive', files[0].read_bytes())
        for target in ('BACKUP_OFFMACHINE_DEST', 'BACKUP_SECOND_DEST'):
            self.assertEqual(files[0].read_bytes(), (Path(self.env[target]) / files[0].name).read_bytes())
        first_extra = next((Path(self.env['BACKUP_OFFMACHINE_DEST']) / 'extras').glob('*.tar.gpg'))
        second_extra = Path(self.env['BACKUP_SECOND_DEST']) / 'extras' / first_extra.name
        self.assertEqual(first_extra.read_bytes(), second_extra.read_bytes())
        self.assertNotIn(b'synthetic vault bytes', first_extra.read_bytes())
        # A colliding run must not delete the valid scheduled file.
        proc = execute('pg_backup.sh', self.env)
        if 'backup_exists' in proc.stdout:
            self.assertTrue(files[0].exists())
        for p in local.glob('*.dump.gpg*'):
            p.unlink()
        time.sleep(1.1)  # fresh filename; manifest registrations are never reused
        no_second = dict(self.env, BACKUP_SECOND_DEST='')
        proc = execute('pg_backup.sh', no_second)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn('second_verified=not-configured', proc.stdout)
        for p in local.glob('*.dump.gpg*'):
            p.unlink()
        time.sleep(1.1)
        self.stub('pg_dump', "import os,signal,sys\nsys.stdout.buffer.write(b'partial');sys.stdout.flush()\nos.kill(os.getpid(),signal.SIGKILL)\n")
        self.refused(execute('pg_backup.sh', self.env), 'dump_interrupted')
        self.assertFalse(list(local.glob('*.dump.gpg')))
        ready = self.tmp / 'dump-ready'
        self.env['DUMP_READY'] = str(ready)
        self.stub('pg_dump', "import os,sys,time\nfrom pathlib import Path\nsys.stdout.buffer.write(b'partial');sys.stdout.flush()\nPath(os.environ['DUMP_READY']).write_text('ready')\ntime.sleep(30)\n")
        parent = subprocess.Popen(['bash', str(SCRIPTS / 'pg_backup.sh')],
                                  env=scrubbed_env(self.env), cwd=str(REPO),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  universal_newlines=True)
        try:
            end = time.monotonic() + 10
            while not ready.exists() and time.monotonic() < end:
                time.sleep(0.05)
            self.assertTrue(ready.exists(), 'dump producer never started')
            parent.send_signal(signal.SIGINT)
            output = parent.communicate(timeout=15)[0]
            self.refused(subprocess.CompletedProcess([], parent.returncode, output), 'dump_interrupted')
            self.assertFalse(list(local.glob('*.dump.gpg')))
        finally:
            if parent.poll() is None:
                parent.terminate()
                parent.communicate(timeout=15)

    def test_stdout_log_equality_and_rto_threshold(self):
        with mock.patch.dict(os.environ, scrubbed_env(self.env), clear=True):
            cfg = row.Config(True)
        for elapsed, expected in [(1, 'PASS'), (3601, 'FAIL')]:
            output = io.StringIO()
            with contextlib.redirect_stdout(output), mock.patch.object(row.time, 'monotonic', return_value=elapsed):
                row.restore_result(cfg, row.utc(), 0, 2, [])
            line = output.getvalue().splitlines()[-1]
            self.assertRegex(line, RESULT)
            self.assertTrue(line.endswith(expected))
            self.assertEqual(cfg.log.read_text().splitlines()[-1], line)

    def test_identity_and_marker_guards_without_database(self):
        cfg = mock.Mock()
        cfg.src, cfg.dst = 'source', 'target'
        for responses, reason in [
                (['127.0.0.1|5432|source'] * 2, 'target_is_primary'),
                (['127.0.0.1|5432|source', '::1|5432|source', '123', '123'], 'target_is_primary'),
                (['127.0.0.1|5432|source', '127.0.0.1|5432|recovery', '123', '123', 'f'], 'target_not_marked'),
                (['||source'], 'identity_unresolved')]:
            with self.subTest(reason=reason):
                cfg.sql.side_effect = responses
                with self.assertRaisesRegex(row.Fail, reason):
                    row.guards(cfg)
                self.assertTrue(all('DROP' not in str(call) for call in cfg.sql.call_args_list))
                cfg.reset_mock()

    def test_restore_fault_decisions_without_database(self):
        # State-machine evidence only. Database SQL/restore integration remains separately gated.
        dest, archive, when = self.register()
        cfg = row.Config(True)
        for fault in ('clean', 'count_mismatch', 'checksum_mismatch', 'canary_missing',
                      'empty_database', 'restore_failed', 'backup_too_old'):
            with self.subTest(fault=fault):
                output = io.StringIO()
                tables = '' if fault == 'empty_database' else 'public.items'
                sql = mock.Mock(side_effect=['', '', tables, 'f' if fault == 'canary_missing' else 't'])
                actual = (2 if fault == 'count_mismatch' else 1,
                          '1' * 32 if fault == 'checksum_mismatch' else '0' * 32)
                started = when.timestamp() - (25 * 3600 if fault == 'backup_too_old' else 0)
                with mock.patch.object(row, 'guards'), mock.patch.object(cfg, 'sql', sql), \
                     mock.patch.object(row, 'candidate', return_value=(started, archive.name, dest.sha(archive.name))), \
                     mock.patch.object(row, 'checksum_table', return_value=actual), \
                     mock.patch.object(row, 'stream', side_effect=[b'', row.Fail('restore_failed')]
                                       if fault == 'restore_failed' else [b'', b'']), \
                     contextlib.redirect_stdout(output):
                    code = row.drill(cfg, True)
                line = output.getvalue().splitlines()[-1]
                self.assertRegex(line, RESULT)
                self.assertEqual(cfg.log.read_text().splitlines()[-1], line)
                if fault == 'clean':
                    self.assertEqual(code, 0)
                else:
                    self.assertEqual(code, 1)
                    self.assertIn('reason=' + fault, output.getvalue())
                    self.assertNotRegex(output.getvalue(), r'\bPASS\b')

    def test_exposure_local_listeners_and_controls(self):
        public = socket.socket()
        control = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        public.bind(('127.0.0.1', 0))
        control.bind(('::1', 0))
        public.listen(20)
        control.listen(20)
        closed = socket.socket()
        closed.bind(('127.0.0.1', 0))
        closed_port = closed.getsockname()[1]
        closed.close()
        self.stub('source-ip', "print('192.0.2.1')\n")
        self.stub('tailscale', 'import sys\nsys.exit(1)\n')
        env = dict(self.env, EXPOSURE_PUBLIC_HOST='127.0.0.1', EXPOSURE_TAILNET_HOST='127.0.0.3',
                   EXPOSURE_CONTROL_HOST='::1', EXPOSURE_CONTROL_PORT=str(control.getsockname()[1]),
                   EXPOSURE_PORTS='%s %s' % (public.getsockname()[1], closed_port),
                   EXPOSURE_LOG=str(self.tmp / 'exposure.log'), SOURCE_IP_CMD='source-ip')
        try:
            p = execute('test_exposure.sh', env)
            line = p.stdout.strip().splitlines()[-1]
            self.assertRegex(line, RESULT)
            self.assertTrue(line.endswith('FAIL'), p.stdout)
            self.assertIn(', %s, FAIL' % public.getsockname()[1], line)
            self.assertEqual(Path(env['EXPOSURE_LOG']).read_text().strip(), line)
            env['EXPOSURE_PORTS'] = str(closed_port)
            p = execute('test_exposure.sh', env)
            self.assertEqual(p.returncode, 0, p.stdout)
            self.assertTrue(p.stdout.strip().endswith('PASS'))
            self.stub('tailscale', 'import sys\nsys.exit(0)\n')
            p = execute('test_exposure.sh', env)
            self.assertIn('ON the tailnet', p.stdout)
            self.assertTrue(p.stdout.strip().endswith('INCONCLUSIVE'))
            self.stub('tailscale', 'import sys\nsys.exit(1)\n')
            control.close()
            p = execute('test_exposure.sh', env)
            self.assertTrue(p.stdout.strip().endswith('INCONCLUSIVE'))
            env['SOURCE_IP_CMD'] = 'source-ip'
            self.stub('source-ip', 'print("")\n')
            self.refused(execute('test_exposure.sh', env), 'source_ip_missing')
            env['SOURCE_IP_CMD'] = ''
            self.refused(execute('test_exposure.sh', env), 'source_ip_missing')
        finally:
            public.close()
            control.close()

    def test_runner_reachability_and_skip_path(self):
        sys.path.insert(0, str(REPO / 'tests'))
        import run_tests
        for name in ('Row05OfflineTests', 'Row05DatabaseTests'):
            self.assertTrue(hasattr(run_tests, name))
        p = subprocess.run([sys.executable, '-B', str(Path(__file__)), 'Row05DatabaseTests'],
                           env=scrubbed_env({'GARS_TEST_NO_CONTAINER': '1'}), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, cwd=str(REPO))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertIn('SKIPPED: GARS_TEST_NO_CONTAINER=1', p.stdout)
        self.assertIn('skipped=', p.stdout)


class Row05DatabaseTests(unittest.TestCase):
    """Only a uniquely named, scratch-volume compose stack is permitted here."""
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='row05-db-', dir=str(scratch())))
        cls.probe = ''
        cls.command = None
        cls.env = {}
        cls.before = repository_bytes()
        cls.engine = next((name for name in ('docker', 'podman') if shutil.which(name)), None)
        if os.environ.get('GARS_TEST_NO_CONTAINER') == '1':
            cls.probe = 'GARS_TEST_NO_CONTAINER=1'
            return
        if not cls.engine:
            cls.probe = 'docker info / podman info: executable absent'
            return
        try:
            p = subprocess.run([cls.engine, 'info'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                               env=scrubbed_env(), timeout=15)
        except subprocess.TimeoutExpired:
            cls.probe = cls.engine + ' info: timed out after 15 s'
            return
        if p.returncode:
            cls.probe = cls.engine + ' info: exit ' + str(p.returncode)
            return
        cls.password = cls.tmp / 'password'
        cls.password.write_text(uuid.uuid4().hex)
        cls.password.chmod(0o600)
        data = cls.tmp / 'pgdata'
        data.mkdir()
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        published = sock.getsockname()[1]
        sock.close()
        cls.env = dict(PGUSER='fixture', PGDATABASE='source', PGHOST='127.0.0.1', PGPORT='5432',
                       PG_PORT=str(published), PG_BIND_ADDR='127.0.0.1', PG_RESTART='no',
                       PG_DATA_DIR=str(data), PG_PASSWORD_FILE=str(cls.password),
                       COMPOSE_PROJECT='gars-row5-%s-%s' % (os.getpid(), uuid.uuid4().hex[:8]),
                       COMPOSE_VOLUME_SUFFIX='-' + uuid.uuid4().hex[:8],
                       CONTAINER_ENGINE=cls.engine, PG_CLIENT_MODE='container',
                       PGPASSFILE=str(cls.password), ENC_KEY_FILE=str(cls.password),
                       ENC_IDENTITY_FILE=str(cls.password), ENC_TOOL='auto')
        cls.command = [cls.engine, 'compose', '-f', str(REPO / 'infra/compose/postgres.compose.yml'),
                       '-p', cls.env['COMPOSE_PROJECT']]
        healthy = False
        end = time.monotonic() + 60
        try:
            p = cls.compose(['up', '-d'], timeout=60)
            if p.returncode:
                cls.probe = cls.engine + ' compose up -d: exit ' + str(p.returncode)
                return
            while time.monotonic() < end:
                cid = cls.compose(['ps', '-q', 'db']).stdout.strip()
                if cid:
                    p = subprocess.run([cls.engine, 'inspect', '--format', '{{.State.Health.Status}}', cid],
                                       env=scrubbed_env(cls.env), stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, universal_newlines=True)
                    if p.returncode == 0 and p.stdout.strip() == 'healthy':
                        healthy = True
                        break
                time.sleep(1)
            if not healthy:
                cls.probe = cls.engine + ' compose db health: not healthy within 60 s'
        except subprocess.TimeoutExpired:
            cls.probe = cls.engine + ' compose readiness: timed out'
        finally:
            if not healthy:
                cls.compose(['down', '-v'])
                cls.command = None

    @classmethod
    def compose(cls, args, timeout=60):
        return subprocess.run(cls.command + args, env=scrubbed_env(cls.env), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout)

    @classmethod
    def tearDownClass(cls):
        try:
            if repository_bytes() != cls.before:
                raise AssertionError('database tests changed repository bytes')
        finally:
            try:
                if cls.command:
                    p = cls.compose(['down', '-v'])
                    if p.returncode:
                        raise AssertionError('throwaway compose down -v failed')
            finally:
                # A bind volume can retain postgres-owned data, always inside scratch.
                shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def setUp(self):
        if self.probe:
            print('SKIPPED: ' + self.probe, flush=True)
            self.skipTest(self.probe)
        self.case = Path(tempfile.mkdtemp(prefix='case-', dir=str(self.tmp)))
        self.e = dict(self.env, BACKUP_LOCAL_DIR=str(self.case / 'local'),
                      BACKUP_WORK_DIR=str(self.case / 'local/private'),
                      BACKUP_OFFMACHINE_DEST=str(self.case / 'off machine'),
                      BACKUP_SECOND_DEST=str(self.case / 'second'),
                      DRILL_TARGET_PGHOST='127.0.0.1', DRILL_TARGET_PGPORT='5432',
                      DRILL_TARGET_PGUSER='fixture', DRILL_TARGET_PGDATABASE='recovery',
                      DRILL_CANARY_FILE=str(self.case / 'canary'), RESTORE_LOG=str(self.case / 'restore.log'))
        self.clean_context = mock.patch.dict(os.environ, scrubbed_env(self.e), clear=True)
        self.clean_context.start()
        self.addCleanup(self.clean_context.stop)
        self.cfg = row.Config()
        self.sql('postgres', 'DROP DATABASE IF EXISTS source')
        self.sql('postgres', 'CREATE DATABASE source')
        self.sql('postgres', 'DROP DATABASE IF EXISTS recovery')
        self.sql('postgres', 'CREATE DATABASE recovery')
        self.sql('source', 'CREATE TABLE public.items(id integer PRIMARY KEY, value text); '
                          "INSERT INTO public.items VALUES (1,'sealed'),(2,'payload')")
        self.sql('recovery', 'CREATE TABLE public.gars_drill_target(acknowledged_by text)')
        count, digest = row.checksum_table(self.cfg, self.cfg.src, 'public.items')
        Path(self.e['DRILL_CANARY_FILE']).write_text('canary,public.items,value,sealed\npublic.items,%s,%s\n' % (count, digest))
        p = execute('pg_backup.sh', self.e)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.archive = next(Path(self.e['BACKUP_OFFMACHINE_DEST']).glob('*.dump.*'))
        if self.archive.name.endswith('.sha256'):
            self.archive = self.archive.with_name(self.archive.name[:-7])
        # Ensure the archive predates the drill's start, without forging its manifest time.

    def sql(self, db, query):
        return self.cfg.sql(self.cfg.src[:3] + (db,), query)

    def drill(self, reason=None, env=None, args=('--destroy',)):
        p = execute('restore_drill.sh', env or self.e, args)
        if reason:
            self.assertNotEqual(p.returncode, 0, p.stdout)
            self.assertIn('reason=' + reason, p.stdout)
            self.assertNotRegex(p.stdout, r'\bPASS\b')
        else:
            self.assertEqual(p.returncode, 0, p.stdout)
        self.assertNotIn(self.password.read_text(), p.stdout)
        return p

    def rebind(self, age=None):
        dest = self.archive.parent
        record = (dest / 'manifest.tsv').read_text().strip().split('\t')
        if age is not None:
            when = row.utc() - dt.timedelta(hours=age)
            new = dest / ('source-' + when.strftime('%Y%m%dT%H%M%SZ') + '.dump.' + self.cfg.tool)
            self.archive.rename(new)
            self.archive.with_name(self.archive.name + '.sha256').unlink()
            self.archive = new
            record[0], record[2] = new.name, when.strftime(row.STAMP)
        when = row.epoch(record[2])
        os.utime(str(self.archive), (when, when))
        record[1] = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.archive.with_name(self.archive.name + '.sha256').write_text(record[1] + '\n')
        (dest / 'manifest.tsv').write_text('\t'.join(record) + '\n')

    def test_dry_run_and_cold_destroy(self):
        before = {str(p): p.read_bytes() for p in self.case.rglob('*') if p.is_file()}
        p = self.drill(args=())
        self.assertIn('writes=none', p.stdout)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.case.rglob('*') if p.is_file()})
        p = self.drill()
        line = p.stdout.strip().splitlines()[-1]
        self.assertRegex(line, RESULT)
        self.assertTrue(line.endswith('PASS'))
        self.assertEqual(Path(self.e['RESTORE_LOG']).read_text(), line + '\n')
        self.assertEqual(self.sql('recovery', 'SELECT count(*) FROM items'), '2')

    def test_unmarked_target(self):
        self.sql('recovery', 'DROP TABLE gars_drill_target')
        self.drill('target_not_marked')
        self.assertEqual(self.sql('recovery', 'SELECT current_database()'), 'recovery')

    def test_primary_identity(self):
        self.sql('source', 'CREATE TABLE gars_drill_target(acknowledged_by text)')
        self.drill('target_is_primary', dict(self.e, DRILL_TARGET_PGDATABASE='source', DRILL_TARGET_PGHOST='localhost'))
        self.assertEqual(self.sql('source', 'SELECT count(*) FROM items'), '2')

    def test_canary_missing(self):
        p = Path(self.e['DRILL_CANARY_FILE'])
        p.write_text(p.read_text().replace('value,sealed', 'value,absent'))
        self.drill('canary_missing')

    def test_count_mismatch(self):
        p = Path(self.e['DRILL_CANARY_FILE'])
        p.write_text(p.read_text().replace('items,2,', 'items,3,'))
        self.drill('count_mismatch')

    def test_checksum_mismatch_same_count(self):
        self.sql('source', "UPDATE items SET value='changed' WHERE id=2")
        count, digest = row.checksum_table(self.cfg, self.cfg.src, 'public.items')
        self.assertEqual(count, 2)
        Path(self.e['DRILL_CANARY_FILE']).write_text('canary,public.items,value,sealed\npublic.items,2,%s\n' % digest)
        self.drill('checksum_mismatch')

    def test_corrupt_destination(self):
        self.archive.write_bytes(self.archive.read_bytes()[:-1] + b'X')
        self.drill('unregistered_backup')

    def test_stray_and_no_scheduled(self):
        stray = self.archive.parent / 'source-20000101T000000Z.dump.gpg'
        stray.write_bytes(b'not registered')
        self.drill(args=())
        self.archive.unlink()
        self.drill('no_scheduled_backup')

    def test_after_start_ignored(self):
        future = time.time() + 3600
        os.utime(str(self.archive), (future, future))
        self.drill('no_scheduled_backup')

    def test_timestamp_drift(self):
        past = time.time() - 600
        os.utime(str(self.archive), (past, past))
        self.drill('timestamp_drift')

    def test_stale_backup_still_restores_fail(self):
        self.rebind(age=25)
        p = self.drill('backup_too_old')
        self.assertTrue(p.stdout.strip().endswith('FAIL'))
        self.assertEqual(self.sql('recovery', 'SELECT count(*) FROM items'), '2')

    def test_empty_database(self):
        self.sql('source', 'DROP TABLE items')
        with self.archive.open('wb') as out:
            with mock.patch.dict(os.environ, scrubbed_env(self.e), clear=True):
                row.stream([self.cfg.client('pg_dump', self.cfg.src, ['--format=custom', '--schema-only']), self.cfg.crypt()], out)
        self.rebind()
        self.drill('empty_database')

    def test_zero_rows(self):
        self.sql('source', 'TRUNCATE items')
        with self.archive.open('wb') as out:
            with mock.patch.dict(os.environ, scrubbed_env(self.e), clear=True):
                row.stream([self.cfg.client('pg_dump', self.cfg.src, ['--format=custom']), self.cfg.crypt()], out)
        self.rebind()
        self.drill('empty_database')

    def test_truncated_archive(self):
        self.archive.write_bytes(self.archive.read_bytes()[:30])
        self.rebind()
        self.drill('restore_failed')

    def test_missing_canary_file(self):
        Path(self.e['DRILL_CANARY_FILE']).unlink()
        self.drill('canary_missing')

    def test_duplicate_manifest(self):
        p = self.archive.parent / 'manifest.tsv'
        p.write_text(p.read_text() * 2)
        self.drill('manifest_ambiguous')

    def test_second_unset_and_crlf(self):
        p = Path(self.e['DRILL_CANARY_FILE'])
        p.write_bytes(p.read_bytes().replace(b'\n', b'\r\n'))
        self.drill(env=dict(self.e, BACKUP_SECOND_DEST=''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
