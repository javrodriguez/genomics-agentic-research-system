#!/usr/bin/env python3
"""Supported report emission: preflight and render one claims snapshot."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_check
import render_report


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    source = result.add_mutually_exclusive_group(required=True)
    source.add_argument('--snapshot', type=Path)
    source.add_argument('--from-db')
    result.add_argument('--manifest', type=Path, required=True)
    result.add_argument('--project', type=Path, required=True)
    result.add_argument('--out', type=Path, required=True)
    return result


def main(argv=None, transport=None):
    args = parser().parse_args(argv)
    temporary = None
    try:
        snapshot = args.snapshot
        if args.from_db is not None:
            payload = render_report.database_snapshot(args.from_db)
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='.claims-',
                                             dir=str(args.out.parent), delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(payload, handle)
            snapshot = temporary
        code = evidence_check.main(['--snapshot', str(snapshot), '--project', str(args.project)],
                                   transport=transport)
        if code:
            return code
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('render_report.py')),
                                 '--snapshot', str(snapshot), '--manifest', str(args.manifest),
                                 '--out', str(args.out)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode:
            print('report refused: renderer failed', file=sys.stderr)
        return result.returncode
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired):
        print('report refused: input or export failed', file=sys.stderr)
        return 1
    finally:
        if temporary is not None:
            temporary.unlink()


if __name__ == '__main__':
    sys.exit(main())
