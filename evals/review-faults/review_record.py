"""JSON Schema 2020-12 contract, implemented with the Python 3.6 standard library."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLASSES = json.loads((HERE / 'classes.json').read_text(encoding='utf-8'))
SCHEMA = json.loads((HERE / 'schema/review_record.schema.json').read_text(encoding='utf-8'))


def validate(value, schema=None, path='record'):
    """Implement every validation keyword used by the shipped schema; return errors."""
    schema = SCHEMA if schema is None else schema
    errors = []
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'integer': int, 'boolean': bool}
    integer = (type(value) is int or (type(value) is float and value.is_integer()))
    if kind and ((kind == 'integer' and not integer) or
                 (kind != 'integer' and not isinstance(value, types[kind]))):
        return [path + ': expected ' + kind]
    if 'enum' in schema and value not in schema['enum']:
        errors.append(path + ': outside vocabulary')
    if kind == 'object':
        for key in schema.get('required', []):
            if key not in value:
                errors.append(path + '.' + key + ': missing')
        for key, item in value.items():
            spec = schema.get('properties', {}).get(key)
            if spec is not None:
                errors.extend(validate(item, spec, path + '.' + key))
            elif schema.get('additionalProperties') is False:
                errors.append(path + '.' + key + ': undeclared')
    if kind == 'array':
        for index, item in enumerate(value):
            errors.extend(validate(item, schema['items'], '%s[%d]' % (path, index)))
    if kind == 'string':
        if len(value) < schema.get('minLength', 0):
            errors.append(path + ': too short')
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            errors.append(path + ': pattern mismatch')
    if kind == 'integer' and value < schema.get('minimum', value):
        errors.append(path + ': below minimum')
    return errors


def review_errors(review):
    return validate(review, SCHEMA['properties']['review'], 'review')


def invalid_reasons(record, manifest=None):
    errors = validate(record)
    if errors:
        return errors
    env = record['envelope']
    if env['reviewer']['uid'] == env['producer']['uid']:
        errors.append('same producing and reviewing OS account on recorded host')
    if env['reviewer']['uid'] == 0:
        errors.append('privileged reviewer')
    if env['blindness']['hits']:
        errors.append('blindness hit')
    if env['ended_on_usage_limit']:
        errors.append('usage limit')
    if env['exit_code']:
        errors.append('review process failed')
    if manifest and env['reviewer']['prompt_sha256'] != manifest['prompt_sha256']:
        errors.append('prompt mismatch')
    if manifest and env['reviewer']['prompt_path'] != manifest['prompt_path']:
        errors.append('prompt path mismatch')
    for finding in record['review']['findings']:
        if finding['line_end'] < finding['line_start']:
            errors.append('reversed finding interval')
    return errors
