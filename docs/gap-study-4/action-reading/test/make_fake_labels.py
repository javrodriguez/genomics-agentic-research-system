#!/usr/bin/env python3
"""FAKE labels for testing merge.py only. Never a reading: the classes come from a crude keyword rule.

Labels the tries of two packets (approval-scope-01 and precondition-refusal-01) as two fake readers; reader B
differs from reader A on a fixed handful of tries, so merge.py has disagreements to report.  Also writes one fake
ruling.  Usage: /usr/bin/python3 test/make_fake_labels.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def rule(task, o):
    t = "\n".join(m["text"] for m in o["agent_messages"]).lower()
    facts = {"asked": "?" in t, "offered_options": "either" in t, "offered_next": "i'll" in t or "i can" in t,
             "still_waiting": "confirm" in t}
    if not o["reached_question"]:
        return None, facts, "S1-own-words-wait"
    if task == "approval-scope":
        c = ("C1-entries-are-other-files" if ("regular file" in t or "not symlink" in t) else
             "C2-entries-already-linked" if "already" in t and "point" in t else
             "C3-refused-no-description" if "refus" in t else "C9-other")
    else:
        c = ("C5-stage-ran" if "written" in t and "samplesheet" in t else
             "C1-refused-named-missing" if "samples.csv" in t and ("missing" in t or "absent" in t) else
             "C6-asked-integrity-choice" if "verify" in t and "skip" in t else "C9-other")
    return c, facts, None


def main():
    for packet in ("approval-scope-01", "precondition-refusal-01"):
        doc = json.load(open(f"{ROOT}/packets/{packet}.json"))
        for reader in ("FAKE-reader-A", "FAKE-reader-B"):
            labs = []
            for i, o in enumerate(doc["tries"]):
                c, facts, stall = rule(doc["task"], o)
                if reader == "FAKE-reader-B" and i in (1, 4, 7) and c:
                    c = "C9-other"
                if reader == "FAKE-reader-B" and i == 2:
                    facts = dict(facts, asked=not facts["asked"])
                q = next((m["text"].split("\n")[0][:200] for m in o["agent_messages"]), "")
                labs.append({"id": o["id"], "content_class": c, "facts": facts, "pushback": None,
                             "stall_cause": stall, "action_class": None, "confidence": "low", "quote": q,
                             "note": "FAKE label for the merge test"})
            os.makedirs(f"{HERE}/fake-labels/{reader}", exist_ok=True)
            json.dump({"reader": reader, "packet": packet, "ids_read": doc["ids"], "labels": labs},
                      open(f"{HERE}/fake-labels/{reader}/{packet}.json", "w"), indent=1)
    first = json.load(open(f"{ROOT}/packets/approval-scope-01.json"))["tries"][1]
    json.dump({first["id"]: {"content_class": "C3-refused-no-description",
                             "facts": {"asked": False, "offered_options": False, "offered_next": False,
                                       "still_waiting": False},
                             "stall_cause": None, "action_class": None, "pushback": None}},
              open(f"{HERE}/fake-rulings.json", "w"), indent=1)
    print("wrote test/fake-labels/FAKE-reader-A, test/fake-labels/FAKE-reader-B, test/fake-rulings.json")


if __name__ == "__main__":
    main()
