#!/usr/bin/env bash
# Run on a host outside the tailnet, with a reachable control on a third host.
set -euo pipefail
exec python3 -B "$(dirname "${BASH_SOURCE[0]}")/row05.py" exposure "$@"
