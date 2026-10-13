# W12A Athena failure follow-up

Producer: Codex Astra Medium. Clock read 2026-10-13 13:23 EDT.
Base: 80b5d3eadf09a7f0598508364b083bfecb087cdd. Work is in a separate no-hardlinks clone, branch codex/w12a-athena-fix. Original recovery checkout remains clean at its original head.

## Diagnosis

Athena run gap4-w12a-80b5d3e-20261013T163237Z failed seven generated-mutant shards and the language lint. Its eight unlisted survivors are current mutation IDs, not stale anchors. Five mutations bypass the check_model branch that refuses missing or leading-hyphen values for supported non-model flags. The ordinary tests did not exercise those cases. Three mutations bypass the FALLBACK_ENV pending guard and produce AttributeError when a pending string is treated as a mapping. The old assertRaises(NotReady) records an error, which the generated-mutation runner correctly refuses to count as an assertion kill.

Local reproduction with Python 3.13.2 confirmed the unchanged ordinary module passes 26/26. The check_model cond-false mutant also passed 26/26, while the take_environment cond-false mutant produced zero assertion failures and one AttributeError. The language lint reproduced the single banned word in the w4b copy-record reason. No production defect was needed to explain these failures.

## Changes

Tests now check missing and leading-hyphen values for each of seven supported non-model flags (21 cases). The pending assertion helper requires NotReady with the named pending cause; a wrong exception becomes an explicit E5.pending assertion failure. Both fallback and vendor-route pending checks use it. The generated runner, generator, equivalent list, mutation IDs, supported models, production code and gate criteria are unchanged.

The copy-record sentence now says “model-check each admitted call” instead of the lint-triggering absolute. No lint rule or excusal is added. The test-owner fragment records the strengthened coverage. No frozen instrument or prompt is changed.

## Verification so far

- Corrected ordinary module: 27/27 PASS, 9.537 seconds, no failures/errors/skips.
- Hand witnesses: 17/17 attributable RED.
- Language lint: clean, 100 inputs, the same 23 excused lines on record.
- Pooling lint: clean, 100 files, zero commits, no excusal path.
- Copy manifest: 357 files/54 fragments, five fixture builders byte-identical, eight frozen paths unchanged.
- git diff --check clean.

The eight previously surviving generated mutants still require a targeted rerun before this fix is complete. Full generated shards and a fresh combined Athena battery remain external gates. Tests use fakes and synthetic strings only; no vendor, credential, container runtime, salt or holdout is accessed. No push or new Athena dispatch occurred. Independent review is required.

## Targeted closure — 2026-10-13 13:28 EDT

Under a gate-approved Mac heavy slot, the existing generated runner was invoked with --only naming the exact eight Athena survivors and --timeout 240. Result: 198 generated, zero dropped, eight run, eight KILLED, zero equivalent, zero survivors, zero listed-but-killed and zero inconclusive. Each kill is an assertion in the strengthened E4.values or E5.pending test; each outcome reports zero errors. The full 198-mutant sweep was not repeated locally; the prior Athena evidence plus this targeted run is stated separately. The slot was released after completion. Logs are `/Users/javrodher/aegis-builds/w12a-athena-fix-{baseline,pending-before,model-before,green,witnesses,survivors8,lint-before}.log`.
