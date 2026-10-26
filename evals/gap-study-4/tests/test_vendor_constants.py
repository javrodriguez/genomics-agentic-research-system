#!/usr/bin/env python3
"""Lane vendor-admission T4 P5: the vendor constants, the vendor view, the merged digest and the vendor side
(lane-reports/vendor-T4-PLAN.md v4, sections 6 and 9; glitch-b5 round 13, Sun 18 Oct 2026).

  P5-block    check_take.VENDOR_CHECKER_CONSTANTS holds one non-empty block per vendor harness, codex and gemini; no key
              of it is a CHECKER_CONSTANTS key and no value is PENDING; each value is the one its code holds (the
              harness, SESSION_STORE_ROOTS, VENDOR_RESUME_TOKENS, VENDOR_CUT_OUTCOMES, the table's model reading and
              every VENDOR_PENDING_ROWS row whole, as its canonical JSON text: review e-71a2b94 NIT 2, round 14).
  P5-rows     vendor_rows_block enters each row whole: a row's reason, state, reader, fixture or ruling changed, or a
              field added, moves the merged digest.
  P5-view     vendor_view takes design_view's Design and returns it with the block in pre and the block's PENDING
              paths in pending, the rest untouched; it refuses a design that is not a Design, a claude-code design, an
              empty block, a block of other keys, a block key that CHECKER_CONSTANTS holds and a design already viewed
              (design_view's shadow rule); a block holding a PENDING value (a billing-route variable not yet named)
              lands in pending, so check4_vendor refuses it as PENDING and it has no digest.
  P5-digest   vendor_checker_constants_sha256 is checker_constants_sha256 of CHECKER_CONSTANTS merged with the block:
              not the Claude-only digest, one per harness, refused when a merged value is PENDING;
              vendor_design_constants_sha256 recovers it from a vendor view and reads None for a plain design_view
              Design or a claude-code one.
  P5-side     _vendor_side on a vendor view is (the merged digest, 0, no Agent call and the CLI's own nested CLI
              calls); on a design that is not a vendor view it refuses naming the harness.
  P5-pre      check4_vendor and check4_walk_vendor read only a vendor view: a plain design_view Design refuses with
              CheckRefused before any reading.
  P5-road     checker_view hands a vendor row's design through vendor_view and a claude-code design back as it is;
              walk_builders' production design_for and walk_regrade.production_design both build that view.
  P5-env      a vendor walk whose environment record names a ledger row routes environment-record (check_walk's leg;
              the take road's record and model legs are test_vendor_body's P2-cases).
  P5-drive    drive.take_checker on a clean vendor take with its vendor view records the merged digest, 0 nudges and
              the vendor Agent summary, and routes exactly the take's PENDING refusals.
  P5-witness  check_take.py compiled in memory with a vendor key shadowing CHECKER_CONSTANTS admitted, the block's
              PENDING paths dropped (a PENDING billing-route variable defaulted), the side reading a plain view, the
              entries reading a plain view, checker_view handing a vendor design back unviewed, the side's nested
              count dropped, a row entering as its reason and state alone and the walk's environment row admitted:
              each goes red.

Fakes and synthetic strings only, inside test_box_integration's process guard with test_drive_loop's checker world:
no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

import test_box_integration as tbi  # noqa: E402
import test_checker_body as tcb  # noqa: E402
import test_vendor_body as tvb  # noqa: E402
import test_vendor_entries as tve  # noqa: E402

HARNESSES = tuple(tvb.VENDORS)
WALK_ID = tvb.WALK_ID
# TEST DATA: a billing-route variable list not yet named, as run_take holds a PENDING value
BILLING = "billing_route_variables"


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


outcome = tve.outcome
world = tve.world


def digest(constants) -> str:
    """An independent sha256 of canonical JSON (check_take.checker_constants_sha256's stated rule), bound, since lane
    pf1-checker-digest (B7), with the checker's code half: the sha256 of {path: git blob id} over the files it lists,
    recomputed here from the files."""
    import check_take
    blob = json.dumps(constants, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    consts = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    root = Path(check_take.CHECKER_CODE_ROOT)
    ids = {rel: hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()
           for rel in check_take.CHECKER_CODE_FILES for raw in ((root / rel).read_bytes(),)}
    code = hashlib.sha256(json.dumps(ids, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    # the fold of review c99f114 (MAJOR 1): the pre-registration in force's two leak values, recomputed here
    import prereg
    doc = json.loads(prereg.in_force().read_text(encoding="utf-8"))
    values = {"leak_context_excusals": doc.get("leak_context_excusals"), "leak_words": doc.get("leak_words")}
    design = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"),
                                       ensure_ascii=False).encode("utf-8")).hexdigest()
    return hashlib.sha256(json.dumps({"checker_code_sha256": code, "constants_sha256": consts,
                                      "design_values_sha256": design}, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def merged(mod, harness) -> dict:
    """The test rig's constants merged with the harness's block, built here, not by the module."""
    return {**tcb.walk_constants(mod), **copy.deepcopy(mod.VENDOR_CHECKER_CONSTANTS[harness])}


# ---- P5-block -------------------------------------------------------------------------------------------------------
def block_problems(mod) -> list:
    out = []
    if sorted(mod.VENDOR_CHECKER_CONSTANTS) != ["codex", "gemini"]:
        out.append(f"VENDOR_CHECKER_CONSTANTS holds {sorted(mod.VENDOR_CHECKER_CONSTANTS)}")
    for harness in HARNESSES:
        block = mod.VENDOR_CHECKER_CONSTANTS.get(harness) or {}
        if not block:
            out.append(f"{harness}: no block")
            continue
        if set(block) & set(mod.CHECKER_CONSTANTS):
            out.append(f"{harness}: the block shadows {sorted(set(block) & set(mod.CHECKER_CONSTANTS))}")
        held = [p for k, v in block.items() for p in mod._pending_paths(v, k)]
        if held:
            out.append(f"{harness}: the block holds PENDING values {held}")
        want = {"vendor_check": {
            "harness": harness, "session_store_root": mod.SESSION_STORE_ROOTS[harness],
            "resume_token": mod.VENDOR_RESUME_TOKENS[harness], "cut_outcomes": list(mod.VENDOR_CUT_OUTCOMES),
            "model_reading": {"codex": "requested", "gemini": "served"}[harness],
            "rows": {k: json.dumps(r, sort_keys=True, separators=(",", ":"))
                     for k, r in mod.VENDOR_PENDING_ROWS[harness].items()}}}
        if block != want:
            out.append(f"{harness}: the block is {block}, not its sources' {want}")
    return out


# ---- P5-rows (review e-71a2b94 NIT 2) -------------------------------------------------------------------------------
def rows_problems(mod) -> list:
    """Each VENDOR_PENDING_ROWS row's every field moves the merged digest: the block rebuilt by vendor_rows_block from
    rows with one field of one row changed (or one field added) digests apart from the production block."""
    out = []
    for harness in HARNESSES:
        base = mod.vendor_checker_constants_sha256(harness)
        rows = mod.VENDOR_PENDING_ROWS[harness]
        key = sorted(rows)[0]
        # lane vendor-settle stage V (S6): the row is settled now, so "the state changed" is a state other than its own
        other = "NOT COMPARABLE" if rows[key]["state"] == "SAME" else "SAME"
        changes = {"the reason": {"reason": "synthetic-other-reason"}, "the state": {"state": other},
                   "a reader": {"reader": "vendor_check"}, "a fixture": {"fixture": "synthetic-fixture"},
                   "a ruling": {"ruling": "synthetic ruling"}}
        for name, change in changes.items():
            moved = copy.deepcopy(rows)
            moved[key] = dict(moved[key], **change)
            block = copy.deepcopy(mod.VENDOR_CHECKER_CONSTANTS[harness])
            block["vendor_check"]["rows"] = mod.vendor_rows_block(moved)
            got = outcome(mod.vendor_checker_constants_sha256, harness, None, block)
            if got[0] != "ok" or got[1] == base:
                out.append(f"{harness} {key}: {name} changed does not move the merged digest ({got[:2]})")
        if mod.vendor_rows_block(rows) != mod.VENDOR_CHECKER_CONSTANTS[harness]["vendor_check"]["rows"]:
            out.append(f"{harness}: the production block's rows are not vendor_rows_block of VENDOR_PENDING_ROWS")
    return out


# ---- P5-view --------------------------------------------------------------------------------------------------------
def view_problems(mod) -> list:
    out = []
    for harness in HARNESSES:
        plain = tvb.plain_design_for(mod, harness)
        got = outcome(mod.vendor_view, plain)
        if got[0] != "ok":
            out.append(f"{harness}: vendor_view refused the plain view: {got}")
            continue
        v = got[1]
        block = mod.VENDOR_CHECKER_CONSTANTS[harness]
        if {k: v.pre.get(k) for k in block} != block or {k: x for k, x in v.pre.items() if k not in block} != plain.pre:
            out.append(f"{harness}: the view's pre is not the plain pre plus the block")
        if tuple(v.pending) != tuple(plain.pending):
            out.append(f"{harness}: the view's pending is {v.pending}, not {plain.pending}")
        if [getattr(v, f) for f in ("task_id", "harness", "half", "script", "run_tree")] != \
                [getattr(plain, f) for f in ("task_id", "harness", "half", "script", "run_tree")]:
            out.append(f"{harness}: the view changed a field other than pre and pending")
        refusals = {
            "not a Design": lambda: mod.vendor_view(types.SimpleNamespace(harness=harness, pre={}, pending=())),
            "an empty block": lambda: mod.vendor_view(plain, {}),
            "a block of other keys": lambda: mod.vendor_view(plain, {"vendor_other": {"x": 1}}),
            "a block key CHECKER_CONSTANTS holds": lambda: mod.vendor_view(plain, {**block, "budgets": {"poll_s": 1}}),
            "a design already viewed": lambda: mod.vendor_view(v),
        }
        for name, call in refusals.items():
            got = outcome(call)
            if got[:2] != ("raised", "CheckRefused"):
                out.append(f"{harness}: vendor_view admitted {name}: {got[:2]}")
        held = copy.deepcopy(block)
        held["vendor_check"][BILLING] = mod.PENDING
        got = outcome(mod.vendor_view, plain, held)
        if got[0] != "ok" or "vendor_check." + BILLING not in got[1].pending:
            out.append(f"{harness}: a PENDING vendor value is not in the view's pending: {got[:2]}")
        else:
            t = tve.take_for(mod, harness, "take", design=got[1])
            ran = outcome(tve.entry_call, mod, t, t.build(), "take")
            if ran[:2] != ("raised", "CheckRefused") or "still PENDING" not in ran[2] or BILLING not in ran[2]:
                out.append(f"{harness}: check4_vendor on a PENDING vendor value: {str(ran)[:200]}")
            ran = outcome(mod.vendor_checker_constants_sha256, harness, tcb.walk_constants(mod), held)
            if ran[:2] != ("raised", "CheckRefused"):
                out.append(f"{harness}: a PENDING vendor value has a digest: {ran[:2]}")
    claude = tcb.view(mod)
    if outcome(mod.vendor_view, claude)[:2] != ("raised", "CheckRefused"):
        out.append("vendor_view built a vendor view of a claude-code design")
    return out


# ---- P5-digest ------------------------------------------------------------------------------------------------------
def digest_problems(mod) -> list:
    out = []
    claude_only = mod.checker_constants_sha256()
    seen = set()
    for harness in HARNESSES:
        want = digest({**mod.CHECKER_CONSTANTS, **mod.VENDOR_CHECKER_CONSTANTS[harness]})
        got = outcome(mod.vendor_checker_constants_sha256, harness)
        if got != ("ok", want):
            out.append(f"{harness}: the production merged digest is {got}, not {want}")
        if want == claude_only:
            out.append(f"{harness}: the merged digest is the Claude-only digest")
        seen.add(want)
        rig = digest(merged(mod, harness))
        view = mod.vendor_view(tvb.plain_design_for(mod, harness))
        if mod.vendor_design_constants_sha256(view) != rig:
            out.append(f"{harness}: the view's recovered digest is {mod.vendor_design_constants_sha256(view)}, not {rig}")
        if outcome(mod.vendor_checker_constants_sha256, harness, tcb.walk_constants(mod)) != ("ok", rig):
            out.append(f"{harness}: the rig's merged digest is not {rig}")
        if mod.vendor_design_constants_sha256(tvb.plain_design_for(mod, harness)) is not None:
            out.append(f"{harness}: a plain design_view Design has a merged digest")
        shadow = outcome(mod.vendor_checker_constants_sha256, harness, None, {"budgets": {"poll_s": 1}})
        if shadow[:2] != ("raised", "CheckRefused"):
            out.append(f"{harness}: a block shadowing the checker constants has a digest: {shadow[:2]}")
    if len(seen) != len(HARNESSES):
        out.append("the two harnesses share one merged digest")
    if mod.vendor_design_constants_sha256(tcb.view(mod)) is not None:
        out.append("a claude-code design has a merged digest")
    return out


# ---- P5-side --------------------------------------------------------------------------------------------------------
def summary(nested: int) -> dict:
    return {"agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0},
            "nested_cli_calls": nested}


def side_problems(mod) -> list:
    import pending_walk
    out = []
    for harness in HARNESSES:
        t = tve.take_for(mod, harness, "take")
        path = t.build()
        got = outcome(mod._vendor_side, path, t.design)
        want = ("ok", (digest(merged(mod, harness)), 0, summary(0)))
        if got != want:
            out.append(f"{harness}: the side read {got}, not {want}")
        elif not pending_walk.valid_agent_summary(*(got[1][2][k] for k in pending_walk.CHECK_AGENT_KEYS)):
            out.append(f"{harness}: the side's Agent summary is not one check.json may carry")
        t = tve.take_for(mod, harness, "take")
        path = t.build(tvb.tool_command("claude -p hello"))
        got = outcome(mod._vendor_side, path, t.design)
        if got[0] != "ok" or got[1][2] != summary(1):
            out.append(f"{harness}: the side of a take running one nested CLI read {got}")
        got = outcome(mod._vendor_side, path, tvb.plain_design_for(mod, harness))
        if got[:2] != ("raised", "CheckRefused") or harness not in got[2]:
            out.append(f"{harness}: the side read a plain design_view Design: {got}")
    return out


# ---- P5-pre ---------------------------------------------------------------------------------------------------------
def pre_problems(mod) -> list:
    out = []
    for harness in HARNESSES:
        for road in ("take", "walk"):
            t = tve.take_for(mod, harness, road, design=tvb.plain_design_for(mod, harness))
            called = []

            def reader(name):
                return lambda *a, **k: called.append(name) or []
            with contextlib.ExitStack() as st:
                for name in tve.READERS:
                    st.enter_context(mock.patch.object(mod, name, reader(name)))
                got = outcome(tve.entry_call, mod, t, t.build(), road)
            if got[:2] != ("raised", "CheckRefused") or "vendor view" not in got[2] or called:
                out.append(f"{harness} {road}: a plain design_view Design read {got[:3]}, readers {called}")
    return out


# ---- P5-road --------------------------------------------------------------------------------------------------------
def road_problems(mod) -> list:
    import walk_builders
    import walk_regrade
    out = []
    claude = tcb.view(mod)
    if mod.checker_view(claude) is not claude:
        out.append("checker_view did not hand the claude-code design back as it is")
    for harness in HARNESSES:
        plain = tvb.plain_design_for(mod, harness)
        if mod.vendor_design_constants_sha256(mod.checker_view(plain)) != digest(merged(mod, harness)):
            out.append(f"{harness}: checker_view did not build the vendor view")
    for harness, design in (("claude-code", claude), *((h, tvb.plain_design_for(mod, h)) for h in HARNESSES)):
        model = tcb.row()["model"] if harness == "claude-code" else tvb.VENDORS[harness][0]
        row = dict(tcb.row(), model=model, agent=dict(tcb.row()["agent"], harness=harness))
        built = {}
        with mock.patch.object(mod, "design_view", lambda r, d=design, **k: d), \
                mock.patch.dict(sys.modules, {"check_take": mod}), \
                mock.patch("batch.expected_pin", lambda r, table=None: {"harness": harness, "model": model}):
            for name, call in (("walk_regrade.production_design", lambda: walk_regrade.production_design(row, "/t")),
                               ("walk_builders design_for", lambda: builders_design_for(walk_builders, row))):
                got = outcome(call)
                built[name] = got
        for name, got in built.items():
            if got[0] != "ok":
                out.append(f"{harness}: {name} refused: {got}")
            elif harness == "claude-code" and got[1] is not design:
                out.append(f"{harness}: {name} did not hand design_view's Design back as it is")
            elif harness != "claude-code" and \
                    mod.vendor_design_constants_sha256(got[1]) != digest(merged(mod, harness)):
                out.append(f"{harness}: {name} did not build the vendor view")
    return out


def builders_design_for(walk_builders, row):
    """walk_builders.production_builders' design_for on `row`, its pin_for and its constants check as in production."""
    out = walk_builders.production_builders()
    if isinstance(out["design_for"], walk_builders.Missing):
        raise AssertionError(f"design_for is Missing: {out['design_for']}")
    return out["design_for"](row, "/t")


# ---- P5-drive -------------------------------------------------------------------------------------------------------
def drive_problems(mod) -> list:
    import drive
    out = []
    for harness in HARNESSES:
        for records, road in (("takes", "take"), ("walks", "walk")):
            t = tve.take_for(mod, harness, road)
            path = t.build()
            row = dict(tcb.row(), arm=t.arm, agent=dict(tcb.row()["agent"], harness=harness))
            if road == "walk":
                row["walk"] = WALK_ID
                take = types.SimpleNamespace(folder=str(path.parent), cross_check=[])
            else:
                take = types.SimpleNamespace(folder=str(path.parent), identity={"row": t.call["row_index"]},
                                             cross_check=[])
            with mock.patch.dict(sys.modules, {"check_take": mod}), \
                    mock.patch.object(mod, "CHECK_HOME", Path(tvb.HOME)), t.own_rows():
                got = outcome(drive.take_checker(design_for=lambda r, tk, d=t.design: d, records=records), row, take, [])
            want = sorted(p.split("] ")[0][1:] for p in tvb.pending_lines(mod, harness))
            if got[0] != "ok" or sorted(got[1]["checker_reasons"]) != want:
                out.append(f"{harness} {road}: take_checker routed {str(got)[:300]}, not {want}")
            side = (getattr(take, "checker_constants_sha256", None), getattr(take, "no_output_nudges", None),
                    getattr(take, "agent_summary", None))
            if side != (digest(merged(mod, harness)), 0, summary(0)):
                out.append(f"{harness} {road}: the take's side readings are {side}")
    return out


# ---- P5-env (the walk road's environment record) ---------------------------------------------------------------------
def env_row(path):
    """The walk's environment.json made to name ledger row 0, its ledger binding rewritten to the new bytes, so only
    the walk's own leg can refuse it."""
    f = path.parent / "environment.json"
    rec = json.loads(f.read_text())
    rec.update(row=0)
    raw = json.dumps(rec).encode("utf-8")
    f.write_bytes(raw)
    led = path.parent / "driver-ledger.json"
    doc = json.loads(led.read_text())
    doc["environment"]["sha256"] = hashlib.sha256(raw).hexdigest()
    led.write_text(json.dumps(doc))


def env_walk_problems(mod) -> list:
    out = []
    for harness in HARNESSES:
        t = tve.take_for(mod, harness, "walk")
        got = outcome(tve.entry_call, mod, t, t.build(None, env_row), "walk")
        want = sorted([p.split("] ")[0][1:] for p in tvb.pending_lines(mod, harness)] + ["environment-record"])
        if got[0] != "ok" or sorted(got[1]["reasons"]) != want:
            out.append(f"{harness}: a walk whose environment record names a row routed {str(got)[:300]}, not {want}")
    return out


class P5Constants(unittest.TestCase):
    def test_p5_the_vendor_blocks_are_their_sources(self):
        with world() as ct:
            self.assertEqual(block_problems(ct), [])

    def test_p5_every_row_field_moves_the_merged_digest(self):
        with world() as ct:
            self.assertEqual(rows_problems(ct), [])

    def test_p5_the_vendor_view_merges_the_block_and_its_pending(self):
        with world() as ct:
            self.assertEqual(view_problems(ct), [])

    def test_p5_the_merged_digest(self):
        with world() as ct:
            self.assertEqual(digest_problems(ct), [])

    def test_p5_the_vendor_side(self):
        with world() as ct:
            self.assertEqual(side_problems(ct), [])

    def test_p5_the_entries_read_only_a_vendor_view(self):
        with world() as ct:
            self.assertEqual(pre_problems(ct), [])

    def test_p5_the_production_roads_build_the_vendor_view(self):
        with world() as ct:
            self.assertEqual(road_problems(ct), [])

    def test_p5_a_walks_environment_record_names_no_row(self):
        with world() as ct:
            self.assertEqual(env_walk_problems(ct), [])

    def test_p5_take_checker_records_the_vendor_side(self):
        with world() as ct:
            self.assertEqual(drive_problems(ct), [])


# ---- the witnesses --------------------------------------------------------------------------------------------------
P5_WITNESSES = {
    "a vendor key shadowing CHECKER_CONSTANTS admitted": ((
        "    shadowed = sorted(set(block) & (set(CHECKER_CONSTANTS) | set(design.pre)))\n",
        "    shadowed = []\n"), view_problems),
    "a PENDING billing-route variable defaulted": ((
        "    return design.replace(pre=pre, pending=tuple(design.pending) + tuple(\n"
        "        p for k, v in block.items() for p in _pending_paths(v, k)))\n",
        "    return design.replace(pre=pre, pending=tuple(design.pending))\n"), view_problems),
    "the side reading a plain view": ((
        "    if digest is None:\n        raise CheckRefused(f\"harness {getattr(design, 'harness', None)!r}: the vendor "
        "side reads only a vendor view \"\n",
        "    if False:\n        raise CheckRefused(f\"harness {getattr(design, 'harness', None)!r}: the vendor "
        "side reads only a vendor view \"\n"), side_problems),
    "the entries reading a plain view": (("    if vendor_design_constants_sha256(design) is None:\n",
                                          "    if False:\n"), pre_problems),
    "checker_view handing a vendor design back unviewed": ((
        "    if isinstance(design, Design) and design.harness in VENDOR_CHECKER_CONSTANTS:\n        return vendor_view("
        "design)\n", ""), road_problems),
    "the side's nested count dropped": ((
        "            \"nested_cli_calls\": sum(len(nested_cli_mentions(c)) for c in cmds)}\n",
        "            \"nested_cli_calls\": 0}\n"), side_problems),
    "a row entering as its reason and state alone": ((
        "    return {key: json.dumps(row, sort_keys=True, separators=(\",\", \":\")) for key, row in rows.items()}\n",
        "    return {key: f\"{row['reason']}: {row['state']}\" for key, row in rows.items()}\n"), rows_problems),
    "the walk's environment row admitted": ((
        "        if isinstance(rec, dict) and any(rec.get(k) is not None for k in (\"row\", \"row_commit\")):\n"
        "            out.append(\"[environment-record] the vendor walk's",
        "        if False:\n            out.append(\"[environment-record] the vendor walk's"), env_walk_problems),
}


class P5Witnesses(unittest.TestCase):
    def test_p5_witness_each_guard_dropped_goes_red(self):
        for name, (edit, check) in P5_WITNESSES.items():
            with self.subTest(witness=name), world() as ct:
                self.assertEqual(check(ct), [], f"{name}: its check is red on check_take.py")
                mutant = tcb.witness_module((edit,))
                with mock.patch.dict(sys.modules, {"check_take": mutant}):
                    self.assertNotEqual(check(mutant), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
