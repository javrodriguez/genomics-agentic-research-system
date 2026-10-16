#!/usr/bin/env python3
"""The edited_text_file attachment: a NAMED DEPARTURE, read as harness furniture of a closed shape (glitch-6b's ruling 1,
15 Oct 2026, under Javier's delegation; CP6 walk w041, held with "unknown attachment type: 'edited_text_file'").

The facts the ruling rests on (lane-reports/attachment-vocabulary-20261016/edited-text-file-trigger-20261015.json, a
static read of the pinned 2.1.296 binary, never run): on every query Claude Code's changed_files pass runs over the
files the agent has read whole, and a file whose mtime is later than the read and whose content differs yields
{type: edited_text_file, filename, snippet}, whoever wrote it. It renders to the model as a steer to take the change as
the current state rather than revert it. In w041 the writer was the agent's own background job. No targeted switch
exists; CLAUDE_CODE_DISABLE_ATTACHMENTS would drop kinds round 3 carries. Round 3's 64 transcripts never carry it.

  E-admit      a w041-shaped record (exactly type, filename, snippet; strings) reads as one harness event, raw type
               attachment:edited_text_file, its text the snippet; an empty snippet (the binary empties it past its
               16384-character budget) is admitted; nothing of it reaches agent text or an operator line.
  E-furniture  a pre-registered awareness phrase inside the snippet is counted as harness furniture, under its raw
               type, and never as the agent's words.
  E-refuse     near misses refuse: an extra key, a missing key, no keys but the type, a filename or snippet of another
               type, an empty filename, and every case or spelling variant of the type name.
  E-allowlist  the allow-list is exactly the 16 names the vocabulary record lists as admitted plus edited_text_file,
               and each of the other 96 names in the pinned binary's vocabulary is refused, bare or in the
               edited_text_file shape.
  E-draft      the study draft names the departure: what it is, why it is admitted, that round 3 never showed it.
  E-witness    each clause dropped in an in-memory mutant turns a check red.

Every fixture here is synthetic; the vocabulary record is read, never written.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent.parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import transcript_view as tv  # noqa: E402

CC = tv.ROUND3_HARNESS
KIND = "edited_text_file"
VOCABULARY = REPO / "lane-reports/attachment-vocabulary-20261016/attachment-vocabulary-20261016.json"
FILENAME = "/synthetic/run-0000/gars/projects/run-0000/HISTORY.md"
SNIPPET = "     1\t# History\n     2\tSynthetic line: this is a test of the furniture.\n"
OP = {"type": "user", "message": {"content": "Run stage 00."}}
DROP = object()


def record(**over):
    a = {"type": KIND, "filename": FILENAME, "snippet": SNIPPET}
    for k, v in over.items():
        if v is DROP:
            a.pop(k, None)
        else:
            a[k] = v
    return {"type": "attachment", "isSidechain": False, "attachment": a}


def lines(*recs):
    return [json.dumps(r) for r in recs]


NEAR = {
    "an extra key": record(commandMode="prompt"),
    "an extra content key": record(content="x"),
    "the filename missing": record(filename=DROP),
    "the snippet missing": record(snippet=DROP),
    "only the type": record(filename=DROP, snippet=DROP),
    "a null filename": record(filename=None),
    "a numeric filename": record(filename=1),
    "a list filename": record(filename=[FILENAME]),
    "an empty filename": record(filename=""),
    "a null snippet": record(snippet=None),
    "a list snippet": record(snippet=[SNIPPET]),
    "an object snippet": record(snippet={"text": SNIPPET}),
    "a boolean snippet": record(snippet=False),
}
VARIANTS = ("Edited_text_file", "EDITED_TEXT_FILE", "edited-text-file", "editedTextFile", "edited_text_files",
            "edited_text_file ", " edited_text_file", "edited_textfile", "edited_file", "edited_image_file")


def admit_problems(view=tv) -> list:
    out = []
    for name, snippet in (("w041-shaped", SNIPPET), ("empty snippet", "")):
        rec = record(snippet=snippet)
        try:
            evs = view.events(CC, lines(OP, rec))
        except view.ViewError as e:
            out.append(f"E-admit {name}: refused: {e}")
            continue
        harness = [e for e in evs if e.kind == view.HARNESS]
        if [e.text for e in harness] != [snippet]:
            out.append(f"E-admit {name}: harness texts {[e.text for e in harness]!r}")
        if view.operator_lines(evs) != [OP["message"]["content"]]:
            out.append(f"E-admit {name}: operator lines {view.operator_lines(evs)!r}")
        if [e for e in evs if e.kind in (view.AGENT_TEXT, view.AGENT_REASONING)]:
            out.append(f"E-admit {name}: the snippet reached the agent's words")
        if view.harness_types(CC, lines(OP, rec)) != {"attachment:" + KIND: 1}:
            out.append(f"E-admit {name}: raw type {view.harness_types(CC, lines(OP, rec))}")
    return out


def refuse_problems(view=tv) -> list:
    out = []
    cases = dict(NEAR)
    cases.update({f"the type spelled {v!r}": record(type=v) for v in VARIANTS})
    for name, rec in cases.items():
        try:
            view.events(CC, lines(OP, rec))
            out.append(f"E-refuse: admitted: {name}")
        except view.ViewError:
            pass
    return out


def vocabulary() -> dict:
    rows = json.loads(VOCABULARY.read_text())["rows"]
    return {r["type"]: r for r in rows}


def allowlist_problems(view=tv) -> list:
    rows = vocabulary()
    admitted_before = {t for t, r in rows.items() if r["transcript_view_admits"]}
    out = []
    if len(rows) != 113 or len(admitted_before) != 16 or KIND in admitted_before:
        out.append(f"E-allowlist: the record is not the one ruled on ({len(rows)} names, {len(admitted_before)} admitted)")
    if set(view.CC_ATTACHMENT_TYPES) != admitted_before | {KIND}:
        out.append(f"E-allowlist: the allow-list differs: {sorted(set(view.CC_ATTACHMENT_TYPES) ^ (admitted_before | {KIND}))}")
    refused = sorted(set(rows) - admitted_before - {KIND})
    if len(refused) != 96:
        out.append(f"E-allowlist: {len(refused)} names left to refuse, not 96")
    for name in refused:
        for shape, rec in (("bare", {"type": "attachment", "attachment": {"type": name}}),
                           ("edited shape", record(type=name))):
            try:
                view.events(CC, lines(OP, rec))
                out.append(f"E-allowlist: {name} ({shape}) admitted")
            except view.ViewError:
                pass
    return out


def furniture_problems() -> list:
    import awareness_furniture as af
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "transcript.jsonl"
        p.write_text("\n".join(lines(OP, record())) + "\n")
        got = af.furniture(CC, p)
    return [] if got == {("this is a test", "attachment:" + KIND): 1} else [f"E-furniture: {got}"]


def source_mutant(old: str, new: str):
    src = Path(tv.__file__).read_text(encoding="utf-8")
    if src.count(old) != 1:
        raise AssertionError(f"mutation site occurs {src.count(old)} times: {old!r}")
    m = types.ModuleType("transcript_view_mutant")
    m.__file__ = tv.__file__
    sys.modules[m.__name__] = m
    try:
        exec(compile(src.replace(old, new), tv.__file__, "exec"), m.__dict__)
    finally:
        del sys.modules[m.__name__]
    return m


MUTANTS = (
    ("closed-keys", "    if set(a) != set(CC_EDITED_TEXT_FILE_KEYS):", "    if False:"),
    ("filename-type", 'type(a["filename"]) is not str or not a["filename"]', "False"),
    ("snippet-type", 'type(a["snippet"]) is not str', "False"),
    ("text-is-snippet", 'text=a["snippet"])]', "text=_joined({k: v for k, v in a.items() if k != \"type\"}))]"),
    ("own-reader", "        if at == CC_EDITED_TEXT_FILE:\n", "        if False:\n"),
)


class TheEditedTextFileAttachment(unittest.TestCase):
    def test_e_admit_a_w041_shaped_record(self):
        self.assertEqual(admit_problems(), [])

    def test_e_refuse_every_near_miss_and_variant(self):
        self.assertEqual(refuse_problems(), [])

    def test_e_allowlist_admits_one_more_name_and_refuses_the_other_96(self):
        self.assertEqual(allowlist_problems(), [])

    def test_e_furniture_counts_the_snippet_as_harness(self):
        self.assertEqual(furniture_problems(), [])

    def test_e_draft_names_the_departure(self):
        import check_take as ct
        draft = json.loads((HERE / "prereg-draft.json").read_text())
        self.assertNotIn("harness_furniture_ruling", ct.CHECKER_CONSTANTS)
        (dep,) = [d for d in draft["harness_furniture_ruling"]["departures"] if d["of"] == KIND]
        for word in ("Claude Code 2.1.296", "edited_text_file", "read whole", "later modification time",
                     "whoever wrote it", "filename and snippet", "current state", "w041",
                     "the agent's own background job", "CLAUDE_CODE_DISABLE_ATTACHMENTS", "no targeted switch",
                     "Round 3's 64 transcripts never carry it", "harness furniture", "not the agent's or the operator's",
                     "RULED 15 Oct (glitch-6b)", "named departure", "closed shape",
                     "lane-reports/attachment-vocabulary-20261016/edited-text-file-trigger-20261015.json"):
            self.assertIn(word, dep["text"])
        self.assertIn("edited_text_file", draft["harness_furniture_ruling"]["source"])

    def test_e_witnesses(self):
        for name, old, new in MUTANTS:
            with self.subTest(clause=name):
                m = source_mutant(old, new)
                try:
                    got = admit_problems(m) + refuse_problems(m) + allowlist_problems(m)
                except Exception as e:  # noqa: BLE001 - a mutant that crashes the reader is red too
                    got = [f"raised {type(e).__name__}"]
                print(f"\nWITNESS {name}: {'red' if got else 'NOT KILLED'} ({got[:1]})", end=" ", file=sys.stderr)
                self.assertTrue(got, name)
        dropped = types.SimpleNamespace(**{k: getattr(tv, k) for k in dir(tv) if not k.startswith("__")})
        dropped.CC_ATTACHMENT_TYPES = tuple(t for t in tv.CC_ATTACHMENT_TYPES if t != KIND)
        self.assertTrue(allowlist_problems(dropped), "witness not-admitted: the allow-list without the name")


if __name__ == "__main__":
    unittest.main()
