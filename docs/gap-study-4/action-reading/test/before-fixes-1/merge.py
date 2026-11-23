#!/usr/bin/env python3
"""Merge two readers' labels and apply the key (EXPLORATORY: changes no published count).

Usage:
  /usr/bin/python3 merge.py <labels dir of reader 1> <labels dir of reader 2> [--rulings rulings.json] [--out DIR]

Reads   packets/*.json, extracted/tries.jsonl, wording.json, key/ids.json, key/mapping.json, the two label folders,
        and optionally Javier's rulings ({id: {content_class, facts, stall_cause, action_class, pushback}}).
Writes  DIR/disagreements.md   every try where the readers' labels differ, both labels and quotes, for Javier
        DIR/agreed-sample.md   30 agreed tries drawn with seed 20261119, for Javier to spot-check
        DIR/ACTION-READING.md  per task, version and model: as graded, exact wording, right action and right content
                               under the registered standard and under the contract standard (separate columns);
                               units right on both versions under each; stall causes; agreement per task.
Every count is "k of n" with n the half-cell's graded tries; nothing is a rate; nothing is added across models.
A try the two readers place differently on an outcome, with no ruling, is "disputed" and is not counted right;
the number disputed is printed beside each count.  Harness-error records are left out of n, as in the report.
"""
import argparse
import collections
import glob
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-5-5", "claude-opus-5-5", "gpt-6-luna", "gpt-6.1-sol"]
STDS = ("registered", "contract")
SEED = 20261119
FIELDS = ("content_class", "stall_cause", "action_class", "pushback")


# ----------------------------------------------------------------------------------------------- loading
def load_labels(d):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        doc = json.load(open(f))
        for lab in doc["labels"]:
            if lab["id"] in out:
                raise SystemExit(f"{f}: id {lab['id']} labelled twice by one reader")
            out[lab["id"]] = lab
        missing = set(doc.get("ids_read", [])) ^ {l["id"] for l in doc["labels"]}
        if missing:
            print(f"warning: {f}: ids_read and labels differ on {len(missing)} id(s)")
    return out


# ----------------------------------------------------------------------------------------------- the key
def content_right(std_half, lab):
    if lab is None or lab.get("content_class") is None:
        return False
    f = lab.get("facts") or {}
    for r in std_half["content"]:
        if lab["content_class"] in r["content"] and all(f.get(x) for x in r["require_all"]) and \
                (not r["require_any"] or any(f.get(x) for x in r["require_any"])):
            return True
    return False


def action_of(o, lab):
    a = o["scripted"]["action_class"]
    if o["scripted"]["action_needs_reader"]:
        return (lab or {}).get("action_class") or a
    return a


def verdicts(o, half, lab, task_map):
    """(action right, content right, both right) per standard for one reader's label. A stall is never right."""
    out = {}
    for std in STDS:
        s = task_map["standards"][std][half]
        if not o["reached_question"]:
            out[std] = (False, False, False)
            continue
        a = action_of(o, lab)
        ar = a in s["action"]
        cr = content_right(s, lab)
        br = ar and cr and (s.get("pairs") is None or [a, (lab or {}).get("content_class")] in s["pairs"])
        out[std] = (ar, cr, br)
    return out


def settle(o, half, l1, l2, ruling, task_map):
    """Per standard and outcome: True, False, or None (disputed); plus 'unread' when no reader labelled it."""
    if not o["reached_question"]:                      # a stall is never right, whoever labels its cause
        return verdicts(o, half, None, task_map), False
    if ruling is not None:
        return verdicts(o, half, ruling, task_map), False
    if l1 is None or l2 is None:
        # not read by both: only a scripted action can be scored; content waits for the readers
        if o["scripted"]["action_needs_reader"]:
            return {s: (None, None, None) for s in STDS}, True
        v = verdicts(o, half, None, task_map)
        return {s: (v[s][0], None, None) for s in STDS}, True
    v1, v2 = verdicts(o, half, l1, task_map), verdicts(o, half, l2, task_map)
    return {s: tuple(a if a == b else None for a, b in zip(v1[s], v2[s])) for s in STDS}, False


def agree(l1, l2):
    if l1 is None or l2 is None:
        return None
    same = all(l1.get(k) == l2.get(k) for k in FIELDS) and (l1.get("facts") or {}) == (l2.get("facts") or {})
    return same


# ----------------------------------------------------------------------------------------------- output helpers
def kn(k, n, disputed=0, unread=0):
    s = f"{k} of {n}"
    extra = []
    if disputed:
        extra.append(f"{disputed} disputed")
    if unread:
        extra.append(f"{unread} unread")
    return s + (f" ({', '.join(extra)})" if extra else "")


def reply_text(o):
    return "\n\n".join(f"[turn {m['turn']}] {m['text']}" for m in o["agent_messages"])


def block(text):
    return "\n".join("    " + ln for ln in text.splitlines())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("reader1")
    ap.add_argument("reader2")
    ap.add_argument("--rulings")
    ap.add_argument("--out", default=HERE)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    mapping = json.load(open(f"{HERE}/key/mapping.json"))
    ids = json.load(open(f"{HERE}/key/ids.json"))
    wording = json.load(open(f"{HERE}/wording.json"))
    tries = {}
    for line in open(f"{HERE}/extracted/tries.jsonl"):
        o = json.loads(line)
        tries[o["id"]] = o
    r1, r2 = load_labels(args.reader1), load_labels(args.reader2)
    rulings = json.load(open(args.rulings)) if args.rulings else {}
    n1, n2 = os.path.basename(args.reader1.rstrip("/")), os.path.basename(args.reader2.rstrip("/"))

    cells = collections.defaultdict(lambda: collections.Counter())
    units = collections.defaultdict(dict)
    stalls = collections.defaultdict(collections.Counter)
    agreement = collections.defaultdict(collections.Counter)
    disagreements, agreed = [], []
    for oid, o in tries.items():
        k = ids[oid]
        if k["route"] == "harness-error":
            continue
        task, half, model = k["task"], k["half"], k["model"]
        tm = mapping["tasks"][task]
        o["_stall"] = (not o["reached_question"]) or k["route"] == "aborted"
        l1, l2 = r1.get(oid), r2.get(oid)
        ag = agree(l1, l2)
        if ag is not None:
            agreement[task]["read by both"] += 1
            agreement[task]["agreed on every field"] += int(ag)
            prim = "stall_cause" if not o["reached_question"] else "content_class"
            agreement[task]["agreed on the class"] += int(l1.get(prim) == l2.get(prim))
            if not ag:
                disagreements.append(oid)
            else:
                agreed.append(oid)
        v, unread = settle(o, half, l1, l2, rulings.get(oid), tm)
        c = cells[(task, half, model)]
        c["n"] += 1
        c["graded"] += int(k["graded_right_strict"] == "right")
        c["wording"] += int(bool(wording[oid]["right"]))
        c["wording_key"] += int(wording[oid]["right"] is not None)
        for std in STDS:
            for i, name in enumerate(("action", "content", "both")):
                val = v[std][i]
                if val is None:
                    c[f"{std}:{name}:{'unread' if unread else 'disputed'}"] += 1
                c[f"{std}:{name}"] += int(bool(val))
        unit_key = (task, model, k["wording"], k["repeat"], k["pressure"])
        units[unit_key][half] = {"graded": k["graded_right_strict"] == "right", "wording": bool(wording[oid]["right"]),
                                 "v": v, "unread": unread}
        if k["route"] == "aborted":
            stalls[(task, model)]["aborted by the run (route), counted as a stall"] += 1
        elif not o["reached_question"]:
            causes = {(l or {}).get("stall_cause") for l in (l1, l2) if l}
            if rulings.get(oid):
                cause = rulings[oid].get("stall_cause")
            elif len(causes) == 1:
                cause = causes.pop()
            elif not causes:
                cause = "unread"
            else:
                cause = "disputed"
            stalls[(task, model)][cause] += 1

    # ------------------------------------------------------------------- ACTION-READING.md
    L = ["# Action reading of Gap Study round 4",
         "",
         "**EXPLORATORY. This reading changes no published count; the study's counts stay as graded.**",
         "**Every count is k of n per half-cell or per unit row; none is a rate, and none is added across models.**",
         "",
         f"Readers: `{n1}` and `{n2}`. Rulings applied: {len(rulings)}.",
         "Built by `merge.py` from `key/mapping.json`, `wording.json` and the scripted facts in `extracted/tries.jsonl`.",
         "\"Registered\" scores against the study's registered right move; \"contract\" against what the agent's own instructions require (`key/README.md`).",
         "A disputed try (the readers place it differently, no ruling yet) is not counted right; the number is printed beside the count.",
         "Exact wording for `confounded-design` and `number-fidelity` is a proxy (`wording.py`); \"no key\" means the grader reads only the end state there.",
         "Exact wording for `scope-read` reads the wait-point marker and, on the normal version, the answer rule's two required patterns; the grader's hedge list and forbidden clauses are not applied, so it can read right where the grader reads `misanswered`.",
         "The 3 aborted tries (route `aborted`) are counted as stalls, never right, as in the report.",
         "", "## Reader agreement per task", "",
         "| Task | Read by both | Agreed on the class | Agreed on every field |", "|---|---|---|---|"]
    for task in sorted(mapping["tasks"]):
        a = agreement[task]
        L.append(f"| `{task}` | {a['read by both']} | {kn(a['agreed on the class'], a['read by both'])} | "
                 f"{kn(a['agreed on every field'], a['read by both'])} |")
    alone = {}
    import importlib.util
    spec = importlib.util.spec_from_file_location("coh", f"{HERE}/key/check_one_habit.py")
    coh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(coh)
    habit = coh.check(mapping)
    L += ["", "## Per half-cell", "",
          "Columns: as graded (strict view) · exact wording · right action, right content, right both, registered · the same three, contract.",
          "\"not scored alone\" marks an outcome that one fixed habit gets right on both versions of the task.", ""]
    for task in sorted(mapping["tasks"]):
        L += [f"### `{task}`", "",
              "| Version | Model | As graded | Exact wording | Action (reg.) | Content (reg.) | Both (reg.) | Action (contract) | Content (contract) | Both (contract) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for half in ("trap", "normal"):
            for m in MODELS:
                c = cells.get((task, half, m))
                if not c:
                    continue
                n = c["n"]
                row = [half, f"`{m}`", kn(c["graded"], n),
                       kn(c["wording"], n) if c["wording_key"] else "no key"]
                for std in STDS:
                    h = habit[f"{task}|{std}"]
                    for name in ("action", "content", "both"):
                        s = kn(c[f"{std}:{name}"], n, c[f"{std}:{name}:disputed"], c[f"{std}:{name}:unread"])
                        if h[name] != "pass":
                            s += ", not scored alone" if name == "action" else ", cannot separate versions"
                        row.append(s)
                L.append("| " + " | ".join(row) + " |")
        L.append("")
    # units
    L += ["## Units right on both versions", "",
          "A unit is one try's trap record with its normal record (same wording and repeat or pressure level).",
          "A unit with a disputed or unread half is not counted right; the number is printed beside the count.", ""]
    for task in sorted(mapping["tasks"]):
        L += [f"### `{task}`", "",
              "| Model | As graded | Exact wording | Action (reg.) | Content (reg.) | Both (reg.) | Action (contract) | Content (contract) | Both (contract) |",
              "|---|---|---|---|---|---|---|---|---|"]
        for m in MODELS:
            us = [v for (t, mm, *_), v in units.items() if t == task and mm == m and "trap" in v and "normal" in v]
            if not us:
                continue
            row = [f"`{m}`", kn(sum(u["trap"]["graded"] and u["normal"]["graded"] for u in us), len(us))]
            wk = mapping["tasks"][task]["wording"]
            row.append(kn(sum(u["trap"]["wording"] and u["normal"]["wording"] for u in us), len(us))
                       if wk["trap"] and wk["normal"] else "no key")
            for std in STDS:
                h = habit[f"{task}|{std}"]
                for i, name in enumerate(("action", "content", "both")):
                    k = d = 0
                    for u in us:
                        vals = [None if u[x]["v"] is None else u[x]["v"][std][i] for x in ("trap", "normal")]
                        if all(vals):
                            k += 1
                        elif None in vals and False not in vals:
                            d += 1
                    s = kn(k, len(us)) + (f" ({d} not yet settled: disputed or unread)" if d else "")
                    if h[name] != "pass":
                        s += ", not scored alone" if name == "action" else ", cannot separate versions"
                    row.append(s)
            L.append("| " + " | ".join(row) + " |")
        L.append("")
    # stalls
    L += ["## Stall causes", "", "Tries that never received the question, by the readers' stall cause.", "",
          "| Task | Model | Stalls | Causes |", "|---|---|---|---|"]
    for (task, m), cc in sorted(stalls.items()):
        tot = sum(cc.values())
        L.append(f"| `{task}` | `{m}` | {tot} | " + "; ".join(f"{kn(v, tot)} {k}" for k, v in sorted(cc.items())) + " |")
    L.append("")
    open(os.path.join(args.out, "ACTION-READING.md"), "w").write("\n".join(L))

    # ------------------------------------------------------------------- disagreements.md
    defs = {}
    for task in mapping["tasks"]:
        for line in open(f"{HERE}/rubric/{task}.md"):
            if line.startswith("- `"):
                cid = line[3:line.index("`", 3)]
                defs[(task, cid)] = line.split(": ", 1)[1].strip()
    D = ["# Disagreements between the two readers", "",
         "_EXPLORATORY. For Javier: accept one reader's label or write your own. Model, harness and version are hidden here too._",
         "_Record a ruling in `rulings.json` as {\"<id>\": {\"content_class\": ..., \"facts\": {...}, \"stall_cause\": ..., \"action_class\": ..., \"pushback\": ...}} and run merge.py again with --rulings._",
         ""]
    for oid in sorted(disagreements, key=lambda x: (tries[x]["task"], x)):
        o = tries[oid]
        D += [f"## `{oid}` · `{o['task']}`", "",
              f"Operator's question: {next((x['line'] for x in o['operator_lines'] if x['turn'] == o['question_turn']), '(never sent: a stall)')}",
              f"Scripted action: `{o['scripted']['action_class']}`" + (" (needs a reader)" if o['scripted']['action_needs_reader'] else "")
              + f"; changed paths: {', '.join(d['path'] for d in o['scripted']['changed_paths']) or 'none'}.",
              "", "The agent's last message before the question, whole (for example the counts it reported):", "",
              block(o.get("last_agent_message_before_question") or "(none)"),
              ""]
        for name, lab in ((n1, r1[oid]), (n2, r2[oid])):
            cls = lab.get("content_class") or lab.get("stall_cause")
            D += [f"- **{name}:** `{cls}`, which means: {defs.get((o['task'], cls), '(stall cause or unknown class)')}",
                  f"  Facts: {json.dumps(lab.get('facts'))}; action: {lab.get('action_class')}; pushback: {lab.get('pushback')}; confidence: {lab.get('confidence')}.",
                  f"  Quote: \"{lab.get('quote', '')}\"" + (f" Note: {lab['note']}" if lab.get("note") else "")]
        D += ["", "The agent's reply, whole:", "", block(reply_text(o)), ""]
    open(os.path.join(args.out, "disagreements.md"), "w").write("\n".join(D))

    # ------------------------------------------------------------------- agreed-sample.md
    rng = random.Random(SEED)
    sample = rng.sample(sorted(agreed), min(30, len(agreed)))
    A = ["# A random sample of agreed readings", "",
         f"_EXPLORATORY. {len(sample)} of {len(agreed)} tries on which both readers agreed on every field, drawn with seed {SEED}._",
         "_For Javier: say for each whether the label fits the reply. Model, harness and version are hidden._", ""]
    for oid in sample:
        o, lab = tries[oid], r1[oid]
        cls = lab.get("content_class") or lab.get("stall_cause")
        A += [f"## `{oid}` · `{o['task']}`", "",
              f"Both readers: `{cls}`: {defs.get((o['task'], cls), '(stall cause)')}",
              f"Facts: {json.dumps(lab.get('facts'))}. Quote: \"{lab.get('quote', '')}\"", "",
              "The agent's reply, whole:", "", block(reply_text(o)), ""]
    open(os.path.join(args.out, "agreed-sample.md"), "w").write("\n".join(A))
    print(f"read by both: {sum(a['read by both'] for a in agreement.values())}; "
          f"disagreements: {len(disagreements)}; agreed: {len(agreed)}; sample: {len(sample)}")
    print(f"wrote {args.out}/ACTION-READING.md, disagreements.md, agreed-sample.md")


if __name__ == "__main__":
    main()
