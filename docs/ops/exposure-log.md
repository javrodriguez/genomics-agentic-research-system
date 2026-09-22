# Exposure evidence

Format: `date, source_ip, control, open_ports, PASS|FAIL|INCONCLUSIVE` (UTC). `source_ip` is
`<v4>|<v6>` when both families were measured (decision 0053); in the table below, a `|` inside
a cell is written `\|`.
Threshold: exposure 0 ports from outside, with a reachable third-host control.
No run has happened; the outside claim needs a host that is not on the tailnet.

| Date | Source IP | Control | Open ports | Result |
|---|---|---|---|---|
