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
                if evidence.get('artifact') is not None:
                    problem = artifact_problem(evidence['artifact'], args.project)
                    if problem:
                        problems.add(problem)
                if evidence.get('source') is not None:
                    reference = evidence['source']['reference']
                    if resolve_citation.doi(reference):
                        problem = resolve_citation.resolve(reference, transport=transport)
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
