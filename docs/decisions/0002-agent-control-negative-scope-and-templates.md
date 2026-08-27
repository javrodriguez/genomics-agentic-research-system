---
date: 2026-08-10
status: standing
kind: lesson
symptoms:
  - "agent read a colleague's files"
  - "volunteered analysis of an unrelated experiment"
  - "instructions present and ignored"
touches:
  - gars/_references/contract_standard.md
  - all stage contracts
---
# Agent control: negative scope boundaries and fixed response templates

**Positive instructions do not constrain an LLM agent.** The first live test had both
"do not improvise steps it does not specify" at workspace level and an explicit failure branch
in the stage contract. Given a path with no FASTQs, the agent searched subdirectories, read a
colleague's `settings.txt` and sample sheets, and volunteered an analysis of an unrelated
experiment. Both instructions were present. Both were ignored.

Three fixes, all now standard in every contract:

1. **Scope Boundaries** — stated negatively, naming the forbidden action literally
   ("do not read sample sheets, settings files, QC reports, or pipeline outputs found there").
2. **Response Format** — fixed templates `T1…Tn`; nothing else may be sent. Free-form replies
   varied every run and buried decisions in prose.
3. **Process decomposition** — one action per numbered step, every failure branch its own step.
   The original step 7 was a 90-word sentence containing five conditionals; buried branches get
   skipped.

Codified as the **Stage Contract Standard**, now eight sections, in
`gars/_references/contract_standard.md`. The eighth, *Human check*, was added later for the
same reason as the others: a gate that is not a named section is a gate a contract author omits.
