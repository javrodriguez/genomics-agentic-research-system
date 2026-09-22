---
date: 2026-09-22
status: standing
kind: defect
touches:
  - infra/backup/row05.py
  - tests/test_row05_backup.py
  - infra/compose/README.md
  - infra/backup/backup.env.example
  - docs/ops/exposure-log.md
  - README.md
  - DEVELOPMENT.md
symptoms:
  - test_exposure.sh prints "0, PASS" while the source address it recorded is on the network under test
  - test_exposure.sh prints a verdict for an IPv4 target while the recorded source address is IPv6, or the reverse
  - An exposure row looks clean but the operator was on the network being tested
---
# The exposure test refuses a probe taken from inside the network under test

## Context

§18 row 5's exit is *exposure 0 ports from outside*. The whole claim rests on the probe standing
somewhere the network under test does not reach, and `exposure()` judged where it stood by exactly
one thing: whether `tailscale status` succeeded.

On 2026-09-22, during row 5's first run on real hardware, an operator turned Tailscale off but
stayed on the home Wi-Fi. The tailnet guard passed, so the function printed two verdicts that
looked like measurements and were not:

| Row | What it said | What it was |
|---|---|---|
| `…17:13:38Z, <home IPv6>, open, 80\|443, FAIL` | two ports exposed | the router answering its own admin interface from the LAN side, against the home IPv4 address |
| `…17:15:28Z, <home IPv6>, open, 0, PASS` | the host is closed from outside | a probe on the target's **own IPv6 `/64`** |

The `PASS` is the serious one. Nothing in the row distinguishes it from a real measurement: the
control host was reachable, every port read `closed`, Tailscale was down. Only a human comparing
the source address against the target by hand caught it.

Two inside shapes were in play:

- **IPv4 behind NAT.** The address the internet reports for the probe *is* the address under test.
- **IPv6 on the same link.** The probe held an address on the target's own `/64`.

A third fact hid the first. `SOURCE_IP_CMD` defaulted to `curl -s https://ifconfig.me`, which on a
dual-stack host answers over IPv6. At 17:13 the probe *reached* the IPv4 target over IPv4 (that is
why the router answered on 80 and 443), yet the recorded source was IPv6, so the one address that
would have given the game away — the probe's own public IPv4, equal to the target — was never
measured.

## Decision

The source address is measured **per family**, and each address of the host under test is judged
against the probe's source **in that address's family**:

- With `SOURCE_IP_CMD` unset (now the recommended form, and the template's), the check runs
  `curl -q -4 -fsS --noproxy '*'` and the same with `-6` against `https://ifconfig.me` itself.
  `-q` ignores `~/.curlrc` and `--noproxy` ignores proxy variables, so the address measured is the
  one the port probes leave from. A family that answers with
  an address of that family is recorded; if neither does, the run refuses with `source_ip_missing`.
- An explicit `SOURCE_IP_CMD` is kept as before: one measurement, in whatever family it reports.
- IPv4-mapped IPv6 (`::ffff:a.b.c.d`) is unwrapped, on sources and targets, so it is keyed as the
  IPv4 address it is.

`outside(source, target)` compares one pair: equal → **inside** (behind that NAT); both IPv6 and
the same `/64` → **inside** (on the link); otherwise same family → **outside**; different families
→ `None`, *cannot be told*.

For the host under test, `exposure()`:

- refuses outright if any address is **link-local** — it is on this host's own link by definition;
- judges each address that has a same-family source with `outside()`;
- for an address with no same-family source, asks the kernel whether this host has **any route**
  to it (`has_route()`: a UDP `connect`, which sends nothing and fails at once without a route).
  Only the errors that mean no route (`ENETUNREACH`, `EHOSTUNREACH`, `EADDRNOTAVAIL`,
  `EAFNOSUPPORT`) leave the address out, because the port probe cannot reach it either; the run
  then prints which addresses were left out and which the verdict covers. A route → `None`: routed,
  but the probe's own address in that family was not measured, so nothing vouches for it. Any other
  error from the route check is also `None`. Whether a `curl` failed is never taken to mean
  "no route".

If **any** address is provably inside, `exposure()` raises `Fail('source_inside_target_network')`
before probing a port or opening the log, so no row is written. If any address is `None`, or none
could be compared at all, the run is forced `INCONCLUSIVE`, with a printed note that names why —
no route to any address; the source unmeasured where a route exists (with the remedy: an address
literal in a family this host can measure, or fixing that family's connectivity); or an explicit
`SOURCE_IP_CMD` in the wrong family, with the remedy (unset it). These join the existing
`INCONCLUSIVE` conditions recorded in 0044 — a working `tailscale status`, an unreachable control,
an unknown network error — which are unchanged.

**The port probe targets the judged addresses**, each as a literal, instead of resolving the name
a second time. When no address is routed at all, every resolved address is probed instead, and the
run is `INCONCLUSIVE` regardless. A port counts as `open` if any probed address answers, `unknown` if any
probe errors, else `closed`.

**The row format widens by one case:** with both families measured, the source field reads
`<v4>|<v6>`, using the `|` the open-ports field already uses. Rows from a single-family probe are
unchanged. `docs/ops/exposure-log.md` states the form and the Markdown escape.

## Why

An exposure row is evidence about a network boundary, and a reviewer reading `0, PASS` is entitled
to assume the probe was on the far side of it. A tool that cannot tell should say so rather than
produce a confident row, as it already does for the tailnet.

This design is the third, and each earlier one failed review for a reason worth keeping:

1. **One source, family mismatch → `INCONCLUSIVE`.** Wrong both ways: it only *downgraded* the real
   17:13 inside run, and it made every **dual-stack outside vantage** (an office, a hotel, a
   dual-stack cloud VM) probing an IPv4 target `INCONCLUSIVE`, although such a probe genuinely
   reaches the target from outside. Measured per family, 17:13 is refused (its IPv4 source equals
   the target) and the dual-stack outside run gets its verdict.
2. **Per family, a failed `curl` read as "no path".** A timeout, an error page or ifconfig.me being
   down in one family would drop that family's comparison while the port probe still reached it —
   so a probe inside the target's IPv4 NAT, with one flaky `curl -4`, could be judged by its IPv6
   address alone and write a verdict. The absence of a signal was being read as a clean one, which
   is the defect this record exists to fix. The route check asks the question that matters — can
   this host reach that address at all — and a failed measurement where a route exists is now
   `INCONCLUSIVE`.

Leaving out an address is therefore claimed only where it is true: the kernel says it has no
route to it, so the probe could not have touched it. A route that exists but does not work (broken
IPv6 behind a default route, say) can only ever give `INCONCLUSIVE`, never a false `PASS`. And a
verdict that covers only some of a host's addresses says which, so a row from an IPv4-only vantage
cannot pass for a dual-stack one. That is what lets a dual-stack hostname be judged from an
IPv4-only vantage point, rather than never passing, and probing the judged literals is what makes
that verdict about the addresses that were judged.

A refusal rather than an `INCONCLUSIVE` row for the provable case is deliberate: being inside is an
operator error with an obvious remedy — move — and a log row would invite the reading that
something about the host was measured. Nothing was.

## Limits, stated rather than hidden

The check proves *inside* only for the shapes above. It does not catch:

- a probe on a **different subnet of the same site** (a second VLAN under one `/56`): `/64` is the
  boundary that proves same-link, and anything wider would refuse legitimate outside probes;
- a **non-global literal target** other than link-local — an RFC 1918, CGNAT (`100.64/10`) or
  loopback address is judged like any other. From a genuinely outside vantage such a probe reaches
  nothing, so its `closed` readings say nothing about the host. Point `EXPOSURE_PUBLIC_HOST` at a
  public address;
- **split-horizon DNS**: a hostname target that resolves, on the LAN, to a private address — the
  same case by another road. Use a public address literal, as `backup.env.example` now asks;
- a **multi-address IPv4 block** where the probe leaves through a different public address of the
  same block;
- a **split-tunnel VPN**, where the `ifconfig.me` request and the port probes take different
  paths. (Proxy settings in the environment or `~/.curlrc` no longer split them: `curl` ignores
  both.) A transparent proxy on the network path would;
- **NPTv6 / NAT66**, where IPv6 is translated after all.

## Evidence

On 2026-09-22, Python 3.13.2 on macOS, against the final code. Each mutation is one protection
broken on its own; every one turns the guard tests red.

| Run | Result |
|---|---|
| The three guard tests with `d3dd56c`'s engine | `FAILED (failures=1, errors=7)` |
| The same tests with the fix | OK |
| Mutation: IPv6 always judged inside | `FAILED (failures=1, errors=3)` |
| Mutation: `/64` widened to `/48` | `FAILED (failures=1)` |
| Mutation: the IPv4-mapped unwrap removed, per-family path | `FAILED (failures=1)` |
| Mutation: the IPv4-mapped unwrap removed, explicit path | `FAILED (failures=1)` |
| Mutation: the per-family default replaced by one measurement | `FAILED (failures=1, errors=6)` |
| Mutation: the refusal removed | `FAILED (failures=3)` |
| Mutation: a failed `curl` read as "no route" (design 2) | `FAILED (failures=2)` |
| Mutation: the port probe resolves the name again | `FAILED (failures=4)` |
| Mutation: the link-local refusal removed | `FAILED (failures=1)` |
| Mutation: `has_route()` always true | `FAILED (failures=4)` |
| Mutation: `has_route()` treats every error as no route | `FAILED (failures=2)` |
| Mutation: an unknown route check leaves the address out | `FAILED (failures=1)` |
| Mutation: `curl -q` dropped | `FAILED (failures=7)` |
| Mutation: `--noproxy` dropped | `FAILED (failures=7)` |
| Mutation: the left-out note removed | `FAILED (failures=1)` |
| `run_tests.py` as CI sets it (`GARS_ROW5_SCRATCH`, `TMPDIR`), Docker answering | `Ran 241 · OK (skipped=11)`; the 17 live-Postgres tests ran |
| `run_tests.py` with `TMPDIR` set but no `GARS_ROW5_SCRATCH` (a macOS cold clone) | `Ran 241 · OK (skipped=55)` |
| `run_tests.py` with neither variable set (as on Linux) | `Ran 241 · OK (skipped=57)` |

`check_counts.py` is clean (enforced=3) and `check_contracts.py` reports 14 contracts clean.
Three fresh-context reviews: rounds 1 and 2 APPROVE WITH FIXES (designs 1 and 2, above); round 3
APPROVE WITH FIXES with no code defect found, its two required prose corrections and four
recommended items applied afterwards and verified by the tests and mutations above, not by a
fourth review.
One earlier run of the row-5 file reported two failures in the repository-unchanged snapshot checks;
their diffs were `CONTEXT.md` and a `__pycache__` file written into the same worktree by an index
rebuild and a count check run **during** that suite. Rerun with nothing else writing: OK. A reader
who sees such a failure should look for a concurrent writer first.
