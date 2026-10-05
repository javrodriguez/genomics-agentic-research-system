#!/usr/bin/env python3
"""Compare a re-run's outputs with a GARS reproduction package, member by member (stdlib only).

  python3 compare.py --package <package dir> --against <re-run dir> [--table-out <dir>]

The package's own comparison modes, declared here and not GARS's rerun_check.py (decision 0283):
  exact     the member's sha256 equals the one the run recorded;
  presence  the member exists and is not empty; counted as P, never as a match.
A member's mode is read from outputs/outputs.tsv, which the package's render took from
outputs/package-tolerances.json; every member with no entry is exact.

Every recorded output lands in exactly one count (M + K + P + F = N):
  M  every member is exact and matches;
  K  every member matches under a mode other than presence, and at least one is not exact;
  P  at least one member is presence, and no member fails;
  F  at least one member fails, or the re-run holds a file the run did not record there.
A member path two nested outputs share is compared once and counted once in n.

Exit 0 when M + K = N, 2 when F > 0, 3 when F = 0 and P > 0, 1 when the package or the
re-run folder cannot be read. Standard library only, Python 3.6 or later, no network.
"""
import argparse
import csv
import hashlib
import io
import os
import sys

sys.dont_write_bytecode = True   # never leave a __pycache__ folder inside the package
FRAME = ('of {N} outputs ({n} files), {M} matched exactly, {K} within the stated tolerance, '
         '{P} present but not byte-comparable, {F} differ (causes in PROVENANCE.md)')
RESULTS_PREFIX = 'run/results/'
OUTPUT_COLUMNS = ('stage', 'output_type', 'output_path', 'members', 'exact', 'presence', 'other',
                  'failed', 'extra', 'result')
MEMBER_COLUMNS = ('stage', 'path', 'mode', 'recorded_sha256', 'rerun_sha256', 'result')


class Unreadable(Exception):
    """The package or the re-run folder cannot be compared."""


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def regular(path):
    return os.path.isfile(path) and not os.path.islink(path)


def mode_exact(path, row):
    if not regular(path):
        return False, 'missing', ''
    actual = sha256(path)
    return actual == row['recorded_sha256'], 'match' if actual == row['recorded_sha256'] else 'differs', actual


def mode_presence(path, row):
    if not regular(path):
        return False, 'missing', ''
    if os.path.getsize(path) == 0:
        return False, 'empty', ''
    return True, 'present', ''


# The modes this package declares. A mode is added only with a cause read from the bytes (0283).
MODES = {'exact': mode_exact, 'presence': mode_presence}


def read_table(path):
    try:
        with io.open(path, encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle, delimiter='\t'))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise Unreadable('cannot read %s (%s)' % (path, type(exc).__name__))
    return rows


def member_path(row):
    return row['output_path'] if row['member'] == '.' else row['output_path'] + '/' + row['member']


def rerun_location(rerun, stage, path):
    """Where a re-run writes a recorded output: run/results/<x> of a stage is results/<stage>/<x>."""
    if not path.startswith(RESULTS_PREFIX) or '..' in path.split('/') or os.path.isabs(path):
        raise Unreadable('recorded output %s of %s is not under %s' % (path, stage, RESULTS_PREFIX))
    return os.path.join(rerun, 'results', stage, *path[len(RESULTS_PREFIX):].split('/'))


def outputs_of(rows):
    """The recorded outputs, in table order, each with its member rows."""
    order, groups = [], {}
    for row in rows:
        key = (row['stage'], row['output_type'], row['output_path'])
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(row)
    return [(key, groups[key]) for key in order]


def extras(rerun, stage, output_path, members):
    """Regular files a re-run holds inside a recorded directory output that the run did not record."""
    top = rerun_location(rerun, stage, output_path)
    if not os.path.isdir(top) or os.path.islink(top):
        return []
    recorded = set(row['member'] for row in members)
    found = []
    for folder, dirs, files in os.walk(top, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(folder, d)))
        for name in sorted(files):
            full = os.path.join(folder, name)
            if os.path.islink(full):
                continue
            relative = os.path.relpath(full, top).replace(os.sep, '/')
            if relative not in recorded:
                found.append(relative)
    return sorted(found)


def package_rows(package):
    rows = read_table(os.path.join(package, 'outputs', 'outputs.tsv'))
    if not rows:
        raise Unreadable('outputs/outputs.tsv lists no output')
    seen = {}
    for row in rows:
        if row['mode'] not in MODES:
            raise Unreadable('outputs/outputs.tsv names an undeclared mode %r' % row['mode'])
        key = (row['stage'], member_path(row))
        if key in seen and (seen[key]['mode'], seen[key]['recorded_sha256']) != \
                (row['mode'], row['recorded_sha256']):
            raise Unreadable('member %s of %s is listed twice with different records' % (key[1], key[0]))
        seen[key] = row
    return rows


def compare(package, rerun):
    if not os.path.isdir(rerun):
        raise Unreadable('the re-run folder %s does not exist' % rerun)
    rows = package_rows(package)
    members, extra_paths = {}, {}
    for row in rows:
        key = (row['stage'], member_path(row))
        if key not in members:
            path = rerun_location(rerun, row['stage'], key[1])
            ok, result, actual = MODES[row['mode']](path, row)
            members[key] = {'row': row, 'ok': ok, 'result': result, 'rerun_sha256': actual}
    for (stage, kind, output_path), group in outputs_of(rows):
        if group[0]['member'] != '.':
            extra_paths[(stage, output_path)] = extras(rerun, stage, output_path, group)
    return rollup(rows, members, extra_paths)


def rollup(rows, members, extra_paths):
    """Every recorded output in exactly one of M, K, P, F (decision 0283), from its members' results;
    `members` maps (stage, member path) to {'row', 'ok', 'result', 'rerun_sha256'}."""
    outputs = []
    counts = {'N': 0, 'n': len(members), 'M': 0, 'K': 0, 'P': 0, 'F': 0}
    for (stage, kind, output_path), group in outputs_of(rows):
        results = [members[(stage, member_path(row))] for row in group]
        extra = extra_paths.get((stage, output_path)) or []
        failed = sum(1 for r in results if not r['ok'])
        presence = sum(1 for r in results if r['row']['mode'] == 'presence')
        exact = sum(1 for r in results if r['row']['mode'] == 'exact')
        if failed or extra:
            verdict = 'F'
        elif presence:
            verdict = 'P'
        elif exact == len(results):
            verdict = 'M'
        else:
            verdict = 'K'
        counts['N'] += 1
        counts[verdict] += 1
        outputs.append({'stage': stage, 'output_type': kind, 'output_path': output_path,
                        'members': len(results), 'exact': exact, 'presence': presence,
                        'other': len(results) - exact - presence, 'failed': failed,
                        'extra': len(extra), 'result': verdict, 'extra_paths': extra})
    member_rows = [{'stage': key[0], 'path': key[1], 'mode': value['row']['mode'],
                    'recorded_sha256': value['row']['recorded_sha256'],
                    'rerun_sha256': value['rerun_sha256'] or '-', 'result': value['result']}
                   for key, value in sorted(members.items())]
    return {'counts': counts, 'outputs': outputs, 'members': member_rows}


def line(counts):
    return FRAME.format(**counts)


def tsv(columns, rows):
    out = io.StringIO()
    out.write('\t'.join(columns) + '\n')
    for row in rows:
        out.write('\t'.join(str(row[c]) for c in columns) + '\n')
    return out.getvalue()


def exit_code(counts):
    if counts['F']:
        return 2
    if counts['P']:
        return 3
    return 0 if counts['M'] + counts['K'] == counts['N'] else 2


def write_tables(result, folder):
    os.makedirs(folder, exist_ok=True)
    for name, columns, rows in (('outputs.tsv', OUTPUT_COLUMNS, result['outputs']),
                                ('members.tsv', MEMBER_COLUMNS, result['members'])):
        with io.open(os.path.join(folder, name), 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(tsv(columns, rows))
    with io.open(os.path.join(folder, 'result.txt'), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write(line(result['counts']) + '\n')


def report(result, stream):
    stream.write(tsv(OUTPUT_COLUMNS, result['outputs']))
    for output in result['outputs']:
        for path in output['extra_paths']:
            stream.write('extra file in %s %s: %s\n' % (output['stage'], output['output_path'], path))
    stream.write(line(result['counts']) + '\n')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package', default=os.path.dirname(os.path.abspath(__file__)))
    parser.add_argument('--against', required=True)
    parser.add_argument('--table-out')
    args = parser.parse_args(argv)
    try:
        result = compare(args.package, args.against)
    except Unreadable as exc:
        print('compare: ' + str(exc), file=sys.stderr)
        return 1
    report(result, sys.stdout)
    if args.table_out:
        write_tables(result, args.table_out)
    return exit_code(result['counts'])


if __name__ == '__main__':
    sys.exit(main())
