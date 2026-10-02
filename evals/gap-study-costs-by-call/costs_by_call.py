#!/usr/bin/env python3
"""The Gap Study token tables, each model call counted once: the dated correction beside them (decision 0271).

    python3 evals/gap-study-costs-by-call/costs_by_call.py            the totals, as published and by call
    python3 evals/gap-study-costs-by-call/costs_by_call.py --write    write CORRECTION-2026-10-02.md
    python3 evals/gap-study-costs-by-call/costs_by_call.py --check    exit 1 unless that page is what --write
                                                                     writes and every published figure on it
                                                                     is in that round's own COSTS.md

WHAT WAS WRONG. Each round's pinned `costs.py` (gap-study, gap-study-2, gap-study-3) adds up `message.usage`
over every transcript record that carries one. Claude Code writes one record per content block of a model
reply (a thinking block, a text block and a tool_use block of one reply are three records), and each of those
records carries the whole reply's usage. So the published tables count usage records, not model calls, and a
call with three blocks is counted three times.

THE KEY. A call is the pair (`message.id`, `requestId`): `message` is the API response as the harness received
it, `usage` is a field of it, and `requestId` is the harness's identifier of the request that returned it. In
the committed transcripts the two are one to one. Two records with one key and different usage are refused
(`Disagreement`) rather than one of them picked. A record missing either half of the key is never merged with
another; it counts as a call of its own and is reported in `partial_key` (none in the committed transcripts).

WHAT IT LEAVES ALONE. The pinned readers and the published tables are not edited: each round's `costs.py` is
pinned by sha256 in its `prereg.json`, which `check_results.py` verifies. The published column here is computed
by importing each round's own pinned `read_one`, and `--check` also finds every published figure printed here
in that round's `COSTS.md`, so this page is bound to the tables it corrects. Wall clock, the recorded pauses and
each round's dollar line do not read usage and are unchanged. No grader, label, count, interval or result reads
usage, so no graded result moves.
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
STUDIES = ("gap-study", "gap-study-2", "gap-study-3")
CLASSES = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
ORDER = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens", "output_tokens")
LABEL = {"input_tokens": "input", "cache_read_input_tokens": "cache read",
         "cache_creation_input_tokens": "cache write", "output_tokens": "output"}
DATED = "2026-10-02"
OUT = HERE / ("CORRECTION-%s.md" % DATED)

# Round 1's COSTS.md also quotes context tokens in prose, written on 8 September 2026 from these transcripts
# (the only ones on disk at commit 990fb47, which wrote the sentences). Each is checked against the prose.
PROSE = (
    {"where": "evals/gap-study/COSTS.md, the walks note and the notes recorded before any take",
     "quote": "5.5 to 6.4 M context tokens", "study": "gap-study",
     "paths": ("evals/transcripts/confounded-refusal/control/transcript.jsonl",
               "evals/transcripts/confounded-refusal/positive/transcript.jsonl")},
    {"where": "evals/gap-study/COSTS.md, the walks note",
     "quote": "1.1 to 2.0 M context tokens", "study": "gap-study",
     "paths": ("evals/gap-study/walks/template-adherence/1/transcript.jsonl",
               "evals/gap-study/walks/template-adherence/2/transcript.jsonl")},
)


# Every line in the repository that quotes a published token figure, or the tables as a token source, as of this
# correction. `--check` fails if a listed line no longer carries its text, so a moved line is noticed. None is
# edited: each sits inside a finished round's folder, which is a record, and rounds 1 and 2 are also bound byte for
# byte by the copy checks of rounds 2 and 3 (`copy_manifest.py --check`).
CITED = (
    ("evals/gap-study/COSTS.md", 21, "## Per take", "the per-take table"),
    ("evals/gap-study/COSTS.md", 137, "## Pre-freeze walks", "the walks table"),
    ("evals/gap-study/COSTS.md", 157, "5.5 to 6.4 M context tokens", "prose: a take of the earlier Layer B evaluation"),
    ("evals/gap-study/COSTS.md", 161, "1.1 to 2.0 M context tokens", "prose: the first two walks"),
    ("evals/gap-study/COSTS.md", 168, "## Per model", "the per-model table"),
    ("evals/gap-study/COSTS.md", 201, "5.5 to 6.4 M context tokens", "prose: the same Layer B take"),
    ("evals/gap-study/README.md", 43, "| `COSTS.md` | tokens by class", "names COSTS.md as the token record"),
    ("evals/gap-study/language-allowlist.json", 23, "The 100 is the number of input tokens for one take",
     "quotes one published input cell"),
    ("evals/gap-study/verification/2026-09-12-95c4923.md", 945, "| input | cache read | cache write | output |",
     "a verifier report quoting per-take rows"),
    ("evals/gap-study/verification/2026-09-12-95c4923.md", 956, "| context tokens | output tokens |",
     "a verifier report quoting the per-model rows"),
    ("evals/gap-study/verification/2026-09-12-a463ed5.md", 946, "| input | cache read | cache write | output |",
     "a verifier report quoting per-take rows"),
    ("evals/gap-study/verification/2026-09-12-a463ed5.md", 959, "| context tokens | output tokens |",
     "a verifier report quoting the per-model rows"),
    ("evals/gap-study-2/COSTS.md", 11, "## Per take", "the per-take table"),
    ("evals/gap-study-2/COSTS.md", 122, "## Pre-freeze walks", "the walks table"),
    ("evals/gap-study-2/COSTS.md", 133, "## Per model", "the per-model table"),
    ("evals/gap-study-2/verification/verifier-1.md", 374, "| input | cache read | cache write | output |",
     "a verifier report quoting a per-take row"),
    ("evals/gap-study-2/verification/verifier-1.md", 379, "| 23,665,927 | 260,712 |",
     "a verifier report quoting the per-model rows"),
    ("evals/gap-study-2/verification/verifier-2.md", 447, "| input | cache read | cache write | output |",
     "a verifier report quoting a per-take row"),
    ("evals/gap-study-2/verification/verifier-2.md", 451, "| context tokens | output tokens |",
     "a verifier report quoting the per-model rows"),
    ("evals/gap-study-3/COSTS.md", 11, "## Per take", "the per-take table"),
    ("evals/gap-study-3/COSTS.md", 70, "## Pre-freeze walks", "the walks table"),
    ("evals/gap-study-3/COSTS.md", 83, "## Per model", "the per-model table"),
    ("evals/gap-study-3/language-allowlist.json", 16, "The hit is a token count, not a rate",
     "quotes one published input cell"),
    ("evals/gap-study-3/prereg.json", 2616, "exactly one hundred input tokens", "amendment 1 quotes the same cell"),
    ("evals/gap-study-3/verification/verify-1.md", 210, "pattern `hundred`", "a verifier report on the same cell"),
    ("evals/gap-study-3/verification/verify-2.md", 198, "exactly one hundred input", "a verifier report on the same cell"),
    ("evals/gap-study-3/verification/verify-2.md", 204, "input column reads one hundre", "a verifier report on the same cell"),
    ("evals/gap-study-3/verification/verify-3.md", 211, "line 27 of `COSTS.md", "a verifier report on the same cell"),
    ("evals/gap-study-3/verification/verify-3.md", 217, "pattern `hundred`", "a verifier report on the same cell"),
)


class Disagreement(ValueError):
    """Two records of one call carry different usage; the reader will not pick one."""


def read_calls(path):
    """Usage by class with each call counted once, and the record and call counts it came from."""
    path = Path(path)
    calls = {}
    records = 0
    partial = 0
    for line in path.read_text(errors="replace").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(rec, dict):
            continue
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        usage = msg.get("usage") or {}
        if not usage:
            continue
        records += 1
        key = (msg.get("id"), rec.get("requestId"))
        if not key[0] or not key[1]:
            partial += 1
            key = ("partial", records)
        counts = tuple(usage.get(c, 0) or 0 for c in CLASSES)
        if key in calls and calls[key] != counts:
            raise Disagreement("%s: call %s carries two different usages, %s and %s" % (path, key, calls[key], counts))
        calls[key] = counts
    out = {"records": records, "calls": len(calls), "partial_key": partial}
    for i, c in enumerate(CLASSES):
        out[c] = sum(v[i] for v in calls.values())
    return out


_PINNED = {}


def pinned(study):
    """The round's own pinned reader, imported unmodified."""
    if study not in _PINNED:
        spec = importlib.util.spec_from_file_location("pinned_costs_" + study.replace("-", "_"),
                                                      str(REPO / "evals" / study / "costs.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PINNED[study] = mod
    return _PINNED[study]


def context(r):
    return r["input_tokens"] + r["cache_read_input_tokens"] + r["cache_creation_input_tokens"]


def collect():
    """Per round: every take and walk its COSTS.md tabulates, as published beside counted by call."""
    got = {}
    for study in STUDIES:
        base = REPO / "evals" / study
        read = pinned(study).read_one
        takes, walks = [], []
        for p in sorted((base / "transcripts").glob("*/*/*/*/transcript.jsonl")):
            takes.append({"slot": p.parent.relative_to(base / "transcripts").parts, "pub": read(p),
                          "call": read_calls(p)})
        for p in sorted((base / "walks").glob("*/*/transcript.jsonl")):
            walks.append({"slot": (p.parent.parent.name, p.parent.name), "pub": read(p), "call": read_calls(p)})
        models = {}
        for t in takes:
            m = models.setdefault(t["slot"][2], {"takes": 0, "pub_ctx": 0, "call_ctx": 0, "pub_out": 0, "call_out": 0})
            m["takes"] += 1
            m["pub_ctx"] += context(t["pub"])
            m["call_ctx"] += context(t["call"])
            m["pub_out"] += t["pub"]["output_tokens"]
            m["call_out"] += t["call"]["output_tokens"]
        got[study] = {"takes": takes, "walks": walks, "models": dict(sorted(models.items()))}
    return got


def prose():
    """Round 1's prose figures: each quoted range, as published (rounded the way the prose rounds) and by call."""
    out = []
    for item in PROSE:
        read = pinned(item["study"]).read_one
        pub = [context(read(REPO / p)) for p in item["paths"]]
        call = [context(read_calls(REPO / p)) for p in item["paths"]]
        out.append(dict(item, pub=pub, call=call))
    return out


def _n(x):
    return "{:,}".format(x)


def _ratio(a, b):
    return "%.2f" % (a / b) if b else "none"


def _sum(rows, side):
    return {c: sum(r[side][c] for r in rows) for c in CLASSES}


def _cells(r):
    return " | ".join(_n(r[c]) for c in ORDER)


def _m(x):
    return "%.1f" % (x / 1e6)


def render(got, quoted):
    everything = [r for s in got.values() for r in s["takes"] + s["walks"]]
    pub_all, call_all = _sum(everything, "pub"), _sum(everything, "call")
    records = sum(r["call"]["records"] for r in everything)
    calls = sum(r["call"]["calls"] for r in everything)
    tp, tc = sum(pub_all.values()), sum(call_all.values())
    L = ["# Correction, %s: the Gap Study token tables count records, not calls" % DATED, "",
         "_Written by `evals/gap-study-costs-by-call/costs_by_call.py --write`; never edited by hand. "
         "`--check` fails when this page differs from what the script writes, or when a published figure it prints "
         "is not in that round's `COSTS.md`. Decision 0271 records why it exists._", "",
         "## What was wrong", "",
         "The token tables in `evals/gap-study/COSTS.md`, `evals/gap-study-2/COSTS.md` and "
         "`evals/gap-study-3/COSTS.md` add up usage over transcript records, not over model calls.",
         "Claude Code writes one record per content block of a model reply (thinking, text, tool use), and each "
         "of those records carries the whole reply's usage, so a reply with three blocks was counted three times.",
         "Across the three rounds, %s usage records hold %s calls, and the tables published %s tokens, %s times "
         "the %s the calls used." % (_n(records), _n(calls), _n(tp), _ratio(tp, tc), _n(tc)),
         "Every duplicate record carries the same usage as the others of its call, so counting each call once is "
         "unambiguous.", "",
         "The published tables stand as published and are not edited; this page gives the figures counted once "
         "per call beside them.",
         "A call is counted once per pair of `message.id` and `requestId`.", "",
         "## What does not change", "",
         "- No graded result. No grader, label, count, interval or result file reads token usage; the "
         "transcript parser the graders use discards it.",
         "- Wall clock, the recorded pauses, and each round's dollar line. None reads usage.",
         "- The published `COSTS.md` tables and the pinned `costs.py` that wrote them.", "",
         "## Each table, and what is wrong in it", "",
         "| round | table | what is wrong | corrected below |", "|---|---|---|---|"]
    for study in STUDIES:
        L += ["| `%s` | Per take | every token cell counts records, not calls | per take |" % study,
              "| `%s` | Pre-freeze walks | every token cell counts records, not calls | per walk |" % study,
              "| `%s` | Per model | context and output totals are sums of the per-take cells | per model |" % study,
              "| `%s` | Recorded pauses | nothing: no token figure | not needed |" % study]
    L += ["| `gap-study` | prose notes (walks note; notes recorded before any take) | two quoted ranges of context "
          "tokens were read from record sums | prose figures |", "",
          "## All three rounds", "",
          "| class | published | counted once per call | published over counted |", "|---|---|---|---|"]
    L += ["| %s | %s | %s | %s |" % (LABEL[c], _n(pub_all[c]), _n(call_all[c]), _ratio(pub_all[c], call_all[c]))
          for c in ORDER]
    L += ["| all four classes | %s | %s | %s |" % (_n(tp), _n(tc), _ratio(tp, tc)), ""]
    for study, s in got.items():
        L += ["## `%s`" % study, ""]
        for kind, name in (("takes", "Per take"), ("walks", "Pre-freeze walks")):
            rows = s[kind]
            p, c = _sum(rows, "pub"), _sum(rows, "call")
            L += ["### %s: totals of the %s table" % (study, name), "",
                  "%d transcripts; %s usage records hold %s calls." % (
                      len(rows), _n(sum(r["call"]["records"] for r in rows)), _n(sum(r["call"]["calls"] for r in rows))),
                  "", "| class | published | counted once per call | published over counted |", "|---|---|---|---|"]
            L += ["| %s | %s | %s | %s |" % (LABEL[k], _n(p[k]), _n(c[k]), _ratio(p[k], c[k])) for k in ORDER]
            L.append("")
        L += ["### %s: per model" % study, "",
              "| model | graded takes | context tokens, published | context tokens, counted once | "
              "output tokens, published | output tokens, counted once |", "|---|---|---|---|---|---|"]
        L += ["| `%s` | %d | %s | %s | %s | %s |" % (m, v["takes"], _n(v["pub_ctx"]), _n(v["call_ctx"]),
                                                   _n(v["pub_out"]), _n(v["call_out"])) for m, v in s["models"].items()]
        L += ["", "### %s: per take" % study, "",
              "Published cells first, then the same cells counted once per call.", "",
              "| task | half | model | take | records | calls | published: input | cache read | cache write | output "
              "| counted once: input | cache read | cache write | output |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in s["takes"]:
            task, half, model, take = r["slot"]
            L.append("| `%s` | %s | `%s` | %s | %d | %d | %s | %s |" % (
                task, half, model, take, r["call"]["records"], r["call"]["calls"], _cells(r["pub"]), _cells(r["call"])))
        L += ["", "### %s: per walk" % study, "",
              "| walk | records | calls | published: input | cache read | cache write | output "
              "| counted once: input | cache read | cache write | output |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in s["walks"]:
            L.append("| `%s` %s | %d | %d | %s | %s |" % (r["slot"][0], r["slot"][1], r["call"]["records"],
                                                         r["call"]["calls"], _cells(r["pub"]), _cells(r["call"])))
        L.append("")
    L += ["## Prose figures", "",
          "| where | published words | published, exact | counted once per call |", "|---|---|---|---|"]
    for q in quoted:
        L.append("| %s | \"%s\" | %s | %s to %s M (%s) |" % (
            q["where"], q["quote"], " and ".join(_n(x) for x in q["pub"]), _m(min(q["call"])), _m(max(q["call"])),
            " and ".join(_n(x) for x in q["call"])))
    L += ["", "## Where the published figures are cited", "",
          "Each line below quotes a published token figure, or names the tables as the token record.",
          "None is edited: each sits inside a finished round's folder, which is a record, and rounds 1 and 2 are "
          "also bound byte for byte by the copy checks of rounds 2 and 3.",
          "The input cell quoted as one hundred is the published figure for `confounded-design`, positive, "
          "`claude-opus-5`, take 1, in round 1 and again in round 3; counted once per call it is %s and %s." % tuple(
              _n(r["call"]["input_tokens"]) for study in ("gap-study", "gap-study-3") for r in got[study]["takes"]
              if r["slot"] == ("confounded-design", "positive", "claude-opus-5", "1")),
          "No page outside the three study folders (the README, `docs/`, `DEVELOPMENT.md`, the demonstration site) "
          "quoted these figures before this correction; `docs/EVALS.md` now points here.", "",
          "| where | what it quotes |", "|---|---|"]
    L += ["| `%s:%d` | %s |" % (path, line, what) for path, line, _, what in CITED]
    L.append("")
    return "\n".join(L)


def evals_sentence(got):
    """The figures docs/EVALS.md quotes, as the reader derives them; --check finds them there verbatim."""
    everything = [r for st in got.values() for r in st["takes"] + st["walks"]]
    tp, tc = sum(_sum(everything, "pub").values()), sum(_sum(everything, "call").values())
    return "published %s tokens, %s times the %s the calls used" % (_n(tp), _ratio(tp, tc), _n(tc))


def binding_problems(got, costs, evals=None):
    """Every published figure on this page must be in that round's COSTS.md, as that file prints it."""
    out = []
    for study, s in got.items():
        text = costs[study]
        for r in s["takes"]:
            task, half, model, take = r["slot"]
            row = "| `%s` | %s | `%s` | %s | %s |" % (task, half, model, take, _cells(r["pub"]))
            if row not in text:
                out.append("%s COSTS.md has no per-take row %s" % (study, row))
        for r in s["walks"]:
            row = "| `%s` %s | `%s` | %s |" % (r["slot"][0], r["slot"][1], r["pub"]["model"] or "unrecorded",
                                              _cells(r["pub"]))
            if row not in text:
                out.append("%s COSTS.md has no walk row %s" % (study, row))
        for m, v in s["models"].items():
            row = "| `%s` | %d | %s | %s |" % (m, v["takes"], _n(v["pub_ctx"]), _n(v["pub_out"]))
            if row not in text:
                out.append("%s COSTS.md has no per-model row %s" % (study, row))
    if evals is None:
        evals = (REPO / "docs" / "EVALS.md").read_text()
    if evals_sentence(got) not in evals:
        out.append("docs/EVALS.md does not quote %r" % evals_sentence(got))
    for path, line, needle, _ in CITED:
        lines = (REPO / path).read_text().split("\n")
        if len(lines) < line or needle not in lines[line - 1]:
            out.append("%s:%d no longer carries %r" % (path, line, needle))
    for q in prose():
        if "%s to %s M context tokens" % (_m(min(q["pub"])), _m(max(q["pub"]))) != q["quote"]:
            out.append("the quoted range %r is not what its transcripts sum to" % q["quote"])
        if q["quote"] not in costs[q["study"]].replace("\n  ", " ").replace("\n", " "):
            out.append("%s COSTS.md no longer carries %r" % (q["study"], q["quote"]))
    return out


def problems(page=None):
    got = collect()
    wanted = render(got, prose())
    if page is None:
        page = OUT.read_text() if OUT.is_file() else None
    out = []
    if page != wanted:
        out.append("%s is not what the reader writes. Run: python3 evals/gap-study-costs-by-call/costs_by_call.py "
                   "--write" % OUT.name)
    costs = {s: (REPO / "evals" / s / "COSTS.md").read_text() for s in STUDIES}
    return out + binding_problems(got, costs)


def main():
    ap = argparse.ArgumentParser(description="The Gap Study token tables, each call counted once.")
    ap.add_argument("--write", action="store_true", help="write %s" % OUT.name)
    ap.add_argument("--check", action="store_true", help="exit 1 unless %s is current and bound" % OUT.name)
    args = ap.parse_args()
    if args.write:
        OUT.write_text(render(collect(), prose()))
        print("wrote %s" % OUT.name)
        return 0
    if args.check:
        found = problems()
        for p in found:
            print(p)
        if found:
            return 1
        print("%s is what the reader writes, and every published figure on it is in its round's COSTS.md" % OUT.name)
        return 0
    got = collect()
    for study, s in got.items():
        for kind in ("takes", "walks"):
            p, c = _sum(s[kind], "pub"), _sum(s[kind], "call")
            print("%s %s: %d records, %d calls" % (study, kind, sum(r["call"]["records"] for r in s[kind]),
                                                  sum(r["call"]["calls"] for r in s[kind])))
            for k in ORDER:
                print("   %-11s published %13s   counted once %13s" % (LABEL[k], _n(p[k]), _n(c[k])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
