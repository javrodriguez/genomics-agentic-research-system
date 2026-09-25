#!/usr/bin/env python3
"""Row 14 smoke delta: the deterministic evidence evaluator of a _system/ merge. Stdlib only.

The three tuned-on refuse-and-flag tasks are loaded one by one with bench.validate_task and
scored with bench.score_task; nothing here re-implements a scorer. evaluate() re-derives every
claim of a smoke record (schema "gars-smoke/1") from the retained outputs, the task contracts at
the bound commit's own tree and the named comparison records, and reports every finding it can
derive. The model is never in it. See evals/smoke/SMOKE.md.

  smoke.py bundle --tree <dir>
  smoke.py check --record <file> --evidence <dir> --tree <dir> --bound-commit <sha>
                 --bound-parent <sha> (--expect-previous <path> | --first)
  smoke.py score --tree <dir> --outputs <dir> --run-id <id> --git-sha <sha> --parent-sha <sha>
                 --model <m> --transcripts <json> --resource <json> --previous <path|none>
                 --floor <path|self> --out-root <repo root>
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def _load_bench():
    # The bench beside this file, under a private name: never a cached module from elsewhere.
    spec = importlib.util.spec_from_file_location('gars_smoke_bench', str(HERE.parent / 'bench.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bench = _load_bench()

SCHEMA = 'gars-smoke/1'
TASK_IDS = ('batch-confounded', 'pseudoreplicates', 'single-replicate')
RECORD_DIR = 'evals/runs/smoke/'
OUTPUTS_DIR = RECORD_DIR + 'outputs/'
RESPONSE_MD = 'benchmarks/RESPONSE.md'
NO_PREVIOUS = 'uncomputable: no previous smoke record'
INTERPRETATIONS = ('no change', 'increase', 'decrease', 'uncomputable')
COMPARED = ('model', 'prompt_sha256', 'suite_sha256')
CODES = ('SCHEMA', 'BINDING_MISMATCH', 'SUITE_MISMATCH', 'PROMPT_MISMATCH', 'MODEL_MISMATCH',
         'OUTPUT_HASH_MISMATCH', 'REGRADE_MISMATCH', 'COUNT_MISMATCH', 'FLOOR_MISMATCH',
         'DELTA_MISMATCH', 'INTERPRETATION_MISMATCH', 'PREVIOUS_MISMATCH', 'UNREADABLE')
FIELDS = ('schema', 'kind', 'path', 'run_id', 'git_sha', 'parent_sha', 'model', 'prompt_sha256',
          'suite', 'runs', 'floor', 'previous', 'delta', 'interpretation')
RUN_FIELDS = ('run_label', 'outputs', 'tasks', 'numerator', 'denominator', 'transcript_sha256',
              'resource')
RUN_ID = re.compile(r'^smoke-[0-9]{8}-[a-z0-9][a-z0-9-]{0,40}$')
SHA1 = re.compile(r'^[0-9a-f]{40}$')
RECORD_PATH = re.compile(r'^evals/runs/smoke/[A-Za-z0-9][A-Za-z0-9_.-]*\.json$')
FRACTION = re.compile(r'^(0|[1-9][0-9]*)/[1-9][0-9]*$')
SIGNED = re.compile(r'^-?(0|[1-9][0-9]*)/[1-9][0-9]*$')


def fraction_text(value):
    return '%d/%d' % (value.numerator, value.denominator)


def floor_range(values):
    """bench.noise_floor's arithmetic: the range of the floor record's three run values."""
    return max(values) - min(values)


def interpret(delta, floor):
    """bench.compare's rule: no change inside the floor, else the sign of the delta."""
    return 'no change' if abs(delta) <= floor else ('increase' if delta > 0 else 'decrease')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def as_bytes(data):
    return data.encode('utf-8') if isinstance(data, str) else bytes(data)


def parse_json(data):
    return json.loads(as_bytes(data).decode('utf-8'), object_pairs_hook=bench.pairs,
                      parse_constant=lambda value: bench.require(False, 'non-finite JSON number'))


def output_names():
    return sorted(task + '/response.json' for task in TASK_IDS)


def outputs_prefix(run_id, label):
    return OUTPUTS_DIR + run_id + '/' + label + '/'


def safe_relative(name):
    bench.require(isinstance(name, str) and name and not name.startswith('/') and '\\' not in name
                  and ':' not in name and all(part not in ('', '.', '..') for part in name.split('/'))
                  and all(ord(char) >= 32 for char in name), 'repository-relative path required')
    return name


def dir_reader(folder):
    """Read regular files under a folder; .listing(prefix) names every non-directory entry."""
    folder = Path(folder)

    def read(name):
        path = folder
        for part in safe_relative(name).split('/'):
            path = path / part
            bench.require(not path.is_symlink(), 'symlink refused: ' + name)
        bench.require(path.is_file(), 'absent: ' + name)
        return path.read_bytes()

    def listing(prefix):
        base = folder / safe_relative(prefix.rstrip('/'))
        if base.is_symlink() or not base.is_dir():
            return []
        found = []
        for dirpath, dirnames, filenames in os.walk(str(base)):
            here = Path(dirpath)
            for name in list(dirnames):
                if (here / name).is_symlink():
                    found.append((here / name).relative_to(base).as_posix())
                    dirnames.remove(name)
            for name in filenames:
                found.append((here / name).relative_to(base).as_posix())
        return sorted(found)

    read.listing = listing
    return read


# ---- the tree: three tasks, their inputs and RESPONSE.md at the bound commit ----------------

def load_tree(read_tree, scratch):
    """Materialise the three task inputs under scratch and validate each task one by one."""
    tasks = {}
    for task_id in TASK_IDS:
        task = parse_json(read_tree('benchmarks/tasks/%s.yaml' % task_id))
        bench.require(isinstance(task, dict) and isinstance(task.get('inputs'), list),
                      'task file is not a task: ' + task_id)
        for item in task['inputs']:
            bench.require(isinstance(item, dict) and isinstance(item.get('path'), str),
                          'task input is not a path: ' + task_id)
            target = bench.contained(scratch, safe_relative(item['path']))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(as_bytes(read_tree(item['path'])))
        tasks[task_id] = bench.validate_task(task, scratch, False)
    response = as_bytes(read_tree(RESPONSE_MD))
    return tasks, response


def prompt_value(tasks, response):
    return {'response_md_sha256': sha256(response),
            'tasks': {task_id: {'question': task['question'],
                                'inputs': [{'path': item['path'], 'sha256': item['sha256']}
                                           for item in task['inputs']]}
                      for task_id, task in sorted(tasks.items())}}


def bundle(read_tree):
    scratch = Path(tempfile.mkdtemp(prefix='gars-smoke-bundle-'))
    try:
        tasks, response = load_tree(read_tree, scratch)
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    return {'prompt_sha256': bench.digest(prompt_value(tasks, response)),
            'suite_sha256': bench.digest(tasks)}


# ---- schema ---------------------------------------------------------------------------------

def schema_problems(record):
    """Every schema problem of a record; an empty list means the closed schema holds."""
    problems = []

    def check(condition, field, detail):
        if not condition:
            problems.append((field, detail))
        return condition

    if not check(isinstance(record, dict), 'record', 'not a JSON object'):
        return problems
    for name in sorted(set(record) - set(FIELDS)):
        problems.append((name, 'unknown field'))
    for name in FIELDS:
        check(name in record, name, 'missing field')
    get = record.get
    check(get('schema') == SCHEMA, 'schema', 'must be ' + SCHEMA)
    check(get('kind') == 'smoke', 'kind', 'must be smoke')
    check(isinstance(get('path'), str) and bool(RECORD_PATH.match(get('path'))), 'path',
          'must be an evals/runs/smoke/<name>.json path')
    check(isinstance(get('run_id'), str) and bool(RUN_ID.match(get('run_id'))), 'run_id',
          'must match ' + RUN_ID.pattern)
    for name in ('git_sha', 'parent_sha'):
        check(isinstance(get(name), str) and bool(SHA1.match(get(name))), name, 'must be 40 hex')
    check(isinstance(get('model'), str) and bool(bench.TOKEN.match(get('model'))), 'model',
          'must be a bench model token')
    check(isinstance(get('prompt_sha256'), str) and bool(bench.HEX.match(get('prompt_sha256'))),
          'prompt_sha256', 'must be 64 hex')
    suite = get('suite')
    if check(isinstance(suite, dict) and set(suite) == {'task_ids', 'suite_sha256'}, 'suite',
             'must hold exactly task_ids and suite_sha256'):
        check(suite['task_ids'] == list(TASK_IDS), 'suite.task_ids',
              'must be the sorted three smoke tasks')
        check(isinstance(suite['suite_sha256'], str) and bool(bench.HEX.match(suite['suite_sha256'])),
              'suite.suite_sha256', 'must be 64 hex')
    runs = get('runs')
    if check(isinstance(runs, list) and len(runs) in (1, 3), 'runs', 'must list 1 or 3 runs'):
        for index, run in enumerate(runs):
            problems.extend(run_problems(run, index))
    floor = get('floor')
    if check(isinstance(floor, dict) and set(floor) == {'record', 'value'}, 'floor',
             'must hold exactly record and value'):
        check(isinstance(floor['record'], str) and bool(RECORD_PATH.match(floor['record'])),
              'floor.record', 'must be an evals/runs/smoke/<name>.json path')
        check(isinstance(floor['value'], str) and bool(FRACTION.match(floor['value'])),
              'floor.value', 'must be fraction text a/b')
    previous = get('previous')
    check(previous is None or (isinstance(previous, str) and bool(RECORD_PATH.match(previous))),
          'previous', 'must be null or an evals/runs/smoke/<name>.json path')
    delta = get('delta')
    check(isinstance(delta, str) and (bool(SIGNED.match(delta)) or (
        delta.startswith('uncomputable: ') and len(delta) > len('uncomputable: '))),
        'delta', 'must be signed fraction text or uncomputable: <reason>')
    check(get('interpretation') in INTERPRETATIONS, 'interpretation', 'invalid interpretation')
    return problems


def run_problems(run, index):
    problems = []
    field = 'runs[%d]' % index

    def check(condition, name, detail):
        if not condition:
            problems.append((field + name, detail))
        return condition

    if not check(isinstance(run, dict) and set(run) == set(RUN_FIELDS), '',
                 'must hold exactly ' + ', '.join(RUN_FIELDS)):
        return problems
    check(run['run_label'] == 'run-%d' % (index + 1), '.run_label', 'must be run-%d' % (index + 1))
    outputs = run['outputs']
    if check(isinstance(outputs, dict) and sorted(outputs) == output_names(), '.outputs',
             'must name exactly one response.json per task'):
        for name, value in sorted(outputs.items()):
            check(isinstance(value, str) and bool(bench.HEX.match(value)),
                  '.outputs[%s]' % name, 'must be 64 hex')
    tasks = run['tasks']
    if check(isinstance(tasks, dict) and sorted(tasks) == list(TASK_IDS), '.tasks',
             'must hold the three smoke tasks'):
        for task_id, verdict in sorted(tasks.items()):
            check(isinstance(verdict, dict) and set(verdict) == {'passed', 'reason'} and
                  type(verdict['passed']) is bool and isinstance(verdict['reason'], str),
                  '.tasks[%s]' % task_id, 'must be {passed, reason} as bench.score_task returns')
    for name in ('numerator', 'denominator'):
        check(type(run[name]) is int and run[name] >= 0, '.' + name, 'must be a nonnegative integer')
    transcripts = run['transcript_sha256']
    if check(isinstance(transcripts, dict) and sorted(transcripts) == list(TASK_IDS),
             '.transcript_sha256', 'must hold one hash per task'):
        for task_id, value in sorted(transcripts.items()):
            check(isinstance(value, str) and bool(bench.HEX.match(value)),
                  '.transcript_sha256[%s]' % task_id, 'must be 64 hex')
    try:
        bench.validate_metadata({'run_id': 'resource', 'git_sha': '0' * 40, 'model': 'resource',
                                 'prompt_sha256': '0' * 64, 'configuration': 'intact',
                                 'resource': run['resource']})
    except (ValueError, TypeError, AttributeError):
        problems.append((field + '.resource', "must follow bench's resource rule"))
    return problems


# ---- the evaluator --------------------------------------------------------------------------

class Evaluation(object):
    def __init__(self, read_evidence, read_tree):
        self.read_evidence = read_evidence
        self.read_tree = read_tree
        self.findings = []
        self.graded = {'records_read': 0, 'records_named': 0, 'tasks_regraded': 0,
                       'outputs_hashed': 0}
        self.scratch = Path(tempfile.mkdtemp(prefix='gars-smoke-regrade-'))
        self.tasks = None
        self.suite = None
        self.prompt = None
        self.counter = 0

    def add(self, code, field, detail):
        self.findings.append({'code': code, 'field': field, 'detail': detail})

    def evidence(self, name):
        try:
            return as_bytes(self.read_evidence(name)), None
        except Exception as error:  # a reader failure is a finding, never a pass
            return None, type(error).__name__

    def load_tree(self):
        try:
            self.tasks, response = load_tree(self.read_tree, self.scratch / 'inputs')
        except Exception as error:
            self.add('UNREADABLE', 'tree', 'task contracts at the bound commit cannot be loaded (%s)'
                     % type(error).__name__)
            return
        self.suite = bench.digest(self.tasks)
        self.prompt = bench.digest(prompt_value(self.tasks, response))

    def named_record(self, path, role, code):
        """A comparison record, parsed and schema-checked; None when unusable."""
        self.graded['records_named'] += 1
        data, error = self.evidence(path)
        if data is None:
            self.add('UNREADABLE', role, 'named record %s cannot be read (%s)' % (path, error))
            return None
        try:
            record = parse_json(data)
        except (ValueError, UnicodeError):
            self.add(code, role, 'named record %s is not JSON' % path)
            return None
        problems = schema_problems(record)
        if problems:
            self.add(code, role, 'named record %s is not a valid smoke record (%s)'
                     % (path, problems[0][0]))
            return None
        self.graded['records_read'] += 1
        if record['path'] != path:
            self.add(code, role, 'named record %s states path %s' % (path, record['path']))
        return record

    def verify_runs(self, record, codes, role):
        """Hash, regrade and count every run; return the verified value of each run."""
        prefix = role + ' ' if role else ''
        regrade = self.tasks is not None and (not role or record['suite']['suite_sha256'] == self.suite)
        listing = getattr(self.read_evidence, 'listing', None)
        root = OUTPUTS_DIR + record['run_id'] + '/'
        if listing is None:
            self.add('UNREADABLE', prefix + 'runs', 'evidence reader cannot list retained outputs')
        else:
            try:
                present = set(listing(root))
            except Exception as error:
                present = None
                self.add('UNREADABLE', prefix + 'runs', 'retained outputs cannot be listed (%s)'
                         % type(error).__name__)
            if present is not None:
                expected = set(run['run_label'] + '/' + name for run in record['runs']
                               for name in run['outputs'])
                for extra in sorted(present - expected):
                    self.add(codes['hash'], prefix + 'runs',
                             'extra file under %s: %s' % (root, extra))
        values = []
        for index, run in enumerate(record['runs']):
            field = '%sruns[%d]' % (prefix, index)
            self.counter += 1
            out = self.scratch / ('outputs-%d' % self.counter)
            for name, expected_hash in sorted(run['outputs'].items()):
                data, error = self.evidence(outputs_prefix(record['run_id'], run['run_label']) + name)
                if data is None:
                    self.add(codes['hash'], '%s.outputs[%s]' % (field, name),
                             'retained output missing (%s)' % error)
                    continue
                self.graded['outputs_hashed'] += 1
                if sha256(data) != expected_hash:
                    self.add(codes['hash'], '%s.outputs[%s]' % (field, name),
                             'retained bytes differ from the manifest')
                target = out / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            passes = None
            if regrade:
                passes = 0
                for task_id in TASK_IDS:
                    folder = out / task_id
                    folder.mkdir(parents=True, exist_ok=True)
                    verdict = bench.score_task(self.tasks[task_id], folder, self.scratch / 'inputs')
                    self.graded['tasks_regraded'] += 1
                    passes += int(verdict.get('passed') is True)
                    if verdict != run['tasks'][task_id]:
                        self.add(codes['regrade'], '%s.tasks[%s]' % (field, task_id),
                                 'recorded %s; bench.score_task gives %s'
                                 % (json.dumps(run['tasks'][task_id], sort_keys=True),
                                    json.dumps(verdict, sort_keys=True)))
            recorded = sum(int(verdict['passed']) for verdict in run['tasks'].values())
            if run['denominator'] != len(TASK_IDS):
                self.add(codes['count'], field + '.denominator',
                         'denominator %d is not %d' % (run['denominator'], len(TASK_IDS)))
            if run['numerator'] != recorded:
                self.add(codes['count'], field + '.numerator',
                         'numerator %d; recorded task verdicts pass %d' % (run['numerator'], recorded))
            if passes is not None and run['numerator'] != passes:
                self.add(codes['count'], field + '.numerator',
                         'numerator %d; the regrade passes %d' % (run['numerator'], passes))
            count = passes if passes is not None else run['numerator']
            values.append(Fraction(count, len(TASK_IDS)))
        return values

    def close(self):
        shutil.rmtree(str(self.scratch), ignore_errors=True)


OWN = {'hash': 'OUTPUT_HASH_MISMATCH', 'regrade': 'REGRADE_MISMATCH', 'count': 'COUNT_MISMATCH'}


def evaluate(record_bytes, read_evidence, read_tree, bound_commit, bound_parent, expect_previous,
             record_path=None):
    """Verdict {"ok", "findings", "graded"}; ok only with zero findings."""
    state = Evaluation(read_evidence, read_tree)
    try:
        _evaluate(state, record_bytes, bound_commit, bound_parent, expect_previous, record_path)
    finally:
        state.close()
    return {'ok': not state.findings, 'findings': state.findings, 'graded': state.graded}


def _evaluate(state, record_bytes, bound_commit, bound_parent, expect_previous, record_path):
    add = state.add
    state.graded['records_named'] += 1
    try:
        record = parse_json(record_bytes)
    except (ValueError, UnicodeError, TypeError):
        add('SCHEMA', 'record', 'not a JSON document')
        return
    problems = schema_problems(record)
    for field, detail in problems:
        add('SCHEMA', field, detail)
    if problems:
        return
    state.graded['records_read'] += 1

    # Binding: the record names its own commit, parent, path and run.
    if record['git_sha'] != bound_commit:
        add('BINDING_MISMATCH', 'git_sha', 'record is bound to %s, not %s'
            % (record['git_sha'], bound_commit))
    if record['parent_sha'] != bound_parent:
        add('BINDING_MISMATCH', 'parent_sha', 'record names parent %s, not %s'
            % (record['parent_sha'], bound_parent))
    if record['path'] != RECORD_DIR + record['run_id'] + '.json':
        add('BINDING_MISMATCH', 'run_id', 'path %s does not name run_id %s'
            % (record['path'], record['run_id']))
    if record_path is not None and record['path'] != record_path:
        add('BINDING_MISMATCH', 'path', 'record read from %s states path %s'
            % (record_path, record['path']))

    # The suite and prompt at the bound commit's own tree.
    state.load_tree()
    if state.suite is not None:
        if record['suite']['suite_sha256'] != state.suite:
            add('SUITE_MISMATCH', 'suite.suite_sha256', 'the tree at the bound commit digests to %s'
                % state.suite)
        if record['prompt_sha256'] != state.prompt:
            add('PROMPT_MISMATCH', 'prompt_sha256', 'the tree at the bound commit bundles to %s'
                % state.prompt)

    values = state.verify_runs(record, OWN, '')
    own = {'model': record['model'], 'prompt_sha256': record['prompt_sha256'],
           'suite_sha256': record['suite']['suite_sha256']}

    def identity(other):
        return {'model': other['model'], 'prompt_sha256': other['prompt_sha256'],
                'suite_sha256': other['suite']['suite_sha256']}

    code_of = {'model': 'MODEL_MISMATCH', 'prompt_sha256': 'PROMPT_MISMATCH',
               'suite_sha256': 'SUITE_MISMATCH'}
    is_floor = record['floor']['record'] == record['path']

    # The predecessor.
    if record['previous'] != expect_previous:
        add('PREVIOUS_MISMATCH', 'previous', 'record names %s; the chain requires %s'
            % (json.dumps(record['previous']), json.dumps(expect_previous)))
    previous = previous_values = None
    if record['previous'] is not None:
        if record['previous'] == record['path']:
            add('PREVIOUS_MISMATCH', 'previous', 'a record cannot be its own predecessor')
        else:
            previous = state.named_record(record['previous'], 'previous', 'PREVIOUS_MISMATCH')
            if previous is not None:
                previous_values = state.verify_runs(
                    previous, dict.fromkeys(('hash', 'regrade', 'count'), 'PREVIOUS_MISMATCH'),
                    'previous')

    # The floor.
    floor_value = None
    if is_floor:
        if len(record['runs']) != 3:
            add('FLOOR_MISMATCH', 'runs', 'a floor record carries three runs')
        else:
            floor_value = floor_range(values)
    else:
        if len(record['runs']) != 1:
            add('FLOOR_MISMATCH', 'runs', 'an ordinary record carries one run')
        if record['previous'] is None:
            add('FLOOR_MISMATCH', 'floor.record',
                'a record with no predecessor must be a floor record')
        if record['floor']['record'] == record['previous']:
            floor, floor_values = previous, previous_values
        else:
            floor = state.named_record(record['floor']['record'], 'floor', 'FLOOR_MISMATCH')
            floor_values = None
            if floor is not None:
                floor_values = state.verify_runs(
                    floor, dict.fromkeys(('hash', 'regrade', 'count'), 'FLOOR_MISMATCH'), 'floor')
        if floor is not None:
            if floor['floor']['record'] != floor['path'] or len(floor['runs']) != 3:
                add('FLOOR_MISMATCH', 'floor.record', 'named record %s is not a floor record'
                    % floor['path'])
            else:
                floor_value = floor_range(floor_values)
            for field in COMPARED:
                if identity(floor)[field] != own[field]:
                    add(code_of[field], 'floor.record', '%s differs from the floor record' % field)
        if previous is not None and previous['floor']['record'] != record['floor']['record']:
            add('FLOOR_MISMATCH', 'floor.record', "the predecessor's floor is %s"
                % previous['floor']['record'])
    if floor_value is not None and record['floor']['value'] != fraction_text(floor_value):
        add('FLOOR_MISMATCH', 'floor.value', 'the floor runs give %s' % fraction_text(floor_value))

    # Delta and interpretation (bench.compare's rule).
    expected_delta = expected_interpretation = None
    if record['previous'] is None:
        expected_delta, expected_interpretation = NO_PREVIOUS, 'uncomputable'
    elif previous is not None:
        changed = [field for field in COMPARED if identity(previous)[field] != own[field]]
        if changed:
            if not is_floor:
                for field in changed:
                    add(code_of[field], 'previous', '%s differs from the predecessor' % field)
            expected_delta = 'uncomputable: changed ' + ', '.join(changed)
            expected_interpretation = 'uncomputable'
        else:
            delta = values[0] - previous_values[0]
            expected_delta = fraction_text(delta)
            if floor_value is not None:
                expected_interpretation = interpret(delta, floor_value)
    if expected_delta is not None and record['delta'] != expected_delta:
        add('DELTA_MISMATCH', 'delta', 'the records give %s' % expected_delta)
    if expected_interpretation is not None and record['interpretation'] != expected_interpretation:
        add('INTERPRETATION_MISMATCH', 'interpretation', 'the records give %s'
            % expected_interpretation)


# ---- writing a record -----------------------------------------------------------------------

def build_evidence(read_tree, outputs, run_id, git_sha, parent_sha, model, transcripts, resources,
                   previous, floor, read_evidence=None):
    """The record and retained outputs as {repository path: bytes}; nothing is written.

    outputs: {run_label: {task_id: response.json bytes}}; floor: 'self' or a record path;
    previous: a record path or None; read_evidence reads the named comparison records."""
    labels = ['run-%d' % (index + 1) for index in range(len(outputs))]
    bench.require(sorted(outputs) == labels and len(labels) == (3 if floor == 'self' else 1),
                  'a floor record needs run-1..run-3; an ordinary record needs run-1')
    scratch = Path(tempfile.mkdtemp(prefix='gars-smoke-score-'))
    try:
        tasks, response = load_tree(read_tree, scratch / 'inputs')
        files = {}
        runs = []
        for label in labels:
            bench.require(sorted(outputs[label]) == list(TASK_IDS), label + ' needs the three tasks')
            verdicts = {}
            manifest = {}
            for task_id in TASK_IDS:
                data = as_bytes(outputs[label][task_id])
                folder = scratch / label / task_id
                folder.mkdir(parents=True)
                (folder / 'response.json').write_bytes(data)
                verdicts[task_id] = bench.score_task(tasks[task_id], folder, scratch / 'inputs')
                manifest[task_id + '/response.json'] = sha256(data)
                files[outputs_prefix(run_id, label) + task_id + '/response.json'] = data
            runs.append({'run_label': label, 'outputs': manifest, 'tasks': verdicts,
                         'numerator': sum(int(v['passed']) for v in verdicts.values()),
                         'denominator': len(TASK_IDS), 'transcript_sha256': transcripts[label],
                         'resource': resources[label]})
    finally:
        shutil.rmtree(str(scratch), ignore_errors=True)
    path = RECORD_DIR + run_id + '.json'
    record = {'schema': SCHEMA, 'kind': 'smoke', 'path': path, 'run_id': run_id,
              'git_sha': git_sha, 'parent_sha': parent_sha, 'model': model,
              'prompt_sha256': bench.digest(prompt_value(tasks, response)),
              'suite': {'task_ids': list(TASK_IDS), 'suite_sha256': bench.digest(tasks)},
              'runs': runs, 'previous': previous}
    value = lambda other, index: Fraction(other['runs'][index]['numerator'],
                                          other['runs'][index]['denominator'])
    if floor == 'self':
        floor_record = record
    else:
        floor_record = parse_json(read_evidence(floor))
    values = [value(floor_record, index) for index in range(len(floor_record['runs']))]
    floor_value = floor_range(values)
    record['floor'] = {'record': path if floor == 'self' else floor,
                       'value': fraction_text(floor_value)}
    if previous is None:
        record['delta'], record['interpretation'] = NO_PREVIOUS, 'uncomputable'
    else:
        before = parse_json(read_evidence(previous))
        changed = [field for field in COMPARED if (
            before['suite'][field] != record['suite'][field] if field == 'suite_sha256'
            else before[field] != record[field])]
        if changed:
            record['delta'] = 'uncomputable: changed ' + ', '.join(changed)
            record['interpretation'] = 'uncomputable'
        else:
            delta = value(record, 0) - value(before, 0)
            record['delta'] = fraction_text(delta)
            record['interpretation'] = interpret(delta, floor_value)
    files[path] = (json.dumps(record, indent=2, sort_keys=True) + '\n').encode('utf-8')
    return path, files


def score(args):
    tree = dir_reader(args.tree)
    out_root = Path(args.out_root)
    outputs_root = Path(args.outputs)
    labels = sorted(p.name for p in outputs_root.iterdir())
    outputs = {}
    for label in labels:
        present = sorted(p.relative_to(outputs_root / label).as_posix()
                         for p in (outputs_root / label).rglob('*') if not p.is_dir())
        bench.require(present == output_names(), label + ' must hold exactly one response.json per task')
        outputs[label] = {task: dir_reader(outputs_root / label)(task + '/response.json')
                          for task in TASK_IDS}
    previous = None if args.previous == 'none' else safe_relative(args.previous)
    evidence = dir_reader(out_root)
    path, files = build_evidence(tree, outputs, args.run_id, args.git_sha, args.parent_sha,
                                 args.model, bench.read_json(Path(args.transcripts)),
                                 bench.read_json(Path(args.resource)), previous, args.floor,
                                 evidence)
    for name in sorted(files):
        bench.require(not os.path.lexists(str(out_root / name)), 'refusing to overwrite ' + name)
    bench.require(not os.path.lexists(str(out_root / (OUTPUTS_DIR + args.run_id))),
                  'refusing to overwrite retained outputs for ' + args.run_id)
    for name, data in sorted(files.items()):
        target = out_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            handle.write(data)
    verdict = evaluate(files[path], evidence, tree, args.git_sha, args.parent_sha, previous,
                       record_path=path)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    if not verdict['ok']:
        print('score: REFUSED; the evaluator does not accept the record it wrote (nothing deleted)',
              file=sys.stderr)
        return 1
    print('score: wrote %s' % path, file=sys.stderr)
    return 0


def check(args):
    record_file = Path(args.record)
    for folder in (args.evidence, args.tree):
        bench.require(Path(folder).is_dir(), 'not a folder: ' + folder)
    for sha in (args.bound_commit, args.bound_parent):
        bench.require(bool(SHA1.match(sha)), 'bound commit and parent must be 40 hex')
    data = record_file.read_bytes()
    record_path = None
    try:
        record_path = record_file.resolve().relative_to(Path(args.evidence).resolve()).as_posix()
    except ValueError:
        pass
    verdict = evaluate(data, dir_reader(args.evidence), dir_reader(args.tree), args.bound_commit,
                       args.bound_parent, None if args.first else args.expect_previous,
                       record_path=record_path)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    graded = verdict['graded']
    print('smoke check: %s; %d findings; graded %d of %d records seen; %d tasks regraded; '
          '%d outputs hashed' % ('ok' if verdict['ok'] else 'REFUSED', len(verdict['findings']),
                                 graded['records_read'], graded['records_named'],
                                 graded['tasks_regraded'], graded['outputs_hashed']),
          file=sys.stderr)
    return 0 if verdict['ok'] else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest='command')
    command = commands.add_parser('bundle')
    command.add_argument('--tree', required=True)
    command = commands.add_parser('check')
    for name in ('--record', '--evidence', '--tree', '--bound-commit', '--bound-parent'):
        command.add_argument(name, required=True)
    group = command.add_mutually_exclusive_group(required=True)
    group.add_argument('--expect-previous')
    group.add_argument('--first', action='store_true')
    command = commands.add_parser('score')
    for name in ('--tree', '--outputs', '--run-id', '--git-sha', '--parent-sha', '--model',
                 '--transcripts', '--resource', '--previous', '--floor', '--out-root'):
        command.add_argument(name, required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    try:
        if args.command == 'bundle':
            bench.require(Path(args.tree).is_dir(), 'not a folder: ' + args.tree)
            result = bundle(dir_reader(args.tree))
            print('prompt_sha256: ' + result['prompt_sha256'])
            print('suite_sha256: ' + result['suite_sha256'])
            return 0
        if args.command == 'check':
            return check(args)
        if args.command == 'score':
            bench.require(bool(RUN_ID.match(args.run_id)), 'run_id must match ' + RUN_ID.pattern)
            return score(args)
        parser.print_usage(sys.stderr)
        return 2
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as error:
        print('refused: %s' % error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
