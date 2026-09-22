---
date: 2026-09-22
status: standing
kind: decision
touches:
  - docs/ops/restore-log.md
  - docs/ops/exposure-log.md
  - docs/ops/HARDWARE.md
---
# Row 5's exit, run on Node 1

## Context

Row 5 (the encrypted nightly backup, the guarded restore drill and the outside exposure probe) was
merged repository-side on 2026-09-17, but its exit had never run: there was no hardware. Node 1,
a Minisforum MS-A2 running Debian 13.7, was provisioned and hardened on 2026-09-21. This record is
the first real run of row 5's exit on it, 2026-09-21 to 2026-09-22, as scoped by 0044.

Two engine defects were found on the way and fixed in their own records: the archive listing that
broke on any archive past the pipe buffers (0052), and an exposure check that could not tell a
probe inside the network under test from one outside it (0053).

## Decision

- **Container mode**, PostgreSQL 16 from the repository's one-service compose file, Docker Engine
  from Docker's signed repository (the key fingerprint was checked). The database is published on
  loopback only.
- **The target is a distinct, marked recovery database in the same cluster**, 0044's supported
  target. The marker is created by a human before each destructive run.
- **A rehearsal before the real drill:** the whole cycle ran once in a throwaway compose project
  (its own port, data, logs, canary and off-machine folder) and passed 12 of 12 steps, so a kit
  defect would have been a rehearsal failure rather than a permanent FAIL row. Rehearsal rows are
  not evidence and are not in [restore-log.md](../ops/restore-log.md).
- **The nightly backup is a systemd timer** at the owner's chosen hour, with bounded retries. The
  drill restored the newest **timer-made** archive, never one made for the drill (§13.2). The
  drill's RPO, worked back to the archive's time, confirms which archive it took.
- **R-095 kept strictly:** no agent session can reach the Docker socket, so every Docker-touching
  step was run by the owner, one line at a time, with the operator context reading the output.
- **The canary is unseen.** A tool on the node chose the table, column and row with a
  cryptographic random source, over synthetic data whose key values were also random. It wrote the
  file readable only by the service account, and printed nothing but its sha256. The owner ran the
  tool, and the value is unknown to the operator context. The seal class is therefore
  `independent_context`, not `external_human_seal`.

## Named deviations, from observed facts

- **The source/backup role is the compose bootstrap superuser.** `postgres.compose.yml` line 5
  sets `POSTGRES_USER: ${PGUSER}`, which makes that role the superuser, against
  `infra/compose/README.md` lines 27 and 34 ("Use a dedicated role for each purpose when
  provisioning"). The recovery role is separate and not a superuser (CREATEDB and LOGIN only).
- **Inside the container, loopback is `trust`.** The observed `pg_hba_file_rules` give `trust` for
  local, 127.0.0.1 and ::1, and `scram-sha-256` only for other hosts. Role separation is therefore
  a guard against mistakes by whoever can run `compose exec`, **not** an authentication boundary.

## Evidence

- **Drill:** `2026-09-22T16:55:13Z, 13.167400, 0.284136, PASS`. RPO 13.17 h and RTO 17 s, against
  24 h and 60 min. Exit 0, and no `result=FAIL` line (0047). The source database was intact
  afterwards: row counts and size unchanged.
- **Negative controls, in order, before the drill:**
  - a dry run with no canary gave `FAIL reason=canary_missing`;
  - after the canary was captured, a dry run against the unmarked target gave
    `FAIL reason=target_not_marked` (not `command_failed`, so connection and privileges were
    sound);
  - after the marker, a dry run gave `DRY_RUN … writes=none`, resolving to the same scheduled
    archive the drill then used.
- **Rehearsal:** 12 of 12 steps passed, including the first run anywhere of:
  - a non-superuser `DROP`/`CREATE`;
  - `pg_restore --no-owner` into a role-owned database;
  - a non-superuser `pg_control_system()`;
  - the SSH remote reads.
  Its artefacts stayed out of the real logs.
- **Transport:** openrsync on the destination preserved archive mtimes to the second, and the
  engine re-hashed the off-machine copy (`offmachine_verified=ok`).
- **Exposure:** see [exposure-log.md](../ops/exposure-log.md). From a carrier network with
  Tailscale off, the router's public IPv4 showed **0 of 9 declared ports open**. Node 1's IPv6
  could not be probed from outside because the carrier tethers IPv4 only, so the result is
  INCONCLUSIVE. Three earlier rows were taken from inside the home network and are void; 0053 is
  the fix they prompted.

## What this does not close

- **§13.2's primary deletion** is not performed; the target is a distinct recovery database (0044).
- **`external_human_seal`:** the public claim that the system restores reliably stays unmeasured.
- **R-136, the second destination:** not configured, pending row 8's data-handling decision.
- **R-126.**
- **RTO at real scale:** measured on about 470,000 synthetic rows (a 66 MB database), not on
  real data.
- **IPv6 exposure from outside:** unmeasured. The IPv4 face is measured.
- **An all-ports scan:** the probe covers the declared ports only.

The next drill is due by 2026-10-22 (30 days).
