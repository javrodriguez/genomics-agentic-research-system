#!/usr/bin/env python3
"""Static contract lint: the compliance checks that need no agent (decision 0023).

Run:  python3 tests/check_contracts.py            (from the repo root; exit 0 = clean)

Three checks, each of which has caught (or would have caught) a real defect:

1. **Eight sections, in order** (contract_standard.md). A contract missing a section is not
   "shorter", it is out of standard, and the standard says every contract changes together.
2. **Script <-> contract vocabulary drift.** Validation rules are stated twice -- as code in a
   `_system/` helper and as Definitions prose in its contract (decision 0011 accepts this and
   mitigates with shared vocabulary). Nothing detected drift until this check: every failure
   code a script can emit must appear in the contract that handles it, or the agent meets a
   code its contract never taught it.
3. **Wait-point sanity.** A template that ends by asking a question is a wait point; two
   templates in one contract must not ask for the same decision (the stage-00 T2 bug, 08-21).
   Mechanically checkable subset: no two templates in a contract may share an identical
   question line.

It also REPORTS (never fails on) the approximate token load of each contract, so growth is a
number that gets tracked instead of an impression (assessment 2026-08-21, §5.4).
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GARS = REPO / "gars"

SECTIONS = ["Purpose", "Inputs", "Scope Boundaries", "Definitions", "Process",
            "Response Format", "OUTPUT", "Human check"]

# script -> (contract, regex extracting the failure vocabulary from the script)
DRIFT = [
    ("_system/stage01_samplesheet.py", "01_prepare_samplesheets/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/nfcore-atacseq-wrapper/nfcore_atacseq_wrapper.py",
     "02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    # wrapperlib's shared codes must appear in every nextflow-wrapper contract
    ("_system/wrapperlib.py",
     "02_bioinformatics/atacseq_bulk/01_nfcore-atacseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrapperlib.py",
     "02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/nfcore-rnaseq-wrapper/nfcore_rnaseq_wrapper.py",
     "02_bioinformatics/rnaseq_bulk/01_nfcore-rnaseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/rnaseq-de/rnaseq_de.py",
     "02_bioinformatics/rnaseq_bulk/02_rnaseq-de/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/nfcore-chipseq-wrapper/nfcore_chipseq_wrapper.py",
     "02_bioinformatics/chipseq_bulk/01_nfcore-chipseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/nfcore-cutandrun-wrapper/nfcore_cutandrun_wrapper.py",
     "02_bioinformatics/cutandrun/01_nfcore-cutandrun-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
    ("_system/wrappers/nfcore-methylseq-wrapper/nfcore_methylseq_wrapper.py",
     "02_bioinformatics/methylseq/01_nfcore-methylseq-wrapper/CONTEXT.md",
     r'fail\("([a-z_]+)"'),
]


def contracts():
    # `**` matches zero directories too, so this single glob covers stages and sub-stages;
    # sorted-set dedupes anything a future pattern overlap would double-count.
    return sorted(set(GARS.glob("0*/**/CONTEXT.md")) | set(GARS.glob("0*/CONTEXT.md")))


def check_sections(path, text, errors):
    heads = re.findall(r"^## (.+)$", text, re.M)
    present = [h for h in SECTIONS if h in heads]
    missing = [h for h in SECTIONS if h not in heads]
    if missing:
        errors.append("%s: missing section(s): %s" % (path, ", ".join(missing)))
        return
    order = [heads.index(h) for h in SECTIONS]
    if order != sorted(order):
        errors.append("%s: sections out of order (%s)" % (path, " > ".join(heads)))


def check_drift(errors):
    for script, contract, rx in DRIFT:
        codes = sorted(set(re.findall(rx, (GARS / script).read_text())))
        ctext = (GARS / contract).read_text()
        for code in codes:
            if code not in ctext:
                errors.append("drift: %s emits failure code %r; %s never mentions it"
                              % (script, code, contract))


def check_wait_points(path, text, errors):
    """No two templates in one contract may end by asking the identical question."""
    questions = {}
    for block in re.findall(r"```\n(.*?)```", text, re.S):
        lines = [l.strip() for l in block.strip().splitlines() if l.strip()]
        if not lines:
            continue
        last = lines[-1]
        if last.endswith("?"):
            questions.setdefault(last, 0)
            questions[last] += 1
    for q, n in sorted(questions.items()):
        if n > 1:
            errors.append("%s: %d templates end with the same question: %r" % (path, n, q))


def report_tokens():
    print("approximate token load per contract (chars/4):")
    total = 0
    for p in contracts():
        n = len(p.read_text()) // 4
        total += n
        print("  %6d  %s" % (n, p.relative_to(GARS)))
    print("  %6d  total" % total)


def main():
    errors = []
    n = 0
    for p in contracts():
        n += 1
        text = p.read_text()
        rel = p.relative_to(GARS)
        check_sections(rel, text, errors)
        check_wait_points(rel, text, errors)
    check_drift(errors)
    report_tokens()
    if errors:
        print("\n%d problem(s):" % len(errors))
        for e in errors:
            print("  FAIL " + e)
        return 1
    print("\n%d contracts clean: sections, wait points, vocabulary." % n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
