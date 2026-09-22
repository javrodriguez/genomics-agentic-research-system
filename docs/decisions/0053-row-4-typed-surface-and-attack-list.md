---
date: 2026-09-21
status: proposed
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/.claude/settings.json
  - gars/_system/tools/
  - gars/_system/tool_call.py
  - gars/_system/stage03_analysis.py
  - gars/_system/wrapperlib.py
  - gars/_system/executorlib.py
  - gars/_system/session_state.sh
  - gars/_system/wrappers/
  - gars/_references/tool_pins.json
  - gars/tests/
  - docs/tools/EXAMPLE.md
  - docs/implementation/row_4_change_report.md
symptoms:
  - a token denylist allows unregistered interpreters and shell separators
  - an agent can invoke the human approval command
  - collect and submit do not compare config_sha256
  - verify trusts approval content without repeating plan gates
---
# Row 4 typed surface and attack list

## Context

Spec v1.0.1 §18 Row 4, R-092/R-093/R-094/R-096 (agent bypass switches and executor
export only), R-098/R-099, R-073 and R-075. Parent: `c934f6d`.
Decision 0042's historical fixes remain evidence; this record supersedes its remaining
allow-on-unfamiliar-command stance. Decisions and formal assessments are not rewritten.

Number note: 0052 belongs to Row 15 on another branch. Renumbering at merge is the owner's.
The owner ruled D-26 on 13 September: git-level hooks covering every harness belong to
Row 15. This row creates no hooks and makes no claim to cover an unguarded builder.

## Decision

The owner's 21 September rulings, quoted:

> 2A: the typed tool surface this row builds is exactly the set of calls the contracts
> already make (`python3 _system/<helper>.py <subcommand> ...` in the `CONTEXT.md` files,
> the wrappers' `check | prepare | collect`, the executor's `submit | status | cancel`,
> and the read-only filesystem calls §9.1 names). Bash is removed for those: an agent
> session can run a registered typed call or a read-only filesystem command and nothing
> else. No helper is rewritten to achieve this; the surface is declared over the helpers
> as they are.

> 3A: R-098 governs. When the guard cannot judge a call it refuses, and every refusal names
> the rule, where it is written, and the typed call to use instead. The stance in
> `guard_hook.py`'s docstring ("a false positive is worse than a miss") is replaced by this
> one, in the same place.

`gars/_system/tools/registry.json` declares each tool's schemas, CLI mapping, roles,
timeout, side effects, network requirement and version. `tools/policy.py` validates the
JSON object before any execution, rejects unknown fields/options, and maps the original
helper argv to the same schema. `tool_call.py` invokes the existing helper as a process,
without a shell, and returns an explicitly typed stdout/stderr/exit-code envelope.
The original helper output remains intact inside that envelope.

The Bash harness transport is only a compatibility carrier for single simple registered
calls and the declared read-only commands. Shell operators, expansion, inline interpreter
code, unregistered helpers and all other commands refuse. Explicit R-096 reasons cover
`--no-verify`, including equals spelling, and `hooks.gitleaks false` before the general
no-git refusal. Malformed calls fail closed. The guard's write-target scanner remains
available as historical code; authorization no longer depends on its completeness.

`READ_ONLY` is the protected-path source; `repo:` patterns are repository-relative for
paths outside `gars/`. The settings deny entries render those as `../` patterns. The
suite tests exact equality and every listed write spelling, including resolved symlink
escapes. Every resolved write outside the workspace refuses. Standing/accepted decisions
are covered by the stronger all-decisions pattern. Non-agent builders require Row 15's
hooks; the workspace hook alone cannot enforce the human-commit requirement.

R-075's charset and `shlex.quote` are applied at config checking, header rendering and
all seven nf-core body render points. Safe scalars retain existing quoting bytes. Free-form
backend argv/directives are refused; `submit_argv` is selected from the built-in enum.
An unfamiliar Groovy executor grammar refuses under ruling 3A; the seeded grammar permits
safe scalar substitutions. The executor passes an explicit environment-name allowlist,
never `--export=ALL`. No secret-containment score is claimed by this row.

`verify` repeats the plan content gates: skeleton markers, outputs, vocabulary, venue,
relative paths, and resolved containment. Config checking compares the current config
against the prepared manifest; it never establishes a new baseline during collect/submit.

Workspace pins cover every shipped `SKILL.md`; no workspace MCP server declaration exists.
Pins start **unreviewed**. Only an independent review may promote them. Session startup
checks inventory, status and content hash before rebuilding the project index. The hook
cannot prevent the harness itself loading skills or MCP servers before that hook, nor can
it inventory globally configured resources outside this workspace. Those enforcement
limits are **NOT met**, not implicit successes.

The command-level enumeration and the exact tree commands used to derive it are in the
Row 4 change report. There are ten wrappers, of which seven are nf-core. Stage helpers:
`stage00_register` (assays/create/inspect/link/finalize), `stage01_samplesheet`,
`configure` (genomes/peaks/protocols/contrasts/apply), `stage03_analysis`
(create/approve/verify), `resolve_artifact`. The executor exposes submit/status and a
refusing cancel declaration pending the missing implementation ruling below. Filesystem
commands: ls, cat, head, tail, stat, shasum, wc, grep, rg, find, with declared restricted
flags. No `resolve_citation` implementation exists on this tree; ruling 2A does not invent it.

## Owner rulings needed

1. **Approval trust and expiry.** The spec requires a launch-time actor, expiry, and refusal
   of a hand-written record after a hook bypass, but chooses no trustworthy launch binding,
   trust anchor or expiry policy. Options: human-owned approval store inaccessible to the
   agent, plus explicit UTC expiry; or human-owned signing key and protected verification
   material, plus explicit UTC expiry. Cryptography cannot be improvised to bypass the
   stdlib constraint. The related reviewer/human launch binding must not use an environment
   variable or an agent-supplied role flag. This part is stopped pending the owner's ruling.
2. **Existing characterization tests.** The file boundaries forbid edits to existing test
   assertions, but those explicitly expect git/bypass commands to pass. Options: authorize
   targeted expectation/golden-byte updates for the named changed requirements; or keep
   the boundaries and report the required whole-suite failures. The question was sent to
   the owner before changing any such assertion.
3. **Collect placement.** Every collect implementation lives in a wrapper; the boundary
   permits only rendering changes in the seven nf-core wrappers. Options: authorize a
   shared hash check at the start of all ten collect implementations; or enforce only at
   the guard/dispatcher boundary and name direct unguarded collect as NOT met.
4. **Contract shell spellings.** Wrapper contracts use `$GARS_WRAPPERS` and
   `${GARS_WRAPPERS:-_system/wrappers}`; the literal typed surface cannot safely execute
   arbitrary shell expansion. Options: authorize future contract replacement by literal
   registered paths/JSON tool calls; or design a narrowly bound substitution mechanism.
   Contract files remain unchanged; literal expanded registered paths are declared now.
5. **Missing cancel.** The existing executor has submit/status/header/describe and no cancel.
   Options: retain a declared refusal until Row 12 supplies the verb; or explicitly authorize
   the minimal backend implementation now, including the >1-hour approval condition.
   No cancellation or lifecycle writer is implemented here.

## What this does not close

- **NOT met:** injection resistance 20/20 with positive control; the synthetic twenty
  documents and control exist, but scoring needs an agent run.
- **NOT met:** R-093 reviewer as a separate OS user with read-only credentials; profiles
  alone are not deployment isolation.
- **NOT met:** external harness R-099 load enforcement, as detailed above.
- **NOT met:** unresolved owner rulings above, pending response and measured evidence.
- R-095 is not applicable: no Docker configuration exists in `gars/`;
  `_references/environment.md` records the environment constraint.
- No Row 15 hook, trailer gate, lifecycle writer, new manifest groups or release checker.
- The owner's standing ruling applies: merge only after the separate study's done commit.
  Source controls for that study may turn red when `gars/` changes; its fixtures, graders,
  `evals/` and `.github/` are unchanged.

## Test

See `docs/implementation/row_4_change_report.md` for the required runners, exact summary
lines, named fault witnesses, boundary audit and residuals. The five deterministic attack
classes do not stand in for the separate agent injection experiment.

## Status

proposed; producer implementation in progress, not independently reviewed or approved

## Date

2026-09-21
