#!/usr/bin/env python3
"""Report what every registered dataset row means after S00-class (decision 0321). Writes nothing.

Under choice 1c no value already in a row changes meaning, so the migration is the identity: no
row is rewritten, and there is no live mode. The dry run walks `projects/*/00_data/dataset.tsv`
and prints, per row, its class, its purpose and what it now means, in the words people read
(`venue_policy.data_line`): a purpose no route of its class serves is marked `no route`, and the
legacy `pilot_internal` is marked as needing its agreement on the cluster. Every
`pilot_external` or `commercial` row, every row whose purpose is none of the five finalize can
write (an unknown purpose, never called legacy), and every row it cannot read, is listed for a
person.

    python3 _system/migrate_data_class.py --dry-run [--workspace <gars/>]

Exit codes: 0 reported; 2 refused (no --dry-run: there is no live mode). Python 3.6, stdlib.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True     # writes nothing, not even a bytecode cache
sys.path.insert(0, str(Path(__file__).resolve().parent))
import venue_policy as policy  # noqa: E402

EXIT_OK, EXIT_REFUSED = 0, 2
FOR_A_PERSON = ('pilot_external', 'commercial')


def emit(result, code):
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return code


def served(data_class):
    """The purposes some route of this class serves, from `_references/data_policy.tsv`."""
    try:
        return {token.split(':', 1)[1] for token in
                policy.permissions(policy.routes()[data_class]['permitted_backends'])}
    except (KeyError, ValueError):
        return set()


def meaning(data_class, purpose):
    if purpose not in policy.PURPOSES:            # a hand edit: the class words alone
        words = policy.data_line(data_class, 'fixture')[len('Data: '):].rsplit(', ', 1)[0]
        return words + ', unknown purpose %s, no route' % purpose
    words = policy.data_line(data_class, purpose)[len('Data: '):]
    if purpose not in served(data_class):
        return words + ', no route'
    if purpose == 'pilot_internal':
        return words + ', cluster needs its agreement'
    return words


def read_row(path):
    try:
        with path.open(encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle, delimiter='\t'))
    except (OSError, ValueError, UnicodeError):
        return None
    if len(rows) != 1 or not rows[0].get('data_class') or not rows[0].get('purpose'):
        return None
    return rows[0]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n', 1)[0])
    parser.add_argument('--workspace', default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument('--dry-run', action='store_true', help='report; the only mode')
    args = parser.parse_args(argv)
    result = {'command': 'migrate_data_class', 'dry_run': args.dry_run, 'written': []}
    if not args.dry_run:
        result['error'] = ('there is no live mode: under decision 0321 no row is rewritten; '
                           'run with --dry-run to see what each row means')
        return emit(result, EXIT_REFUSED)
    rows, person = [], []
    for path in sorted(Path(args.workspace).glob('projects/*/00_data/dataset.tsv')):
        project = path.parents[1].name
        row = read_row(path)
        if row is None:
            entry = {'project': project, 'data_class': None, 'purpose': None,
                     'means': 'unreadable'}
        else:
            entry = {'project': project, 'data_class': row['data_class'],
                     'purpose': row['purpose'],
                     'means': meaning(row['data_class'], row['purpose'])}
        rows.append(entry)
        if row is None or row['purpose'] in FOR_A_PERSON or row['purpose'] not in policy.PURPOSES:
            person.append(entry)
    result.update(rows=rows, for_a_person=person)
    return emit(result, EXIT_OK)


if __name__ == '__main__':
    sys.exit(main())
