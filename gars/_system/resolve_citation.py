#!/usr/bin/env python3
"""Resolve DOI registration; replay is available only to in-process test callers."""
import argparse
import json
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('reference')
    return result


def dois(reference):
    """Extract DOI tokens wherever a citation writes them, preserving suffix case."""
    values = re.findall(r"10\.[0-9]{4,9}/[^\s<>\"']+", reference, re.I)
    return [value[:-1] if value.endswith(('.', ',', ';')) else value for value in values]


def doi(reference):
    values = dois(reference)
    return values[0] if values else None


def mentions_doi(reference):
    return bool(re.search(r'\bdoi\b', reference, re.I))


def live_transport(url):
    try:
        with urlopen(url, timeout=20) as response:
            return response.getcode(), response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def resolve(reference, transport=None):
    identifier = doi(reference)
    if identifier is None:
        return 'citation_unverifiable'
    transport = transport or live_transport
    try:
        status, body = transport('https://api.crossref.org/works/' + quote(identifier, safe=''))
        if status == 200:
            payload = json.loads(body.decode('utf-8'))
            if payload.get('status') == 'ok' and isinstance(payload.get('message'), dict):
                return 'resolved'
            return 'citation_unverifiable'
        if status != 404:
            return 'citation_unverifiable'
        status, body = transport('https://doi.org/api/handles/' + quote(identifier, safe=''))
        payload = json.loads(body.decode('utf-8'))
        if status == 200 and payload.get('responseCode') == 1:
            return 'resolved'
        if status == 404 and payload.get('responseCode') == 100:
            return 'citation_unresolved'
        return 'citation_unverifiable'
    except Exception:
        # Includes network failures, malformed replies, and transport exceptions.
        return 'citation_unverifiable'


def main(argv=None, transport=None):
    args = parser().parse_args(argv)
    code = resolve(args.reference, transport=transport)
    print(code)
    return 0 if code == 'resolved' else 1


if __name__ == '__main__':
    sys.exit(main())
