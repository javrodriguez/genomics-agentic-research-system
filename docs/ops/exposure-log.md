# Exposure evidence

Format: `date, source_ip, control, open_ports, PASS|FAIL|INCONCLUSIVE` (UTC). `source_ip` is
`<v4>|<v6>` when both families were measured (decision 0053); in the table below, a `|` inside
a cell is written `\|`.
Threshold: exposure 0 ports from outside, with a reachable third-host control.
The first runs were on 2026-09-22 (decision 0054). Every run is listed, including three that do
not count; the note under the table says why.

| Date | Source IP | Control | Open ports | Result |
|---|---|---|---|---|
| 2026-09-22T17:02:02Z | `<home IPv6>` | open | 80\|443 | INCONCLUSIVE |
| 2026-09-22T17:13:38Z | `<home IPv6>` | open | 80\|443 | FAIL |
| 2026-09-22T17:15:28Z | `<home IPv6>` | open | 0 | PASS |
| 2026-09-22T18:27:40Z | `<carrier IPv4>` | open | 0 | PASS |
| 2026-09-22T18:27:52Z | `<carrier IPv4>` | open | 0 | INCONCLUSIVE |

**The first three rows are void: they were taken from inside the home network, not from outside.**
Their source address is the operator's home IPv6 and is withheld here; it is in the private
operations record. At 17:02 Tailscale was still up and the check refused correctly. At 17:13 and
17:15 Tailscale was off but the probe was still on the home Wi-Fi, and the check could not tell: the
17:13 `FAIL` is the router answering its own admin interface from the LAN side, and the 17:15 `PASS`
is a false PASS for a host on the probe's own IPv6 /64. Decision 0053 fixes the check so that both
are now refused. They are kept, not edited out, because they are how the defect was found.

**The two valid rows**, from a phone hotspot on a carrier network with Tailscale off:
- **IPv4: PASS, 0 of 9 declared ports open** on the home router's public address. Behind NAT, this
  covers the router's public face and so what reaches Node 1 over IPv4.
- **IPv6: INCONCLUSIVE, not measured.** The carrier tethers IPv4 only (no global IPv6 address, no
  IPv6 route), so Node 1's global IPv6 address could not be probed from outside. Node 1's firewall
  is default-deny inbound with no IPv6 acceptance rule, and an on-link probe found 0 of 9 ports
  open, but neither of those is an outside measurement: **IPv6 exposure from outside stays
  unmeasured.**

Declared ports: 22, 80, 443, 2375, 5432, 6379, 8006, 8080, 55432. A configured-port probe is not an
all-ports scan.
