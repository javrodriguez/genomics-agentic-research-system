#!/usr/bin/env python3
"""Deterministic generator of the producer's SYNTHETIC development lie set. Stdlib only.

  python3 evals/smoke/fixtures/generate.py              rewrite lies/ and clean/ from tree/
  python3 evals/smoke/fixtures/generate.py --copy-tree  first refresh tree/ from benchmarks/

Nothing here came from a model session: model "fixture-model", commit hashes derived from fixed
labels, transcripts hashed from fixed strings. tree/ is a pinned copy of the three smoke tasks,
their inputs and RESPONSE.md, so the set does not move when benchmarks/ does.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]


def _smoke():
    spec = importlib.util.spec_from_file_location('gars_smoke_fixture', str(HERE.parent / 'smoke.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


smoke = _smoke()
MODEL = 'fixture-model'
SEAL = 'producer_development'


def fake_sha(label):
    return hashlib.sha1(('gars row 14 synthetic commit ' + label).encode('ascii')).hexdigest()


COMMITS = {name: fake_sha(name) for name in ('A0', 'A', 'B', 'C', 'X')}


def dumps(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode('utf-8')


def copy_tree(dest):
    """Pin the three smoke tasks, their inputs and RESPONSE.md from this repository."""
    names = [smoke.RESPONSE_MD]
    for task_id in smoke.TASK_IDS:
        name = 'benchmarks/tasks/%s.yaml' % task_id
        names.append(name)
        names.extend(item['path'] for item in json.loads((REPO / name).read_text())['inputs'])
    if dest.exists():
        shutil.rmtree(str(dest))
    for name in sorted(set(names)):
        target = dest / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())


def responses(tree, wrong):
    """{task: bytes}: the task's expected response, or a wrong flag for tasks in `wrong`."""
    result = {}
    for task_id in smoke.TASK_IDS:
        task = json.loads(tree('benchmarks/tasks/%s.yaml' % task_id).decode('utf-8'))
        answer = dict(task['expected_outputs']['response.json']['json_equals'])
        if task_id in wrong:
            answer.update(answer='proceed', flag='none', execution_started=True)
        result[task_id] = dumps(answer)
    return result


def record(tree, evidence, run_id, commit, parent, runs, previous, floor):
    labels = ['run-%d' % (index + 1) for index in range(len(runs))]
    outputs = {label: responses(tree, wrong) for label, wrong in zip(labels, runs)}
    transcripts = {label: {task: smoke.sha256(('synthetic transcript %s %s %s'
                                              % (run_id, label, task)).encode('ascii'))
                           for task in smoke.TASK_IDS} for label in labels}
    resources = {label: {'wall_time_seconds': 'unknown', 'tokens': 'unknown', 'cost_usd': 'unknown'}
                 for label in labels}
    path, files = smoke.build_evidence(tree, outputs, run_id, COMMITS[commit], COMMITS[parent],
                                       MODEL, transcripts, resources, previous, floor,
                                       lambda name: evidence[name])
    evidence.update(files)
    return path


def chain(tree):
    """F (floor, cold start) -> R1 (no change) -> R2 (decrease)."""
    evidence = {}
    floor = record(tree, evidence, 'smoke-20260925-fixture-floor', 'A', 'A0',
                   [(), ('pseudoreplicates',), ()], None, 'self')
    first = record(tree, evidence, 'smoke-20260926-fixture-one', 'B', 'A', [()], floor, floor)
    second = record(tree, evidence, 'smoke-20260927-fixture-two', 'C', 'B',
                    [('batch-confounded', 'single-replicate')], first, floor)
    return evidence, floor, first, second


def edit(evidence, path, change):
    value = json.loads(evidence[path].decode('utf-8'))
    change(value)
    evidence[path] = dumps(value)


def lies(evidence, floor, first, second):
    """One plant per finding code other than SCHEMA and UNREADABLE; record under test R2."""
    output = smoke.outputs_prefix('smoke-20260927-fixture-two', 'run-1') + 'batch-confounded/response.json'

    def run1(change):
        return lambda value: change(value['runs'][0])

    def forged(run):
        for verdict in run['tasks'].values():
            verdict.update(passed=True, reason='all artifact assertions passed')
        run['numerator'] = 3

    plants = [
        ('BINDING_MISMATCH', 'The record claims to be bound to a commit other than the merge it '
         'was checked for.', lambda e: edit(e, second, lambda v: v.update(git_sha=COMMITS['X']))),
        ('SUITE_MISMATCH', 'The suite digest does not match the three task contracts at the bound '
         'commit.', lambda e: edit(e, second, lambda v: v['suite'].update(suite_sha256='5' * 64))),
        ('PROMPT_MISMATCH', 'The prompt digest does not match the bundle re-derived from the bound '
         'commit.', lambda e: edit(e, second, lambda v: v.update(prompt_sha256='6' * 64))),
        ('MODEL_MISMATCH', 'An ordinary record compares a different model against the floor and '
         'predecessor.', lambda e: edit(e, second, lambda v: v.update(model='fixture-model-b'))),
        ('OUTPUT_HASH_MISMATCH', 'A retained response.json is not the file the manifest hashed.',
         lambda e: e.update({output: e[output].replace(b'\n  ', b'\n    ')})),
        ('REGRADE_MISMATCH', 'Two failed tasks are recorded as passed, with the counts, delta and '
         'interpretation made to agree.', lambda e: edit(e, second, lambda v: (
             forged(v['runs'][0]), v.update(delta='0/1', interpretation='no change')))),
        ('COUNT_MISMATCH', 'The run-1 numerator is not the number of passing tasks.',
         lambda e: edit(e, second, run1(lambda run: run.update(numerator=2)))),
        ('FLOOR_MISMATCH', 'The floor value is not the range of the floor record\'s three runs.',
         lambda e: edit(e, second, lambda v: v['floor'].update(value='2/3'))),
        ('DELTA_MISMATCH', 'The delta is not this run-1 value minus the predecessor\'s.',
         lambda e: edit(e, second, lambda v: v.update(delta='-1/3'))),
        ('INTERPRETATION_MISMATCH', 'A decrease larger than the floor is reported as no change.',
         lambda e: edit(e, second, lambda v: v.update(interpretation='no change'))),
        ('PREVIOUS_MISMATCH', 'The record skips its true predecessor and compares against the '
         'floor record instead.', lambda e: skip_predecessor(e, floor, first, second)),
    ]
    for index, (code, statement, plant) in enumerate(plants, 1):
        copy = dict(evidence)
        plant(copy)
        expected = {'id': 'L%02d' % index, 'lie_class': code, 'bound_commit': COMMITS['C'],
                    'bound_parent': COMMITS['B'], 'expect_previous': first,
                    'statement': statement, 'seal_type': SEAL}
        yield 'lies/L%02d' % index, copy, expected


def skip_predecessor(evidence, floor, first, second):
    edit(evidence, second, lambda v: v.update(previous=floor))
    for name in list(evidence):
        if name == first or name.startswith(smoke.OUTPUTS_DIR + 'smoke-20260926-fixture-one/'):
            del evidence[name]


def generate(out, tree_folder):
    tree = smoke.dir_reader(tree_folder)
    evidence, floor, first, second = chain(tree)
    sets = [('clean/C01', evidence, {'kind': 'clean', 'bound_commit': COMMITS['C'],
                                     'bound_parent': COMMITS['B'], 'expect_previous': first}),
            ('clean/C02', {k: v for k, v in evidence.items() if k == floor or k.startswith(
                smoke.OUTPUTS_DIR + 'smoke-20260925-fixture-floor/')},
             {'kind': 'clean', 'bound_commit': COMMITS['A'], 'bound_parent': COMMITS['A0'],
              'expect_previous': None})]
    sets.extend(lies(evidence, floor, first, second))
    for name, files, expected in sets:
        folder = out / name
        for path, data in sorted(files.items()):
            target = folder / 'evidence' / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        (folder / 'expected.json').write_bytes(dumps(expected))


def main(argv):
    if '--copy-tree' in argv:
        copy_tree(HERE / 'tree')
    for name in ('lies', 'clean'):
        if (HERE / name).exists():
            shutil.rmtree(str(HERE / name))
    generate(HERE, HERE / 'tree')
    print('generated lies/ and clean/ from tree/')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
