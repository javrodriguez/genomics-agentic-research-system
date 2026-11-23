VERDICT: CHANGES

# Review of lane pf1-l3-transcript-integrity at fb354328 (base 96c1d959)

Reviewer: a fresh, independent Opus 5.5 session, written Sat 24 Oct 2026, 21:41 EDT (from `date`).
Scope: MAJOR 7 and m9 of pfr-20261024/round1/prefreeze-1.md, read against FOLD-PLAN-prefreeze-1.md and the caller's threat model.
No code was changed.
The probes ran on scratch copies of committed walks in my scratchpad; nothing in the clone or the round folder was written apart from this file.

## What I ran (Mac, behind mac_slot light-ok, python3.12, one module at a time)

- `tests/test_pf1_transcript_integrity.py`: 21 tests OK (T3 asserts 151 claude-code, 38 codex and 36 gemini walks, each equal but w-g24).
- `tests/test_pf1_egress_probe.py`: 12 tests OK.
- `routing.py --check`: "23 rows, 3 annotations, sound".
- Not run by me: test_claude_code_adapter, test_routing, test_preflight, test_build_draft.
- The athena run pf1-l3-checks-fb35432-20261025T012547Z ran four other modules (test_vendor_entries, test_vendor_body, test_pipeline, test_box_integration), 4/4 PASS-SUBSET (run.log, summary.txt).
- READER_SOURCES (native_reader_registration.py lines 85-87): none of the nine files is in `git diff --name-only 96c1d959 fb354328`.

## Break attempts (scratch copies of w125, w-o46, w-g21)

| Attempt | Result |
|---|---|
| Reply word edited in the session file only | refused: `[transcript-mismatch] turn 1 ... at item 14` |
| The same edit in both the session file and the turn stream | passes; this is residual (a), out of the stated threat model |
| A tool_result record dropped | refused at item 3 |
| Turns 1 and 2 swapped, operator lines with them | refused, both turns |
| An assistant text before the first operator line | refused ("1 content item(s) before its first operator line") |
| A Codex argv changed by one trailing space (w-o46, snapshot digest rebound) | refused `[transcript-mismatch] turn-1.jsonl line 5` |
| A Gemini string resultDisplay turned into an object (w-g21) | refused `[transcript-mismatch] turn-1.jsonl line 7` |
| A Gemini object resultDisplay changed to another object | passes; no grader reads an object display (gemini_projection.py line 30: "output is the string resultDisplay only"), and the raw-record readers read both copies |
| Reply rewritten plus one auto_mode attachment appended | `[transcript-mismatch]` and `[harness-condition-violated] ... auto_mode`: routes harness-error (finding 1) |
| Reply rewritten plus one deferred_tools_delta adding SendMessage | `[transcript-mismatch]` and `[harness-condition-violated] a deferred_tools_delta adds ['SendMessage']`: routes harness-error (finding 1) |
| An operator line's text edited, nothing else | no mismatch (finding 2) |
| An isSidechain assistant record injected | no mismatch; the view refuses the record (finding 2) |
| A user record with origin task-notification injected mid-turn | no mismatch (finding 6) |
| Egress: an empty route table | refused ("names no gateway and no on-link network") |
| Egress: an inspect gateway that is not among the candidates | refused (`_check_gateway`, the `missing` test) |

## Findings

### 1. MAJOR: a forged claude-code transcript can still route its own take to harness-error, by adding one record to the same file

- The transcript-mismatch row (routing.json, row 10) has `none_of: harness-condition-violated`, so beside that reason the take goes to operator-reason-after-first-turn, which is harness-error and re-run.
- Two of the harness-condition checks read the session file, which is the same agent-writable file the mismatch check has just shown to be untrustworthy:
  - `steer_condition_problems`: any `auto_mode` attachment line (check_take.py `_auto_mode_records`, about line 2706, raised about line 2739);
  - `denied_tool_problems`: any `deferred_tools_delta` attachment whose `addedNames` holds a denied tool (about lines 2793-2806).
- Reproduced on a copy of w125: rewriting a reply and appending either record gives both reasons.
  The lane's own oracle encodes the result: test_routing.py line 1788 (`[tm, HCV] -> harness-error`) and SCENARIOS line 3218.
- This breaks the threat model's line "A forgery must not be able to route its own take to harness-error ... after the first turn".
  Residual (c) in PF1_TRANSCRIPT_RESIDUAL names the auto_mode road; it does not name deferred_tools_delta.
- Standalone, without any forgery, the same one-line write voids any take and re-runs it.
  That is an agent-caused re-run, which goes against the MAJOR 5 principle.
- Suggested fix (it needs a ruling, because glitch-b5's ruling 3 is involved): make the none_of read only the host-side harness-condition evidence (launch journals, stream init).
  One way is to emit the two session-file causes under their own tag.
  Another is to drop them as evidence when transcript-mismatch is present, since that file has been shown not to be the record.
  Keep ruling 3 for the journal and init causes.

### 2. MINOR: other in-file edits still void a take as harness-error, and the residual does not name them

- If only an operator line's text is edited, the content check passes, because operator lines split the turns but their text is not compared.
  Reading `operator_line_problems` (check_take.py about lines 1095-1143), that edit raises `[operator-lines]`, a generic operator reason: harness-error, re-run.
  I did not run check4 end to end for this; it is from reading the code.
- An injected sidechain record, or a non-JSON or U+2028 line, raises transcript-unreadable (harness-error) and leaves the units unchanged.
- Beside a real content rewrite, these are outranked by the aborted row, so they do not hide a forgery.
  Alone, though, each is an agent-caused re-run.
- A cheap partial close: each turn's operator line must equal the prompt in that turn's launch journal (argv[2], host-written, already parsed by `_journal_view`), under transcript-mismatch.
- At least name the rest in residual (c).

### 3. MINOR: on Codex and Gemini, an unreadable record routes harness-error, so corrupting the native store hides any rewrite and re-runs the take

- `vendor_content_problems` turns every read error into `[transcript-unreadable]`, an operator reason: harness-error after the first turn.
  It never passes, so "unreadable means refused" holds in the sense of never-a-pass.
  But a Codex or Gemini agent that leaves its native store unreadable makes the mismatch impossible to compute, and the take is re-run.
- The vendor readers had this class before this lane.
- Name it beside finding 2.
  Do not reroute it to aborted without a ruling, because w-g24 shows unreadable can be a genuine harness state.

### 4. MINOR: the two data-matched rules send a false positive to aborted, against the model

- The Codex rule (shlex.split of the stream command equals the rollout argv) holds on 226 of 226 commands.
  The Gemini rule (stream output equals resultDisplay when it is a string, absent otherwise) holds on 2375 of 2375 results.
  Neither is cited to the pinned source; residual (c)'s last sentences say so.
- What the residual does not say: if the renderer differs on a genuine take (a quoting edge case, a NUL, an unusual display), that take is published as the model's aborted outcome, counted against holding and never re-run.
- Name that consequence.
- Also: a stream command that shlex cannot parse (`ValueError`, check_take.py `_codex_command_problems`) is host-side text, not something the agent wrote.
  It reads more truly as transcript-unreadable than as transcript-mismatch.

### 5. MINOR: m9's probe has not run against a real box

- test_box_integration uses a spy preflight ("collect_and_evaluate is a spy", lines 55-56).
  The athena run included no lane module.
  So DIRECT_PROGRAM has only met fake route tables and a fake connect.
  The checks.d header defers the live run to freeze_rehearsal.
- Before the freeze, the live preflight record should show egress-gateway-refused's detail with the bridge gateway among `gateway_candidates`.
- Inference, not verified: on a `--internal` network the inspect's `Gateway` may be empty.
  The binding to the inspect is then vacuous, and the "first host of the on-link network" heuristic alone finds the gateway.
- The evidence statement "athena passed 4/4" is true, but it is not evidence for m9 or for the content check.

### 6. NIT: two roads are not named

- IPv6: DIRECT_PROGRAM reads /proc/net/route only, and no IPv6 target is tried.
  The egress residual should say so.
- An injected `user` record with `origin.kind` task-notification is read by the view as harness text and is not compared.
  Residual (b) lists attachment, system and bookkeeping records but not these.

## The open question from the L2a review: can the agent, through its writable config folder, change a later turn's init event and so route a take to harness-error?

- **Through the init event itself: I found no road.**
  This is inferred from the argv; I did not test it on the binary.
  - Every arm-A turn runs `--setting-sources project,local --strict-mcp-config` (claude_code_adapter.py ISOLATION_FLAGS, line 75; run_take.py line 346), so the folder's user settings and user MCP servers never load.
  - The denials ride in the argv and in the inline `--settings`, which outrank anything in the folder.
  - The init fields routing pins (`model`, `permission_mode`, `version`) come from the argv and the binary.
  - Not checked: whether the cached feature flags in the folder's `.claude.json` can change the init.
  - The arm-A config folder has no per-turn guard: CONFIG_FOLDER_HARNESSES is (codex, gemini), run_take.py about line 2236.
- **But the folder holds the session file, so the answer to the underlying question is yes.**
  An auto_mode or deferred_tools_delta record written there raises harness-condition-violated, and the take routes harness-error (finding 1, reproduced).
- A child process can also write an init record with a denied tool into the CLI's stdout pipe.
  That falls under residual (a), the one-uid road, which the threat model puts out of scope.

## What holds

- On the main thread, the claude-code content comparison is the same unit set the view reads: text, thinking, tool_use with canonical input, tool_result with canonical content and is_error, and other blocks.
- Its turn split matches transcript_view's operator-line rule.
  The admitted isMeta wakeup and nudge records are not operator lines in either.
- It bites on every rewrite I tried.
- A cut or non-JSON line becomes a missing unit.
- C6 carries the same comparison live, and a turn record without units fails closed.
- The pinned walk results do not move: T3 is green on all committed walks, and w-g24 stays transcript-unreadable.
- The routing row, its source and the labels4 docstring agree, and routing.py --check is sound.
- The egress checks fail closed on a missing shape, an empty candidate set, an untried port and a gateway missing from the inspect.
  An answered refusal is listed, never counted as a connection.
