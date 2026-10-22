#!/usr/bin/env python3
"""Lane vendor-b27: write the stub-model probe's scenario scripts (A1, A2, A3, B1, B2, C1, C2) as data, one JSON file
each beside this file. Run by hand (`python3 -I make_scenarios.py`); tests/test_stub_model_server.py binds every JSON
file to this generator's output byte for byte, so the data and its rule never drift apart.

Every scenario follows the B27 design's section 3 (lane-reports/vendor-b27-DESIGN.md), with the CLI's default
thresholds and the study's own settings (the probe writes them through take_config.write):
  - heavy files are 2,000 lines of 30 characters (62,000 characters), read with read_file, which is never cut at
    execution time (only the shell tool is, :348856-348880) and stops at 2,000 lines (:253707-253708);
  - every call names a distinct file and every text answer is distinct, so the client-side loop check stays quiet;
  - call arguments name `${RUN_TREE}/<file>`; the probe writes the files and fills the run tree's absolute path before
    the stub reads the script (the materialised script is kept with the probe's records);
  - an inflated promptTokenCount (600,000, over 0.5 x 1,048,576, :337135-337143, :334569-334585) is named only where
    the design names it; every other count is computed by the stub from the request.
`expect` carries the design's predictions: the road, and per snapshot the B26 reader's predicted verdict (the reader
harness, box/stub_model_reading.py, prints the observed verdict beside it). The predictions are never an input to the
stub.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "gemini-3.8-flash"
INFLATED = 600_000
HEAVY = {"kind": "heavy", "lines": 2000, "width": 30}
SMALL = {"kind": "small", "lines": 20, "width": 30}
SUMMARY_PREFIX = "Generate a new <state_snapshot> based on the provided history."             # :337193
VERIFY_PREFIX = "Critically evaluate the <state_snapshot> you just generated."                  # :337228
RESUME_REFUSAL = "the resume after a history re-record"
RETIRED_REFUSAL = "a retired native message id is recorded again"
COMPRESSION_REFUSAL = "native chat compression (the context turn survives a re-record)"
TRUNCATION_REFUSAL = "neither one of its originals nor masked"


def read(name, thought=None, tokens=None):
    r = {"calls": [{"name": "read_file", "args": {"file_path": "${RUN_TREE}/" + name}}]}
    if thought:
        r["thought"] = {"subject": thought, "description": f"Reading {name} next, as asked."}
    if tokens:
        r["prompt_tokens"] = tokens
    return r


def say(text, thought=None):
    r = {"text": text}
    if thought:
        r["thought"] = {"subject": thought, "description": "Answering from what was read."}
    return r


def prompt(text, respond, note=None):
    e = {"endpoint": "stream", "match": {"kind": "user_text", "text": text}, "respond": respond}
    return dict(e, note=note) if note else e


def answer(respond, note=None):
    e = {"endpoint": "stream", "match": {"kind": "function_response"}, "respond": respond}
    return dict(e, note=note) if note else e


def helper(prefix, respond, note):
    return {"endpoint": "generate", "match": {"kind": "user_text_prefix", "prefix": prefix}, "respond": respond,
            "note": note}


def reads(prompt_text, names, final, *, tokens_on_last=None, thought="Reading the files"):
    """A process that reads `names` one by one after `prompt_text`, then says `final`."""
    out = [prompt(prompt_text, read(names[0], thought=thought,
                                    tokens=tokens_on_last if len(names) == 1 else None))]
    for i, n in enumerate(names[1:], start=1):
        out.append(answer(read(n, tokens=tokens_on_last if i == len(names) - 1 else None)))
    out.append(answer(say(final)))
    return out


def heavy(*names):
    return {n: dict(HEAVY) for n in names}


def small(*names):
    return {n: dict(SMALL) for n in names}


def verdicts(*items):
    """Per snapshot: "PASS" or a refusal's expected words."""
    return {str(i): ({"verdict": "PASS"} if v == "PASS" else {"verdict": "refused", "reason_contains": v})
            for i, v in enumerate(items, start=1)}


R = [f"r{n:02d}.txt" for n in range(1, 9)]
S = [f"s{n:02d}.txt" for n in range(1, 9)]

A1_P = ("Read the files r01.txt to r08.txt one by one.", "Summarise what you read.", "Thanks.")
A1_REQUESTS = reads(A1_P[0], R[:7], "I read seven of the files; each is a numbered list of synthetic lines.") \
    + [prompt(A1_P[1], say("Each file held two thousand numbered synthetic lines.", thought="Summarising")),
       prompt(A1_P[2], say("You are welcome."))]

SCENARIOS = {
    "A1": {
        "road": "a masking re-record in process 1, then a resume after it (process 2) and a second resume (process 3)",
        "processes": list(A1_P), "files": heavy(*R[:8]), "requests": A1_REQUESTS,
        "expect": {"snapshots": verdicts("PASS", RETIRED_REFUSAL, RETIRED_REFUSAL),
                   "stub_log": "the first request carrying <tool_output_masked> sits in process 1"},
        "fake_cross_check": True,
    },
    "A2": {
        "road": "F-B26-7's conditional-yes variant: process 2's prompt starts with '/', masking falls inside process 2, "
                "process 3 resumes after it",
        "processes": ["Read the file s01.txt.", "/srv/raw is the raw data path. Now read r01.txt to r07.txt one by one.",
                      "Thanks."],
        "files": dict(small("s01.txt"), **heavy(*R[:7])),
        "requests": reads("Read the file s01.txt.", ["s01.txt"], "s01.txt holds twenty numbered synthetic lines.")
        + reads("/srv/raw is the raw data path. Now read r01.txt to r07.txt one by one.", R[:7],
                "I read r01.txt to r07.txt from the run tree.")
        + [prompt("Thanks.", say("Glad to help."))],
        "expect": {"snapshots": verdicts("PASS", "PASS", RESUME_REFUSAL),
                   "stub_log": "the first masked request sits in process 2; process 3's first request no longer holds "
                               "the '/' prompt"},
    },
    "A3": {
        "road": "the w-g47 pattern with a boundary after it: five heavy reads, a resume whose re-added _response turns "
                "push the history over the masking line at its first request, then a resume after that",
        "processes": ["Read r01.txt to r05.txt one by one.", "Read r06.txt too.", "Thanks."],
        "files": heavy(*R[:6]),
        "requests": reads("Read r01.txt to r05.txt one by one.", R[:5], "I read the five files.")
        + reads("Read r06.txt too.", [R[5]], "r06.txt is read as well.")
        + [prompt("Thanks.", say("Any time."))],
        "expect": {"snapshots": verdicts("PASS", "PASS", RESUME_REFUSAL),
                   "stub_log": "the first masked request is process 2's first request"},
    },
    "B1": {
        "road": "true chat compression at process 2's second request (one response reports promptTokenCount 600,000), "
                "then a resume after it",
        "processes": ["Read s01.txt and s02.txt.", "Read s03.txt.", "Thanks."],
        "files": small(*S[:3]),
        "requests": reads("Read s01.txt and s02.txt.", S[:2], "Both small files are read.")
        + [prompt("Read s03.txt.", read(S[2], thought="Reading s03", tokens=INFLATED),
                  note="promptTokenCount 600,000: the next request compresses"),
           helper(SUMMARY_PREFIX, say("<state_snapshot>The user asked for three small files to be read; s01.txt and "
                                      "s02.txt were read; s03.txt is being read.</state_snapshot>"),
                  "the compression summary (:337194-337220)"),
           helper(VERIFY_PREFIX, say("<state_snapshot>The user asked for three small files to be read; s01.txt and "
                                     "s02.txt were read; s03.txt is being read.</state_snapshot>"),
                  "the summary's verification (:337221-337238)"),
           answer(say("s03.txt is read too.")),
           prompt("Thanks.", say("You are welcome, all three are read."))],
        "expect": {"snapshots": verdicts("PASS", COMPRESSION_REFUSAL, COMPRESSION_REFUSAL),
                   "stub_log": "the two generateContent helper requests sit between process 2's first and second "
                               "stream requests"},
    },
    "B2": {
        "road": "the realistic interleave: A1's masking re-record in process 1, then B1's compression in a resumed "
                "process 2, then a resume",
        "processes": [A1_P[0], "Read s03.txt.", "Thanks."],
        "files": dict(heavy(*R[:8]), **small("s03.txt")),
        "requests": reads(A1_P[0], R[:7], "I read seven of the files; each is a numbered list of synthetic lines.")
        + [prompt("Read s03.txt.", read("s03.txt", thought="Reading s03", tokens=INFLATED),
                  note="promptTokenCount 600,000: the next request compresses"),
           helper(SUMMARY_PREFIX, say("<state_snapshot>Seven heavy files were read; s03.txt is being read."
                                      "</state_snapshot>"), "the compression summary"),
           helper(VERIFY_PREFIX, say("<state_snapshot>Seven heavy files were read; s03.txt is being read."
                                     "</state_snapshot>"), "the summary's verification"),
           answer(say("s03.txt is read after the seven heavy files.")),
           prompt("Thanks.", say("Happy to help with the files."))],
        "expect": {"snapshots": verdicts("PASS", RESUME_REFUSAL, RESUME_REFUSAL),
                   "stub_log": "masked requests from process 1; the two helper requests in process 2"},
    },
    "C1": {
        "road": "content truncation after a failed compression: an inflated summary fails compression "
                "(COMPRESSION_FAILED_INFLATED_TOKEN_COUNT), the next request truncates the oldest heavy result "
                "(CONTENT_TRUNCATED), then a resume",
        "processes": ["Read s01.txt.", "Read r01.txt to r04.txt one by one.", "Thanks."],
        "files": dict(small("s01.txt", "s02.txt"), **heavy(*R[:4])),
        "requests": reads("Read s01.txt.", ["s01.txt"], "s01.txt is read.")
        + reads("Read r01.txt to r04.txt one by one.", R[:4], "unused", tokens_on_last=INFLATED)[:-1]
        + [helper(SUMMARY_PREFIX, {"text_generated": {"chars": 2_600_000, "open": "<state_snapshot>",
                                                      "close": "</state_snapshot>", "seed": "c1-summary"}},
                  "an inflated summary: the new history's estimate exceeds 600,000 (:337271-337282)"),
           helper(VERIFY_PREFIX, {"text_generated": {"chars": 2_600_000, "open": "<state_snapshot>",
                                                     "close": "</state_snapshot>", "seed": "c1-verified"}},
                  "the inflated verification"),
           answer(read("s02.txt", tokens=INFLATED), note="promptTokenCount 600,000 again: the next request truncates"),
           answer(say("All four heavy files and s02.txt are read.")),
           prompt("Thanks.", say("Done with every file."))],
        "expect": {"snapshots": verdicts("PASS", TRUNCATION_REFUSAL, TRUNCATION_REFUSAL),
                   "stub_log": "the first request carrying 'Output too large. Showing first' follows the s02.txt "
                               "response"},
    },
    "C2": {
        "road": "a truncation re-record that truncates nothing: as C1 with results that all fit the 50,000-token "
                "budget, so CONTENT_TRUNCATED re-records an image-identical history",
        "processes": ["Read s01.txt.", "Read s02.txt to s05.txt one by one."],
        "files": small(*S[:6]),
        "requests": reads("Read s01.txt.", ["s01.txt"], "s01.txt is read.")
        + reads("Read s02.txt to s05.txt one by one.", S[1:5], "unused", tokens_on_last=INFLATED)[:-1]
        + [helper(SUMMARY_PREFIX, {"text_generated": {"chars": 2_600_000, "open": "<state_snapshot>",
                                                      "close": "</state_snapshot>", "seed": "c2-summary"}},
                  "an inflated summary"),
           helper(VERIFY_PREFIX, {"text_generated": {"chars": 2_600_000, "open": "<state_snapshot>",
                                                     "close": "</state_snapshot>", "seed": "c2-verified"}},
                  "the inflated verification"),
           answer(read("s06.txt", tokens=INFLATED), note="promptTokenCount 600,000 again: a truncation pass"),
           answer(say("Every small file is read."))],
        "expect": {"snapshots": verdicts("PASS", "PASS"),
                   "stub_log": "no request carries the truncation text"},
    },
}


def build() -> dict:
    out = {}
    for name, s in SCENARIOS.items():
        doc = {"schema": 1, "scenario": name, "model": MODEL, **s}
        doc.setdefault("fake_cross_check", False)
        out[f"{name}.json"] = (json.dumps(doc, indent=1, sort_keys=True) + "\n").encode("utf-8")
    return out


def main() -> int:
    for name, data in build().items():
        (HERE / name).write_bytes(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
