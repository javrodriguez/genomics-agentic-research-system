#!/usr/bin/env python3
"""Render a claims export, manifest and shipped template; Python 3.6 / stdlib.

No path in either JSON input is opened. Database mode uses row 5's container
psql transport and reads the password inside the container, never in Python.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import string
import sys
import tempfile
import unicodedata

SECTIONS = (
    ('question', 'question'),
    ('data and classification', 'data'),
    ('methods (workflow versions, parameters, reference release)', 'methods'),
    ('QC summary', 'qc'),
    ('claims table (type, both confidence groups, evidence links)', 'claims'),
    ('limitations adjacent to the affected claims', 'limitations'),
    ('manifest reference and "reproduce this analysis" (`commands.sh`)', 'manifest'),
    ('cost', 'cost'),
)
# Twenty observation verbs, including regular and irregular inflections.
OBSERVATION_VERBS = (
    'show|shows|showed|shown|showing',
    'demonstrate|demonstrates|demonstrated|demonstrating',
    'prove|proves|proved|proven|proving',
    'confirm|confirms|confirmed|confirming',
    'establish|establishes|established|establishing',
    'reveal|reveals|revealed|revealing',
    'observe|observes|observed|observing',
    'detect|detects|detected|detecting',
    'measure|measures|measured|measuring',
    'find|finds|found|finding',
    'identify|identifies|identified|identifying',
    'verify|verifies|verified|verifying',
    'validate|validates|validated|validating',
    'determine|determines|determined|determining',
    'record|records|recorded|recording',
    'document|documents|documented|documenting',
    'quantify|quantifies|quantified|quantifying',
    'indicate|indicates|indicated|indicating',
    'exhibit|exhibits|exhibited|exhibiting',
    'display|displays|displayed|displaying',
)
# Digits and underscores delimit a readable verb; letters preserve inflection boundaries.
OBSERVATION = re.compile(r'(?<![^\W\d_])(?:' + '|'.join(OBSERVATION_VERBS) + r')(?![^\W\d_])', re.I)


def unknown(owner):
    return 'UNKNOWN (owned by %s)' % owner


def display(value, owner):
    if value is None or value == [] or (isinstance(value, str) and not value.strip()):
        return unknown(owner)
    if isinstance(value, (dict, list)):
        value = json.dumps(value, sort_keys=True, ensure_ascii=True)
    # Input text cannot introduce headings, table rows or executable HTML.
    value = html.escape(str(value), quote=False)
    value = re.sub(r'([\\`*_{}\[\]()#+.!|>~$-])', r'\\\1', value)
    return value.replace('\r', ' ').replace('\n', ' ')


def validate_sections(text):
    headings = re.findall(r'^## (.+)$', text, re.M)
    for heading, _ in SECTIONS:
        if headings.count(heading) != 1:
            raise ValueError('missing or duplicate section: ' + heading)
    if headings != [s[0] for s in SECTIONS]:
        raise ValueError('section order: ' + ', '.join(headings))


def lexical(text, separators=False):
    # Preserve actual word boundaries. Invisible characters can split either a
    # word or two words: the verb gate checks both interpretations.
    result = []
    for c in unicodedata.normalize('NFKD', text):
        if c.isspace():
            result.append(' ')
        elif unicodedata.category(c)[0] in ('C', 'M') or c in ('\u115f', '\u1160'):
            result.append(' ' if separators else '')
        else:
            result.append(c)
    return ''.join(result)


GROUP_KEYS = {
    'bio_support': {'statistical_support', 'replication', 'orthogonal_assay', 'effect_size', 'literature'},
    'process_risk': {'data_quality', 'confounding_risk', 'provenance_completeness', 'qc_disposition', 'limitation'},
}


def reserved_keys(value):
    if isinstance(value, dict):
        return any(k.lower() in ('confidence', 'score') or reserved_keys(v) for k, v in value.items())
    if isinstance(value, list):
        return any(reserved_keys(v) for v in value)
    return False


def free_text(value):
    """Yield every string rendered in a cell, including nested JSON keys."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from free_text(item)
    elif isinstance(value, list):
        for item in value:
            yield from free_text(item)


def render(snapshot, manifest, template):
    if not isinstance(snapshot, dict) or not isinstance(manifest, dict):
        raise ValueError('snapshot and manifest must be JSON objects')
    if snapshot.get('run') is not None and not isinstance(snapshot['run'], dict):
        raise ValueError('run must be a JSON object')
    if snapshot.get('claims') is not None and not isinstance(snapshot['claims'], list):
        raise ValueError('claims must be a JSON array')
    validate_sections(template)
    for heading, key in SECTIONS:
        section = template.split('## ' + heading + '\n', 1)[1].split('\n## ', 1)[0]
        fields = [(field, spec, conversion) for _, field, spec, conversion in
                  string.Formatter().parse(section) if field is not None]
        if fields != [(key, '', None)]:
            raise ValueError('missing section source: ' + heading)
    run = snapshot.get('run') or {}
    claims = snapshot.get('claims') or []
    for claim in claims:
        if not isinstance(claim, dict):
            raise ValueError('claim must be a JSON object')
        cid = claim.get('id')
        if not isinstance(cid, int) or isinstance(cid, bool) or not -(2 ** 63) <= cid < 2 ** 63:
            raise ValueError('invalid claim id')
        if claim.get('type') not in ('OBSERVATION', 'INTERPRETATION', 'HYPOTHESIS', 'RECOMMENDATION'):
            raise ValueError('invalid claim type')
        if claim.get('text') is not None and not isinstance(claim['text'], str):
            raise ValueError('claim text must be a string')
        if not isinstance(claim.get('evidence'), list) or not claim['evidence']:
            raise ValueError('claim %s has no evidence links' % cid)
        for group in ('bio_support', 'process_risk'):
            if group in claim and not isinstance(claim[group], dict):
                raise ValueError(group + ' must be a JSON object')
            if group in claim and (set(claim[group]) - GROUP_KEYS[group] or reserved_keys(claim[group])):
                raise ValueError('invalid ' + group + ' keys')
    claims = sorted(claims, key=lambda c: c['id'])
    releases = set(c.get('reference_release') for c in claims)
    rows = ['| id | type | claim | biological support | process risk | evidence links | reference |',
            '|---|---|---|---|---|---|---|']
    qc, methods = [], []
    for claim in claims:
        cid = claim['id']
        text = claim.get('text') or ''
        risk = claim.get('process_risk') or {}
        disposition = risk.get('qc_disposition')
        if disposition is not None and disposition not in ('HALT', 'DEGRADE', 'WARN'):
            raise ValueError('invalid QC disposition in claim %s' % cid)
        limitation = risk.get('limitation')
        if disposition == 'DEGRADE' and (not isinstance(limitation, str) or not any(c.isalnum() for c in lexical(limitation))):
            raise ValueError('DEGRADE requires limitation in claim %s' % cid)
        label = 'claim ' + display(cid, 'row 7: claim writer')
        values = [cid, claim.get('type'), text, claim.get('bio_support'), risk,
                  claim.get('evidence'), claim.get('reference_release')]
        if claim.get('type') == 'HYPOTHESIS' and any(
                OBSERVATION.search(lexical(value, mode))
                for value in free_text(values + [claim.get('workflow_version')]) for mode in (False, True)):
            raise ValueError('HYPOTHESIS observation verb in claim %s' % cid)
        cells = [display(v, 'row 7: claim writer') for v in values]
        if len(releases) > 1:
            cells[-1] += ' **REFERENCE RELEASE MISMATCH**'
        rows.append('| ' + ' | '.join(cells) + ' |')
        # A separate table row immediately after its claim keeps the qualification adjacent.
        rows.append('| | | Limitation: ' + display(limitation, 'row 7: claim writer') + ' | | | | |')
        qc.append('- ' + label + ': ' + display(disposition, '§14 QC dispositions'))
        methods.append('- ' + label + ': workflow_version=' +
                       display(claim.get('workflow_version'), 'row 7: claim writer') +
                       '; reference_release=' + display(claim.get('reference_release'), 'row 7: claim writer'))
    values = {
        'question': display(run.get('question'), 'row 7: run registrar'),
        'data': unknown('row 6: data_class, venue, purpose'),
        'methods': 'pipeline_commit: ' + display(manifest.get('pipeline_commit'), 'row 6: manifest producer') +
                   '\n\nparams: ' + display(manifest.get('params'), 'row 6: manifest producer') + '\n\n' +
                   ('\n'.join(methods) or unknown('row 7: claim writer')) +
                   '\n\nGenome hashes, model/prompt/routing: ' + unknown('row 6'),
        'qc': '\n'.join(qc) or unknown('§14 QC dispositions'),
        'claims': '\n'.join(rows) if claims else unknown('row 7: claim writer'),
        'limitations': ('Limitations from process_risk.limitation appear directly under each affected claim above.'
                        if any(c.get('process_risk', {}).get('limitation') for c in claims)
                        else unknown('row 7: claim writer')),
        'manifest': 'Manifest path: ' + display(run.get('manifest_path'), 'row 7: run registrar') +
                    '\n\nManifest sha256: ' + display(run.get('manifest_sha256'), 'row 7: run registrar') +
                    '\n\nReproduce this analysis (`commands.sh`): ' + unknown('row 6'),
        'cost': unknown('row 11: docs/ledger.csv has no per-run cost source'),
    }
    result = template.format(**values)
    validate_sections(result)
    return result


def database_snapshot(run_id):
    if not re.fullmatch(r'[0-9]+', run_id):
        raise ValueError('--from-db requires a numeric run id')
    e = os.environ
    engine = e.get('CONTAINER_ENGINE', 'docker')
    if engine not in ('docker', 'podman'):
        raise ValueError('invalid container engine')
    project = e.get('COMPOSE_PROJECT', '')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]*', project):
        raise ValueError('COMPOSE_PROJECT is required')
    # Same argv and static secret-reading shell as Config.client / Config.sql in row05.py.
    compose = Path(__file__).resolve().parents[3] / 'infra/compose/postgres.compose.yml'
    argv = [engine, 'compose', '-f', str(compose), '-p', project, 'exec', '-T', 'db',
            'sh', '-c', 'export PGPASSWORD="$(cat /run/secrets/pg_password)"; '
            'export PGCONNECT_TIMEOUT=5; exec "$@"', 'row07', 'psql',
            '-h', e['PGHOST'], '-p', e['PGPORT'], '-U', e['PGUSER'], '-d', e['PGDATABASE'],
            '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=1', '-c',
            'SELECT claims.claims_export(%s);' % int(run_id)]
    p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    if p.returncode:
        raise ValueError('container psql claims_export failed (exit %s)' % p.returncode)
    return json.loads(p.stdout.decode('utf-8'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--snapshot', type=Path)
    source.add_argument('--from-db')
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    temporary = None
    try:
        snapshot = (json.loads(args.snapshot.read_text(encoding='utf-8')) if args.snapshot else
                    database_snapshot(args.from_db))
        manifest_bytes = args.manifest.read_bytes()
        manifest = json.loads(manifest_bytes.decode('utf-8'))
        if not isinstance(snapshot, dict) or not isinstance(manifest, dict):
            raise ValueError('snapshot and manifest must be JSON objects')
        if snapshot.get('run') is not None and not isinstance(snapshot['run'], dict):
            raise ValueError('run must be a JSON object')
        digest = (snapshot.get('run') or {}).get('manifest_sha256')
        if digest is not None and digest != '':
            if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
                raise ValueError('invalid manifest sha256')
            if digest != hashlib.sha256(manifest_bytes).hexdigest():
                raise ValueError('manifest sha256 mismatch')
        template = Path(__file__).resolve().with_name('report_template.md').read_text(encoding='utf-8')
        result = render(snapshot, manifest, template)
        with tempfile.NamedTemporaryFile(mode='wb', prefix='.report-', dir=str(args.out.parent),
                                         delete=False) as fh:
            temporary = fh.name
            fh.write(result.encode('utf-8'))
        os.replace(temporary, str(args.out))
        temporary = None
    except (ValueError, KeyError, TypeError, IndexError, RecursionError, OSError, subprocess.TimeoutExpired) as exc:
        print('report refused: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        if temporary:
            os.unlink(temporary)
    return 0


if __name__ == '__main__':
    sys.exit(main())
