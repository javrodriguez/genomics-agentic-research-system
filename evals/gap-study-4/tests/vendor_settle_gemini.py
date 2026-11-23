#!/usr/bin/env python3
"""Lane vendor-settle: the Gemini rows' settlement cases (stage K made this module empty; stage G, the Gemini builder, is
its only writer). tests/test_vendor_check.py imports it and merges its three tables with the other harness's module
(tests/vendor_settle_codex.py); a key here must be a ("gemini", <key>) of check_take.VENDOR_PENDING_ROWS, and no key may
appear in both modules.

  SAME_FIRES   ("gemini", key) -> fire(fixture_path) -> list of problems: the row's site run on a planted copy of the
               row's RECORDED fixture (tests/vendor_plant.planted); VPSameFires requires a line carrying the row's
               reason, for every SAME row of the live map. Each fire also runs the site on the clean copy and refuses
               (AssertionError) unless VP-plant-scope holds (the plant adds lines, each of the row's reason, none
               removed); it returns the added lines.
  CLEAN_CASES  ("gemini", key) -> case() -> (got, want): the reader on the unmodified RECORDED copy against the
               independent value the case's own plain-json parser derives; VPSettleCases requires got == want.
  NC_CASES     ("gemini", key) -> case() -> list of problems: a NOT COMPARABLE row's partial check on its non-hollow
               plant; VPSettleCases requires a non-empty list whose every line carries the row's reason.

RECORDED folders for this harness: tests/fixtures/recorded-gemini-w-g21 (one context version) and
tests/fixtures/recorded-gemini-w-g14 (four context versions: the first write, two resume $patch updates that wrote over
it, and a re-recorded copy; the review's MAJOR 1).

Stage G adds, beside the three tables (run as `python3 -B tests/vendor_settle_gemini.py`, checks.d/vendor-settle-g.txt):

  G-rows       the live map: the five SAME rows (T-4, T-10, T-11, T-12:instruction-files, T-14) name their reader and the
               w-g21 fixture; the six NOT COMPARABLE rows name their partial check and the adopted ruling text, verbatim
               (each text's sha256 pinned below, read from plans/gap-study-round-4/vendor-settle-NC-RULINGS-2026-10-21.md
               on Wed 21 Oct 2026); every site hands in the row's reader (VP-keys, test_vendor_check).
  G-versions   MAJOR 1: on w-g14 the readers read every <session_context> version; the test's own generic parser (every
               string anywhere in the parsed records that opens <session_context>, thought parts aside) counts the
               same versions; the replay's timeline holds one; a plant made only in the overwritten first version fires
               T-10, T-4, T-11, T-12:instruction-files and T-14, and the mutant reading the replay's timeline only goes
               red on it. Thoughts inside a $patch update (w-g14 holds one) are never read as context.
  G-decoded    MAJOR 3: a leak word right after an escaped newline in the raw JSON is read (the T-10 plant), and the
               raw-line mutant goes red on it.
  G-scope      every SAME plant through the whole vendor_check and vendor_round4_problems adds only its row's reason
               and the declared siblings.
  G-mutants    each SAME reader returning [], or reading the first version only, goes red on its firing case or on
               the w-g14 plant; each NOT COMPARABLE partial check returning [] goes red on its case.
  G-reach      MINOR 5: vendor_session_cwd reads Gemini's one recorded workspace directory, so the reach's home and temp
               legs admit the run tree (the clean w-g21 copy reads no read-outside-the-checkout; with the directory
               unread, it reads 102 mentions, the T-8 READER item's old reading).
  G-items      the 15 Gemini READER items (check_take.VENDOR_READER_ITEMS) on the RECORDED w-g21 copy: each item's
               reading equals the independent value of the test's own parser (ITEM_CASES), and each item's planted
               violation on a re-bound copy fires its reason (ITEM_PLANTS).
  G-legi       leg i, prepared for stage V (gemini_adapter.SHAPES_SOURCE stays "documented" until V flips it): the
               adapter's read_stream on the RECORDED w-g21 turn streams against values the test derives with plain
               json (init model and session id, the assistant output, the tool events, the stats, the end reason).

The RECORDED folders are walk records: every plant edits a scratch copy (tests/vendor_plant.py), never the fixture.
No take, model, container or network.
"""

from __future__ import annotations

import collections
import contextlib
import functools
import hashlib
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import check_take as ct  # noqa: E402
import gemini_adapter  # noqa: E402
import gemini_session_replay  # noqa: E402
import run as run_mod  # noqa: E402
import scrub  # noqa: E402
import variants  # noqa: E402
import walk_regrade  # noqa: E402
from box import run_take  # noqa: E402

_added = str(HERE / "tests") not in sys.path
if _added:
    sys.path.insert(0, str(HERE / "tests"))
try:
    import vendor_plant  # noqa: E402
finally:
    if _added:
        sys.path.remove(str(HERE / "tests"))

H = "gemini"
G21, G14 = "recorded-gemini-w-g21", "recorded-gemini-w-g14"
WALKS = {G21: "w-g21", G14: "w-g14"}
SNAPS = {G21: ("session/native-turn-1.jsonl", "session/native-turn-2.jsonl"),
         G14: ("session/native-turn-1.jsonl", "session/native-turn-2.jsonl", "session/native-turn-3.jsonl",
               "session/native-turn-4.jsonl")}
MODEL = "gemini-3.8-flash"                      # the register entry of both walks (rehearsals/register.json)
TREE21 = "/tmp/run-752c6e21"                    # w-g21's turn-1.jsonl.launch.json cwd
# The adopted rulings' texts (vendor-settle-NC-RULINGS-2026-10-21.md, arm G, each section's heading and body lines
# joined by newlines, the Codex rows' form, review 0df1437 NIT 2): sha256 read from that file (whole-file sha256
# 3c29d72b...) by the stage V builder (last copy).
RULING_SHA256 = {
    # Citation move: run_take.py:2381-2437 -> run_take.py:2383-2439 (lane pf1-codex-lock added two CODEX_ALLOWED lines
    # above GEMINI_ALLOWED; the cited lines are the same). Was 6f25807077b7caaecc43c7f4d012a589b0c0d2cc8632e6931d243ac457a6998a;
    # re-pinned by glitch-45's ruling, Tue 27 Oct 2026: citation-only change from lane pf1-codex-lock.
    "T-12:offered-context": "871fbe72ff754466d256640b335540259481f6b13e71bfdd90465622dff2b801",
    "T-12:prompt-snapshot": "bc7d5500c4d5e29e2c34f63237108751e18baf14d0fadc76bf1e6e93e2eee68a",
    # Citation move: run_take.py:2429-2430 -> run_take.py:2431-2432 (the same two memory-file refusal lines, moved
    # down two by lane pf1-codex-lock). Was 7481bfa7792b88d6b4c8529ece5304114718dbc5364201239748d428c222e299;
    # re-pinned by glitch-45's ruling, Tue 27 Oct 2026: citation-only change from lane pf1-codex-lock.
    "T-12:memory": "81c72da0d8a793918b43054a10738719e633de15f534e3e3043d41161908f575",
    "T-13": "6f2018c26831baf57aa36598c40592dd591405314b5dcea4f0d10b5cc75fd632",
    "T-17:billing-route": "8e6b496e8962b7cec74485fdbb7b26394a4f067e6d017217ef11d850aeafc024",
    "T-18": "3db3238eb5db2707426b61ae075b447304cfc9433e7254514a857db0d4ce5e5b",
}
SAME_READERS = {"T-4": "vendor_gemini_run_tree_reads", "T-10": "vendor_gemini_loaded_context_reads",
                "T-11": "vendor_gemini_cwd_reads", "T-12:instruction-files": "vendor_gemini_instruction_files_reads",
                "T-14": "vendor_gemini_instruction_content_reads"}
NC_READERS = {"T-12:offered-context": "vendor_gemini_offered_partial",
              "T-12:prompt-snapshot": "vendor_gemini_prompt_partial",
              "T-12:memory": "vendor_gemini_memory_partial", "T-13": "vendor_gemini_checkout_partial",
              "T-17:billing-route": "vendor_gemini_billing_route_partial", "T-18": "vendor_gemini_tools_partial"}
FIXTURE = f"{G21}/transcript.jsonl"
CONTEXT_OPEN = "<session_context>"


# ---- the test's own plain-json readings (never check_take's helpers) ------------------------------------------------
def _json_lines(path: Path) -> list:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]


def own_last_snapshot(folder: Path) -> Path:
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    return folder / "session" / ledger["native_snapshots"][-1]["file"]


def own_context_texts(folder: Path) -> list:
    """Every string anywhere in the last snapshot's parsed records that opens <session_context>, a thought part's text
    aside (the review's generic parser): a different method from the readers' structural one."""
    out = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("thought") is True:
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
        elif isinstance(o, str) and o.startswith(CONTEXT_OPEN):
            out.append(o)
    for rec in _json_lines(own_last_snapshot(folder)):
        walk(rec)
    return out


_DIRS = re.compile(r"- \*\*Workspace Directories:\*\*\n((?:  - [^\n]*\n)*)")
_ROOT = re.compile(r"- \*\*Directory Structure:\*\*\n\nShowing up to [^\n]*\n\n(/[^\n]*)/\n")
_FILES = re.compile(r"--- Context from: ([^\n]*) ---\n(.*?)\n--- End of Context from: \1 ---", re.S)


def own_facts(text: str) -> dict:
    d = _DIRS.search(text)
    r = _ROOT.search(text)
    return {"dirs": [x[4:] for x in d.group(1).split("\n") if x] if d else None, "root": r.group(1) if r else None,
            "files": _FILES.findall(text),
            "tags": sorted(set(re.findall(r"</?([a-z_]+)>", _FILES.sub("", text))))}


@functools.lru_cache(maxsize=None)
def pinned(rel: str):
    got = subprocess.run(["git", "-C", str(HERE), "show", f"{variants.PINNED_TREE}:{rel}"], capture_output=True)
    return got.stdout.decode("utf-8") if got.returncode == 0 else None


@functools.lru_cache(maxsize=None)
def leak_words() -> tuple:
    return tuple(json.loads((HERE / "prereg-draft.json").read_text(encoding="utf-8"))["leak_words"])


def own_leaks(text: str) -> list:
    low = text.lower()
    return sorted(w for w in leak_words() if re.search(r"\b" + re.escape(w.lower()) + r"\b", low))


def own_cwds(folder: Path) -> set:
    return {json.loads(p.read_text(encoding="utf-8"))["cwd"] for p in folder.glob("turn-*.jsonl.launch.json")}


# ---- the design a recorded walk is read against (walk_regrade.production_design, as its recheck builds it) -----------
@functools.lru_cache(maxsize=None)
def design_for(fixture: str):
    folder = vendor_plant.fixture_folder(fixture)
    walk = WALKS[folder.name]
    register = json.loads((HERE / "rehearsals" / "register.json").read_text(encoding="utf-8"))
    entry = [e for e in register["walks"] if e.get("walk") == walk]
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    row = dict(run_mod.walk_row(entry[0], ledger), walk=walk, slot=walk)
    tree = json.loads((folder / "turn-1.jsonl.launch.json").read_text(encoding="utf-8"))["cwd"]
    return row, walk_regrade.production_design(row, tree)


def whole_check(fixture: str, path: Path) -> list:
    row, design = design_for(fixture)
    out = ct.vendor_check(path, row["task"], row["half"], None, wording_script=design.script, design=design,
                          arm=row["arm"], walk_id=row["walk"])
    return out + ct.vendor_round4_problems(path, design, arm=row["arm"])


# ---- plants (one logical event, written into every snapshot that records it) ----------------------------------------
def in_snapshots(fixture: str, old: str, new: str, count: int = 1) -> tuple:
    """The raw-JSON text `old` -> `new` in every retained snapshot of the fixture (`count` times in each)."""
    return tuple(vendor_plant.replace_bytes(rel, old, new, count=count) for rel in SNAPS[fixture])


def raw(text: str) -> str:
    """A context text as it is written in the session file's JSON (newlines escaped)."""
    return json.dumps(text, ensure_ascii=False)[1:-1]


PLANTS = {
    # T-4: the workspace directory renamed (the listing root kept)
    "T-4": in_snapshots(G21, raw(f"\n  - {TREE21}\n"), raw("\n  - /tmp/run-0f0f0f0f\n")),
    # T-10 (and MAJOR 3): a leak word right after an escaped newline in the preamble
    "T-10": in_snapshots(G21, raw("\nMy operating system is: linux"), raw("\nGap study. My operating system is: linux")),
    # T-11: the Workspace Directories block emptied
    "T-11": in_snapshots(G21, raw(f"\n  - {TREE21}\n"), raw("\n")),
    # T-12:instruction-files: the loaded file's header and end marker name a file outside the workspace
    "T-12:instruction-files": in_snapshots(G21, f"Context from: {TREE21}/GEMINI.md ---",
                                           "Context from: /opt/cfg/.gemini/GEMINI.md ---", count=2),
    # T-14: one word of the loaded GEMINI.md body
    "T-14": in_snapshots(G21, "no bespoke upgrade machinery", "no bespoke upgrade tooling"),
    # NOT COMPARABLE plants
    "T-12:offered-context": in_snapshots(G21, raw(f"\n  - {TREE21}\n"), raw(f"\n  - {TREE21}\n  - /opt/extra\n")),
    "T-12:memory": in_snapshots(G21, raw("\n</loaded_context>"),
                                raw("\n<global_context>\nA saved memory.\n</global_context>\n</loaded_context>")),
    "T-13": in_snapshots(G21, raw(f"\n\n{TREE21}/\n"), raw("\n\n/tmp/run-0f0f0f0f/\n")),
    "T-17:billing-route": (vendor_plant.replace_bytes(
        "environment.json", '  "names_present": [\n',
        '  "names_present": [\n    {\n      "name": "GOOGLE_CLOUD_ACCESS_TOKEN",\n      "matched_by": "generic"\n'
        '    },\n'),),
}
# T-18: one read_file call renamed web_fetch in its stream tool_use and every session copy of the call (toolCalls,
# functionCall, functionResponse), its id kept.
CALL = "read_file__call_881980"


def _rename_call(text: str) -> str:
    return re.sub(r'("id":"' + CALL + r'","name":)"read_file"', r'\1"web_fetch"', text)


def _rename_edit(rel: str, stream: bool):
    def edit(folder: Path) -> None:
        f = folder / rel
        data = f.read_text(encoding="utf-8")
        if stream:
            old = f'"tool_name":"read_file","tool_id":"{CALL}"'
            assert data.count(old) == 1, rel
            new = data.replace(old, f'"tool_name":"web_fetch","tool_id":"{CALL}"')
        else:
            new = _rename_call(data)
        if new == data:
            raise vendor_plant.PlantRefused(f"{rel}: the call {CALL} is not there")
        f.write_text(new, encoding="utf-8")
    return edit


PLANTS["T-18"] = (_rename_edit("turn-1.jsonl", True),) + tuple(_rename_edit(rel, False) for rel in SNAPS[G21])


# ---- SAME_FIRES ------------------------------------------------------------------------------------------------------
def _site(key):
    return {"T-4": lambda p, d: ct.vendor_design_tree_problems(p, H, d),
            "T-10": lambda p, d: ct.vendor_loaded_context_problems(p, H, d),
            "T-11": lambda p, d: ct.vendor_inherited_cwd_problems(p, H, d),
            "T-12:instruction-files": lambda p, d: ct.vendor_instruction_file_problems(p, H, d),
            "T-14": lambda p, d: ct.vendor_checkout_problems(p, H, d)}[key]


def _fire(key: str):
    reason = ct.VENDOR_PENDING_ROWS[H][key]["reason"]

    def fire(fixture_path) -> list:
        fixture = vendor_plant.fixture_folder(fixture_path).name
        _, design = design_for(fixture)
        with vendor_plant.planted(fixture) as clean:
            before = _site(key)(clean.path, design)
        with vendor_plant.planted(fixture, *PLANTS[key]) as p:
            after = _site(key)(p.path, design)
        scope = vendor_plant.plant_scope_problems(before, after, reason)
        if scope:
            raise AssertionError(f"gemini {key} plant scope: {scope}")
        return vendor_plant.added_lines(before, after)
    return fire


SAME_FIRES: dict = {(H, key): _fire(key) for key in SAME_READERS}


# ---- CLEAN_CASES (the reader on the clean copy against the test's own reading) -------------------------------------
def _clean(key: str):
    def case():
        _, design = design_for(G21)
        with vendor_plant.planted(G21) as clean:
            got = getattr(ct, SAME_READERS[key])(*((clean.path, design) if key in ("T-4", "T-10", "T-14")
                                                     else (clean.path,)))
            texts = own_context_texts(clean.folder)
            facts = [own_facts(t) for t in texts]
            cwds = own_cwds(clean.folder)
        ok = bool(texts) and {
            "T-4": all(f["dirs"] == [design.run_tree] and f["root"] == design.run_tree for f in facts)
            and cwds == {design.run_tree},
            "T-10": not own_leaks(" ".join(texts)),
            "T-11": all(f["dirs"] is not None and len(f["dirs"]) == 1 for f in facts),
            "T-12:instruction-files": all(p.startswith(f["dirs"][0] + "/") for f in facts for p, _ in f["files"]),
            "T-14": all(f["files"] and all(pinned(p[len(design.run_tree) + 1:].replace("GEMINI.md", "CLAUDE.md"))
                                           .rstrip() == body.rstrip() for p, body in f["files"]) for f in facts),
        }[key]
        return got, ([] if ok else ["the test's own reading finds the row's violation on the clean copy"])
    return case


def _nc_clean(key: str):
    def case():
        _, design = design_for(G21)
        with vendor_plant.planted(G21) as clean:
            reader = getattr(ct, NC_READERS[key])
            got = reader(clean.path, design) if key == "T-12:prompt-snapshot" else reader(clean.path)
            facts = [own_facts(t) for t in own_context_texts(clean.folder)]
            cwds = own_cwds(clean.folder)
            env = json.loads((clean.folder / "environment.json").read_text(encoding="utf-8"))
            calls = [r.get("tool_name") for k in (1, 2) for r in _json_lines(clean.folder / f"turn-{k}.jsonl")
                     if r.get("type") == "tool_use"]
        ok = {
            "T-12:offered-context": len(cwds) == 1 and all(f["dirs"] == sorted(cwds) for f in facts),
            "T-12:prompt-snapshot": True,          # input side only: no recorded value to derive
            "T-12:memory": all(set(f["tags"]) <= {"session_context", "loaded_context", "project_context"}
                               for f in facts),
            "T-13": len(cwds) == 1 and all(f["root"] in cwds for f in facts),
            "T-17:billing-route": [x["name"] for x in env["names_present"]] == ["GEMINI_API_KEY"],
            "T-18": bool(calls) and not {"google_web_search", "web_fetch", "invoke_agent"} & set(calls),
        }[key]
        return got, ([] if ok and facts else ["the test's own reading finds the row's violation on the clean copy"])
    return case


CLEAN_CASES: dict = {(H, key): _clean(key) for key in SAME_READERS}
CLEAN_CASES.update({(H, key): _nc_clean(key) for key in NC_READERS})


# ---- NC_CASES (each partial check on its non-hollow plant) ----------------------------------------------------------
def _nc(key: str):
    def case():
        _, design = design_for(G21)
        reader = getattr(ct, NC_READERS[key])
        if key == "T-12:prompt-snapshot":       # the ruling's test: either name patched into the launch environment
            out = []
            with vendor_plant.planted(G21) as clean:
                for name in ct.GEMINI_PROMPT_OVERRIDES:
                    with mock.patch.dict(run_take.TAKE_ENV[H], {name: "/opt/cfg/system.md"}):
                        got = reader(clean.path, design)
                    if not got:
                        return []                # one name not firing makes the case hollow
                    out += got
            return out
        with vendor_plant.planted(G21, *PLANTS[key]) as p:
            return reader(p.path)
    return case


NC_CASES: dict = {(H, key): _nc(key) for key in NC_READERS}


# ---- READER items on the RECORDED w-g21 copy ---------------------------------------------------------------------
def _ledger(folder):
    return json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))


def _streams(folder):
    return [_json_lines(folder / f"turn-{k}.jsonl") for k in range(1, len(_ledger(folder)["turns"]) + 1)]


def stop_and_marker_problems(fixture: str, path: Path) -> list:
    """T-7's reading as vendor_check runs it: required_steps' stop lines, operator_line_problems and
    continuation_problems on the bound view's turns, against the walk's own wording script."""
    _, design = design_for(fixture)
    view = ct.vendor_take_view(path, H)
    turns = ct._vendor_turns(view["events"] or [])
    ops = [t["text"] for t in turns if t["role"] == "user"]
    project = ct.neutral_name(_ledger(path.parent)["session_id"])
    source = design.source(project)
    joined = ct.vendor_continuation_turns(path, H, turns)          # stage W ruling 3: one view for both readings
    required, out = ct.required_steps(design.script, path, joined, False, project, source, ())
    lines = ct.operator_line_problems(ops, required, project, source)
    out += lines
    if not lines:                               # stage V ruling (a): the turns vendor_check hands continuation
        out += ct.continuation_problems(joined, required, [], project, source)
    return out


def own_unheld_markers(folder: Path) -> list:
    """The turns whose reply (the stream's assistant text) lacks the marker the ledger says it expects, while a later
    line was sent."""
    ledger = _ledger(folder)
    out = []
    for k, turn in enumerate(ledger["turns"][:-1], 1):
        reply = "".join(r["content"] for r in _json_lines(folder / f"turn-{k}.jsonl")
                        if r.get("type") == "message" and r.get("role") == "assistant")
        if turn["expects"] and turn["expects"] not in reply:
            out.append(k)
    return out


def _item_reading(item: str, path: Path, folder: Path, fixture: str = G21):
    """The item's reader on a copy (check_take's own function for the item)."""
    row, design = design_for(fixture)
    ledger = _ledger(folder)
    view = ct.vendor_take_view(path, H)
    ops = [t["text"] for t in ct._vendor_turns(view["events"] or []) if t["role"] == "user"]
    return {
        "T-1": lambda: ct.vendor_first_turn_problems(view["events"] or []),
        "T-2": lambda: (ct.vendor_session_id(path, H), ct.vendor_session_id_problems(path, H)),
        "T-3": lambda: ct.vendor_operator_problems(path, H),
        "T-5": lambda: ct.vendor_origin_problems(path, H, design) + ct.vendor_operator_problems(path, H),
        "T-6": lambda: ct.vendor_leak_problems(ops, design.pre)
        + ct.vendor_project_problems(ops, ct.neutral_name(ledger["session_id"])),
        "T-7": lambda: stop_and_marker_problems(fixture, path),
        "T-8": lambda: (ct.vendor_reach(path, H, run_tree=ct.vendor_session_cwd(path, H))["problems"],
                        sum(1 for w, _, _ in ct.vendor_raw_records(path, H) if w.startswith("turn-"))),
        "T-9": lambda: ct.vendor_email_problems(path),
        "T-15": lambda: ct.vendor_model_problems(path, H, ledger, None, row["walk"]),
        "T-16": lambda: ct.vendor_offered_context_problems(path, H, design, row["arm"]),
        "T-17": lambda: ct.vendor_environment_problems(path, H, ledger, design.pre, None, row["walk"]),
        "T-20": lambda: ct.vendor_session_binding_problems(path, H),
        "T-21": lambda: ct.vendor_session_store_problems(path, H) + ct.vendor_nested_flag_problems(path, H),
        "T-23": lambda: ct.vendor_unread_problems(path, H, ledger),
        "T-24": lambda: ct.vendor_turn_end_problems(path, H, ledger),
    }[item]()


def _item_want(item: str, folder: Path):
    """The independent value: the test's own plain-json reading of the clean copy."""
    ledger = _ledger(folder)
    streams = _streams(folder)
    envs = _json_lines(folder / "transcript.jsonl")
    header = _json_lines(own_last_snapshot(folder))[0]
    init_ids = {r["session_id"] for s in streams for r in s if r.get("type") == "init"}
    if item == "T-1":
        return [] if any(r.get("type") == "tool_use" for s in streams for r in s) else ["no agent output"]
    if item == "T-2":
        sid = streams[0][0]["session_id"]
        return (sid, []) if init_ids == {sid} == {header["sessionId"]} else ("", ["the ids differ"])
    if item in ("T-3", "T-5"):
        users = [r["content"] for s in streams for r in s if r.get("type") == "message" and r.get("role") == "user"]
        sent = [t["sent"] for t in ledger["turns"]]
        return [] if users == sent == [e["sent"] for e in envs] and len(sent) == 2 else ["the sent lines differ"]
    if item == "T-6":
        joined = " ".join(e["sent"] for e in envs).lower()
        leaked = [w for w in leak_words() if w.lower() in joined]
        return [] if not leaked and ledger["project"] in joined else ["a leak word or no project name"]
    if item == "T-7":
        return [] if not own_unheld_markers(folder) else ["a reply without its marker, and the next line sent"]
    if item == "T-8":
        return [], sum(1 for s in streams for r in s if r.get("type") in ("tool_use", "tool_result"))
    if item == "T-9":
        marker = scrub.NOTE.encode("utf-8")
        files = ["transcript.jsonl"] + [e["stream"] for e in envs] + [f"session/{x['file']}"
                                                                       for x in ledger["native_snapshots"]]
        return [] if not any(marker in (folder / f).read_bytes() for f in files) else ["a marker"]
    if item == "T-15":
        models = {r["model"] for s in streams for r in s if r.get("type") == "init"}
        models |= {m for s in streams for r in s if r.get("type") == "result" for m in r["stats"]["models"]}
        return [] if models == {MODEL} == {ledger["model_requested"]} else ["another model"]
    if item == "T-16":
        argvs = [json.loads((folder / f"turn-{k}.jsonl.launch.json").read_text())["argv"] for k in (1, 2)]
        return [] if all(a[a.index("--approval-mode") + 1] == "yolo" for a in argvs) else ["another mode"]
    if item == "T-17":
        env = json.loads((folder / "environment.json").read_text(encoding="utf-8"))
        ok = [x["name"] for x in env["names_present"]] == ["GEMINI_API_KEY"] and not env["api_key_set"] \
            and not env["billing_route_set"] and env["session_id"] == ledger["session_id"]
        return [] if ok else ["the environment record differs"]
    if item == "T-20":
        ids = {e["vendor_session_id"] for e in envs} | init_ids | {header["sessionId"]}
        return [] if len(ids) == 1 and {e["session_id"] for e in envs} == {ledger["session_id"]} else ["ids differ"]
    if item == "T-21":
        store = json.loads((folder / "session-store.json").read_text(encoding="utf-8"))
        ok = len(store["listings"]) == len(ledger["native_snapshots"]) + 1 and store["nested_cli_calls"] == 0
        return [] if ok else ["the store differs"]
    if item == "T-23":
        types = {r.get("type") for s in streams for r in s}
        return [] if types <= {"init", "message", "tool_use", "tool_result", "result"} else ["an unknown line"]
    if item == "T-24":
        ends = [[r.get("status") for r in s if r.get("type") == "result"] for s in streams]
        return [] if ends == [["success"]] * len(ledger["turns"]) else ["a turn without its end"]
    raise KeyError(item)


ITEMS = ("T-1", "T-2", "T-3", "T-5", "T-6", "T-7", "T-8", "T-9", "T-15", "T-16", "T-17", "T-20", "T-21", "T-23",
         "T-24")


def item_case(item: str):
    with vendor_plant.planted(G21) as clean:
        return _item_reading(item, clean.path, clean.folder), _item_want(item, clean.folder)


def _edit_json(rel: str, fn):
    def edit(folder: Path) -> None:
        f = folder / rel
        doc = json.loads(f.read_text(encoding="utf-8"))
        fn(doc)
        f.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return edit


def _drop_line(rel: str, pick):
    def edit(folder: Path) -> None:
        f = folder / rel
        lines = f.read_bytes()[:-1].split(b"\n")
        keep = [x for x in lines if not pick(json.loads(x))]
        assert len(keep) == len(lines) - 1, rel
        f.write_bytes(b"\n".join(keep) + b"\n")
    return edit


def _append_line(rel: str, data: bytes):
    def edit(folder: Path) -> None:
        f = folder / rel
        f.write_bytes(f.read_bytes() + data + b"\n")
    return edit


TOOL_RESULT_LINE = 3        # turn-1.jsonl's first tool_result (line index 3: init, user message, tool_use, tool_result)

# Each item's plant on a re-bound copy of w-g21, and the reason its reading must then carry. T-1 and T-6 plant on the
# reader's input (an agent turn with no output; an operator line with a leak word): on the recorded copy each of those
# is bound by the operator records and the view first (readers-disagree), so the reader itself is fed the planted
# value. T-7's plant drops the marker from turn 1's reply in the stream (the record the view reads), turn 2 still sent.
ITEM_PLANTS = {
    "T-2": ("no-session-id", (vendor_plant.edit_jsonl("turn-1.jsonl", lambda i, r: (
        {k: v for k, v in r.items() if k != "session_id"} if r.get("type") == "init" else None)),)),
    "T-3": ("readers-disagree", (_edit_json("driver-ledger.json", lambda d: d["turns"][1].update(
        sent="I read the plan file. Where will the plot be saved?")),)),
    "T-5": ("readers-disagree", (vendor_plant.replace_bytes(
        "session/native-turn-2.jsonl", "I read the plan file. Noted.", "I read the plan file. Noted. Continue."),)),
    "T-7": ("continued-past-unheld-marker", (vendor_plant.replace_bytes(
        "turn-1.jsonl", '"content":" Approve as written?"', '"content":" Shall I go ahead?"'),)),
    "T-8": ("study-materials-reached", (vendor_plant.edit_jsonl("turn-1.jsonl", lambda i, r: (
        dict(r, parameters=dict(r["parameters"], file_path="evals/gap-study-4/prereg.json"))
        if r.get("type") == "tool_use" and r.get("tool_id") == CALL else None)),)),
    "T-9": ("account-email", (vendor_plant.edit_jsonl("turn-1.jsonl", lambda i, r: (
        dict(r, output=f"owner {scrub.NOTE}") if i == TOOL_RESULT_LINE else None)),)),
    "T-15": ("model-binding", (vendor_plant.edit_jsonl("turn-2.jsonl", lambda i, r: (
        dict(r, model="gemini-3.5-flash-lite") if r.get("type") == "init" else None)),)),
    "T-16": ("inherited-context", (_edit_json("turn-2.jsonl.launch.json", lambda d: d["argv"].__setitem__(
        d["argv"].index("yolo"), "auto_edit")),)),
    "T-17": ("environment-record", (vendor_plant.replace_bytes(
        "environment.json", '"ANTHROPIC_API_KEY": "absent"', '"ANTHROPIC_API_KEY": "set"'),)),
    "T-20": ("session-binding", (vendor_plant.replace_bytes(
        "transcript.jsonl", '"vendor_session_id": "9d6e08be-586f-4143-b4bb-cfbc60d5b09c", "n": 2',
        '"vendor_session_id": "00000000-586f-4143-b4bb-cfbc60d5b09c", "n": 2'),)),
    "T-21": ("nested-agent", (_edit_json("session-store.json", lambda d: d.update(nested_cli_calls=1)),)),
    "T-23": ("transcript-unreadable", (_append_line("turn-2.jsonl", b'{"type":"progress","timestamp":"x"}'),)),
    "T-24": ("outcome-binding", (_drop_line("turn-2.jsonl", lambda r: r.get("type") == "result"),)),
}
INPUT_PLANTS = {
    "T-1": ("no-first-agent-turn", lambda: ct.vendor_first_turn_problems(
        [e for e in ct.vendor_take_view(vendor_plant.fixture_folder(G21) / "transcript.jsonl", H)["events"]
         if e.kind == ct.transcript_view.OPERATOR])),
    "T-6": ("leak-in-operator-turn", lambda: ct.vendor_leak_problems(
        [e["sent"] + " This is an eval." for e in _json_lines(vendor_plant.fixture_folder(G21) / "transcript.jsonl")],
        design_for(G21)[1].pre)),
}


def item_plant(item: str) -> list:
    reason, edits = ITEM_PLANTS[item]
    with vendor_plant.planted(G21, *edits) as p:
        got = _item_reading(item, p.path, p.folder)
    lines = got[1] if item == "T-2" else got[0] if item == "T-8" else got
    return [x for x in lines if isinstance(x, str)]


# ---- leg i (prepared for stage V) ------------------------------------------------------------------------------------
def legi_problems() -> list:
    """gemini_adapter.read_stream and end_reason on each RECORDED w-g21 turn stream, against values the test derives
    with plain json: the init's model and session id, the assistant text (consecutive delta chunks joined, runs
    joined by newlines), that the agent produced output, the tool_use ids, the result's status and stats and its
    models, one result, nothing undecoded, and end_turn on the ledger's exit 0."""
    out = []
    folder = vendor_plant.fixture_folder(G21)
    ledger = _ledger(folder)
    for k in (1, 2):
        recs = _json_lines(folder / f"turn-{k}.jsonl")
        init = [r for r in recs if r["type"] == "init"]
        result = [r for r in recs if r["type"] == "result"]
        runs, open_run = [], False
        for r in recs:
            if r["type"] == "message" and r["role"] == "assistant":
                if r.get("delta") is True and open_run:
                    runs[-1] += r["content"]
                else:
                    runs.append(r["content"])
                open_run = r.get("delta") is True
            else:
                open_run = False
        tools = [r["tool_id"] for r in recs if r["type"] == "tool_use"]
        want = {"init_model": init[0]["model"], "session_id": init[0]["session_id"], "agent_text": "\n".join(runs),
                "agent_output": bool(tools) or any(x.strip() for x in runs), "api_errors": [],
                "status": result[0]["status"], "stats": result[0]["stats"],
                "served_models": list(result[0]["stats"]["models"]), "results": len(result), "tool_ids": tools,
                "undecoded": 0}
        got = gemini_adapter.read_stream((folder / f"turn-{k}.jsonl").read_text(encoding="utf-8"), model=MODEL)
        out += [f"turn {k}: read_stream's {key} is {str(got.get(key))[:60]!r}, the stream's {str(v)[:60]!r}"
                for key, v in want.items() if got.get(key) != v]
        if sorted(got) != sorted(want):
            out.append(f"turn {k}: read_stream returns the fields {sorted(got)}")
        turn = ledger["turns"][k - 1]
        if gemini_adapter.end_reason(turn["exit"], False, got) != turn["end"]:
            out.append(f"turn {k}: end_reason is not the ledger's {turn['end']!r}")
    return out


# ---- the tests ----------------------------------------------------------------------------------------------------
class GRows(unittest.TestCase):
    def test_g_rows_the_live_map(self):
        rows = ct.VENDOR_PENDING_ROWS[H]
        for key, reader in SAME_READERS.items():
            with self.subTest(key=key):
                self.assertEqual({k: rows[key][k] for k in ("state", "reader", "fixture")},
                                 {"state": "SAME", "reader": reader, "fixture": FIXTURE})
                self.assertIsNone(ct.vendor_row_problem(H, key, rows[key]))
        for key, reader in NC_READERS.items():
            with self.subTest(key=key):
                self.assertEqual((rows[key]["state"], rows[key]["reader"]), ("NOT COMPARABLE", reader))
                self.assertEqual(hashlib.sha256(rows[key]["ruling"].encode("utf-8")).hexdigest(), RULING_SHA256[key])
                self.assertIsNone(ct.vendor_row_problem(H, key, rows[key]))
        self.assertEqual(ct.vendor_rows_problems(H), [])
        self.assertEqual(ct.VENDOR_CHECK_SHAPES_SOURCE[H], "recorded")       # stage V flipped it

    def test_g_rows_every_item_names_the_recorded_fixture(self):
        self.assertEqual(ct.VENDOR_READER_ITEMS[H], dict.fromkeys(ITEMS, FIXTURE))
        self.assertEqual(ct.vendor_reader_items_problems(H), [])

    def test_g_rows_the_cases_are_whole(self):
        self.assertEqual(sorted(k for _, k in SAME_FIRES), sorted(SAME_READERS))
        self.assertEqual(sorted(k for _, k in NC_CASES), sorted(NC_READERS))
        self.assertEqual(sorted(k for _, k in CLEAN_CASES), sorted({**SAME_READERS, **NC_READERS}))


class GCases(unittest.TestCase):
    def test_g_same_fires(self):
        for (h, key), fire in SAME_FIRES.items():
            with self.subTest(key=key):
                got = fire(ct.HERE / "tests" / "fixtures" / FIXTURE)
                self.assertTrue(got)
                self.assertTrue(all(x.startswith(f"[{ct.VENDOR_PENDING_ROWS[h][key]['reason']}] ") for x in got), got)

    def test_g_clean_cases(self):
        for key, case in CLEAN_CASES.items():
            with self.subTest(key=key):
                got, want = case()
                self.assertEqual(got, want)
                self.assertEqual(want, [])

    def test_g_nc_t17_credential_source_counts_the_turns(self):
        # Gemini review 0df1437 NIT: the credential leg ties its per_turn entries to the walk's turn count
        old = ',\n      {\n        "n": 2,\n        "recovery": false,\n        "exit": 0,\n        "apiKeySource": null\n      }'
        with vendor_plant.planted(G21, vendor_plant.replace_bytes("environment.json", old, "")) as plant:
            got = ct.vendor_gemini_billing_route_partial(plant.path)
        self.assertEqual(len(got), 1, got)
        self.assertTrue(got[0].startswith("[environment-record] ") and "turn" in got[0], got)

    def test_g_nc_t17_credential_source_leg(self):
        # stage V, glitch-f1's amendment of both T-17 rulings: a non-null credential_source on one vendor turn, and a
        # reported one, each fires the credential line alone; the clean copy carries none
        with vendor_plant.planted(G21) as clean:
            self.assertEqual(ct.vendor_gemini_billing_route_partial(clean.path), [])
        for old, new in (('"n": 2,\n        "recovery": false,\n        "exit": 0,\n        "apiKeySource": null',
                          '"n": 2,\n        "recovery": false,\n        "exit": 0,\n        "apiKeySource": "oauth"'),
                         ('"reported": null', '"reported": "oauth"')):
            with self.subTest(plant=new[-40:]), vendor_plant.planted(G21, vendor_plant.replace_bytes(
                    "environment.json", old, new)) as plant:
                got = ct.vendor_gemini_billing_route_partial(plant.path)
                self.assertEqual(len(got), 1, got)
                self.assertTrue(got[0].startswith("[environment-record] ") and "credential_source" in got[0], got)
            with self.subTest(hollow=new[-40:]), vendor_plant.planted(G21, vendor_plant.replace_bytes(
                    "environment.json", old, new)) as plant, \
                    mock.patch.object(ct, "vendor_credential_source_problems", lambda *a, **k: []):
                self.assertEqual(ct.vendor_gemini_billing_route_partial(plant.path), [])

    def test_g_nc_cases(self):
        for (h, key), case in NC_CASES.items():
            with self.subTest(key=key):
                got = case()
                reason = ct.VENDOR_PENDING_ROWS[h][key]["reason"]
                self.assertTrue(got)
                self.assertTrue(all(x.startswith(f"[{reason}] ") for x in got), got)


# The whole check's added reasons per SAME plant: the row's own and the declared siblings (the same context record is
# read by T-12:offered-context's partial and T-12:instruction-files; MINOR 5's reach reads the workspace directory).
SCOPE_SIBLINGS = {"T-4": ("inherited-context", "read-outside-the-checkout"),
                  "T-10": (), "T-11": ("readers-disagree", "read-outside-the-checkout"),
                  "T-12:instruction-files": (), "T-14": ()}


class GScope(unittest.TestCase):
    def test_g_scope_whole_check(self):
        with vendor_plant.planted(G21) as clean:
            base = whole_check(G21, clean.path)
        for key, siblings in SCOPE_SIBLINGS.items():
            with self.subTest(key=key), vendor_plant.planted(G21, *PLANTS[key]) as p:
                got = whole_check(G21, p.path)
                reason = ct.VENDOR_PENDING_ROWS[H][key]["reason"]
                self.assertEqual(vendor_plant.plant_scope_problems(base, got, reason, siblings), [])


def timeline_only_versions(path):
    """MUTANT: the context versions the replay's timeline holds, as the design's first reading took them."""
    raw_bytes = ct._vendor_last_snapshot(path, ct._gemini_ledger(path))
    replayed = gemini_session_replay.replay(raw_bytes)
    return [(f"timeline {m.get('id')}", t) for m in replayed["timeline"] if m.get("type") == "user"
            for t in ct._gemini_context_parts(m.get("content"))]


def plant_first() -> tuple:
    """A second workspace directory in the first write only (line 2 of every snapshot), the version both resumes
    wrote over: the edit is made on that record's own text, in every snapshot, re-serialised in its style."""
    def fn(i, rec):
        if i != 1 or rec.get("type") != "user":
            return None
        text = rec["content"][0]["text"]
        tree = own_facts(text)["dirs"][0]
        new = text.replace(f"\n  - {tree}\n", f"\n  - {tree}\n  - /opt/extra\n", 1)
        assert new != text
        return dict(rec, content=[dict(rec["content"][0], text=new)] + rec["content"][1:])
    return tuple(vendor_plant.edit_jsonl(rel, fn) for rel in SNAPS[G14])


def plant_second() -> tuple:
    """A leak word after an escaped newline in the version the first resume wrote (the $patch update of the context
    message, line 147), in every snapshot holding it; no other version carries it."""
    def fn(i, rec):
        patch = rec.get("$patch")
        if i != 146 or not isinstance(patch, dict):
            return None
        update = patch["updates"][0]
        text = update["content"][0]["text"]
        assert text.startswith(CONTEXT_OPEN)
        new = text.replace("\nMy operating system is: linux", "\nGap study. My operating system is: linux", 1)
        assert new != text
        updates = [dict(update, content=[dict(update["content"][0], text=new)] + update["content"][1:])]
        return dict(rec, **{"$patch": dict(patch, updates=updates + patch["updates"][1:])})
    have = [rel for rel in SNAPS[G14]
            if len((vendor_plant.fixture_folder(G14) / rel).read_bytes().split(b"\n")) > 147]
    return tuple(vendor_plant.edit_jsonl(rel, fn) for rel in have)


class GVersions(unittest.TestCase):
    """MAJOR 1 on w-g14."""

    def test_g_versions_every_version_is_read(self):
        with vendor_plant.planted(G14) as clean:
            got = ct.gemini_context_versions(clean.path)
            own = own_context_texts(clean.folder)
            self.assertEqual([t for _, t in got], own)
            self.assertEqual(len(got), 4)
            self.assertEqual([w for w, _ in got], ["line 2", "line 147 ($patch update 1)",
                                                   "line 430 ($patch update 1)", "line 517"])
            self.assertEqual(len(timeline_only_versions(clean.path)), 1)
            # a $patch update of a model message carries thoughts; none is read as context
            patches = [r["$patch"] for r in _json_lines(own_last_snapshot(clean.folder)) if "$patch" in r]
            thoughts = [p for u in sorted(patches, key=str) for x in u.get("updates", [])
                        for p in x.get("content", []) if isinstance(p, dict) and p.get("thought")]
            self.assertTrue(thoughts)
            self.assertFalse(any(t["text"].startswith(CONTEXT_OPEN) for t in thoughts))

    def test_g_versions_a_plant_in_the_overwritten_version_fires_and_the_timeline_mutant_misses_it(self):
        _, design = design_for(G14)
        with vendor_plant.planted(G14, *plant_first()) as p:
            live = ct.vendor_gemini_cwd_reads(p.path) + ct.vendor_gemini_run_tree_reads(p.path, design)
            self.assertTrue(any(x.startswith("[inherited-context] ") for x in live), live)
            self.assertTrue(any(x.startswith("[readers-disagree] ") for x in live), live)
            self.assertTrue(ct.vendor_gemini_offered_partial(p.path))
            with mock.patch.object(ct, "gemini_context_versions", timeline_only_versions):
                self.assertEqual(ct.vendor_gemini_cwd_reads(p.path) + ct.vendor_gemini_run_tree_reads(p.path, design),
                                 [])


class GDecoded(unittest.TestCase):
    """MAJOR 3: the leak word after an escaped newline (the T-10 plant) is read; the raw-line sweep misses it."""

    def test_g_decoded_the_raw_line_mutant_misses_the_word(self):
        _, design = design_for(G21)
        with vendor_plant.planted(G21, *PLANTS["T-10"]) as p:
            self.assertEqual(ct.vendor_gemini_loaded_context_reads(p.path, design)[:1][0].split("]")[0],
                             "[leak-in-loaded-context")
            raw_text = own_last_snapshot(p.folder).read_text(encoding="utf-8").lower()
            self.assertIn("\\ngap study.", raw_text)
            self.assertEqual(ct.context_leaks(raw_text, design.pre) & {"gap study"}, set())   # the raw sweep is blind


def _returns_nothing(*args, **kwargs):
    return []


class GMutants(unittest.TestCase):
    def test_g_mutants_a_same_reader_returning_nothing_goes_red(self):
        for key, name in SAME_READERS.items():
            with self.subTest(key=key), mock.patch.object(ct, name, _returns_nothing):
                with self.assertRaises(Exception):
                    SAME_FIRES[(H, key)](ct.HERE / "tests" / "fixtures" / FIXTURE)

    def test_g_mutants_a_partial_check_returning_nothing_goes_red(self):
        for key, name in NC_READERS.items():
            with self.subTest(key=key), mock.patch.object(ct, name, _returns_nothing):
                self.assertEqual(NC_CASES[(H, key)](), [])

    def test_g_mutants_reading_one_version_only_goes_red(self):
        _, design = design_for(G14)
        original = ct.gemini_context_versions
        mutants = {"the replay's timeline only": timeline_only_versions,
                   "the first version only": lambda path: original(path)[:1],
                   "the last version only": lambda path: original(path)[-1:]}
        # a leak word planted only in the version the first resume wrote ($patch update, line 147): all three miss it
        with vendor_plant.planted(G14, *plant_second()) as p:
            self.assertTrue(ct.vendor_gemini_loaded_context_reads(p.path, design))
            for name, mutant in mutants.items():
                with self.subTest(mutant=name), mock.patch.object(ct, "gemini_context_versions", mutant):
                    self.assertEqual(ct.vendor_gemini_loaded_context_reads(p.path, design), [])
        # a second directory planted only in the first write: the timeline and last-version mutants miss it
        with vendor_plant.planted(G14, *plant_first()) as p:
            self.assertTrue(ct.vendor_gemini_cwd_reads(p.path))
            for name in ("the replay's timeline only", "the last version only"):
                with self.subTest(mutant=name), mock.patch.object(ct, "gemini_context_versions", mutants[name]):
                    self.assertEqual(ct.vendor_gemini_cwd_reads(p.path), [])


class GUnread(unittest.TestCase):
    """A snapshot the ledger's digest does not bind is never read as a context: every context reader refuses it as
    transcript-unreadable (as the codex readers refuse an unreadable rollout), and the session's cwd reads None."""

    def test_g_unread_an_unbound_snapshot_refuses(self):
        _, design = design_for(G21)
        with vendor_plant.planted(G21, *PLANTS["T-14"], rebind_digests=False) as p:
            got = []
            for key, name in {**SAME_READERS, **NC_READERS}.items():
                if key in ("T-17:billing-route", "T-12:prompt-snapshot"):
                    continue                  # input-side and environment-record legs: no snapshot read
                reader = getattr(ct, name)
                lines = reader(p.path, design) if key in ("T-4", "T-10", "T-14") else reader(p.path)
                with self.subTest(key=key):
                    self.assertTrue(lines)
                    self.assertTrue(all(x.startswith("[transcript-unreadable] ") for x in lines), lines)
                got += lines
            self.assertIsNone(ct.vendor_session_cwd(p.path, H))


class GReach(unittest.TestCase):
    def test_g_reach_reads_the_recorded_workspace_directory(self):
        with vendor_plant.planted(G21) as clean:
            self.assertEqual(ct.vendor_session_cwd(clean.path, H), TREE21)
            self.assertEqual(ct.vendor_reach(clean.path, H, run_tree=TREE21)["problems"], [])
            old = ct.vendor_reach(clean.path, H, run_tree=None)
            self.assertEqual(len(old["outside"]), 102)
            self.assertEqual([x.split("]")[0] for x in old["problems"]], ["[read-outside-the-checkout"])


class GItems(unittest.TestCase):
    def test_g_items_clean_readings_equal_the_independent_values(self):
        for item in ITEMS:
            with self.subTest(item=item):
                got, want = item_case(item)
                self.assertEqual(got, want)

    def test_g_items_each_plant_fires_its_reason(self):
        for item, (reason, _) in ITEM_PLANTS.items():
            with self.subTest(item=item):
                got = item_plant(item)
                self.assertTrue(any(x.startswith(f"[{reason}] ") for x in got), got)
        for item, (reason, fn) in INPUT_PLANTS.items():
            with self.subTest(item=item):
                got = fn()
                self.assertTrue(any(x.startswith(f"[{reason}] ") for x in got), got)
        self.assertEqual(sorted(set(ITEM_PLANTS) | set(INPUT_PLANTS)), sorted(ITEMS))


# ---- T-7, Gemini delta chunks (glitch-f1's ruling on stage G's hand-back, stage V) ---------------------------------
# The bound view writes each assistant delta chunk as its own agent-text event (transcript_gemini.py, a READER_SOURCES
# file, unchanged), so continuation_problems, which joins agent texts with newlines, read a marker the CLI streamed
# across two chunks as absent: a false [continued-past-unheld-marker] on w-g14 turn 1 while its ledger says held.
# Ruled: check_take joins one message's delta chunks as gemini_adapter.read_stream does (no separator), for
# continuation_problems only.
T7_SPLIT_WALKS = ("w-g14", "w-g31", "w-g39")       # stage G's survey: the three turns whose marker spans two chunks


def walk_check(walk: str) -> list:
    """vendor_check and vendor_round4_problems on the committed walk folder rehearsals/<walk> (read in place, never
    written), through the walk road, as whole_check runs a RECORDED copy."""
    folder = HERE / "rehearsals" / walk
    register = json.loads((HERE / "rehearsals" / "register.json").read_text(encoding="utf-8"))
    entry = [e for e in register["walks"] if e.get("walk") == walk]
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    row = dict(run_mod.walk_row(entry[0], ledger), walk=walk, slot=walk)
    tree = json.loads((folder / "turn-1.jsonl.launch.json").read_text(encoding="utf-8"))["cwd"]
    design = walk_regrade.production_design(row, tree)
    path = folder / "transcript.jsonl"
    out = ct.vendor_check(path, row["task"], row["half"], None, wording_script=design.script, design=design,
                          arm=row["arm"], walk_id=row["walk"])
    return out + ct.vendor_round4_problems(path, design, arm=row["arm"])


# ---- one plant per published leg (Gemini review 0df1437 MINOR 2): each fires through its leg alone ----------------
def _settings_patch(change):
    tc = ct._settle_g_take_config
    real = tc.files_for

    def files_for(harness, **kw):
        out = dict(real(harness, **kw))
        doc = json.loads(out[tc.GEMINI_SETTINGS_PATH])
        change(doc)
        out[tc.GEMINI_SETTINGS_PATH] = json.dumps(doc).encode("utf-8")
        return out
    return mock.patch.object(tc, "files_for", files_for)


def _refused_without(name):
    real = ct._settle_g_run_take.refused_variables
    return mock.patch.object(ct._settle_g_run_take, "refused_variables", lambda h: set(real(h)) - {name})


def _sub_in_snapshots(pattern, repl):
    """A regex substitution in every retained snapshot of w-g21 (at least one change in each)."""
    def edit(folder):
        for rel in SNAPS[G21]:
            f = folder / rel
            data = f.read_text(encoding="utf-8")
            new = re.sub(pattern, repl, data)
            if new == data:
                raise vendor_plant.PlantRefused(f"{rel}: {pattern} not found")
            f.write_text(new, encoding="utf-8")
    return edit


def _journal(k, change):
    def edit(folder):
        f = folder / f"turn-{k}.jsonl.launch.json"
        doc = json.loads(f.read_text(encoding="utf-8"))
        change(doc)
        f.write_text(json.dumps(doc, separators=(",", ":")) + "\n", encoding="utf-8")
    return edit


@contextlib.contextmanager
def _constant_only():
    """The pinned constant changed while the built settings stay the real ones (files_for reads the constant, so it is
    held at its unpatched output): the constant leg alone."""
    tc = ct._settle_g_take_config
    real = tc.files_for
    cache = {}

    def files_for(harness, **kw):
        key = (harness, tuple(sorted(kw.items())))
        if key not in cache:
            with mock.patch.object(tc, "GEMINI_AUTH_SETTING", GEMINI_AUTH_REAL):
                cache[key] = real(harness, **kw)
        return cache[key]
    with mock.patch.object(tc, "files_for", files_for), mock.patch.object(
            tc, "GEMINI_AUTH_SETTING", {"path": "security.auth.selectedType", "value": "oauth-personal"}):
        yield


GEMINI_AUTH_REAL = dict(ct._settle_g_take_config.GEMINI_AUTH_SETTING)
HC = ct.HARNESS_CONDITION_VIOLATED
# (leg, reason, reader(path, design) -> problems, plant edits, a patch context factory or None)
G_LEG_PLANTS = [
    ("T-17: the pinned auth setting is not the API key (the constant)", "environment-record",
     lambda p, d: ct.vendor_gemini_billing_route_partial(p), [], lambda: _constant_only()),
    ("T-17: the built settings select another auth type", "environment-record",
     lambda p, d: ct.vendor_gemini_billing_route_partial(p), [],
     lambda: _settings_patch(lambda doc: doc["security"]["auth"].update(selectedType="oauth-personal"))),
    ("T-18: web_fetch missing from the pinned exclude list", HC,
     lambda p, d: ct.vendor_gemini_tools_partial(p), [],
     lambda: _settings_patch(lambda doc: doc["tools"].update(
         exclude=[x for x in doc["tools"]["exclude"] if x != "web_fetch"]))),
    ("T-18: a denied tool in the turn stream alone", HC,
     lambda p, d: ct.vendor_gemini_tools_partial(p), [_rename_edit("turn-1.jsonl", True)], None),
    # the session's copies alone (toolCalls, functionCall and functionResponse; the stream untouched): the projection
    # refuses a session whose toolCalls entry and functionCall part disagree (a single-copy rename reads
    # transcript-unreadable), so the two session legs always see a denied call together
    ("T-18: a denied tool in the session's copies alone", HC,
     lambda p, d: ct.vendor_gemini_tools_partial(p), [_rename_edit(rel, False) for rel in SNAPS[G21]], None),
    ("T-18: a single session copy renamed is refused upstream (fail-closed)", "transcript-unreadable",
     lambda p, d: ct.vendor_gemini_tools_partial(p),
     [_sub_in_snapshots(r'(?<!"functionCall":)\{"id":"' + CALL + r'","name":"read_file","args"',
                        '{"id":"' + CALL + '","name":"web_fetch","args"')], None),
    ("T-12:memory: the pinned settings carry a context block", "inherited-context",
     lambda p, d: ct.vendor_gemini_memory_partial(p), [],
     lambda: _settings_patch(lambda doc: doc.update(context={"fileName": ["MEMORY.md"]}))),
    ("T-12:memory: a loaded file outside the workspace directory", "inherited-context",
     lambda p, d: ct.vendor_gemini_memory_partial(p),
     list(in_snapshots(G21, f"Context from: {TREE21}/GEMINI.md ---", "Context from: /opt/cfg/.gemini/GEMINI.md ---",
                       count=2)), None),
    ("T-12:prompt-snapshot: GEMINI_SYSTEM_MD out of the refused set", "inherited-context",
     lambda p, d: ct.vendor_gemini_prompt_partial(p, d), [], lambda: _refused_without("GEMINI_SYSTEM_MD")),
    ("T-12:prompt-snapshot: a launch argv the adapter never writes", "inherited-context",
     lambda p, d: ct.vendor_gemini_prompt_partial(p, d),
     [_journal(1, lambda doc: doc["argv"].extend(["--extra-flag"]))], None),
    ("T-4: the listing root alone", "readers-disagree",
     lambda p, d: ct.vendor_gemini_run_tree_reads(p, d),
     list(in_snapshots(G21, raw(f"\n\n{TREE21}/\n"), raw("\n\n/tmp/run-0f0f0f0f/\n"))), None),
    ("T-4: one launch journal's cwd alone", "readers-disagree",
     lambda p, d: ct.vendor_gemini_run_tree_reads(p, d), [_journal(2, lambda doc: doc.update(cwd="/tmp/other"))], None),
]


class GPromptSwitches(unittest.TestCase):
    def test_g_prompt_section_switch_in_the_launch_environment_fires(self):
        # glitch-f1's stage Z (1), GEMINI-S0-READ: isSectionEnabled reads GEMINI_PROMPT_<SECTION> and drops that section
        # on 0 or false ([C] 336004-336008); names built at run time, so a prefix test beside the two literal names
        _, design = design_for(G21)
        with vendor_plant.planted(G21) as clean:
            self.assertEqual(ct.vendor_gemini_prompt_partial(clean.path, design), [])
            with mock.patch.dict(run_take.TAKE_ENV[H], {"GEMINI_PROMPT_COREMANDATES": "0"}):
                got = ct.vendor_gemini_prompt_partial(clean.path, design)
        self.assertTrue(got and all(x.startswith("[inherited-context] ") for x in got), got)
        self.assertTrue(any("GEMINI_PROMPT_COREMANDATES" in x for x in got), got)
        # GEMINI_WRITE_SYSTEM_MD is the prompt-dump variable, never called an override
        with vendor_plant.planted(G21) as clean, mock.patch.dict(run_take.TAKE_ENV[H], {"GEMINI_WRITE_SYSTEM_MD": "1"}):
            got = ct.vendor_gemini_prompt_partial(clean.path, design)
        self.assertTrue(got and not any("replaces Gemini CLI's system prompt" in x for x in got), got)


def _tool_use_plant(name, params):
    """A tool_use record (and its tool_result) appended to w-g21's turn-1 stream, the envelope re-bound by the plant."""
    def edit(folder):
        f = folder / "turn-1.jsonl"
        recs = [json.loads(x) for x in f.read_text(encoding="utf-8").split("\n") if x.strip()]
        ts = recs[0].get("timestamp")
        at = max(i for i, r in enumerate(recs) if r.get("type") == "tool_result") + 1
        recs[at:at] = [{"type": "tool_use", "timestamp": ts, "tool_name": name, "tool_id": "plant_call_1",
                        "parameters": params},
                       {"type": "tool_result", "timestamp": ts, "tool_id": "plant_call_1", "status": "success",
                        "output": "ok"}]
        f.write_text("".join(json.dumps(r, separators=(",", ":")) + "\n" for r in recs), encoding="utf-8")
    return edit


class GMemoryWrites(unittest.TestCase):
    """glitch-f1's stage Z (2b), GEMINI-S0-READ: 0.64.0 has no memory tool and saves memory by editing files
    ([C] 335872), so the count is of write_file, replace and run_shell_command calls naming GEMINI.md outside the
    workspace or /memory/ under the config folder (check_take.gemini_memory_file_writes)."""

    def test_g_memory_writes_count_the_calls_that_name_a_memory_file(self):
        with vendor_plant.planted(G21) as clean:
            self.assertEqual(ct.gemini_memory_file_writes(clean.path), [])
        cases = {
            "write_file to the config folder's GEMINI.md": ("write_file", {"file_path": "/opt/cfg/.gemini/GEMINI.md",
                                                                           "content": "x"}, 1),
            "replace in the home-relative GEMINI.md": ("replace", {"file_path": "~/.gemini/GEMINI.md", "old_string": "a",
                                                                   "new_string": "b"}, 1),
            "a shell write into the project memory folder": (
                "run_shell_command", {"command": "echo x >> /opt/cfg/.gemini/tmp/run-752c6e21/memory/MEMORY.md"}, 1),
            "the workspace's own GEMINI.md": ("replace", {"file_path": f"{TREE21}/GEMINI.md", "old_string": "a",
                                                          "new_string": "b"}, 0),
            "a relative GEMINI.md (inside the workspace)": ("write_file", {"file_path": "gars/GEMINI.md",
                                                                          "content": "x"}, 0),
        }
        for what, (name, params, want) in cases.items():
            with self.subTest(case=what), vendor_plant.planted(G21, _tool_use_plant(name, params)) as plant:
                self.assertEqual(len(ct.gemini_memory_file_writes(plant.path)), want)


class GTexts(unittest.TestCase):
    """The adopted texts' legs (Gemini text review): T-12:memory's "no memory-file write" and T-17's launch-environment
    and refused-set legs, each with a firing plant."""

    def test_g_texts_memory_partial_counts_a_memory_file_write(self):
        write = _tool_use_plant("write_file", {"file_path": "/opt/cfg/.gemini/GEMINI.md", "content": "Remember x."})
        with vendor_plant.planted(G21, write) as plant:
            got = ct.vendor_gemini_memory_partial(plant.path)
        self.assertTrue(got and all(x.startswith("[inherited-context] ") for x in got), got)
        self.assertTrue(any("GEMINI.md" in x for x in got), got)

    def test_g_texts_t17_launch_environment_and_refused_set_legs_fire(self):
        names = sorted(ct._settle_g_run_take.VENDOR_BILLING_ROUTE_VARIABLES["gemini"])
        name = "GOOGLE_GENAI_USE_VERTEXAI" if "GOOGLE_GENAI_USE_VERTEXAI" in names else names[0]
        with vendor_plant.planted(G21) as clean:
            self.assertEqual(ct.vendor_gemini_billing_route_partial(clean.path), [])
            with mock.patch.dict(run_take.TAKE_ENV[H], {name: "true"}):
                got = ct.vendor_gemini_billing_route_partial(clean.path)
            self.assertEqual(len(got), 1, got)
            self.assertTrue(got[0].startswith("[environment-record] the launch environment carries"), got)
            with _refused_without(name):
                got = ct.vendor_gemini_billing_route_partial(clean.path)
            self.assertEqual(len(got), 1, got)
            self.assertTrue(got[0].startswith("[environment-record] the refused set misses"), got)


class GLegs(unittest.TestCase):
    """Gemini review 0df1437 MINOR 2: each leg a published text names fires alone on its own scratch copy."""

    def test_g_legs_each_plant_fires_through_its_leg(self):
        _, design = design_for(G21)
        with vendor_plant.planted(G21) as clean:
            for name, reason, read, edits, patch in G_LEG_PLANTS:
                self.assertEqual(read(clean.path, design), [], name)
        for name, reason, read, edits, patch in G_LEG_PLANTS:
            with self.subTest(leg=name), contextlib.ExitStack() as stack:
                if patch is not None:
                    stack.enter_context(patch())
                plant = stack.enter_context(vendor_plant.planted(G21, *edits))
                got = read(plant.path, design)
                self.assertTrue(got, f"{name}: the plant reads clean")
                self.assertTrue(all(x.startswith(f"[{reason}] ") for x in got), got)


class GLegsW14(unittest.TestCase):
    """Gemini closure MINOR C1: the session toolCalls leg of T-18 is not equivalent. 2,222 of the walks' 2,744 session
    toolCalls entries carry no functionCall part; on the RECORDED w-g14 copy, read_file__call_710162 is one (last
    snapshot only), so a denied name planted in its session copies (the stream untouched) is accepted by the projection
    and caught only through the toolCalls leg."""

    def test_g_legs_an_unpaired_session_toolcalls_entry_fires(self):
        call = "read_file__call_710162"
        rename = vendor_plant.replace_bytes(
            "session/native-turn-4.jsonl", f'"id":"{call}","name":"read_file"', f'"id":"{call}","name":"web_fetch"',
            count=3)
        with vendor_plant.planted(G14) as clean:
            self.assertEqual(ct.vendor_gemini_tools_partial(clean.path), [])
        with vendor_plant.planted(G14, rename) as plant:
            self.assertEqual(ct.vendor_take_view(plant.path, H)["problems"], [])
            where = [w for w, n in ct._gemini_called_names(plant.path) if n == "web_fetch"]
            got = ct.vendor_gemini_tools_partial(plant.path)
        self.assertEqual([w.split(" ")[-1] for w in where], ["toolCalls"])      # that leg alone reads it
        self.assertTrue(got and all(x.startswith(f"[{HC}] ") for x in got), got)


class GConstants(unittest.TestCase):
    def test_g_constants_read_the_mode_from_the_launch_argv(self):
        # stage V ruling (c): T-24's permission-mode leg reads every turn's launch argv (mode_binding.argv_mode, input
        # side), never the ledger's "unrecorded" (all 36 Gemini ledgers); a journal's mode flag removed fires
        _, design = design_for(G21)
        with vendor_plant.planted(G21) as clean:
            ledger = _ledger(clean.folder)
            self.assertEqual(ledger["permission_mode"], "unrecorded")
            self.assertEqual(ct.vendor_constant_problems(clean.path, H, ledger, design.pre), [])
            self.assertFalse([p for p in whole_check(G21, clean.path) if "permission mode" in p])
        with vendor_plant.planted(G21, vendor_plant.replace_bytes("turn-1.jsonl.launch.json", ',"--approval-mode","yolo"]', ']')) as p:
            got = ct.vendor_constant_problems(p.path, H, ledger, design.pre)
        self.assertTrue(got and all(x.startswith("[constant-binding] ") and "input side" in x for x in got), got)


class GT7(unittest.TestCase):
    def test_g_t7_a_marker_split_across_delta_chunks_reads_held(self):
        for walk in T7_SPLIT_WALKS:
            with self.subTest(walk=walk):
                ledger = json.loads((HERE / "rehearsals" / walk / "driver-ledger.json").read_text(encoding="utf-8"))
                self.assertTrue(ledger["turns"][0]["held"])                       # the driver saw it held
                self.assertEqual([p for p in walk_check(walk) if p.startswith("[continued-past-unheld-marker]")],
                                 [])
        with vendor_plant.planted(G14) as clean:
            self.assertEqual(stop_and_marker_problems(G14, clean.path), [])
            # witness: the join dropped (the view's turns handed on) is the false line again
            with mock.patch.object(ct, "vendor_continuation_turns", lambda path, harness, turns: turns):
                self.assertTrue(any(p.startswith("[continued-past-unheld-marker]")
                                    for p in stop_and_marker_problems(G14, clean.path)))
            # the joined reply holds the marker the ledger expects (the two chunks read as one text)
            joined = ct.vendor_continuation_turns(clean.path, H, ct._vendor_turns(
                ct.vendor_take_view(clean.path, H)["events"] or []))
            self.assertTrue(any("Reply with a comma-separated list of IDs" in t["text"] for t in joined
                                if t["role"] == "assistant"))
            self.assertEqual(ct.vendor_continuation_turns(clean.path, "codex", ["x"]), ["x"])
            # Gemini review 0df1437 MINOR 1: a view whose agent texts are not the chunks one for one comes back as it is
            view = ct._vendor_turns(ct.vendor_take_view(clean.path, H)["events"] or [])
            off = [dict(t, text=t["text"] + " (edited)") if t["role"] == "assistant" else t for t in view]
            self.assertEqual(ct.vendor_continuation_turns(clean.path, H, off), off)
            short = [t for t in view if not (t["role"] == "assistant" and t is view[-1])]
            self.assertEqual(ct.vendor_continuation_turns(clean.path, H, short), short)


class GLegI(unittest.TestCase):
    def test_g_legi_read_stream_on_the_recorded_streams(self):
        self.assertEqual(legi_problems(), [])
        self.assertEqual(gemini_adapter.SHAPES_SOURCE, "recorded")           # stage V flipped it


if __name__ == "__main__":
    unittest.main()
