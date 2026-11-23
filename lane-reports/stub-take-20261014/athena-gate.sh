#!/bin/bash
# The athena gate: exit 0 only when gap4-merge-32e688a has ended and no athena-suite process runs.
st=$(/usr/local/bin/python3.13 /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py status gap4-merge-32e688a-20261014T133252Z 2>&1 | tail -1)
echo "gate: $st"
case "$st" in *state=running*|"") echo "gate: CLOSED (the run is in progress or unreadable)"; exit 1;; esac
n=$(ssh -a -x -o BatchMode=yes athena -- 'ps -u athena-suite -o pid= | wc -l') || { echo "gate: CLOSED (ssh failed)"; exit 1; }
echo "gate: athena-suite processes $n"
[ "$n" -eq 0 ] || { echo "gate: CLOSED (athena-suite processes running)"; exit 1; }
echo "gate: OPEN"
