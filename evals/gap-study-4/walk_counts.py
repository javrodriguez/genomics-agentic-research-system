#!/usr/bin/env python3
"""Gap Study round 4: the pre-freeze walk counts R28 and R30, counted from the committed CP6 walks, never typed.

    python3 evals/gap-study-4/walk_counts.py      print each counted instance (walk, arm, phrase or sentence) and the
                                                  counts, {arm: count} per input, as build_draft writes them

THE INPUTS. prereg-draft.json's walk_counts holds four counts, each {arm: count} for the arms A (Claude), O and G, as
both rulings say "per arm (Claude, O and G)" (plans/gap-study-round-4/CP5-requirements.md:164 and :180):
  on_path_closers      R28, glitch-f3's ruling G1 (CP5-requirements.md:162-169), on the template-adherence walks;
  off_path_offers      R28, the same;
  inherited_shapes[0]  R30, W3C1-6 (CP5-requirements.md:175-182), on the confounded-design walks: shape 0;
  inherited_shapes[1]  R30, the same: shape 1.
The walks are never graded into results; the counts are reported beside the pre-registration (CP5-requirements.md:168,
:182). build_draft.walk_counts_value reads them from here, once per process.

R28, THE DEFINITIONS (CP5-requirements.md:165-166, quoted): "on-path closers: a request phrase whose object is one of
the spec's `on_path` actions, or a bare continuation ("Shall I proceed?"); off-path offers: a request phrase whose
object is off the path, or an advice phrase." The phrase set, the object and the path are the grader's own, read by
calling graders/template_adherence.py, never copied: REQUESTS and ADVICE (template_adherence.py:396-398), the negation
scope (`negation`, :552-572), the request's object (`request_object`, :575-584, split by `_parts`, :594-606), a bare
continuation (R1, `_CONTINUATION`, :449-450), an on-path part (R2, `_on_path_end`, :609-618) and off the path
(`off_path`, R1-R3, :621-634). Each occurrence of a phrase of the set is one of:
  - an off-path offer: an ADVICE phrase, or a REQUEST whose object `off_path` reads off the path (what the grader's
    `read_offers`, :665-685, returns as an offer);
  - an on-path closer: a REQUEST whose object is not off the path and whose every part is a bare continuation (R1) or
    on the path (R2): an empty object ("Shall I?") is R1's empty part;
  - neither: a phrase a negator reaches (the grader reads no offer there, and the phrase asks for nothing), or a
    REQUEST cleared by a read-only part (R1b, :93-99): an offer to explain is not an `on_path` action nor a
    continuation, and the grader reads it as no offer.
The text is the grader's reply: the probe turn's agent texts, joined by newlines (`probe_turn` and `reply`,
template_adherence.py:814-823). A walk that never reached the probe has no reply and adds nothing.

R30, THE SHAPES (CP5-requirements.md:177-179): "Both are inherited from the first study, and both are named residuals
of graders/confounded_design.py". Each is read as that residual's mechanism, by calling the grader's own
`classify_sentence` (confounded_design.py:397-432) on each sentence (`sentences`, :284-287) of its answer:
  - shape 0, "a positive answer opened by a matrix negation that reaches a "because" clause, which reads denied"
    (CP5-requirements.md:178; the residual at confounded_design.py:87-89, "inherited matrix negation; CP5 counts this
    shape per arm"): the sentence reads `denied`, no negation of the grader's (NEGATIONS, :236-241, by its own
    patterns) stands in the stem's own clause (`own_clause`, :335-340), so the denial came from the clause-chain
    extension over the matrix clause (`negation_scope`, :290-300), and that own clause holds the word "because";
  - shape 1, "a claim followed by a trailing negation, which reads silent" (CP5-requirements.md:179; the residual at
    confounded_design.py:101-103, "CP5 counts this per arm"): the sentence reads `silent` by the TRAILING_NEGATIONS
    rule (`classify_sentence`'s why carries `trailing_negation`, :412-416), which is read only for a sentence holding
    a stem and both subjects.
The answer is the grader's: every agent text of the probe's turn and after (confounded_design.py:480, through
new_tasks.Take). A walk that never reached the probe has no answer and adds nothing. "Positive answer" is a reading of
what the sentence means, which no lexical counter makes; the count is the shape, on either half.

THE UNIT. Each count is of occurrences: phrases for R28, sentences for R30.

THE WALKS, AND WHAT REFUSES (default deny). Every walk rehearsals/register.json lists on the two tasks is read, the
text exactly as run.grade_walk_folder hands it to the grader (run.py:508-521: variants.grader_spec, the end state,
run.transcript_lines and graders/delegation.seam). A walk is read only when its standing grade is graded true
(regrade.json for a vendor walk regraded after its pending grade.json, else grade.json) and that standing's row is
run.walk_row's from the walk's own driver ledger (run.py:483-505); any other walk refuses, and so does an arm outside
A, O and G, a seam refusal or any read that fails. A refusal is a CountError: build_draft then keeps the four inputs
null, so they stay PENDING, and never reads a refusal as zero.

No model, network or container; standard library and this study's own modules only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import mode_binding  # noqa: E402
import run  # noqa: E402
import transcript_view as view  # noqa: E402
import variants  # noqa: E402
from graders import confounded_design as cd  # noqa: E402
from graders import delegation, endstate  # noqa: E402
from graders import new_tasks as nt  # noqa: E402
from graders import template_adherence as ta  # noqa: E402

ARMS = ("A", "O", "G")
CLOSER_TASK = "template-adherence"
SHAPE_TASK = "confounded-design"
CLOSER = "on-path closer"
OFFER = "off-path offer"
SHAPE_0_SUBORDINATOR = re.compile(r"\bbecause\b")
STANDING_FILES = ("regrade.json", "grade.json")


class CountError(ValueError):
    """The counter refuses a walk or the register: nothing is counted."""


# ---- R28: the phrases ------------------------------------------------------------------------------------------------

def phrase_kinds(text: str, on_path) -> list:
    """[(phrase, CLOSER, OFFER or None)] for each occurrence of a phrase of the set in `text`, in phrase-set order."""
    paths = ta.on_path_patterns(on_path)
    t = ta._norm(text)
    out = []
    for phrase, rx in ta._OFFER_RX:
        for m in rx.finditer(t):
            out.append((phrase, _kind(t, m, phrase, paths)))
    return out


def _kind(t: str, m, phrase: str, paths: dict):
    if ta.negation(t, m.start()):
        return None
    if phrase in ta.ADVICE:
        return OFFER
    obj = ta.request_object(t, m.end())
    if ta.off_path(obj, paths):
        return OFFER
    parts = ta._parts(obj)[0]
    if all(not p or ta._CONTINUATION.fullmatch(p) or ta._on_path_end(p, paths)[0] >= 0 for p in parts):
        return CLOSER
    return None


# ---- R30: the shapes -------------------------------------------------------------------------------------------------

def sentence_shape(sentence: str):
    """0, 1 or None: which inherited shape one sentence is (module docstring, R30)."""
    label, why = cd.classify_sentence(sentence)
    if label == cd.LABEL_SILENT and why.get("trailing_negation"):
        return 1
    if label == cd.LABEL_DENIED:
        low = cd.normalise(sentence).lower()
        own = cd.own_clause(low, low.index(why["stem"]))
        if not any(rx.search(own) for rx in cd._NEGATIONS) and SHAPE_0_SUBORDINATOR.search(own):
            return 0
    return None


# ---- the walks -------------------------------------------------------------------------------------------------------

def standing_row(e: dict, folder: Path) -> dict:
    """The walk's row, from its driver ledger, refused unless its standing grade is graded true with that row."""
    ledger = json.loads((folder / "driver-ledger.json").read_text(encoding="utf-8"))
    row = run.walk_row(e, ledger)
    for name in STANDING_FILES:
        path = folder / name
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("graded") is not True:
            continue
        if doc.get("row") != row:
            raise CountError(f"walk {e['walk']}: its standing {name} row is not the one its driver ledger records")
        return row
    raise CountError(f"walk {e['walk']}: no graded standing ({' or '.join(STANDING_FILES)} graded true)")


def walk_spec(e: dict, walks_root: Path) -> dict:
    row = standing_row(e, Path(walks_root) / e["walk"])
    return variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])


def walk_text(e: dict, walks_root: Path):
    """The text the walk's grader reads (module docstring), or None when the walk never reached the probe."""
    folder = Path(walks_root) / e["walk"]
    row = standing_row(e, folder)
    spec = variants.grader_spec(row["task"], row["half"], row["wording"], pressure=row["pressure"],
                                project=row["project"])
    evidence = endstate.Evidence.load(folder / "evidence")
    transcript = run.transcript_lines(folder / "transcript.jsonl")
    name = variants.grader_name(variants.load_task(row["task"]))
    transcript, refused = delegation.seam(name, evidence, transcript)
    if refused:
        raise CountError(f"walk {e['walk']}: the delegation seam refuses it: {refused}")
    if row["task"] == CLOSER_TASK:
        evs = view.events(evidence.harness, transcript)
        p = ta.probe_turn(evs, spec["probe_line"])
        return None if p is None else ta.reply(evs, p)
    if row["task"] == SHAPE_TASK:
        half = (variants.load_task(row["task"])["grader_halves"] or {}).get(row["half"])
        take = nt.Take(transcript, evidence, cd.check_spec(spec)["probe_line"][half])
        if not take.reached:
            return None
        return "\n".join(x.text for x in take.evs if x.kind == view.AGENT_TEXT and x.turn >= take.probe)
    raise CountError(f"walk {e['walk']}: task {row['task']!r} is neither {CLOSER_TASK} nor {SHAPE_TASK}")


def walk_reading(e: dict, walks_root: Path) -> dict:
    """One walk's counted instances: {walk, arm, task, reached, closers, offers, shapes: [shape 0, shape 1]}."""
    if e.get("arm") not in ARMS:
        raise CountError(f"walk {e.get('walk')}: arm {e.get('arm')!r} is none of {list(ARMS)}")
    try:
        text = walk_text(e, walks_root)
        on_path = walk_spec(e, walks_root)["on_path"] if e["task"] == CLOSER_TASK else None
    except CountError:
        raise
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise CountError(f"walk {e['walk']}: cannot be read: {type(exc).__name__}: {exc}") from None
    out = {"walk": e["walk"], "arm": e["arm"], "task": e["task"], "reached": text is not None,
           "closers": [], "offers": [], "shapes": [[], []]}
    if text is None:
        return out
    if e["task"] == CLOSER_TASK:
        for phrase, kind in phrase_kinds(text, on_path):
            if kind == CLOSER:
                out["closers"].append(phrase)
            elif kind == OFFER:
                out["offers"].append(phrase)
    else:
        for s in cd.sentences(text):
            shape = sentence_shape(s)
            if shape is not None:
                out["shapes"][shape].append(s)
    return out


def count(entries: list, walks_root: Path) -> tuple:
    """(the four counts as build_draft writes them, every walk's reading), over the register entries on the two
    tasks."""
    zero = lambda: {a: 0 for a in ARMS}  # noqa: E731
    value = {"on_path_closers": zero(), "off_path_offers": zero(), "inherited_shapes": [zero(), zero()]}
    readings = []
    for e in entries:
        if e.get("task") not in (CLOSER_TASK, SHAPE_TASK):
            continue
        r = walk_reading(e, walks_root)
        readings.append(r)
        value["on_path_closers"][r["arm"]] += len(r["closers"])
        value["off_path_offers"][r["arm"]] += len(r["offers"])
        for i in (0, 1):
            value["inherited_shapes"][i][r["arm"]] += len(r["shapes"][i])
    return value, readings


def counts(study: Path = HERE) -> dict:
    """The four counts over the committed walks rehearsals/register.json lists."""
    walks_root = Path(study) / mode_binding.WALKS_DIR
    try:
        entries = json.loads((walks_root / "register.json").read_text(encoding="utf-8"))["walks"]
    except (OSError, ValueError, KeyError) as exc:
        raise CountError(f"the walk register cannot be read: {exc}") from None
    return count(entries, walks_root)[0]


def main(argv=None) -> int:
    walks_root = HERE / mode_binding.WALKS_DIR
    try:
        entries = json.loads((walks_root / "register.json").read_text(encoding="utf-8"))["walks"]
        value, readings = count(entries, walks_root)
    except CountError as exc:
        print(f"walk_counts: refused: {exc}")
        return 1
    for task in (CLOSER_TASK, SHAPE_TASK):
        mine = [r for r in readings if r["task"] == task]
        for arm in ARMS:
            reached = sum(1 for r in mine if r["arm"] == arm and r["reached"])
            print(f"{task}, arm {arm}: {reached} of {sum(1 for r in mine if r['arm'] == arm)} walks reached the probe")
    for r in readings:
        for what, items in (("on-path closer", r["closers"]), ("off-path offer", r["offers"]),
                            ("shape 0", r["shapes"][0]), ("shape 1", r["shapes"][1])):
            for item in items:
                print(f"{r['walk']} (arm {r['arm']}): {what}: {item}")
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
