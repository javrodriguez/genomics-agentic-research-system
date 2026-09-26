"""Science path adapter and any-of dispatch to row 9's field-match oracle."""
from bio_common import SEVERITY, false_alarm, row9_caught


def matching_copy(review):
    """Strip one ./ then one project/; never let row 9 strip a repo/ prefix."""
    findings = []
    for finding in review['findings']:
        name = finding['file']
        if name.startswith('./'):
            name = name[2:]
        if name.startswith('project/'):
            name = name[8:]
        # Do not let row 9 remove another dot prefix (or expose a hidden repo/).
        if name.startswith('./'):
            continue
        if name.startswith('repo/'):
            continue
        findings.append(dict(finding, file=name))
    return dict(review, findings=findings)


def caught(review, expected):
    matching = matching_copy(review)
    return any(row9_caught(matching, dict(expected, match=entry))
               for entry in expected['match_any'])
