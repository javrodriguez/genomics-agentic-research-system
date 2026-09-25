"""Science adapter: validate, check science identity, then project only the path."""
import copy
from bio_common import (HERE, PROMPT_PATH, read_json, validate,
                        row9_invalid_reasons, rf_common)

SCHEMA = read_json(HERE / 'schema/review_record.schema.json')


def project_prompt_path(record, manifest):
    """Pure projection, called only after the three-way science-path check."""
    result, context = copy.deepcopy(record), copy.deepcopy(manifest)
    result['envelope']['reviewer']['prompt_path'] = rf_common.PROMPT_PATH
    context['prompt_path'] = rf_common.PROMPT_PATH
    return result, context


def invalid_reasons(record, manifest=None):
    errors = validate(record, SCHEMA)
    if errors:
        return errors
    env = record['envelope']
    manifest = manifest or {'prompt_path': PROMPT_PATH,
                            'prompt_sha256': env['reviewer']['prompt_sha256']}
    if not (env['reviewer']['prompt_path'] == manifest['prompt_path'] == PROMPT_PATH):
        return ['science prompt path mismatch']
    phases = env['phases']
    if len(phases) != 2:
        return ['exactly two phases required']
    for phase, schema in zip(phases, SCHEMA['properties']['envelope']['properties']['phases']['prefixItems']):
        errors.extend(validate(phase, schema))
    if errors:
        return errors
    view, context = project_prompt_path(record, manifest)
    del view['envelope']['phases']
    del view['envelope']['narrative_withheld_until_phase_b']
    view['envelope']['blindness'] = {
        'calls': sum(p['blindness']['calls'] for p in phases),
        'hits': sum(p['blindness']['hits'] for p in phases),
        'ambiguous': env['blindness']['ambiguous']}
    if any(env['blindness'][key] != view['envelope']['blindness'][key] for key in ('calls', 'hits')):
        errors.append('phase blindness totals differ')
    for finding in view['review']['findings']:
        finding['class'] = 'other'
    errors.extend(row9_invalid_reasons(view, context))
    for phase in phases:
        for key, message in (('exit_code', 'process failed'),
                             ('ended_on_usage_limit', 'usage limit')):
            if phase[key]:
                errors.append('phase ' + phase['name'] + ': ' + message)
        if phase['blindness']['hits']:
            errors.append('phase ' + phase['name'] + ': blindness hit')
    if not env['narrative_withheld_until_phase_b']:
        errors.append('narrative not withheld')
    if not phases[1]['session_matches_phase_a'] or phases[0]['session_id'] != phases[1]['session_id']:
        errors.append('resume session differs')
    return errors
