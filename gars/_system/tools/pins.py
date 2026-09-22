"""R-099: reject unknown, unreviewed, rejected or changed workspace skill/MCP pins."""
import hashlib
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]


def inventory(root):
    root = Path(root)
    paths = set(root.rglob('SKILL.md'))
    paths.update(root.rglob('.mcp.json'))
    paths.update(root.rglob('mcp.json'))
    return sorted(paths)


def check(root=WORKSPACE):
    root = Path(root)
    problems = []
    try:
        entries = json.loads((root / '_references/tool_pins.json').read_text())['pins']
        known = {e['path']: e for e in entries}
        if len(known) != len(entries):
            problems.append('duplicate pin')
        actual = {p.relative_to(root).as_posix():p for p in inventory(root)}
        if set(actual) != set(known):
            problems.append('inventory differs from pin file')
        for rel, entry in known.items():
            if entry['review_status'] != 'reviewed':
                problems.append(rel + ': ' + entry['review_status'])
            p = actual.get(rel)
            if p is None or hashlib.sha256(p.read_bytes()).hexdigest() != entry['sha256']:
                problems.append(rel + ': sha256 differs')
    except (OSError, ValueError, KeyError, TypeError):
        problems.append('missing or malformed pin inventory')
    return problems


if __name__ == '__main__':
    problems = check()
    if problems:
        print('R-099 / spec §9.6 / decision 0058: session refused: ' + '; '.join(problems), file=sys.stderr)
        sys.exit(2)
    print('R-099: workspace pins reviewed and intact')
