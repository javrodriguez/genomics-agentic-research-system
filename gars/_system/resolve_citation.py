#!/usr/bin/env python3
"""Resolve DOI registration; replay is available only to in-process test callers."""
import argparse
import json
import re
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import urlopen


DOI_PATTERN = r"10\.[0-9]{4,9}(?:\.[0-9]+)*/[^\s<>\"']+"
MARKER_PATTERN = r'(?<![0-9A-Za-z])doi(?=\b|_|10[./])'
ASCII_ALNUM_PATTERN = r"[0-9A-Za-z]"


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('reference')
    return result


def _doi_spans(reference):
    """Extract DOI tokens wherever a citation writes them, preserving suffix case."""
    for match in re.finditer(DOI_PATTERN, reference, re.I):
        value = match.group()
        punctuation_removed = False
        while value:
            if value[-1] in '.,;' and not punctuation_removed:
                value = value[:-1]
                punctuation_removed = True
            elif (value[-1] in ')]}'
                  and value.count(value[-1]) > value.count({')': '(', ']': '[', '}': '{'}[value[-1]])):
                value = value[:-1]
            else:
                break
        yield value, match.start(), match.start() + len(value)


def dois(reference):
    return [value for value, start, end in _doi_spans(reference)]


def _has_unbound_doi_number(reference):
    """Bind marker-local numbers, consuming parsed identifiers and their lists."""
    spans = list(_doi_spans(reference))
    for marker in re.finditer(MARKER_PATTERN, reference, re.I):
        if any(start <= marker.start() < end for value, start, end in spans):
            continue
        # Check the leading boundary after the marker, including attached DOI10/.
        tail = reference[marker.end():]
        token_end = re.match(r'\S*', tail).end()
        number = re.search(r'(?<![0-9A-Za-z])10[./]', tail)
        if number is None or re.search(ASCII_ALNUM_PATTERN, tail[token_end:number.start()]):
            continue
        number_start = marker.end() + number.start()
        while True:
            identifier_end = next((end for value, start, end in spans
                                   if start <= number_start < end), None)
            if identifier_end is None:
                return True
            # Any number inside the identifier is satisfied; chain from its end.
            cursor = identifier_end
            while cursor < len(reference) and not re.match(ASCII_ALNUM_PATTERN, reference[cursor]):
                cursor += 1
            if not re.match(r'10[./]', reference[cursor:]):
                break
            number_start = cursor
    return False


def doi(reference):
    values = dois(reference)
    return values[0] if values else None


def mentions_doi(reference):
    # Check what remains after every parsed identifier is removed: one valid
    # DOI cannot conceal another, unparseable DOI in the same reference.
    identifiers = dois(reference)
    if identifiers: return _has_unbound_doi_number(reference)
    for identifier in identifiers:
        reference = reference.replace(identifier, ' ')
    # A resolved DOI may leave its own explicit marker behind. Preserve the
    # original malformed-marker refusal when no identifier could be parsed.
    explicit = not identifiers and re.search(
        r'(?<![0-9A-Za-z])doi(?::|\.org\b)', reference, re.I)
    # Both sides admit underscore separators; attached numeric tokens retain
    # the empty-separator spelling. Remove markers before checking numeric
    # boundaries so DOI10/x is checked while the year 2010. is not.
    pattern = r'(?<![0-9A-Za-z])doi(?=\b|_|10[./])'
    marker = re.search(pattern, reference, re.I)
    numeric = re.search(r'(?<![0-9A-Za-z])10[./]',
                        re.sub(pattern, ' ', reference, flags=re.I))
    return bool(explicit or (marker and numeric))


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
