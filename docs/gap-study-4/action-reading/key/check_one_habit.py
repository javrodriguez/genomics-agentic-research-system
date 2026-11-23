#!/usr/bin/env python3
"""One-habit check on key/mapping.json (EXPLORATORY).

For every task and standard, tries every fixed habit, meaning one action class, one content class and one setting
of the recorded facts, used the same way on both versions, and reports whether that habit is right on both versions:
  - for the action outcome alone   (habit = an action class),
  - for the content outcome alone  (habit = a content class with a setting of the facts),
  - for the two outcomes together  (habit = an action class with a content class and a setting of the facts).
An outcome with such a habit cannot separate the versions on that task: it is marked "not scored alone" (action)
or "cannot separate" (content, or both together).  Exit 0 when, for every task under the registered standard, the
content outcome and the two outcomes together pass; the contract standard is reported, never gated, because a
contract that asks for the same move on both versions is a finding, not a kit fault.
Usage: /usr/bin/python3 key/check_one_habit.py [--json]
"""
import itertools
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def content_right(std_half, c, facts):
    """`_wording` is enumerated like a fact: a habit can always use (or never use) the fixed wording."""
    for r in std_half["content"]:
        if c in r["content"] and all(facts[f] for f in r["require_all"]) and \
                (not r["require_any"] or any(facts[f] for f in r["require_any"])) and \
                (not r.get("require_wording") or facts["_wording"]):
            return True
    return False


def both_right(std_half, a, c, facts):
    if a not in std_half["action"] or not content_right(std_half, c, facts):
        return False
    pairs = std_half.get("pairs")
    return pairs is None or [a, c] in pairs


def check(mapping):
    out = {}
    names = mapping["facts"] + ["_wording"]
    settings = [dict(zip(names, v)) for v in itertools.product([False, True], repeat=len(names))]
    for task, t in mapping["tasks"].items():
        for std, halves in t["standards"].items():
            tr, no = halves["trap"], halves["normal"]
            act = [a for a in t["actions"] if a in tr["action"] and a in no["action"]]
            con = sorted({c for c in t["content"] for f in settings
                          if content_right(tr, c, f) and content_right(no, c, f)})
            bth = sorted({f"{a}+{c}" for a in t["actions"] for c in t["content"] for f in settings
                          if both_right(tr, a, c, f) and both_right(no, a, c, f)})
            out[f"{task}|{std}"] = {
                "action": "not scored alone (right on both: " + ", ".join(act) + ")" if act else "pass",
                "content": "cannot separate (right on both: " + ", ".join(con) + ")" if con else "pass",
                "both": "cannot separate (right on both: " + ", ".join(bth) + ")" if bth else "pass",
            }
    return out


def main():
    mapping = json.load(open(os.path.join(HERE, "mapping.json")))
    res = check(mapping)
    if "--json" in sys.argv:
        print(json.dumps(res, indent=1))
    else:
        for k, v in res.items():
            print(f"{k:42s} action: {v['action']}")
            print(f"{'':42s} content: {v['content']}")
            print(f"{'':42s} both: {v['both']}")
    bad = [k for k, v in res.items() if k.endswith("|registered") and (v["content"] != "pass" or v["both"] != "pass")]
    if bad:
        print("FAIL under the registered standard:", ", ".join(bad))
        sys.exit(1)
    print("PASS: under the registered standard no fixed habit is right on both versions of any task, for the "
          "content outcome and for the two outcomes together.")


if __name__ == "__main__":
    main()
