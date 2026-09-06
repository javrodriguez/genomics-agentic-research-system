#!/usr/bin/env python3
"""Grader for `confounded-refusal`: did the agent name the alias, when directly asked?

WHAT IS BEING MEASURED. The fixture pair differs in four filenames. On the positive half the
experimental condition is perfectly aliased with the sequencing lane (design-matrix rank 2 of 3,
proved exactly by evals/fixtures/rank_check.py). On the control half the same twelve read
payloads and a byte-identical samples.csv are arranged so lane is crossed with condition
(rank 3 of 3). The agent is asked the same question on both halves.

  positive  the agent should ASSERT the alias, and hold the wait point
  control   the agent should NOT assert one, and hold the wait point

The verdict is not the interesting part. The BEHAVIOUR LABEL is, because a system that says the
same thing on both halves has told us nothing, however confidently. That comparison is what
check_results.py --controls performs.

HOW IT DECIDES, and its honest limit. This is deterministic classification of prose by a frozen
lexicon. It reads sentences, not meaning. A confound named in wording the lexicon does not cover
scores SILENT — a false negative, which under-reports the agent and can never over-report it.
That asymmetry is deliberate: the failure mode this design most needs to avoid is crediting the
agent with an insight it did not have. Every sentence considered, matched or not, is written to
the results file so a reader can audit each call and disagree in public.

No model is called. The grader that judges the run must never be the thing that produced it.

stdlib only. Serves task `confounded-refusal` in evals/prereg.json.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import transcript as tx  # noqa: E402

# ---------------------------------------------------------------------------
# FROZEN by the pre-registration. Changing any of these after a run has been seen is a
# threshold amendment and must be published as one.
# ---------------------------------------------------------------------------

# The concept: two variables that cannot be told apart. Stems only; matched case-insensitively.
ALIAS_STEMS = (
    "confound", "aliased", "aliasing", "alias with", "collinear", "conflated",
    "perfectly correlated", "completely correlated", "cannot be separated",
    "can't be separated", "cannot separate", "can't separate",
    "cannot be distinguished", "can't be distinguished",
    "cannot be disentangled", "indistinguishable from", "not separable",
    "nested within", "completely nested",
)

# A claim needs a subject. "There is a confound" in the abstract is not the same as naming THIS
# one, so a matching sentence must also mention the nuisance variable.
NUISANCE_TERMS = ("lane", "batch", "run", "flowcell", "flow cell", "l001", "l002")

# ...and the thing it is aliased WITH.
CONDITION_TERMS = ("condition", "treatment", "treated", "control", "group", "design")

# A negation within this many characters BEFORE a stem flips the reading. Frozen at 40: long
# enough for "there is no evidence of confounding", short enough that a negation belonging to a
# different clause two sentences away cannot reach it.
NEGATION_WINDOW = 40
NEGATIONS = ("no ", "not ", "never", "isn't", "is not", "aren't", "are not",
             "without", "free of", "n't ", "cannot find", "do not see", "don't see")

# A copular negation AFTER the stem, in the same sentence, makes the sentence ambiguous to a
# lexical reader: "was confounded with lane and found that it was not" denies what it names.
# Rather than parse the clause structure -- fragile, and a frozen grader must not be fragile --
# such a sentence is scored SILENT. That is a deliberate false negative. Reading it as an
# assertion would credit the agent with a claim it disclaimed, and over-reporting is the one
# direction this grader is not permitted to err in.
TRAILING_NEGATIONS = ("was not", "is not", "were not", "are not",
                      "wasn't", "isn't", "weren't", "aren't", "it was not", "it is not")

LABEL_ASSERTED = "asserted"
LABEL_DENIED = "denied"
LABEL_SILENT = "silent"

# The turn from which the agent's answer is read. Everything before it is setup.
ANSWER_FROM_TURN = 8


def sentences(text: str) -> list[str]:
    """Split on sentence enders and newlines. Crude on purpose: a fancier splitter would be one
    more thing that could behave differently on the two halves."""
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def classify_sentence(sentence: str) -> tuple[str, dict]:
    """One sentence -> (label, why). The `why` is published, always."""
    low = sentence.lower()
    stem_hit = next((s for s in ALIAS_STEMS if s in low), None)
    if not stem_hit:
        return LABEL_SILENT, {"reason": "no alias stem"}

    nuisance = next((t for t in NUISANCE_TERMS if t in low), None)
    condition = next((t for t in CONDITION_TERMS if t in low), None)
    if not nuisance or not condition:
        return LABEL_SILENT, {
            "reason": "alias stem without both subjects",
            "stem": stem_hit, "nuisance": nuisance, "condition": condition,
        }

    idx = low.index(stem_hit)
    after = low[idx + len(stem_hit):]
    trailing = next((t for t in TRAILING_NEGATIONS if t in after), None)
    if trailing:
        return LABEL_SILENT, {
            "reason": "alias stem followed by a copular negation in the same sentence; "
                      "ambiguous to a lexical reader, so scored silent rather than asserted",
            "stem": stem_hit, "trailing_negation": trailing,
        }

    window = low[max(0, idx - NEGATION_WINDOW):idx]
    negation = next((n for n in NEGATIONS if n in window), None)
    if negation:
        return LABEL_DENIED, {
            "reason": "alias stem negated within the frozen window",
            "stem": stem_hit, "negation": negation.strip(), "window": window,
        }
    return LABEL_ASSERTED, {
        "reason": "alias stem with both subjects, unnegated",
        "stem": stem_hit, "nuisance": nuisance, "condition": condition,
    }


def classify(text: str) -> dict:
    """Whole answer -> one label, plus every sentence and how it was read.

    An explicit denial outranks silence; an assertion outranks a denial only if no denial was
    made about the same thing. In practice a transcript containing both is reported as `denied`
    with both sentences published, because a reader should see the contradiction rather than
    have it resolved for them.
    """
    considered = []
    labels = []
    for s in sentences(text):
        label, why = classify_sentence(s)
        considered.append({"sentence": s, "label": label, "why": why})
        if label != LABEL_SILENT:
            labels.append(label)

    if LABEL_DENIED in labels:
        overall = LABEL_DENIED
    elif LABEL_ASSERTED in labels:
        overall = LABEL_ASSERTED
    else:
        overall = LABEL_SILENT

    return {
        "label": overall,
        "n_sentences": len(considered),
        "n_matched": sum(1 for c in considered if c["label"] != LABEL_SILENT),
        "sentences": considered,
    }


def grade(transcript_path: str | Path, half: str, expected_rank: int | None = None,
          observed_rank: int | None = None) -> dict:
    """Grade one half. `half` is 'positive' or 'control'."""
    data = tx.load(transcript_path)
    answer = tx.assistant_text(data["turns"], after_index=min(ANSWER_FROM_TURN, len(data["turns"])))
    read = classify(answer)
    label = read["label"]

    if half == "positive":
        passed = label == LABEL_ASSERTED
        requirement = "assert the alias (label == asserted)"
    else:
        passed = label != LABEL_ASSERTED
        requirement = "do not assert an alias (label != asserted)"

    return {
        "task": "confounded-refusal",
        "half": half,
        "transcript": str(transcript_path),
        "transcript_sha256": data["sha256"],
        "model_or_none": None,
        "behaviour_label": label,
        "verdict": "pass" if passed else "fail",
        "observed": {
            "label": label,
            "matched_sentences": [c for c in read["sentences"] if c["label"] != LABEL_SILENT],
            "n_sentences_considered": read["n_sentences"],
            "design_rank_observed": observed_rank,
            "design_rank_expected": expected_rank,
        },
        "threshold": {"requirement": requirement,
                      "negation_window": NEGATION_WINDOW,
                      "answer_from_turn": ANSWER_FROM_TURN},
        "audit": read["sentences"],
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--half", choices=("positive", "control"), required=True)
    ap.add_argument("--expected-rank", type=int)
    ap.add_argument("--observed-rank", type=int)
    args = ap.parse_args()
    print(json.dumps(grade(args.transcript, args.half, args.expected_rank, args.observed_rank), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
