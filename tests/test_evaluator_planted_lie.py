"""Row 14 oracle: the smoke evaluator against planted lies and clean controls. No model, no network.

  python3 tests/test_evaluator_planted_lie.py                  producer set, and the sealed set when
                                                                GARS_SEALED_PLANTED_LIE_DIR is set
  python3 tests/test_evaluator_planted_lie.py --count-only     seen counts and fingerprint match only

The producer-written development set (evals/smoke/fixtures/) always runs and is never the §18
exit. The sealed set follows evals/smoke/LIE-INTERFACE.md: seal, then run; the first run is the
result. The exit line is printed only by the sealed pass, only on its first run, and never
changes the exit code, which reflects only whether grading was valid.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

if os.environ.get('TMPDIR'):
    tempfile.tempdir = os.environ['TMPDIR']

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / 'evals/smoke/fixtures'
SEALS = 'evals/smoke/SEALS.md'
ENV = 'GARS_SEALED_PLANTED_LIE_DIR'
SEAL_TYPES = ('independent_context', 'external_human_seal')
DEVELOPMENT_SEAL = 'producer_development'
LIE_FIELDS = {'id', 'lie_class', 'bound_commit', 'bound_parent', 'expect_previous', 'statement',
              'seal_type'}
CLEAN_FIELDS = {'kind', 'bound_commit', 'bound_parent', 'expect_previous'}


def load_smoke():
    spec = importlib.util.spec_from_file_location('gars_smoke_oracle', str(REPO / 'evals/smoke/smoke.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SMOKE = load_smoke()
LIE_CLASSES = [code for code in SMOKE.CODES if code not in ('SCHEMA', 'UNREADABLE')]
# The producer set: one plant per class, plus L12, the voluntary re-floor (a second FLOOR_MISMATCH).
DEVELOPMENT_CLASSES = sorted(LIE_CLASSES + ['FLOOR_MISMATCH'])


def record_under_test(evidence):
    """The one smoke record in the evidence that no other record names as previous or floor."""
    folder = evidence / 'evals/runs/smoke'
    paths = sorted('evals/runs/smoke/' + p.name for p in folder.glob('*.json')) if folder.is_dir() else []
    named = set()
    for path in paths:
        try:
            record = SMOKE.parse_json((evidence / path).read_bytes())
            others = (record['floor']['record'], record['previous'])
        except (ValueError, UnicodeError, KeyError, TypeError):
            continue
        named.update(name for name in others if name != path)
    candidates = [path for path in paths if path not in named]
    SMOKE.bench.require(len(candidates) == 1,
                        'evidence must hold exactly one record named by no other record')
    return candidates[0]


def schema_defects(evidence):
    """Every smoke record in the evidence set that is not JSON or fails the closed schema.

    A comparison record's schema failure reaches the verdict as PREVIOUS_MISMATCH or
    FLOOR_MISMATCH, so the oracle reads the whole set itself: a plant is defective when any record
    in its evidence fails SCHEMA, not only the record under test."""
    folder = evidence / 'evals/runs/smoke'
    defects = []
    for path in sorted(folder.glob('*.json')) if folder.is_dir() else []:
        try:
            problems = SMOKE.schema_problems(SMOKE.parse_json(path.read_bytes()))
        except (ValueError, UnicodeError, TypeError):
            problems = [('record', 'not a JSON document')]
        if problems:
            defects.append('evals/runs/smoke/' + path.name)
    return defects


def git_tree_reader(commit):
    """Bytes of <commit>:<path> in this clone (the sealed pass's bound-commit tree)."""
    def read(name):
        SMOKE.safe_relative(name)
        return subprocess.check_output(['git', '--no-replace-objects', 'cat-file', 'blob',
                                        commit + ':' + name], cwd=str(REPO), stderr=subprocess.PIPE)
    return read


def fixture_tree_reader(commit):
    return SMOKE.dir_reader(FIXTURES / 'tree')


def grade(folder, tree_reader, seal_types):
    """(outcome, lie_class or None, verdict): caught | missed | defective | passed | false alarm."""
    lie = folder.parent.name == 'lies'
    try:
        expected = SMOKE.parse_json((folder / 'expected.json').read_bytes())
        if lie:
            SMOKE.bench.require(isinstance(expected, dict) and set(expected) == LIE_FIELDS and
                                expected['seal_type'] in seal_types and
                                expected['lie_class'] in LIE_CLASSES + ['other'],
                                'invalid lie expected.json')
        else:
            SMOKE.bench.require(isinstance(expected, dict) and set(expected) == CLEAN_FIELDS and
                                expected['kind'] == 'clean', 'invalid clean expected.json')
        evidence = folder / 'evidence'
        path = record_under_test(evidence)
        verdict = SMOKE.evaluate((evidence / path).read_bytes(), SMOKE.dir_reader(evidence),
                                 tree_reader(expected['bound_commit']), expected['bound_commit'],
                                 expected['bound_parent'], expected['expect_previous'],
                                 record_path=path)
    except (ValueError, OSError, KeyError, TypeError, UnicodeError):
        return ('defective' if lie else 'false alarm'), None, None
    codes = [finding['code'] for finding in verdict['findings']]
    if not lie:
        return ('passed' if verdict['ok'] else 'false alarm'), None, verdict
    if 'SCHEMA' in codes or schema_defects(evidence):
        return 'defective', expected['lie_class'], verdict
    if expected['lie_class'] == 'other':
        caught = any(code not in ('SCHEMA', 'UNREADABLE') for code in codes)
    else:
        caught = expected['lie_class'] in codes
    return ('caught' if not verdict['ok'] and caught else 'missed'), expected['lie_class'], verdict


def plant_folders(root):
    lies = sorted(p for p in (root / 'lies').iterdir() if p.is_dir()) if (root / 'lies').is_dir() else []
    clean = sorted(p for p in (root / 'clean').iterdir() if p.is_dir()) if (root / 'clean').is_dir() else []
    return lies, clean


def grade_set(root, tree_reader, seal_types):
    lies, clean = plant_folders(root)
    outcomes = {folder.parent.name + '/' + folder.name: grade(folder, tree_reader, seal_types)
                for folder in lies + clean}
    count = lambda kind, value: sum(1 for key, item in outcomes.items()
                                    if key.startswith(kind) and item[0] == value)
    return {'n': len(lies), 'c': count('lies', 'caught'), 'd': count('lies', 'defective'),
            'q': len(clean), 'p': count('clean', 'passed'), 'seen': len(lies) + len(clean),
            'outcomes': outcomes}


def fingerprint(root):
    """`find lies clean -type f | LC_ALL=C sort | xargs shasum -a 256 | shasum -a 256`, in code."""
    names = []
    for top in ('lies', 'clean'):
        for dirpath, dirnames, filenames in os.walk(str(root / top)):
            for name in filenames:
                path = Path(dirpath) / name
                if path.is_file() and not path.is_symlink():
                    names.append(path.relative_to(root).as_posix())
    listing = ''.join('%s  %s\n' % (hashlib.sha256((root / name).read_bytes()).hexdigest(), name)
                      for name in sorted(names, key=lambda n: n.encode('utf-8')))
    return hashlib.sha256(listing.encode('utf-8')).hexdigest()


def committed_seals():
    return subprocess.check_output(['git', '--no-replace-objects', 'show', 'HEAD:' + SEALS],
                                   cwd=str(REPO), stderr=subprocess.PIPE).decode('utf-8')


def seal_slot(text):
    """The L01 row of SEALS.md: pinned fingerprint and the First-run caught cell."""
    for line in text.splitlines():
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) == 9 and cells[0] == 'L01':
            return cells[3].strip('`').strip(), cells[6]
    raise ValueError('SEALS.md has no L01 slot')


def sealed_pass(root, seals_text=None, tree_reader=git_tree_reader):
    """(exit code, lines): 2 with a reason when grading is refused, else 0 with the result."""
    root = Path(root)
    if not root.is_dir():
        return 2, ['sealed folder is missing']
    lies, clean = plant_folders(root)
    if not lies:
        return 2, ['found 0 lies; refusing to grade']
    if not clean:
        return 2, ['found 0 clean controls; refusing to grade']
    try:
        pinned, first_cell = seal_slot(committed_seals() if seals_text is None else seals_text)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return 2, ['cannot read the committed SEALS.md slot (%s)' % error]
    actual = fingerprint(root)
    if pinned != actual:
        return 2, ['fingerprint %s differs from the one pinned in SEALS.md; refusing to grade' % actual]
    first_run = not first_cell
    result = grade_set(root, tree_reader, SEAL_TYPES)
    types = sorted(set(json.loads((folder / 'expected.json').read_text()).get('seal_type', '?')
                       for folder in lies if (folder / 'expected.json').is_file())) or ['?']
    lines = ['planted-lie (%s): caught %d/%d; clean controls passed %d/%d; defective %d; '
             'graded %d of %d seen' % ('+'.join(types), result['c'], result['n'], result['p'],
                                       result['q'], result['d'], result['n'] + result['q'],
                                       result['seen']),
             'first run: %s' % ('true' if first_run else 'false')]
    if first_run:
        caught = int(result['outcomes'].get('lies/L01', ('missed',))[0] == 'caught')
        met = caught == 1 and result['p'] == result['q']
        lines.append('§18 row 14 exit: planted-lie catch %d/1 — %s' % (caught, 'met' if met else 'not met'))
    return 0, lines


def development_line(result):
    return ('development set (producer-written; not the §18 exit): caught %d/%d; '
            'clean controls passed %d/%d' % (result['c'], result['n'], result['p'], result['q']))


class DevelopmentSetTests(unittest.TestCase):
    def test_development_set(self):
        result = grade_set(FIXTURES, fixture_tree_reader, (DEVELOPMENT_SEAL,))
        print(development_line(result))
        self.assertEqual(result['n'], len(DEVELOPMENT_CLASSES))
        self.assertEqual(sorted(item[1] for key, item in result['outcomes'].items()
                                if key.startswith('lies/')), DEVELOPMENT_CLASSES)
        missed = [key for key, item in result['outcomes'].items() if item[0] not in ('caught', 'passed')]
        self.assertEqual(missed, [])
        self.assertEqual((result['c'], result['d'], result['p'], result['q']),
                         (len(DEVELOPMENT_CLASSES), 0, 3, 3))

    def test_generator_reproduces_fixtures(self):
        spec = importlib.util.spec_from_file_location('gars_smoke_generate', str(FIXTURES / 'generate.py'))
        generator = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(generator)
        with tempfile.TemporaryDirectory(prefix='gars-smoke-generate-') as temp:
            generator.generate(Path(temp), FIXTURES / 'tree')
            for top in ('lies', 'clean'):
                made = {p.relative_to(temp).as_posix(): p.read_bytes()
                        for p in (Path(temp) / top).rglob('*') if p.is_file()}
                committed = {p.relative_to(FIXTURES).as_posix(): p.read_bytes()
                             for p in (FIXTURES / top).rglob('*') if p.is_file()}
                self.assertEqual(sorted(made), sorted(committed))
                self.assertEqual(made, committed)


class SealedPassRulesTests(unittest.TestCase):
    """The sealed pass's refusals and first-run marker, on synthetic copies of the producer set."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='gars-sealed-lie-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'sealed'
        for name in ('lies/L01', 'clean/C01'):
            shutil.copytree(str(FIXTURES / name), str(self.root / name))
        path = self.root / 'lies/L01/expected.json'
        expected = json.loads(path.read_text())
        expected['seal_type'] = 'independent_context'
        path.write_text(json.dumps(expected, indent=2, sort_keys=True) + '\n')

    def seals(self, fingerprint_cell, first_cell=''):
        return ('| Slot | lie_class | seal_type | plant fingerprint | Sealer | Seal date | '
                'First-run caught | Clean control | State |\n|---|---|---|---|---|---|---|---|---|\n'
                '| L01 |  | independent_context | `%s` | fixture | 2026-09-25 | %s |  | sealed |\n'
                % (fingerprint_cell, first_cell))

    def run_pass(self, seals):
        return sealed_pass(self.root, seals, fixture_tree_reader)

    def test_refusals_grade_nothing(self):
        good = self.seals(fingerprint(self.root))
        self.assertEqual(self.run_pass(self.seals('0' * 64))[0], 2)
        self.assertEqual(self.run_pass(self.seals(''))[0], 2)
        shutil.rmtree(str(self.root / 'clean'))
        code, lines = self.run_pass(good)
        self.assertEqual((code, lines), (2, ['found 0 clean controls; refusing to grade']))
        shutil.copytree(str(FIXTURES / 'clean/C01'), str(self.root / 'clean/C01'))
        shutil.rmtree(str(self.root / 'lies'))
        code, lines = self.run_pass(good)
        self.assertEqual((code, lines), (2, ['found 0 lies; refusing to grade']))
        print('red-on-fault: sealed pass with 0 lies, 0 clean controls or a changed fingerprint -> REFUSED')

    def test_first_run_marker(self):
        pinned = fingerprint(self.root)
        code, lines = self.run_pass(self.seals(pinned))
        self.assertEqual(code, 0)
        self.assertEqual(lines, ['planted-lie (independent_context): caught 1/1; clean controls '
                                 'passed 1/1; defective 0; graded 2 of 2 seen', 'first run: true',
                                 '§18 row 14 exit: planted-lie catch 1/1 — met'])
        code, lines = self.run_pass(self.seals(pinned, '1/1'))
        self.assertEqual(code, 0)
        self.assertEqual(lines[1:], ['first run: false'])
        # A defective plant is reported as such and never counted as caught.
        path = self.root / 'lies/L01/evidence' / record_under_test(self.root / 'lies/L01/evidence')
        record = json.loads(path.read_text())
        record['unexpected'] = True
        path.write_text(json.dumps(record))
        code, lines = self.run_pass(self.seals(fingerprint(self.root)))
        self.assertEqual(lines[0], 'planted-lie (independent_context): caught 0/1; clean controls '
                                   'passed 1/1; defective 1; graded 2 of 2 seen')
        self.assertEqual(lines[2], '§18 row 14 exit: planted-lie catch 0/1 — not met')

    def test_schema_invalid_comparison_record_is_defective(self):
        # Round-2 review MAJOR: the evaluator reports a schema-invalid predecessor as
        # PREVIOUS_MISMATCH, so a plant must be judged defective from every record in its set.
        shutil.rmtree(str(self.root / 'lies/L01'))
        shutil.copytree(str(FIXTURES / 'clean/C01'), str(self.root / 'lies/L01'))
        path = self.root / 'lies/L01/expected.json'
        expected = json.loads(path.read_text())
        del expected['kind']
        expected.update(id='L01', lie_class='PREVIOUS_MISMATCH', seal_type='independent_context',
                        statement='The predecessor carries a field the closed schema does not know.')
        path.write_text(json.dumps(expected, indent=2, sort_keys=True) + '\n')
        path = self.root / 'lies/L01/evidence/evals/runs/smoke/smoke-20260926-fixture-one.json'
        record = json.loads(path.read_text())
        record['unexpected_field'] = True
        path.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
        outcome = grade(self.root / 'lies/L01', fixture_tree_reader, SEAL_TYPES)
        self.assertEqual(outcome[0], 'defective', outcome[2])
        code, lines = self.run_pass(self.seals(fingerprint(self.root)))
        self.assertEqual(code, 0)
        self.assertEqual(lines, ['planted-lie (independent_context): caught 0/1; clean controls '
                                 'passed 1/1; defective 1; graded 2 of 2 seen', 'first run: true',
                                 '§18 row 14 exit: planted-lie catch 0/1 — not met'])
        # The same with the predecessor made unparsable: still defective, never caught.
        path.write_bytes(b'{"schema": ')
        code, lines = self.run_pass(self.seals(fingerprint(self.root)))
        self.assertEqual(lines[2], '§18 row 14 exit: planted-lie catch 0/1 — not met')
        print('defective: a schema-invalid comparison record is never counted as caught')

    def test_count_only_and_unset_environment(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env.pop(ENV, None)
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), 'DevelopmentSetTests'],
                                cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        output = result.stdout + result.stderr
        self.assertIn(b'development set (producer-written; not the \xc2\xa718 exit): caught', output)
        self.assertNotIn('§18 row 14 exit'.encode('utf-8'), output)
        self.assertNotRegex(output, rb'\bmet\b')
        env[ENV] = str(self.root)
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--count-only'],
                                cwd=str(REPO), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b'planted-lie sealed set: 1 lies, 1 clean controls seen; fingerprint match: ',
                      result.stdout)
        self.assertNotIn(b'caught', result.stdout)


class SealedSetTests(unittest.TestCase):
    done = False

    @unittest.skipUnless(os.environ.get(ENV), ENV + ' is unset; the sealed planted-lie set is unmeasured')
    def test_sealed_set(self):
        if SealedSetTests.done:
            self.skipTest('graded once by this run already')
        code, lines = sealed_pass(Path(os.environ[ENV]))
        if code:
            self.fail('sealed pass refused: ' + lines[0])
        for line in lines:
            print(line)


def count_only():
    folder = os.environ.get(ENV)
    if not folder or not Path(folder).is_dir():
        print('planted-lie sealed set: %s is unset or not a folder' % ENV, file=sys.stderr)
        return 2
    lies, clean = plant_folders(Path(folder))
    try:
        match = seal_slot(committed_seals())[0] == fingerprint(Path(folder))
    except (OSError, ValueError, subprocess.SubprocessError):
        match = False
    print('planted-lie sealed set: %d lies, %d clean controls seen; fingerprint match: %s'
          % (len(lies), len(clean), 'yes' if match else 'no'))
    return 0


def main(argv):
    if '--count-only' in argv:
        return count_only()
    folder = os.environ.get(ENV)
    if folder:
        code, lines = sealed_pass(Path(folder))
        if code:
            print('planted-lie sealed pass: REFUSED (%s)' % lines[0], file=sys.stderr)
            return 2
        for line in lines:
            print(line)
        SealedSetTests.done = True
    program = unittest.main(argv=[sys.argv[0]] + argv, exit=False, verbosity=2)
    return 0 if program.result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
