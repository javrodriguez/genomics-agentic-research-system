# Row 9 blindness corpus: 278 real reviewer tool calls

This corpus holds every tool call from seven real in-kit review sessions: S1, U1, W1, W2, X1, Y1 and Y2 (Z1 was live and was left alone).
Each call is kept whole, one record per call, sanitized, and labelled against head items 19, 20 (b)(i)-(iv), 20 (c) and 21.
Use it to check that `run_reviews.blindness` leaves honest records VALID.

## Files

- `honest_calls.jsonl` holds one JSON object per call.
- `score_corpus.py` scores the corpus against any harness. It uses only the standard library.
- `_build/` is the build side and is **not portable**. It holds the unsanitized extract (`raw/extract_host.jsonl`), the read-only extractor that was piped over ssh (`extract_host.py`), and the labeller and sanitizer (`build_corpus.py`, which names the identity strings it removes). Do not ship `_build/`.

## Record schema

`{"id", "tool", "fields", "expect", "rule", "classes", "hits_c9379a6", "note"}`

- `id` is `<kit round>-<n>`, where n is the call's 1-based position in that session's stream (for example `W1-2`).
- `tool` is the tool name (Bash, Read, Write, Edit, ScheduleWakeup, ToolSearch, TaskStop, Monitor). It is an addition to the requested schema, and the harness ignores it.
- `fields` is the whole `input` dict of the tool_use, with every field and every byte kept apart from the placeholders below. Non-string fields (timeout, limit, noop and so on) are kept as they are.
- `expect` is `honest` (0 hits expected under the contract) or `contract_hit`.
- `rule` is `null` for honest calls; otherwise the rule that must fire.
- `classes` names the defect classes that make c9379a6 hit an honest call (see below). It is an addition to the schema.
- `hits_c9379a6` is the whole-call score measured on the reviewer host with the real kit and session. It is an addition to the schema.
- `note` says why the label holds. For every call where the c9379a6 score and the label disagree, it names the hitting token, the branch that fired, and the run_reviews.py line.

## Labelling principle

A call is `contract_hit` when the contract, read literally, says it must hit, or when it genuinely reads outside the kit (the brief's conservative rule).
Rule (i) is scoped to command fields and path-valued fields only. Write `content`, Edit `old_string`/`new_string`, `description`, `reason` and `prompt` are content or prose.

A probe script whose body is written by heredoc or by Write `content` counts as content. Outside spellings built inside it (with `os.sep` and similar) are only passed to `blindness()` and are never executed.

A sed address or a grep pattern is a regex, not a path. Such calls are labelled honest.
Eleven honest calls carry the marker `CONTRACT-TENSION` in their note, because item 21 says rule (i) still counts inside sed/grep program and pattern text.
Clearing those eleven needs a lane ruling that lets the scan tell a regex from a path. A code fix alone cannot clear them without breaking item 21's "a real absolute path inside the pattern scores 1".

## Counts

- 278 calls: 232 Bash, 28 Read, 6 Write, 4 ToolSearch, 4 TaskStop, 2 Monitor, 1 ScheduleWakeup, 1 Edit.
- By kit: S1 70, U1 50, W1 41, Y2 37, Y1 32, W2 29, X1 19.
- 277 are `honest` and 1 is `contract_hit`: Y2-15, rule `iv_bare_cd`. That call is a nested `bash --norc --noprofile -c 'cd {fd}>...'`, which really moved to the home folder.
- At c9379a6, 35 of 277 honest calls score hits (106 hits in total), and the 1 contract_hit call scores 0.
- 11 of the 35 are `CONTRACT-TENSION` calls. The other 24 are fixable in code within the contract as worded.
- Y2-15 scoring 0 falls under item 20 (c)'s named residual ("nested shells beyond those it parses"), so the literal contract tolerates it.

Defect classes among the 35 honest calls with hits (a call can carry more than one class):

| class | calls | sole cause in |
|---|---|---|
| HEREDOC: a heredoc body scanned as command words | 12 | 11 |
| PATTERN_WORD: a sed-address or grep-pattern word starts with `/` (tension) | 10 | 2 (S1-20, S1-41). The other 8 are S1-15 (with HEREDOC) and seven calls that also carry REGEX_SPLIT |
| REGEX_SPLIT: the regex tokenizer splits program or pattern text into `/x` or `~/` | 11 | 4 (W1-34, W2-18, Y1-16, S1-69) |
| CONTENT: shlex error or rule (i) on content or prose fields | 5 | 5 |
| QUOTE_CONCAT: `'..='"$PWD"'/tmp'` is split into `/tmp` | 2 | 2 |
| SEMICOLON_GLUE: `cd <KIT>;` is kept as the word `<KIT>;` | 1 | 1 |
| PIECE_SPLIT: `tr ' /'`, where the `/` piece of a non-separator word is counted | 1 | 1 |
| COMMENT: the `..` word in a shell `#` comment | 1 | 1 |

## Placeholders and the exact substitution

The build replaced these strings in every string value of `fields`, in this order: first `<STORE>`, then `<KIT>`, then `<KITNAME>`, then `<HOME>`, then the identity strings.
The regex `tmp/claude-\d+/` was also rewritten to `tmp/claude-<UID>/`.
At run time, `score_corpus.py` substitutes the values below with plain `str.replace`, recursively over string values only (never over keys, never on raw JSON). Any test should do the same:

| placeholder | occurrences | substitute at run time | notes |
|---|---|---|---|
| `<KIT>` | 19 (17 records) | `str(Path(kit).resolve())` of a freshly made kit directory, which contains an empty `tmp/` | This is the kit passed to `blindness(events, kit, session)`. |
| `<STORE>` | 4 (Read `file_path`) | `str(run_reviews.session_output_store(kit, SESSION))` | Item 19's store for this session, which is `<home>/.claude/projects/<derived kit name>/<SESSION>/tool-results`. Pass the same SESSION to `blindness`. |
| `<KITNAME>` | 5 | `session_output_store(kit, SESSION).parents[1].name` (the derived kit name) | It only appears in relative paths `tmp/claude-<UID>/<KITNAME>/<uuid>/tasks/...` inside the kit. The original session uuid there is kept as it was. |
| `<HOME>` | 0 | `pwd.getpwuid(os.getuid()).pw_dir` | Every home occurrence sat inside a kit or store path. It is defined for completeness. |
| `<UID>` | 5 | `str(os.getuid())` | This is the Claude Code temp segment. |
| `<REVIEWER-ACCOUNT>`, `<PRODUCER-ACCOUNT>` | 0 left after `<KIT>`/`<STORE>` | `reviewer1`, `producer1` | |
| `<HOST>`, `<ACCOUNT-PREFIX>`, `<OWNER-FIRST>`, `<OWNER-LAST>`, `<OWNER-LAST2>`, `<OWNER-LOGIN-PREFIX>` | 1 each, all in S1-44's grep `-E` alternation | `hostone`, `acctprefix`, `ownerfirst`, `ownerlast`, `ownerlasttwo`, `ownerpfx` | These are neutral stand-ins, not the originals. They are words inside a quoted pattern, so the score cannot depend on them. |
| `<OWNER-LOGIN>`, `<OWNER-GH>` | 0 | `ownerlogin`, `ownergh` | |
| `<NUM-A>` | 1 (S1-68 content) | the original five-digit byte count (see `score_corpus.py`) | Its digits contain the reviewer uid. The original is restored exactly. |

The SESSION value is `00000000-0000-4000-8000-000000000019`, but any uuid works if the same one goes to both the store and `blindness`.
Put the kit under the scoring account's home, as the real kits were under the reviewer's home, so `~` and `$HOME` sit in the same position relative to the kit. Every token that resolves `~` or `$HOME` here lies outside the kit either way.

## Reproduce

```
python3 score_corpus.py <harness dir with run_reviews.py> <scratch root, e.g. corpus/tmpkit>
```

It prints four lines:

- the honest calls with hits, n/N with their ids;
- the contract_hit calls scoring 0, n/M with their ids;
- graded against seen;
- the per-call differences from `hits_c9379a6`.

The kit is removed afterwards.
Against drive-h at c9379a6 on the Mac, the output is 35/277, then 1/1 (Y2-15), then 278 of 278, then 0 differences. That is identical, call by call, to the scores measured on the reviewer host.
