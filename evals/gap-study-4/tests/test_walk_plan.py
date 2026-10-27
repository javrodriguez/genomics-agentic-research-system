#!/usr/bin/env python3
"""Lane w11c-walk-plan: the CP6 walk list and its coverage report (rehearsals/README.md question 3).

walk_plan.plan_walks(design) lists the walks CP6 requires (plan 874-876; arms O and G per ruling Q-2, D8:448), each
spec carrying exactly the register entry's fields plus the agent, derived from the design files and checked by
walk_register.entry_problems. These tests re-derive every figure from the design with code of their own, never
from a typed number, and bind:

  P1.counts         the figures per arm and model equal an independent derivation from prereg-draft.json and
                    tasks/<task>.json (every wording of every task and half on the arm A haiku model, each task
                    and half once on every other planned model, nothing for the optional arm C)
  P2.dropped        a dropped task or a dropped wording in a synthetic copy of the design changes the figures, to
                    what the independent derivation says; witnesses count-hard-coded, wordings-typed
  P3.halves         every planned model gets every task and every half; every spec has exactly the register's
                    fields plus the agent, passes entry_problems, names the harness the design's rows give, is
                    never counted and carries no walk id; the optional arm is not required; witnesses half-missing,
                    optional-required, agent-unread
  P4.off-design     coverage(): an entry the design refuses, one the plan does not require, a non-object entry and
                    an entry whose cell is no row of the design are reported (by walk id, or "entry <i>") and never
                    counted; a retry covers its spec once; on the command line an arm C walk is reported outside the
                    plan; witnesses off-design-counted, outside-counted, rows-unchecked-coverage, entry-label-fallback
  P5.exact-wording  on the every-wording model a walk covers only its own wording; on every other model any wording
                    of the task covers the task and half; two specs on one key refuse; witnesses
                    exact-wording-unchecked, spec-key-shared
  P6.require        --coverage exits 0 while walks are missing and names each missing walk, and each covered walk
                    with its walk id; the empty-register line prints only for an empty register; --require-complete
                    exits 1 on any gap and 0 only on a register that covers every spec; a missing or symlinked
                    register exits 2; witnesses require-complete-gap, register-link-admitted, stand-ins-missing
  P7.register-only  --coverage opens, stats and lists nothing under rehearsals/ but the register: no walk folder is
                    listed, read, or looked up; witnesses folder-listed, folder-statted
  P8.spec-checked   a spec the register's design refuses, or one whose cell is not a row of the design, refuses the
                    whole plan, and so does a planned model whose rows name two harnesses; witnesses spec-unchecked,
                    cell-unchecked, harness-mixed-admitted
  P9.prose          the printed plan and coverage report are clean under lint_language's and lint_pooling's
                    patterns, and no printed line states a figure across arms or models; witness figure-across-arms
  P10.every-rule    the every-wording model is the one haiku model of arm A: none, or two, on arm A refuse by
                    PlanRefused (never another error), and a haiku-named model on another arm is neither taken nor
                    counted as a second; witnesses every-rule-first-match, every-rule-dropped, every-rule-any-arm
  P11.design        synthetic designs that drop a half, add a half, and add a model to another arm move the figures
                    to what the independent derivation says (W11C-R1-5); witness halves-typed
  P12.register      (W11C-R1-1, R1-4) the coverage report refuses, exit 2, every register walk_register.check
                    refuses, with the check's own words: one walk id covering every spec, a walk id registered twice,
                    ids that differ only by case, a wrong schema, an extra top-level key, walks not a list, a
                    top-level list, a non-object entry, a counted entry, an off-design entry and a duplicate JSON
                    key; witness register-check-skipped
  P13.per-model     (W11C-R1-2) each model's missing figure counts that model's gaps only, on a register missing a
                    different number of walks on each model, and on a synthetic design that plans one model id on
                    two arms; witnesses per-model-arm-dropped, per-model-model-dropped
  P14.cli           (W11C-R1-3) run as a script, walk_plan exits with main's code; --list with --require-complete is
                    refused; the "ok" line prints only under --require-complete with nothing missing; without --base
                    the register is walk_register.REHEARSALS'; witnesses script-entry-dropped, list-require-admitted,
                    ok-unconditional, default-base-ignored
  P15.sweep         the generated sweep is armed (mutants generated, ids unique) and its EQUIVALENT registry is current:
                    an entry on a changed line, with no such mutant, or without a reason is reported
  P16.scratch-only  (athena sweep, L206.drop2) a register naming a walk id that is a path (a parent step, "..", an
                    absolute path) is refused, exit 2, and the run writes nothing outside its own scratch folder,
                    which is gone after; witness stand-in-any-id
  P17.wrong-type    stand_in_ids keeps only walk ids: an entry that is no object, a walk that is no string (None, an
                    int, a bool, a list, an object, missing) or no walk id is skipped, never a crash, and bytes that
                    are no register give []; coverage() labels an entry whose walk is no string "entry <i>";
                    witnesses stand-in-type-unchecked, stand-in-entry-unchecked, stand-in-walks-unchecked
  P19.run-arms      (lane pf1-l1-freeze-gates, pre-freeze review 1 MAJOR 4 part 3) deferred_arms reads the draft's
                    deferred arms only; run_arm_gaps and --require-run-arms require every arm the freeze runs and
                    print each deferred arm and model as recorded; coverage_report is the --coverage reading; bound
                    by the generated sweep, no named witness
  P20.strict        (lane pf1-walk-cover-strict, OD131 "walk-cover strict", OD132 "walk-cover-o strict")
                    strict_walks names arm A's and arm O's walks; on --coverage and in coverage_report such a walk
                    whose reading carries a reason HEAD's routing routes to harness-error covers nothing and is
                    reported with why, an arm G walk with the same reason covers as before, and a clean strict walk
                    covers; witnesses strict-unread-cli, strict-unread-report, strict-every-arm, strict-arm-o-dropped,
                    strict-arm-g-added (pending_walk's own rule: tests/test_walk_cover_strict.py)
  P21.witness-rule  (the review of ff58e02f, NIT 3) --witnesses reads a bound test that failed by P0.module (a mutant
                    whose anchor does not occur once, or that does not load) as FAIL, never red

Red first: before walk_plan.py exists every test fails by its own assertion (P0.module), with no error. The helpers
that call walk_plan (plan, cover, cli) turn any exception other than the documented refusal into a failure carrying
the clause, so a refusal guard that is removed fails by an assertion, never only by an error (W11C-R1-4).

--mutant NAME compiles one altered walk_plan in memory before the bound test runs; --witnesses runs every
registered mutant in its own process, only its bound test, and requires that test to fail by an AssertionError
carrying its clause token, with no error (rule B).

--generated-mutants [--shard i/n] is the generated mutation sweep over walk_plan.py: a stdlib AST mutator makes every
mutant of a closed operator set (below), each runs the whole suite in its own process, and each must be killed by an
assertion (failures only, no error) or be listed in EQUIVALENT with its line and a reason; a listed mutant that is
killed, or an entry whose mutant is no longer generated on that line, fails the sweep (a stale entry). The
unmutated module, re-emitted the same way, must pass first, so the sweep is armed. Each mutant's suite runs with
--failfast: the first failing test decides, and it must fail by an assertion. --only ID[,ID] runs named mutants and
prints the run of any not killed. String constants and f-strings are
never mutated (the one message rule: every printed line the gate depends on is bound by an assertion above); the
operators are a comparison negated, an if or conditional test set to True and to False, and/or swapped, each
operand of an and/or dropped, a `not` removed, each branch of a conditional expression taken, a slice's upper bound
removed, an integer constant moved by one, each comprehension filter dropped, and an assignment, expression
statement, raise, return or continue replaced by pass; inside every function and the `__main__` block only.

Fakes and synthetic copies of the design only: no walk, model, network, container, credential, salt or holdout.
setUpModule arms a process guard (every subprocess start is refused while the tests run) and tearDownModule
restores sys.path and the guard. No folder outside this study and the test's own temporary folders is read.
"""
from __future__ import annotations

import ast
import builtins
import contextlib
import copy
import io
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

SELECTED = None
MUTANT_SOURCE = None
MODS: dict = {}
SAVED: dict = {}
LANE = "w11c-walk-plan"
FIELDS = ("walk", "task", "half", "wording", "arm", "model", "reason", "counted")


def mutants():
    """name -> (clause, old text, new text) in walk_plan.py. Each weakens one guard; old must occur exactly once."""
    return {
        "count-hard-coded": ("P2.dropped",
                             "    out: dict = {}\n    for spec in specs:\n",
                             "    return {\"A\": {\"claude-opus-5-5\": 18, \"claude-sonnet-5-5\": 18, "
                             "\"claude-haiku-4-5-20251001\": 90}, \"O\": {\"gpt-6.1-sol\": 18, \"gpt-6-luna\": 18}, "
                             "\"G\": {\"gemini-3.8-flash\": 18, \"gemini-3.5-flash-lite\": 18}}\n"
                             "    out: dict = {}\n    for spec in specs:\n"),
        "wordings-typed": ("P2.dropped",
                           "wordings = list(task[\"wordings\"]) if every else list(task[\"wordings\"])[:1]",
                           "wordings = [\"w1\", \"w2\", \"w3\", \"w4\", \"w5\"] if every else [\"w1\"]"),
        "half-missing": ("P3.halves", "            for half in task[\"halves\"]:",
                         "            for half in task[\"halves\"][:1]:"),
        "optional-required": ("P3.halves",
                              "    planned = {arm: list(models) for arm, models in draft[\"models\"].items()}",
                              "    planned = {arm: list(models) for arm, models in register[\"arms\"].items()}"),
        "agent-unread": ("P3.halves", "                        \"agent\": agents[(arm, model)],",
                         "                        \"agent\": \"claude-code\","),
        "off-design-counted": ("P4.off-design", "        if bad:\n", "        if False:\n"),
        "outside-counted": ("P4.off-design", "        if key not in by_key:\n", "        if False:\n"),
        "rows-unchecked-coverage": ("P4.off-design",
                                    "        if cell not in design[\"cells\"]:\n            outside.append(",
                                    "        if False:\n            outside.append("),
        "entry-label-fallback": ("P4.off-design",
                                 "        label = entry.get(\"walk\") if isinstance(entry, dict) and "
                                 "isinstance(entry.get(\"walk\"), str) \\\n            else f\"entry {i}\"",
                                 "        label = entry.get(\"walk\")"),
        "exact-wording-unchecked": ("P5.exact-wording",
                                    "    exact = (entry[\"arm\"], entry[\"model\"]) == design[\"every_wording\"]",
                                    "    exact = False"),
        "spec-key-shared": ("P5.exact-wording", "        if key in by_key:\n            raise PlanRefused(",
                            "        if False:\n            raise PlanRefused("),
        "require-complete-gap": ("P6.require", "    if args.require_complete and missing:",
                                 "    if False:"),
        "register-link-admitted": ("P6.require", "    if path.is_symlink() or not path.is_file():",
                                   "    if not path.is_file():"),
        "stand-ins-missing": ("P6.require", "        for walk in stand_in_ids(raw):", "        for walk in []:"),
        "folder-listed": ("P7.register-only", "        entries = read_register(base, design)\n",
                          "        entries = read_register(base, design)\n"
                          "        _ = sorted(p.name for p in base.iterdir())\n"),
        "folder-statted": ("P7.register-only", "        entries = read_register(base, design)\n",
                           "        entries = read_register(base, design)\n"
                           "        _ = [Path(base, e[\"walk\"]).exists() for e in entries]\n"),
        "spec-unchecked": ("P8.spec-checked", "    if problems:\n        raise PlanRefused(",
                           "    if False:\n        raise PlanRefused("),
        "cell-unchecked": ("P8.spec-checked",
                           "        if cell not in design[\"cells\"]:\n            problems.append(",
                           "        if False:\n            problems.append("),
        "harness-mixed-admitted": ("P8.spec-checked", "            if len(got) != 1:\n", "            if not got:\n"),
        "figure-across-arms": ("P9.prose", "    return lines\n\n\ndef coverage_lines(",
                               "    lines.append(f\"{len(specs)} required walks on every arm and model\")\n"
                               "    return lines\n\n\ndef coverage_lines("),
        "every-rule-first-match": ("P10.every-rule", "    if len(found) != 1:\n", "    if not found:\n"),
        "every-rule-dropped": ("P10.every-rule", "    if len(found) != 1:\n        raise PlanRefused(",
                               "    if False:\n        raise PlanRefused("),
        "every-rule-any-arm": ("P10.every-rule",
                               "    found = [m for m in models_by_arm.get(arm, []) if family in m.casefold()]",
                               "    found = [m for ms in models_by_arm.values() for m in ms if family in "
                               "m.casefold()]"),
        "halves-typed": ("P11.design", "                for half in task[\"halves\"]:",
                         "                for half in (\"trap\", \"normal\"):"),
        "stand-in-crash": ("P12.register", "            except OSError:\n                pass",
                           "            except FileNotFoundError:\n                pass"),
        "register-check-skipped": ("P12.register", "        if problems:\n            raise RegisterUnreadable(",
                                   "        if False:\n            raise RegisterUnreadable("),
        # these two and default-base-ignored re-anchored by lane pf1-walk-cover-strict: lane pf1-l1-freeze-gates's
        # deferred_lines and coverage_report repeat the bare lines, so each anchor occurred twice and its witness went
        # red only by P0.module; each is now anchored on the site it was written for (coverage_lines, main)
        "per-model-arm-dropped": ("P13.per-model",
                                  "if (s[\"arm\"], s[\"model\"]) == (arm, model))\n            lines.append(f\"{model_line(",
                                  "if s[\"model\"] == model)\n            lines.append(f\"{model_line("),
        "per-model-model-dropped": ("P13.per-model",
                                    "if (s[\"arm\"], s[\"model\"]) == (arm, model))\n            lines.append(f\"{model_line(",
                                    "if s[\"arm\"] == arm)\n            lines.append(f\"{model_line("),
        "script-entry-dropped": ("P14.cli", "    raise SystemExit(main())", "    main()"),
        "list-require-admitted": ("P14.cli", "    if args.require_complete and not args.coverage:",
                                  "    if False:"),
        "ok-unconditional": ("P14.cli", "    if args.require_complete:\n        print(\"ok",
                             "    if True:\n        print(\"ok"),
        "default-base-ignored": ("P14.cli", "if args.base else walk_register.REHEARSALS",
                                 "if args.base else HERE / \"rehearsals\""),
        "stand-in-any-id": ("P16.scratch-only", "\n            and walk_register.WALK_ID.fullmatch(e[\"walk\"])]",
                            "]"),
        "stand-in-type-unchecked": ("P17.wrong-type",
                                    "isinstance(e, dict) and isinstance(e.get(\"walk\"), str)\n            and ",
                                    "isinstance(e, dict)\n            and "),
        "stand-in-entry-unchecked": ("P17.wrong-type",
                                     "if isinstance(e, dict) and isinstance(e.get(\"walk\"), str)\n",
                                     "if isinstance(e.get(\"walk\"), str)\n"),
        "stand-in-walks-unchecked": ("P17.wrong-type", "    if not isinstance(walks, list):\n        return []\n",
                                     ""),
        # batch-8 review finding 1 (glitch-06, 14 Oct 2026): a pending walk is never coverage
        "pending-counted": ("P18.pending", "        if entry[\"walk\"] in uncounted:            # batch-8 rulings",
                            "        if False:            # batch-8 rulings"),
        # re-anchored by lane pf1-walk-cover-strict: the call line also stands in coverage_report, so the bare line
        # occurred twice and the witness went red only by P0.module (the module refused its anchor); now main's site
        "pending-unread": ("P18.pending",
                           "    got = coverage(entries, specs, design,\n                   pending_walk.uncounted_walks("
                           "base, [e[\"walk\"] for e in entries], strict_walks(entries)))\n    print(",
                           "    got = coverage(entries, specs, design)\n    print("),
        # OD131 (lane pf1-walk-cover-strict): arm A's walks are judged by the strict rule, on both roads, and only they
        "strict-unread-cli": ("P20.strict", "strict_walks(entries)))\n    print(", "[]))\n    print("),
        "strict-unread-report": ("P20.strict", "strict_walks(entries)))\n    return {", "[]))\n    return {"),
        # OD132 (26 Oct 2026, "walk-cover-o strict"): arm O joins; arm G, deferred, stays as coded
        "strict-arm-o-dropped": ("P20.strict", "WALK_COVER_STRICT = {\"arms\": (\"A\", \"O\"),",
                                 "WALK_COVER_STRICT = {\"arms\": (\"A\",),"),
        "strict-arm-g-added": ("P20.strict", "WALK_COVER_STRICT = {\"arms\": (\"A\", \"O\"),",
                               "WALK_COVER_STRICT = {\"arms\": (\"A\", \"O\", \"G\"),"),
        "strict-every-arm": ("P20.strict","    return [e[\"walk\"] for e in entries if e[\"arm\"] in "
                             "WALK_COVER_STRICT[\"arms\"]]\n", "    return [e[\"walk\"] for e in entries]\n"),
        "pending-unreported": ("P18.pending", "    for label, why in got[\"uncounted\"]:\n", "    for label, why in []:\n"),
    }


class Refused(Exception):
    pass


def refuse_process(*args, **kwargs):
    raise Refused(f"test_walk_plan: a process start is refused while the tests run: {args[:1]!r}")


def load_walk_plan(text: str, label: str):
    path = HERE / "walk_plan.py"
    mod = types.ModuleType("walk_plan")
    mod.__file__ = str(path)
    sys.modules["walk_plan"] = mod
    exec(compile(text, str(path) + f" ({label})", "exec"), mod.__dict__)
    return mod


def setUpModule():
    SAVED["path"] = list(sys.path)
    for p in (HERE, HERE / "tests"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    SAVED["popen"] = subprocess.Popen
    subprocess.Popen = refuse_process          # the process guard: armed here, never at import
    for name in ("walk_register", "lint_language", "lint_pooling"):
        MODS[name] = __import__(name)
    # OD131 (lane pf1-walk-cover-strict): pending_walk reads the routing table as HEAD's commit holds it, with git,
    # which the process guard refuses; here the study's own routing.json stands in for it (a clean checkout holds
    # HEAD's), and tests/test_walk_cover_strict.py binds the git read itself
    import pending_walk
    import routing
    SAVED["head_routing_table"] = getattr(pending_walk, "head_routing_table", None)
    pending_walk.head_routing_table = lambda: routing.load_table()
    path = HERE / "walk_plan.py"
    if not path.is_file():
        MODS["walk_plan"] = None               # red first: every test fails by P0.module, never by an error
        return
    text = path.read_text()
    try:
        if MUTANT_SOURCE is not None:          # the generated sweep: one mutated module
            text = Path(MUTANT_SOURCE).read_text()
            MODS["walk_plan"] = load_walk_plan(text, "generated mutant")
        elif SELECTED is not None:             # a witness: one anchored edit
            _, old, new = mutants()[SELECTED]
            assert text.count(old) == 1, f"mutant {SELECTED}: its anchor occurs {text.count(old)} times"
            text = text.replace(old, new)
            MODS["walk_plan"] = load_walk_plan(text, "witness")
        else:
            # a walk_plan another module imported earlier in the battery (test_recheck_coverage) is bound to the
            # walk_register of that moment, which a later module's tearDown may have dropped: load it afresh
            sys.modules.pop("walk_plan", None)
            import walk_plan
            MODS["walk_plan"] = walk_plan
        # the tests patch MODS["walk_register"]; walk_plan must read that very module, or a patch silently misses
        assert MODS["walk_plan"].walk_register is MODS["walk_register"], \
            "walk_plan reads another walk_register than the one these tests patch"
    except (Exception, SystemExit) as exc:     # a module that does not load (or exits on import) fails by P0.module
        MODS["walk_plan"] = None
        MODS["load_error"] = repr(exc)
    MODS["walk_plan_source"] = text


def tearDownModule():
    subprocess.Popen = SAVED["popen"]
    import pending_walk
    if SAVED.get("head_routing_table") is None:
        pending_walk.__dict__.pop("head_routing_table", None)
    else:
        pending_walk.head_routing_table = SAVED["head_routing_table"]
    if SELECTED is not None or MUTANT_SOURCE is not None:
        sys.modules.pop("walk_plan", None)     # a compiled mutant never outlives this module
    sys.path[:] = SAVED["path"]


# ---- the independent derivation: the tests' own reading of the design files, never walk_plan's ----

def read_design(study: Path):
    draft = json.loads((study / "prereg-draft.json").read_text())
    tasks = []
    for t in draft["tasks"]:
        halves = list(json.loads((study / "tasks" / f"{t['id']}.json").read_text())["halves"])
        tasks.append((t["id"], halves, list(t["wordings"])))
    return draft, tasks


def every_wording_model(draft) -> tuple:
    """The plan's rule (plan 875, "every wording of every task, on Haiku"): Haiku is a Claude model, so the search
    is arm A's models only (W11C-R1-5), never every arm."""
    found = [m for m in draft["models"]["A"] if "haiku" in m.casefold()]
    assert len(found) == 1, f"the design names {len(found)} haiku models on arm A"
    return "A", found[0]


def expected_counts(study: Path) -> dict:
    draft, tasks = read_design(study)
    every = every_wording_model(draft)
    out: dict = {}
    for arm, models in draft["models"].items():
        for m in models:
            n = 0
            for _, halves, wordings in tasks:
                n += len(halves) * (len(wordings) if (arm, m) == every else 1)
            out.setdefault(arm, {})[m] = n
    return out


def harness_of(draft) -> dict:
    out: dict = {}
    for row in draft["rows"]:
        out.setdefault((row["arm"], row["model"]), set()).add(row["agent"]["harness"])
    return out


GRADED = '{"graded": true, "row": {}, "grade": {"label": "stand-in"}}\n'


def checked(folder: Path) -> None:
    """BOOTSTRAP B5 (glitch-6b's first-walk bootstrap ruling, 15 Oct 2026): a graded walk counts only beside a check.json
    the checker wrote under the constants in force, naming no constant-bound reason (pending_walk.checker_standing)."""
    import check_take
    (folder / "check.json").write_text(json.dumps({"walk": folder.name, "checked": True, "checker_reasons": [],
                                                   "events": {"outside_reach": 0}, "route": "graded", "route_refused": None,
                                                   "checker_constants_sha256": check_take.checker_constants_sha256(),
                                                   "no_output_nudges": 0,     # review r6 MINOR 2: walk_runner's count
                                                   "agent_calls": 0, "subagents": {"calls": [], "models": [], "stream_file_differences": 0}, "nested_cli_calls": 0}))   # Agent parity, part 6


def entry(spec: dict, walk: str, **changes) -> dict:
    e = {k: spec[k] for k in FIELDS}
    e.update(walk=walk, reason="synthetic register entry for a test", counted=False)
    e.update(changes)
    return e


def model_line(arm, model, agent, covered, n) -> str:
    return f"arm {arm}, {model} ({agent}): {covered} of {n} required walks covered, {n - covered} missing"


class Base(unittest.TestCase):
    def wp(self, clause: str):
        mod = MODS.get("walk_plan")
        self.assertIsNotNone(mod, f"P0.module {clause}: walk_plan.py does not exist yet or does not load "
                                  f"({MODS.get('load_error')})")
        return mod

    def plan(self, clause: str, study: Path = HERE):
        wp = self.wp(clause)
        try:
            design = wp.design_in_force(study)
            return design, wp.plan_walks(design)
        except Exception as exc:
            self.fail(f"{clause}: the plan was refused or raised: {exc!r}")

    def call(self, clause: str, fn, *args):
        """fn(*args), where any exception fails the clause by an assertion (W11C-R1-4)."""
        try:
            return fn(*args)
        except Exception as exc:
            self.fail(f"{clause}: {getattr(fn, '__name__', fn)} raised {exc!r}")

    def typed(self, kind, fn, *args):
        got = self.call(self.CLAUSE, getattr(self.wp(self.CLAUSE), fn), *args)
        self.assertIsInstance(got, kind, f"{self.CLAUSE}: {fn} returned {got!r}")
        return got

    def key(self, *args):
        return self.typed(tuple, "cover_key", *args)

    def sline(self, spec):
        return self.typed(str, "spec_line", spec)

    def counts(self, specs):
        return self.typed(dict, "counts", specs)

    def refuses(self, clause: str, call, *args):
        """call(*args) must raise walk_plan.PlanRefused, and nothing else (W11C-R1-4)."""
        wp = self.wp(clause)
        try:
            call(*args)
        except wp.PlanRefused as exc:
            return exc
        except Exception as exc:
            self.fail(f"{clause}: raised {exc!r}, not PlanRefused")
        self.fail(f"{clause}: not refused")

    def cover(self, clause: str, entries: list, specs: list, design: dict) -> dict:
        wp = self.wp(clause)
        try:
            return wp.coverage(entries, specs, design)
        except Exception as exc:
            self.fail(f"{clause}: coverage was refused or raised: {exc!r}")

    def tmpdir(self) -> Path:
        d = Path(tempfile.mkdtemp(prefix="w11c-"))
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def study_copy(self) -> Path:
        """A synthetic copy of the design files: prereg-draft.json and tasks/*.json, nothing else."""
        d = self.tmpdir()
        shutil.copy2(HERE / "prereg-draft.json", d / "prereg-draft.json")
        (d / "tasks").mkdir()
        for f in (HERE / "tasks").glob("*.json"):
            shutil.copy2(f, d / "tasks" / f.name)
        return d

    def edit_draft(self, study: Path, edit) -> None:
        path = study / "prereg-draft.json"
        draft = json.loads(path.read_text())
        edit(draft)
        path.write_text(json.dumps(draft))

    def edit_task(self, study: Path, task: str, edit) -> None:
        path = study / "tasks" / f"{task}.json"
        doc = json.loads(path.read_text())
        edit(doc)
        path.write_text(json.dumps(doc))

    def rehearsals(self, entries, graded=True) -> Path:
        """A register of `entries`; with `graded`, each entry whose walk is a walk id gets a graded-true grade.json
        (the batch-8 fix ruling: only a graded walk covers its spec, and a missing grade fails closed)."""
        base = self.raw_register(json.dumps({"schema": 1, "walks": entries}))
        if graded:
            import walk_register as wr
            for e in entries:
                walk = e.get("walk") if isinstance(e, dict) else None
                if isinstance(walk, str) and wr.WALK_ID.fullmatch(walk) and not (base / walk).exists():
                    (base / walk).mkdir()
                    (base / walk / "grade.json").write_text(GRADED)
                    checked(base / walk)
        return base

    def raw_register(self, text: str) -> Path:
        base = self.tmpdir() / "rehearsals"
        base.mkdir()
        (base / "register.json").write_text(text)
        return base

    def cli(self, clause: str, argv: list) -> tuple[int, str]:
        """main(argv)'s exit code and output; a SystemExit is its code, any other exception fails the clause."""
        wp = self.wp(clause)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = wp.main(argv)
        except SystemExit as exc:
            code = exc.code
        except Exception as exc:
            self.fail(f"{clause}: main({argv!r}) raised {exc!r}")
        return code, out.getvalue() + err.getvalue()


class P1Counts(Base):
    CLAUSE = "P1.counts"

    def test_the_figures_are_rederived_from_the_design(self):
        _, specs = self.plan("P1.counts")
        self.wp("P1.counts")
        self.assertEqual(self.counts(specs), expected_counts(HERE), "P1.counts")
        self.assertEqual(len(specs), sum(sum(v.values()) for v in expected_counts(HERE).values()), "P1.counts")
        # the study folder may be named by a string, as by a Path
        self.assertEqual(self.plan("P1.counts", str(HERE))[1], specs, "P1.counts: a study folder named by a string")


class P2Dropped(Base):
    CLAUSE = "P2.dropped"

    def test_a_dropped_task_or_wording_changes_the_figures(self):
        self.wp("P2.dropped")
        base = expected_counts(HERE)
        # a dropped task: gone from the draft's tasks and rows
        study = self.study_copy()
        draft = json.loads((study / "prereg-draft.json").read_text())
        gone = draft["tasks"][-1]["id"]
        self.edit_draft(study, lambda d: (d.__setitem__("tasks", [t for t in d["tasks"] if t["id"] != gone]),
                                          d.__setitem__("rows", [r for r in d["rows"] if r["task"] != gone])))
        _, specs = self.plan("P2.dropped", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P2.dropped: the synthetic edit did not change the design")
        self.assertEqual(self.counts(specs), want, f"P2.dropped: a dropped task ({gone})")
        self.assertNotIn(gone, {s["task"] for s in specs}, "P2.dropped")
        # a dropped wording: the last wording of the first task, gone from the task and its rows
        study = self.study_copy()
        draft = json.loads((study / "prereg-draft.json").read_text())
        task, last = draft["tasks"][0]["id"], draft["tasks"][0]["wordings"][-1]

        def drop(d):
            d["tasks"][0]["wordings"] = d["tasks"][0]["wordings"][:-1]
            d["rows"] = [r for r in d["rows"] if not (r["task"] == task and r["wording"] == last)]
        self.edit_draft(study, drop)
        _, specs = self.plan("P2.dropped", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P2.dropped: the synthetic edit did not change the design")
        self.assertEqual(self.counts(specs), want, f"P2.dropped: a dropped wording ({task} {last})")
        self.assertNotIn((task, last), {(s["task"], s["wording"]) for s in specs}, "P2.dropped")


class P3Halves(Base):
    CLAUSE = "P3.halves"

    def test_every_task_and_half_on_every_planned_model(self):
        design, specs = self.plan("P3.halves")
        wr = MODS["walk_register"]
        draft, tasks = read_design(HERE)
        every = every_wording_model(draft)
        harness = harness_of(draft)
        reg = wr.design_in_force(HERE)
        for arm, models in draft["models"].items():
            for m in models:
                mine = [s for s in specs if (s["arm"], s["model"]) == (arm, m)]
                self.assertEqual({(s["task"], s["half"]) for s in mine},
                                 {(t, h) for t, halves, _ in tasks for h in halves}, f"P3.halves {arm} {m}")
                if (arm, m) == every:
                    self.assertEqual({(s["task"], s["half"], s["wording"]) for s in mine},
                                     {(t, h, w) for t, halves, ws in tasks for h in halves for w in ws},
                                     f"P3.halves every wording on {m}")
        for i, s in enumerate(specs):
            self.assertEqual(tuple(s), FIELDS + ("agent",), f"P3.halves spec {i}: its fields")
            self.assertIsNone(s["walk"], f"P3.halves spec {i}: the walk id is the runner's")
            self.assertIs(s["counted"], False, f"P3.halves spec {i}: counted")
            self.assertTrue(isinstance(s["reason"], str) and s["reason"].strip(), f"P3.halves spec {i}: reason")
            rule = "every wording of every task" if (s["arm"], s["model"]) == every else "with at least one wording"
            self.assertIn(rule, s["reason"], f"P3.halves spec {i}: the reason names its rule")
            self.assertEqual({s["agent"]}, harness[(s["arm"], s["model"])], f"P3.halves spec {i}: agent")
            self.assertEqual(wr.entry_problems(i, entry(s, f"probe-{i}"), reg), [], f"P3.halves spec {i}")
        optional = {spec["model"] for spec in (draft.get("optional_arms") or {}).values()}
        self.assertTrue(optional, "P3.halves: the design names an optional arm (arm C)")
        self.assertFalse(optional & {s["model"] for s in specs}, "P3.halves: an optional arm is never required")
        self.assertFalse(set(draft.get("optional_arms") or {}) & {s["arm"] for s in specs}, "P3.halves")
        self.assertEqual(design["every_wording"], every, "P3.halves")


class P4OffDesign(Base):
    CLAUSE = "P4.off-design"

    def test_an_entry_outside_the_plan_is_reported_never_counted(self):
        self.wp("P4.off-design")
        design, specs = self.plan("P4.off-design")
        draft, _ = read_design(HERE)
        every = design["every_wording"]
        other = next(s for s in specs if (s["arm"], s["model"]) != every)
        later_wording = next(t["wordings"][-1] for t in draft["tasks"] if t["id"] == other["task"])
        c_arm, c_spec = next(iter(draft["optional_arms"].items()))
        entries = [
            entry(other, "w-ok", wording=later_wording),                 # covers: any wording of the task
            entry(other, "w-retry"),                                     # a retry: the same spec, counted once
            entry(other, "w-bad-wording", wording="w-not-in-design"),    # refused by the design
            entry(other, "w-counted", counted=True),                     # refused: a walk is never counted
            entry(other, "w-wrong-arm", arm="O" if other["arm"] != "O" else "G"),
            entry(other, "w-arm-c", arm=c_arm, model=c_spec["model"]),   # in the design, not in the plan
            5,                                                           # not an object
            entry(other, 7),                                             # a walk id that is not a string
        ]
        got = self.cover("P4.off-design", entries, specs, design)
        key = self.key(other, design)
        self.assertEqual(list(got["covered"]), [key], "P4.off-design: only the plan's spec is covered")
        self.assertEqual(got["covered"][key], ["w-ok", "w-retry"], "P4.off-design: a retry covers the spec once")
        self.assertEqual(len(got["missing"]), len(specs) - 1, "P4.off-design: one spec covered, once")
        outside = [w for w, _ in got["outside"]]
        self.assertEqual(outside, ["w-bad-wording", "w-counted", "w-wrong-arm", "w-arm-c", "entry 6", "entry 7"],
                         "P4.off-design")
        why = dict(got["outside"])
        self.assertIn("not a walk the plan requires", why["w-arm-c"], "P4.off-design")
        self.assertIn("is not an object", why["entry 6"], "P4.off-design")
        # an entry the register admits whose cell is no row of the design covers nothing
        thinned = copy.deepcopy(design)
        cell = (other["arm"], other["model"], other["task"], other["half"], later_wording)
        thinned["cells"].discard(cell)
        got = self.cover("P4.off-design", entries[:2], specs, thinned)
        self.assertEqual(got["covered"].get(key), ["w-retry"], "P4.off-design: a wording with no row covers nothing")
        self.assertIn("not a row of the design", dict(got["outside"]).get("w-ok", ""), "P4.off-design")
        # on the command line: an arm C walk is reported outside the plan, by its walk id, and exit 0
        base = self.rehearsals([entries[0], entries[1], entries[5]])
        code, out = self.cli("P4.off-design", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P4.off-design: {out[-400:]}")
        self.assertRegex(out, r"(?m)^outside the plan, not counted: walk 'w-arm-c': not a walk the plan requires",
                         "P4.off-design")
        self.assertRegex(out, rf"(?m)^covered  {re.escape(self.sline(other))} by w-ok \(also w-retry, ",
                         "P4.off-design")


class P5ExactWording(Base):
    CLAUSE = "P5.exact-wording"

    def test_the_every_wording_model_needs_each_wording(self):
        wp = self.wp("P5.exact-wording")
        design, specs = self.plan("P5.exact-wording")
        every = [s for s in specs if (s["arm"], s["model"]) == design["every_wording"]]
        first, second = every[0], next(s for s in every[1:] if (s["task"], s["half"]) == (every[0]["task"],
                                                                                          every[0]["half"]))
        got = self.cover("P5.exact-wording", [entry(second, "h-second")], specs, design)
        self.assertEqual(list(got["covered"]), [self.key(second, design)], "P5.exact-wording")
        self.assertIn(first, got["missing"], "P5.exact-wording: another wording does not cover this one")
        self.assertNotEqual(self.key(first, design), self.key(second, design), "P5.exact-wording")
        other = next(s for s in specs if (s["arm"], s["model"]) != design["every_wording"])
        twin = dict(other, wording=first["wording"] if other["wording"] != first["wording"] else "w2")
        self.refuses("P5.exact-wording: two specs for one task and half", wp.coverage, [], [other, twin], design)
        self.assertEqual(sum(1 for s in specs if self.key(s, design) == self.key(other, design)), 1,
                         "P5.exact-wording: one spec per task and half on every other model")


class P6Require(Base):
    CLAUSE = "P6.require"

    def test_require_complete_refuses_a_gap(self):
        self.wp("P6.require")
        _, specs = self.plan("P6.require")
        empty = self.rehearsals([])
        code, out = self.cli("P6.require", ["--coverage", "--base", str(empty)])
        self.assertEqual(code, 0, f"P6.require: missing walks before the freeze exit 0: {out}")
        self.assertIn("the register lists no walk", out, "P6.require: an empty register is said out loud")
        self.assertEqual(out.count("\nmissing  "), len(specs), "P6.require: every walk missing, each named")
        for s in specs:
            self.assertRegex(out, rf"(?m)^missing  {re.escape(self.sline(s))}$", "P6.require")
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(empty)])
        self.assertEqual(code, 1, "P6.require: --require-complete with every walk missing")
        one_gap = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs[:-1])])
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(one_gap)])
        self.assertEqual(code, 1, f"P6.require: --require-complete with one gap: {out[-400:]}")
        self.assertNotIn("the register lists no walk", out, "P6.require: the empty line on a register with walks")
        self.assertRegex(out, rf"(?m)^missing  {re.escape(self.sline(specs[-1]))}$", "P6.require")
        self.assertEqual(out.count("\nmissing  "), 1, "P6.require: one missing line")
        for i, s in enumerate(specs[:-1]):
            self.assertRegex(out, rf"(?m)^covered  {re.escape(self.sline(s))} by walk-{i}$", "P6.require")
        full = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs)])
        code, out = self.cli("P6.require", ["--coverage", "--require-complete", "--base", str(full)])
        self.assertEqual(code, 0, f"P6.require: a complete register: {out[-400:]}")
        self.assertNotIn("\nmissing  ", out, "P6.require")
        code, out = self.cli("P6.require", ["--coverage", "--base", str(self.tmpdir())])
        self.assertEqual(code, 2, f"P6.require: a missing register is not an empty one: {out}")
        self.assertIn("a missing register is not an empty one", out, "P6.require")
        with mock.patch.object(Path, "read_bytes", side_effect=PermissionError("synthetic unreadable")):
            code, out = self.cli("P6.require", ["--coverage", "--base", str(full)])
        self.assertEqual(code, 2, f"P6.require: an unreadable register: {out[-300:]}")
        self.assertIn("cannot be read: synthetic unreadable", out, "P6.require: an unreadable register is named")
        linked = self.tmpdir() / "rehearsals"
        linked.mkdir()
        (linked / "register.json").symlink_to(full / "register.json")
        code, out = self.cli("P6.require", ["--coverage", "--base", str(linked)])
        self.assertEqual(code, 2, f"P6.require: a symlinked register is refused: {out[-300:]}")


class P7RegisterOnly(Base):
    CLAUSE = "P7.register-only"

    def test_coverage_reads_the_register_and_never_a_walk_folder(self):
        _, specs = self.plan("P7.register-only")
        base = self.rehearsals([entry(specs[0], "walk-a")])
        (base / "walk-a" / "grade.json").write_text(GRADED)       # graded true (the batch-8 fix ruling)
        touched: list = []
        real = {"open": builtins.open, "listdir": os.listdir, "scandir": os.scandir, "stat": os.stat,
                "lstat": os.lstat}

        def recorder(kind, fn):
            def rec(path=".", *a, **k):
                touched.append((kind, str(path)))
                return fn(path, *a, **k)
            return rec
        with mock.patch("builtins.open", recorder("open", real["open"])), \
                mock.patch("io.open", recorder("open", real["open"])), \
                mock.patch("os.listdir", recorder("list", real["listdir"])), \
                mock.patch("os.scandir", recorder("list", real["scandir"])), \
                mock.patch("os.stat", recorder("stat", real["stat"])), \
                mock.patch("os.lstat", recorder("stat", real["lstat"])):
            code, out = self.cli("P7.register-only", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P7.register-only: {out[-300:]}")
        register = (base / "register.json").resolve()
        under = [(kind, p) for kind, p in touched if p not in (".", "")
                 and Path(p).resolve().is_relative_to(base.resolve())]
        self.assertTrue(under, "P7.register-only: the recorder saw the register (the instrument is armed)")
        grade = (base / "walk-a" / "grade.json").resolve()      # batch-8 ruling: each registered walk's grade
        check = (base / "walk-a" / "check.json").resolve()      # BOOTSTRAP B5: and its check.json
        # moved by lane vendor-admission T4 P5 (plan v4 section 6, NIT 4; glitch-b5 round 13): and its driver ledger,
        # read only to pick the digest in force for its harness (pending_walk.constants_in_force)
        ledger = (base / "walk-a" / "driver-ledger.json").resolve()
        self.assertEqual({Path(p).resolve() for _, p in under}, {register, grade, check, ledger},
                         f"P7.register-only: only the register and each registered walk's grade.json, check.json and "
                         f"driver ledger are opened or "
                         f"looked up under rehearsals/, and nothing is listed: {sorted(set(under))}")
        self.assertNotIn("list", {kind for kind, _ in under}, "P7.register-only")
        self.assertRegex(out, r"(?m)^covered  .* by walk-a$", "P7.register-only")


class P8SpecChecked(Base):
    CLAUSE = "P8.spec-checked"

    def test_a_spec_the_design_refuses_refuses_the_plan(self):
        wp = self.wp("P8.spec-checked")
        design, _ = self.plan("P8.spec-checked")
        # the register's design no longer admits one planned model
        arm, models = next((a, m) for a, m in design["planned"].items() if a != design["every_wording"][0])
        bent = copy.deepcopy(design)
        bent["register"]["arms"][arm] = [m for m in bent["register"]["arms"][arm] if m != models[0]]
        self.refuses("P8.spec-checked: a model the register refuses", wp.plan_walks, bent)
        # a planned cell that is not a row of the design
        bent = copy.deepcopy(design)
        bent["cells"] = {c for c in bent["cells"] if c[1] != models[0]}
        exc = self.refuses("P8.spec-checked: a cell with no row", wp.plan_walks, bent)
        n = expected_counts(HERE)[arm][models[0]]
        self.assertGreater(n, 6, "P8.spec-checked: the case is long")
        self.assertEqual(len(re.findall(r"spec \d+: ", str(exc))), 5, "P8.spec-checked: the first five are named")
        self.assertTrue(str(exc).endswith(f"; and {n - 5} more"), f"P8.spec-checked: the rest are counted: {exc}")
        # six planned cells with no row: five named, and one more
        bent = copy.deepcopy(design)
        for s in [s for s in self.plan("P8.spec-checked")[1] if s["model"] == models[0]][:6]:
            bent["cells"].discard((s["arm"], s["model"], s["task"], s["half"], s["wording"]))
        exc = self.refuses("P8.spec-checked: six cells with no row", wp.plan_walks, bent)
        self.assertEqual(len(re.findall(r"spec \d+: ", str(exc))), 5, "P8.spec-checked: six problems, five named")
        self.assertTrue(str(exc).endswith("; and 1 more"), f"P8.spec-checked: six problems, one more: {exc}")
        # one planned cell with no row: one problem, named, and nothing said to be left out
        bent = copy.deepcopy(design)
        bent["cells"].discard(next(c for c in sorted(bent["cells"]) if c[1] == models[0]))
        exc = self.refuses("P8.spec-checked: one cell with no row", wp.plan_walks, bent)
        self.assertNotIn(" more", str(exc), "P8.spec-checked: a short refusal leaves nothing out")
        # a planned model whose rows name two harnesses
        study = self.study_copy()

        def mixed(d):
            row = next(r for r in d["rows"] if r["model"] == models[0])
            row["agent"] = dict(row["agent"], harness=row["agent"]["harness"] + "-other")
        self.edit_draft(study, mixed)
        self.refuses("P8.spec-checked: two harnesses for one model", wp.design_in_force, study)


class P9Prose(Base):
    CLAUSE = "P9.prose"

    def test_the_printed_plan_and_report_are_clean(self):
        _, specs = self.plan("P9.prose")
        ll, lp = MODS["lint_language"], MODS["lint_pooling"]
        code, listed = self.cli("P9.prose", ["--list"])
        self.assertEqual(code, 0, f"P9.prose: {listed[-400:]}")
        base = self.rehearsals([entry(specs[0], "walk-a")])
        code, covered = self.cli("P9.prose", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, "P9.prose")
        draft, _ = read_design(HERE)
        for name, text in (("--list", listed), ("--coverage", covered)):
            found = lp.scan_text(text, f"walk_plan {name}")
            found += ll.scan_text(text, f"walk_plan {name}", ll.load_allowlist())
            self.assertEqual(found, [], f"P9.prose {name}")
            for line in text.splitlines():
                # a figure sits on a line that names one model, on a citation header, or on one register entry
                named = any(m in line for models in draft["models"].values() for m in models)
                if re.search(r"\d", line):
                    self.assertTrue(named or line.startswith(("# ", "outside the plan, not counted: walk ")),
                                    f"P9.prose {name}: a figure not bound to one model: {line!r}")
        walk_lines = [line for line in listed.splitlines() if line.startswith("walk  ")]
        self.assertEqual(walk_lines, [f"walk  {s['arm']} {s['model']} {s['agent']} {s['task']} {s['half']} "
                                      f"{s['wording']}" for s in specs], "P9.prose: one line per required walk")
        every = every_wording_model(draft)
        for arm, models in draft["models"].items():
            for m in models:
                rule = "every wording of each task and half" if (arm, m) == every else \
                    "each task and half, any one wording"
                self.assertRegex(listed, rf"(?m)^arm {arm}, {re.escape(m)} \(.*\): \d+ required walks, {rule}$",
                                 f"P9.prose: a line for {m}")


class P10EveryRule(Base):
    CLAUSE = "P10.every-rule"

    def test_the_every_wording_model_is_one_model_of_the_design(self):
        wp = self.wp("P10.every-rule")
        design, _ = self.plan("P10.every-rule")
        draft, _ = read_design(HERE)
        self.assertEqual(design["every_wording"], every_wording_model(draft), "P10.every-rule")
        haiku = every_wording_model(draft)[1]

        def two(d):
            # a second haiku model on arm A with rows of its own, so only the every-wording rule can refuse it
            d["models"]["A"] = d["models"]["A"] + ["claude-haiku-x"]
            d["rows"] = d["rows"] + [dict(r, model="claude-haiku-x") for r in d["rows"] if r["model"] == haiku]

        def moved(d):
            # the only haiku model sits on arm O (rows of its own): arm A has none, so the rule refuses
            d["models"]["A"] = [m for m in d["models"]["A"] if m != haiku]
            d["models"]["O"] = d["models"]["O"] + [haiku]
            d["rows"] = [dict(r, arm="O", agent=dict(r["agent"], harness="codex")) if r["model"] == haiku else r
                         for r in d["rows"]]
        for label, edit in (("none", lambda d: d["models"].__setitem__(
                                "A", [m for m in d["models"]["A"] if m != haiku])),
                            ("two", two), ("moved to arm O", moved)):
            study = self.study_copy()
            self.edit_draft(study, edit)
            exc = self.refuses(f"P10.every-rule: {label}", wp.design_in_force, study)
            self.assertIn("for every wording", str(exc), f"P10.every-rule: {label}")
        # a haiku-named model on another arm is not a second every-wording model, and gets one wording
        study = self.study_copy()

        def other_arm(d):
            d["models"]["O"] = d["models"]["O"] + ["gpt-haiku-test"]
            d["rows"] = d["rows"] + [dict(r, model="gpt-haiku-test") for r in d["rows"]
                                     if r["arm"] == "O" and r["model"] == d["models"]["O"][0]]
        self.edit_draft(study, other_arm)
        design, specs = self.plan("P10.every-rule", study)
        self.assertEqual(design["every_wording"], ("A", haiku), "P10.every-rule: arm A's haiku")
        self.assertEqual(self.counts(specs), expected_counts(study), "P10.every-rule: one wording on arm O's model")


class P11Design(Base):
    CLAUSE = "P11.design"

    def test_a_half_or_a_model_moves_the_figures(self):
        self.wp("P11.design")
        base = expected_counts(HERE)
        draft, tasks = read_design(HERE)
        task, halves, _ = tasks[0]
        # a dropped half: gone from the task file and the rows
        study = self.study_copy()
        self.edit_task(study, task, lambda doc: doc["halves"].pop(halves[-1]))
        self.edit_draft(study, lambda d: d.__setitem__(
            "rows", [r for r in d["rows"] if not (r["task"] == task and r["half"] == halves[-1])]))
        _, specs = self.plan("P11.design", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P11.design: the synthetic edit did not change the design")
        self.assertEqual(self.counts(specs), want, "P11.design: a dropped half")
        self.assertNotIn((task, halves[-1]), {(s["task"], s["half"]) for s in specs}, "P11.design")
        # an added half: a copy of the last one under a new name, in the task file and the rows
        study = self.study_copy()
        self.edit_task(study, task, lambda doc: doc["halves"].__setitem__("extra", doc["halves"][halves[-1]]))
        self.edit_draft(study, lambda d: d.__setitem__(
            "rows", d["rows"] + [dict(r, half="extra") for r in d["rows"]
                                 if r["task"] == task and r["half"] == halves[-1]]))
        _, specs = self.plan("P11.design", study)
        want = expected_counts(study)
        self.assertNotEqual(want, base, "P11.design: the synthetic edit did not change the design")
        self.assertEqual(self.counts(specs), want, "P11.design: an added half")
        self.assertIn((task, "extra"), {(s["task"], s["half"]) for s in specs}, "P11.design")
        # an added model on arm G, with rows of its own
        study = self.study_copy()

        def add(d):
            first = d["models"]["G"][0]
            d["models"]["G"] = d["models"]["G"] + ["gemini-test-added"]
            d["rows"] = d["rows"] + [dict(r, model="gemini-test-added") for r in d["rows"] if r["model"] == first]
        self.edit_draft(study, add)
        _, specs = self.plan("P11.design", study)
        want = expected_counts(study)
        self.assertIn("gemini-test-added", want["G"], "P11.design")
        self.assertEqual(self.counts(specs), want, "P11.design: an added model on another arm")


class P12Register(Base):
    CLAUSE = "P12.register"

    def test_a_register_the_register_check_refuses_is_refused(self):
        wr = MODS["walk_register"]
        _, specs = self.plan("P12.register")
        good = [entry(s, f"walk-{i}") for i, s in enumerate(specs[:3])]
        cases = {
            "one walk id for every spec": json.dumps({"schema": 1, "walks": [entry(s, "only-walk") for s in specs]}),
            "a walk id registered twice": json.dumps({"schema": 1, "walks": good + [dict(good[0])]}),
            "ids that differ only by case": json.dumps({"schema": 1, "walks": good + [
                entry(specs[3], good[0]["walk"].upper())]}),
            "a wrong schema": json.dumps({"schema": 99, "walks": good}),
            "an extra top-level key": json.dumps({"schema": 1, "walks": good, "extra": True}),
            "walks not a list": json.dumps({"schema": 1, "walks": {}}),
            "a top-level list": json.dumps([good]),
            "a non-object entry": json.dumps({"schema": 1, "walks": good + [5]}),
            "a counted entry": json.dumps({"schema": 1, "walks": good + [entry(specs[3], "walk-c", counted=True)]}),
            "an off-design entry": json.dumps({"schema": 1, "walks": good + [
                entry(specs[3], "walk-d", wording="w-not-in-design")]}),
            "a duplicate JSON key": '{"schema": 1, "walks": [], "walks": ' + json.dumps(good) + "}",
            "a walk id that is not a string": json.dumps({"schema": 1, "walks": good + [entry(specs[3], 7)]}),
            "a walk id of two path segments": json.dumps({"schema": 1, "walks": good + [
                entry(specs[3], "nested/walk")]}),
        }
        for label, text in cases.items():
            base = self.raw_register(text)
            problems, _ = wr.check(base, wr.design_in_force(HERE))
            self.assertTrue(problems, f"P12.register {label}: walk_register.check refuses it (the case is armed)")
            for argv in (["--coverage"], ["--coverage", "--require-complete"]):
                code, out = self.cli("P12.register", argv + ["--base", str(base)])
                self.assertEqual(code, 2, f"P12.register {label} {argv}: {out[-400:]}")
                self.assertIn("walk_register's check refuses", out, f"P12.register {label}")
                self.assertNotIn("ok:", out, f"P12.register {label}")
                self.assertNotIn("\ncovered  ", "\n" + out, f"P12.register {label}: nothing is reported covered")
        # and the register check's own words reach the report
        code, out = self.cli("P12.register", ["--coverage", "--base", str(self.raw_register(cases[
            "one walk id for every spec"]))])
        self.assertIn("registered twice", out, "P12.register: the check's own words")
        self.assertRegex(out, r"; and \d+ more", "P12.register: a long refusal says how many it left out")
        # six problems: the first five named, and one more; many: five named and the rest counted
        for k in (6, 9):
            walks = [entry(s, f"c-{i}", counted=True) for i, s in enumerate(specs[:k])]
            text = json.dumps({"schema": 1, "walks": walks})
            base = self.raw_register(text)
            code, out = self.cli("P12.register", ["--coverage", "--base", str(base)])
            self.assertEqual(code, 2, f"P12.register: {k} counted entries")
            self.assertEqual(len(re.findall(r"walk entry \d+: ", out)), 5, f"P12.register: {k} problems, five named")
            self.assertIn(f"; and {k - 5} more", out, f"P12.register: {k} problems, the rest counted")
        # walk ids that cannot be stand-in folder names are a named refusal, never a crash
        for label, walk in (("register.json", "register.json"), ("a 300-character id", "w" * 300)):
            base = self.raw_register(json.dumps({"schema": 1, "walks": good + [entry(specs[3], walk)]}))
            code, out = self.cli("P12.register", ["--coverage", "--base", str(base)])
            self.assertEqual(code, 2, f"P12.register {label}: {out[-300:]}")
            self.assertIn("walk_register's check refuses", out, f"P12.register {label}")
        code, out = self.cli("P12.register", ["--coverage", "--base", str(self.raw_register(cases["a wrong schema"]))])
        self.assertIn("schema is 99", out, "P12.register: the check's own words")
        self.assertNotIn(" more", out, "P12.register: a short refusal leaves nothing out")
        # a register the check accepts is read
        code, out = self.cli("P12.register", ["--coverage", "--base", str(self.rehearsals(good))])
        self.assertEqual(code, 0, f"P12.register: a good register: {out[-300:]}")


class P13PerModel(Base):
    CLAUSE = "P13.per-model"

    def test_each_model_figure_counts_its_own_gaps(self):
        wp = self.wp("P13.per-model")
        design, specs = self.plan("P13.per-model")
        draft, _ = read_design(HERE)
        # a different number of gaps on each model: model k of the plan misses k walks (k = 0, 1, 2, ...)
        order = [(arm, m) for arm, models in draft["models"].items() for m in models]
        gaps = {pair: k for k, pair in enumerate(order)}
        kept, dropped = [], {}
        for s in specs:
            pair = (s["arm"], s["model"])
            if dropped.get(pair, 0) < gaps[pair]:
                dropped[pair] = dropped.get(pair, 0) + 1
                continue
            kept.append(s)
        base = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(kept)])
        code, out = self.cli("P13.per-model", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P13.per-model: {out[-300:]}")
        want = expected_counts(HERE)
        harness = harness_of(draft)
        for arm, m in order:
            n, gap = want[arm][m], gaps[(arm, m)]
            line = model_line(arm, m, next(iter(harness[(arm, m)])), n - gap, n)
            self.assertRegex(out, rf"(?m)^{re.escape(line)}$", f"P13.per-model {arm} {m}")
        # one model id planned on two arms: each arm's line counts its own gaps
        haiku = design["every_wording"]
        model = next(m for m in design["planned"]["A"] if (("A", m)) != haiku)
        twin = copy.deepcopy(design)
        twin["planned"]["O"] = twin["planned"]["O"] + [model]
        twin["agents"][("O", model)] = "codex"
        twin["register"]["arms"]["O"] = twin["register"]["arms"]["O"] + [model]
        twin["cells"] |= {("O", model, t, h, w) for (a, mm, t, h, w) in design["cells"] if (a, mm) == ("A", model)}
        twin_specs = self.call(self.CLAUSE, wp.plan_walks, twin)
        mine = {arm: [s for s in twin_specs if (s["arm"], s["model"]) == (arm, model)] for arm in ("A", "O")}
        entries = [entry(s, f"a-{i}") for i, s in enumerate(mine["A"][2:])] + \
            [entry(s, f"o-{i}") for i, s in enumerate(mine["O"][5:])]
        got = self.cover("P13.per-model", entries, twin_specs, twin)
        lines = self.call(self.CLAUSE, wp.coverage_lines, got, twin_specs, twin, len(entries))
        for arm, gap in (("A", 2), ("O", 5)):
            n = len(mine[arm])
            self.assertIn(model_line(arm, model, twin["agents"][(arm, model)], n - gap, n), lines,
                          f"P13.per-model: {model} on arm {arm}")


class P14Cli(Base):
    CLAUSE = "P14.cli"

    def run_script(self, argv: list) -> tuple:
        """walk_plan's source run as a script (`__name__ == "__main__"`), as a gate calls it."""
        self.wp("P14.cli")
        source = MODS["walk_plan_source"]
        out = io.StringIO()
        scope = {"__name__": "__main__", "__file__": str(HERE / "walk_plan.py")}
        code = "no SystemExit"
        try:
            with mock.patch.object(sys, "argv", ["walk_plan.py", *argv]), contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(out):
                exec(compile(source, str(HERE / "walk_plan.py") + " (as a script)", "exec"), scope)
        except SystemExit as exc:
            code = exc.code
        except Exception as exc:
            self.fail(f"P14.cli: the script raised {exc!r}")
        return code, out.getvalue()

    def test_the_command_line_exits(self):
        wr = MODS["walk_register"]
        _, specs = self.plan("P14.cli")
        empty = self.rehearsals([])
        full = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs)])
        # the script entry exits with main's code
        self.assertEqual(self.run_script(["--coverage", "--require-complete", "--base", str(empty)])[0], 1,
                         "P14.cli: the script exits 1 on a gap")
        self.assertEqual(self.run_script(["--coverage", "--require-complete", "--base", str(full)])[0], 0,
                         "P14.cli: the script exits 0 on a complete register")
        self.assertEqual(self.run_script(["--list"])[0], 0, "P14.cli")
        code, listed = self.cli("P14.cli", ["--list"])
        self.assertEqual(code, 0, "P14.cli")
        self.assertFalse(re.search(r"(?m)^(covered  |missing  |# walk coverage|the register lists)", listed),
                         "P14.cli: --list prints the plan, never a coverage report")
        code, out = self.cli("P14.cli", ["--coverage", "--require-complete", "--base", str(empty)])
        self.assertEqual(out.splitlines()[-1], "FAIL --require-complete: required walks are missing (the lines "
                         "above name each)", "P14.cli: the gap is said on the last line")
        # --require-complete goes with --coverage only
        code, out = self.cli("P14.cli", ["--list", "--require-complete"])
        self.assertEqual(code, 2, f"P14.cli: --list --require-complete is refused: {out[-300:]}")
        self.assertIn("--require-complete goes with --coverage", out, "P14.cli")
        # the ok line: only under --require-complete with nothing missing
        code, out = self.cli("P14.cli", ["--coverage", "--base", str(empty)])
        self.assertNotIn("ok:", out, "P14.cli: no ok line while walks are missing")
        code, out = self.cli("P14.cli", ["--coverage", "--base", str(full)])
        self.assertNotIn("ok:", out, "P14.cli: no ok line without --require-complete")
        code, out = self.cli("P14.cli", ["--coverage", "--require-complete", "--base", str(full)])
        self.assertEqual(out.splitlines()[-1], "ok: every required walk is covered", "P14.cli")
        # a design that cannot be derived exits 2, saying so
        wp = self.wp("P14.cli")
        with mock.patch.object(wp, "design_in_force", side_effect=wp.PlanRefused("synthetic refusal")):
            for argv in (["--list"], ["--coverage", "--base", str(full)]):
                code, out = self.cli("P14.cli", argv)
                self.assertEqual((code, out.strip()), (2, "FAIL the walk plan cannot be derived: synthetic refusal"),
                                 f"P14.cli {argv}")
        # without --base the register is walk_register.REHEARSALS'
        one = self.rehearsals([entry(specs[0], "walk-default")])
        with mock.patch.object(wr, "REHEARSALS", one):
            code, out = self.cli("P14.cli", ["--coverage"])
        self.assertEqual(code, 0, f"P14.cli: {out[-300:]}")
        self.assertRegex(out, r"(?m)^covered  .* by walk-default$", "P14.cli: the default register is read")


class P15Sweep(Base):
    CLAUSE = "P15.sweep"

    def test_the_sweep_generates_and_its_registry_is_current(self):
        self.wp("P15.sweep")
        made = generated_mutants(MODS["walk_plan_source"])
        self.assertTrue(made, "P15.sweep: the mutator generates mutants (the sweep is armed)")
        self.assertEqual(len({m["id"] for m in made}), len(made), "P15.sweep: mutant ids are unique")
        self.assertEqual(equivalent_problems(made, EQUIVALENT), [], "P15.sweep: the EQUIVALENT registry is current")
        first = made[0]
        self.assertEqual(len(equivalent_problems(made, {first["id"]: (first["line"] + " changed", "a reason")})), 1,
                         "P15.sweep: an entry on a changed line is stale")
        self.assertEqual(len(equivalent_problems(made, {"L0.pass.0": ("x", "a reason")})), 1,
                         "P15.sweep: an entry with no such mutant is stale")
        self.assertEqual(len(equivalent_problems(made, {first["id"]: (first["line"], " ")})), 1,
                         "P15.sweep: an entry needs a reason")


class P16ScratchOnly(Base):
    CLAUSE = "P16.scratch-only"

    def test_a_path_shaped_walk_id_writes_nothing_outside_the_scratch(self):
        wr = MODS["walk_register"]
        _, specs = self.plan("P16.scratch-only")
        good = [entry(s, f"walk-{i}") for i, s in enumerate(specs[:3])]
        root, outside = self.tmpdir(), self.tmpdir()      # root holds the scratch folder; outside is a bystander
        ids = {"a parent step": "../escaped-up", "the parent itself": "..", "an absolute path":
               str(outside / "escaped-abs")}
        for label, walk in ids.items():
            self.assertIsNone(wr.WALK_ID.fullmatch(walk), f"P16.scratch-only {label}: not a walk id (case armed)")
            base = self.raw_register(json.dumps({"schema": 1, "walks": good + [entry(specs[3], walk)]}))
            problems, _ = wr.check(base, wr.design_in_force(HERE))
            self.assertTrue(problems, f"P16.scratch-only {label}: walk_register.check refuses it (case armed)")
            with mock.patch.object(tempfile, "tempdir", str(root)):
                code, out = self.cli("P16.scratch-only", ["--coverage", "--base", str(base)])
            self.assertEqual(code, 2, f"P16.scratch-only {label}: {out[-300:]}")
            self.assertIn("walk_register's check refuses", out, f"P16.scratch-only {label}")
            self.assertEqual(sorted(os.listdir(root)), [], f"P16.scratch-only {label}: the scratch folder is the "
                                                           f"only thing written, and it is gone")
            self.assertEqual(sorted(os.listdir(outside)), [], f"P16.scratch-only {label}: nothing written outside")


class P17WrongType(Base):
    CLAUSE = "P17.wrong-type"

    def test_a_field_of_the_wrong_type_is_skipped_never_a_crash(self):
        wp = self.wp("P17.wrong-type")
        ok = {"walk": "walk-ok"}
        wrong = [{"walk": None}, {"walk": 7}, {"walk": True}, {"walk": ["walk-l"]}, {"walk": {"walk": "walk-d"}},
                 {"not-walk": "walk-k"}, 5, "walk-s", None, ["walk-x"], {"walk": ""}, {"walk": "a/b"},
                 {"walk": "../up"}, {"walk": "-dash"}]
        got = self.call("P17.wrong-type", wp.stand_in_ids, json.dumps({"schema": 1, "walks": [ok] + wrong + [
            {"walk": "walk-last"}]}).encode())
        self.assertEqual(got, ["walk-ok", "walk-last"], "P17.wrong-type: stand_in_ids keeps walk ids only")
        for label, raw in (("not JSON", b"{"), ("not UTF-8", b"\xff\xfe"), ("a top-level list", b"[]"),
                           ("walks an object", b'{"walks": {"walk": "walk-ok"}}'), ("walks null", b'{"walks": null}'),
                           ("no walks", b'{"schema": 1}'), ("a duplicate key", b'{"walks": [], "walks": []}')):
            self.assertEqual(self.call("P17.wrong-type", wp.stand_in_ids, raw), [],
                             f"P17.wrong-type: stand_in_ids of {label}")
        # coverage(): an entry whose walk id is no string is reported as "entry <i>", never by the value
        design, specs = self.plan("P17.wrong-type")
        other = next(s for s in specs if (s["arm"], s["model"]) != design["every_wording"])
        entries = [entry(other, walk) for walk in (None, ["walk-l"], {"walk": "walk-d"})]
        bare = {k: v for k, v in entry(other, "x").items() if k != "walk"}
        got = self.cover("P17.wrong-type", entries + [bare], specs, design)
        self.assertEqual(got["covered"], {}, "P17.wrong-type: nothing covered")
        self.assertEqual([w for w, _ in got["outside"]], ["entry 0", "entry 1", "entry 2", "entry 3"],
                         "P17.wrong-type: labelled by position")


class P18Pending(Base):
    """Batch-8 review finding 1 and the batch-8 fix ruling (glitch-06, 14 Oct 2026; CP6: "Every walk is graded but
    never counted"): a walk covers its spec only when graded true, or a pending walk that a verified graded-true
    regrade supersedes; every other registered walk is reported with why and never counted, and a missing or
    unreadable grade.json fails closed. The reviewer's witness is the arm-G entry that used to cover its spec."""
    CLAUSE = "P18.pending"

    PENDING = {"graded": False, "status": "pending-native-reader",
               "why": "not graded, because its native cross-check is pending: a stand-in"}

    def test_a_pending_walk_covers_nothing(self):
        design, specs = self.plan("P18.pending")
        spec = next(s for s in specs if s["arm"] == "G")
        got = self.cover("P18.pending", [entry(spec, "g-pending-1")], specs, design)
        self.assertEqual(list(got["covered"]), [self.key(spec, design)], "P18.pending: the control covers its spec")
        self.assertEqual(got["uncounted"], [], "P18.pending")
        wp = self.wp("P18.pending")
        got = wp.coverage([entry(spec, "g-pending-1")], specs, design, {"g-pending-1": "pending"})
        self.assertEqual(got["covered"], {}, "P18.pending: an uncounted walk covers nothing")
        self.assertEqual(got["uncounted"], [("g-pending-1", "pending")], "P18.pending: and is reported with why")
        self.assertIn(spec, got["missing"], "P18.pending: its spec stays missing")
        walks = {"g-pending-1": json.dumps(self.PENDING), "g-ungraded-2": json.dumps({"graded": False, "why": "x"}),
                 "g-garbled-3": "{not json", "g-missing-4": None, "g-list-5": "[]"}
        base = self.rehearsals([entry(spec, w) for w in walks], graded=False)
        for walk, text in walks.items():
            (base / walk).mkdir()
            if text is not None:
                (base / walk / "grade.json").write_text(text)
        code, out = self.cli("P18.pending", ["--coverage", "--require-complete", "--base", str(base)])
        self.assertEqual(code, 1, f"P18.pending: no graded walk, the spec is missing: {out[-300:]}")
        self.assertRegex(out, rf"(?m)^missing  {re.escape(self.sline(spec))}$", "P18.pending")
        for walk, why in (("g-pending-1", "pending"), ("g-ungraded-2", "not graded"),
                          ("g-garbled-3", "grade unreadable"), ("g-missing-4", "grade unreadable"),
                          ("g-list-5", "grade unreadable")):
            self.assertRegex(out, rf"(?m)^{why}, not counted: walk '{walk}': only a graded walk covers its spec$",
                             f"P18.pending: {walk} is reported, fail closed")
        (base / "g-pending-1" / "regrade.json").write_text('{"graded": true}\n')
        code, out = self.cli("P18.pending", ["--coverage", "--base", str(base)])
        self.assertIn("pending, not counted: walk 'g-pending-1'", out,
                      "P18.pending: a regrade that does not re-derive supersedes nothing")
        (base / "g-ungraded-2" / "grade.json").write_text(GRADED)
        checked(base / "g-ungraded-2")                          # BOOTSTRAP B5
        code, out = self.cli("P18.pending", ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P18.pending: {out[-300:]}")
        self.assertRegex(out, rf"(?m)^covered  {re.escape(self.sline(spec))} by g-ungraded-2$",
                         "P18.pending: the graded walk covers the spec alone")


class P19RunArms(Base):
    """Lane pf1-l1-freeze-gates (pre-freeze review 1, MAJOR 4 part 3): --require-run-arms requires every arm the
    freeze runs and records each deferred arm (the draft's deferred_arms), per arm and model; coverage_report is the
    --coverage reading freeze.py runs in process. Written so the generated sweep binds the new lines."""
    CLAUSE = "P19.run-arms"

    def test_the_freeze_requires_the_arms_it_runs(self):
        wp = self.wp(self.CLAUSE)
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        got = self.call(self.CLAUSE, wp.deferred_arms)
        self.assertEqual(got, {"G": draft["deferred_arms"]["G"]}, "P19.run-arms: the draft defers arm G")
        for name, edit, want in (("running", lambda d: d["deferred_arms"]["G"].update(status="running"), {}),
                                 ("not a dict", lambda d: d["deferred_arms"].update(G="deferred"), {}),
                                 ("absent", lambda d: d.pop("deferred_arms"), {}),
                                 ("null", lambda d: d.update(deferred_arms=None), {})):
            study = self.study_copy()
            self.edit_draft(study, edit)
            self.assertEqual(self.call(self.CLAUSE, wp.deferred_arms, study), want, f"P19.run-arms: {name}")
        design, specs = self.plan(self.CLAUSE)
        missing = [{"arm": "A", "model": "m"}, {"arm": "G", "model": "n"}]
        self.assertEqual(self.call(self.CLAUSE, wp.run_arm_gaps, {"missing": missing}, {"G": {}}), missing[:1],
                         "P19.run-arms: a deferred arm's gap is not required")
        self.assertEqual(self.call(self.CLAUSE, wp.run_arm_gaps, {"missing": missing}, {}), missing,
                         "P19.run-arms: with no arm deferred every gap is required")
        g = [s for s in specs if s["arm"] == "G"]
        g_models = list(dict.fromkeys(s["model"] for s in g))
        lines = self.call(self.CLAUSE, wp.deferred_lines, {"missing": g[:1]}, specs, {"G": {}})
        want = []
        for model in g_models:
            n = sum(1 for s in g if s["model"] == model)
            gap = 1 if model == g[0]["model"] else 0
            want.append(f"deferred arm G, {model}: {n - gap} of {n} required walks covered, {gap} missing; recorded, "
                        f"not required at this freeze (the draft's deferred_arms); complete coverage is a "
                        f"precondition of its later go (--require-complete)")
        self.assertEqual(lines, want, "P19.run-arms: one line per deferred arm and model")
        self.assertEqual(self.call(self.CLAUSE, wp.deferred_lines, {"missing": []}, specs, {}), [],
                         "P19.run-arms: no line for an arm that runs")
        full = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs)])
        rep = self.call(self.CLAUSE, wp.coverage_report, full)
        self.assertIsInstance(rep, dict, "P19.run-arms: coverage_report returns the reading")
        self.assertEqual((rep["got"]["missing"], rep["specs"], len(rep["entries"]), sorted(rep["deferred"])),
                         ([], specs, len(specs), ["G"]), "P19.run-arms: coverage_report on a full register")
        study = self.study_copy()
        self.edit_draft(study, lambda d: d["deferred_arms"]["G"].update(status="running"))
        rep = self.call(self.CLAUSE, wp.coverage_report, full, study)
        self.assertEqual(rep.get("deferred") if isinstance(rep, dict) else rep, {},
                         "P19.run-arms: coverage_report reads the study it is given")
        live = self.call(self.CLAUSE, wp.coverage_report)
        self.assertIsInstance(live, dict, "P19.run-arms: coverage_report returns the reading")
        import walk_register as wr
        self.assertEqual(len(live["entries"]), len(wr.registered(wr.REHEARSALS)),
                         "P19.run-arms: with no base, the study's own register")
        no_g = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs) if s is not g[0]])
        code, out = self.cli(self.CLAUSE, ["--coverage", "--require-run-arms", "--base", str(no_g)])
        self.assertEqual(code, 0, f"P19.run-arms: a deferred arm's gap alone exits 0: {out[-300:]}")
        self.assertEqual(out.splitlines()[-1], "ok: every required walk of the arms the freeze runs is covered",
                         "P19.run-arms")
        for line in want:
            self.assertIn(line, out, "P19.run-arms: the deferred arm is printed")
        a_spec = next(s for s in specs if s["arm"] == "A")
        no_a = self.rehearsals([entry(s, f"walk-{i}") for i, s in enumerate(specs) if s is not a_spec])
        code, out = self.cli(self.CLAUSE, ["--coverage", "--require-run-arms", "--base", str(no_a)])
        self.assertEqual(code, 1, f"P19.run-arms: a gap in arm A exits 1: {out[-300:]}")
        self.assertEqual(out.splitlines()[-1], "FAIL --require-run-arms: 1 required walk(s) of the arms the freeze "
                         "runs are missing (the lines above name each)", "P19.run-arms")
        for argv in (["--list", "--require-run-arms"], ["--coverage", "--require-run-arms", "--require-complete"]):
            code, out = self.cli(self.CLAUSE, argv + ["--base", str(full)])
            self.assertEqual(code, 2, f"P19.run-arms: {argv} is refused")
            self.assertIn("--require-run-arms goes with --coverage, without --require-complete", out, "P19.run-arms")
        code, out = self.cli(self.CLAUSE, ["--coverage", "--base", str(no_a)])
        self.assertEqual(code, 0, "P19.run-arms: plain --coverage is unchanged")
        self.assertNotIn("--require-run-arms", out, "P19.run-arms: plain --coverage is unchanged")


class P21WitnessRule(unittest.TestCase):
    """The review of lane pf1-walk-cover-strict at ff58e02f, NIT 3: run_witnesses reads a P0.module failure as FAIL,
    never red, and a behavioural assertion carrying the clause as red."""
    CLAUSE = "P21.witness-rule"
    METHOD = "P18Pending.test_a_pending_walk_covers_nothing"

    def stderr(self, body: str) -> str:
        return (f"FAIL: test_a_pending_walk_covers_nothing (__main__.P18Pending.test_a_pending_walk_covers_nothing)\n"
                f"----\nTraceback (most recent call last):\n{body}\n\n"
                f"======================================================================\n")

    def test_a_load_refusal_is_never_red(self):
        rule = globals().get("attributed_red")
        self.assertTrue(callable(rule), "P21.witness-rule: run_witnesses has no attribution rule of its own")
        hollow = self.stderr("AssertionError: unexpectedly None : P0.module P18.pending: walk_plan.py does not exist "
                             "yet or does not load (AssertionError('mutant pending-unread: its anchor occurs 2 times'))")
        real = self.stderr("AssertionError: Regex didn't match: 'missing  G' : P18.pending")
        self.assertFalse(rule(hollow, self.METHOD, "P18.pending"), "P21.witness-rule: P0.module is not red")
        self.assertTrue(rule(real, self.METHOD, "P18.pending"), "P21.witness-rule: a behavioural failure is red")
        self.assertFalse(rule(real, self.METHOD, "P19.run-arms"), "P21.witness-rule: another clause is not red")
        self.assertFalse(rule(real, "P18Pending.other", "P18.pending"), "P21.witness-rule: another test is not red")


class P20Strict(Base):
    """Lane pf1-walk-cover-strict, OD131 (Javier, 25 Oct 2026: "walk-cover strict"): a Claude walk counts as covered
    only if it rechecks clean under the harness as it will be frozen; OD132 (Javier, 26 Oct 2026: "walk-cover-o
    strict"): a Codex walk too. walk_plan names arm A's and arm O's walks strict (strict_walks), on the --coverage road
    and in coverage_report, and pending_walk judges them; an arm G walk carrying the same reason counts as before (arm
    G is deferred and stays as coded). Written so the generated sweep binds the new lines."""
    CLAUSE = "P20.strict"

    def dirty(self, base: Path, walk: str, reasons) -> None:
        path = base / walk / "check.json"
        doc = json.loads(path.read_text())
        doc["checker_reasons"] = list(reasons)
        path.write_text(json.dumps(doc))

    def test_arm_a_and_o_walks_count_only_clean_and_arm_g_as_coded(self):
        import pending_walk
        wp = self.wp(self.CLAUSE)
        design, specs = self.plan(self.CLAUSE)
        a, o, g =(next(s for s in specs if s["arm"] == arm) for arm in ("A", "O", "G"))
        entries = [entry(a, "walk-a"), entry(o, "walk-o"), entry(g, "walk-g"), entry(a, "walk-a2")]
        self.assertEqual(self.call(self.CLAUSE, getattr(wp, "strict_walks", None), entries),
                         ["walk-a", "walk-o", "walk-a2"], "P20.strict: the arm A and O walks, in register order")
        self.assertEqual(self.call(self.CLAUSE, getattr(wp, "strict_walks", None), []), [], "P20.strict")
        hcv = "harness-condition-violated"
        why = f"{getattr(pending_walk, 'STRICT_WHY', 'no strict rule')}: {hcv}"
        base = self.rehearsals(entries[:3])
        for walk in ("walk-a", "walk-o", "walk-g"):
            self.dirty(base, walk, [hcv])
        code, out = self.cli(self.CLAUSE, ["--coverage", "--base", str(base)])
        self.assertEqual(code, 0, f"P20.strict: {out[-300:]}")
        self.assertRegex(out, rf"(?m)^missing  {re.escape(self.sline(a))}$", "P20.strict: the arm A walk covers nothing")
        self.assertRegex(out, rf"(?m)^missing  {re.escape(self.sline(o))}$", "P20.strict: the arm O walk covers nothing")
        self.assertRegex(out, rf"(?m)^covered  {re.escape(self.sline(g))} by walk-g$",
                         "P20.strict: the arm G walk counts as before")
        for walk in ("walk-a", "walk-o"):
            self.assertIn(f"{why}, not counted: walk '{walk}'", out, "P20.strict: and is reported with why")
        rep = self.call(self.CLAUSE, wp.coverage_report, base)
        self.assertEqual(rep["got"]["uncounted"], [("walk-a", why), ("walk-o", why)],
                         "P20.strict: coverage_report applies the rule")
        self.assertEqual(list(rep["got"]["covered"]), [self.key(g, design)], "P20.strict: coverage_report")
        for walk in ("walk-a", "walk-o"):
            self.dirty(base, walk, [])
        code, out = self.cli(self.CLAUSE, ["--coverage", "--base", str(base)])
        for spec, walk in ((a, "walk-a"), (o, "walk-o")):
            self.assertRegex(out, rf"(?m)^covered  {re.escape(self.sline(spec))} by {walk}$",
                             "P20.strict: a clean strict walk covers its spec")
        rep = self.call(self.CLAUSE, wp.coverage_report, base)
        self.assertEqual(rep["got"]["uncounted"], [], "P20.strict: a clean strict walk is counted by coverage_report")
        # last, so each arm witness is red by what the rule does, not by the constant's spelling
        self.assertEqual(getattr(wp, "WALK_COVER_STRICT", {}).get("arms"), ("A", "O"),
                         "P20.strict: OD131 names arm A and OD132 arm O; arm G stays as coded")


BOUND = {"P2.dropped": "P2Dropped.test_a_dropped_task_or_wording_changes_the_figures",
         "P3.halves": "P3Halves.test_every_task_and_half_on_every_planned_model",
         "P4.off-design": "P4OffDesign.test_an_entry_outside_the_plan_is_reported_never_counted",
         "P5.exact-wording": "P5ExactWording.test_the_every_wording_model_needs_each_wording",
         "P6.require": "P6Require.test_require_complete_refuses_a_gap",
         "P7.register-only": "P7RegisterOnly.test_coverage_reads_the_register_and_never_a_walk_folder",
         "P8.spec-checked": "P8SpecChecked.test_a_spec_the_design_refuses_refuses_the_plan",
         "P9.prose": "P9Prose.test_the_printed_plan_and_report_are_clean",
         "P10.every-rule": "P10EveryRule.test_the_every_wording_model_is_one_model_of_the_design",
         "P11.design": "P11Design.test_a_half_or_a_model_moves_the_figures",
         "P12.register": "P12Register.test_a_register_the_register_check_refuses_is_refused",
         "P13.per-model": "P13PerModel.test_each_model_figure_counts_its_own_gaps",
         "P14.cli": "P14Cli.test_the_command_line_exits",
         "P16.scratch-only": "P16ScratchOnly.test_a_path_shaped_walk_id_writes_nothing_outside_the_scratch",
         "P17.wrong-type": "P17WrongType.test_a_field_of_the_wrong_type_is_skipped_never_a_crash",
         "P18.pending": "P18Pending.test_a_pending_walk_covers_nothing",
         "P19.run-arms": "P19RunArms.test_the_freeze_requires_the_arms_it_runs",
         "P20.strict": "P20Strict.test_arm_a_and_o_walks_count_only_clean_and_arm_g_as_coded"}
WITNESSES = {name: (BOUND[clause], clause) for name, (clause, _, _) in mutants().items()}


def child(argv: list, timeout: int = 110):
    """Run this file in its own process; (returncode, outcome dict or None, stdout, stderr)."""
    got = subprocess.run([sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()), *argv],
                         capture_output=True, text=True, timeout=timeout)
    record = re.findall(r"^test_walk_plan outcomes: (\{.*\})$", got.stdout, re.M)
    return got.returncode, (json.loads(record[-1]) if record else None), got.stdout, got.stderr


def attributed_red(stderr: str, method: str, clause: str) -> bool:
    """The bound test failed by an AssertionError carrying its clause token. A failure by P0.module is never red (the
    review of lane pf1-walk-cover-strict at ff58e02f, NIT 3): it means the mutant did not load (an anchor occurring
    other than once, or a module that refuses), so the guard the witness names was never exercised; four witnesses
    went hollow that way after lane pf1-l1-freeze-gates repeated their anchored lines."""
    blocks = re.findall(r"^FAIL: (\w+) \(__main__\.(\w+)\.\w+\)[^\n]*\n(.*?)(?=^=|^Ran |\Z)", stderr, re.M | re.S)
    return any(f"{cls}.{test}" == method and "AssertionError" in body and "P0.module" not in body and
               re.search(r"(?<![\w:.-])" + re.escape(clause) + r"(?![\w.-])", body)
               for test, cls, body in blocks)


def run_witnesses(names) -> int:
    red = 0
    chosen = names or sorted(WITNESSES)
    import mutation_baseline  # lane t104-mutation-baseline: the unmutated selection runs first; a red one refuses (exit 3), nothing counted
    mutation_baseline.require_green("test_walk_plan witnesses", [sys.executable, "-B", "-W", "ignore", str(Path(__file__).resolve()),
                                    *sorted({WITNESSES[x][0] for x in chosen})], timeout=1800, tag="test_walk_plan")
    for name in chosen:
        method, clause = WITNESSES[name]
        code, outcome, stdout, stderr = child(["--mutant", name, method])
        attributed = attributed_red(stderr, method, clause)
        clean = bool(outcome) and outcome["failures"] == [method] and outcome["errors"] == [] \
            and outcome["skipped"] == []
        passed = attributed and clean and code != 0
        print(f"witness {name} -> {method} {clause}: {'RED' if passed else 'FAIL'}", flush=True)
        if not passed:
            print(stdout[-3000:] + stderr[-3000:], flush=True)
            return 1
        red += 1
    print(f"test_walk_plan witnesses: {red} of {len(chosen)} red; registry {len(WITNESSES)}", flush=True)
    return 0


# ---- the generated mutation sweep (review W11C-R1 ruling: bind the class, not only the named guards) ----

# id -> (the mutated line's text in walk_plan.py, stripped; why no assertion can kill it). An entry whose id is no
# longer generated on that exact line is stale and fails the sweep; a listed mutant that is killed fails it too.
EQUIVALENT: dict = {}

NEGATE = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In, ast.Is: ast.IsNot,
          ast.IsNot: ast.Is, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt}
STATEMENTS = (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.Expr, ast.Raise, ast.Return, ast.Continue)


class Mutator(ast.NodeTransformer):
    """Numbers every mutation site in a fixed walk order; with target k, applies site k only."""

    def __init__(self, target=None):
        self.target, self.count, self.sites, self.scope = target, 0, [], False

    def hit(self, node, kind) -> bool:
        if not self.scope:
            return False
        k = self.count
        self.count += 1
        self.sites.append((node.lineno, kind))
        return k == self.target

    def visit_Module(self, node):
        for i, stmt in enumerate(node.body):
            main_guard = isinstance(stmt, ast.If) and "__name__" in ast.unparse(stmt.test)
            if isinstance(stmt, (ast.FunctionDef, ast.ClassDef)) or main_guard:
                self.scope = True
                node.body[i] = self.visit(stmt)
                self.scope = False
        return node

    def visit_JoinedStr(self, node):
        return node                                      # message text: never mutated

    def visit_Constant(self, node):
        if type(node.value) is int and self.hit(node, "int"):
            return ast.copy_location(ast.Constant(node.value + 1), node)
        return node

    def statement(self, node):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            return node                                  # a docstring
        if self.hit(node, "pass"):
            return ast.copy_location(ast.Pass(), node)
        return self.generic_visit(node)

    visit_Assign = visit_AugAssign = visit_AnnAssign = visit_Expr = statement
    visit_Raise = visit_Return = visit_Continue = statement

    def visit_Compare(self, node):
        if len(node.ops) == 1 and type(node.ops[0]) in NEGATE and self.hit(node, "cmp"):
            node.ops = [NEGATE[type(node.ops[0])]()]
            return node
        return self.generic_visit(node)

    def visit_If(self, node):
        for value in (True, False):
            if self.hit(node, f"if-{str(value).lower()}"):
                node.test = ast.Constant(value)
                return node
        return self.generic_visit(node)

    def visit_IfExp(self, node):
        for value in (True, False):
            if self.hit(node, f"if-{str(value).lower()}"):
                node.test = ast.Constant(value)
                return node
        if self.hit(node, "ifexp-body"):
            return node.body
        if self.hit(node, "ifexp-else"):
            return node.orelse
        return self.generic_visit(node)

    def visit_BoolOp(self, node):
        if self.hit(node, "boolop"):
            node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
            return node
        for j in range(len(node.values)):
            if self.hit(node, f"drop{j}"):
                rest = node.values[:j] + node.values[j + 1:]
                return rest[0] if len(rest) == 1 else ast.BoolOp(op=node.op, values=rest)
        return self.generic_visit(node)

    def visit_UnaryOp(self, node):
        if isinstance(node.op, ast.Not) and self.hit(node, "not"):
            return node.operand
        return self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.slice, ast.Slice) and node.slice.upper is not None and self.hit(node, "slice"):
            node.slice.upper = None
            return node
        return self.generic_visit(node)

    def visit_comprehension(self, node):
        for j in range(len(node.ifs)):
            if self.hit(node.ifs[j], f"comp-if{j}"):
                node.ifs = node.ifs[:j] + node.ifs[j + 1:]
                return node
        return self.generic_visit(node)


def generated_mutants(source: str) -> list[dict]:
    """Every mutant's id, its line's text and its index k; the source is made on demand by mutant_source(source, k)."""
    collector = Mutator()
    collector.visit(ast.parse(source))
    lines = source.splitlines()
    out, seen = [], {}
    for k, (lineno, kind) in enumerate(collector.sites):
        n = seen.get((lineno, kind), 0)
        seen[(lineno, kind)] = n + 1
        out.append({"id": f"L{lineno}.{kind}.{n}", "line": lines[lineno - 1].strip(), "k": k})
    return out


def mutant_source(source: str, k: int) -> str:
    tree = Mutator(target=k).visit(ast.parse(source))
    return ast.unparse(ast.fix_missing_locations(tree))


def equivalent_problems(made: list, equivalent: dict) -> list[str]:
    """A listed entry whose id is not generated on exactly its line is stale; an entry without a reason is refused."""
    by_id = {m["id"]: m for m in made}
    bad = []
    for mid, (line, why) in sorted(equivalent.items()):
        if mid not in by_id or by_id[mid]["line"] != line:
            bad.append(f"STALE equivalent entry {mid}: no such mutant on the line {line!r}")
        elif not (isinstance(why, str) and why.strip()):
            bad.append(f"equivalent entry {mid} gives no reason")
    return bad


def run_generated(argv: list) -> int:
    shard, of = 1, 1
    if "--shard" in argv:
        shard, of = (int(x) for x in argv[argv.index("--shard") + 1].split("/"))
        if not 1 <= shard <= of:
            print(f"refusing: shard {shard} of {of}")
            return 2
    source = (HERE / "walk_plan.py").read_text()
    made = generated_mutants(source)
    bad = equivalent_problems(made, EQUIVALENT)
    work = Path(tempfile.mkdtemp(prefix="w11c-sweep-"))
    try:
        armed = work / "unmutated.py"
        armed.write_text(ast.unparse(ast.parse(source)))
        code, outcome, stdout, stderr = child(["--mutant-source", str(armed)])
        if code != 0 or not outcome or outcome["failures"] or outcome["errors"]:
            print("FAIL the unmutated module, re-emitted, does not pass: the sweep is not armed")
            print(stdout[-2000:] + stderr[-2000:])
            return 1
        chosen = [m for i, m in enumerate(made) if i % of == shard - 1]
        if "--only" in argv:                   # one or more ids, comma-separated: to read one mutant's run
            only = set(argv[argv.index("--only") + 1].split(","))
            chosen = [m for m in made if m["id"] in only]
        killed = equivalent = 0
        for m in chosen:
            path = work / "mutant.py"
            path.write_text(mutant_source(source, m["k"]))
            try:
                code, outcome, stdout, stderr = child(["--mutant-source", str(path), "--failfast"], timeout=105)
            except subprocess.TimeoutExpired:
                code, outcome = None, None
            by_assertion = code not in (0, None) and bool(outcome) and bool(outcome["failures"]) \
                and outcome["errors"] == []
            survived = code == 0
            if m["id"] in EQUIVALENT:
                verdict = "EQUIVALENT" if survived else "KILLED-BUT-LISTED"
                equivalent += survived
                if not survived:
                    bad.append(f"{m['id']} is listed EQUIVALENT and is killed; remove the entry")
            elif by_assertion:
                verdict = "KILLED"
                killed += 1
            else:
                verdict = "SURVIVED" if survived else "ERROR"
                bad.append(f"{m['id']} ({m['line']!r}) {verdict.lower()}: "
                           f"{(outcome or {}).get('errors') or 'no failing assertion'}")
            print(f"mutant {m['id']} {verdict}: {m['line'][:90]}", flush=True)
            if "--only" in argv and verdict != "KILLED":
                print(stdout[-2500:] + stderr[-2500:], flush=True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    for line in bad:
        print(f"FAIL {line}")
    print(f"test_walk_plan generated mutants: shard {shard} of {of}, {len(chosen)} run of {len(made)} generated; "
          f"{killed} killed by an assertion, {equivalent} equivalent as listed, {len(bad)} failing", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    if "--witnesses" in sys.argv:
        raise SystemExit(run_witnesses(sys.argv[sys.argv.index("--witnesses") + 1:]))
    if "--generated-mutants" in sys.argv:
        raise SystemExit(run_generated(sys.argv[sys.argv.index("--generated-mutants") + 1:]))
    if "--mutant" in sys.argv:
        index = sys.argv.index("--mutant")
        SELECTED = sys.argv[index + 1]
        if SELECTED not in WITNESSES:
            raise SystemExit(f"unknown mutant {SELECTED!r}")
        del sys.argv[index:index + 2]
    if "--mutant-source" in sys.argv:
        index = sys.argv.index("--mutant-source")
        MUTANT_SOURCE = sys.argv[index + 1]
        del sys.argv[index:index + 2]
    failfast = "--failfast" in sys.argv               # the sweep: the first failing test decides the verdict
    if failfast:
        sys.argv.remove("--failfast")
    result = unittest.main(verbosity=2, exit=False, failfast=failfast).result
    ids = lambda pairs: [t.id().removeprefix("__main__.").split(" ")[0] for t, _ in pairs]  # noqa: E731
    print(f"test_walk_plan: {result.testsRun} run, {len(result.failures)} failures, "
          f"{len(result.errors)} errors, {len(result.skipped)} skipped")
    print("test_walk_plan outcomes: " + json.dumps({"failures": ids(result.failures), "errors": ids(result.errors),
                                                    "skipped": ids(result.skipped)}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
