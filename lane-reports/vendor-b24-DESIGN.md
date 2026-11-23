# vendor-b24 design: OD57 in every vendor read shape, one rule for both scanners (B24-1)

Builder: a Claude Opus 5.5 sub-agent of glitch-26 (the Lane-orchestrator, under Javier's standing delegation).
Written: Wed 21 Oct 2026, from 03:41 EDT (`date`).
Clone: /Users/javrodher/aegis-builds/vendor-b24-20261021, branch lane/vendor-b24-20261021, base d8ceb1811393df8f709596874b5064396fe658d6.
Door read (never edited): /Users/javrodher/glitch/workspaces/aegis/ops/athena_suite.py, unchanged from 4c2db58 to the workspace head 040a7bb (`git diff --stat 4c2db58 HEAD -- ops/athena_suite.py` is empty).
Design only: no code, nothing run on athena, nothing written there, no push, no mirror.

## 0. In one paragraph

w-g22 did not meet a new copy of a known read.
It met a read tool that neither scanner admits: Gemini's `grep_search` (displayName SearchText), run with `dir_path` set to the doc's folder.
All 11 findings in its walk log are the OD57 line, every one inside the exact 80 bytes, carried as `L175: <line>` in the tool's output and as a bare `line` field in its `resultDisplay.matches[]`.
The harness twin refused it because `grep_search` is not in the Gemini shapes' tool table (B17-7 / open point O2 of B17-DESIGN-NOTE kept it out, as Claude's Grep is kept out), and the door would refuse it for the same reason and also because it reads no `$patch` record.
`grep_search` is a common Gemini read: 184 calls and 319 replayed responses in the 33 committed Gemini walks.
So the selection risk in the brief is real: a measured take that greps the doc would be held on its tool choice.
The design below admits the line in every vendor read shape the walks produce, with one binding per shape that names the doc by a tool-written field.
It recommends one rule set in one module, shared by the twin and the door through a byte-pinned copy, plus one shared corpus that both must judge the same.

## 1. B24-1(a): w-g22's findings

Source: the walk log /home/javier/w-2T3c9VTJ/walk.log (exit 1, `state: held`, "the drive scan refused the take", "the walk folder is left for a human, never committed").
The log names 11 generic-api-key findings on 7 record lines, all in `rehearsals/w-g22/session/`.
The turn streams (turn-1.jsonl, turn-2.jsonl) hold no finding in the log.

Method: each flagged line was read over `ssh athena 'sed -n Np <file>'` into memory on the Mac, never written to disk on either side.
gitleaks 8.30.0 on the Mac (athena's pin is 8.30.1) ran on each line through `gitleaks stdin`, its report kept in memory; it found the same count per line as the walk log (2, 1, 2, 1, 1, 2, 2).
Only types, keys, counts, lengths, character classes, sha256 and masks (letters and digits as `x`) were printed.
Script: /private/tmp/claude-501/-Users-javrodher-glitch/53dfdf22-47a7-465a-873b-7e472f6f10e7/scratchpad/b24/char_wg22.py and probe2.py.

The match, the same at all 11 findings:
- length 37 characters, classes lower + upper + digit and `` . : = ` `` and space;
- sha256 of the match e7408198cd714004426c69346edb01ae61538338f6b0fd15cdce43e5ef1d10ba (the rule's Secret group: 14 characters, sha256 prefix 7e391d92);
- masked context: ``x xxxxx xxxxxxx xxxxxx\\xxxxx: xxx xxxxxx xxxxxxxx: `xxxxxxx==x.x.x`, `xxxxxx-xxxxx==x.x.x`, `xxxx`` (a package==version pin list);
- the match starts at the first byte of the OD57 text and lies inside it (`inside_OD57=True` at every one);
- the OD57 line here is the sha256 0b85623f…df313 line, 80 bytes, the same as RULED_LINES in both scanners.

| File:line | Record | Where the line sits (JSON path) | Tool, call | Findings |
|---|---|---|---|---|
| native-turn-1.jsonl:198 | `gemini` message: keys content, id, model, thoughts, timestamp, tokens, toolCalls, type | (1) `toolCalls[0].result[0].functionResponse.response.output`, output line 11 of 21, after the prefix `L175: `; (2) `toolCalls[0].resultDisplay.matches[6].line`, the whole string | toolCalls[0] keys args, description, displayName (SearchText), id, name (`grep_search`), renderOutputAsMarkdown, result, resultDisplay (a dict: matches, summary), status (success), timestamp; args `dir_path`, `pattern` | 2 |
| native-turn-1.jsonl:199 | `user` message: keys content, id, timestamp, type | `content[0].functionResponse.response.output`, line 11 of 21, after `L175: ` | functionResponse {id, name `grep_search`, response {output}}, the same call id as :198 | 1 |
| native-turn-2.jsonl:198 | same record as turn-1:198 (same sha256 of the line) | as turn-1:198 | as turn-1:198 | 2 |
| native-turn-2.jsonl:199 | same record as turn-1:199 | as turn-1:199 | as turn-1:199 | 1 |
| native-turn-2.jsonl:272 | `user` message | `content[0].functionResponse.response.output`, line 11 of 21, after `L175: ` | grep_search, same call id | 1 |
| native-turn-2.jsonl:622 | `user` message | `content[0]` and `content[1]`, two functionResponse parts with the same id, each line 11 of 21 after `L175: ` | grep_search, same call id | 2 |
| native-turn-2.jsonl:798 | control line: top-level key `$patch` only; `$patch` keys removeIds, updates (46 updates) | `$patch.updates[38].toolCalls[0].result[0]` and `.result[1]`, two functionResponses (both `grep_search`, one id) | the `$patch` toolCalls entry has keys id and toolCalls' result only: no name, no args, no resultDisplay | 2 |

The read that produced it, from the call (keys and masks only):
- tool `grep_search`; its first word is the tool itself, there is no shell;
- `dir_path` masked `x/_x`: it ends in `_references`, the doc's own folder, relative to the run tree; it is not the doc itself;
- `pattern` masked `x-x|x|x|x|x|x`, 50 characters: an alternation written by the model;
- output (21 lines): line 0 the tool's header (`x x x x x "<pattern>" x x "<dir>":`), then three blocks of `---`, `File: <path relative to dir_path>`, and `L<n>: <text>` lines; the OD57 line is in the second block, whose header is masked `File: x.x` (one name, `environment.md`, relative to the doc's folder), at `L175: `;
- resultDisplay.matches: 13 entries {absolutePath, filePath, line, lineNumber}; entries 3 to 7 have an absolutePath ending in `_references/environment.md`; entry 6 is lineNumber 175 with `line` equal to the OD57 text; every `filePath` is relative (none ends in the doc's suffix).

Is each one inside the exact OD57 line? Yes, all 11: the match begins at the line's first byte and ends 37 bytes in, and removing the line's 80 bytes removes the match.
But in the function responses the line is not a whole line of the output: it follows `L175: `, which neither scanner's prefix list (`_RULED_PREFIX`) allows.

Why each scanner refuses, replayed in memory on lines 198-199 of native-turn-1 with the code as it stands (scratchpad replay.py, Python 3.12; the .pyc files it wrote in the clone and in aegis ops were deleted after):
- twin (`scan_record._ruled_text` with gemini_adapter.READ_SHAPES): refuse, refuse. The session shapes find the call (`grep_search`), but `_shape_read` returns None: `grep_search` is not in the shape's tools.
- door (`ruled_line_text` with `_VENDOR_READERS["g"]`): refuse, refuse. `_GEMINI_TOOLS` is read_file and run_shell_command only.
- Even with the tool admitted, the prefix `L175: ` is not allowed; the door reads no `$patch` line (798); and on line 198 the `resultDisplay.matches[6].line` copy is counted by the raw-count guard but read by no shape, so the record would still refuse.

## 2. B24-1(b): the vendor read shapes that can carry the line

Counts are from the records clone /Users/javrodher/aegis-builds/gap4-walk-records-20261019 (71 walk refs: 33 Gemini, 38 GPT; distinct blobs: Gemini 44 session and 44 stream files, Codex 89 and 89), read with `git cat-file`, types, keys and counts only (scratchpad survey.py, survey2.py).
That clone holds w-g21; its five OD57 lines are the only ones in any committed vendor stream or session file (5 found).
Source citations are the ones the adapters already pin (Gemini CLI 0.64.0 bundle, tarball 891a794e…; openai/codex rust-v0.162.1, 092d3acd).

"Twin" is scan_record.py with the adapters' READ_SHAPES at d8ceb181; "door" is athena_suite.py at 4c2db58.

| # | Shape (where the doc's text is) | In committed walks | Twin today | Door today | The rule that admits only the whole OD57 line |
|---|---|---|---|---|---|
| G1 | Gemini session `read_file` functionResponse `response.output`: in a `gemini` record's `toolCalls[i].result[j]`, a `user` record's `content[i]`, and under `$patch` (direct or `updates[*]`) | 419 calls; responses 419 (toolCalls) + 584 (user) + 185 + 8 (`$patch`) | admits: path kind on `file_path` (suffix rule), all six positions, anchored | admits in `gemini` and `user` records (RS6 path rule); `$patch` lines refused | the call (one distinct call for the id, found only at a `gemini` record's `toolCalls[*]`) is `read_file` whose `file_path` names the doc; the line is a whole output line, no prefix |
| G2 | Gemini session `run_shell_command` functionResponse output: `<untrusted_context>` first line, then `Output: <first stdout line>`, the stdout, a `Process Group PGID: N` tail | 1714 calls; 1714 + 2448 + 413 responses | admits: script kind (`_ruled_bash`), prefix `Output: ` on the first line after the opener only | refuses a line right behind `Output: `; admits other whole stdout lines, but only in a record with no resultDisplay copy (RS7: in practice the `user` record only) | `_ruled_bash` admits the call's `command`; the call's args hold no key but command and description (no `dir_path`, as B20-6's git binding); the line is a whole stdout line, or the first line after the opener with exactly `Output: ` before it; the wrapper and PGID lines are tool-written and never admitted text |
| G3 | Gemini session `run_shell_command` `resultDisplay` (a string, the raw stdout) | 1714 (all strings) | admits (shape "session resultDisplay", joined) | refuses (the copy is not read, so the raw count differs and the whole `gemini` record refuses) | the same call test as G2, on the same toolCalls entry; whole stdout lines only |
| G4 | **Gemini session `grep_search` functionResponse output** (w-g22): header line, then `---` / `File: <rel>` / `L<n>: ` (match) or `L<n>- ` (context) lines | 184 calls; 184 + 319 + 77 responses; output lines: 2284 `L<n>: `, 2813 `L<n>- `, 713 `File: ` (all relative), 836 `---` | refuses (tool not in the table) | refuses (tool not admitted; `$patch` not read) | new tool kind (§2.1): the line is exactly `L175: ` or `L175- ` then the 80 bytes, inside a block whose `File: ` path, joined to the call's `dir_path` (`.` when absent) and normalised, names the doc; and the call's own `gemini` record in the same file attests it (G5) |
| G5 | **Gemini session `grep_search` `resultDisplay.matches[k]`** {absolutePath, filePath, line, lineNumber} (w-g22 line 198) | 168 dict displays, 2284 match entries | refuses (only `run_shell_command` has a display shape) | refuses | a match entry whose `line` is exactly the 80 bytes, `lineNumber` is 175, and `absolutePath` names the doc (suffix rule on an absolute path); in a `grep_search` toolCalls entry of a `gemini` record, its id naming one call |
| G6 | Gemini turn stream `tool_result.output` (the display string), joined to `tool_use` by `tool_id` | 2277 tool_use and 2277 tool_result; 1875 string outputs | admits `run_shell_command` only (`read_file`'s and `grep_search`'s displays carry no file text, per the adapter's cites) | refuses (the `g` reader reads only `gemini` and `user` records) | `tool_use` (one per id) is `run_shell_command` with `_ruled_bash` admitting `parameters.command`; whole stdout lines; no prefix |
| G7 | Gemini session `$patch` lines: `updates[*]` entries {id, toolCalls} or {id, content}; w-g22's toolCalls entry there has id and result only, no name | 20 `$patch` lines; 779 update entries | admits functionResponses under `$patch` and `$patch.updates[*]`, the call found by id in a `gemini` record elsewhere in the file | refuses every `$patch` line | as G1, G2, G4 for the functionResponse's own `name`, the call found by id only at a `gemini` record's `toolCalls[*]` (never at the nameless `$patch` entry) |
| G8 | Gemini git read (B20-5): a diff body line `+`/`-`/space then the 80 bytes, in a hunk of `diff --git a/gars/_references/environment.md b/…` | none carrying the line | admits for `git log -p -n 1 <sha>` / `git show <sha>`, args command and description only | refuses (no git rule) | unchanged B20-5/B20-7 rule, now in the shared module so the door has it too |
| O1 | Codex turn stream `item.completed` / `item.started` `command_execution.aggregated_output`; `command` the shell-quoted argv | 452 items, all `/bin/bash -lc` | admits `[/bin/bash, -lc or -c, script]`, string or list, copies "same" | admits `/bin/bash -lc` only, string or list (F-RS-6) | `command` is exactly `/bin/bash -lc <script>` and `_ruled_bash(<script>)`; whole output lines after `_RULED_PREFIX`; `-c` dropped from the twin (no committed record uses it; admitting less is fine) |
| O2 | Codex rollout `event_msg` `item_completed` `CommandExecution.aggregated_output` (keys aggregated_output, command, cwd, duration, exit_code, id, parsed_cmd, process_id, source, status, type) | 508 | admits: argv list `[/bin/bash, -lc, script]` | admits `/bin/bash -lc`, list or string | the list form only, as the twin; git reads only with `cwd` = `file://` + session_meta's cwd (B20-6) |
| O3 | Codex rollout `custom_tool_call_output.output[*].text` of the `exec` JavaScript tool, tied by `call_id` to its `custom_tool_call` | 483 calls, 483 outputs (all lists); no `function_call` or `function_call_output` exists | admits only spans that copy, verbatim or as one exact JSON string literal, an O2 read lying between this exec's call line and its output line (B17-16b to B17-22) | refuses (held item 1 of rs-od57) | unchanged twin copy rule, in the shared module |
| O4 | Codex model text (`agent_message`, `response_item` `message`, `reasoning`) | 169, 894, 303 | refuses | refuses | stays refused: model text is never a read |

### 2.1 The new Gemini grep rule (G4, G5), exactly

- The call: `grep_search` only (its legacy alias `search_file_content` is not admitted: no committed record names it; admitting less is fine).
- The call is found by its id only at a `gemini` record's `toolCalls[*]`, and every copy of that id carries the same name and args (copies "same"); a `$patch` toolCalls entry, which has no name, is never a call.
- The args hold no key but `pattern`, `dir_path`, `include_pattern` (the committed sets; `path`, 4 calls, and every option such as `context`, `before`, `after`, `names_only`, `no_ignore` refuse, so context lines `L<n>- ` never arise in an admitted read).
  If glitch-26 wants context lines admitted, the rule adds `context`, `before`, `after` to the allowed keys and `L175- ` to the forms; the design defaults to not admitting them.
- G5, the attestation, read from the call's own toolCalls entry: a `resultDisplay.matches[k]` with `lineNumber` 175, `line` exactly the 80 bytes, and `absolutePath` absolute, normalised, and ending in `/gars/_references/environment.md`.
- G4, the output, in any of G1's six positions: the functionResponse's `name` is `grep_search`, its id finds that call, and that call's G5 attestation exists in the same file.
  The output splits on `\n` into line 0 (the tool's header) and blocks; a block opens at a `File: <p>` line that follows a `---` line.
  The OD57 line is admitted only as a line exactly `L175: ` + the 80 bytes, inside a block whose `normpath(join(dir_path or ".", p))` equals `gars/_references/environment.md` or ends in `/gars/_references/environment.md`, with no `..` left after normalising.
  Line 0 is never admitted text (it carries the model's pattern).
- Why the attestation: a functionResponse's output is one string, so a file whose *name* holds newlines could forge a `---` / `File: …environment.md` / `L175: …` block inside it.
  The display's `matches[]` are JSON fields the tool writes per match, which a file name cannot split.
  The `user` and `$patch` copies carry no display of their own; the attestation ties them to their call's `gemini` record in the same file (w-g22 holds it in both session files, native-turn-2 replaying it; that every session file always does is inferred from the recorder, not counted here).
- Line number 175: grep is the one shape that writes the doc's own line number into tool-written fields, so the rule binds it; if the doc was edited and the line moved, the read refuses.

### 2.2 The binding every shape keeps (the common core, as both scanners have it today)

- The finding's file is an agent-text file of a walk of the shape's family and file kind (twin: `kinds`; door: `RULED_VENDOR_TEXT` group 1 plus, new, the file kind: F-RS-5 closed by keying on (family, file kind)).
- The 80 bytes at sha256 0b85623f…df313, never a near line: the length and the digest are checked on the text after only the shape's own prefix.
- Every occurrence of those bytes in the record, decoded and raw, is an admitted hit, or the record refuses (so a copy no shape reads, such as w-g22's display line today, refuses the record).
- The probe rescan: the file with exactly those occurrences removed is scanned again, and any finding of the rule on that line refuses (a second key on the line).
- Each admitted finding is listed (`ruled` in the twin, `OD57:<commit>:<path>:<line>` at the door).

### 2.3 Two tightenings proposed for both scanners together (each needs a ruling)

- T1, the doc-write guard ("never a write followed by a read"): in the same file, a write-kind call whose path names the doc, at a line before the read, disqualifies every OD57 admission after it.
  Write-kind: Gemini `write_file` and `replace` (`file_path`); Codex `file_change` items whose changes name the doc; Claude `Write`, `Edit`, `MultiEdit` (if the Claude path is brought in).
  Shell writes (`>`, `tee`, `sed -i`) are not detectable in general and stay a named residual, bounded by the digest: only the public line's own 80 bytes can ever be admitted.
- T2, a single-operand shell read: today `_ruled_bash` needs only *a* token naming the doc, so `grep -h x <doc> /tmp/notes.md` admits lines printed from a model-written file.
  Tightened: in the grep or cat segment, every non-option operand after grep's pattern is the doc (cat: every operand), and grep takes no `-f`, `-r`, `-R` or `--include`.
  No committed vendor walk reads the doc by shell (the reviewer's sweep: only w-g21's read_file), so this narrows nothing that has been seen.

## 3. B24-1(c): how the two scanners agree

Options weighed:
- (A) one rule set: the OD57 admission moves out of scan_record.py into a stdlib-only module, and the door runs a byte-pinned copy of it;
- (B) two implementations, bound by a differential test: one shared corpus of shaped records run through both, verdicts compared;
- (C) one data table read by two engines: the shapes as data, each scanner with its own reader.

Recommendation: (A), with (B)'s corpus as its binding check.

Why (A): every divergence found so far came from two hand-kept readers drifting (MINOR-1 path rule, F-RS-5 file kinds, F-RS-6 `-c`, NIT-4 suffix, the held `$patch`, stream, resultDisplay, exec-copy and git gaps).
A new tool kind written twice doubles exactly the code that keeps failing review.
(C) still leaves two engines; (B) alone detects drift but only on the cases someone thought to write.

The shape of (A):
- Study repo: new `evals/gap-study-4/box/od57_rule.py`, stdlib only (hashlib, json, posixpath, re, shlex), holding RULED_LINES, `_RULED_PREFIX`, `_ruled_bash`, `_ruled_git`, the read-shape schema and engine (`_check_shapes`, `_shape_calls`, `_shape_strings`, `_copy_hits`, `_ruled_text`), the new grep kind and T1/T2 if ruled.
  Its entry point is a pure function over bytes: `ruled_text(body, ruling, file_bytes, family, file_kind, line)`.
- New `evals/gap-study-4/box/od57_shapes.py`, data only, no imports: the per-(family, file kind) shapes.
  `gemini_adapter.READ_SHAPES` and `codex_adapter.READ_SHAPES` become those values (drive.scan_read_shapes is unchanged: it reads `module.READ_SHAPES`).
- scan_record.py keeps its probe, masking, witness and refusal code and calls od57_rule; its Claude path stays byte-for-byte (no shapes = before B17).
- Door: `ops/od57_rule.py` and `ops/od57_shapes.py` are byte copies, each pinned in athena_suite.py by sha256 and the study commit they came from; a test fails when the copy's bytes differ from the pin.
  athena_suite.py's vendor branch calls the copy; Claude's admission (`RULED_AGENT_TEXT`, `_ruled_tool`) is unchanged, so F-RS-4 stays a named follow-up.
  The door keeps its own probe rescan and `OD57:` listing.
- The corpus (B's part): `evals/gap-study-4/tests/fixtures/od57-agreement/` holds synthetic records built from the committed shapes (types and keys as §2, invented text, the real public line), one case per row of §4, each with its expected verdict per (file, line).
  The twin's test runs them through `scan_record._ruled_findings` with a fake scanner; the door's test runs the same files (copied, pinned by sha256) through `ruled_line_findings` on a scratch git repo with the real gitleaks.
  Both must reproduce the expected verdicts; the door test also runs the four committed walk re-scans (w-g21's five admissions, w-o47, w-g20) unchanged.

Cost: the door's import surface grows by one reviewed module; test_sidecar's default-deny audit gains an entry for od57_rule.py (its imports are a subset of scan_record's today).

Parity of the scanner call itself (added at 03:45 EDT on glitch-26's message; see §5a): agreement on the rule is worth nothing if one seat's gitleaks run can be silenced.
The door's every content scan already passes `--ignore-gitleaks-allow` and `--gitleaks-ignore-path` to an emptied file of its own (`scan_flags`, athena_suite.py:1055-1059; `no-rulings.gitleaksignore` at :2167 and :2763), and walk_launch.py's own scans do the same (box/walk_launch.py:410-411).
The twin's commit-time scanner does not (§5a); after (f) the two seats run gitleaks with the same allowance flags.
The door's calls are left as they are.

## 4. B24-1(d): witnesses that must stay refused, and the red tests

Red tests are written first and must fail on d8ceb181 (twin) and 4c2db58 (door) where the shape is new to that scanner.

Admission witnesses (each must fail first, then pass), per scanner unless marked:
- G4/G5: w-g22's real shape, synthetic text: the `gemini` record (output + display) and its `user`, replayed `user` (two parts, one id) and `$patch` copies, each admitted; red on both scanners.
- G2 with the real wrapper: a `cat` of the doc, the line deep in the stdout, and a `grep` whose only line follows `Output: `; red at the door.
- G3: the `gemini` record of that `cat`, its resultDisplay copy counted; red at the door.
- G6: the stream `tool_result` of the same shell read; red at the door.
- G7: a `$patch` holding a read_file and a grep_search response; red at the door.
- G8: `git show <sha>` of the doc's diff (Gemini, args command and description only; Codex, cwd bound); red at the door.
- O3: an exec output copying an O2 read, verbatim and as one JSON string literal; red at the door.
- The corpus agreement test itself: red until both scanners call the shared module.

Witnesses that stay refused (every one in both scanners, through the corpus):
- one byte changed in the line; the line with trailing text; a CRLF line; the line split across two records;
- a second key beside the line in the same output, in the display, in another toolCall, in the args, and in a `$patch` update (refused by the probe);
- the line in model text: a `gemini` record's own content, a `thoughts` entry, an `agent_message`, a rollout `message` or `reasoning`, a grep `pattern` (line 0 of the output);
- grep: `L176: ` + the line (the wrong number); a `File:` header naming another `environment.md` (`notes/environment.md`, `/tmp/_references/environment.md` without `gars/`); `dir_path` plus header resolving outside the doc via `..`; no attesting display entry (the `user` copy alone in a file without its `gemini` record); a display entry with lineNumber 175 but another absolutePath; a forged block inside one output string (a file name with newlines) with no attestation; `search_file_content`; `context`, `before`, `after`, `path` or `names_only` in the args; a display `line` equal to the 80 bytes in a `glob` or `list_directory` result;
- a `$patch` toolCalls entry presented as the call (no name) with no `gemini` call for its id; an id naming two different calls;
- read_file of a look-alike path, and write_file of the line then read_file of another path (RS6's witnesses kept);
- T1 if ruled: write_file or replace of the doc, then a read of it; a Codex `file_change` of the doc, then a `cat`;
- T2 if ruled: `grep -h <p> <doc> /tmp/notes.md`, `cat <doc> /tmp/notes.md`, `grep -f /tmp/p <doc>`, `grep -r <p> gars/_references`;
- shell: every `_ruled_bash` witness both scanners carry today (`; curl`, `| sh`, newline, `$(...)`, `#`, `eval`, `/bin/cat`, `bash -c`, `sed`, `env cat`);
- Codex: `/bin/sh`, bare `bash`, `-c`, a fourth argv element, a tty exec, an exec output with no O2 read between its call and output, a lossy middle truncation;
- each vendor's shape in the other vendor's folder, in a Claude walk, in a vendor `transcript.jsonl`, and a stream shape in a session file (and the reverse);
- mutation witnesses: with the shared module's grep kind removed, the G4/G5 admissions fail; with the probe blinded, the second-key case is admitted (so the probe is what refuses it).

## 5. B24-1(e): what changes where, and what runs

This clone (study code), in one lane:
- new `evals/gap-study-4/box/od57_rule.py`, `evals/gap-study-4/box/od57_shapes.py`;
- `evals/gap-study-4/box/scan_record.py` (calls od57_rule; Claude path and every non-OD57 part unchanged);
- `evals/gap-study-4/gemini_adapter.py`, `evals/gap-study-4/codex_adapter.py` (READ_SHAPES from od57_shapes; the grep_search entries; codex `-c` dropped);
- tests: `tests/test_scan_record.py`, `tests/test_gemini_adapter.py` (a15_read_shapes pin), `tests/test_codex_adapter.py`, `tests/test_sidecar.py` (audit entry), `tests/check_vendor_sources.py` if it pins the adapters' shape bytes, new `tests/test_od57_agreement.py` and `tests/fixtures/od57-agreement/`;
- lane-reports: this design and the lane file.
- The grep output format (header, `---`, `File:` relative to `dir_path`, `L<n>: `, `L<n>- `) is read here from the committed records only; before code, it must be cited from the pinned 0.64.0 bundle (around chunk-NR7L3FXV.js 321746-322309, where gemini_tool_sources.py cites the grep invocation), which needs a read-only `docker cp` on athena (held, §6).

aegis (the door), in its own lane after this one lands:
- new `ops/od57_rule.py`, `ops/od57_shapes.py` (byte copies, pinned);
- `ops/athena_suite.py` (the vendor branch calls the copy; `_VENDOR_READERS` and `_GEMINI_TOOLS` retire; the pin constants);
- `ops/test_athena_od57.py` (the corpus run, the pin test, the re-scans) and the corpus copy under `ops/fixtures/`;
- `lane-reports/lane/` note.

Runs:
- Study code: yes, athena's battery on the lane head, and a mirror, because the walks run this code inside the drive on athena (the twin is study code).
- Door: the aegis suites on the Mac under heavy slots (`test_athena_od57`, `test_athena_rulings`, `test_athena_door_rule`, `test_athena_suite`), with the known 20 GB disk-floor failures read as before; no mirror.
- Re-scans, read-only, at the end: w-g21 (five admissions unchanged), w-g22 from a copy of its walk folder (eleven admissions, both scanners), w-o47 and w-g20 (unchanged).

## 5a. B24-1(f): the twin's gitleaks call reads a `.gitleaksignore` from its working folder

Added Wed 21 Oct 2026 03:45 EDT, on glitch-26's message (its read-only check: a planted `.gitleaksignore` silenced a finding, found=[] on gitleaks 8.30.0 in a throwaway test).

Where (verified by reading, nothing run): the call is `scan_argv` in `evals/gap-study-4/box/rules_scanner.py:49-54`, not in scan_record.py (scan_record only receives the built callable).
It runs `[binary, "dir", path, "--no-banner", "--redact", "--ignore-gitleaks-allow", "--report-format", "json", "--report-path", report, "--exit-code", "0", "--log-level", "warn"]`, with no `--gitleaks-ignore-path`.
gitleaks' default for that flag is `.` (8.30.0 `stdin --help` on this Mac: "path to .gitleaksignore file or folder containing one (default ".")"), so the runtime's working folder decides which ignore file applies.
Which folder that is on athena (`runtime.run` in the drive) was not checked here.
The scanner's environment is built from nothing (`run_take.runtime_env`, only RUNTIME_ENV_NAMES), so `GITLEAKS_CONFIG` and `GITLEAKS_CONFIG_TOML` do not reach it unless those names are in that list (not checked).

The change:
- `gitleaks_scanner` makes, once per build, an empty file of its own in its report folder (for example `report_dir/no-rulings.gitleaksignore`, created with exclusive create, mode 600, size 0 checked before each scan), and `scan_argv` takes it and passes `--gitleaks-ignore-path <that file>`.
- The report folder's "must exist and be empty" check stays; the ignore file is created after it, and the report counter's names cannot collide with it.
- Before each scan the file is checked to be a plain file (not a link) of 0 bytes; anything else refuses (ScannerRefused).
- Files: box/rules_scanner.py; tests/test_rules_scanner.py (it binds scan_argv's argv); any test or pin that holds scan_argv's exact argv or rules_scanner.py's bytes (check_vendor_sources, test_sidecar's audit for rules_scanner.py, the stub-take record test) is updated in the same lane.
  Study code: athena's battery and a mirror, as §5.

Red tests (written first, failing on d8ceb181):
- with a `.gitleaksignore` holding the finding's fingerprint in the scan's working folder, a planted canary key in a scanned file is still found (today: silenced);
- the same with the ignore file in the scanned file's own folder;
- `scan_argv`'s argv carries `--gitleaks-ignore-path` naming a file inside the report folder;
- the ignore file replaced by a link, or written non-empty between scans: the next scan refuses;
- these run the pinned binary where it exists (athena) and the same flags with the Mac's 8.30.0 locally, and are skipped nowhere silently: a missing binary is a named failure.

Adjacent, not checked, raised for glitch-26: neither seat passes `--config`, and gitleaks' config precedence includes "(target path)/.gitleaks.toml" (same help text).
For the twin's `dir <file>` and the door's `git <repo>` scans, whether a `.gitleaks.toml` planted in the scanned tree (a take could write one into its record folder or a commit) would replace the default rules is not verified; if it would, both seats need an explicit `--config` to a pinned file, with its own red test.

## 6. Held for glitch-26

1. The grep rule's scope: admit `grep_search` at all (the design says yes: it is the selection risk the brief names), and if so, with or without context lines (default: without).
2. Claude parity: Claude's `Grep` is not admitted (B17-7), and Claude's `Read` is admitted for any path at the door (F-RS-4).
   The same selection argument applies to the Claude arm; the design leaves Claude unchanged and asks whether a twin lane follows.
   Not checked: whether any committed Claude walk read the doc with Grep.
3. T1 (doc-write guard) and T2 (single-operand shell read): adopt, or leave as named residuals.
4. Option (A), the shared module with a pinned copy in the door, against (B), the corpus alone.
5. The pinned-source read of `grep_search`'s output format needs a read-only container copy on athena (creates and removes a container and a temporary folder there): a ruling, because this round writes nothing on athena.
6. Codex: whether the code-mode `exec` tool can read a file other than through a CommandExecution (a JS read with no O2 record would carry the line with nothing to copy) was not checked against the pinned source here; the twin's B17-16 note says only `exec` and `wait` are exposed.
7. rs-od57's held item 4 stands: this Mac's free disk is under athena_suite's 20 GB local floor.
