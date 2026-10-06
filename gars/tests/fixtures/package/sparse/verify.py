#!/usr/bin/env python3
"""Verify a GARS reproduction package, and optionally a re-run against it (stdlib only, offline).

  python3 verify.py                       every file against SHA256SUMS, and the package's own
                                          cross-links; the landing README beside the package, if any
  python3 verify.py --against <re-run>    the same, then every recorded output member by member
                                          (compare.py), with the result line and its table

Exit 0 when the package verifies (and, with --against, every output matched: M + K = N); 1 when a
check fails; 2 when the package verifies and some output differs (F > 0); 3 when the package
verifies, none differs and some are presence-only (P > 0). Python 3.6 or later; no network.
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True   # a __pycache__ folder would be a file SHA256SUMS does not list
sys.path.insert(0, HERE)
import compare  # noqa: E402

SUMS = 'SHA256SUMS'
SUM_LINE = re.compile(r'([0-9a-f]{64})  ([^\n]+)\Z')
LANDING_DIGEST = re.compile(r'package sha256 `?([0-9a-f]{64})`?')
ORIGINS = ('S2b-preregistered', 'pass-1')


class Failed(Exception):
    """One named check that did not hold."""


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(package, rel):
    try:
        with open(os.path.join(package, *rel.split('/')), 'rb') as handle:
            return handle.read()
    except OSError:
        raise Failed('cannot read %s' % rel)


def read_json(package, rel):
    try:
        return json.loads(read_bytes(package, rel).decode('utf-8'))
    except (UnicodeError, ValueError):
        raise Failed('%s is not valid JSON' % rel)


def table(package, rel):
    try:
        return compare.read_table(os.path.join(package, *rel.split('/')))
    except compare.Unreadable as exc:
        raise Failed(str(exc))


def files_in(package):
    found = []
    for folder, dirs, files in os.walk(package, followlinks=False):
        dirs.sort()
        for name in dirs:   # a linked folder is not walked, so it is refused here (S5 review r2, M9)
            if os.path.islink(os.path.join(folder, name)):
                raise Failed('%s is a link; a package holds only regular files'
                             % os.path.relpath(os.path.join(folder, name), package).replace(os.sep, '/'))
        for name in files:
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, package).replace(os.sep, '/')
            if os.path.islink(full):
                raise Failed('%s is a link; a package holds only regular files' % rel)
            found.append(rel)
    return sorted(found)


def check_sums(package):
    lines = read_bytes(package, SUMS).decode('utf-8').split('\n')
    if lines[-1] != '':
        raise Failed('SHA256SUMS does not end with a newline')
    listed = {}
    for text in lines[:-1]:
        match = SUM_LINE.match(text)
        if not match or match.group(2) in listed:
            raise Failed('SHA256SUMS line is malformed or repeated: %r' % text[:80])
        rel = match.group(2)
        if rel.startswith('/') or '..' in rel.split('/') or rel == SUMS:
            raise Failed('SHA256SUMS names a path outside the package: %s' % rel)
        listed[rel] = match.group(1)
    present = [rel for rel in files_in(package) if rel != SUMS]
    missing = sorted(set(listed) - set(present))
    unlisted = sorted(set(present) - set(listed))
    if missing:
        raise Failed('a file SHA256SUMS lists is missing: %s' % missing[0])
    if unlisted:
        raise Failed('a file is in the package but not in SHA256SUMS: %s' % unlisted[0])
    for rel in present:
        if sha256_bytes(read_bytes(package, rel)) != listed[rel]:
            raise Failed('%s does not match its SHA256SUMS line' % rel)
    return len(present)


def records(package):
    found = {}
    for rel in files_in(package):
        if rel.startswith('records/') and rel.endswith('.manifest.json'):
            record = read_json(package, rel)
            found[record.get('stage')] = record
    if not found:
        raise Failed('records/ holds no manifest')
    return found


def field(rows, name):
    values = [row['value'] for row in rows if row['field'] == name]
    if len(values) != 1:
        raise Failed('code/GARS.txt does not name %s exactly once' % name)
    return values[0]


def check_links(package, out):
    recs = records(package)
    gars = table(package, 'code/GARS.txt')
    commit = field(gars, 'gars_commit')
    for stage, record in sorted(recs.items()):
        if record.get('gars_commit') != commit:
            raise Failed('code/GARS.txt gars_commit differs from records/%s.manifest.json' % stage)
    out.append('ok: GARS commit %s is the commit every record names' % commit)

    pipes = dict((row['stage'], row) for row in table(package, 'code/pipelines.tsv'))
    for stage, record in sorted(recs.items()):
        row = pipes.get(stage)
        if row is None or row['pipeline_commit'] != record.get('pipeline_commit') or \
                row['release'] != record.get('workflow_version'):
            raise Failed('code/pipelines.tsv does not carry the pipeline commit and release of %s' % stage)
    out.append('ok: code/pipelines.tsv carries each record\'s pipeline commit and release')

    config = sha256_bytes(read_bytes(package, 'env/run-executor.config'))
    for stage, record in sorted(recs.items()):
        named = [e.get('sha256') for e in record.get('execution_config') or []
                 if e.get('role') == 'nextflow_config']
        if named != [config]:
            raise Failed('env/run-executor.config is not the executor config %s recorded' % stage)
    out.append('ok: env/run-executor.config is byte for byte the executor config the run recorded')

    rows = table(package, 'outputs/outputs.tsv')
    listed = dict(((r['stage'], compare.member_path(r)), r) for r in rows)
    expected = {}
    for stage, record in sorted(recs.items()):
        for output in record.get('outputs') or []:
            if output.get('members') is None:
                expected[(stage, output['path'])] = output['sha256']
            else:
                for member in output['members']:
                    expected[(stage, output['path'] + '/' + member['path'])] = member['sha256']
    # every row, not one per key: a member two nested outputs share is listed twice (a dict would keep
    # only the last row and hide an edit to the first)
    if set(expected) != set(listed) or any(expected.get((r['stage'], compare.member_path(r))) != r['recorded_sha256']
                                           for r in rows):
        raise Failed('outputs/outputs.tsv does not list exactly the members the records name, with their sha256')
    for row in rows:
        if row['recorded_sha256'] == 'withheld' and row['mode'] != 'presence':
            raise Failed('%s: a withheld sha256 is allowed only on a presence member' % compare.member_path(row))
        if row['mode'] == 'presence' and row['recorded_sha256'] != 'withheld':
            raise Failed('%s: a presence member must read withheld, never a sha256' % compare.member_path(row))
    for stage, record in sorted(recs.items()):
        for output in record.get('outputs') or []:
            if output.get('members') and any(m['sha256'] == 'withheld' for m in output['members']) \
                    and output.get('sha256') != 'withheld':
                raise Failed('%s: a directory output holding a withheld member must withhold its tree hash'
                             % output['path'])
    out.append('ok: outputs/outputs.tsv lists the %d recorded members with their recorded sha256' % len(expected))

    small = [rel for rel in files_in(package) if rel.startswith('outputs/small/')]
    for rel in small:   # outputs/small/<stage>/<path under the stage's run/results/>
        parts = rel.split('/', 3)
        key = (parts[2], compare.RESULTS_PREFIX + parts[3]) if len(parts) == 4 else None
        if key not in listed or sha256_bytes(read_bytes(package, rel)) != listed[key]['recorded_sha256']:
            raise Failed('%s is not a recorded member with its recorded sha256' % rel)
    out.append('ok: the %d result tables in outputs/small/ match the sha256 the run recorded' % len(small))

    methods = read_bytes(package, 'METHODS.md').decode('utf-8')
    for value in [commit] + sorted(set(r.get('pipeline_commit') for r in recs.values())):
        if value not in methods:
            raise Failed('METHODS.md does not cite %s' % value)
    out.append('ok: METHODS.md cites the GARS commit and every pipeline commit')

    entries = read_json(package, 'outputs/package-tolerances.json').get('entries')
    if not isinstance(entries, list):
        raise Failed('outputs/package-tolerances.json has no entries list')
    declared = {}
    for entry in entries:
        if entry.get('mode') not in compare.MODES or entry.get('mode') == 'exact' or \
                entry.get('origin') not in ORIGINS or not entry.get('cause') or not entry.get('evidence'):
            raise Failed('a tolerance entry lacks a declared mode, a cause, evidence or an origin')
        for member in entry.get('members') or []:
            declared[(entry.get('stage'), member)] = entry['mode']
    for row in rows:   # every row: a dict by member would hide an edit to the first of two (S5 review r1, m3)
        key = (row['stage'], compare.member_path(row))
        if row['mode'] != declared.get(key, 'exact'):
            raise Failed('the mode of %s %s is not its tolerance entry\'s' % key)
        if row['mode'] in ('sorted_table', 'column_matched_table', 'sign_aligned_numeric') and \
                row.get('normalised', '-') == '-':
            raise Failed('%s %s has no normalised form for its mode' % key)
    if set(declared) - set(listed):
        raise Failed('a tolerance entry names a member the run did not record')
    out.append('ok: every non-exact member has a tolerance entry with a cause, evidence and origin')

    for row in table(package, 'params/approval.tsv') if os.path.exists(
            os.path.join(package, 'params', 'approval.tsv')) else []:
        plan = 'params/%s.PLAN.md' % row['stage']
        if sha256_bytes(read_bytes(package, plan)) != row['plan_sha256']:
            raise Failed('%s is not the plan its approval record binds' % plan)
        out.append('ok: %s is byte for byte the approved plan' % plan)

    for stage, record in sorted(recs.items()):
        for item in record.get('withheld_fields') or []:
            out.append('not checkable from this package: %s field %s (%s)'
                       % (stage, item.get('field'), item.get('reason')))


def check_landing(package, digest, out):
    landing = os.path.join(os.path.dirname(os.path.abspath(package)), 'README.md')
    if not os.path.isfile(landing):
        out.append('note: no landing README beside the package (as in a zip); nothing to check')
        return
    with io.open(landing, encoding='utf-8') as handle:
        found = LANDING_DIGEST.findall(handle.read())
    if not found or any(value != digest for value in found):
        raise Failed('the landing README beside the package names another package digest')
    out.append('ok: the landing README names this package (sha256 %s)' % digest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package', default=HERE)
    parser.add_argument('--against')
    parser.add_argument('--table-out')
    args = parser.parse_args(argv)
    out = []
    try:
        count = check_sums(args.package)
        digest = sha256_bytes(read_bytes(args.package, SUMS))
        out.append('ok: %d files match SHA256SUMS (package sha256 %s)' % (count, digest))
        check_links(args.package, out)
        check_landing(args.package, digest, out)
    except Failed as exc:
        print('\n'.join(out))
        print('FAIL: ' + str(exc))
        return 1
    print('\n'.join(out))
    if not args.against:
        print('package verified')
        return 0
    try:
        result = compare.compare(args.package, args.against)
    except compare.Unreadable as exc:
        print('FAIL: ' + str(exc))
        return 1
    compare.report(result, sys.stdout)
    if args.table_out:
        compare.write_tables(result, args.table_out)
        with io.open(os.path.join(args.table_out, 'package-sha256.txt'), 'w', encoding='utf-8',
                     newline='\n') as handle:
            handle.write(digest + '\n')
    return compare.exit_code(result['counts'])


if __name__ == '__main__':
    sys.exit(main())
