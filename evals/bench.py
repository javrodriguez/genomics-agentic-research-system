#!/usr/bin/env python3
"""Score existing Claude Code outputs only. Python 3.6.8+, stdlib only.

Task YAML uses the strict JSON subset; see benchmarks/HOLDOUT.md for the wire contract.
No code from tasks or agent outputs is executed. `pytest` denotes Python assertion
contracts, run using unittest so the scorer needs no third-party test runner.
"""
import argparse
import csv
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import unittest

REPO = Path(__file__).resolve().parent.parent
FIELDS = set(('question', 'inputs', 'expected_workflow', 'expected_outputs',
              'known_pitfalls', 'reference_answer', 'reference_source', 'scorer', 'holdout'))
SOURCES = ('public_dataset_with_published_result(DOI)', 'nfcore_test_data_expected_output',
           'synthetic_with_generator_seed', 'sealed_human_answer(author ≠ builder)')
SCORERS = ('exact', 'regex', 'pytest', 'human')
PARTITIONS = ('tuned_on', 'held_out')
HEX = re.compile(r'^[0-9a-f]{64}$')
TOKEN = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda value: require(False, 'non-finite JSON number'))


def relative_path(value):
    require(isinstance(value, str) and bool(value), 'path must be a nonempty string')
    p = Path(value)
    require(not p.is_absolute() and '..' not in p.parts and value != '.', 'path must be relative and contained')
    require('\\' not in value, 'backslash paths are not supported')
    return p


def contained(root, value):
    p = root / relative_path(value)
    require(root.resolve() in p.resolve().parents, 'path escapes root')
    return p


def validate_task(task, input_root, holdout):
    require(isinstance(task, dict) and set(task) == FIELDS, 'task fields must match schema exactly')
    require(type(task['holdout']) is bool and task['holdout'] == holdout,
            'holdout mismatch: held-out tasks are refused in benchmarks/tasks/')
    require(task['reference_source'] in SOURCES, 'invalid reference_source enum')
    require(task['scorer'] in SCORERS, 'invalid scorer; models are never scorers')
    require(task['scorer'] != 'human', 'human scorer unsupported: supply deterministic contract or leave task unmeasured outside this suite')
    for field in ('question', 'expected_workflow', 'known_pitfalls', 'reference_answer'):
        require(isinstance(task[field], str) and task[field].strip(), field + ' must be nonempty text')
    require(isinstance(task['inputs'], list) and task['inputs'], 'inputs must be nonempty')
    seen = set()
    for item in task['inputs']:
        require(isinstance(item, dict) and set(item) == {'path', 'sha256'}, 'input requires path + sha256')
        require(isinstance(item['sha256'], str) and HEX.fullmatch(item['sha256']), 'invalid input sha256')
        require(item['path'] not in seen, 'duplicate input path')
        seen.add(item['path'])
        path = contained(input_root, item['path'])
        require(path.is_file() and file_sha(path) == item['sha256'], 'input sha256 mismatch: ' + item['path'])
    outputs = task['expected_outputs']
    require(isinstance(outputs, dict) and outputs, 'expected_outputs must be a nonempty contract mapping')
    for path, contract in outputs.items():
        relative_path(path)
        require(isinstance(contract, dict) and len(contract) == 1, 'one assertion per output path required')
        kind, expected = next(iter(contract.items()))
        allowed = {'exact': {'json_equals', 'text_equals'}, 'regex': {'regex'},
                   'pytest': {'artifact_registry', 'text_equals', 'json_equals', 'nonempty'}}
        require(kind in allowed[task['scorer']], 'unsupported output assertion for scorer')
        if kind in ('text_equals', 'regex'):
            require(isinstance(expected, str) and expected, 'text assertion must be nonempty')
        if kind == 'regex':
            re.compile(expected)
        if kind == 'nonempty':
            require(expected is True, 'nonempty must be true')
        if kind == 'artifact_registry':
            require(isinstance(expected, dict) and set(expected) == {
                'types', 'samplesheet', 'sample_mode', 'expected_samplesheet', 'reference_counts'},
                'artifact_registry requires types, samplesheet, sample_mode, expected_samplesheet, reference_counts')
            relative_path(expected['samplesheet'])
            require(expected['sample_mode'] in ('rnaseq', 'atacseq'), 'invalid sample_mode')
            require(isinstance(expected['types'], dict) and expected['types'], 'artifact_registry must name types')
            for typ, rule in expected['types'].items():
                require(TOKEN.fullmatch(typ) and rule in ('file', 'directory', 'counts', 'bed'),
                        'invalid registry type or content rule')
            roster = expected['expected_samplesheet']
            require(roster is None or roster in seen, 'expected samplesheet must name a hashed task input')
            refs = expected['reference_counts']
            require(isinstance(refs, dict), 'reference_counts must map count types to hashed inputs')
            for typ, reference in refs.items():
                require(expected['types'].get(typ) == 'counts' and reference in seen,
                        'reference count must name a count type and hashed task input')
    return task


def load_tasks(folder, input_root, holdout):
    folder = Path(folder)
    require(folder.is_dir(), 'task directory is missing')
    if holdout:
        tuned = (REPO / 'benchmarks/tasks').resolve()
        require(folder.resolve() != tuned and tuned not in folder.resolve().parents,
                'holdout cannot be loaded from benchmarks/tasks/')
    paths = sorted(folder.glob('*.yaml'))
    require(paths, 'task directory is empty')
    tasks = {}
    for path in paths:
        require(TOKEN.fullmatch(path.stem), 'invalid task id')
        require(not path.is_symlink(), 'task symlinks are refused')
        tasks[path.stem] = validate_task(read_json(path), Path(input_root), holdout)
    return tasks


def sample_tokens(sheet, mode):
    with sheet.open(encoding='utf-8', newline='') as handle:
        samples = list(csv.DictReader(handle))
    require(samples, 'samplesheet must not be empty')
    tokens = set()
    for sample in samples:
        require(sample.get('sample'), 'missing sample id')
        token = sample['sample']
        if mode == 'atacseq':
            require(sample.get('replicate', '').isdigit(), 'missing replicate')
            token += '_REP' + sample['replicate']
        tokens.add(token)
    return tokens


def assert_registry(case, path, contract, output_root, input_root):
    rules = contract['types']
    require(contract['expected_samplesheet'] is not None, 'independent expected samplesheet unresolved')
    expected_samples = sample_tokens(contained(input_root, contract['expected_samplesheet']), contract['sample_mode'])
    actual_samples = sample_tokens(contained(output_root, contract['samplesheet']), contract['sample_mode'])
    case.assertEqual(actual_samples, expected_samples, 'export differs from independent sample roster')
    rows = [line for line in path.read_text(encoding='utf-8').splitlines()
            if line.strip() and not line.startswith('#')]
    registry = {}
    for row in csv.reader(rows, delimiter='\t'):
        case.assertEqual(len(row), 3, 'registry needs type, role, path')
        typ, role, target = row
        case.assertNotIn(typ, registry, 'duplicate artifact type')
        case.assertEqual(role, 'native')
        artifact = contained(path.parent, target)
        case.assertTrue(output_root.resolve() in artifact.resolve().parents)
        registry[typ] = artifact
    for typ, rule in rules.items():
        case.assertIn(typ, registry, 'missing artifact type: ' + typ)
        artifact = registry[typ]
        if rule == 'directory':
            case.assertTrue(artifact.is_dir(), 'artifact must be directory: ' + typ)
            children = list(artifact.rglob('*'))
            case.assertTrue(any(p.is_file() and p.stat().st_size for p in children), 'empty artifact directory')
            for child in children:
                case.assertTrue(output_root.resolve() in child.resolve().parents, 'artifact symlink escapes outputs')
            continue
        case.assertTrue(artifact.is_file() and artifact.stat().st_size > 0, 'missing or empty artifact: ' + typ)
        if rule == 'counts':
            lines = [line for line in artifact.read_text(encoding='utf-8').splitlines()
                     if line and not line.startswith('#')]
            table = list(csv.reader(lines, delimiter='\t'))
            case.assertGreaterEqual(len(table), 2, 'counts need header and data')
            header = table[0]
            # featureCounts metadata columns precede numerical sample columns.
            offset = 6 if header[:6] == ['Geneid', 'Chr', 'Start', 'End', 'Strand', 'Length'] else (2 if len(header) > 1 and header[1] == 'gene_name' else 1)
            case.assertGreater(len(header), offset, 'counts need samples')
            case.assertEqual(len(set(header)), len(header), 'duplicate sample columns')
            matched = []
            for col in header[offset:]:
                # featureCounts names BAM paths; compare the complete sample token,
                # not a substring that lets REP1 stand in for REP10.
                matches = [sample for sample in expected_samples if re.search(
                    r'(?<![A-Za-z0-9_])' + re.escape(sample) + r'(?![A-Za-z0-9_])', col)]
                case.assertEqual(len(matches), 1, 'unknown or ambiguous count sample')
                matched.extend(matches)
            case.assertEqual(len(matched), len(set(matched)), 'duplicate count sample')
            case.assertEqual(set(matched), expected_samples, 'lost sample')
            ids = set()
            for row in table[1:]:
                case.assertEqual(len(row), len(header))
                case.assertTrue(row[0] and row[0] not in ids, 'missing or duplicate feature id')
                ids.add(row[0])
                for value in row[offset:]:
                    number = float(value)
                    case.assertTrue(math.isfinite(number) and number >= 0, 'invalid count')
            if typ in contract['reference_counts']:
                case.assertEqual(file_sha(artifact), file_sha(contained(input_root, contract['reference_counts'][typ])),
                                 'counts differ from independent reference')
        if rule == 'bed':
            lines = artifact.read_text(encoding='utf-8').splitlines()
            data = [line for line in lines if line and not line.startswith(('#', 'track', 'browser'))]
            case.assertTrue(data, 'BED has no intervals')
            for line in data:
                row = line.split('\t')
                case.assertGreaterEqual(len(row), 3)
                case.assertTrue(row[0] and 0 <= int(row[1]) < int(row[2]), 'invalid BED interval')


def json_equal(actual, expected):
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(json_equal(actual[k], expected[k]) for k in expected)
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(json_equal(a, b) for a, b in zip(actual, expected))
    return actual == expected


def score_task(task, output_root, input_root=None):
    case = unittest.TestCase()
    try:
        input_root = Path(input_root) if input_root is not None else REPO
        validate_task(task, input_root, task['holdout'])
        for name, contract in task['expected_outputs'].items():
            path = contained(Path(output_root), name)
            case.assertTrue(path.is_file(), 'missing expected output: ' + name)
            kind, expected = next(iter(contract.items()))
            if kind == 'json_equals':
                case.assertTrue(json_equal(read_json(path), expected), 'JSON value or type differs')
            elif kind == 'text_equals':
                case.assertEqual(path.read_text(encoding='utf-8').strip(), expected)
            elif kind == 'regex':
                case.assertIsNotNone(re.fullmatch(expected, path.read_text(encoding='utf-8').strip()))
            elif kind == 'nonempty':
                case.assertGreater(path.stat().st_size, 0)
            elif kind == 'artifact_registry':
                assert_registry(case, path, expected, Path(output_root), input_root)
        return {'passed': True, 'reason': 'all artifact assertions passed'}
    except (AssertionError, ValueError, OSError, UnicodeError) as error:
        # Do not persist exception text: it may contain private paths or submitted data.
        return {'passed': False, 'reason': 'artifact contract failed: ' + type(error).__name__}


def ratio_text(numerator, denominator):
    if not denominator:
        return '%s/%s = uncomputable' % (numerator, denominator)
    return '%s/%s = %.6f' % (numerator, denominator, numerator / denominator)


def output_manifest(root):
    require(root.is_dir(), 'agent outputs directory is missing')
    result = {}
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink(), 'output symlinks refused; export self-contained artifacts')
        if path.is_file():
            result[path.relative_to(root).as_posix()] = file_sha(path)
    return result


def score_partition(tasks, root, input_root=None):
    results = {name: score_task(task, root / name, input_root) for name, task in sorted(tasks.items())}
    return {'state': 'measured', 'numerator': sum(int(r['passed']) for r in results.values()),
            'denominator': len(results), 'tasks': results,
            'suite_sha256': digest(tasks)}


def validate_metadata(metadata):
    require(set(metadata) == {'run_id', 'git_sha', 'model', 'prompt_sha256', 'configuration', 'resource'},
            'metadata fields must match run-record contract')
    for field in ('run_id', 'model'):
        require(isinstance(metadata[field], str) and TOKEN.fullmatch(metadata[field]), 'invalid ' + field)
    require(re.fullmatch('[0-9a-f]{40}', metadata['git_sha']), 'git_sha must be full commit hash')
    require(HEX.fullmatch(metadata['prompt_sha256']), 'prompt_sha256 must be SHA-256')
    require(metadata['configuration'] in ('intact', 'degraded'), 'invalid configuration')
    resource = metadata['resource']
    require(isinstance(resource, dict) and set(resource) == {'wall_time_seconds', 'tokens', 'cost_usd'},
            'resource requires wall_time_seconds, tokens, cost_usd')
    for key, value in resource.items():
        require(value == 'unknown' or (type(value) in (int, float) and math.isfinite(value) and value >= 0),
                'resource must be nonnegative or unknown')
        if key == 'tokens' and value != 'unknown':
            require(type(value) is int, 'tokens must be integer or unknown')


def make_record(outputs, metadata):
    validate_metadata(metadata)
    manifest = output_manifest(outputs)
    record = dict(metadata, schema_version=1, outputs=manifest,
                  run_sha256=digest({'run_id': metadata['run_id'], 'outputs': manifest}))
    tuned = load_tasks(REPO / 'benchmarks/tasks', REPO, False)
    scores = {'tuned_on': score_partition(tuned, outputs / 'tuned_on'),
              'held_out': {'state': 'unmeasured', 'reason': 'GARS_BENCH_HOLDOUT_DIR is unset'}}
    holdout = os.environ.get('GARS_BENCH_HOLDOUT_DIR')
    if holdout is not None:
        require(bool(holdout.strip()), 'GARS_BENCH_HOLDOUT_DIR is empty')
        root = Path(holdout)
        tasks = load_tasks(root / 'tasks', root, True)
        seal = read_json(root / 'seal.json')
        require(set(seal) == {'seal_type', 'suite_sha256', 'producer_access_denied'}, 'invalid seal fields')
        require(seal['seal_type'] in ('independent_context', 'external_human_seal') and
                seal['producer_access_denied'] is True and seal['suite_sha256'] == digest(tasks),
                'invalid seal or suite digest')
        scores['held_out'] = score_partition(tasks, outputs / 'held_out', root)
        scores['held_out']['seal'] = seal
    record['scores'] = scores
    return record


def write_record(record, destination):
    destination.mkdir(parents=True, exist_ok=True)
    # Never overwrite a repeat, including a rerun with changed metadata.
    for path in destination.glob('*.json'):
        require(read_json(path).get('run_id') != record['run_id'], 'duplicate run_id')
    name = '%s-%s-%s.json' % (record['run_sha256'], record['model'], record['prompt_sha256'])
    with (destination / name).open('x', encoding='utf-8') as handle:
        json.dump(record, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return name


def validate_record(record):
    require(record.get('schema_version') == 1, 'unsupported record schema')
    validate_metadata({k: record[k] for k in ('run_id', 'git_sha', 'model', 'prompt_sha256',
                                           'configuration', 'resource')})
    require(set(record['scores']) == set(PARTITIONS), 'record requires both score partitions')
    require(isinstance(record['outputs'], dict), 'output manifest must be a mapping')
    for path, sha in record['outputs'].items():
        relative_path(path)
        require(isinstance(sha, str) and HEX.fullmatch(sha), 'invalid output hash')
    require(record['configuration'] in ('intact', 'degraded'), 'invalid configuration')
    require(record['run_sha256'] == digest({'run_id': record['run_id'], 'outputs': record['outputs']}),
            'run sha mismatch')
    for part in PARTITIONS:
        score = record['scores'][part]
        if score['state'] == 'unmeasured':
            require(part == 'held_out' and 'numerator' not in score and 'denominator' not in score,
                    'unmeasured is not zero')
            continue
        require(score['state'] == 'measured', 'invalid score state')
        require(HEX.fullmatch(score['suite_sha256']), 'invalid suite digest')
        if part == 'held_out':
            seal = score.get('seal', {})
            require(set(seal) == {'seal_type', 'suite_sha256', 'producer_access_denied'} and
                    seal['seal_type'] in ('independent_context', 'external_human_seal') and
                    seal['producer_access_denied'] is True and
                    seal['suite_sha256'] == score['suite_sha256'], 'invalid held-out record seal')
        tasks = score['tasks']
        require(tasks and all(type(r['passed']) is bool for r in tasks.values()), 'invalid task results')
        require(type(score['numerator']) is int and type(score['denominator']) is int and
                score['denominator'] == len(tasks) and
                score['numerator'] == sum(int(r['passed']) for r in tasks.values()), 'score does not match tasks')
    archive = os.environ.get('GARS_BENCH_OUTPUTS_DIR')
    require(archive and archive.strip(), 'GARS_BENCH_OUTPUTS_DIR required to verify retained artifacts')
    outputs = contained(Path(archive), record['run_id'])
    require(output_manifest(outputs) == record['outputs'], 'retained output manifest/hash mismatch')
    metadata = {k: record[k] for k in ('run_id', 'git_sha', 'model', 'prompt_sha256', 'configuration', 'resource')}
    recomputed = make_record(outputs, metadata)
    require(json_equal(recomputed['scores'], record['scores']),
            'record differs from recomputed verdicts, pinned suite, or seal')
    return record


def read_record(path):
    return validate_record(read_json(Path(path)))


def compatible(records, partition):
    for record in records:
        validate_record(record)
    for field in ('model', 'prompt_sha256'):
        require(len(set(r[field] for r in records)) == 1, 'refusing delta across different ' + field)
    scores = [r['scores'][partition] for r in records]
    require(all(s['state'] == 'measured' for s in scores), partition + ': unmeasured')
    require(len(set(s['suite_sha256'] for s in scores)) == 1 and
            len(set(tuple(sorted(s['tasks'])) for s in scores)) == 1, 'different task suites')


def score_value(record, partition):
    score = record['scores'][partition]
    return Fraction(score['numerator'], score['denominator'])


def noise_floor(records, partition='tuned_on'):
    require(len(records) == 3, 'noise floor uncomputable: requires exactly three intact records; found %d' % len(records))
    compatible(records, partition)
    require(all(r['configuration'] == 'intact' for r in records), 'noise floor requires intact records')
    require(len(set(r['run_id'] for r in records)) == 3 and
            len(set(r['run_sha256'] for r in records)) == 3, 'noise floor requires distinct repeats')
    require(len(set(r['git_sha'] for r in records)) == 1, 'intact repeats must share git_sha')
    values = [score_value(r, partition) for r in records]
    return max(values) - min(values), sum(values) / 3


def compare(before, after, intact, partition='tuned_on'):
    compatible([before, after] + intact, partition)
    floor, baseline = noise_floor(intact, partition)
    delta = score_value(after, partition) - score_value(before, partition)
    return {'delta': delta, 'noise_floor': floor,
            'interpretation': 'no change' if abs(delta) <= floor else ('increase' if delta > 0 else 'decrease')}


def discriminates(intact, degraded, partition='tuned_on'):
    compatible(intact + [degraded], partition)
    require(degraded['configuration'] == 'degraded', 'requires a degraded record')
    require(degraded['run_id'] not in [r['run_id'] for r in intact], 'degraded record must be distinct')
    floor, baseline = noise_floor(intact, partition)
    return score_value(degraded, partition) < baseline - floor


def reference_readiness(tasks, input_root):
    """Refuse placeholder nf-core tasks even when their artifact shapes pass."""
    for name, task in tasks.items():
        if task['reference_source'] != 'nfcore_test_data_expected_output':
            continue
        inputs = {item['path'] for item in task['inputs']}
        registries = [c['artifact_registry'] for c in task['expected_outputs'].values()
                      if 'artifact_registry' in c]
        require(registries, name + ': unresolved required references: no numerical contract')
        for contract in registries:
            counts = {typ for typ, rule in contract['types'].items() if rule == 'counts'}
            require(contract['expected_samplesheet'] is not None and counts and
                    set(contract['reference_counts']) == counts,
                    name + ': unresolved required references: expected samplesheet and all reference counts required')
            with contained(input_root, contract['expected_samplesheet']).open(encoding='utf-8', newline='') as handle:
                rows = list(csv.DictReader(handle))
            require(rows, name + ': unresolved required references: empty expected samplesheet')
            for row in rows:
                require(row.get('fastq_1') in inputs and
                        (not row.get('fastq_2') or row['fastq_2'] in inputs),
                        name + ': unresolved required references: samplesheet FASTQs must be hashed task inputs')
        for item in task['inputs']:
            if item['path'].endswith('.json'):
                descriptor = read_json(contained(input_root, item['path']))
                require(not isinstance(descriptor, dict) or not descriptor.get('expected_output_gap'),
                        name + ': unresolved required references: source descriptor still declares a gap')


def row_exit(records):
    """Strict row exit: missing owner evidence is an error, never a skip."""
    ids = [record['run_id'] for record in records]
    require(len(ids) == len(set(ids)), 'duplicate owner run ids')
    required = ('intact-1', 'intact-2', 'intact-3', 'degraded-1')
    missing = [name for name in required if name not in ids]
    require(not missing, 'missing owner run record(s): ' + ', '.join(missing))
    chosen = {record['run_id']: record for record in records}
    intact = [chosen[name] for name in required[:3]]
    degraded = chosen['degraded-1']
    for record in intact + [degraded]:
        validate_record(record)
        require(record['scores']['held_out']['state'] == 'measured', 'held_out: unmeasured; row exit NOT met')
    reference_readiness(load_tasks(REPO / 'benchmarks/tasks', REPO, False), REPO)
    holdout = Path(os.environ['GARS_BENCH_HOLDOUT_DIR'])
    reference_readiness(load_tasks(holdout / 'tasks', holdout, True), holdout)
    for part in PARTITIONS:
        require(discriminates(intact, degraded, part),
                part + ': degraded must score below intact mean minus three-repeat range')
    return True


def print_fraction(label, value):
    print(label + ': ' + ratio_text(value.numerator, value.denominator))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command')
    validate = commands.add_parser('validate')
    validate.add_argument('--tasks', default=str(REPO / 'benchmarks/tasks'))
    score = commands.add_parser('score')
    score.add_argument('--outputs', required=True)
    score.add_argument('--metadata', required=True)
    score.add_argument('--runs', default=str(REPO / 'evals/runs'))
    delta = commands.add_parser('delta')
    delta.add_argument('before')
    delta.add_argument('after')
    delta.add_argument('--intact', nargs='+', required=True)
    delta.add_argument('--partition', choices=PARTITIONS, default='tuned_on')
    strict = commands.add_parser('row-exit', help='strict owner-evidence exit; never skips')
    strict.add_argument('--runs', default=str(REPO / 'evals/runs'))
    args = parser.parse_args(argv)
    try:
        if args.command == 'validate':
            tasks = load_tasks(Path(args.tasks), REPO, False)
            print('valid tasks: ' + ratio_text(len(tasks), len(tasks)))
        elif args.command == 'score':
            record = make_record(Path(args.outputs), read_json(Path(args.metadata)))
            name = write_record(record, Path(args.runs))
            for part, score in sorted(record['scores'].items()):
                print(part + ': ' + (ratio_text(score['numerator'], score['denominator'])
                                     if score['state'] == 'measured' else 'unmeasured (' + score['reason'] + ')'))
            print('record: ' + name)
        elif args.command == 'delta':
            result = compare(read_record(args.before), read_record(args.after),
                             [read_record(p) for p in args.intact], args.partition)
            for field in ('delta', 'noise_floor'):
                print_fraction(args.partition + ' ' + field, result[field])
            print(result['interpretation'])
        elif args.command == 'row-exit':
            row_exit([read_json(p) for p in sorted(Path(args.runs).glob('*.json'))])
            print('row exit: PASS (verified artifacts, both partitions, resolved references)')
        else:
            parser.error('choose validate, score, or delta')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('refused: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
