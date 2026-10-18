"""0100 route enforcement; no environment, flags or test exceptions (Python 3.6)."""
import csv
import datetime
import re
from decimal import Decimal
from pathlib import Path

POLICY = Path(__file__).resolve().parents[1] / '_references/data_policy.tsv'
PURPOSES = ('fixture', 'internal', 'pilot_internal', 'pilot_external', 'commercial')
# S00-class (0321, choice 1c): a new registration writes only these two, which people read as
# test and analysis; the legacy three are still read and enforced in the rows that carry them,
# exactly as before, and never written by a new registration.
REGISTRABLE_PURPOSES = ('fixture', 'internal')
LEGACY_PURPOSES = ('pilot_internal', 'pilot_external', 'commercial')
USE_OF_PURPOSE = {'fixture': 'test', 'internal': 'analysis'}
VENUES = ('local', 'homelab', 'slurm')
ASSAY_IDS = ('atacseq_bulk', 'chipseq_bulk', 'cutandrun', 'methylseq', 'rnaseq_bulk', 'scrnaseq',
             'spatialvi')
# 0293: the memory one job may request, per venue; a venue with no entry has no GARS ceiling
# (Slurm's is the partition's; homelab's waits on a measured host size). check()'s local rule
# compares the same number, and a test holds the two equal.
MEM_CEILING = {'local': 8 * 1024 ** 3}
ACCEPTED_MEM = {'local': '8G'}
# 0293 part 3: the summed input bytes a venue can hold, per venue. Empty on purpose: homelab's
# number waits on a measured host size, and no number is invented for it (round 9 item 3);
# local already refuses every input outside public/fixture, and Slurm's limit is the cluster's.
INPUT_BUDGET = {}
# What stage 00 seeds into compute.mem: on a venue with a ceiling its accepted value, elsewhere
# the value the templates carried before 0293, byte for byte.
_CLUSTER_MEM = {'atacseq_bulk': '64G', 'chipseq_bulk': '64G', 'cutandrun': '64G',
                'methylseq': '96G', 'rnaseq_bulk': '64G', 'scrnaseq': '96G', 'spatialvi': '32G'}
SEEDED_MEM = {(venue, aid): ACCEPTED_MEM.get(venue, _CLUSTER_MEM[aid])
              for venue in VENUES for aid in ASSAY_IDS}


def fail(code, detail):
    return {'check': code, 'detail': detail}


def routes():
    with POLICY.open(encoding='utf-8', newline='') as handle:
        return {row['data_class']: row for row in csv.DictReader(handle, delimiter='\t')}


def data_line(data_class, purpose):
    """The one line people read for a registration: `Data: public, test` (0321)."""
    use = USE_OF_PURPOSE.get(purpose) or 'legacy %s' % purpose
    if data_class == 'public':
        return 'Data: public, %s' % use
    return 'Data: restricted (%s), %s' % (data_class, use)


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


def seeded_mem(venue, assay_id):
    return SEEDED_MEM.get((venue, assay_id))


def lowered_mem(venue, assay_id, requested):
    """The value to lower `requested` to on this venue, or None; never above `requested`.

    Only a venue with a ceiling lowers, and only a request above it, or one the submit could not
    parse; the value is the venue's seed, which a test holds at or below the ceiling.
    """
    if venue not in MEM_CEILING or requested is None:
        return None
    try:
        if memory_bytes(requested) <= MEM_CEILING[venue]:
            return None
    except ValueError:
        pass
    return seeded_mem(venue, assay_id)


def check(dataset_row, venue, purpose, mem_bytes, fastq_inputs, input_bytes=None):
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
            failures.append(fail("venue_not_permitted", 'venue local memory rule: above 8 GiB; '
                                 'this venue accepts up to %s' % ACCEPTED_MEM['local']))
        if fastq_inputs and not fixture:
            failures.append(fail("venue_not_permitted", 'venue local FASTQ rule: exactly public/fixture required'))
    for path in fastq_inputs:
        if not Path(path).is_file():
            failures.append(fail("input_missing", 'listed FASTQ input does not exist'))
    budget = INPUT_BUDGET.get(venue)
    if budget is not None and input_bytes is not None and input_bytes > budget:
        failures.append(fail("venue_too_small", "inputs %d bytes (%.1f GiB) exceed venue %s's budget "
                             "of %d bytes (%.1f GiB); this dataset needs a bigger venue (slurm)"
                             % (input_bytes, input_bytes / 1024.0 ** 3, venue, budget,
                                budget / 1024.0 ** 3)))
    return failures
