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
    for field in ('safeguard_refusal', 'retry_binding_sha256'):
        view['envelope'].pop(field, None)
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
    if env.get('safeguard_refusal', False):
        errors.append('safeguard refusal: unscored attempt')
    for phase in phases:
        for key, message in (('exit_code', 'process failed'),
                             ('ended_on_usage_limit', 'usage limit')):
            if phase[key]:
                errors.append('phase ' + phase['name'] + ': ' + message)
        if phase['blindness']['hits']:
            errors.append('phase ' + phase['name'] + ': blindness hit')
    if not env['narrative_withheld_until_phase_b']:
        errors.append('narrative not withheld')
    return errors


def check_history(history):
    """Validate retry budget and unchanged inputs; return the first refusal."""
    refused = None
    for i, record in enumerate(history):
        env = record['envelope']
        if env['reviewer']['attempt'] != i + 1:
            raise ValueError('attempt history must be contiguous')
        if i:
            previous = history[i - 1]['envelope']
            if refused is not None:
                if i != refused['envelope']['reviewer']['attempt']:
                    raise ValueError('only one safeguard retry allowed')
                original = refused['envelope']
                digest = original.get('retry_binding_sha256')
                if not digest or env.get('retry_binding_sha256') != digest:
                    raise ValueError('safeguard retry inputs or command changed')
                for field in ('prompt_path', 'prompt_sha256', 'session_id', 'tool_version'):
                    if env['reviewer'][field] != original['reviewer'][field]:
                        raise ValueError('safeguard retry reviewer binding changed')
                if env['sandbox_settings_sha256'] != original['sandbox_settings_sha256']:
                    raise ValueError('safeguard retry settings changed')
            elif not previous['ended_on_usage_limit']:
                raise ValueError('only usage-limit or safeguard attempts may be retried')
        if env.get('safeguard_refusal', False) and refused is None:
            refused = record
    return refused
