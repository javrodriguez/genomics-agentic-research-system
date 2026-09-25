"""0100 route enforcement; no environment, flags or test exceptions (Python 3.6)."""
import csv
import datetime
import re
from decimal import Decimal
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / '_references/data_policy.tsv'
PURPOSES = ('fixture', 'internal', 'pilot_internal', 'pilot_external', 'commercial')
VENUES = ('local', 'homelab', 'slurm')


def fail(code, detail):
    return {'check': code, 'detail': detail}


def routes():
    with POLICY.open(encoding='utf-8', newline='') as handle:
        return {row['data_class']: row for row in csv.DictReader(handle, delimiter='\t')}


def permissions(value):
    if value == 'none':
        return set()
    tokens = value.split('|')
    if not tokens or any(not re.fullmatch(
            r'(local|homelab|slurm):(fixture|internal|pilot_internal|pilot_external|commercial)',
            token) for token in tokens) or len(set(tokens)) != len(tokens):
        raise ValueError('permitted_backends_invalid')
    return set(tokens)


def narrowed(data_class, value=None):
    default = routes()[data_class]['permitted_backends']
    value = default if value is None else value
    if not permissions(value).issubset(permissions(default)):
        raise ValueError('permitted_backends_widened')
    return value


def expiry_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('expiry must be YYYY-MM-DD')
    return datetime.datetime.strptime(value, '%Y-%m-%d').date()


def memory_bytes(value):
    if value is None:
        return None
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)([KMGT])', str(value))
    if not match:
        raise ValueError('memory must be a number with unit K/M/G/T')
    return Decimal(match.group(1)) * (1024 ** ('KMGT'.index(match.group(2)) + 1))


def check(dataset_row, venue, purpose, mem_bytes, fastq_inputs):
    """Accumulate independent refusals; values are exact, never normalized."""
    failures = []
    row = dataset_row or {}
    data_class = row.get('data_class')
    fixture = data_class == 'public' and row.get('purpose') == 'fixture'
    if not dataset_row:
        failures.append(fail("dataset_unclassified", 'no readable 00_data/dataset.tsv'))
    if data_class == 'identifiable':
        failures.append(fail("class_not_permitted", 'identifiable has no route'))
    try:
        allowed = permissions(narrowed(data_class, row.get('permitted_backends')))
    except (KeyError, TypeError, AttributeError, ValueError):
        allowed = set()
    if (purpose != row.get('purpose') or purpose not in PURPOSES or
            venue + ':' + str(purpose) not in allowed):
        failures.append(fail("venue_not_permitted", 'route: class %s venue %s purpose %s' %
                             (data_class, venue, purpose)))
    if venue == 'slurm' and purpose == 'pilot_internal' and (
            not row.get('agreement_ref') or row['agreement_ref'].strip().lower() in
            ('none', 'unknown', 'todo', 'null')):
        failures.append(fail("venue_not_permitted", 'venue slurm pilot_internal requires agreement_ref'))
    expiry = row.get('expiry')
    if (expiry and expiry != 'none') or data_class == 'deidentified_under_agreement':
        try:
            if expiry_date(expiry) < datetime.datetime.now(datetime.timezone.utc).date():
                raise ValueError('expiry is in the past')
        except (ValueError, TypeError):
            failures.append(fail("dataset_expired", 'expiry absent, invalid or expired'))
    if venue == 'local':
        if purpose != 'fixture':
            failures.append(fail("venue_not_permitted", 'venue local purpose rule: fixture only'))
        if mem_bytes is None and not fixture:
            failures.append(fail("resource_undeclared", 'venue local requires declared memory outside public/fixture'))
        if mem_bytes is not None and mem_bytes > 8 * 1024 ** 3:
            failures.append(fail("venue_not_permitted", 'venue local memory rule: above 8 GiB'))
        if fastq_inputs and not fixture:
            failures.append(fail("venue_not_permitted", 'venue local FASTQ rule: exactly public/fixture required'))
    for path in fastq_inputs:
        if not Path(path).is_file():
            failures.append(fail("input_missing", 'listed FASTQ input does not exist'))
    return failures
