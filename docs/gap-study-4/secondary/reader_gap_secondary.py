#!/usr/bin/env python3
"""OD201's pre-registered secondary (sensitivity) analysis of the reader gap, on branch analysis/reader-gap-secondary
only, never on the line (plans/gap-study-4-reader-gap-sensitivity-PREREG-20261108.md, items 2 to 5).

    python3 -B -P reader_gap_secondary.py grades  --tree <checkout> [--secondary] --out <grades.json>
    python3 -B -P reader_gap_secondary.py compare --frozen <grades.json> --patched <grades.json> --out <check.json>
    python3 -B -P reader_gap_secondary.py report  --tree <this branch> --check <check.json> --attempt1 <check.json>
                                                  --shapes <shapes-detail.json> --base <sha> --out <SECONDARY.md>
                                                  --frozen-grades <grades.json> --patched-grades <grades.json>

The patched reader is the frozen claude-code parser plus four shapes (transcript_view_secondary.py), installed into
transcript_view.PARSERS at runtime by --secondary (and always by `report`); transcript_view.py is never edited, so the
native-reader acceptance records still bind the frozen sources (glitch-34's ruling, option 1, 13 Nov 2026).
`grades` grades every committed take that has a registered row with run.grade_committed, in the checkout named (the
frozen parser, or with --secondary the patched one), and writes each take's grade as the sha256 of
its canonical bytes (graded_by made study-relative, so two checkouts compare), or the exception type it raised.
`compare` is item 3, the blind check: every take the frozen reader could read must have a byte-identical grade under the
patched reader; it prints only how many takes were compared and how many differ. `report` is items 2, 4 and 5: the
takes ruled aborted with a cite starting "end state unreadable: ViewError" (and no others) are regraded with the patched
reader, their rulings routed graded in a copy of the history held in memory (nothing committed is changed), the results
are produced through the same run.produce and result.from_records the primary uses, and SECONDARY.md shows the primary
and secondary results side by side. The script imports the study modules from --tree alone (its own folder is removed
from sys.path), so the frozen run reads the frozen reader. No model is called. Standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

UNREAD_VIEW = "end state unreadable: ViewError"
SHAPE_NAMES = (   # the frozen reader's refusal, by the words that open it, to the plan item 1 shape it is
    ("tool 'Write': argument keys with no entry: ['file_text']", "Write.file_text"),
    ("tool name with no entry in the parser's table: 'Skill'", "Skill call"),
    ("a record carrying isMeta", "Skill companion (isMeta turnCompanion record)"),
    ("unknown attachment type: 'command_permissions'", "command_permissions attachment"),
)


def load(tree, secondary: bool = False):
    """Import the study modules from `tree` only; returns (study dir, modules). With `secondary`, the patched
    claude-code parser (transcript_view_secondary) is installed into transcript_view.PARSERS at runtime;
    transcript_view.py itself is never edited, so the native-reader acceptance records still bind the frozen sources."""
    me = Path(__file__).resolve().parent
    sys.path[:] = [p for p in sys.path if p and Path(p).resolve() != me]
    study = Path(tree).resolve() / "evals" / "gap-study-4"
    sys.path.insert(0, str(study))
    import batch
    import prereg
    import result
    import run
    import stats
    import takes
    import transcript_view
    from graders import labels4
    for mod in (run, transcript_view, takes, result):
        if Path(mod.__file__).resolve().parent != study:
            raise SystemExit(f"{mod.__name__} loaded from {mod.__file__}, not from {study}")
    sec = None
    if secondary:
        import transcript_view_secondary as sec
        if Path(sec.__file__).resolve().parent != study or sec.tv is not transcript_view:
            raise SystemExit("transcript_view_secondary is not this tree's, or reads another transcript_view")
        sec.install()
        if not isinstance(transcript_view.PARSERS["claude-code"], sec.SecondaryClaudeCodeParser):
            raise SystemExit("the patched claude-code parser is not installed")
    return study, dict(batch=batch, prereg=prereg, result=result, run=run, stats=stats, takes=takes,
                       tv=transcript_view, labels4=labels4, sec=sec)


def parser_identity(m) -> dict:
    sec = m["sec"]
    return {"parser": "secondary" if sec else "frozen",
            "reader_sha256": hashlib.sha256(Path(m["tv"].__file__).read_bytes()).hexdigest(),
            "secondary_module_sha256": hashlib.sha256(Path(sec.__file__).read_bytes()).hexdigest() if sec else None,
            "installed_parser": type(m["tv"].PARSERS["claude-code"]).__name__}


def canonical(grade: dict, study: Path) -> bytes:
    g = dict(grade)
    if isinstance(g.get("graded_by"), str):
        g["graded_by"] = Path(g["graded_by"]).resolve().relative_to(study.resolve()).as_posix()
    return json.dumps(g, sort_keys=True, ensure_ascii=False).encode("utf-8")


def keyname(key) -> str:
    return f"{key[0]}/{key[1]}"


def cmd_grades(args) -> int:
    study, m = load(args.tree, secondary=args.secondary)
    rows, history = m["takes"].load_rows(), m["takes"].read_history()
    registered = {(r["slot"], r["attempt"]): r for r in rows}
    out = {}
    for o in history:
        if not m["batch"].is_outcome(o):
            continue
        key = (o["slot"], o["attempt"])
        if key not in registered or keyname(key) in out:
            continue
        try:
            got = m["run"].grade_committed(registered[key], o)
            out[keyname(key)] = {"sha256": hashlib.sha256(canonical(got, study)).hexdigest(), "raised": None}
        except Exception as e:  # noqa: BLE001  a take this reader cannot grade is recorded by its exception type
            out[keyname(key)] = {"sha256": None, "raised": type(e).__name__,
                                 "view_error": type(e).__name__ == "ViewError"}
    Path(args.out).write_text(json.dumps(dict(parser_identity(m), tree=str(Path(args.tree).resolve()), grades=out),
                                         indent=1, sort_keys=True) + "\n")
    print(f"grades: wrote {args.out}")
    return 0


def cmd_compare(args) -> int:
    a = json.loads(Path(args.frozen).read_text())
    b = json.loads(Path(args.patched).read_text())
    if (a["parser"], b["parser"]) != ("frozen", "secondary") or b["installed_parser"] == a["installed_parser"]:
        raise SystemExit("compare: the first file must be the frozen parser's, the second the installed secondary's")
    if a["reader_sha256"] != b["reader_sha256"]:
        raise SystemExit("compare: transcript_view.py differs between the two runs; it must be the frozen file in both")
    readable = sorted(k for k, v in a["grades"].items() if v["raised"] is None)
    differ = sorted(k for k in readable if b["grades"].get(k) != a["grades"][k])
    missing = sorted(set(a["grades"]) ^ set(b["grades"]))
    doc = {"reader_sha256": a["reader_sha256"], "secondary_module_sha256": b["secondary_module_sha256"],
           "frozen_parser": a["installed_parser"], "secondary_parser": b["installed_parser"],
           "takes_graded": len(a["grades"]), "compared": len(readable), "identical": len(readable) - len(differ),
           "differ": differ, "takes_not_in_both": missing, "pass": not differ and not missing}
    Path(args.out).write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"compare: {'PASS' if doc['pass'] else 'FAIL'}; takes compared {doc['compared']}, byte-identical "
          f"{doc['identical']}, differing {len(differ)}, keys not in both files {len(missing)}")
    return 0 if doc["pass"] else 1


# ---- the report ---------------------------------------------------------------------------------------------------
IDENT = ("family", "arm", "task", "model", "harness", "harness_a", "model_a", "harness_b", "model_b", "wording")


def _excludes_zero(r) -> object:
    try:
        lo, hi = float(r["lower"]), float(r["upper"])
    except (KeyError, TypeError, ValueError):
        return None
    return lo > 0 or hi < 0


DECISIONS = {"comparisons": ("at or under alpha", lambda r: r.get("at_alpha")),
             "holds": ("holds", lambda r: r.get("holds")),
             "across_tasks": ("interval excludes zero", _excludes_zero)}


def ident(r) -> str:
    return " · ".join(f"{k} {r[k]}" for k in IDENT if k in r and r[k] is not None)


def decision_rows(p_tables, s_tables, name):
    label, f = DECISIONS[name]
    p, s = p_tables.get(name), s_tables.get(name)
    p = {ident(r): r for r in p} if isinstance(p, list) else {}
    s = {ident(r): r for r in s} if isinstance(s, list) else {}
    out = []
    for k in sorted(set(p) | set(s)):
        a = f(p[k]) if k in p else "absent"
        b = f(s[k]) if k in s else "absent"
        out.append((k, a, b))
    return label, out


def fmt(v) -> str:
    return {True: "yes", False: "no", None: "—"}.get(v, str(v)) if not isinstance(v, str) else v


def is_target(e, batch, labels4) -> bool:
    """Plan item 2's selection: a route ruling to aborted whose cite starts "end state unreadable: ViewError"."""
    return (batch.is_ruling(e) and e.get("ruling") == labels4.RULE_ROUTE and e.get("route") == labels4.ABORTED
            and isinstance(e.get("cite"), str) and e["cite"].startswith(UNREAD_VIEW))


def select_targets(history, batch, labels4) -> list:
    return [e for e in history if is_target(e, batch, labels4)]


def uncovered_unreadable(frozen_grades: dict, patched_grades: dict, targets, history, batch) -> list:
    """Review MINOR 1: the takes the frozen reader cannot read (ViewError) that no item-2 ruling covers, each with how
    the history routed it: [{take, slot, attempt, state, rulings, patched_reads}], in take order."""
    covered = {keyname((e["slot"], e["attempt"])) for e in targets}
    out = []
    for name in sorted(frozen_grades):
        v = frozen_grades[name]
        if v.get("raised") != "ViewError" or name in covered:
            continue
        states = [o.get("state") for o in history if batch.is_outcome(o) and keyname((o["slot"], o["attempt"])) == name]
        rulings = [f"{e.get('ruling')} {e.get('route')}" for e in history if batch.is_ruling(e)
                   and keyname((e.get("slot"), e.get("attempt"))) == name]
        slot, attempt = name.rsplit("/", 1)
        out.append({"take": name, "slot": slot, "attempt": attempt, "state": states[-1] if states else None,
                    "rulings": rulings, "patched_reads": (patched_grades.get(name) or {}).get("raised") is None})
    return out


def uncovered_sentences(uncovered: list) -> list:
    """One sentence per take uncovered_unreadable lists (none when it lists none)."""
    out = []
    for u in uncovered:
        how = (f"ruled {', '.join(u['rulings'])}" if u["rulings"] else
               f"routed `{u['state']}` by the routing table on its own records and never ruled")
        out.append(f"Take `{u['slot']}` attempt {u['attempt']} also cannot be read by the frozen reader (ViewError), "
                   f"but it carries no ruling citing `{UNREAD_VIEW}`: it was {how}, so it is graded in neither "
                   f"analysis, and item 2, which regrades only the takes ruled aborted with that cite, does not cover "
                   f"it ({'the patched parser reads it' if u['patched_reads'] else 'the patched parser cannot read it either'}). "
                   f"The plan's Primary section expects every take the frozen reader cannot read to be ruled aborted "
                   f"with that cite; this take is the exception, and it is not in the table above.")
    return out


def side_by_side(tables_p, tables_s, headings) -> tuple:
    """Plan item 4's decision tables, primary beside secondary: (markdown sections, changed rows) where a changed row
    is (table, row, primary decision, secondary decision)."""
    changed, sections = [], []
    for name in DECISIONS:
        label, drows = decision_rows(tables_p, tables_s, name)
        changed += [(name, k, a, b) for k, a, b in drows if a != b]
        lines = [f"### {headings.get(name, name).lstrip('#').strip()} — {label}", "",
                 "| Row | Primary | Secondary | Changed |", "|---|---|---|---|"]
        lines += [f"| {k} | {fmt(a)} | {fmt(b)} | {'**yes**' if a != b else ''} |" for k, a, b in drows] or \
            ["| (no rows) | | | |"]
        sections.append("\n".join(lines) + "\n")
    return sections, changed


DISCLOSURE = [
    "## Disclosure (the plan's Disclosure section)", "",
    "The reader gap: two measured takes, `s-3c4f8d` and `s-0e780d`, could not be read by the frozen transcript reader "
    "(`transcript_view.map_tool` ViewError). One was a Write call with the argument key `file_text`; the other was a "
    "Skill tool call, followed by its harness meta record and a `command_permissions` attachment.",
    "OD200 was the decision to fix the reader. OD201 reversed it: editing the reader voids the native-reader acceptance "
    "records (they bind the hash of the reader sources, `transcript_view.py` among them) and stales the checker digest. "
    "So the primary analysis keeps the frozen reader and rules such takes aborted, and this pre-registered secondary "
    "analysis reads them with a patched reader beside it.",
    "The gap is in the reader's code, not in the agent's behaviour.", ""]


def cmd_report(args) -> int:
    study, m = load(args.tree, secondary=True)
    run, result, stats, labels4, batch = m["run"], m["result"], m["stats"], m["labels4"], m["batch"]
    tv, sec = m["tv"], m["sec"]
    attempt1 = json.loads(Path(args.attempt1).read_text())
    check = json.loads(Path(args.check).read_text())
    shapes = json.loads(Path(args.shapes).read_text())
    rows, history = m["takes"].load_rows(), m["takes"].read_history()
    registered = {(r["slot"], r["attempt"]): r for r in rows}
    pre = result.tip_limit_held(m["prereg"].require_frozen("the OD201 secondary analysis"))
    targets = select_targets(history, batch, labels4)
    uncovered = uncovered_unreadable(json.loads(Path(args.frozen_grades).read_text())["grades"],
                                     json.loads(Path(args.patched_grades).read_text())["grades"], targets, history,
                                     batch)
    outcome_of = {}
    for o in history:
        if batch.is_outcome(o):
            outcome_of[(o["slot"], o["attempt"])] = o
    regraded, still = {}, {}
    for e in targets:
        key = (e["slot"], e["attempt"])
        try:
            regraded[key] = run.grade_committed(registered[key], outcome_of[key])
        except Exception as err:  # noqa: BLE001
            still[key] = f"{type(err).__name__}: {err}"
    flip = {id(e) for e in targets if (e["slot"], e["attempt"]) in regraded}
    history2 = [dict(e, route=labels4.GRADED) if id(e) in flip else e for e in history]
    secondary = run.produce(rows, history2, run.grade_committed)
    S = result.from_records(secondary["records"], pre, rows, history2)
    primary_records = stats.load_results(run.RECORDS)       # the committed primary records, as the frozen reader graded
    patched_parser = tv.PARSERS["claude-code"]
    tv.PARSERS["claude-code"] = sec.FROZEN_PARSER            # the primary side is derived under the frozen parser
    try:
        P = result.from_records(primary_records, pre, rows, history)
    finally:
        tv.PARSERS["claude-code"] = patched_parser

    # untouched takes' records, the same in both (a record carries no slot; it is keyed by its try, stats.try_key,
    # which check_records holds unique)
    p_by = {repr(stats.try_key(r)): r for r in primary_records}
    s_by = {repr(stats.try_key(r)): r for r in secondary["records"]}
    tkeys = {(e["slot"], e["attempt"]) for e in targets}
    ttries = {repr(stats.try_key(registered[k])) for k in tkeys}
    other_same = all(p_by.get(k) == s_by.get(k) for k in (set(p_by) | set(s_by)) - ttries)

    # unreadable takes per arm, and the shapes that caused them (the frozen reader's line-by-line refusals)
    detail = {(d["slot"], d["attempt"]): d for d in shapes}
    per_arm = {}
    for e in targets:
        key = (e["slot"], e["attempt"])
        arm = registered[key]["arm"]
        a = per_arm.setdefault(arm, {"unreadable": 0, "regraded": 0, "still": 0, "shapes": set()})
        a["unreadable"] += 1
        a["regraded" if key in regraded else "still"] += 1
        for line in (detail.get(key) or {}).get("refused_lines", []):
            a["shapes"].add(next((n for w, n in SHAPE_NAMES if line["error"].startswith(w)
                                  or line["error"].split(": ", 1)[-1].startswith(w)), "other: " + line["error"][:80]))
    if set(detail) != tkeys:
        raise SystemExit("report: the shape scan and the targets name different takes")

    tables_p, tables_s = P["stats"]["tables"], S["stats"]["tables"]
    sections, changed = side_by_side(tables_p, tables_s, stats.TABLE_HEADINGS)
    differing_tables = sorted(t for t in tables_p if tables_p[t] != tables_s.get(t))

    out = ["# Gap Study round 4 — OD201 reader-gap secondary analysis", "",
           "Pre-registered in `workspaces/aegis/plans/gap-study-4-reader-gap-sensitivity-PREREG-20261108.md` "
           "(written 2026-11-08, before any result was read).",
           "Built on branch `analysis/reader-gap-secondary` from the post-run head "
           f"`{args.base}`; never on the line, never pushed.",
           "The headline claim rests on the primary analysis; this is the sensitivity analysis beside it.", "",
           *DISCLOSURE,
           "## The reader patch and how it is applied (plan item 1)", "",
           "The patched reader admits exactly four more shapes than the frozen one, and nothing else: `Write.file_text` "
           "as an alias of `content` (a call carrying both is refused); `Skill` as a tool call of kind other (keys "
           "`skill`, `args`); the harness's isMeta turnCompanion record whose `sourceToolUseID` is an earlier Skill "
           "call (one per call), read as harness; and the `command_permissions` attachment (exactly the keys `type`, "
           "`allowedTools`), read as harness.",
           "**Method.** The patch is applied at runtime to the claude-code parser only: "
           "`evals/gap-study-4/transcript_view_secondary.py` subclasses the frozen `ClaudeCodeSessionParser` and is "
           "installed into `transcript_view.PARSERS[\"claude-code\"]` for this analysis's process alone. "
           "`transcript_view.py` is unchanged, byte-identical to the frozen file (sha256 "
           f"`{check['reader_sha256']}`; secondary module sha256 `{check['secondary_module_sha256']}`), so the "
           "native-reader acceptance records, which bind the hash of the reader sources, still hold, and the codex and "
           "gemini readers are admitted exactly as in the primary analysis; no acceptance record is bypassed and no "
           "reader registry is handed in.",
           "**First attempt, disclosed.** A first attempt edited `transcript_view.py` in place. Under it, "
           f"{attempt1['takes_graded']} takes were graded; {attempt1['identical']} of the {attempt1['compared']} the "
           f"frozen reader could read had byte-identical grades and {len(attempt1['differ'])} got no grade at all, each "
           "refused with `VendorAdmissionRefused`: they are vendor (codex) takes, and the codex acceptance record binds "
           "`reader_sources_sha256` over `native_reader_registration.READER_SOURCES`, which include "
           "`transcript_view.py`, so editing that file voids the acceptance (the effect the pre-registration's "
           "Disclosure names). No take received a different grade. The check was stopped as failed, and glitch-34 "
           "ruled (13 Nov 2026) to apply the patch at runtime instead (option 1), refusing the alternative of handing "
           "the reader registry in (option 2).",
           "Tests on fakes: `evals/gap-study-4/tests/test_reader_gap_secondary.py`.", "",
           "## The blind check (plan item 3)", "",
           f"{'PASS' if check['pass'] else 'FAIL'}: of {check['takes_graded']} committed takes with a registered row, "
           f"the frozen reader graded {check['compared']}; with the patched parser installed {check['identical']} of "
           f"them have a byte-identical grade (canonical JSON, `graded_by` study-relative), {len(check['differ'])} "
           f"differ or are refused.", "",
           "## Unreadable takes per arm, and the shapes that caused them (plan item 4)", "",
           "Unreadable: ruled aborted with a cite starting `end state unreadable: ViewError` (the primary analysis).",
           "", "| Arm | Unreadable (primary) | Read by the patched reader | Still unreadable | Shapes |",
           "|---|---|---|---|---|"]
    for arm in sorted(per_arm):
        a = per_arm[arm]
        out.append(f"| {arm} | {a['unreadable']} | {a['regraded']} | {a['still']} | {'; '.join(sorted(a['shapes']))} |")
    if not per_arm:
        out.append("| (none) | 0 | 0 | 0 | |")
    extra = uncovered_sentences(uncovered)
    if extra:
        out += [""] + extra
    out += ["", "### The regraded takes (plan item 2)", "",
            "| Slot | Attempt | Arm | Task | Half | Model | Primary | Secondary label | Secondary views |",
            "|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(tkeys):
        r = registered[key]
        if key in regraded:
            g = regraded[key]
            sec = (g.get("label"), json.dumps(run.grade_views(g), sort_keys=True))
        else:
            sec = ("still unreadable", still[key])
        out.append(f"| {key[0]} | {key[1]} | {r['arm']} | {r['task']} | {r['half']} | {r['model']} | aborted "
                   f"(ViewError) | {sec[0]} | {sec[1]} |")
    out += ["", f"Every record outside the regraded takes is identical in the primary and secondary results: "
            f"{'yes' if other_same else 'no'}.", "",
            "## Primary and secondary, side by side (plan item 4)", "",
            f"Takes in the results: primary {P['stats']['takes']}, secondary {S['stats']['takes']}.",
            f"Stats tables whose values differ: {', '.join(differing_tables) if differing_tables else 'none'}.", "",
            "The decision each table states, row by row:", ""] + sections
    out += ["## Does any conclusion change? (plan item 5)", ""]
    if changed:
        out += ["**Yes. The secondary analysis changes a conclusion of the primary analysis.** The headline claim "
                "rests on the primary analysis; the write-up must say so plainly:", ""]
        out += [f"- {name}: {k}: primary {fmt(a)}, secondary {fmt(b)}" for name, k, a, b in changed]
    else:
        out += ["No. No decision in the comparison, holds or across-tasks tables changes between the primary and "
                "secondary analyses."]
    out += ["", "(The rule used here: a conclusion is a row's stated decision in table 5 (Holm-adjusted p at or under "
            "alpha), the holds table (holds), or the across-tasks table (the bootstrap interval excludes zero).)", "",
            "## Appendix A — the primary result's stats block", "", result.stats_block(P["stats"]), "",
            "## Appendix B — the secondary result's stats block", "", result.stats_block(S["stats"]), ""]
    Path(args.out).write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"report: wrote {args.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grades")
    g.add_argument("--tree", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--secondary", action="store_true", help="install the patched claude-code parser at runtime")
    c = sub.add_parser("compare")
    c.add_argument("--frozen", required=True)
    c.add_argument("--patched", required=True)
    c.add_argument("--out", required=True)
    r = sub.add_parser("report")
    r.add_argument("--tree", required=True)
    r.add_argument("--check", required=True)
    r.add_argument("--shapes", required=True)
    r.add_argument("--base", required=True)
    r.add_argument("--attempt1", required=True, help="the first attempt's check.json (in-place edit), disclosed")
    r.add_argument("--frozen-grades", required=True, help="grades' output under the frozen parser (review MINOR 1)")
    r.add_argument("--patched-grades", required=True, help="grades' output under the patched parser")
    r.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return {"grades": cmd_grades, "compare": cmd_compare, "report": cmd_report}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
