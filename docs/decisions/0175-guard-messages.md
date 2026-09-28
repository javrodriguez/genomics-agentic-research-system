---
date: 2026-09-27
status: standing
kind: decision
touches:
  - gars/_system/guard_hook.py
  - gars/_system/tools/policy.py
  - gars/_system/tool_call.py
  - gars/tests/test_refusal_messages.py
  - gars/tests/build_refusal_corpus.py
  - gars/tests/fixtures/refusal_decisions.jsonl
  - README.md
  - DEVELOPMENT.md
symptoms:
  - a read of a background command's output file is refused with "R-073 human approval store is outside workspace read access"
  - every refusal ends with "Use typed call: python3 _system/tool_call.py fs.read '{"paths":["CONTEXT.md"]}'", whatever was refused
  - a STATUS write is refused with two different "Use typed call" sentences
  - a refusal cites "Rule R-092/R-094/R-098" when another rule fired
---
# Guard messages: every refusal says what is true and what to do next

Follow-up to [0058](0058-row-4-typed-surface-and-attack-list.md), [0160](0160-front-door-defects.md) and [0165](0165-guard-lexer.md), whose bytes are unchanged.
Every ruling here is **the lane's**, made under the owner's standing delegation of 23 September 2026 by the lane's coordinator; no sentence in this record is the owner's.
0176 is the lane's delegated approval of the protected change; this record does not write it.

## Context

A refusal's text is the only thing an agent reads when GARS says no, and at public main `a80df2d` it often sent the agent the wrong way.
Each item below was reproduced by feeding json-built hook payloads straight into `gars/_system/guard_hook.py`, with no model involved.

1. **One suffix on every refusal.**
   `deny()` appended "Rule R-092/R-094/R-098, spec §9.1/§9.3/§9.6; decision 0058. Use typed call: … fs.read CONTEXT.md" to every refusal.
   The rule list was wrong for R-151, R-096, R-073, 0107 and 0141 refusals, and the typed call contradicted every site that already named its own next step: a STATUS write ended with two different "Use typed call" sentences.
2. **One alternative for every typed-surface refusal.**
   `Refusal.record()` in `tools/policy.py` gave every refusal in `policy.py` and `tool_call.py` the same `alternative`, reading `CONTEXT.md`.
3. **An outside read named the approval store.**
   A native Read, Glob or Grep outside the workspace said "R-073 human approval store is outside workspace read access" for any outside path, including a background command's own output file (0160's deferred D3); the file-tool refusal cited R-073 in prose while its record's rule is R-094.
4. **Refusals that named nothing to do.**
   The lexer's refusals (0165) all read "only one simple command; no shell operators or expansion"; a flag outside a tool's vocabulary and an unregistered command never said what is allowed.

## Decision

**Ruling 0175 (the lane's).** The change is to text only: the message, the `alternative` and the rule citation in prose, never what is refused.

1. **Each site owns its rule citation and its next step** (`guard_hook.py`).
   `deny()` no longer appends a suffix; every guard refusal carries its own rule citation as a trailing parenthesis and ends with one sentence starting `Next: ` (the marker ruled as Q-msg-marker A).
   Sites that already named a next step (R-151's STATUS writer, the generated files, the pilot log's writer, the doors and closed-project texts, `rg --pre`) keep their text and lose only the suffix; the unreadable-input and guard-failure texts keep "retry, then stop and report" as their next step; R-096 gains "Next: commit and push normally; the secret scan runs by itself."
2. **Each typed-surface refusal passes its own alternative** (`tools/policy.py`, `tool_call.py`).
   `Refusal` takes an `alternative`; `record()` keeps its six keys (`type field rule message source alternative`), and every `field`, `rule` and `type` value is byte-identical to `a80df2d`.
   A vocabulary refusal names the allowed values from the schema's own enum at refusal time (`ls` takes only `-a -l -la -al`); an unregistered command names the file tools by their command names and the typed-call form with where the tool list lives (`_system/tools/registry.json`), read from the registry at refusal time (Q-msg-list A).
3. **One outside-read sentence, true for every outside path** (Q-msg-073 A).
   "`<path>` is outside the workspace (`<root>`); a session reads only inside it (R-073). Next: if it is a command's background output, run that command in the foreground and read its result directly (decision 0160)."
   No path-class branching: parsing the harness's task-output path shape in the guard would add new path logic for a hint.
   The file-tool refusal keeps its record rule R-094 and cites "R-073 (recorded as R-094)" (Q-msg-rule A); changing the record field belongs to a record-level lane.
4. **The lexer's refusals name the quoting that is allowed at `a80df2d`.**
   "One command per call: run each step as its own call", plus, where the character can be an argument, the quoting 0165 allows: a `#`, brace, tilde or parenthesis inside quotes in any command's arguments; `; | & < >` inside quotes only in the file tools' arguments (`ls cat head tail stat shasum wc grep rg find`); a `$`, backtick or newline never.
   A quoted operator in a command that is not a file tool is told to send a search pattern with `|` to `grep` or `rg` directly.
   Each such sentence was checked against the lexer: advice the lexer would refuse is a defect.
5. **The decision pin.**
   `gars/tests/fixtures/refusal_decisions.jsonl` holds the payloads harvested from the seven modules that drive the guard, the registry and the reported rows, each with its exit code, record `type`, `field` and `rule` and the dispatcher's decision, generated at `a80df2d` and first committed alone, 2166 rows, before any wording commit; `gars/tests/test_refusal_messages.py` replays every row through the current guard and the dispatcher's refusal path (parse and authorize only, never executing a tool).
   The first review showed that a guard letting a two-path `find` through still passed the pin, because no row sent a file tool two paths; 13 rows were added, again generated at `a80df2d` (a two-path call per file tool, a `find` expression, and the two payloads of the review's findings below), and every one of the 2166 earlier rows kept its payload bytes and its decision.
   Over the final 2179 rows the refused set (1709) and the allowed set (470) are equal before and after.
6. **The fixture carries no machine identity.**
   The first fixture held the building machine's absolute scratch path behind JSON escapes and in compressed snapshots, which a text scanner cannot read; it was regenerated at `a80df2d` with placeholder roots and plain-JSON snapshots, every decision identical to the first pin.
   A test walks every string in the fixture, decodes every base64 and zlib blob it finds, and fails on a home prefix, the running machine's home, repository root or user name, or any of four owner tokens that it holds only as lengths and SHA-256 digests, so the test itself spells none of them.

7. **Two texts the first review found false for an input that triggers them.**
   A typed tool name that is not registered, sent through the dispatcher over Bash, was told its JSON could not be read (the name check's refusal was caught by the JSON handler); it now says the tool name is not registered and points to the registry, with the same field `args` and rule R-092.
   The R-096 texts said a command disables the secret scan when the guard had only found the words in it (a read-only `grep -n hooks.gitleaks false.txt` is refused); they now say the command contains those words, which can disable the scan.
8. **Generated-file texts reworded, although the head said they keep theirs.**
   `projects/_index.md`, `files.csv`, the samplesheet and the template catch-all gained rule citations and a `Next:` sentence; the `_index.md` text had named `bash _system/build_projects_index.sh`, which the guard itself refuses (`bash` is not registered), and now asks the human to run it.

The rest is tests only: `test_refusal_messages.py` (the pin, a static check that every `deny(` and `Refusal(` site carries a next step, a dynamic check that every refused row renders exactly one non-generic next step, no "approval store" text on a generic outside path, a prose rule that cites the record rule, the reported rows by name, and the fixture's privacy), `build_refusal_corpus.py`, and the moved assertions that named old text in `test_bash_lexer.py`, `test_policy_attacks.py`, `test_nonpublic_read_block.py`, `test_pilot_doors.py` and `test_pilot_log.py`, each keeping its exit and field assertions.

## Rejected alternatives

- **Branching the outside-read text on the path's class** (a task-output file versus a system file): new path parsing in the guard, for a hint one sentence can give truthfully for every path.
- **Changing a record's `rule` to match its prose** (R-094 to R-073 on the file-tool outside read): a record-level change the pin forbids; this lane changes words only.
- **A JSON next-step field on every deny** (Q-msg-marker B): the plain `Next: ` sentence reads the same to an agent and changes no record shape.
- **Writing the flag and tool lists into the messages** (Q-msg-list B): two sources that drift; the registry is the one source.

## What this does not close

- The R-096 next step, "commit and push normally; the secret scan runs by itself", was ruled word for word by the lane's head, but a session's own `git commit` and `git push` are refused as unregistered, so a session cannot take it; the re-review recorded this as a NOTE, and a next step a session can take (leaving commits to the human builder) is for a later lane.
- `find _system -name CONTEXT.md` meets the earlier "paths cannot be options or stdin" check, whose next step (prefix a dash name with `./`) leads to the `find` one-path refusal; the text is true, and naming `find`'s one-path rule there is a later wording change.
- Regenerating the fixture kept every earlier row's payload and decision but re-captured its run-time context (a generated project page carries its creation date), so 1292 context hashes differ from the first pin; the build log reports only the decision comparison.
- Three NOTEs of the first review, recorded and not changed: the config-drift refusal cuts its text before "run prepare" and routes the agent to the human, although the producer role may run the `.prepare` typed call itself; a quoted operator inside a typed call's JSON gets the ruled search-pattern advice, true but not helpful for that call; the build log names the producer's scratch copies by parent-relative paths (no machine or owner identity in them).
- Which payloads the guard refuses: owned by 0058, 0107, 0141 and 0165, unchanged here.
- The wording of tools other than the guard and the dispatcher.

## Test

`gars/tests/test_refusal_messages.py` is new, 15 tests: the decision pin replays all 2179 rows of `gars/tests/fixtures/refusal_decisions.jsonl` through the guard and the dispatcher's refusal path and asserts each exit code and record `type`, `field` and `rule`, with per-source row counts non-zero; a static walk of the three `_system` files requires a next step at every `deny(` and `Refusal(` site; every refused row must render exactly one non-generic next step, no "approval store" on a generic outside path, and a prose rule that cites its record rule; the reported rows and both reviews' payloads are asserted by name; and the fixture's own privacy is scanned through every string and every decoded blob.
It was red at its own commit (3254 failures with the pin green) and green after the wording.
It must fail when the generic suffix returns, when one site loses its alternative, when a refused payload is allowed (including a two-path `find`), when a record's `rule` changes, when "approval store" returns to the outside-read text, and when the fixture carries a home path in plain, escaped or compressed form; each was planted and each turned the module red.
The full suite then found two test-side defects, both fixed in the producer's fifth round: an assertion on the old outside-workspace text in `gars/tests/test_protected_paths.py`, never moved, and the corpus replay reading the temp-folder variable directly, so the module errored when it is unset.
The suite total moves from 1150 to 1165.
The landing's evidence is recorded in 0176.

## Status

Standing.

## Date

2026-09-27
