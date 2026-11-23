#!/bin/bash
# The athena gate for G14's stub take (15 Oct 2026): exit 0 only when the final merged battery
# gap4-merge-final-383e5c2-383e5c2-20261015T043059Z is no longer running, no athena-suite process runs,
# and no container is present for javier's rootless Docker. Adapted from stub-take-20261014/athena-gate.sh.
RUN=gap4-merge-final-383e5c2-383e5c2-20261015T043059Z
st=$(/usr/bin/python3 /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py status "$RUN" 2>&1 | tail -1)
echo "gate: $st"
case "$st" in *state=running*|"") echo "gate: CLOSED (the run is in progress or unreadable)"; exit 1;; esac
n=$(ssh -a -x -o BatchMode=yes athena -- 'ps -u athena-suite -o pid= | wc -l') || { echo "gate: CLOSED (ssh failed)"; exit 1; }
echo "gate: athena-suite processes $n"
[ "$n" -eq 0 ] || { echo "gate: CLOSED (athena-suite processes running)"; exit 1; }
c=$(ssh -a -x -o BatchMode=yes athena -- 'docker ps -aq | wc -l') || { echo "gate: CLOSED (docker ps failed)"; exit 1; }
echo "gate: javier containers $c"
[ "$c" -eq 0 ] || { echo "gate: CLOSED (containers present)"; exit 1; }
echo "gate: OPEN"
