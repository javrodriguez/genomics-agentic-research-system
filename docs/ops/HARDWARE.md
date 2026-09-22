# Hardware record — Stage 1: Node 1 recorded, Node 2 pending

Reference profiles from §13.3 are targets, not measured machine facts. Two nodes
are **not HA**: no quorum, replicated state or tested failover is claimed.

| Node | Reference class | Reference roles (later roles not deployed by row 5) | Recorded hardware |
|---|---|---|---|
| Node 1 | M70q-class; 16 GB; 1 TB NVMe | PostgreSQL; later workers, Nextflow fixtures, disposable VMs | RAM 32 GB (29 GiB usable) · disk 1 TB NVMe (953.9 G) · OS Debian 13.7 "trixie" · serial and tailnet name in the private operations record (recorded 2026-09-21) |
| Node 2 | N100-class; 12+ GB | Separate failure domain; later monitoring, DNS/reverse proxy, uptime, external observer | <to be recorded at Stage 1: RAM · disk · serial · OS version · tailnet name> |

OS decision: Debian directly on Node 1 (0044); actual version Debian 13.7 "trixie", installed directly, no hypervisor.
Node 2 Linux version: <to be recorded at Stage 1>.
Off-machine destination: MacBook over the tailnet (the path is in the private operations record); a dedicated,
key-only receiving account that cannot unlock the disk.
Second destination: <to be recorded at Stage 1 after the row-8 data-handling decision permits it>.
Firewall: default-deny nftables inbound on Node 1; SSH key-only, from the LAN and the tailnet (the private
operations record has the rules). PostgreSQL is published on loopback only.

## How to fill this in

A human records observed inventory, OS and storage facts after provisioning; keep
serials, addresses and tailnet identifiers in the private operational record, not
this public template. Run the nightly backup and distinct marked recovery drill,
retain dated RPO/RTO evidence, then run exposure from outside the tailnet with a
third-host control. On 2026-09-22 Node 1 did all three: the nightly backup ran from its timer, the
drill passed ([restore-log.md](restore-log.md)), and exposure from outside passed on IPv4 with IPv6
unmeasured ([exposure-log.md](exposure-log.md)); decision 0054 has the details. Node 2 and the
second destination have not been provisioned.
