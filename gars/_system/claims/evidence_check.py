#!/usr/bin/env python3
"""Preflight claim evidence paths, bytes and DOI registrations."""
import argparse
import hashlib
import json
from os import pardir
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import resolve_citation


# Exact keys emitted by claims.claims_export at BASE (decision 0075).
EVIDENCE_KEYS = {'id', 'artifact_id', 'source_id', 'kind', 'relation', 'artifact', 'source'}
PARENT_KEYS = {'artifact': {'id', 'path', 'sha256'}, 'source': {'id', 'reference'}}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--snapshot', type=Path, required=True)
    result.add_argument('--project', type=Path, required=True)
    return result


def artifact_problem(artifact, project):
    try:
        relative = Path(artifact['path'])
        if relative.is_absolute() or pardir in relative.parts:
            return 'evidence_missing'
        path = (project / relative).resolve()
        path.relative_to(project.resolve())
        if not path.is_file():
            return 'evidence_missing'
        digest = hashlib.sha256()
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b''):
                digest.update(chunk)
        if digest.hexdigest() != artifact['sha256']:
            return 'evidence_hash_mismatch'
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return 'evidence_missing'
    return None


def main(argv=None, transport=None):
    args = parser().parse_args(argv)
    failed = False
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding='utf-8'))
        for claim in snapshot['claims']:
            cid = claim['id']
            if not isinstance(cid, int) or isinstance(cid, bool):
                raise ValueError('invalid claim id')
            problems = set()
            for evidence in claim['evidence']:
                if not isinstance(evidence, dict) or set(evidence) != EVIDENCE_KEYS:
                    problems.add('evidence_missing')
                    continue
                if (type(evidence['id']) is not int
                        or evidence['kind'] not in ('computational', 'statistical', 'literature')
                        or evidence['relation'] not in ('supports', 'contradicts', 'absent')):
                    problems.add('evidence_missing')
                    continue
                artifact, source = evidence.get('artifact'), evidence.get('source')
                kind = 'artifact' if artifact is not None else 'source'
                parent = artifact if kind == 'artifact' else source
                other = 'source' if kind == 'artifact' else 'artifact'
                if (not isinstance(parent, dict) or set(parent) != PARENT_KEYS[kind]
                        or (artifact is not None and source is not None)
                        or type(evidence.get(kind + '_id')) is not int
                        or type(parent.get('id')) is not int
                        or evidence[kind + '_id'] != parent['id']
                        or evidence.get(other + '_id') is not None):
                    problems.add('evidence_missing')
                    continue
                if kind == 'artifact':
                    digest = artifact.get('sha256')
                    if (not isinstance(artifact.get('path'), str) or not artifact['path'].strip()
                            or not isinstance(digest, str) or len(digest) != 64
                            or any(c not in '0123456789abcdef' for c in digest)):
                        problems.add('evidence_missing')
                        continue
                    problem = artifact_problem(artifact, args.project)
                    if problem:
                        problems.add(problem)
                else:
                    reference = source.get('reference')
                    if not isinstance(reference, str) or not reference.strip():
                        problems.add('evidence_missing')
                        continue
                    identifiers = resolve_citation.dois(reference)
                    if not identifiers and resolve_citation.mentions_doi(reference):
                        problems.add('citation_unverifiable')
                    for identifier in identifiers:
                        problem = resolve_citation.resolve(identifier, transport=transport)
                        if problem != 'resolved':
                            problems.add(problem)
            for problem in sorted(problems):
                print('%s: claim %d' % (problem, cid))
                failed = True
    except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
        print('evidence_missing: invalid snapshot')
        return 1
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
