#!/usr/bin/env python3
"""The counted run's builders (Gap Study round 4, lane run-launcher; glitch-f1's rulings on DESIGN-run-launcher.md,
Thu 22 Oct 2026, under Javier's standing delegation).

  S1.plan    run_arms and run_rows: the frozen take_order filtered to the run's arms in frozen relative order (never
             re-sorted); a deferred arm left out until its go record, then kept in place; an arm without rows (C)
             never runs; final slots dropped, owed re-runs kept at their frozen place; --arms only narrows; --limit
             a positive whole number; no take_order and a go reader that is not callable refused.
  S1.order   order_problems (ruling 2): first registrations follow take_order within each launch part (the base part,
             each deferred arm its own); a swap in a part, a first registration that is not attempt 1, a slot outside
             take_order and an arm that differs are named; without deferred_arms there is one part.
  S1.ledger  ledger_snapshot: exactly batch.LEDGER_KEYS; start ROUND_START (ruling 5); every spend record kept,
             projected to {vendor, at, usd}; walks only for money-billing (arm, model) of the run's arms, O at "0" and
             G at the registered figures (ruling 7) only when G runs; tries_left counts the non-final slots; no read
             for a capped vendor refuses (ruling 6); each stored-record rule refuses alone; the latest trim record;
             a pair without a registered cost refuses; the reading passes batch's money gate for an O row.
  S1.history ledger_history_problems: one record per version, earlier records unchanged.
  S1.git     append_spend / append_trim / read_ledger_doc / SpendLedger in a scratch repository: one commit per record,
             a dirty repository refused with nothing written, an uncommitted edit and a rewritten history refused.
  S1.window  claude_reset, codex_reset and reset_for (Gemini raises, naming the residual); wait_target over the
             restart_waits tail with a ruled pause, the latest reset plus the margin, both bounds; wait_until returns at
             once when the target has passed, else sleeps in bounded chunks until it; UsageWindow reads committed files.
  G1         the generated mutants (tests/walk_mutation.py's generator over every top-level function of
             run_builders.py): EQUIVALENT names only generated ids, each with a reason.
  REVIEW     the review of 122b559e (PASS WITH FIXES), folded under glitch-f1's rulings: S2.build build_run's arms (no
             gemini sub-driver or G walks before a go record; MINOR-2) and the pinned RULED_DEFERRALS refusal
             (MINOR-1); S3.main --arms/--limit only with --run (NIT-1); S3.run --arms reaches build_run and a bad ledger
             history is a named refusal (NIT-3, NIT-2); S4.rehearse the clone's two zero spend reads through the real
             writer and a real SpendLedger behind batch's real money gate (MAJOR-1), the take step bounded by the rows'
             budget and refused:takes-timeout (MINOR-4); S4.takes refused:money-gate / loop-stopped for a stop with no
             take (MAJOR-1) and kept run trees removed, kept_removed, refused:run-tree-left (MINOR-3).

Synthetic data only: no model, vendor, network, container, credential, salt or holdout. --mutant / --witnesses /
--gen-mutant / --generated-mutants as in tests/test_walk_builders.py (rule B).
"""
from __future__ import annotations

import ast
import contextlib
import copy
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent.parent
for p in (HERE, HERE / "tests"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import batch  # noqa: E402
import costs  # noqa: E402

SELECTED = None
GENERATED = None
MODS: dict = {}
TARGETS = ("run_builders",)
NOW = datetime.datetime(2026, 10, 24, 12, 0, tzinfo=datetime.timezone.utc)


def rb():
    return MODS["run_builders"]


# ------------------------------------------------------------------------------------------------- synthetic design
AGENTS = {"A": ("claude-code", "2.1.296"), "O": ("codex", "0.162.1"), "G": ("gemini", "0.64.0")}
MODELS = {"A": ["claude-opus-5-5", "claude-sonnet-5-5"], "O": ["gpt-6.1-sol", "gpt-6-luna"],
          "G": ["gemini-3.8-flash", "gemini-3.5-flash-lite"]}


def design(deferred=True, per=3) -> dict:
    rows = []
    for arm, models in MODELS.items():
        for model in models:
            for k in range(per):
                h, v = AGENTS[arm]
                rows.append({"slot": f"s-{arm}-{model}-{k}", "arm": arm, "model": model, "half_cell": f"hc-{arm}-{model}",
                             "agent": {"harness": h, "version": v}, "task": "t", "half": "h", "wording": 1})
    order = sorted(copy.deepcopy(rows), key=lambda r: hashlib.sha256(r["slot"].encode()).hexdigest())
    pre = {"arms": ["A", "C", "O", "G"], "rows": rows, "take_order": order}
    if deferred:
        pre["deferred_arms"] = {"G": {"status": "deferred"}}
    return pre


def no_go(arm):
    return None


def go_g(arm):
    return {"kind": "deferred arm go", "arm": arm} if arm == "G" else None


def outcome(slot, attempt=1, state="graded", final=True):
    return {"slot": slot, "attempt": attempt, "state": state, "final": final, "half_cell": "hc"}


def spend(vendor, at, usd, source="a read", by="Javier"):
    return {"vendor": vendor, "at": at, "usd": usd, "source": source, "by": by}


def doc_with(*records, trimmed=()):
    return {"spend": list(records), "trimmed": list(trimmed)}


READS = (spend("google", "2026-10-15T20:00:00Z", "16.87", source="r4-g billing page"),
         spend("openai", "2026-10-21T12:00:00Z", "0", source="Codex2 subscription"))


# ------------------------------------------------------------------------------------------------- mutation plumbing
def road() -> dict:
    tree = ast.parse((HERE / "run_builders.py").read_text())
    return {"run_builders": tuple(n.name for n in tree.body if isinstance(n, ast.FunctionDef))}


def generate():
    import walk_mutation
    with mock.patch.dict(walk_mutation.ROAD, road(), clear=True):
        return walk_mutation.generate()


def by_id() -> dict:
    return {m.id: m for m in generate()[0]}


def one_generated(mid: str):
    """The one generated mutant a --gen-mutant child runs, found without the generator's per-mutant compile check
    (1531 whole-module compiles, about 22 s, paid by every child): ids and spans come from the AST and the
    replacement alone, and the parent's generate() already dropped every mutant that does not compile, so the lookup
    finds the same mutant, and compile_module still compiles it. walk_mutation.py (lane w10) is not changed: only
    the name compile in its globals is shadowed, during this lookup only."""
    import walk_mutation
    with mock.patch.dict(walk_mutation.ROAD, road(), clear=True), \
            mock.patch.object(walk_mutation, "compile", lambda *a, **k: None, create=True):
        return {m.id: m for m in walk_mutation.generate()[0]}[mid]


def mutants() -> dict:
    return {
        "plan-resorted": ("S1.plan", "run_builders",
                          "rows = [copy.deepcopy(r) for r in order if r[\"arm\"] in chosen and r[\"slot\"] not in done]",
                          "rows = sorted((copy.deepcopy(r) for r in order if r[\"arm\"] in chosen and r[\"slot\"] not in "
                          "done), key=lambda r: r[\"slot\"])"),
        "plan-no-arm-filter": ("S1.plan", "run_builders",
                               "if r[\"arm\"] in chosen and r[\"slot\"] not in done]",
                               "if r[\"slot\"] not in done]"),
        "plan-deferral-ignored": ("S1.plan", "run_builders", "        if arm in deferred and go(arm) is None:",
                                  "        if False:"),
        "plan-final-kept": ("S1.plan", "run_builders", "    done = final_slots(history)\n    rows =",
                            "    done = set()\n    rows ="),
        "plan-arms-widen": ("S1.plan", "run_builders", "        if outside:\n            raise RunRefused",
                            "        if False:\n            raise RunRefused"),
        "order-always-ok": ("S1.order", "run_builders", "        if part in last and index < last[part][0]:",
                            "        if False:"),
        "order-one-part": ("S1.order", "run_builders", "        part = arm if arm in deferred else \"base\"",
                           "        part = \"base\""),
        "ledger-g-walks": ("S1.ledger", "run_builders",
                           "if r[\"arm\"] not in arms or harness in routing.NO_MONEY_HARNESSES",
                           "if harness in routing.NO_MONEY_HARNESSES"),
        "ledger-spend-by-month": ("S1.ledger", "run_builders",
                                  "\"spend\": [{\"vendor\": r[\"vendor\"], \"at\": r[\"at\"], \"usd\": r[\"usd\"]} for r "
                                  "in doc[\"spend\"]],",
                                  "\"spend\": [{\"vendor\": r[\"vendor\"], \"at\": r[\"at\"], \"usd\": r[\"usd\"]} for r "
                                  "in doc[\"spend\"] if r[\"at\"][:7] == str(now)[:7]],"),
        "ledger-no-read-allowed": ("S1.ledger", "run_builders", "    if unread:\n        raise LedgerRefused",
                                   "    if False:\n        raise LedgerRefused"),
        "window-at-once": ("S1.window", "run_builders", "        if now >= target:\n            return",
                           "        if True:\n            return"),
        "window-gemini-waits": ("S1.window", "run_builders", "    reader = RESET_READERS.get(harness)",
                                "    reader = RESET_READERS.get(harness, lambda files: 0.0 + 1)"),
        "window-past-sleeps": ("S1.window", "run_builders", "        if now >= target:\n            return",
                               "        if now > target + 10 ** 9:\n            return"),
        "window-bound-removed": ("S1.window", "run_builders", "        if reset > now + RESET_AHEAD_MAX_S:",
                                 "        if False:"),
        "tree-shared-session": ("S2.tree", "run_builders",
                                "        tree = drive.clean_run_tree(commit, session_id, list(exclude), Path(repo))",
                                "        tree = drive.clean_run_tree(commit, \"fixed\", list(exclude), Path(repo))"),
        "launch-prepare-first": ("S2.driver", "run_builders", "    rd.precheck(sub, row)\n    rd.road.prepare(row)",
                                 "    rd.road.prepare(row)\n    rd.precheck(sub, row)"),
        "published-never-discards": ("S2.driver", "run_builders",
                                     "            rd.road.keep(row[\"slot\"])\n        else:\n            rd.road.discard(row[\"slot\"])",
                                     "            rd.road.keep(row[\"slot\"])\n        else:\n            pass"),
        "counted-run-walk-login": ("S2.login", "run_builders", "def run_login_path(account: str = RUN_ACCOUNT):",
                                   "def run_login_path(account: str = REHEARSAL_ACCOUNT):"),
        "union-first-only": ("S2.lease", "run_builders", "        for source in sources:",
                               "        for source in sources[:1]:"),
        "cid-first-driver": ("S2.driver", "run_builders", "        sub = rd._by_cid.get(container_id)",
                             "        sub = next(iter(rd.drivers.values()))"),
        "lease-shared-road": ("S2.lease", "run_builders", "        road = pool._by_slot.get(take.row[\"slot\"])",
                              "        road = next(iter(pool._by_slot.values()), None)"),
        "identity-other-row": ("S2.identity", "run_builders", "    commit = commits[where[0]]",
                               "    commit = commits[0]"),
        "main-refusal-kept": ("S3.main", "batch", "    if args.run:\n        import run_builders",
                              "    if False:\n        import run_builders"),
        "main-no-nohup": ("S3.main", "batch", "    if not (under_nohup() or args.foreground):",
                          "    if False:"),
        "run-history-passed": ("S3.run", "run_builders", "serial=serial,\n                           ledger=built[\"ledger\"])",
                               "serial=serial,\n                           ledger=built[\"ledger\"], history=[])"),
        "run-ledger-none": ("S3.run", "run_builders", "serial=serial,\n                           ledger=built[\"ledger\"])",
                            "serial=serial,\n                           ledger=None)"),
        "spend-event-unnamed": ("S3.run", "run_builders",
                                "kind=\"spend event\" if SPEND_CAP_ROW in reason else \"stop\")", "kind=\"stop\")"),
        "hook-removed": ("S3.hook", "check_results", "    problems = run_builders.order_problems(rows, pre)",
                         "    problems = []"),
        "blob-any-take-path": ("S3.blob", "box/walk_launch", "|takes/s-[0-9a-f]{64}/[1-9][0-9]*)", "|takes/.*)"),
        "rows-last-not-first": ("S4.rows", "run_builders", "        if r[\"arm\"] in (\"A\", \"O\") and r[\"arm\"] not in first:",
                                "        if r[\"arm\"] in (\"A\", \"O\"):"),
        "overlap-always": ("S4.summary", "run_builders", "def overlap_of(times: dict) -> bool:\n",
                           "def overlap_of(times: dict) -> bool:\n    return bool(times)\n"),
        "lease-ignored": ("S4.takes", "run_builders", "    lease_dead = lease_problem(builders, rows) is not None",
                          "    lease_dead = False"),
        "lease-reason-words": ("S4.summary", "run_builders", "\"reason\": LEASE_REASON,", "\"reason\": \"lease expired\","),
        "rehearsal-on-run-token": ("S4.takes", "run_builders", "arms=[\"A\", \"O\"], account=REHEARSAL_ACCOUNT,",
                                   "arms=[\"A\", \"O\"], account=RUN_ACCOUNT,"),
        "rehearse-into-source": ("S4.rehearse", "run_builders", "    if why == \"out-inside-source\":", "    if False:"),
        "rehearse-remote-kept": ("S4.rehearse", "run_builders",
                                 "             [\"git\", \"-C\", str(clone), \"remote\", \"remove\", \"origin\"]]",
                                 "             ]"),
        # The review of 122b559e (PASS WITH FIXES), folded under glitch-f1's rulings.
        "spend-read-failure-ignored": ("S4.rehearse", "run_builders",
                                       "        if code:\n            write_summary(out, rehearsal_summary([], {}, {}, "
                                       "refused=\"freeze-failed\"))\n            return 1\n    try:\n        timeout",
                                       "        if False:\n            write_summary(out, rehearsal_summary([], {}, "
                                       "{}, refused=\"freeze-failed\"))\n            return 1\n    try:\n        "
                                       "timeout"),
        "money-gate-unnamed": ("S4.takes", "run_builders", "        why = \"money-gate\" if str(",
                               "        why = \"loop-stopped\" if str("),
        "kept-trees-left": ("S4.takes", "run_builders", "    removed, left = remove_kept(built[\"road\"])",
                            "    removed, left = 0, []"),
        "takes-unbounded": ("S4.rehearse", "run_builders",
                            "\"rehearse-takes\", \"--out\", str(out)], str(clone), timeout)",
                            "\"rehearse-takes\", \"--out\", str(out)], str(clone), None)"),
        "deferral-unruled": ("S2.build", "run_builders", "    if deferral:\n        raise RunRefused(deferral)",
                             "    if False:\n        raise RunRefused(deferral)"),
        "build-run-all-arms": ("S2.build", "run_builders",
                               "chosen = tuple(a for a in run_arms(pre, go) if arms is None or a in arms)",
                               "chosen = tuple(a for a in pre[\"arms\"] if arms is None or a in arms)"),
        "run-main-arms-ignored": ("S3.run", "run_builders",
                                  "narrowed = None if arms is None else [a.strip() for a in str(arms).split(\",\")]",
                                  "narrowed = None"),
        "rehearse-error-unwritten": ("S4.rehearse", "run_builders",
                                     "            elif args.verb == \"rehearse\" and rehearse_out_writable(Path(args.out)):",
                                     "            elif False:"),
        "lease-exit-ignores-route": ("S4.takes", "run_builders", "return LEASE_REFUSED_EXIT if a_done else 1",
                                     "return LEASE_REFUSED_EXIT"),
        "loop-error-escapes": ("S4.takes", "run_builders", "    except Exception:  # noqa: BLE001 - closure MINOR-1",
                               "    except RunRefused:  # noqa: BLE001 - closure MINOR-1"),
        "order-mark-lowered": ("S1.order", "run_builders",
                               "                            f\"frozen order\")\n        else:\n            last[part] = (index, slot)",
                               "                            f\"frozen order\")\n        last[part] = (index, slot)"),
        "repo-secrets-first-harness": ("S2.build", "run_builders", "secrets=union_secrets(*sources),",
                                       "secrets=union_secrets(*sources[:1]),"),
        "main-arms-without-run": ("S3.main", "batch",
                                  "    if (args.arms is not None or args.limit is not None) and not args.run:",
                                  "    if False:"),
    }


METHOD = {
    "plan-resorted": "S1Plan.test_frozen_order_kept_deferred_arm_left_out",
    "plan-no-arm-filter": "S1Plan.test_frozen_order_kept_deferred_arm_left_out",
    "plan-deferral-ignored": "S1Plan.test_frozen_order_kept_deferred_arm_left_out",
    "plan-final-kept": "S1Plan.test_final_slots_dropped_owed_kept",
    "plan-arms-widen": "S1Plan.test_arms_narrows_only",
    "order-always-ok": "S1Order.test_a_swap_in_a_part_is_named",
    "order-one-part": "S1Order.test_a_deferred_arm_after_later_base_rows_passes",
    "ledger-g-walks": "S1Ledger.test_walks_only_for_the_runs_money_arms",
    "ledger-spend-by-month": "S1Ledger.test_every_spend_record_is_kept",
    "ledger-no-read-allowed": "S1Ledger.test_a_capped_vendor_without_a_read_refuses",
    "window-at-once": "S1Window.test_wait_until_sleeps_in_bounded_chunks",
    "window-gemini-waits": "S1Window.test_gemini_and_unknown_harnesses_raise",
    "window-past-sleeps": "S1Window.test_wait_until_returns_at_once_when_passed",
    "window-bound-removed": "S1Window.test_bounds",
    "tree-shared-session": "S2Tree.test_the_takes_own_checkout",
    "launch-prepare-first": "S2Driver.test_a_refused_records_check_builds_nothing",
    "published-never-discards": "S2Driver.test_published_removes_or_keeps_the_tree",
    "counted-run-walk-login": "S2Login.test_the_run_token_path_and_the_rehearsals_walk_login",
    "union-first-only": "S2Lease.test_union_secrets",
    "cid-first-driver": "S2Driver.test_each_call_reaches_the_rows_own_sub_driver",
    "lease-shared-road": "S2Lease.test_one_lease_per_take",
    "identity-other-row": "S2Identity.test_the_identity_is_the_open_registrations",
    "main-refusal-kept": "S3Main.test_run_delegates_after_the_nohup_rule",
    "main-no-nohup": "S3Main.test_run_delegates_after_the_nohup_rule",
    "run-history-passed": "S3RunMain.test_the_loop_gets_the_ledger_and_no_history",
    "run-ledger-none": "S3RunMain.test_the_loop_gets_the_ledger_and_no_history",
    "spend-event-unnamed": "S3RunMain.test_a_spend_cap_stop_reads_spend_event",
    "hook-removed": "S3Hook.test_the_order_check_reaches_publication",
    "blob-any-take-path": "S3Blob.test_take_blobs_admitted_other_paths_refused",
    "rows-last-not-first": "S4Rows.test_the_first_a_and_the_first_o_in_frozen_order",
    "overlap-always": "S4Summary.test_overlap",
    "lease-ignored": "S4Takes.test_a_dead_lease_runs_the_a_take_alone",
    "lease-reason-words": "S4Summary.test_the_lease_refusal_entry",
    "rehearsal-on-run-token": "S4Takes.test_the_two_takes_on_the_walk_login",
    "rehearse-into-source": "S4Rehearse.test_refusals_before_anything",
    "rehearse-remote-kept": "S4Rehearse.test_every_step_stays_under_out",
    "spend-read-failure-ignored": "S4Rehearse.test_a_failed_step_is_a_closed_reason",
    "money-gate-unnamed": "S4Takes.test_a_stop_with_no_take_is_one_closed_refusal",
    "kept-trees-left": "S4Takes.test_kept_run_trees_are_removed",
    "takes-unbounded": "S4Rehearse.test_every_step_stays_under_out",
    "deferral-unruled": "S2Harness.test_build_run_refuses_an_undeferred_ruled_arm",
    "build-run-all-arms": "S2Harness.test_build_run_chooses_the_runs_arms",
    "run-main-arms-ignored": "S3RunMain.test_arms_narrow_reaches_build_run",
    "main-arms-without-run": "S3Main.test_arms_and_limit_go_with_run",
    "order-mark-lowered": "S1Order.test_the_high_water_mark_holds_after_a_problem",
    "loop-error-escapes": "S4Takes.test_a_loop_error_is_one_closed_refusal",
    "lease-exit-ignores-route": "S4Takes.test_a_dead_lease_exits_3_only_beside_a_done_a_take",
    "rehearse-error-unwritten": "S4Rehearse.test_an_error_escaping_rehearse_is_freeze_failed",
    "repo-secrets-first-harness": "S2Harness.test_build_run_chooses_the_runs_arms",
}
WITNESSES = {name: (METHOD[name], m[0]) for name, m in mutants().items()}

EQUIVALENT: dict = {}


def compile_module(name: str, source: str) -> types.ModuleType:
    """`name` is a target's path under the study folder without .py (box/walk_launch); its module is box.walk_launch."""
    mod = types.ModuleType(name.replace("/", "."))
    mod.__file__ = str(HERE / f"{name}.py")
    sys.modules[name.replace("/", ".")] = mod
    exec(compile(source, mod.__file__ + " (witness)", "exec"), mod.__dict__)
    return mod


def target(name: str):
    """The module a test reads: the witness's compiled one when it targets `name`, else the real one."""
    if name in MODS:
        return MODS[name]
    import importlib
    return importlib.import_module(name.replace("/", "."))


def setUpModule():
    if SELECTED is not None:
        _, target, old, new = mutants()[SELECTED]
        text = (HERE / f"{target}.py").read_text()
        assert text.count(old) == 1, f"witness {SELECTED}: its anchor occurs {text.count(old)} times"
        MODS[target] = compile_module(target, text.replace(old, new))
    if GENERATED is not None:
        m = one_generated(GENERATED)
        MODS[m.module] = compile_module(m.module, m.source((HERE / f"{m.module}.py").read_text()))
    for name in TARGETS:
        if name not in MODS:
            try:
                MODS[name] = __import__(name)
            except ImportError:
                MODS[name] = types.SimpleNamespace()


def tearDownModule():
    if SELECTED is not None or GENERATED is not None:
        for name in list(MODS):
            sys.modules.pop(name.replace("/", "."), None)


class Case(unittest.TestCase):
    def must(self, clause, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AssertionError:
            raise
        except (Exception, SystemExit) as e:  # noqa: BLE001
            self.fail(f"{clause}: {type(e).__name__}: {str(e)[:400]}")

    def refuses(self, clause, kind_name, words, fn, *args, **kwargs):
        kind = getattr(rb(), kind_name, None)
        self.assertIsNotNone(kind, f"{clause}: run_builders has no {kind_name}")
        try:
            fn(*args, **kwargs)
        except kind as e:
            self.assertIn(words, str(e), f"{clause}: refused for another reason: {e}")
            return str(e)
        except Exception as e:  # noqa: BLE001
            self.fail(f"{clause}: raised {type(e).__name__}, not {kind_name}: {str(e)[:300]}")
        self.fail(f"{clause}: not refused ({words!r})")


# ------------------------------------------------------------------------------------------------- S1.plan
class S1Plan(Case):
    def slots(self, pre, arms):
        return [r["slot"] for r in pre["take_order"] if r["arm"] in arms]

    def test_frozen_order_kept_deferred_arm_left_out(self):
        pre = design()
        self.assertEqual(self.must("S1.plan", rb().run_arms, pre, no_go), ("A", "O"), "S1.plan: run arms")
        got = self.must("S1.plan", rb().run_rows, pre, [], go=no_go)
        self.assertEqual([r["slot"] for r in got], self.slots(pre, ("A", "O")), "S1.plan: not take_order filtered")
        self.assertEqual(got, [r for r in pre["take_order"] if r["arm"] in ("A", "O")], "S1.plan: rows altered")
        got[0]["slot"] = "changed"
        self.assertNotEqual(pre["take_order"][0]["slot"], "changed", "S1.plan: the frozen rows were handed out")

    def test_a_go_record_admits_the_deferred_arm_in_place(self):
        pre = design()
        self.assertEqual(self.must("S1.plan", rb().run_arms, pre, go_g), ("A", "O", "G"), "S1.plan")
        got = self.must("S1.plan", rb().run_rows, pre, [], go=go_g)
        self.assertEqual([r["slot"] for r in got], [r["slot"] for r in pre["take_order"]], "S1.plan: G not in place")
        no_key = design(deferred=False)
        self.assertEqual(self.must("S1.plan", rb().run_arms, no_key, no_go), ("A", "O", "G"),
                         "S1.plan: an arm not deferred needs no go")

    def test_final_slots_dropped_owed_kept(self):
        pre = design()
        order = self.slots(pre, ("A", "O"))
        history = [outcome(order[0]), outcome(order[3], state="harness-error", final=False),
                   {"kind": "ruling", "slot": order[5], "attempt": 1, "ruling": "re-run", "route": None, "by": "x"}]
        got = [r["slot"] for r in self.must("S1.plan", rb().run_rows, pre, history, go=no_go)]
        self.assertEqual(got, order[1:], "S1.plan: final slot kept or owed slot dropped")
        self.assertIn(order[3], got, "S1.plan")

    def test_arms_narrows_only(self):
        pre = design()
        got = [r["slot"] for r in self.must("S1.plan", rb().run_rows, pre, [], go=no_go, arms=["A"])]
        self.assertEqual(got, self.slots(pre, ("A",)), "S1.plan: --arms A")
        self.refuses("S1.plan", "RunRefused", "not among this run's arms", rb().run_rows, pre, [], go=no_go, arms=["G"])
        self.refuses("S1.plan", "RunRefused", "not among this run's arms", rb().run_rows, pre, [], go=no_go, arms=["C"])
        for bad in ([], "A", [1]):
            self.refuses("S1.plan", "RunRefused", "names one or more arms", rb().run_rows, pre, [], go=no_go, arms=bad)

    def test_limit(self):
        pre = design()
        got = [r["slot"] for r in self.must("S1.plan", rb().run_rows, pre, [], go=no_go, limit=2)]
        self.assertEqual(got, self.slots(pre, ("A", "O"))[:2], "S1.plan: --limit")
        for bad in (0, -1, True, 2.0, "2"):
            self.refuses("S1.plan", "RunRefused", "positive whole number", rb().run_rows, pre, [], go=no_go, limit=bad)

    def test_refusals(self):
        pre = design()
        for order in (None, []):
            self.refuses("S1.plan", "RunRefused", "no take_order", rb().run_rows, dict(pre, take_order=order), [],
                         go=no_go)
        self.refuses("S1.plan", "RunRefused", "must be callable", rb().run_arms, pre, None)
        self.refuses("S1.plan", "RunRefused", "not an object", rb().run_arms, dict(pre, deferred_arms=["G"]), no_go)


# ------------------------------------------------------------------------------------------------- S1.order
class S1Order(Case):
    def regs(self, slots, pre):
        by = {r["slot"]: r for r in pre["rows"]}
        return [dict(by[s], attempt=a) for s, a in slots]

    def test_the_frozen_order_passes_with_reruns(self):
        pre = design()
        base = [r["slot"] for r in pre["take_order"] if r["arm"] in ("A", "O")]
        regs = self.regs([(base[0], 1), (base[1], 1), (base[0], 2), (base[2], 1)], pre)
        self.assertEqual(self.must("S1.order", rb().order_problems, regs, pre), [], "S1.order")
        self.assertEqual(self.must("S1.order", rb().order_problems, [], pre), [], "S1.order: none registered")

    def test_a_swap_in_a_part_is_named(self):
        pre = design()
        base = [r["slot"] for r in pre["take_order"] if r["arm"] in ("A", "O")]
        got = self.must("S1.order", rb().order_problems, self.regs([(base[1], 1), (base[0], 1)], pre), pre)
        self.assertEqual(len(got), 1, f"S1.order: {got}")
        self.assertIn("not the frozen order", got[0], "S1.order")

    def test_the_high_water_mark_holds_after_a_problem(self):
        """Review mutant R24: an out-of-order registration never lowers the part's mark, so a later row still behind
        the mark is named too."""
        pre = design()
        base = [r["slot"] for r in pre["take_order"] if r["arm"] in ("A", "O")]
        got = self.must("S1.order", rb().order_problems, self.regs([(base[2], 1), (base[0], 1), (base[1], 1)], pre), pre)
        self.assertEqual(len(got), 2, f"S1.order: a row behind the mark passed after a problem: {got}")
        self.assertTrue(all(f"after slot {base[2]!r}" in x for x in got), f"S1.order: the mark moved: {got}")

    def test_a_deferred_arm_after_later_base_rows_passes(self):
        pre = design()
        base = [r["slot"] for r in pre["take_order"] if r["arm"] in ("A", "O")]
        g = [r["slot"] for r in pre["take_order"] if r["arm"] == "G"]
        regs = self.regs([(s, 1) for s in base] + [(s, 1) for s in g], pre)
        self.assertEqual(self.must("S1.order", rb().order_problems, regs, pre), [], "S1.order: a later go fails")
        swapped = self.regs([(s, 1) for s in base] + [(g[1], 1), (g[0], 1)], pre)
        got = self.must("S1.order", rb().order_problems, swapped, pre)
        self.assertTrue(got and "launch part 'G'" in got[0], f"S1.order: a swap inside G passed: {got}")
        one = design(deferred=False)
        self.assertNotEqual(self.must("S1.order", rb().order_problems, regs, one), [],
                            "S1.order: without deferred_arms, one part")

    def test_named_problems(self):
        pre = design()
        base = [r["slot"] for r in pre["take_order"] if r["arm"] in ("A", "O")]
        got = self.must("S1.order", rb().order_problems, self.regs([(base[0], 2)], pre), pre)
        self.assertTrue(any("not 1" in x for x in got), f"S1.order: {got}")
        got = self.must("S1.order", rb().order_problems, [{"slot": "s-x", "arm": "A", "attempt": 1}], pre)
        self.assertTrue(any("not in take_order" in x for x in got), f"S1.order: {got}")
        wrong = dict(self.regs([(base[0], 1)], pre)[0], arm="Z")
        got = self.must("S1.order", rb().order_problems, [wrong], pre)
        self.assertTrue(any("registered under arm" in x for x in got), f"S1.order: {got}")
        got = self.must("S1.order", rb().order_problems, [], dict(pre, take_order=None))
        self.assertTrue(got and "no take_order" in got[0], f"S1.order: {got}")


# ------------------------------------------------------------------------------------------------- S1.ledger
class S1Ledger(Case):
    def snap(self, doc, arms=("A", "O"), history=(), pre=None, now=NOW):
        return rb().ledger_snapshot(doc, pre=pre or design(), history=list(history), arms=arms, now=now)

    def test_exact_keys_start_and_now(self):
        got = self.must("S1.ledger", self.snap, doc_with(*READS))
        self.assertEqual(set(got), set(batch.LEDGER_KEYS), "S1.ledger: keys")
        self.assertEqual(got["start"], "2026-10-07T03:43:50Z", "S1.ledger: start (ruling 5)")
        self.assertEqual(costs.utc(got["now"]), NOW, "S1.ledger: now")
        self.assertIsNone(got["trimmed"], "S1.ledger")
        self.assertEqual(batch.ledger_shape_problems(got), [], "S1.ledger: batch's shape check")

    def test_every_spend_record_is_kept(self):
        records = (spend("google", "2026-10-07T03:43:50Z", "1.00"), spend("google", "2026-10-15T20:00:00Z", "15.87"),
                   spend("openai", "2026-10-21T12:00:00Z", "0"), spend("google", "2026-10-24T11:00:00Z", "0.50"))
        november = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=datetime.timezone.utc)   # the caps are round-wide
        got = self.must("S1.ledger", self.snap, doc_with(*records), now=november)
        self.assertEqual(got["spend"], [{k: r[k] for k in ("vendor", "at", "usd")} for r in records],
                         "S1.ledger: a spend record was dropped or changed")
        spent = costs.spent_since(got["spend"], got["start"])
        self.assertEqual(spent["google"], costs.amount("17.37"), "S1.ledger: Google's walk-phase spend not counted")

    def test_walks_only_for_the_runs_money_arms(self):
        pre = design()
        sol = [r["slot"] for r in pre["rows"] if r["model"] == "gpt-6.1-sol"]
        got = self.must("S1.ledger", self.snap, doc_with(*READS), history=[outcome(sol[0])])
        want = [{"vendor": "openai", "model": "gpt-6.1-sol", "agent": {"harness": "codex", "version": "0.162.1"},
                 "tries_left": 2, "cost_per_try": "0"},
                {"vendor": "openai", "model": "gpt-6-luna", "agent": {"harness": "codex", "version": "0.162.1"},
                 "tries_left": 3, "cost_per_try": "0"}]
        self.assertEqual(got["walks"], want, "S1.ledger: walks while G is deferred")
        with_g = self.must("S1.ledger", self.snap, doc_with(*READS), arms=("A", "O", "G"))
        g = {w["model"]: w["cost_per_try"] for w in with_g["walks"] if w["vendor"] == "google"}
        self.assertEqual(g, {"gemini-3.8-flash": "0.78", "gemini-3.5-flash-lite": "0.154"}, "S1.ledger: ruling 7")
        self.assertEqual(costs.walk_gate(got["walks"], got["spend"], got["start"])["decision"], costs.PROCEED,
                         "S1.ledger: the walk gate")

    def test_the_reading_passes_the_money_gate_for_an_o_row(self):
        snap = self.must("S1.ledger", self.snap, doc_with(*READS))
        row = next(r for r in design()["rows"] if r["arm"] == "O")
        ledger = types.SimpleNamespace(read=lambda: snap)
        self.assertEqual(batch.money_gate_problems([row], ledger, clock=lambda: NOW), [], "S1.ledger: money gate")

    def test_a_capped_vendor_without_a_read_refuses(self):
        for records, who in ((READS[1:], "google"), (READS[:1], "openai"), ((), "google")):
            self.refuses("S1.ledger", "LedgerRefused", who, self.snap, doc_with(*records))

    def test_each_stored_record_rule_refuses(self):
        good = READS[0]
        bad = {"extra key": dict(good, note="x"), "missing key": {k: v for k, v in good.items() if k != "by"},
               "vendor": dict(good, vendor="anthropic"), "usd number": dict(good, usd=16.87),
               "usd negative": dict(good, usd="-1"), "usd text": dict(good, usd="lots"),
               "before start": dict(good, at="2026-10-07T03:43:49Z"), "after now": dict(good, at="2026-10-25T00:00:00Z"),
               "naive": dict(good, at="2026-10-15T20:00:00"), "empty source": dict(good, source=" "),
               "empty by": dict(good, by="")}
        for name, rec in bad.items():
            with self.subTest(name=name):
                self.assertNotEqual(self.must("S1.ledger", rb().spend_record_problems, rec, now=NOW), [],
                                    f"S1.ledger: {name} admitted")
                self.refuses("S1.ledger", "LedgerRefused", "", self.snap, doc_with(rec, *READS))
        self.assertEqual(rb().spend_record_problems(good, now=NOW), [], "S1.ledger: a good record refused")
        for doc in ({"spend": []}, {"spend": {}, "trimmed": []}, [], {"spend": [], "trimmed": [], "x": 1}):
            self.refuses("S1.ledger", "LedgerRefused", "run-ledger.json", self.snap, doc)

    def test_the_latest_trim_record_and_its_rules(self):
        t1 = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11", "at": "2026-10-31T22:00:00Z",
              "figures": {"openai": "0", "google": "140"}}
        t2 = dict(t1, at="2026-10-31T23:00:00Z")
        got = self.must("S1.ledger", self.snap, doc_with(*READS, trimmed=(t1, t2)))
        self.assertEqual(got["trimmed"], t2, "S1.ledger: not the latest trim")
        for bad in (dict(t1, by="glitch"), dict(t1, kind="trim"), dict(t1, month="2026-13"), dict(t1, at="soon"),
                    dict(t1, figures={"openai": "0"}), {k: v for k, v in t1.items() if k != "figures"}):
            self.refuses("S1.ledger", "LedgerRefused", "trim", self.snap, doc_with(*READS, trimmed=(bad,)))

    def test_a_money_pair_without_a_cost_refuses(self):
        with mock.patch.dict(rb().COST_PER_TRY, {}, clear=True):
            self.refuses("S1.ledger", "LedgerRefused", "no registered cost per try", self.snap, doc_with(*READS))
        self.assertEqual(self.must("S1.ledger", self.snap, doc_with(*READS), arms=("A",))["walks"], [],
                         "S1.ledger: arm A bills nothing")

    def test_computed_reads(self):
        doc = doc_with(spend("google", "2026-10-22T20:00:00Z", "16.87", source=rb().COMPUTED_SOURCE), READS[1])
        self.assertEqual(rb().computed_reads(doc), ["google"], "S1.ledger: ruling 6's fallback not named")
        self.assertEqual(rb().computed_reads(doc_with(*READS)), [], "S1.ledger")
        self.assertEqual(rb().COMPUTED_SOURCE, "computed, not a vendor read", "S1.ledger: ruling 6's words")


class S1History(Case):
    def test_append_only_one_record_per_version(self):
        v1 = doc_with(READS[0])
        v2 = doc_with(*READS)
        self.assertEqual(rb().ledger_history_problems([v1, v2]), [], "S1.history")
        bad = {"changed": [v1, doc_with(dict(READS[0], usd="1"), READS[1])], "two at once": [doc_with(*READS)],
               "none added": [v1, v1], "removed": [v2, doc_with(READS[1])], "not a doc": [{"spend": []}]}
        for name, versions in bad.items():
            with self.subTest(name=name):
                self.assertNotEqual(rb().ledger_history_problems(versions), [], f"S1.history: {name}")


# ------------------------------------------------------------------------------------------------- scratch repository
class Scratch:
    def __init__(self):
        self.base = Path(tempfile.mkdtemp(prefix="run-builders-"))
        self.repo = self.base / "repo"
        self.root = self.repo / "evals" / "gap-study-4"
        self.root.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.name", "synthetic")
        self.git("config", "user.email", "synthetic@example.invalid")
        (self.root / "README").write_text("x\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")

    def git(self, *args):
        got = subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True,
                             env=dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))
        if got.returncode:
            raise RuntimeError(got.stderr)
        return got.stdout

    def commit_file(self, rel, data: bytes, msg="c"):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def close(self):
        shutil.rmtree(self.base, ignore_errors=True)


class S1Git(Case):
    def setUp(self):
        self.s = Scratch()
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.s.close()

    def append(self, rec):
        return rb().append_spend(rec, root=self.s.root, repo=self.s.repo, clock=lambda: NOW)

    def test_one_commit_per_record_and_the_ledger_reads(self):
        before = self.s.git("rev-list", "--count", "HEAD").strip()
        for rec in READS:
            self.must("S1.git", self.append, rec)
        self.assertEqual(int(self.s.git("rev-list", "--count", "HEAD")), int(before) + 2, "S1.git: one commit each")
        self.assertEqual(self.must("S1.git", rb().read_ledger_doc, self.s.root, self.s.repo), doc_with(*READS),
                         "S1.git")
        self.assertEqual(self.s.git("status", "--porcelain"), "", "S1.git: left dirty")
        led = rb().SpendLedger(root=self.s.root, repo=self.s.repo, pre=design(), history=lambda: [], arms=("A", "O"),
                               clock=lambda: NOW)
        self.assertEqual(self.must("S1.git", led.read)["spend"][0]["usd"], "16.87", "S1.git: SpendLedger.read")
        trim = {"kind": "caps trimmed", "by": "Javier", "month": "2026-11", "at": "2026-10-31T22:00:00Z",
                "figures": {"openai": "0", "google": "140"}}
        self.must("S1.git", rb().append_trim, trim, root=self.s.root, repo=self.s.repo)
        self.assertEqual(self.must("S1.git", led.read)["trimmed"], trim, "S1.git: trim")

    def test_a_dirty_repository_is_refused_with_nothing_written(self):
        (self.s.root / "stray").write_text("x")
        head = self.s.git("rev-parse", "HEAD")
        self.refuses("S1.git", "LedgerRefused", "clean repository", self.append, READS[0])
        self.assertEqual(self.s.git("rev-parse", "HEAD"), head, "S1.git")
        self.assertFalse((self.s.root / "run-ledger.json").exists(), "S1.git: written anyway")
        self.refuses("S1.git", "LedgerRefused", "", self.append, dict(READS[0], vendor="x"))

    def test_an_uncommitted_edit_or_a_rewritten_history_is_refused(self):
        self.must("S1.git", self.append, READS[0])
        (self.s.root / "run-ledger.json").write_text("{}")
        self.refuses("S1.git", "LedgerRefused", "uncommitted", rb().read_ledger_doc, self.s.root, self.s.repo)
        self.s.git("checkout", "-q", "--", ".")
        self.s.commit_file("run-ledger.json", (json.dumps(doc_with(dict(READS[0], usd="1"), READS[1])) + "\n").encode())
        self.refuses("S1.git", "LedgerRefused", "append-only", rb().read_ledger_doc, self.s.root, self.s.repo)

    def test_the_window_reads_committed_take_files(self):
        events = [{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": 1_800_000_000}}]
        self.s.commit_file("takes/s-1/1/turn-1.jsonl", b"\n".join(json.dumps(e).encode() for e in events))
        files = self.must("S1.git", rb().committed_take_files, self.s.root, self.s.repo, "s-1", 1)
        self.assertEqual(list(files), ["evals/gap-study-4/takes/s-1/1/turn-1.jsonl"], "S1.git")
        rows = [{"slot": "s-1", "attempt": 1, "agent": {"harness": "claude-code", "version": "v"}}]
        clock = types.SimpleNamespace(t=1_800_000_000 - 30)
        slept = []

        def sleep(s):
            slept.append(s)
            clock.t += s
        win = rb().UsageWindow(root=self.s.root, repo=self.s.repo, history=lambda: [outcome("s-1", state="pause",
                               final=False)], rows=lambda: rows, clock=lambda: clock.t, sleep=sleep)
        self.must("S1.git", win.wait_reset)
        self.assertEqual(clock.t, 1_800_000_000 + rb().RESET_MARGIN_S, f"S1.git: waited to {clock.t}")


# ------------------------------------------------------------------------------------------------- S1.window
def jl(*objs) -> bytes:
    return b"\n".join(json.dumps(o).encode() for o in objs) + b"\n"


def rle(status, reset, windows=None):
    info = {"status": status, "resetsAt": reset}
    if windows is not None:
        info["unifiedWindows"] = windows
    return {"type": "rate_limit_event", "rate_limit_info": info}


def rl(primary, secondary=None):
    return {"type": "event_msg", "payload": {"type": "token_count", "rate_limits": {"primary": primary,
                                                                                    "secondary": secondary}}}


class S1Window(Case):
    def test_claude_reset(self):
        files = {"x/turn-2.jsonl": jl(rle("rejected", 2_000), rle("allowed", 9_000)),
                 "x/turn-10.jsonl": jl(rle("rejected", 3_000), rle("allowed", 9_500))}
        self.assertEqual(self.must("S1.window", rb().claude_reset, files), 3_000.0,
                         "S1.window: the last refused event (turn order by number)")
        full = {"x/turn-1.jsonl": jl(rle("allowed", 1_000, {"five_hour": {"utilization": 1.0, "resetsAt": 4_000},
                                                            "seven_day": {"utilization": 0.4, "resetsAt": 8_000}}))}
        self.assertEqual(self.must("S1.window", rb().claude_reset, full), 4_000.0, "S1.window: a full window")
        none_full = {"x/turn-1.jsonl": jl(rle("allowed", 1_000, {"five_hour": {"utilization": 0.2, "resetsAt": 4_000}}))}
        self.assertEqual(self.must("S1.window", rb().claude_reset, none_full), 1_000.0, "S1.window: the last event")
        for files in ({}, {"x/turn-1.jsonl": jl({"type": "assistant"})}, {"x/notes.jsonl": jl(rle("rejected", 5))}):
            self.refuses("S1.window", "WindowRefused", "no rate_limit_event", rb().claude_reset, files)
        self.refuses("S1.window", "WindowRefused", "not an epoch", rb().claude_reset,
                     {"x/turn-1.jsonl": jl(rle("rejected", "soon"))})

    def test_codex_reset(self):
        files = {"s/native-turn-1.jsonl": jl(rl({"used_percent": 100.0, "resets_at": 7_000})),
                 "s/native-turn-2.jsonl": jl(rl({"used_percent": 100.0, "resets_at": 5_000},
                                                {"used_percent": 20.0, "resets_at": 9_000}))}
        self.assertEqual(self.must("S1.window", rb().codex_reset, files), 5_000.0, "S1.window: the full window")
        none_full = {"s/native-turn-1.jsonl": jl(rl({"used_percent": 10.0, "resets_at": 5_000},
                                                    {"used_percent": 20.0, "resets_at": 9_000}))}
        self.assertEqual(self.must("S1.window", rb().codex_reset, none_full), 9_000.0, "S1.window: the latest")
        self.refuses("S1.window", "WindowRefused", "no rate_limits", rb().codex_reset, {"s/native-turn-1.jsonl": b"{}\n"})
        self.refuses("S1.window", "WindowRefused", "holds no window", rb().codex_reset,
                     {"s/native-turn-1.jsonl": jl(rl(None))})

    def test_gemini_and_unknown_harnesses_raise(self):
        for harness in ("gemini", "fake-second"):
            msg = self.refuses("S1.window", "WindowRefused", "no reset signal", rb().reset_for, harness, {})
            self.assertIn("named residual", msg, "S1.window")
        self.assertEqual(self.must("S1.window", rb().reset_for, "claude-code",
                                   {"t/turn-1.jsonl": jl(rle("rejected", 42))}), 42.0, "S1.window")

    def target(self, history, resets, now):
        return rb().wait_target(history, lambda s, a: "claude-code",
                                lambda s, a: {"t/turn-1.jsonl": jl(rle("rejected", resets[s]))}, now)

    def test_wait_target(self):
        h = [outcome("s1"), outcome("s2", state="pause", final=False), outcome("s3", state="pause", final=False)]
        got = self.must("S1.window", self.target, h, {"s2": 1_000_500, "s3": 1_000_200}, 1_000_000)
        self.assertEqual(got, 1_000_500 + 120, "S1.window: latest reset plus the margin")
        ruled = [outcome("s1"), {"kind": "ruling", "slot": "s1", "attempt": 1, "ruling": "route", "route": "pause",
                                 "by": "x"}]
        self.assertEqual(self.must("S1.window", self.target, ruled, {"s1": 1_000_100}, 1_000_000), 1_000_220,
                         "S1.window: a ruled pause")
        old = [outcome("s0", state="pause", final=False)] + [outcome(f"s{i}") for i in range(1, batch.MAX_OPEN + 1)]
        self.refuses("S1.window", "WindowRefused", "holds no pause", self.target, old, {}, 1_000_000)

    def test_bounds(self):
        h = [outcome("s1", state="pause", final=False)]
        now = 10_000_000
        self.refuses("S1.window", "WindowRefused", "ahead", self.target, h, {"s1": now + 8 * 24 * 3600 + 1}, now)
        self.refuses("S1.window", "WindowRefused", "behind", self.target, h, {"s1": now - 24 * 3600 - 1}, now)
        self.assertEqual(self.must("S1.window", self.target, h, {"s1": now + 8 * 24 * 3600}, now),
                         now + 8 * 24 * 3600 + 120, "S1.window")

    def test_wait_until_returns_at_once_when_passed(self):
        def sleep(s):          # fails at once: a wait that loops on a fixed clock never hangs the test
            raise AssertionError(f"S1.window: slept {s} s although the window had reset")
        self.must("S1.window", rb().wait_until, 100.0, lambda: 100.0, sleep)
        self.must("S1.window", rb().wait_until, 100.0, lambda: 150.0, sleep)

    def test_wait_until_sleeps_in_bounded_chunks(self):
        clock = types.SimpleNamespace(t=0.0)
        slept = []

        def sleep(s):
            slept.append(s)
            clock.t += s
        reads = []

        def now():             # bounded: a wait that reads the clock without sleeping fails, never hangs the test
            reads.append(clock.t)
            if len(reads) > 50:
                raise AssertionError("S1.window: the clock was read 50 times without the wait ending")
            return clock.t
        self.must("S1.window", rb().wait_until, 700.0, now, sleep)
        self.assertEqual(slept, [300.0, 300.0, 100.0], "S1.window: chunks")
        self.assertEqual(clock.t, 700.0, "S1.window")


# ------------------------------------------------------------------------------------------------- S2
RUN_TOKEN_PATH = "/home/javier/gap4-secrets/claude-run/claude-run-token"      # ruling 4's words


class S2Login(Case):
    def test_the_run_token_path_and_the_rehearsals_walk_login(self):
        import walk_builders as wb
        self.assertEqual(rb().RUN_LOGIN_FILES, {"claude-run": RUN_TOKEN_PATH}, "S2.login: ruling 4")
        real_open = open
        with mock.patch("builtins.open", side_effect=AssertionError("S2.login: a login file was opened")), \
                mock.patch.object(os, "open", side_effect=AssertionError("S2.login: a login file was opened")):
            self.assertEqual(self.must("S2.login", rb().run_login_path), RUN_TOKEN_PATH, "S2.login: default")
            self.assertEqual(self.must("S2.login", rb().run_login_path, "claude-run"), RUN_TOKEN_PATH, "S2.login")
            got = self.must("S2.login", rb().run_login_path, "claude1")
        self.assertIs(real_open, open)
        self.assertEqual(got, wb.walk_login_path("claude1"), "S2.login: ruling 8, the walk login")
        self.assertNotEqual(got, RUN_TOKEN_PATH, "S2.login: the rehearsal used the run token")
        self.refuses("S2.login", "RunRefused", "no run login is recorded", rb().run_login_path, "claude2")
        self.assertEqual(rb().RUN_ACCOUNT, "claude-run", "S2.login")

    def test_the_run_login_files_are_a_plain_literal(self):
        """Part T contract line 1 (its review MAJOR-1): ops reads the assignment with ast.literal_eval."""
        tree = ast.parse((HERE / "run_builders.py").read_text())
        found = [n.value for n in tree.body if isinstance(n, ast.Assign)
                 and [getattr(x, "id", None) for x in n.targets] == ["RUN_LOGIN_FILES"]]
        self.assertEqual(len(found), 1, "S2.literal: RUN_LOGIN_FILES is not assigned exactly once at top level")
        try:
            value = ast.literal_eval(found[0])
        except ValueError as e:
            self.fail(f"S2.literal: ast.literal_eval refuses RUN_LOGIN_FILES: {e}")
        self.assertEqual(value, {"claude-run": RUN_TOKEN_PATH}, "S2.literal: not the ruled path")
        for bad in ("relative/token", "/home/javier/../x", None):
            with mock.patch.dict(rb().RUN_LOGIN_FILES, {"claude-run": bad}):
                self.refuses("S2.login", "RunRefused", "not an absolute, normalised path", rb().run_login_path)


def draft_rows(n=2):
    import prereg
    rows = prereg.load()["rows"]
    return [json.loads(json.dumps(r)) for r in rows[:n]]


class S2Identity(Case):
    def setUp(self):
        self.s = Scratch()
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.s.close()

    def register(self, rows):
        done = []
        for r in rows:
            done.append(r)
            self.s.commit_file("takes.json", (json.dumps({"rows": done}, indent=2) + "\n").encode(), "Register")

    def test_the_identity_is_the_open_registrations(self):
        import takes
        a, b = draft_rows(2)
        self.register([dict(a, attempt=1), dict(b, attempt=1)])
        got = self.must("S2.identity", rb().take_identity, self.s.root, self.s.repo, b["slot"])
        commits = takes.row_commits(root=self.s.root, repo=self.s.repo)
        self.assertEqual(got, {"index": 1, "attempt": 1, "row_commit": commits[1],
                               "session_id": takes.session_id_for(commits[1])}, "S2.identity")
        self.assertNotEqual(got["session_id"], takes.session_id_for(commits[0]), "S2.identity: another row's session")
        import drive
        try:
            rb().take_identity(self.s.root, self.s.repo, "s-not-registered")
        except drive.LaunchRefused as e:
            self.assertIn("open registrations", str(e), "S2.identity")
        else:
            self.fail("S2.identity: an unregistered slot gave an identity")


def origin_repo(base: Path):
    repo = base / "origin"
    (repo / "src").mkdir(parents=True)
    (repo / "evals").mkdir()
    (repo / "src" / "a.txt").write_text("a\n")
    (repo / "evals" / "secret.txt").write_text("study\n")
    (repo / "CLAUDE.md").write_text("instructions\n")
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    for args in (("init", "-q"), ("config", "user.name", "s"), ("config", "user.email", "s@example.invalid"),
                 ("add", "-A"), ("commit", "-q", "-m", "origin")):
        subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, capture_output=True,
                         text=True, env=env).stdout.strip()
    return repo, sha


class S2Tree(Case):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="run-tree-")).resolve()
        self.tmp = self.base / "tmp"
        self.tmp.mkdir()
        self.patches = [mock.patch.object(tempfile, "tempdir", str(self.tmp)),
                        mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})]
        for p_ in self.patches:
            p_.start()

    def tearDown(self):
        for p_ in self.patches:
            p_.stop()
        shutil.rmtree(self.base, ignore_errors=True)

    def test_the_takes_own_checkout(self):
        import drive
        repo, sha = origin_repo(self.base)
        sid = "11111111-2222-5333-8444-555555555555"
        tree = self.must("S2.tree", rb().build_take_run_tree, sid, repo=repo, commit=sha, exclude=["evals"],
                         harness="claude-code")
        self.assertEqual(Path(tree), self.tmp.resolve() / drive.neutral_name(sid), "S2.tree: not the take's session")
        self.assertTrue((Path(tree) / "src" / "a.txt").is_file(), "S2.tree")
        self.assertFalse((Path(tree) / "evals").exists(), "S2.tree: an excluded path in the checkout")
        self.assertFalse((Path(tree) / "AGENTS.md").exists(), "S2.tree: a native file for Claude Code")
        other = self.must("S2.tree", rb().build_take_run_tree, "99999999-2222-5333-8444-555555555555", repo=repo,
                          commit=sha, exclude=["evals"], harness="codex")
        self.assertNotEqual(Path(other), Path(tree), "S2.tree: two takes share a tree")
        self.assertEqual((Path(other) / "AGENTS.md").read_text(), "instructions\n", "S2.tree: R-6 for codex")

    def test_refusals_leave_nothing(self):
        import walk_builders as wb
        repo, sha = origin_repo(self.base)
        for kwargs, words in (({"commit": "0" * 40}, "was not built"), ({"commit": sha[:12]}, "40-hex"),
                              ({"exclude": "evals"}, "list of relative paths")):
            args = dict(repo=repo, commit=sha, exclude=["evals"], harness="claude-code")
            args.update(kwargs)
            with self.assertRaises(wb.BuilderRefused, msg="S2.tree") as got:
                rb().build_take_run_tree("11111111-2222-5333-8444-555555555555", **args)
            self.assertIn(words, str(got.exception), "S2.tree")
        with self.assertRaises(wb.BuilderRefused, msg="S2.tree"):
            rb().build_take_run_tree("", repo=repo, commit=sha, exclude=["evals"])
        self.assertEqual(list(self.tmp.iterdir()), [], "S2.tree: a refused build left something")


class S2Prepare(Case):
    def test_identity_tree_and_a_refused_fixture(self):
        import drive
        ident = {"index": 4, "attempt": 2, "row_commit": "c" * 40, "session_id": "sid-x"}
        row = {"slot": "s-1", "agent": {"harness": "codex", "version": "v"}}
        built, removed = [], []

        def tree_builder(sid, *, repo, commit, exclude, harness):
            built.append((sid, repo, commit, tuple(exclude), harness))
            return Path("/synthetic/tree-" + sid)
        with mock.patch.object(rb(), "take_identity", lambda root, repo, slot: dict(ident)):
            got = self.must("S2.prepare", rb().prepare_take, row, root="/r", repo="/repo", origin=("/o", "d" * 40),
                            exclude=["evals"], gars_tree_sha="e" * 40, tree_builder=tree_builder,
                            fixture_builder=lambda r, tree, project: ({"sha256": "f" * 64}, "/synthetic/source"))
            self.assertEqual(built, [("sid-x", "/o", "d" * 40, ("evals",), "codex")], "S2.prepare: the tree")
            self.assertEqual(got["identity"], {"session_id": "sid-x", "row": 4, "row_commit": "c" * 40,
                                               "source": "/synthetic/source", "fixture": {"sha256": "f" * 64},
                                               "gars_tree_sha": "e" * 40}, "S2.prepare: identity")
            self.assertEqual(set(got["identity"]), set(drive.IDENTITY_KEYS), "S2.prepare")
            self.assertEqual((got["project"], got["attempt"], got["tree"]),
                             (drive.neutral_name("sid-x"), 2, Path("/synthetic/tree-sid-x")), "S2.prepare")

            def refused(r, tree, project):
                raise RuntimeError("synthetic fixture refusal")
            import walk_builders as wb
            with mock.patch.object(wb, "remove_run_tree", lambda tree: removed.append(str(tree))):
                with self.assertRaises(RuntimeError, msg="S2.prepare"):
                    rb().prepare_take(row, root="/r", repo="/repo", origin=("/o", "d" * 40), exclude=["evals"],
                                      gars_tree_sha="e" * 40, tree_builder=tree_builder, fixture_builder=refused)
        self.assertEqual(removed, ["/synthetic/tree-sid-x"], "S2.prepare: a refused fixture left its tree")


class S2Road(Case):
    def road(self):
        self.removed = []
        return rb().TakeRoad(prepare=lambda r: {"tree": Path(f"/t/{r['slot']}"), "project": "p"},
                             remove=lambda tree: self.removed.append(str(tree)) or None)

    def test_prepare_state_discard_keep(self):
        road = self.road()
        a, b = {"slot": "a"}, {"slot": "b"}
        self.must("S2.road", road.prepare, a)
        self.must("S2.road", road.prepare, b)
        self.assertEqual(road.state(a)["tree"], Path("/t/a"), "S2.road")
        self.refuses("S2.road", "RunRefused", "already has a prepared take", road.prepare, a)
        road.discard("a")
        self.assertEqual(self.removed, ["/t/a"], "S2.road: discard did not remove the tree")
        self.refuses("S2.road", "RunRefused", "no prepared take", road.state, a)
        road.keep("b")
        self.assertEqual((self.removed, road.kept), (["/t/a"], [("b", "/t/b")]), "S2.road: keep removed the tree")
        road.discard("b")
        self.assertEqual(self.removed, ["/t/a"], "S2.road: a kept tree removed later")
        failing = rb().TakeRoad(prepare=lambda r: {"tree": Path("/t/x")}, remove=lambda tree: "synthetic: busy")
        failing.prepare({"slot": "x"})
        failing.discard("x")
        self.assertEqual(failing.problems, ["slot 'x': synthetic: busy"], "S2.road: a failed removal unnamed")


class FakeSub:
    def __init__(self, name, log, fail=None):
        self.name, self.log, self.fail = name, log, fail

    def launch(self, row):
        self.log.append((self.name, "launch", row["slot"]))
        if self.fail is not None:
            raise self.fail
        return f"cid-{self.name}-{row['slot']}"

    def drive(self, row, cid):
        self.log.append((self.name, "drive", cid))
        return {"by": self.name}

    def remove(self, cid):
        self.log.append((self.name, "remove", cid))

    def record_files(self, row, attempt):
        self.log.append((self.name, "files", row["slot"]))
        return [self.name]

    def published(self, row, attempt):
        self.log.append((self.name, "published", row["slot"]))


def a_row(slot, harness):
    return {"slot": slot, "agent": {"harness": harness, "version": "v"}}


class S2Driver(Case):
    def rig(self, fail=None, history=()):
        self.log = []
        road = rb().TakeRoad(prepare=lambda r: self.log.append(("road", "prepare", r["slot"])) or {"tree": Path("/t")},
                             remove=lambda tree: self.log.append(("road", "remove", str(tree))) or None)
        subs = {"claude-code": FakeSub("A", self.log), "codex": FakeSub("O", self.log, fail=fail)}
        return rb().RunDriver(drivers=subs, road=road, history=lambda: list(history),
                              precheck=lambda d, r: self.log.append(("check", d.name, r["slot"])))

    def test_each_call_reaches_the_rows_own_sub_driver(self):
        rd = self.rig()
        ca = self.must("S2.driver", rd.launch, a_row("s1", "claude-code"))
        co = self.must("S2.driver", rd.launch, a_row("s2", "codex"))
        self.assertEqual(rd.drive(a_row("s2", "codex"), co), {"by": "O"}, "S2.driver: drive")
        rd.remove(ca)
        rd.remove(co)
        self.assertEqual(rd.record_files(a_row("s1", "claude-code"), 1), ["A"], "S2.driver: record_files")
        self.assertEqual(self.log[:6], [("check", "A", "s1"), ("road", "prepare", "s1"), ("A", "launch", "s1"),
                                        ("check", "O", "s2"), ("road", "prepare", "s2"), ("O", "launch", "s2")],
                         "S2.driver: the records check first, then the take, then the launch")
        self.assertIn(("A", "remove", ca), self.log, "S2.driver")
        self.assertIn(("O", "remove", co), self.log, "S2.driver")
        self.refuses("S2.driver", "RunRefused", "has no driver in this run", rd.launch, a_row("s3", "gemini"))
        self.refuses("S2.driver", "RunRefused", "was not launched by this run", rd.remove, "cid-unknown")

    def test_a_refused_records_check_builds_nothing(self):
        rd = self.rig()
        rd.precheck = lambda d, r: (_ for _ in ()).throw(RuntimeError("synthetic: not registered"))
        with self.assertRaises(RuntimeError, msg="S2.driver"):
            rd.launch(a_row("s1", "claude-code"))
        self.assertEqual(self.log, [], "S2.driver: something was built before the records check")

    def test_a_failed_launch_removes_or_keeps_by_its_container(self):
        rd = self.rig(fail=RuntimeError("synthetic launch failure"))
        with self.assertRaises(RuntimeError, msg="S2.driver"):
            rd.launch(a_row("s2", "codex"))
        self.assertIn(("road", "remove", "/t"), self.log, "S2.driver: a launch with no container kept its tree")
        err = RuntimeError("synthetic launch failure, container left")
        err.container_id = "cid-left"
        rd = self.rig(fail=err)
        with self.assertRaises(RuntimeError, msg="S2.driver"):
            rd.launch(a_row("s2", "codex"))
        self.assertNotIn(("road", "remove", "/t"), self.log, "S2.driver: removed before batch removed the container")
        rd.remove("cid-left")
        self.assertIn(("O", "remove", "cid-left"), self.log, "S2.driver: the left container is not this run's")

    def test_published_removes_or_keeps_the_tree(self):
        clean = [outcome("s1", state="graded")]
        rd = self.rig(history=clean)
        rd.launch(a_row("s1", "claude-code"))
        rd.published(a_row("s1", "claude-code"), 1)
        self.assertEqual(self.log[-2:], [("A", "published", "s1"), ("road", "remove", "/t")], "S2.driver: publish")
        blocked = [dict(outcome("s1", state="blocked", final=False), drive_started=True)]
        rd = self.rig(history=blocked)
        rd.launch(a_row("s1", "claude-code"))
        rd.published(a_row("s1", "claude-code"), 1)
        self.assertNotIn(("road", "remove", "/t"), self.log, "S2.driver: a take needing a ruling lost its tree")
        self.assertEqual(rd.road.kept, [("s1", "/t")], "S2.driver: not kept for a human")


class FakeLease:
    made = []

    def __init__(self, src, uid_map=None, clock=None):
        self.src, self.walk_s, self.placed = src, None, None
        FakeLease.made.append(self)

    def place(self, cfg):
        self.placed = cfg
        return cfg + "/auth.json"

    def login_file_for(self, take):
        return ("login", self.placed)

    def secrets(self):
        return [("token", "shared"), ("token", f"v-{self.placed}")]


class S2Lease(Case):
    def test_one_lease_per_take(self):
        FakeLease.made = []
        pool = rb().LeasePool("/srv/codex2/auth.json", uid_map=None, clock=None,
                              walk_s_for=lambda r: {"s1": 100, "s2": 200}[r["slot"]], road_class=FakeLease)
        self.assertEqual(pool.secrets(), [], "S2.lease: secrets before any placement")
        pool.place({"slot": "s1"}, "/cfg1")
        pool.place({"slot": "s2"}, "/cfg2")
        self.assertEqual([(m.placed, m.walk_s) for m in FakeLease.made], [("/cfg1", 100), ("/cfg2", 200)],
                         "S2.lease: one placement per take, each with its own budget")
        take = types.SimpleNamespace(row={"slot": "s2"})
        self.assertEqual(pool.login_file_for(take), ("login", "/cfg2"), "S2.lease: another take's lease")
        self.assertEqual(pool.secrets(), [("token", "shared"), ("token", "v-/cfg1"), ("token", "v-/cfg2")],
                         "S2.lease: the union, each pair once")
        self.refuses("S2.lease", "RunRefused", "no lease is placed", pool.login_file_for,
                     types.SimpleNamespace(row={"slot": "s9"}))

    def test_union_secrets(self):
        got = rb().union_secrets(lambda: [("token", "a")], lambda: [("token", "a"), ("token", "b")])()
        self.assertEqual(got, [("token", "a"), ("token", "b")], "S2.lease: union")


class S2Harness(Case):
    """harness_driver hands walk_driver records="takes" and per-take hooks that read the road."""

    def builders(self):
        import walk_builders as wb
        return {"lock_path": "/lock", "proxy": "proxy-launch", "runtime": types.SimpleNamespace(run=lambda *a, **k: 0),
                "config_parent": "/cfgp", "sidecar_for": lambda r, ev, tree, project: ("side", ev, tree, project),
                "hosts": {}, "cgroup_dir_for": lambda take: "/cg", "pin_for": lambda r: {}, "design_for": None,
                "uid_map": None, "budgets": (600, 180, 1), "clock": None, "sleep": None, "ownership": "own",
                "settings_guard": "guard", "machine_gate": lambda: [], "login_path": "/login",
                "gemini_login_path": wb.Missing("synthetic: no gemini key"),
                "take_spec": lambda r, cfg, tree: ("spec", cfg, tree)}

    def test_claude_code_hooks_read_the_road(self):
        import drive
        import walk_builders as wb
        seen = {}
        road = rb().TakeRoad(prepare=lambda r: {"tree": Path("/t/" + r["slot"]), "project": "proj-" + r["slot"],
                                                "identity": {"session_id": "sid"}}, remove=lambda t: None)
        road.prepare({"slot": "s1"})
        with mock.patch.object(drive, "walk_driver", lambda **kw: seen.update(kw) or "driver"), \
                mock.patch.object(wb, "login_file_by_name", lambda path, h: "checked:" + path), \
                mock.patch.object(wb, "login_secrets", lambda login, h: (lambda: [("token", login)])), \
                mock.patch.object(wb, "vendor_config", lambda r, cfg, tree: None):
            driver, secrets = self.must("S2.harness", rb().harness_driver, self.builders(), "claude-code", road,
                                        "rules", "/root")
        self.assertEqual((driver, seen["records"], seen["root"], seen["login_file"]),
                         ("driver", "takes", "/root", "checked:/login"), "S2.harness")
        row = {"slot": "s1", "agent": {"harness": "claude-code", "version": "v"}}
        self.assertEqual(seen["spec_for"](row, "/cfg"), ("spec", "/cfg", "/t/s1"), "S2.harness: spec_for's tree")
        self.assertEqual(seen["sidecar_for"](row, "/ev"), ("side", "/ev", "/t/s1", "proj-s1"), "S2.harness: sidecar")
        self.assertEqual(seen["project_for"](row), "proj-s1", "S2.harness")
        got = seen["identity_for"](row)
        got["session_id"] = "changed"
        self.assertEqual(road.state(row)["identity"]["session_id"], "sid", "S2.harness: identity handed by reference")
        self.assertEqual(secrets(), [("token", "checked:/login")], "S2.harness")
        self.refuses("S2.harness", "RunRefused", "its login file is missing", rb().harness_driver, self.builders(),
                     "gemini", road, "rules", "/root")
        self.refuses("S2.harness", "RunRefused", "admits Claude Code, Codex and Gemini", rb().harness_driver,
                     self.builders(), "fake-second", road, "rules", "/root")

    def test_build_run_refuses_by_name_before_anything_is_built(self):
        import walk_builders as wb
        b = self.builders()
        b["runtime"] = wb.Missing("synthetic: no runtime")
        with mock.patch.object(wb, "walk_rules_scanner", side_effect=AssertionError("S2.build: built")):
            msg = self.refuses("S2.build", "RunRefused", "missing runtime: synthetic: no runtime", rb().build_run,
                               pre=design(), go=no_go, builders=b, root="/r", repo="/repo")
        for name in ("table", "rules_scanner", "run_tree_origin"):
            self.assertIn(f"missing {name}", msg, "S2.build: every missing value named")

    @contextlib.contextmanager
    def stand_ins(self):
        """build_run over stand-ins: every value present, no history, the per-harness driver and the take repository
        recorded, never built."""
        import drive
        import takes
        import walk_builders as wb
        seen = {"harness": []}
        b = dict(self.builders(), rules_scanner="rules", run_tree_origin=("/o", "t"), run_tree_exclude=(),
                 table={"t": 1})
        with mock.patch.object(wb, "missing", lambda builders: []), \
                mock.patch.object(takes, "read_history", lambda **kw: []), \
                mock.patch.object(wb, "walk_rules_scanner", lambda *a, **k: "rules"), \
                mock.patch.object(drive, "TakeRepo", lambda **kw: types.SimpleNamespace(history=lambda: [], **kw)), \
                mock.patch.object(rb(), "harness_driver",
                                  lambda builders, harness, road, rules, root: seen["harness"].append(
                                      (harness, builders["login_path"])) or (f"driver-{harness}",
                                                                             lambda: [(harness, "synthetic")])):
            yield b, seen

    def test_build_run_chooses_the_runs_arms(self):
        """MINOR-2 (review of 122b559e): no gemini sub-driver and no G walks before G's go record; both after it."""
        with self.stand_ins() as (b, seen):
            built = self.must("S2.build", rb().build_run, pre=design(), go=no_go, builders=b, root="/r", repo="/repo")
            self.assertEqual(built["arms"], ("A", "O"), "S2.build: the run's arms")
            self.assertNotIn("gemini", built["harnesses"], "S2.build: a gemini sub-driver before G's go record")
            self.assertEqual([h for h, _ in seen["harness"]], ["claude-code", "codex"], "S2.build: the sub-drivers")
            self.assertEqual(built["ledger"].arms, ("A", "O"), "S2.build: the ledger's arms")
            self.assertEqual(built["repo"].secrets(), [("claude-code", "synthetic"), ("codex", "synthetic")],
                             "S2.build: the take repository masks only the first harness's secrets (review R20)")
            self.assertEqual(seen["harness"][0][1], rb().RUN_LOGIN_FILES[rb().RUN_ACCOUNT],
                             "S2.build: the counted run's login")
            seen["harness"].clear()
            built = self.must("S2.build", rb().build_run, pre=design(), go=go_g, builders=b, root="/r", repo="/repo",
                              account=rb().REHEARSAL_ACCOUNT)
            self.assertEqual((built["arms"], built["ledger"].arms), (("A", "O", "G"), ("A", "O", "G")),
                             "S2.build: G after its go record")
            self.assertIn("gemini", built["harnesses"], "S2.build")
            self.assertNotEqual(seen["harness"][0][1], rb().RUN_LOGIN_FILES[rb().RUN_ACCOUNT],
                                "S2.build: the rehearsal's account ignored (the run token used)")

    def test_build_run_refuses_an_undeferred_ruled_arm(self):
        """MINOR-1: a design with G rows that does not defer G, and no go record, is refused by name before anything
        is built; a go record admits it."""
        with self.stand_ins() as (b, seen):
            self.refuses("S2.build", "RunRefused", "the frozen design does not defer arm G (OD105)", rb().build_run,
                         pre=design(deferred=False), go=no_go, builders=b, root="/r", repo="/repo")
            self.assertEqual(seen["harness"], [], "S2.build: built before the refusal")
            built = self.must("S2.build", rb().build_run, pre=design(deferred=False), go=go_g, builders=b, root="/r",
                              repo="/repo")
            self.assertIn("G", built["arms"], "S2.build: a go record does not admit G")
        self.assertEqual(rb().RULED_DEFERRALS, {"G": "OD105"}, "S2.build: the pinned deferral")


# ------------------------------------------------------------------------------------------------- S3
import contextlib  # noqa: E402
import io  # noqa: E402


def call(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = fn(*args, **kwargs)
    return rc, out.getvalue(), err.getvalue()


class S3Main(Case):
    def test_without_run_the_old_refusal_stays(self):
        rc, _, err = self.must("S3.main", call, target("batch").main, ["--foreground"])
        self.assertEqual(rc, 2, "S3.main")
        self.assertIn("batch: no driver exists yet; the sealed box's driver arrives in CP2", err, "S3.main")
        rc, out, _ = self.must("S3.main", call, target("batch").main, ["--check"])
        self.assertEqual((rc, out.strip()), (0, "batch: routing.json ready"), "S3.main: --check changed")

    def test_run_delegates_after_the_nohup_rule(self):
        seen = []
        with mock.patch.object(rb(), "run_main", lambda **kw: seen.append(kw) or 0), \
                mock.patch.object(target("batch"), "under_nohup", lambda: False):
            rc, _, err = self.must("S3.main", call, target("batch").main, ["--run"])
            self.assertEqual((rc, seen), (2, []), "S3.main: --run without nohup or --foreground ran")
            self.assertIn("run under nohup", err, "S3.main")
            rc, _, _ = self.must("S3.main", call, target("batch").main,
                                 ["--run", "--arms", "A,O", "--limit", "2", "--foreground"])
            self.assertEqual((rc, seen), (0, [{"arms": "A,O", "limit": 2, "serial": False}]), "S3.main: --run")
        with mock.patch.object(rb(), "run_main", lambda **kw: seen.append(kw) or 0), \
                mock.patch.object(target("batch"), "under_nohup", lambda: True):
            rc, _, _ = self.must("S3.main", call, target("batch").main, ["--run", "--serial"])
        self.assertEqual((rc, seen[-1]), (0, {"arms": None, "limit": None, "serial": True}), "S3.main: under nohup")

    def test_arms_and_limit_go_with_run(self):
        """NIT-1: --arms or --limit without --run is refused, before anything else."""
        seen = []
        with mock.patch.object(rb(), "run_main", lambda **kw: seen.append(kw) or 0):
            for argv in (["--arms", "A", "--foreground"], ["--limit", "1", "--foreground"], ["--arms", "A", "--check"]):
                rc, _, err = self.must("S3.main", call, target("batch").main, argv)
                self.assertEqual((rc, "batch: --arms and --limit go with --run" in err), (2, True),
                                 f"S3.main: {argv} accepted")
        self.assertEqual(seen, [], "S3.main: ran")


class FakeBatch:
    made = []
    stopped = None
    result: list = []

    def __init__(self, driver, repo, window, **kw):
        FakeBatch.made.append(dict(kw, driver=driver, repo=repo, window=window))
        self.stopped = FakeBatch.stopped

    def run(self, rows):
        FakeBatch.made[-1]["rows"] = rows
        if isinstance(FakeBatch.result, Exception):
            raise FakeBatch.result
        return FakeBatch.result


class S3RunMain(Case):
    def built(self, ledger="LEDGER"):
        road = rb().TakeRoad(prepare=lambda r: {}, remove=lambda t: None)
        return {"driver": "D", "repo": "R", "window": "W", "ledger": ledger, "rows": [{"slot": "s1"}],
                "arms": ("A", "O"), "harnesses": ["claude-code", "codex"], "road": road, "table": {"t": 1}}

    @contextlib.contextmanager
    def world(self, built, result=(), stopped=None):
        import prereg
        FakeBatch.made, FakeBatch.result, FakeBatch.stopped = [], result, stopped
        with mock.patch.object(prereg, "require_frozen", lambda what: design()), \
                mock.patch.object(rb(), "build_run", lambda **kw: built), \
                mock.patch.object(rb(), "read_ledger_doc", lambda root, repo: doc_with(*READS)), \
                mock.patch.object(batch, "Batch", FakeBatch):
            yield

    def test_the_loop_gets_the_ledger_and_no_history(self):
        with self.world(self.built(), result=[outcome("s1")]):
            rc, out, _ = self.must("S3.run", call, rb().run_main, serial=True, root="/r", repo="/repo")
        self.assertEqual(rc, 0, "S3.run")
        kw = FakeBatch.made[0]
        self.assertEqual((kw.get("ledger"), kw.get("serial"), kw.get("table"), kw["rows"]),
                         ("LEDGER", True, {"t": 1}, [{"slot": "s1"}]), "S3.run: the loop's inputs")
        self.assertNotIn("history", kw, "S3.run: history= passed (W1B4-6 i)")
        doc = json.loads(out)
        self.assertEqual((doc["counts"], doc["stopped"], doc["arms"], doc["rows"]),
                         ({"graded": 1}, None, ["A", "O"], 1), "S3.run: the summary")

    def test_a_spend_cap_stop_reads_spend_event(self):
        stop = {"slot": "s1", "attempt": 1, "state": "blocked", "reason": "routing: spend-cap-reached (openai)"}
        with self.world(self.built(), result=[outcome("s1", state="blocked", final=False)], stopped=stop):
            rc, out, _ = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual(rc, 1, "S3.run: a stopped loop exits 1")
        self.assertEqual(json.loads(out)["stopped"]["kind"], "spend event", "S3.run: a spend cap read as a stop")
        other = dict(stop, reason="nightly stop rule")
        with self.world(self.built(), stopped=other):
            _, out, _ = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual(json.loads(out)["stopped"]["kind"], "stop", "S3.run")

    def test_refusals_and_the_computed_read(self):
        import prereg
        with mock.patch.object(prereg, "require_frozen", lambda what: (_ for _ in ()).throw(SystemExit("not frozen"))):
            rc, _, err = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual((rc, "not frozen" in err), (2, True), "S3.run: an unfrozen design")
        with self.world(self.built()), mock.patch.object(rb(), "build_run",
                                                         side_effect=rb().RunRefused("missing runtime: x")):
            rc, _, err = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual((rc, "missing runtime: x" in err, FakeBatch.made), (2, True, []), "S3.run: built anyway")
        with self.world(self.built(), result=batch.BatchConfigError("rows refused")):
            rc, out, err = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual((rc, "rows refused" in err), (1, True), "S3.run: a refused row set")
        computed = doc_with(spend("google", "2026-10-22T20:00:00Z", "16.87", source=rb().COMPUTED_SOURCE), READS[1])
        with self.world(self.built(), result=[]), mock.patch.object(rb(), "read_ledger_doc", lambda r, p: computed):
            _, out, _ = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual(json.loads(out)["computed_spend_reads"], ["google"], "S3.run: ruling 6 not reported")

    def test_arms_narrow_reaches_build_run(self):
        """NIT-3: --arms reaches build_run as a list; NIT-2: a ledger history that cannot be read is a named refusal."""
        seen = []
        with self.world(self.built(), result=[]), mock.patch.object(rb(), "build_run",
                                                                    lambda **kw: seen.append(kw) or self.built()):
            self.must("S3.run", call, rb().run_main, arms="A", root="/r", repo="/repo")
            self.must("S3.run", call, rb().run_main, arms="A, O", root="/r", repo="/repo")
            self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual([kw["arms"] for kw in seen], [["A"], ["A", "O"], None], "S3.run: --arms not narrowed")
        with self.world(self.built()), mock.patch.object(rb(), "read_ledger_doc",
                                                         side_effect=rb().LedgerRefused("append-only broken")):
            rc, _, err = self.must("S3.run", call, rb().run_main, root="/r", repo="/repo")
        self.assertEqual((rc, "batch: refused: LedgerRefused: append-only broken" in err, FakeBatch.made),
                         (2, True, []), "S3.run: a bad ledger history is not a named refusal")

    def test_go_reader_is_r5s(self):
        import prereg
        seen = []
        with mock.patch.object(prereg, "committed_go_records", lambda root=None: seen.append(root) or ["rec"]), \
                mock.patch.object(prereg, "deferred_arm_go", lambda arm, records: arm == "G" and records == ["rec"]):
            go = rb().go_reader("/root")
            self.assertEqual((go("G"), go("O"), seen), (True, None, ["/root", "/root"]), "S3.run: the go reader")


class S3Writers(Case):
    def setUp(self):
        self.s = Scratch()
        self.patches = [mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}),
                        mock.patch.object(rb(), "STUDY_ROOT", [self.s.root])]
        for p_ in self.patches:
            p_.start()

    def tearDown(self):
        for p_ in self.patches:
            p_.stop()
        self.s.close()

    def count(self):
        return int(self.s.git("rev-list", "--count", "HEAD"))

    def test_spend_read_and_trimmed_make_one_commit_each(self):
        n = self.count()
        rc, out, err = self.must("S3.writers", call, rb().main, ["spend-read", "--vendor", "google", "--usd", "16.87",
                                 "--at", "2026-10-15T20:00:00Z", "--source", "r4-g billing page", "--by", "Javier"])
        self.assertEqual((rc, self.count()), (0, n + 1), f"S3.writers: spend-read {err}")
        self.assertEqual(json.loads(out)["commit"], self.s.git("rev-parse", "HEAD").strip(), "S3.writers")
        rc, _, err = self.must("S3.writers", call, rb().main, ["trimmed", "--month", "2026-11", "--at",
                               "2026-10-31T22:00:00Z", "--by", "Javier", "--figure", "google=140", "--figure", "openai=0"])
        self.assertEqual((rc, self.count()), (0, n + 2), f"S3.writers: trimmed {err}")
        doc = rb().read_ledger_doc(self.s.root, self.s.repo)
        self.assertEqual(doc["trimmed"], [{"kind": "caps trimmed", "by": "Javier", "month": "2026-11",
                                           "at": "2026-10-31T22:00:00Z", "figures": {"google": "140", "openai": "0"}}],
                         "S3.writers")
        for argv in (["trimmed", "--month", "2026-11", "--at", "2026-10-31T22:00:00Z", "--by", "glitch", "--figure",
                      "google=140", "--figure", "openai=0"],
                     ["trimmed", "--month", "2026-11", "--at", "2026-10-31T22:00:00Z", "--by", "Javier", "--figure",
                      "google=140", "--figure", "google=1"]):
            rc, _, _ = self.must("S3.writers", call, rb().main, argv)
            self.assertEqual((rc, self.count()), (1, n + 2), f"S3.writers: {argv} committed")

    def test_night_ruling_is_takes_door(self):
        seen = []

        def door(**kw):
            seen.append(kw)
            self.s.commit_file("rulings.json", b"[]\n", "one night ruling")
        import takes
        n = self.count()
        with mock.patch.object(takes, "commit_night_ruling", door):
            rc, out, _ = self.must("S3.writers", call, rb().main, ["night-ruling", "--slot", "s-1", "--attempt", "2",
                                                                    "--by", "Javier"])
        self.assertEqual((rc, self.count()), (0, n + 1), "S3.writers: night-ruling")
        self.assertEqual(seen, [{"slot": "s-1", "attempt": 2, "by": "Javier", "root": self.s.root.resolve(),
                                 "repo": self.s.repo.resolve()}], "S3.writers: the door's arguments")


class S3Hook(Case):
    def test_the_order_check_reaches_publication(self):
        import result
        import stats
        cr = target("check_results")
        fake = types.SimpleNamespace(produce=lambda rows, history, grade, table=None: {"records": []})
        with mock.patch.object(cr, "pipeline", lambda: fake), mock.patch.object(stats, "check_records", lambda r: None), \
                mock.patch.object(cr.takes_mod, "require_planned_row", lambda row, pre: None), \
                mock.patch.object(result, "from_records", lambda *a: "doc"), \
                mock.patch.object(result, "render", lambda doc: "PAGE"), \
                mock.patch.object(rb(), "order_problems", lambda rows, pre: ["synthetic order problem"]):
            got = self.must("S3.hook", cr.check_publication, [{"slot": "s"}], [], [], design(), "PAGE", None)
        self.assertEqual(got, ["synthetic order problem"], "S3.hook: the order check does not reach publication")


class S3Blob(Case):
    def test_take_blobs_admitted_other_paths_refused(self):
        pat = target("box/walk_launch").EVIDENCE_BLOB
        slot, blob = "s-" + "a1" * 32, "f" * 64
        good = [f"evals/gap-study-4/takes/{slot}/1/evidence/blobs/{blob}",
                f"evals/gap-study-4/takes/{slot}/12/evidence/blobs/{blob}",
                f"evals/gap-study-4/rehearsals/w-o42/evidence/blobs/{blob}"]
        bad = [f"evals/gap-study-4/takes/s-{'a1' * 31}a/1/evidence/blobs/{blob}",
               f"evals/gap-study-4/takes/{slot}/0/evidence/blobs/{blob}",
               f"evals/gap-study-4/takes/{slot}/1/evidence/other/{blob}",
               f"evals/gap-study-4/takes/{slot}/1/session/evidence/blobs/{blob}",
               f"evals/gap-study-4/takes/../{slot}/1/evidence/blobs/{blob}",
               f"evals/gap-study-4/takes/S-{'A1' * 32}/1/evidence/blobs/{blob}",
               f"evals/gap-study-4/{slot}/1/evidence/blobs/{blob}"]
        self.assertEqual([p_ for p_ in good if not pat.fullmatch(p_)], [], "S3.blob: a take or walk blob refused")
        self.assertEqual([p_ for p_ in bad if pat.fullmatch(p_)], [], "S3.blob: a path outside the take folder admitted")


# ------------------------------------------------------------------------------------------------- S4
def arow(slot, arm):
    h, v = AGENTS[arm]
    return {"slot": slot, "arm": arm, "agent": {"harness": h, "version": v}}


class S4Rows(Case):
    def test_the_first_a_and_the_first_o_in_frozen_order(self):
        rows = [arow("s1", "O"), arow("s2", "A"), arow("s3", "O"), arow("s4", "A")]
        got = self.must("S4.rows", rb().rehearsal_rows, rows)
        self.assertEqual([r["slot"] for r in got], ["s1", "s2"], "S4.rows: not the first A and O in frozen order")
        got = self.must("S4.rows", rb().rehearsal_rows, [arow("s2", "A"), arow("s1", "O")])
        self.assertEqual([r["slot"] for r in got], ["s2", "s1"], "S4.rows")
        for rows in ([arow("s1", "A")], [arow("s1", "O")], []):
            with self.assertRaises(rb().RehearsalRefused, msg="S4.rows") as got_e:
                rb().rehearsal_rows(rows)
            self.assertEqual(got_e.exception.reason, "rows-missing", "S4.rows")


class S4Summary(Case):
    def test_overlap(self):
        t = {"a": {"launched_at": 0, "drive_started_at": 1, "drive_ended_at": 10},
             "b": {"launched_at": 5, "drive_started_at": 6, "drive_ended_at": 12}}
        self.assertTrue(rb().overlap_of(t), "S4.summary: an overlap missed")
        serial = {"a": {"launched_at": 0, "drive_started_at": 1, "drive_ended_at": 4},
                  "b": {"launched_at": 5, "drive_started_at": 6, "drive_ended_at": 12}}
        self.assertFalse(rb().overlap_of(serial), "S4.summary: a serial run read as overlapping")
        self.assertFalse(rb().overlap_of({"a": {"launched_at": 0, "drive_started_at": None, "drive_ended_at": None},
                                          "b": {"launched_at": 5, "drive_started_at": 6, "drive_ended_at": 9}}),
                         "S4.summary: an undriven take")
        # glitch-f1's ruling 2 on the fold: overlap is two drive intervals intersecting, never launch-during-drive.
        wave = {"a": {"launched_at": 0, "drive_started_at": 2, "drive_ended_at": 5},       # batch.Batch's wave: both
                "b": {"launched_at": 1, "drive_started_at": 3, "drive_ended_at": 4}}       # launched, then both driven
        self.assertTrue(rb().overlap_of(wave), "S4.summary: two intersecting drives read as no overlap")
        launched_only = {"a": {"launched_at": 0, "drive_started_at": 1, "drive_ended_at": 4},
                         "b": {"launched_at": 2, "drive_started_at": 5, "drive_ended_at": 9}}
        self.assertFalse(rb().overlap_of(launched_only),
                         "S4.summary: a launch during a drive read as overlap, the drives never intersecting")
        touching = {"a": {"launched_at": 0, "drive_started_at": 1, "drive_ended_at": 4},
                    "b": {"launched_at": 0, "drive_started_at": 4, "drive_ended_at": 9}}
        self.assertFalse(rb().overlap_of(touching), "S4.summary: drives that only touch read as overlapping")

    def test_exact_keys_closed_values_and_pass(self):
        times = {"s1": {"launched_at": 100.0, "drive_started_at": 101.0, "drive_ended_at": 200.0},
                 "s2": {"launched_at": 150.0, "drive_started_at": 151.0, "drive_ended_at": 210.0}}
        outs = [dict(outcome("s1"), reason="words never written"), dict(outcome("s2", state="rehearsal", final=False))]
        commits = {("s1", 1): "a" * 40, ("s2", 1): "b" * 40}
        arms = {"s1": "A", "s2": "O"}
        got = self.must("S4.summary", rb().rehearsal_summary, outs, times, commits, arms=arms)
        self.assertEqual(set(got), {"takes", "overlap", "pass", "counts"}, "S4.summary: the contract keys")
        for t in got["takes"]:
            self.assertEqual(set(t), {"arm", "state", "route", "commit", "launched_at", "drive_started_at",
                                      "drive_ended_at"}, "S4.summary: a take's keys")
        self.assertEqual([t["arm"] for t in got["takes"]], ["A", "O"], "S4.summary: the arm field")
        self.assertNotIn("words never written", json.dumps(got), "S4.summary: a reason's text was written")
        self.assertEqual((got["pass"], got["overlap"], got["counts"]), (True, True, {"graded": 1, "rehearsal": 1}),
                         "S4.summary")
        self.assertEqual(got["takes"][0]["launched_at"], "1970-01-01T00:01:40+00:00", "S4.summary: the time")
        self.assertEqual(got["takes"][1]["state"], "committed", "S4.summary")
        blocked = [outs[0], dict(outcome("s2", state="blocked", final=False))]
        self.assertFalse(rb().rehearsal_summary(blocked, times, commits, arms=arms)["pass"],
                         "S4.summary: a blocked take passed")
        uncommitted = rb().rehearsal_summary(outs, times, {("s1", 1): "a" * 40}, arms=arms)
        self.assertEqual((uncommitted["pass"], uncommitted["takes"][1]["state"]), (False, "not committed"),
                         "S4.summary: an uncommitted take passed")
        serial = dict(times, s2={"launched_at": 300.0, "drive_started_at": 301.0, "drive_ended_at": 400.0})
        self.assertFalse(rb().rehearsal_summary(outs, serial, commits, arms=arms)["pass"],
                         "S4.summary: no overlap passed")
        self.assertFalse(rb().rehearsal_summary(outs[:1], times, commits, arms=arms)["pass"],
                         "S4.summary: one take passed")
        self.refuses("S4.summary", "RunRefused", "no rehearsal arm", rb().rehearsal_summary, outs, times, commits,
                     arms={"s1": "A"})

    def test_the_lease_refusal_entry(self):
        times = {"s1": {"launched_at": 100.0, "drive_started_at": 101.0, "drive_ended_at": 200.0}}
        got = rb().rehearsal_summary([outcome("s1")], times, {("s1", 1): "a" * 40}, arms={"s1": "A"},
                                     lease_refused=True)
        self.assertEqual(got["takes"][1], {"arm": "O", "state": "refused", "reason": "codex lease not live",
                                           "route": None, "commit": None, "launched_at": None,
                                           "drive_started_at": None, "drive_ended_at": None},
                         "S4.summary: the lease refusal entry (Part T's contract)")
        self.assertEqual((got["takes"][0]["arm"], got["takes"][0]["state"], got["pass"]), ("A", "committed", False),
                         "S4.summary")
        self.assertEqual([t for t in got["takes"] if "reason" in t], [got["takes"][1]],
                         "S4.summary: a reason on another take")

    def test_a_refusal_is_one_closed_entry(self):
        got = rb().rehearsal_summary([], {}, {}, refused="codex-lease-not-live")
        self.assertEqual(got, {"takes": [], "overlap": False, "pass": False,
                               "counts": {"refused:codex-lease-not-live": 1}}, "S4.summary: the refusal")
        self.refuses("S4.summary", "RunRefused", "not a closed rehearsal refusal", rb().rehearsal_summary, [], {}, {},
                     refused="anything else")


class S4Timed(Case):
    def test_times_around_launch_and_drive(self):
        clock = iter([1.0, 2.0, 3.0]).__next__
        inner = FakeSub("A", [])
        td = rb().TimedDriver(inner, clock)
        cid = td.launch(a_row("s1", "claude-code"))
        td.drive(a_row("s1", "claude-code"), cid)
        td.remove(cid)
        self.assertEqual(td.times, {"s1": {"launched_at": 1.0, "drive_started_at": 2.0, "drive_ended_at": 3.0}},
                         "S4.timed")
        self.assertEqual([x[1] for x in inner.log], ["launch", "drive", "remove"], "S4.timed: calls not passed on")


class S4Lease(Case):
    def builders(self, lease="/srv/codex2/auth.json"):
        design_view = types.SimpleNamespace(script=["a", "b"])
        return {"lease_path": lease, "design_for": lambda r, t: design_view, "budgets": (600, 180, 1),
                "clock": lambda: 1000.0}

    def test_a_dead_lease_is_a_closed_refusal(self):
        import walk_builders as wb
        rows = [arow("s1", "A"), arow("s2", "O")]
        with mock.patch.object(wb, "codex_gate_problem", lambda: None), \
                mock.patch.object(wb, "walk_budget_s", lambda script, budgets: 1200), \
                mock.patch.object(wb, "lease_freshness_problem", lambda path, now, walk_s: None):
            self.assertIsNone(rb().lease_problem(self.builders(), rows), "S4.lease: a live lease refused")
        for patches in ({"lease_freshness_problem": lambda path, now, walk_s: "expires in 3 min"},
                        {"codex_gate_problem": lambda: "the Codex lease gate is closed"},
                        {"lease_freshness_problem": lambda path, now, walk_s: (_ for _ in ()).throw(OSError("x"))}):
            base = {"codex_gate_problem": lambda: None, "walk_budget_s": lambda s, b: 1200,
                    "lease_freshness_problem": lambda path, now, walk_s: None}
            base.update(patches)
            with contextlib.ExitStack() as st:
                for k, v in base.items():
                    st.enter_context(mock.patch.object(wb, k, v))
                self.assertEqual(rb().lease_problem(self.builders(), rows), "codex-lease-not-live",
                                 f"S4.lease: {list(patches)} not refused")
        with mock.patch.object(wb, "codex_gate_problem", lambda: None):
            self.assertEqual(rb().lease_problem(self.builders(lease=wb.Missing("none")), rows), "codex-lease-not-live",
                             "S4.lease: a missing lease source")
        self.assertIsNone(rb().lease_problem(self.builders(), rows[:1]), "S4.lease: an A row needs no lease")


class HookSub(FakeSub):
    """A FakeSub whose next drive first runs `hook` (a launch made while that drive runs)."""
    hook = None

    def drive(self, row, cid):
        hook, self.hook = self.hook, None
        if hook is not None:
            hook()
        return super().drive(row, cid)


class S4Takes(Case):
    """rehearse_takes: ruling 8's rows, the walk login, the lease refusal before any take, and the summary file."""

    def setUp(self):
        self.out = Path(tempfile.mkdtemp(prefix="rehearse-out-"))

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def world(self, lease=None):
        import prereg
        seen = {}
        inner = HookSub("A", [])
        built = {"driver": inner, "repo": "R", "window": "W", "ledger": "L", "table": {},
                 "rows": [arow("s1", "O"), arow("s2", "A"), arow("s3", "A"), arow("s4", "O")], "arms": ("A", "O"),
                 "road": rb().TakeRoad(prepare=lambda r: {}, remove=lambda t: None)}

        class Loop:
            def __init__(self, driver, repo, window, **kw):
                seen["loop"] = dict(kw, driver=driver)

            def run(self, rows):
                """Batch's wave: both takes launched, then the second driven while the first's drive runs."""
                seen["rows"] = [r["slot"] for r in rows]
                td = seen["loop"]["driver"]
                cids = {r["slot"]: td.launch(r) for r in rows}
                if len(rows) > 1:
                    inner.hook = lambda: td.drive(rows[1], cids[rows[1]["slot"]])
                td.drive(rows[0], cids[rows[0]["slot"]])
                return [outcome(r["slot"]) for r in rows]
        st = contextlib.ExitStack()
        st.enter_context(mock.patch.object(prereg, "require_frozen", lambda what: design()))
        st.enter_context(mock.patch.object(rb(), "build_run", lambda **kw: seen.update(build=kw) or built))
        st.enter_context(mock.patch.object(rb(), "lease_problem", lambda b, rows: lease))
        st.enter_context(mock.patch.object(rb(), "outcome_commits",
                                           lambda root, repo: {("s1", 1): "a" * 40, ("s2", 1): "b" * 40}))
        return st, seen, Loop

    def test_the_two_takes_on_the_walk_login(self):
        ticks = iter(range(100)).__next__
        st, seen, loop = self.world()
        with st:
            rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r", repo="/repo",
                           clock=lambda: float(ticks()), batch_class=loop)
        self.assertEqual(seen["rows"], ["s1", "s2"], "S4.takes: not the first O and A rows in frozen order")
        self.assertEqual((seen["build"]["account"], seen["build"]["arms"]), ("claude1", ["A", "O"]),
                         "S4.takes: the rehearsal's login or arms (ruling 8)")
        self.assertNotIn("history", seen["loop"], "S4.takes: history= passed")
        summary = json.loads((self.out / "summary.json").read_text())
        self.assertEqual(set(summary), {"takes", "overlap", "pass", "counts"}, "S4.takes")
        self.assertEqual((rc, summary["overlap"], summary["pass"]), (0, True, True), f"S4.takes: {summary}")

    def test_a_dead_lease_runs_the_a_take_alone(self):
        ticks = iter(range(100)).__next__
        st, seen, loop = self.world(lease="codex-lease-not-live")
        with st:
            rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r", repo="/repo",
                           clock=lambda: float(ticks()), batch_class=loop)
        self.assertEqual(seen["rows"], ["s2"], "S4.takes: the O take ran on a dead lease, or the A take did not run")
        summary = json.loads((self.out / "summary.json").read_text())
        self.assertEqual([(t["arm"], t["state"], t.get("reason")) for t in summary["takes"]],
                         [("A", "committed", None), ("O", "refused", "codex lease not live")], f"S4.takes: {summary}")
        self.assertEqual((rc, summary["pass"]), (3, False), "S4.takes: the lease refusal's exit")

    def test_a_refused_build_writes_a_closed_reason(self):
        st, seen, loop = self.world()
        with st, mock.patch.object(rb(), "build_run", side_effect=rb().RunRefused("missing runtime: words")):
            rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r", repo="/repo",
                           clock=lambda: 0.0, batch_class=loop)
        text = (self.out / "summary.json").read_text()
        self.assertEqual((rc, json.loads(text)["counts"]), (1, {"refused:builders-missing": 1}), "S4.takes")
        self.assertNotIn("words", text, "S4.takes: a refusal's words were written")

    def test_a_dead_lease_exits_3_only_beside_a_done_a_take(self):
        """Closure NIT-1: exit 3 needs the A take committed under a route; a blocked or uncommitted A take beside a dead
        lease exits 1 (the review's mutant X8)."""
        for state, commits, why in (("blocked", {("s2", 1): "b" * 40}, "a blocked A take"),
                                    ("graded", {}, "an uncommitted A take")):
            ticks = iter(range(100)).__next__
            st, seen, loop = self.world(lease="codex-lease-not-live")

            class Ends(loop):
                def run(self_, rows, state=state):
                    return [dict(o, state=state, final=False) for o in super().run(rows)]
            with st, mock.patch.object(rb(), "outcome_commits", lambda root, repo, c=commits: c):
                rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r",
                               repo="/repo", clock=lambda: float(ticks()), batch_class=Ends)
            self.assertEqual(rc, 1, f"S4.takes: {why} beside a dead lease exited {rc}, not 1")

    def test_a_loop_error_is_one_closed_refusal(self):
        """Closure MINOR-1: a BatchConfigError (or any error) from the loop's construction or run is written as the
        closed refusal batch-config, so summary.json always exists; main never lets one escape either."""
        class Refuses:
            def __init__(self, driver, repo, window, **kw):
                raise batch.BatchConfigError("routing.json is not ready: words")

        class Breaks:
            def __init__(self, driver, repo, window, **kw):
                pass

            def run(self, rows):
                raise RuntimeError("words")
        for cls in (Refuses, Breaks):
            st, seen, _ = self.world()
            with st:
                rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r",
                               repo="/repo", clock=lambda: 0.0, batch_class=cls)
            path = self.out / "summary.json"
            text = path.read_text() if path.exists() else "{}"
            self.assertEqual((rc, json.loads(text)), (1, {"takes": [], "overlap": False, "pass": False,
                                                          "counts": {"refused:batch-config": 1}}),
                             f"S4.takes: {cls.__name__}")
            self.assertNotIn("words", text, "S4.takes: the error's words were written")
            path.unlink(missing_ok=True)
        with mock.patch.object(rb(), "rehearse_takes", side_effect=batch.BatchConfigError("words")):
            rc, _, err = self.must("S4.takes", call, rb().main, ["rehearse-takes", "--out", str(self.out)])
        text = (self.out / "summary.json").read_text() if (self.out / "summary.json").exists() else "{}"
        self.assertEqual((rc, json.loads(text).get("counts")), (1, {"refused:batch-config": 1}),
                         "S4.takes: an error escaping rehearse_takes left no closed summary")
        self.assertNotIn("words", text, "S4.takes")

    def stopping_loop(self, reason):
        class Stops:
            stopped = None

            def __init__(self, driver, repo, window, **kw):
                pass

            def run(self, rows):
                self.stopped = {"slot": rows[0]["slot"], "attempt": 1, "state": "blocked", "reason": reason}
                return []
        return Stops

    def test_a_stop_with_no_take_is_one_closed_refusal(self):
        """MAJOR-1: a loop stopped by the money gate before any take is refused:money-gate; any other stop with no take
        is refused:loop-stopped; never a bare fail with no reason, and no stop words written."""
        for reason, want in (("the money gate refuses the block (nothing registered or launched): words", "money-gate"),
                             ("registering slot s1 failed: words", "loop-stopped")):
            st, seen, _ = self.world()
            with st:
                rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r",
                               repo="/repo", clock=lambda: 0.0, batch_class=self.stopping_loop(reason))
            text = (self.out / "summary.json").read_text()
            self.assertEqual((rc, json.loads(text)), (1, {"takes": [], "overlap": False, "pass": False,
                                                          "counts": {f"refused:{want}": 1}}), f"S4.takes: {reason}")
            self.assertNotIn("words", text, "S4.takes: the stop's words were written")

    def test_kept_run_trees_are_removed(self):
        """MINOR-3: a run tree the road kept for a human is removed at the end, counted in kept_removed; a tree that
        cannot be removed is refused:run-tree-left."""
        for fails in (False, True):
            removed = []
            road = rb().TakeRoad(prepare=lambda r: {"tree": "/t/" + r["slot"]},
                                 remove=lambda t: (removed.append(t) or None) if not fails or t != "/t/s2" else "busy")
            ticks = iter(range(100)).__next__
            st, seen, loop = self.world()
            with st:
                real_build = rb().build_run

                def build(**kw):
                    built = real_build(**kw)
                    built["road"] = road
                    return built

                class Keeps(loop):
                    def run(self_, rows):
                        got = super().run(rows)
                        for r in rows:                  # each take's tree held for a human (a ruling owed)
                            road.prepare(r)
                            road.keep(r["slot"])
                        return got
                with mock.patch.object(rb(), "build_run", build):
                    rc = self.must("S4.takes", rb().rehearse_takes, str(self.out), builders={"x": 1}, root="/r",
                                   repo="/repo", clock=lambda: float(ticks()), batch_class=Keeps)
            summary = json.loads((self.out / "summary.json").read_text())
            self.assertEqual(road.kept, [], "S4.takes: a kept run tree left on the road")
            if fails:
                self.assertEqual((rc, summary["counts"]), (1, {"refused:run-tree-left": 1}),
                                 f"S4.takes: a tree left outside <dir>: {summary}")
            else:
                self.assertEqual(sorted(removed), ["/t/s1", "/t/s2"], "S4.takes: the kept trees not removed")
                self.assertEqual((rc, summary["counts"]), (0, {"graded": 2, "kept_removed": 2}),
                                 f"S4.takes: {summary}")


class S4Rehearse(Case):
    def setUp(self):
        self.s = Scratch()
        self.base = Path(tempfile.mkdtemp(prefix="rehearse-")).resolve()
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.s.close()
        shutil.rmtree(self.base, ignore_errors=True)

    def test_refusals_before_anything(self):
        calls = []
        runner = lambda argv, cwd: calls.append(argv) or (0, "")  # noqa: E731
        inside = self.s.repo / "out"
        self.assertEqual(rb().rehearse(inside, source=self.s.repo, review="r" * 40, runner=runner), 1, "S4.rehearse")
        self.assertFalse(inside.exists(), "S4.rehearse: wrote into the source repository")
        full = self.base / "full"
        full.mkdir()
        (full / "x").write_text("x")
        rb().rehearse(full, source=self.s.repo, review="r" * 40, runner=runner)
        self.assertEqual(json.loads((full / "summary.json").read_text())["counts"], {"refused:out-not-empty": 1},
                         "S4.rehearse")
        (self.s.root / "stray").write_text("x")
        dirty = self.base / "dirty"
        rb().rehearse(dirty, source=self.s.repo, review="r" * 40, runner=runner)
        self.assertEqual(json.loads((dirty / "summary.json").read_text())["counts"], {"refused:source-not-clean": 1},
                         "S4.rehearse")
        (self.s.root / "stray").unlink()
        none = self.base / "none"
        with mock.patch.object(rb(), "latest_review", lambda source: None):
            rb().rehearse(none, source=self.s.repo, runner=runner)
        self.assertEqual(json.loads((none / "summary.json").read_text())["counts"], {"refused:no-pre-freeze-review": 1},
                         "S4.rehearse")
        self.assertEqual(calls, [], "S4.rehearse: a step ran after a refusal")
        self.refuses("S4.rehearse", "RunRefused", "absolute path", rb().rehearse, "relative/out", source=self.s.repo)

    def test_every_step_stays_under_out(self):
        import freeze_rehearsal as fr
        calls = []

        def runner(argv, cwd):
            calls.append((list(argv), cwd))
            return 0, ""
        out = self.base / "out"
        takes_calls = []

        def takes_runner(argv, cwd, timeout):
            takes_calls.append((list(argv), cwd, timeout))
            calls.append((list(argv), cwd))
            return 0, ""
        with mock.patch.object(fr, "synthetic_holdout_source", lambda draft, dest: calls.append((["holdout", str(dest)],
                                                                                                None))):
            rc = rb().rehearse(out, source=self.s.repo, review="r" * 40, runner=runner, takes_runner=takes_runner,
                               budget_for=lambda clone: 4321, clock=lambda: NOW)
        self.assertEqual(rc, 0, "S4.rehearse")
        clone = str(out / "clone")
        self.assertEqual(calls[0][0], ["git", "clone", "-q", "--no-local", str(self.s.repo.resolve()), clone],
                         "S4.rehearse")
        self.assertEqual(calls[1][0], ["git", "-C", clone, "remote", "remove", "origin"], "S4.rehearse: the remote kept")
        self.assertEqual(calls[2][0], ["holdout", str(out / fr.HOLDOUT_FILE)], "S4.rehearse: the synthetic digests")
        freeze_argv = calls[3][0]
        self.assertTrue(freeze_argv[4].startswith(clone) and freeze_argv[4].endswith("/freeze.py"), "S4.rehearse")
        self.assertEqual(freeze_argv[5:], ["--review-commit", "r" * 40, "--rehearsal", "--write", "--holdout-digests",
                                           str(out / fr.HOLDOUT_FILE)], "S4.rehearse: not freeze_rehearsal's command")
        last = calls[-1][0]
        self.assertEqual(last[4:], [clone + "/evals/gap-study-4/run_builders.py", "rehearse-takes", "--out", str(out)],
                         "S4.rehearse: the takes do not run in the clone")
        self.assertEqual([(c[1], c[2]) for c in takes_calls], [(clone, 4321)],
                         "S4.rehearse: the take step is not bounded by the rehearsal rows' budget (MINOR-4)")
        reads = [argv[4:] for argv, cwd in calls[-3:-1]]
        self.assertEqual(reads, [[clone + "/evals/gap-study-4/run_builders.py", "spend-read", "--vendor", v, "--usd",
                                  "0", "--at", "2026-10-24T12:00:00Z", "--source",
                                  "rehearsal clone, not a vendor read", "--by", "rehearsal"]
                                 for v in ("google", "openai")],
                         "S4.rehearse: the clone's two zero spend reads (MAJOR-1)")
        self.assertEqual([cwd for argv, cwd in calls[-3:-1]], [clone, clone],
                         "S4.rehearse: a spend read outside the clone")
        for n, (argv, cwd) in enumerate(calls):
            for part in argv[(5 if n == 0 else 0):] + ([cwd] if cwd else []):     # the clone's source, read only
                if isinstance(part, str) and part.startswith("/") and part != sys.executable:
                    self.assertTrue(part.startswith(str(out)), f"S4.rehearse: a step names {part} outside --out")
        self.assertEqual(self.s.git("status", "--porcelain"), "", "S4.rehearse: the source changed")

    def test_a_failed_step_is_a_closed_reason(self):
        out = self.base / "out"
        rc = rb().rehearse(out, source=self.s.repo, review="r" * 40, runner=lambda argv, cwd: (1, "words"))
        text = (out / "summary.json").read_text()
        self.assertEqual((rc, json.loads(text)["counts"]), (1, {"refused:freeze-failed": 1}), "S4.rehearse")
        self.assertNotIn("words", text, "S4.rehearse")
        import freeze_rehearsal as fr
        for n, (budget, takes, want) in enumerate((
                (lambda c: 60, None, "freeze-failed"),                       # a spend read refused
                (lambda c: (_ for _ in ()).throw(rb().RehearsalRefused("rows-missing", "words")), None, "rows-missing"),
                (lambda c: (_ for _ in ()).throw(OSError("words")), None, "builders-missing"),
                (lambda c: 60, "timeout", "takes-timeout"))):
            out = self.base / f"out-{n}"

            def runner(argv, cwd, n=n):
                return (1, "words") if n == 0 and "spend-read" in argv else (0, "")

            def takes_runner(argv, cwd, timeout):
                raise subprocess.TimeoutExpired(argv, timeout, output="words")
            with mock.patch.object(fr, "synthetic_holdout_source", lambda draft, dest: None):
                rc = rb().rehearse(out, source=self.s.repo, review="r" * 40, runner=runner, budget_for=budget,
                                   takes_runner=takes_runner if takes else (lambda a, c, t: (0, "")))
            text = (out / "summary.json").read_text() if (out / "summary.json").exists() else "{}"
            self.assertEqual((rc, json.loads(text).get("counts")), (1, {f"refused:{want}": 1}), f"S4.rehearse: {want}")
            self.assertNotIn("words", text, "S4.rehearse")

    def test_an_error_escaping_rehearse_is_freeze_failed(self):
        """Closure 2 NIT-1: an unexpected error inside `rehearse` writes the closed summary refused:freeze-failed into
        an absolute, existing --out outside the source repository, never the error's text; never into the source."""
        import drive
        out = self.base / "out"
        out.mkdir()
        with mock.patch.object(drive, "REPO", self.s.repo), \
                mock.patch.object(rb(), "rehearse", side_effect=OSError("words")):
            rc, _, err = self.must("S4.rehearse", call, rb().main, ["rehearse", "--out", str(out)])
            path = out / "summary.json"
            text = path.read_text() if path.exists() else "{}"
            self.assertEqual((rc, json.loads(text)), (1, {"takes": [], "overlap": False, "pass": False,
                                                          "counts": {"refused:freeze-failed": 1}}),
                             "S4.rehearse: an error escaping rehearse left no closed summary")
            self.assertNotIn("words", text + err, "S4.rehearse: the error's words were written")
            inside = self.s.repo / "out"
            inside.mkdir()
            rc, _, _ = self.must("S4.rehearse", call, rb().main, ["rehearse", "--out", str(inside)])
            self.assertEqual((rc, (inside / "summary.json").exists()), (1, False),
                             "S4.rehearse: a summary written into the source repository")
            inside.rmdir()

    def test_the_take_budget(self):
        """MINOR-4: each rehearsal row's walk budget (a step with a recovery counts twice) plus one quiescence cap."""
        scripts = {"s1": [{"n": 1}, {"n": 2, "recovery": "r"}], "s2": [{"n": 1}]}
        got = rb().takes_budget_s([arow("s1", "A"), arow("s2", "O")], (900, 180, 3), lambda r: scripts[r["slot"]])
        self.assertEqual(got, 3 * 1080 + 1 * 1080 + 180, "S4.rehearse: the take step's bound")

    def test_the_clones_budget_and_the_take_step(self):
        """MINOR-4: rehearsal_budget_s reads the clone's frozen take_order (the first A and O rows), their own scripts
        from the clone's study folder and the checker's budgets; a Missing budget is builders-missing. run_takes_step
        returns the child's code and lets a timeout through."""
        import variants
        import walk_builders as wb
        folder = self.base / "clone" / "evals" / "gap-study-4"
        folder.mkdir(parents=True)
        order = [dict(arow("s1", "O"), task="t", half="h", wording="w1"),
                 dict(arow("s2", "A"), task="t", half="h", wording="w2"), dict(arow("s3", "A"), task="t", half="h",
                                                                              wording="w3")]
        (folder / "prereg.json").write_text(json.dumps({"take_order": order}))
        seen = []

        def steps(task, half, wording, pressure=None, root=None):
            seen.append((wording, Path(root)))
            return [{"n": 1}] * (2 if wording == "w1" else 1)
        with mock.patch.object(variants, "operator_steps", steps), \
                mock.patch.object(wb, "checker_budgets", lambda: (900, 180, 3)):
            got = self.must("S4.rehearse", rb().rehearsal_budget_s, self.base / "clone")
        self.assertEqual((got, seen), (2 * 1080 + 1080 + 180, [("w1", folder), ("w2", folder)]),
                         "S4.rehearse: the clone's budget")
        with mock.patch.object(wb, "checker_budgets", lambda: wb.Missing("pending")):
            with self.assertRaises(rb().RehearsalRefused, msg="S4.rehearse") as e:
                rb().rehearsal_budget_s(self.base / "clone")
        self.assertEqual(e.exception.reason, "builders-missing", "S4.rehearse")
        code, out = rb().run_takes_step([sys.executable, "-c", "print('ran'); raise SystemExit(3)"], self.base, 60)
        self.assertEqual((code, out.strip()), (3, "ran"), "S4.rehearse: the take step's code")
        with self.assertRaises(subprocess.TimeoutExpired, msg="S4.rehearse: the take step's bound"):
            rb().run_takes_step([sys.executable, "-c", "import time; time.sleep(30)"], self.base, 0.5)

    def test_the_clone_records_two_zero_reads_and_the_money_gate_admits_the_wave(self):
        """MAJOR-1 (review of 122b559e): rehearse in a real clone of a scratch repository, with the clone's real writer
        (run_builders.main spend-read over the clone) and rehearse_takes over a real SpendLedger on that clone; the
        stand-in loop puts the one A and one O row through batch's real money gate first, as Batch does. Without the
        clone's two zero reads the gate refuses the wave and nothing launches."""
        import prereg
        out = self.base / "out"
        clone = out / "clone"
        study_dir = clone / "evals" / "gap-study-4"
        pre = design(per=1)
        first = [next(r for r in pre["take_order"] if r["arm"] == arm)["slot"] for arm in ("A", "O")]
        pre["take_order"] = [r for r in pre["take_order"] if r["slot"] in first]      # one A and one O row
        identity = {f"GIT_{role}_{part}": v for role in ("AUTHOR", "COMMITTER")
                    for part, v in (("NAME", "rehearsal"), ("EMAIL", "rehearsal@example.invalid"))}
        inner = HookSub("A", [])
        gate = {}

        class GatedLoop:
            stopped = None

            def __init__(self, driver, repo, window, ledger=None, **kw):
                self.driver, self.ledger = driver, ledger

            def run(self, rows):
                problems = batch.money_gate_problems(rows, self.ledger, clock=lambda: NOW)
                gate["problems"] = problems
                if problems:
                    self.stopped = {"slot": rows[0]["slot"], "attempt": 1, "state": "blocked",
                                    "reason": "the money gate refuses the block (nothing registered or launched): "
                                              + "; ".join(problems)}
                    return []
                cids = {r["slot"]: self.driver.launch(r) for r in rows}
                inner.hook = lambda: self.driver.drive(rows[1], cids[rows[1]["slot"]])
                self.driver.drive(rows[0], cids[rows[0]["slot"]])
                return [outcome(r["slot"]) for r in rows]

        def takes(argv, cwd, timeout=None):
            ledger = rb().SpendLedger(root=study_dir, repo=clone, pre=pre, history=lambda: [], arms=("A", "O"),
                                      clock=lambda: NOW)
            built = {"driver": inner, "repo": "R", "window": "W", "ledger": ledger, "table": {},
                     "rows": copy.deepcopy(pre["take_order"]), "arms": ("A", "O"),
                     "road": rb().TakeRoad(prepare=lambda r: {}, remove=lambda t: None)}
            ticks = iter(range(100)).__next__
            with mock.patch.object(prereg, "require_frozen", lambda what: pre), \
                    mock.patch.object(rb(), "build_run", lambda **kw: built), \
                    mock.patch.object(rb(), "lease_problem", lambda b, rows: None), \
                    mock.patch.object(rb(), "outcome_commits",
                                      lambda root, repo: {(r["slot"], 1): "c" * 40 for r in pre["take_order"]}):
                return rb().rehearse_takes(out, builders={"x": 1}, root=study_dir, repo=clone,
                                           clock=lambda: float(ticks()), batch_class=GatedLoop), ""

        def runner(argv, cwd):
            if argv[0] == "git":
                got = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
                return got.returncode, got.stdout + got.stderr
            if argv[4].endswith("/freeze.py"):          # freeze.py's three outputs, synthetic
                for rel in ("prereg.json", "COPIED.json", "COPIED.d/freeze.json"):
                    (study_dir / rel).parent.mkdir(parents=True, exist_ok=True)
                    (study_dir / rel).write_text(json.dumps({"synthetic": rel}) + "\n")
                return 0, ""
            if argv[5] == "spend-read":                 # the clone's writer, over the clone
                with mock.patch.object(rb(), "STUDY_ROOT", [study_dir]), mock.patch.dict(os.environ, identity):
                    rc, _, err = call(rb().main, argv[5:])
                return rc, err
            if argv[5] == "rehearse-takes":
                return takes(argv, cwd)
            raise AssertionError(f"S4.rehearse: an unexpected step {argv[:6]}")
        import freeze_rehearsal as fr
        with mock.patch.object(fr, "synthetic_holdout_source", lambda draft, dest: None), \
                mock.patch.object(rb(), "run_takes_step", takes, create=True), \
                mock.patch.object(rb(), "rehearsal_budget_s", lambda clone_: 60, create=True), \
                mock.patch.object(rb(), "utc_now", lambda: NOW - datetime.timedelta(days=4)):   # before any clock
            rc = self.must("S4.rehearse", rb().rehearse, out, source=self.s.repo, review="r" * 40, runner=runner)
        summary = json.loads((out / "summary.json").read_text())
        self.assertEqual(gate.get("problems"), [], f"S4.rehearse: the money gate refused the rehearsal wave: {gate}")
        self.assertEqual((rc, summary["pass"], [(t["arm"], t["state"]) for t in summary["takes"]]),
                         (0, True, [("A", "committed"), ("O", "committed")]), f"S4.rehearse: {summary}")
        doc = rb().read_ledger_doc(study_dir, clone)
        self.assertEqual([(r["vendor"], r["usd"], r["source"], r["by"]) for r in doc["spend"]],
                         [("google", "0", "rehearsal clone, not a vendor read", "rehearsal"),
                          ("openai", "0", "rehearsal clone, not a vendor read", "rehearsal")], "S4.rehearse: the reads")
        self.assertFalse((self.s.root / "run-ledger.json").exists(), "S4.rehearse: the source repository was written")
        self.assertEqual(self.s.git("status", "--porcelain"), "", "S4.rehearse: the source changed")


class S4Commits(Case):
    def setUp(self):
        self.s = Scratch()
        self.env = mock.patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.s.close()

    def test_outcome_commits(self):
        self.s.commit_file("outcomes.json", json.dumps([outcome("s1")]).encode(), "one")
        first = self.s.git("rev-parse", "HEAD").strip()
        self.s.commit_file("outcomes.json", json.dumps([outcome("s1"), outcome("s2")]).encode(), "two")
        second = self.s.git("rev-parse", "HEAD").strip()
        self.assertEqual(rb().outcome_commits(self.s.root, self.s.repo), {("s1", 1): first, ("s2", 1): second},
                         "S4.commits")


# ------------------------------------------------------------------------------------------------- G1
class G1Generated(Case):
    def test_every_test_class_runs_under_a_generated_mutant(self):
        classes = {n for n, v in globals().items() if isinstance(v, type) and issubclass(v, unittest.TestCase)
                   and any(a.startswith("test") for a in vars(v))}
        self.assertEqual(sorted(classes - set(GENERATED_ORDER)), [], "G1.order: classes the sweep never runs")

    def test_the_equivalent_list_matches_the_generated_mutants(self):
        ids = set(self.must("G1.generated", by_id))
        self.assertGreater(len(ids), 0, "G1.generated: the generator produced nothing")
        self.assertEqual(sorted(set(EQUIVALENT) - ids), [], "G1.generated: EQUIVALENT entries that name no mutant")
        bare = sorted(k for k, why in EQUIVALENT.items() if not isinstance(why, str) or len(why.strip()) < 12)
        self.assertEqual(bare, [], "G1.generated: EQUIVALENT entries without a reason")

    def test_every_witness_anchor_occurs_once(self):
        for name, (clause, target, old, new) in mutants().items():
            text = (HERE / f"{target}.py").read_text()
            self.assertEqual(text.count(old), 1, f"G1.anchor: witness {name}'s anchor")


GENERATED_ORDER = ("S1Plan", "S1Order", "S1Ledger", "S1History", "S1Window", "S2Login", "S2Road", "S2Driver",
                   "S2Lease", "S2Prepare", "S2Harness", "S3Blob", "S3Main", "S3RunMain", "S3Hook", "S4Rows",
                   "S4Summary", "S4Timed", "S4Lease", "S4Takes", "G1Generated", "S1Git", "S2Identity", "S2Tree",
                   "S3Writers", "S4Commits", "S4Rehearse")


def _outcome_line(got):
    record = re.findall(r"^test_run_builders outcomes: (\{.*\})$", got.stdout, re.M)
    return json.loads(record[-1]) if record else None


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    for name in chosen:
        method, clause = WITNESSES[name]
        got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--mutant", name,
                              method], capture_output=True, text=True, timeout=110)
        outcome_ = _outcome_line(got)
        blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", got.stderr,
                            re.M | re.S)
        attributed = any(f"{cls}.{test}" == method and "AssertionError" in body and
                         re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
                         for test, cls, body in blocks)
        clean = bool(outcome_) and set(outcome_["failures"]) == {method} and outcome_["errors"] == [] \
            and outcome_["skipped"] == []
        passed = attributed and clean and got.returncode != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(got.stdout[-3000:] + got.stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_run_builders witnesses: {red}/{len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


def run_generated(shard=None, sample=None, timeout=600, only=None) -> int:
    mutants_all, dropped = generate()
    chosen = list(enumerate(mutants_all))
    if shard:
        i, n = shard
        chosen = [(k, m) for k, m in chosen if k % n == i - 1]
    if sample:
        chosen = chosen[::sample]
    if only is not None:
        chosen = [(k, m) for k, m in chosen if m.id in only]
    killed, survived, equivalent, listed_killed, inconclusive = [], [], [], [], []

    def one(mid, fast):
        argv = [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), "--gen-mutant", mid]
        got = subprocess.run(argv + (["--failfast"] if fast else []), capture_output=True, text=True, timeout=timeout)
        return got, _outcome_line(got)

    for _, m in chosen:
        try:
            got, outcome_ = one(m.id, True)
            if outcome_ is not None and not outcome_["failures"] and outcome_["errors"]:
                got, outcome_ = one(m.id, False)
        except subprocess.TimeoutExpired:
            inconclusive.append(m.id)
            print(f"generated {m.id}: TIMEOUT (inconclusive)", flush=True)
            continue
        if outcome_ is None:
            inconclusive.append(m.id)
            print(f"generated {m.id}: NO OUTCOME (rc {got.returncode})\n{got.stderr[-1500:]}", flush=True)
            continue
        state = "KILLED" if outcome_["failures"] else "SURVIVED"
        if outcome_["failures"]:
            killed.append(m.id)
            if m.id in EQUIVALENT:
                listed_killed.append(m.id)
        elif m.id in EQUIVALENT:
            equivalent.append(m.id)
            state = "EQUIVALENT"
        else:
            survived.append(m.id)
        print(f"generated {m.id}: {state} by {outcome_['failures'][:1]} (errors {len(outcome_['errors'])}) "
              f"[{m.kind} at line {m.line}: {m.original[:60]!r} -> {m.replacement[:40]!r}]", flush=True)
    print(f"test_run_builders generated mutants: {len(mutants_all)} generated ({dropped} dropped, not compiling), "
          f"{len(chosen)} run, {len(killed)} killed, {len(equivalent)} equivalent (listed), {len(survived)} "
          f"survived unlisted, {len(listed_killed)} listed but killed, {len(inconclusive)} inconclusive", flush=True)
    for name, ids in (("SURVIVED (unlisted)", survived), ("LISTED BUT KILLED", listed_killed),
                      ("INCONCLUSIVE", inconclusive)):
        for x in ids:
            print(f"  {name}: {x}", flush=True)
    # The last line, one line whatever the count, so a log tail carries this shard's whole red list.
    print(f"test_run_builders shard reds: survived unlisted [{','.join(survived)}]; listed but killed "
          f"[{','.join(listed_killed)}]; inconclusive [{','.join(inconclusive)}]", flush=True)
    return 0 if not survived and not listed_killed and not inconclusive else 1


if __name__ == "__main__":
    if "--generated-mutants" in sys.argv:
        shard = sample = None
        if "--shard" in sys.argv:
            a, b = sys.argv[sys.argv.index("--shard") + 1].split("/")
            shard = (int(a), int(b))
            if not 1 <= shard[0] <= shard[1]:
                raise SystemExit("--shard i/n with 1 <= i <= n")
        if "--sample" in sys.argv:
            sample = int(sys.argv[sys.argv.index("--sample") + 1])
        per = int(sys.argv[sys.argv.index("--timeout") + 1]) if "--timeout" in sys.argv else 600
        only = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
        raise SystemExit(run_generated(shard, sample, per, only))
    failfast = "--failfast" in sys.argv
    if failfast:
        sys.argv.remove("--failfast")
    if "--gen-mutant" in sys.argv:
        index = sys.argv.index("--gen-mutant")
        GENERATED = sys.argv[index + 1]
        del sys.argv[index:index + 2]
        if len(sys.argv) == 1:
            sys.argv += list(GENERATED_ORDER)
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    result = unittest.main(verbosity=2, exit=False, failfast=failfast).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_run_builders: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_run_builders outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                      "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
