#!/usr/bin/env python3
"""Build the GARS step map: extracted facts + authored judgment -> map/<contract>.json + MAP.md.

    python3 evals/step-map/build_map.py           # validate, merge, rank, render
    python3 evals/step-map/build_map.py --check   # validate and diff against what is committed

Facts come from extract.py (facts/, regenerable, every field carries its source as path:line).
Judgment is authored by hand in judgment/ (every field there is judgment and is marked so).
Two shared shapes carry the stage 02 sub-stages: judgment/_shape_wrapper.json (the seven nf-core
wrappers) and judgment/_shape_downstream.json (rnaseq-de, scrna-qc-cluster, spatial-cluster-count);
a contract file inherits one and overrides by step.

Validation refuses: a judgment pinned to another commit; a facts step without a judgment row (or the
reverse); a control outside the method note's 19 kinds; a rung outside R0-R5 or a placing question
that does not match the rung; a score outside 1-10; an occurrence with no measurement cited; a
duplicate unsaid id; a defect reference that DEFECTS.md does not define.

Ranking (the method note): severity, then detection, then occurrence (all unmeasured here, so it
never decides), then the earliest step. Scores are not multiplied.
Standard library only.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FACTS = os.path.join(HERE, "facts")
JUDGMENT = os.path.join(HERE, "judgment")
MAP = os.path.join(HERE, "map")

CONTROL_KINDS = (
    "negative scope rules", "fixed response templates", "wait points", "one action per step",
    "definitions shared with helper code", "one human check per stage", "a bounded voice",
    "helper exit codes", "closed menus built by code", "the plan gate", "closed vocabularies",
    "guard deny rules", "typed tool calls", "read-only file modes",
    "run markers bound to script hashes", "exit gates that check content",
    "history entries written by helpers", "a session-start state render", "written rules only",
)
RUNGS = ("R0", "R1", "R2", "R3", "R4", "R5")
QUESTION_FOR = {"R5": 1, "R0": 2, "R2": 3, "R3": 4, "R1": 5, "R4": 5}
ACTORS = ("model", "helper", "human", "guard", "scheduler")
GROUPS = [
    ("Stage 00: register the project and its raw data", ["00_initialize_project"]),
    ("Stage 01: validate the design and write samplesheets", ["01_prepare_samplesheets"]),
    ("Stage 02 router: settings menus and routing", ["02_bioinformatics"]),
    ("Stage 02 sub-stages: run the pipelines", None),   # every other 02 contract
    ("Stage 03: custom analysis", ["03_custom_analysis"]),
]


class Invalid(Exception):
    pass


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def defect_ids():
    path = os.path.join(HERE, "DEFECTS.md")
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return set(re.findall(r"\*\*(D\d+)\*\*", fh.read()))


def facts_contracts():
    out = {}
    for name in sorted(os.listdir(FACTS)):
        if name.endswith(".json") and not name.startswith("_"):
            c = load(os.path.join(FACTS, name))
            out[c["id"]] = c
    return out


def expand(contract_id, steps_in_facts):
    """The judgment rows for one contract: its shape's rows overridden by its own, and its own
    unsaid decisions appended to the inherited ones."""
    own = load(os.path.join(JUDGMENT, contract_id + ".json"))
    rows, meta = {}, {"sha": own["sha"], "by": own.get("by"), "date": own.get("date"),
                      "inherits": own.get("inherits")}
    if own.get("inherits"):
        shape = load(os.path.join(JUDGMENT, own["inherits"] + ".json"))
        if shape["sha"] != own["sha"]:
            raise Invalid("%s and its shape %s are pinned to different commits"
                          % (contract_id, own["inherits"]))
        for n, row in shape["steps"].items():
            rows[n] = dict(row, inherited_from=own["inherits"])
    drop = set(own.get("drop_unsaid", []))
    for n, row in own.get("steps", {}).items():
        base = rows.get(n, {})
        merged = dict(base)
        merged.update({k: v for k, v in row.items() if k not in ("unsaid", "extra_unsaid")})
        unsaid = row["unsaid"] if "unsaid" in row else base.get("unsaid", [])
        merged["unsaid"] = list(unsaid) + list(row.get("extra_unsaid", []))
        if row and "inherited_from" in base and set(row) - {"extra_unsaid"}:
            merged["inherited_from"] = base["inherited_from"] + " (overridden)"
        rows[n] = merged
    for n in rows:
        rows[n]["unsaid"] = [u for u in rows[n].get("unsaid", []) if u["id"] not in drop]
    missing = [n for n in steps_in_facts if n not in rows]
    extra = [n for n in rows if n not in steps_in_facts]
    if missing or extra:
        raise Invalid("%s: judgment rows missing for steps %s, rows for absent steps %s"
                      % (contract_id, missing, extra))
    return rows, meta


def validate_row(contract_id, n, row, defects):
    where = "%s step %s" % (contract_id, n)
    for key in ("actor", "inputs", "evidence", "controls", "rung_now", "rung_target", "question",
                "rung_why", "unsaid"):
        if key not in row:
            raise Invalid("%s: judgment field %s missing" % (where, key))
    bad = [a for a in row["actor"] if a not in ACTORS]
    if bad:
        raise Invalid("%s: unknown actor %s" % (where, bad))
    bad = [c for c in row["controls"] if c not in CONTROL_KINDS]
    if bad:
        raise Invalid("%s: controls outside the method's 19 kinds: %s" % (where, bad))
    for key in ("rung_now", "rung_target"):
        if row[key] not in RUNGS:
            raise Invalid("%s: %s %r is not R0-R5" % (where, key, row[key]))
    # The ordered questions place a step: Q1 flags a decision with no rule (the step is R5
    # today); otherwise the first of Q2-Q5 that applies places it, on its target rung.
    if row["rung_now"] == "R5":
        if row["question"] != 1:
            raise Invalid("%s: an R5 step is placed by question 1, not %s" % (where, row["question"]))
        if row["rung_target"] == "R5":
            raise Invalid("%s: R5 is a finding to fix, never a target" % where)
    elif QUESTION_FOR[row["rung_target"]] != row["question"]:
        raise Invalid("%s: target %s is placed by question %d, not %s"
                      % (where, row["rung_target"], QUESTION_FOR[row["rung_target"]],
                         row["question"]))
    if bool(row["unsaid"]) != (row["rung_now"] == "R5"):
        raise Invalid("%s: a step with an unsaid decision is R5 today, and an R5 step names one"
                      % where)
    for u in row["unsaid"]:
        for key in ("id", "decision", "goes_wrong", "severity", "detection", "occurrence",
                    "why_rank", "fix", "fix_rung"):
            if key not in u:
                raise Invalid("%s: unsaid %s lacks %s" % (where, u.get("id"), key))
        for key in ("severity", "detection"):
            if not isinstance(u[key], int) or not 1 <= u[key] <= 10:
                raise Invalid("%s: %s %s must be an integer 1-10" % (where, u["id"], key))
        if u["occurrence"] is not None and not u.get("measured_by"):
            raise Invalid("%s: %s has an occurrence with no measurement cited" % (where, u["id"]))
        if u["fix_rung"] not in RUNGS[:5] and u["fix_rung"] != "guard":
            raise Invalid("%s: %s fix_rung %r" % (where, u["id"], u["fix_rung"]))
        for d in u.get("defects", []):
            if d not in defects:
                raise Invalid("%s: %s cites %s, which DEFECTS.md does not define"
                              % (where, u["id"], d))


def step_facts(contract, step):
    """The extracted facts of one step, each with its source."""
    path = contract["path"]
    sites = [cs for cs in contract["call_sites"] if cs["step"] == step["n"]]
    flags = [f for f in contract["prose_flags"] if f["step"] == step["n"]]
    calls = []
    for c in step["calls"]:
        g = c.get("guard") or {}
        entry = {"command": c["command"], "tool": c["tool"], "kind": c["kind"],
                 "source": "%s:%d" % (path, c["line"])}
        if g.get("status") == "checked":
            entry["guard"] = {"intended_workspace": g["intended"],
                              "allowed_where_intended": g["allowed_where_intended"],
                              "allowed_by_workspace": {s: d["allow"] for s, d in
                                                       g["forms"]["minimal"]["decisions"].items()},
                              "dispatcher_allowed_by_workspace": {
                                  s: d["allow"] for s, d in
                                  g.get("dispatcher", {}).get("decisions", {}).items()}}
            if not g["allowed_where_intended"]:
                entry["guard"]["refusal"] = \
                    g["forms"]["minimal"]["decisions"][g["intended"]]["reason"][:400]
        calls.append(entry)
    return {
        "source": step["source"],
        "text": step["text"],
        "templates": step["templates"],
        "wait": step["wait"],
        "calls": calls,
        "exit_branches": [{"tool": cs["tool"], "source": "%s:%d" % (path, cs["line"]),
                           "handled": cs["handled"], "emitted": cs["emitted"],
                           "unhandled": cs["unhandled"],
                           "unhandled_emit_sites": cs["unhandled_sites"],
                           "prose_handling": cs["prose_handling"]} for cs in sites],
        "file_actions": [{"tool": a["tool"], "path": a["path"], "source": "%s:%d" % (path, a["line"]),
                          "allowed_by_workspace": {s: d["allow"] for s, d in a["guard"].items()}}
                         for a in step["file_actions"]],
        "prose_flags": [{"flag": f["flag"], "value": f["value"], "target_tool": f["target_tool"],
                         "in_command": f["in_command"], "prohibited": f["prohibited"],
                         "source": "%s:%d" % (path, f["line"]),
                         "allowed_where_intended": (f.get("guard") or {}).get("allowed_where_intended")}
                        for f in flags],
    }


def build():
    contracts = facts_contracts()
    summary = load(os.path.join(FACTS, "_summary.json"))
    defects = defect_ids()
    maps, unsaid_index = {}, {}
    order = sorted(contracts, key=lambda c: (group_of(c), c))
    for cid in order:
        contract = contracts[cid]
        rows, meta = expand(cid, [s["n"] for s in contract["steps"]])
        if meta["sha"] != summary["sha"]:
            raise Invalid("%s: judgment pinned to %s, facts to %s" % (cid, meta["sha"], summary["sha"]))
        steps = []
        for k, step in enumerate(contract["steps"]):
            row = rows[step["n"]]
            validate_row(cid, step["n"], row, defects)
            judgment = {key: row[key] for key in ("actor", "inputs", "evidence", "controls",
                                                  "rung_now", "rung_target", "question",
                                                  "rung_why", "unsaid")}
            judgment["kind"] = "judgment"
            if row.get("inherited_from"):
                judgment["inherited_from"] = row["inherited_from"]
            if row.get("note"):
                judgment["note"] = row["note"]
            steps.append({"n": step["n"], "extracted": step_facts(contract, step),
                          "judgment": judgment})
            for u in row["unsaid"]:
                entry = unsaid_index.setdefault(u["id"], {"unsaid": u, "where": []})
                if entry["unsaid"] != u:
                    raise Invalid("unsaid id %s is defined twice with different content" % u["id"])
                entry["where"].append((order.index(cid), k, cid, step["n"], step["source"]))
        maps[cid] = {"schema": "stepmap-map/1", "sha": summary["sha"], "id": cid,
                     "path": contract["path"], "judgment_by": meta["by"],
                     "judgment_date": meta["date"], "inherits": meta["inherits"],
                     "steps": steps}
    ranked = rank(unsaid_index, contracts)
    for cid in maps:
        maps[cid]["unsaid_ranked"] = [r for r in ranked if any(w["contract"] == cid
                                                               for w in r["where"])]
    return maps, ranked, summary, contracts


def group_of(cid):
    for k, (_, members) in enumerate(GROUPS):
        if members is None:
            if cid.startswith(("atacseq", "chipseq", "cutandrun", "methylseq", "rnaseq_bulk",
                               "scrnaseq", "spatialvi")):
                return k
        elif cid in members:
            return k
    raise Invalid("contract %s belongs to no stage group" % cid)


def rank(unsaid_index, contracts):
    """One entry per decision per stage group it touches: a decision that recurs across stages
    is ranked in each of them, on its own scores, at its earliest step in that stage."""
    out = []
    for uid, entry in unsaid_index.items():
        u = entry["unsaid"]
        by_group = {}
        for w in sorted(entry["where"]):
            by_group.setdefault(group_of(w[2]), []).append(w)
        for group, where in sorted(by_group.items()):
            first = where[0]
            out.append(dict(u, group=group,
                            where=[{"contract": w[2], "step": w[3], "source": w[4]} for w in where],
                            elsewhere=sorted(GROUPS[g][0] for g in by_group if g != group),
                            _key=(group, -u["severity"], -u["detection"],
                                  -(u["occurrence"] or 0), first[0], first[1])))
    out.sort(key=lambda r: r["_key"])
    rank_in_group = {}
    for r in out:
        rank_in_group[r["group"]] = rank_in_group.get(r["group"], 0) + 1
        r["rank_in_stage"] = rank_in_group[r["group"]]
        r["stage"] = GROUPS[r["group"]][0]
        del r["_key"]
    return out


# --- rendering ---------------------------------------------------------------------------------

def md_escape(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


def render(maps, ranked, summary, contracts):
    sha = summary["sha"]
    s = summary
    lines = [
        "# GARS step map",
        "",
        "_Every numbered step of the 14 GARS stage contracts at `%s`, with the facts code pulled out"
        " of the contracts and helpers and the judgment a reviewer added._" % sha[:8],
        "_Generated by `evals/step-map/build_map.py` from `facts/` (extracted by `extract.py`) and"
        " `judgment/` (authored); do not edit by hand._",
        "",
        "## How to read this",
        "",
        "Each step has two kinds of field.",
        "**Extracted** fields (calls, exit branches, templates, waits, file actions, guard decisions)"
        " come from code and carry their source as `path:line` at the pin; `facts/` holds them in full.",
        "**Judgment** fields (actor, inputs, evidence, controls, rung, unsaid decisions and their"
        " scores) are a reviewer's reading under the method in `gars-step-map-method.md`; they are"
        " marked `\"kind\": \"judgment\"` in `map/`.",
        "",
        "Rungs: R0 pure code; R1 code checks the form; R2 model proposes, code verifies;"
        " R3 model proposes, a human confirms; R4 model judges under a written rule; R5 unsaid."
        " A step's rung is placed by the first of the method's ordered questions that applies"
        " (Q1 unsaid decision, Q2 an algorithm can do it, Q3 code can verify it, Q4 wrong output acts"
        " outside, is irreversible or becomes a claim, Q5 otherwise).",
        "`rung now` is where the step sits today; `target` is the lowest workable rung the fix would"
        " reach.",
        "",
        "Scores, each 1 to 10, applied to every decision by these anchors.",
        "",
        "**Severity**, the worst downstream consequence if the model gets it wrong:"
        " 10 a data-policy breach on non-public data, or a wrong scientific result nothing flags;"
        " 9 a wrong scientific result, complete and plausible, the user may act on;"
        " 8 the wrong analysis runs (wrong assay, settings, samples or inputs), or a permanent"
        " governance record is wrong;"
        " 7 the user's data or work is changed irreversibly without consent;"
        " 6 false provenance in the permanent record, or the right analysis on the wrong project;"
        " 5 the stage dead-ends with no compliant road, compute is wasted, or a setting is changed"
        " without the user;"
        " 4 a stall or confusion the user has to sort out;"
        " 3 a wrong or misleading message;"
        " 2 a wrong but harmless detail in a record;"
        " 1 cosmetic.",
        "",
        "**Detection**, the chance the error escapes every later check:"
        " 1 a code gate always catches it before harm;"
        " 2 it fails loudly at once (a refusal, a crash);"
        " 3 a later code check usually catches it;"
        " 4 the user is asked to confirm it before it takes effect;"
        " 5 it is shown to the user unasked, or the stage's human check covers it;"
        " 6 it sits in a record or report the user is pointed to, for one who looks closely;"
        " 7 only an attentive expert notices it in the outputs;"
        " 8 nothing shows it; only reading the files or the transcript reveals it;"
        " 9 nothing shows it and nothing later checks it;"
        " 10 nothing could ever reveal it.",
        "",
        "**Occurrence** is unmeasured for every decision here (no paired measurement exists yet),"
        " so it is left empty and never decides a rank. Ranking, within each stage: severity, then"
        " detection, then the earliest step; scores are never multiplied. A decision that recurs in"
        " several stages is ranked in each of them.",
        "",
        "## Counts (extracted)",
        "",
        "| What | Count |",
        "|---|---|",
        "| Contracts | %d |" % s["contracts"],
        "| Numbered steps | %d |" % s["steps"],
        "| Response templates | %d |" % s["templates"],
        "| Commands named in steps | %d (%d mapped to a registry tool, %d unregistered, %d"
        " uninstantiable) |" % (s["command_accounting"]["seen"], s["command_accounting"]["mapped"],
                                s["command_accounting"]["unregistered"],
                                s["command_accounting"]["uninstantiable"]),
        "| Unregistered commands steps need | %s |" % "; ".join(
            "`%s` (%s)" % (x, ", ".join(sorted({u["kind"] for u in s["unregistered_calls"]
                                               if u["executable"] == x})))
            for x in s["unregistered_in_process"]),
        "| Call sites with exit branches compared | %d |" % s["exits"]["call_sites"],
        "| Exit codes the helpers can emit there (static) | %d |" % s["exits"]["emitted"],
        "| Codes the contract branches on | %d |" % s["exits"]["handled"],
        "| Non-zero codes with no branch (static) | %d |" % s["exits"]["unhandled"],
        "| Fixed answers (accept tokens) | %s |" % ", ".join("`%s`" % t for t in s["accept_tokens"]),
        "| Template placeholders | %d seen: %d graded against the backing call's keys (key, label,"
        " unbound, no source), %d not graded (context words, choices, model-written text,"
        " artifact paths); by kind: %s |" % (
            s["placeholder_accounting"]["seen"], s["placeholder_accounting"]["graded"],
            s["placeholder_accounting"]["ungraded"],
            ", ".join("%s %d" % kv for kv in sorted(s["placeholder_accounting"]["by_binding"].items()))),
        "| Exit codes ruled unreachable by a cited reading | %d (rulings re-checked against their lines"
        " on every run) |" % s["exits"]["ruled_out"],
        "| Backtick spans in steps | %d, counted independently in the raw lines and matched |"
        % s["span_accounting"]["seen"],
        "| Calls and flag variants put to the pinned guard | %d calls, in 5 synthetic workspaces |"
        % s["guard"]["calls_checked"],
        "| File actions put to the pinned guard | %d |" % s["guard"]["file_actions_checked"],
        "| File-verb sentences seen but not classified | %d (listed in `facts/`) |"
        % s["file_mentions_unclassified"],
        "",
        "\"Static\" means reachable in the helper's code as written, with branches the command's own"
        " flags decide pruned; codes a reader proved unreachable from a given caller are ruled out"
        " with the lines that prove it (`facts/_summary.json`, `rulings`). Uncaught exceptions are"
        " not modelled (`limits`).",
        "",
        "## Rung totals (judgment)",
        "",
    ]
    totals = {}
    for m in maps.values():
        for st in m["steps"]:
            key = st["judgment"]["rung_now"]
            totals[key] = totals.get(key, 0) + 1
    lines += ["| Rung now | Steps |", "|---|---|"] + \
        ["| %s | %d |" % (r, totals.get(r, 0)) for r in RUNGS] + [""]
    bands = {"severity 7-10": 0, "severity 5-6": 0, "severity 1-4": 0}
    low_only = {}
    for m in maps.values():
        for st in m["steps"]:
            unsaid = st["judgment"]["unsaid"]
            if not unsaid:
                continue
            top = max(u["severity"] for u in unsaid)
            band = "severity 7-10" if top >= 7 else "severity 5-6" if top >= 5 else "severity 1-4"
            bands[band] += 1
            if top < 5:
                key = ", ".join(sorted(u["id"] for u in unsaid))
                low_only[key] = low_only.get(key, 0) + 1
    lines += ["An R5 step is one with at least one decision no rule covers; most carry only a"
              " low-severity cross-cutting one. By each R5 step's worst unsaid decision:", "",
              "| Worst unsaid decision in the step | R5 steps |", "|---|---|"] + \
        ["| %s | %d |" % kv for kv in bands.items()] + [""] + \
        ["Of the severity 1-4 steps, the unsaid decisions are: %s." % "; ".join(
            "%s (%d step%s)" % (k, v, "" if v == 1 else "s")
            for k, v in sorted(low_only.items(), key=lambda kv: (-kv[1], kv[0]))), ""]
    lines += ["## Top unsaid decisions per stage (judgment, ranked)", ""]
    for k, (title, _) in enumerate(GROUPS):
        lines += ["### " + title, "", "| Rank | Id | Where | Decision the model makes silently |"
                  " Sev | Det | Fix |", "|---|---|---|---|---|---|---|"]
        for r in [r for r in ranked if r["group"] == k]:
            where = ", ".join(sorted({"%s %s" % (w["contract"], w["step"]) for w in r["where"]}))
            if len(r["where"]) > 3:
                where = "%s and %d more" % (", ".join(
                    "%s %s" % (w["contract"], w["step"]) for w in r["where"][:2]), len(r["where"]) - 2)
            lines.append("| %d | %s | %s | %s | %d | %d | %s → %s |" % (
                r["rank_in_stage"], r["id"], md_escape(where + (" (also in: %s)" % "; ".join(
                    r["elsewhere"]) if r["elsewhere"] else "")), md_escape(r["decision"]),
                r["severity"], r["detection"], md_escape(r["fix"]), r["fix_rung"]))
        lines.append("")
    lines += ["## Every step", ""]
    for cid, m in maps.items():
        lines += ["### `%s`" % m["path"], ""]
        if m["inherits"]:
            lines += ["Judgment inherits `judgment/%s.json`; overrides are marked." % m["inherits"], ""]
        lines += ["| Step | Actor | Rung now → target | Calls (tool) | No-branch exits | Wait |"
                  " Controls | Unsaid |", "|---|---|---|---|---|---|---|---|"]
        for st in m["steps"]:
            j, x = st["judgment"], st["extracted"]
            calls = ", ".join(sorted({c["tool"] or ("`%s` (unregistered)" % c["command"])
                                      for c in x["calls"]})) or "none"
            nob = "; ".join("%s %s" % (e["tool"], e["unhandled"]) for e in x["exit_branches"]
                            if e["unhandled"]) or "none"
            wait = x["wait"]["kind"] or "no"
            if x["wait"]["accept_tokens"]:
                wait += " (" + ", ".join(x["wait"]["accept_tokens"]) + ")"
            lines.append("| %s | %s | %s → %s | %s | %s | %s | %s | %s |" % (
                st["n"], "+".join(j["actor"]), j["rung_now"], j["rung_target"], md_escape(calls),
                md_escape(nob), md_escape(wait), md_escape(", ".join(j["controls"])),
                ", ".join(u["id"] for u in j["unsaid"]) or "none"))
        lines.append("")
    return "\n".join(lines) + "\n"


def write_all(maps, md, out_map=MAP, out_md=os.path.join(HERE, "MAP.md")):
    os.makedirs(out_map, exist_ok=True)
    for cid, m in maps.items():
        with open(os.path.join(out_map, cid + ".json"), "w", encoding="utf-8") as fh:
            json.dump(m, fh, indent=1, sort_keys=True, ensure_ascii=False)
            fh.write("\n")
    with open(out_md, "w", encoding="utf-8") as fh:
        fh.write(md)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="validate and compare with the committed map/ and MAP.md; write nothing")
    args = ap.parse_args(argv)
    try:
        maps, ranked, summary, contracts = build()
    except Invalid as exc:
        print("INVALID: %s" % exc, file=sys.stderr)
        return 1
    md = render(maps, ranked, summary, contracts)
    if args.check:
        problems = []
        for cid, m in maps.items():
            path = os.path.join(MAP, cid + ".json")
            fresh = json.dumps(m, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
            if not os.path.exists(path) or open(path, encoding="utf-8").read() != fresh:
                problems.append(path)
        if open(os.path.join(HERE, "MAP.md"), encoding="utf-8").read() != md:
            problems.append("MAP.md")
        for p in problems:
            print("STALE: %s differs from a fresh build" % p, file=sys.stderr)
        return 1 if problems else 0
    write_all(maps, md)
    steps = sum(len(m["steps"]) for m in maps.values())
    print("map: %d contracts, %d steps, %d unsaid decisions ranked" % (len(maps), steps, len(ranked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
