#!/usr/bin/env python3
"""Lane vendor-admission T4 P0b (lane-reports/vendor-T4-PLAN.md v4 section 9, R-4, ruled READY by glitch-b5 on Sat
17 Oct 2026): a codex or gemini row whose model has no routing pin refuses by name, never with a bare KeyError.

  PV-named    walk_builders.production_builders()["pin_for"] (walk_builders.py:939-940, batch.expected_pin over the
              committed routing.json) on the committed draft's first claude-code row gets its pin. A table with no
              block for the harness at all, and one whose block lacks the model, raise batch.PinProfileMissing for
              the first codex row (arm O) and first gemini row (arm G), naming the harness and the model and that CP5
              registers it. Round 17 B7 (R4 of RULINGS-codex2-signin-road-2026-10-18.md, which moves this
              assertion): on the committed table, which now holds R4's profiles, the first codex and gemini rows get
              exactly R4's profile as their pin (codex bypass 0.162.1, gemini yolo 0.64.0).
  PV-witness  batch.py compiled in memory with expected_pin's bare lookup restored goes red.

CP5 registers the O and G pin_profiles under its rate-limit and spend-cap rules (R-4); round 17 B7 added them (R4);
nothing here adds one. No take, model, container or network.
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import batch  # noqa: E402
import routing  # noqa: E402
import walk_builders  # noqa: E402

ROWS = json.loads((HERE / "prereg-draft.json").read_text())["rows"]
# R4 (round 17 B7): the profile each vendor row's pin must be on the committed table, typed once from the ruling.
R4 = {"codex": {"permission_mode": "bypass", "version": "0.162.1"},
      "gemini": {"permission_mode": "yolo", "version": "0.64.0"}}


def first(harness: str) -> dict:
    return next(r for r in ROWS if r["agent"]["harness"] == harness)


def named_problems(mod) -> list:
    out = []
    table = routing.load_table()
    pin_for = walk_builders.production_builders()["pin_for"]
    if mod is not batch:
        pin_for = (lambda row: mod.expected_pin(row, table))
    cc = first("claude-code")
    if pin_for(cc) != dict(table["pin_profiles"]["claude-code"][cc["model"]], model=cc["model"], harness="claude-code"):
        out.append("the claude-code row's pin changed")
    tables = {"the committed table": table,
              "no block for the harness": dict(table, pin_profiles={"claude-code": table["pin_profiles"]["claude-code"]}),
              "a block without the model": dict(table, pin_profiles=dict(table["pin_profiles"],
                                                                         codex={"synthetic-model": {}},
                                                                         gemini={"synthetic-model": {}}))}
    for harness in ("codex", "gemini"):
        r = first(harness)
        for name, t in tables.items():
            call = pin_for if name == "the committed table" else (lambda row, t=t: mod.expected_pin(row, t))
            try:
                got = call(r)
                if name == "the committed table":   # R4 (round 17 B7): the registered profile, exactly
                    if got != dict(R4[harness], model=r["model"], harness=harness):
                        out.append(f"{harness} on {name}: the pin is {got}, not R4's profile")
                else:
                    out.append(f"{harness} on {name}: a pin was returned: {got}")
            except getattr(mod, "PinProfileMissing", ()) as e:
                if name == "the committed table":
                    out.append(f"{harness} on {name}: R4's profile is refused: {e}")
                    continue
                want = (f"routing.json's pin_profiles hold no {harness}/{r['model']} profile; CP5 registers it")
                if str(e) != want:
                    out.append(f"{harness} on {name}: the refusal reads {str(e)!r}, not {want!r}")
                if not isinstance(e, KeyError):
                    out.append(f"{harness} on {name}: the refusal is no longer a KeyError for its callers")
            except Exception as e:  # noqa: BLE001 - a bare KeyError is the failure PV-named names
                out.append(f"{harness} on {name}: {type(e).__name__} {e!s}, not a named refusal")
    return out


class PinForVendor(unittest.TestCase):
    def test_pv_named_a_vendor_row_without_a_pin_refuses_by_name(self):
        self.assertEqual(named_problems(batch), [])


BARE = '    return dict(table["pin_profiles"][harness][row["model"]], model=row["model"], harness=harness)\n'


def mutant() -> types.ModuleType:
    src = Path(batch.__file__).read_text(encoding="utf-8")
    start = src.index("def expected_pin(")
    end = src.index("\n\n\n", start)
    body = src[start:end]
    doc = body.index('"""', body.index('"""') + 3) + 3
    src = src[:start] + body[:doc] + "\n    harness = row[\"agent\"][\"harness\"]\n" + BARE.rstrip("\n") + src[end:]
    m = types.ModuleType("batch_p0b_witness")
    m.__file__ = batch.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src, batch.__file__ + " (witness)", "exec"), m.__dict__)  # noqa: S102
    finally:
        sys.modules.pop(m.__name__, None)
    return m


class Witness(unittest.TestCase):
    def test_pv_witness_the_bare_lookup_restored_goes_red(self):
        self.assertNotEqual(named_problems(mutant()), [], "the bare-lookup witness stayed green")


if __name__ == "__main__":
    unittest.main()
