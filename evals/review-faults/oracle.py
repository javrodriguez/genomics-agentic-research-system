"""Deterministic structured finding oracle; no model or prose matching."""
SEVERITY = {'NOTE': 0, 'MINOR': 1, 'MAJOR': 2, 'BLOCKER': 3}


def normalize_file(name):
    if name.startswith('./'):
        name = name[2:]
    if name.startswith('repo/'):
        name = name[5:]
    return name


def caught(review, expected):
    target = expected['match']
    for finding in review['findings']:
        if finding['class'] != expected['class']:
            continue
        if normalize_file(finding['file']) != target['file']:
            continue
        if SEVERITY[finding['severity']] < SEVERITY[expected.get('min_severity', 'MINOR')]:
            continue
        if target['mode'] == 'file' or (
                finding['line_start'] <= target['line_end'] + 3 and
                finding['line_end'] >= target['line_start'] - 3):
            return True
    return False


def false_alarm(review, class_id=None):
    return any(SEVERITY[f['severity']] >= SEVERITY['MINOR'] and
               (class_id is None or f['class'] == class_id)
               for f in review['findings'])
