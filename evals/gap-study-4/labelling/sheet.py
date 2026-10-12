#!/usr/bin/env python3
"""CP8's blind sheet: each sampled take's text and actions after the probe, the label definitions and a stop-cause
column, and nothing that says which model, arm or harness ran it or what the grader said.

    python3 evals/gap-study-4/labelling/sheet.py --contents <post-probe.json> --out <sheet.md>

BLIND BY CONSTRUCTION. The sheet is rendered from blind items only, each exactly {"sheet_id", "task", "text",
"actions"}, built by blind_items(), which copies those four and nothing else from a sample item and the take's
post-probe content; render() refuses any item holding another key. The sheet id is the sample's shuffled number,
never the take's id. Inside the content (the agent's own words can name itself) every model id of the design, every
harness name, the vendor and family words in VENDOR_WORDS and every take id of the frame are replaced by HIDDEN,
case-insensitively, and write_sheet() refuses a rendered sheet in which any of them is still found. Model id, arm,
harness, wording, repeat or pressure, grader label, verdict, route and the take's id never reach an item.

THE INPUTS. The sample (sample.json), the frame (frame.json, for the take ids to hide), the design (prereg.json's
labelling_design), the definitions (definitions.json: {task: {label: meaning}}, each task's label set exactly
grader_labels(task), bound by validate_definitions) and the post-probe content ({take: {"text": str, "actions": [str]}}), which
CP8's reader of a take folder writes (not built here; Q-w11d-2). Every take renders in the same neutral format, and
each action must already be in it: one of ACTION_VERBS, a space, and its object ("read notes/plan.md", "run make
check"), so no harness's own tool names (each harness names its tools differently) reach the sheet; any other action
is refused.

WHAT IT CANNOT HIDE, SAID PLAINLY. A model that names itself in words off these lists, or writes in a style a reader
recognises, is not hidden by a word list; the reader that writes the content keeps harness furniture out of the text,
and Javier labels what the take did, not who did it.

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
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)
for _p in (_STUDY, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import sample  # noqa: E402
import stats  # noqa: E402

DEFINITIONS = os.path.join(_HERE, "definitions.json")
ITEM_FIELDS = ("sheet_id", "task", "text", "actions")
CONTENT_FIELDS = ("text", "actions")
HIDDEN = "[hidden]"
VENDOR_WORDS = ("anthropic", "claude", "opus", "sonnet", "haiku", "fable", "openai", "chatgpt", "gpt", "codex",
                "google", "deepmind", "gemini")
STOP_CAUSES = stats.labels4.STOPS
ACTION_VERBS = ("read", "write", "delete", "run")
NEUTRAL_ACTION = re.compile("(?:" + "|".join(ACTION_VERBS) + r") \S.*")


class SheetError(Exception):
    """An input or a rendered sheet the blind sheet refuses."""


def hidden_tokens(frame, design) -> list:
    """Every string the sheet must never show, longest first."""
    toks = set(VENDOR_WORDS) | set(design["harness_models"])
    toks |= {m for ms in design["harness_models"].values() for m in ms}
    toks |= {e["take"] for e in frame}
    return sorted(toks, key=lambda t: (-len(t), t))


def mask(text: str, tokens: list) -> str:
    for t in tokens:
        text = re.sub(re.escape(t), HIDDEN, text, flags=re.IGNORECASE)
    return text


def leak_problems(text: str, tokens: list) -> list:
    low = text.lower()
    return [f"LEAK: the sheet shows {t!r}" for t in tokens if t.lower() in low]


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
    return c


def blind_items(doc: dict, contents: dict, frame, design) -> list:
    """The sheet's items: sheet id, task, and the masked text and actions after the probe. Nothing else is copied."""
    tokens = hidden_tokens(frame, design)
    items = []
    for it in sorted(doc["items"], key=lambda i: i["sheet_id"]):
        if it["take"] not in contents:
            raise SheetError(f"{it['sheet_id']}: no post-probe content for its take")
        c = validate_content(contents[it["take"]], it["sheet_id"])
        items.append({"sheet_id": it["sheet_id"], "task": it["stratum"]["task"], "text": mask(c["text"], tokens),
                      "actions": [mask(a, tokens) for a in c["actions"]]})
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
        out += [f"## {it['sheet_id']} (task {it['task']})", "", "Text after the probe:", "", "```", it["text"], "```",
                "", "Actions after the probe:"]
        out += [f"- {a}" for a in it["actions"]] or ["- none"]
        out += ["", "Label: ", "Stop cause: ", ""]
    return "\n".join(out)


def write_sheet(doc, contents, frame, design, defs, grader_labels) -> str:
    """The rendered sheet, or SheetError when any hidden string is still in it."""
    items = blind_items(doc, contents, frame, design)
    validate_definitions(defs, [i["task"] for i in items], grader_labels)
    text = render(items, defs)
    bad = leak_problems(text, hidden_tokens(frame, design))
    if bad:
        raise SheetError("; ".join(bad))
    return text


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--contents", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if os.path.abspath(args.out).startswith(_STUDY + os.sep):
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
