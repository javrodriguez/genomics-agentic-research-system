"""S00-class: routes never widen (0321; S00-CLASS-DESIGN.md section 5).

One table over every class x purpose x venue the policy table names, with and without a named
agreement, with and without an expiry: for each, venue_policy.check's decision now is the one it
gave before S00-class (BASE), or a refusal; never a new allow. Under 1c enforcement did not change,
so every row is also equal to its base decision.

Then the registration path, where the only change is allowed to live: what a new registration may
write. The person's finalize refuses a legacy purpose anew; the agent's finalize, through the real
guard, is refused for anything but exactly public with fixture or internal. The agent rows need the
frozen-file hunks R1 and G2 (patch files in lanes/gars-t74/); each such test says which.
"""
import importlib.util
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import GARS, REPO
import manifest_check
import venue_policy

# The base by content (lane gars-t74 before S00-class: the T57 merge and its ruled test), never by
# a commit id, which the landing changes; both blobs are in the landed history.
BASE_BLOBS = {'gars/_system/venue_policy.py': '8dc4f08acaac122f2fcf8aff32eb4f9d9fa0b5b3',
              'gars/_references/data_policy.tsv': '19ae1f098ece04990ccb54f405d1c465c62efc98'}
CLASSES = ('public', 'deidentified_under_agreement', 'identifiable')
PURPOSES = ('fixture', 'internal', 'pilot_internal', 'pilot_external', 'commercial')
VENUES = ('local', 'homelab', 'slurm')
AGREEMENTS = ('none', 'DUA-2026-01')
EXPIRIES = ('none', '2099-12-31')
GIB = 1024 ** 3


def base_policy(tmp):
    """venue_policy.py and data_policy.tsv as they stood at BASE, importable from tmp."""
    system, refs = Path(tmp) / 'gars/_system', Path(tmp) / 'gars/_references'
    system.mkdir(parents=True)
    refs.mkdir(parents=True)
    for rel, dest in (('gars/_system/venue_policy.py', system / 'venue_policy.py'),
                      ('gars/_references/data_policy.tsv', refs / 'data_policy.tsv')):
        dest.write_bytes(subprocess.run(['git', 'cat-file', 'blob', BASE_BLOBS[rel]], cwd=str(REPO),
                                        stdout=subprocess.PIPE, check=True).stdout)
    spec = importlib.util.spec_from_file_location('venue_policy_base', str(system / 'venue_policy.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dataset_row(policy, data_class, purpose, agreement, expiry):
    return {'data_class': data_class, 'purpose': purpose, 'agreement_ref': agreement,
            'input_data_location': '[]',
            'permitted_backends': policy.routes()[data_class]['permitted_backends'],
            'provider_exposure': policy.routes()[data_class]['provider_exposure'],
            'retention': policy.routes()[data_class]['retention_rule'], 'expiry': expiry}


def table():
    for data_class in CLASSES:
        for purpose in PURPOSES:
            for venue in VENUES:
                for agreement in AGREEMENTS:
                    for expiry in EXPIRIES:
                        yield data_class, purpose, venue, agreement, expiry


def decision(policy, data_class, purpose, venue, agreement, expiry):
    row = dataset_row(policy, data_class, purpose, agreement, expiry)
    return sorted(f['detail'] for f in policy.check(row, venue, purpose, GIB, []))


class RouteTableTests(unittest.TestCase):
    """The table: every class x purpose x venue, before and after; never a new allow."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='route-never-widens-')
        cls.before = base_policy(cls.tmp)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_the_table_covers_every_name_the_policy_table_has(self):
        self.assertEqual(set(CLASSES), set(venue_policy.routes()))
        self.assertEqual(set(PURPOSES), set(venue_policy.PURPOSES))
        self.assertEqual(set(VENUES), set(venue_policy.VENUES))
        self.assertEqual(set(PURPOSES), set(self.before.PURPOSES))

    def test_no_row_gains_an_allow(self):
        rows = 0
        for key in table():
            with self.subTest(row=key):
                before, after = decision(self.before, *key), decision(venue_policy, *key)
                if not after:
                    self.assertEqual(before, [], 'a new allow')
                rows += 1
        self.assertEqual(rows, 3 * 5 * 3 * 2 * 2)

    def test_under_1c_every_row_decides_as_before(self):
        for key in table():
            with self.subTest(row=key):
                self.assertEqual(decision(venue_policy, *key), decision(self.before, *key))

    def test_the_route_facts_hold(self):
        allowed = {key for key in table() if not decision(venue_policy, *key)}
        self.assertTrue(allowed)
        for data_class, purpose, venue, agreement, expiry in allowed:
            with self.subTest(row=(data_class, purpose, venue, agreement, expiry)):
                self.assertNotEqual(data_class, 'identifiable')            # refused everywhere
                if data_class != 'public':                                 # restricted:
                    self.assertEqual(venue, 'slurm')                       # cluster only
                    self.assertNotEqual(expiry, 'none')                    # with an expiry
                if venue == 'local':
                    self.assertEqual(purpose, 'fixture')                   # local: test only
                if venue == 'slurm' and purpose == 'pilot_internal':
                    self.assertNotEqual(agreement, 'none')                 # its agreement
        self.assertIn(('public', 'pilot_internal', 'slurm', 'DUA-2026-01', 'none'), allowed)
        self.assertNotIn(('public', 'pilot_internal', 'slurm', 'none', 'none'), allowed)


class OldRecordTests(unittest.TestCase):
    def test_old_run_records_still_pass_manifest_check(self):
        """Group 11 (the route facts) still accepts every purpose a run record carries."""
        schema = manifest_check.load_schema()
        for name in ('nfcore', 'local'):
            path = GARS / 'tests/fixtures/methods' / ('%s-manifest.json' % name)
            manifest = json.loads(path.read_text())
            for purpose in PURPOSES:
                with self.subTest(manifest=name, purpose=purpose):
                    self.assertTrue(manifest_check.group_present(
                        11, dict(manifest, purpose=purpose), schema))


class RegistrationPathTests(unittest.TestCase):
    """The only place a decision may change: what a new registration writes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='route-registration-'))
        cls.ws = cls.tmp / 'gars'
        cls.ws.mkdir()
        for d in ('_system', '_references', '_templates'):
            shutil.copytree(str(GARS / d), str(cls.ws / d),
                            ignore=shutil.ignore_patterns('__pycache__'))
        (cls.ws / 'projects').mkdir()
        cls.seq = cls.tmp / 'seq'
        cls.seq.mkdir()
        import gzip
        for s in ('A1_S1', 'A2_S2'):
            for r in ('R1', 'R2'):
                with gzip.open(str(cls.seq / ('%s_L001_%s_001.fastq.gz' % (s, r))), 'wt') as fh:
                    fh.write('@r\nACGT\n+\nIIII\n')
        (cls.ws / 'data_sources.tsv').write_text(
            'source\tdata_class\tdeclared_by\n%s\tpublic\tlane fixture\n' % cls.seq)

    @classmethod
    def tearDownClass(cls):
        for root, _, files in os.walk(str(cls.tmp)):
            for f in files:
                try:
                    os.chmod(os.path.join(root, f), stat.S_IRUSR | stat.S_IWUSR)
                except OSError:
                    pass
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def project(self, name):
        done = subprocess.run([sys.executable, str(self.ws / '_system/stage00_register.py'),
                               'create', '--title', name, '--assays', 'rnaseq_bulk'],
                              cwd=str(self.ws), stdout=subprocess.PIPE, timeout=120)
        self.assertEqual(done.returncode, 0)
        raw = self.ws / 'projects' / name / '00_data/rnaseq_bulk/raw'
        for f in sorted(self.seq.iterdir()):
            (raw / f.name).symlink_to(f)
        return self.ws / 'projects' / name

    def person(self, name, *flags):
        done = subprocess.run([sys.executable, str(self.ws / '_system/stage00_register.py'),
                               'finalize', '--project', 'projects/' + name] + list(flags),
                              cwd=str(self.ws), stdout=subprocess.PIPE,
                              universal_newlines=True, timeout=120)
        return done.returncode, json.loads(done.stdout)

    def agent(self, name, *flags):
        command = ' '.join(['python3', '_system/stage00_register.py', 'finalize', '--project',
                            'projects/' + name] + list(flags))
        done = subprocess.run(
            [sys.executable, str(GARS / '_system/guard_hook.py')],
            input=json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command},
                              'cwd': str(self.ws)}),
            env=dict(os.environ, CLAUDE_PROJECT_DIR=str(self.ws), PYTHONDONTWRITEBYTECODE='1'),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=120)
        return done.returncode, done.stderr

    def test_a_persons_new_registration_writes_no_legacy_purpose(self):
        for purpose in PURPOSES:
            with self.subTest(purpose=purpose):
                name = 'person-' + purpose.replace('_', '-')
                project = self.project(name)
                code, result = self.person(name, '--data-class', 'public', '--purpose', purpose)
                if purpose in venue_policy.REGISTRABLE_PURPOSES:
                    self.assertEqual(code, 0, result)
                else:
                    self.assertEqual(code, 2, result)
                    self.assertFalse((project / '00_data/dataset.tsv').exists())

    def test_the_agents_registration_is_public_fixture_or_internal_only(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S00-class-R1-registry.patch (R1) and
        lanes/gars-t74/S00-class-G2-guard.patch (G2); red at the lane's head only in the
        legacy-purpose rows of class public, which the guard allows today."""
        name = 'agent'
        self.project(name)
        for data_class in CLASSES:
            for purpose in PURPOSES:
                with self.subTest(data_class=data_class, purpose=purpose):
                    code, err = self.agent(name, '--data-class', data_class, '--purpose', purpose)
                    if data_class == 'public' and purpose in ('fixture', 'internal'):
                        self.assertEqual(code, 0, err)
                    else:
                        self.assertEqual(code, 2, err)
                        self.assertIn('Blocked:', err)

    def test_an_agents_re_run_of_a_legacy_row_is_refused_and_the_row_kept(self):
        """Fails until glitch-b5 applies lanes/gars-t74/S00-class-R1-registry.patch (R1).

        The row is the person's: their finalize re-runs it (not registry-bound); the agent's is
        refused, and the row is byte for byte after it (run 11 ruling 6)."""
        name = 'legacy'
        project = self.project(name)
        sys.path.insert(0, str(self.ws / '_system'))
        try:
            spec = importlib.util.spec_from_file_location(
                's0_copy', str(self.ws / '_system/stage00_register.py'))
            s0 = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(s0)
            base = {'data_class': 'public', 'purpose': 'pilot_internal', 'agreement_ref': 'none',
                    'input_data_location': json.dumps(sorted(
                        str(p.resolve()) for p in (project / '00_data').glob('*/raw/*')),
                        separators=(',', ':'))}
            s0.write_dataset_record(project, s0.dataset_values(project, base))
        finally:
            sys.path.remove(str(self.ws / '_system'))
        row = project / '00_data/dataset.tsv'
        before = row.read_bytes()
        code, err = self.agent(name, '--data-class', 'public', '--purpose', 'pilot_internal',
                               '--agreement-ref', 'none')
        self.assertEqual(code, 2, err)
        self.assertEqual(row.read_bytes(), before)
        code, result = self.person(name, '--data-class', 'public', '--purpose', 'pilot_internal',
                                   '--agreement-ref', 'none')
        self.assertEqual(code, 0, result)
        self.assertEqual(row.read_bytes(), before)


class BasePinTests(unittest.TestCase):
    """The base is pinned by content, never by a commit id: the landing gives every commit a new id."""

    def test_each_pin_is_a_blob(self):
        pins = globals().get('BASE_BLOBS')
        self.assertIsInstance(pins, dict, 'BASE_BLOBS names no blob')
        self.assertEqual(set(pins), {'gars/_system/venue_policy.py', 'gars/_references/data_policy.tsv'})
        for rel, blob in pins.items():
            with self.subTest(path=rel):
                kind = subprocess.run(['git', 'cat-file', '-t', blob], cwd=str(REPO),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(kind.stdout.decode().strip(), 'blob', blob)

    def test_the_module_names_no_commit_id(self):
        text = Path(__file__).read_text()
        for token in sorted(set(re.findall(r'\b[0-9a-f]{7,40}\b', text))):
            kind = subprocess.run(['git', 'cat-file', '-t', token], cwd=str(REPO),
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            with self.subTest(token=token):
                self.assertNotEqual(kind.stdout.decode().strip(), 'commit', token)


if __name__ == '__main__':
    unittest.main()
