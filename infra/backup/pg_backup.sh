#!/usr/bin/env bash
# Schedule nightly with a trusted exported environment; see ../compose/README.md.
set -euo pipefail
exec python3 -B "$(dirname "${BASH_SOURCE[0]}")/row05.py" backup "$@"
