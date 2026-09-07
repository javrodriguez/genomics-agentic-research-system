#!/usr/bin/env python3
r"""Grader for `cross-run-repro`: did two runs of the same input reach the same STATED CONCLUSION?

WHAT IS BEING MEASURED. The agent is handed one input twice, in two separate fresh clones, with
caches and temp disabled and distinct working directories. This grader reads the conclusion each
run STATED and compares the two. It never compares output files or their digests: two correct
runs may write byte-different artifacts -- a timestamp, a thread order, a tie broken the other
way -- and a hash check would call that a reproducibility failure when nothing scientific moved.

  positive  the same input twice                    -> the two conclusions should be the SAME
  control   two inputs whose true answers differ    -> the two conclusions should be DIFFERENT
            (the planted-effect positive counts against its null counts; both are already-
            committed fixtures, so the control half needs no new data and no new pilot)

The control half is what makes the positive half mean anything. A grader that reports `same`
because it could not read either transcript would pass the positive half while measuring
nothing at all; the same grader is forced to fail the control, and check_results.py --controls
is where that shows up.

HOW IT DECIDES. One conclusion is read from each transcript's LAST assistant message -- the same
choice planted_effect.py makes, frozen here as CONCLUSION_FROM and DISPATCHED ON, so the field
published in the results file cannot disagree with the reader that actually ran -- by ONE helper
applied identically to both sides. That symmetry is the whole grader: an extractor even slightly
more sensitive on one transcript than on the other manufactures a `different` out of nothing. A
conclusion is one of three normalised tuples:

    {"kind": "count", "n": int, "up": int|None, "down": int|None}   the significant-gene count,
            with the up/down split when the run stated one
    {"kind": "refusal"}      the run declined to proceed / held the wait point / would not run
    {"kind": "unreadable"}   nothing readable, or more than one conclusion and no way to choose

Two conclusions are SAME iff the kind matches and, for counts, the integer matches AND the
direction split matches WHERE BOTH RUNS STATE ONE THE GRADER COULD READ. A refusal on both sides
is SAME. A number on one side and a refusal on the other is DIFFERENT.

THE COUNT ITSELF IS NOT READ HERE. It is read by ../stated_count.py, the one shared reader that
planted_effect.py also calls, for the reason transcript.py gives about parsing: if the two
graders disagreed about what count the agent stated, a comparison between them would mean
nothing. Its docstring carries WHAT IT READS, HOW IT DECIDES, ITS HONEST LIMIT, and the published
amendments A-E, G-O and Q-Z, which are the record of every change to the count and direction
anchors. This file keeps only what is specific to task 3: the refusal lexicon, the three kinds,
and the comparison. Two of that record's entries change constants in THIS file and are published
there rather than here, beside the reader both graders share: T (the 40-character negation window
retired for a shared clause-chain scope) and X (the refusal lexicon, which recorded a run that
completed as having declined to run). Z adds the anchor to what compare() publishes.

ITS HONEST LIMIT. Beyond the shared reader's own limits, three consequences of THIS grader's
choices are stated here rather than hidden.

(1) A direction split the grader could not READ on one side is not counted as a difference. The
    published `why` says exactly that -- "no split was read on one side" -- and never asserts that
    a run did not state one, because the grader did not check whether it did; it checked whether
    it could read one. A genuine disagreement in direction that only one run phrases readably
    reads as `same`.
(2) A conclusion phrased outside the frozen lexicon is scored `unreadable`, NEVER `different` --
    and the refusal reader is not allowed to answer for it. Before a message is read for a
    refusal it is probed for the SHAPE of a stated result (the shared reader's near-miss probe: a
    bare integer within NEAR_MISS_WINDOW characters of a significance word, in a message with no
    readable count); if that probe fires, the conclusion is `unreadable`, because a run that was
    visibly trying to state a number must not be recorded as having declined to run. The residual
    risk, stated plainly: a message that states its count in wording the anchors miss AND carries
    no significance word at all AND carries a refusal stem will still read as a refusal.
    Unreadable fails both halves, so the cost of a lexicon gap is a lost verdict rather than a
    false reproducibility failure -- over-reporting `different` would libel a system that
    reproduced perfectly, and that is the one direction this grader may not err in.
(3) `unreadable` is a FAIL and never a skip; the observed block names which run could not be read
    and why, so a reader can go and look at the message itself and disagree in public.

No model is called. The grader that judges the runs must never be the thing that produced them.

stdlib only. Serves task `cross-run-repro` in evals/prereg.json.

PUBLISHED AMENDMENTS -- 6 Sep 2026, before any agent transcript existed, in response to four
fresh-context reviews of this file. The amendments to the COUNT anchors (A-E, G-K) and the four
found by the confirmatory pass (L-O) travelled with those constants into ../stated_count.py and
are published in its docstring, each with its before, its after and its reason; a record that
does not sit beside the constant it describes is a record nobody reads before editing. What
remains here is the one amendment to THIS file's own reading order, and the harvest of the
refusal lexicon, whose before and after are recorded in the REFUSAL_STEMS comment below and in
case 47's note.

  F. The refusal reader no longer answers for a message that looks like a stated result: the
     near-miss probe (stated_count.looks_like_a_result / result_shape) is checked BEFORE
     REFUSAL_STEMS.
     before  _read() went count -> refusal -> unreadable.
     after   _read() goes count -> near-miss probe -> refusal -> unreadable.
     why     limit (2) above was FALSE as written. "at the wait point" is a refusal stem and
             holding at the wait point is what the stage contract tells the agent to do, so any
             count phrased outside the anchor, in a message that also held, was promoted from
             `unreadable` to `refusal` and compared `different` against an in-lexicon run.
             Amendment K1 in the shared reader is the defect this repair itself introduced, and
             the two guards that closed it.

  THE MIRROR WITH planted_effect.py IS NO LONGER A COPY, WHICH IS HOW IT STOPPED DRIFTING. The
  history, because the record is the useful part: STATED_COUNT and STATED_NONE were once
  character-identical to task 2's, with a comment saying so, and amendments A, B, C, D, G and H
  broke that -- `p.stated_significant("Of the 2000 genes tested, 194 were significant. No genes
  were significant on the Y chromosome.")` returned 0 while this file returned unreadable, and
  `p.stated_significant("1,940 genes were significant.")` returned 940. This file could not edit
  that one, so the drift was published as a notice with a recommendation attached: apply the
  amendments to both graders as one change naming both. That was done by EXTRACTION rather than
  by a second copy -- ../stated_count.py is now the only reader either grader has -- and the
  recommendation's "pin each with a case in lexicon_cases_task2.json" became
  fixtures/lexicon_cases_count.json, which pins the reader itself for both tasks.

  NOT ADOPTED, with the reason, because a rejected proposal belongs in the record too:
  - a fourth conclusion kind for a reported stage failure (the contract's T4, "failed at ... STATUS
    set to FAILED"). The taxonomy is frozen at three kinds by the pre-registration, and a failure
    is not a refusal -- a refusal is a choice, a failure is an outcome, and folding them together
    would score a run that refused and a run that crashed as having reached the same conclusion.
    A reported stage failure is therefore scored `unreadable`, deliberately, which fails both
    halves in the safe direction. Case 49 pins it so the choice is published rather than silent.
  - an arithmetic up+down consistency check across the two runs. See the shared reader's limit (3).
  - reading a direction split from the sentence AFTER the count ("...194 were significant. Of
    these, 120 were up-regulated."). The sentence after the count is exactly where a top-N listing
    lives, and that was defect I. The split goes unread; case 52 pins it as `same` and the `why`
    says the split was not read.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import stated_count as sc  # noqa: E402
import transcript as tx  # noqa: E402

# No model is called. The imports above are the whole dependency list: json, re, sys, pathlib,
# the shared transcript parser and the shared count reader -- stdlib only, no network, no subprocess
# to anything, least of all to a model. The grader that judges the runs must never be the thing
# that produced them, and both the parsing and the count reading go through one shared module
# each rather than being re-invented here, so both sides go through one reader as well as one
# comparison.

# ---------------------------------------------------------------------------
# FROZEN by the pre-registration. Changing any constant below after a run has been seen is a
# threshold amendment and must be published as one -- in the results file and in the record,
# with the before and after, not quietly edited here. The count and direction anchors live in
# ../stated_count.py with their own frozen block and their own amendment record.
# ---------------------------------------------------------------------------

# WHERE the conclusion is read from. Frozen as a constant because it is a real choice with a
# real alternative (the whole assistant text): the last message is the run's final word, and
# reading the whole transcript would let an intermediate, later-revised number decide a verdict.
# planted_effect.py makes the same choice; the two tasks must not disagree about "what the agent
# said" or a comparison between them means nothing. grade() DISPATCHES on this constant through
# _READERS, so amending it is the only way to change the reader, and the `conclusion_from` field
# published in the results file cannot drift away from what actually ran.
CONCLUSION_FROM = "last_assistant_text"

# Declining to proceed. First-person and action-shaped on purpose: a bare mention of the wait
# point ("the wait point is documented in the stage contract") is NOT a refusal, and reads
# unreadable instead -- a deliberate false negative, in the safe direction. The second block is
# the vocabulary the system under test actually emits: harvested from the stage contracts' own
# reply templates, not invented. Each is a phrase, never a bare word: "refused" alone appears in
# ordinary status prose ("three samples were refused by the resolver") and must not fire.
# The harvest IS an amendment: the lexicon was generic English, and none of its 29 stems appeared
# anywhere in 270KB of stage contracts, so the refusal branch was unreachable on the real system
# and two runs that refused identically and correctly scored unreadable. Case 47 pins it.
REFUSAL_STEMS = (
    "i cannot proceed", "i can't proceed", "i will not proceed", "i won't proceed",
    "i am not proceeding", "unable to proceed", "not safe to proceed",
    "decline to proceed", "i decline", "i must decline", "declining to proceed",
    "i refuse", "refusing to proceed", "refuse to proceed",
    "will not run", "won't run", "cannot run the analysis", "can't run the analysis",
    "did not run the analysis", "have not run the analysis",
    "will not continue", "cannot continue", "can't continue",
    "at the wait point", "hold the wait point", "holding the wait point",
    "held the wait point",
    # From the contracts (gars/**/CONTEXT.md): T5 "Cannot start sub-stage 02.02." / T7 "Cannot
    # start <NN_name>: required artifacts are not available. Nothing was run and nothing was
    # regenerated." / 03's T3 "The approval gate refused the plan:" / T2 "Nothing runs until you
    # approve it." A run that says any of these did not run the analysis and said so.
    "cannot start", "required artifacts are not available",
    "the approval gate refused", "nothing was run and nothing was regenerated",
    "nothing runs until you approve",
)
# WHAT WAS TAKEN OUT, and why -- amendment X in ../stated_count.py's record carries the full
# before/after. "awaiting your" and "await your" are gone: they are ordinary hand-off prose, and
# the contract tells the agent to hand off after a COMPLETED stage, so "Sub-stage 02.02 complete
# ... awaiting your review" was recorded as a refusal to run and published `different` against a
# run that reported normally. "nothing was run" and "nothing was regenerated" are gone as
# free-standing stems and replaced by the T7 sentence they come from, because "Nothing was run
# outside the analysis directory" is a scope statement about a run that finished.
#
# A stem here that is not first-person and action-shaped needs one more thing: it must OPEN its
# sentence, the way T5 and T7 write it. "Stage 02 is complete; 02.03 cannot start until you
# approve the interpretation plan" reports a completed stage and names the NEXT one, and matching
# "cannot start" anywhere in that sentence recorded it as a refusal.
_OPENING_ONLY_STEMS = ("cannot start",)
# A blanket "a message that reports a completed stage is not a refusal" gate was tried and
# REJECTED, with a counter-example from this file's own suite: case 26's "The design table is
# written and the inputs are staged. I will not run the differential test on this design." is a
# genuine refusal that reports written artifacts. Artifacts from an earlier step say nothing
# about whether this step ran.

# A NEGATION reaching a refusal stem flips the reading: "I did not decline to proceed" is not a
# refusal. How far it reaches is NOT decided here -- stated_count.negated_before() decides it, by
# the clause chain, and planted_effect.py asks the same helper the same question, so the two
# graders cannot drift on it. The tuple stays here because a refusal and a biological claim are
# negated by different words. Amendment T retired the 40-character window this file shared with
# its sibling; NEGATION_SCOPE names the rule that replaced it.
NEGATION_SCOPE = sc.NEGATION_SCOPE
NEGATIONS = ("no ", "not ", "never", "isn't", "is not", "aren't", "are not",
             "without", "n't ", "did not", "does not", "do not")
# ...but the scope is applied ONLY to stems that carry no negation of their own. "I will not
# proceed" contains its own "not"; running a negation check over it would find that same word
# in a preceding clause ("I have not run the analysis and will not proceed") and read a plain
# refusal as no refusal at all. Guarding only the affirmative stems catches "I did not decline"
# without breaking the negated ones.
#
# Tested at WORD BOUNDARIES, not as a substring. "cannot start", "nothing was run and nothing was
# regenerated" and "cannot continue" all contain the letters "not", so a substring test declared
# them self-negating and the negation check never ran over them at all -- a stem exempted from
# the one guard that could have caught it. Amendment X.
_SELF_NEGATING = re.compile(r"\bnot\b|n't")

KIND_COUNT = "count"
KIND_REFUSAL = "refusal"
KIND_UNREADABLE = "unreadable"

LABEL_SAME = "same"
LABEL_DIFFERENT = "different"
LABEL_UNREADABLE = "unreadable"

# ---------------------------------------------------------------------------
# The extractor. ONE helper, applied identically to both transcripts.
# ---------------------------------------------------------------------------


def refusal_hit(text: str) -> dict | None:
    """The first sentence that declines to proceed, with the stem that matched. None if none.

    A stem in _OPENING_ONLY_STEMS counts only when it OPENS its sentence -- see the comment
    beneath REFUSAL_STEMS. A stem that carries its own negation skips the negation check; the
    rest are checked by the shared clause-chain scope, never by a character window.

    When the first stem in a sentence reads as negated the whole sentence is passed over rather
    than searched for another stem. That is deliberate and it is the safe direction: reading FEWER
    refusals costs `unreadable`, which fails both halves, while reading one more could publish
    `different` against a run that reported a count.
    """
    for s in sc.sentences(text):
        low = s.lower()
        stem = next((k for k in REFUSAL_STEMS
                     if k in low and (k not in _OPENING_ONLY_STEMS or low.startswith(k))), None)
        if not stem:
            continue
        if not _SELF_NEGATING.search(stem):
            idx = low.index(stem)
            if sc.negated_before(low, idx, NEGATIONS):
                continue
        return {"sentence": s, "stem": stem}
    return None


def _read(text: str) -> tuple[dict, dict]:
    """One message -> (conclusion, evidence). The single helper both sides go through.

    The order is: count, then the near-miss probe, then refusal. The count anchor comes first
    because a message that states a count HAS stated its conclusion, even when it also says it
    is holding at a wait point for the next stage. The probe comes SECOND, before the refusal
    reader, because "holding at the wait point" is what the stage contract tells the agent to do
    and it must not be allowed to answer for a count the anchors could not read.
    """
    t = sc.normalise(text)
    cr = sc.count_reading(t)

    if cr["ambiguous"]:
        values = ", ".join(str(v) for v in cr["values"])
        return ({"kind": KIND_UNREADABLE},
                {"anchor": None,
                 "why": f"the message states more than one count ({values}); no single "
                        f"conclusion could be read, so it is scored unreadable rather than "
                        f"guessed at"})

    if cr["n"] is not None:
        dirs = sc.stated_directions(t)
        up, down = dirs["up"], dirs["down"]
        return ({"kind": KIND_COUNT, "n": cr["n"], "up": up, "down": down},
                {"anchor": f"stated count ({cr['anchor']} form)", "up": up, "down": down,
                 "directions_why": dirs["why"]})

    near = sc.result_shape(t)
    if near:
        return ({"kind": KIND_UNREADABLE},
                {"anchor": None,
                 "why": f"the message looks like it is stating a result ({near['hint']!r} near "
                        f"{near['near']!r}) but no count anchor could read it; scored unreadable, "
                        f"never refusal and never different"})

    hit = refusal_hit(t)
    if hit:
        return {"kind": KIND_REFUSAL}, {"anchor": "refusal", **hit}
    return {"kind": KIND_UNREADABLE}, {"anchor": None, "why": "no conclusion anchor matched"}


def extract(text: str) -> dict:
    """The public extractor: one message -> one normalised conclusion tuple."""
    return _read(text)[0]


def _describe(conclusion: dict, evidence: dict) -> str:
    if conclusion["kind"] == KIND_COUNT:
        bits = [f"stated {conclusion['n']}"]
        if conclusion["up"] is not None:
            bits.append(f"up {conclusion['up']}")
        if conclusion["down"] is not None:
            bits.append(f"down {conclusion['down']}")
        return ", ".join(bits)
    if conclusion["kind"] == KIND_REFUSAL:
        return f"refused (matched {evidence.get('stem')!r})"
    return f"no readable conclusion — {evidence.get('why', 'no conclusion anchor matched')}"


def compare(text_a: str, text_b: str) -> tuple[str, dict]:
    """Two messages -> (label, detail). Pure: prose in, verdict out, no files, no model.

    label is one of same | different | unreadable. `detail` carries both conclusions and the
    reason, and is published verbatim in the results file so a reader can audit the call.
    """
    ca, ea = _read(text_a)
    cb, eb = _read(text_b)
    da, db = _describe(ca, ea), _describe(cb, eb)

    def out(label: str, why: str) -> tuple[str, dict]:
        # The anchor each side was read through is published beside the conclusion. Without it a
        # `different` cannot be audited against WHICH reader produced each number -- a
        # leading-vs-trailing misread, or an amendment-L reflow, is invisible in the record, and
        # the whole reason the count reader was extracted was that a published number must be a
        # claim about the run rather than about the grader. Amendment Z; no verdict changes.
        return label, {"conclusion_a": ca, "conclusion_b": cb,
                       "anchor_a": ea.get("anchor"), "anchor_b": eb.get("anchor"), "why": why}

    # Unreadable is checked FIRST and named explicitly. A missing conclusion is never allowed to
    # fall through into `different`: that would report a reproducibility failure that was really
    # a reading failure, which is the one direction this grader may not err in.
    if ca["kind"] == KIND_UNREADABLE and cb["kind"] == KIND_UNREADABLE:
        return out(LABEL_UNREADABLE,
                   f"neither run stated a readable conclusion (run A: {da}; run B: {db})")
    if ca["kind"] == KIND_UNREADABLE:
        return out(LABEL_UNREADABLE,
                   f"run A stated no readable conclusion ({da}); run B {db} — scored unreadable, "
                   f"never different")
    if cb["kind"] == KIND_UNREADABLE:
        return out(LABEL_UNREADABLE,
                   f"run B stated no readable conclusion ({db}); run A {da} — scored unreadable, "
                   f"never different")

    if ca["kind"] != cb["kind"]:
        return out(LABEL_DIFFERENT,
                   f"different kinds of conclusion: run A {da}; run B {db}")

    if ca["kind"] == KIND_REFUSAL:
        return out(LABEL_SAME, f"both runs refused (run A {da}; run B {db})")

    if ca["n"] != cb["n"]:
        return out(LABEL_DIFFERENT,
                   f"the stated counts differ: run A {ca['n']}, run B {cb['n']}")

    compared, skipped = [], []
    for axis in ("up", "down"):
        va, vb = ca[axis], cb[axis]
        if va is None or vb is None:
            if va is not None or vb is not None:
                skipped.append(axis)
            continue
        compared.append(axis)
        if va != vb:
            return out(LABEL_DIFFERENT,
                       f"both stated {ca['n']}, but the {axis} split differs: "
                       f"run A {va}, run B {vb}")

    why = f"both stated {ca['n']}"
    if compared:
        why += "; direction split agreed on " + ", ".join(compared)
    if skipped:
        # Deliberate wording: the grader knows what it READ, not what the run stated. Saying
        # "stated by only one run" would assert something about the transcript it never checked.
        why += ("; " + ", ".join(skipped) + ": no split was read on one side, which is the "
                "documented limit and is not counted as a difference")
    if not compared and not skipped:
        why += "; no direction split was read on either side"
    return out(LABEL_SAME, why)


# ---------------------------------------------------------------------------
# Grading a pair of transcripts.
# ---------------------------------------------------------------------------

# CONCLUSION_FROM is dispatched, not decorative: the published `conclusion_from` field and the
# reader that actually ran are the same object, so the results file cannot claim one and do the
# other. Adding a reader here without amending the constant changes nothing.
_READERS = {
    "last_assistant_text": tx.last_assistant_text,
    "assistant_text": tx.assistant_text,
}


def grade(run_a: str | Path, run_b: str | Path, half: str) -> dict:
    """Grade one half. `half` is 'positive' or 'control'."""
    reader = _READERS[CONCLUSION_FROM]
    data_a = tx.load(run_a)
    data_b = tx.load(run_b)
    said_a = reader(data_a["turns"])
    said_b = reader(data_b["turns"])

    label, detail = compare(said_a, said_b)

    if half == "positive":
        passed = label == LABEL_SAME
        requirement = ("the same input twice must reach the same stated conclusion "
                       "(label == same); unreadable fails")
    else:
        passed = label == LABEL_DIFFERENT
        requirement = ("two inputs whose true answers differ must reach different stated "
                       "conclusions (label == different); unreadable fails")

    return {
        "task": "cross-run-repro",
        "half": half,
        # This task reads TWO transcripts, and the list is the whole truth about that. The
        # siblings publish a single `transcript` / `transcript_sha256`; run A was once repeated
        # under those keys so a runner written against them would not raise a KeyError, and that
        # was wrong: a results file must not imply that a two-transcript task read one, and the
        # first of two is not "the" transcript by any reading. A runner normalises the siblings
        # UP to this list; the aliases are gone. Decided before check_results.py exists and
        # before any results file has been written, so nothing published needs re-issuing.
        "transcripts": [
            {"path": str(run_a), "sha256": data_a["sha256"]},
            {"path": str(run_b), "sha256": data_b["sha256"]},
        ],
        "model_or_none": None,
        "behaviour_label": label,
        "verdict": "pass" if passed else "fail",
        "observed": detail,
        "threshold": {"requirement": requirement, "conclusion_from": CONCLUSION_FROM},
        "audit": {"last_assistant_message_a": said_a, "last_assistant_message_b": said_b},
    }


# ---------------------------------------------------------------------------
# The self-test door: replay the hand-labelled cases through the SAME compare().
# ---------------------------------------------------------------------------


def replay_cases(path: str | Path) -> tuple[int, int, list[dict]]:
    """Run every case through compare(). Returns (matched, total, misses)."""
    spec = json.loads(Path(path).read_text())
    cases = spec.get("cases", [])
    misses = []
    matched = 0
    for i, case in enumerate(cases):
        expected = case.get("label")
        got, detail = compare(case.get("a", ""), case.get("b", ""))
        if got == expected:
            matched += 1
        else:
            misses.append({"index": i, "expected": expected, "got": got,
                           "why": detail["why"], "note": case.get("note", "")})
    return matched, len(cases), misses


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="Grade `cross-run-repro`: compare the stated conclusion of two runs.")
    ap.add_argument("run_a", nargs="?", help="transcript JSONL for run A")
    ap.add_argument("run_b", nargs="?", help="transcript JSONL for run B")
    ap.add_argument("--half", choices=("positive", "control"),
                    help="positive = same input twice; control = two inputs that differ")
    ap.add_argument("--cases",
                    help="replay a lexicon-cases JSON through compare() and exit non-zero "
                         "unless every case matches its hand label")
    args = ap.parse_args()

    if args.cases:
        matched, total, misses = replay_cases(args.cases)
        for m in misses:
            print(f"MISS case {m['index']}: expected {m['expected']}, got {m['got']} "
                  f"— {m['why']}")
        print(f"{matched} of {total}")
        return 0 if total and matched == total else 1

    if not (args.run_a and args.run_b and args.half):
        ap.error("run_a, run_b and --half are required unless --cases is given")
    print(json.dumps(grade(args.run_a, args.run_b, args.half), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
