#!/usr/bin/env python3
"""Lane vendor-admission T4 P4 (lane-reports/vendor-T4-PLAN.md v4 sections 1b, 2, 6 and 9, ruled READY by glitch-b5 on
Sat 17 Oct 2026, on Javier's typed word "vendor-t4: yes"; R-2: session binding option (a); glitch-b5 round 12): the
vendor session store and the session binding's legs, read by the checker from the take's own records.

  P4-store    check_take.vendor_session_store_problems: session-store.json of the vendor's closed shape (harness,
              root, listings after every turn and at publish, one sweep per turn, the drive's two counts); the take's
              own native session derived by the checker from the publish listing with the drive's own locator and the
              CLI's session id (codex: the whole thread id in rollout-<time>-<id>.jsonl; gemini: its first 8
              characters in session-<minute>-<8>.jsonl), and found in every listing; every listing holding only it and
              every sweep finding no session but it, re-derived, never the drive's verdict (the own path admitted only
              with the harness's own shape and the CLI's session id, as Claude Code's sweep admits it; review d-7c774ad
              finding 2); the counts the checker's own. Each F3 case adds exactly its nested-agent lines.
  P4-binding  check_take.vendor_session_binding_problems, plan section 2's legs on the CLI's own bytes: leg 1 (turn
              1's launch resumes nothing, every later turn's exactly the CLI's id), leg 2 (that one id in every
              envelope and the last retained snapshot), leg 3 (the snapshot holds one interaction per turn stream).
              Each F3 case adds exactly its session-binding lines.
  P4-entry    through the entry (check4_vendor and check4_walk_vendor): a clean take routes no store or binding
              reason; a store case routes nested-agent, a binding case and leg 5's project name from another commit
              (a session id that is not the row commit's) route session-binding.
  P4-fixture  the fixture writer's expected mounts are check_take.sweep_expected's.
  P4-witness  check_take.py compiled in memory with an extra listing entry admitted, a turn-2 argv resuming another
              id admitted, an extra native interaction admitted, a project name from another commit admitted, the
              store unread, the derived session not bound to the CLI's id, the snapshot's id unread, the envelopes'
              ids unread, the turn-1 resume admitted, the sweeps unread, the counts trusted and the own path admitted
              on its path alone: each goes red.

Fakes and synthetic strings only, inside test_box_integration's process guard with test_drive_loop's checker world:
no take, model, vendor, network, Docker, credential or holdout.
"""

from __future__ import annotations

import collections
import json
import sys
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
import vendor_check_fixtures as vcf  # noqa: E402

HARNESSES = tve.HARNESSES
OTHER = "0badc0de-0000-4000-8000-00000000beef"          # another vendor session id (synthetic)


def setUpModule():
    tbi.setUpModule()


def tearDownModule():
    tbi.tearDownModule()


def tags(lines) -> collections.Counter:
    return collections.Counter(p.split("] ")[0][1:] for p in lines)


# ---- the F3 edits ---------------------------------------------------------------------------------------------------
def store_edit(fn):
    """A folder edit: session-store.json read, changed by fn(doc, harness), written back."""
    def edit(path, harness):
        f = path.parent / "session-store.json"
        doc = json.loads(f.read_text())
        fn(doc, harness)
        f.write_text(json.dumps(doc))
    return edit


def other_session(harness) -> str:
    rel = vcf.NATIVE_REL[harness]
    return rel.replace(vcf.CODEX_TID, OTHER) if harness == "codex" else rel.replace(vcf.GEMINI_SID[:8], OTHER[:8])


def extra_session(doc, harness):
    doc["listings"][-1]["entries"].append([other_session(harness), "file"])


def renamed_session(doc, harness):
    for x in doc["listings"]:
        x["entries"] = [[other_session(harness) if rel == vcf.NATIVE_REL[harness] else rel, kind]
                        for rel, kind in x["entries"]]


def linked(doc, harness):
    doc["listings"][-1]["entries"].insert(0, [f"{vcf.STORE_ROOTS[harness]}/elsewhere", "link"])


STORE_CASES = {
    # name: (folder edit (path, harness), the nested-agent lines it adds, by id: pre-freeze review 2, MAJOR 1 splits
    # nested-agent-session, what the agent's uid produces, from nested-agent, what only the driver or runtime does)
    "no store record": (lambda path, harness: (path.parent / "session-store.json").unlink(), {"nested-agent": 1}),
    "a key off the shape": (store_edit(lambda d, h: d.update(extra=1)), {"nested-agent": 1}),
    "another harness's record": (store_edit(lambda d, h: d.update(harness="claude-code")), {"nested-agent": 1}),
    "another store root": (store_edit(lambda d, h: d.update(root="elsewhere")), {"nested-agent": 1}),
    "a turn's listing missing": (store_edit(lambda d, h: d["listings"].pop(0)), {"nested-agent": 1}),
    "a turn's sweep missing": (store_edit(lambda d, h: d["sweeps"].pop()), {"nested-agent": 1}),
    "an extra session in the store at publish": (store_edit(extra_session), {"nested-agent-session": 1}),
    "the store's session named for another id": (store_edit(renamed_session), {"nested-agent-session": 1}),
    "a link in the store": (store_edit(linked), {"nested-agent-session": 1}),
    "a listing refused": (store_edit(lambda d, h: d["listings"].__setitem__(1, {"at": "post-2", "refused": "x"})), {"nested-agent-session": 1}),
    "a turn's listing without the session": (store_edit(lambda d, h: d["listings"][0].update(entries=[])), {"nested-agent-session": 1}),
    "a sweep finding another session": (store_edit(lambda d, h: d["sweeps"][0]["files"].append(
        [f"{vcf.CONFIG_MOUNT}/{other_session(h)}", h, OTHER])), {"nested-agent-session": 1}),
    # round 13, review d-7c774ad finding 2: the own path is admitted only as [path, the harness's shape, the CLI's id]
    "the own path swept with another shape": (store_edit(lambda d, h: d["sweeps"][0]["files"][0].__setitem__(
        1, "gemini" if h == "codex" else "codex")), {"nested-agent-session": 1}),
    "the own path swept as a claude session": (store_edit(lambda d, h: d["sweeps"][0]["files"][0].__setitem__(
        1, "claude")), {"nested-agent-session": 1}),
    "the own path swept with another session id": (store_edit(lambda d, h: d["sweeps"][1]["files"][0].__setitem__(
        2, OTHER)), {"nested-agent-session": 1}),
    "a sweep's mounts widened": (store_edit(lambda d, h: d["sweeps"][0]["mounts"].append("/srv")), {"nested-agent": 1}),
    "a sweep refused": (store_edit(lambda d, h: d["sweeps"].__setitem__(0, {"at": "post-1", "refused": "x"})), {"nested-agent-session": 1}),
    "the record's nested CLI count": (store_edit(lambda d, h: d.update(nested_cli_calls=1)), {"nested-agent": 1}),
    "the record's unread line count": (store_edit(lambda d, h: d.update(unread_stream_lines=2)), {"nested-agent": 1}),
}


def journal_edit(k, fn):
    def edit(path, harness):
        j = path.parent / f"turn-{k}.jsonl.launch.json"
        doc = json.loads(j.read_text())
        doc["argv"] = fn(doc["argv"], harness, path)
        j.write_text(json.dumps(doc))
    return edit


def resumed_other(argv, harness, path):
    token = tbi_ct().VENDOR_RESUME_TOKENS[harness]
    return [OTHER if i and argv[i - 1] == token else a for i, a in enumerate(argv)]


def resumed_on_turn_one(argv, harness, path):
    """Turn 1's launch rebuilt by the adapter as a resume of the CLI's own session, for the same line and model."""
    import codex_adapter
    import gemini_adapter
    adapter = codex_adapter if harness == "codex" else gemini_adapter
    vid = vcf.CODEX_TID if harness == "codex" else vcf.GEMINI_SID
    sent = json.loads(path.read_text().splitlines()[0])["sent"]
    model = argv[argv.index(adapter.MODEL_FLAG) + 1]
    return adapter.argv(sent, model=model, mode=vcf.MODES[harness], session_id=vid, first=False)


def envelope_other(path, harness):
    lines = [json.loads(x) for x in path.read_text().splitlines()]
    lines[1]["vendor_session_id"] = OTHER
    path.write_text("".join(json.dumps(x) + "\n" for x in lines))


def snapshot_other(parts):
    if "rollout" in parts:
        parts["meta"].update(id=OTHER, session_id=OTHER)
    else:
        parts["meta"]["sessionId"] = OTHER


def extra_interaction(parts):
    (tvb.codex_extra_turn if "rollout" in parts else tvb.gemini_extra_interaction)(parts)


BINDING_CASES = {
    # name: (parts edit, folder edit (path, harness), session-binding lines it adds)
    "turn 2 resumes another session": (None, journal_edit(2, resumed_other), 1),
    "turn 1 resumes a session": (None, journal_edit(1, resumed_on_turn_one), 1),
    "an envelope naming another vendor id": (None, envelope_other, 1),
    "a snapshot of another session": (snapshot_other, None, 1),
    "an extra native interaction": (extra_interaction, None, 1),
}

_CT = {}


def tbi_ct():
    return _CT["ct"]


def built(mod, harness, parts_edit=None, folder_edit=None, road="take"):
    t = tve.take_for(mod, harness, road)
    path = t.build(parts_edit, (lambda p: folder_edit(p, harness)) if folder_edit else None)
    return t, path


def store_problems(mod) -> list:
    out = []
    for harness in HARNESSES:
        _, path = built(mod, harness)
        clean = mod.vendor_session_store_problems(path, harness)
        if clean:
            out.append(f"{harness} clean: {clean}")
        for name, (edit, n) in STORE_CASES.items():
            _, path = built(mod, harness, folder_edit=edit)
            got = mod.vendor_session_store_problems(path, harness)
            if tags(got) != collections.Counter(n):
                out.append(f"{harness} {name}: {got}")
    return out


def binding_problems(mod) -> list:
    out = []
    for harness in HARNESSES:
        _, path = built(mod, harness)
        clean = mod.vendor_session_binding_problems(path, harness)
        if clean:
            out.append(f"{harness} clean: {clean}")
        for name, (parts_edit, folder_edit, n) in BINDING_CASES.items():
            _, path = built(mod, harness, parts_edit, folder_edit)
            got = mod.vendor_session_binding_problems(path, harness)
            if tags(got) != collections.Counter({"session-binding": n}):
                out.append(f"{harness} {name}: {got}")
    return out


def entry_problems(mod) -> list:
    out = []
    cases = (("an extra session in the store at publish", STORE_CASES["an extra session in the store at publish"][0],
              None, "nested-agent-session"),
             ("turn 2 resumes another session", BINDING_CASES["turn 2 resumes another session"][1], None,
              "session-binding"),
             ("an extra native interaction", None, extra_interaction, "session-binding"))
    for harness in HARNESSES:
        for road in ("take", "walk"):
            for name, folder_edit, parts_edit, want in cases:
                t, path = built(mod, harness, parts_edit, folder_edit, road)
                got = tve.outcome(tve.entry_call, mod, t, path, road)
                if got[0] != "ok" or want not in got[1]["reasons"]:
                    out.append(f"{harness} {road} {name}: {str(got)[:300]}")
        # leg 5: a session id that is not the row commit's (so its project name is another commit's)
        t = tvb.Take(mod, harness, tvb.design_for(mod, harness), sid=tvb.SID_OTHER)
        got = tve.outcome(tve.entry_call, mod, t, t.build(), "take")
        if got[0] != "ok" or "session-binding" not in got[1]["reasons"]:
            out.append(f"{harness} leg 5, a project name from another commit: {str(got)[:300]}")
    return out


class P4Session(unittest.TestCase):
    def setUp(self):
        self.world = tve.world()
        _CT["ct"] = self.world.__enter__()

    def tearDown(self):
        self.world.__exit__(None, None, None)

    def test_p4_the_store_is_read_and_rederived(self):
        self.assertEqual(store_problems(tbi_ct()), [])

    def test_p4_the_binding_legs_on_the_clis_bytes(self):
        self.assertEqual(binding_problems(tbi_ct()), [])

    def test_p4_the_entries_route_the_store_and_binding_reasons(self):
        self.assertEqual(entry_problems(tbi_ct()), [])

    def test_p4_the_fixture_mounts_are_the_checkers(self):
        self.assertEqual(vcf.session_store("codex", [1])["sweeps"][0]["expected"],
                         tbi_ct().sweep_expected(vcf.RUN_TREE))
        self.assertEqual(vcf.CONFIG_MOUNT, tbi_ct().SWEEP_CONFIG_MOUNT)
        self.assertEqual(vcf.STORE_ROOTS, {h: tbi_ct().SESSION_STORE_ROOTS[h] for h in HARNESSES})


P4_WITNESSES = {
    "an extra listing entry admitted": (("        bad = vendor_store_violations(x[\"entries\"], harness, own)\n",
                                         "        bad = []\n"), store_problems),
    "a turn-2 argv resuming another id admitted": (("        if k > 1 and resumed != vid:\n", "        if False:\n"),
                                                   binding_problems),
    "an extra native interaction admitted": (("    if n != len(envelopes):\n", "    if False:\n"), binding_problems),
    "a project name from another commit admitted": ((
        "        problems += vendor_take_binding_problems(task_id, half_name, row_index, sid)\n", "        pass\n"),
        entry_problems),
    "the store unread": (("        problems += vendor_session_problems(path, harness)\n", ""), entry_problems),
    "the derived session not bound to the CLI's id": ((
        "    return VENDOR_SESSION_LOCATORS[harness](lister, vendor_id)\n",
        "    return next(rel for rel, kind in entries if kind == \"file\")\n"), store_problems),
    "the snapshot's id unread": (("    if snap_ids != {vid}:\n", "    if False:\n"), binding_problems),
    "the envelopes' ids unread": (("    if ids != {vid}:\n", "    if False:\n"), binding_problems),
    "the turn-1 resume admitted": (("        if k == 1 and token in argv:\n", "        if False:\n"), binding_problems),
    "the sweeps unread": (("        out += [f\"[{sweep_finding_id(v, driver)}] the sweep at {x['at']}: {v}\" for v in seen][:5]\n", ""),
                          store_problems),
    "the counts trusted": (("    if (doc[\"nested_cli_calls\"], doc[\"unread_stream_lines\"]) != (calls, len(unread)):\n",
                            "    if False:\n"), store_problems),
    "the own path admitted on its path alone": (("if f != [own_path, harness, vid]]", "if f[0] != own_path]"),
                                                store_problems),
}


class P4Witnesses(unittest.TestCase):
    def test_p4_witness_each_guard_dropped_goes_red(self):
        for name, (edit, check) in P4_WITNESSES.items():
            with self.subTest(witness=name), tve.world() as ct:
                _CT["ct"] = ct
                self.assertEqual(check(ct), [], f"{name}: its check is red on check_take.py")
                mutant = tcb.witness_module((edit,))
                _CT["ct"] = mutant
                with mock.patch.dict(sys.modules, {"check_take": mutant}):
                    self.assertNotEqual(check(mutant), [], f"witness {name} stayed green")


if __name__ == "__main__":
    unittest.main()
