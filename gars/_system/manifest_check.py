#!/usr/bin/env python3
"""Grade only supplied manifests against the shipped §8.1 schema (stdlib, Python 3.6)."""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parents[1] / '_references/manifest_schema.json'
PLACEHOLDERS = ('', 'unknown', 'todo', 'null', 'none', 'n/a', 'na', 'not-applicable', 'no-rng-in-code-path', 'not-exposed-by-harness')


def load_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def text_present(value, sentinels=()):
    return (isinstance(value, str) and (value in sentinels or
            (value.strip().lower() not in PLACEHOLDERS and
             not value.strip().startswith(('<', '{{')))))


def parameter_present(value):
    if isinstance(value, str):
        return text_present(value)
    if isinstance(value, dict):
        return bool(value) and all(text_present(k) and parameter_present(v) for k,v in value.items())
    if isinstance(value, list):
        return bool(value) and all(parameter_present(v) for v in value)
    return type(value) in (int, float, bool)


def digest(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def recorded_file(value):
    return isinstance(value, dict) and text_present(value.get('path')) and digest(value.get('sha256'))


def positive(value):
    return type(value) in (int, float) and value > 0


def facts_for(manifest, schema):
    facts = manifest.get('predicate_facts')
    if not isinstance(facts, dict):
        raise ValueError('predicate_facts missing or not an object')
    for key, values in schema['predicate_facts'].items():
        if key not in facts or not any(type(facts[key]) is type(v) and facts[key] == v for v in values):
            raise ValueError('predicate_facts.%s missing or outside its closed vocabulary' % key)
    return facts


def applicable(group, facts):
    predicate = group['predicate']
    if predicate is None:
        return True
    if set(predicate) != {'fact', 'equals'} or predicate['fact'] not in facts:
        raise ValueError('predicate must read only a named predicate_facts fact')
    return facts[predicate['fact']] == predicate['equals']


def group_present(number, m, schema):
    """Shape and content, not truthiness: a placeholder never fills a required field."""
    if number == 1:
        inputs, locations = m.get('inputs'), m.get('input_data_location')
        return (isinstance(inputs, dict) and bool(inputs) and isinstance(locations, dict) and
                all(text_present(p) and text_present(locations.get(k)) and digest(m.get(k + '_sha256'))
                    for k, p in inputs.items()))
    if number == 2:
        return all(text_present(m.get(k)) for k in ('wrapper','pipeline_commit','workflow_name','workflow_version','gars_commit'))
    if number == 3:
        entries = m.get('execution_config')
        valid = (isinstance(entries, list) and bool(entries) and
                 all(recorded_file(e) and e.get('role') in
                     ('executor_descriptor', 'nextflow_config') and
                     not Path(e['path']).is_absolute() for e in entries))
        roles = [e['role'] for e in entries] if valid else []
        valid = (valid and len(roles) == len(set(roles)) and
                 'executor_descriptor' in roles and
                 (m.get('predicate_facts', {}).get('wrapper_kind') != 'nextflow' or
                  'nextflow_config' in roles))
        return (isinstance(m.get('params'), dict) and parameter_present(m['params']) and
                digest(m.get('config_sha256')) and valid)
    if number == 4:
        rows = m.get('containers')
        return (isinstance(rows, list) and bool(rows) and all(isinstance(r, dict) and
                text_present(r.get('process')) and text_present(r.get('image')) and
                ((isinstance(r.get('digest'), str) and re.fullmatch(r'sha256:[0-9a-f]{64}', r['digest']) is not None
                  and r['image'].endswith('@' + r['digest'])) or
                 (digest(r.get('image_sha256')) and text_present(r.get('image_path')))) for r in rows))
    if number == 5:
        rows = m.get('software_versions')
        return (isinstance(rows, list) and bool(rows) and all(recorded_file(r) and
                isinstance(r.get('versions'), dict) and bool(r['versions']) and
                all(text_present(v) for v in r['versions'].values()) for r in rows))
    if number == 6:
        r = m.get('reference', {})
        return (isinstance(r, dict) and all(text_present(r.get(k)) for k in ('build','annotation_release'))
                and all(digest(r.get(k)) for k in ('fasta_sha256','gtf_sha256')) and r.get('comparison') == 'matched')
    if number == 7:
        return recorded_file(m.get('command'))
    if number == 8:
        rows = m.get('outputs')
        if not isinstance(rows, list) or not rows:
            return False
        for r in rows:
            if not isinstance(r, dict) or not all(text_present(r.get(k)) for k in ('type','role','path')) or r.get('artifact_class') not in ('durable','intermediate'):
                return False
            value = r.get('sha256')
            if not isinstance(value, str) or not any(re.fullmatch(p, value) for p in schema['output_sha256_forms']):
                return False
            if value.startswith('sha256-tree:'):
                import hashlib
                members = r.get('members')
                if not isinstance(members, list) or not members or not all(recorded_file(f) for f in members):
                    return False
                paths = [f['path'] for f in members]
                if paths != sorted(set(paths)):
                    return False
                listing = ''.join(f['path'] + '\t' + f['sha256'] + '\n' for f in members)
                if value != 'sha256-tree:' + hashlib.sha256(listing.encode('utf-8')).hexdigest():
                    return False
                if not isinstance(r.get('symlinks'), list):
                    return False
        return True
    if number == 9:
        r = m.get('execution')
        return isinstance(r, dict) and all(text_present(r.get(k)) for k in ('start','complete'))
    if number == 10:
        r = m.get('resources')
        return isinstance(r, dict) and all(text_present(r.get(k)) for k in ('Elapsed','MaxRSS','AllocCPUS'))
    if number == 11:
        return (m.get('backend') in ('local','slurm') and m.get('backend') == m['predicate_facts']['backend'] and
                m.get('venue') == m.get('backend') and
                m.get('purpose') in ('fixture','internal','pilot_internal','pilot_external','commercial') and
                m.get('data_class') in ('public','deidentified_under_agreement','identifiable') and
                isinstance(m.get('input_data_location'), dict) and bool(m['input_data_location']) and
                all(text_present(v) for v in m['input_data_location'].values()) and text_present(m.get('artifact_destination')))
    if number == 12:
        rows = m.get('approvals')
        return isinstance(rows, list) and bool(rows) and all(isinstance(r, dict) and text_present(r.get('id')) and digest(r.get('sha256')) for r in rows)
    if number == 13:
        seeds = m.get('random_seeds')
        good = seeds in schema['sentinels']['random_seeds'] if isinstance(seeds, str) else (
            isinstance(seeds, list) and bool(seeds) and all(isinstance(r, dict) and text_present(r.get('call')) and
             (type(r.get('seed')) is int or (r.get('seed_supported') is False and r.get('determinism') == 'unknown')) for r in seeds))
        return good and positive(m.get('threads'))
    if number == 14:
        return recorded_file(m.get('design_check'))
    if number == 15:
        return m.get('failure_class') in ('transient','infrastructure','tool','data_quality','workflow','agent_reasoning','scientific_validation')
    if number == 16:
        rows = m.get('model_steps')
        if not isinstance(rows, list) or not rows:
            return False
        for r in rows:
            if not isinstance(r, dict) or not all(text_present(r.get(k)) for k in ('provider','model_id','model_version','prompt_id')):
                return False
            provider = next((v for k,v in schema['model_providers'].items() if r['model_id'].startswith(k)), None)
            if provider is None or r['provider'] != provider:
                return False
            prompt = r.get('prompt_sha256', {})
            if not isinstance(prompt, dict) or prompt.get('algorithm') not in ('git-sha1','git-sha256'):
                return False
            length = 40 if prompt['algorithm'] == 'git-sha1' else 64
            if not isinstance(prompt.get('value'), str) or not re.fullmatch('[0-9a-f]{%d}' % length, prompt['value']):
                return False
            if r.get('routing_rule_id') not in schema['sentinels']['model_steps.routing_rule_id'] or r.get('sampling_parameters') not in schema['sentinels']['model_steps.sampling_parameters'] or not recorded_file(r.get('input_context')):
                return False
        return True
    if number == 17:
        return digest(m.get('idempotency_key'))
    if number == 18:
        return text_present(m.get('template_version')) and text_present(m.get('agent_model'), schema['sentinels']['agent_model'])
    raise ValueError('unknown manifest group')


def grade(manifest, schema=None):
    schema = load_schema() if schema is None else schema
    if not isinstance(manifest, dict):
        raise ValueError('manifest must be an object')
    facts = facts_for(manifest, schema)
    # Resolve every predicate before inspecting any governed group.
    decisions = [(g, applicable(g, facts)) for g in schema['groups']]
    groups, numerator, denominator, optional_missing = [], 0, 0, []
    for g, applies in decisions:
        present = bool(group_present(g['number'], manifest, schema))
        row = dict(g, applicable=applies, present=present)
        groups.append(row)
        if g['class'] not in ('required','required_if_applicable','optional'):
            raise ValueError('invalid group class')
        if g['class'] == 'optional':
            if applies and not present:
                optional_missing.append(g['number'])
        elif applies:
            denominator += 1
            numerator += int(present)
    return {'groups':groups,'present':numerator,'applicable':denominator,
            'optional_missing':optional_missing,'ok':bool(denominator) and numerator == denominator}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifests', nargs='+', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    reports, read, graded = [], 0, 0
    schema = load_schema()
    for path in args.manifests:
        read += 1
        try:
            report = grade(json.loads(path.read_text(encoding='utf-8')), schema)
            graded += 1
        except (OSError, ValueError, TypeError, KeyError, UnicodeError) as exc:
            report = {'ok':False,'error':str(exc)}
        report['manifest'] = str(path)
        reports.append(report)
        if not args.json:
            if 'error' in report:
                print('ERROR %s: %s' % (path, report['error']))
                continue
            for g in report['groups']:
                print('%s %s %s applicable=%s present=%s' % (g['number'],g['name'],g['class'],
                      'yes' if g['applicable'] else 'no','yes' if g['present'] else 'no'))
            print('manifest completeness: %d/%d required groups%s' % (report['present'],report['applicable'],
                  ' (uncomputable)' if not report['applicable'] else ''))
            print('optional missing: %s' % (','.join(map(str,report['optional_missing'])) or 'none'))
    if args.json:
        print(json.dumps({'manifests_read':read,'manifests_graded':graded,'manifests':reports},sort_keys=True))
    else:
        print('manifests read: %d; manifests graded: %d' % (read,graded))
    return 0 if read == graded and all(r['ok'] for r in reports) else 1


if __name__ == '__main__':
    sys.exit(main())
