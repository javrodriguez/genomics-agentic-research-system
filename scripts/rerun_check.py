#!/usr/bin/env python3
"""Re-execute a COMPLETE manifest; fixture results are an instrument self-test.

Stdlib only, Python 3.6 grammar. No manifest is repaired or completed here.
"""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import fnmatch
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'gars/_system'))
import manifest_check as mc
import wrapperlib as wl
import executorlib as ex

TOLERANCES = REPO / 'gars/_references/tolerances.yaml'
WRAPPERS = REPO / 'gars/_system/wrappers'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def load_tolerances(path=TOLERANCES):
    """JSON is the supported YAML subset: no tags, aliases or implicit scalars."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    require(isinstance(data, dict) and set(data) == {'entries'}, 'invalid tolerance file')
    require(isinstance(data['entries'], list), 'invalid tolerance entries')
    for entry in data['entries']:
        require(isinstance(entry, dict), 'invalid tolerance entry')
        for key in ('wrapper', 'artifact', 'cause', 'evidence'):
            require(isinstance(entry.get(key), str) and bool(entry[key].strip()),
                    'tolerance entry missing ' + key)
        require(entry.get('mode') in ('byte_stable', 'numeric_tolerance'), 'unknown mode')
        if entry['mode'] == 'numeric_tolerance':
            require(entry.get('metric') == 'max_absolute_error', 'unknown or missing metric')
            threshold = entry.get('threshold')
            require(type(threshold) in (int, float) and math.isfinite(threshold) and threshold >= 0,
                    'invalid or missing threshold')
    return data['entries']


def rule_for(entries, wrapper, row):
    matched = [e for e in entries if e['wrapper'] == wrapper and
               (e['artifact'] == row['type'] or fnmatch.fnmatchcase(row['path'], e['artifact']))]
    require(len(matched) <= 1, 'ambiguous tolerance entry: ' + row['path'])
    return matched[0] if matched else {'mode': 'byte_stable'}


def numeric_table(path):
    # Metadata comment lines and CRLF are normalized. Column names and unique row
    # identifiers are exact; numeric cells use finite Decimal values. No rounding.
    lines = [line for line in Path(path).read_text(encoding='utf-8-sig').splitlines()
             if line.strip() and not line.startswith('#')]
    rows = list(csv.reader(lines, delimiter='\t'))
    require(bool(rows) and len(rows[0]) >= 2, 'numeric table missing header')
    header = rows[0]
    require(len(header) == len(set(header)), 'duplicate numeric column')
    require('id' in header, 'numeric table needs id column')
    key_index = header.index('id')
    values = {}
    ids = set()
    for row in rows[1:]:
        require(len(row) == len(header), 'ragged numeric table')
        key = row[key_index]
        require(bool(key) and key not in ids, 'duplicate or empty numeric row')
        ids.add(key)
        for index, column in enumerate(header):
            if index == key_index:
                continue
            try:
                value = Decimal(row[index])
            except InvalidOperation:
                raise ValueError('non-numeric table cell')
            require(value.is_finite(), 'non-finite numeric cell')
            values[(key, column)] = value
    require(bool(values), 'empty numeric table')
    return sorted(header), sorted(values.items())


def compare_artifact(original, replay, row, rule):
    left = wl.output_evidence(original, {k: row[k] for k in ('type', 'role', 'path')})
    right = wl.output_evidence(replay, {k: row[k] for k in ('type', 'role', 'path')})
    if 'sha256' in row:
        require(left['sha256'] == row['sha256'] and left.get('symlinks') == row.get('symlinks'),
                'original output drifted: ' + row['path'])
    mode = rule['mode']
    if mode == 'byte_stable':
        matched = left['sha256'] == right['sha256'] and left.get('symlinks') == right.get('symlinks')
        metric, value = 'sha256_equal', int(matched)
    else:
        a = numeric_table(original / row['path'])
        b = numeric_table(replay / row['path'])
        same_shape = a[0] == b[0] and [k for k, v in a[1]] == [k for k, v in b[1]]
        error = max(abs(x[1] - y[1]) for x, y in zip(a[1], b[1])) if same_shape else Decimal('Infinity')
        metric, value = rule['metric'], str(error)
        matched = same_shape and error <= Decimal(str(rule['threshold']))
    return dict(path=row['path'], mode=mode, match=matched, metric=metric, value=value,
                original_sha256=left['sha256'], replay_sha256=right['sha256'])


def require_clean_code(repo, paths, label):
    status = wl.git_value(repo, 'status', '--porcelain', '--untracked-files=all', '--', *paths)
    require(status is not None, 'cannot inspect ' + label + ' code')
    require(not status, label + ' code has uncommitted changes')


def require_route_recording(manifest):
    if manifest.get('data_class') == 'deidentified_under_agreement':
        require(all(key in manifest for key in ('expiry', 'permitted_backends')),
                'manifest_predates_expiry_recording: prepare and complete a new original')


def validate_manifest(manifest, stage):
    require('agreement_ref' in manifest and manifest['agreement_ref'] is not None,
            'no agreement_ref recorded')
    require('execution_config' in manifest, 'no execution config recorded')
    require_route_recording(manifest)
    try:
        grade = mc.grade(manifest)
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError('incomplete manifest: ' + str(exc))
    missing = [str(g['number']) + ' ' + g['name'] for g in grade['groups']
               if g['applicable'] and g['class'] != 'optional' and not g['present']]
    require(grade['ok'], 'incomplete manifest: ' + '; '.join(missing))
    require(manifest['predicate_facts']['status'] == 'COMPLETE' and wl.read_status(stage) == 'COMPLETE',
            'run status is not COMPLETE')
    require(wl.git_value(Path(manifest['checkout']), 'rev-parse', 'HEAD') == manifest['pipeline_commit'],
            'pipeline_commit differs from HEAD')
    require(wl.git_value(REPO, 'rev-parse', 'HEAD') == manifest['gars_commit'], 'gars_commit differs from HEAD')
    require_clean_code(REPO, ['gars/_system', 'scripts', 'gars/_references'], 'GARS')
    if manifest['predicate_facts']['wrapper_kind'] == 'nextflow':
        require_clean_code(Path(manifest['checkout']), ['.'], 'pipeline')
    if manifest['predicate_facts']['design_record']:
        evidence = manifest['design_check']
        design_check = stage.parents[2] / evidence['path']
        require(design_check.is_file() and wl.sha256(design_check) == evidence['sha256'],
                'design check changed or missing')
    if manifest['wrapper'] == 'rnaseq-de':
        design_path = stage.parents[2] / '01_samplesheets' / 'rnaseq_bulk_design.csv'
        require('design' in manifest['inputs'] and
                Path(manifest['inputs']['design']).resolve() == design_path.resolve(),
                'design is not the canonical project design')
    for label, path in manifest['inputs'].items():
        require(Path(path).is_file() and wl.sha256(Path(path)) == manifest[label + '_sha256'],
                'input hash changed: ' + label)
    for entry in manifest['execution_config']:
        path = REPO / entry['path']
        require(path.is_file() and wl.sha256(path) == entry['sha256'],
                'execution config drifted: ' + entry['path'])
    require(manifest.get('execution_config_resolved', {}).get('backend') == manifest['backend'],
            'execution config backend differs')
    replay_dataset_values(manifest, stage.parents[2])
    wl.verify_output_manifest(stage)
    require(manifest['wrapper'] != 'scrna-qc-cluster' or 'samplesheet' in manifest['inputs'],
            'manifest lacks required samplesheet input: scrna-qc-cluster')
    if manifest['backend'] == 'slurm':
        try:
            probe = subprocess.run(['sbatch', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            available = probe.returncode == 0
        except OSError:
            available = False
        require(available, 'second backend unavailable')


def wrapper_info(manifest, wrappers_root):
    default_root = (REPO / 'gars/_system/wrappers').resolve()
    require(wrappers_root == default_root or manifest['wrapper'] == 'rerun-fixture',
            'wrappers root override is only allowed for rerun-fixture')
    info = mc.load_schema()['wrappers'].get(manifest['wrapper'])
    if info is None and wrappers_root != default_root and manifest['wrapper'] == 'rerun-fixture':
        info = dict(name='rerun-fixture', assay='rerun-fixture', substage='01_rerun-fixture', kind='local')
    require(info is not None, 'unregistered wrapper')
    # Same directory and Python filename spelling as the tool registry and gars-env.
    path = wrappers_root / info['name'] / (info['name'].replace('-', '_') + '.py')
    require(path.is_file(), 'wrapper unavailable: ' + info['name'])
    return info, path


def prepare_arguments(manifest):
    inputs = manifest['inputs']
    if manifest['wrapper'] == 'rnaseq-de':
        return ['--counts', inputs['counts'], '--design', inputs['design']]
    if manifest['wrapper'] in ('scrna-qc-cluster', 'spatial-cluster-count'):
        value = manifest['params'].get('h5ad')
        return ['--h5ad', value] if value and value != 'None' else []
    return []


def run_wrapper(wrapper, verb, project, manifest, env):
    argv = [sys.executable, str(wrapper), verb, '--project', str(project)]
    argv += prepare_arguments(manifest) if verb == 'prepare' else ['--model', 'none']
    result = subprocess.run(argv, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'wrapper ' + verb + ' failed: ' +
            result.stdout.decode('utf-8', 'replace') + result.stderr.decode('utf-8', 'replace'))


def replay_dataset_values(manifest, original_project=None):
    """Compare recorded classification and route before constructing a replay."""
    import venue_policy
    require_route_recording(manifest)
    values = {key: manifest.get(key) for key in ('data_class', 'purpose', 'agreement_ref',
                                                'expiry', 'permitted_backends')}
    # Old public manifests have no expiry requirement and use the class route.
    if values['data_class'] == 'public':
        if values['expiry'] is None:
            values['expiry'] = 'none'
        if values['permitted_backends'] is None:
            values['permitted_backends'] = venue_policy.narrowed('public')
    require(all(value is not None for value in values.values()),
            'replay_dataset_mismatch: dataset route fields not recorded in manifest')
    if original_project is not None:
        registered = wl.dataset_record(original_project)
        for key, value in values.items():
            actual = registered.get(key)
            if key == 'permitted_backends' and actual is None:
                actual = venue_policy.narrowed(registered.get('data_class'))
            if key == 'expiry' and actual is None and registered.get('data_class') == 'public':
                actual = 'none'
            require(actual == value, 'replay_dataset_mismatch: ' + key)
    return values


def bind_project(manifest, project, info, original_project=None):
    dataset_values = replay_dataset_values(manifest, original_project)
    config = project / '_config'
    config.mkdir(parents=True)
    # Original inputs stay immutable and keep their resolved names and hashes.
    (config / (info['assay'] + '.yaml')).symlink_to(Path(manifest['inputs']['config']))
    for entry in manifest['execution_config']:
        source = (REPO / entry['path']).resolve()
        target = config / ('executor.yaml' if entry['role'] == 'executor_descriptor' else
                           manifest['execution_config_resolved']['nextflow_config'])
        target.symlink_to(source)
    if 'samplesheet' in manifest['inputs'] or 'design' in manifest['inputs']:
        sheets = project / '01_samplesheets'
        sheets.mkdir()
        for label, suffix in (('samplesheet', '_samplesheet.csv'), ('design', '_design.csv')):
            if label in manifest['inputs']:
                (sheets / (info['assay'] + suffix)).symlink_to(Path(manifest['inputs'][label]))
    if original_project is not None and manifest['predicate_facts']['design_record']:
        evidence = manifest['design_check']
        source = original_project / evidence['path']
        target = project / '01_samplesheets' / (info['assay'] + '_design_check.json')
        target.symlink_to(source.resolve())
    # Reconstruct registration links only from the recorded dataset locations.
    # Finalize owns the row, its validation and its read-only mode.
    locations = json.loads(manifest['input_data_location']['dataset'])
    require(isinstance(locations, list) and bool(locations) and
            all(isinstance(path, str) and Path(path).is_absolute() for path in locations),
            'dataset locations are not a recorded path list')
    raw = project / '00_data' / info['assay'] / 'raw'
    raw.mkdir(parents=True)
    for location in locations:
        source = Path(location)
        require(source.exists(), 'dataset input unavailable: ' + location)
        target = raw / source.name
        require(not target.exists(), 'dataset input basename collision: ' + source.name)
        target.symlink_to(source)
    for name in ('CONTEXT.md', 'HISTORY.md'):
        (project / name).write_text('# Re-run from manifest\n', encoding='utf-8')
    result = subprocess.run([sys.executable, str(REPO / 'gars/_system/stage00_register.py'),
        'finalize', '--project', str(project), '--data-class', manifest['data_class'],
        '--purpose', manifest['purpose'], '--agreement-ref', manifest['agreement_ref'],
        '--model', 'none', '--permitted-backends', dataset_values['permitted_backends']] +
        (['--expiry', dataset_values['expiry']] if dataset_values['expiry'] != 'none' else []),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    require(result.returncode == 0, 'dataset finalize failed: ' +
            result.stdout.decode('utf-8', 'replace') + result.stderr.decode('utf-8', 'replace'))
    replay_dataset_values(dict(manifest, **dataset_values), project)


def validate_preparation(original, replay, old_stage, new_stage):
    expected = dict(original['params'])
    if 'outdir' in expected:
        require(expected['outdir'] == str(old_stage / 'run/results'), 'unrecognized output parameter')
        expected['outdir'] = str(new_stage / 'run/results')
    require(replay['params'] == expected, 're-preparation params differ')
    require(replay['config_sha256'] == original['config_sha256'], 're-preparation config differs')
    require(replay['inputs'] == original['inputs'], 're-preparation inputs differ')
    require(replay['pipeline_commit'] == original['pipeline_commit'] and
            Path(replay['checkout']).resolve() == Path(original['checkout']).resolve(),
            're-preparation pipeline differs')
    require(replay.get('execution_config') == original['execution_config'] and
            replay.get('execution_config_resolved') == original['execution_config_resolved'],
            're-preparation execution config differs')


def reproduce(manifest_path, runs, out, wrappers_root=WRAPPERS):
    require(runs > 0, 'runs must be positive')
    manifest_path = Path(manifest_path).resolve()
    original_stage = manifest_path.parent.parent
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = load_tolerances()
    committed = wl.git_value(REPO, 'show', 'HEAD:gars/_references/tolerances.yaml')
    require(committed == TOLERANCES.read_text(encoding='utf-8').strip(), 'tolerances are not pre-committed')
    validate_manifest(manifest, original_stage)
    tolerances_sha256 = wl.sha256(TOLERANCES)
    info, wrapper = wrapper_info(manifest, Path(wrappers_root).resolve())
    rows = manifest['outputs']
    rules = [rule_for(entries, manifest['wrapper'], row) for row in rows]
    out = Path(out).resolve()
    require(not out.exists(), 'output directory already exists')
    out.mkdir(parents=True)
    results, matched = [], 0
    env = dict(os.environ)
    if info['kind'] == 'nextflow':
        env['GARS_PIPELINES'] = str(Path(manifest['checkout']).parent)
    for number in range(1, runs + 1):
        job, comparisons, success, reason = None, [], False, None
        code = dict(wrappers_root=str(wrapper.parent.parent), wrapper=str(wrapper))
        try:
            code.update(wrapper_sha256=wl.sha256(wrapper),
                        wrapperlib_sha256=wl.sha256(REPO / 'gars/_system/wrapperlib.py'))
            validate_manifest(manifest, original_stage)
            project = out / ('run-%d' % number)
            bind_project(manifest, project, info, original_stage.parents[2])
            stage = project / '02_bioinformatics' / info['assay'] / info['substage']
            run_wrapper(wrapper, 'prepare', project, manifest, env)
            replay_path = stage / 'reproducibility/manifest.json'
            replay = json.loads(replay_path.read_text(encoding='utf-8'))
            validate_preparation(manifest, replay, original_stage, stage)
            job, reason = ex.submit(project, stage / 'submit.sh')
            require(job is not None, 'submit refused: ' + str(reason))
            while True:
                state, reason = ex.status(project, job)
                require(state is not None, 'executor unavailable: ' + str(reason))
                if state in ('COMPLETED', 'VALIDATING', 'COMPLETE'):
                    break
                require(state in ('PENDING', 'SUBMITTED', 'RUNNING'), 're-run failed: ' + str(state))
                time.sleep(0.1 if manifest['backend'] == 'local' else 5)
            run_wrapper(wrapper, 'collect', project, manifest, env)
            require(wl.read_status(stage) == 'COMPLETE', 're-run status is not COMPLETE')
            wl.verify_output_manifest(stage)
            replay = json.loads(replay_path.read_text(encoding='utf-8'))
            require([(r['type'], r['role'], r['path']) for r in replay['outputs']] ==
                    [(r['type'], r['role'], r['path']) for r in rows], 'output inventory differs')
            for row, rule in zip(rows, rules):
                result = compare_artifact(original_stage, stage, row, rule)
                comparisons.append(result)
                print('%s %s match=%s %s=%s' % (result['path'], result['mode'],
                      'yes' if result['match'] else 'no', result['metric'], result['value']), flush=True)
            require(len(comparisons) == len(rows), 'output silently skipped')
            print('graded %d of %d outputs' % (len(comparisons), len(rows)), flush=True)
            success = all(r['match'] for r in comparisons)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            reason = str(exc)
            print('run %d match=no reason=%s' % (number, reason), flush=True)
        matched += int(success)
        results.append(dict(run=number, job=job, match=success, reason=reason,
                            artifacts=comparisons, code=code))
        (out / 'comparison.json').write_text(json.dumps(dict(runs=results, requested=runs,
            original=str(manifest_path), tolerances_sha256=tolerances_sha256,
            wrappers_root=str(wrapper.parent.parent), wrapper_sha256=results[0]['code'].get('wrapper_sha256')),
            indent=2, sort_keys=True) + '\n')
    print('reproduction: %d/%d' % (matched, runs), flush=True)
    return 0 if matched == runs and len(results) == runs else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--runs', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--wrappers-root', type=Path, default=WRAPPERS,
                        help='test-only fixture wrapper root; default is the real wrappers root')
    args = parser.parse_args(argv)
    try:
        return reproduce(args.manifest, args.runs, args.out, args.wrappers_root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print('refused: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
