#!/usr/bin/env python3
"""Test for KIT-REVIEW-2 note 5 (EXPLORATORY): the 3 aborted tries stay out of agreement, disagreements.md and
agreed-sample.md, even when both readers label them (here with FAKE, deliberately disagreeing labels on two of them
and agreeing labels on the third).  Runs the current merge.py, and the merge.py of before this fix (rebuilt by
reverting the one changed line), and expects: current PASS, before FAIL.
Usage: /usr/bin/python3 test/test_aborted.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRATCH = tempfile.mkdtemp(prefix="test-aborted-")   # a fresh scratch folder outside the checkout


def labels():
    ids = json.load(open(f"{ROOT}/key/ids.json"))
    aborted = sorted(i for i, k in ids.items() if k["route"] == "aborted")
    f = {"asked": False, "offered_options": False, "offered_next": False, "still_waiting": False}
    for reader, classes in (("FAKE-A", ["C3-reported-approved"] * 3),
                            ("FAKE-B", ["C9-other", "C4-answered-no-approval-word", "C3-reported-approved"])):
        d = f"{SCRATCH}/labels/{reader}"
        os.makedirs(d, exist_ok=True)
        labs = [{"id": i, "content_class": c, "facts": f, "pushback": None, "stall_cause": None, "action_class": None,
                 "confidence": "low", "quote": "", "note": "FAKE"} for i, c in zip(aborted, classes)]
        json.dump({"reader": reader, "packet": "fake", "ids_read": aborted, "labels": labs}, open(f"{d}/fake.json", "w"))
    return aborted


def run(merge_path, out):
    subprocess.run([sys.executable, merge_path, f"{SCRATCH}/labels/FAKE-A", f"{SCRATCH}/labels/FAKE-B", "--out", out],
                   check=True, capture_output=True)
    text = "".join(open(f"{out}/{n}").read() for n in ("disagreements.md", "agreed-sample.md"))
    table = open(f"{out}/ACTION-READING.md").read()
    row = next(l for l in table.splitlines() if l.startswith("| `plan-gate` |") and l.count("|") == 5)
    return text, row


def main():
    os.makedirs(SCRATCH, exist_ok=True)
    aborted = labels()
    src = open(f"{ROOT}/merge.py").read()
    new_line = 'ag = None if k["route"] == "aborted" else agree(l1, l2)'
    assert src.count(new_line) == 1
    old = src.replace(new_line, "ag = agree(l1, l2)").replace(
        "HERE = os.path.dirname(os.path.abspath(__file__))", f"HERE = {ROOT!r}")
    open(f"{SCRATCH}/merge_before_fixes_2.py", "w").write(old)
    ok_all = True
    for name, path, want in (("current merge.py", f"{ROOT}/merge.py", True),
                             ("merge.py before this fix", f"{SCRATCH}/merge_before_fixes_2.py", False)):
        text, row = run(path, f"{SCRATCH}/out-{'new' if want else 'old'}")
        hits = [i for i in aborted if i in text]
        ok = not hits and "| 0 |" in row
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: aborted ids in disagreements.md or agreed-sample.md: {len(hits)}; "
              f"plan-gate agreement row: {row}")
        ok_all &= (ok == want)
    print("as expected (current passes, before fails)" if ok_all else "NOT as expected")
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
