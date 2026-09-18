#!/usr/bin/env python3
"""Compute the three-intact-repeat range; never substitutes synthetic observations."""
import argparse
import sys
from pathlib import Path
import bench


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('records', nargs='*')
    parser.add_argument('--output', help='write the measured report as text (use a .txt suffix)')
    parser.add_argument('--partition', choices=bench.PARTITIONS, default='tuned_on')
    args = parser.parse_args()
    try:
        records = [bench.read_record(p) for p in args.records]
        floor, baseline = bench.noise_floor(records, args.partition)
        lines = ['method: three intact repeats; range, arithmetic mean, equal binary task weights']
        for record in records:
            s = record['scores'][args.partition]
            lines.append(record['run_id'] + ' [' + record['run_sha256'] + ']: ' + bench.ratio_text(s['numerator'], s['denominator']))
        lines.append(args.partition + ' noise floor: ' + bench.ratio_text(floor.numerator, floor.denominator))
        lines.append(args.partition + ' intact mean: ' + bench.ratio_text(baseline.numerator, baseline.denominator))
        report = '\n'.join(lines) + '\n'
        if args.output:
            bench.require(Path(args.output).suffix == '.txt', 'noise report must use .txt, not run-record .json')
            with Path(args.output).open('x', encoding='utf-8') as handle:
                handle.write(report)
        print(report, end='')
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print('uncomputable: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
