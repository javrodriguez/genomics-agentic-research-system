# PostgreSQL foundation

One service, PostgreSQL 16. No worker, queue, reverse proxy or monitoring is deployed.
Use Debian directly on Node 1 (0044). The compose file binds loopback by default;
choosing a tailnet/LAN bind also requires the operator's default-deny firewall.
Administrative access stays on trusted local/VPN paths. Do not enable serve/funnel.

Copy `../backup/backup.env.example` outside git, fill placeholders and export its
values in a trusted shell. Create the private backup/work, data and destination
folders, a mode-600 compose password file, PGPASSFILE and encryption files. The
compose file reads PGUSER, PGDATABASE, PG_PASSWORD_FILE, PG_DATA_DIR, PG_BIND_ADDR,
PG_PORT, PG_RESTART, COMPOSE_PROJECT and COMPOSE_VOLUME_SUFFIX. Its named volume
binds PG_DATA_DIR, so data location is explicit and tests can keep all volume data
under GARS_ROW5_SCRATCH. Keep secrets and real logs outside this checkout.

```sh
docker compose -f infra/compose/postgres.compose.yml -p "$COMPOSE_PROJECT" config
docker compose -f infra/compose/postgres.compose.yml -p "$COMPOSE_PROJECT" up -d
bash infra/backup/pg_backup.sh
bash infra/backup/restore_drill.sh               # read-only default
```

PG_CLIENT_MODE=container runs matching client tools via compose exec -T db. PGHOST
and PGPORT (and the DRILL_TARGET equivalents) must be reachable **inside** db;
PG_PORT is the published host port, a different setting. CONTAINER_ENGINE may be
podman. Host mode requires matching client/server majors and a protected PGPASSFILE.
A backup role needs read access to every application table; recovery role needs
createdb and target ownership. Both drill roles need read access to pg_control_system()
for alias-safe cluster identity checks. Use a dedicated role for each purpose when provisioning.
No password is passed as a command argument. Both remote endpoints need rsync,
SSH key access, and Python 3; set host keys up interactively beforehand.

Schedule `pg_backup.sh` nightly using the site's scheduler, with the filled
exported environment, working directory set to the checkout, and stdout/stderr
retained outside git. Example crontab shape (replace every placeholder):

```text
0 2 * * * /absolute/operator-backup-wrapper >> /absolute/private-backup-log 2>&1
```

The trusted wrapper sources the environment with `set -a`, then invokes this
checkout's absolute pg_backup.sh path. Test the wrapper interactively first.
Retention is 14 archives at each configured location, manifest history retained.
Only encrypted PostgreSQL archives receive this retention; EXTRA_PATHS is a
encrypted tar and checksum-verified copy hook for the Brain owner, not a vault retention policy.
Missing second destination is explicitly reported and does not authorize a data route.

For a development restore, an independent person/session captures a canary and
one count/checksum record for EVERY user table via the read-only checksum_table
function in `infra/backup/row05.py`. Primary keys and ordinary schema/table identifiers
are required. Exclude only public.gars_drill_target. Supply the file outside the
operator context. The target is a **distinct** disposable recovery database. A human
must manually create `public.gars_drill_target` there before each destructive drill;
it is intentionally not recreated by the script. Run dry-run, then `--destroy`.
The source identity and marker guards cannot be disabled. Decision 0044 records
why the spec's literal primary-deletion exit is not implemented. Do not rename the
source endpoint to evade the guard. A failed/stale archive never yields PASS.

Run exposure from a host outside the tailnet, with a known reachable control on a
third host. Supply the public and tailnet endpoints and all relevant service ports;
the control must resolve to different addresses from both. Retain source IP,
control result and open ports. A configured-port probe is not an all-ports scan:
audit listening services and firewall configuration as part of real provisioning.
Both logs in docs/ops are empty evidence templates, not proof of a run.

Tests require GARS_ROW5_SCRATCH plus TMPDIR, TEMP and TMP set to that private
scratch directory, and PYTHONDONTWRITEBYTECODE=1. CI's existing jobs are unchanged;
configure that environment externally before running this module. Tests refuse
without scratch. They scrub inherited database/backup/drill/exposure configuration,
use `-p gars-row5-<pid>-<random>`, random loopback PG_PORT, COMPOSE_VOLUME_SUFFIX,
PG_RESTART=no and a random mode-600 password file. The named volume binds a data
folder inside scratch. `down -v` executes in a finally, even on failed readiness.
A failed docker/podman info probe or 60-second health gate skips each database case
with the failed probe named. Set GARS_TEST_NO_CONTAINER=1 to exercise that skip path.
No database test may point at an existing stack or use inherited PG settings.
