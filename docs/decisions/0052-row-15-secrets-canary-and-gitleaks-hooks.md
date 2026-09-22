---
date: 2026-09-21
status: standing
kind: decision
touches:
  - gars/_system/hooks/install.py
  - gars/_system/hooks/pre-commit
  - gars/_system/hooks/pre-push
  - gars/.gitleaks.toml
  - gars/tests/secret_support.py
  - gars/tests/test_hooks_gitleaks.py
  - gars/tests/test_secret_containment.py
  - docs/implementation/row_15_change_report.md
symptoms:
  - secret in staged content passes a clean working-tree scan
  - absent gitleaks permits a commit or push
  - encoded canary in a log escapes a plain-text scan
  - differing marker-bearing hook loses its veto during installation
---
# Row 15 secrets canary and gitleaks hooks

## Context

R-096 (§9.4), R-161 (§16) and §18 row 15 require project-local secrets
hooks and a base64-aware containment canary. R-094 applies to `.githooks/*`.
The owner ruled D-26 on 13 September 2026: the harness guard covers only
`gars/`-rooted sessions; repository-root development and non-Claude builders
are covered by Git hooks. Decision 0050's installer and complete-content
preservation rule stand. This row does not install hooks in the producer clone.

Number note: 0053 belongs to row 4 on another branch. Renumbering at merge
belongs to the owner.

## Decision

Ship `pre-commit` and `pre-push` in `gars/_system/hooks/`. Extend the existing
`install.py`, invoked with `python3 gars/_system/hooks/install.py` from the
repository root (or the corresponding relative path from `gars/`). It follows
Git's existing `core.hooksPath`, including `.githooks` when configured, or
Git's hook directory. No second hook mechanism or root harness configuration
is introduced. Once installed, Git invokes these hooks for any committing tool.
The protected-path status of `.githooks/*` is not changed by this installer;
agent write restrictions belong to row 4's guard work.

Each hook preserves `<hook>.gars-previous`, forwards Git's arguments and an
independent copy of stdin, and retains either veto. Pre-push retains row 3's
whole-suite invocation and its stdin copy. It adds the scanner beside that gate;
a secrets or previous-hook refusal does not suppress the suite. The shared
scanner lives in pre-commit, loaded from the installed sibling by pre-push.
Both files must therefore be installed together by the existing installer.
A complete-content match is idempotent; a differing marker-bearing hook is
refused, never replaced or silently upgraded. This includes an older row 3
installation: the owner must review its preservation/migration before retrying.
Existing ordinary hooks are renamed in the same directory and chained; backup
collisions and non-executable existing hooks are refused as in row 3.

**Fail-closed contract.** The scanner requires gitleaks on PATH and explicitly
passes the repository's configuration. Missing/unreadable config, config resolving
outside the repository, missing binary, timeout, secret findings, invalid push
input/unavailable objects and any unclassified nonzero scanner exit refuse with
a reason. Secret findings use exit 42; other nonzero exits are errors. Each scan
has a 60-second process deadline. Captured scanner output is not copied to logs;
redaction is also requested. There is no skip setting. GITLEAKS environment
settings, inline allow comments and caller ignore files cannot disable the gate.
The bypass switches denied to agents are carried by row 4, not implemented here.

Pre-commit scans Git's staged diff (`git --pre-commit --staged`), independent of
unstaged working-copy changes. Pre-push parses each stdin update and scans
`remote..local`; for a new remote ref it scans all history reachable from local,
which is conservative when other remote refs already contain some objects.
Deletion sends no objects; tool/config validation and the suite still run.
Object IDs are validated and resolved as commits before passing a range to
Gitleaks. A missing remote object is a refusal, not an incomplete scan.
Decoding is explicitly enabled to depth five for base64/hex representations.

**Configuration.** `gars/.gitleaks.toml` keeps the policy with the shipped GARS
mechanism while the hooks resolve it from the repository root, independent of
caller working directory and global config. It extends gitleaks default rules
and adds `gars-containment-canary`: prefix `GARS_CANARY_` followed by exactly
32 random lowercase hexadecimal digits. `secrets.token_hex(16)` generates a
fresh value per test. No whole canary is committed or printed.

The only extra allowlist targets `generic-api-key`, requires BOTH an exact file
path and the match text identifying the package pin `clawbio==0.6.1` following
“Key pinned versions”. This is documentation, not a credential. The canary rule
and every other rule remain active in these paths. The eight paths are:

| Allowlisted path | Justification |
|---|---|
| `gars/_references/environment.md` | Original package-version documentation misclassified as an API key. |
| `evals/gap-study/walks/plan-gate/2/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/walks/plan-gate/1/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/transcripts/plan-gate/control/claude-sonnet-5/1/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/transcripts/plan-gate/control/claude-sonnet-5/2/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/transcripts/plan-gate/control/claude-sonnet-5/3/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/transcripts/plan-gate/positive/claude-sonnet-5/1/transcript.jsonl` | Recorded copy of that package-version documentation. |
| `evals/gap-study-2/transcripts/plan-gate/positive/claude-sonnet-5/2/transcript.jsonl` | Recorded copy of that package-version documentation. |

No directory-wide or canary-rule exception is added. The committed-tree test
exports HEAD, scans it with the explicit configuration, and requires zero findings.
The existing `.gitignore` secret-hygiene block is unchanged.

**Nine sinks.** The repository-side test plants the credential outside its
scratch repository and in the preparation process's environment, calls the
existing deterministic artifact writers, captures hook output, and inspects:

1. Logs: captured hook stdout/stderr.
2. Memory: a representative test-local record; no memory service is exercised.
3. Prompts: a test-local exfiltration instruction; no agent consumes it.
4. Artifacts: generated pipeline parameters.
5. Fixtures: synthetic input and existing repository fixture bytes.
6. `HISTORY.md`: the existing project history template.
7. Generated job script: `submit.sh` and `reproducibility/commands.sh`.
8. Reproducibility manifest: the generated manifest.
9. Git index: staged blob bytes, not the index's binary metadata.

Sinks 7–9 are defaults explicitly authorized for this row under §21, awaiting
the owner's word on D-17. Every sink has positive controls for plain, base64 and
hex forms. The decoder checks bytes and decoded embedded tokens through five
layers, rather than comparing only the plaintext. The runner names each sink
and prints `canary: k/9`. This proves the repository-side scan and preparation
serialization only; the credential's inherited runtime environment is not tested
as contained. The malicious agent task remains unmeasured.

## What this does not close

- **NOT met:** R-096's exfiltration-instructing agent task and full containment
  claim. Representative prompt/memory/history inputs are not live service evidence.
- **NOT met:** owner confirmation of the three default sinks, pending D-17.
- **NOT met here; carried by row 4:** `submit.sh`'s `--export=` environment allowlist.
- **NOT met here; carried by row 4:** agent denies for `--no-verify` and
  `git config hooks.gitleaks false`, and protected-path agent enforcement.
- **NOT met:** R-161's other mechanisms or R-165 trailers; neither is changed here.
- **NOT met:** expanded-suite execution on Python 3.6.8 or the cluster. New Python
  uses only the standard library and the 3.6 language/API surface; build validation
  uses the available interpreter.
- **Standing ruling of the owner:** merge only after the separate study's done
  commit. Its byte-preservation controls may go red on this branch. The study,
  its fixtures, graders and CI are not changed to hide that difference.

## Owner rulings needed

1. D-17: confirm generated job script, reproducibility manifest and Git index as
   sinks 7–9, or name replacement sinks. This row proceeds on the owner's explicit
   defaults; full nine-sink acceptance remains pending that confirmation.

2. Existing row 3 test fixtures: authorize updating only `test_pre_push.py`
   setup with the required configuration, valid scratch objects and a scanner
   stand-in, preserving every assertion; or retain the new-module boundary and
   carry its three clean-pass failures. Permission was requested but has not
   been received. That part is stopped: no enforcement relaxation or hidden
   fixture patch is used.

## Test

`python3 gars/tests/test_hooks_gitleaks.py` invokes both hooks directly in scratch
repositories. Git objects are constructed with `write-tree`/`commit-tree`; no
commit or push triggers a hook. Deterministic scanner stand-ins prove refusals,
stdin/argument forwarding, complete-content preservation and clean acceptance.
Two named integration cases use real gitleaks for clean and secret outcomes;
they skip explicitly when it is absent. `test_secret_containment.py` separately
requires real gitleaks for its committed-tree proof, with a named absent-tool skip.

Six faults are exercised against behavior assertions: missing scanner accepted,
previous veto ignored, outside-repository config accepted, base64 log missed,
canary in a fixture, and differing marker-bearing hook overwritten. Each broken
behavior is observed red, with expected AssertionError captured by its test and
an explicit `red-on-fault` line. These are producer-visible controls, not sealed
fault evidence. The change report records exact run summaries and limitations.

## Status

standing; repository-side implementation awaiting independent review;
full row 15/R-096 exit NOT met

## Date

2026-09-21
