# W12A-R1-1 model-call binding fold

Producer: Codex Astra Medium. Clock read Tue 13 Oct 2026 11:37:56 EDT.
Base: d1662fdbc98dfe79ecd204aa9364011623478a33. Same owned codex/w12a-recovery clone.
Independent finding: plans/gap-study-round-4/w12a-review-astra-2026-10-13.md, W12A-R1-1.

## Closure

For arm G, check_model now admits only bare gemini or an absolute executable path whose basename is gemini. Every admitted spelling receives the same full-model-ID check. Empty calls, relative paths, wrappers and other executables refuse by name; they no longer return unchecked. Other arms retain their existing behavior. Non-model preflight/version probes already use the separate agent_exec_argv path.

The parser consumes the model option and the adapter's supported value-taking options (-p/--prompt, -o/--output-format, --approval-mode, --resume/-r). Separate and equals model-value forms are covered. Unsupported compact/clustered flags, -- positional tails and other arguments fail closed, preventing an unparsed second model selection. Prompt values are consumed as values. Both approved Gemini IDs and the alias table are unchanged.

Tests that previously sent agent-cli or x as Gemini turns now send the admitted Gemini client with the existing pinned model. Their original environment, cross-arm and PENDING assertions remain. Copy fragments record these adjustments. The generated-shard comment now derives its count at runtime instead of retaining a stale hardcoded count.

## Evidence

- Red-first regression on d1662fd: 1 assertion failure, 0 errors. The absolute Gemini alias reached the fake launcher trap instead of Refused. read_login returned a synthetic value; no login file or runtime was accessed.
- Green allowlist module: 26/26 PASS, 5.560 seconds. Boundary regression covers bare and two absolute spellings, all three supported model flag forms, alias refusal before launcher dispatch, approved IDs, disallowed executable forms and ambiguous trailing option forms.
- Hand witnesses: 17/17 attributable assertion RED, including gemini-executable-unbound. No errors used as successful kills.
- Entire ordinary test_run_take module: 44/44 PASS, 30.986 seconds. It had previously measured about 20 seconds; this run exceeded the light estimate and a first heavy slot was acquired under w12a-fold, then released. All batches started after successful light-ok checks. No generated sweep or full repository suite was launched.
- Gemini adapter argv and fake-runtime turn checks: 2/2 PASS, 0.115 seconds; existing production adapter options still pass.
- git diff --check clean. Final manifest and staged secret sweep results accompany the commit handback.

Existing reports are unchanged; this is a new addendum. No real vendor/container/credential probe, athena dispatch, push, merge or landing. Generated shards, integration battery and CP2 real-image checks remain separate gates. Ready for the independent bounded fold review.
