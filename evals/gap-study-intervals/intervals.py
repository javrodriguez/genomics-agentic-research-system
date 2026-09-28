#!/usr/bin/env python3
"""Exact intervals for every graded half of the Gap Study, rounds 1-3, re-derived on demand.

Run (from the repo root; standard library only, seconds):
    python3 evals/gap-study-intervals/intervals.py --write    regenerate INTERVALS.md and intervals.json
    python3 evals/gap-study-intervals/intervals.py --check    re-derive both and compare byte for byte

WHAT IT READS. The committed results files of the three rounds, evals/gap-study*/results/*.json,
and nothing else. It writes only into its own folder. The study folders are pinned instruments;
this script never writes, imports or regrades anything in them.

WHAT IT COUNTS. For each half (one task, one model, one half), the takes graded are the number of
labels in the results file and the correct takes are the labels whose verdict is `correct`. The
`n` field is never read: round 2 has a cell whose `n` says 3 where one take was graded.

WHAT IT COMPUTES. An exact two-sided 0.95 Clopper-Pearson interval on the per-take probability,
in exact rational arithmetic, each bound rounded outward to three decimals; per round, the
smallest two-sided Fisher exact p any two halves of the sizes present could reach (a property of
the design, labelled post hoc; no test between actual halves is computed); the probability of a
hold (six correct of six) under a per-take probability p; a sample-size table for any later
round; and, as the evidence for the method, the coverage of Clopper-Pearson and Wilson intervals
at the sizes the rounds graded.

WHAT --check BINDS. The committed page and data equal what this script derives from the
committed results files, and every results file equals its blob at its round's done commit (the
commit that round's CI job pins). It refuses, exit 2, in a shallow clone or outside git, rather
than passing on a binding it could not read. A check that saw no half fails.
"""

import argparse
import hashlib
import json
import math
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

# (round, study folder, done commit): the commit each round's job in .github/workflows/ci.yml
# checks out; test_intervals.py asserts these equal the pinned refs.
ROUNDS = (
    ("1", "evals/gap-study", "b735229f5c9213bb20c7e49fb7ceddddbcac7abc"),
    ("2", "evals/gap-study-2", "bf065feedccc0392f69e95a6d674288bb861a2b0"),
    ("3", "evals/gap-study-3", "e2979b3143081824aadea73523ec41af30c1ddb1"),
)
ROUND_NOTES = {
    "1": ("Round 1's counts as its own instrument graded them. `docs/EVALS.md` also prints round 1's "
          "takes regraded by round 2's instrument; those regraded counts are not used here."),
    "2": "Round 2's counts as graded, including its one incomplete half.",
    "3": "Round 3's counts as graded.",
}
OUT = "evals/gap-study-intervals"
PAGE = OUT + "/INTERVALS.md"
DATA = OUT + "/intervals.json"
HALVES = ("positive", "control")
VERDICTS = ("correct", "incorrect")
TAKES_PER_HALF = 3            # the rounds' design: three takes per half; a hold is 3 of 3 on both
ALPHA = Fraction(1, 20)       # two-sided 0.95
GRID = 1000                   # bounds on the 0.001 grid
WILSON_Z2 = Fraction(3841458820694124, 10 ** 15)   # the 0.975 normal quantile, squared
COVERAGE_SIZES = (1, 3)
SAMPLE_SIZES = (3, 5, 10, 15, 20, 30, 50)
POWER = Fraction(4, 5)
HOLD_P = ("0.5", "0.7", "0.8", "0.9", "0.95", "0.99")


# ---- exact arithmetic ---------------------------------------------------------------------------

def _tail(n, x, k, upper):
    """Numerator over GRID**n of P(X >= x) (upper) or P(X <= x), X ~ Bin(n, k/GRID)."""
    xs = range(x, n + 1) if upper else range(0, x + 1)
    return sum(math.comb(n, i) * k ** i * (GRID - k) ** (n - i) for i in xs)


def _at_most(num, n, level):
    return num * level.denominator <= level.numerator * GRID ** n


def clopper_pearson(x, n, alpha=ALPHA):
    """(lower, upper) as Fractions on the 0.001 grid: lower floored, upper ceiled (outward)."""
    if not 0 <= x <= n or n < 1:
        raise ValueError("need 0 <= x <= n and n >= 1")
    half = alpha / 2
    lower = Fraction(0)
    if x > 0:
        lo, hi = 0, GRID          # largest k with P(X >= x | k) <= alpha/2
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if _at_most(_tail(n, x, mid, True), n, half):
                lo = mid
            else:
                hi = mid - 1
        lower = Fraction(lo, GRID)
    upper = Fraction(1)
    if x < n:
        lo, hi = 0, GRID          # smallest k with P(X <= x | k) <= alpha/2
        while lo < hi:
            mid = (lo + hi) // 2
            if _at_most(_tail(n, x, mid, False), n, half):
                hi = mid
            else:
                lo = mid + 1
        upper = Fraction(lo, GRID)
    return lower, upper


def fmt(value):
    """A Fraction on the 0.001 grid, as text."""
    scaled = value * GRID
    if scaled.denominator != 1:
        raise ValueError("not on the 0.001 grid: %s" % value)
    whole, part = divmod(int(scaled), GRID)
    return "%d.%03d" % (whole, part)


def fmt_p(value):
    """A p-value to three decimals; one that rounds to zero is written as under 0.001."""
    if value < Fraction(1, 2 * GRID):
        return "under 0.001"
    return fmt(round3(value))


def floor3(value):
    return Fraction(math.floor(value * GRID), GRID)


def round3(value):
    return Fraction(round(value * GRID), GRID)


def fisher_two_sided(x1, n1, x2, n2):
    """Two-sided Fisher exact p: the tables no more probable than the one observed, summed."""
    k = x1 + x2
    weights = {i: math.comb(n1, i) * math.comb(n2, k - i)
               for i in range(max(0, k - n2), min(k, n1) + 1)}
    observed = weights[x1]
    return Fraction(sum(w for w in weights.values() if w <= observed), math.comb(n1 + n2, k))


def min_fisher_p(n1, n2):
    return min(fisher_two_sided(a, n1, b, n2) for a in range(n1 + 1) for b in range(n2 + 1))


_REJECT = {}


def _rejection(n):
    if n not in _REJECT:
        _REJECT[n] = [(a, b) for a in range(n + 1) for b in range(n + 1)
                      if fisher_two_sided(a, n, b, n) <= ALPHA]
    return _REJECT[n]


def power_centred(n, a):
    """Exact power of the two-sided Fisher test at 0.05, two halves of n takes, per-take
    probabilities (50 - a)/100 and (50 + a)/100."""
    lo, hi = 50 - a, 50 + a
    first = [math.comb(n, x) * lo ** x * hi ** (n - x) for x in range(n + 1)]
    second = [math.comb(n, x) * hi ** x * lo ** (n - x) for x in range(n + 1)]
    return Fraction(sum(first[x1] * second[x2] for x1, x2 in _rejection(n)), 100 ** (2 * n))


def smallest_detectable(n):
    """Smallest a (difference 2a/100) whose power reaches 0.80, or None."""
    for a in range(1, 51):
        if power_centred(n, a) >= POWER:
            return a
    return None


def coverage_minimum(n, method):
    """(lowest coverage, p where first reached) on the grid p = 0.001 .. 0.999."""
    best = None
    for k in range(1, GRID):
        covered = 0
        for x in range(n + 1):
            if method == "clopper-pearson":
                inside = ((x == 0 or _tail(n, x, k, True) * 40 >= GRID ** n) and
                          (x == n or _tail(n, x, k, False) * 40 >= GRID ** n))
            elif method == "wilson":
                inside = (GRID * x - n * k) ** 2 <= WILSON_Z2 * n * k * (GRID - k)
            else:
                raise ValueError(method)
            if inside:
                covered += math.comb(n, x) * k ** x * (GRID - k) ** (n - x)
        value = Fraction(covered, GRID ** n)
        if best is None or value < best[0]:
            best = (value, Fraction(k, GRID))
    return best


# ---- reading the rounds -------------------------------------------------------------------------

def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_round(root, rnd, folder, commit):
    inputs, halves = [], []
    for path in sorted((Path(root) / folder / "results").glob("*.json")):
        raw = path.read_bytes()
        rel = folder + "/results/" + path.name
        inputs.append({"round": rnd, "path": rel, "sha256": sha256(raw), "done_commit": commit})
        data = json.loads(raw.decode("utf-8"))
        task = data["task"]
        for model in sorted(data["cells"]):
            cells = data["cells"][model]
            if sorted(cells) != sorted(HALVES):
                raise ValueError("%s: %s has halves %s" % (rel, model, sorted(cells)))
            for half in HALVES:
                cell = cells[half]
                labels = cell["labels"]
                if not isinstance(labels, list):
                    raise ValueError("%s: %s %s labels is not a list" % (rel, model, half))
                verdicts = [label["verdict"] for label in labels]
                unknown = [v for v in verdicts if v not in VERDICTS]
                if unknown:
                    raise ValueError("%s: %s %s unknown verdicts %s" % (rel, model, half, unknown))
                graded, correct = len(verdicts), verdicts.count("correct")
                lower = upper = None
                if graded:
                    lo, hi = clopper_pearson(correct, graded)
                    lower, upper = fmt(lo), fmt(hi)
                halves.append({"task": task, "model": model, "half": half, "graded": graded,
                               "correct": correct, "lower": lower, "upper": upper,
                               "state": cell.get("state")})
    return inputs, halves


def pair_verdict(pos, ctl):
    if not pos["graded"] and not ctl["graded"]:
        return "not run"
    if pos["graded"] < TAKES_PER_HALF or ctl["graded"] < TAKES_PER_HALF:
        return "incomplete"
    full = pos["correct"] == pos["graded"] and ctl["correct"] == ctl["graded"]
    return "yes" if full else "no"


def sensitivity(halves):
    sizes = sorted({h["graded"] for h in halves if h["graded"]})
    counts = {s: sum(1 for h in halves if h["graded"] == s) for s in sizes}
    out = []
    for i, a in enumerate(sizes):
        for b in sizes[i:]:
            if a == b and counts[a] < 2:
                continue
            out.append({"sizes": [a, b], "halves": [counts[a], counts[b]],
                        "smallest_p": fmt_p(min_fisher_p(a, b)),
                        "could_reach_0.05": min_fisher_p(a, b) <= ALPHA})
    return out


def derive(root):
    root = Path(root)
    inputs, rounds = [], []
    for rnd, folder, commit in ROUNDS:
        got, halves = read_round(root, rnd, folder, commit)
        inputs.extend(got)
        rounds.append({"round": rnd, "folder": folder, "done_commit": commit, "halves": halves,
                       "sensitivity": sensitivity(halves)})
    coverage = []
    for n in COVERAGE_SIZES:
        row = {"takes": n}
        for method in ("clopper-pearson", "wilson"):
            value, at = coverage_minimum(n, method)
            row[method] = {"lowest": fmt(floor3(value)), "at_p": fmt(at),
                           "below_0.95": value < 1 - ALPHA}
        coverage.append(row)
    sample = []
    for n in SAMPLE_SIZES:
        bounds = [clopper_pearson(x, n) for x in range(n + 1)]
        a = smallest_detectable(n)
        sample.append({"takes": n,
                       "widest_interval": fmt(max(hi - lo for lo, hi in bounds)),
                       "lower_when_all_correct": fmt(bounds[n][0]),
                       "smallest_fisher_p": fmt_p(min_fisher_p(n, n)),
                       "centred_difference_at_power_0.80": None if a is None else {
                           "difference": fmt(Fraction(2 * a, 100)),
                           "between": [fmt(Fraction(50 - a, 100)), fmt(Fraction(50 + a, 100))]}})
    holds = [{"p": p, "hold": fmt(round3(Fraction(p) ** 6))} for p in HOLD_P]
    three = clopper_pearson(3, 3)
    two = clopper_pearson(2, 3)
    return {
        "generated_by": OUT + "/intervals.py",
        "level": "0.95",
        "method": "Clopper-Pearson, two-sided, exact; bounds rounded outward to 0.001",
        "graded_is": "the number of labels in a half; the n field is never read",
        "inputs": inputs,
        "rounds": rounds,
        "holds": {"per_take_p": holds, "lowest_p_on_each_half_for_3_of_3": fmt(three[0]),
                  "highest_p_for_2_of_3": fmt(two[1])},
        "sample_size": sample,
        "coverage": coverage,
    }


# ---- rendering ----------------------------------------------------------------------------------

def render_json(data):
    return json.dumps(data, indent=1, ensure_ascii=False) + "\n"


def _cell(h):
    if not h["graded"]:
        return "not run", ""
    return "%d of %d" % (h["correct"], h["graded"]), "%s to %s" % (h["lower"], h["upper"])


def render_md(data):
    out = []
    w = out.append
    w("# Gap Study intervals")
    w("")
    w("_Generated by `evals/gap-study-intervals/intervals.py --write`; never edited by hand. "
      "`python3 evals/gap-study-intervals/intervals.py --check` re-derives every figure on this page "
      "from the committed results files, and CI runs it on every push._")
    w("")
    w("A secondary analysis, written after all three rounds were graded and not part of any round's pre-registration.")
    w("It changes no count, label or table the rounds published, and it never pools takes across rounds, tasks, models or halves.")
    w("")
    w("## What is shown")
    w("")
    w("For each half (one task, one model, one half: positive or control), the correct takes out of the takes actually graded, "
      "and an exact two-sided 0.95 confidence interval on the per-take probability of a correct take.")
    w("The takes graded are the labels in the results file, never its `n` field.")
    w("The interval is Clopper-Pearson, computed in exact arithmetic, with each bound rounded outward to three decimals, "
      "so the printed interval contains the exact one.")
    w("No point estimate is printed: a count of three carries no rate.")
    w("")
    w("## Method, and why Clopper-Pearson")
    w("")
    w("An interval method is judged by its coverage: the chance, at a given true per-take probability p, that the interval it builds contains p.")
    w("Clopper-Pearson's coverage is at least 0.95 at every p for every number of takes.")
    w("The Wilson score interval is narrower, but at the sizes these rounds graded its coverage falls well under 0.95 at some p.")
    w("Lowest coverage over the grid p = 0.001 to 0.999, derived exactly by the script:")
    w("")
    w("| Takes graded | Clopper-Pearson: lowest coverage | at p | Wilson: lowest coverage | at p |")
    w("|---|---|---|---|---|")
    for row in data["coverage"]:
        cp, wi = row["clopper-pearson"], row["wilson"]
        w("| %d | %s | %s | %s | %s |" % (row["takes"], cp["lowest"], cp["at_p"], wi["lowest"], wi["at_p"]))
    w("")
    w("With three takes the price of guaranteed coverage is width; the width is the finding, not a defect of the method.")
    w("")
    for rnd in data["rounds"]:
        w("## Round %s" % rnd["round"])
        w("")
        w("Results files: `%s/results/`, as committed; `--check` also verifies each is byte-identical to its blob "
          "at the round's done commit `%s`, the commit this round's CI job pins." % (rnd["folder"], rnd["done_commit"][:7]))
        w(ROUND_NOTES[rnd["round"]])
        w("")
        w("| Task | Model | Positive | 0.95 interval | Control | 0.95 interval | 6 of 6 |")
        w("|---|---|---|---|---|---|---|")
        pairs = {}
        for h in rnd["halves"]:
            pairs.setdefault((h["task"], h["model"]), {})[h["half"]] = h
        states = []
        for (task, model), pair in pairs.items():
            pos, ctl = pair["positive"], pair["control"]
            pc, pi = _cell(pos)
            cc, ci = _cell(ctl)
            w("| `%s` | `%s` | %s | %s | %s | %s | %s |" % (task, model, pc, pi, cc, ci, pair_verdict(pos, ctl)))
            for h in (pos, ctl):
                if h["state"] != "RAN":
                    states.append(h)
        w("")
        not_run = [h for h in states if not h["graded"]]
        partial = [h for h in states if h["graded"]]
        if not_run:
            models = sorted({h["model"] for h in not_run})
            texts = sorted({h["state"] for h in not_run})
            w("Not run, so no interval: %s (%d halves). The results files record: %s" % (
                ", ".join("`%s`" % m for m in models), len(not_run),
                " / ".join('"%s"' % t for t in texts)))
            w("")
        for h in partial:
            w("Incomplete: `%s`, `%s`, %s half, %d of its takes graded; the results file records the state \"%s\" "
              "and an `n` field this page does not read." % (h["task"], h["model"], h["half"], h["graded"], h["state"]))
            w("")
        sizes = rnd["sensitivity"]
        graded = [h for h in rnd["halves"] if h["graded"]]
        w("**Sensitivity (post hoc, not pre-registered).** %d halves graded." % len(graded))
        for s in sizes:
            a, b = s["sizes"]
            what = ("two halves of %d takes" % a) if a == b else ("a half of %d take%s and a half of %d takes" % (
                a, "" if a == 1 else "s", b))
            w("Between %s, the most extreme split possible (every take correct in one, none in the other) "
              "gives a two-sided Fisher exact p of %s." % (what, s["smallest_p"]))
        if sizes and not any(s["could_reach_0.05"] for s in sizes):
            w("So no two halves of this round could differ at the 0.05 level, whatever their counts.")
        w("No test between actual halves is computed.")
        w("")
    holds = data["holds"]
    w("## What a hold means")
    w("")
    w("The rounds call a task held by a model when all three takes are correct on both halves: six correct takes of six.")
    w("If every take were an independent draw with the same per-take probability p on both halves, a hold would be seen with probability p to the sixth:")
    w("")
    w("| Per-take probability p | Chance of a hold |")
    w("|---|---|")
    for row in holds["per_take_p"]:
        w("| %s | %s |" % (row["p"], row["hold"]))
    w("")
    w("A hold is consistent with a per-take probability as low as %s on each half (the lower bound of 3 of 3), "
      "and a half with 2 of 3 with one as high as %s." % (holds["lowest_p_on_each_half_for_3_of_3"],
                                                        holds["highest_p_for_2_of_3"]))
    w("")
    w("## Sizing a later round")
    w("")
    w("For two halves of n takes each; exact, from the same arithmetic.")
    w("The last column is the smallest difference between two per-take probabilities centred on 0.5, "
      "on a 0.02 grid, that a two-sided Fisher exact test at 0.05 finds with power 0.80.")
    w("")
    w("| Takes per half | Widest 0.95 interval | Lower bound when every take is correct | Smallest attainable Fisher p | Difference found with power 0.80 |")
    w("|---|---|---|---|---|")
    for row in data["sample_size"]:
        diff = row["centred_difference_at_power_0.80"]
        found = "none" if diff is None else "%s (%s vs %s)" % (diff["difference"], diff["between"][0], diff["between"][1])
        w("| %d | %s | %s | %s | %s |" % (row["takes"], row["widest_interval"], row["lower_when_all_correct"],
                                         row["smallest_fisher_p"], found))
    w("")
    w("## Limitations")
    w("")
    w("- Each interval assumes the takes of a half are independent draws with one per-take probability; that is a model of the takes, not a measurement of them.")
    w("- A bound speaks only for the round's own task, fixture, instrument and harness version.")
    w("- The rounds' instruments differ, so each round is shown on its own and never pooled.")
    w("- The sensitivity, hold and sizing figures were computed after grading and were not pre-registered.")
    w("")
    w("## Inputs")
    w("")
    w("| Round | Results file | sha256 |")
    w("|---|---|---|")
    for item in data["inputs"]:
        w("| %s | `%s` | `%s` |" % (item["round"], item["path"], item["sha256"]))
    w("")
    return "\n".join(out)


def write(root):
    root = Path(root)
    data = derive(root)
    (root / OUT).mkdir(parents=True, exist_ok=True)
    (root / PAGE).write_text(render_md(data), encoding="utf-8")
    (root / DATA).write_text(render_json(data), encoding="utf-8")
    return data


# ---- the check ----------------------------------------------------------------------------------

class _Failed(object):
    returncode, stdout = 127, b""


def _git(root, *args):
    try:
        return subprocess.run(["git", "--no-replace-objects", "-C", str(root)] + list(args),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return _Failed()


def git_blob(root, commit, rel):
    got = _git(root, "cat-file", "blob", "%s:%s" % (commit, rel))
    if got.returncode != 0:
        return None
    return got.stdout


def git_listing(root, commit, folder):
    got = _git(root, "ls-tree", "--name-only", commit, "--", folder + "/results/")
    if got.returncode != 0:
        return None
    return sorted(Path(name).name for name in got.stdout.decode("utf-8").splitlines()
                  if name.endswith(".json"))


def _first_difference(a, b):
    for number, (x, y) in enumerate(zip(a.splitlines(), b.splitlines()), 1):
        if x != y:
            return "line %d" % number
    return "length (%d vs %d lines)" % (len(a.splitlines()), len(b.splitlines()))


def check(root, verify_history=True, blob=None, listing=None):
    """(exit code, lines): 0 clean, 1 a mismatch or unreadable input, 2 a binding it could not read."""
    root = Path(root)
    lines, failed = [], False
    try:
        data = derive(root)
    except (OSError, ValueError, KeyError, TypeError, UnicodeError) as exc:
        return 1, ["FAIL cannot derive from the results files: %s" % exc]
    seen = sum(len(r["halves"]) for r in data["rounds"])
    graded = sum(1 for r in data["rounds"] for h in r["halves"] if h["graded"])
    lines.append("graded against seen: %d rounds, %d results files, %d halves seen, %d graded, %d not run"
                 % (len(data["rounds"]), len(data["inputs"]), seen, graded, seen - graded))
    if seen == 0 or graded == 0:
        lines.append("FAIL no half graded: a check that measured nothing is not a pass")
        failed = True
    try:
        committed = json.loads((root / DATA).read_text(encoding="utf-8"))
        recorded = {i["path"]: i["sha256"] for i in committed["inputs"]}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        committed, recorded = None, {}
        lines.append("FAIL %s unreadable: %s" % (DATA, exc))
        failed = True
    current = {i["path"]: i["sha256"] for i in data["inputs"]}
    for path in sorted(set(recorded) | set(current)):
        if path not in current:
            lines.append("FAIL input removed since the page was generated: %s" % path)
            failed = True
        elif path not in recorded:
            lines.append("FAIL input added since the page was generated: %s" % path)
            failed = True
        elif recorded[path] != current[path]:
            lines.append("FAIL input changed since the page was generated: %s" % path)
            failed = True
    for rel, text in ((PAGE, render_md(data)), (DATA, render_json(data))):
        try:
            have = (root / rel).read_text(encoding="utf-8")
        except OSError as exc:
            lines.append("FAIL %s unreadable: %s" % (rel, exc))
            failed = True
            continue
        if have == text:
            lines.append("ok %s is exactly what the script derives" % rel)
        else:
            lines.append("FAIL %s differs from what the script derives, first at %s"
                         % (rel, _first_difference(have, text)))
            failed = True
    refused = False
    if verify_history:
        if blob is None and listing is None:
            shallow = _git(root, "rev-parse", "--is-shallow-repository")
            if shallow.returncode != 0:
                lines.append("REFUSED not a git checkout: the done-commit binding cannot be read")
                refused = True
            elif shallow.stdout.strip() != b"false":
                lines.append("REFUSED shallow clone: the done commits are absent, so the binding cannot be read")
                refused = True
        blob = blob or git_blob
        listing = listing or git_listing
        if not refused:
            bound = 0
            for rnd, folder, commit in ROUNDS:
                names = listing(root, commit, folder)
                if names is None:
                    lines.append("REFUSED cannot list %s/results/ at %s" % (folder, commit[:7]))
                    refused = True
                    continue
                here = sorted(Path(i["path"]).name for i in data["inputs"] if i["round"] == rnd)
                if names != here:
                    lines.append("FAIL round %s results files differ from the done commit %s: %s vs %s"
                                 % (rnd, commit[:7], here, names))
                    failed = True
                for item in (i for i in data["inputs"] if i["round"] == rnd):
                    raw = blob(root, commit, item["path"])
                    if raw is None:
                        lines.append("FAIL %s has no blob at the done commit %s" % (item["path"], commit[:7]))
                        failed = True
                        continue
                    if sha256(raw) != item["sha256"]:
                        lines.append("FAIL %s differs from its blob at the done commit %s"
                                     % (item["path"], commit[:7]))
                        failed = True
                    else:
                        bound += 1
            lines.append("done-commit binding: %d of %d results files equal their blobs"
                         % (bound, len(data["inputs"])))
            if bound != len(data["inputs"]):
                failed = True
    if failed:
        return 1, lines
    if refused:
        return 2, lines
    return 0, lines


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="regenerate the page and the data")
    mode.add_argument("--check", action="store_true", help="re-derive and compare; bind the inputs")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parent.parent.parent
    if args.write:
        data = write(root)
        print("wrote %s and %s from %d results files" % (PAGE, DATA, len(data["inputs"])))
        return 0
    code, lines = check(root)
    print("\n".join(lines))
    print("gap-study intervals: %s" % {0: "PASS", 1: "FAIL", 2: "REFUSED"}[code])
    return code


if __name__ == "__main__":
    sys.exit(main())
