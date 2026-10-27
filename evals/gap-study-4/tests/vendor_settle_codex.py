#!/usr/bin/env python3
"""Lane vendor-settle: the Codex rows' settlement cases (stage K made this module empty; stage C, the Codex builder, is
its only writer). tests/test_vendor_check.py imports it and merges its three tables with the other harness's module
(tests/vendor_settle_gemini.py); a key here must be a ("codex", <key>) of check_take.VENDOR_PENDING_ROWS, and no key may
appear in both modules.

  SAME_FIRES   ("codex", key) -> fire(fixture_path) -> list of problems: the row's site (or vendor_check) run on a
               planted copy of the row's RECORDED fixture (tests/vendor_plant.planted); VPSameFires requires a line
               carrying the row's reason, for every SAME row of the live map.
  CLEAN_CASES  ("codex", key) -> case() -> (got, want): the reader on the unmodified RECORDED copy against the
               independent value the case's own plain-json parser derives; VPSettleCases requires got == want.
  NC_CASES     ("codex", key) -> case() -> list of problems: a NOT COMPARABLE row's partial check on its non-hollow
               plant; VPSettleCases requires a non-empty list whose every line carries the row's reason.

RECORDED folders for this harness: tests/fixtures/recorded-codex-w-o46 (also w-o47, w-o7).

Stage C also runs this file directly (checks.d/vendor-settle-c.txt) for the tests the three tables cannot express:

  C-reach      K's open point 2, ruled by glitch-f1: the clean w-o46 copy's one read-outside-the-checkout event was a
               code-mode tool output whose printed text is a JSON document; read as encoded text, its escaped newlines
               joined a listing of run-tree files into one path outside the run tree (a false event), and an outside
               path after an escaped newline was not seen at all (a blind spot). The rollout's returned tool texts are
               read decoded when they are a JSON object or array (check_take.vendor_codex_returned_documents): the
               clean copy reads no outside path (the test's own count), and an outside path planted after an escaped
               newline in that text fires.

Every case reads the RECORDED folders through scratch copies (vendor_plant.planted); the committed fixtures are never
written. No take, model, container or network.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
import unittest.mock
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
_ADDED = [p for p in (str(HERE), str(HERE / "tests")) if p not in sys.path]
sys.path[:0] = _ADDED
try:
    import check_take as ct  # noqa: E402
    import vendor_plant as vp  # noqa: E402
    # imported here, once, so no test imports a module that edits sys.path (tests leave interpreter state as found)
    import codex_adapter  # noqa: E402,F401
    import run  # noqa: E402,F401
    import walk_regrade  # noqa: E402,F401
    import test_codex_adapter  # noqa: E402,F401
    import test_codex_patch_reads  # noqa: E402,F401
finally:
    for _p in _ADDED:
        sys.path.remove(_p)

O46 = "recorded-codex-w-o46"
O47 = "recorded-codex-w-o47"
O7 = "recorded-codex-w-o7"
LAST_O46 = "session/native-turn-3.jsonl"


def _rollout(folder: Path) -> list:
    """The last retained rollout's records, parsed here with plain json (never a check_take helper)."""
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    name = ledger["native_snapshots"][-1]["file"]
    return [json.loads(x) for x in (folder / "session" / name).read_text(encoding="utf-8").split("\n") if x]


def _cwd(records: list) -> str:
    return records[0]["payload"]["cwd"]


# ---- C-reach: K's open point 2 ---------------------------------------------------------------------------------------
# The code-mode output part of w-o46's native-turn-3 line 16: its text is a JSON document whose "output" lists files of
# the run tree, one per line; in the file the escaped newline is written `\\n`.
LISTING = b"/tmp/run-8617d222\\\\nCLAUDE.md"
OUTSIDE = b"/tmp/run-8617d222\\\\n/tmp/run-0123abcd/notes.md\\\\nCLAUDE.md"


def independent_outside_count(folder: Path) -> int:
    """How many paths of the rollout's code-mode output texts that decode as JSON objects sit outside the run tree, by
    this test's own parse: each such text's string values split on newlines, every line naming /tmp/ checked against
    the session's cwd."""
    records = _rollout(folder)
    cwd = _cwd(records)
    n = 0

    def strings(x):
        if isinstance(x, str):
            yield x
        elif isinstance(x, dict):
            for v in x.values():
                yield from strings(v)
        elif isinstance(x, list):
            for v in x:
                yield from strings(v)
    for r in records:
        p = r["payload"]
        if r["type"] != "response_item" or p.get("type") != "custom_tool_call_output":
            continue
        for part in p["output"]:
            try:
                doc = json.loads(part["text"])
            except ValueError:
                continue
            if not isinstance(doc, (dict, list)):
                continue
            for s in strings(doc):
                for line in s.split("\n"):
                    if line.startswith("/tmp/") and not (line == cwd or line.startswith(cwd + "/")):
                        n += 1
    return n


class CReach(unittest.TestCase):
    def reach(self, plant):
        return ct.vendor_reach(plant.path, "codex", run_tree=ct.vendor_session_cwd(plant.path, "codex"))

    def test_c_reach_the_clean_copy_reads_no_outside_path(self):
        with vp.planted(O46) as plant:
            self.assertEqual(independent_outside_count(plant.folder), 0)
            got = self.reach(plant)
        self.assertEqual(got["outside"], [], got["problems"])
        self.assertEqual([p for p in got["problems"] if p.startswith(f"[{ct.EVENT_OUTSIDE}]")], [])

    def test_c_reach_an_outside_path_after_an_escaped_newline_fires(self):
        with vp.planted(O46, vp.replace_bytes(LAST_O46, LISTING, OUTSIDE)) as plant:
            self.assertEqual(independent_outside_count(plant.folder), 1)
            got = self.reach(plant)
        # one path, read by both legs that judge another take's run tree (the home-and-temp leg and the temp leg), as
        # C's readers count a Claude Code take's
        self.assertTrue(got["outside"], got)
        self.assertTrue(all(x.endswith("/run-0123abcd/notes.md") for x in got["outside"]), got["outside"])


    # ---- stage V ruling (b): a truncated JSON body after the CLI's "Warning: truncated output" header ----------------
    # glitch-f1's ruling on stage C's hand-back: w-o12 losing its false event to C1 is accepted (named in the lane
    # notes); for w-o11, w-o13 and w-o26 the returned text opens with the header and its JSON body was cut, so it does
    # not decode, and an undecodable truncated body is read with its literal backslash-n unescaped before the paths are
    # taken. w-o30's five events name a real temp file outside the run tree and stay.
    def walk_reach(self, walk):
        path = HERE / "rehearsals" / walk / "transcript.jsonl"            # the committed walk, read in place
        return ct.vendor_reach(path, "codex", run_tree=ct.vendor_session_cwd(path, "codex"))

    def test_c_reach_a_truncated_listing_in_the_run_tree_reads_no_outside_path(self):
        for walk in ("w-o11", "w-o13", "w-o26"):
            with self.subTest(walk=walk):
                self.assertEqual(self.walk_reach(walk)["outside"], [])
        self.assertEqual(len(self.walk_reach("w-o30")["outside"]), 5)

    def test_c_reach_an_outside_path_in_a_truncated_body_fires(self):
        head = "Warning: truncated output (original token count: 9000)\nTotal output lines: 40\n\n"
        body = '{"output":"/tmp/run-0123abcd\\nCLAUDE.md\\n/root/secret.txt\\nDEVELOPMENT.md'      # cut mid-document
        got = ct.vendor_codex_returned_documents({"type": "custom_tool_call_output", "output": [
            {"type": "input_text", "text": head + body}]})["output"][0]["text"]
        self.assertIn("\n/root/secret.txt\n", got)
        self.assertNotIn("\\n", got)
        # a text without the header, or a body that decodes, is read as before
        plain = ct.vendor_codex_returned_documents({"output": [{"type": "input_text", "text": body}]})
        self.assertEqual(plain["output"][0]["text"], body)


# ---- the production walk check on a scratch copy ---------------------------------------------------------------------
_REGISTER = HERE / "rehearsals" / "register.json"


def walk_design(plant):
    """The production design a GPT walk is re-checked against (walk_regrade.production_design, its run tree as
    recheck_doc derives it on a machine whose temp root is /tmp), for the scratch copy's walk."""
    import run as run_mod
    import walk_regrade
    walk = plant.folder.name
    entry = [e for e in json.loads(_REGISTER.read_text(encoding="utf-8"))["walks"] if e.get("walk") == walk]
    ledger = json.loads((plant.folder / "driver-ledger.json").read_text(encoding="utf-8"))
    row = dict(run_mod.walk_row(entry[0], ledger), walk=walk, slot=walk)
    return row, walk_regrade.production_design(row, "/tmp/" + ct.neutral_name(ct.walk_session_id(walk)))


def walk_check(plant) -> list:
    """check4_walk_vendor's problems on the scratch copy (the whole production road: vendor_check, the section 1b
    readings and P4's), read as arm O."""
    row, design = walk_design(plant)
    return ct.check4_walk_vendor(plant.path, row["task"], row["half"], plant.folder.name, wording_script=design.script,
                                 arm=row["arm"], design=design)["problems"]


_CLEAN: dict = {}


def clean_check(fixture) -> list:
    """walk_check on the unmodified copy of `fixture`, read once per process."""
    name = vp.fixture_folder(fixture).name
    if name not in _CLEAN:
        with vp.planted(fixture) as plant:
            _CLEAN[name] = walk_check(plant)
    return _CLEAN[name]


def _payload_edit(rel: str, match, change):
    """vp.edit_jsonl on `rel` changing exactly one record: the one `match(record)` selects (more or fewer refuses)."""
    hits = []

    def fn(i, rec):
        if not match(rec):
            return None
        hits.append(i)
        if len(hits) > 1:
            raise vp.PlantRefused(f"{rel}: the plant's record is not one ({hits})")
        out = json.loads(json.dumps(rec))
        change(out)
        return out
    edit = vp.edit_jsonl(rel, fn)

    def checked(folder):
        edit(folder)
        if len(hits) != 1:
            raise vp.PlantRefused(f"{rel}: the plant's record is not one ({hits})")
    return checked


def _is(rec, rtype, **pay) -> bool:
    p = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
    return rec.get("type") == rtype and all(p.get(k) == v for k, v in pay.items())


def _message_with(role, prefix):
    return lambda rec: _is(rec, "response_item", type="message", role=role) and any(
        (c.get("text") or "").startswith(prefix) for c in rec["payload"]["content"])


def _set_part(prefix, fn):
    def change(rec):
        for c in rec["payload"]["content"]:
            if (c.get("text") or "").startswith(prefix):
                c["text"] = fn(c["text"])
    return change


def _nth(rtype, n):
    """A matcher for the n-th (1-based) record of `rtype` in file order (a plant placed past the first record, so a
    reader reading only the first would miss it)."""
    seen = [0]

    def match(rec):
        if rec.get("type") != rtype:
            return False
        seen[0] += 1
        return seen[0] == n
    return match


def _nth_event(etype, n):
    seen = [0]

    def match(rec):
        if not _is(rec, "event_msg", type=etype):
            return False
        seen[0] += 1
        return seen[0] == n
    return match


# The one logical violation each SAME row's firing case plants (design section 2 per row; MAJOR 2 for T-16).
SAME_PLANTS = {
    # T-5: an extra user part beside turn 2's operator line ("skip"); read_rollout skips response_item messages unread.
    "T-5": lambda: _payload_edit(LAST_O46, lambda r: _is(r, "response_item", type="message", role="user") and [
        c.get("text") for c in r["payload"]["content"]] == ["skip"],
        lambda r: r["payload"]["content"].append({"type": "input_text", "text": "Continue with the task."})),
    # T-10: a leak word in the collaboration_mode developer section (no other row reads its words).
    "T-10": lambda: _payload_edit(LAST_O46, _message_with("developer", "<skills_instructions>"),
                                  _set_part("<collaboration_mode>", lambda t: t + " eval")),
    # T-12:instruction-files: the AGENTS.md message names a directory outside the session folder.
    "T-12:instruction-files": lambda: _payload_edit(
        LAST_O46, _message_with("user", ct.CODEX_AGENTS_PREFIX),
        _set_part(ct.CODEX_AGENTS_PREFIX, lambda t: ct.CODEX_AGENTS_PREFIX + "/opt/cfg" + t[t.index("\n"):])),
    # T-12:prompt-snapshot: base_instructions' text emptied, the key kept.
    "T-12:prompt-snapshot": lambda: _payload_edit(LAST_O46, lambda r: r.get("type") == "session_meta",
                                                  lambda r: r["payload"]["base_instructions"].update(text="")),
    # T-14: one word of world_state.agents_md.text changed (the message copy kept).
    "T-14": lambda: _payload_edit(LAST_O46, lambda r: r.get("type") == "world_state",
                                  lambda r: r["payload"]["state"]["agents_md"].update(
                                      text=r["payload"]["state"]["agents_md"]["text"].replace(
                                          "repository orientation", "repository introduction", 1))),
    # T-16: turn 2's turn_context approval_policy "on-request" (a value read_rollout accepts).
    "T-16": lambda: _payload_edit(LAST_O46, _nth("turn_context", 2),
                                  lambda r: r["payload"].update(approval_policy="on-request")),
}
SAME_REASONS = {"T-5": "unknown-harness-origin", "T-10": "leak-in-loaded-context",
                "T-12:instruction-files": "inherited-context", "T-12:prompt-snapshot": "inherited-context",
                "T-14": "checkout-binding", "T-16": "constant-binding"}


def _fire(key):
    def fire(fixture):
        with vp.planted(fixture, SAME_PLANTS[key]()) as plant:
            return walk_check(plant)
    return fire


SAME_FIRES: dict = {("codex", k): _fire(k) for k in SAME_PLANTS}


def _all_strings(node):
    """Every key and string value of parsed JSON, decoded (this test's own walk)."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _all_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _all_strings(v)


def _leak_words(text: str) -> list:
    """The pre-registration draft's leak words found on word boundaries in `text`, lower-cased (read from
    prereg-draft.json here, never through check_take; no excusal is needed for these records)."""
    import re
    words = json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))["leak_words"]
    low = text.lower()
    return [w for w in words if re.search(r"\b" + re.escape(w.lower()) + r"\b", low)]


# ---- clean cases: each SAME reader on the clean w-o46 copy against the test's own reading ---------------------------
def _facts_o46(folder: Path) -> dict:
    """What the clean copy's records say, read here with plain json only."""
    recs = _rollout(folder)
    meta = recs[0]["payload"]
    cwd = meta["cwd"]
    sent = [json.loads(x)["sent"] for x in (folder / "transcript.jsonl").read_text(encoding="utf-8").split("\n") if x]
    user = [c["text"] for r in recs if _is(r, "response_item", type="message", role="user")
            for c in r["payload"]["content"]]
    dev = [c["text"] for r in recs if _is(r, "response_item", type="message", role="developer")
           for c in r["payload"]["content"]]
    ws = [r["payload"]["state"] for r in recs if r["type"] == "world_state"]
    agents = [t for t in user if t.startswith("# AGENTS.md instructions for ")]
    pinned = ct._git_pinned("show", f"{ct._variants.PINNED_TREE}:CLAUDE.md").decode("utf-8")
    tcs = [r["payload"] for r in recs if r["type"] == "turn_context"]
    tss = [r["payload"]["thread_settings"] for r in recs if _is(r, "event_msg", type="thread_settings_applied")]
    return {
        "operator in order": [t for t in user if t in sent] == sent,
        "one AGENTS.md, one environment": (len(agents), sum(t.startswith("<environment_context>") for t in user)) == (
            1, 1),
        "no other user part": all(t in sent or t.startswith(("# AGENTS.md instructions for ", "<environment_context>"))
                                  for t in user),
        "developer tags known": all(t.split(">")[0].lstrip("<") in ct.CODEX_DEVELOPER_SECTIONS for t in dev),
        "no leak word": not _leak_words(" ".join(list(_all_strings([meta, ws])) + dev + agents
                                                 + [t for t in user if t.startswith("<environment_context>")])),
        "agents in cwd": all(t.split("\n")[0].endswith(" " + cwd) for t in agents)
        and all(s["agents_md"]["directory"] == cwd for s in ws),
        "prompt text": bool(meta["base_instructions"]["text"].strip()),
        "agents equal pinned": all(t.split("<INSTRUCTIONS>\n", 1)[1].rsplit("\n</INSTRUCTIONS>", 1)[0].rstrip()
                                   == pinned.rstrip() for t in agents)
        and all(s["agents_md"]["text"].rstrip() == pinned.rstrip() for s in ws),
        "modes": len(tcs) == len(sent) and all(
            (t["approval_policy"], t["sandbox_policy"]["type"]) == ("never", "danger-full-access") for t in tcs)
        and all((s["approval_policy"], s["permission_profile"]["type"]) == ("never", "disabled") for s in tss)
        and len(tss) == 4,
    }


CLEAN_FACTS = {"T-5": ("operator in order", "one AGENTS.md, one environment", "no other user part",
                       "developer tags known"),
               "T-10": ("no leak word",), "T-12:instruction-files": ("agents in cwd",),
               "T-12:prompt-snapshot": ("prompt text",), "T-14": ("agents equal pinned",), "T-16": ("modes",)}


def _read(key, plant):
    p = plant.path
    if key == "T-5":
        return ct.vendor_codex_origin_reads(p)
    if key == "T-10":
        return ct.vendor_codex_loaded_context_reads(p, walk_design(plant)[1].pre)
    if key == "T-12:instruction-files":
        return ct.vendor_codex_instruction_files_reads(p)
    if key == "T-12:prompt-snapshot":
        return ct.vendor_codex_prompt_reads(p)
    if key == "T-14":
        return ct.vendor_codex_instruction_content_reads(p, walk_design(plant)[1])
    if key == "T-16":
        return ct.vendor_codex_recorded_mode_reads(p, walk_design(plant)[1], None)
    raise KeyError(key)


def _clean(key):
    def case():
        with vp.planted(O46) as plant:
            facts = _facts_o46(plant.folder)
            want = [] if all(facts[f] for f in CLEAN_FACTS[key]) else [f"the clean copy's facts differ: {facts}"]
            return _read(key, plant), want
    return case


CLEAN_CASES: dict = {("codex", k): _clean(k) for k in CLEAN_FACTS}


# ---- NOT COMPARABLE partial checks: each non-hollow plant, as glitch-f1's adopted rulings word the test -------------
def _partial(fixture, reader, *edits, patches=()):
    import contextlib
    with contextlib.ExitStack() as stack:
        for target, attr, value in patches:
            stack.enter_context(unittest.mock.patch.dict(target[attr], value))
        plant = stack.enter_context(vp.planted(fixture, *edits))
        if reader is ct.vendor_billing_route_partial:
            return reader(plant.path, "codex", walk_design(plant)[1].pre)
        return reader(plant.path)


def nc_t8() -> list:
    """T-8:file-change: through the settled site, a synthetic stream patch the rollout does not hold and a rename
    (the ruling's two cases, on lane vendor-b23's synthetic take builder)."""
    import tempfile
    sys.path.insert(0, str(HERE / "tests"))
    try:
        import test_codex_patch_reads as tcp
    finally:
        sys.path.remove(str(HERE / "tests"))
    out = []
    for parts in (tcp.take_parts(in_rollout=False), tcp.take_parts(tcp.file_change_item(move_path=tcp.PATH_B))):
        with tempfile.TemporaryDirectory() as tmp:
            got = ct.vendor_file_change_problems(tcp.write_take(parts, Path(tmp)), "codex")
        out += got if got else ["(a T-8 case gave no problem)"]
    return out


NC_PLANTS = {
    "T-12:offered-context": [(O46, ct.vendor_codex_offered_partial, (lambda: _payload_edit(
        LAST_O46, lambda r: r.get("type") == "session_meta",
        lambda r: r["payload"]["runtime_workspace_roots"].append("/root/outside")),), ()),
        # review 0df1437 MINOR 2 (glitch-f1's ruling): session_meta.dynamic_tools (recorder.rs:970-974, absent in all
        # 89 native turns of the 38 walks) names a tool offered to the session
        (O46, ct.vendor_codex_offered_partial, (lambda: _payload_edit(
            LAST_O46, lambda r: r.get("type") == "session_meta",
            lambda r: r["payload"].update(dynamic_tools=[{"name": "web_fetch", "description": "x",
                                                          "inputSchema": {}}])),), ())],
    "T-12:memory": [(O46, ct.vendor_codex_memory_partial, (lambda: _payload_edit(
        LAST_O46, lambda r: r.get("type") == "world_state", lambda r: r["payload"]["state"].update(memories={})),), ()),
                    (O46, ct.vendor_codex_memory_partial, (lambda: _payload_edit(
                        LAST_O46, _message_with("developer", "<skills_instructions>"),
                        lambda r: r["payload"]["content"].append(           # the shape the CLI writes (review NIT 3)
                            {"type": "input_text", "text": "## Memory\n\nYou have access to a memory folder."})),),
                     ())],
    "T-13": [(O46, ct.vendor_codex_checkout_partial, (lambda: _payload_edit(
        LAST_O46, lambda r: r.get("type") == "session_meta", lambda r: r["payload"].update(git=None)),), ()),
             (O46, ct.vendor_codex_checkout_partial, (lambda: _payload_edit(
                 LAST_O46, lambda r: r.get("type") == "session_meta",
                 lambda r: r["payload"]["git"].update(branch="other")),), ())],
    "T-17:billing-route": [
        (O46, ct.vendor_billing_route_partial, (lambda: vp.replace_bytes(
            "environment.json", '  "names_present": [],\n',
            '  "names_present": [{"name": "CODEX_ACCESS_TOKEN", "matched_by": "generic"}],\n'),), ()),
        (O46, ct.vendor_billing_route_partial, (), ((ct._run_take.TAKE_ENV, "codex", {"OPENAI_BASE_URL": "x"}),)),
        (O46, ct.vendor_billing_route_partial, (lambda: _payload_edit(
            LAST_O46, lambda r: r.get("type") == "session_meta", lambda r: r["payload"].update(model_provider="oss")),),
         ()),
        # stage V, glitch-f1's amendment: a non-null credential_source on one vendor turn, and a reported one
        (O46, ct.vendor_billing_route_partial, (lambda: vp.replace_bytes(
            "environment.json", '"n": 2,\n        "recovery": false,\n        "exit": 0,\n        "apiKeySource": null',
            '"n": 2,\n        "recovery": false,\n        "exit": 0,\n        "apiKeySource": "ChatGPT"'),), ()),
        (O46, ct.vendor_billing_route_partial, (lambda: vp.replace_bytes(
            "environment.json", '"reported": null', '"reported": "ChatGPT"'),), ())],
    "T-18": [(O47, ct.vendor_codex_tools_partial, (lambda: _payload_edit(
        "session/native-turn-1.jsonl", _message_with("developer", "<skills_instructions>"),
        lambda r: r["payload"]["content"].append(
            {"type": "input_text", "text": "<multi_agent_role>You are `/root`, the primary agent.</multi_agent_role>"})),
        ), ())],
}


def _nc_runs(key) -> list:
    """[problems of each plant of the row], each plant on its own scratch copy."""
    out = []
    for fixture, reader, edits, patches in NC_PLANTS[key]:
        out.append(_partial(fixture, reader, *[e() for e in edits], patches=patches) if edits or patches else [])
    return out


def _nc(key):
    def case():
        runs = _nc_runs(key)
        return [p for run in runs for p in run] if all(runs) else []
    return case


NC_CASES: dict = {("codex", k): _nc(k) for k in NC_PLANTS}
NC_CASES[("codex", "T-8:file-change")] = nc_t8


# ---- the 15 Codex READER items (VENDOR_READER_ITEMS["codex"]): each reader on a RECORDED copy against the test's
# own reading (design section 3), and, where a plant is cheap and reaches the reader, the item's violation re-planted
# on the recorded copy (the rest of plan section 8's F3 re-runs on recorded copies are lane R's, review section 3) ---
ITEM_FIXTURES = {item: f"{O46}/transcript.jsonl" for item in ("T-1", "T-2", "T-3", "T-4", "T-6", "T-7", "T-8", "T-9",
                                                               "T-11", "T-15", "T-17", "T-20", "T-21", "T-23",
                                                               "T-24")}
_READ_TYPES = ("function_call", "function_call_output", "local_shell_call", "custom_tool_call",
               "custom_tool_call_output", "tool_search_call", "tool_search_output", "web_search_call")


def _streams(folder: Path) -> list:
    envs = [json.loads(x) for x in (folder / "transcript.jsonl").read_text(encoding="utf-8").split("\n") if x]
    return envs, [[json.loads(x) for x in (folder / e["stream"]).read_text(encoding="utf-8").split("\n") if x.strip()]
                  for e in envs]


def item_facts(folder: Path, want_model: str) -> dict:
    """Each item's independent reading of the clean copy, plain json only (True where the take is as recorded)."""
    recs = _rollout(folder)
    envs, streams = _streams(folder)
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    sent = [e["sent"] for e in envs]
    meta = recs[0]["payload"]
    tcs = [r["payload"] for r in recs if r["type"] == "turn_context"]
    users = [r["payload"]["item"]["content"][0]["text"] for r in recs if _is(r, "event_msg", type="item_completed")
             and r["payload"]["item"]["type"] == "UserMessage"]
    tids = [x["thread_id"] for st in streams for x in st if x["type"] == "thread.started"]
    run_tree = "/tmp/" + ct.neutral_name(ct.walk_session_id(folder.name))
    journals = [json.loads((folder / f"turn-{k}.jsonl.launch.json").read_text(encoding="utf-8"))
                for k in range(1, len(envs) + 1)]
    n_records = sum(1 for st in streams for x in st if x["type"].startswith("item.")
                    and x["item"]["type"] in ("command_execution", "file_change"))
    n_records += sum(1 for r in recs if _is(r, "event_msg", type="item_completed")
                     and r["payload"]["item"]["type"] in ("CommandExecution", "FileChange"))
    n_records += sum(1 for r in recs if r["type"] == "response_item" and r["payload"].get("type") in _READ_TYPES)
    env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
    store = json.loads((folder / "session-store.json").read_text(encoding="utf-8"))
    project = ct.neutral_name(ledger["session_id"])
    marker = "[redacted: operator email]"
    files = ["transcript.jsonl"] + [e["stream"] for e in envs] + [f"session/{s['file']}"
                                                                  for s in ledger["native_snapshots"]]
    return {
        "T-1": any(x["type"] == "item.completed" and x["item"]["type"] == "agent_message" for st in streams
                   for x in st),
        "T-2": len(set(tids)) == 1 and {e["vendor_session_id"] for e in envs} == set(tids) == {meta["id"]},
        "T-3": users == sent == [t["sent"] for t in ledger["turns"]],
        "T-4": all(t["cwd"] == run_tree for t in tcs) and all(j["cwd"] == run_tree for j in journals),
        "T-6": project in sent[0] and not _leak_words(" ".join(sent)),
        "T-7": len(sent) == len(ledger["turns"]) and all(t.get("exit") == 0 for t in ledger["turns"]),
        "T-8": n_records,
        "T-9": not any(marker in (folder / f).read_text(encoding="utf-8") for f in files),
        "T-11": len({t["cwd"] for t in tcs}) == 1,
        "T-15": {t["model"] for t in tcs} == {want_model} == {ledger["model_requested"]},
        "T-17": env["names_present"] == [] and not env["api_key_set"] and not env["billing_route_set"],
        "T-20": len(set(tids)) == 1 and sum(_is(r, "event_msg", type="task_started") for r in recs) == len(envs),
        "T-21": store["nested_cli_calls"] == 0 and store["unread_stream_lines"] == 0
        and [x["at"] for x in store["listings"]] == [f"post-{k}" for k in range(1, len(envs) + 1)] + ["publish"],
        "T-23": True,             # every stream line parsed as JSON above (json.loads raises otherwise)
        "T-24": all(sum(x["type"] == "turn.completed" for x in st) == 1
                    and not any(x["type"] == "turn.failed" for x in st) for st in streams),
    }


def item_reading(item: str, plant) -> list:
    """The item's own check_take reader(s) on the copy, as vendor_check and vendor_round4_problems call them."""
    p, h = plant.path, "codex"
    row, design = walk_design(plant)
    ledger = json.loads((plant.folder / "driver-ledger.json").read_text(encoding="utf-8"))
    view = ct.vendor_take_view(p, h)
    turns = ct._vendor_turns(view["events"] or [])
    ops = [t["text"] for t in turns if t["role"] == "user"]
    project = ct.neutral_name(ledger["session_id"])
    if item == "T-1":
        return ct.vendor_first_turn_problems(view["events"])
    if item == "T-2":
        return ct.vendor_session_id_problems(p, h)
    if item == "T-3":
        return ct.vendor_operator_problems(p, h)
    if item == "T-4":
        return ct.vendor_design_tree_problems(p, h, design)
    if item == "T-6":
        return ct.vendor_leak_problems(ops, design.pre) + ct.vendor_project_problems(ops, project)
    if item == "T-7":
        source = design.source(project)
        required, out = ct.required_steps(design.script, p, turns, False, project, source, ())
        lines = ct.operator_line_problems(ops, required, project, source)
        return out + lines + ([] if lines else ct.continuation_problems(turns, required, [], project, source))
    if item == "T-8":
        return ct.vendor_reach(p, h, run_tree=ct.vendor_session_cwd(p, h))["problems"]
    if item == "T-9":
        return ct.vendor_email_problems(p)
    if item == "T-11":
        return ct.vendor_inherited_cwd_problems(p, h, design)
    if item == "T-15":
        return ct.vendor_model_problems(p, h, ledger, None, plant.folder.name)
    if item == "T-17":
        return ct.vendor_environment_problems(p, h, ledger, design.pre, None, plant.folder.name)
    if item == "T-20":
        return ct.vendor_session_binding_problems(p, h)
    if item == "T-21":
        return ct.vendor_session_store_problems(p, h) + ct.vendor_nested_flag_problems(p, h)
    if item == "T-23":
        return ct.vendor_unread_problems(p, h, ledger)
    if item == "T-24":
        return ct.vendor_turn_end_problems(p, h, ledger)
    raise KeyError(item)


def _item_case(item, fixture=O46, model="gpt-6.1-sol"):
    def case():
        with vp.planted(fixture) as plant:
            facts = item_facts(plant.folder, model)
            got = item_reading(item, plant)
            if item == "T-8":
                reach = ct.vendor_reach(plant.path, "codex", run_tree=ct.vendor_session_cwd(plant.path, "codex"))
                return (got, reach["records"]), ([], facts["T-8"])
        return got, ([] if facts[item] else [f"the copy's own reading of {item} is off: {facts[item]!r}"])
    return case


ITEM_CASES = {item: _item_case(item) for item in ITEM_FIXTURES}
ITEM_CASES["T-15 (w-o47, gpt-6-luna)"] = _item_case("T-15", O47, "gpt-6-luna")

# The item violations re-planted on the recorded copy, each read by the item's own reader: (plant, reason).
ITEM_PLANTS = {
    # T-3: the rollout's turn-3 UserMessage differs from the envelope's sent line
    "T-3": (lambda: _payload_edit(LAST_O46, lambda r: _is(r, "event_msg", type="item_completed") and r["payload"][
        "item"]["type"] == "UserMessage" and r["payload"]["item"]["content"][0]["text"].startswith("Why does"),
        lambda r: r["payload"]["item"]["content"][0].update(text="Why does the design table show two conditions?")),
        "readers-disagree"),
    # T-4: turn 2's launch journal records another working folder
    "T-4": (lambda: vp.replace_bytes("turn-2.jsonl.launch.json", '"cwd":"/tmp/run-8617d222"',
                                     '"cwd":"/tmp/run-0123abcd"'), "readers-disagree"),
    # T-9: the scan's email marker in turn 3's stream (an agent message)
    "T-9": (lambda: vp.replace_bytes("turn-3.jsonl", "The design table has a typo",
                                     "[redacted: operator email] The design table has a typo"), "account-email"),
    # T-15: turn 2's turn_context names another model
    "T-15": (lambda: _payload_edit(LAST_O46, _nth("turn_context", 2), lambda r: r["payload"].update(
        model="gpt-6-luna")), "model-binding"),
    # T-24: turn 3's stream loses its turn.completed record
    "T-24": (lambda: _drop_line("turn-3.jsonl", '"type":"turn.completed"'), "outcome-binding"),
}


def _drop_line(rel: str, needle: str):
    """An edit removing the one line of `rel` holding `needle` (exactly one)."""
    def edit(folder):
        f = folder / rel
        lines = f.read_text(encoding="utf-8").split("\n")
        hits = [i for i, x in enumerate(lines) if needle in x.replace(" ", "")]
        if len(hits) != 1:
            raise vp.PlantRefused(f"{rel}: {needle} is on {len(hits)} lines, not one")
        del lines[hits[0]]
        f.write_text("\n".join(lines), encoding="utf-8")
    return edit


def item_fire(item) -> list:
    plant_fn, _reason = ITEM_PLANTS[item]
    with vp.planted(O46, plant_fn()) as plant:
        return item_reading(item, plant)


# ---- the tests the tables cannot express --------------------------------------------------------------------------
def _hollow(name):
    def reader(*args, **kwargs):
        return []
    reader.__name__ = name
    reader.__module__ = ct.__name__
    return reader


class CSame(unittest.TestCase):
    """Every SAME row's firing case adds lines carrying only its reason (VP-plant-scope, no sibling declared), the
    clean copy reads its independent value, and a hollow reader (the row's reader returning []) goes red."""

    def test_c_same_plants_are_scoped(self):
        for key, reason in SAME_REASONS.items():
            with self.subTest(key=key):
                got = SAME_FIRES[("codex", key)](vp.fixture_folder(O46))
                self.assertEqual(vp.plant_scope_problems(clean_check(O46), got, reason, ()), [])

    def test_c_same_clean_cases(self):
        for key, case in CLEAN_CASES.items():
            with self.subTest(key=key):
                got, want = case()
                self.assertEqual(want, [])
                self.assertEqual(got, want)

    def test_c_same_hollow_readers_go_red(self):
        for key, reason in SAME_REASONS.items():
            name = ct.VENDOR_PENDING_ROWS["codex"][key]["reader"]
            with self.subTest(key=key), unittest.mock.patch.object(ct, name, _hollow(name)):
                got = SAME_FIRES[("codex", key)](vp.fixture_folder(O46))
                # stage V ruling (c): T-24's constants read the same rollout mode record (vendor_constant_problems,
                # its lines naming their source), so T-16's hollow witness reads past those lines
                self.assertFalse([p for p in vp.added_lines(clean_check(O46), got)
                                  if p.startswith(f"[{reason}] ") and ct._mode_binding.CODEX_SOURCE not in p],
                                 f"the hollow {name} still fired")

    def test_c_constants_read_the_mode_from_the_rollout(self):
        # stage V ruling (c): T-24's permission-mode leg reads mode_binding's rollout record, never the ledger's
        # "unrecorded" (all 38 GPT ledgers); the clean copy binds, a turn_context off the pin fires naming its source
        self.assertFalse([p for p in clean_check(O46) if "permission mode" in p])
        with vp.planted(O46) as plant:
            design = walk_design(plant)[1]
            ledger = json.loads((plant.folder / "driver-ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(ledger["permission_mode"], "unrecorded")
            self.assertEqual(ct.vendor_constant_problems(plant.path, "codex", ledger, design.pre), [])
        with vp.planted(O46, _payload_edit(LAST_O46, _nth("turn_context", 2),
                                           lambda r: r["payload"].update(sandbox_policy={"type": "workspace-write"}))
                        ) as plant:
            got = ct.vendor_constant_problems(plant.path, "codex", ledger, design.pre)
        self.assertTrue(got and all(p.startswith("[constant-binding] ") and ct._mode_binding.CODEX_SOURCE in p
                                    for p in got), got)

    def test_c_same_t16_thread_settings_and_sandbox_legs_fire(self):
        # review MAJOR 2: thread_settings carries approval_policy and permission_profile, turn_context the sandbox
        design = None
        for edit in (_payload_edit(LAST_O46, _nth_event("thread_settings_applied", 3),
                                   lambda r: r["payload"]["thread_settings"].update(approval_policy="on-request")),
                     _payload_edit(LAST_O46, _nth("turn_context", 3),
                                   lambda r: r["payload"].update(sandbox_policy={"type": "workspace-write"}))):
            with vp.planted(O46, edit) as plant:
                design = design or walk_design(plant)[1]
                got = ct.vendor_codex_recorded_mode_reads(plant.path, design, None)
            self.assertTrue(got and all(p.startswith("[constant-binding] ") for p in got), got)

    def test_c_same_t16_reuses_the_freeze_gates_fix_reading(self):
        # glitch-f1's adjustment: T-16 reads mode_binding.codex_mode_records (cherry-picked d05e2264), never its own
        def broken(raw):
            return {"turns": 0, "turn_contexts": [], "thread_settings": []}
        with vp.planted(O46) as plant, unittest.mock.patch.object(ct._mode_binding, "codex_mode_records", broken):
            got = ct.vendor_codex_recorded_mode_reads(plant.path, walk_design(plant)[1], None)
        self.assertTrue(any("turn_context record(s)" in p for p in got), got)


class CNotComparable(unittest.TestCase):
    """Each NOT COMPARABLE row: every plant the adopted ruling names fires its reason alone, the clean copy reads
    its natural value, and the partial check replaced by `return []` goes red."""

    def test_c_nc_each_plant_fires(self):
        for key in NC_PLANTS:
            reason = ct.VENDOR_PENDING_ROWS["codex"][key]["reason"]
            for k, got in enumerate(_nc_runs(key), 1):
                with self.subTest(key=key, plant=k):
                    self.assertTrue(got and all(p.startswith(f"[{reason}] ") for p in got), got)
        got = nc_t8()
        self.assertEqual(len(got), 2, got)
        self.assertTrue("do not join" in got[0] and "a rename through the patch tool" in got[1], got)

    def test_c_nc_natural_readings(self):
        # silent on the clean w-o46 copy except T-18, which fires on w-o46 (offered the collaboration tools, as the
        # ruling says) and is silent on w-o47 (after B22-10)
        with vp.planted(O46) as plant:
            pre = walk_design(plant)[1].pre
            for reader in (ct.vendor_codex_offered_partial, ct.vendor_codex_memory_partial,
                           ct.vendor_codex_checkout_partial, ct.vendor_file_change_reads):
                self.assertEqual(reader(plant.path), [], reader.__name__)
            self.assertEqual(ct.vendor_billing_route_partial(plant.path, "codex", pre), [])
            t18 = ct.vendor_codex_tools_partial(plant.path)
        self.assertEqual([p.split(" section")[0].split(" [")[0] for p in t18],
                         ["[harness-condition-violated] the rollout carries the multi_agent_role",
                          "[harness-condition-violated] the rollout carries the multi_agent_mode",
                          # stage Z2: the turn_context record says the same directly
                          "[harness-condition-violated] a turn_context records multi_agent_version"])
        with vp.planted(O47) as plant:
            self.assertEqual(ct.vendor_codex_tools_partial(plant.path), [])
        with vp.planted(O7) as plant:     # the recommended_plugins section: both rows' checks read it
            self.assertTrue(any("recommended_plugins" in p for p in ct.vendor_codex_offered_partial(plant.path)))
            self.assertTrue(any("recommended_plugins" in p for p in ct.vendor_codex_tools_partial(plant.path)))

    def test_c_nc_hollow_partials_go_red(self):
        for key in list(NC_PLANTS) + ["T-8:file-change"]:
            name = ct.VENDOR_PENDING_ROWS["codex"][key]["reader"]
            with self.subTest(key=key), unittest.mock.patch.object(ct, name, _hollow(name)):
                got = nc_t8() if key == "T-8:file-change" else [p for run in _nc_runs_hollow(key) for p in run]
                self.assertFalse([p for p in got if p.startswith("[")], f"the hollow {name} still fired: {got}")

    def test_c_nc_t17_credential_source_leg_is_its_own(self):
        # stage V, glitch-f1's amendment: the two credential_source plants fire through the leg alone; with the leg
        # hollowed (vendor_credential_source_problems returning []) they read clean
        for fixture, reader, edits, patches in NC_PLANTS["T-17:billing-route"][3:]:
            with self.subTest(plant=len(edits)):
                got = _partial(fixture, reader, *[e() for e in edits], patches=patches)
                self.assertEqual(len(got), 1, got)
                self.assertIn("credential_source", got[0])
                with unittest.mock.patch.object(ct, "vendor_credential_source_problems", lambda *a, **k: []):
                    self.assertEqual(_partial(fixture, reader, *[e() for e in edits], patches=patches), [])

    def test_c_nc_rulings_are_glitch_f1s_text(self):
        for key in list(NC_PLANTS) + ["T-8:file-change"]:
            row = ct.VENDOR_PENDING_ROWS["codex"][key]
            with self.subTest(key=key):
                self.assertEqual(row["state"], "NOT COMPARABLE")
                self.assertTrue(row["ruling"].startswith(f"### {key} ("), row["ruling"][:60])
                self.assertIn("glitch-f1's ruling under Javier's standing delegation, 21 Oct 2026", row["ruling"])
                self.assertIn("A reader may conclude", row["ruling"])
                self.assertEqual(hashlib.sha256(row["ruling"].encode("utf-8")).hexdigest(), RULING_SHA256[key])

    def test_c_memory_settings_leg_and_memory_mode(self):
        # glitch-f1's re-amendment (22 Oct 02:37, review 0df1437 MAJOR 1): the pin has features.memories (off by
        # default, features/src/lib.rs:1230-1235), so the check reads the rebuilt pinned config.toml and fires when it
        # turns the feature on; memory_mode "disabled" (recorder.rs:976, the record of generation off) is consistent;
        # any other memory-named key still fires
        text = ct.VENDOR_PENDING_ROWS["codex"]["T-12:memory"]["ruling"]
        self.assertIn("features.memories", text)
        self.assertNotIn("names no memory setting", text)
        real = ct._take_config.files_for

        def memories_on(harness, **kw):
            out = dict(real(harness, **kw))
            cfg = out[ct._take_config.CODEX_CONFIG].decode("ascii")
            out[ct._take_config.CODEX_CONFIG] = cfg.replace("[features]\n", "[features]\nmemories = true\n").encode()
            return out
        with vp.planted(O46) as clean:
            self.assertEqual(ct.vendor_codex_memory_partial(clean.path), [])
            with unittest.mock.patch.object(ct._take_config, "files_for", memories_on):
                got = ct.vendor_codex_memory_partial(clean.path)
        self.assertTrue(got and all(p.startswith("[inherited-context] ") for p in got), got)
        self.assertTrue(any("features.memories" in p for p in got), got)
        disabled = _payload_edit(LAST_O46, lambda r: r.get("type") == "session_meta",
                                 lambda r: r["payload"].update(memory_mode="disabled"))
        with vp.planted(O46, disabled) as plant:
            self.assertEqual(ct.vendor_codex_memory_partial(plant.path), [])
        other = _payload_edit(LAST_O46, lambda r: r.get("type") == "session_meta",
                              lambda r: r["payload"].update(memory_mode="enabled"))
        with vp.planted(O46, other) as plant:
            self.assertTrue(ct.vendor_codex_memory_partial(plant.path))


# The adopted rulings' texts (vendor-settle-NC-RULINGS-2026-10-21.md, arm O, each section's heading and body lines
# joined by newlines): sha256 read from that file (whole-file sha256 3c29d72b..., after glitch-f1's 22 Oct
# amendments: T-17's credential_source sentence; T-12:memory's settings leg and T-8's reader by name, 02:37) by the stage V builder.
RULING_SHA256 = {
    "T-8:file-change": "92b0d31a12200d0c0000f9f23f05a6fc51cbbf63ba3ef76af3ecf2978e629598",
    "T-12:offered-context": "8493792afbe9e5307991e57bc057ee07106048fd45eb92f9b38a02904e2c0ca8",
    "T-12:memory": "da5a7b9d12e8792129fa31f013260b7b86b53c6cc4f8d936511f503c791387fa",
    "T-13": "1f64ec3c648c0ef3358e8052569bf49ef63388128a5504685286d56cc43cd6e6",
    # Citation move: run_take.py:2413 -> run_take.py:2415 (lane pf1-codex-lock added two CODEX_ALLOWED lines above the
    # .env refusal; the cited line is the same). Was c10a5062685940ccbc4fdf020a812747646ef7bafcb30c966062818018e498d9;
    # re-pinned by glitch-45's ruling, Tue 27 Oct 2026: citation-only change from lane pf1-codex-lock.
    "T-17:billing-route": "57c3cf77d7f0639315c6f99952a9d7b903d82601d9ee600b05be5e077444ccee",
    "T-18": "1372fe564a387a651d001ec73214a7dd8623b10d50e73e7c30db936026d365bb",
}


# ---- one plant per leg (review 0df1437 MINOR 1): each leg of the published partial checks and SAME readers has a
# plant that fires through that leg alone, so a mutant dropping the leg goes red ------------------------------------
TREE46 = "/tmp/run-8617d222"


def _sess(change):
    return lambda: _payload_edit(LAST_O46, lambda r: r.get("type") == "session_meta", change)


def _ws(change):
    return lambda: _payload_edit(LAST_O46, lambda r: r.get("type") == "world_state", change)


def _dev(prefix, fn):
    return lambda: _payload_edit(LAST_O46, _message_with("developer", "<skills_instructions>"), _set_part(prefix, fn))


def _user(prefix, fn):
    return lambda: _payload_edit(LAST_O46, _message_with("user", prefix), _set_part(prefix, fn))


def _config_with(old, new):
    real = ct._take_config.files_for

    def files_for(harness, **kw):
        out = dict(real(harness, **kw))
        cfg = out[ct._take_config.CODEX_CONFIG].decode("ascii")
        if cfg.count(old) != 1:
            raise AssertionError(f"config plant {old!r} occurs {cfg.count(old)} times")
        out[ct._take_config.CODEX_CONFIG] = cfg.replace(old, new).encode("ascii")
        return out
    return unittest.mock.patch.object(ct._take_config, "files_for", files_for)


def _refused_missing(name):
    real = ct._run_take.refused_variables
    return unittest.mock.patch.object(ct._run_take, "refused_variables",
                                      lambda h: [v for v in real(h) if v != name])


ROOT_OUT = f"<root>{TREE46}</root><root>/root/outside</root>"


def _additional_tools():
    """An additional_tools response_item after the first turn_context of the last rollout, every ordinal renumbered
    (read_rollout accepts it then, so the legs that read it are reachable; review 0df1437 thought it refused first)."""
    def edit(folder):
        f = folder / LAST_O46
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").split("\n") if x]
        at = next(i for i, r in enumerate(recs) if r["type"] == "turn_context") + 1
        rec = dict(recs[at - 1], type="response_item",
                   payload={"type": "additional_tools", "tools": [{"name": "web_fetch"}]})
        recs.insert(at, rec)
        for i, r in enumerate(recs):
            if "ordinal" in r:
                r["ordinal"] = i
        f.write_text("".join(json.dumps(r) + "\n" for r in recs), encoding="utf-8")
    return edit
LEAK_W = "evaluation"
# (leg, reason, reader(plant, design) -> problems, plant edits, a patch context or None)
LEG_PLANTS = [
    ("M1 offered: the environment context's roots", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [_user(ct.CODEX_ENVIRONMENT_PREFIX, lambda t: t.replace(f"<root>{TREE46}</root>", ROOT_OUT))], None),
    ("M2 offered: world_state's filesystem roots", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [_ws(lambda r: r["payload"]["state"]["environments"].update(filesystem=r["payload"]["state"]["environments"][
         "filesystem"].replace(f"<root>{TREE46}</root>", ROOT_OUT)))], None),
    ("M3 offered: a thread_settings snapshot's roots", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [lambda: _payload_edit(LAST_O46, _nth_event("thread_settings_applied", 2),
                            lambda r: r["payload"]["thread_settings"]["runtime_workspace_roots"].append("/root/out"))],
     None),
    ("M4 offered: world_state's apps section on", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [_ws(lambda r: r["payload"]["state"].update(apps_instructions=True))], None),
    ("M21 T-18: world_state's apps section on", ct.HARNESS_CONDITION_VIOLATED,
     lambda p, d: [x for x in ct.vendor_codex_tools_partial(p.path) if "apps_instructions" in x],
     [_ws(lambda r: r["payload"]["state"].update(apps_instructions=True))], None),
    ("M5 offered: an additional_tools item", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path), [_additional_tools], None),
    ("M20 T-18: an additional_tools item", ct.HARNESS_CONDITION_VIOLATED,
     lambda p, d: [x for x in ct.vendor_codex_tools_partial(p.path) if "additional_tools" in x], [_additional_tools],
     None),
    ("M6 offered: a skill root outside the pinned folder", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [_dev("<skills_instructions>", lambda t: t.replace("- `r0` = `/opt/cfg/skills/.system`",
                                                        "- `r0` = `/root/skills`", 1))], None),
    ("M7 memory: world_state's key set", "inherited-context",
     lambda p, d: ct.vendor_codex_memory_partial(p.path),
     [_ws(lambda r: r["payload"]["state"].update(extra_section={}))], None),
    ("M8 memory: a memory-named key in session_meta", "inherited-context",
     lambda p, d: ct.vendor_codex_memory_partial(p.path),
     [_sess(lambda r: r["payload"].update(memory_root="/opt/cfg/memories"))], None),
    ("M9 memory: a memory-named key in a turn_context", "inherited-context",
     lambda p, d: ct.vendor_codex_memory_partial(p.path),
     [lambda: _payload_edit(LAST_O46, _nth("turn_context", 2), lambda r: r["payload"].update(memories={}))], None),
    ("M9 memory: a memory-named key in a thread_settings snapshot", "inherited-context",
     lambda p, d: ct.vendor_codex_memory_partial(p.path),
     [lambda: _payload_edit(LAST_O46, _nth_event("thread_settings_applied", 2),
                            lambda r: r["payload"]["thread_settings"].update(memories={}))], None),
    ("M11 T-13: the commit hash off its shape", "checkout-binding",
     lambda p, d: ct.vendor_codex_checkout_partial(p.path),
     [_sess(lambda r: r["payload"]["git"].update(commit_hash="HEAD"))], None),
    ("M13 T-17: the refused set misses a billing route", "environment-record",
     lambda p, d: ct.vendor_billing_route_partial(p.path, "codex", d.pre), [],
     lambda: _refused_missing("CODEX_ACCESS_TOKEN")),
    ("M15 T-17: a token_count with no plan", "environment-record",
     lambda p, d: ct.vendor_billing_route_partial(p.path, "codex", d.pre),
     [lambda: _payload_edit(LAST_O46, _nth_event("token_count", 2),
                            lambda r: r["payload"]["rate_limits"].update(plan_type=None))], None),
    ("M18 T-17: an empty per_turn credential list", "environment-record",
     lambda p, d: ct.vendor_billing_route_partial(p.path, "codex", d.pre),
     [lambda: vp.replace_bytes("environment.json", '"per_turn": [', '"per_turn": [], "per_turn_was": [')], None),
    ("Y T-17: credential_source per_turn short of the walk's turns", "environment-record",
     lambda p, d: ct.vendor_billing_route_partial(p.path, "codex", d.pre),
     [lambda: vp.replace_bytes("environment.json", ',\n      {\n        "n": 3,\n        "recovery": false,\n'
                               '        "exit": 0,\n        "apiKeySource": null\n      }', '')], None),
    ("M19 T-18: the pinned config turns agents on", ct.HARNESS_CONDITION_VIOLATED,
     lambda p, d: [x for x in ct.vendor_codex_tools_partial(p.path) if "config.toml" in x], [],
     lambda: _config_with("[agents]\nenabled = false\n", "[agents]\nenabled = true\n")),
    ("M23 T-5: a second AGENTS.md part", "unknown-harness-origin",
     lambda p, d: ct.vendor_codex_origin_reads(p.path),
     [lambda: _payload_edit(LAST_O46, _message_with("user", ct.CODEX_AGENTS_PREFIX),
                            lambda r: r["payload"]["content"].append(dict(r["payload"]["content"][0])))], None),
    # the LAST operator line dropped (a middle one would also read as a part of unknown origin, another leg)
    ("M24 T-5: the last operator line missing from the rollout", "unknown-harness-origin",
     lambda p, d: ct.vendor_codex_origin_reads(p.path),
     [lambda: _payload_edit(LAST_O46, lambda r: _is(r, "response_item", type="message", role="user") and [
         c.get("text") for c in r["payload"]["content"]] == ["Why does the design table show three conditions?"],
         lambda r: r["payload"].update(content=[]))], None),
    ("M25 T-10: a leak word in world_state", "leak-in-loaded-context",
     lambda p, d: ct.vendor_codex_loaded_context_reads(p.path, d.pre),
     [_ws(lambda r: r["payload"]["state"]["persistent_mode"].update(note=LEAK_W))], None),
    ("M26 T-10: a leak word in the environment context part", "leak-in-loaded-context",
     lambda p, d: ct.vendor_codex_loaded_context_reads(p.path, d.pre),
     [_user(ct.CODEX_ENVIRONMENT_PREFIX, lambda t: t.replace("<shell>bash</shell>", f"<shell>bash {LEAK_W}</shell>"))],
     None),
    ("M26 T-10: a leak word in the AGENTS.md message body", "leak-in-loaded-context",
     lambda p, d: ct.vendor_codex_loaded_context_reads(p.path, d.pre),
     [_user(ct.CODEX_AGENTS_PREFIX, lambda t: t.replace("</INSTRUCTIONS>", f"{LEAK_W}\n</INSTRUCTIONS>"))], None),
    ("M27 T-10: a leak word in session_meta", "leak-in-loaded-context",
     lambda p, d: ct.vendor_codex_loaded_context_reads(p.path, d.pre),
     [_sess(lambda r: r["payload"]["base_instructions"].update(
         text=r["payload"]["base_instructions"]["text"] + " " + LEAK_W))], None),
    ("M28 T-10: a leak word after an escaped newline in a developer section", "leak-in-loaded-context",
     lambda p, d: ct.vendor_codex_loaded_context_reads(p.path, d.pre),
     [_dev("<collaboration_mode>", lambda t: t + "\n" + LEAK_W)], None),
    ("M29 T-12:instruction-files: world_state's agents_md outside the session folder", "inherited-context",
     lambda p, d: ct.vendor_codex_instruction_files_reads(p.path),
     [_ws(lambda r: r["payload"]["state"]["agents_md"].update(directory="/opt/cfg"))], None),
    ("M30 T-14: one word of the AGENTS.md message copy", "checkout-binding",
     lambda p, d: ct.vendor_codex_instruction_content_reads(p.path, d),
     [_user(ct.CODEX_AGENTS_PREFIX, lambda t: t.replace("repository orientation", "repository introduction", 1))],
     None),
    ("M36 offered: session_meta.dynamic_tools", "inherited-context",
     lambda p, d: ct.vendor_codex_offered_partial(p.path),
     [_sess(lambda r: r["payload"].update(dynamic_tools=[{"name": "web_fetch"}]))], None),
]


class CLegs(unittest.TestCase):
    """Review 0df1437 MINOR 1: each leg fires alone on its own scratch copy of the RECORDED w-o46 take."""

    def test_c_legs_each_plant_fires_through_its_leg(self):
        import contextlib
        with vp.planted(O46) as clean:
            design = walk_design(clean)[1]
        for name, reason, read, edits, patch in LEG_PLANTS:
            with self.subTest(leg=name), contextlib.ExitStack() as stack:
                if patch is not None:
                    stack.enter_context(patch())
                plant = stack.enter_context(vp.planted(O46, *[e() for e in edits]))
                got = read(plant, design)
                self.assertTrue(got, f"{name}: the plant reads clean")
                if reason is not None:
                    self.assertTrue(all(p.startswith(f"[{reason}] ") for p in got), got)
        with vp.planted(O46) as clean:                         # every leg read here is silent on the clean copy
            for name, reason, read, edits, patch in LEG_PLANTS:   # (T-18's own legs filtered to their lines above)
                self.assertEqual(read(clean, design), [], name)


# ---- stage Z2 (glitch-f1's rulings on CODEX-S0-READ-20261022.md) --------------------------------------------------
APPLY_PATCH = 'text(await tools.apply_patch("*** Begin Patch\\n*** Add File: notes.md\\n+x\\n*** End Patch"))'


def _first_exec_call(change):
    return lambda: _payload_edit(LAST_O46, _nth_custom_call(1), change)


def _nth_custom_call(n):
    seen = [0]

    def match(rec):
        if not _is(rec, "response_item", type="custom_tool_call"):
            return False
        seen[0] += 1
        return seen[0] == n
    return match


def _first_command_execution(change):
    seen = [0]

    def match(rec):
        if not (_is(rec, "event_msg", type="item_completed") and rec["payload"]["item"].get("type") == "CommandExecution"):
            return False
        seen[0] += 1
        return seen[0] == 1
    return lambda: _payload_edit(LAST_O46, match, change)


class CZ2(unittest.TestCase):
    def test_z2_t8_an_apply_patch_script_with_no_file_change_refuses(self):
        # code_mode/mod.rs:337-373: a code-mode exec script calls tools.apply_patch; with no joined FileChange the
        # patch is invisible to the view, so the T-8 site reads it and refuses (0 of 216 recorded calls name it)
        with vp.planted(O46) as clean:
            self.assertEqual(ct.vendor_file_change_problems(clean.path, "codex"), [])
        with vp.planted(O46, _first_exec_call(lambda r: r["payload"].update(
                input=r["payload"]["input"] + "; " + APPLY_PATCH))()) as plant:
            got = ct.vendor_file_change_problems(plant.path, "codex")
        self.assertTrue(got and all(x.startswith(f"[{ct.TRANSCRIPT_UNREADABLE}] ") for x in got), got)
        self.assertTrue(any("apply_patch" in x for x in got), got)

    def test_z2_t8_the_apply_patch_shell_alias_refuses(self):
        # arg0/src/lib.rs:325-340: a shell command running the apply_patch alias leaves only a CommandExecution
        with vp.planted(O46, _first_command_execution(lambda r: r["payload"]["item"].update(
                command=["/bin/bash", "-lc", "apply_patch < /tmp/p.diff"]))()) as plant:
            got = ct.vendor_file_change_problems(plant.path, "codex")
        self.assertTrue(got and all(x.startswith(f"[{ct.TRANSCRIPT_UNREADABLE}] ") for x in got), got)
        self.assertTrue(any("apply_patch" in x for x in got), got)

    def test_z2_t8_a_path_qualified_apply_patch_alias_refuses(self):
        # Codex closure NIT: the alias matched by its basename wherever a command word can stand
        for cmd in ("/usr/local/bin/apply_patch < /tmp/p.diff", "cd x && ./apply_patch < p.diff",
                    "true; /opt/codex/tmp/arg0/codex-arg0abc123/applypatch <<'EOF'"):
            with self.subTest(cmd=cmd), vp.planted(O46, _first_command_execution(lambda r: r["payload"]["item"].update(
                    command=["/bin/bash", "-lc", cmd]))()) as plant:
                got = ct.vendor_file_change_problems(plant.path, "codex")
                self.assertTrue(any("apply_patch alias" in x for x in got), got)
        for cmd in ("cat docs/apply_patch.md", "grep apply_patch_x notes.txt"):   # not a command word
            with self.subTest(cmd=cmd), vp.planted(O46, _first_command_execution(lambda r: r["payload"]["item"].update(
                    command=["/bin/bash", "-lc", cmd]))()) as plant:
                self.assertEqual(ct.vendor_file_change_problems(plant.path, "codex"), [])

    def test_z2_offered_an_exec_script_calling_another_tool_fires(self):
        with vp.planted(O46, _first_exec_call(lambda r: r["payload"].update(
                input=r["payload"]["input"] + '; text(await tools.web_run({q: "x"}))'))()) as plant:
            got = ct.vendor_codex_offered_partial(plant.path)
        self.assertTrue(got and all(x.startswith("[inherited-context] ") for x in got), got)
        self.assertTrue(any("web_run" in x for x in got), got)

    def test_z2_t17_forced_login_method_and_the_env_refusal(self):
        with vp.planted(O46) as clean:
            design = walk_design(clean)[1]
            self.assertEqual(ct.vendor_billing_route_partial(clean.path, "codex", design.pre), [])
            with _config_with('forced_login_method = "chatgpt"\n', ""):
                got = ct.vendor_billing_route_partial(clean.path, "codex", design.pre)
            self.assertTrue(got and all(x.startswith("[environment-record] ") for x in got), got)
            self.assertTrue(any("forced_login_method" in x for x in got), got)
            named = {h: tuple(x for x in v if x[0] != r"\.env") for h, v in ct._run_take.CONFIG_FOLDER_NAMED.items()}
            with unittest.mock.patch.object(ct._run_take, "CONFIG_FOLDER_NAMED", named):
                got = ct.vendor_billing_route_partial(clean.path, "codex", design.pre)
            self.assertTrue(got and any(".env" in x for x in got), got)

    def test_z2_t18_multi_agent_version_read_directly(self):
        with vp.planted(O47) as clean:
            self.assertEqual(ct.vendor_codex_tools_partial(clean.path), [])
        v2 = _payload_edit("session/native-turn-1.jsonl", lambda r: r.get("type") == "turn_context",
                           lambda r: r["payload"].update(multi_agent_version="v2"))
        with vp.planted(O47, v2) as plant:
            got = ct.vendor_codex_tools_partial(plant.path)
        # the new leg alone catches it: no multi-agent section was rendered, so the section proxy is silent
        self.assertEqual([x for x in got if "multi_agent_version" not in x], [], got)
        self.assertTrue(any("multi_agent_version" in x for x in got), got)


class CItems(unittest.TestCase):
    """The 15 Codex READER items on the RECORDED w-o46 copy (T-15 also on w-o47's gpt-6-luna), each against the test's
    own reading, and five items' violations re-planted on the recorded copy."""

    def test_c_items_are_the_live_map_and_recorded(self):
        self.assertEqual(ct.VENDOR_READER_ITEMS["codex"], ITEM_FIXTURES)
        self.assertEqual(ct.vendor_reader_items_problems("codex"), [])

    def test_c_items_clean_readings(self):
        for item, case in ITEM_CASES.items():
            with self.subTest(item=item):
                got, want = case()
                self.assertEqual(got, want)

    def test_c_items_replanted_fire(self):
        for item, (_plant, reason) in ITEM_PLANTS.items():
            with self.subTest(item=item):
                got = item_fire(item)
                self.assertTrue(got and all(p.startswith(f"[{reason}] ") for p in got), got)


class CLegI(unittest.TestCase):
    """Freeze leg i for the Codex adapter, prepared for stage V (which copies the streams into
    tests/fixtures/codex-streams, flips codex_adapter.SHAPES_SOURCE and rewrites its docstring): codex_adapter's
    CodexAdapter drives the RECORDED w-o46 turn streams and rollouts (three turns, resumed) and w-o47's one-turn
    gpt-6-luna take through test_codex_adapter's FakeRuntime and its stubbed run_turn, and every reading equals the
    value this test derives with plain json: the agent's text, the end reason, agent output, the thread id, the usage,
    and the rollout's requested context (model, approval policy, CLI version)."""

    def drive(self, fixture, model):
        saved = list(sys.path)                 # test_codex_adapter's tearDownModule writes sys.path back; keep ours
        try:
            return self._drive(fixture, model)
        finally:
            sys.path[:] = saved

    def _drive(self, fixture, model):
        sys.path.insert(0, str(HERE / "tests"))
        try:
            import codex_adapter
            import test_codex_adapter as tca
        finally:
            sys.path.remove(str(HERE / "tests"))
        with vp.planted(fixture) as plant:
            envs, streams = _streams(plant.folder)
            ledger = json.loads((plant.folder / "driver-ledger.json").read_text(encoding="utf-8"))
            texts = [(plant.folder / e["stream"]).read_text(encoding="utf-8") for e in envs]
            rollouts = [(plant.folder / "session" / s["file"]).read_text(encoding="utf-8")
                        for s in ledger["native_snapshots"]]
            want = []
            for st, ro in zip(streams, rollouts):
                recs = [json.loads(x) for x in ro.split("\n") if x]
                tc = [r["payload"] for r in recs if r["type"] == "turn_context"][-1]
                want.append({
                    "text": "\n".join(x["item"]["text"] for x in st if x["type"] == "item.completed"
                                      and x["item"]["type"] == "agent_message"),
                    "thread_ids": [x["thread_id"] for x in st if x["type"] == "thread.started"],
                    "usage": [x for x in st if x["type"] == "turn.completed"][0]["usage"],
                    "context": {"model": tc["model"], "permission_mode": tc["approval_policy"],
                                "version": recs[0]["payload"]["cli_version"]}})
            tca.setUpModule()
            try:
                with unittest.mock.patch.object(tca, "MODEL", model):
                    box = tca.FakeRuntime(texts, version_out="codex-cli 0.162.1\n",
                                          exit_codes=[t["exit"] for t in ledger["turns"]])
                    a = tca.adapter(codex_adapter, box, rollouts=rollouts)
                    a.start_take({"row_id": 1, "slot": "s1", "half_cell": "c1"})
                    results = [a.turn(e["sent"], first=k == 0, budget_s=60) for k, e in enumerate(envs)]
                    records = list(a.turn_records)
            finally:
                tca.tearDownModule()
        return want, results, records

    def check(self, fixture, model, turns):
        import os
        before = (list(sys.path), dict(os.environ), ct._run_take.VENDOR_BILLING_ROUTE_VARIABLES,
                  ct._run_take.run_turn)
        want, results, records = self.drive(fixture, model)
        self.assertEqual((list(sys.path), dict(os.environ), ct._run_take.VENDOR_BILLING_ROUTE_VARIABLES,
                          ct._run_take.run_turn), before, "the drive left interpreter state changed")
        self.assertEqual(len(results), turns)
        for k, (w, r, rec) in enumerate(zip(want, results, records), 1):
            with self.subTest(fixture=fixture, turn=k):
                self.assertEqual(r.text, w["text"])
                self.assertEqual(r.end_reason, "end_turn")
                self.assertIs(r.agent_output, True)
                self.assertEqual(rec["thread_ids"], w["thread_ids"])
                self.assertEqual(rec["usage"], w["usage"])
                self.assertEqual(rec["requested_context"], w["context"])
                self.assertEqual(rec["requested_context"], {"model": model, "permission_mode": "never",
                                                            "version": "0.162.1"})
                self.assertEqual((rec["completed"], rec["failed"], rec["undecoded"]), (1, 0, 0))

    def test_c_leg_i_w_o46_three_resumed_turns(self):
        self.check(O46, "gpt-6.1-sol", 3)

    def test_c_leg_i_w_o47_post_b22_luna(self):
        self.check(O47, "gpt-6-luna", 1)


def _nc_runs_hollow(key) -> list:
    """_nc_runs with each plant's reader looked up by name on check_take at call time (so a patched one is read)."""
    out = []
    for fixture, reader, edits, patches in NC_PLANTS[key]:
        live = getattr(ct, reader.__name__)
        import contextlib
        with contextlib.ExitStack() as stack:
            for target, attr, value in patches:
                stack.enter_context(unittest.mock.patch.dict(target[attr], value))
            plant = stack.enter_context(vp.planted(fixture, *[e() for e in edits]))
            out.append(live(plant.path, "codex", walk_design(plant)[1].pre) if reader.__name__ ==
                       "vendor_billing_route_partial" else live(plant.path))
    return out


if __name__ == "__main__":
    unittest.main()
