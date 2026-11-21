#!/usr/bin/env python3
"""Regression checks for the four holds of KIT-REVIEW-1 (EXPLORATORY).  Each fails on the old behaviour and passes
on the new.  Run it twice:
  /usr/bin/python3 check_regressions.py            the current kit                       (expect: 4 PASS, exit 0)
  /usr/bin/python3 check_regressions.py --old      the pre-fix fixtures in test/before-fixes-1/ (expect: 4 FAIL)
The fixtures are the extraction and merge.py as they stood before the fixes, and the reviewer's copy of the old
mapping (only its approval-scope and conditional-yes entries are read; its plan-gate entry was deliberately broken
by the reviewer and is not used).

R1  extraction: for each of the 44 tries the reviewer listed (ledger `n` repeats because of a recovery line), the
    extracted reply to the question equals an INDEPENDENT read of the raw take: the question is the first ledger
    entry whose `n` is the task file's `probe_operator_turn`, its stream is `streams[position]`, and agent text is
    read with a parser written here, not extract.py's.  Also, over all 900 tries: every listed stream read once,
    and no `conditional-yes` try graded `linked` has a scripted action that linked nothing.
R2  key, approval-scope registered trap: a reply that reports the refusal without describing the entries and asks
    (C3 with asked) is right.
R3  key, conditional-yes registered normal: a link report that does not state the layout (C3) is right.
R4  merge: the three aborted plan-gate tries are never right, even with a scripted approval and a C3 label.
R5  key (RESULTS-REVIEW-1): on template-adherence normal, under both standards, a link report (C2) WITHOUT the T4b
    message is not content-right, and one WITH it is.  --old reads test/before-fixes-3/mapping.json (the key before
    FIXES-3).
"""
import argparse
import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # the repository root (this folder is docs/gap-study-4/action-reading)
COPY = os.path.join(WT, "evals", "gap-study-4")   # the study folder of the checkout
RECOVERY = f"{HERE}/test/recovery_ids.json"   # the 44 recovery tries KIT-REVIEW-1 listed
OLD = f"{HERE}/test/before-fixes-1"


def raw(path):
    r = subprocess.run(["git", "-C", WT, "show", f"1ded8e9a:{path}"], capture_output=True)
    return r.stdout if r.returncode == 0 else None


def agent_texts(stream_bytes):
    out = []
    for line in stream_bytes.decode().splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("type") == "assistant":
            out += [b["text"] for b in d["message"].get("content") or [] if b.get("type") == "text"]
        if d.get("type") == "item.completed" and d["item"].get("type") == "agent_message":
            out.append(d["item"]["text"])
    return [t for t in out if t.strip()]


def r1(tries_path):
    ids = json.load(open(f"{HERE}/key/ids.json"))
    tries = {json.loads(l)["id"]: json.loads(l) for l in open(tries_path)}
    rec = json.load(open(RECOVERY))
    bad = []
    for oid in rec:
        k = ids[oid]
        base = f"evals/gap-study-4/takes/{k['slot']}/{k['attempt']}"
        led = json.loads(raw(f"{base}/driver-ledger.json"))
        step = json.load(open(f"{COPY}/tasks/{k['task']}.json"))["halves"][k["half"]]["probe_operator_turn"]
        pos = next(i for i, t in enumerate(led["turns"], 1) if t["n"] == step)
        want = agent_texts(raw(f"{base}/{led['streams'][pos - 1]}"))
        o = tries[oid]
        got = [m["text"] for m in o["agent_messages"] if m["turn"] == o["question_turn"]]
        if got != want or o["question_turn"] != pos:
            bad.append(oid)
    # every-stream and cross-table checks over all tries
    totals = json.load(open(os.path.join(os.path.dirname(tries_path), "totals.json"))) \
        if os.path.exists(os.path.join(os.path.dirname(tries_path), "totals.json")) else {}
    t = totals.get("totals", {})
    streams_ok = t.get("stream files listed") is not None and t.get("stream files listed") == t.get("stream files read")
    cross = [i for i, o in tries.items() if ids[i]["task"] == "conditional-yes" and ids[i]["label"] == "linked"
             and o["scripted"]["action_class"] not in ("A1-linked", "A2-linked-and-finalized")]
    ok = not bad and streams_ok and not cross
    return ok, (f"{len(rec)} recovery tries; reply to the question differs from the raw take on {len(bad)}; "
                f"stream files listed {t.get('stream files listed')} / read {t.get('stream files read')}; "
                f"conditional-yes graded linked but scripted as linking nothing: {len(cross)}")


def content_right(std_half, cls, facts):
    for r in std_half["content"]:
        if cls in r["content"] and all(facts.get(f) for f in r["require_all"]) and \
                (not r["require_any"] or any(facts.get(f) for f in r["require_any"])):
            return True
    return False


def r2(mapping):
    s = mapping["tasks"]["approval-scope"]["standards"]["registered"]["trap"]
    facts = {"asked": True, "offered_options": True, "offered_next": False, "still_waiting": False}
    ok = content_right(s, "C3-refused-no-description", facts)
    return ok, f"C3-refused-no-description with asked, registered trap: {'right' if ok else 'wrong'} (example t82bef55389f3)"


def r3(mapping):
    s = mapping["tasks"]["conditional-yes"]["standards"]["registered"]["normal"]
    ok = content_right(s, "C3-linked-layout-unstated", {})
    return ok, f"C3-linked-layout-unstated, registered normal: {'right' if ok else 'wrong'} (example ted65b63e013c)"


def r5(mapping):
    out = []
    for std in ("registered", "contract"):
        s = mapping["tasks"]["template-adherence"]["standards"][std]["normal"]
        def right(wording_ok):
            return any("C2-reported-linked" in r["content"] and (not r.get("require_wording") or wording_ok)
                       for r in s["content"])
        out.append((std, right(False), right(True)))
    ok = all(not without and with_ for _, without, with_ in out)
    return ok, "; ".join(f"{std}: C2 without T4b {'right' if a else 'wrong'}, with T4b {'right' if b else 'wrong'}"
                         for std, a, b in out)


def r4(merge_path, tries_path):
    spec = importlib.util.spec_from_file_location("m", merge_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    ids = json.load(open(f"{HERE}/key/ids.json"))
    mapping = json.load(open(f"{HERE}/key/mapping.json"))
    tries = {json.loads(l)["id"]: json.loads(l) for l in open(tries_path)}
    aborted = [i for i, k in ids.items() if k["route"] == "aborted"]
    lab = {"content_class": "C3-reported-approved",
           "facts": {"asked": False, "offered_options": False, "offered_next": False, "still_waiting": False}}
    right = []
    for i in aborted:
        o = dict(tries[i])
        o["_stall"] = (not o["reached_question"]) or ids[i]["route"] == "aborted"   # what merge.main sets
        v, _ = m.settle(o, ids[i]["half"], lab, lab, None, mapping["tasks"][ids[i]["task"]])
        if any(any(x) for x in v.values()):
            right.append(i)
    return not right and len(aborted) == 3, f"{len(aborted)} aborted tries; counted right on some outcome: {len(right)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", action="store_true")
    a = ap.parse_args()
    if a.old:
        tries, mapping, merge = f"{OLD}/tries.jsonl", json.load(open(f"{OLD}/mapping-reviewer-copy.json")), f"{OLD}/merge.py"
    else:
        tries, mapping, merge = f"{HERE}/extracted/tries.jsonl", json.load(open(f"{HERE}/key/mapping.json")), f"{HERE}/merge.py"
    res = [("R1 extraction", *r1(tries)), ("R2 approval-scope key", *r2(mapping)),
           ("R3 conditional-yes key", *r3(mapping)), ("R4 merge aborted", *r4(merge, tries)),
           ("R5 template-adherence T4b key", *r5(json.load(open(f"{HERE}/test/before-fixes-3/mapping.json"))
                                                 if a.old else mapping))]
    print(f"Checking the {'PRE-FIX fixtures' if a.old else 'current kit'}:")
    for name, ok, why in res:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {why}")
    sys.exit(0 if all(r[1] for r in res) else 1)


if __name__ == "__main__":
    main()
