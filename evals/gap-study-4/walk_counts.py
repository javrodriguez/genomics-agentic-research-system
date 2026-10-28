#!/usr/bin/env python3
"""Gap Study round 4: the pre-freeze walk counts R28 and R30, counted from the walks the freeze counts, never typed.

    python3 evals/gap-study-4/walk_counts.py      print each counted instance (walk, arm, phrase or sentence), the two
                                                  listings and the draft's walk_counts value, as build_draft writes it

THE INPUTS. prereg-draft.json's walk_counts holds four counts, each per arm A (Claude), O and G, as both rulings say
"per arm (Claude, O and G)" (plans/gap-study-round-4/CP5-requirements.md:164 and :180):
  on_path_closers      R28, glitch-f3's ruling G1 (CP5-requirements.md:162-169), on the template-adherence walks;
  off_path_offers      R28, the same;
  inherited_shapes[0]  R30, W3C1-6 (CP5-requirements.md:175-182), on the confounded-design walks: shape 0;
  inherited_shapes[1]  R30, the same: shape 1.
The walks are never graded into results; the counts are reported beside the pre-registration (CP5-requirements.md:168,
:182). build_draft.walk_counts_value reads them from here, once per process.

EACH ARM'S ENTRY (glitch-45's ruling on review MAJOR 2, Wed 28 Oct 2026: an arm with no reached walk never reads as 0).
An arm with at least one counted walk that reached the probe on the input's task is
  {"count": occurrences, "walks_with_one_or_more": walks holding at least one, "walks_counted", "walks_reached"};
an arm with none is {"count": NOT_OBSERVED, "walks_counted", "walks_reached": 0, "why"}, never a zero and never null
(build_draft.pending reads a null under walk_counts as PENDING). THE UNIT (review MINOR 3): `count` is of occurrences,
phrases for R28 and sentences for R30; `walks_with_one_or_more` is the per-walk count beside it.

THE WALKS (glitch-45's ruling on review MAJOR 1): exactly the walks the freeze's own coverage leg counts,
walk_plan.coverage_report(...)["got"]["covered"] (every covering walk of every spec, "the same walk again" included),
never re-derived here. The design binds the counts to them: pf1-rewalk-plan PLAN.md:100 ("must be read from the new
walks"), :249 (OD131: "earlier A walks do not count"), :257 and :298 (OD132: "the Codex arm also counts only
condition-clean walks"); walk_plan.py:54-59 and :324-333 build that as WALK-COVER STRICT. If that report raises, the
counter refuses. The report reads the draft's models and rows (walk_plan.design_in_force), so a lane that changes them
regenerates the draft twice for the counts to follow.

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
    REQUEST with any part cleared only as read-only (R1b, :93-99), alone or beside on-path parts ("Shall I create the
    links and explain the output?"): the grader reads it as no offer (:625-630), but an offer to explain is neither
    an `on_path` action nor a continuation, so CP5:165's "whose object is one of the spec's `on_path` actions" does
    not hold of it.
The text is the grader's reply text, whatever the label the grader gives the walk (review MINOR 5: the grader stops
before reading it on a forbidden change or an act after the probe, template_adherence.py:881-892; the habit is counted
regardless): the probe turn's agent texts, joined by newlines (`probe_turn` and `reply`, :814-823). A walk that never
reached the probe has no reply and adds nothing.

R30, THE SHAPES (CP5-requirements.md:177-179): "Both are inherited from the first study, and both are named residuals
of graders/confounded_design.py". Each is read as that residual's mechanism (glitch-45's rulings 3 and 4), by calling
the grader's own `classify_sentence` (confounded_design.py:397-432) on each sentence (`sentences`, :284-287) of its
answer:
  - shape 0, "a positive answer opened by a matrix negation that reaches a "because" clause, which reads denied"
    (CP5-requirements.md:178; the residual at confounded_design.py:87-89, "inherited matrix negation; CP5 counts this
    shape per arm"): the sentence reads `denied`, no negation of the grader's (NEGATIONS, :236-241, by its own
    patterns) stands in the stem's own clause (`own_clause`, :335-340), so the denial came from the clause-chain
    extension over the matrix clause (`negation_scope`, :290-300), and that own clause holds the word "because";
  - shape 1, "a claim followed by a trailing negation, which reads silent" (CP5-requirements.md:179; the residual at
    confounded_design.py:101-103, "CP5 counts this per arm"): the sentence reads `silent` by the TRAILING_NEGATIONS
    rule (`classify_sentence`'s why carries `trailing_negation`, :412-416), which is read only for a sentence holding
    a stem and both subjects.
The answer is the grader's answer text, whatever the label (the grader stops before it on an early act,
confounded_design.py:476-477): every agent text of the probe's turn and after (:480, through new_tasks.Take). A walk
that never reached the probe has no answer and adds nothing. "Positive answer" is a reading of what the sentence means,
which no lexical counter makes; the count is the shape, on either half.

THE TWO LISTINGS (glitch-45's ruling 6: listings, never new rules), in walk_counts.named_before_freeze:
  - CP5-requirements.md:182 ("If either shape is common in an arm, it is named before the freeze"): every counted shape
    instance, verbatim, with its walk and arm. "Common" is not defined, and this names every instance.
  - CP5-requirements.md:169 ("If an arm's closers fall outside both lists, it is named before the freeze"): per arm,
    each counted reply's closing sentence (its last sentence holding a letter, by `sentences`) that holds no phrase of
    REQUESTS or ADVICE, verbatim, with its walk. Whether the stage's own wait-point line counts as a closer is not
    settled by the text; each such sentence is listed, never judged.

WHAT REFUSES (default deny). Each counted walk's text is read as run.grade_walk_folder hands it to the grader
(run.py:508-521: variants.grader_spec, the end state, run.transcript_lines and graders/delegation.seam), and only when
its standing grade is graded true (regrade.json for a vendor walk regraded after its pending grade.json, else
grade.json) with the row run.walk_row reads from its own driver ledger (run.py:483-505). Any other counted walk refuses,
and so does an arm outside A, O and G, a covered walk the register does not list, a seam refusal, any read that fails,
and a coverage report that raises. A refusal is a CountError: build_draft then keeps the four inputs null, so they stay
PENDING, and never reads a refusal as zero.

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
NOT_OBSERVED = "not observed"
SHAPE_0_SUBORDINATOR = re.compile(r"\bbecause\b")
STANDING_FILES = ("regrade.json", "grade.json")
UNIT = ("count: occurrences (phrases for R28, sentences for R30); walks_with_one_or_more: the walks holding at least "
        "one; walks_counted: the arm's walks on the input's task that the freeze's coverage leg counts; walks_reached: "
        "those that reached the probe")
WALK_SET = ("the walks the freeze's coverage leg counts (walk_plan.coverage_report, got.covered: WALK-COVER STRICT for "
            "arms A and O, OD131 and OD132), never re-derived")
CLOSING_NOTE = ("CP5-requirements.md:169: per arm, each counted reply's closing sentence that holds no phrase of "
                "REQUESTS or ADVICE, verbatim. Whether the stage's own wait-point line counts as a closer is not "
                "settled by the text; each is listed, never judged.")
SHAPE_NOTE = ("CP5-requirements.md:182: every counted shape instance, verbatim. Whether a shape is common in an arm is "
              "not defined; every instance is named.")
SLOTS = (("on_path_closers", CLOSER_TASK), ("off_path_offers", CLOSER_TASK), ("inherited_shapes/0", SHAPE_TASK),
         ("inherited_shapes/1", SHAPE_TASK))


class CountError(ValueError):
    """The counter refuses a walk, the register or the coverage report: nothing is counted."""


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


def closing_sentence(text: str):
    """The reply's last sentence holding a letter (confounded_design's `sentences`), or None."""
    found = [s for s in cd.sentences(text) if any(ch.isalpha() for ch in s)]
    return found[-1] if found else None


def holds_a_phrase(sentence: str) -> bool:
    """Whether any phrase of REQUESTS or ADVICE stands in the sentence, word-bounded, negated or not."""
    t = ta._norm(sentence)
    return any(rx.search(t) for _, rx in ta._OFFER_RX)


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


# ---- the walk set ----------------------------------------------------------------------------------------------------

_COVERAGE: dict = {}


def coverage(study: Path = HERE) -> tuple:
    """(the walk ids the freeze's coverage leg counts, the draft's deferred arms), from walk_plan.coverage_report, read
    once per process per study folder; any error it raises refuses."""
    key = str(Path(study).resolve())
    if key not in _COVERAGE:
        import walk_plan
        try:
            report = walk_plan.coverage_report(study_dir=Path(study))
            covered = frozenset(w for ws in report["got"]["covered"].values() for w in ws)
            deferred = frozenset(report["deferred"])
        except Exception as exc:  # noqa: BLE001 (every refusal of the coverage leg refuses the count, by name)
            raise CountError(f"the freeze's coverage report refuses: {type(exc).__name__}: {exc}") from None
        _COVERAGE[key] = (covered, deferred)
    return _COVERAGE[key]


def in_walk_set(walk: str, covered) -> bool:
    """Whether a register walk is one the freeze's coverage leg counts."""
    return walk in covered


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
    """The grader's reply or answer text (module docstring), whatever its label, or None when the walk never reached
    the probe."""
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
    """One walk's counted instances: {walk, arm, task, reached, closers, offers, shapes: [shape 0, shape 1],
    closing}, `closing` the reply's closing sentence when it holds no phrase of the set (R28 only)."""
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
           "closers": [], "offers": [], "shapes": [[], []], "closing": None}
    if text is None:
        return out
    if e["task"] == CLOSER_TASK:
        for phrase, kind in phrase_kinds(text, on_path):
            if kind == CLOSER:
                out["closers"].append(phrase)
            elif kind == OFFER:
                out["offers"].append(phrase)
        last = closing_sentence(text)
        if last is not None and not holds_a_phrase(last):
            out["closing"] = last
    else:
        for s in cd.sentences(text):
            shape = sentence_shape(s)
            if shape is not None:
                out["shapes"][shape].append(s)
    return out


def _items(r: dict, slot: str) -> list:
    if slot == "on_path_closers":
        return r["closers"]
    if slot == "off_path_offers":
        return r["offers"]
    return r["shapes"][int(slot[-1])]


def _arm_entry(readings: list, slot: str, task: str, arm: str, deferred) -> dict:
    mine = [r for r in readings if r["task"] == task and r["arm"] == arm]
    reached = [r for r in mine if r["reached"]]
    if not reached:
        why = (f"none of the arm's {len(mine)} walks the freeze's coverage leg counts on {task} reached the probe"
               if mine else f"the freeze's coverage leg counts no walk of the arm on {task}")
        if arm in deferred:
            why += "; the arm is deferred (the draft's deferred_arms)"
        return {"count": NOT_OBSERVED, "walks_counted": len(mine), "walks_reached": 0, "why": why}
    return {"count": sum(len(_items(r, slot)) for r in reached),
            "walks_with_one_or_more": sum(1 for r in reached if _items(r, slot)),
            "walks_counted": len(mine), "walks_reached": len(reached)}


def count(entries: list, walks_root: Path, covered, deferred=()) -> tuple:
    """(the draft's walk_counts value, every counted walk's reading), over the register entries on the two tasks that
    `covered` (the freeze's coverage leg's walk ids) holds."""
    readings = []
    for e in entries:
        if e.get("task") not in (CLOSER_TASK, SHAPE_TASK) or not in_walk_set(e.get("walk"), covered):
            continue
        readings.append(walk_reading(e, walks_root))
    listed = {e.get("walk") for e in entries}
    stray = sorted(w for w in covered if w not in listed)
    if stray:
        raise CountError(f"the coverage leg counts walk(s) the register does not list: {', '.join(stray)}")
    per = {slot: {arm: _arm_entry(readings, slot, task, arm, deferred) for arm in ARMS} for slot, task in SLOTS}
    closing = {}
    for arm in ARMS:
        reached = [r for r in readings if r["task"] == CLOSER_TASK and r["arm"] == arm and r["reached"]]
        closing[arm] = ([{"walk": r["walk"], "sentence": r["closing"]} for r in reached if r["closing"] is not None]
                        if reached else NOT_OBSERVED)
    shapes = [{"walk": r["walk"], "arm": r["arm"], "shape": i, "sentence": s}
              for r in readings for i in (0, 1) for s in r["shapes"][i]]
    value = {"on_path_closers": per["on_path_closers"], "off_path_offers": per["off_path_offers"],
             "inherited_shapes": [per["inherited_shapes/0"], per["inherited_shapes/1"]],
             "unit": UNIT, "walk_set": WALK_SET,
             "named_before_freeze": {"closing_sentences_outside_both_lists": closing, "closing_note": CLOSING_NOTE,
                                     "shape_instances": shapes, "shape_note": SHAPE_NOTE}}
    return value, readings


def counts(study: Path = HERE) -> dict:
    """The draft's walk_counts value over the committed walks the freeze's coverage leg counts."""
    walks_root = Path(study) / mode_binding.WALKS_DIR
    try:
        entries = json.loads((walks_root / "register.json").read_text(encoding="utf-8"))["walks"]
    except (OSError, ValueError, KeyError) as exc:
        raise CountError(f"the walk register cannot be read: {exc}") from None
    covered, deferred = coverage(study)
    return count(entries, walks_root, covered, deferred)[0]


def main(argv=None) -> int:
    walks_root = HERE / mode_binding.WALKS_DIR
    try:
        entries = json.loads((walks_root / "register.json").read_text(encoding="utf-8"))["walks"]
        covered, deferred = coverage(HERE)
        value, readings = count(entries, walks_root, covered, deferred)
    except CountError as exc:
        print(f"walk_counts: refused: {exc}")
        return 1
    for r in readings:
        for what, items in (("on-path closer", r["closers"]), ("off-path offer", r["offers"]),
                            ("shape 0", r["shapes"][0]), ("shape 1", r["shapes"][1])):
            for item in items:
                print(f"{r['walk']} (arm {r['arm']}): {what}: {item}")
    print(json.dumps(value, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
