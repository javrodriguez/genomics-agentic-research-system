#!/usr/bin/env python3
"""R-116/R-170: derive the frozen §17 rows and refuse incomplete release evidence.

Only existing evidence formats are read. Missing producers stay unmeasured; no
operator-supplied current-value or PASS override is accepted. Python 3.6 stdlib.
"""
import argparse
import datetime
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import sys

REPO = Path(__file__).resolve().parents[1]
SPEC = 'docs/specs/GARS_Unified_Master_Guideline_v1.0.1_FINAL.md'
OUTPUT = 'docs/implementation/dod_current.md'
RESTORE = 'docs/ops/restore-log.md'
RESULT_HEADER = '| Date | RPO_h | RTO_min | Result |'
PROVENANCE_HEADER = '| Date | Venue | Source | Target | Data | Seal | Record |'
# The lane's ruling Q1 (0105): a development seal qualifies the §17 cell; the
# README's public row still needs external_human_seal.
ACCEPTED_SEALS = ('independent_context', 'external_human_seal')
DECISIONS = 'docs/decisions'
# A zero-padded UTC stamp, so string order is time order (0105, round 2).
STAMP_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z'
# Claims stronger than 0054's drill; the cited record must quote the whole provenance row
# for any of them, because a bare token also matches a negation (0105, round 2).
BOUND_CLAIMS = ('external_human_seal', 'primary', 'real')
# Any date or date-time in the log's UTC form, padded or not: routing and the stamp-token
# refusal use these, so no evidence-shaped line reaches the skip (0105, round 3).
DATE_LED = r'^\d{1,4}-\d{1,2}-\d{1,2}'
STAMP_TOKEN = r'\d{1,4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{1,2}:\d{1,2}'


def clauses(root):
    text = (root / SPEC).read_text(encoding='utf-8')
    section = text.split('\n## 17. ', 1)[1].split('\n## 18. ', 1)[0]
    rows = []
    for line in section.splitlines():
        if line.startswith('| ') and not line.startswith('| Clause |'):
            # A literal pipe in a code span is not a table delimiter here.
            cells = [cell.strip() for cell in line.strip('|').split(' | ')]
            if len(cells) != 3:
                raise ValueError('unreadable specification table')
            rows.append(cells)
    if len(rows) != 13:
        raise ValueError('expected all thirteen §17 clauses')
    return rows


def restore_cells(line, count):
    stripped = line.rstrip()
    if not stripped.startswith('|') or not stripped.endswith('|') or len(stripped) < 2:
        raise ValueError('malformed restore table row')
    cells = [cell.strip() for cell in stripped[1:-1].split('|')]
    if len(cells) != count:
        raise ValueError('malformed restore table row')
    try:
        if not re.match(STAMP_PATTERN, cells[0]):
            raise ValueError('unpadded stamp')
        datetime.datetime.strptime(cells[0], '%Y-%m-%dT%H:%M:%SZ')
    except ValueError:
        raise ValueError('malformed restore table row')
    return cells


def restore_result_record(stamp, rpo_text, rto_text, status):
    """One result, CSV or table: (date, stamp, RPO, RTO, status, raw RPO, raw RTO)."""
    if not re.match(STAMP_PATTERN, stamp):
        raise ValueError('invalid restore output')
    when = datetime.datetime.strptime(stamp, '%Y-%m-%dT%H:%M:%SZ').date()
    rpo, rto = Decimal(rpo_text), Decimal(rto_text)
    if not all(x.is_finite() and x >= 0 for x in (rpo, rto)) or status not in ('PASS', 'FAIL'):
        raise ValueError('invalid restore output')
    return (when, stamp, rpo, rto, status, rpo_text, rto_text)


def restore_records(text):
    """Read every result shape in the restore log, in line order, and the provenance table.

    Legacy `date, RPO_h, RTO_min, PASS|FAIL` lines, rows of the RESULT_HEADER table and rows
    of the PROVENANCE_HEADER table. A date-led table row outside a known table, or any
    malformed row inside one, raises: the log is never skipped silently (0105). An indented
    date-led line or table row raises too, since markdown still renders it (0105, round 2).
    So does any other line holding a stamp-shaped token, padded or not: list items, block
    quotes, unpadded dates (0105, round 3). Prose without such a token is ignored.
    """
    records, provenance = [], {}
    block = None
    separator = False
    for line in text.splitlines():
        if block is not None and line.startswith('|'):
            if separator:
                if line.rstrip() != '|---' * (4 if block == 'result' else 7) + '|':
                    raise ValueError('malformed restore table row')
                separator = False
                continue
            if block == 'result':
                stamp, rpo, rto, status = restore_cells(line, 4)
                try:
                    records.append(restore_result_record(stamp, rpo, rto, status))
                except (ValueError, InvalidOperation):
                    raise ValueError('malformed restore table row')
                continue
            stamp, venue, source, target, data, seal, record = restore_cells(line, 7)
            if (venue != 'node1' or source != 'scheduled-offmachine' or
                    target not in ('recovery-db', 'primary') or data not in ('synthetic', 'real') or
                    seal not in ('independent_context', 'external_human_seal', 'none') or
                    not re.match(r'^\d{4}$', record)):
                raise ValueError('restore provenance outside its closed vocabulary')
            if stamp in provenance:
                raise ValueError('duplicate restore provenance row')
            provenance[stamp] = (venue, source, target, data, seal, record)
            continue
        block, separator = None, False
        if line == RESULT_HEADER or line == PROVENANCE_HEADER:
            block = 'result' if line == RESULT_HEADER else 'provenance'
            separator = True
            continue
        bare = line.lstrip()
        if re.match(DATE_LED, bare):
            if bare != line:
                raise ValueError('indented restore line')
            fields = [value.strip() for value in line.split(',')]
            if len(fields) != 4:
                raise ValueError('malformed restore output')
            records.append(restore_result_record(*fields))
        elif bare.startswith('|') and re.match(DATE_LED, bare[1:].strip()):
            raise ValueError('restore table row outside a known table')
        elif re.search(STAMP_TOKEN, line):
            raise ValueError('restore stamp outside a result or provenance row')
    stamps = set(row[1] for row in records)
    if any(stamp not in stamps for stamp in provenance):
        raise ValueError('restore provenance row names no result')
    return records, provenance


def restore_qualifies(root, record, provenance):
    """(value, meets) for a result with a provenance row, or None without one.

    The cited record must be standing, touch the restore log, and carry the drill's own
    CSV evidence line and the seal token, so no other record can vouch for the drill. A
    claim in BOUND_CLAIMS also needs the record to quote the whole provenance row.
    """
    when, stamp, rpo, rto, status, rpo_text, rto_text = record
    if stamp not in provenance:
        return None
    venue, source, target, data, seal, number = provenance[stamp]
    failed = None
    if status != 'PASS':
        failed = 'status ' + status
    elif rpo > 24:
        failed = 'RPO above 24 h'
    elif rto > 60:
        failed = 'RTO above 60 min'
    elif venue != 'node1' or source != 'scheduled-offmachine':
        failed = 'not Node 1 from the scheduled off-machine copy'
    elif seal not in ACCEPTED_SEALS:
        failed = 'seal %s not accepted' % seal
    else:
        quoted = None
        if any(claim in BOUND_CLAIMS for claim in (target, data, seal)):
            quoted = '| %s |' % ' | '.join((stamp,) + provenance[stamp])
        failed = restore_record_fails(root, number, '%s, %s, %s, %s' % (
            stamp, rpo_text, rto_text, status), seal, quoted)
    head = '%s; RPO %s h; RTO %s min; %s; ' % (stamp, rpo_text, rto_text, status)
    if failed is not None:
        return head + 'not qualifying: ' + failed, False
    value = head + ('Node 1 from the scheduled off-machine copy; target %s; %s data; seal %s (%s)'
                    % (target, data, seal, number))
    if seal != 'external_human_seal':
        value += '; public seal pending (external_human_seal)'
    return value, True


def restore_record_fails(root, number, evidence, seal, quoted=None):
    paths = sorted((root / DECISIONS).glob(number + '-*.md'))
    if len(paths) != 1:
        return 'record %s not found exactly once' % number
    lines = paths[0].read_text(encoding='utf-8').splitlines()
    if not lines or lines[0] != '---' or '---' not in lines[1:]:
        return 'record %s has no front matter' % number
    close = lines.index('---', 1)
    status, touches, key = None, [], None
    for line in lines[1:close]:
        item = re.match(r'^\s+-\s+(.*)$', line)
        if item and key == 'touches':
            touches.append(item.group(1).strip())
            continue
        field = re.match(r'^([A-Za-z_]+):\s*(.*)$', line)
        if field:
            key = field.group(1)
            if key == 'status':
                status = field.group(2).strip()
    if status != 'standing':
        return 'record %s not standing' % number
    if RESTORE not in touches:
        return 'record %s does not touch %s' % (number, RESTORE)
    body = '\n'.join(lines[close + 1:])
    if evidence not in body:
        return 'record %s lacks the evidence line' % number
    if seal not in body:
        return 'record %s lacks the seal %s' % (number, seal)
    if quoted is not None and quoted not in body:
        return 'record %s does not quote the provenance row' % number
    return None


def restore_measurement(root):
    """Consume row 5's restore log: CSV lines and the result table, including FAIL records.

    The latest result qualifies only with a provenance-table row naming Node 1, the
    scheduled off-machine copy and an accepted seal, citing a standing decision record
    that touches the log and quotes the drill's CSV evidence line and seal (0105); an
    external_human_seal, primary target or real data also needs the record to quote the
    whole provenance row (0105, round 2).
    Without that row the missing venue/canary evidence stays unmeasured. Age is left to
    release_failures, so the generated cell stays byte-stable.
    """
    path = root / RESTORE
    if not path.exists():
        return 'unmeasured', None, False
    records, provenance = restore_records(path.read_text(encoding='utf-8'))
    if not records:
        return 'unmeasured', None, False
    # Row 5 appends terminal corrections with the original invocation timestamp.
    # Reverse append order makes the final row win a tie without changing recency.
    record = max(reversed(records), key=lambda row: row[1])
    when, stamp, rpo, rto, status = record[:5]
    qualified = restore_qualifies(root, record, provenance)
    if qualified is not None:
        return qualified[0], when, qualified[1]
    value = '%s; RPO %s h; RTO %s min; %s; venue/canary unmeasured' % (stamp, rpo, rto, status)
    return value, when, False



def reviewer_measurement(root):
    """Row 9 code evidence cannot establish the science half or public sealing."""
    paths = list((root / 'evals/review-faults/runs').glob('*.json'))
    if not paths:
        return 'unmeasured', None, False
    records = [(json.loads(p.read_text(encoding='utf-8')), p) for p in paths]
    record, path = max(records, key=lambda pair: (pair[0]['created_at'], pair[1].name))
    when = datetime.datetime.strptime(record['created_at'], '%Y%m%dT%H%M%SZ').date()
    overall = record['overall']
    slots = record['sealed_slots']
    types = sorted({v for values in slots.values() for v in values})
    external = (set(slots) == {'race', 'hardcoded-secret', 'weakened-criterion'} and
                all(values == ['external_human_seal'] for values in slots.values()))
    public = ('unmeasured (public: needs external_human_seal); ' if not external else
              'public code seals external_human_seal; ')
    # 0074: every figure comes from the run file's own fields. The scorer's overall
    # false-alarm denominator is every clean case; the per-class denominator counts only
    # valid clean reviews, so the cell prints that one and the clean cases left without a
    # valid review, then the INVALID count and the scorer's own threshold verdict.
    clean_total = overall['false_alarms']['d']
    clean_valid = max((rates['false_alarms']['d'] for rates in record['per_class'].values()), default=0)
    value = (public + 'development, code: %s/%s catch, %s/%s false alarms in valid clean reviews '
             '(%s of %s clean cases without a valid review), invalid %s/%s, thresholds %s, seals %s, '
             'first-run-at-sha %s (%s); science: unmeasured') % (
                 overall['caught']['n'], overall['caught']['d'],
                 overall['false_alarms']['n'], clean_valid, clean_total - clean_valid, clean_total,
                 overall['invalid']['n'], overall['invalid']['d'],
                 'met' if record['thresholds_met'] else 'not met',
                 ','.join(types) or 'unsealed',
                 str(record['first_run_at_sha']).lower(), path.relative_to(root).as_posix())
    # This clause includes science; even external code seals cannot complete it.
    return value, when, False


def measurements(root, rows):
    values = {row[0]: ('unmeasured', None, False) for row in rows}
    values['restore drill'] = restore_measurement(root)
    values['reviewer catch rate (code; science)'] = reviewer_measurement(root)
    # Existing benchmark runs measure tasks, not §17's sealed design catalogue,
    # reviewer sets, manifests, pilots or semantic mutants. Historical report
    # prose and producer-visible controls cannot fill those acceptance cells.
    return values


def render(rows, values):
    lines = ['# Definition of done — current evidence', '',
             'GENERATED by `python3 scripts/release_check.py`; do not edit cells.',
             'Clause, test and threshold are copied from frozen §17. Missing qualifying evidence is unmeasured.',
             '', '| Clause | Test | Threshold | Current value |', '|---|---|---|---|']
    for clause, test, threshold in rows:
        lines.append('| %s | %s | %s | %s |' % (clause, test, threshold, values[clause][0]))
    return '\n'.join(lines) + '\n'


def release_failures(values, today):
    errors = []
    for clause, (value, when, meets) in values.items():
        if when is None or 'unmeasured' in value:
            errors.append(clause + ': unmeasured')
        if not meets:
            errors.append(clause + ': threshold not established')
        if when is not None:
            age = (today - when).days
            if age > 14:
                errors.append(clause + ': older than 14 days')
            if age < 0:
                errors.append(clause + ': future evidence date')
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='detect missing or hand-edited generated cells')
    parser.add_argument('--tag', action='store_true', help='release eligibility gate; does not create a Git tag')
    args = parser.parse_args(argv)
    try:
        rows = clauses(REPO)
        values = measurements(REPO, rows)
        expected = render(rows, values).encode('utf-8')
        output = REPO / OUTPUT
        # A tag check never silently repairs a hand-edited cell.
        if args.check or args.tag:
            if not output.is_file() or output.read_bytes() != expected:
                raise ValueError('DoD cells differ from regeneration (missing or hand-edited)')
            print('DoD cells verified: %d/%d byte-stable' % (len(rows), len(rows)))
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(expected)
            print('DoD cells regenerated: %d/%d' % (len(rows), len(rows)))
        if args.tag:
            errors = release_failures(values, datetime.datetime.utcnow().date())
            if errors:
                for error in errors:
                    print('release tag: REFUSED (%s)' % error)
                return 1
            print('release tag: eligible')
        return 0
    except (OSError, ValueError, IndexError, InvalidOperation) as exc:
        print('release check: REFUSED (%s)' % exc, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
