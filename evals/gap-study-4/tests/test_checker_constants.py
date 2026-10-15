#!/usr/bin/env python3
"""Lane bootstrap-constants (Gap Study round 4): the checker constants, bound to their sources (B2), the take and walk
ledger's quiescence cap and poll interval (B4), the coverage rule for a walk the constants decide (B5) and the draft's
naming of them (B6). glitch-6b's ruling plans/gap-study-round-4/first-walk-bootstrap-ruling-2026-10-15.md (01:07 EDT,
15 Oct 2026) and its addition of the same morning (the 2.1.296 vocabulary, box ba6d7f14).

Every check is a function of the constants (or of the record it reads) returning its problems, each line opening with
the check's own id; the test asserts the real tree is green, and each witness changes ONE value and asserts the
check's own line goes red (a binding that cannot fail is the threat this lane is reviewed against).

  K-closed      the block holds exactly its seven keys and no value is PENDING.
  K-turn        budgets.turn_timeout_s: round 3's prereg.json budgets (e2979b31) and D8's 900 s for every arm.
  K-finalize    budgets.finalize_wait_s: drive.FINALIZE_WAIT_S and round 3's driver_constants.finalize_wait_s.
  K-poll        budgets.poll_s: round 3's drive.py wait_for_samples_csv sleep cap (ast, e2979b31; line 769 there).
  K-origin      harness_delivered_user_records: [transcript_view.CC_TASK_NOTIFICATION], equal to round 3's list.
  K-location    run_location: round 3's excluded paths in order, box/preflight.STUDY_PATHS (or PENDING, on a tree
                without CP5's fill: never another value), drive.TREE_IDENTITY[0] and TREE_SUBJECT, round 3's identity
                and subject; drive.excluded_from_run_tree reads the paths back.
  K-env         environment_record: exactly drive.py's RECORD_ vocabulary; round 3's patterns and lists a prefix of
                it (round 3's names a subset); run_take.py's copies of round 3's lists equal round 3's; the additions
                exactly the 2.1.296 classified lists (CLASSIFIED below, typed from the box lane's file), and the
                added patterns match exactly the flagged names among the read's unmatched names.
  K-stripped    driver_constants.stripped_env: [] and drive.STRIPPED_ENV.
  K-tmpdir      driver_constants.run_tree_tmpdir: drive's RUN_TREE_TMPDIR constants, round 3's, run_take's copies,
                and run_take.TAKE_ENV's claude-code row pointing each variable at the run tree's folder.
  K-sweep       the pinned tree exported the driver's way (drive.clean_run_tree at variants.PINNED_TREE, minus
                run_location's paths) has smoke_run_tree.TREE_SWEEP hits in README.md and docs/RESULTS.md only, and
                in both; a planted file naming the study is refused.
  K-ledger      (B4) ledger_budget_problems: a ledger whose finalize_wait_s or poll_s is not the pre-registered value,
                or is missing, or a design that has none, is constant-binding.
  K-cover       (B5) pending_walk.coverage_status: a graded-true walk whose check.json names a constant-bound reason,
                carries another constants digest, carries none, or has no readable check.json, is never counted.
  K-draft       (B6) prereg-draft.json's checker_constants_ruling names every carry-over, departure, limitation and
                residual of the ruling, each path a real CHECKER_CONSTANTS path, and shadows no constant.

D8 lives in Glitch's plans, outside this repository: its row is quoted here (D8_ROW) with its file and line, and the
quote is what is bound. The classified lists are typed from the box lane's evidence file (CLASSIFICATION_SOURCE, its
sha256 below), which is not in this repository either. No model, no network, no container; read-only git of this
repository (round 3's commit and the pinned tree) and one temporary export of the pinned tree, removed afterwards.
"""

from __future__ import annotations

import ast
import contextlib
import copy
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
_STACK = contextlib.ExitStack()
_STACK.callback(sys.path.__setitem__, slice(None), list(sys.path))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import drive  # noqa: E402
import pending_walk  # noqa: E402
import prereg  # noqa: E402
import smoke_run_tree  # noqa: E402
import transcript_view  # noqa: E402
import variants  # noqa: E402
from box import preflight, run_take as rt  # noqa: E402

R3_COMMIT = "e2979b3143081824aadea73523ec41af30c1ddb1"
D8_SOURCE = "plans/gap-study-round-4/D8-non-claude-arms.md:294"
D8_ROW = "| Turn budget | the driver's 900 s | the same | the same |"
CLASSIFICATION_SOURCE = ("box ba6d7f14 lane-reports/stub-take-20261015/claude-2.1.296-env-classification-20261015.json "
                         "(sha256 4e4c81bff32694a5739b2d4e0e39963562ac8b22066ba8737a96a83601e0fcbd), flags.*.names")
CLASSIFIED = {
    "billing_route_outside_every_pattern": ["CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
                                            "CLAUDE_CODE_USE_MANTLE", "CLAUDE_CODE_USE_GATEWAY",
                                            "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST"],
    "billing_route_in_patterns_not_listed": ["ANTHROPIC_BEDROCK_BASE_URL", "ANTHROPIC_VERTEX_BASE_URL",
                                             "ANTHROPIC_FOUNDRY_BASE_URL", "ANTHROPIC_FOUNDRY_RESOURCE",
                                             "ANTHROPIC_AWS_BASE_URL", "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
                                             "ANTHROPIC_BEDROCK_MANTLE_BASE_URL", "ANTHROPIC_UNIX_SOCKET"],
    "credential_in_patterns_not_listed": ["ANTHROPIC_FOUNDRY_AUTH_TOKEN", "ANTHROPIC_IDENTITY_TOKEN",
                                          "ANTHROPIC_IDENTITY_TOKEN_FILE", "ANTHROPIC_ENVIRONMENT_KEY",
                                          "ANTHROPIC_WORK_SECRET", "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR",
                                          "CLAUDE_CODE_GATEWAY_TOKEN"],
    "credential_outside_every_pattern": ["CLAUDE_CODE_HOST_CREDS_FILE"],
}
# The ruling's mapping of the four flags onto the three lists: the subscription OAuth token by file descriptor is a
# subscription-token road (the file's own words), every other credential an API key, every route a billing route.
SUBSCRIPTION_ADDED = ["CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR"]
# The read's names that matched no pattern (partition matched_by "outside", 52): the added patterns must match the
# flagged ones among them and nothing else.
OUTSIDE_2_1_296 = [
    "ATTR_CLOUD_PROVIDER", "CLAUDE_BRIDGE_BASE_URL", "CLAUDE_CODE_ARTIFACTS_API_BASE_URL",
    "CLAUDE_CODE_ARTIFACT_ASSET_BASE_URL", "CLAUDE_CODE_ARTIFACT_LIVE_BASE_URL", "CLAUDE_CODE_ARTIFACT_SYNC_BASE_URL",
    "CLAUDE_CODE_ARTIFACT_VIEWER_BASE_URL", "CLAUDE_CODE_GB_BASE_URL", "CLAUDE_CODE_MEMORY_API_BASE_URL",
    "CLAUDE_CODE_PROVIDER_MANAGED_BY_HOST", "CLAUDE_CODE_SKIP_AWS_CRED_CACHE", "CLAUDE_CODE_SKIP_FAST_MODE_NETWORK_ERRORS",
    "CLAUDE_CODE_SKIP_FAST_MODE_ORG_CHECK", "CLAUDE_CODE_SKIP_HFI_VERSION_CHECK", "CLAUDE_CODE_SKIP_MODEL_ACCESS_MEMORY",
    "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS", "CLAUDE_CODE_SKIP_PLUGIN_MCP_SERVERS_EXCEPT",
    "CLAUDE_CODE_SKIP_PROJECT_BACKFILL", "CLAUDE_CODE_SKIP_PROMPT_HISTORY", "CLAUDE_CODE_SKIP_REPO_UPLOAD",
    "CLAUDE_CODE_USE_ANTHROPIC_AWS", "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD", "CLAUDE_CODE_USE_CCR_V2",
    "CLAUDE_CODE_USE_COWORK_PLUGINS", "CLAUDE_CODE_USE_GATEWAY", "CLAUDE_CODE_USE_MANTLE",
    "CLAUDE_CODE_USE_NATIVE_FILE_SEARCH", "CLAUDE_CODE_USE_POWERSHELL_TOOL", "CLAUDE_RUNNER_API_BASE_URL",
    "CLOUDPROVIDERVALUES_ALIBABA_CLOUD", "CLOUDPROVIDERVALUES_AWS", "CLOUDPROVIDERVALUES_AZURE",
    "CLOUDPROVIDERVALUES_GCP", "DEFAULT_INFERENCE_PROVIDER", "FAASINVOKEDPROVIDERVALUES_ALIBABA_CLOUD",
    "FAASINVOKEDPROVIDERVALUES_AWS", "FAASINVOKEDPROVIDERVALUES_AZURE", "FAASINVOKEDPROVIDERVALUES_GCP",
    "HYBRID_SERVABLE_PROVIDERS", "NOOP_METER_PROVIDER", "PROVIDER_ARMS", "PROVIDER_CLI_FLAG", "PROVIDER_DETECTED",
    "PROVIDER_DISPLAY", "PROVIDER_SELECTOR_ENV_FLAGS", "SEMATTRS_FAAS_INVOKED_PROVIDER", "SEMRESATTRS_CLOUD_PROVIDER",
    "THIRD_PARTY_PROVIDER_ENV_VARS", "THIRD_PARTY_PROVIDER_LABELS", "VOICE_STREAM_BASE_URL", "WEB_SEARCH_PROVIDERS",
    "WEB_SEARCH_PROVIDER_HOSTS"]
PERMITTED_SWEEP = ["README.md", "docs/RESULTS.md"]
KEYS = ["budgets", "driver_constants", "driver_outcome_shapes", "environment_record", "harness_delivered_user_records",
        "run_location", "system_under_test"]
ENV_LISTS = ("api_key_variables", "billing_route_variables", "subscription_token_variables")
CONSTANT_BOUND = ["unknown-harness-origin", "constant-binding", "environment-record", "checkout-binding",
                  "readers-disagree"]


def tearDownModule():
    _STACK.close()


def _git(*args: str) -> bytes:
    got = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if got.returncode != 0:
        raise AssertionError(f"git {' '.join(args[:2])} failed: {got.stderr[:200]!r}")
    return got.stdout


_R3: dict = {}


def r3() -> dict:
    if not _R3:
        _R3.update(json.loads(_git("show", f"{R3_COMMIT}:evals/gap-study-3/prereg.json")))
    return _R3


def r3_poll_cap() -> float:
    """The cap of round 3's finalize poll: the first argument of min() in wait_for_samples_csv's time.sleep."""
    tree = ast.parse(_git("show", f"{R3_COMMIT}:evals/gap-study-3/drive.py").decode("utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "wait_for_samples_csv")
    caps = [c.args[0].args[0].value for c in ast.walk(fn)
            if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "sleep"
            and c.args and isinstance(c.args[0], ast.Call) and getattr(c.args[0].func, "id", None) == "min"
            and isinstance(c.args[0].args[0], ast.Constant)]
    if len(caps) != 1:
        raise AssertionError(f"round 3's wait_for_samples_csv has {len(caps)} min()-capped sleeps, not one")
    return caps[0]


def d8_budget() -> int:
    m = re.fullmatch(r"\| Turn budget \| the driver's (\d+) s \| the same \| the same \|", D8_ROW)
    if not m:
        raise AssertionError(f"the D8 row ({D8_SOURCE}) is not the per-arm turn budget row")
    return int(m.group(1))


def _int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


# ------------------------------------------------------------------------------------------------ the bound checks
def k_closed(c):
    out = []
    if sorted(c) != KEYS:
        out.append(f"K-closed: the keys are {sorted(c)}, not {KEYS}")
    held = [x for k, v in c.items() for x in ct._pending_paths(v, k)]
    if held:
        out.append(f"K-closed: {held} are PENDING")
    return out


def k_turn(c):
    b = c.get("budgets") or {}
    v = b.get("turn_timeout_s")
    out = []
    if sorted(b) != ["finalize_wait_s", "poll_s", "turn_timeout_s"]:
        out.append(f"K-turn: budgets holds {sorted(b)}")
    if not _int(v) or v != r3()["budgets"]["turn_timeout_s"]:
        out.append(f"K-turn: turn_timeout_s {v!r} is not round 3's {r3()['budgets']['turn_timeout_s']}")
    if v != d8_budget():
        out.append(f"K-turn: turn_timeout_s {v!r} is not D8's {d8_budget()} ({D8_SOURCE})")
    return out


def k_finalize(c):
    v = (c.get("budgets") or {}).get("finalize_wait_s")
    out = []
    if not _int(v) or v != drive.FINALIZE_WAIT_S:
        out.append(f"K-finalize: finalize_wait_s {v!r} is not drive.FINALIZE_WAIT_S {drive.FINALIZE_WAIT_S}")
    if v != r3()["driver_constants"]["finalize_wait_s"]:
        out.append(f"K-finalize: finalize_wait_s {v!r} is not round 3's {r3()['driver_constants']['finalize_wait_s']}")
    return out


def k_poll(c):
    v = (c.get("budgets") or {}).get("poll_s")
    cap = r3_poll_cap()
    if not _int(v) or v != cap:
        return [f"K-poll: poll_s {v!r} is not round 3's finalize poll cap {cap}"]
    return []


def k_origin(c):
    h = c.get("harness_delivered_user_records")
    out = []
    if h != {"origin_kinds": [transcript_view.CC_TASK_NOTIFICATION]}:
        out.append(f"K-origin: {h!r} is not exactly [transcript_view.CC_TASK_NOTIFICATION]")
    if (h or {}).get("origin_kinds") != r3()["harness_delivered_user_records"]["origin_kinds"]:
        out.append("K-origin: the origin kinds are not round 3's")
    return out


def k_location(c, study_paths=None):
    rl = c.get("run_location") or {}
    study_paths = preflight.STUDY_PATHS if study_paths is None else study_paths
    out = []
    if sorted(rl) != ["checkout_identity", "checkout_subject", "excluded_from_the_run_tree"]:
        out.append(f"K-location: run_location holds {sorted(rl)}")
    entries = rl.get("excluded_from_the_run_tree") or []
    if not all(isinstance(e, dict) and set(e) == {"path"} for e in entries):
        out.append("K-location: an excluded entry is not exactly {path}")
    paths = [e.get("path") for e in entries if isinstance(e, dict)]
    r3rl = r3()["run_location"]
    if paths != [e["path"] for e in r3rl["excluded_from_the_run_tree"]]:
        out.append(f"K-location: the excluded paths are not round 3's, in order: {paths}")
    if study_paths != preflight.PENDING and list(study_paths) != paths:
        out.append(f"K-location: the excluded paths are not box/preflight.STUDY_PATHS {study_paths!r}")
    if paths and drive.excluded_from_run_tree({"run_location": rl}) != paths:
        out.append("K-location: drive.excluded_from_run_tree does not read them back")
    if rl.get("checkout_identity") != drive.TREE_IDENTITY[0] or rl.get("checkout_identity") != r3rl["checkout_identity"]:
        out.append(f"K-location: checkout_identity {rl.get('checkout_identity')!r} is not drive's and round 3's")
    if rl.get("checkout_subject") != drive.TREE_SUBJECT or rl.get("checkout_subject") != r3rl["checkout_subject"]:
        out.append(f"K-location: checkout_subject {rl.get('checkout_subject')!r} is not drive's and round 3's")
    return out


def drive_record_vocabulary() -> dict:
    return {"file": drive.ENVIRONMENT_RECORD_FILE, "schema": drive.ENVIRONMENT_SCHEMA,
            "name_patterns": {"harness": list(drive.RECORD_HARNESS_NAME_PATTERNS),
                              "generic": list(drive.GENERIC_NAME_PATTERNS)},
            "api_key_variables": list(drive.RECORD_API_KEY_VARIABLES),
            "billing_route_variables": list(drive.RECORD_BILLING_ROUTE_VARIABLES),
            "subscription_token_variables": list(drive.RECORD_SUBSCRIPTION_TOKEN_VARIABLES),
            "credential_source_key": drive.CREDENTIAL_SOURCE_KEY}


def k_env(c):
    e = c.get("environment_record") or {}
    out = []
    if e != drive_record_vocabulary():
        out.append("K-env: environment_record is not drive.py's RECORD_ vocabulary")
    r = r3()["environment_record"]
    for key in ("file", "schema", "credential_source_key"):
        if e.get(key) != r[key]:
            out.append(f"K-env: {key} {e.get(key)!r} is not round 3's {r[key]!r}")
    pats = e.get("name_patterns") or {}
    if pats.get("generic") != r["name_patterns"]["generic"]:
        out.append("K-env: the generic pattern is not round 3's")
    harness = list(pats.get("harness") or [])
    base = r["name_patterns"]["harness"]
    if harness[:len(base)] != base:
        out.append("K-env: round 3's harness patterns are not a prefix of round 4's")
    added_patterns = harness[len(base):]
    for key in ENV_LISTS:
        got, was = list(e.get(key) or []), r[key]
        if got[:len(was)] != was:
            out.append(f"K-env: round 3's {key} are not a prefix of round 4's")
        if list(getattr(rt, key.upper())) != was:
            out.append(f"K-env: run_take.{key.upper()} is not round 3's {key}")
    added = {key: list(e.get(key) or [])[len(r[key]):] for key in ENV_LISTS}
    routes = CLASSIFIED["billing_route_outside_every_pattern"] + CLASSIFIED["billing_route_in_patterns_not_listed"]
    creds = CLASSIFIED["credential_in_patterns_not_listed"] + CLASSIFIED["credential_outside_every_pattern"]
    want = {"billing_route_variables": routes,
            "api_key_variables": [n for n in creds if n not in SUBSCRIPTION_ADDED],
            "subscription_token_variables": SUBSCRIPTION_ADDED}
    if added != want:
        out.append(f"K-env: the 2.1.296 additions {added} are not the classified lists {want} ({CLASSIFICATION_SOURCE})")
    flagged_outside = CLASSIFIED["billing_route_outside_every_pattern"] + CLASSIFIED["credential_outside_every_pattern"]
    universe = sorted(set(OUTSIDE_2_1_296) | set(flagged_outside))
    hit = sorted(n for n in universe if any(re.search(p, n) for p in added_patterns))
    if hit != sorted(flagged_outside):
        out.append(f"K-env: the added patterns match {hit}, not exactly the flagged names {sorted(flagged_outside)}")
    every = [n for v in CLASSIFIED.values() for n in v]
    unmatched = [n for n in every if not any(re.search(p, n) for p in harness + list(pats.get("generic") or []))]
    if unmatched:
        out.append(f"K-env: classified names no pattern records: {unmatched}")
    return out


def k_stripped(c):
    v = (c.get("driver_constants") or {}).get("stripped_env")
    if v != [] or list(drive.STRIPPED_ENV) != v:
        return [f"K-stripped: stripped_env {v!r} is not [] and drive.STRIPPED_ENV {drive.STRIPPED_ENV!r}"]
    return []


def k_tmpdir(c):
    dc = c.get("driver_constants") or {}
    v = dc.get("run_tree_tmpdir")
    out = []
    if sorted(dc) != ["run_tree_tmpdir", "stripped_env"]:
        out.append(f"K-tmpdir: driver_constants holds {sorted(dc)}")
    if v != {"path": drive.RUN_TREE_TMPDIR, "variables": list(drive.RUN_TREE_TMPDIR_VARIABLES)}:
        out.append(f"K-tmpdir: {v!r} is not drive's RUN_TREE_TMPDIR constants")
    r = r3()["driver_constants"]["run_tree_tmpdir"]
    if v != {"path": r["path"], "variables": r["variables"]}:
        out.append("K-tmpdir: not round 3's run_tree_tmpdir")
    if (rt.RUN_TREE_TMPDIR, list(rt.RUN_TREE_TMPDIR_VARIABLES)) != ((v or {}).get("path"), (v or {}).get("variables")):
        out.append("K-tmpdir: run_take's copies differ")
    row = rt.TAKE_ENV[rt.CLAUDE_CODE]
    for name in (v or {}).get("variables") or []:
        if row.get(name) != rt.RUN_TREE_TMP or not rt.RUN_TREE_TMP.endswith("/" + str((v or {}).get("path"))):
            out.append(f"K-tmpdir: TAKE_ENV's claude-code {name} is not the run tree's {(v or {}).get('path')}")
    return out


CHECKS = (k_closed, k_turn, k_finalize, k_poll, k_origin, k_location, k_env, k_stripped, k_tmpdir)


def all_problems(c) -> list[str]:
    return [x for f in CHECKS for x in f(c)]


def edited(path: str, value):
    c = copy.deepcopy(ct.CHECKER_CONSTANTS)
    *head, last = path.split(".")
    node = c
    for k in head:
        node = node[k]
    node[last] = value(copy.deepcopy(node[last])) if callable(value) else value
    return c


# One witness per binding: (name, path, new value, the check whose own line must go red).
WITNESSES = (
    ("turn-901", "budgets.turn_timeout_s", 901, k_turn),
    ("turn-true", "budgets.turn_timeout_s", True, k_turn),
    ("finalize-181", "budgets.finalize_wait_s", 181, k_finalize),
    ("poll-4", "budgets.poll_s", 4, k_poll),
    ("poll-float", "budgets.poll_s", 3.0, k_poll),
    ("budgets-extra", "budgets.extra", 1, k_turn),
    ("origin-plus-auto-continuation", "harness_delivered_user_records.origin_kinds",
     lambda v: v + ["auto-continuation"], k_origin),
    ("location-path-dropped", "run_location.excluded_from_the_run_tree", lambda v: v[:-1], k_location),
    ("location-path-why", "run_location.excluded_from_the_run_tree", lambda v: [dict(v[0], why="x")] + v[1:],
     k_location),
    ("location-identity", "run_location.checkout_identity", "operator", k_location),
    ("location-subject", "run_location.checkout_subject", "init", k_location),
    ("env-api-key-dropped", "environment_record.api_key_variables", lambda v: v[:-1], k_env),
    ("env-r3-route-dropped", "environment_record.billing_route_variables", lambda v: v[1:], k_env),
    ("env-subscription-extra", "environment_record.subscription_token_variables", lambda v: v + ["X_TOKEN"], k_env),
    ("env-pattern-dropped", "environment_record.name_patterns.harness", lambda v: v[:-1], k_env),
    ("env-pattern-wide", "environment_record.name_patterns.harness", lambda v: v[:-3] + ["^CLAUDE_CODE_USE_"] + v[-2:],
     k_env),
    ("env-schema", "environment_record.schema", 2, k_env),
    ("stripped-one", "driver_constants.stripped_env", ["CLAUDECODE"], k_stripped),
    ("tmpdir-path", "driver_constants.run_tree_tmpdir.path", ".scratch", k_tmpdir),
    ("tmpdir-variable", "driver_constants.run_tree_tmpdir.variables", ["TMPDIR", "TMP"], k_tmpdir),
    ("pending-back", "run_location", ct.PENDING, k_closed),
)


class TestTheConstantsAreBoundToTheirSources(unittest.TestCase):
    def test_every_binding_is_green_on_the_tree(self):
        self.assertEqual(all_problems(ct.CHECKER_CONSTANTS), [])

    def test_each_binding_goes_red_when_its_value_changes(self):
        prefix = {f: f.__name__.replace("k_", "K-") for f in CHECKS}
        self.assertEqual(all_problems(ct.CHECKER_CONSTANTS), [])
        for name, path, value, check in WITNESSES:
            with self.subTest(witness=name):
                got = check(edited(path, value))
                own = [x for x in got if x.startswith(prefix[check] + ":")]
                print(f"\nWITNESS {name}: {'red' if own else 'NOT KILLED'} by {prefix[check]} ({len(own)} own)",
                      end=" ", file=sys.stderr, flush=True)
                self.assertTrue(own, f"{name}: {got}")

    def test_the_run_location_binding_reads_preflights_paths(self):
        """On a tree where box/preflight.STUDY_PATHS is filled (CP5), it binds; PENDING binds nothing else here, and
        any other value is red."""
        self.assertEqual(k_location(ct.CHECKER_CONSTANTS, preflight.PENDING), [])
        paths = [e["path"] for e in ct.CHECKER_CONSTANTS["run_location"]["excluded_from_the_run_tree"]]
        self.assertEqual(k_location(ct.CHECKER_CONSTANTS, tuple(paths)), [])
        self.assertTrue(k_location(ct.CHECKER_CONSTANTS, tuple(paths[:-1])), "a shorter STUDY_PATHS stayed green")
        self.assertIn(preflight.STUDY_PATHS, (preflight.PENDING, tuple(paths)))

    def test_the_d8_row_and_round_3_sources_are_read(self):
        self.assertEqual(d8_budget(), 900)
        self.assertEqual(r3_poll_cap(), 3.0)
        self.assertEqual(r3()["budgets"]["turn_timeout_s"], 900)
        self.assertEqual(r3()["driver_constants"]["finalize_wait_s"], 180)

    def test_round_3s_names_are_a_subset_and_the_record_lists_every_classified_name(self):
        e = ct.CHECKER_CONSTANTS["environment_record"]
        r = r3()["environment_record"]
        for key in ENV_LISTS:
            self.assertTrue(set(r[key]) <= set(e[key]), key)
        self.assertTrue(set(r["name_patterns"]["harness"]) <= set(e["name_patterns"]["harness"]))
        listed = {n for key in ENV_LISTS for n in e[key]}
        self.assertEqual(sorted(n for v in CLASSIFIED.values() for n in v if n not in listed), [])
        for n in (x for v in CLASSIFIED.values() for x in v):
            self.assertIsNotNone(drive.matched_by(n), f"drive.matched_by does not record {n}")

    def test_the_digest_is_the_constants_and_refuses_pending(self):
        d = ct.checker_constants_sha256()
        self.assertRegex(d, r"^[0-9a-f]{64}$")
        self.assertNotEqual(d, ct.checker_constants_sha256(edited("budgets.poll_s", 4)))
        with self.assertRaises(ct.CheckRefused):
            ct.checker_constants_sha256(edited("run_location", ct.PENDING))
        self.assertEqual(list(ct.CONSTANT_BOUND_REASONS), CONSTANT_BOUND)


class TestTheExportedRunTree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        paths = [e["path"] for e in ct.CHECKER_CONSTANTS["run_location"]["excluded_from_the_run_tree"]]
        cls.tree = drive.clean_run_tree(variants.PINNED_TREE, str(uuid.uuid4()), paths)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tree, ignore_errors=True)

    @staticmethod
    def hits(tree: Path) -> dict:
        """{file: [line, ...]} for every line TREE_SWEEP matches, read as smoke_run_tree reads the checkout."""
        out: dict = {}
        for f in sorted(tree.rglob("*")):
            if ".git" in f.relative_to(tree).parts or not f.is_file():
                continue
            try:
                text = f.read_text(errors="strict")
            except (UnicodeDecodeError, OSError):
                continue
            for i, ln in enumerate(text.splitlines(), start=1):
                if smoke_run_tree.TREE_SWEEP.search(ln):
                    out.setdefault(f.relative_to(tree).as_posix(), []).append(i)
        return out

    def test_sweep_hits_only_in_the_permitted_files_and_in_both(self):
        got = self.hits(self.tree)
        self.assertEqual(sorted(got), PERMITTED_SWEEP, f"K-sweep: {got}")

    def test_a_planted_file_naming_the_study_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy_ = Path(tmp) / "copy"
            shutil.copytree(self.tree, copy_, ignore=shutil.ignore_patterns(".git"))
            (copy_ / "docs" / "notes-planted.md").write_text("Background: the gap study's pre-registration.\n")
            self.assertNotEqual(sorted(self.hits(copy_)), PERMITTED_SWEEP, "K-sweep: a planted file went unrefused")


def ledger(**kw) -> dict:
    return dict({"finalize_wait_s": 180, "poll_s": 3}, **kw)


class TestTheLedgerRecordsTheCapAndThePoll(unittest.TestCase):
    PRE = {"budgets": copy.deepcopy(ct.CHECKER_CONSTANTS["budgets"])}

    def test_the_pre_registered_values_pass(self):
        self.assertEqual(ct.ledger_budget_problems(ledger(), self.PRE), [])
        self.assertEqual(ct.ledger_budget_problems(None, self.PRE), [])

    def test_each_departure_is_constant_binding(self):
        for name, led, pre in (("cap", ledger(finalize_wait_s=30), self.PRE), ("poll", ledger(poll_s=5), self.PRE),
                               ("cap-missing", {"poll_s": 3}, self.PRE), ("poll-missing", {"finalize_wait_s": 180},
                                                                          self.PRE),
                               ("poll-true", ledger(poll_s=True), {"budgets": {"finalize_wait_s": 180, "poll_s": 1}}),
                               ("design-has-none", ledger(), {"budgets": {"turn_timeout_s": 900}})):
            with self.subTest(case=name):
                got = ct.ledger_budget_problems(led, pre)
                self.assertTrue(got and all(x.startswith("[constant-binding] ") for x in got), got)

    def test_a_design_without_a_whole_budget_is_named_as_such(self):
        """Sweep fold: a design with no budgets block, no key, or a boolean value refuses as carrying none, even where
        the ledger's value would compare equal (True == 1)."""
        for name, pre, led in (("no-budgets", {}, ledger()), ("budgets-none", {"budgets": None}, ledger()),
                               ("no-key", {"budgets": {"poll_s": 3}}, ledger()),
                               ("bool", {"budgets": {"finalize_wait_s": 180, "poll_s": True}}, ledger(poll_s=1))):
            with self.subTest(case=name):
                got = ct.ledger_budget_problems(led, pre)
                self.assertTrue(any("carries no budgets." in x for x in got), got)

    def test_the_driver_ledger_writes_both_beside_the_turn_budget(self):
        """drive.py's ledger literal carries finalize_wait_s and poll_s from the driver's own values (the rig tests,
        test_walk_wiring E1, read them back from a driven take)."""
        tree = ast.parse((HERE / "drive.py").read_text())
        found = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == "budget_s"
                                                  for k in node.keys):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and k.value in ("finalize_wait_s", "poll_s"):
                        found[k.value] = ast.unparse(v)
        self.assertEqual(found, {"finalize_wait_s": "self.finalize_wait_s", "poll_s": "self.poll_s"})


class TestAWalkTheConstantsDecideIsNeverCounted(unittest.TestCase):
    WALK = "w-bootstrap"

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="bootstrap-cover-")) / "rehearsals"
        (self.base / self.WALK).mkdir(parents=True)
        self.write(grade={"graded": True, "row": {}, "grade": {}},
                   check={"walk": self.WALK, "checked": True, "checker_reasons": [], "events": {}, "route": "graded",
                          "route_refused": None, "checker_constants_sha256": ct.checker_constants_sha256()})

    def tearDown(self):
        shutil.rmtree(self.base.parent, ignore_errors=True)

    def write(self, grade=None, check=None):
        if grade is not None:
            (self.base / self.WALK / "grade.json").write_text(json.dumps(grade))
        if check is not None:
            (self.base / self.WALK / "check.json").write_text(json.dumps(check))

    def check(self) -> dict:
        return json.loads((self.base / self.WALK / "check.json").read_text())

    def test_a_clean_graded_walk_counts(self):
        self.assertIsNone(pending_walk.coverage_status(self.base, self.WALK))
        self.assertEqual(pending_walk.uncounted_walks(self.base, [self.WALK]), {})

    def test_a_graded_walk_with_another_reason_still_counts(self):
        self.write(check=dict(self.check(), checker_reasons=["operator-lines"]))
        self.assertIsNone(pending_walk.coverage_status(self.base, self.WALK))

    def test_each_constant_bound_reason_is_never_counted(self):
        for reason in CONSTANT_BOUND:
            with self.subTest(reason=reason):
                self.write(check=dict(self.check(), checker_reasons=["operator-lines", reason]))
                why = pending_walk.coverage_status(self.base, self.WALK)
                self.assertIsNotNone(why, f"K-cover: a graded walk naming {reason} was counted")
                self.assertIn(reason, why)
                self.assertIn(self.WALK, pending_walk.uncounted_walks(self.base, [self.WALK]))

    def test_another_digest_or_none_is_stale(self):
        for name, doc in (("other", dict(self.check(), checker_constants_sha256="0" * 64)),
                          ("none", {k: v for k, v in self.check().items() if k != "checker_constants_sha256"})):
            with self.subTest(digest=name):
                self.write(check=doc)
                self.assertRegex(pending_walk.coverage_status(self.base, self.WALK) or "", r"^stale")

    def test_an_unreadable_check_is_never_counted(self):
        for name, raw in (("missing", None), ("not-json", "{"), ("no-reasons", '{"walk": "w"}'), ("a-list", "[]"),
                          ("reasons-not-a-list", '{"checker_reasons": "constant-binding"}')):
            with self.subTest(check=name):
                p = self.base / self.WALK / "check.json"
                if raw is None:
                    p.unlink(missing_ok=True)
                else:
                    p.write_text(raw)
                self.assertEqual(pending_walk.coverage_status(self.base, self.WALK), "check unreadable")

    def test_pending_constants_count_nothing(self):
        held = edited("run_location", ct.PENDING)
        orig = ct.CHECKER_CONSTANTS
        ct.CHECKER_CONSTANTS = held
        try:
            self.assertEqual(pending_walk.coverage_status(self.base, self.WALK),
                             "the checker constants in force are PENDING")
        finally:
            ct.CHECKER_CONSTANTS = orig

    def test_the_walk_runner_writes_the_digest(self):
        import walk_runner
        doc = walk_runner.check_record(self.WALK, {"checker_reasons": [], "events": {}}, {}, lambda r, t: {"route": "x"},
                                       checked=True)
        self.assertEqual(doc["checker_constants_sha256"], ct.checker_constants_sha256())


class TestTheStripRuleReadsTheRecordVocabulary(unittest.TestCase):
    def test_a_2_1_296_listed_name_is_never_stripped(self):
        """drive.never_stripped_problems reads the RECORD_ lists: a 2.1.296 credential matched by no harness pattern
        (only the generic one) is still never stripped, because it is listed."""
        self.assertEqual(drive.matched_by("CLAUDE_CODE_GATEWAY_TOKEN"), "generic")
        got = drive.never_stripped_problems(["CLAUDE_CODE_GATEWAY_TOKEN", "CLAUDECODE"])
        self.assertEqual(len(got), 1, got)
        self.assertIn("listed credential or billing list", got[0])


class TestTheDraftNamesTheRuling(unittest.TestCase):
    def test_the_draft_names_every_carry_over_departure_limitation_and_residual(self):
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        r = draft.get("checker_constants_ruling")
        self.assertIsInstance(r, dict, "K-draft: no checker_constants_ruling in the draft")
        self.assertNotIn("checker_constants_ruling", ct.CHECKER_CONSTANTS)
        self.assertEqual(sorted(set(draft) & set(ct.CHECKER_CONSTANTS)), [], "K-draft: the draft shadows a constant")
        named = {k: [e["constant"] for e in r[k]] for k in ("carried", "derived", "departures", "limitations",
                                                            "residuals")}
        self.assertEqual(named["carried"], ["budgets.turn_timeout_s", "budgets.finalize_wait_s", "budgets.poll_s"])
        self.assertEqual(sorted(named["departures"]), ["budgets.finalize_wait_s", "driver_constants.stripped_env",
                                                       "environment_record", "run_location"])
        self.assertEqual(named["limitations"], ["environment_record"])
        self.assertEqual(named["residuals"], ["harness_delivered_user_records"])
        self.assertIn("auto-continuation", r["residuals"][0]["text"])
        self.assertIn("2.1.296", [e for e in r["derived"] if e["constant"] == "harness_delivered_user_records"][0]
                      ["evidence"])
        for path in (p for v in named.values() for p in v):
            node = ct.CHECKER_CONSTANTS
            for k in path.split("."):
                self.assertIn(k, node, f"K-draft: {path} is not a CHECKER_CONSTANTS path")
                node = node[k]

    def test_the_design_view_takes_the_draft_without_shadowing(self):
        self.assertNotIn("checker_constants_ruling", KEYS)
        self.assertIn("checker_constants_ruling", prereg.load())


if __name__ == "__main__":
    unittest.main()
