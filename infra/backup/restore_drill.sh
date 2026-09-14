#!/usr/bin/env bash
# HUMAN PRE-STEP: on the distinct recovery database, manually execute:
# CREATE TABLE public.gars_drill_target (acknowledged_by text);
# Obtain the pre-destroy canary file from an independent context before this step.
# The source primary is NEVER a permitted target. See decision 0044's spec conflict.
# No flags bypass the identity or marker guard. Default is read-only dry-run.
set -euo pipefail
exec python3 -B "$(dirname "${BASH_SOURCE[0]}")/row05.py" drill "$@"
