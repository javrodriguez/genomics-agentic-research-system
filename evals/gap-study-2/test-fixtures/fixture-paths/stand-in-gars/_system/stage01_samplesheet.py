#!/usr/bin/env python3
"""A stand-in for the GARS stage 01 `--check`, for TheFixtureNamesNoPathOutsideTheRunTree only.

The precondition branch alone: exit 3 when the samples table is absent, 0 when it is there, as the real
script does for the two variants the project generator builds.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    missing = [d.name for d in sorted((args.project / "00_data").glob("*"))
               if not (d / "samples.csv").is_file()]
    if missing:
        print(json.dumps({"ok": False, "error": f"missing samples.csv for: {', '.join(missing)}"}))
        return 3
    print(json.dumps({"ok": True}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
