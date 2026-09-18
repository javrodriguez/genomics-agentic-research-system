# Hardware record — Stage 1 pending

Reference profiles from §13.3 are targets, not measured machine facts. Two nodes
are **not HA**: no quorum, replicated state or tested failover is claimed.

| Node | Reference class | Reference roles (later roles not deployed by row 5) | Recorded hardware |
|---|---|---|---|
| Node 1 | M70q-class; 16 GB; 1 TB NVMe | PostgreSQL; later workers, Nextflow fixtures, disposable VMs | <to be recorded at Stage 1: RAM · disk · serial · OS version · tailnet name> |
| Node 2 | N100-class; 12+ GB | Separate failure domain; later monitoring, DNS/reverse proxy, uptime, external observer | <to be recorded at Stage 1: RAM · disk · serial · OS version · tailnet name> |

OS decision: Debian directly on Node 1 (0044); actual version <to be recorded at Stage 1>.
Node 2 Linux version: <to be recorded at Stage 1>.
Off-machine destination: MacBook over the tailnet, <to be recorded at Stage 1: destination and absolute path>.
Second destination: <to be recorded at Stage 1 after the row-8 data-handling decision permits it>.
Firewall/default-deny and trusted SSH access evidence: <to be recorded at Stage 1>.

## How to fill this in

A human records observed inventory, OS and storage facts after provisioning; keep
serials, addresses and tailnet identifiers in the private operational record, not
this public template. Run the nightly backup and distinct marked recovery drill,
retain dated RPO/RTO evidence, then run exposure from outside the tailnet with a
third-host control. No hardware inventory, marker creation or exit test has run.
