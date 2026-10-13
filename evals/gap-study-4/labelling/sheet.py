#!/usr/bin/env python3
"""CP8's blind sheet: each sampled take's text and actions after the probe, the label definitions and a stop-cause
column, and nothing that says which model, arm or harness ran it or what the grader said.

    python3 evals/gap-study-4/labelling/sheet.py --contents <post-probe.json> --out <sheet.md>

BLIND BY CONSTRUCTION. The sheet is rendered from blind items only, each exactly {"sheet_id", "task", "text",
"actions"}, built by blind_items(), which copies those four and nothing else from a sample item and the take's
post-probe content; render() refuses any item holding another key. The sheet id is the sample's shuffled number,
never the take's id. Inside the content (the agent's own words can name itself) the text is read as tokens (tokens():
NFKC, casefold, every character that is not a letter or a digit a separator, letters and digits split apart), so no
spelling of a separator (a non-breaking hyphen, an en dash, a line break, a colon, brackets) and no full-width form
escapes. Every hidden token sequence (hidden_set: the vendor words, every harness name, model id and take id whole;
every alphabetic part of three or more letters of a design id; every design version as a digit sequence, wherever it
stands; the harness furniture in FURNITURE) is replaced by HIDDEN over its original span. Over-masking an ordinary
number is the price of a blind sheet. write_sheet() is the backstop: it refuses a rendered sheet whose token stream
still holds any hidden sequence, a short id part beside a mask, or a harness's own tool or instruction-file name
(HARNESS_WORDS); a human rewrites that take's content, nothing is guessed. Model id, arm, harness, wording, repeat or
pressure, grader label, verdict, route and the take's id never reach an item.

THE INPUTS. The sample (sample.json), the frame (frame.json, for the take ids to hide), the design (prereg.json's
labelling_design), the definitions (definitions.json: {task: {label: meaning}}, each task's label set exactly
grader_labels(task), bound by validate_definitions) and the post-probe content ({take: {"text": str, "actions": [str]}}), which
CP8's reader of a take folder writes (not built here; Q-w11d-2). Every take renders in the same neutral format, and
each action must already be in it: one of ACTION_VERBS, a space, and its object ("read notes/plan.md", "run make
check"), and no action may name a harness's own tool or instruction file (HARNESS_WORDS); any other action is refused.
The CP8 reader slice that writes the content (Q-w11d-2) must pass this file's checks on its own output as an
acceptance test: write_sheet over every sampled take, with no refusal.

RENDERING. The text and the actions each sit in a code fence one backtick longer than any backtick run in them, so
no take can close its fence and have the rest read as Markdown or HTML (an entity such as &#72; shows as written).

WHAT IT CANNOT HIDE, SAID PLAINLY (Javier's call, review W11D-R3 residuals): look-alike letters from other scripts
(a Cyrillic a in Claude; NFKC does not fold scripts, a TR39 confusables fold would), names spelled out letter by
letter, number words ("four point five"), misspellings, and digits from other scripts. A model that names itself in words off these lists, or writes in a style a reader
recognises, is not hidden by a word list; the reader that writes the content keeps harness furniture out of the text,
and Javier labels what the take did, not who did it.

BLIND BY PROCEDURE, TOO (a rule for the CP8 brief; no code can hold it). Whoever runs sheet.py is not the labeller,
and the labeller never opens sample.json (it names model, harness and arm per sheet id) or the --contents file (it
is keyed by take id): he reads only the sheet and writes only labels.json.

WHERE THE SHEET GOES. --out names a file outside the study folder: the sheet holds agent text, which is a record and
not this study's prose (Q-w11d-3). Javier writes his labels into labelling/labels.json, which agreement.py reads.

No model, no network, standard library only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import itertools
import sys
import unicodedata

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_STUDY, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sample  # noqa: E402
import stats  # noqa: E402
import transcript_view as tv  # noqa: E402

DEFINITIONS = os.path.join(_HERE, "definitions.json")
ITEM_FIELDS = ("sheet_id", "task", "text", "actions")
CONTENT_FIELDS = ("text", "actions")
HIDDEN = "[hidden]"
VENDOR_WORDS = ("anthropic", "claude", "opus", "sonnet", "haiku", "fable", "openai", "chatgpt", "gpt", "codex",
                "google", "deepmind", "gemini")
STOP_CAUSES = stats.labels4.STOPS
ACTION_VERBS = ("read", "write", "delete", "run")
NEUTRAL_ACTION = re.compile("(?:" + "|".join(ACTION_VERBS) + r") \S.*")
# Each harness's own tool and instruction-file names (review W11D-R1-3). Claude Code's are derived from
# transcript_view.CC_TOOLS, the table its reader maps, plus the names its reader has not met yet. Codex's and Gemini's
# are copied from lanes w11a (transcript_codex's item types, D8 section 1) and w11b (transcript_gemini.GEMINI_TOOLS),
# whose tables are not on this lane's base; Q-w11d-6 binds them to those tables at the merge.
HARNESS_WORDS = {
    "claude-code": tuple(tv.CC_TOOLS) + ("Task", "TodoWrite", "MultiEdit", "NotebookEdit", "WebFetch", "WebSearch",
                                         "ExitPlanMode", "BashOutput", "KillShell", "CLAUDE.md"),
    "codex": ("apply_patch", "update_plan", "exec_command", "command_execution", "file_change", "mcp_tool_call",
              "AGENTS.md"),
    "gemini": ("run_shell_command", "read_file", "write_file", "replace", "glob", "search_file_content",
               "list_directory", "write_todos", "GEMINI.md"),
}
# Harness furniture the sheet can see as tokens (review W11D-R2, residual): a CLI's name word, an entry-point variable,
# a TOML config file (Codex's). The rest (a harness's version string, its home folder layout) is the CP8 reader's
# acceptance test (Q-w11d-2): write_sheet over every sampled take, with no refusal.
FURNITURE = ("cli", "entrypoint", "toml")
# In free text only the names no plain sentence uses are refused: one with an underscore, or a case that is neither
# all lower nor a capitalised word (TodoWrite, AGENTS.md); "Read", "replace" or "glob" in a sentence are words, and are refused in an
# action only.
TEXT_HARNESS_WORDS = tuple(sorted({w for ws in HARNESS_WORDS.values() for w in ws
                                   if "_" in w or w not in (w.lower(), w.capitalize())}))


class SheetError(Exception):
    """An input or a rendered sheet the blind sheet refuses."""


def tokens(text: str) -> list:
    """The text as tokens over its own character positions (review W11D-R2-1): each character is NFKC-normalised and
    casefolded, every character that is not a letter or a digit is a separator (every Unicode dash and space,
    punctuation, line breaks), and a run of letters and a run of digits are tokens of their own ("haiku4.5" is
    haiku, 4, 5). An invisible format character (Unicode category Cf: a soft hyphen, a zero-width space or joiner,
    U+2060) is dropped before grouping, so "Hai" + U+00AD + "ku" is one token (review W11D-R3-2). Each token is (its normalised text, the start and the end of its span in the original text)."""
    out, kind = [], None
    for i, ch in enumerate(text):
        for c in unicodedata.normalize("NFKC", ch).casefold():
            if unicodedata.category(c) == "Cf":
                continue
            k = (c.isalpha(), c.isdigit()) if c.isalpha() or c.isdigit() else None
            if k is not None and k == kind:
                out[-1] = (out[-1][0] + c, out[-1][1], i + 1)
            elif k is not None:
                out.append((c, i, i + 1))
            kind = k
    return out


def words(text: str) -> tuple:
    return tuple(t for t, _, _ in tokens(text))


def versions(models) -> set:
    """Every design version as a digit-token sequence: each run of digit tokens of a model id, and every stretch of two
    or more of a longer run (claude-haiku-4-5-20251001 gives 4 5 20251001, 4 5 and 5 20251001; gpt-6-luna gives 6)."""
    out = set()
    for m in models:
        for digits, run in itertools.groupby(words(m), key=str.isdigit):
            r = tuple(run)
            if digits:
                out |= {r[i:j] for i in range(len(r)) for j in range(i + 2, len(r) + 1)} | {r}
    return out


def hidden_set(frame, design) -> dict:
    """What the sheet must never show, as token sequences (review W11D-R2-1, ruling w11d-R2-fold):
    sequences  every vendor word, every harness name, every model id and every take id, whole; every part of three or
               more characters of every design id and harness name (sol, luna, flash, lite, code, 20251001, ...);
               every design version (versions()), wherever it stands; and the harness furniture in FURNITURE.
               Longest first.
    residual   every short alphabetic part of a design id (under three letters): a mask beside one is refused."""
    models = [m for ms in design["harness_models"].values() for m in ms]
    names = list(design["harness_models"]) + models
    seqs = {words(t) for t in set(VENDOR_WORDS) | set(names) | {e["take"] for e in frame}}
    seqs |= {(p,) for n in names for p in words(n) if len(p) >= 3}
    seqs |= versions(models)
    seqs |= {words(f) for f in FURNITURE}
    residual = sorted({p for n in names for p in words(n) if p.isalpha() and len(p) < 3})
    return {"sequences": sorted(seqs, key=lambda q: (-len(q), q)), "residual": residual}


def _ranges(toks: list, hidden: dict) -> list:
    """(first, last + 1) token ranges of every hidden sequence in toks, the longest at each position, left to right."""
    out, i = [], 0
    names = [t for t, _, _ in toks]
    while i < len(names):
        for q in hidden["sequences"]:
            if tuple(names[i:i + len(q)]) == q:
                out.append((i, i + len(q)))
                i += len(q)
                break
        else:
            i += 1
    return out


def mask(text: str, hidden: dict) -> str:
    toks = tokens(text)
    spans = _ranges(toks, hidden)
    out, at = [], 0
    for i, j in spans:
        out += [text[at:toks[i][1]], HIDDEN]
        at = toks[j - 1][2]
    return "".join(out) + text[at:]


def leak_problems(text: str, hidden: dict) -> list:
    """The backstop: on the text's token stream (a HIDDEN mark is the token "hidden", in no sequence), any hidden
    sequence still there, any short id part or any number beside a mark (review W11D-R3-1: a family's major version
    names it, "Gemini 3"), and a harness's own tool or instruction-file name no plain sentence uses
    (TEXT_HARNESS_WORDS). Any line refuses the sheet; a human rewrites that take's content."""
    toks = tokens(text)
    marked = [t == "hidden" and text[s - 1:s] == "[" and text[e:e + 1] == "]" for t, s, e in toks]
    found = sorted({tuple(t for t, _, _ in toks[i:j]) for i, j in _ranges(toks, hidden)})
    out = [f"LEAK: the sheet shows {' '.join(q)!r}" for q in found]
    near, digits = set(), set()
    for k, m in enumerate(marked):
        if m:
            for n in (k - 1, k + 1):
                if 0 <= n < len(toks) and toks[n][0] in hidden["residual"]:
                    near.add(toks[n][0])
                if 0 <= n < len(toks) and toks[n][0].isdigit():
                    digits.add(toks[n][0])
    out += [f"LEAK: {HIDDEN} stands next to the id part {p!r}" for p in sorted(near)]
    out += [f"LEAK: {HIDDEN} stands next to the number {d!r}" for d in sorted(digits)]
    out += [f"LEAK: the sheet names the harness word {w!r}" for w in TEXT_HARNESS_WORDS
            if re.search(_word(w), text, re.IGNORECASE)]
    return out


def _word(w: str) -> str:
    return r"(?<![A-Za-z0-9_])" + re.escape(w) + r"(?![A-Za-z0-9_])"


def harness_word(action: str) -> bool:
    """Does the action name a harness's own tool or instruction file (a file name in any case, a tool as written)?"""
    return any(re.search(_word(w), action, re.IGNORECASE if w.endswith(".md") else re.NOFLAG)
               for ws in HARNESS_WORDS.values() for w in ws)


def validate_content(c, take: str) -> dict:
    if not isinstance(c, dict) or set(c) != set(CONTENT_FIELDS):
        raise SheetError(f"take {take}: post-probe content holds exactly {CONTENT_FIELDS}")
    if not isinstance(c["text"], str):
        raise SheetError(f"take {take}: text is a string")
    if not isinstance(c["actions"], list) or not all(isinstance(a, str) for a in c["actions"]):
        raise SheetError(f"take {take}: actions is a list of strings")
    for a in c["actions"]:
        if not NEUTRAL_ACTION.fullmatch(a):
            raise SheetError(f"take {take}: an action not in the neutral format: {a!r}")
        if harness_word(a):
            raise SheetError(f"take {take}: an action names a harness's own tool or file: {a!r}")
    return c


def blind_items(doc: dict, contents: dict, frame, design) -> list:
    """The sheet's items: sheet id, task, and the masked text and actions after the probe. Nothing else is copied."""
    hidden = hidden_set(frame, design)
    items = []
    for it in sorted(doc["items"], key=lambda i: i["sheet_id"]):
        if it["take"] not in contents:
            raise SheetError(f"{it['sheet_id']}: no post-probe content for its take")
        c = validate_content(contents[it["take"]], it["sheet_id"])
        items.append({"sheet_id": it["sheet_id"], "task": it["stratum"]["task"], "text": mask(c["text"], hidden),
                      "actions": [mask(a, hidden) for a in c["actions"]]})
    return items


def validate_definitions(defs, tasks, grader_labels) -> dict:
    """{task: {label: meaning}} for every task sampled, each label set exactly the grader's, every meaning written."""
    if not isinstance(defs, dict):
        raise SheetError("the definitions are {task: {label: meaning}}")
    for task in sorted(set(tasks)):
        d = defs.get(task)
        if not isinstance(d, dict):
            raise SheetError(f"no definitions for task {task}")
        if set(d) != set(grader_labels[task]):
            raise SheetError(f"task {task}: the labels defined are not its grader's labels")
        for label, meaning in d.items():
            if not isinstance(meaning, str) or not meaning.strip():
                raise SheetError(f"task {task}: label {label} has no meaning written")
    return defs


def grader_labels(task: str) -> tuple:
    """The labels a take of the task can carry: its grader's (graders/<module>.LABELS, or TASK_LABELS[task] for a
    per-task grader), then labels4's reserved labels it lacks (a stop the ledger decides, never the grader)."""
    with open(os.path.join(_STUDY, "tasks", task + ".json"), encoding="utf-8") as fh:
        g = json.load(fh)["grader"]
    path = os.path.join(_STUDY, g["module"])
    spec = importlib.util.spec_from_file_location(g["module"], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    own = tuple(mod.TASK_LABELS[task]) if ":" in g["entry"] else tuple(mod.LABELS)
    return own + tuple(x for x in stats.labels4.RESERVED if x not in own)


def fence(*texts: str) -> str:
    """A code fence one backtick longer than any backtick run in the texts (three at least), so none can close it."""
    return "`" * max([3] + [len(r) + 1 for t in texts for r in re.findall("`+", t)])


def render(items: list, defs: dict) -> str:
    out = ["# Blind labelling sheet", "",
           "For each take: read the text and actions after the probe, write one label from its task's definitions, "
           "and a stop cause where the take stopped before the probe. Write both into labels.json under its sheet id.",
           "", f"Stop causes: {', '.join(STOP_CAUSES)}, or blank.", "", "## Label definitions", ""]
    for task in sorted({i["task"] for i in items}):
        out.append(f"### {task}")
        out += [f"- `{label}`: {meaning}" for label, meaning in sorted(defs[task].items())]
        out.append("")
    for it in items:
        if set(it) != set(ITEM_FIELDS):
            raise SheetError(f"a sheet item holds exactly {ITEM_FIELDS}")
        ft, fa = fence(it["text"]), fence(*it["actions"])
        out += [f"## {it['sheet_id']} (task {it['task']})", "", "Text after the probe:", "", ft, it["text"], ft,
                "", "Actions after the probe:"]
        out += ["", fa, *it["actions"], fa] if it["actions"] else ["- none"]
        out += ["", "Label: ", "Stop cause: ", ""]
    return "\n".join(out)


def write_sheet(doc, contents, frame, design, defs, grader_labels) -> str:
    """The rendered sheet, or SheetError when any hidden string is still in it."""
    items = blind_items(doc, contents, frame, design)
    validate_definitions(defs, [i["task"] for i in items], grader_labels)
    text = render(items, defs)
    bad = leak_problems(text, hidden_set(frame, design))
    if bad:
        raise SheetError("; ".join(bad))
    return text


def inside_study(path) -> bool:
    """Is path the study folder or under it, on real paths compared without case (review W11D-R1-4: this Mac's disk
    ignores case, so a path spelled in another case is the same folder)?"""
    real = os.path.normcase(os.path.realpath(_STUDY)).casefold()
    got = os.path.normcase(os.path.realpath(path)).casefold()
    return got == real or got.startswith(real + os.sep)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--contents", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if inside_study(args.out):
        print("sheet: FAIL --out is inside the study folder; the sheet holds agent text (Q-w11d-3)")
        return 1
    try:
        got = sample.derive()
        if got is None:
            print("sheet: no takes; no sheet written")
            return 1
        frame, design, doc = got
        with open(sample.SAMPLE, encoding="utf-8") as fh:
            if fh.read() != sample.render(doc):
                raise SheetError("sample.json differs from the draw; run sample.py --check")
        with open(args.contents, encoding="utf-8") as fh:
            contents = json.load(fh)
        with open(DEFINITIONS, encoding="utf-8") as fh:
            defs = json.load(fh)
        tasks = {i["stratum"]["task"] for i in doc["items"]}
        text = write_sheet(doc, contents, frame, design, defs, {t: grader_labels(t) for t in tasks})
    except (SheetError, sample.SampleError, stats.StatsError, OSError, ValueError) as err:
        print(f"sheet: FAIL {err}")
        return 1
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"sheet: wrote {len(doc['items'])} blind items to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
