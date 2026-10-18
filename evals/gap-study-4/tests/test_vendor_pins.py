#!/usr/bin/env python3
"""Lane vendor-admission round 17 B7 (lane-reports/PLAN-codex2-signin-road-2026-10-18.md section 5, R4 of
RULINGS-codex2-signin-road-2026-10-18.md; glitch-b5's B7 rulings, ROUND 17 CONTINUED (2) and (3), 18 Oct 2026):
the O and G pin profiles, registered in routing.json with their rate-limit and spend-cap entries.

  B7.profiles  routing.load_table() admits the committed table, whose pin_profiles hold codex, each arm O model
               {"permission_mode": "bypass", "version": "0.162.1"}, and gemini, each arm G model {"permission_mode":
               "yolo", "version": "0.64.0"} (R4): each mode a key of its adapter's MODE_FLAGS, each version its take
               lock's harness.version, the models exactly the draft's arm O and arm G models.
  B7.markers   the codex and gemini rate-limit entries are the values sourced by the static read of the pinned
               packages (CONTINUED (2) item 3), each with its source; codex's spend-cap list is the pinned CLI's
               texts out of credits, spend cap and quota exceeded (moved by glitch-b5's ruling B7-F4, 18 Oct 2026,
               from the empty list of CONTINUED (3) item 1), codex is out of routing.EMPTY_SPEND_LIST_HARNESSES, which
               is claude-code alone with its reason, and never in NO_MONEY_HARNESSES (arm O keeps batch's money gate);
               gemini's is status 402 and the text payment required, its source holding both documentation URLs, the
               quote and the read date (item 2).
  B7.status    rate_limit_markers_status and spend_cap_markers_status are glitch-b5's RULED 18 Oct 2026 lines, each
               quoting the status it supersedes, word for word, and neither pending by batch.is_pending (item 4).
  B7.pin       production_builders' pin_for returns the profile on the committed draft's first codex and first gemini
               row, and walk_builders.agent_versions() gives 0.162.1 and 0.64.0; the draft's version_pins carry them.

Mutants (each must turn the check red): codex's spend list emptied (refused by check_table, B7-F4); a usage-limit
text added to codex's spend list (B7-F4; also red in tests/test_codex_spend_texts.py); codex put in
NO_MONEY_HARNESSES (arm O out of the money gate); gemini's spend list empty; a rate-limit entry with no source;
codex's pin with permission mode yolo; codex at version 0.162.0; one arm G model missing. No take, model, container
or network.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import batch  # noqa: E402
import build_draft  # noqa: E402
import codex_adapter  # noqa: E402
import gemini_adapter  # noqa: E402
import routing  # noqa: E402
import walk_builders  # noqa: E402
from box import image_lock  # noqa: E402

CODEX, GEMINI, CLAUDE = "codex", "gemini", "claude-code"
PROFILES = {CODEX: {m: {"permission_mode": "bypass", "version": "0.162.1"} for m in build_draft.MODELS["O"]},
            GEMINI: {m: {"permission_mode": "yolo", "version": "0.64.0"} for m in build_draft.MODELS["G"]}}
ADAPTER_MODES = {CODEX: codex_adapter.MODE_FLAGS, GEMINI: gemini_adapter.MODE_FLAGS}
LOCKS = {CODEX: os.path.join(HERE, "box", "codex", "image.lock"), GEMINI: os.path.join(HERE, "box", "gemini", "image.lock")}
API = ("status", "type", "text")
RATE = {CODEX: {"status": [429], "type": ["usage_limit_reached"], "text": ["usage limit", "rate limit", "429"],
                "reset_wait": None},
        GEMINI: {"status": [429], "type": ["RetryableQuotaError", "TerminalQuotaError"],
                 "text": ["request a quota increase", "exhausted your daily quota"], "reset_wait": None}}
# What each rate-limit source must name: the pinned package and the files the values were read from.
RATE_CITES = {CODEX: ("rust-v0.162.1", "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d", "codex-rs/protocol/src/error.rs",
                      "codex-rs/codex-api/src/api_bridge.rs", "codex_adapter.py 150 and 152"),
              GEMINI: ("@google/gemini-cli 0.64.0", "891a794e55c8319b6b78f6f8f13d6b8b2782a4709dfd2fcabf3a1f63ae8365e6",
                       "bundle/chunk-NR7L3FXV.js", "bundle/gemini-Q2GRYIAK.js", "gemini_adapter.py 157 and 184")}
SPEND = {CODEX: {"status": [], "type": [], "text": ["out of credits", "spend cap", "quota exceeded"]},   # B7-F4
         GEMINI: {"status": [402], "type": [], "text": ["payment required"]}}
GEMINI_SPEND_CITES = ("https://ai.google.dev/gemini-api/docs/billing",
                      "\"Requests then fail with an HTTP 402 Payment Required error until you add credits.\"",
                      "https://ai.google.dev/gemini-api/docs/troubleshooting", "\"depleted Prepay credits\"",
                      "18 Oct 2026")
RULED = "RULED 18 Oct 2026 by glitch-b5 under the owner's delegation"
# The two statuses B7 supersedes, as they stood at 6d1b69db (each new status quotes its old one, word for word).
OLD_RATE_STATUS = (
    "RULED 6 Oct 2026 by glitch-f3 (in-plan; recorded as glitch-f3's ruling, not the owner's): status 429 or type "
    "rate_limit_error, OR round 3's four text markers in the API-error record's harness-side error text, word-bounded "
    "and case-insensitive (see rate_limit_markers.source). CP6 walk check, still to do: a replay of a real recorded "
    "usage-limit refusal through harness_records must route pause. batch.py starts only on a status that, stripped and "
    "upper-cased, begins RULED or FILLED (lane review round 2, W4H2-1). The ruled values are claude-code's entry since "
    "lane w4h-w1b-next-touch keyed the markers by harness; another harness's entry is added only with its adapter "
    "(D8).")
OLD_SPEND_STATUS = (
    "RULED 2026-10-12 by Javier (\"spend markers: 1A 2A 3A\", typed Mon 12 Oct 2026 08:52 EDT in glitch-1b's window, "
    "on plans/gap-study-round-4/spend-markers-proposal-2026-10-11.md): claude-code's spend-cap list is empty on "
    "purpose; arm A runs on his subscription login (D4 A), which bills no money per call, and a usage or weekly limit "
    "pauses under rate_limit_markers. The OpenAI and Google entries are added with their adapters, each with a "
    "non-empty list (OpenAI: project_spend_limit_exceeded, organization_spend_limit_exceeded, "
    "credit_balance_exhausted, insufficient_quota; Google: status 402 and its spend-cap error read at a walk), and "
    "this status is ruled again then.")


def draft() -> dict:
    with open(os.path.join(HERE, "prereg-draft.json"), encoding="utf-8") as fh:
        return json.load(fh)


def first(rows, harness):
    return next(r for r in rows if r["agent"]["harness"] == harness)


def table_problems(table: dict) -> list[str]:
    """B7.profiles, B7.markers and B7.status on one routing table (the committed one, or a mutant of it)."""
    p = []
    try:
        found = routing.check_table(table)
    except Exception as e:  # noqa: BLE001 - a crash is a finding, never a pass
        found = [f"check_table raised {type(e).__name__}: {e}"]
    if found:
        p.append(f"B7.profiles: check_table refuses the table: {found}")
    profiles = table.get("pin_profiles") or {}
    for h, want in PROFILES.items():
        got = profiles.get(h)
        if got != want:
            p.append(f"B7.profiles: {h}'s profiles are {got!r}, not R4's {want!r}")
            continue
        lock = image_lock.load(LOCKS[h])["harness"]["version"]
        for m, prof in got.items():
            if prof["permission_mode"] not in ADAPTER_MODES[h]:
                p.append(f"B7.profiles: {h}/{m} mode {prof['permission_mode']!r} is no key of its adapter's MODE_FLAGS")
            if prof["version"] != lock:
                p.append(f"B7.profiles: {h}/{m} version {prof['version']!r} is not its take lock's {lock!r}")
    rate, spend = table.get("rate_limit_markers") or {}, table.get("spend_cap_markers") or {}
    for h in PROFILES:
        e = rate.get(h) or {}
        if {k: e.get(k) for k in RATE[h]} != RATE[h]:
            p.append(f"B7.markers: {h}'s rate-limit entry is {e!r}, not the sourced values")
        missing = [c for c in RATE_CITES[h] if c not in str(e.get("source"))]
        if missing:
            p.append(f"B7.markers: {h}'s rate-limit source does not cite {missing}")
        s = spend.get(h) or {}
        if {k: s.get(k) for k in API} != SPEND[h]:
            p.append(f"B7.markers: {h}'s spend-cap list is {s!r}, not the ruled one")
        if not (isinstance(s.get("source"), str) and s["source"]):
            p.append(f"B7.markers: {h}'s spend-cap list cites no source")
    missing = [c for c in GEMINI_SPEND_CITES if c not in str((spend.get(GEMINI) or {}).get("source"))]
    if missing:
        p.append(f"B7.markers: gemini's spend-cap source does not hold {missing}")
    empty = getattr(routing, "EMPTY_SPEND_LIST_HARNESSES", None)
    reasons = getattr(routing, "EMPTY_SPEND_LIST_REASONS", None)
    if empty != (CLAUDE,) or not isinstance(reasons, dict) or tuple(reasons) != empty \
            or not all(isinstance(v, str) and "names no spend-cap error" in v for v in reasons.values()):
        p.append(f"B7.markers: routing.EMPTY_SPEND_LIST_HARNESSES is {empty!r} with reasons {reasons!r}, not "
                 f"(claude-code,) with its reason (B7-F4)")
    if tuple(routing.NO_MONEY_HARNESSES) != (CLAUDE,):
        p.append(f"B7.markers: routing.NO_MONEY_HARNESSES is {routing.NO_MONEY_HARNESSES!r}: arm O leaves the money gate")
    for h in PROFILES:
        if not batch.bills_money({"agent": {"harness": h}}):
            p.append(f"B7.markers: a {h} row no longer meets batch's money gate")
    for key, old in (("rate_limit_markers_status", OLD_RATE_STATUS), ("spend_cap_markers_status", OLD_SPEND_STATUS)):
        status = table.get(key)
        if not (isinstance(status, str) and status.startswith(RULED) and old in status
                and not batch.is_pending(status)):
            p.append(f"B7.status: {key} is not glitch-b5's 18 Oct line quoting the one it supersedes: "
                     f"{str(status)[:90]!r}")
    return p


def pin_problems() -> list[str]:
    """B7.pin: the production pin and agent version for arms O and G, and the committed draft's version pins."""
    p = []
    d = draft()
    pin_for = walk_builders.production_builders()["pin_for"]
    for h, want in PROFILES.items():
        row = first(d["rows"], h)
        try:
            got = pin_for(row)
        except Exception as e:  # noqa: BLE001 - the named refusal is the red
            got = f"{type(e).__name__}: {e}"
        if got != dict(want[row["model"]], model=row["model"], harness=h):
            p.append(f"B7.pin: pin_for on the first {h} row gives {got!r}")
        version = next(iter({v["version"] for v in want.values()}))
        pins = d["version_pins"].get(h) or {}
        for m, prof in want.items():
            if pins.get(m) != dict(prof, image_version=version, agent_version=version):
                p.append(f"B7.pin: the draft's {h}/{m} version pin is {pins.get(m)!r}")
        if {r["agent"]["version"] for r in d["rows"] if r["agent"]["harness"] == h} != {version}:
            p.append(f"B7.pin: the draft's {h} rows do not carry agent version {version}")
    versions = walk_builders.agent_versions()
    for h, want in PROFILES.items():
        got = versions.values.get(h)
        if got != next(iter({v["version"] for v in want.values()})):
            p.append(f"B7.pin: agent_versions gives {h} {got!r}")
    return p


def real() -> dict:
    return routing.load_table()


def mutated(edit) -> dict:
    t = copy.deepcopy(real())
    edit(t)
    return t


def _codex_mode_yolo(t):
    t["pin_profiles"][CODEX][build_draft.MODELS["O"][0]]["permission_mode"] = "yolo"


def _codex_version(t):
    t["pin_profiles"][CODEX][build_draft.MODELS["O"][0]]["version"] = "0.162.0"


def _gemini_model_missing(t):
    del t["pin_profiles"][GEMINI][build_draft.MODELS["G"][-1]]


def _gemini_spend_empty(t):
    t["spend_cap_markers"][GEMINI].update(status=[], type=[], text=[])


def _codex_spend_emptied(t):
    t["spend_cap_markers"][CODEX].update(status=[], type=[], text=[])


def _codex_spend_usage_text(t):
    t["spend_cap_markers"][CODEX]["text"].append("purchase more credits")


def _rate_source_dropped(t):
    t["rate_limit_markers"][CODEX]["source"] = ""


# name: (a routing.py patch or None, a table edit or None)
MUTANTS = {
    # B7-F4 (glitch-b5, 18 Oct 2026) replaced "codex out of EMPTY_SPEND_LIST_HARNESSES with its empty list"
    "codex's spend list emptied": (None, _codex_spend_emptied),
    "a usage-limit text added to codex's spend list": (None, _codex_spend_usage_text),
    "codex in NO_MONEY_HARNESSES (arm O out of the money gate)": (
        lambda: mock.patch.object(routing, "NO_MONEY_HARNESSES", (CLAUDE, CODEX)), None),
    "gemini's spend list empty": (None, _gemini_spend_empty),
    "a rate-limit entry with no source": (None, _rate_source_dropped),
    "codex's pin with permission mode yolo": (None, _codex_mode_yolo),
    "codex at version 0.162.0": (None, _codex_version),
    "one arm G model missing": (None, _gemini_model_missing),
}


class TestVendorPins(unittest.TestCase):
    def test_b7_the_committed_table_registers_arms_o_and_g(self):
        self.assertEqual(table_problems(real()), [])

    def test_b7_the_production_pin_and_versions(self):
        self.assertEqual(pin_problems(), [])

    def test_b7_load_table_admits_the_profiles_with_their_markers(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "routing.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(real(), fh)
            self.assertEqual(table_problems(routing.load_table(path)), [])
            t = real()
            for h in PROFILES:                       # the profiles alone, without their marker entries: refused
                del t["rate_limit_markers"][h], t["spend_cap_markers"][h]
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(t, fh)
            with self.assertRaisesRegex(routing.TableError, "has no rate_limit_markers or spend_cap_markers entry"):
                routing.load_table(path)


class TestMutants(unittest.TestCase):
    def test_every_mutant_is_red(self):
        self.assertEqual(table_problems(real()), [], "the check is not green on the tree")
        survivors = []
        for name, (patch, edit) in MUTANTS.items():
            t = mutated(edit) if edit else real()
            if patch:
                with patch():
                    found = table_problems(t)
            else:
                found = table_problems(t)
            if not found:
                survivors.append(name)
        self.assertEqual(survivors, [])

    def test_the_version_mutant_is_refused_by_the_draft_builder(self):
        locks = build_draft.source_locks(build_draft.HERE)
        with self.assertRaisesRegex(ValueError, "routing and image versions disagree"):
            build_draft.version_pins(locks, mutated(_codex_version))


if __name__ == "__main__":
    unittest.main()
