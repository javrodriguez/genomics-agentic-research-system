#!/usr/bin/env python3
"""The non-model checks before every take (CP2), and the credential-file check after it.

Three parts, so the judgment is pure:
  - `probes(...)` builds each probe: an exec as the agent with `--workdir /` (a short program run as
    `python3 -I -B -c`, which never reads under the run tree: after `begin` the watcher is armed, and anything opened
    there would be logged in turn 1's window), a host-side exec into the sidecar, an inspect, or a host-side read;
  - `run(runtime, probes)` collects the raw records, and a probe that fails to run is recorded as failed;
  - `evaluate(raw, *, spec, lock, sidecar_expect, harness, hosts, evidence_dir)` turns them into the preflight record
    `{"ok", "checks": [{"id", "ok", "detail"}], "recorded"}`, one entry per id of the closed ordered tuple
    `PREFLIGHT_CHECKS`. `ok` is True only when every check ran and passed. A check whose probe is missing or failed
    fails; a check whose expected value (from `spec`, `lock`, `sidecar_expect` or a constant here) is PENDING fails.
    Any failure refuses the take before the first turn, as a rehearsal: the drive step passes `preflight_ok`.
    `evidence_dir` is required (CP2-preflight-3): the sidecar's read-write evidence mount must have it as its source
    and the probes must have read it, so a mount at one folder with probes at another fails.

The drive step calls one entry point, `collect_and_evaluate(...)` (CP2-preflight-2): it reads the take's lock through
`load_take_lock` (image_lock.load, the harness's own take image, image_lock.require_ready, then the five LOCK_KEYS
projected from the validated lock) and the sidecar's lock through `load_sidecar_lock` (LW-7), takes the spec, the take id and the sidecar id from the launch record
(`Launched.spec`, never the pre-launch placeholder), runs the probes and evaluates them with the very same
evidence folder and sidecar expectation. It never launches, runs a turn or tears down: the drive step's own launch
and cleanup lifecycle stays around it, and a lock or launch-record refusal raises before any runtime call.

`write(record, path)` puts the record BESIDE the evidence folder, in the take's record folder (ruling C2), never in
it. `postflight(config_dir, harness)` checks the per-take config folder after a take (D8 B2 item 7).

The lock evaluate takes is a dict of exactly w4a's schema paths (`LOCK_KEYS`), projected by `load_take_lock` from a
lock read through `image_lock.load` (merge binding 8; lane w6a). No model, no network from the host, standard library
only.
"""

from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable

from box import image_lock
from box import run_take
from box import sidecar_contract

PENDING = run_take.PENDING
NotReady = run_take.NotReady

# Merge binding 1: equal to every image.lock's users.watcher.uid (w4a) and sidecar.create_argv's default user (w4c).
WATCHER_UID = 10002
AGENT_UID = int(run_take.AGENT_USER.split(":")[0])
KEEPALIVE_UID = int(run_take.KEEPALIVE_USER.split(":")[0])
# CAP_DAC_READ_SEARCH is capability 2: the one capability the watcher holds.
WATCHER_CAP_EFF = 1 << 2

LOCK_KEYS = ("image_id", "harness.version", "users.agent.uid", "users.watcher.uid", "users.keepalive.uid",
             "manifest_digest")
# The platform whose image manifest is the content identity (glitch-06's lock-writer ruling (a), 14 Oct 2026):
# `docker image inspect --platform linux/amd64` returns that manifest's digest as its Id on athena's containerd
# store, the same across rebuilds of identical content (measured: candidate2-20261014/index-reading-all).
# On the classic (graphdriver) store the inspect either errors or returns the image's CONFIG digest; neither equals
# a lock's manifest digest (the lock writer refuses a record whose manifest digest equals its config digest, LW-4),
# so a lock written from a containerd build fails closed on a classic store: the check refuses, it never passes.
IMAGE_PLATFORM = "linux/amd64"
# The sidecar's own lock (LW-7): its image id and platform manifest are checked like the take image's. The names
# below are image_lock's values, spelled here (preflight reads image_lock only through load and require_ready; the
# test binds each to image_lock's own): the sidecar lock's place in box/, each take lock's folder in box/, the
# sidecar image's name and the shape of an image id.
SIDECAR_LOCK_KEYS = ("image_id", "manifest_digest")
SIDECAR_LOCK_IMAGE = "sidecar"
SIDECAR_LOCK_PATH = "sidecar/image.lock"
TAKE_LOCK_DIRS = {"take-a": "", "take-o": "codex", "take-g": "gemini"}
IMAGE_ID_SHAPE = re.compile(r"sha256:[0-9a-f]{64}")
# The egress proxy's own lock (O-1, glitch-06, 14 Oct 2026), as LW-7 did the sidecar's: the launch record's proxy
# image and the running proxy must be its image id, and the probe of that image's platform manifest its digest.
EGRESS_LOCK_KEYS = ("image_id", "manifest_digest")
EGRESS_LOCK_IMAGE = "egress"
EGRESS_LOCK_PATH = "egress/image.lock"
PROXY_CREATE_STEP = "proxy-create"
# Each harness's own take image (image_lock.TAKE_IMAGES; arms A and C share take-a). Merge binding 8 binds it.
TAKE_IMAGE = {run_take.CLAUDE_CODE: "take-a", run_take.CODEX: "take-o", run_take.GEMINI: "take-g"}
SIDECAR_EXPECT_KEYS = ("user", "network_mode", "cap_drop", "cap_add", "security_opt", "privileged", "pid_mode",
                       "mounts", "image", "cmd", "entrypoint")
# The take container's mount target for the sidecar's evidence folder; the agent must fail to list it.
SIDECAR_EVIDENCE_MOUNT = "/srv/ev"
# Names that must never resolve from the take, beside the other two harnesses' hosts (plan; D8 B2 item 8).
BLOCKED_NAMES = ("github.com", "huggingface.co")
OTHER_HOST_VIA_PROXY = "github.com"
CGROUP_ROOT = "/sys/fs/cgroup"
CPU_PERIOD = 100000            # the runtime's default CFS period; cpu.max reads "<cpus * period> <period>"
HEALTH = "health.jsonl"

PREFLIGHT_CHECKS = (
    "agent-non-root",
    "image-matches-lock",
    "harness-version-matches-lock",
    "take-inspect-matches-spec",
    "limits-apply",
    "evidence-out-of-reach",
    "watcher-invisible",
    "sidecar-isolated",
    "watcher-started",
    "watcher-capability",
    "consequential-paths-readable",
    "no-container-socket",
    "egress-allowed-host",
    "egress-other-host-refused",
    "egress-direct-refused",
    "names-do-not-resolve",
    "study-folders-absent",
    "run-tree-path-neutral",
    "egress-raw-ip-refused",
    "egress-metadata-refused",
    "egress-gateway-refused",
)
# PF1-L3 (pre-freeze review 1, m9; fold plan prefreeze-1, the lane orchestrator's approval, Sat 24 Oct 2026, under
# Javier's standing delegation): the three roads out that egress-direct-refused (the take's own host by name) does not
# try. The direct-egress probe, run as the agent, connects (TCP, DIRECT_TIMEOUT_S each, all at once) to two public
# addresses by IP literal (no name to resolve), to the link-local metadata address, and to every gateway the take's
# own route table names, plus the first host of each on-link network (where Docker's default IPAM puts an internal
# network's gateway), on GATEWAY_PORTS. Each check passes only when no connection was made; the gateway check also
# needs the take inspect's own gateway (NetworkSettings.Networks.*.Gateway, when it names one) among the addresses
# tried, so the probe cannot have tried somewhere else. Lane pf1-gateway (glitch-45's ruling, Mon 26 Oct 2026, under
# Javier's standing delegation; w-o48's live preflight): Docker names no per-container Gateway on an --internal
# network, so the expected gateway is also read host-side, outside the take's reach, from `docker network inspect` of
# the take's own network (spec.network; the take-network-inspect probe): its IPAM.Config gateways must be tried too,
# and a network neither record names a gateway for still refuses, fail closed. An answered refusal (the host's stack
# is reachable, the port closed) is listed in the detail, never read as a connection. A host service on a port
# outside GATEWAY_PORTS is not tried (box_residuals names it).
DIRECT_TARGETS = {"raw-ip-a": ("1.1.1.1", 443), "raw-ip-b": ("8.8.8.8", 443), "metadata": ("169.254.169.254", 80)}
RAW_IP_TARGETS = ("raw-ip-a", "raw-ip-b")
METADATA_TARGET = "metadata"
GATEWAY_PORTS = (22, 53, 80, 443, 2375, 2376, 3128, 8080)
DIRECT_TIMEOUT_S = 3
POSTFLIGHT_CHECKS = ("no-credential-file",)

# `<harness> --version`'s output form, per harness: a regex with one group (the version) once a walk measures it.
VERSION_COMMANDS = {run_take.CLAUDE_CODE: ("claude", "--version"), run_take.CODEX: ("codex", "--version"),
                    run_take.GEMINI: ("gemini", "--version")}
# FILLED 14 Oct 2026 (box lane; stub-take review PASS, rule R-VERSION): the lock's version replaced by one group in the
# output measured on athena: claude-code through this module's own harness-version probe in a stub take; codex and
# gemini from a one-shot container of their locked images (confirm at their first preflight; a mismatch fails closed).
VERSION_PATTERNS = {run_take.CLAUDE_CODE: '([0-9]+(?:\\.[0-9]+){2})\\ \\(Claude\\ Code\\)',
                    run_take.CODEX: 'codex\\-cli\\ ([0-9]+(?:\\.[0-9]+){2})',
                    run_take.GEMINI: '([0-9]+(?:\\.[0-9]+){2})'}
# The pre-registered study folders that must be absent from the run tree (run-tree-relative; CP5's list).
# RULED by Javier, "CP5: all as recommended" (08:11 EDT, 14 Oct 2026), on the draft's value 1
# (plans/gap-study-round-4/cp5-values-draft-2026-10-14.md): round 3's run_location.excluded_from_the_run_tree,
# verbatim and in order, read from e2979b31:evals/gap-study-3/prereg.json (the round 4 run tree is exported from the
# same pinned commit, 844a4ce0, where all seven exist). tests/test_preflight.py binds the two.
STUDY_PATHS = ("evals", "docs/EVALS.md", ".github", "docs/implementation", "docs/reviews", "docs/specs",
               "docs/decisions/0041-glitch-produces-the-v1-0-1-gap-assessment.md")
# The round's leak words for the run tree's PATH only (CP5's list; interface 16; never matched against transcripts).
# RULED by Javier, "CP5: all as recommended" (08:11 EDT, 14 Oct 2026), the draft's value 2 with items 3 and 4:
# prereg-draft.json's 25 leak_words (round 3's 23 plus gap-study-4 and round 4), the box users' names from the image
# locks' users.agent.name and users.watcher.name (dana, eli: bound to the committed locks by tests/test_preflight.py),
# and gap4. 28 words. Departure from the earlier note "Round 3's are never committed here": the owner's ruling names
# this literal list, and prereg-draft.json already carries round 3's words.
LEAK_WORDS = ("evaluation", "eval", "benchmark", "test case", "grading", "graded", "score", "correct answer",
              "we are testing", "under test", "gap-study", "gap study", "prereg", "pre-registration",
              "pre-registered", "gap-study-2", "gars-eval-v3", "round 2", "gap-study-3", "gars-eval-v4", "round 3",
              "allowlist", "allowedTools", "gap-study-4", "round 4", "dana", "eli", "gap4")

# Credential files a harness could leave in its config folder, each with the source that names it. A file whose
# name merely looks like a credential (CREDENTIAL_LIKE) fails the check too: this lane's stricter reading.
# Only a name a source gives is used as a real value; names recalled without a source wait in RECORDED_PENDING for
# the walk (Review A, glitch-f3's ruling "fold all of it"), and CREDENTIAL_LIKE stays the backstop that catches them.
CREDENTIAL_FILES = {
    run_take.CLAUDE_CODE: (),
    run_take.CODEX: (("auth.json", "the owner's 13 Oct subscription amendment (take_config.CODEX_TOP: "
                                   "forced_login_method chatgpt, cli_auth_credentials_store file): the login is "
                                   "stored in CODEX_HOME/auth.json, the config folder; superseding D8 section 3's "
                                   "'so no auth.json is written' (api, ephemeral)"),),
    run_take.GEMINI: (),
}
CREDENTIAL_LIKE = re.compile(r"(cred|oauth|token|secret|auth|account|\.pem$|\.key$)", re.IGNORECASE)

PENDING_WHY = {
    "VERSION_PATTERNS": "every `--version` output form: a walk-only value; no parse pattern is invented.",
    "STUDY_PATHS": "the pre-registered list of study folders absent from the run tree: CP5's.",
    "LEAK_WORDS": "the round's own leak words: CP5's (it adds the box users' names, image.lock users.*.name).",
}
# Lane d8-furniture fold 2 (glitch-f1, 22 Oct 2026): arm G's Google project tier is the owner's own account fact,
# recorded as given with its source (D8 mitigation 1 rests on it alone; measuring it needs an API call with the key).
GOOGLE_PROJECT_TIER = ("Google Paid, cap $140 (Javier's own words, 8 Oct 2026, plans/gap-study-round-4.md line 2129; "
                       "the owner's account fact, not measured)")
RECORDED_PENDING = {
    "token_visible_to_children": "whether the login reaches the agent's child processes: measured at the first "
                                 "walk, so the secret scan is sized to it.",
    "watcher_holds_capability": "whether a non-root watcher holds its added capability in its effective set: the "
                                "watcher-capability check passes only when it does.",
    "internal_resolver": "whether an --internal network's resolver refuses outside names: the names check measures "
                         "it.",
    "credential_file_names": "the credential files each harness could leave, recalled without a source and confirmed "
                             "by a walk: Claude Code .credentials.json; Gemini CLI oauth_creds.json and "
                             "google_accounts.json. Until then CREDENTIAL_LIKE catches them.",
    "cap_add spelling": "the runtime's spelling of the sidecar's one added capability: sidecar_expect carries "
                        "PENDING until the stub take.",
}


def _is_pending(v) -> bool:
    return run_take._is_pending(v)


def pending() -> dict:
    """Every constant of this module still PENDING, with its reason."""
    values = {"VERSION_PATTERNS": VERSION_PATTERNS, "STUDY_PATHS": STUDY_PATHS, "LEAK_WORDS": LEAK_WORDS}
    return {k: why for k, why in PENDING_WHY.items() if _is_pending(values[k])}


# -------------------------------------------------------------------------------------- the take's expected facts
TAKE_FACT_KEYS = ("image", "user", "entrypoint", "cmd", "working_dir", "network_mode", "cap_drop", "cap_add", "security_opt",
                  "privileged", "devices", "pid_mode", "pids_limit", "memory", "memory_reservation", "nano_cpus",
                  "mounts", "readonly_rootfs", "tmpfs")


def expected_take_inspect(spec) -> dict:
    """Every fact `docker container inspect` must show for the take container, derived from the same spec."""
    run_take.check_spec(spec)
    return {
        "image": spec.image, "user": run_take.KEEPALIVE_USER, "entrypoint": list(run_take.KEEPALIVE_COMMAND[:1]),
        "cmd": list(run_take.KEEPALIVE_COMMAND[1:]),
        "working_dir": spec.run_tree, "network_mode": spec.network, "cap_drop": ["ALL"], "cap_add": [],
        "security_opt": ["no-new-privileges"], "privileged": False, "devices": [], "pid_mode": "",
        "pids_limit": spec.pids_limit, "memory": spec.memory, "memory_reservation": spec.memory_reservation,
        "nano_cpus": spec.nano_cpus(),
        "mounts": sorted([
            {"type": "bind", "source": spec.run_tree, "destination": spec.run_tree, "rw": True},
            {"type": "bind", "source": spec.config_dir, "destination": run_take.CONFIG_MOUNT, "rw": True}],
            key=lambda m: m["destination"]),
        "readonly_rootfs": True, "tmpfs": dict(run_take.TAKE_TMPFS),    # the read-only root (glitch-b5, 16 Oct 2026)
    }


_LIST_FACTS = ("cap_drop", "cap_add", "security_opt", "devices", "cmd", "entrypoint")
_MOUNT_FIELDS = {"type": "Type", "source": "Source", "destination": "Destination", "rw": "RW"}


def _facts(obj: dict, keys) -> dict:
    out = {}
    for k in keys:
        try:
            v = run_take._path_get(obj, run_take.INSPECT_PATHS[k])
        except (KeyError, TypeError):
            out[k] = "<absent>"
            continue
        if k in _LIST_FACTS and v is None:
            v = []
        if k == "pid_mode" and v is None:
            v = ""
        out[k] = v
    return out


def inspect_mismatches(obj, expected: dict, *, kind: str) -> list:
    """Every difference between an inspect object and the expected facts; refuses while anything is PENDING."""
    if _is_pending(run_take.INSPECT_STATUS):
        return [f"the inspect spellings are PENDING: {run_take.PENDING_WHY['INSPECT_STATUS']}"]
    keys = TAKE_FACT_KEYS if kind == "take" else SIDECAR_EXPECT_KEYS if kind == "sidecar" else None
    if keys is None:
        return [f"unknown inspect kind {kind!r}"]
    if not isinstance(expected, dict) or set(expected) != set(keys):
        return [f"the {kind} expectation must name exactly {list(keys)}"]
    still = sorted(k for k, v in expected.items() if _is_pending(v))
    if still:
        return [f"{kind} expectation PENDING: {', '.join(still)}"]
    if not isinstance(obj, dict):
        return [f"the {kind} inspect is not an object"]
    got = _facts(obj, keys)
    out = []
    for k in keys:
        want, have = expected[k], got[k]
        if k == "mounts":
            fields = sorted({f for m in want for f in m}) if want else ["destination"]
            if not isinstance(have, list):
                out.append("mounts: absent")
                continue
            proj = sorted(({f: m.get(_MOUNT_FIELDS[f]) for f in fields} for m in have if isinstance(m, dict)),
                          key=lambda m: str(m.get("destination")))
            if len(proj) != len(have) or proj != sorted(want, key=lambda m: str(m.get("destination"))):
                out.append(f"mounts: {proj} != {want}")
        elif k in _LIST_FACTS:
            if not isinstance(have, list) or sorted(map(str, have)) != sorted(map(str, want)) \
                    or len(have) != len(want):
                out.append(f"{k}: {have!r} != {want!r}")
        elif type(have) is not type(want) or have != want:
            out.append(f"{k}: {have!r} != {want!r}")
    return out


# --------------------------------------------------------------------------------------------- the programs
# Each runs as `python3 -I -B -c` in the take (as the agent, workdir /) or in the sidecar (host-side exec). None
# opens anything under the run tree; none names the study (interface 16); each parses at feature_version (3, 11).
IDENTITY_PROGRAM = """\
import json, os
fields = {}
with open("/proc/self/status") as fh:
    for line in fh:
        name, _, value = line.partition(":")
        if name in ("Uid", "Gid", "CapEff", "CapPrm", "CapBnd", "NoNewPrivs"):
            fields[name] = value.split()
print(json.dumps({"uid": os.getuid(), "gid": os.getgid(), "status": fields}))
"""

CGROUP_PROGRAM = """\
import json, sys
out = {}
for name in sys.argv[2:]:
    try:
        with open(sys.argv[1] + "/" + name) as fh:
            out[name] = fh.read().strip()
    except OSError as e:
        out[name] = {"error": type(e).__name__}
print(json.dumps(out))
"""

LISTING_PROGRAM = """\
import json, os, sys
out = {}
for path in sys.argv[1:]:
    try:
        os.listdir(path)
        out[path] = "listed"
    except OSError as e:
        out[path] = type(e).__name__
print(json.dumps(out))
"""

PROCESSES_PROGRAM = """\
import json, os
me = os.getpid()
rows = []
for name in os.listdir("/proc"):
    if not name.isdigit() or int(name) == me:
        continue
    try:
        with open("/proc/" + name + "/status") as fh:
            fields = dict(line.split(":", 1) for line in fh if ":" in line)
    except OSError as e:
        rows.append({"pid": int(name), "unreadable": type(e).__name__})
        continue
    rows.append({"pid": int(name), "uid": int(fields["Uid"].split()[0]), "name": fields.get("Name", "").strip(),
                 "uids": [int(x) for x in fields["Uid"].split()],
                 "gids": [int(x) for x in fields["Gid"].split()],
                 "groups": [int(x) for x in fields["Groups"].split()],
                 "no_new_privs": int(fields["NoNewPrivs"].strip()),
                 "cap_eff": int(fields["CapEff"].strip(), 16),
                 "cap_prm": int(fields["CapPrm"].strip(), 16),
                 "cap_inh": int(fields["CapInh"].strip(), 16),
                 "cap_bnd": int(fields["CapBnd"].strip(), 16),
                 "cap_amb": int(fields["CapAmb"].strip(), 16)})
print(json.dumps(sorted(rows, key=lambda r: r["pid"])))
"""

SOCKETS_PROGRAM = """\
import glob, json, os
paths = ["/var/run/docker.sock", "/run/docker.sock", "/run/containerd/containerd.sock",
         "/run/podman/podman.sock", "/var/run/podman/podman.sock"]
paths += glob.glob("/run/user/*/docker.sock") + glob.glob("/run/user/*/podman/podman.sock")
print(json.dumps({"present": sorted(p for p in paths if os.path.lexists(p)),
                  "docker_host": "DOCKER_HOST" in os.environ}))
"""

EGRESS_PROGRAM = """\
import json, socket, sys
proxy, port, allowed, other = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
names = sys.argv[5:]
def via_proxy(host):
    try:
        s = socket.create_connection((proxy, port), timeout=10)
    except OSError as e:
        return {"error": type(e).__name__}
    try:
        s.sendall(("CONNECT %s:443 HTTP/1.1\\r\\nHost: %s:443\\r\\n\\r\\n" % (host, host)).encode("ascii"))
        data = b""
        while b"\\r\\n" not in data and len(data) < 4096:
            chunk = s.recv(1024)
            if not chunk:
                break
            data += chunk
        parts = data.split(b"\\r\\n", 1)[0].decode("latin-1").split()
        return {"status": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None}
    except OSError as e:
        return {"error": type(e).__name__}
    finally:
        s.close()
def direct(host):
    try:
        socket.create_connection((host, 443), timeout=10).close()
        return {"connected": True}
    except OSError as e:
        return {"connected": False, "error": type(e).__name__}
def resolves(name):
    try:
        socket.getaddrinfo(name, 443)
        return True
    except OSError:
        return False
print(json.dumps({"via_proxy": {allowed: via_proxy(allowed), other: via_proxy(other)}, "direct": direct(allowed),
                  "resolves": {n: resolves(n) for n in names}}))
"""

# R4-2 (lane vendor-b11 round 4, glitch-26's ruling, Mon 19 Oct 2026): arms O's and G's `--version` never touch the
# take's config folder. Codex's arg0 dispatch (rust-v0.162.1 arg0/src/lib.rs 158-162, 355-401) leaves tmp/arg0 and a
# codex-arg0 folder under CODEX_HOME before clap's --version exit, and before turn 1 the config folder must hold exactly
# the placed set (run_take.check_config_folder). So the probe makes one fresh folder under the take's /tmp tmpfs
# (VERSION_PROBE_ROOT; neither the config folder nor the run tree), runs the harness with its config home and HOME both
# on it (VERSION_PROBE_HOMES), discards it, and passes the harness's output and exit code through. A folder that cannot
# be discarded fails the probe. Arm A's probe is unchanged (CLAUDE_CONFIG_DIR on the config mount).
VERSION_PROBE_ROOT = "/tmp"
VERSION_PROBE_HOMES = {run_take.CODEX: ("CODEX_HOME", "HOME"), run_take.GEMINI: ("GEMINI_CLI_HOME", "HOME")}
VERSION_PROBE_PROGRAM = """\
import os, shutil, subprocess, sys, tempfile
root, names, argv = sys.argv[1], sys.argv[2].split(","), sys.argv[3:]
home = tempfile.mkdtemp(prefix="version-home-", dir=root)
env = dict(os.environ)
env.update({n: home for n in names})
try:
    done = subprocess.run(argv, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=50)
finally:
    shutil.rmtree(home)
sys.stdout.write(done.stdout.decode("utf-8", "replace"))
sys.stderr.write(done.stderr.decode("utf-8", "replace"))
sys.exit(done.returncode)
"""

# PF1-L3 (m9): the direct-egress probe. It reads /proc/net/route only (never under the run tree) and prints
# {"routes", "gateway_candidates", "gateway": {address: {port: result}}, "targets": {label: result}}, each result
# {"address", "connected"} plus the error's type name when no connection was made.
DIRECT_PROGRAM = """\
import concurrent.futures, json, socket, struct, sys
timeout, ports, fixed = float(sys.argv[1]), [int(p) for p in sys.argv[2].split(",")], sys.argv[3:]
def ip(h):
    return socket.inet_ntoa(struct.pack("<I", int(h, 16)))
rows, cands = [], set()
with open("/proc/net/route") as fh:
    for line in fh.read().splitlines()[1:]:
        f = line.split()
        if len(f) < 8:
            continue
        rows.append({"iface": f[0], "destination": ip(f[1]), "gateway": ip(f[2]), "mask": ip(f[7])})
        if f[2] != "00000000":
            cands.add(ip(f[2]))
        elif f[1] != "00000000" and f[7].upper() != "FFFFFFFF":
            net = int.from_bytes(struct.pack("<I", int(f[1], 16)), "big")
            cands.add(socket.inet_ntoa((net + 1).to_bytes(4, "big")))
def attempt(address, port):
    try:
        socket.create_connection((address, port), timeout=timeout).close()
        return {"address": "%s:%d" % (address, port), "connected": True}
    except OSError as e:
        return {"address": "%s:%d" % (address, port), "connected": False, "error": type(e).__name__}
jobs = {("gateway", a, p): (a, p) for a in sorted(cands) for p in ports}
for t in fixed:
    label, _, where = t.partition("=")
    address, _, port = where.rpartition(":")
    jobs[("target", label, None)] = (address, int(port))
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(jobs))) as pool:
    got = dict(zip(jobs, pool.map(lambda k: attempt(*jobs[k]), list(jobs))))
gateway = {}
for (kind, a, p), r in got.items():
    if kind == "gateway":
        gateway.setdefault(a, {})[str(p)] = r
print(json.dumps({"routes": rows, "gateway_candidates": sorted(cands), "gateway": gateway,
                  "targets": {a: r for (kind, a, p), r in got.items() if kind == "target"}}))
"""

PROGRAMS = {"identity": IDENTITY_PROGRAM, "cgroup": CGROUP_PROGRAM, "listing": LISTING_PROGRAM,
            "processes": PROCESSES_PROGRAM, "sockets": SOCKETS_PROGRAM, "egress": EGRESS_PROGRAM,
            "watcher-caps": PROCESSES_PROGRAM, "direct-egress": DIRECT_PROGRAM}


def _proxy_port() -> str:
    """The proxy's port, derived from run_take.PROXY_URL (never typed apart from it)."""
    m = re.fullmatch(r"http://([a-z0-9-]+):([0-9]+)", run_take.PROXY_URL)
    if m is None or m.group(1) != run_take.PROXY_ALIAS:
        raise run_take.Refused("PROXY_URL is http://<alias>:<port>")
    return m.group(2)


def _config_home_values(harness: str) -> dict:
    """The harness's non-secret config-home variable, so `--version` reads and writes only the config folder."""
    return {k: v for k, v in run_take.HARNESS_ENV[harness].items() if k in run_take.config_home_names()}


def _py(program: str, *args: str) -> list:
    return ["python3", "-I", "-B", "-c", program, *args]


def _version_argv(agent, harness: str) -> tuple:
    """The harness-version probe's argv: for codex and gemini the throwaway-home program (R4-2), for claude-code the
    command itself with its config home on the config mount."""
    if harness in VERSION_PROBE_HOMES:
        return agent(_py(VERSION_PROBE_PROGRAM, VERSION_PROBE_ROOT, ",".join(VERSION_PROBE_HOMES[harness]),
                         *VERSION_COMMANDS[harness]))
    return agent(list(VERSION_COMMANDS[harness]), _config_home_values(harness))


# ------------------------------------------------------------------------------------------------- the probes
@dataclass(frozen=True)
class Probe:
    id: str
    argv: tuple | None = None
    read: Callable | None = None


PROBE_IDS = ("identity", "take-inspect", "take-image-manifest", "harness-version", "cgroup", "listing", "processes", "sidecar-inspect",
             "sidecar-image-manifest", "proxy-inspect", "egress-image-manifest", "egress-launch", "health",
             "watcher-caps", "sockets", "egress", "study-folders", "take-network-inspect", "direct-egress")
PROBE_TIMEOUT_S = 60


def _check_hosts(hosts) -> dict:
    if not isinstance(hosts, dict) or set(hosts) != set(run_take.LOGIN_VARIABLE):
        raise run_take.Refused(f"hosts must name exactly the harnesses {sorted(run_take.LOGIN_VARIABLE)}")
    for h in hosts.values():
        if not isinstance(h, str) or not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+", h):
            raise run_take.Refused("every host is a lower-case DNS name")
    if len(set(hosts.values())) != len(hosts):
        raise run_take.Refused("each harness has its own host")
    return hosts


def refused_names(harness: str, hosts: dict) -> list:
    """github.com, huggingface.co and the other harnesses' hosts: none may resolve from the take."""
    run_take._known_harness(harness)
    _check_hosts(hosts)
    return list(BLOCKED_NAMES) + sorted(v for k, v in hosts.items() if k != harness)


def direct_target_args() -> list:
    """PF1-L3 (m9): DIRECT_TARGETS as the direct-egress program's label=address:port arguments, in order."""
    return [f"{label}={address}:{port}" for label, (address, port) in DIRECT_TARGETS.items()]


def _read_health(path: str):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _study_folders(run_tree: str):
    if _is_pending(STUDY_PATHS):
        return {"pending": True}
    return {p: os.path.lexists(os.path.join(run_tree, p)) for p in STUDY_PATHS}


def probes(spec, *, take_id: str, sidecar_id: str, harness: str, hosts: dict, evidence_dir: str,
           sidecar_image: str, proxy_id: str, proxy_image: str) -> tuple:
    """Every probe, in PROBE_IDS order. `sidecar_image` is the image the sidecar launch expects (its manifest is read);
    `proxy_id` is the egress proxy container and `proxy_image` the image the launch record created it from (O-1)."""
    run_take.check_spec(spec)
    run_take._known_harness(harness)
    _check_hosts(hosts)
    run_take._check_id(take_id, "take id")
    run_take._check_id(sidecar_id, "sidecar id")
    if not isinstance(sidecar_image, str) or not IMAGE_ID_SHAPE.fullmatch(sidecar_image):
        raise run_take.Refused("the sidecar image must be a sha256 image id")
    run_take._check_id(proxy_id, "proxy id")
    if not isinstance(proxy_image, str) or not IMAGE_ID_SHAPE.fullmatch(proxy_image):
        raise run_take.Refused("the proxy image must be a sha256 image id")
    evidence_dir = run_take._abs_path(evidence_dir, "evidence_dir")
    agent = lambda inner, home=None: tuple(run_take.agent_exec_argv(take_id, inner, workdir="/",  # noqa: E731
                                                                     config_home=home))
    inspect = lambda cid: (run_take.RUNTIME_CLIENT, "container", "inspect", cid)  # noqa: E731
    run_tree = spec.run_tree
    return (
        Probe("identity", agent(_py(IDENTITY_PROGRAM))),
        Probe("take-inspect", inspect(take_id)),
        Probe("take-image-manifest", (run_take.RUNTIME_CLIENT, "image", "inspect", "--platform", IMAGE_PLATFORM,
                                      "--format", "{{json .Id}}", spec.image)),
        Probe("harness-version", _version_argv(agent, harness)),
        Probe("cgroup", agent(_py(CGROUP_PROGRAM, CGROUP_ROOT, "cpu.max", "memory.max", "memory.low", "pids.max"))),
        Probe("listing", agent(_py(LISTING_PROGRAM, SIDECAR_EVIDENCE_MOUNT, evidence_dir))),
        Probe("processes", agent(_py(PROCESSES_PROGRAM))),
        Probe("sidecar-inspect", inspect(sidecar_id)),
        Probe("sidecar-image-manifest", (run_take.RUNTIME_CLIENT, "image", "inspect", "--platform", IMAGE_PLATFORM,
                                         "--format", "{{json .Id}}", sidecar_image)),
        Probe("proxy-inspect", inspect(proxy_id)),
        Probe("egress-image-manifest", (run_take.RUNTIME_CLIENT, "image", "inspect", "--platform", IMAGE_PLATFORM,
                                        "--format", "{{json .Id}}", proxy_image)),
        Probe("egress-launch", read=lambda: proxy_image),
        Probe("health", read=lambda: _read_health(os.path.join(evidence_dir, HEALTH))),
        Probe("watcher-caps", (run_take.RUNTIME_CLIENT, "exec", "--user", sidecar_contract.WATCHER_USER,
                               sidecar_id, *_py(PROCESSES_PROGRAM))),
        Probe("sockets", agent(_py(SOCKETS_PROGRAM))),
        Probe("egress", agent(_py(EGRESS_PROGRAM, run_take.PROXY_ALIAS, _proxy_port(), hosts[harness],
                                  OTHER_HOST_VIA_PROXY, *refused_names(harness, hosts)))),
        Probe("study-folders", read=lambda: _study_folders(run_tree)),
        Probe("take-network-inspect", (run_take.RUNTIME_CLIENT, "network", "inspect", spec.network)),  # pf1-gateway
        Probe("direct-egress", agent(_py(DIRECT_PROGRAM, str(DIRECT_TIMEOUT_S), ",".join(map(str, GATEWAY_PORTS)),
                                         *direct_target_args()))),       # PF1-L3 (m9)
    )


def run(runtime, probe_list, *, begin_reply=None, caller_env=None) -> dict:
    """Collect every probe's raw record. A probe that cannot run is recorded with its error, never skipped.
    `begin_reply` is the sidecar's parsed `begin` reply (its `unreadable_consequential` folds into preflight)."""
    env = run_take.runtime_env(caller_env)
    raw = {}
    for p in probe_list:
        try:
            if p.read is not None:
                raw[p.id] = {"value": p.read()}
            else:
                c = runtime.run(list(p.argv), env=env, timeout=PROBE_TIMEOUT_S)
                raw[p.id] = {"returncode": c.returncode, "stdout": c.stdout, "stderr": c.stderr}
        except Exception as exc:  # recorded as failed; the check that needs it fails
            raw[p.id] = {"error": type(exc).__name__}
    raw["sidecar-begin"] = {"value": begin_reply} if begin_reply is not None else {"error": "no begin reply"}
    return raw


# --------------------------------------------------------------------------------------------------- judging
class _Fail(Exception):
    pass


def _json_out(raw: dict, pid: str):
    r = raw.get(pid)
    if not isinstance(r, dict):
        raise _Fail(f"probe {pid} is missing")
    if "error" in r:
        raise _Fail(f"probe {pid} failed to run ({r['error']})")
    if r.get("returncode") != 0:
        raise _Fail(f"probe {pid} exited {r.get('returncode')}")
    try:
        return json.loads(r.get("stdout", ""))
    except ValueError:
        raise _Fail(f"probe {pid} printed no JSON") from None


def _value(raw: dict, pid: str):
    r = raw.get(pid)
    if not isinstance(r, dict):
        raise _Fail(f"probe {pid} is missing")
    if "error" in r:
        raise _Fail(f"probe {pid} failed to run ({r['error']})")
    if "value" not in r:
        raise _Fail(f"probe {pid} recorded no value")
    return r["value"]


def _inspect_obj(raw: dict, pid: str) -> dict:
    doc = _json_out(raw, pid)
    if not (isinstance(doc, list) and len(doc) == 1 and isinstance(doc[0], dict)):
        raise _Fail(f"probe {pid} is not exactly one inspect object")
    return doc[0]


def _lock(lock: dict, key: str):
    v = lock[key]
    if _is_pending(v):
        raise _Fail(f"lock {key} is PENDING")
    return v


def _need(cond: bool, detail: str):
    if not cond:
        raise _Fail(detail)


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _check_agent(raw, spec, lock, harness, hosts, sidecar_expect, *_):
    who = _json_out(raw, "identity")
    _need(_lock(lock, "users.agent.uid") == AGENT_UID, "the lock's agent uid is not the agent user's")
    _need(who.get("uid") == AGENT_UID and who.get("uid") != 0, f"the exec ran as uid {who.get('uid')}")
    st = who.get("status") or {}
    for cap in ("CapEff", "CapPrm", "CapBnd"):
        vals = st.get(cap)
        _need(isinstance(vals, list) and len(vals) == 1 and re.fullmatch(r"[0-9a-fA-F]+", vals[0]) is not None
              and int(vals[0], 16) == 0, f"{cap} is not zero")
    _need(st.get("NoNewPrivs") == ["1"], "NoNewPrivs is not 1")
    return f"uid {AGENT_UID}, no capability, no new privileges"


def _manifest(raw, pid: str) -> str:
    try:
        manifest = json.loads(_plain(raw, pid))
    except ValueError:
        raise _Fail(f"probe {pid} is not one JSON string") from None
    _need(isinstance(manifest, str), f"probe {pid} is not one JSON string")
    return manifest


def _check_image(raw, spec, lock, harness, hosts, sidecar_expect, evidence_dir, sidecar_lock, egress_lock, *_):
    obj = _inspect_obj(raw, "take-inspect")
    if _is_pending(run_take.INSPECT_STATUS):
        raise _Fail("the inspect spellings are PENDING")
    image = _lock(lock, "image_id")
    got = _facts(obj, ("image",))["image"]
    _need(got == image and spec.image == image, f"the take's image {got} is not the lock's {image}")
    # The content identity (ruling (a)): the platform image manifest, which names the config and every layer.
    want = _lock(lock, "manifest_digest")
    manifest = _manifest(raw, "take-image-manifest")
    _need(manifest == want, f"the take image's {IMAGE_PLATFORM} manifest {manifest} is not the lock's {want}")
    # LW-7: the sidecar's image, by its own lock's id and platform manifest.
    side_id, side_want = _lock(sidecar_lock, "image_id"), _lock(sidecar_lock, "manifest_digest")
    _need(isinstance(sidecar_expect, dict) and sidecar_expect.get("image") == side_id,
          f"the sidecar launch's image is not the sidecar lock's {side_id}")
    _need(_inspect_obj(raw, "sidecar-inspect").get("Image") == side_id,
          f"the running sidecar's image is not the sidecar lock's {side_id}")
    side = _manifest(raw, "sidecar-image-manifest")
    _need(side == side_want, f"the sidecar image's {IMAGE_PLATFORM} manifest {side} is not its lock's {side_want}")
    # O-1: the egress proxy's image, by its own lock's id (launched and running) and platform manifest.
    egress_id, egress_want = _lock(egress_lock, "image_id"), _lock(egress_lock, "manifest_digest")
    _need(_value(raw, "egress-launch") == egress_id, f"the proxy was not launched from the egress lock's {egress_id}")
    _need(_inspect_obj(raw, "proxy-inspect").get("Image") == egress_id,
          f"the running proxy's image is not the egress lock's {egress_id}")
    egress = _manifest(raw, "egress-image-manifest")
    _need(egress == egress_want, f"the egress image's {IMAGE_PLATFORM} manifest {egress} is not its lock's {egress_want}")
    return "the take's, the sidecar's and the egress proxy's images are their locks', by id and by platform manifest"


def _check_version(raw, spec, lock, harness, *_):
    want = _lock(lock, "harness.version")
    pattern = VERSION_PATTERNS[harness]
    if _is_pending(pattern):
        raise _Fail(f"the {harness} --version output form is PENDING")
    out = _plain(raw, "harness-version")
    m = re.fullmatch(pattern, out.strip())
    _need(m is not None and m.group(1) == want, f"{harness} --version does not read the lock's {want}")
    return f"{harness} {want}"


def _plain(raw, pid):
    r = raw.get(pid)
    if not isinstance(r, dict) or "error" in r or r.get("returncode") != 0:
        raise _Fail(f"probe {pid} is missing or failed")
    return r.get("stdout", "")


def _check_take_inspect(raw, spec, *_):
    bad = inspect_mismatches(_inspect_obj(raw, "take-inspect"), expected_take_inspect(spec), kind="take")
    _need(not bad, "; ".join(bad))
    return "a read-only root, exactly the two bind mounts and the tmpfs mounts, and every inspected fact equals the spec's"


def _check_limits(raw, spec, *_):
    got = _json_out(raw, "cgroup")
    quota = int(Decimal(spec.cpus) * CPU_PERIOD)
    want = {"cpu.max": f"{quota} {CPU_PERIOD}", "memory.max": str(spec.memory),
            "memory.low": str(spec.memory_reservation), "pids.max": str(spec.pids_limit)}
    bad = [f"{k} reads {got.get(k)!r}, not {v!r}" for k, v in want.items() if got.get(k) != v]
    _need(not bad, "; ".join(bad))
    return "cpu, memory and pids limits read back as set"


def _check_evidence(raw, spec, lock, harness, hosts, sidecar_expect, evidence_dir, *_):
    got = _json_out(raw, "listing")
    _need(isinstance(got, dict) and len(got) == 2 and SIDECAR_EVIDENCE_MOUNT in got,
          "the listing did not try both paths")
    _need(evidence_dir in got, f"the listing did not try the evidence folder preflight judges ({evidence_dir})")
    listed = [p for p, v in got.items() if v == "listed"]
    _need(not listed, f"the agent listed {listed}")
    return "neither the sidecar mount nor the host path lists"


def _check_watcher_invisible(raw, spec, lock, *_):
    _need(_lock(lock, "users.watcher.uid") == WATCHER_UID, "the lock's watcher uid is not WATCHER_UID")
    _need(_lock(lock, "users.keepalive.uid") == KEEPALIVE_UID, "the lock's keep-alive uid is not the keep-alive's")
    rows = _json_out(raw, "processes")
    _need(isinstance(rows, list), "the process table is not a list")
    _need(not [r for r in rows if isinstance(r, dict) and "unreadable" in r],
          "a process the agent could not read: a finding, never a skip")
    _need(all(isinstance(r, dict) and _int(r.get("pid")) and _int(r.get("uid")) for r in rows),
          "a process row is off its shape")
    _need(not [r for r in rows if r["uid"] == WATCHER_UID], "a process of the watcher's uid is visible")
    _need([(r["pid"], r["uid"]) for r in rows] == [(1, KEEPALIVE_UID)],
          f"the only other process is not PID 1 of the keep-alive uid: {[(r['pid'], r['uid']) for r in rows]}")
    return "only PID 1 (the keep-alive) is visible"


def _evidence_source_problems(exp: dict, evidence_dir: str) -> list:
    """CP2-preflight-3: the sidecar's read-write evidence mount takes its source from exactly the folder preflight
    reads (lexical, normalised absolute paths, as the probes use; no host path is resolved)."""
    sources = [m.get("source") for m in exp["mounts"] if isinstance(m, dict) and m.get("destination")
               == SIDECAR_EVIDENCE_MOUNT]
    return [] if sources == [evidence_dir] else [f"the sidecar's evidence mount source {sources} is not the evidence "
                                                 f"folder preflight reads ({evidence_dir})"]


def _check_sidecar(raw, spec, lock, harness, hosts, sidecar_expect, evidence_dir, *_):
    exp = sidecar_expect
    _need(isinstance(exp, dict) and set(exp) == set(SIDECAR_EXPECT_KEYS),
          f"sidecar_expect must name exactly {list(SIDECAR_EXPECT_KEYS)}")
    still = sorted(k for k, v in exp.items() if _is_pending(v))
    _need(not still, f"sidecar_expect PENDING: {', '.join(still)}")
    _need(exp["user"] == sidecar_contract.BOOT_USER, "the sidecar launch does not use the fixed privilege-drop bootstrap")
    _need(exp["network_mode"] == "none", "the sidecar's expected network is not none")
    _need(exp["security_opt"] == ["no-new-privileges"], "the sidecar's expected security option is not no-new-privileges")
    _need([m.get("destination") for m in exp["mounts"] if isinstance(m, dict) and m.get("rw") is True]
          == [SIDECAR_EVIDENCE_MOUNT], f"the sidecar's one read-write mount is not {SIDECAR_EVIDENCE_MOUNT}")
    _need(exp["cap_drop"] == ["ALL"] and isinstance(exp["cap_add"], list)
          and sorted(exp["cap_add"]) == sorted(sidecar_contract.BOOT_INSPECT_CAPABILITIES),
          "the sidecar drops ALL and adds exactly its registered bootstrap capabilities")
    _need(exp["privileged"] is False and exp["pid_mode"] == "", "the sidecar is privileged or shares a pid space")
    prefix = [*sidecar_contract.WATCHER_LAUNCHER, *sidecar_contract.INTERPRETER, sidecar_contract.PROGRAM, "serve"]
    _need(isinstance(exp["cmd"], list) and exp["cmd"][:len(prefix)] == prefix and exp["entrypoint"] == [],
          "the sidecar does not exec the fixed privilege-drop launcher")
    want_mounts = [{"source": spec.run_tree, "destination": spec.run_tree, "rw": False}]
    _need(isinstance(exp["mounts"], list) and len(exp["mounts"]) == 2
          and [m for m in exp["mounts"] if m.get("destination") == spec.run_tree] == want_mounts
          and [m.get("rw") for m in exp["mounts"] if m.get("destination") != spec.run_tree] == [True],
          "the sidecar's mounts are not the run tree read-only and one read-write evidence folder")
    _need(not _evidence_source_problems(exp, evidence_dir), "; ".join(_evidence_source_problems(exp, evidence_dir)))
    inspected = _inspect_obj(raw, "sidecar-inspect")
    _need(inspected.get("Config", {}).get("Cmd") == exp["cmd"], "the sidecar command differs in order or content")
    bad = inspect_mismatches(inspected, exp, kind="sidecar")
    _need(not bad, "; ".join(bad))
    return "no network, its own process space, the run tree read-only, fixed boot-only capability set"


def _check_watcher_started(raw, *_):
    health = _value(raw, "health")
    _need(isinstance(health, list) and health, "no health record")
    _need(all(isinstance(h, dict) for h in health), "a health record is off its shape")
    _need(health[-1].get("kind") == "watcher-start", "the last health record is not a watcher-start")
    return "the watcher's start record is the last health record"


def _check_watcher_cap(raw, *_):
    rows = _json_out(raw, "watcher-caps")
    _need(isinstance(rows, list) and not [r for r in rows if isinstance(r, dict) and "unreadable" in r],
          "a process in the sidecar could not be read: a finding, never a skip")
    _need(isinstance(rows, list) and all(isinstance(r, dict) and _int(r.get("pid")) and _int(r.get("cap_eff"))
                                         and _int(r.get("uid")) for r in rows), "the sidecar's table is off its shape")
    others = [r for r in rows if r["pid"] != 1]
    _need(others, "no watcher process is running in the sidecar")
    _need(sum(r["pid"] == 1 for r in rows) == 1, "the sidecar has no unique PID 1 watcher")
    bad = [r for r in rows if r["uid"] != WATCHER_UID
           or r.get("uids") != [WATCHER_UID] * 4 or r.get("gids") != [WATCHER_UID] * 4
           or r.get("groups") != [] or r.get("no_new_privs") != 1
           or any(r.get(k) != WATCHER_CAP_EFF for k in ("cap_eff", "cap_prm", "cap_inh", "cap_bnd", "cap_amb"))]
    _need(not bad, f"a watcher process does not hold exactly CAP_DAC_READ_SEARCH as {WATCHER_UID}: "
                   f"{[(r['pid'], r['uid'], hex(r['cap_eff'])) for r in bad]}")
    return "the watcher holds exactly CAP_DAC_READ_SEARCH"


def _check_consequential(raw, *_):
    reply = _value(raw, "sidecar-begin")
    _need(isinstance(reply, dict) and reply.get("ok") is True and reply.get("command") == "begin",
          "the sidecar's begin did not reply ok")
    unread = reply.get(UNREADABLE_CONSEQUENTIAL_KEY)
    _need(isinstance(unread, list), f"the begin reply carries no {UNREADABLE_CONSEQUENTIAL_KEY} list")
    _need(not unread, f"consequential paths unreadable before the first turn: {unread}")
    return "every consequential path is readable"


def _check_socket(raw, spec, *_):
    got = _json_out(raw, "sockets")
    _need(isinstance(got, dict) and got.get("present") == [], f"runtime sockets present: {got.get('present')}")
    _need(got.get("docker_host") is False, "DOCKER_HOST is set in the take")
    obj = _inspect_obj(raw, "take-inspect")
    if _is_pending(run_take.INSPECT_STATUS):
        raise _Fail("the inspect spellings are PENDING")
    env = _facts(obj, ("env",))["env"]
    _need(isinstance(env, list) and not [e for e in env if str(e).split("=", 1)[0] == "DOCKER_HOST"],
          "DOCKER_HOST is in the take's create-time environment")
    names = {str(e).split("=", 1)[0] for e in env}
    _need(not names.intersection(run_take.GEMINI_MODE_ROUTE_VARIABLES),
          "Gemini mode-route variable is in the take's create-time environment")
    refused = set(run_take.LOGIN_VARIABLE.values()) | set(run_take.refused_variables(run_take.CLAUDE_CODE))
    # glitch-06 (14 Oct 2026): the names the Codex CLI extends per variable are refused by prefix at create time too
    leaked = sorted(n for n in names if n in refused or n.startswith(run_take.REFUSED_NAME_PREFIXES))
    _need(not leaked, f"credential names in the take's create-time environment: {leaked}")
    return "no runtime socket, no DOCKER_HOST, no credential name at create"


def _egress(raw):
    got = _json_out(raw, "egress")
    _need(isinstance(got, dict), "the egress record is not an object")
    return got


def _check_allowed(raw, spec, lock, harness, hosts, *_):
    host = _check_hosts(hosts)[harness]
    st = (_egress(raw).get("via_proxy") or {}).get(host) or {}
    _need(st.get("status") == 200, f"CONNECT {host}:443 through the proxy answered {st}")
    return f"CONNECT {host}:443 answered 200"


def _check_other(raw, *_):
    st = (_egress(raw).get("via_proxy") or {}).get(OTHER_HOST_VIA_PROXY) or {}
    _need(_int(st.get("status")) and st["status"] != 200,
          f"CONNECT {OTHER_HOST_VIA_PROXY}:443 through the proxy was not refused: {st}")
    return f"CONNECT {OTHER_HOST_VIA_PROXY}:443 refused ({st['status']})"


def _check_direct(raw, *_):
    d = _egress(raw).get("direct") or {}
    _need(d.get("connected") is False, "a direct connection to the take's host was made")
    return "no direct connection"


def _check_names(raw, spec, lock, harness, hosts, *_):
    want = refused_names(harness, hosts)
    res = _egress(raw).get("resolves")
    _need(isinstance(res, dict) and sorted(res) == sorted(want), f"the names tried are not {want}")
    resolved = [n for n in want if res[n] is not False]
    _need(not resolved, f"resolved from the take: {resolved}")
    return f"none of {want} resolves"


def _check_study(raw, *_):
    if _is_pending(STUDY_PATHS):
        raise _Fail("the study folders' list is PENDING (CP5)")
    _need(isinstance(STUDY_PATHS, (list, tuple)) and STUDY_PATHS, "the study folders' list is empty")
    got = _value(raw, "study-folders")
    _need(isinstance(got, dict) and sorted(got) == sorted(STUDY_PATHS), "not every study folder was looked for")
    present = [p for p in STUDY_PATHS if got[p] is not False]
    _need(not present, f"study folders present in the run tree: {present}")
    return f"{len(STUDY_PATHS)} study folders absent"


def leak_hits(text: str, words) -> list:
    return [w for w in words if re.search(r"(?<![A-Za-z0-9])" + re.escape(w) + r"(?![A-Za-z0-9])", text,
                                          re.IGNORECASE)]


def _check_path_neutral(raw, spec, *_):
    if _is_pending(LEAK_WORDS):
        raise _Fail("the round's leak words are PENDING (CP5)")
    _need(isinstance(LEAK_WORDS, (list, tuple)) and LEAK_WORDS, "the leak words are empty")
    hits = leak_hits(spec.run_tree, LEAK_WORDS)
    _need(not hits, f"the run tree's path carries {hits}")
    return "the run tree's path carries no leak word"


def _direct(raw) -> dict:
    got = _json_out(raw, "direct-egress")
    _need(isinstance(got, dict) and isinstance(got.get("targets"), dict) and isinstance(got.get("gateway"), dict)
          and isinstance(got.get("gateway_candidates"), list), "the direct-egress record is not its shape")
    return got


def _target_refused(raw, label: str) -> str:
    want = "%s:%d" % DIRECT_TARGETS[label]
    r = _direct(raw)["targets"].get(label)
    _need(isinstance(r, dict) and r.get("address") == want, f"{want} ({label}) was not tried")
    _need(r.get("connected") is False, f"a direct connection to {want} ({label}) was made")
    return f"{want} refused ({r.get('error')})"


def _check_raw_ip(raw, *_):
    return "; ".join(_target_refused(raw, label) for label in RAW_IP_TARGETS)


def _check_metadata(raw, *_):
    return _target_refused(raw, METADATA_TARGET)


def _host_network_gateways(raw, spec) -> dict:
    """Lane pf1-gateway (glitch-45's ruling, Mon 26 Oct 2026): the host-side record of the take's network, read by
    `docker network inspect <spec.network>` (the take-network-inspect probe, run by the host like every inspect, never
    inside the take). It must be exactly one network object whose Id is the take spec's network; it gives
    {its Name: (its Id, every non-empty IPAM.Config Gateway)}. An unreadable or unbound record fails the check."""
    doc = _json_out(raw, "take-network-inspect")
    _need(isinstance(doc, list) and len(doc) == 1 and isinstance(doc[0], dict),
          "the take network's inspect is not exactly one network object")
    obj = doc[0]
    net_id = spec.network
    _need(isinstance(net_id, str) and bool(net_id) and obj.get("Id") == net_id,
          f"the network inspected host-side is not the take's network {net_id!r}")
    name = obj.get("Name")
    _need(isinstance(name, str) and bool(name), "the take network's inspect names no network name")
    ipam = obj.get("IPAM")
    _need(ipam is None or isinstance(ipam, dict), "the take network's IPAM record is not its shape")
    config = (ipam or {}).get("Config")
    _need(config is None or (isinstance(config, list) and all(isinstance(c, dict) for c in config)),
          "the take network's IPAM config is not its shape")
    gws = [c.get("Gateway") for c in config or []]
    _need(all(g is None or isinstance(g, str) for g in gws), "the take network's IPAM gateway is not its shape")
    return {name: (net_id, sorted({g for g in gws if g}))}


def _inspect_gateways(obj, host=None) -> list:
    """The gateways the probe must have tried, one or more per network the take is on. PF1-L3 (the lane orchestrator's
    ruling on review fb354328 finding 5, 24 Oct 2026): an empty Gateway on any of its networks (as an --internal
    network reports) refuses, fail closed, unless something host-side names it: the probe's candidates come from the
    take's own route table, so the check never passes on the route table's word alone. Lane pf1-gateway (glitch-45's
    ruling, 26 Oct 2026, w-o48's live reading: Docker reports an empty Gateway for an --internal network): `host` is
    _host_network_gateways' record; for the network it names (same name, and the same NetworkID where the take inspect
    gives one) its IPAM gateways are wanted beside any Gateway the take inspect names. A network with neither
    refuses."""
    nets = (obj.get("NetworkSettings") or {}).get("Networks") if isinstance(obj, dict) else None
    _need(isinstance(nets, dict) and nets, "the take inspect names no network, so its gateway cannot be shown")
    host = host or {}
    want, empty = set(), []
    for k, n in nets.items():
        own = n.get("Gateway") if isinstance(n, dict) else None
        if isinstance(own, str) and own:
            want.add(own)
        rec = host.get(k)
        bound = rec is not None and isinstance(n, dict) and n.get("NetworkID") in ("", None, rec[0])
        if bound and rec[1]:
            want.update(rec[1])
        elif not (isinstance(own, str) and own):
            empty.append(str(k))
    empty.sort()
    _need(not empty, f"the take inspect names no gateway for network(s) {empty}: the addresses tried cannot be bound "
                     f"to the take's own gateway, and no host-side record of the network names one (fail closed)")
    return sorted(want)


def _check_gateway(raw, spec, *_):
    got = _direct(raw)
    cands = got["gateway_candidates"]
    _need(bool(cands), "the take's route table names no gateway and no on-link network: nothing was tried")
    want = _inspect_gateways(_inspect_obj(raw, "take-inspect"), _host_network_gateways(raw, spec))
    missing = [g for g in want if g not in cands]
    _need(not missing, f"the take's gateway {missing} (its inspect or the host-side network record) was not among the "
                       f"addresses tried {cands}")
    answered = []
    for address in cands:
        ports = got["gateway"].get(address)
        _need(isinstance(ports, dict) and sorted(ports) == sorted(map(str, GATEWAY_PORTS)),
              f"gateway {address}: not every port of {list(GATEWAY_PORTS)} was tried")
        made = [p for p, r in ports.items() if not isinstance(r, dict) or r.get("connected") is not False]
        _need(not made, f"a direct connection to gateway {address} port(s) {sorted(made, key=int)} was made")
        answered += [f"{address}:{p}" for p, r in ports.items() if r.get("error") == "ConnectionRefusedError"]
    tail = f"; answered refused (reachable, port closed): {sorted(answered)}" if answered else ""
    return f"no connection to {cands} on {list(GATEWAY_PORTS)}{tail}"


CHECKS = {
    "agent-non-root": _check_agent, "image-matches-lock": _check_image,
    "harness-version-matches-lock": _check_version, "take-inspect-matches-spec": _check_take_inspect,
    "limits-apply": _check_limits, "evidence-out-of-reach": _check_evidence,
    "watcher-invisible": _check_watcher_invisible, "sidecar-isolated": _check_sidecar,
    "watcher-started": _check_watcher_started, "watcher-capability": _check_watcher_cap,
    "consequential-paths-readable": _check_consequential, "no-container-socket": _check_socket,
    "egress-allowed-host": _check_allowed, "egress-other-host-refused": _check_other,
    "egress-direct-refused": _check_direct, "names-do-not-resolve": _check_names,
    "study-folders-absent": _check_study, "run-tree-path-neutral": _check_path_neutral,
    "egress-raw-ip-refused": _check_raw_ip, "egress-metadata-refused": _check_metadata,
    "egress-gateway-refused": _check_gateway,
}
# The C3 routing name (interface 11, fixed by lane w4h): the sidecar's reply field. Before the first turn a
# non-empty list folds into preflight_ok false (consequential-paths-readable).
UNREADABLE_CONSEQUENTIAL_KEY = "unreadable_consequential"
UNREADABLE_CONSEQUENTIAL_ROW = "unreadable-consequential-path"


def evaluate(raw: dict, *, spec, lock: dict, sidecar_expect: dict, harness: str, hosts: dict,
             evidence_dir: str, sidecar_lock: dict, egress_lock: dict) -> dict:
    """The preflight record, pure: every check of PREFLIGHT_CHECKS in order, `ok` only when every one passed.

    `evidence_dir` is required and has no default (CP2-preflight-3): the folder the probes read, which the sidecar's
    evidence mount source must equal. A missing, relative or unnormalised one refuses (run_take.Refused)."""
    if not isinstance(lock, dict) or set(lock) != set(LOCK_KEYS):
        raise ValueError(f"lock must hold exactly {list(LOCK_KEYS)}")
    if not isinstance(sidecar_lock, dict) or set(sidecar_lock) != set(SIDECAR_LOCK_KEYS):
        raise ValueError(f"sidecar_lock must hold exactly {list(SIDECAR_LOCK_KEYS)}")
    if not isinstance(egress_lock, dict) or set(egress_lock) != set(EGRESS_LOCK_KEYS):
        raise ValueError(f"egress_lock must hold exactly {list(EGRESS_LOCK_KEYS)}")
    run_take._known_harness(harness)
    evidence_dir = run_take._abs_path(evidence_dir, "evidence_dir")
    checks = []
    for cid in PREFLIGHT_CHECKS:
        fn = CHECKS.get(cid)
        try:
            if fn is None:
                raise _Fail("no check is defined")
            detail, passed = fn(raw, spec, lock, harness, hosts, sidecar_expect, evidence_dir, sidecar_lock,
                                egress_lock), True
        except _Fail as e:
            detail, passed = str(e), False
        except Exception as e:  # a check that cannot read its records fails, never passes
            detail, passed = f"the check could not read its records ({type(e).__name__})", False
        checks.append({"id": cid, "ok": passed, "detail": detail})
    recorded = {"harness": harness,
                "harness_version_output": (raw.get("harness-version") or {}).get("stdout"),
                "token_visible_to_children": PENDING,
                "google_project_tier": GOOGLE_PROJECT_TIER if harness == run_take.GEMINI else "not-applicable",
                "watcher_processes": _safe(lambda: _json_out(raw, "watcher-caps")),
                "take_processes": _safe(lambda: _json_out(raw, "processes"))}
    ok = len(checks) == len(PREFLIGHT_CHECKS) and all(c["ok"] for c in checks)
    return {"ok": ok, "checks": checks, "recorded": recorded}


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


# ----------------------------------------------------------------------------- the lock and the composition (w6a)
def load_take_lock(lock_path: str, *, harness: str) -> dict:
    """The five LOCK_KEYS of the harness's take lock, read only through w4a's loader (CP2-preflight-2).

    image_lock.load (the closed schema, duplicate keys refused, bound to the Dockerfile beside it), then the lock
    must be the harness's own take image (TAKE_IMAGE: a sidecar, egress or other take's lock refuses), then
    image_lock.require_ready (every PENDING field refuses), then the projection. A caller passes a path, never a
    dictionary: there is no way in for a pre-flattened lock. Refusals raise (image_lock.LockError or NotReady,
    run_take.Refused); nothing defaults."""
    run_take._known_harness(harness)
    lock_path = run_take._abs_path(lock_path, "lock_path")
    lock = image_lock.load(lock_path)
    if lock["image"] != TAKE_IMAGE[harness]:
        raise run_take.Refused(f"the lock is the {lock['image']} image's, not {harness}'s take image "
                               f"{TAKE_IMAGE[harness]}")
    image_lock.require_ready(lock)
    # A schema-1 lock is never ready (its image_id is PENDING); were it to pass, its absent schema-2 field projects
    # as PENDING, which every check refuses, never as a value.
    return {k: (run_take._path_get(lock, k) if k != "manifest_digest" or k in lock else PENDING) for k in LOCK_KEYS}


def load_sidecar_lock(take_lock_path: str, *, harness: str) -> dict:
    """The sidecar lock's SIDECAR_LOCK_KEYS (LW-7), read only through w4a's loader: the box folder is the one the take
    lock was loaded from (image_lock.load has bound that lock to the Dockerfile beside it), the sidecar lock sits at
    SIDECAR_LOCK_PATH in it (image_lock.load binds it to the sidecar's Dockerfile), it must be the sidecar image's own
    lock, image_lock.require_ready, then the projection. Called after load_take_lock has accepted the take lock."""
    run_take._known_harness(harness)
    take_dir = os.path.dirname(run_take._abs_path(take_lock_path, "lock_path"))
    box = take_dir
    for part in reversed([p for p in TAKE_LOCK_DIRS[TAKE_IMAGE[harness]].split("/") if p]):
        if os.path.basename(box) != part:
            raise run_take.Refused(f"the take lock is not in its {part}/ folder")
        box = os.path.dirname(box)
    side = image_lock.load(os.path.join(box, SIDECAR_LOCK_PATH))
    if side["image"] != SIDECAR_LOCK_IMAGE:
        raise run_take.Refused(f"the sidecar lock is the {side['image']} image's")
    image_lock.require_ready(side)
    # As for the take lock: a schema-1 lock is never ready; were it to pass, its absent schema-2 field projects as
    # PENDING, which the check refuses, never as a value.
    return {k: side[k] if k in side else PENDING for k in SIDECAR_LOCK_KEYS}


def load_egress_lock(take_lock_path: str, *, harness: str) -> dict:
    """The egress lock's EGRESS_LOCK_KEYS (O-1), read only through w4a's loader from the take lock's box folder, as
    load_sidecar_lock reads the sidecar's: image_lock.load, the egress image's own lock, require_ready, projection."""
    run_take._known_harness(harness)
    box = os.path.dirname(run_take._abs_path(take_lock_path, "lock_path"))
    for part in reversed([p for p in TAKE_LOCK_DIRS[TAKE_IMAGE[harness]].split("/") if p]):
        if os.path.basename(box) != part:
            raise run_take.Refused(f"the take lock is not in its {part}/ folder")
        box = os.path.dirname(box)
    egress_lock = image_lock.load(os.path.join(box, EGRESS_LOCK_PATH))
    if egress_lock["image"] != EGRESS_LOCK_IMAGE:
        raise run_take.Refused(f"the egress lock is the {egress_lock['image']} image's")
    image_lock.require_ready(egress_lock)
    return {k: egress_lock[k] if k in egress_lock else PENDING for k in EGRESS_LOCK_KEYS}


def _proxy_launch_image(launched) -> str:
    """The image the launch record's one proxy-create step created the proxy from (its one sha256 image id)."""
    try:
        steps = [s for s in launched.steps if isinstance(s, dict) and s.get("step") == PROXY_CREATE_STEP]
    except (AttributeError, TypeError):
        raise run_take.Refused("the launch record carries no steps") from None
    if len(steps) != 1 or not isinstance(steps[0].get("argv"), list):
        raise run_take.Refused(f"the launch record holds {len(steps)} {PROXY_CREATE_STEP} steps, not one")
    ids = [a for a in steps[0]["argv"] if isinstance(a, str) and IMAGE_ID_SHAPE.fullmatch(a)]
    if len(ids) != 1:
        raise run_take.Refused(f"the {PROXY_CREATE_STEP} step names {len(ids)} image ids, not one")
    return ids[0]


def _launched_parts(launched) -> tuple:
    """(spec, take id, sidecar id) from a successful launch record, or a refusal before any runtime call."""
    try:
        ok, spec, network_id = launched.ok, launched.spec, launched.network_id
        take_id, sidecar_id = launched.take_id, launched.sidecar_id
    except AttributeError:
        raise run_take.Refused("launched must be the launch record run_take.launch returned") from None
    if ok is not True:
        raise run_take.Refused("the launch did not succeed: no preflight on a failed launch")
    if spec is None:
        raise run_take.Refused("the launch record carries no spec (Launched.spec)")
    run_take.check_spec(spec)
    run_take._check_id(take_id, "the launch record's take id")
    run_take._check_id(sidecar_id, "the launch record's sidecar id")
    if spec.network != network_id:
        raise run_take.Refused("Launched.spec is not on the network the launch made")
    return spec, take_id, sidecar_id


def collect_and_evaluate(runtime, *, launched, sidecar, lock_path: str, harness: str, hosts: dict, evidence_dir: str,
                         begin_reply, caller_env=None) -> dict:
    """The drive step's one preflight call (CP2-preflight-2): the lock through load_take_lock, the spec and ids from
    the launch record (`Launched.spec`), the probes built and run, then evaluate with the very same evidence folder
    and the sidecar's own expectation. Lock and launch-record refusals raise before any runtime call; it creates no
    container, runs no turn, reads no login, writes no record and tears nothing down (the drive step's lifecycle)."""
    lock = load_take_lock(lock_path, harness=harness)
    sidecar_lock = load_sidecar_lock(lock_path, harness=harness)
    egress_lock = load_egress_lock(lock_path, harness=harness)
    evidence_dir = run_take._abs_path(evidence_dir, "evidence_dir")
    spec, take_id, sidecar_id = _launched_parts(launched)
    try:
        expect = sidecar.expect
    except AttributeError:
        raise run_take.Refused("sidecar must be the SidecarLaunch the launch used") from None
    sidecar_image = expect.get("image") if isinstance(expect, dict) else None
    proxy_image = _proxy_launch_image(launched)
    probe_list = probes(spec, take_id=take_id, sidecar_id=sidecar_id, sidecar_image=sidecar_image, harness=harness,
                        hosts=hosts, proxy_id=launched.proxy_id, proxy_image=proxy_image, evidence_dir=evidence_dir)
    raw = run(runtime, probe_list, begin_reply=begin_reply, caller_env=caller_env)
    return evaluate(raw, spec=spec, lock=lock, sidecar_expect=expect, harness=harness, hosts=hosts,
                    evidence_dir=evidence_dir, sidecar_lock=sidecar_lock, egress_lock=egress_lock)


# ------------------------------------------------------------------------------------------------ the record
RECORD_NAME = "preflight.json"
EVIDENCE_FILES = ("ledger.jsonl", "access.jsonl", HEALTH, "snapshots", "blobs")


def write(record: dict, path: str) -> str:
    """Write the preflight record beside the evidence folder (ruling C2), never inside it, never over another."""
    if not isinstance(record, dict) or set(record) != {"ok", "checks", "recorded"} \
            or [c.get("id") for c in record["checks"]] != list(PREFLIGHT_CHECKS):
        raise run_take.Refused("the record is not a preflight record of PREFLIGHT_CHECKS")
    if record["ok"] is not all(c["ok"] is True for c in record["checks"]):
        raise run_take.Refused("the record's ok disagrees with its checks")
    path = run_take._abs_path(path, "preflight record path")
    folder = os.path.dirname(path)
    if os.path.basename(path) != RECORD_NAME:
        raise run_take.Refused(f"the preflight record is named {RECORD_NAME}")
    if os.path.basename(folder) == "evidence" or any(os.path.lexists(os.path.join(folder, f))
                                                     for f in EVIDENCE_FILES):
        raise run_take.Refused("the preflight record never goes inside the evidence folder")
    if os.path.lexists(path):
        raise run_take.Refused("a preflight record is never written over another")
    run_take._write_json(path, record)
    return path


# ------------------------------------------------------------------------------------------- after the take
# The Codex lease's ONE registered credential file (glitch-06, 14 Oct 2026; the owner's 13 Oct subscription amendment:
# cli_auth_credentials_store file, so the login lives at CODEX_HOME/auth.json, and CODEX_HOME is the per-take config
# folder, the lease home). Postflight admits exactly this file at exactly this path, and nothing else credential-shaped.
LEASE_CREDENTIAL = {run_take.CODEX: "auth.json"}
LEASE_CREDENTIAL_MAX_BYTES = 1024 * 1024


def _read_capped(path: str, cap: int, checked):
    """The bytes of the regular file the caller's lstat `checked` saw, opened without following a link, or None past
    `cap`. Never logged or returned in a message: callers compare them only. Opened non-blocking (a FIFO never blocks)
    and compared on the descriptor with `checked`: the same device, inode, links, mode (the file type with it) and
    owner, so the file read is the file checked (glitch-06, NIT 5). Anything else raises OSError, naming no contents."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    opened = os.fstat(fd)
    if (opened.st_dev, opened.st_ino, opened.st_nlink, opened.st_mode, opened.st_uid) != \
            (checked.st_dev, checked.st_ino, checked.st_nlink, checked.st_mode, checked.st_uid):
        os.close(fd)
        raise OSError(f"{os.path.basename(path)}: not the regular file that was checked")
    with os.fdopen(fd, "rb") as fh:
        data = fh.read(cap + 1)
    return None if len(data) > cap else data


def lease_credential_problems(config_dir: str, harness: str, listing: list) -> tuple:
    """(problems, the credential-shaped paths the lease admits) for a Codex lease home after the take.

    Admitted: at most one file, LEASE_CREDENTIAL[harness] at the folder's root, a regular file (never a link) with
    exactly one link, mode 600, owned by the reading user (the host user, after ownership.restore). Refused, each by
    the file's path and the rule, never its contents: a credential-shaped name anywhere else (a second auth file, a
    renamed auth file); a file anywhere else whose bytes equal the registered file's (a renamed copy, whatever its
    name); a symbolic link to the registered file or to a folder above it; a file the host cannot read (refused by
    path, never raised); the registered path as a link, a non-regular file, with another
    hard link, another mode or another owner. Absent is refused too (glitch-06, 14 Oct 2026): "exactly one registered
    credential file" means exactly one."""
    reg = LEASE_CREDENTIAL[harness]
    reg_path = os.path.join(config_dir, reg)
    problems, admitted, reg_bytes = [], [], None
    if os.path.lexists(reg_path):
        st = os.lstat(reg_path)
        if stat.S_ISLNK(st.st_mode):
            problems.append(f"{reg}: the registered credential must be a regular file, never a link")
        elif not stat.S_ISREG(st.st_mode):
            problems.append(f"{reg}: the registered credential must be a regular file")
        elif st.st_nlink != 1:
            problems.append(f"{reg}: the registered credential must have exactly one link")
        elif stat.S_IMODE(st.st_mode) != 0o600:
            problems.append(f"{reg}: the registered credential's mode must be 600")
        elif st.st_uid != os.getuid():
            problems.append(f"{reg}: the registered credential must be owned by the host user")
        else:
            try:
                reg_bytes = _read_capped(reg_path, LEASE_CREDENTIAL_MAX_BYTES, checked=st)
            except OSError:
                problems.append(f"{reg}: the registered credential is unreadable, or changed between its check "
                                f"and its read")
            else:
                if reg_bytes is None:
                    problems.append(f"{reg}: the registered credential is larger than "
                                    f"{LEASE_CREDENTIAL_MAX_BYTES} bytes")
                else:
                    admitted.append(reg)
    else:
        problems.append(f"{reg}: absent; the lease home must hold exactly one registered credential file")
    reg_real = os.path.realpath(reg_path)
    for rel in listing:
        if rel == reg:
            continue
        path = os.path.join(config_dir, rel)
        name = os.path.basename(rel)
        try:
            st = os.lstat(path)
        except OSError:
            problems.append(f"{rel}: unreadable after the take; the lease home must be readable whole")
            continue
        if stat.S_ISLNK(st.st_mode):
            real = os.path.realpath(path)
            if os.path.commonpath([real, reg_real]) == real \
                    or name in _credential_names() or CREDENTIAL_LIKE.search(name):
                problems.append(f"{rel}: a link to the registered credential, to a folder above it, "
                                f"or with a credential's name")
            continue
        if name in _credential_names() or CREDENTIAL_LIKE.search(name):
            problems.append(f"{rel}: a credential-shaped file outside the registered path {reg}")
            continue
        if reg_bytes is not None and stat.S_ISREG(st.st_mode) and st.st_size == len(reg_bytes):
            try:
                same = _read_capped(path, LEASE_CREDENTIAL_MAX_BYTES, checked=st) == reg_bytes
            except OSError:
                problems.append(f"{rel}: unreadable after the take; the lease home must be readable whole")
                continue
            if same:
                problems.append(f"{rel}: a copy of the registered credential under another name")
    return problems, admitted


def _credential_names() -> set:
    return {n for files in CREDENTIAL_FILES.values() for n, _source in files}


# Lane fold6/kill-leftovers (glitch-45's ruling (a), Sun 1 Nov 2026, under Javier's standing delegation): a claude-code
# take killed at its budget leaves Claude Code's peer-messaging pair, sessions/N.json and sessions/N.<64 hex>.key, in its
# config folder (a clean exit removes them; the lb5 live-box probe at 961e232d was held on the .key). postflight admits
# exactly that pair, bound to its producer: given the take's own session id and run tree (drive.py passes both), N.json
# must name that session and the take's own socket <run tree>/.tmp/cc-socks/N.sock. Without them nothing is admitted.
SESSION_PAIR_DIR = "sessions"
SESSION_PAIR_JSON = re.compile(r"(\d+)\.json")
SESSION_PAIR_KEY = re.compile(r"(\d+)\.[0-9a-f]{64}\.key")
SESSION_PAIR_MAX_BYTES = {"json": 64 * 1024, "key": 4 * 1024}


def session_pair(config_dir: str, listing: list, session_id: str, run_tree: str) -> tuple[list, list]:
    """(admitted [{name, size, uid, gid}], problems) for the config folder's sessions/ entries; never reads the key."""
    inside = sorted(p for p in listing if p.split(os.sep)[0] == SESSION_PAIR_DIR and p != SESSION_PAIR_DIR)
    jsons = [p for p in inside if SESSION_PAIR_JSON.fullmatch(os.path.basename(p)) and os.path.dirname(p) == SESSION_PAIR_DIR]
    keys = [p for p in inside if SESSION_PAIR_KEY.fullmatch(os.path.basename(p)) and os.path.dirname(p) == SESSION_PAIR_DIR]
    if len(jsons) != 1 or len(keys) != 1 or set(inside) != set(jsons + keys):
        return [], [f"sessions/ is not exactly one N.json and one N.<64 hex>.key: {inside}"]
    n = SESSION_PAIR_JSON.fullmatch(os.path.basename(jsons[0])).group(1)
    if SESSION_PAIR_KEY.fullmatch(os.path.basename(keys[0])).group(1) != n:
        return [], [f"the sessions/ pair names two processes: {inside}"]
    admitted = []
    for rel, kind in ((jsons[0], "json"), (keys[0], "key")):
        st = os.lstat(os.path.join(config_dir, rel))
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1 or st.st_size > SESSION_PAIR_MAX_BYTES[kind]:
            return [], [f"{rel} is not one regular file of at most {SESSION_PAIR_MAX_BYTES[kind]} bytes with one link"]
        admitted.append({"name": rel, "size": st.st_size, "uid": st.st_uid, "gid": st.st_gid})
    try:
        with open(os.path.join(config_dir, jsons[0]), encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, UnicodeError, ValueError) as e:
        return [], [f"{jsons[0]} does not parse ({type(e).__name__})"]
    sock = os.path.join(run_tree, ".tmp", "cc-socks", f"{n}.sock")
    if not isinstance(doc, dict) or doc.get("sessionId") != session_id or doc.get("messagingSocketPath") != sock:
        return [], [f"{jsons[0]} does not name this take's session and its socket .tmp/cc-socks/{n}.sock"]
    return admitted, []


def postflight(config_dir: str, harness: str, *, session_id: str | None = None, run_tree: str | None = None) -> dict:
    """The per-take config folder holds no credential file after a take; the full listing is recorded. A Codex lease
    home (LEASE_CREDENTIAL) holds exactly its one registered credential file, refusing it absent, and nothing else
    credential-shaped. Given the take's session id and run tree, a claude-code take's killed-process pair in sessions/
    is admitted when it is exactly the producer-bound pair (session_pair), and recorded (names, sizes, owners)."""
    run_take._known_harness(harness)
    config_dir = run_take._abs_path(config_dir, "config_dir")
    listing, problems = [], []
    if os.path.islink(config_dir) or not os.path.isdir(config_dir):
        problems.append("the config folder is not a folder")
    else:
        def onerror(e):
            problems.append(f"unreadable: {os.path.relpath(getattr(e, 'filename', config_dir) or config_dir, config_dir)}")
        for root, dirs, files in os.walk(config_dir, onerror=onerror, followlinks=False):
            for name in sorted(dirs) + sorted(files):
                listing.append(os.path.relpath(os.path.join(root, name), config_dir))
    admitted, session_admitted = [], []
    if harness in LEASE_CREDENTIAL and not problems:
        lease_problems, admitted = lease_credential_problems(config_dir, harness, sorted(listing))
        problems += lease_problems
    elif harness not in LEASE_CREDENTIAL:
        names = {n for n, _ in CREDENTIAL_FILES[harness]}
        hits = sorted(p for p in listing if os.path.basename(p) in names
                      or CREDENTIAL_LIKE.search(os.path.basename(p)))
        if session_id and run_tree and harness == "claude-code" and not problems and any(
                p.split(os.sep)[0] == SESSION_PAIR_DIR and p != SESSION_PAIR_DIR for p in hits):
            pair, pair_problems = session_pair(config_dir, listing, session_id, run_tree)
            problems += pair_problems
            session_admitted = pair
            hits = [p for p in hits if p not in {a["name"] for a in pair}]
        if hits:
            problems.append(f"credential-like files present: {hits}")
    detail = "; ".join(problems) or ("only the registered credential " + admitted[0] if admitted
                                     else "no credential file")
    check = {"id": POSTFLIGHT_CHECKS[0], "ok": not problems, "detail": detail}
    recorded = {"listing": sorted(listing), "admitted_credential": admitted,
                "credential_files": [{"name": n, "source": s} for n, s in CREDENTIAL_FILES[harness]]}
    if session_id is not None or run_tree is not None:
        recorded["admitted_session_pair"] = session_admitted
    return {"ok": not problems, "checks": [check], "recorded": recorded}
