# Vendor provenance source-validation checkpoint

Parent checkpoint: c35fc915. Production integration remains incomplete.

The independent reviewer approved the minimal source contract and reviewed the resulting `vendor_provenance.py` and four synthetic tests: no MAJOR or check-weakening MINOR within this narrow scope. No additional review round is requested.

The module validates the box lane's exact actual-invocation journal against the registered adapter argv, bound model/mode/prompt/resume, cwd, container and stream. This journal is written before the runtime call: it proves the submitted request, never successful launch or completion. Native session projections must come from independent registered readers over retained regular-file bytes and SHA-256 references; the production registry remains empty. Native absent optional values stay `None`. Prompt, output and session identity are required and contradictions refuse. Requested model is compared when the native session reports it; later aggregate admission must require Codex's rollout model and Gemini's stream init/model statistics under their distinct D8 rules.

Observed CLI-version output is parsed against the pin; retained config, instruction and public vendor-source bytes are compared with frozen hashes. These facts do not claim that the CLI loaded those bytes. Actual config-directory/preflight/context joins remain owed.

## Focused verification

The Mac held at warning pressure during initial test development. Tests were authored first, but the missing-module baseline was executed after the implementation, rather than claiming an unrun red-first result.

Root approved an exact twelve-file source-only Athena transfer, excluding repository/history/holdout/credentials. At a fresh normal Mac gate the 207,709 source bytes and SHA manifest were staged under `/tmp/gap4-harness-provenance-20261013-1hhdkn12/source`. Unsuppressed gitleaks from a clean external cwd with configuration environment overrides removed returned exit 0 and `[]`. The remote source lives in its own `/home/javier/gap4-harness-provenance-20261013-1hhdkn12/source` folder. All twelve file hashes matched before execution.

Under a 60-second limit and a minimal environment, `tests/test_vendor_provenance.py` passed 4/4 in 0.024 s. The subsequent missing-module baseline failed all four by assertion, with no errors. Three in-memory mutations were each killed by assertion (no errors): ignoring submitted argv, ignoring native byte hash, and ignoring native cross-check disagreement. No candidate source bytes were changed by the witnesses. `result.json` and `witnesses.json` are retained beside the remote source. Test slots were serialized with the box builder and released after each invocation. This is a focused synthetic subset, not the integrated or full study proof.

## Literal-newline correction

After the initial four-test checkpoint, a fifth regression witness exposed literal U+2028/U+2029 characters being incorrectly treated as JSONL record boundaries by `splitlines`. At a fresh normal Mac gate the native-answer witness failed by assertion (one failure, no errors). The bound-envelope/native reader now frames only on literal LF and removes at most one terminal empty segment, preserving refusal of blank records. The final witness includes those characters in both the operator envelope and the native answer. At a subsequent fresh normal gate all five provenance tests passed locally in 0.134 s. Historical Claude parsing is unchanged; this correction grants no production admission.

The independent reviewer passed this focused correction with no findings; its review loop is closed.

## Native snapshot history join

The subsequent `session_history_facts` API uses the existing hash-reference and fact schemas to read every earlier interaction again from each later retained snapshot. It requires exact prior-fact equality (including optional `None` fields), stable native session identity and unique retained filenames. Current facts are deep-copied before retention. Missing ordinal errors propagate. This is not a native interaction-count proof: the eventual semantic reader and aggregate admission must reject extra/unassigned interactions separately.

The new witness ran red-first by one assertion; all six provenance tests then passed locally in 0.324 s at a fresh normal gate. Independent focused static review passed this new function/test with no MAJOR or check-weakening MINOR. The duplicate-filename witness was subsequently strengthened to use a repeated snapshot that actually contains both ordinals, so it cannot pass accidentally through the missing-ordinal refusal. The final targeted witness passed under a fresh normal gate; three in-memory mutations were each killed with one assertion failure and no errors: ignoring rewritten prefixes, duplicate snapshot references, or current native session changes. Candidate bytes were unchanged.

## Subscription-only OpenAI amendment

The owner's 13 October amendment requires existing Codex subscriptions, with no API-paid fallback or silent account switching. Preserve both registered O model IDs and coverage. Freeze opaque account aliases and deterministic account/slot assignment before runs; prohibit cross-account session resume and outcome/quota-triggered reassignment. The box lane owns supported isolated ChatGPT authentication, actual-route preflight, refusal of API billing variables, credential isolation and verified egress changes.

The shared checker must retain actual submitted model/config and native rollout model joins. An observed served-model mismatch refuses; absent served identity remains explicitly unverified. ChatGPT subscriptions have no D8 API project usage-by-model ledger, and allowance readings cannot replace served-model evidence. Record list-equivalent token cost separately from verified incremental subscription spend and usage; never fabricate a zero-dollar per-call vendor bill. Per-account quota remaining, reset times, model eligibility and before/after readings remain prerequisites, not established by the existence of two accounts. Google remains paid-key only under its $140 ceiling. The existing-account premise and freeze schema need explicit amendment and review before production admission. The reviewer clarified that D8's API-only holdout language applies to a later round: round 4 never runs holdout anywhere. Existing accounts also require owner-verified training settings and an explicit broader-account credential-exposure record; isolated CODEX_HOME does not narrow backend credential scope.

Preserve the existing environment-record scientific invariant (`check_take.py`, Decision 4): billing-route refusal belongs before launch. An executed take's reported credential source must remain recorded; rejecting it merely to turn the attempt into a replaceable rehearsal would create a selection route. The amendment needs a reviewed audit/protocol-departure classification for an executed auth anomaly, not a silent discard or replacement.

## Remaining blockers

- Shared driver publishing, checker invariants, per-harness aggregate identity/mode admission, cost/furniture and provenance-completeness integration remain owed.
- Gemini 0.64.0's installed source records ordered JSONL metadata, full-message upserts, patches, metadata sets and rewinds. An independent session reader must replay ordinary updates and explicitly refuse unsupported destructive edits; it cannot treat each line as an immutable message.
- Codex 0.162.1's offline generated app-server schemas are available from the box lane, but are not evidence that rollout records share those schemas.
- Source-derived native readers remain provisional until first recorded streams validate them. No production reader or checker was admitted by this slice.

Inspection-based remaining engineering estimate sent to the coordinator: 8–14 active hours, excluding resource holds and real-stream prerequisites; 12–20 if pinned-version shapes/configs differ materially. This is judgment, not measured campaign pace.
